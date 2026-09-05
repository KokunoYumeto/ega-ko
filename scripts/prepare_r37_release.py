#!/usr/bin/env python3
"""Create sanitized build evidence and the pre-publication R37 build receipt.

This script is intentionally fail-closed until the independently generated
R37 PDF QA control exists.  The cumulative-manifest identity is measured at
runtime and must agree byte-for-byte with that QA control; its critical scope,
source-prefix, target and historical-marker fields are also independently
cross-checked below.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


PDF_BYTES = 1_479_200
PDF_SHA = "22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61"
PASS2_BYTES = 1_479_213
PASS2_SHA = "24AFB20EEF59581E036ABBEBF590184097F31D1D9DDFFC1E5AA8A406E68FE8A4"
RAW_LOG_BYTES = 51_950
RAW_LOG_SHA = "D3EB9074068C39518143D6E2271D0552039059ED0CE99D0A94CB8F0DB97727BA"
MANIFEST_BYTES = 16_264
MANIFEST_SHA = "21ED41DDE0E7B850C12E9DF7A7839FB3FFE279B5BC205CC4FBE794A9FED4BAED"
EXPECTED_PAGES = 238
EXPECTED_MARKERS = 227
EXPECTED_PREFIX_SHA = "0815285B46DA35D916612CDDACB92A1DD646153FAF6AC0D15E03417F9D349182"
EXPECTED_TARGET_BYTES = 75_622
EXPECTED_TARGET_SHA = "FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def ident(path: Path, repo: Path | None = None) -> dict[str, Any]:
    shown = path.relative_to(repo).as_posix() if repo else str(path)
    return {"path": shown, "bytes": path.stat().st_size, "sha256": sha256(path)}


def sanitize_log(raw: str, repo: Path, private_root: Path, canonical_root: Path) -> str:
    replacements = [
        (str(repo), "[KOREAN_REPO_ROOT]"),
        (str(private_root), "[PRIVATE_WORK_ROOT]"),
        (str(canonical_root), "[CANONICAL_ROOT]"),
    ]
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    for source, target in replacements:
        text = text.replace(source, target).replace(source.replace("\\", "/"), target)
    text = re.sub(r"(?i)C:[\\/]Users[\\/][^\\/\s]+", "[USER_PROFILE]", text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--canonical-root", required=True, type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    private_root = args.private_root.resolve()
    canonical_root = args.canonical_root.resolve()
    raw_log = repo / "build" / "out" / "main.log"
    reader = repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    manifest_path = repo / "source" / "CUMULATIVE_INPUTS.json"
    qa_path = repo / "evidence" / "controls" / "R37_PDF_QA.json"
    admission_path = repo / "evidence" / "controls" / "R37_TRANSLATION_ADMISSION.json"
    build_script = repo / "build" / "BUILD.ps1"
    qa_script = repo / "scripts" / "qa_r37_pdf.py"
    target_path = repo / "source" / "c2s1.tex"

    for required_path in (
        raw_log,
        reader,
        manifest_path,
        qa_path,
        admission_path,
        build_script,
        qa_script,
        target_path,
    ):
        require(required_path.is_file(), f"required R37 input is absent: {required_path}")

    require(reader.stat().st_size == PDF_BYTES, "R37 reader byte count mismatch")
    require(sha256(reader) == PDF_SHA, "R37 reader SHA-256 mismatch")
    require(raw_log.stat().st_size == RAW_LOG_BYTES, "R37 raw build-log byte count mismatch")
    require(sha256(raw_log) == RAW_LOG_SHA, "R37 raw build-log SHA-256 mismatch")
    require(target_path.stat().st_size == EXPECTED_TARGET_BYTES, "R37 c2s1 target byte count mismatch")
    require(sha256(target_path) == EXPECTED_TARGET_SHA, "R37 c2s1 target SHA-256 mismatch")

    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    require(admission.get("schema") == "agko-r37-translation-admission-v1", "wrong R37 admission schema")
    require(admission.get("state", {}).get("translation") == "admitted", "R37 translation is not admitted")
    authority = admission.get("authority", {})
    require(authority.get("admitted_prefix_lines") == "1-1605", "wrong admitted canonical prefix")
    require(authority.get("admitted_prefix_sha256") == EXPECTED_PREFIX_SHA, "wrong admitted prefix SHA-256")
    require(authority.get("next_boundary") == "line 1606 blank; line 1607 begins environment 2.1.10", "wrong next canonical boundary")
    integrated = admission.get("integrated_target", {})
    require(integrated.get("public_path") == "pub/ega-ko/source/c2s1.tex", "wrong admitted public target")
    require(integrated.get("bytes") == EXPECTED_TARGET_BYTES, "admission target byte count mismatch")
    require(integrated.get("sha256") == EXPECTED_TARGET_SHA, "admission target SHA-256 mismatch")

    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    require(qa.get("schema") == "agko-r37-pdf-qa-v1", "wrong R37 PDF QA schema")
    require(qa.get("edition") == "2026-09-05-r37", "wrong R37 PDF QA edition")
    require(qa.get("status") == "PASS", "R37 PDF QA did not pass")
    qa_pdf = qa.get("pdf", {})
    require(qa_pdf.get("bytes") == PDF_BYTES, "QA reader byte count mismatch")
    require(qa_pdf.get("sha256") == PDF_SHA, "QA reader SHA-256 mismatch")
    require(qa_pdf.get("pages") == EXPECTED_PAGES, "QA reader page count mismatch")
    require(qa_pdf.get("build_output_pdf_byte_identical") is True, "QA build output is not reader-identical")
    qa_log = qa.get("build_logs", {}).get("raw_retained", {})
    require(qa_log.get("bytes") == RAW_LOG_BYTES, "QA raw-log byte count mismatch")
    require(qa_log.get("sha256") == RAW_LOG_SHA, "QA raw-log SHA-256 mismatch")
    require(qa.get("visual_findings", {}).get("status") == "PASS", "R37 visual QA did not pass")
    require(qa.get("font_unicode", {}).get("all_type0_hangul_fonts_have_tounicode") is True, "Hangul ToUnicode QA failed")
    require(not qa.get("navigation", {}).get("invalid_named_destinations"), "invalid named destinations remain")
    require(not qa.get("navigation", {}).get("invalid_link_destinations"), "invalid link destinations remain")
    require(not qa.get("navigation", {}).get("invalid_outline_destinations"), "invalid outline destinations remain")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_identity = ident(manifest_path, repo)
    require(manifest_identity["bytes"] == MANIFEST_BYTES, "R37 cumulative-manifest byte count mismatch")
    require(manifest_identity["sha256"] == MANIFEST_SHA, "R37 cumulative-manifest SHA-256 mismatch")
    qa_manifest = qa.get("source_bindings", {}).get("cumulative_manifest", {})
    require(qa_manifest.get("path") == "source/CUMULATIVE_INPUTS.json", "QA manifest path mismatch")
    require(qa_manifest.get("bytes") == manifest_identity["bytes"], "QA manifest byte count mismatch")
    require(qa_manifest.get("sha256") == manifest_identity["sha256"], "QA manifest SHA-256 mismatch")
    require(manifest.get("schema") == "ega-ko-cumulative-inputs-v2", "wrong cumulative manifest schema")
    require(manifest.get("reader") == reader.name, "cumulative manifest reader mismatch")
    scope = manifest.get("scope", {})
    require(scope.get("historical_source_pages") == EXPECTED_MARKERS, "wrong declared historical-source page count")
    require("through2.1.9" in scope.get("terminal_coverage", ""), "manifest terminal coverage omits 2.1.9")
    require("lines1-1605" in scope.get("terminal_coverage", ""), "manifest terminal coverage omits lines1-1605")
    ordered_inputs = manifest.get("ordered_inputs", [])
    require(len(ordered_inputs) == 17, "wrong number of cumulative ordered inputs")
    require(ordered_inputs[-1].get("path") == "c2s1.tex", "c2s1 is not the terminal ordered input")
    matrix = manifest.get("coverage_matrix", [])
    require(len(matrix) == 23, "wrong number of canonical coverage rows")
    c2_rows = [row for row in matrix if row.get("target_path") == "c2s1.tex"]
    require(len(c2_rows) == 1, "c2s1 coverage row is absent or duplicated")
    c2_row = c2_rows[0]
    require(c2_row.get("status") == "partial", "c2s1 coverage status is not partial")
    require(c2_row.get("target_bytes") == EXPECTED_TARGET_BYTES, "manifest c2s1 byte count mismatch")
    require(c2_row.get("target_sha256") == EXPECTED_TARGET_SHA, "manifest c2s1 SHA-256 mismatch")
    admitted_slice = c2_row.get("admitted_source_slice", {})
    require(admitted_slice.get("lines") == "1-1605", "manifest admitted slice mismatch")
    require(admitted_slice.get("sha256") == EXPECTED_PREFIX_SHA, "manifest admitted-prefix SHA-256 mismatch")
    counts = {
        status: sum(1 for row in matrix if row.get("status") == status)
        for status in ("complete", "partial", "not_translated")
    }
    require(counts == {"complete": 16, "partial": 1, "not_translated": 6}, "coverage-matrix status counts changed")
    marker_count = sum(int(row.get("historical_page_markers", 0)) for row in matrix)
    require(marker_count == EXPECTED_MARKERS, "coverage-matrix historical-marker count mismatch")
    qa_markers = qa.get("historical_markers", {})
    require(qa_markers.get("source_count") == EXPECTED_MARKERS, "QA historical-marker count mismatch")
    require(qa_markers.get("pypdf_full_sequence_matches") is True, "pypdf marker sequence mismatch")
    require(qa_markers.get("poppler_numeric_sequence_matches_with_documented_0I_70_exception") is True, "Poppler marker sequence mismatch")
    qa_admission = qa.get("source_bindings", {}).get("separate_translation_control", {})
    admission_identity = ident(admission_path, repo)
    require(qa_admission.get("path") == "evidence/controls/R37_TRANSLATION_ADMISSION.json", "QA admission path mismatch")
    require(qa_admission.get("bytes") == admission_identity["bytes"], "QA admission byte count mismatch")
    require(qa_admission.get("sha256") == admission_identity["sha256"], "QA admission SHA-256 mismatch")

    qa_extractions = {entry.get("path"): entry for entry in qa.get("extractions", [])}
    poppler_qa = qa_extractions.get("evidence/extract.txt", {})
    pypdf_qa = qa_extractions.get("evidence/extract-pypdf.txt", {})
    require(poppler_qa.get("replacement_characters") == 0, "Poppler extraction contains replacement characters")
    require(pypdf_qa.get("replacement_characters") == 0, "pypdf extraction contains replacement characters")
    require(poppler_qa.get("hangul_syllables") == pypdf_qa.get("hangul_syllables"), "extraction Hangul counts differ")
    require(pypdf_qa.get("full_marker_sequence_matches") is True, "pypdf extraction marker sequence mismatch")
    require(poppler_qa.get("numeric_marker_sequence_matches_with_documented_0I_70_exception") is True, "Poppler extraction marker sequence mismatch")

    sanitized = sanitize_log(
        raw_log.read_text(encoding="utf-8", errors="replace"),
        repo,
        private_root,
        canonical_root,
    )
    log_r37 = repo / "evidence" / "build-r37.log"
    log_current = repo / "evidence" / "build.log"
    for path in (log_r37, log_current):
        path.write_text(sanitized, encoding="utf-8", newline="\n")
    require(log_r37.read_bytes() == log_current.read_bytes(), "sanitized public logs differ")
    require(not re.search(r"(?i)C:[\\/]Users[\\/]", sanitized), "local user-profile path remains in sanitized log")

    receipt = {
        "schema_version": 4,
        "version": "2026-09-05-r37",
        "snapshot_phase": "local_qa_checkpoint_before_archive_freeze",
        "coverage": "EGA 0_I and EGA I complete; EGA II Chapter II programme/table of contents complete; EGA II main text contiguous through 2.1.9 at canonical lines 1-1605. Full EGA II and the EGA corpus remain incomplete.",
        "reader": {**ident(reader, repo), "pages": EXPECTED_PAGES},
        "coverage_manifest": {
            **manifest_identity,
            "identity_gate": "Runtime bytes/SHA-256 agree exactly with the pinned R37 manifest identity and R37_PDF_QA.json; critical scope, target, prefix and marker fields independently cross-checked by this script.",
            "ordered_inputs": len(ordered_inputs),
            "canonical_rows": len(matrix),
            **counts,
            "historical_markers": marker_count,
        },
        "exact_doi": "10.5281/zenodo.22315714",
        "concept_doi": "10.5281/zenodo.21921513",
        "prior_public_checkpoint": "r36 / 10.5281/zenodo.22217711; Zenodo and GitHub dual anonymous byte replay PASS",
        "next_source": "EGA II source/ega2/ega2-1-fr.tex line 1607, environment 2.1.10; line 1606 blank",
        "publication_evidence_rule": "This file is a pre-publication snapshot. Frozen archive, portable replay, GitHub/Zenodo transaction and anonymous public-byte replay evidence must be recorded separately and are not inferred here.",
        "engine": "XeLaTeX / MiKTeX",
        "mutex": {
            "name": "Global\\InterlanguageTeXSlotV1",
            "timeout_ms": 300000,
            "acquired": True,
            "abandoned_recovery": False,
        },
        "convergence": {
            "strict_passes": 8,
            "independent_four_pass_cycles": 2,
            "cycle_a": {
                "pass2_bytes": PASS2_BYTES,
                "pass2_sha256": PASS2_SHA,
                "pass3_bytes": PDF_BYTES,
                "pass3_sha256": PDF_SHA,
                "pass4_bytes": PDF_BYTES,
                "pass4_sha256": PDF_SHA,
                "pass2_equals_final": False,
                "pass3_equals_pass4": True,
            },
            "cycle_b": {
                "pass2_bytes": PASS2_BYTES,
                "pass2_sha256": PASS2_SHA,
                "pass3_bytes": PDF_BYTES,
                "pass3_sha256": PDF_SHA,
                "pass4_bytes": PDF_BYTES,
                "pass4_sha256": PDF_SHA,
                "pass2_equals_final": False,
                "pass3_equals_pass4": True,
            },
            "cycle_finals_byte_identical": True,
            "reader_promotion_byte_identical": True,
            "fixed_point_gate": "Pass 2 differs from the accepted reader; pass 3 equals pass 4 in each independent clean cycle, both cycle finals are byte-identical, and reader promotion preserves those exact bytes.",
        },
        "build_script": ident(build_script, repo),
        "logs": {
            "raw_retained": ident(raw_log, repo),
            "expected_raw_identity": {"bytes": RAW_LOG_BYTES, "sha256": RAW_LOG_SHA},
            "public_sanitized": [ident(log_r37, repo), ident(log_current, repo)],
            "public_logs_equal": True,
            "sanitization": "Exact Korean repository, private-work, canonical and local user-profile paths replaced by bracketed role labels; derivatives normalized to LF. The raw log remains under build/out and no historical log was edited.",
            "local_absolute_profile_absent": True,
        },
        "extraction": {
            "poppler": ident(repo / "evidence" / "extract.txt", repo),
            "pypdf": ident(repo / "evidence" / "extract-pypdf.txt", repo),
            "each_hangul_syllables": poppler_qa["hangul_syllables"],
            "each_replacement_characters": 0,
            "full_historical_sequence_pypdf": True,
            "poppler_documented_0I_page70_exception": True,
        },
        "translation_admission": admission_identity,
        "pdf_qa": ident(qa_path, repo),
        "qa_script": ident(qa_script, repo),
        "portable_replay": "Required after frozen source archive; not claimed by this snapshot",
        "status": "PASS_LOCAL_BUILD_AND_PDF_QA",
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    build_receipt = repo / "evidence" / "BUILD_RECEIPT.json"
    build_receipt.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    private_qa = private_root / "controls" / "R37_PDF_QA.json"
    private_build = private_root / "controls" / "R37_BUILD_RECEIPT.json"
    shutil.copyfile(qa_path, private_qa)
    shutil.copyfile(build_receipt, private_build)

    print(
        "PASS_R37_RELEASE_EVIDENCE|"
        f"build_receipt={build_receipt.stat().st_size}/{sha256(build_receipt)}|"
        f"qa={qa_path.stat().st_size}/{sha256(qa_path)}|"
        f"log={log_r37.stat().st_size}/{sha256(log_r37)}|"
        f"manifest={manifest_identity['bytes']}/{manifest_identity['sha256']}"
    )


if __name__ == "__main__":
    main()
