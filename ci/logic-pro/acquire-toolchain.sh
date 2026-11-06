#!/usr/bin/env bash
# Reuse only hash-pinned frozen inputs; unavailable archives use the same recipe.
set -euo pipefail
[[ $# == 1 ]] || { echo 'usage: acquire-toolchain.sh OUTPUT_DIRECTORY' >&2; exit 2; }
source_root=$(git rev-parse --show-toplevel)
output=$(realpath -m "$1")
[[ ! -e "$output" && ! -L "$output" ]] || { echo 'Output must not exist' >&2; exit 2; }
arguments=(--manifest "$source_root/docs/compat/logic-pro/retained-toolchain.json"
  --committed-lock "$source_root/docs/compat/logic-pro/toolchain.lock.json"
  --recipe "$source_root/ci/logic-pro/Dockerfile.p003")
origin=$(python3 "$source_root/tools/compat/logic-pro/restore_toolchain.py" origin "${arguments[@]}")
download=$(mktemp -d)
trap 'rm -rf "$download"' EXIT
# curl strips Authorization on cross-host redirects. No token is needed by the
# downloaded archive; all content is bound to its committed SHA256 before use.
headers=(-H 'Accept: application/vnd.github+json')
if [[ -n "${GITHUB_TOKEN:-}" ]]; then headers+=(-H "Authorization: Bearer $GITHUB_TOKEN"); fi
if curl --fail --silent --show-error --location --retry 2 --connect-timeout 30 \
    --max-time 300 "${headers[@]}" "$origin" -o "$download/toolchain.zip" \
    2> "$download/download.log"; then
  # Integrity errors are fatal. Only unavailability permits fresh acquisition.
  python3 "$source_root/tools/compat/logic-pro/restore_toolchain.py" restore \
    "${arguments[@]}" --archive "$download/toolchain.zip" --output "$output"
else
  echo 'Retained archive unavailable; acquiring the unchanged frozen recipe.'
  cat "$download/download.log" >&2
  bash "$source_root/ci/logic-pro/prepare-toolchain.sh" "$output"
fi
cp "$download/download.log" "$output/retained-download.log"
