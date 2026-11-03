#!/usr/bin/env python3
"""P004 live fault-injection runner.

A successful Python process is not proof that a computation or callback worked.
This runner executes an actual subprocess for each fault, validates independently
observable results, and retains original stdout/stderr/exit/deadline evidence.
It never treats the expected failure of a fault fixture as compatibility PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

EXPECTED_VALUE = 42
EXPECTED_CALLBACKS = ["initialized", "rendered", "completed"]
EXPECTED_EFFECT = b"p004-rendered-value=42\n"
FAULT_EXPECTATIONS = {
    "wrong-result": "wrong-result",
    "crash": "process-crash",
    "hang": "deadline-exceeded",
    "missing-callback": "missing-callback",
    "missing-executable": "missing-executable",
    "fake-success": "no-observable-side-effect",
}

# Each probe runs in a fresh subprocess and private temporary directory.
# The crash fixture disables core dumps in its child before aborting.
PROBE_SOURCE = r"""
import json
import os
import resource
import time

fault = os.environ["P004_FAULT"]
if fault == "crash":
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.abort()
if fault == "hang":
    time.sleep(30)

value = 41 if fault == "wrong-result" else 42
callbacks = [] if fault == "missing-callback" else ["initialized", "rendered", "completed"]
if fault != "fake-success":
    with open(os.environ["P004_EFFECT"], "wb") as stream:
        stream.write(b"p004-rendered-value=42\n")
print(json.dumps({
    "nonce": os.environ["P004_NONCE"],
    "value": value,
    "callbacks": callbacks,
}, sort_keys=True), flush=True)
"""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run_case(case: str, *, timeout_seconds: float = 1.5) -> dict:
    """Run an independently checked positive control or one of six faults.

    Return the observed failure reason, not a guessed label.  A fault fixture
    counts as detected only if the reason matches the declared fault contract.
    """
    if case != "control" and case not in FAULT_EXPECTATIONS:
        raise ValueError("unknown fault case: " + case)
    if not 0.1 <= timeout_seconds <= 10:
        raise ValueError("test deadline must be bounded between 0.1 and 10 seconds")

    nonce = secrets.token_hex(16)
    with tempfile.TemporaryDirectory(prefix="p004-fault-") as directory:
        effect = Path(directory) / "observable-result.bin"
        command = (
            [str(Path(directory) / "executable-that-must-not-exist")]
            if case == "missing-executable"
            else [sys.executable, "-B", "-c", PROBE_SOURCE]
        )
        env = os.environ.copy()
        env.update({
            "P004_FAULT": case,
            "P004_EFFECT": str(effect),
            "P004_NONCE": nonce,
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        started = time.monotonic()
        error = None
        timed_out = False
        return_code = None
        stdout = ""
        stderr = ""
        try:
            process = subprocess.run(
                command,
                cwd=directory,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            error = "missing-executable"
            stderr = str(exc)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            error = "deadline-exceeded"
            stdout = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = (exc.stderr or b"").decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        else:
            stdout, stderr, return_code = process.stdout, process.stderr, process.returncode
            if return_code < 0:
                error = "process-crash"
            elif return_code != 0:
                error = "nonzero-exit"
            else:
                lines = stdout.splitlines()
                if len(lines) != 1:
                    error = "missing-or-extra-result"
                else:
                    try:
                        payload = json.loads(lines[0])
                    except (json.JSONDecodeError, TypeError):
                        error = "malformed-result"
                    else:
                        if not isinstance(payload, dict) or payload.get("nonce") != nonce:
                            error = "nonce-mismatch"
                        elif type(payload.get("value")) is not int or payload["value"] != EXPECTED_VALUE:
                            error = "wrong-result"
                        elif payload.get("callbacks") != EXPECTED_CALLBACKS:
                            error = "missing-callback"
                        elif not effect.is_file() or effect.read_bytes() != EXPECTED_EFFECT:
                            error = "no-observable-side-effect"

        elapsed_ms = round((time.monotonic() - started) * 1000, 3)
        expected = FAULT_EXPECTATIONS.get(case)
        detected = error == expected if expected is not None else error is None
        observed_effect = effect.read_bytes() if effect.is_file() else b""
        return {
            "case": case,
            "expected_detection": expected,
            "observed_detection": error,
            "detected": detected,
            "detector_exit_code": 0 if error is None else 1,
            "observed_process_exit_code": return_code,
            "timed_out": timed_out,
            "timeout_seconds": timeout_seconds,
            "elapsed_ms": elapsed_ms,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_sha256": digest(stdout.encode("utf-8", "replace")),
            "stderr_sha256": digest(stderr.encode("utf-8", "replace")),
            "effect_size_bytes": len(observed_effect),
            "effect_sha256": digest(observed_effect),
            "nonce_sha256": digest(nonce.encode()),
        }


def save_json(path: Path, record: dict) -> tuple[int, str]:
    raw = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return len(raw), digest(raw)


def run_matrix(output: Path, *, timeout_seconds: float = 1.5) -> dict:
    """Write complete independent process observations and immutable hashes.

    On any unexpected result the summary is still preserved, and the CLI
    exits nonzero. Do not silently generate a DETECTED record from a label.
    """
    output.mkdir(parents=True, exist_ok=True)
    control = run_case("control", timeout_seconds=timeout_seconds)
    control_size, control_hash = save_json(output / "faults/control.json", control)
    faults = []
    for case, expected in FAULT_EXPECTATIONS.items():
        result = run_case(case, timeout_seconds=timeout_seconds)
        path = "faults/" + case + ".json"
        size, sha = save_json(output / path, result)
        faults.append({
            "id": case,
            "status": "DETECTED" if result["detected"] and result["detector_exit_code"] != 0 else "UNDETECTED",
            "expected_reason": expected,
            "observed_reason": result["observed_detection"],
            "detector_exit_code": result["detector_exit_code"],
            "artifact": {"path": path, "sha256": sha, "size_bytes": size},
        })
    success = control["detected"] and control["detector_exit_code"] == 0 and all(
        item["status"] == "DETECTED" for item in faults
    )
    summary = {
        "schema_version": 1,
        "status": "PASS" if success else "FAIL",
        "control": {
            "status": "PASS" if control["detected"] else "FAIL",
            "artifact": {
                "path": "faults/control.json",
                "sha256": control_hash,
                "size_bytes": control_size,
            },
        },
        "fault_matrix": faults,
    }
    save_json(output / "fault-matrix.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P004 fault-injection compatibility probes")
    parser.add_argument("--output", type=Path, required=True, help="Evidence directory")
    parser.add_argument("--timeout-seconds", type=float, default=1.5)
    args = parser.parse_args()
    summary = run_matrix(args.output, timeout_seconds=args.timeout_seconds)
    print(json.dumps({
        "status": summary["status"],
        "detected": sum(x["status"] == "DETECTED" for x in summary["fault_matrix"]),
        "required": len(FAULT_EXPECTATIONS),
        "control": summary["control"]["status"],
    }, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
