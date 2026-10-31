#!/usr/bin/env python3
"""Inventory, hydrate and verify the exact P002 Git LFS payloads.

Pointer discovery and verification use committed Git objects and direct file
reads, never user-supplied clean/smudge filters. Hydration is a separate, explicit
operation using the installed Git LFS client and only the HTTPS endpoint in the
owner's pinned .lfsconfig. No credentials or fallback endpoints are permitted.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from urllib.parse import urlsplit

import inventory


POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
POINTER_LIMIT = 1024
POINTER = re.compile(
    rb"version https://git-lfs.github.com/spec/v1\n"
    rb"oid sha256:([0-9a-f]{64})\nsize (0|[1-9][0-9]*)\n"
)
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
OBJECT_FIELDS = {"path", "repository", "repository_path", "repository_commit",
                 "pointer_blob_sha1", "mode", "oid_sha256", "size"}
REPOSITORY_FIELDS = {"repository", "repository_commit", "origin", "endpoint",
                     "lfsconfig_blob_sha1", "lfsconfig_sha256"}


class LFSError(inventory.InventoryError):
    """Missing, unsafe, changed, or unverified LFS source/payload evidence."""


def safe_path(value: str, *, root: bool = False) -> str:
    if root and value == ".":
        return value
    if (not isinstance(value, str) or not value or value == "." or value.startswith("/")
            or "\\" in value or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or str(PurePosixPath(value)) != value
            or any(part in (".", "..", ".git") for part in PurePosixPath(value).parts)):
        raise LFSError("unsafe LFS path")
    return value


def safe_https(value: str) -> str:
    """Require a public, credential-free HTTPS URL, without rewriting it."""
    if not isinstance(value, str) or any(ord(char) <= 32 or ord(char) == 127 for char in value):
        raise LFSError("LFS URL must be credential-free public HTTPS")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        invalid = (parsed.scheme != "https" or parsed.username is not None
                   or parsed.password is not None or parsed.query or parsed.fragment
                   or not host or parsed.port not in (None, 443)
                   or not re.fullmatch(r"[A-Za-z0-9.-]+", host)
                   or "." not in host or not re.search(r"[A-Za-z]", host.rsplit(".", 1)[-1])
                   or host.lower() == "localhost" or host.lower().endswith(".localhost")
                   or "\\" in parsed.path or any(part == ".." for part in parsed.path.split("/")))
        try:
            invalid = invalid or not ipaddress.ip_address(host).is_global
        except ValueError:
            pass
        if invalid:
            raise LFSError("LFS URL must be credential-free public HTTPS")
    except ValueError as error:
        raise LFSError("invalid LFS HTTPS URL") from error
    return value


def parse_pointer(content: bytes) -> dict | None:
    """Return exact canonical v1 metadata; reject malformed pointer-like blobs."""
    match = POINTER.fullmatch(content)
    if match and len(content) <= POINTER_LIMIT:
        size = int(match[2])
        if size > (1 << 63) - 1:
            raise LFSError("LFS pointer size exceeds the signed 64-bit specification")
        return {"oid_sha256": match[1].decode("ascii"), "size": size}
    if (content.startswith(POINTER_PREFIX)
            or content.startswith(b"version https://git-lfs.github.com/spec/")):
        raise LFSError("malformed or unsupported LFS pointer")
    return None


def _head(repo: Path) -> str:
    commit = inventory.decode(inventory.git(repo, "rev-parse", "HEAD^{commit}")).strip()
    if not SHA1.fullmatch(commit):
        raise LFSError("P002 requires an immutable SHA-1 Git commit")
    top = inventory.decode(inventory.git(repo, "rev-parse", "--show-toplevel")).strip()
    if os.path.abspath(top) != os.path.abspath(repo):
        raise LFSError("LFS owner is not an initialized repository root")
    return commit


def scan_repository(repo: Path, repository: str, origin: str) -> list[dict]:
    """Discover pointers in ALL small committed blobs, not attribute patterns.

    Canonical Git LFS pointers are at most 1024 bytes. ls-tree supplies blob
    sizes without loading large runtime objects. Reading these small blobs via
    cat-file does not run filters, examine the index, or trust working bytes.
    """
    safe_path(repository, root=True)
    commit = _head(repo)
    candidates = []
    raw = inventory.git(repo, "ls-tree", "-rlz", "--full-tree", commit)
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        header, path = entry.split(b"\t", 1)
        mode, kind, oid, size = header.split()
        if kind == b"blob" and int(size) <= POINTER_LIMIT:
            candidates.append({"mode": mode.decode("ascii"), "object": oid.decode("ascii"),
                               "path": inventory.decode(path)})
    blobs = inventory.read_blobs(repo, [entry["object"] for entry in candidates])
    records = []
    for entry in candidates:
        pointer = parse_pointer(blobs[entry["object"]])
        if pointer is None:
            continue
        if entry["mode"] not in ("100644", "100755"):
            raise LFSError("LFS pointer must be a regular Git blob")
        path = safe_path(entry["path"])
        records.append({"path": path if repository == "." else repository + "/" + path,
                        "repository": repository, "repository_path": path,
                        "repository_commit": commit, "pointer_blob_sha1": entry["object"],
                        "mode": entry["mode"], **pointer})
    if records:
        safe_https(origin)
    return sorted(records, key=lambda item: item["path"])


def repository_metadata(repo: Path, repository: str, origin: str) -> dict:
    """Read and validate endpoint provenance from the committed owner .lfsconfig.

    Requiring one explicit lfs.url is deliberate: new implicit endpoints or
    transfer settings require a separately reviewed provenance update.
    """
    safe_path(repository, root=True)
    safe_https(origin)
    commit = _head(repo)
    entries = [entry for entry in inventory.tree_entries(repo, commit) if entry["path"] == ".lfsconfig"]
    if len(entries) != 1 or entries[0]["type"] != "blob" or entries[0]["mode"] not in ("100644", "100755"):
        raise LFSError("LFS owner must have a committed regular .lfsconfig")
    entry = entries[0]
    content = inventory.read_blobs(repo, [entry["object"]])[entry["object"]]
    raw = inventory.git(repo, "config", "--no-includes", "--file", "-", "--null", "--list",
                        input_bytes=content)
    settings = [record.split(b"\n", 1) for record in raw.split(b"\0") if record]
    if len(settings) != 1 or len(settings[0]) != 2 or settings[0][0] != b"lfs.url":
        raise LFSError("committed .lfsconfig must contain exactly one lfs.url and no other settings")
    endpoint = safe_https(inventory.decode(settings[0][1]))
    return {"repository": repository, "repository_commit": commit, "origin": origin,
            "endpoint": endpoint, "lfsconfig_blob_sha1": entry["object"],
            "lfsconfig_sha256": hashlib.sha256(content).hexdigest()}


def _hash_field(record: dict, name: str, pattern: re.Pattern) -> None:
    if not isinstance(record.get(name), str) or not pattern.fullmatch(record[name]):
        raise LFSError("invalid LFS metadata hash: " + name)


def validate_manifest(document: dict, submodules: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    """Validate exact schema, counts, owner coverage, order, and optional pin binding."""
    if not isinstance(document, dict):
        raise LFSError("LFS manifest must be an object")
    repositories, objects = document.get("lfs_repositories"), document.get("lfs_objects")
    count = document.get("expected_lfs_objects")
    if (not isinstance(repositories, list) or not isinstance(objects, list)
            or type(count) is not int or count != len(objects)):
        raise LFSError("LFS inventory/count is missing or inconsistent")
    owners = {}
    for record in repositories:
        if not isinstance(record, dict) or set(record) != REPOSITORY_FIELDS:
            raise LFSError("invalid LFS repository metadata fields")
        owner = safe_path(record["repository"], root=True)
        if owner in owners:
            raise LFSError("duplicate LFS repository owner")
        for name in ("repository_commit", "lfsconfig_blob_sha1"):
            _hash_field(record, name, SHA1)
        _hash_field(record, "lfsconfig_sha256", SHA256)
        safe_https(record["origin"])
        safe_https(record["endpoint"])
        owners[owner] = record
    paths, used_owners = set(), set()
    for record in objects:
        if not isinstance(record, dict) or set(record) != OBJECT_FIELDS:
            raise LFSError("invalid LFS object metadata fields")
        path, owner = safe_path(record["path"]), safe_path(record["repository"], root=True)
        local_path = safe_path(record["repository_path"])
        if path != (local_path if owner == "." else owner + "/" + local_path):
            raise LFSError("LFS object path is not within its exact owner")
        if path in paths or owner not in owners:
            raise LFSError("duplicate LFS object or missing owner metadata")
        paths.add(path)
        used_owners.add(owner)
        for name in ("repository_commit", "pointer_blob_sha1"):
            _hash_field(record, name, SHA1)
        _hash_field(record, "oid_sha256", SHA256)
        if record["repository_commit"] != owners[owner]["repository_commit"]:
            raise LFSError("LFS object/owner commit mismatch")
        if (record["mode"] not in ("100644", "100755") or type(record["size"]) is not int
                or not 0 <= record["size"] <= (1 << 63) - 1):
            raise LFSError("invalid LFS object mode or size")
        pointer = (POINTER_PREFIX + b"\noid sha256:" + record["oid_sha256"].encode("ascii")
                   + b"\nsize " + str(record["size"]).encode("ascii") + b"\n")
        pointer_blob = hashlib.sha1(b"blob " + str(len(pointer)).encode("ascii") + b"\0" + pointer).hexdigest()
        if pointer_blob != record["pointer_blob_sha1"]:
            raise LFSError("LFS pointer blob does not encode its locked payload OID/size")
    if used_owners != set(owners):
        raise LFSError("unused or missing LFS repository owner")
    if repositories != sorted(repositories, key=lambda item: item["repository"]):
        raise LFSError("LFS repository metadata must be sorted")
    if objects != sorted(objects, key=lambda item: item["path"]):
        raise LFSError("LFS object metadata must be sorted")
    if submodules is not None:
        pins = {}
        for pin in submodules:
            if not isinstance(pin, dict) or pin.get("path") in pins:
                raise LFSError("invalid or duplicate pinned submodule")
            pins[pin.get("path")] = pin
        for owner, record in owners.items():
            pin = pins.get(owner)
            if (not pin or pin.get("commit") != record["repository_commit"]
                    or pin.get("resolved_url") != record["origin"]):
                raise LFSError("LFS owner is not bound to the exact locked submodule origin/commit")
    return repositories, objects


def _root_fd(root: Path) -> int:
    """Open even the caller's root ancestors without following symlinks."""
    if ".." in root.parts:
        raise LFSError("unsafe LFS root path")
    absolute = Path(os.path.abspath(root))
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in absolute.parts[1:]:
            next_descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _parent_fd(root: Path, path: str) -> tuple[int, str]:
    parts = PurePosixPath(safe_path(path)).parts
    descriptor = _root_fd(root)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor, parts[-1]
    except BaseException:
        os.close(descriptor)
        raise


