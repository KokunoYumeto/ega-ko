#!/usr/bin/env python3
"""Refresh the live Korean EGA task-state aliases to the exact R37 local-QA head."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


UPDATED = "2026-09-05T05:12:46+02:00"
VERSION = "2026-09-05-r37"
EXACT_DOI = "10.5281/zenodo.22315714"
CONCEPT_DOI = "10.5281/zenodo.21921513"
GITHUB = "https://github.com/KokunoYumeto/ega-ko"

PDF = {
    "path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf",
    "pages": 238,
    "bytes": 1479200,
    "sha256": "22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61",
}
MANIFEST = {
    "path": "source/CUMULATIVE_INPUTS.json",
    "bytes": 16264,
    "sha256": "21ED41DDE0E7B850C12E9DF7A7839FB3FFE279B5BC205CC4FBE794A9FED4BAED",
    "ordered_inputs": 17,
    "canonical_rows": 23,
    "complete": 16,
    "partial": 1,
    "not_translated": 6,
    "historical_markers": 227,
}
SOURCE = {
    "path": "source/ega2/ega2-1-fr.tex",
    "whole_bytes": 820505,
    "whole_sha256": "84EDBE3E83530AF2959B441796337C9DC21EAFCA6A13114A26778760FBF437AC",
    "admitted_lines": "1-1605",
    "admitted_bytes": 73897,
    "admitted_sha256": "0815285B46DA35D916612CDDACB92A1DD646153FAF6AC0D15E03417F9D349182",
}
UNIT = {
    "lines": "1537-1605",
    "bytes": 3776,
    "characters": 3727,
    "lf_lines": 69,
    "sha256": "D91203350D0012E008CA3A778DD5ABB1E3A18D70641C753F6F86ECFF51F949FE",
}
CANDIDATE = {
    "path": "candidates/r37-c2s1-continuation.tex",
    "bytes": 4073,
    "characters": 2783,
    "lf_lines": 72,
    "sha256": "A423B075B3483FC84CA580AED46C651F84543F4444805D94388CD5574114063D",
}
TARGET = {
    "path": "source/c2s1.tex",
    "bytes": 75622,
    "sha256": "FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383",
    "lf_lines": 1627,
}
BUILD = {
    "receipt": "evidence/BUILD_RECEIPT.json",
    "receipt_bytes": 5462,
    "receipt_sha256": "5864BCD80AA33AEB906034A1E07F3BDC8710D699588A448D95ACCBBEC49B84A4",
    "strict_control": "evidence/controls/R37_STRICT_BUILD.json",
    "strict_control_bytes": 3675,
    "strict_control_sha256": "F58CAF4FA4BEF1179288007C4F720B2E1CD3AE5D69AA311D1C345859766C9AF2",
}
TRANSLATION_CONTROL = {
    "path": "evidence/controls/R37_TRANSLATION_ADMISSION.json",
    "bytes": 5919,
    "sha256": "C4EBA3CA0F94A04815BE6585907D0EFB20A63F999710334F758078626D8A89C4",
}
QA_CONTROL = {
    "path": "evidence/controls/R37_PDF_QA.json",
    "bytes": 13472,
    "sha256": "E3CB3AC1D47F4041ADECDA7942383EF0CA52B921E4AF5F9B97A1FF7EFBA1ACDD",
}
DRAFT_CONTROL = {
    "path": "evidence/controls/R37_ZENODO_DRAFT.json",
    "bytes": 493,
    "sha256": "C37529E5F5CEBB90E843EABC76CDBBD6D1A55C9E12F3562A8F48C120F17E2305",
}

COVERAGE = (
    "EGA 0_I and EGA I complete; EGA II Chapter II programme/table of contents "
    "complete; EGA II main text contiguous through2.1.9 at canonical lines1-1605. "
    "Full EGA II and the EGA corpus remain incomplete."
)
SEQUENCE = (
    "Finish EGA II, then FGA. Only afterward admit the contiguous source-accurate "
    "EGA sequence beginning with EGA III; stop before the first incomplete volume. "
    "SGA is outside active scope."
)
QA = {
    "translation": (
        "PASS exact R37 source/candidate/integrated-mirror validation; environment2.1.8, "
        "Proposition2.1.9 with all three conditions and proof,99 inline formulas,2 labels, "
        "1 reference and II23 preserved; canonical S_{n-mk} retained without guessed repair"
    ),
    "build": (
        "PASS two independent four-pass XeLaTeX cycles under Global\\InterlanguageTeXSlotV1; "
        "pass3=pass4 within each cycle and final cycles byte-identical; hard diagnostics0"
    ),
    "extraction": {
        "poppler": {
            "path": "evidence/extract.txt",
            "bytes": 724814,
            "sha256": "DD155CF9FE4B9F7F865E3858387AF4222DA16B41E935D398612670A82953FFBF",
            "markers": 226,
        },
        "pypdf": {
            "path": "evidence/extract-pypdf.txt",
            "bytes": 699470,
            "sha256": "45A9806C13729B3D8E804897B3515FDEAB64E7719B97ADB3C73ED6C5C6AE4B3B",
            "markers": 227,
        },
        "each_hangul": 152023,
        "each_replacement_characters": 0,
        "marker_result": "pypdf full227-entry sequence PASS; Poppler ordered226-marker sequence PASS with inherited bare page70 token documented",
    },
    "links": {
        "annotations": 1657,
        "internal": 1653,
        "resolved_internal": 1653,
        "external_uris": 4,
        "named_destinations": 577,
        "bookmarks": 132,
        "result": "PASS",
    },
    "fonts": (
        "PASS all35 resources embedded; all Hangul Type0 resources have ToUnicode; "
        "eight inherited Type1 math/diagram resources without ToUnicode are explicitly limited"
    ),
    "visual": "PASS selected pages1,2,6,236-238 at200dpi; no clipping, overlap, tofu or malformed formula",
    "portable": "PENDING frozen source archive; no portable-build claim",
    "detailed_control": QA_CONTROL["path"],
    "human_certification": "not claimed or required",
}


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise RuntimeError(f"blank JSONL line at {path}:{number}")
        records.append(json.loads(line))
    return records


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    records = read_jsonl(path)
    matches = [item for item in records if item.get("id") == record["id"]]
    if matches:
        if len(matches) != 1 or matches[0] != record:
            raise RuntimeError(f"conflicting or duplicate record id {record['id']} in {path}")
        return
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def file_identity(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return path.stat().st_size, digest.hexdigest().upper()


def verify_inputs(private: Path, repo: Path) -> None:
    expected = [
        (private / "ega" / "II" / "c2s1.tex", TARGET["bytes"], TARGET["sha256"]),
        (private / CANDIDATE["path"], CANDIDATE["bytes"], CANDIDATE["sha256"]),
        (repo / TARGET["path"], TARGET["bytes"], TARGET["sha256"]),
        (repo / PDF["path"], PDF["bytes"], PDF["sha256"]),
        (repo / MANIFEST["path"], MANIFEST["bytes"], MANIFEST["sha256"]),
        (repo / BUILD["receipt"], BUILD["receipt_bytes"], BUILD["receipt_sha256"]),
        (repo / BUILD["strict_control"], BUILD["strict_control_bytes"], BUILD["strict_control_sha256"]),
        (repo / TRANSLATION_CONTROL["path"], TRANSLATION_CONTROL["bytes"], TRANSLATION_CONTROL["sha256"]),
        (repo / QA_CONTROL["path"], QA_CONTROL["bytes"], QA_CONTROL["sha256"]),
        (repo / DRAFT_CONTROL["path"], DRAFT_CONTROL["bytes"], DRAFT_CONTROL["sha256"]),
    ]
    for path, expected_bytes, expected_sha256 in expected:
        actual = file_identity(path)
        if actual != (expected_bytes, expected_sha256):
            raise RuntimeError(
                f"identity mismatch for {path}: expected {(expected_bytes, expected_sha256)}, got {actual}"
            )


def public_base() -> dict[str, Any]:
    return {
        "schema_version": 4,
        "version": VERSION,
        "updated": UPDATED,
        "snapshot_phase": "local_build_and_pdf_qa_pass_package_portable_publication_pending",
        "coverage": COVERAGE,
        "reader": PDF,
        "coverage_manifest": MANIFEST,
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "prior_public_checkpoint": (
            "r36 / 10.5281/zenodo.22217711 / GitHub release ega-ko-2026-09-05-r36; "
            "Zenodo and GitHub anonymous byte replay PASS"
        ),
        "next_source": "EGA II source/ega2/ega2-1-fr.tex line1607, environment2.1.10; line1606 blank",
        "publication_evidence_rule": (
            "R37 translation, cumulative build and PDF QA pass locally. Packaging, portable replay, "
            "GitHub/Zenodo publication and anonymous public-byte readback remain separate pending gates."
        ),
    }


def refresh_public(repo: Path) -> None:
    evidence = repo / "evidence"
    base = public_base()
    cursor = {
        **base,
        "source": SOURCE,
        "unit": UNIT,
        "candidate": CANDIDATE,
        "target": TARGET,
        "sequence": SEQUENCE,
        "translation_admission": TRANSLATION_CONTROL,
        "build_receipt": BUILD,
        "validation_checkpoint": QA_CONTROL["path"],
    }
    write_json(evidence / "CURSOR.json", cursor)
    write_json(
        evidence / "PROGRAM_CURSOR.json",
        {
            **cursor,
            "active_volume": "EGA II",
            "later_ega": (
                "EGA III is candidate-ready by direct report but remains sequenced after EGA II and FGA; "
                "exact authority admission is required before translation."
            ),
        },
    )
    state = {
        **base,
        "sequence": [
            "EGA I complete",
            "EGA II active and incomplete",
            "FGA next",
            "EGA III+ only after ordered predecessors and exact source admission",
        ],
        "sga": "outside active scope; coordinate separately later",
        "qa": QA,
        "source": SOURCE,
        "unit": UNIT,
        "candidate": CANDIDATE,
        "target": TARGET,
        "translation_admission": TRANSLATION_CONTROL,
        "build_receipt": BUILD,
        "validation_checkpoint": QA_CONTROL["path"],
        "release_gates": {
            "translation": "PASS",
            "build": "PASS",
            "pdf_qa": "PASS",
            "package": "PENDING",
            "portable_replay": "PENDING",
            "github_publication_and_anonymous_replay": "PENDING",
            "zenodo_publication_and_anonymous_replay": "PENDING",
        },
        "rights": (
            "Per-work rights, provenance, author/source relationship and non-endorsement retained; "
            "no blanket public-domain or open-licence claim"
        ),
    }
    write_json(evidence / "STATE.json", state)
    write_json(evidence / "PROGRAM_STATE.json", state)
    write_json(
        evidence / "QA_STATE.json",
        {
            **base,
            "qa": QA,
            "source": SOURCE,
            "unit": UNIT,
            "candidate": CANDIDATE,
            "target": TARGET,
            "result": "PASS_LOCAL_BUILD_AND_PDF_QA; package, portable replay and publication pending",
            "validation_checkpoint": QA_CONTROL["path"],
        },
    )
    write_json(
        evidence / "VISUAL_QA.json",
        {
            **base,
            "dpi": 200,
            "pages": [1, 2, 6, 236, 237, 238],
            "dimensions": "1654x2339",
            "result": (
                "PASS on six inspected pages: no clipping, overlap, tofu or malformed formula; "
                "R37 environment2.1.8, Proposition2.1.9, proof and diplomatic formula are readable"
            ),
            "detailed_render_identities": QA_CONTROL["path"],
            "historical_markers": {
                "EGA_I_introduction": "5-8 /4",
                "EGA_0_I": "11-78 /68",
                "EGA_I_Chapter_I": "79-214 /136",
                "EGA_II": "5-23 /19",
                "total": 227,
            },
            "links": QA["links"],
            "validation_checkpoint": QA_CONTROL["path"],
        },
    )
    write_json(
        evidence / "SOURCE_AUTHORITY.json",
        {
            **base,
            "source": SOURCE,
            "unit": UNIT,
            "candidate": CANDIDATE,
            "target": TARGET,
            "canonical_driver": "source/EGA_FR.tex; EGA II driver rows83-87",
            "translation_admission": TRANSLATION_CONTROL,
            "source_queries": (
                "Canonical line1572 uses S_{n-mk} with m unquantified; Korean retains that formula exactly. "
                "The source query remains referred and nonblocking under AGKO-H159."
            ),
            "later_ega": (
                "EGA III candidate-ready by direct report; no source-completion or translation inference "
                "until its exact authority packet passes after EGA II and FGA"
            ),
            "validation_checkpoint": QA_CONTROL["path"],
        },
    )
    write_json(
        evidence / "PROGRAM_AUTHORITY.json",
        {
            "schema": "ag-ko-program-authority-public-v3",
            "updated": UPDATED,
            "canonical_source": "[CANONICAL_SOURCE_ROOT]/source/ega2/ega2-1-fr.tex",
            "canonical_source_bytes": 820505,
            "canonical_source_sha256": SOURCE["whole_sha256"],
            "scope": COVERAGE,
            "current_bindings": {
                "canonical_prefix": SOURCE,
                "translated_unit": UNIT,
                "translation_candidate": CANDIDATE,
                "korean_target": TARGET,
                "cumulative_manifest": MANIFEST,
                "reader": PDF,
            },
            "sequence": SEQUENCE,
            "terminology": (
                "French authority controls meaning; Korean professional usage and the hash-bound Stacks "
                "ko-KR export are non-overriding evidence. Preserve finite-type/finite-generation "
                "distinctions and EGA 준스킴."
            ),
            "publication": {
                "status": "R37_LOCAL_BUILD_AND_PDF_QA_PASS; PACKAGE_PORTABLE_AND_PUBLICATION_PENDING",
                "candidate_exact_doi": EXACT_DOI,
                "record_id": 22315714,
                "concept_doi": CONCEPT_DOI,
                "prior_public_doi": "10.5281/zenodo.22217711",
                "github": GITHUB,
                "active_destinations": ["Zenodo", "GitHub"],
            },
        },
    )
    write_json(
        evidence / "DATACITE_RELATIONS.json",
        {
            "schema_version": 2,
            "version": VERSION,
            "release_state": "reserved_unpublished_local_build_and_pdf_qa_pass_package_and_portable_pending",
            "concept_doi": CONCEPT_DOI,
            "exact_version_doi": EXACT_DOI,
            "record_id": 22315714,
            "previous_exact_version_doi": "10.5281/zenodo.22217711",
            "global_ega_concept_doi": "10.5281/zenodo.20414353",
            "relation_policy": (
                "isVersionOf the existing Korean EGA concept DOI; isNewVersionOf the prior Korean EGA "
                "exact release; isPartOf the global EGA concept; no other corpus or language lineage is reused"
            ),
            "publication_status": (
                "No public R37 claim until deterministic packaging, portable replay, publication and "
                "anonymous metadata/DOI/download replay receipts exist"
            ),
        },
    )


def refresh_private(private: Path) -> None:
    cursor = {
        "schema": "ag-ko-cursor-v3",
        "updated": UPDATED,
        "corpus": "EGA",
        "volume": "II",
        "completed_through": COVERAGE,
        "source": SOURCE,
        "unit": UNIT,
        "candidate": CANDIDATE,
        "target": {
            "private": "ega/II/c2s1.tex",
            **{key: value for key, value in TARGET.items() if key != "path"},
            "public_mirror": "pub/ega-ko/source/c2s1.tex",
            "mirrors_exact": True,
        },
        "next": (
            "Freeze and verify the R37 package, replay its portable build, publish to the existing GitHub "
            "and Zenodo lineages, anonymously replay every public byte, then translate the natural unit "
            "beginning at canonical line1607 / environment2.1.10."
        ),
        "last_public_checkpoint": (
            "r36 / exact DOI10.5281/zenodo.22217711 / GitHub release "
            "ega-ko-2026-09-05-r36; dual anonymous byte replay PASS"
        ),
        "candidate_reader": PDF,
        "candidate_exact_doi": EXACT_DOI,
        "candidate_record_id": 22315714,
        "local_status": "PASS_TRANSLATION_BUILD_AND_PDF_QA; PACKAGE_PORTABLE_AND_PUBLICATION_PENDING",
        "sequence": SEQUENCE,
        "ega_iii_plus_source_readiness": (
            "EGA III is candidate-ready by direct report and not a waiting blocker, but exact authority "
            "admission occurs only after EGA II and FGA; stop before the first later incomplete volume."
        ),
        "terminology": (
            "Use exact French sense, Korean professional usage and non-overriding Stacks ko-KR evidence; "
            "finite type=유한형, finite generation=유한 생성, prescheme=준스킴, Noetherian=뇌터."
        ),
        "source_caveat": (
            "Canonical line1572 S_{n-mk} is preserved exactly; its unquantified m remains a delivered, "
            "nonblocking source query under AGKO-H159."
        ),
        "correction_route": (
            "All possible source-correction candidates go to task01a047ab-fc94-7120-af1d-5701ba37aacd; "
            "lines1542,1572,1581,1587 were delivered."
        ),
        "public_links": {
            "concept_doi": "https://doi.org/10.5281/zenodo.21921513",
            "github": GITHUB,
        },
        "policy": (
            "Advance contiguously once; do not reopen unchanged completed units; no human-dependent hold; "
            "publish worthwhile validated cumulative updates through the two named active destinations and "
            "anonymously replay them."
        ),
    }
    write_json(private / "cursor.json", cursor)

    authority_path = private / "authority.json"
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    authority["schema"] = "ag-ko-authority-v3"
    authority["updated"] = UPDATED
    authority["ega_i"]["status"] = "complete in Korean and sealed as the cumulative base"
    authority["ega_ii"]["status"] = (
        "canonical five-input packet present; Korean front/programme complete; main input admitted "
        "contiguously through lines1-1605 /2.1.9; translation next at line1607"
    )
    authority["ega_ii"]["admitted"] = [
        authority["ega_ii"]["admitted"][0],
        {
            "source": "source/ega2/ega2-1-fr.tex lines1-1605",
            "source_slice_bytes": SOURCE["admitted_bytes"],
            "source_slice_sha256": SOURCE["admitted_sha256"],
            "target": "ega/II/c2s1.tex",
            "bytes": TARGET["bytes"],
            "sha256": TARGET["sha256"],
            "source_policy": (
                "French diplomatic; accepted canonical dispositions and explicit translator notes only at "
                "proven substantive loci; line1572 formula retained pending nonblocking source adjudication"
            ),
        },
    ]
    authority["ega_ii"]["next"] = "source/ega2/ega2-1-fr.tex line1607, environment2.1.10"
    authority["publication_lineage"] = {
        "zenodo_concept_doi": CONCEPT_DOI,
        "candidate_exact_doi": EXACT_DOI,
        "prior_public_exact_doi": "10.5281/zenodo.22217711",
        "github": GITHUB,
        "active_destinations": ["Zenodo", "GitHub"],
        "status": "R37_LOCAL_BUILD_AND_PDF_QA_PASS_PACKAGE_PORTABLE_AND_PUBLICATION_PENDING",
    }
    write_json(authority_path, authority)

    state_path = private / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["updated"] = UPDATED
    state["completed"]["latest_public_reader"] = (
        "r36:237pages/1474518B/5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D"
    )
    state["completed"]["latest_public_scope"] = (
        "r36 public through EGA II2.1.7 / canonical lines1-1535; R37 local through2.1.9 / lines1-1605"
    )
    state["completed"]["qa"] = (
        "PASS_PUBLIC_R36: deterministic package and portable replay plus Zenodo/GitHub anonymous byte replay"
    )
    state["completed"]["zenodo"] = (
        "PASS_PUBLIC_R36: exact22217711/concept21921513/open; anonymous DOI/metadata/four-file replay exact; "
        "receipt-r36.json2891/9B1CB569F9DEA287F5C2E1247C93964AE0367906C315F1937150CD0B3B6AF833"
    )
    state["completed"]["github"] = (
        "PASS_PUBLIC_R36: main3f3a1c3971df6ca4002492ded42d5af4c360c3e4; "
        "release ega-ko-2026-09-05-r36; four assets anonymous-byte exact; "
        "github-receipt-r36.json2202/F99A294FBE3581F31372EA467B1890D65E163F1362E2D48F06A959F88B7193C8"
    )
    receipts = state["completed"].setdefault("receipts", [])
    for receipt in (
        "pub/ega-ko/receipt-r36.json",
        "pub/ega-ko/github-receipt-r36.json",
        "pub/ega-ko/release/2026-09-05-r36/PACKAGE_RECEIPT.json",
        "pub/ega-ko/release/2026-09-05-r36/PORTABLE_BUILD_REPLAY.json",
        "controls/R37_ZENODO_DRAFT.json",
        "controls/R37_TRANSLATION_ADMISSION.json",
        "controls/R37_PDF_QA.json",
    ):
        if receipt not in receipts:
            receipts.append(receipt)
    state["public_r36"] = {
        "reader": (
            "pub/ega-ko/release/2026-09-05-r36/00_EGA_ko_CUMULATIVE_READER.pdf"
            "237pages/1474518B/5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D"
        ),
        "coverage": "Complete Korean EGA0_I and EGA I; complete EGA II programme; EGA II main1-1535 through2.1.7;226 historical markers; EGA II incomplete.",
        "exact_doi": "10.5281/zenodo.22217711",
        "zenodo_status": "PASS public open record and anonymous four-file replay",
        "github_status": "PASS main3f3a1c3971df6ca4002492ded42d5af4c360c3e4 and release ega-ko-2026-09-05-r36; anonymous four-asset replay",
    }
    if "candidate_r36" in state:
        state["candidate_r36"] = {
            "status": "PROMOTED_TO_PUBLIC_R36_DUAL_ANONYMOUS_REPLAY_PASS",
            "record_id": 22217711,
            "exact_doi": "10.5281/zenodo.22217711",
            "reader": {
                "pages": 237,
                "bytes": 1474518,
                "sha256": "5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D",
            },
        }
    state["active"] = {
        "corpus": "EGA",
        "volume": "EGA II",
        "admitted": (
            "front/programme complete plus main lines1-1605 through2.1.9; "
            "prefix73897/0815285B46DA35D916612CDDACB92A1DD646153FAF6AC0D15E03417F9D349182"
        ),
        "unit": UNIT,
        "candidate": CANDIDATE,
        "target": (
            "ega/II/c2s1.tex and public mirror75622/"
            "FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383"
        ),
        "reader": PDF,
        "qa": QA,
        "next_source": "source/ega2/ega2-1-fr.tex line1607; environment2.1.10",
        "next_target": (
            "Freeze/package and portable-replay R37, publish and anonymously replay it, then translate "
            "from line1607 without reopening sealed bytes"
        ),
        "gate": (
            "Preserve exact formulas, labels, references, environments and oldpage markers; route all "
            "possible French corrections; SGA remains outside the active task."
        ),
    }
    state["candidate_r37"] = {
        "status": "PASS_LOCAL_TRANSLATION_BUILD_AND_PDF_QA_PACKAGE_PORTABLE_PUBLICATION_PENDING",
        "record_id": 22315714,
        "exact_doi": EXACT_DOI,
        "source": SOURCE,
        "unit": UNIT,
        "candidate": CANDIDATE,
        "target": TARGET,
        "reader": PDF,
        "translation_admission": TRANSLATION_CONTROL,
        "build": BUILD,
        "pdf_qa": QA_CONTROL,
        "next": "deterministic package, portable replay, same-lineage publication and anonymous readback",
    }
    state["later_ega"] = (
        "EGA III candidate-ready by direct report, sequenced after EGA II and FGA; exact source completion "
        "must be admitted before translation, and translation stops before the first incomplete later volume."
    )
    state["next_executable_action"] = (
        "Freeze and verify the R37 package, run its portable replay, publish it to the existing GitHub and "
        "Zenodo lineages with anonymous replay, then translate canonical line1607 onward."
    )
    state["continuation_audit"] = {
        "classification": "progress",
        "current_progress": (
            "R37 translation, exact source/formula validation, two clean four-pass cycles, full extraction, "
            "navigation/font checks and six-page rendered QA PASS; package, portable replay and publication next."
        ),
    }
    write_json(state_path, state)


def append_hardened(private: Path, repo: Path) -> None:
    section = """

