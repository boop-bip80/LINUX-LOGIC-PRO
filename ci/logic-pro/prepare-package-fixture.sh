#!/usr/bin/env bash
# Prepare real source-package tools before the fixture's 60-second deadline.
set -euo pipefail
if [[ $# != 1 ]]; then
  echo 'usage: prepare-package-fixture.sh OUTPUT_DIRECTORY' >&2
  exit 2
fi

source_root=$(git rev-parse --show-toplevel)
recipe="$source_root/ci/logic-pro/Dockerfile.package-fixture"
lock="$source_root/docs/compat/logic-pro/toolchain.lock.json"
output=$(realpath -m -- "$1")
[[ ! -L "$1" ]] || { echo 'Output must not be a symlink' >&2; exit 1; }
mkdir -p "$output"
[[ -z "$(find "$output" -mindepth 1 -maxdepth 1 -print -quit)" ]] || {
  echo 'Output directory must be empty' >&2
  exit 1
}

parameters=$(python3 - "$lock" <<'PY'
import datetime
import json
import pathlib
import re
import sys

record = json.loads(pathlib.Path(sys.argv[1]).read_text())
base = record.get("base_image")
snapshot = record.get("ubuntu_snapshot")
if not isinstance(base, str) or re.fullmatch(r"ubuntu@sha256:[0-9a-f]{64}", base) is None:
    raise SystemExit("Committed toolchain must pin an immutable Ubuntu base")
if not isinstance(snapshot, str) or re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", snapshot) is None:
    raise SystemExit("Committed toolchain must pin an Ubuntu archive snapshot")
datetime.datetime.strptime(snapshot, "%Y%m%dT%H%M%SZ")
print(base)
print(snapshot)
PY
)
mapfile -t frozen <<< "$parameters"
[[ ${#frozen[@]} == 2 ]] || { echo 'Malformed fixture image pins' >&2; exit 1; }
base=${frozen[0]}
snapshot=${frozen[1]}

# No tag can select a stale image after a failed build. The public image-id.txt
# is written only after the newly built image and its real packages are checked.
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 --pull --no-cache \
  --secret id=bootstrap_ca,src=/etc/ssl/certs/ca-certificates.crt \
  --build-arg "BASE_IMAGE=$base" --build-arg "UBUNTU_SNAPSHOT=$snapshot" \
  --iidfile "$output/built-image-id.txt" \
  -f "$recipe" "$source_root/ci/logic-pro" \
  2>&1 | tee "$output/build.log"
image_id=$(cat "$output/built-image-id.txt")
[[ "$image_id" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo 'Invalid built image ID' >&2; exit 1; }
docker image inspect "$image_id" > "$output/image-inspect.json"

inspection=(docker run --rm --pull never --platform linux/amd64 --network none --read-only
  --tmpfs /tmp:rw,nosuid,nodev,mode=1777 "$image_id")
"${inspection[@]}" /usr/bin/dpkg-query --show \
  '--showformat=${binary:Package}\t${Architecture}\t${Version}\n' > "$output/packages.tsv"
"${inspection[@]}" /bin/cat /etc/os-release > "$output/os-release"

python3 - "$output" "$base" "$snapshot" "$recipe" "$lock" <<'PY'
import hashlib
import json
import pathlib
import re
import shlex
import sys

output, base, snapshot, recipe, lock = sys.argv[1:]
output = pathlib.Path(output)
image_id = (output / "built-image-id.txt").read_text().strip()
if re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
    raise SystemExit("Fixture image ID is not immutable")
inspection = json.loads((output / "image-inspect.json").read_text())
if (not isinstance(inspection, list) or len(inspection) != 1
        or inspection[0].get("Id") != image_id
        or inspection[0].get("Architecture") != "amd64"
        or inspection[0].get("Os") != "linux"):
    raise SystemExit("Built image identity or Linux amd64 platform changed")

os_release = (output / "os-release").read_text()
os_fields = {}
for line in os_release.splitlines():
    if line and not line.startswith("#"):
        key, value = line.split("=", 1)
        os_fields[key] = " ".join(shlex.split(value))
if os_fields.get("ID") != "ubuntu" or os_fields.get("VERSION_ID") != "22.04":
    raise SystemExit("Fixture image is not Ubuntu 22.04")

packages = []
seen = set()
for line in (output / "packages.tsv").read_text().splitlines():
    name, architecture, version = line.split("\t")
    if not name or not architecture or not version or (name, architecture) in seen:
        raise SystemExit("Malformed or duplicate installed package record")
    seen.add((name, architecture))
    packages.append({"name": name, "architecture": architecture, "version": version})
required = {"ca-certificates", "dpkg-dev", "build-essential", "xz-utils"}
if not required.issubset({item["name"].split(":", 1)[0] for item in packages}):
    raise SystemExit("Fixture image is missing required source-package tools")

def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

record = {
    "schema": "darling.package-fixture-image.v1",
    "purpose": "Synthetic Debian source-package regression fixtures",
    "image_id": image_id,
    "base_image": base,
    "ubuntu_snapshot": snapshot,
    "recipe_sha256": sha256(recipe),
    "toolchain_lock_sha256": sha256(lock),
    "architecture": "amd64",
    "os_release": os_release,
    "packages": sorted(packages, key=lambda item: (item["name"], item["architecture"])),
    "build_log": {"file": "build.log", "sha256": sha256(output / "build.log")},
    "image_inspect": {"file": "image-inspect.json", "sha256": sha256(output / "image-inspect.json")},
}
(output / "image-metadata.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
(output / "image-id.txt").write_text(image_id + "\n")
print("Prepared source-package fixture image:", image_id)
print("Fixture image metadata:", output / "image-metadata.json")
PY
