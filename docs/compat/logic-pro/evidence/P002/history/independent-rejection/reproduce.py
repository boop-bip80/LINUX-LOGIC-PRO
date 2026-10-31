#!/usr/bin/env python3
"""Independent P002 negative reproductions; edits only disposable Git fixtures."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import sys

SOURCE = Path(sys.argv[1]).resolve()
SPEC = importlib.util.spec_from_file_location("p002_author_fixtures", SOURCE / "tests/compat/logic-pro/submodules/test_lock.py")
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


def run_case(name, mutation):
    f = FIXTURE.RealRecursiveClone()
    f.setUp()
    try:
        extra = mutation(f) or {}
        try:
            result = f.check()
            outcome = {"result": result["result"], "dirty_repositories": result.get("dirty_repositories")}
        except Exception as exc:
            outcome = {"result": "REJECTED", "error_type": type(exc).__name__, "error": str(exc)}
        if "_filter_marker" in extra:
            extra["filter_executed_by_verifier"] = Path(extra.pop("_filter_marker")).exists()
        return {"case": name, **outcome, **extra}
    finally:
        f.doCleanups()


def hidden_modules(f, flag):
    FIXTURE.git(f.clone, "update-index", flag, ".gitmodules")
    p = f.clone / ".gitmodules"
    p.write_text(p.read_text().replace(f.lock["submodules"][0]["declared_url"], "https://github.com/wrong/dependency.git"))
    return {"physical_modification": "root .gitmodules URL no longer equals locked URL", "concealment": flag}


def hidden_child(f):
    child = f.clone / "sub/nested"
    FIXTURE.git(child, "update-index", "--assume-unchanged", "data.txt")
    (child / "data.txt").write_text("tampered nested source\n")
    return {"physical_modification": "nested tracked source bytes changed", "concealment": "--assume-unchanged"}


def hidden_mode(f):
    child = f.clone / "sub"
    FIXTURE.git(child, "config", "core.filemode", "false")
    p = child / "data.txt"
    p.chmod(p.stat().st_mode | 0o111)
    return {"physical_modification": "child tracked source executable mode changed", "concealment": "core.filemode=false"}


def untracked_root(f):
    (f.clone / "unexpected-runtime-input.dylib").write_text("unexpected\n")
    return {"physical_modification": "untracked file added to root"}


def clean_filter(f):
    marker = Path(f.temp.name) / "filter-was-executed"
    raw_git = FIXTURE.git(f.clone, "rev-parse", "--absolute-git-dir")
    (Path(raw_git) / "info" / "attributes").write_text("data.txt filter=review\n")
    code = "import pathlib,sys;pathlib.Path(" + repr(str(marker)) + ").write_text('executed');sys.stdout.write('root\\n')"
    FIXTURE.git(f.clone, "config", "filter.review.clean", shlex.quote(sys.executable) + " -c " + shlex.quote(code))
    (f.clone / "data.txt").write_text("evil\n")
    return {"physical_modification": "root tracked source bytes changed", "concealment": "configured clean filter", "_filter_marker": str(marker)}


def rewritten_origin(f):
    child = f.clone / "sub"
    wrong = "file:///definitely-not-the-provenance-source.git"
    right = f.lock["submodules"][0]["resolved_url"]
    FIXTURE.git(child, "remote", "set-url", "origin", wrong)
    FIXTURE.git(child, "config", "url." + right + ".insteadOf", wrong)
    return {"physical_modification": "raw child remote.origin.url differs from recorded source", "raw_origin": wrong, "effective_origin": FIXTURE.git(child, "remote", "get-url", "origin")}


out = {"reviewer": "/root/p002_adversarial", "reviewed_commit": FIXTURE.git(SOURCE, "rev-parse", "HEAD"), "cases": [
    run_case("dirty_gitmodules_assume_unchanged", lambda f: hidden_modules(f, "--assume-unchanged")),
    run_case("dirty_gitmodules_skip_worktree", lambda f: hidden_modules(f, "--skip-worktree")),
    run_case("dirty_nested_source_assume_unchanged", hidden_child),
    run_case("dirty_child_executable_mode", hidden_mode),
    run_case("untracked_root_runtime_input", untracked_root),
    run_case("clean_filter_hides_source_and_executes", clean_filter),
    run_case("raw_origin_hidden_by_local_rewrite", rewritten_origin),
]}
print(json.dumps(out, indent=2, sort_keys=True))