def _stamp(info: os.stat_result) -> tuple:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_file(root: Path, path: str, *, mode: str | None = None,
               size: int | None = None, capture: bool = False) -> tuple[str, bytes, int]:
    parent = None
    try:
        parent, name = _parent_fd(root, path)
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise LFSError("LFS input is not a regular physical file: " + path)
            if mode and ("100755" if before.st_mode & stat.S_IXUSR else "100644") != mode:
                raise LFSError("LFS payload executable mode differs: " + path)
            if size is not None and before.st_size != size:
                raise LFSError("LFS payload size differs (possibly an unhydrated pointer): " + path)
            digest, chunks = hashlib.sha256(), []
            total, prefix = 0, b""
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
                if len(prefix) < POINTER_LIMIT:
                    prefix = (prefix + chunk)[:POINTER_LIMIT]
                if capture:
                    chunks.append(chunk)
            after = os.fstat(stream.fileno())
            if _stamp(before) != _stamp(after) or total != before.st_size:
                raise LFSError("LFS input changed during verification: " + path)
            # Reopen every directory from the caller's root as well: a renamed
            # parent must not let an old open descriptor validate a replacement.
            current_parent, current_name = _parent_fd(root, path)
            try:
                if _stamp(os.stat(current_name, dir_fd=current_parent, follow_symlinks=False)) != _stamp(after):
                    raise LFSError("LFS input was replaced during verification: " + path)
            finally:
                os.close(current_parent)
            if size is not None and prefix.startswith(POINTER_PREFIX):
                raise LFSError("unhydrated LFS pointer remains: " + path)
            return digest.hexdigest(), b"".join(chunks), total
    except OSError as error:
        raise LFSError("missing, unreadable, or symlinked LFS input: " + path) from error
    finally:
        if parent is not None:
            os.close(parent)


