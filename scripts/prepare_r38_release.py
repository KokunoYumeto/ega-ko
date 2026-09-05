#!/usr/bin/env python3
"""Create the sanitized local R38 build evidence and pre-package receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION = "2026-09-05-r38"
EXACT_DOI = "10.5281/zenodo.22346664"
CONCEPT_DOI = "10.5281/zenodo.21921513"
PDF_BYTES = 1_485_270
PDF_SHA = "FEC06D6723BFE9CC7D3C46E285C7DE8A49929F2797FD2F4F47877D2BDA06FE15"
PASS2_BYTES = 1_485_279
PASS2_SHA = "E6945583AA1D5AE63F0424109463DFAE04F46DFBF7EE1380638A3E3DF156D699"
RAW_LOG_BYTES = 51_956
RAW_LOG_SHA = "3F82AC4B8E3FE604C565C3ACCE72C4559E760AA60163B53F6ED86086A8AFE4D2"
MANIFEST_BYTES = 16_250
MANIFEST_SHA = "50C9896A8436E2A381817BA322DE45A5EFCB768F2790E7BC14A206D70AAA81AE"
EXPECTED_PAGES = 239
EXPECTED_MARKERS = 228
CANONICAL_BYTES = 820_504
CANONICAL_SHA = "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E"
UNIT_BYTES = 4_191
UNIT_CHARACTERS = 4_096
UNIT_SHA = "44583D53F17603797145FE63822F3F78DC6ECFD7ADA1B38EF01813F9E3F22BE6"
PREFIX_BYTES = 78_088
PREFIX_SHA = "7DE4ECF8630F2B575C08ED0EE4AEC560F6BD4C6026C4BC894DD057D4AE1B9B75"
TARGET_BYTES = 80_222
TARGET_LINES = 1_708
TARGET_SHA = "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006"
CANDIDATE_BYTES = 4_599
CANDIDATE_SHA = "8D37AF2B8B05D9C938F2D282F58902092FB7FCF55300B0A85B28C9538340CF93"
BUILD_SCRIPT_BYTES = 20_370
BUILD_SCRIPT_SHA = "330A0F8337C6019010700088E0D8D398EA0B33CA922D06641D607E2F63D51F77"
QA_BYTES = 34_043
QA_SHA = "5140761219F2C8AFAC7075BEEF1044D4190FA41B590B670FA349DF1EF6B55B45"
QA_SCRIPT_BYTES = 41_547
QA_SCRIPT_SHA = "CA8449B6FDF0757783F48DC9B969C49B766D4835EDA1223F86CBB2C34268141E"
ADMISSION = (8_103, "23CA8C711E89448D910BCD585BCC815B1A87F56A9890220485F27E3E8377FEC2")
INTEGRATION = (5_209, "3901DE2B2F9BD1DDB6399D7B35005FAD196F1A3A229061D9D46F3813E58BB020")
RECONCILIATION = (6_698, "C60088AE26B2E33B2CFBCD88044E1F5BDA2636DB2BF93D5E392B62CB4915688C")
STRICT = (8_533, "E8A844FF6DA59EAFAA890D34E180B81BE2B8D1D639E4801692897B89DA5CD6FB")
POPPLER = (728_827, "B5A047C7799FD4A741099CE9334797F26CCDDD5EC9D68F9A6A03EFABA6ADDC99")
PYPDF = (703_381, "9207B6B25CBAC5113A6C718C7B970E232E159799AC68CB7C527F908455173AD6")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def ident(path: Path, repo: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(repo).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def assert_ident(path: Path, expected: tuple[int, str], label: str) -> None:
    require(path.is_file(), f"missing {label}: {path}")
    require((path.stat().st_size, sha256(path)) == expected, f"{label} identity drift")


def sanitize_log(raw: str, repo: Path, private_root: Path, canonical_root: Path) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    for source, replacement in (
        (repo, "[KOREAN_REPO_ROOT]"),
        (private_root, "[PRIVATE_WORK_ROOT]"),
        (canonical_root, "[CANONICAL_ROOT]"),
    ):
        rendered = str(source)
        text = text.replace(rendered, replacement).replace(rendered.replace("\\", "/"), replacement)
    text = re.sub(r"(?i)[A-Z]:[\\/]Users[\\/][^\\/\s]+", "[USER_PROFILE]", text)
    text = re.sub(r"(?i)(?<![A-Za-z0-9_])/(?:home|Users)/[^/\s]+", "[USER_PROFILE]", text)
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
    controls = repo / "evidence" / "controls"
    raw_log = repo / "build" / "out" / "main.log"
    reader = repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    manifest_path = repo / "source" / "CUMULATIVE_INPUTS.json"
    target_path = repo / "source" / "c2s1.tex"
    candidate_path = private_root / "candidates" / "r38-c2s1-continuation.tex"
    canonical_path = canonical_root / "source" / "ega2" / "ega2-1-fr.tex"
    build_script = repo / "build" / "BUILD.ps1"
    qa_script = repo / "scripts" / "qa_r38_pdf.py"
    admission_path = controls / "R38_TRANSLATION_ADMISSION.json"
    integration_path = controls / "R38_TRANSLATION_INTEGRATION.json"
    reconciliation_path = controls / "R38_POST_CORRECTION_SOURCE_RECONCILIATION.json"
    strict_path = controls / "R38_STRICT_BUILD.json"
    qa_path = controls / "R38_PDF_QA.json"
    r38_poppler = repo / "evidence" / "r38-extract-poppler.txt"
    r38_pypdf = repo / "evidence" / "r38-extract-pypdf.txt"

    for path, expected, label in (
        (reader, (PDF_BYTES, PDF_SHA), "R38 reader"),
        (raw_log, (RAW_LOG_BYTES, RAW_LOG_SHA), "R38 raw build log"),
        (manifest_path, (MANIFEST_BYTES, MANIFEST_SHA), "R38 cumulative manifest"),
        (target_path, (TARGET_BYTES, TARGET_SHA), "R38 Korean target"),
        (candidate_path, (CANDIDATE_BYTES, CANDIDATE_SHA), "R38 candidate"),
        (canonical_path, (CANONICAL_BYTES, CANONICAL_SHA), "current canonical EGA II source"),
        (build_script, (BUILD_SCRIPT_BYTES, BUILD_SCRIPT_SHA), "build script"),
        (qa_script, (QA_SCRIPT_BYTES, QA_SCRIPT_SHA), "R38 QA helper"),
        (admission_path, ADMISSION, "R38 translation admission"),
        (integration_path, INTEGRATION, "R38 translation integration"),
        (reconciliation_path, RECONCILIATION, "R38 source reconciliation"),
        (strict_path, STRICT, "R38 strict build"),
        (qa_path, (QA_BYTES, QA_SHA), "R38 PDF QA"),
        (r38_poppler, POPPLER, "R38 Poppler extraction"),
        (r38_pypdf, PYPDF, "R38 pypdf extraction"),
    ):
        assert_ident(path, expected, label)
    require(target_path.read_bytes().count(b"\n") == TARGET_LINES, "R38 target LF-line drift")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("schema") == "ega-ko-cumulative-inputs-v2", "wrong cumulative manifest schema")
    require(manifest.get("reader") == reader.name, "cumulative manifest reader mismatch")
    scope = manifest.get("scope", {})
    require(scope.get("historical_source_pages") == EXPECTED_MARKERS, "historical marker-count drift")
    require("through2.2.1" in scope.get("terminal_coverage", ""), "manifest omits terminal 2.2.1")
    require("lines1-1683" in scope.get("terminal_coverage", ""), "manifest omits lines1-1683")
    ordered_inputs = manifest.get("ordered_inputs", [])
    matrix = manifest.get("coverage_matrix", [])
    require(len(ordered_inputs) == 17 and ordered_inputs[-1].get("path") == "c2s1.tex", "ordered input set drift")
    require(len(matrix) == 23, "canonical coverage-row count drift")
    c2_rows = [row for row in matrix if row.get("target_path") == "c2s1.tex"]
    require(len(c2_rows) == 1, "c2s1 coverage row absent or duplicated")
    c2_row = c2_rows[0]
    admitted = c2_row.get("admitted_source_slice", {})
    require((c2_row.get("status"), c2_row.get("target_bytes"), c2_row.get("target_sha256")) == ("partial", TARGET_BYTES, TARGET_SHA), "manifest c2s1 binding drift")
    require((admitted.get("lines"), admitted.get("lf_bytes"), admitted.get("sha256")) == ("1-1683", PREFIX_BYTES, PREFIX_SHA), "manifest canonical-prefix binding drift")
    counts = {status: sum(row.get("status") == status for row in matrix) for status in ("complete", "partial", "not_translated")}
    require(counts == {"complete": 16, "partial": 1, "not_translated": 6}, "coverage status-count drift")
    require(sum(int(row.get("historical_page_markers", 0)) for row in matrix) == EXPECTED_MARKERS, "coverage marker-sum drift")

    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    require(admission.get("schema") == "agko-r38-translation-admission-v1", "wrong R38 admission schema")
    require(admission.get("state", {}).get("translation") == "admitted_candidate", "R38 candidate is not admitted")
    authority = admission.get("authority", {})
    require((authority.get("unit_lines"), authority.get("unit_bytes"), authority.get("unit_characters"), authority.get("unit_sha256")) == ("1607-1683", UNIT_BYTES, UNIT_CHARACTERS, UNIT_SHA), "historical R38 unit binding drift")
    candidate = admission.get("candidate", {})
    require((candidate.get("bytes"), candidate.get("characters"), candidate.get("lf_lines"), candidate.get("sha256")) == (CANDIDATE_BYTES, 2_773, 80, CANDIDATE_SHA), "R38 candidate control drift")
    require(admission.get("structure_and_formula_validation", {}).get("result") == "PASS_R38_SOURCE_CANDIDATE_AND_PROSPECTIVE_MIRRORS", "R38 candidate validation did not pass")

    integration = json.loads(integration_path.read_text(encoding="utf-8"))
    require(integration.get("schema") == "agko-r38-translation-integration-v1", "wrong R38 integration schema")
    final_integration = integration.get("final_integration", {})
    require((final_integration.get("bytes"), final_integration.get("lf_lines"), final_integration.get("sha256"), final_integration.get("private_public_exact")) == (TARGET_BYTES, TARGET_LINES, TARGET_SHA, True), "R38 final integration drift")
    require(str(integration.get("result", "")).startswith("PASS_R38_TRANSLATION_INTEGRATION"), "R38 integration did not pass")

    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    require(reconciliation.get("schema") == "agko-r38-post-correction-source-reconciliation-v1", "wrong reconciliation schema")
    unit = reconciliation["source_span_replay"]["r38_unit_lines1607_1683"]
    prefix = reconciliation["source_span_replay"]["admitted_prefix_lines1_1683"]
    require((unit.get("bytes"), unit.get("characters"), unit.get("sha256"), unit.get("unchanged")) == (UNIT_BYTES, UNIT_CHARACTERS, UNIT_SHA, True), "reconciled R38 unit drift")
    require((prefix.get("postimage_bytes"), prefix.get("postimage_sha256")) == (PREFIX_BYTES, PREFIX_SHA), "reconciled prefix drift")
    require((reconciliation["korean_target"].get("bytes"), reconciliation["korean_target"].get("sha256"), reconciliation["korean_target"].get("translation_change_required")) == (TARGET_BYTES, TARGET_SHA, False), "reconciled target drift")
    require(reconciliation.get("result") == "PASS_R38_POST_CORRECTION_SOURCE_RECONCILIATION_REBUILD_REQUIRED", "source reconciliation did not pass")

    strict = json.loads(strict_path.read_text(encoding="utf-8"))
    require(strict.get("schema") == "agko-r38-strict-build-control-v1", "wrong strict-build schema")
    release = strict.get("release", {})
    require((release.get("version"), release.get("exact_doi"), release.get("concept_doi")) == (VERSION, EXACT_DOI, CONCEPT_DOI), "strict release identity drift")
    require(strict.get("status") == "PASS_R38_STRICT_TWO_CYCLE_FOUR_PASS_BUILD", "strict R38 build did not pass")
    require(strict.get("reader") == {"path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf", "bytes": PDF_BYTES, "sha256": PDF_SHA, "pages": EXPECTED_PAGES}, "strict reader binding drift")
    require(strict.get("strict_build", {}).get("xelatex_passes") == 8, "strict pass count drift")
    require(strict.get("convergence", {}).get("cycle_finals_byte_identical") is True, "strict cycle finals differ")
    require(strict.get("convergence", {}).get("reader_promotion_byte_identical_to_both_cycle_finals") is True, "strict reader promotion drift")

    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    require((qa.get("schema"), qa.get("edition"), qa.get("status")) == ("agko-r38-pdf-qa-v1", VERSION, "PASS"), "wrong R38 PDF-QA identity")
    require((qa["pdf"].get("bytes"), qa["pdf"].get("sha256"), qa["pdf"].get("pages"), qa["pdf"].get("build_output_pdf_byte_identical")) == (PDF_BYTES, PDF_SHA, EXPECTED_PAGES, True), "R38 PDF-QA reader drift")
    require(qa.get("build_logs", {}).get("raw_retained") == {"path": "build/out/main.log", "bytes": RAW_LOG_BYTES, "sha256": RAW_LOG_SHA}, "R38 QA raw-log binding drift")
    required_controls = qa.get("required_controls", {})
    for key, path, expected in (
        ("translation_admission", admission_path, ADMISSION),
        ("translation_integration", integration_path, INTEGRATION),
        ("post_correction_source_reconciliation", reconciliation_path, RECONCILIATION),
        ("strict_build", strict_path, STRICT),
    ):
        require((required_controls.get(key, {}).get("bytes"), required_controls.get(key, {}).get("sha256")) == expected, f"QA {key} binding drift")
        require(required_controls.get(key, {}).get("path") == path.relative_to(repo).as_posix(), f"QA {key} path drift")
    require(qa.get("source_bindings", {}).get("canonical_prefix") == {"lines": "1-1683", "bytes": PREFIX_BYTES, "sha256": PREFIX_SHA, "matches_current_manifest": True, "historical_admission_preimage_reconciled": True}, "QA canonical-prefix binding drift")
    require((qa.get("source_bindings", {}).get("korean_target", {}).get("bytes"), qa.get("source_bindings", {}).get("korean_target", {}).get("sha256")) == (TARGET_BYTES, TARGET_SHA), "QA Korean-target binding drift")
    markers = qa.get("historical_markers", {})
    require(markers.get("source_count") == EXPECTED_MARKERS and markers.get("pypdf_full_sequence_matches") is True, "QA historical-marker gate failed")
    require(markers.get("terminal_marker") == ["II", 24], "QA terminal marker drift")
    require(qa.get("visual_findings", {}).get("status") == "PASS_NO_OBSERVED_DEFECTS", "R38 visual QA did not pass")
    require(qa.get("font_unicode", {}).get("all_type0_hangul_fonts_have_tounicode") is True, "Hangul ToUnicode QA failed")
    navigation = qa.get("navigation", {})
    require(not navigation.get("invalid_named_destinations") and not navigation.get("invalid_link_destinations") and not navigation.get("invalid_outline_destinations"), "invalid PDF navigation remains")
    qa_extractions = {entry["path"]: entry for entry in qa.get("extractions", [])}
    require((qa_extractions["evidence/r38-extract-poppler.txt"]["bytes"], qa_extractions["evidence/r38-extract-poppler.txt"]["sha256"]) == POPPLER, "QA Poppler extraction drift")
    require((qa_extractions["evidence/r38-extract-pypdf.txt"]["bytes"], qa_extractions["evidence/r38-extract-pypdf.txt"]["sha256"]) == PYPDF, "QA pypdf extraction drift")
    require(all(entry.get("replacement_characters") == 0 for entry in qa_extractions.values()), "replacement characters in extraction")

    sanitized = sanitize_log(raw_log.read_text(encoding="utf-8", errors="replace"), repo, private_root, canonical_root)
    require(not re.search(r"(?i)[A-Z]:[\\/]Users[\\/]", sanitized), "absolute Windows profile path remains in sanitized log")
    require(not re.search(r"(?i)(?<![A-Za-z0-9_])/(?:home|Users)/", sanitized), "absolute POSIX profile path remains in sanitized log")
    log_r38 = repo / "evidence" / "build-r38.log"
    log_current = repo / "evidence" / "build.log"
    for path in (log_r38, log_current):
        path.write_text(sanitized, encoding="utf-8", newline="\n")
    require(log_r38.read_bytes() == log_current.read_bytes(), "sanitized public logs differ")
    shutil.copyfile(r38_poppler, repo / "evidence" / "extract.txt")
    shutil.copyfile(r38_pypdf, repo / "evidence" / "extract-pypdf.txt")

    manifest_identity = ident(manifest_path, repo)
    receipt = {
        "schema_version": 5,
        "version": VERSION,
        "snapshot_phase": "local_qa_checkpoint_before_archive_freeze",
        "coverage": "EGA 0_I and EGA I complete; EGA II Chapter II programme/table of contents complete; EGA II main text contiguous through 2.2.1 at canonical lines 1-1683. Full EGA II and the EGA corpus remain incomplete.",
        "reader": {**ident(reader, repo), "pages": EXPECTED_PAGES},
        "coverage_manifest": {
            **manifest_identity,
            "identity_gate": "Runtime bytes/SHA-256 agree exactly with the current R38 reconciliation, strict-build and PDF-QA controls; scope, target, prefix and marker fields are independently cross-checked.",
            "ordered_inputs": len(ordered_inputs),
            "canonical_rows": len(matrix),
            **counts,
            "historical_markers": EXPECTED_MARKERS,
        },
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "prior_public_checkpoint": "r37 / 10.5281/zenodo.22315714; Zenodo and GitHub dual anonymous byte replay PASS",
        "next_source": "EGA II source/ega2/ega2-1-fr.tex line 1685, Lemma 2.2.2; line 1684 blank",
        "publication_evidence_rule": "This file is a pre-publication snapshot. Frozen archive, portable replay, publication transaction and anonymous public-byte replay evidence must be recorded separately and are not inferred here.",
        "engine": "XeLaTeX / MiKTeX",
        "mutex": {"name": "Global\\InterlanguageTeXSlotV1", "timeout_ms": 300000, "acquired": True, "abandoned_recovery": False},
        "convergence": {
            "strict_passes": 8,
            "independent_four_pass_cycles": 2,
            "cycle_a": {"pass2_bytes": PASS2_BYTES, "pass2_sha256": PASS2_SHA, "pass3_bytes": PDF_BYTES, "pass3_sha256": PDF_SHA, "pass4_bytes": PDF_BYTES, "pass4_sha256": PDF_SHA, "pass2_equals_final": False, "pass3_equals_pass4": True},
            "cycle_b": {"pass2_bytes": PASS2_BYTES, "pass2_sha256": PASS2_SHA, "pass3_bytes": PDF_BYTES, "pass3_sha256": PDF_SHA, "pass4_bytes": PDF_BYTES, "pass4_sha256": PDF_SHA, "pass2_equals_final": False, "pass3_equals_pass4": True},
            "cycle_finals_byte_identical": True,
            "reader_promotion_byte_identical": True,
            "fixed_point_gate": "Pass 2 differs from the accepted reader; pass 3 equals pass 4 in each independent clean cycle; both cycle finals and reader promotion are byte-identical.",
        },
        "build_script": ident(build_script, repo),
        "logs": {
            "raw_retained": ident(raw_log, repo),
            "expected_raw_identity": {"bytes": RAW_LOG_BYTES, "sha256": RAW_LOG_SHA},
            "public_sanitized": [ident(log_r38, repo), ident(log_current, repo)],
            "public_logs_equal": True,
            "sanitization": "Repository, private-work, canonical and user-profile paths replaced by bracketed role labels; derivatives normalized to LF. The raw build log remains local under build/out.",
            "absolute_profile_locator_absent": True,
        },
        "extraction": {
            "poppler": ident(repo / "evidence" / "extract.txt", repo),
            "pypdf": ident(repo / "evidence" / "extract-pypdf.txt", repo),
            "r38_named_poppler": ident(r38_poppler, repo),
            "r38_named_pypdf": ident(r38_pypdf, repo),
            "aliases_byte_identical": True,
            "each_hangul_syllables": qa_extractions["evidence/r38-extract-poppler.txt"]["hangul_syllables"],
            "each_replacement_characters": 0,
            "full_historical_sequence_pypdf": True,
            "poppler_documented_0I_page70_exception": True,
        },
        "translation_admission": ident(admission_path, repo),
        "translation_integration": ident(integration_path, repo),
        "post_correction_source_reconciliation": ident(reconciliation_path, repo),
        "strict_build": ident(strict_path, repo),
        "pdf_qa": ident(qa_path, repo),
        "qa_script": ident(qa_script, repo),
        "portable_replay": "Required after frozen source archive; not claimed by this snapshot",
        "status": "PASS_LOCAL_BUILD_AND_PDF_QA",
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    build_receipt = repo / "evidence" / "BUILD_RECEIPT.json"
    build_receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    require(json.loads(build_receipt.read_text(encoding="utf-8")) == receipt, "written R38 build receipt replay drift")

    private_controls = private_root / "controls"
    shutil.copyfile(qa_path, private_controls / "R38_PDF_QA.json")
    shutil.copyfile(build_receipt, private_controls / "R38_BUILD_RECEIPT.json")
    print(
        "PASS_R38_RELEASE_EVIDENCE|"
        f"build_receipt={build_receipt.stat().st_size}/{sha256(build_receipt)}|"
        f"qa={qa_path.stat().st_size}/{sha256(qa_path)}|"
        f"log={log_r38.stat().st_size}/{sha256(log_r38)}|"
        f"manifest={manifest_identity['bytes']}/{manifest_identity['sha256']}"
    )


if __name__ == "__main__":
    main()
