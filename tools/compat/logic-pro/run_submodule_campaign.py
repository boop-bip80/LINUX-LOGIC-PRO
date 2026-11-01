#!/usr/bin/env python3
"""Qualify P002 with ordinary Git at an immutable root commit.

The source checkout supplies the runner/tests only. Dependency objects come from
a fresh anonymous clone, never that checkout's object store. Failed commands and
fixture transcripts are retained alongside successful evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

from check_submodules import safe_url
from run_baseline import verify_fixture_transcript

SHA = re.compile(r"^[0-9a-f]{40}$")
SOURCE_URL = "https://github.com/boop-bip80/MAC-OS-EMULATION.git"
MIN_FIXTURE_TESTS = 96  # The independently accepted P002 fixture-suite baseline.


class CampaignFailure(ValueError):
    pass


def environment(*, allow_local: bool = False) -> dict[str, str]:
    """Keep proxy/CA settings, not ambient Git selectors, alternates or tokens."""
    excluded = {"GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT", "SSH_AUTH_SOCK", "SSH_AGENT_PID",
                "SSH_ASKPASS", "SSH_ASKPASS_REQUIRE", "NETRC", "CURL_HOME"}
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k not in excluded
           and not k.endswith(("_TOKEN", "_PASSWORD", "_SECRET"))}
    # libcurl/Git LFS can read netrc independently of credential.helper. Refuse
    # such an environment rather than read or relocate private credentials.
    if any(os.path.lexists(Path.home() / name) for name in (".netrc", "_netrc")):
        raise CampaignFailure("anonymous acquisition requires an environment without a netrc credential file")
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "/bin/false", "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_ALLOW_PROTOCOL": "https:file" if allow_local else "https",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return env


def git(*args: str) -> list[str]:
    return ["git", "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false",
            "-c", "credential.helper=", "-c", "http.extraHeader=",
            "-c", "core.attributesFile=" + os.devnull, "-c", "core.autocrlf=false",
            "-c", "core.symlinks=true", "-c", "core.filemode=true", *args]


def validate_commit(commit: str) -> str:
    if not isinstance(commit, str) or not SHA.fullmatch(commit):
        raise CampaignFailure("--commit must be a full lowercase 40-character commit SHA")
    return commit


def verify_fixture_suite(transcript: str) -> int:
    """Require the final unittest result to be green and retain accepted coverage."""
    try:
        count = verify_fixture_transcript(transcript)
    except ValueError as exc:
        raise CampaignFailure(str(exc)) from exc
    if count < MIN_FIXTURE_TESTS:
        raise CampaignFailure(f"P002 fixture coverage shrank: {count} < {MIN_FIXTURE_TESTS}")
    return count


def write_json(path: Path, value: dict | list) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class Commands:
    def __init__(self, output: Path, *, allow_local: bool = False):
        self.output, self.allow_local = output, allow_local
        self.records: list[dict] = []

    def run(self, label: str, argv: list[str], filename: str, *, cwd: Path | None = None,
            append: bool = False, required: bool = True, timeout: float = 3600,
            fixtures: bool = False) -> tuple[int, bytes]:
        started = time.monotonic()
        log = self.output / filename
        offset = log.stat().st_size if append and log.exists() else 0
        print(f"P002: {label}", flush=True)
        with log.open("ab" if append else "wb") as stream:
            try:
                result = subprocess.run(argv, cwd=cwd, env=environment(allow_local=self.allow_local or fixtures),
                                        stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, check=False)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 124
                stream.write(b"\nP002 command timed out\n")
            except OSError as exc:
                code = 127
                stream.write(("\nP002 could not start command: " + type(exc).__name__ + "\n").encode())
        with log.open("rb") as stream:
            stream.seek(offset)
            data = stream.read()
        self.records.append({"label": label, "command": argv, "cwd": str(cwd) if cwd else None,
                             "exit_code": code, "duration_seconds": round(time.monotonic() - started, 3),
                             "log": filename, "log_offset": offset, "log_bytes": len(data),
                             "output_sha256": hashlib.sha256(data).hexdigest()})
        write_json(self.output / "commands.json", self.records)
        if required and code:
            raise CampaignFailure(f"{label}: exit {code}; see {filename}")
        return code, data


def acquire_checkout(url: str, commit: str, destination: Path, commands: Commands,
                     *, host_id: str = "a", jobs: int = 12) -> str:
    validate_commit(commit)
    safe_url(url, allow_local=commands.allow_local)
    if destination.exists() or destination.is_symlink():
        raise CampaignFailure("clone destination already exists; existing objects are never reused")
    logfile = f"clone-{host_id}.log"
    commands.run("clone-root", git("clone", "--no-local", "--no-hardlinks", "--no-checkout",
                                  "--no-recurse-submodules", "--origin", "origin", url, str(destination)), logfile)
    code, _ = commands.run("locate-exact-commit", git("-C", str(destination), "cat-file", "-e", commit + "^{commit}"),
                           logfile, append=True, required=False)
    if code:
        # PR merge commits may be advertised only outside refs/heads. Fetch the
        # immutable SHA, never a newly advanced master or PR branch tip.
        commands.run("fetch-exact-commit", git("-C", str(destination), "fetch", "--no-tags",
                     "--no-recurse-submodules", "origin", commit), logfile, append=True)
    commands.run("checkout-exact-commit", git("-C", str(destination), "checkout", "--detach", commit),
                 logfile, append=True)
    _, raw = commands.run("verify-exact-head", git("-C", str(destination), "rev-parse", "HEAD"), "head.sha")
    head = raw.decode().strip()
    if head != commit:
        raise CampaignFailure("cloned HEAD differs from the exact requested implementation SHA")
    commands.run("ordinary-recursive-submodules", git("-C", str(destination), "submodule", "update",
                 "--init", "--recursive", "--jobs", str(jobs)), logfile, append=True, timeout=6000)
    return head


def verify_native_status(raw: bytes, lock: dict) -> int:
    expected = {e["path"]: e["commit"] for e in lock["submodules"]}
    if not expected or len(expected) != lock["expected_recursive_gitlinks"]:
        raise CampaignFailure("native status oracle has an incomplete or duplicated dependency lock")
    observed = set()
    for line in raw.decode("utf-8", "strict").splitlines():
        if len(line) < 43 or line[0] != " " or line[41] != " ":
            raise CampaignFailure("native Git status reports a missing, mismatched, conflicted or invalid gitlink")
        pin, rest = line[1:41], line[42:]
        matches = [p for p in expected if rest == p or rest.startswith(p + " (")]
        if len(matches) != 1 or matches[0] in observed or expected[matches[0]] != pin:
            raise CampaignFailure("native recursive status differs from the locked paths or exact commits")
        observed.add(matches[0])
    if observed != set(expected):
        raise CampaignFailure("native recursive status does not cover every locked dependency")
    return len(observed)


def verify_lock_regeneration(original: Path, regenerated: Path, output: Path) -> None:
    before, after = original.read_bytes(), regenerated.read_bytes()
    result = {"result": "PASS" if before == after else "FAIL",
              "committed_sha256": hashlib.sha256(before).hexdigest(),
              "regenerated_sha256": hashlib.sha256(after).hexdigest(), "byte_identical": before == after}
    write_json(output / "lock-regeneration.json", result)
    if before != after:
        raise CampaignFailure("regenerated recursive lock is not byte-identical to committed provenance")


def verify_hydration_report(hydration: dict, lock: dict) -> tuple[int, int]:
    expected_lfs = lock["expected_lfs_objects"]
    expected_bytes = sum(record["size"] for record in lock["lfs_objects"])
    if (hydration.get("result") != "PASS" or hydration.get("expected_lfs_objects") != expected_lfs
            or hydration.get("verified_lfs_objects") != expected_lfs
            or hydration.get("verified_payload_bytes") != expected_bytes):
        raise CampaignFailure("LFS report does not prove every locked payload's exact bytes")
    expected = [{key: record[key] for key in ("path", "oid_sha256", "size", "mode")}
                for record in lock["lfs_objects"]]
    observed = [dict(record) for record in hydration.get("objects", [])]
    for record in observed:
        if record.pop("status", None) != "PASS":
            raise CampaignFailure("LFS report contains a nonpassing payload")
    if observed != expected or hydration.get("errors"):
        raise CampaignFailure("LFS report object digests, paths or sizes differ from the committed lock")
    return expected_lfs, expected_bytes


def verify_physical_report(verdict: dict, lock: dict, commit: str) -> None:
    count = len(lock["submodules"])
    if (verdict.get("result") != "PASS" or verdict.get("root_commit") != commit
            or verdict.get("schema_version") != 2
            or verdict.get("verified_gitlinks") != count
            or verdict.get("verified_repositories") != count + 1
            or type(verdict.get("verified_physical_blobs")) is not int
            or verdict["verified_physical_blobs"] <= count
            or verdict.get("verified_lfs_payloads") != lock["expected_lfs_objects"]
            or verdict.get("verified_lfs_bytes") != sum(record["size"] for record in lock["lfs_objects"])
            or verdict.get("verification_method") != "physical_committed_bytes_modes_symlinks_and_lfs_sha256_without_filters"):
        raise CampaignFailure("strict verifier report does not match the exact complete physical campaign")


def checksums(output: Path) -> None:
    records = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
               for p in sorted(output.iterdir()) if p.is_file() and p.name != "checksums.sha256"]
    (output / "checksums.sha256").write_text("".join(records))


def run_campaign(source: Path, destination: Path, output: Path, commit: str, *,
                 host_id: str = "a", url: str = SOURCE_URL, jobs: int = 12,
                 allow_local: bool = False) -> dict:
    validate_commit(commit)
    if host_id not in ("a", "b") or not 1 <= jobs <= 32:
        raise CampaignFailure("host must be a or b and jobs must be 1..32")
    if destination.is_symlink() or output.is_symlink():
        raise CampaignFailure("clone and evidence paths must not be symlinks")
    source, destination, output = source.resolve(strict=True), destination.resolve(), output.resolve()
    paths = [source, destination, output]
    if any(a == b or a in b.parents or b in a.parents for i, a in enumerate(paths) for b in paths[i + 1:]):
        raise CampaignFailure("source, fresh clone and evidence directories must be separate and non-overlapping")
    # Refuse existing evidence instead of deleting it or accepting stale files.
    output.mkdir(parents=True, exist_ok=False)
    commands = Commands(output, allow_local=allow_local)
    summary = {"schema_version": 1, "phase": "P002", "result": "FAIL", "host_id": host_id,
               "implementation_commit": commit, "failures": [], "ordinary_git_acquisition": True,
               "credential_or_reference_cache_used": False,
               "started_at": datetime.now(timezone.utc).isoformat()}
    try:
        safe_url(url, allow_local=allow_local)
        if destination.exists() or destination.is_symlink():
            raise CampaignFailure("clone destination already exists; no cleanup or reuse is permitted")
        _, version = commands.run("git-version", git("--version"), "git-version.txt")
        details = {"utc": summary["started_at"], "git": version.decode().strip(),
                   "python": platform.python_version(), "system": platform.system(),
                   "kernel": platform.release(), "machine": platform.machine(),
                   "runner_os": os.environ.get("RUNNER_OS"), "runner_arch": os.environ.get("RUNNER_ARCH"),
                   "image_os": os.environ.get("ImageOS"), "image_version": os.environ.get("ImageVersion")}
        (output / "environment.txt").write_text(json.dumps(details, indent=2, sort_keys=True) + "\n")
        _, source_head = commands.run("source-head", git("-C", str(source), "rev-parse", "HEAD"), "source-head.sha")
        if source_head.decode().strip() != commit:
            raise CampaignFailure("runner/test source HEAD differs from requested implementation SHA")
        acquire_checkout(url, commit, destination, commands, host_id=host_id, jobs=jobs)
        commands.run("fixture-tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s",
                     str(destination / "tests/compat/logic-pro/submodules"), "-v"], "fixture-tests.log",
                     cwd=destination, fixtures=True)
        transcript = (output / "fixture-tests.log").read_text()
        summary["fixture_tests_executed"] = verify_fixture_suite(transcript)
        lock_path = destination / "docs/compat/logic-pro/submodules.lock.json"
        lock = json.loads(lock_path.read_text())
        tool = destination / "tools/compat/logic-pro"
        _, lfs_version = commands.run("git-lfs-version", git("lfs", "version"), "git-lfs-version.txt")
        details["git_lfs"] = lfs_version.decode().strip()
        write_json(output / "environment.txt", details)
        commands.run("hydrate-locked-lfs", [sys.executable, "-B", str(tool / "lfs_manifest.py"),
                     "hydrate", "--repo", str(destination), "--lock", str(lock_path),
                     "--output", str(output / "lfs-hydration.json")], "lfs-hydration.log", cwd=destination,
                     timeout=6000)
        hydration = json.loads((output / "lfs-hydration.json").read_text())
        expected_lfs, expected_bytes = verify_hydration_report(hydration, lock)
        summary.update(verified_lfs_objects=expected_lfs, verified_lfs_payload_bytes=expected_bytes)
        _, status = commands.run("native-recursive-status", git("-C", str(destination), "submodule", "status", "--recursive"),
                                 "native-git-status.txt")
        summary["native_gitlinks_verified"] = verify_native_status(status, lock)
        commands.run("strict-lock-verifier", [sys.executable, "-B", str(tool / "check_submodules.py"),
                     "--repo", str(destination), "--lock", str(lock_path), "--output", str(output / f"verification-{host_id}.json")],
                     f"verifier-{host_id}.log", cwd=destination)
        verdict = json.loads((output / f"verification-{host_id}.json").read_text())
        verify_physical_report(verdict, lock, commit)
        commands.run("regenerate-lock", [sys.executable, "-B", str(tool / "make_submodule_lock.py"),
                     "--repo", str(destination), "--evidence", str(destination / "docs/compat/logic-pro/evidence/P001/source-retrieval.json"),
                     "--output", str(output / "regenerated-lock.json")], "lock-regeneration.log", cwd=destination)
        verify_lock_regeneration(lock_path, output / "regenerated-lock.json", output)
        summary.update(result="PASS", verified_gitlinks=verdict["verified_gitlinks"],
                       verified_repositories=verdict["verified_repositories"],
                       verified_physical_blobs=verdict["verified_physical_blobs"],
                       verification_method=verdict["verification_method"], lock_regeneration="PASS")
    except (CampaignFailure, OSError, ValueError, KeyError, TypeError) as exc:
        summary["failures"].append(str(exc))
    finally:
        summary["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_json(output / "summary.json", summary)
        write_json(output / "commands.json", commands.records)
        checksums(output)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--host-id", choices=("a", "b"), required=True)
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args()
    try:
        result = run_campaign(args.source, args.destination, args.output, args.commit, host_id=args.host_id, jobs=args.jobs)
    except (CampaignFailure, OSError, ValueError) as exc:
        print(f"P002 campaign setup failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