def verify_payload(root: Path, record: dict) -> dict:
    """Read-only, streaming SHA-256/size/mode verification with O_NOFOLLOW."""
    path = safe_path(record["path"])
    _hash_field(record, "oid_sha256", SHA256)
    if (record.get("mode") not in ("100644", "100755")
            or type(record.get("size")) is not int or record["size"] < 0):
        raise LFSError("invalid LFS payload metadata")
    observed, _, size = _read_file(root, path, mode=record["mode"], size=record["size"])
    if observed != record["oid_sha256"]:
        raise LFSError("LFS payload SHA-256 differs: " + path)
    return {"path": path, "oid_sha256": observed, "size": size, "mode": record["mode"], "status": "PASS"}


def hydration_environment() -> dict[str, str]:
    """Preserve required proxies/CA trust, never ambient Git or user credentials."""
    excluded = {"GH_TOKEN", "GITHUB_TOKEN", "GITHUB_PAT", "SSH_AUTH_SOCK", "SSH_AGENT_PID",
                "SSH_ASKPASS", "SSH_ASKPASS_REQUIRE", "NETRC", "CURL_HOME"}
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_") and key not in excluded
                   and not key.endswith(("_TOKEN", "_PASSWORD", "_SECRET"))}
    # Git LFS reads ~/.netrc independently of credential.helper. Refuse rather
    # than read it, mutate HOME, or claim a credentialed fetch is anonymous.
    home = environment.get("HOME")
    if home and any(os.path.lexists(Path(home) / name) for name in (".netrc", "_netrc")):
        raise LFSError("anonymous hydration requires an environment without a netrc credential file")
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
                        "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false",
                        "SSH_ASKPASS": "/bin/false", "GIT_ALLOW_PROTOCOL": "https",
                        "GIT_OPTIONAL_LOCKS": "0", "GIT_LFS_SKIP_SMUDGE": "1",
                        "GIT_ATTR_NOSYSTEM": "1"})
    return environment