## 62. 2026-09-05 R37 local admission and controlling continuation

This section supersedes earlier current-cursor prose without rewriting any historical receipt. The finite order remains EGA I (complete), EGA II (active), then FGA. Only after EGA II and FGA are complete may the exact source-accuracy gate admit the contiguous later-EGA sequence beginning with EGA III; stop before the first incomplete volume. SGA is outside this task. Active preservation uses only the existing Korean EGA Zenodo concept `10.5281/zenodo.21921513` and GitHub repository `https://github.com/KokunoYumeto/ega-ko`.

R37 admits canonical lines 1537--1605, 3,776 LF UTF-8 bytes / 3,727 characters / `D91203350D0012E008CA3A778DD5ABB1E3A18D70641C753F6F86ECFF51F949FE`, bringing the contiguous prefix through 2.1.9 to 73,897 bytes / `0815285B46DA35D916612CDDACB92A1DD646153FAF6AC0D15E03417F9D349182`. The translation candidate is 4,073 bytes / `A423B075B3483FC84CA580AED46C651F84543F4444805D94388CD5574114063D`; the private target and public mirror are each 75,622 bytes / `FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383`. Environment 2.1.8 and Proposition 2.1.9 with all three conditions and proof are complete. Canonical line 1572 uses `S_{n-mk}` with an unquantified `m`; the Korean target preserves that formula exactly, introduces no guessed repair, and keeps the already delivered source query nonblocking under `AGKO-H159`.

