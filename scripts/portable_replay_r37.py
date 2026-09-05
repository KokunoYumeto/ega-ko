#!/usr/bin/env python3
"""Replay the frozen R37 source archive under its BUILD.ps1 TeX mutex."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import pypdf
from pypdf import PdfReader


VERSION = "2026-09-05-r37"
EXACT_DOI = "10.5281/zenodo.22315714"
CONCEPT_DOI = "10.5281/zenodo.21921513"
STRICT_PDF_BYTES = 1_479_200
STRICT_PDF_SHA = "22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61"
PAGES = 238
BUILD_SCRIPT_BYTES = 20_370
BUILD_SCRIPT_SHA = "330A0F8337C6019010700088E0D8D398EA0B33CA922D06641D607E2F63D51F77"
MANIFEST_BYTES = 16_264
MANIFEST_SHA = "21ED41DDE0E7B850C12E9DF7A7839FB3FFE279B5BC205CC4FBE794A9FED4BAED"
TARGET_BYTES = 75_622
TARGET_SHA = "FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383"
POPPLER_BYTES = 724_814
POPPLER_SHA = "DD155CF9FE4B9F7F865E3858387AF4222DA16B41E935D398612670A82953FFBF"
PYPDF_BYTES = 699_470
PYPDF_SHA = "45A9806C13729B3D8E804897B3515FDEAB64E7719B97ADB3C73ED6C5C6AE4B3B"
EXPECTED_PYPDF_VERSION = "6.12.2"
EXPECTED_PDFTOTEXT_VERSION = "pdftotext version 24.04.0"
REQUIRED_SOURCE_MEMBERS = {
    "build/BUILD.ps1",
    "source/CUMULATIVE_INPUTS.json",
    "source/c2s1.tex",
    "candidates/r37-c2s1-continuation.tex",
    "candidates/validate_r37_candidate.py",
    "scripts/package_r37.py",
    "scripts/portable_replay_r37.py",
    "scripts/prepare_r37_release.py",
    "scripts/qa_r37_pdf.py",
    "scripts/validate_expert_review_log.py",
}
RENDER_IDENTITIES = {
    1: (91_501, "E087A30C56F76DF99A1762B4C9C8313453F266759AE38F560036CA7C3836199B"),
    237: (574_945, "BA2C144EA19A407BDD727A373FED338614EA3EE32997293296DCD0ED647F33E9"),
    238: (134_494, "4AEC28026EB31066E39C74C1BF02804D704A132B987F4969282851C1CA9ED7C3"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def ident_bytes(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha_bytes(data)}


def assert_ident(path: Path, expected_bytes: int, expected_sha: str, label: str) -> None:
    require(path.is_file(), f"missing {label}: {path}")
    require(path.stat().st_size == expected_bytes, f"{label} byte-count drift")
    require(sha_file(path) == expected_sha, f"{label} SHA-256 drift")


def pypdf_extract(path: Path) -> bytes:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n") for page in reader.pages]
    return ("\n\f\n".join(pages) + "\n").encode("utf-8")


def poppler_extract(path: Path) -> bytes:
    result = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-eol", "unix", str(path), "-"],
        capture_output=True,
        timeout=300,
        check=True,
    )
    return result.stdout


def render(path: Path, page: int, output_prefix: Path) -> Path:
    subprocess.run(
        ["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-r", "200", "-png", str(path), str(output_prefix)],
        capture_output=True,
        timeout=180,
        check=True,
    )
    return output_prefix.with_suffix(".png")


def safe_member_name(name: str) -> None:
    path = PurePosixPath(name)
    require(name != "" and "\\" not in name, f"unsafe source ZIP member: {name!r}")
    require(not re.match(r"^[A-Za-z]:", name), f"drive-qualified source ZIP member: {name}")
    require(not path.is_absolute(), f"absolute source ZIP member: {name}")
    require(all(part not in {"", ".", ".."} for part in path.parts), f"traversing source ZIP member: {name}")


def extract_and_verify_source(source_zip: Path, stage: Path) -> dict[str, Any]:
    inventory_rows = ["relative_path\tbytes\tcrc32\tsha256"]
    file_count = 0
    directory_count = 0
    with zipfile.ZipFile(source_zip, "r") as archive:
        require(archive.testzip() is None, "source archive CRC verification failed")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)), "source archive contains duplicate member names")
        for name in names:
            safe_member_name(name)
        normalized = [name.rstrip("/") for name in names]
        require(len(normalized) == len(set(normalized)), "source archive contains file/directory name collisions")
        normalized_set = set(normalized)
        for name in normalized:
            parts = PurePosixPath(name).parts
            for index in range(1, len(parts)):
                require("/".join(parts[:index]) not in normalized_set or "/".join(parts[:index]) + "/" in names, f"source archive file/directory prefix collision: {name}")
        file_names = {info.filename for info in infos if not info.is_dir()}
        require(REQUIRED_SOURCE_MEMBERS.issubset(file_names), f"source archive lacks R37 replay/validation members: {sorted(REQUIRED_SOURCE_MEMBERS - file_names)}")
        for info in infos:
            mode = stat.S_IFMT(info.external_attr >> 16)
            require(mode in {stat.S_IFREG, stat.S_IFDIR}, f"source archive contains non-file/non-directory member: {info.filename}")
            destination = stage.joinpath(*PurePosixPath(info.filename).parts)
            require(destination.resolve().is_relative_to(stage.resolve()), f"source member escapes replay stage: {info.filename}")
            if info.is_dir():
                require(mode == stat.S_IFDIR and info.file_size == 0 and info.CRC == 0, f"invalid source directory member: {info.filename}")
                destination.mkdir(parents=True, exist_ok=True)
                inventory_rows.append(f"{info.filename}\t0\t00000000\t{sha_bytes(b'')}")
                directory_count += 1
                continue
            require(mode == stat.S_IFREG, f"invalid source file mode: {info.filename}")
            data = archive.read(info.filename)
            crc = binascii.crc32(data) & 0xFFFFFFFF
            require(len(data) == info.file_size, f"source member size drift: {info.filename}")
            require(crc == info.CRC, f"source member CRC drift: {info.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            require(destination.read_bytes() == data, f"extracted source member byte drift: {info.filename}")
            inventory_rows.append(f"{info.filename}\t{len(data)}\t{crc:08X}\t{sha_bytes(data)}")
            file_count += 1
    inventory = ("\n".join(inventory_rows) + "\n").encode("utf-8")
    return {
        "entries_verified": len(infos),
        "files_verified": file_count,
        "directories_verified": directory_count,
        "complete_inventory_bytes": len(inventory),
        "complete_inventory_sha256": sha_bytes(inventory),
        "verification": "PASS safe names, no duplicates, member types, CRC, sizes, extracted bytes and per-file SHA-256 inventory",
    }


def safe_remove_stage(stage: Path, expected_parent: Path) -> None:
    require(not stage.is_symlink(), f"portable replay stage is a symlink/reparse path: {stage}")
    require(not expected_parent.is_symlink(), f"portable staging parent is a symlink/reparse path: {expected_parent}")
    resolved_stage = stage.resolve()
    resolved_parent = expected_parent.resolve()
    require(resolved_stage.parent == resolved_parent, f"unsafe portable stage parent: {resolved_stage}")
    require(resolved_stage.name == "r37-portable-replay", f"unsafe portable stage leaf: {resolved_stage}")
    require(resolved_parent.name == "release-staging", f"unexpected portable staging parent: {resolved_parent}")
    if resolved_stage.exists():
        shutil.rmtree(resolved_stage)
    require(not resolved_stage.exists(), f"portable replay stage cleanup failed: {resolved_stage}")


def parse_terminal(terminal: str) -> tuple[int, str, dict[str, str]]:
    match = re.fullmatch(r"PASS (\d+) bytes SHA-256 ([0-9A-F]{64}); (.+)", terminal)
    require(match is not None, f"malformed BUILD.ps1 terminal record: {terminal!r}")
    fields: dict[str, str] = {}
    for item in match.group(3).split("; "):
        require("=" in item, f"malformed terminal field: {item!r}")
        key, value = item.split("=", 1)
        require(key not in fields, f"duplicate terminal field: {key}")
        fields[key] = value
    return int(match.group(1)), match.group(2), fields


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    private_root = args.private_root.resolve()
    release = repo / "release" / VERSION
    source_zip = release / "01_EGA_ko_EDITABLE_SOURCES.zip"
    evidence_zip = release / "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip"
    strict_reader = release / "00_EGA_ko_CUMULATIVE_READER.pdf"
    receipt_path = release / "PORTABLE_BUILD_REPLAY.json"
    package_receipt_path = release / "PACKAGE_RECEIPT.json"
    outer_manifest_path = release / "03_EGA_ko_SHA256_MANIFEST.txt"
    staging_parent = private_root / "release-staging"
    stage = staging_parent / "r37-portable-replay"

    require(release.is_dir(), f"R37 release directory is absent: {release}")
    require(source_zip.is_file(), f"R37 frozen source archive is absent: {source_zip}")
    require(evidence_zip.is_file(), f"R37 frozen evidence archive is absent: {evidence_zip}")
    assert_ident(strict_reader, STRICT_PDF_BYTES, STRICT_PDF_SHA, "strict frozen R37 reader")
    require(package_receipt_path.is_file(), f"R37 package receipt is absent: {package_receipt_path}")
    require(outer_manifest_path.is_file(), f"R37 outer manifest is absent: {outer_manifest_path}")
    require(not receipt_path.exists(), f"refusing to overwrite portable replay receipt: {receipt_path}")
    require(not stage.exists(), f"fresh portable replay stage already exists: {stage}")
    package_receipt = json.loads(package_receipt_path.read_text(encoding="utf-8"))
    require(package_receipt.get("version") == VERSION and package_receipt.get("exact_doi") == EXACT_DOI, "R37 package receipt identity drift")
    require(package_receipt.get("concept_doi") == CONCEPT_DOI, "R37 package receipt concept DOI drift")
    require(package_receipt.get("result") == "PASS_R37_LOCAL_PACKAGE", "R37 package did not pass")
    require(package_receipt.get("public_artifact_count") == 4, "R37 package does not declare four public artifacts")
    rows = {row["name"]: row for row in package_receipt.get("files", [])}
    require(set(rows) == {"00_EGA_ko_CUMULATIVE_READER.pdf", "01_EGA_ko_EDITABLE_SOURCES.zip", "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip", "03_EGA_ko_SHA256_MANIFEST.txt"}, "R37 package public-artifact allowlist drift")
    source_row = rows[source_zip.name]
    evidence_row = rows[evidence_zip.name]
    require((source_zip.stat().st_size, sha_file(source_zip)) == (source_row["bytes"], source_row["sha256"]), "source ZIP/package-receipt identity drift")
    require((evidence_zip.stat().st_size, sha_file(evidence_zip)) == (evidence_row["bytes"], evidence_row["sha256"]), "evidence ZIP/package-receipt identity drift")
    manifest_rows: dict[str, tuple[int, str]] = {}
    manifest_lines = outer_manifest_path.read_text(encoding="utf-8").splitlines()
    require(manifest_lines and manifest_lines[0] == "filename\tbytes\tsha256", "outer manifest header drift")
    for line in manifest_lines[1:]:
        name, byte_text, digest = line.split("\t")
        require(name not in manifest_rows, f"duplicate outer-manifest row: {name}")
        manifest_rows[name] = (int(byte_text), digest)
    require(manifest_rows.get(source_zip.name) == (source_zip.stat().st_size, sha_file(source_zip)), "source ZIP/outer-manifest identity drift")
    require(manifest_rows.get(evidence_zip.name) == (evidence_zip.stat().st_size, sha_file(evidence_zip)), "evidence ZIP/outer-manifest identity drift")
    require(manifest_rows.get(strict_reader.name) == (STRICT_PDF_BYTES, STRICT_PDF_SHA), "reader/outer-manifest identity drift")
    require(set(manifest_rows) == {"00_EGA_ko_CUMULATIVE_READER.pdf", "01_EGA_ko_EDITABLE_SOURCES.zip", "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip"}, "outer manifest must list exactly the three non-self artifacts")
    require(rows[outer_manifest_path.name]["bytes"] == outer_manifest_path.stat().st_size and rows[outer_manifest_path.name]["sha256"] == sha_file(outer_manifest_path), "outer-manifest/package-receipt identity drift")
    require(len(PdfReader(str(strict_reader)).pages) == PAGES, "strict frozen R37 reader page-count drift")
    require(pypdf.__version__ == EXPECTED_PYPDF_VERSION, f"pypdf version drift: {pypdf.__version__}")
    pdftotext_version = subprocess.run(["pdftotext", "-v"], capture_output=True, timeout=30, check=True)
    pdftotext_version_text = (pdftotext_version.stderr or pdftotext_version.stdout).decode("utf-8", errors="replace").splitlines()[0].strip()
    require(pdftotext_version_text == EXPECTED_PDFTOTEXT_VERSION, f"pdftotext version drift: {pdftotext_version_text}")
    require(not staging_parent.is_symlink(), f"portable staging parent is a symlink/reparse path: {staging_parent}")
    staging_parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir()

    archive_verification = extract_and_verify_source(source_zip, stage)
    require(archive_verification["entries_verified"] == source_row["entries"], "source ZIP entry-count/package-receipt drift")
    require(archive_verification["files_verified"] == source_row["files"], "source ZIP file-count/package-receipt drift")
    require(archive_verification["complete_inventory_sha256"] == source_row["complete_inventory_sha256"], "source ZIP inventory/package-receipt drift")
    require(not (stage / "build" / "out").exists(), "frozen source archive contains a pre-existing build/out tree")
    build_script = stage / "build" / "BUILD.ps1"
    manifest_path = stage / "source" / "CUMULATIVE_INPUTS.json"
    target_path = stage / "source" / "c2s1.tex"
    assert_ident(build_script, BUILD_SCRIPT_BYTES, BUILD_SCRIPT_SHA, "frozen R37 build script")
    assert_ident(manifest_path, MANIFEST_BYTES, MANIFEST_SHA, "frozen R37 cumulative manifest")
    assert_ident(target_path, TARGET_BYTES, TARGET_SHA, "frozen R37 target")
    script_text = build_script.read_text(encoding="utf-8")
    require(len(re.findall(r"for \(\$pass = 1; \$pass -le 4; \$pass\+\+\)", script_text)) == 1, "four-pass loop not proved in frozen BUILD.ps1")
    require(script_text.count("Invoke-XeLaTeXCycle -Cycle") == 2, "two-cycle control flow not proved in frozen BUILD.ps1")
    require("did not converge byte-exactly between passes 3 and 4" in script_text, "pass3/pass4 fail-closed gate missing")
    require("Global\\InterlanguageTeXSlotV1" in script_text, "global TeX mutex name missing from frozen BUILD.ps1")
    require("The two independent clean builds are not byte-identical." in script_text, "cycle-final equality fail-closed gate missing")

    env = os.environ.copy()
    for name in ("AGKO_CANONICAL_ROOT", "AGKO_PRIVATE_ROOT"):
        env.pop(name, None)
    env["AGKO_REQUIRE_LIVE_COVERAGE"] = "0"
    invocation = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(build_script)]
    result = subprocess.run(invocation, cwd=stage, env=env, capture_output=True, timeout=1800)
    if result.returncode != 0:
        raise RuntimeError(
            "portable build failed: "
            + result.stderr.decode("utf-8", errors="replace")[-2000:]
            + result.stdout.decode("utf-8", errors="replace")[-2000:]
        )
    stdout = result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    terminal_lines = [line for line in stdout.splitlines() if line.startswith("PASS ")]
    require(len(terminal_lines) == 1, f"unexpected portable terminal output: {stdout!r}")
    terminal = terminal_lines[0]
    terminal_bytes, terminal_sha, terminal_fields = parse_terminal(terminal)

    portable_reader = stage / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    portable_pdf = portable_reader.read_bytes()
    strict_pdf = strict_reader.read_bytes()
    portable_sha = sha_bytes(portable_pdf)
    portable_pages = len(PdfReader(str(portable_reader)).pages)
    require(portable_pages == PAGES, f"portable page count drift: {portable_pages}")
    require(terminal_bytes == len(portable_pdf) and terminal_sha == portable_sha, "terminal PDF identity does not match portable reader")
    require(terminal_fields.get("cycle_a_pass3_final_identical") == "true", "portable cycle A lacks pass3=pass4")
    require(terminal_fields.get("cycle_b_pass3_final_identical") == "true", "portable cycle B lacks pass3=pass4")
    require(terminal_fields.get("cycle_a_sha256") == terminal_fields.get("cycle_b_sha256") == portable_sha, "portable cycle finals are not identical to promoted reader")
    require(terminal_fields.get("cycle_a_pass3_sha256") == terminal_fields.get("cycle_a_sha256"), "portable cycle A pass3/final hash drift")
    require(terminal_fields.get("cycle_b_pass3_sha256") == terminal_fields.get("cycle_b_sha256"), "portable cycle B pass3/final hash drift")
    require(terminal_fields.get("mutex") == r"Global\InterlanguageTeXSlotV1", "portable build terminal mutex identity drift")

    with zipfile.ZipFile(evidence_zip, "r") as frozen_evidence:
        require(frozen_evidence.testzip() is None, "frozen evidence archive CRC verification failed")
        evidence_names = [info.filename for info in frozen_evidence.infolist()]
        require(len(evidence_names) == len(set(evidence_names)), "frozen evidence archive contains duplicate names")
        required_evidence = {
            "extract.txt",
            "extract-pypdf.txt",
            "render/r37-p001.png",
            "render/r37-p237.png",
            "render/r37-p238.png",
        }
        require(required_evidence.issubset(evidence_names), f"frozen evidence archive lacks replay references: {sorted(required_evidence - set(evidence_names))}")
        frozen_poppler = frozen_evidence.read("extract.txt")
        frozen_pypdf = frozen_evidence.read("extract-pypdf.txt")
        frozen_renders = {page: frozen_evidence.read(f"render/r37-p{page:03d}.png") for page in (1, 237, 238)}
    require((len(frozen_poppler), sha_bytes(frozen_poppler)) == (POPPLER_BYTES, POPPLER_SHA), "frozen R37 Poppler extraction identity drift")
    require((len(frozen_pypdf), sha_bytes(frozen_pypdf)) == (PYPDF_BYTES, PYPDF_SHA), "frozen R37 pypdf extraction identity drift")
    strict_poppler = poppler_extract(strict_reader)
    portable_poppler = poppler_extract(portable_reader)
    require(strict_poppler == portable_poppler == frozen_poppler, "portable Poppler extraction drift")
    strict_pypdf = pypdf_extract(strict_reader)
    portable_pypdf = pypdf_extract(portable_reader)
    require(strict_pypdf == portable_pypdf == frozen_pypdf, "portable pypdf extraction drift")

    render_rows = []
    for page in (1, 237, 238):
        generated = render(portable_reader, page, stage / f"portable-render-r37-p{page:03d}")
        expected_bytes, expected_sha = RENDER_IDENTITIES[page]
        reference = frozen_renders[page]
        require((len(reference), sha_bytes(reference)) == (expected_bytes, expected_sha), f"frozen R37 render page {page} identity drift")
        require(generated.read_bytes() == reference, f"portable render drift on page {page}")
        render_rows.append(
            {
                "physical_page": page,
                "bytes": generated.stat().st_size,
                "sha256": sha_file(generated),
                "frozen_evidence_entry": f"render/r37-p{page:03d}.png",
                "byte_identical": True,
            }
        )

    raw_log = stage / "build" / "out" / "main.log"
    require(raw_log.is_file(), "portable build log is absent")
    pdf_equal = strict_pdf == portable_pdf
    receipt = {
        "schema": "ag-ko-portable-replay-v3",
        "version": VERSION,
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "source_archive": {
            "name": source_zip.name,
            "bytes": source_zip.stat().st_size,
            "sha256": sha_file(source_zip),
            **archive_verification,
            "required_r37_replay_and_validation_members": sorted(REQUIRED_SOURCE_MEMBERS),
        },
        "evidence_archive": {
            "name": evidence_zip.name,
            "bytes": evidence_zip.stat().st_size,
            "sha256": sha_file(evidence_zip),
            "package_receipt_and_outer_manifest_identity": "PASS",
            "frozen_replay_members": ["extract.txt", "extract-pypdf.txt", "render/r37-p001.png", "render/r37-p237.png", "render/r37-p238.png"],
        },
        "frozen_source_bindings": {
            "cumulative_manifest": {"bytes": MANIFEST_BYTES, "sha256": MANIFEST_SHA, "coverage": "through2.1.9 / canonical lines1-1605 / 227 historical markers"},
            "korean_target": {"bytes": TARGET_BYTES, "sha256": TARGET_SHA},
            "build_script": {"bytes": BUILD_SCRIPT_BYTES, "sha256": BUILD_SCRIPT_SHA},
        },
        "build": {
            "invocations": 1,
            "internal_xelatex_passes": 8,
            "mutex": "Global\\InterlanguageTeXSlotV1",
            "pass_count_proof": {
                "bytes": build_script.stat().st_size,
                "sha256": sha_file(build_script),
                "four_pass_loop_definition": 1,
                "cycle_invocations": 2,
                "declared_xelatex_invocations": 8,
                "failure_semantics": "each engine invocation throws on nonzero exit; pass3 must equal pass4 inside each cycle; cycle B final must equal cycle A final",
                "result": "PASS_EXACT_BUILD_SCRIPT_CONTROL_FLOW",
            },
            "terminal_completion_proof": {
                "stdout_terminal_record": terminal,
                "cycle_a_pass3_equals_pass4": True,
                "cycle_b_pass3_equals_pass4": True,
                "cycle_finals_byte_identical": True,
                "portable_reader": {"bytes": len(portable_pdf), "sha256": portable_sha},
                "result": "PASS",
            },
            "timeout_seconds": 1800,
            "timed_out": False,
            "live_authority_environment": "omitted; frozen target hashes, declared inputs and admission records enforced",
            "returncode": result.returncode,
            "stdout": ident_bytes(result.stdout),
            "stderr": ident_bytes(result.stderr),
            "log": {"bytes": raw_log.stat().st_size, "sha256": sha_file(raw_log)},
            "result": "PASS",
        },
        "strict_reader": {"bytes": len(strict_pdf), "sha256": sha_bytes(strict_pdf), "pages": PAGES},
        "portable_reader": {"bytes": len(portable_pdf), "sha256": portable_sha, "pages": portable_pages},
        "pdf_byte_identical": pdf_equal,
        "container_delta": {
            "observed": not pdf_equal,
            "strict": {"bytes": len(strict_pdf), "sha256": sha_bytes(strict_pdf)},
            "portable": {"bytes": len(portable_pdf), "sha256": portable_sha},
            "byte_identical": pdf_equal,
            "size_delta_portable_minus_strict": len(portable_pdf) - len(strict_pdf),
            "classification": "none; containers are byte-identical" if pdf_equal else "unadjudicated container-level delta only",
            "retention": "portable container identity is retained in this receipt; its staging bytes are deliberately deleted after all content-property replays pass",
            "inference_rule": "No content, correctness, completion or publication-status inference is made from a container difference.",
        },
        "extraction": {
            "poppler": {**ident_bytes(strict_poppler), "strict_portable_and_frozen_byte_identical": True, "hangul": len(re.findall("[가-힣]", strict_poppler.decode("utf-8"))), "replacement_characters": strict_poppler.decode("utf-8").count("\ufffd")},
            "pypdf": {**ident_bytes(strict_pypdf), "strict_portable_and_frozen_byte_identical": True, "hangul": len(re.findall("[가-힣]", strict_pypdf.decode("utf-8"))), "replacement_characters": strict_pypdf.decode("utf-8").count("\ufffd")},
        },
        "extraction_runtime": {
            "python_version": sys.version.split()[0],
            "pypdf_version": pypdf.__version__,
            "pypdf_version_required": EXPECTED_PYPDF_VERSION,
            "pdftotext_version": pdftotext_version_text,
            "pdftotext_version_required": EXPECTED_PDFTOTEXT_VERSION,
            "pypdf_page_join": "LF+FF+LF with one final LF; CRLF/CR normalized to LF",
            "poppler_options": ["-enc", "UTF-8", "-eol", "unix", "input.pdf", "-"],
        },
        "render_replay": {
            "comparisons": len(render_rows),
            "dpi": 200,
            "pages": render_rows,
            "result": "PASS_EXACT_PORTABLE_FROZEN_RASTER_IDENTITY_3_OF_3",
        },
        "visual_qa": "Portable raster bytes on pages1,237,238 exactly reproduce their already inspected strict-reader counterparts; no new full-document visual rereview is claimed.",
        "staging_cleanup": {
            "exact_target": "[PRIVATE_ROOT]/release-staging/r37-portable-replay",
            "scope": "only the fresh task-owned replay staging directory after all replay gates passed",
            "deleted": True,
        },
        "result": "PASS_PORTABLE_BUILD_EXACT_TEXT_AND_SELECTED_RENDER_REPLAY",
    }
    receipt_payload = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    safe_remove_stage(stage, staging_parent)
    receipt_path.write_bytes(receipt_payload)
    require(json.loads(receipt_path.read_text(encoding="utf-8")) == receipt, "written R37 portable receipt replay drift")
    print(
        "PASS_R37_PORTABLE_REPLAY|"
        f"portable_pdf={len(portable_pdf)}/{portable_sha}|"
        f"pdf_identical={str(pdf_equal).lower()}|"
        f"receipt={receipt_path.stat().st_size}/{sha_file(receipt_path)}"
    )


if __name__ == "__main__":
    main()