def _check_local_config(repo: Path, origin: str) -> None:
    """Fresh acquisitions need no executable helpers, rewrites, or custom LFS config."""
    raw = inventory.git(repo, "config", "--no-includes", "--local", "--null", "--list")
    allowed = {"core.repositoryformatversion", "core.filemode", "core.bare", "core.logallrefupdates",
               "core.worktree", "core.ignorecase", "core.precomposeunicode", "core.symlinks",
               "core.autocrlf", "core.eol", "remote.origin.url", "remote.origin.fetch",
               "lfs.repositoryformatversion"}
    origins = []
    for setting in raw.split(b"\0"):
        if not setting:
            continue
        key, _, value = setting.partition(b"\n")
        name = inventory.decode(key)
        if name not in allowed and not re.fullmatch(r"branch\.[^.]+\.(remote|merge)", name):
            raise LFSError("anonymous LFS hydration refuses nonstandard local Git configuration")
        if name == "remote.origin.url":
            origins.append(inventory.decode(value))
    if origins != [origin]:
        raise LFSError("raw LFS owner origin differs from the pinned origin")


def _check_index(repo: Path) -> None:
    """Git LFS checkout uses the index; it must exactly equal the audited tree."""
    committed = [(entry["path"], entry["mode"], entry["object"], 0)
                 for entry in inventory.tree_entries(repo, "HEAD")]
    indexed = [(entry["path"], entry["mode"], entry["object"], entry["stage"])
               for entry in inventory.index_entries(repo)]
    if sorted(committed) != sorted(indexed):
        raise LFSError("LFS hydration requires the complete index to equal the pinned HEAD tree")