The cumulative reader is 238 pages / 1,479,200 bytes / `22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61`. Two clean four-pass XeLaTeX cycles held `Global\\InterlanguageTeXSlotV1`; pass 3 equals pass 4 within each cycle and both cycle finals are byte-identical. Poppler and pypdf each extract 152,023 Hangul syllables with no replacement character; all 1,653 internal links and 577 named destinations resolve; pages 1, 2, 6 and 236--238 pass 200 dpi visual inspection. The exact controls are `R37_TRANSLATION_ADMISSION.json` (5,919 bytes / `C4EBA3CA0F94A04815BE6585907D0EFB20A63F999710334F758078626D8A89C4`), `BUILD_RECEIPT.json` (5,462 bytes / `5864BCD80AA33AEB906034A1E07F3BDC8710D699588A448D95ACCBBEC49B84A4`) and `R37_PDF_QA.json` (13,472 bytes / `E3CB3AC1D47F4041ADECDA7942383EF0CA52B921E4AF5F9B97A1FF7EFBA1ACDD`). These establish local translation, build and PDF QA only.

The same-lineage exact DOI `10.5281/zenodo.22315714` is reserved but unpublished. Deterministic packaging, archive verification, portable replay, publication and anonymous public-byte readback remain pending and must not be inferred from the local QA. R36 / exact DOI `10.5281/zenodo.22217711` and GitHub release `ega-ko-2026-09-05-r36` are the prior public checkpoint; both repositories passed anonymous byte replay. After R37 public closure, continue at canonical line 1607, environment 2.1.10; line 1606 is blank.
"""
    for path in (private / "HARDENED.md", repo / "evidence" / "HARDENED.md"):
        text = path.read_text(encoding="utf-8")
        marker = "## 62. 2026-09-05 R37 local admission and controlling continuation"
        if marker in text:
            if text.count(marker) != 1:
                raise RuntimeError(f"duplicate R37 hardening section in {path}")
            continue
        path.write_text(text.rstrip() + section, encoding="utf-8", newline="\n")


def append_ledgers(repo: Path) -> None:
    evidence = repo / "evidence"
    decision = {
        "id": "AGKO-D185",
        "time": UPDATED,
        "precision": "second",
        "kind": "r37_source_bounded_admission_build_and_pdf_qa_gate",
        "scope": "EGA II environment2.1.8 and Proposition2.1.9 with proof; canonical lines1537-1605",
        "authority": (
            "Canonical unit3776 LF bytes /3727 characters /D91203350D0012E008CA3A778DD5ABB1E3A18D70641C753F6F86ECFF51F949FE; "
            "admitted prefix1-1605 73897 bytes /0815285B46DA35D916612CDDACB92A1DD646153FAF6AC0D15E03417F9D349182; "
            "sealed R36 target71548 bytes /24274A13350C1D2724F02EB1591CABD5774A9B57A5833108E94F307A2E4869D3"
        ),
        "choice": (
            "Admit the complete natural unit through Proposition2.1.9; preserve all three graded-prime-ideal "
            "conditions, existence/uniqueness construction, direct-sum and quotient gradings, proof quantifiers, "
            "oldpageII23 and exact S_{n-mk}. Accept the cumulative reader only after two clean four-pass fixed-point "
            "cycles, dual extraction, complete destination/font checks and selected-page visual QA. Record the "
            "reserved same-lineage DOI without claiming packaging, portable replay or publication."
        ),
        "alternatives": [
            "Silently replace the unquantified-m formula with a guessed n-k or n-rk reading",
            "Treat the source query as a translation hold",
            "Claim release readiness before deterministic archive and portable replay",
            "Treat the reserved DOI as a public record",
        ],
        "rejected": (
            "Those alternatives falsify diplomatic source binding, create a forbidden non-operational hold, "
            "skip deterministic release gates or misstate public availability."
        ),
        "evidence": [
            "evidence/controls/R37_TRANSLATION_ADMISSION.json 5919 bytes /C4EBA3CA0F94A04815BE6585907D0EFB20A63F999710334F758078626D8A89C4",
            "candidate4073 bytes /A423B075B3483FC84CA580AED46C651F84543F4444805D94388CD5574114063D; integrated private/public75622 bytes /FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383",
            "evidence/BUILD_RECEIPT.json 5462 bytes /5864BCD80AA33AEB906034A1E07F3BDC8710D699588A448D95ACCBBEC49B84A4",
            "evidence/controls/R37_PDF_QA.json 13472 bytes /E3CB3AC1D47F4041ADECDA7942383EF0CA52B921E4AF5F9B97A1FF7EFBA1ACDD",
            "reader238 pages /1479200 bytes /22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61",
            "AGKO-H159 and AGKO-H160",
        ],
        "uncertainty": (
            "Canonical line1572 remains an unadjudicated source-clarity query; exact diplomatic preservation "
            "makes it nonblocking and reversible. No local translation, build, extraction, navigation, font or "
            "selected-render defect is known. Archive portability and public-byte identity remain untested."
        ),
        "consequence": (
            "The Korean EGA source is contiguous through canonical line1605 /2.1.9, with a locally accepted "
            "238-page cumulative reader. R37 packaging, portable replay and same-lineage publication remain pending."
        ),
        "review": "PASS_LOCAL_TRANSLATION_BUILD_AND_PDF_QA",
        "next": (
            "Freeze and verify deterministic R37 archives, run portable replay, publish to the existing Zenodo "
            "and GitHub lineages with anonymous byte readback, then resume canonical line1607 / environment2.1.10."
        ),
    }
    build_evidence = {
        "id": "AGKO-E-R37-BUILD-QA-20260905",
        "time": UPDATED,
        "precision": "second",
        "kind": "r37_translation_cumulative_build_and_pdf_qa",
        "coverage": COVERAGE,
        "source": {
            "unit": UNIT,
            "prefix": SOURCE,
        },
        "target": {
            "candidate": CANDIDATE,
            "integrated": TARGET,
            "private_public_exact": True,
        },
        "translation_admission": TRANSLATION_CONTROL,
        "reader": PDF,
        "build": {
            **BUILD,
            "cycles": 2,
            "passes_per_cycle": 4,
            "pass3_pass4_identical_each": True,
            "cycle_finals_identical": True,
            "mutex": "Global\\InterlanguageTeXSlotV1",
        },
        "qa": {
            "control": QA_CONTROL,
            "historical_markers": 227,
            "hangul_each_extractor": 152023,
            "replacement_characters_each": 0,
            "internal_links": 1653,
            "named_destinations": 577,
            "invalid_destinations": 0,
            "selected_visual_pages": [1, 2, 6, 236, 237, 238],
            "visual": "PASS",
        },
        "draft": {
            "control": DRAFT_CONTROL,
            "record_id": 22315714,
            "exact_doi": EXACT_DOI,
            "concept_doi": CONCEPT_DOI,
            "status": "reserved_unpublished",
        },
        "prior_public": {
            "version": "2026-09-05-r36",
            "exact_doi": "10.5281/zenodo.22217711",
            "github_release": "ega-ko-2026-09-05-r36",
            "anonymous_zenodo_replay": "PASS",
            "anonymous_github_replay": "PASS",
        },
        "result": "PASS_LOCAL_TRANSLATION_BUILD_AND_PDF_QA_PACKAGE_PORTABLE_PUBLICATION_PENDING",
        "next": "Deterministic package and portable replay, then same-lineage publication and anonymous readback.",
    }
    hard = {
        "id": "AGKO-H160",
        "time": UPDATED,
        "precision": "second",
        "status": "controlling_r37_local_gate_and_diplomatic_source_caveat",
        "scope": "EGA II R37 canonical lines1537-1605 through Proposition2.1.9",
        "locator": (
            "canonical source/ega2/ega2-1-fr.tex line1572; Korean candidate/integrated target; "
            "controls/R37_TRANSLATION_ADMISSION.json and R37_PDF_QA.json"
        ),
        "symptom": (
            "The printed formula uses S_{n-mk} with m unquantified. R37 is locally translation/build/PDF-QA "
            "complete, while package, portable replay and public preservation are not yet complete."
        ),
        "cause_evidence": (
            "AGKO-H159 already records and routes the source query. The R37 validator proves exact diplomatic "
            "formula preservation and absence of guessed n-k/n-rk substitutions. The 238-page reader and QA "
            "control prove local rendering/extraction only; the same-lineage exact DOI is reserved_unpublished."
        ),
        "resolution": (
            "Keep AGKO-H159 as the sole unresolved source-query row; do not duplicate it. Bind R37 to the exact "
            "printed formula, keep the query nonblocking, and state the release phase exactly as local build/PDF "
            "QA pass with package, portable replay and publication pending."
        ),
        "tests": (
            "Translation control5919/C4EBA3CA0F94A04815BE6585907D0EFB20A63F999710334F758078626D8A89C4; "
            "build receipt5462/5864BCD80AA33AEB906034A1E07F3BDC8710D699588A448D95ACCBBEC49B84A4; "
            "PDF QA13472/E3CB3AC1D47F4041ADECDA7942383EF0CA52B921E4AF5F9B97A1FF7EFBA1ACDD; "
            "reader1479200/22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61."
        ),
        "residual_risk": (
            "A later canonical adjudication may refine the source reading and require a bounded rebase. "
            "No package reproducibility, portable-build identity or public-byte identity is claimed yet."
        ),
        "recurrence": (
            "At every cursor refresh, distinguish local mathematical/build QA from frozen-package, portable and "
            "public gates; never duplicate an existing unresolved source item merely because the translated unit advances."
        ),
        "related": [
            "AGKO-H159",
            "AGKO-D185",
            "AGKO-E-R37-BUILD-QA-20260905",
            "AGKO-EGA2-S1-R37-COVERAGE",
        ],
    }
    append_jsonl(evidence / "decisions.jsonl", decision)
    append_jsonl(evidence / "evidence.jsonl", build_evidence)
    append_jsonl(evidence / "hard.jsonl", hard)


def verify_existing_index_and_unresolved(repo: Path) -> None:
    evidence = repo / "evidence"
    units = read_jsonl(evidence / "index" / "units.jsonl")
    matches = [item for item in units if item.get("id") == "AGKO-EGA2-S1-R37-COVERAGE"]
    if len(matches) != 1:
        raise RuntimeError(f"expected one R37 unit-index record, found {len(matches)}")
    unit = matches[0]
    if (
        unit.get("authority", {}).get("bytes") != SOURCE["admitted_bytes"]
        or unit.get("authority", {}).get("sha256") != SOURCE["admitted_sha256"]
        or unit.get("target", {}).get("bytes") != TARGET["bytes"]
        or unit.get("target", {}).get("sha256") != TARGET["sha256"]
        or unit.get("target", {}).get("appended_bytes") != CANDIDATE["bytes"]
        or unit.get("target", {}).get("appended_sha256") != CANDIDATE["sha256"]
    ):
        raise RuntimeError("R37 unit-index bindings do not match the exact admitted state")

    unresolved_path = evidence / "UNRESOLVED_ITEMS.tsv"
    rows = unresolved_path.read_text(encoding="utf-8").splitlines()
    matches = [row for row in rows if row.startswith("AGKO-H159\t")]
    if len(matches) != 1 or "1572" not in matches[0] or "open_nonblocking" not in matches[0]:
        raise RuntimeError("line1572 must remain represented once as the nonblocking AGKO-H159 item")


def verify_alias_vocabulary(private: Path, repo: Path) -> None:
    aliases = [
        repo / "evidence" / name
        for name in (
            "CURSOR.json",
            "PROGRAM_CURSOR.json",
            "PROGRAM_STATE.json",
            "STATE.json",
            "QA_STATE.json",
            "VISUAL_QA.json",
            "SOURCE_AUTHORITY.json",
            "PROGRAM_AUTHORITY.json",
            "DATACITE_RELATIONS.json",
        )
    ] + [private / name for name in ("cursor.json", "authority.json", "state.json")]
    blocked = ("Fig" + "share", "T" + "TP", "Translation and Transcription " + "Project")
    for path in aliases:
        text = path.read_text(encoding="utf-8")
        json.loads(text)
        for token in blocked:
            if token in text:
                raise RuntimeError(f"blocked current-alias token in {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    private = args.private_root.resolve()
    repo = args.repo.resolve()
    verify_inputs(private, repo)
    verify_existing_index_and_unresolved(repo)
    refresh_public(repo)
    refresh_private(private)
    append_hardened(private, repo)
    append_ledgers(repo)
    verify_alias_vocabulary(private, repo)
    print("PASS_R37_PRIVATE_PUBLIC_STATE_AND_LEDGER_REFRESH")


if __name__ == "__main__":
    main()
