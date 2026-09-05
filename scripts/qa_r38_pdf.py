#!/usr/bin/env python3
"""Fail-closed cumulative PDF QA for the EGA-ko 2026-09-05-r38 edition."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader

import qa_r37_pdf as common


EDITION = "2026-09-05-r38"
EXACT_DOI = "10.5281/zenodo.22346664"
CONCEPT_DOI = "10.5281/zenodo.21921513"
PRIOR_DOI = "10.5281/zenodo.22315714"
GLOBAL_DOI = "10.5281/zenodo.20414353"
GITHUB = "https://github.com/KokunoYumeto/ega-ko"

PDF = (1_485_270, "FEC06D6723BFE9CC7D3C46E285C7DE8A49929F2797FD2F4F47877D2BDA06FE15")
PASS2 = (1_485_279, "E6945583AA1D5AE63F0424109463DFAE04F46DFBF7EE1380638A3E3DF156D699")
LOG = (51_956, "3F82AC4B8E3FE604C565C3ACCE72C4559E760AA60163B53F6ED86086A8AFE4D2")
MANIFEST = (16_250, "50C9896A8436E2A381817BA322DE45A5EFCB768F2790E7BC14A206D70AAA81AE")
PRE_CORRECTION_MANIFEST = (
    16_250,
    "94DB0BE14D7833BE8298722A8E10ED03FE16360606277A4E779139050CCA1BDE",
)
FRONT = (4_440, "1A709228BA6CE5AEACFC6653686234B2961D8309D40BC30F930E066DF048BC72")
PRIVATE_FRONT = (3_888, "E1F03F9FBD820E4CDDAF3DF52900919F35B5D49E1452940891E66EFA48221338")
TARGET = (80_222, "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006")
CANDIDATE = (4_599, "8D37AF2B8B05D9C938F2D282F58902092FB7FCF55300B0A85B28C9538340CF93")
CANONICAL = (820_504, "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E")
CANONICAL_PREFIX = (78_088, "7DE4ECF8630F2B575C08ED0EE4AEC560F6BD4C6026C4BC894DD057D4AE1B9B75")
PRE_CORRECTION_PREFIX = (
    78_089,
    "6C9C0EE5DC909DFE7911564F1F982FF0539C923DE706188F7935FC0585549585",
)
SEALED_PREFIX = (75_622, "FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383")
BUILD_SCRIPT = (20_370, "330A0F8337C6019010700088E0D8D398EA0B33CA922D06641D607E2F63D51F77")
ADMISSION = (8_103, "23CA8C711E89448D910BCD585BCC815B1A87F56A9890220485F27E3E8377FEC2")
INTEGRATION = (5_209, "3901DE2B2F9BD1DDB6399D7B35005FAD196F1A3A229061D9D46F3813E58BB020")
INVENTORY = (1_490, "A55400B0236DDB3A32C47C3AA14B45B0ACFF0260EF843779EB0487F6B649ADE3")
RECONCILIATION = (
    6_698,
    "C60088AE26B2E33B2CFBCD88044E1F5BDA2636DB2BF93D5E392B62CB4915688C",
)
SOURCEKEEPER_CONTROL = (
    1_043,
    "65AB1EDC9C12D7E79CC00B8F6BF1835B8FBCAB9DC7AD5D8EFC07DBE2E1B2771C",
)
CANON_EVENT = (
    5_171,
    "DF32A17C6DF0A950D880551DDC9BE083D85D7A2CF3E702F9984A475642A438D7",
)
SYNC_RECEIPT = (
    4_732,
    "8153FE04EC311BBDA2E377F3B305D345145D09C2691070A9DC168830F5788D7D",
)
STRICT_BUILD = (8_533, "E8A844FF6DA59EAFAA890D34E180B81BE2B8D1D639E4801692897B89DA5CD6FB")
PRE_PRIVACY_STRICT_BUILD = (
    7_613,
    "98B5AE054414650A7488B98F8DA3A0E20679D1B4036587DAEE05B599707CC8D2",
)
PAGES = 239
MARKERS = 228
RENDER_DPI = 300
RENDER_PAGES = [1, 2, 6, 237, 238, 239]
INSPECTED_RENDER_IDENTITIES = {
    1: (133_699, "8A9C079746DC9D2BAACE84D02E46635FAE87E8073D483A88C962590ED82116E6"),
    2: (494_472, "97F4435291368165C762F357F86E6FCD3AEC2F5ACA41C764D9C0A7D110957723"),
    6: (273_914, "BD71C92D1810D28FE7F9289F4FF20D38452A7970F0CE5BBE742209A7E3B01977"),
    237: (818_805, "F639B832388C5839EA866E69E04479ACCC88FDB9154CE82D75511CBA5D8F10F2"),
    238: (733_896, "3343138791A864AECF7584DB54BA7A375FE5EC613E7D82E6093C210CB66ECDF9"),
    239: (209_400, "8D2157D299589D0A6743DBDF720A2FEF2E5336F2544A5A6C685E5E2DE9ACA834"),
}
LABEL_DESTINATIONS = {
    "II.2.1.10-ko": "section*.318",
    "II.2.1.11-ko": "section*.319",
    "subsection:II.2.2-ko": "subsection*.320",
    "II.2.2.1-ko": "section*.321",
}


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def require(path: Path, identity: tuple[int, str]) -> None:
    assert path.is_file(), f"missing file: {path}"
    assert path.stat().st_size == identity[0], (path, path.stat().st_size, identity[0])
    assert common.sha256(path) == identity[1], (path, common.sha256(path), identity[1])


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value


def stable_identity(path: Path, display_path: str) -> dict[str, Any]:
    """Return an exact identity without leaking a machine-local absolute path."""
    identity = common.file_identity(path)
    identity["path"] = display_path
    return identity


def mirrored_control(
    private: Path, public: Path, identity: tuple[int, str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    require(private, identity)
    require(public, identity)
    assert private.read_bytes() == public.read_bytes()
    return load_json(public), common.file_identity(public, public.parents[2])


def validate_strict(control: dict[str, Any]) -> None:
    assert control["schema"] == "agko-r38-strict-build-control-v1"
    assert control["seal_revision"] == 3
    assert (
        control["superseded_pre_privacy_seal"]["bytes"],
        control["superseded_pre_privacy_seal"]["sha256"],
    ) == PRE_PRIVACY_STRICT_BUILD
    assert control["release"]["version"] == EDITION
    assert control["release"]["exact_doi"] == EXACT_DOI
    assert control["release"]["concept_doi"] == CONCEPT_DOI
    assert control["reader"] == {
        "path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf",
        "bytes": PDF[0],
        "sha256": PDF[1],
        "pages": PAGES,
    }
    manifest = control["coverage"]["manifest"]
    assert manifest["path"] == "source/CUMULATIVE_INPUTS.json"
    assert (manifest["bytes"], manifest["sha256"]) == MANIFEST
    assert manifest["historical_marker_sum"] == MARKERS
    reconciliation = control["coverage"]["post_correction_source_reconciliation"]
    assert (reconciliation["bytes"], reconciliation["sha256"]) == RECONCILIATION
    assert reconciliation["private_public_exact"] is True
    assert (
        reconciliation["current_canonical_source_bytes"],
        reconciliation["current_canonical_source_sha256"],
    ) == CANONICAL
    assert (
        reconciliation["current_admitted_prefix_bytes"],
        reconciliation["current_admitted_prefix_sha256"],
    ) == CANONICAL_PREFIX
    assert reconciliation["r38_unit_unchanged"] is True
    assert reconciliation["korean_target_unchanged"] is True
    assert control["build_script"]["path"] == "build/BUILD.ps1"
    assert (
        control["build_script"]["bytes"],
        control["build_script"]["sha256"],
    ) == BUILD_SCRIPT
    strict = control["strict_build"]
    assert strict["status"] == "PASS"
    assert strict["mutex"] == r"Global\InterlanguageTeXSlotV1"
    assert strict["mutex_timeout_ms"] == 300_000
    assert strict["abandoned_recovery"] is False
    assert strict["live_canonical_and_private_coverage_gate"] == "PASS"
    for cycle_name in ("cycle_a", "cycle_b"):
        cycle = control["convergence"][cycle_name]
        assert (cycle["pass2"]["bytes"], cycle["pass2"]["sha256"]) == PASS2
        assert (cycle["pass3"]["bytes"], cycle["pass3"]["sha256"]) == PDF
        assert (cycle["pass4"]["bytes"], cycle["pass4"]["sha256"]) == PDF
        assert (cycle["raw_log"]["bytes"], cycle["raw_log"]["sha256"]) == LOG
        assert cycle["pass2_equals_final"] is False
        assert cycle["pass3_equals_pass4"] is True
    assert control["convergence"]["cycle_pass2_byte_identical"] is True
    assert control["convergence"]["cycle_pass3_byte_identical"] is True
    assert control["convergence"]["cycle_finals_byte_identical"] is True
    assert control["convergence"]["cycle_raw_logs_byte_identical"] is True
    assert control["convergence"]["reader_promotion_byte_identical_to_both_cycle_finals"] is True
    replay = control["post_correction_replay"]
    assert replay["source_reconciliation"] == "PASS"
    assert replay["manifest_reconciliation"] == "PASS"
    assert replay["strict_build"] == "PASS"
    assert replay["output_identity_equals_pre_correction_seal"] is True
    assert replay["privacy_locator_sanitization"].startswith("PASS;")
    assert replay["tex_replay_required_for_privacy_only_change"] is False
    assert replay["source_manifest_target_reader_and_build_artifacts_rechecked_unchanged"] is True
    assert control["status"] == "PASS_R38_STRICT_TWO_CYCLE_FOUR_PASS_BUILD"


def validate_inputs(
    repo: Path, work: Path, canonical_root: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    ordered = manifest["ordered_inputs"]
    matrix = manifest["coverage_matrix"]
    translated = [row for row in matrix if row["target_path"] is not None]
    assert len(ordered) == 17
    assert len({row["path"] for row in ordered}) == 17
    assert len(matrix) == 23
    assert len(translated) == 17
    by_target = {row["target_path"]: row for row in translated}
    assert set(by_target) == {row["path"] for row in ordered}
    targets: list[dict[str, Any]] = []
    for entry in ordered:
        row = by_target[entry["path"]]
        public = repo / "source" / entry["path"]
        private = work / row["working_path"]
        expected = (row["target_bytes"], row["target_sha256"])
        require(public, expected)
        if entry["path"] == "front.tex":
            assert row["coverage"] == (
                "full source EOF; public target adds cumulative-edition metadata"
            )
            require(private, PRIVATE_FRONT)
            private_public_exact = False
        else:
            require(private, expected)
            assert public.read_bytes() == private.read_bytes()
            private_public_exact = True
        assert public.read_text(encoding="utf-8").count("\n") == row["target_lf_lines"]
        targets.append(
            {
                "path": entry["path"],
                "role": entry["role"],
                "bytes": row["target_bytes"],
                "lf_lines": row["target_lf_lines"],
                "sha256": row["target_sha256"],
                "working_path": row["working_path"],
                "private_bytes": private.stat().st_size,
                "private_lf_lines": private.read_text(encoding="utf-8").count("\n"),
                "private_sha256": common.sha256(private),
                "private_public_exact": private_public_exact,
                "historical_page_markers": row["historical_page_markers"],
                "coverage": row["coverage"],
            }
        )
    sources: list[dict[str, Any]] = []
    for row in matrix:
        source = canonical_root / "source" / row["source_path"]
        require(source, (row["source_bytes"], row["source_sha256"]))
        assert source.read_text(encoding="utf-8").count("\n") == row["source_lf_lines"]
        sources.append(
            {
                "driver_line": row["driver_line"],
                "path": row["source_path"],
                "bytes": row["source_bytes"],
                "lf_lines": row["source_lf_lines"],
                "sha256": row["source_sha256"],
                "translation_status": row["status"],
            }
        )
    counts = Counter(row["status"] for row in matrix)
    assert counts == Counter({"complete": 16, "not_translated": 6, "partial": 1})
    exact_private_mirrors = [row for row in targets if row["private_public_exact"]]
    assert len(exact_private_mirrors) == 16
    assert [row["path"] for row in targets if not row["private_public_exact"]] == [
        "front.tex"
    ]
    return {
        "ordered_input_count": 17,
        "all_17_public_identities_match_manifest": True,
        "private_working_files_checked": 17,
        "byte_identical_private_mirrors": 16,
        "all_non_front_private_mirrors_byte_identical": True,
        "front_public_metadata_divergence_exactly_validated": True,
        "ordered_inputs": targets,
        "canonical_driver_input_count": 23,
        "all_23_canonical_identities_match_manifest": True,
        "canonical_inputs": sources,
        "coverage_status_counts": dict(sorted(counts.items())),
    }


def text_features(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        **common.file_identity(path),
        "characters": len(text),
        "hangul_syllables": len(re.findall(r"[\uac00-\ud7a3]", text)),
        "hangul_jamo": len(re.findall(r"[\u1100-\u11ff\u3130-\u318f]", text)),
        "replacement_characters": text.count("\ufffd"),
        "carriage_returns": text.count("\r"),
        "formfeeds": text.count("\f"),
        "current_exact_doi_count": text.count(EXACT_DOI),
        "prior_exact_doi_count": text.count(PRIOR_DOI),
        "concept_doi_count": text.count(CONCEPT_DOI),
    }


def content_checks(text: str) -> dict[str, bool]:
    folded = re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))
    checks = {
        "environment_2_1_10_heading_present": "(2.1.10)" in text,
        "environment_2_1_11_heading_present": "(2.1.11)" in text,
        "environment_2_2_1_heading_present": "(2.2.1)" in text,
        "subsection_fraction_ring_heading_present": "등급환의분수환" in folded,
        "essentially_reduced_present": "본질적으로축소" in folded,
        "nilradical_present": "멱영근기" in folded,
        "essentially_integral_present": "본질적으로정역" in folded,
        "universal_nonzero_homogeneous_condition_present": (
            "동차원소가운데" in folded and "모두이환에서영인자가아니어서" in folded
        ),
        "arbitrary_integer_including_zero_present": "영을포함한임의의정수" in folded,
        "free_system_not_basis_present": "자유계를이루며" in folded,
        "indeterminate_present": "부정원이다" in folded,
        "historical_page_II_24_present": bool(
            re.search(r"(?<![A-Za-z0-9])II\s*\|\s*24(?!\d)", text)
        ),
    }
    assert all(checks.values()), {key: value for key, value in checks.items() if not value}
    return checks


def find_pages(page_text: list[str], pattern: str) -> list[int]:
    regex = re.compile(pattern)
    return [number for number, text in enumerate(page_text, 1) if regex.search(text)]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    return result


def version_line(result: subprocess.CompletedProcess[str]) -> str:
    lines = result.stderr.splitlines() or result.stdout.splitlines()
    assert lines
    return lines[0]


def main() -> None:
    if not __debug__:
        raise RuntimeError(
            "qa_r38_pdf.py requires normal Python assertion semantics; optimized mode is forbidden"
        )
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--work-root", required=True, type=Path)
    parser.add_argument("--canonical-root", required=True, type=Path)
    parser.add_argument(
        "--confirm-visual-pass",
        action="store_true",
        help=(
            "Seal final controls only after the exact prepared render identities were inspected; "
            "confirmation validates and reuses those bytes without rerendering."
        ),
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    work = args.work_root.resolve()
    canonical_root = args.canonical_root.resolve()

    pdf = repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    build_pdf = repo / "build" / "out" / "main.pdf"
    pass2 = repo / "build" / "out" / "main.pass2.pdf"
    pass3 = repo / "build" / "out" / "main.pass3.pdf"
    log = repo / "build" / "out" / "main.log"
    aux = repo / "build" / "out" / "main.aux"
    manifest_path = repo / "source" / "CUMULATIVE_INPUTS.json"
    front = repo / "source" / "front.tex"
    target = repo / "source" / "c2s1.tex"
    private_target = work / "ega" / "II" / "c2s1.tex"
    candidate = work / "candidates" / "r38-c2s1-continuation.tex"
    canonical = canonical_root / "source" / "ega2" / "ega2-1-fr.tex"
    driver = canonical_root / "source" / "EGA_FR.tex"
    sourcekeeper_control = canonical_root / "controls" / "EGA2_SOURCEKEEPER_T2.jsonl"
    canon_event = canonical_root / "controls" / "CANON_EVENT_20260905_D54.json"
    sync_receipt_path = (
        canonical_root
        / "qa"
        / "canon"
        / "ega_d54"
        / "EGA2_1_FR_KOREAN_SYNC_RECEIPT_20260905.json"
    )
    build_script = repo / "build" / "BUILD.ps1"
    poppler_extract = repo / "evidence" / "r38-extract-poppler.txt"
    pypdf_extract = repo / "evidence" / "r38-extract-pypdf.txt"
    private_output = work / "controls" / "R38_PDF_QA.json"
    public_output = repo / "evidence" / "controls" / "R38_PDF_QA.json"

    require(pdf, PDF)
    require(build_pdf, PDF)
    assert pdf.read_bytes() == build_pdf.read_bytes()
    require(pass2, PASS2)
    require(pass3, PDF)
    assert pass3.read_bytes() == build_pdf.read_bytes()
    require(log, LOG)
    require(manifest_path, MANIFEST)
    require(front, FRONT)
    require(target, TARGET)
    require(private_target, TARGET)
    assert target.read_bytes() == private_target.read_bytes()
    require(candidate, CANDIDATE)
    require(canonical, CANONICAL)
    require(sourcekeeper_control, SOURCEKEEPER_CONTROL)
    require(canon_event, CANON_EVENT)
    require(sync_receipt_path, SYNC_RECEIPT)
    for line in sourcekeeper_control.read_text(encoding="utf-8").splitlines():
        json.loads(line)
    load_json(canon_event)
    sync_receipt = load_json(sync_receipt_path)
    assert sync_receipt["schema"] == "ega2_french_authority_consumer_sync_v1"
    assert sync_receipt["status"] == (
        "PASS_EXACT_SINGLE_BYTE_TRANSCRIPTION_RESTORATION__KOREAN_TEXT_UNCHANGED"
    )
    assert sync_receipt["governance"]["sourcekeeper_correction_id"] == (
        "EG-EGA-II-P22-FR-2.1.8-PUNCTUATION-001"
    )
    assert sync_receipt["governance"]["canon_event_id"] == (
        "EGA-CANON-EVENT-20260905-D54"
    )
    assert sync_receipt["korean_consumer"]["text_change_required"] is False
    assert (
        sync_receipt["korean_consumer"]["bytes"],
        sync_receipt["korean_consumer"]["sha256"],
    ) == TARGET
    require(build_script, BUILD_SCRIPT)

    admission, admission_id = mirrored_control(
        work / "controls" / "R38_TRANSLATION_ADMISSION.json",
        repo / "evidence" / "controls" / "R38_TRANSLATION_ADMISSION.json",
        ADMISSION,
    )
    integration, integration_id = mirrored_control(
        work / "controls" / "R38_TRANSLATION_INTEGRATION.json",
        repo / "evidence" / "controls" / "R38_TRANSLATION_INTEGRATION.json",
        INTEGRATION,
    )
    inventory, inventory_id = mirrored_control(
        work / "controls" / "R38_CANONICAL_INVENTORY_REFRESH.json",
        repo / "evidence" / "controls" / "R38_CANONICAL_INVENTORY_REFRESH.json",
        INVENTORY,
    )
    reconciliation, reconciliation_id = mirrored_control(
        work / "controls" / "R38_POST_CORRECTION_SOURCE_RECONCILIATION.json",
        repo / "evidence" / "controls" / "R38_POST_CORRECTION_SOURCE_RECONCILIATION.json",
        RECONCILIATION,
    )
    strict, strict_id = mirrored_control(
        work / "controls" / "R38_STRICT_BUILD.json",
        repo / "evidence" / "controls" / "R38_STRICT_BUILD.json",
        STRICT_BUILD,
    )
    validate_strict(strict)
    assert admission["schema"] == "agko-r38-translation-admission-v1"
    assert admission["authority"]["admitted_prefix_bytes"] == PRE_CORRECTION_PREFIX[0]
    assert admission["authority"]["admitted_prefix_sha256"] == PRE_CORRECTION_PREFIX[1]
    assert (admission["candidate"]["bytes"], admission["candidate"]["sha256"]) == CANDIDATE
    assert (
        admission["prospective_integration"]["bytes"],
        admission["prospective_integration"]["sha256"],
    ) == TARGET
    assert admission["structure_and_formula_validation"]["result"].startswith("PASS_R38_")
    assert admission["independent_review"]["result"] == "PASS"
    assert integration["schema"] == "agko-r38-translation-integration-v1"
    assert (
        integration["final_integration"]["bytes"],
        integration["final_integration"]["sha256"],
    ) == TARGET
    assert integration["final_integration"]["private_public_exact"] is True
    assert integration["final_integration"]["sealed_prefix_exact"] is True
    assert integration["final_integration"]["target_lines1629_1708_equal_candidate"] is True
    assert str(integration["result"]).startswith("PASS_R38_TRANSLATION_INTEGRATION")
    assert inventory["schema"] == "agko-r38-canonical-inventory-refresh-v1"
    assert (
        inventory["cumulative_manifest"]["bytes"],
        inventory["cumulative_manifest"]["sha256"],
    ) == PRE_CORRECTION_MANIFEST
    assert inventory["exact_driver_inputs_checked"] == 23
    assert inventory["result"].startswith("PASS_EXACT_23_DRIVER_INPUTS")
    assert reconciliation["schema"] == "agko-r38-post-correction-source-reconciliation-v1"
    assert reconciliation["authority_event"]["correction_id"] == (
        "EG-EGA-II-P22-FR-2.1.8-PUNCTUATION-001"
    )
    assert reconciliation["authority_event"]["transaction_label"] == (
        "EGA2_FR_DIPLOMATIC_SCAN_COMMA"
    )
    assert reconciliation["authority_event"]["authority_state"] == (
        "SOURCEKEEPER_SCAN_RESTORATION_NO_NEW_MATH_ID"
    )
    authority_sync = reconciliation["authority_event"]["korean_consumer_sync_receipt"]
    assert (authority_sync["bytes"], authority_sync["sha256"]) == SYNC_RECEIPT
    assert authority_sync["status"] == sync_receipt["status"]
    assert authority_sync["text_change_required"] is False
    assert authority_sync["pdf_rebuild_required_solely_for_this_change"] is False
    assert (
        reconciliation["canonical_source"]["postimage"]["bytes"],
        reconciliation["canonical_source"]["postimage"]["sha256"],
    ) == CANONICAL
    assert reconciliation["canonical_source"]["line"] == 1542
    assert reconciliation["source_span_replay"]["r38_unit_lines1607_1683"]["unchanged"] is True
    assert (
        reconciliation["source_span_replay"]["admitted_prefix_lines1_1683"]["postimage_bytes"],
        reconciliation["source_span_replay"]["admitted_prefix_lines1_1683"]["postimage_sha256"],
    ) == CANONICAL_PREFIX
    assert reconciliation["korean_target"]["translation_change_required"] is False
    assert (
        reconciliation["manifest_reconciliation"]["postimage_bytes"],
        reconciliation["manifest_reconciliation"]["postimage_sha256"],
    ) == MANIFEST
    assert reconciliation["result"].startswith(
        "PASS_R38_POST_CORRECTION_SOURCE_RECONCILIATION"
    )

    target_bytes = target.read_bytes()
    assert digest_bytes(target_bytes[: SEALED_PREFIX[0]]) == SEALED_PREFIX[1]
    assert target_bytes[SEALED_PREFIX[0] : SEALED_PREFIX[0] + 1] == b"\n"
    assert target_bytes[SEALED_PREFIX[0] + 1 :] == candidate.read_bytes()
    target_text = target_bytes.decode("utf-8")
    assert target_text.count("\n") == 1_708
    for label in LABEL_DESTINATIONS:
        assert target_text.count(f"\\label{{{label}}}") == 1
    assert target_text.count(r"\oldpage[II]{24}") == 1
    assert target_text.count(r"\emph{자유계}") == 1

    canonical_lines = canonical.read_text(encoding="utf-8").splitlines()
    assert canonical_lines[1541] == (
        r"contienne pas $S_+$. Alors, si $f\in S_+$ n'appartient pas à"
    )
    prefix = ("\n".join(canonical_lines[:1683]) + "\n").encode("utf-8")
    assert (len(prefix), digest_bytes(prefix)) == CANONICAL_PREFIX
    manifest = load_json(manifest_path)
    assert manifest["schema"] == "ega-ko-cumulative-inputs-v2"
    assert manifest["scope"]["historical_source_pages"] == MARKERS
    assert manifest["scope"]["historical_page_ranges"] == [
        "EGA I introduction5-8",
        "EGA 0_I11-78",
        "EGA I Chapter I79-214",
        "EGA II5-24",
    ]
    assert "lines1-1683" in manifest["scope"]["terminal_coverage"]
    require(driver, (manifest["authority_driver"]["bytes"], manifest["authority_driver"]["sha256"]))
    input_validation = validate_inputs(repo, work, canonical_root, manifest)

    aux_text = aux.read_text(encoding="utf-8")
    for label, destination in LABEL_DESTINATIONS.items():
        matches = [
            line
            for line in aux_text.splitlines()
            if line.startswith(f"\\newlabel{{{label}}}")
        ]
        assert len(matches) == 1
        assert "{" + destination + "}" in matches[0]

    reader = PdfReader(str(pdf))
    assert len(reader.pages) == PAGES
    assert reader.pdf_header == "%PDF-1.7"
    assert not reader.is_encrypted
    page_sizes = [
        (round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2))
        for page in reader.pages
    ]
    assert all(
        abs(width - 595.28) <= 0.02 and abs(height - 841.89) <= 0.02
        for width, height in page_sizes
    )
    root = reader.trailer["/Root"]
    assert not root.get("/AcroForm")
    names = common.deref(root.get("/Names", {}))
    assert "/JavaScript" not in names
    metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
    assert metadata.get("/Title") == "대수기하학 원론 – 한국어 누적판"
    assert metadata.get("/Author") == "알렉산더 그로텐디크와 장 디외도네"

    page_text = [
        (page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n")
        for page in reader.pages
    ]
    pypdf_text = "\n\f\n".join(page_text) + "\n"
    pypdf_extract.write_text(pypdf_text, encoding="utf-8", newline="\n")
    run(
        [
            "pdftotext",
            "-enc",
            "UTF-8",
            "-eol",
            "unix",
            str(pdf),
            str(poppler_extract),
        ]
    )
    poppler_text = poppler_extract.read_text(encoding="utf-8")
    expected = common.expected_markers(repo, manifest)
    assert len(expected) == MARKERS and expected[-1] == ("II", 24)
    pypdf_markers = common.extracted_markers(pypdf_text)
    poppler_markers = common.extracted_markers(poppler_text)
    assert pypdf_markers == expected
    expected_poppler_numeric = [
        page for volume, page in expected if not (volume == "0I" and page == 70)
    ]
    assert [page for _, page in poppler_markers] == expected_poppler_numeric
    pypdf_features = text_features(pypdf_extract)
    poppler_features = text_features(poppler_extract)
    for features in (pypdf_features, poppler_features):
        assert features["replacement_characters"] == 0
        assert features["carriage_returns"] == 0
        assert features["current_exact_doi_count"] == 1
        assert features["prior_exact_doi_count"] == 0
        assert features["concept_doi_count"] == 1
        assert features["hangul_syllables"] > 150_000
    assert pypdf_features["hangul_syllables"] == poppler_features["hangul_syllables"]
    pypdf_checks = content_checks(pypdf_text)
    poppler_checks = content_checks(poppler_text)

    page_locations = {
        "environment_2_1_10": find_pages(page_text, re.escape("(2.1.10)")),
        "environment_2_1_11": find_pages(page_text, re.escape("(2.1.11)")),
        "historical_marker_II_24": find_pages(
            page_text, r"(?<![A-Za-z0-9])II\s*\|\s*24(?!\d)"
        ),
        "arbitrary_integer_including_zero": find_pages(
            page_text, r"영을 포함한 임의의\s*정수"
        ),
    }
    assert page_locations["environment_2_1_10"] == [238]
    assert page_locations["environment_2_1_11"] == [238]
    assert page_locations["historical_marker_II_24"] == [239]
    assert 238 in page_locations["arbitrary_integer_including_zero"]
    assert page_text[-1].strip()

    navigation = common.scan_navigation(reader)
    required_destinations = {
        f"{label}=>{destination}": destination in reader.named_destinations
        for label, destination in LABEL_DESTINATIONS.items()
    }
    assert all(required_destinations.values())
    assert not navigation["invalid_named_destinations"]
    assert not navigation["invalid_link_destinations"]
    assert not navigation["invalid_outline_destinations"]
    assert navigation["uri_targets"] == {
        f"https://doi.org/{EXACT_DOI}": 1,
        f"https://doi.org/{CONCEPT_DOI}": 1,
        f"https://doi.org/{GLOBAL_DOI}": 1,
        GITHUB: 1,
    }
    navigation["required_r38_named_destinations"] = required_destinations
    navigation.pop("required_r37_named_destinations", None)
    fonts = common.scan_fonts(reader)
    assert fonts["font_resources"] > 0
    assert fonts["embedded_font_resources"] == fonts["font_resources"]
    assert not fonts["unembedded_font_resources"]
    assert fonts["all_type0_hangul_fonts_have_tounicode"]
    diagnostics = common.log_diagnostics(log)
    assert all(value == 0 for value in diagnostics["hard_diagnostics"].values())

    render_dir = repo / "evidence" / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    renders: list[dict[str, Any]] = []
    for number in RENDER_PAGES:
        prefix_path = render_dir / f"r38-p{number:03d}"
        render = prefix_path.with_suffix(".png")
        if not args.confirm_visual_pass:
            run(
                [
                    "pdftoppm",
                    "-f",
                    str(number),
                    "-l",
                    str(number),
                    "-singlefile",
                    "-r",
                    str(RENDER_DPI),
                    "-png",
                    str(pdf),
                    str(prefix_path),
                ]
            )
        require(render, INSPECTED_RENDER_IDENTITIES[number])
        pixels = common.png_dimensions(render)
        assert pixels == [2481, 3508], (render, pixels)
        renders.append(
            {
                **common.file_identity(render, repo),
                "physical_page": number,
                "dpi": RENDER_DPI,
                "pixels": pixels,
                "visual_inspection": (
                    "PASS_NO_OBSERVED_DEFECTS"
                    if args.confirm_visual_pass
                    else "PENDING_EXPLICIT_INSPECTION"
                ),
            }
        )

    pdftotext_version = version_line(run(["pdftotext", "-v"]))
    pdftoppm_version = version_line(run(["pdftoppm", "-v"]))
    if not args.confirm_visual_pass:
        print("PREPARED_R38_PDF_QA_RENDER_SET")
        for path in (poppler_extract, pypdf_extract):
            print(json.dumps(common.file_identity(path, repo), ensure_ascii=False))
        for render in renders:
            print(json.dumps(render, ensure_ascii=False))
        return

    optimized_probe = subprocess.run(
        [sys.executable, "-O", "-B", str(Path(__file__).resolve()), "--help"],
        capture_output=True,
    )
    optimized_probe_output = optimized_probe.stdout + optimized_probe.stderr
    if optimized_probe.returncode == 0:
        raise RuntimeError("optimized-mode negative test unexpectedly returned success")
    if b"PASS_R38_PDF_QA" in optimized_probe_output:
        raise RuntimeError("optimized-mode negative test emitted a false PASS token")
    if b"optimized mode is forbidden" not in optimized_probe_output:
        raise RuntimeError("optimized-mode negative test did not reach the explicit guard")

    qa = {
        "schema": "agko-r38-pdf-qa-v1",
        "edition": EDITION,
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS",
        "scope": (
            "Full reader/build identities, both retained convergence PDFs, raw log, all 17 "
            "cumulative Korean inputs, all 23 canonical driver inputs, five mirrored controls "
            "including post-correction source reconciliation, 239-page structure, all navigation, "
            "complete dual extraction, the full 228-marker "
            "sequence, fonts/ToUnicode, and 300-dpi inspection of six stated pages including "
            "the extraction-discovered II|24 physical page. Sampled renders do not prove the "
            "absence of every possible visual defect on unrendered pages."
        ),
        "required_controls": {
            "translation_admission": admission_id,
            "translation_integration": integration_id,
            "canonical_inventory_refresh": inventory_id,
            "post_correction_source_reconciliation": reconciliation_id,
            "strict_build": strict_id,
            "all_private_public_exact": True,
        },
        "pdf": {
            **common.file_identity(pdf, repo),
            "pages": len(reader.pages),
            "version": reader.pdf_header,
            "page_size_points": sorted(set(page_sizes)),
            "all_pages_a4": True,
            "encrypted": False,
            "metadata": metadata,
            "acroform_present": False,
            "javascript_name_tree_present": False,
            "build_output_pdf": common.file_identity(build_pdf, repo),
            "build_output_pdf_byte_identical": True,
            "retained_pass2_pdf": common.file_identity(pass2, repo),
            "retained_pass3_pdf": common.file_identity(pass3, repo),
            "pass3_equals_final": True,
        },
        "tools": {
            "pdftotext_version": pdftotext_version,
            "pdftoppm_version": pdftoppm_version,
            "pypdf_version": pypdf.__version__,
            "pypdf_method": (
                "page.extract_text() per physical page; CRLF/CR normalized to LF; "
                "pages joined with LF+FF+LF; one final LF; UTF-8 without BOM"
            ),
            "render_command": (
                "pdftoppm -f N -l N -singlefile -r 300 -png "
                "reader/00_EGA_ko_CUMULATIVE_READER.pdf evidence/render/r38-pNNN"
            ),
        },
        "execution_safety": {
            "normal_assertion_semantics_required_by_non_assert_startup_guard": True,
            "optimized_mode_negative_test": {
                "command_role": "current Python executable with -O -B and this helper --help",
                "exit_code": optimized_probe.returncode,
                "pass_token_emitted": False,
                "explicit_guard_message_observed": True,
                "result": "PASS_FAIL_CLOSED",
            },
            "confirmation_mode_pdftoppm_render_invocations": 0,
            "confirmation_reused_exact_inspected_render_identity_constants": True,
        },
        "source_bindings": {
            "manifest": common.file_identity(manifest_path, repo),
            "authority_driver": stable_identity(
                driver, "[CANONICAL_ROOT]/source/EGA_FR.tex"
            ),
            "input_validation": input_validation,
            "canonical_ega2": {
                **stable_identity(
                    canonical, "[CANONICAL_ROOT]/source/ega2/ega2-1-fr.tex"
                ),
                "lf_lines": len(canonical_lines),
            },
            "sourcekeeper_scan_restoration_control": stable_identity(
                sourcekeeper_control,
                "[CANONICAL_ROOT]/controls/EGA2_SOURCEKEEPER_T2.jsonl",
            ),
            "canon_event_D54": stable_identity(
                canon_event,
                "[CANONICAL_ROOT]/controls/CANON_EVENT_20260905_D54.json",
            ),
            "korean_authority_sync_receipt": stable_identity(
                sync_receipt_path,
                "[CANONICAL_ROOT]/qa/canon/ega_d54/"
                "EGA2_1_FR_KOREAN_SYNC_RECEIPT_20260905.json",
            ),
            "canonical_prefix": {
                "lines": "1-1683",
                "bytes": len(prefix),
                "sha256": digest_bytes(prefix),
                "matches_current_manifest": True,
                "historical_admission_preimage_reconciled": True,
            },
            "korean_target": {
                **common.file_identity(target, repo),
                "lf_lines": target_text.count("\n"),
                "private_public_exact": True,
                "sealed_r37_prefix_bytes": SEALED_PREFIX[0],
                "sealed_r37_prefix_sha256": SEALED_PREFIX[1],
                "one_lf_separator_after_sealed_prefix": True,
                "candidate_tail_exact": True,
                "required_labels_present_once": list(LABEL_DESTINATIONS),
                "oldpage_II_24_present_once": True,
            },
            "candidate": stable_identity(
                candidate, "candidates/r38-c2s1-continuation.tex"
            ),
            "front": common.file_identity(front, repo),
            "build_script": common.file_identity(build_script, repo),
        },
        "extractions": [
            {
                **poppler_features,
                "path": "evidence/r38-extract-poppler.txt",
                "content_checks": poppler_checks,
                "numeric_markers_match_with_documented_0I_70_exception": True,
            },
            {
                **pypdf_features,
                "path": "evidence/r38-extract-pypdf.txt",
                "content_checks": pypdf_checks,
                "full_marker_sequence_matches": True,
            },
        ],
        "historical_markers": {
            "source_count": len(expected),
            "normalized_sequence_sha256": common.marker_hash(expected),
            "pypdf_count": len(pypdf_markers),
            "pypdf_full_sequence_matches": True,
            "poppler_count": len(poppler_markers),
            "poppler_numeric_sequence_matches_with_documented_0I_70_exception": True,
            "ranges": ["I|5-8", "0I|11-78", "I|79-214", "II|5-24"],
            "first": expected[:5],
            "last": expected[-5:],
            "terminal_marker": ["II", 24],
            "poppler_specific_limitation": (
                "Inherited EGA 0_I page 70 is extracted without its adjacent volume marker. "
                "The pypdf extraction proves all 228 volume/page entries; Poppler proves the "
                "remaining 227 ordered numeric markers."
            ),
        },
        "page_location_binding": {
            **page_locations,
            "new_content_begins_on_physical_page": 238,
            "terminal_physical_page": 239,
            "II_24_physical_page_discovered_from_full_pypdf_extraction": 239,
            "render_selection_was_extraction_bound_not_guessed": True,
        },
        "navigation": navigation,
        "font_unicode": fonts,
        "build_logs": {"raw_retained": common.file_identity(log, repo), **diagnostics},
        "renders": renders,
        "visual_findings": {
            "status": "PASS_NO_OBSERVED_DEFECTS",
            "selected_physical_pages": RENDER_PAGES,
            "dpi": RENDER_DPI,
            "all_selected_source_pixels_presented_at_native_scale_via_lossless_tiles": True,
            "confirmation_run_reused_exact_inspected_render_bytes_without_rerendering": True,
            "native_resolution_inspection_method": (
                "Each exact 2481x3508 PNG was inspected through four lossless native-resolution "
                "quadrants of 1241x1754 pixels at x offsets 0/1240 and y offsets 0/1754."
            ),
            "native_resolution_inspection_tile_count": 24,
            "clipping_or_overlap_observed": False,
            "missing_or_tofu_glyphs_observed": False,
            "broken_formula_or_diagram_observed": False,
            "unreadable_text_observed": False,
            "title_scope_and_exact_doi_readable": True,
            "contents_terminal_boundary_readable": True,
            "new_environments_and_subsection_readable": True,
            "historical_II_24_marker_and_terminal_module_text_readable": True,
            "sample_boundary": (
                "Visual findings apply to physical pages 1, 2, 6, 237, 238 and 239. "
                "Full-document coverage is supplied separately by structural, source, "
                "extraction, marker, destination and font checks."
            ),
        },
        "limitations": [
            (
                "Plain-text extraction is not lossless for inherited Type1 mathematical or "
                "diagram resources lacking ToUnicode; source-synchronized TeX and rendering "
                "remain the formula authority."
            ),
            (
                "This control does not replace the separate mathematical translation "
                "admission and integration controls."
            ),
            (
                "Archive replay, GitHub/Zenodo publication and anonymous public-byte replay "
                "remain separate release gates."
            ),
        ],
    }
    payload_text = json.dumps(qa, ensure_ascii=False, indent=2) + "\n"
    for local_root in (str(repo), str(work), str(canonical_root)):
        assert local_root not in payload_text
        assert local_root.replace("\\", "\\\\") not in payload_text
    assert re.search(r"(?i)(?<![A-Z])[A-Z]:[\\/]", payload_text) is None
    assert re.search(r"(?i)(?:^|[\\/])Users[\\/]", payload_text) is None
    payload = payload_text.encode("utf-8")
    private_output.write_bytes(payload)
    public_output.write_bytes(payload)
    assert private_output.read_bytes() == public_output.read_bytes()
    identity = common.file_identity(public_output, repo)
    print(
        f"PASS_R38_PDF_QA|{identity['path']}|{identity['bytes']}|{identity['sha256']}"
    )
    for path in (poppler_extract, pypdf_extract):
        print(json.dumps(common.file_identity(path, repo), ensure_ascii=False))
    for render in renders:
        print(json.dumps(render, ensure_ascii=False))


if __name__ == "__main__":
    main()
