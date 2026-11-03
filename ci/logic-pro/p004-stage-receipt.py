#!/usr/bin/env python3
"""Create a P004 job receipt only after checking real P003/fixture outputs.

This is *not* phase acceptance. It binds each CI job's observed results to its
exact source SHA, so the P004 gate collector can reject missing or forged jobs.
A failed job leaves no passing receipt. Source compatibility with Logic Pro is
not claimed; these are synthetic Darling runtime tests only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


class ReceiptFailure(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptFailure(message)


def load(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), f"Missing regular report: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"Non-object report: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assertion(name: str, actual: object, expected: object) -> dict:
    require(actual == expected, f"{name}: {actual!r} != {expected!r}")
    return {"id": name, "kind": "equals", "expected": expected, "actual": actual}




# Production P003 tests have ten *named*, observable cases per replay.
# Case counts alone are never evidence that XPC/GUI/Mach-O probes ran.
BUILD_CASES = frozenset((
    "macho-known-vector", "macho-nonce", "macho-boundary-64", "macho-reject-65",
    "macho-invalid-arguments", "foundation-invalid-arguments", "gui-invalid-arguments",
    "foundation-objects", "gui-event-roundtrip", "runtime-shutdown",
))
RUNTIME_CASES = frozenset((
    "macho-known-vector", "macho-fresh-nonce", "macho-boundary-64", "macho-reject-65",
    "macho-invalid-arguments", "foundation-invalid-arguments", "gui-invalid-arguments",
    "foundation-fresh-nonce", "gui-event-roundtrip", "runtime-shutdown",
))
FRAMEWORK_VERSIONS = {
    "AppKit": "C", "Foundation": "C", "CoreGraphics": "A", "CoreText": "A",
    "ImageIO": "A", "QuartzCore": "A", "AudioToolbox": "A",
}


def verify_cases(cases: object, expected: frozenset[str], status: str, label: str) -> None:
    require(isinstance(cases, list) and len(cases) == len(expected),
            f"{label}: must execute exactly {len(expected)} real named cases")
    require(all(isinstance(item, dict) and isinstance(item.get("name"), str)
                and item.get("status") == status for item in cases),
            f"{label}: case identity/status is missing or not {status}")
    names = [item["name"] for item in cases]
    require(len(names) == len(set(names)) and set(names) == expected,
            f"{label}: duplicate, missing or unknown cases: {names!r}")


def verified_log(directory: Path, filename: str, marker: str, expected: str) -> None:
    path = directory / filename
    require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
            f"Original probe log missing: {path}")
    require(path.stat().st_size <= 4 * 1024 * 1024, f"Probe log unexpectedly large: {path}")
    records = [line for line in path.read_text(encoding="utf-8").splitlines()
               if line.startswith(marker)]
    require(records == [expected],
            f"Original {filename} did not prove exact, unique {marker!r} marker")


def real_xwd_samples(path: Path) -> dict:
    """Sample original XWD pixels independently of the P003 producer's JSON."""
    import struct

    data = path.read_bytes()
    require(len(data) >= 100, f"XWD screenshot truncated: {path}")
    fields = struct.unpack_from("!25I", data)
    size, version, layout, depth, width, height, xoffset, order = fields[:8]
    bits, stride, visual = fields[11:14]
    masks = fields[14:17]
    colors = fields[19]
    require(version == 7 and layout == 2 and visual == 4
            and depth in (24, 32) and bits in (24, 32) and bits >= depth
            and order in (0, 1) and xoffset == 0
            and 200 <= width <= 1024 and 120 <= height <= 768
            and 100 < size <= len(data) and colors <= 4096
            and width * (bits // 8) <= stride <= width * 8,
            f"Invalid original XWD geometry: {path}")
    offset = size + colors * 12
    require(offset + stride * height == len(data),
            f"Truncated/trailing original XWD pixels: {path}")
    require(all(masks) and not (masks[0] & masks[1] or masks[0] & masks[2]
                               or masks[1] & masks[2]), "Invalid original XWD RGB masks")
    specs = []
    for mask in masks:
        require(mask < (1 << bits), "XWD mask exceeds source pixel")
        shift = (mask & -mask).bit_length() - 1
        maximum = mask >> shift
        require(maximum & (maximum + 1) == 0, "Discontinuous XWD RGB mask")
        specs.append((mask, shift, maximum))

    def rgb_at(x: int, y: int) -> list[int]:
        position = offset + y * stride + x * (bits // 8)
        pixel = int.from_bytes(data[position:position + bits // 8],
                               "little" if order == 0 else "big")
        return [((pixel & mask) >> shift) * 255 // maximum
                for mask, shift, maximum in specs]

    left, right = rgb_at(width // 4, height // 2), rgb_at(3 * width // 4, height // 2)
    samples = {"width": width, "height": height, "depth": depth,
               "left_rgb": left, "right_rgb": right}
    return samples


def verify_screenshots(directory: Path, report: dict, independent: bool) -> None:
    shots = report.get("screenshots")
    require(isinstance(shots, dict) and set(shots) == {"before", "after"},
            "Visible GUI must have raw before and after captures")
    xwd_hashes = []
    for state, targets in (("before", ((255, 0, 0), (0, 0, 255))),
                           ("after", ((0, 255, 0), (255, 255, 0)))):
        shot = shots[state]
        require(isinstance(shot, dict), f"GUI {state} screenshot metadata absent")
        screenshot_filename = shot.get("file")
        require(isinstance(screenshot_filename, str)
                and re.fullmatch(r"[A-Za-z0-9._-]+\.xwd", screenshot_filename) is not None,
                "Unsafe/non-XWD screenshot filename")
        screenshot = directory / screenshot_filename
        require(screenshot.is_file() and not screenshot.is_symlink()
                and screenshot.stat().st_size >= 100,
                f"Original GUI {state} screenshot bytes absent")
        require(shot.get("sha256") == sha256(screenshot),
                f"GUI {state} original screenshot digest mismatch")
        if independent:
            require(shot.get("bytes") == screenshot.stat().st_size
                    and type(shot.get("capture_attempts")) is int
                    and shot["capture_attempts"] > 0,
                    "Independent screenshot byte count/capture attempts missing")
        xwd_hashes.append(shot["sha256"])
        # Decode the *real* XWD, not just the claim about its rendered colors.
        samples = real_xwd_samples(screenshot)
        require(shot.get("pixels") == samples,
                f"GUI {state} recorded pixels disagree with original capture")
        if independent:
            require(samples["width"] >= 320 and samples["height"] >= 200,
                    "Independent GUI screenshot smaller than source-free pixel oracle")
        left, right = samples["left_rgb"], samples["right_rgb"]
        for actual, expected in ((left, targets[0]), (right, targets[1])):
            require(max(abs(actual[channel] - expected[channel]) for channel in range(3)) <= 40,
                    f"GUI {state} does not show required visible {expected} state")
        if independent:
            patches = shot.get("patches")
            require(isinstance(patches, dict)
                    and patches.get("expected_rgb") == [list(color) for color in targets]
                    and patches.get("pixels_per_half") == 25
                    and patches.get("maximum_allowed_error") == 40,
                    f"Independent GUI {state} 50-pixel patch oracle missing")
            actual_patches = []
            # Re-evaluate 25 *real* pixels per half, rather than trusting JSON.
            # The decoder is repeated here for the limited 50 points by
            # reconstructing their original source pixels.
            import struct
            data = screenshot.read_bytes()
            fields = struct.unpack_from("!25I", data)
            size, colors, stride, bits, order = fields[0], fields[19], fields[12], fields[11], fields[7]
            masks = fields[14:17]
            specs = [(mask, (mask & -mask).bit_length() - 1) for mask in masks]
            offset = size + colors * 12
            width, height = samples["width"], samples["height"]
            for center, color in ((width // 4, targets[0]), (3 * width // 4, targets[1])):
                maximum_error = 0
                for y in range(height // 2 - 2, height // 2 + 3):
                    for x in range(center - 2, center + 3):
                        position = offset + y * stride + x * (bits // 8)
                        pixel = int.from_bytes(data[position:position + bits // 8],
                                               "little" if order == 0 else "big")
                        for channel, (mask, shift) in enumerate(specs):
                            maximum = mask >> shift
                            observed = ((pixel & mask) >> shift) * 255 // maximum
                            maximum_error = max(maximum_error, abs(observed - color[channel]))
                actual_patches.append(maximum_error)
            require(actual_patches == patches.get("maximum_channel_error")
                    and max(actual_patches) <= 40,
                    f"Independent GUI {state} raw 50-pixel oracle does not match")
        else:
            require(shot.get("asserted_state") ==
                    ("red/blue before input" if state == "before" else "green/yellow after input"),
                    f"Build GUI {state} expected screenshot state absent")
        png = shot.get("png")
        require(isinstance(png, dict), "Lossless GUI preview missing")
        png_name = png.get("file")
        require(isinstance(png_name, str)
                and re.fullmatch(r"[A-Za-z0-9._-]+\.png", png_name) is not None,
                "Invalid GUI PNG preview filename")
        png_path = directory / png_name
        require(png_path.is_file() and not png_path.is_symlink()
                and png_path.stat().st_size > 40
                and png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"),
                "Original GUI PNG preview absent")
        require(png.get("sha256") == sha256(png_path), "GUI PNG digest mismatch")
        if independent:
            require(png.get("bytes") == png_path.stat().st_size,
                    "GUI PNG byte count mismatch")
    require(len(set(xwd_hashes)) == 2, "GUI before/after pixels did not change")


def verify_observables(directory: Path, report: dict, independent: bool) -> None:
    nonce = report.get("nonce")
    require(isinstance(nonce, str) and re.fullmatch(r"[0-9a-f]{16}", nonce) is not None,
            "Real replay must contain its own unpredictable 64-bit nonce")
    foundation = directory / "foundation.stdout.log"
    verified_log(directory, foundation.name, "P003_FOUNDATION ",
                 f"P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 answer=42 bytes=007fff missing=nil")
    verified_log(directory, foundation.name, "P003_TRANSACTION ",
                 f"P003_TRANSACTION nonce={nonce} deltas=1|2|1|0")
    verified_log(directory, "gui.stdout.log", "P003_GUI ",
                 f"P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1")
    gui_log = directory / "gui.stdout.log"
    image_lines = [line for line in gui_log.read_text(encoding="utf-8").splitlines()
                   if line.startswith("P003_IMAGE ")]
    owners = [f"/System/Library/Frameworks/{name}.framework/Versions/{version}/{name}"
              for name, version in FRAMEWORK_VERSIONS.items()]
    require(sorted(image_lines) == sorted("P003_IMAGE " + owner for owner in owners),
            "Exact seven genuine GUI framework owners missing/duplicated")
    if independent:
        require(sorted(report.get("loaded_framework_paths") or []) == sorted(owners),
                "Independent reviewer missing loaded framework paths")
        require(type(report.get("window_id")) is int and report["window_id"] > 0,
                "No independently observed stable GUI window ID")
    verify_screenshots(directory, report, independent)
    lifecycle = report.get("lifecycle")
    require(isinstance(lifecycle, dict) and isinstance(lifecycle.get("server_before"), dict)
            and type(lifecycle["server_before"].get("pid")) is int
            and lifecycle["server_before"]["pid"] > 1
            and isinstance(lifecycle["server_before"].get("mount_namespace"), str)
            and lifecycle.get("server_exited") is True
            and lifecycle.get("namespace_holders_after") == []
            and lifecycle.get("mount_namespace_released") is True,
            "Real Darling server shutdown and private mount cleanup not proven")
    stubs = report.get("stub_diagnostics")
    require(isinstance(stubs, dict) and stubs.get("enabled") is True
            and stubs.get("hits") == []
            and (stubs.get("environment") or {}).get("STUB_VERBOSE") == "1",
            "Cannot certify a runtime with absent/disabled stub diagnostics")
    require(report.get("errors") == [], "Runtime reported errors or malformed errors field")

def source_receipt(directory: Path, commit: str) -> tuple[int, list[dict]]:
    summary = load(directory / "source-summary.json")
    assertions = [assertion("source-sha", summary.get("source_commit"), commit),
                  assertion("source-status", summary.get("status"), "PASS")]
    suites = summary.get("suites")
    floors = {"baseline": 143, "submodules": 97, "build": 151, "harness": 86, "evidence": 28}
    require(isinstance(suites, list) and len(suites) == len(floors),
            "Missing or additional required source fixture suites")
    by_suite = {row.get("suite"): row for row in suites if isinstance(row, dict)}
    require(len(by_suite) == len(floors) and set(by_suite) == set(floors),
            "Missing/duplicated source fixture suites")
    total = 0
    for suite, floor in floors.items():
        row = by_suite[suite]
        count = row.get("count")
        require(type(count) is int and count >= floor, f"{suite} fixture floor not satisfied")
        assertions.append(assertion(f"{suite}-exit", row.get("exit_code"), 0))
        assertions.append(assertion(f"{suite}-discovered-executed",
                                    row.get("discovered"), count))
        assertions.append(assertion(f"{suite}-passed", row.get("passed"), count))
        assertions.append(assertion(f"{suite}-skipped", row.get("skipped"), 0))
        total += count
        log = directory / f"{suite}.log"
        require(log.is_file() and not log.is_symlink() and log.stat().st_size > 0,
                f"Missing {suite} original test output")
        assertions.append(assertion(f"{suite}-log-sha", row.get("sha256"), sha256(log)))
        if suite == "harness":
            observed = log.read_text(encoding="utf-8").splitlines()
            stage_receipt_tests = [line for line in observed
                                   if line.startswith("test_")
                                   and "(test_stage_receipt." in line
                                   and line.endswith(" ... ok")]
            require(len(stage_receipt_tests) >= 39,
                    "Independent stage receipt adversarial coverage shrank below 39")
            assertions.append(assertion("receipt-adversarial-minimum-39",
                                        len(stage_receipt_tests) >= 39, True))
            for name in (
                "test_build_wrong_case_names_cannot_fake_ten_passing_probes",
                "test_build_original_xpc_transaction_marker_mutation_rejected",
                "test_build_fake_gui_color_even_when_sha_and_pixels_agree_rejected",
                "test_runtime_source_isolation_absent_rejected",
            ):
                matches = [line for line in observed
                           if line.startswith(name + " (") and line.endswith(" ... ok")]
                require(len(matches) == 1,
                        f"Receipt adversarial unittest not executed exactly once: {name}")
                assertions.append(assertion(f"receipt-mutation-{name}", len(matches), 1))
    faults = load(directory / "fault-matrix.json")
    require(bool(faults), "Fault matrix cannot be empty")
    assertions.append(assertion("fault-matrix-present", (directory / "fault-matrix.json").is_file(), True))
    assertions.append(assertion("all-three-regressions", all(by_suite[k]["count"] >= floors[k] for k in ("baseline", "submodules", "build")), True))
    return total, assertions


def toolchain_receipt(directory: Path) -> tuple[int, list[dict]]:
    lock = load(directory / "toolchain.lock.json")
    archive = directory / "toolchain-image.tar.gz"
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size > 0,
            "Actual frozen toolchain archive is missing")
    meta = lock.get("image_archive")
    require(isinstance(meta, dict), "Frozen toolchain lock missing image identity")
    digest = meta.get("sha256")
    require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
            "Frozen image digest invalid")
    return 1, [assertion("frozen-lock-verified", sha256(archive) == digest, True),
               assertion("frozen-image-sha", sha256(archive), digest),
               assertion("toolchain-lock-present", (directory / "toolchain.lock.json").is_file(), True)]


def build_receipt(directory: Path, commit: str, role: str) -> tuple[int, list[dict]]:
    summary = load(directory / "build-summary.json")
    assertions = [assertion("build-sha", summary.get("source_commit"), commit),
                  assertion("build-status", summary.get("status"), "PASS"),
                  assertion("build-exit", summary.get("exit_code"), 0),
                  assertion("build-stage", summary.get("last_stage"), "complete"),
                  assertion("build-identity", summary.get("build_id"), role[-1])]
    total = 0
    for cycle in ("first", "second"):
        report = load(directory / f"probes-{cycle}" / "report.json")
        cases = report.get("cases")
        require(isinstance(cases, list), f"No real P003 {cycle} runtime cases")
        assertions.append(assertion(f"{cycle}-runtime-status", report.get("status"), "PASSED"))
        assertions.append(assertion(f"{cycle}-runtime-source", report.get("source_revision"), commit))
        assertions.append(assertion(f"{cycle}-runtime-passed", report.get("passed"), True))
        assertions.append(assertion(f"{cycle}-stub-count", len((report.get("stub_diagnostics") or {}).get("hits") or []), 0))
        assertions.append(assertion(f"{cycle}-lifecycle-present", isinstance(report.get("lifecycle"), dict), True))
        assertions.append(assertion(f"{cycle}-runtime-error-count", len(report.get("errors") or []), 0))
        assertions.append(assertion(f"{cycle}-runtime-case-count", len(cases), 10))
        verify_cases(cases, BUILD_CASES, "PASSED", f"build-{cycle}")
        verify_observables(directory / f"probes-{cycle}", report, independent=False)
        assertions.append(assertion(f"{cycle}-real-native-xpc-and-gui", True, True))
        total += len(cases)
    archive = directory / "runtime-prefix.tar.gz"
    digest_file = directory / "runtime-prefix.sha256"
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size > 0,
            "Installed runtime archive missing")
    require(digest_file.is_file() and not digest_file.is_symlink(), "Archive hash record missing")
    recorded = digest_file.read_text().split()[0]
    assertions.append(assertion("installed-package-sha", sha256(archive), recorded))
    assertions.append(assertion("installed-runtime-probes", total, 20))
    for filename in ("install-first.json", "install-second.json", "uninstall.json"):
        assertions.append(assertion(filename + "-present", (directory / filename).is_file(), True))
    return total, assertions


def runtime_receipt(directory: Path, commit: str) -> tuple[int, list[dict]]:
    package = load(directory / "package-review.json")
    report = load(directory / "runtime" / "report.json")
    assertions = [assertion("package-sha", package.get("source_commit"), commit),
                  assertion("package-status", package.get("status"), "PASS"),
                  assertion("installed-readback", package.get("installed_readback"), "PASS"),
                  assertion("runtime-sha", report.get("source_commit"), commit),
                  assertion("runtime-status", report.get("status"), "PASS"),
                  assertion("runtime-passed", report.get("passed"), True)]
    cases = report.get("cases")
    require(isinstance(cases, list), "Independent runtime case list missing")
    assertions.append(assertion("runtime-case-count", len(cases), 10))
    assertions.append(assertion("runtime-errors", len(report.get("errors") or []), 0))
    assertions.append(assertion("runtime-source-isolation", (report.get("isolation") or {}).get("source_and_build_absent"), True))
    assertions.append(assertion("runtime-stub-hits", len((report.get("stub_diagnostics") or {}).get("hits") or []), 0))
    assertions.append(assertion("runtime-lifecycle", (report.get("lifecycle") or {}).get("mount_namespace_released"), True))
    verify_cases(cases, RUNTIME_CASES, "PASS", "independent-runtime")
    verify_observables(directory / "runtime", report, independent=True)
    assertions.append(assertion("runtime-real-native-xpc-and-gui", True, True))
    (directory / "runtime-summary.json").write_text(json.dumps({
        "schema": "darling.p004.independent-runtime-summary.v1",
        "phase": "P004", "source_commit": commit, "status": "PASS",
        "package_review": "PASS", "runtime_cases": len(cases),
        "source_free_replay": True, "errors": [],
    }, indent=2, sort_keys=True) + "\n")
    assertions.append(assertion("source-free-probes", len(cases), 10))
    return len(cases), assertions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("source", "toolchain", "build-a", "build-b", "independent-runtime"),
                        required=True)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--runner", required=True, choices=("ubuntu-22.04",))
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--publication", required=True)
    args = parser.parse_args()
    try:
        require(re.fullmatch(r"[0-9a-f]{40}", args.commit) is not None, "Source SHA must be exact")
        require(args.run_id > 0 and args.run_attempt > 0, "GitHub run and attempt must be positive")
        require(re.fullmatch(r"[0-9a-f]{40}", args.publication) is not None,
                "Publication SHA must be exact")
        actual_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()
        require(actual_commit == args.commit and re.fullmatch(r"[0-9a-f]{40}", tree) is not None,
                "Job did not checkout exact source commit and tree")
        source_lock = Path("docs/compat/logic-pro/submodules.lock.json")
        require(source_lock.is_file(), "Current source dependency lock missing")
        submodule_count = None
        if args.role in ("source", "build-a", "build-b"):
            result = subprocess.run(["git", "submodule", "status", "--recursive"],
                                    check=True, capture_output=True, text=True)
            lines = result.stdout.splitlines()
            require(len(lines) == 160 and all(row.startswith(" ") for row in lines),
                    "Current recursively checked out dependency pins are missing/mismatched")
            submodule_count = len(lines)
        require(args.directory.is_dir() and not args.directory.is_symlink(), "Output directory missing")
        receipt = args.directory / "p004-job.json"
        require(not receipt.exists() and not receipt.is_symlink(),
                "Never overwrite an existing phase job receipt")
        if args.role == "source":
            count, assertions = source_receipt(args.directory, args.commit)
        elif args.role == "toolchain":
            count, assertions = toolchain_receipt(args.directory)
        elif args.role in ("build-a", "build-b"):
            count, assertions = build_receipt(args.directory, args.commit, args.role)
        else:
            count, assertions = runtime_receipt(args.directory, args.commit)
        require(count > 0 and assertions, "Job cannot qualify with no executed assertions")
        result = {
            "schema": "darling.p004.job.v1", "phase": "P004",
            "name": args.role, "role": args.role, "source_commit": args.commit,
            "runner": args.runner, "status": "PASS",
            "github_run_id": args.run_id, "github_run_attempt": args.run_attempt,
            "source_tree": tree, "publication_commit": args.publication,
            "source_lock_sha256": sha256(source_lock),
            "submodule_pin_count": submodule_count,
            "submodule_verification": ("recursive-160-pins" if submodule_count == 160
                                       else "bound-to-source-sha-and-tree"),
            "discovered": count, "executed": count, "passed": count,
            "failed": 0, "skipped": 0, "timed_out": False, "exit_code": 0,
            "assertions": assertions,
        }
        receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"role": args.role, "source_commit": args.commit,
                          "discovered": count, "executed": count, "status": "PASS"}))
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        print(f"P004 {args.role} receipt BLOCKED/FAIL: {error}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