def _check_no_overrides(repo: Path) -> None:
    """Refuse private attributes/object stores before Git LFS can write files."""
    for name in ("info/attributes", "objects/info/alternates", "objects/info/http-alternates", "info/grafts"):
        path = Path(inventory.decode(inventory.git(repo, "rev-parse", "--git-path", name)).strip())
        if not path.is_absolute():
            path = repo / path
        descriptor = None
        try:
            descriptor = _root_fd(path.parent)
            metadata = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size:
                raise LFSError("anonymous LFS hydration refuses private attributes or object-store overrides")
        except FileNotFoundError:
            pass
        except OSError as error:
            raise LFSError("unsafe LFS repository administration path") from error
        finally:
            if descriptor is not None:
                os.close(descriptor)


def _check_attribute_inputs(repo: Path, objects: list[dict]) -> None:
    """Only pinned attributes may affect the explicit trusted index refresh."""
    entries = {entry["path"]: entry for entry in inventory.tree_entries(repo, "HEAD")
               if PurePosixPath(entry["path"]).name == ".gitattributes"}
    blobs = inventory.read_blobs(repo, [entry["object"] for entry in entries.values() if entry["type"] == "blob"])
    paths = set(entries)
    for record in objects:
        paths.add(".gitattributes")
        for parent in PurePosixPath(record["repository_path"]).parents:
            if str(parent) != ".":
                paths.add(str(parent / ".gitattributes"))
    for path in sorted(paths):
        entry = entries.get(path)
        if entry is not None:
            if entry["type"] != "blob" or entry["mode"] not in ("100644", "100755"):
                raise LFSError("LFS attributes must be regular committed files")
            digest, _, _ = _read_file(repo, path, mode=entry["mode"])
            if digest != hashlib.sha256(blobs[entry["object"]]).hexdigest():
                raise LFSError("physical LFS attributes differ from the pinned tree")
        elif os.path.lexists(repo / path):
            raise LFSError("untracked attributes may not affect LFS hydration")


def _lfs_command(repo: Path, endpoint: str, *arguments: str) -> list[str]:
    settings = ["credential.helper=", "http.extraHeader=", "core.hooksPath=/dev/null",
                "core.fsmonitor=false", "core.attributesFile=/dev/null",
                "lfs.url=" + endpoint, "lfs.basictransfersonly=true",
                "lfs.standalonetransferagent=", "lfs.fetchrecentalways=false",
                "lfs.fetchrecentrefsdays=0", "lfs.fetchrecentcommitsdays=0",
                "lfs.skipdownloaderrors=false", "lfs.cachecredentials=false",
                "lfs.concurrenttransfers=4"]
    if arguments and arguments[0] == "checkout":
        # Git LFS 3.x otherwise silently skips checkout when global installation
        # config is disabled. Its index refresh may invoke this exact trusted
        # client, never a repository-supplied filter. Nothing is installed or
        # persisted, and read-only verification never receives this setting.
        settings.append("filter.lfs.clean=git-lfs clean -- %f")
    command = ["git", "--no-optional-locks", "--literal-pathspecs", "-C", str(repo)]
    for setting in settings:
        command.extend(["-c", setting])
    return command + ["lfs", *arguments]


