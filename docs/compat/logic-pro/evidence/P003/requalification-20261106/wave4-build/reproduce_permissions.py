#!/usr/bin/env python3
"""Independent, bounded execution of the actual old and repaired EXIT handlers.

Synthetic Git repositories exercise status capture only. This is not a Darling
build, uploader-host execution, or runtime qualification receipt.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[7]
OLD = "af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2"
NEW = "cc268442e9711beeb117f59850dcc6526dd03c46"


def git(*args: str, cwd: Path = ROOT) -> bytes:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def main() -> None:
    sources = {name: git("show", revision + ":ci/logic-pro/build-p003.sh").decode()
               for name, revision in (("old", OLD), ("repaired", NEW))}
    sources["without_fchmod_control"] = sources["repaired"].replace(
        "        os.fchmod(stream.fileno(), 0o644)\n", "")
    assert sources["without_fchmod_control"] != sources["repaired"]
    results = []
    for version, script in sources.items():
        finish = "finish() {\n" + script.split("finish() {\n", 1)[1].split(
            "\ntrap finish EXIT", 1)[0]
        for mask in ("022", "077"):
            for dirty in (False, True):
                for original_code in (0, 42):
                    with tempfile.TemporaryDirectory(prefix="p003-wave4-permission-") as temporary:
                        base = Path(temporary)
                        source, evidence = base / "source", base / "evidence"
                        source.mkdir()
                        evidence.mkdir()
                        pin = source / "docs/compat/logic-pro/submodules.lock.json"
                        pin.parent.mkdir(parents=True)
                        pin.write_bytes(b"{}\n")
                        tracked = source / "tracked.txt"
                        tracked.write_bytes(b"original\n")
                        lock = base / "toolchain.lock.json"
                        lock.write_bytes(b"{}\n")
                        git("init", "-q", cwd=source)
                        git("add", ".", cwd=source)
                        git("-c", "user.name=Independent P003 Review", "-c",
                            "user.email=review@example.invalid", "commit", "-qm",
                            "Controlled source fixture", cwd=source)
                        commit = git("rev-parse", "HEAD", cwd=source).decode().strip()
                        if dirty:
                            tracked.write_bytes(b"changed\n")
                        expected = git("status", "--porcelain=v1", "--untracked-files=all",
                                       "--ignore-submodules=none", cwd=source)
                        stage = "compile" if original_code else "complete"
                        harness = "\n".join((
                            "set -euo pipefail", "source_root=$1", "evidence=$2",
                            "source_commit=$3", "lock=$4", "stage=$5", 'umask "$7"',
                            "export SOURCE_DATE_EPOCH=0", finish, "trap finish EXIT",
                            'exit "$6"', ""))
                        run = subprocess.run(
                            ["bash", "-s", "--", str(source), str(evidence), commit,
                             str(lock), stage, str(original_code), mask], input=harness,
                            text=True, capture_output=True, timeout=10)
                        status = evidence / "source-status-after.txt"
                        summary = json.loads((evidence / "build-summary.json").read_text())
                        mode = stat.S_IMODE(status.lstat().st_mode)
                        expected_mode = (0o600 if version == "old" or
                                         (version == "without_fchmod_control" and mask == "077")
                                         else 0o644)
                        code = original_code or int(dirty)
                        expected_stage = "source-cleanliness" if dirty and not original_code else stage
                        assert status.read_bytes() == expected
                        assert stat.S_ISREG(status.lstat().st_mode)
                        assert mode == expected_mode
                        assert run.returncode == code == summary["exit_code"]
                        assert summary["status"] == ("FAIL" if code else "PASS")
                        assert summary["last_stage"] == expected_stage
                        results.append({"version": version, "umask": mask, "dirty": dirty,
                                        "original_exit_code": original_code,
                                        "actual_exit_code": run.returncode,
                                        "last_stage": summary["last_stage"],
                                        "status_bytes_hex": expected.hex(),
                                        "actual_mode_octal": oct(mode),
                                        "group_and_other_read": bool(mode & 0o040) and bool(mode & 0o004)})
    report = {"schema": "darling.p003.wave4.permission-review.v1",
              "reviewer": "/root/wave4_build", "non_author": True,
              "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "old_revision": OLD, "repaired_revision": NEW,
              "producer_sha256": {name: hashlib.sha256(script.encode()).hexdigest()
                                  for name, script in sources.items()},
              "cases": results, "status": "PASSED",
              "scope": "24 isolated EXIT-handler cases; no hosted uploader or full build acceptance."}
    destination = Path(__file__).with_name("permission-reproduction.json")
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "cases": len(results),
                      "receipt": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
