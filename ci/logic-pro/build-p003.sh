#!/usr/bin/env bash
# This entry point runs only inside a new privileged, disposable qualification
# container. The privilege is a Darwin runtime prerequisite, not a build need.
set -euo pipefail
if [[ $# -ne 4 ]]; then
  echo 'usage: build-p003.sh SOURCE BUILD EVIDENCE TOOLCHAIN_LOCK' >&2
  exit 2
fi
source_root=$(realpath "$1")
build=$(realpath -m "$2")
evidence=$(realpath -m "$3")
lock=$(realpath "$4")
# Fixed paths make compiler path-sensitive outputs comparable across fresh VMs.
[[ "$source_root" == /p003/source && "$build" == /p003/build && "$evidence" == /p003/evidence ]] || {
  echo 'P003 requires its documented isolated /p003 paths' >&2; exit 2;
}
test -f /.dockerenv || { echo 'Run only in a disposable Docker container' >&2; exit 2; }
[[ "$(id -u)" == 0 ]] || { echo 'Runtime setup needs root inside the isolated container' >&2; exit 2; }
[[ ! -e "$build" && ! -e /opt/darling-p003 && ! -e /p003/runtime-first && ! -e /p003/runtime-second ]] || {
  echo 'Clean build, installation and runtime paths are required' >&2; exit 2;
}
mkdir -p "$evidence"
test -z "$(find "$evidence" -mindepth 1 -maxdepth 1 -print -quit)" || { echo 'Evidence output must be empty' >&2; exit 2; }
export PYTHONDONTWRITEBYTECODE=1 LC_ALL=C.UTF-8 LANG=C.UTF-8 TZ=UTC
export CC=clang-14 CXX=clang++-14
export SOURCE_DATE_EPOCH
SOURCE_DATE_EPOCH=$(git -C "$source_root" show -s --format=%ct HEAD)
source_commit=$(git -C "$source_root" rev-parse HEAD)
export P003_SOURCE_REVISION="$source_commit"
stage=toolchain
finish() {
  result=$?
  trap - EXIT
  if [[ "$stage" != complete && "$result" == 0 ]]; then result=1; fi
  python3 - "$evidence" "$source_root" "$source_commit" "$lock" "$stage" "$result" <<'PY'
import hashlib, json, os, platform, sys
from pathlib import Path
out, source, commit, lock, stage, result = sys.argv[1:]
report = {
    "schema": "darling.p003.build.v1", "phase": "P003",
    "source_commit": commit, "toolchain_sha256": hashlib.sha256(Path(lock).read_bytes()).hexdigest(),
    "build_id": os.environ.get("P003_BUILD_ID"),
    "source_lock_sha256": hashlib.sha256((Path(source)/"docs/compat/logic-pro/submodules.lock.json").read_bytes()).hexdigest(),
    "status": "PASS" if result == "0" and stage == "complete" else "FAIL",
    "last_stage": stage, "exit_code": int(result),
    "host_kernel": platform.uname()._asdict(),
    "runtime_privileges": {"uid": os.getuid(), "disposable_privileged_container": True},
    "installation_prefix": "/opt/darling-p003", "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH"),
    "configuration": {
      "components": "cli,gui", "target_x86_64": True, "target_i386": False,
      "build_type": "Release", "metal": "ON", "ccache": False,
      "p003_probes": True, "debian_packaging": True,
      "compiler_c": "/usr/bin/clang-14", "compiler_cxx": "/usr/bin/clang++-14"
    }
}
Path(out, "build-summary.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
PY
  exit "$result"
}
trap finish EXIT
cp "$lock" "$evidence/toolchain.lock.json"
stage=runtime-prerequisites
# Verify required namespace/overlay operations on the actual bind-mounted
# filesystem before spending time compiling. Never accept a disabled overlay.
mkdir -p /p003/prerequisite/{lower,upper,work,merged}
unshare --mount --fork bash -c '
  set -euo pipefail
  mount --make-rprivate /
  mount -t overlay overlay -o lowerdir=/p003/prerequisite/lower,upperdir=/p003/prerequisite/upper,workdir=/p003/prerequisite/work /p003/prerequisite/merged
  trap "umount /p003/prerequisite/merged" EXIT
  printf "p003-overlay\n" > /p003/prerequisite/merged/probe
  test "$(cat /p003/prerequisite/upper/probe)" = p003-overlay
' 2>&1 | tee "$evidence/runtime-prerequisites.log"
rm -rf /p003/prerequisite
stage=toolchain
python3 "$source_root/tools/compat/logic-pro/lock_toolchain.py" verify \
  --lock "$lock" --recipe "$source_root/ci/logic-pro/Dockerfile.p003" \
  --output "$evidence/toolchain-host-observation.json" \
  2>&1 | tee "$evidence/toolchain-verification.log"
stage=source-lock
python3 "$source_root/tools/compat/logic-pro/check_submodules.py" \
  --repo "$source_root" --lock "$source_root/docs/compat/logic-pro/submodules.lock.json" \
  --output "$evidence/source-lock-verification.json" \
  2>&1 | tee "$evidence/source-lock-verification.log"
git -C "$source_root" submodule status --recursive > "$evidence/submodule-heads.txt"
git -C "$source_root" status --porcelain=v1 --untracked-files=all > "$evidence/source-status-before.txt"
test ! -s "$evidence/source-status-before.txt" || { echo 'Root source must be clean' >&2; exit 1; }
stage=configure
mkdir -p "$build/.cmake/api/v1/query"
touch "$build/.cmake/api/v1/query/codemodel-v2"
cmake -S "$source_root" -B "$build" -G Ninja \
  -DCMAKE_C_COMPILER=/usr/bin/clang-14 -DCMAKE_CXX_COMPILER=/usr/bin/clang++-14 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/darling-p003 \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DDARLING_NO_CCACHE=ON \
  -DTARGET_x86_64=ON -DTARGET_i386=OFF -DCOMPONENTS=cli,gui \
  -DDEBIAN_PACKAGING=ON -DENABLE_METAL=ON -DCOMPILE_PY2_BYTECODE=OFF \
  -DDARLING_P003_PROBES=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  2>&1 | tee "$evidence/configure.log"
cp "$build/CMakeCache.txt" "$evidence/CMakeCache.txt"
cp "$build/compile_commands.json" "$evidence/compile_commands.json"
stage=compile
build_jobs=$(nproc)
memory_kib=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
if [[ "$memory_kib" -lt 8388608 ]]; then build_jobs=2; fi
cmake --build "$build" --parallel "${P003_BUILD_JOBS:-$build_jobs}" \
  2>&1 | tee "$evidence/build.log"
stage=install-first
python3 "$source_root/tools/compat/logic-pro/isolated_install.py" mark \
  --prefix /opt/darling-p003 --output "$evidence/install-owner.json"
cmake --install "$build" 2>&1 | tee "$evidence/install-first.log"
cp "$build/install_manifest.txt" "$evidence/cmake-install-manifest-first.txt"
python3 "$source_root/tools/compat/logic-pro/verify_build_install.py" \
  --source "$source_root" --build "$build" --prefix /opt/darling-p003 \
  --output "$evidence/install-first.json"
python3 "$source_root/tools/compat/logic-pro/native_dependencies.py" \
  --source "$source_root" --prefix /opt/darling-p003 \
  --output "$evidence/native-first.json"
stage=probes-first
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$source_root/tools/compat/logic-pro/run_build_probes.py" \
  --installation /opt/darling-p003 --output "$evidence/probes-first" \
  --prefix /p003/runtime-first 2>&1 | tee "$evidence/probes-first.log"
stage=uninstall
python3 "$source_root/tools/compat/logic-pro/isolated_install.py" remove \
  --prefix /opt/darling-p003 --marker "$evidence/install-owner.json" \
  --manifest "$evidence/install-first.json" --output "$evidence/uninstall.json"
test ! -e /opt/darling-p003
# The second invocation cannot use any installed binaries from the first:
# remove its separate, stopped Darwin prefix after checking for live mounts.
python3 - <<'PY'
from pathlib import Path
import os, shutil
for prefix in (Path('/p003/runtime-first'), Path('/p003/runtime-first.home'), Path('/p003/runtime-first.workdir')):
    if prefix.is_symlink():
        raise SystemExit('Unexpected symlink at owned runtime path')
    if prefix.exists():
        for root, dirs, files in os.walk(prefix, followlinks=False):
            if os.path.ismount(root):
                raise SystemExit('Runtime mount remains after required shutdown')
        shutil.rmtree(prefix)
    assert not prefix.exists()
PY
stage=install-second
python3 "$source_root/tools/compat/logic-pro/isolated_install.py" mark \
  --prefix /opt/darling-p003 --output "$evidence/install-owner-second.json"
cmake --install "$build" 2>&1 | tee "$evidence/install-second.log"
cp "$build/install_manifest.txt" "$evidence/cmake-install-manifest-second.txt"
python3 "$source_root/tools/compat/logic-pro/verify_build_install.py" \
  --source "$source_root" --build "$build" --prefix /opt/darling-p003 \
  --output "$evidence/install-second.json"
python3 "$source_root/tools/compat/logic-pro/native_dependencies.py" \
  --source "$source_root" --prefix /opt/darling-p003 \
  --output "$evidence/native-second.json"
stage=probes-second
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$source_root/tools/compat/logic-pro/run_build_probes.py" \
  --installation /opt/darling-p003 --output "$evidence/probes-second" \
  --prefix /p003/runtime-second 2>&1 | tee "$evidence/probes-second.log"
stage=build-manifest
# Preserve the actual installed bytes for independent inspection; the private
# removal-ownership marker is not part of the redistributable installation.
tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner \
  --exclude=./.p003-isolated-install.json -C /opt/darling-p003 -cf - . \
  | gzip -n -6 > "$evidence/runtime-prefix.tar.gz"
sha256sum "$evidence/runtime-prefix.tar.gz" > "$evidence/runtime-prefix.sha256"
# Record source-built linker identity; it is produced from the pinned cctools
# submodule and is intentionally not confused with the native Linux linker.
python3 - "$build" "$evidence" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
build, out = map(Path, sys.argv[1:])
linkers = []
for path in sorted((build/'src/external/cctools-port/cctools/ld64/src').rglob('*')):
    if path.is_file() and path.name.endswith('-ld'):
        run = subprocess.run([str(path), '-v'], capture_output=True, text=True)
        linkers.append({'path': str(path.relative_to(build)),
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'version_exit_code': run.returncode,
                        'version_output': run.stdout+run.stderr})
if not linkers:
    raise SystemExit('Source-built Mach-O linker evidence missing')
(out/'source-built-linker.json').write_text(json.dumps(linkers, indent=2)+"\n")
PY
git -C "$source_root" status --porcelain=v1 --untracked-files=all > "$evidence/source-status-after.txt"
stage=complete