def _run(command: list[str], environment: dict[str, str], report: dict, *, timeout: int = 900) -> str:
    print("+ " + " ".join(command), flush=True)
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             env=environment, timeout=timeout, check=False)
    output = process.stdout.decode("utf-8", "replace")
    print(output, end="" if output.endswith("\n") else "\n", flush=True)
    report["commands"].append({"argv": command, "exit_code": process.returncode,
                               "output_sha256": hashlib.sha256(process.stdout).hexdigest()})
    if process.returncode:
        raise LFSError("trusted Git LFS command failed (exit " + str(process.returncode) + ")")
    return output.strip()


def hydrate(root: Path, document: dict, report: dict) -> None:
    """Fetch exact pinned objects anonymously; only Git LFS writes payloads."""
    repositories, objects = validate_manifest(document, document.get("submodules"))
    report["expected_lfs_objects"] = len(objects)
    environment = hydration_environment()
    report["git_lfs_version"] = _run(["git", "lfs", "version"], environment, report, timeout=30)
    for metadata in repositories:
        owner = metadata["repository"]
        repo = root if owner == "." else root / owner
        descriptor = _root_fd(repo)
        os.close(descriptor)
        _check_local_config(repo, metadata["origin"])
        _check_no_overrides(repo)
        if repository_metadata(repo, owner, metadata["origin"]) != metadata:
            raise LFSError("committed LFS endpoint/owner provenance differs: " + owner)
        expected = [item for item in objects if item["repository"] == owner]
        if scan_repository(repo, owner, metadata["origin"]) != expected:
            raise LFSError("committed LFS pointer inventory differs: " + owner)
        _check_index(repo)
        _check_attribute_inputs(repo, expected)
        config_hash, _, _ = _read_file(repo, ".lfsconfig")
        if config_hash != metadata["lfsconfig_sha256"]:
            raise LFSError("physical .lfsconfig differs from the pinned endpoint configuration")
        # Git LFS does not overwrite locally modified files. Preflight every
        # target's parents and current bytes before allowing the write operation.
        for item in expected:
            if any(character in item["repository_path"] for character in "*?[]"):
                raise LFSError("LFS hydration refuses ambiguous checkout glob paths")
            _, content, _ = _read_file(root, item["path"], mode=item["mode"], capture=True)
            pointer = parse_pointer(content)
            if pointer is not None:
                if pointer != {"oid_sha256": item["oid_sha256"], "size": item["size"]}:
                    raise LFSError("working pointer differs from locked object")
            else:
                verify_payload(root, item)
        endpoint = metadata["endpoint"]
        _run(_lfs_command(repo, endpoint, "fetch", "--include=", "--exclude=", "origin",
                          metadata["repository_commit"]), environment, report)
        _check_index(repo)
        _check_local_config(repo, metadata["origin"])
        _check_no_overrides(repo)
        _check_attribute_inputs(repo, expected)
        _run(_lfs_command(repo, endpoint, "checkout", "--",
                          *[item["repository_path"] for item in expected]), environment, report)
        report["repositories"].append(dict(metadata, status="PASS"))
        for item in expected:
            verified = verify_payload(root, item)
            report["objects"].append(verified)
            report["verified_lfs_objects"] += 1
            report["verified_payload_bytes"] += item["size"]
    report["result"] = "PASS"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("hydrate", help="explicit anonymous hydration followed by byte verification")
    command.add_argument("--repo", type=Path, required=True)
    command.add_argument("--lock", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"schema_version": 1, "phase": "P002", "result": "FAIL", "expected_lfs_objects": 0,
              "verified_lfs_objects": 0, "verified_payload_bytes": 0, "git_lfs_version": None,
              "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "repositories": [], "objects": [], "commands": [], "errors": []}
    try:
        document = json.loads(args.lock.read_text())
        hydrate(args.repo.absolute(), document, report)
    except (inventory.InventoryError, OSError, ValueError, subprocess.SubprocessError) as error:
        report["errors"].append({"message": str(error)})
        print("LFS hydration FAIL: " + str(error), file=sys.stderr)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"LFS hydration {report['result']}: {report['verified_lfs_objects']}/{report['expected_lfs_objects']} payloads")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
