#!/usr/bin/env bash
# Freeze a single acquired toolchain for both independent P003 build VMs.
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo 'usage: prepare-toolchain.sh OUTPUT_DIRECTORY [UBUNTU_SNAPSHOT]' >&2
  exit 2
fi
source_root=$(git rev-parse --show-toplevel)
output=$(realpath -m "$1")
snapshot=${2:-20261031T000000Z}
[[ "$snapshot" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] || { echo 'Invalid snapshot timestamp' >&2; exit 2; }
mkdir -p "$output"
test -z "$(find "$output" -mindepth 1 -maxdepth 1 -print -quit)" || { echo 'Output must be empty' >&2; exit 2; }
committed_lock="$source_root/docs/compat/logic-pro/toolchain.lock.json"
locked_packages=''
if [[ -f "$committed_lock" ]]; then
  pins=$(python3 "$source_root/tools/compat/logic-pro/lock_toolchain.py" recipe-pins --lock "$committed_lock")
  mapfile -t frozen <<< "$pins"
  [[ ${#frozen[@]} == 3 ]] || { echo 'Malformed frozen toolchain pins' >&2; exit 1; }
  base=${frozen[0]}
  snapshot=${frozen[1]}
  locked_packages=${frozen[2]}
  if [[ $# == 2 && "$2" != "$snapshot" ]]; then
    echo 'Requested snapshot conflicts with committed toolchain lock' >&2; exit 1
  fi
  docker pull --platform linux/amd64 "$base" 2>&1 | tee "$output/base-pull.log"
else
  # Observed in hosted acquisition 41269126730; do not resolve a mutable tag
  # again between the first failed bootstrap and its qualification rerun.
  base=ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11
  docker pull --platform linux/amd64 "$base" 2>&1 | tee "$output/base-pull.log"
fi
[[ "$base" =~ ^ubuntu@sha256:[0-9a-f]{64}$ ]] || { echo 'No immutable Ubuntu base digest' >&2; exit 1; }
docker build --platform linux/amd64 --no-cache \
  --secret id=bootstrap_ca,src=/etc/ssl/certs/ca-certificates.crt \
  --build-arg "BASE_IMAGE=$base" --build-arg "UBUNTU_SNAPSHOT=$snapshot" \
  --build-arg "LOCKED_PACKAGES=$locked_packages" \
  -f "$source_root/ci/logic-pro/Dockerfile.p003" \
  -t darling-p003-toolchain:locked "$source_root/ci/logic-pro" \
  2>&1 | tee "$output/toolchain-build.log"
image_id=$(docker image inspect darling-p003-toolchain:locked --format '{{.Id}}')
docker run --rm --platform linux/amd64 \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$source_root,dst=/source,readonly" \
  --mount "type=bind,src=$output,dst=/evidence" \
  darling-p003-toolchain:locked \
  python3 /source/tools/compat/logic-pro/lock_toolchain.py capture \
    --base-image "$base" --image-id "$image_id" --snapshot "$snapshot" \
    --recipe /source/ci/logic-pro/Dockerfile.p003 --output /evidence/toolchain.lock.json
docker save darling-p003-toolchain:locked | gzip -1 > "$output/toolchain-image.tar.gz"
python3 "$source_root/tools/compat/logic-pro/lock_toolchain.py" seal \
  --lock "$output/toolchain.lock.json" --archive "$output/toolchain-image.tar.gz"
if [[ -f "$committed_lock" ]]; then
  python3 "$source_root/tools/compat/logic-pro/lock_toolchain.py" compare-environment \
    --lock "$committed_lock" --candidate "$output/toolchain.lock.json"
fi
sha256sum "$output/toolchain.lock.json" "$output/toolchain-image.tar.gz" > "$output/SHA256SUMS"
