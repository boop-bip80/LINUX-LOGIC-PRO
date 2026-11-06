#!/usr/bin/env python3
"""Independent readback of ORIGINAL GitHub Actions ZIPs for P001-P004.

This is review-only code, intentionally not importing the project's producer,
inventory, comparison or gate modules. It never grants phase acceptance.
Run it only against immutable canonical-branch push run IDs with a read-only token.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import urllib.error
import urllib.request
import urllib.parse
import zipfile
import zlib

SOURCE_SHA = re.compile(r"[0-9a-f]{40}\Z")
FILE_SHA = re.compile(r"[0-9a-f]{64}\Z")
REPO = "boop-bip80/LINUX-LOGIC-PRO"
BRANCH = "main"
HISTORICAL_REPO = "boop-bip80/MAC-OS-EMULATION"
CANONICAL_SCOPES = frozenset({(REPO, BRANCH), (HISTORICAL_REPO, "master")})
WORKFLOWS = {
    "P001": ".github/workflows/phase1-baseline.yml",
    "P002": ".github/workflows/phase2-submodules.yml",
    "P003": ".github/workflows/phase3-build.yml",
    "P004": ".github/workflows/compat.yml",
}
JOBS = {
    "P001": ("Source recovery (ubuntu-22.04)", "Source recovery (ubuntu-24.04)"),
    "P002": ("Independent clone a (ubuntu-22.04)", "Independent clone b (ubuntu-24.04)"),
    "P003": (
        "Prior-phase regression and P003 verifier adversarial tests",
        "Freeze Ubuntu 22.04 and Clang 14 toolchain",
        "Clean build, install and runtime probes a",
        "Clean build, install and runtime probes b",
        "Independent runtime reproduction from the installed archive",
        "Compare independent builds and all required evidence",
    ),
    "P004": ("resolve", "source", "toolchain", "build-a", "build-b",
             "independent-runtime", "gate-validation"),
}
CAPTURE = frozenset({
    "summary.json", "commands.json", "checksums.json", "checksums.sha256",
    "build-summary.json", "toolchain.lock.json", "runtime-prefix.sha256",
    "package-review.json", "runtime/report.json", "p003-comparison.json",
    "p004-job.json", "source-equivalence.json", "inventory.json",
    "manifest.json", "p004-validation.json", "verification-a.json",
    "verification-b.json", "source-retrieval.json",
})
MAX_JSON_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_ARCHIVE = 12 * 1024**3
DEFAULT_MAX_UNPACKED = 60 * 1024**3


class AuditError(Exception):
    """A contradiction in purported original evidence."""


class EvidenceUnavailable(Exception):
    """Evidence is missing, expired or not ready to read."""


class SafeArtifactRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward GitHub bearer tokens to signed third-party ZIP hosts."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        destination = urllib.parse.urlsplit(newurl)
        if (destination.scheme != "https" or not destination.netloc
                or destination.username is not None
                or destination.password is not None):
            raise AuditError("GitHub artifact attempted an unsafe non-HTTPS redirect")
        target = super().redirect_request(req, fp, code, msg, headers, newurl)
        if target is None:
            return None
        source = urllib.parse.urlsplit(req.full_url)
        if (source.scheme, source.netloc.lower()) != (
                destination.scheme, destination.netloc.lower()):
            sensitive = {"authorization", "cookie", "proxy-authorization"}
            for header in set(target.headers) | set(target.unredirected_hdrs):
                if header.lower() in sensitive:
                    target.remove_header(header)
        return target


def safe_open(request, timeout: int):
    return urllib.request.build_opener(SafeArtifactRedirect()).open(
        request, timeout=timeout)


def unique_json_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise AuditError(f"Duplicate key in original evidence JSON: {key}")
        result[key] = value
    return result


def reject_json_constant(value):
    raise AuditError(f"Nonfinite value in original evidence JSON: {value}")


def strict_json_bytes(data: bytes, label: str, expected_type= dict):
    try:
        value = json.loads(data.decode("utf-8"),
                           object_pairs_hook=unique_json_pairs,
                           parse_constant=reject_json_constant)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise AuditError(f"Malformed original evidence JSON: {label}") from exc
    require(type(value) is expected_type,
            f"Original evidence JSON had incorrect top-level type: {label}")
    return value


def require(condition, message):
    if not condition:
        raise AuditError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iso_time(value: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"),
            "GitHub artifact timestamp missing UTC timezone")
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuditError("Malformed GitHub artifact timestamp") from exc


def get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "independent-original-zip-review",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
    })
    try:
        with safe_open(req, timeout=45) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404, 410, 429):
            raise EvidenceUnavailable(f"GitHub API unavailable ({exc.code}): {url}") from exc
        raise
    if len(raw) > 16 * 1024 * 1024:
        raise AuditError("GitHub metadata response exceeds review limit")
    value = json.loads(raw)
    require(isinstance(value, dict), "GitHub metadata was not an object")
    return value


def pages(url: str, key: str, token: str) -> list[dict]:
    records = []
    for number in range(1, 21):
        result = get_json(f"{url}{'&' if '?' in url else '?'}per_page=100&page={number}", token)
        data = result.get(key)
        require(isinstance(data, list), f"GitHub {key} response malformed")
        records.extend(data)
        if len(data) < 100:
            return records
    raise AuditError(f"GitHub {key} result exceeded 2,000-item cap")


def validate_scope(repo: str, branch: str) -> None:
    require((repo, branch) in CANONICAL_SCOPES,
            "Unexpected repository/branch pair; use LINUX-LOGIC-PRO/main or "
            "explicit historical MAC-OS-EMULATION/master")


def validate_run(repo: str, phase: str, run_id: int, commit: str, token: str,
                 *, branch: str = BRANCH) -> dict:
    validate_scope(repo, branch)
    require(isinstance(commit, str) and SOURCE_SHA.fullmatch(commit) is not None,
            "Full tested-source SHA is required")
    run = get_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}", token)
    require((run.get("repository") or {}).get("full_name") == repo
            and run.get("path") == WORKFLOWS[phase]
            and run.get("head_sha") == commit,
            f"{phase} run repository/workflow/source SHA mismatch")
    require(run.get("event") == "push" and run.get("head_branch") == branch,
            f"{phase} is not an original {branch}-push run")
    if run.get("status") != "completed":
        raise EvidenceUnavailable(f"{phase} original run is {run.get('status')}, not completed")
    require(run.get("conclusion") == "success",
            f"{phase} original run did not conclude success")
    attempt = run.get("run_attempt")
    require(type(attempt) is int and attempt > 0, f"{phase} run attempt unavailable")
    created_at = run.get("created_at")
    iso_time(created_at)  # GitHub anchors artifact retention to this run timestamp.
    jobs = pages(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs",
                 "jobs", token)
    for required in JOBS[phase]:
        hits = [j for j in jobs if isinstance(j, dict) and j.get("name") == required]
        require(len(hits) == 1 and hits[0].get("status") == "completed"
                and hits[0].get("conclusion") == "success",
                f"{phase} mandatory job missing, ambiguous or unsuccessful: {required}")
    return {
        "phase": phase, "run_id": run_id, "attempt": attempt, "event": "push",
        "repository": repo, "branch": branch,
        "source_sha": commit, "workflow": WORKFLOWS[phase],
        "conclusion": "success", "created_at": created_at,
        "jobs": [{"name": name, "id": next(j["id"] for j in jobs if j.get("name") == name)}
                 for name in JOBS[phase]],
    }


def artifact_names(phase: str, source: str, publication: str) -> tuple[str, ...]:
    if phase == "P001":
        return tuple(f"p001-{os_name}-{source}" for os_name in ("ubuntu-22.04", "ubuntu-24.04"))
    if phase == "P002":
        return tuple(f"p002-clone-{host}-{source}" for host in ("a", "b"))
    if phase == "P003":
        return tuple(f"p003-{role}-{source}" for role in
                     ("fixtures", "toolchain", "build-a", "build-b",
                      "independent-runtime", "comparison"))
    return tuple(f"p004-{role}-{source}" for role in
                 ("source", "toolchain", "build-a", "build-b", "runtime", "gate")) + (
                     f"p004-resolver-{publication}",)


def get_artifact_metadata(repo: str, run_id: int, wanted: tuple[str, ...],
                          token: str, *, run_created_at: str) -> dict[str, dict]:
    run_created = iso_time(run_created_at)
    listed = pages(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts",
                   "artifacts", token)
    result = {}
    for name in wanted:
        matches = [item for item in listed if isinstance(item, dict)
                   and item.get("name") == name]
        if not matches:
            raise EvidenceUnavailable(f"Original uploaded ZIP absent: {name}")
        require(len(matches) == 1, f"Ambiguous duplicate original artifact: {name}")
        item = matches[0]
        digest = item.get("digest")
        require(item.get("expired") is False
                and type(item.get("id")) is int and item["id"] > 0
                and type(item.get("size_in_bytes")) is int and item["size_in_bytes"] > 0
                and isinstance(digest, str) and digest.startswith("sha256:")
                and FILE_SHA.fullmatch(digest[7:]) is not None,
                f"Original uploaded archive metadata invalid: {name}")
        # GitHub calculates Actions artifact expiry from the workflow RUN
        # creation time, not the later per-artifact upload/creation timestamp.
        # Real 90-day artifacts therefore have expires-created < 90 days.
        artifact_created = iso_time(item["created_at"])
        expires = iso_time(item["expires_at"])
        require(artifact_created >= run_created and expires > artifact_created,
                f"Original artifact timestamps contradict workflow run: {name}")
        require(expires - run_created >= dt.timedelta(days=90),
                f"Original artifact retention below 90-day run policy: {name}")
        identity = item.get("workflow_run") or {}
        require(identity.get("id") == run_id,
                f"Artifact {name} does not belong to requested GitHub run")
        result[name] = item
    return result


def canonical_name(filename: str, is_dir: bool, prefix: str) -> str:
    require(isinstance(filename, str) and bool(filename),
            "Original ZIP has a blank member name")
    if filename.startswith(prefix + "/"):
        filename = filename[len(prefix) + 1:]
    if is_dir:
        require(filename.endswith("/"), "Directory ZIP member lacks trailing slash")
        filename = filename[:-1]
    require(filename and "\x00" not in filename and "\\" not in filename
            and not filename.startswith("/") and "//" not in filename,
            f"Unsafe ZIP member path: {filename!r}")
    normalized = PurePosixPath(filename)
    require(normalized.as_posix() == filename
            and all(part not in (".", "..", "") for part in normalized.parts),
            f"Noncanonical ZIP member path: {filename!r}")
    return filename


def inspect_zip(stream, prefix: str, *, max_unpacked: int = DEFAULT_MAX_UNPACKED):
    """Stream each member without extraction; reject ZipSlip, links, bombs, extra data."""
    entries = {}
    captured = {}
    seen_dirs = set()
    total = 0
    try:
        with zipfile.ZipFile(stream, "r") as archive:
            for member in archive.infolist():
                name = canonical_name(member.filename, member.is_dir(), prefix)
                mode = (member.external_attr >> 16) & 0xFFFF
                kind = stat.S_IFMT(mode)
                require(kind not in (stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK,
                                     stat.S_IFIFO, stat.S_IFSOCK),
                        f"Original ZIP contains link or special device: {name}")
                if member.is_dir():
                    require(kind in (0, stat.S_IFDIR),
                            f"ZIP directory has a regular-file mode: {name}")
                    require(name not in seen_dirs and name not in entries,
                            f"Duplicate ZIP directory: {name}")
                    seen_dirs.add(name)
                    continue
                require(kind in (0, stat.S_IFREG),
                        f"Nonregular original ZIP member: {name}")
                require(name not in entries and name not in seen_dirs,
                        f"Duplicate original ZIP member: {name}")
                require(member.file_size >= 0 and member.file_size <= max_unpacked
                        and total + member.file_size <= max_unpacked,
                        f"ZIP expanded-byte limit exceeded: {name}")
                total += member.file_size
                digest = hashlib.sha256()
                crc = 0
                observed = 0
                chunks = [] if name in CAPTURE and member.file_size <= MAX_JSON_BYTES else None
                with archive.open(member, "r") as reader:
                    while True:
                        block = reader.read(1024 * 1024)
                        if not block:
                            break
                        observed += len(block)
                        require(observed <= member.file_size,
                                f"ZIP member expanded past declared size: {name}")
                        digest.update(block)
                        crc = zlib.crc32(block, crc)
                        if chunks is not None:
                            chunks.append(block)
                require(observed == member.file_size and (crc & 0xFFFFFFFF) == member.CRC,
                        f"Original ZIP member size or CRC mismatch: {name}")
                entries[name] = {
                    "sha256": digest.hexdigest(), "size": observed,
                    "crc32": f"{crc & 0xFFFFFFFF:08x}",
                }
                if chunks is not None:
                    captured[name] = b"".join(chunks)
    except (zipfile.BadZipFile, RuntimeError, EOFError, OSError, NotImplementedError) as exc:
        raise AuditError(f"Cannot fully validate original ZIP members: {type(exc).__name__}") from exc
    require(bool(entries), "Original uploaded ZIP contained no ordinary files")
    for directory in seen_dirs:
        require(any(name.startswith(directory + "/") for name in entries),
                f"Unreferenced or empty original ZIP directory: {directory}")
    return entries, captured, total


def read_archive(repo: str, token: str, item: dict,
                 *, max_archive: int = DEFAULT_MAX_ARCHIVE,
                 max_unpacked: int = DEFAULT_MAX_UNPACKED) -> dict:
    name = item["name"]
    url = f"https://api.github.com/repos/{repo}/actions/artifacts/{item['id']}/zip"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "independent-original-zip-review",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with tempfile.TemporaryFile(mode="w+b") as temporary:
            digest = hashlib.sha256()
            size = 0
            with safe_open(request, timeout=120) as response:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    size += len(block)
                    require(size <= max_archive, f"Original ZIP exceeds byte budget: {name}")
                    digest.update(block)
                    temporary.write(block)
            require(size == item["size_in_bytes"],
                    f"Original ZIP compressed bytes differ from API metadata: {name}")
            require(digest.hexdigest() == item["digest"][7:],
                    f"Original ZIP SHA-256 differs from GitHub API digest: {name}")
            temporary.seek(0)
            members, captured, expanded = inspect_zip(
                temporary, name, max_unpacked=max_unpacked)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404, 410, 429):
            raise EvidenceUnavailable(f"Original artifact download unavailable: {name} ({exc.code})") from exc
        raise
    return {
        "name": name, "artifact_id": item["id"], "run_id": item["workflow_run"]["id"],
        "original_zip_sha256": digest.hexdigest(), "original_zip_bytes": size,
        "created_at": item["created_at"], "expires_at": item["expires_at"],
        "member_count": len(members), "expanded_bytes": expanded,
        "members": members, "_captured": captured,
    }


def anchor(record: dict, path: str) -> bytes:
    captured = record["_captured"]
    require(path in record["members"], f"{record['name']} missing required {path}")
    require(path in captured, f"{record['name']} oversized/unavailable anchor {path}")
    return captured[path]


def parse_json(record: dict, path: str, expected_type=dict):
    return strict_json_bytes(anchor(record, path),
                             f"{record['name']}/{path}", expected_type)


def verify_hash_list(record: dict, *, p001: bool) -> None:
    checks = parse_json(record, "checksums.json") if p001 else anchor(
        record, "checksums.sha256").decode("utf-8").splitlines()
    if p001:
        require(isinstance(checks, dict) and len(checks) >= 5,
                "P001 did not publish original self-checksums")
        for name, expected in checks.items():
            entry = record["members"].get(name)
            require(entry is not None and expected.get("sha256") == entry["sha256"]
                    and expected.get("bytes") == entry["size"],
                    f"Original P001 report checksum mismatch: {name}")
    else:
        require(len(checks) >= 5, "P002 did not publish original self-checksums")
        seen = set()
        for row in checks:
            match = re.fullmatch(r"([0-9a-f]{64})  ([^/\n]+)", row)
            require(match is not None and match[2] not in seen,
                    "P002 checksums.sha256 was malformed or duplicate")
            seen.add(match[2])
            require(record["members"].get(match[2], {}).get("sha256") == match[1],
                    f"Original P002 report checksum mismatch: {match[2]}")


def review_phase_anchors(phase: str, records: dict[str, dict], source: str) -> None:
    if phase == "P001":
        for record in records.values():
            summary = parse_json(record, "summary.json")
            require(summary.get("result") == "PASS"
                    and summary.get("implementation_commit") == source
                    and summary.get("failures") == []
                    and summary.get("fixture_tests_executed", 0) >= 130,
                    "P001 original source recovery/fixture evidence incomplete")
            verify_hash_list(record, p001=True)
    elif phase == "P002":
        for host, record in zip(("a", "b"), records.values()):
            summary = parse_json(record, "summary.json")
            require(summary.get("result") == "PASS"
                    and summary.get("implementation_commit") == source
                    and summary.get("host_id") == host
                    and summary.get("failures") == []
                    and summary.get("native_gitlinks_verified", 0) >= 160,
                    "P002 original recursive clone/pin evidence incomplete")
            verify_hash_list(record, p001=False)
    elif phase == "P003":
        by_role = {name.split("-" + source)[0].removeprefix("p003-"): value
                   for name, value in records.items()}
        fixtures = parse_json(by_role["fixtures"], "summary.json", list)
        require(isinstance(fixtures, list)
                and {r.get("suite") for r in fixtures} == {"baseline", "submodules", "build"},
                "P003 original fixture suite list incomplete")
        for suite in fixtures:
            require(suite.get("exit_code") == 0
                    and suite.get("count", 0) >= {"baseline": 130, "submodules": 97, "build": 151}[suite["suite"]],
                    "P003 original fixture minimum not met")
        lock = parse_json(by_role["toolchain"], "toolchain.lock.json")
        image = by_role["toolchain"]["members"].get("toolchain-image.tar.gz")
        require(image is not None and lock.get("image_archive", {}).get("sha256") == image["sha256"],
                "P003 original frozen toolchain bytes mismatch")
        for role in ("build-a", "build-b"):
            record = by_role[role]
            summary = parse_json(record, "build-summary.json")
            require(summary.get("status") == "PASS" and summary.get("source_commit") == source,
                    "P003 original build did not pass at exact source")
            marker = anchor(record, "runtime-prefix.sha256").decode("utf-8").split()[0]
            tar = record["members"].get("runtime-prefix.tar.gz")
            require(tar is not None and marker == tar["sha256"],
                    "P003 original installed tar was not byte-bound")
        runtime = by_role["independent-runtime"]
        package = parse_json(runtime, "package-review.json")
        installed = parse_json(runtime, "runtime/report.json")
        require(package.get("status") == "PASS" and installed.get("status") == "PASS"
                and installed.get("source_commit") == source,
                "P003 original source-free runtime did not pass")
        comparison = parse_json(by_role["comparison"], "p003-comparison.json")
        require(comparison.get("status") == "READY_FOR_INDEPENDENT_REVIEW"
                and comparison.get("automated_checks") == "PASS"
                and comparison.get("implementation_commit") == source,
                "P003 original two-build comparison did not pass automated checks")


def review_p004(records: dict[str, dict], source: str, publication: str,
                run_id: int, attempt: int) -> None:
    require(source != publication, "A==B is an unreviewed candidate, not final P004 publication")
    resolver = records[f"p004-resolver-{publication}"]
    proof = anchor(resolver, "source-equivalence.json")
    source_record = records[f"p004-source-{source}"]
    require(anchor(source_record, "source-equivalence.json") == proof,
            "Original P004 resolver proof differs from its source-stage copy")
    obj = strict_json_bytes(proof, 'original resolver source-equivalence.json')
    require(obj.get("status") == "PASS"
            and obj.get("tested_commit") == source
            and obj.get("publication_commit") == publication,
            "Original independent A-to-B source equivalence did not pass")
    gate = records[f"p004-gate-{source}"]
    inventory = parse_json(gate, "inventory.json")
    require(inventory.get("schema") == "darling.p004.evidence-inventory.v1"
            and inventory.get("source_commit") == source
            and inventory.get("publication_commit") == publication
            and inventory.get("github_run_id") == run_id
            and inventory.get("github_run_attempt") == attempt,
            "Original P004 gate inventory source/run identity differs")
    stages = inventory.get("artifacts")
    require(isinstance(stages, list) and len(stages) == 5,
            "P004 gate inventory omits original producer stages")
    role_names = {"source": "source", "toolchain": "toolchain",
                  "build-a": "build-a", "build-b": "build-b",
                  "independent-runtime": "runtime"}
    require({s.get("role") for s in stages if isinstance(s, dict)} == set(role_names),
            "P004 stage roles incomplete or duplicated")
    trees, locks = set(), set()
    for stage in stages:
        role = stage["role"]
        original = records[f"p004-{role_names[role]}-{source}"]
        files = stage.get("files")
        require(isinstance(files, list) and bool(files),
                f"P004 {role} has no original file inventory")
        expected = {}
        for item in files:
            name = item.get("path")
            require(isinstance(name, str) and name not in expected
                    and FILE_SHA.fullmatch(item.get("sha256", "")) is not None
                    and type(item.get("size")) is int and item["size"] >= 0,
                    f"P004 {role} has malformed/duplicate file inventory")
            expected[name] = {"sha256": item["sha256"], "size": item["size"]}
        observed = {path: {"sha256": value["sha256"], "size": value["size"]}
                    for path, value in original["members"].items()}
        require(observed == expected, f"P004 original {role} ZIP differs from inventoried member set/bytes")
        receipt = parse_json(original, "p004-job.json")
        require(receipt.get("schema") == "darling.p004.job.v1"
                and receipt.get("role") == role and receipt.get("name") == role
                and receipt.get("status") == "PASS"
                and receipt.get("source_commit") == source
                and receipt.get("publication_commit") == publication
                and receipt.get("github_run_id") == run_id
                and receipt.get("github_run_attempt") == attempt,
                f"P004 original {role} producer receipt contradicts source/run")
        trees.add(receipt.get("source_tree"))
        locks.add(receipt.get("source_lock_sha256"))
    require(len(trees) == 1 and len(locks) == 1
            and next(iter(trees)) == inventory.get("source_tree")
            and next(iter(locks)) == inventory.get("source_lock_sha256"),
            "P004 original source tree / recursive dependency lock not identical")
    verdict = parse_json(gate, "p004-validation.json")
    require(verdict.get("status") == "PASS",
            "Original P004 hosted gate did not independently report PASS")
    return


def review_publication_delta(repo: str, source: str, publication: str, token: str) -> None:
    require(source != publication, "Documentation publication must differ from tested source")
    obj = get_json(f"https://api.github.com/repos/{repo}/compare/{source}...{publication}", token)
    require(obj.get("status") == "ahead" and obj.get("behind_by") == 0
            and obj.get("ahead_by", 0) >= 1,
            "Publication B is not a strict descendant of tested source A")
    changed = obj.get("files")
    require(isinstance(changed, list) and bool(changed) and len(changed) < 300,
            "Missing or truncated original GitHub B documentation diff")
    for item in changed:
        name = item.get("filename")
        require(item.get("status") in ("added", "modified")
                and (name == "README.md" or
                     (isinstance(name, str) and re.fullmatch(
                         r"docs/compat/logic-pro/evidence/P004/[^/]+\.json", name) is not None)),
                f"Non-documentation B publication edit: {name}")


def make_report(args, token: str):
    validate_scope(args.repo, args.branch)
    source, publication = args.source_sha, args.publication_sha
    require(SOURCE_SHA.fullmatch(source) is not None,
            "Full tested-source SHA is required")
    if args.predecessors_only:
        require(publication in (None, source),
                "Predecessor-only review cannot pre-accept publication B")
        publication = None
    else:
        require(isinstance(publication, str)
                and SOURCE_SHA.fullmatch(publication) is not None
                and publication != source,
                "Full review requires an actual distinct documentation-only B commit")
    run_specs = [("P001", args.p001_run, source),
                 ("P002", args.p002_run, source),
                 ("P003", args.p003_run, source)]
    if not args.predecessors_only:
        run_specs.append(("P004", args.p004_run, publication))
    runs = {}
    records = {}
    for phase, run_id, sha in run_specs:
        runs[phase] = validate_run(args.repo, phase, run_id, sha, token,
                                   branch=args.branch)
        expected = artifact_names(phase, source, publication or source)
        metadata = get_artifact_metadata(args.repo, run_id, expected, token,
                                         run_created_at=runs[phase]["created_at"])
        phase_records = {}
        for name in expected:
            inspected = read_archive(args.repo, token, metadata[name],
                                     max_archive=args.max_archive_bytes,
                                     max_unpacked=args.max_unpacked_bytes)
            phase_records[name] = inspected
            records[name] = inspected
        if phase in ("P001", "P002", "P003"):
            review_phase_anchors(phase, phase_records, source)
    if args.predecessors_only:
        require(len(records) == 10,
                "Predecessor-only run must authenticate exactly 10 original archives")
    else:
        review_publication_delta(args.repo, source, publication, token)
        review_p004(records, source, publication, args.p004_run,
                    runs["P004"]["attempt"])
        require(len(records) == 17,
                "Full B run must authenticate exactly 17 original archives")
    return {
        "schema": "darling.p004.original-zip-audit.v1",
        "audit_status": ("PREDECESSOR_ORIGINAL_BYTES_VERIFIED" if args.predecessors_only
                         else "ORIGINAL_BYTES_VERIFIED"),
        "phase_verdict": "NOT_EVALUATED",
        "review_mode": ("predecessors-only" if args.predecessors_only else "full-B"),
        "repository": args.repo, "branch": args.branch,
        "source_commit": source, "publication_commit": publication,
        "reviewer_script_commit": os.environ.get("GITHUB_SHA"),
        "review_source_is_independent_of_producers": True,
        "github_runs": list(runs.values()),
        "artifact_count": len(records),
        "artifacts": [{k: v for k, v in rec.items() if k != "_captured"}
                      for rec in records.values()],
        "note": "Archive verification is supporting evidence; no P001-P004 acceptance or Logic Pro execution claim.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--branch", default=BRANCH,
                        help="Canonical push branch: main, or master with the historical repo")
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--publication-sha")
    parser.add_argument("--predecessors-only", action="store_true",
                        help="Authenticate only 10 predecessor ZIPs before B publication")
    for phase in ("p001", "p002", "p003"):
        parser.add_argument(f"--{phase}-run", type=int, required=True)
    parser.add_argument("--p004-run", type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-archive-bytes", type=int, default=DEFAULT_MAX_ARCHIVE)
    parser.add_argument("--max-unpacked-bytes", type=int, default=DEFAULT_MAX_UNPACKED)
    args = parser.parse_args(argv)
    report = {
        "schema": "darling.p004.original-zip-audit.v1",
        "audit_status": "NOT_VERIFIED",
        "phase_verdict": "NOT_EVALUATED",
        "review_mode": "predecessors-only" if args.predecessors_only else "full-B",
        "repository": args.repo, "branch": args.branch,
        "source_commit": args.source_sha,
        "publication_commit": args.publication_sha,
    }
    code = 2
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        require(bool(token), "A read-only GITHUB_TOKEN is required")
        validate_scope(args.repo, args.branch)
        require(all(getattr(args, phase + "_run") is not None
                    and getattr(args, phase + "_run") > 0
                    for phase in ("p001", "p002", "p003")),
                "All three exact-branch predecessor push run IDs are required")
        if not args.predecessors_only:
            require(args.p004_run is not None and args.p004_run > 0,
                    "Full review requires exact final B P004 canonical-branch push run ID")
        else:
            require(args.p004_run is None,
                    "Predecessor-only review must not imply a final P004 run")
        require(args.max_archive_bytes > 0 and args.max_unpacked_bytes > 0,
                "Invalid archive size limits")
        report = make_report(args, token)
        code = 0
    except EvidenceUnavailable as exc:
        report.update(audit_status="BLOCKED", reason=str(exc))
        code = 2
    except (AuditError, urllib.error.URLError, OSError, ValueError, KeyError,
            TypeError, AttributeError, IndexError, zipfile.BadZipFile) as exc:
        report.update(audit_status="FAIL", reason=str(exc))
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "artifacts"},
                     sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
