#!/usr/bin/env python3
"""Refresh live private/public task-state aliases to the admitted R36 cursor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


UPDATED = "2026-09-05T04:25:00+02:00"
PDF = {
    "path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf",
    "pages": 237,
    "bytes": 1474518,
    "sha256": "5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D",
}
MANIFEST = {
    "path": "source/CUMULATIVE_INPUTS.json",
    "bytes": 16262,
    "sha256": "C2004B6109417CAE7F8B53513C12C78CF9C23D99BEFD2A8AEDE3F83AAC36196C",
    "ordered_inputs": 17,
    "canonical_rows": 23,
    "complete": 16,
    "partial": 1,
    "not_translated": 6,
    "historical_markers": 226,
}
SOURCE = {
    "path": "source/ega2/ega2-1-fr.tex",
    "whole_bytes": 820505,
    "whole_sha256": "84EDBE3E83530AF2959B441796337C9DC21EAFCA6A13114A26778760FBF437AC",
    "admitted_lines": "1-1535",
    "admitted_bytes": 70120,
    "admitted_sha256": "ED3DC79E9408C4D5325D24F3FF1CB06548611C5C8BD79CC67348402D9A0C0D91",
}
TARGET = {
    "path": "source/c2s1.tex",
    "bytes": 71548,
    "sha256": "24274A13350C1D2724F02EB1591CABD5774A9B57A5833108E94F307A2E4869D3",
    "lf_lines": 1554,
}
COVERAGE = "EGA 0_I and EGA I complete; EGA II Chapter II programme/table of contents complete; EGA II main text contiguous through2.1.7 at canonical lines1-1535. Full EGA II and the EGA corpus remain incomplete."
QA = {
    "translation": "PASS exact R36 source/candidate/integrated-mirror validation; all six Lemma2.1.6 assertions, formulas, labels, references, environments and II22 preserved; threshold discrepancy disclosed rather than silently normalized",
    "build": "PASS two independent four-pass XeLaTeX cycles under Global\\InterlanguageTeXSlotV1; pass3=pass4 within each cycle and final cycles byte-identical; hard diagnostics0",
    "extraction": {
        "poppler": {"path": "evidence/extract.txt", "bytes": 721726, "sha256": "909937C7A40D31DA9787C01812DCB46C8CC40DACF3D5C1F69BD5099959277E46"},
        "pypdf": {"path": "evidence/extract-pypdf.txt", "bytes": 696608, "sha256": "D56B3623A698A1E5283DB33BD7B59EDF59D2ECAAD698950420BB0A35136B81B8"},
        "each_hangul": 151372,
        "each_replacement_characters": 0,
        "historical_markers": "pypdf full226-entry sequence PASS; Poppler ordered225-marker sequence PASS with inherited bare page70 token documented",
    },
    "links": {"annotations": 1656, "internal": 1652, "resolved_internal": 1652, "external_uris": 4, "named_destinations": 574, "bookmarks": 132, "result": "PASS"},
    "fonts": "PASS all35 resources embedded; all Hangul Type0 resources have ToUnicode; eight inherited Type1 math/diagram resources without ToUnicode are explicitly limited",
    "visual": "PASS selected pages1,2,6,233-237 at200dpi; no clipping, overlap, tofu or malformed formula",
    "portable": "PASS eight-pass replay from the frozen archive; strict/portable Poppler and pypdf bytes exact and pages1,236,237 raster bytes exact. Five-byte PDF-container delta remains unadjudicated.",
    "detailed_control": "evidence/controls/R36_PDF_QA.json",
    "human_certification": "not claimed or required",
}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def public_base() -> dict[str, Any]:
    return {
        "schema_version": 4,
        "version": "2026-09-05-r36",
        "updated": UPDATED,
        "snapshot_phase": "local_qa_and_portable_replay_ready_for_publication",
        "coverage": COVERAGE,
        "reader": PDF,
        "coverage_manifest": MANIFEST,
        "exact_doi": "10.5281/zenodo.22217711",
        "concept_doi": "10.5281/zenodo.21921513",
        "prior_public_checkpoint": "r34 / 10.5281/zenodo.22209381; Zenodo and GitHub anonymous byte replay PASS",
        "next_source": "EGA II source/ega2/ega2-1-fr.tex line1537, environment2.1.8; line1536 blank",
        "publication_evidence_rule": "This alias records the locally accepted R36 bytes before publication. Deterministic archive and portable replay evidence is under release/2026-09-05-r36; public status requires separate GitHub/Zenodo receipts and anonymous byte readback.",
    }


def refresh_public(repo: Path) -> None:
    evidence = repo / "evidence"
    base = public_base()
    cursor = {
        **base,
        "source": SOURCE,
        "target": TARGET,
        "sequence": "Finish EGA II, then FGA. Only afterward admit the contiguous source-accurate EGA sequence beginning with EGA III; stop before the first incomplete volume. SGA is outside active scope.",
        "validation_checkpoint": "evidence/controls/R36_PDF_QA.json",
    }
    write_json(evidence / "CURSOR.json", cursor)
    write_json(evidence / "PROGRAM_CURSOR.json", {**cursor, "active_volume": "EGA II", "later_ega": "EGA III is candidate-ready by direct report but remains sequenced after EGA II and FGA; exact authority admission is required before translation."})
    state = {
        **base,
        "sequence": ["EGA I complete", "EGA II active and incomplete", "FGA next", "EGA III+ only after ordered predecessors and exact source admission"],
        "sga": "outside active scope; coordinate separately later",
        "qa": QA,
        "source": SOURCE,
        "target": TARGET,
        "translation_admission": "evidence/controls/R36_TRANSLATION_ADMISSION.json",
        "build_receipt": "evidence/BUILD_RECEIPT.json",
        "validation_checkpoint": "evidence/controls/R36_PDF_QA.json",
        "rights": "Per-work rights, provenance, author/source relationship and non-endorsement retained; no blanket public-domain or open-licence claim",
    }
    write_json(evidence / "STATE.json", state)
    write_json(evidence / "PROGRAM_STATE.json", state)
    write_json(evidence / "QA_STATE.json", {**base, "qa": QA, "source": SOURCE, "target": TARGET, "result": "PASS_LOCAL_QA_AND_PORTABLE_REPLAY; publication receipts remain separate subsequent evidence", "validation_checkpoint": "evidence/controls/R36_PDF_QA.json"})
    write_json(
        evidence / "VISUAL_QA.json",
        {
            **base,
            "dpi": 200,
            "pages": [1, 2, 6, 233, 234, 235, 236, 237],
            "dimensions": "1654x2339",
            "result": "PASS on eight inspected pages: no clipping, overlap, tofu or malformed formula; R36 corollaries, six-part lemma, proof and threshold note are readable",
            "detailed_render_identities": "evidence/controls/R36_PDF_QA.json",
            "historical_markers": {"EGA_I_introduction": "5-8 /4", "EGA_0_I": "11-78 /68", "EGA_I_Chapter_I": "79-214 /136", "EGA_II": "5-22 /18", "total": 226},
            "links": QA["links"],
            "validation_checkpoint": "evidence/controls/R36_PDF_QA.json",
        },
    )
    write_json(
        evidence / "SOURCE_AUTHORITY.json",
        {
            **base,
            "source": SOURCE,
            "target": TARGET,
            "canonical_driver": "source/EGA_FR.tex; EGA II driver rows83-87",
            "translation_admission": "evidence/controls/R36_TRANSLATION_ADMISSION.json",
            "new_unit": "canonical1449-1535 /4096 LF bytes /F9AE6849245F4B23482B75B8CD8A4FC0999717A2A1DFB49B160C5EF9F58D07E3",
            "source_queries": "Lemma2.1.6 threshold mismatch is preserved and referred; next-unit syntax/clarity candidates at lines1542,1572,1581,1587 are referred without mutating French authority",
            "later_ega": "EGA III candidate-ready by direct report; no source-completion or translation inference until its exact authority packet passes after EGA II and FGA",
            "validation_checkpoint": "evidence/controls/R36_PDF_QA.json",
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
            "current_bindings": {"canonical_prefix": SOURCE, "korean_target": TARGET, "cumulative_manifest": MANIFEST, "reader": PDF},
            "sequence": "EGA I then EGA II then FGA; later EGA begins with EGA III only after the sequence and exact source validation; SGA is separate and inactive",
            "terminology": "French authority controls meaning; Korean professional usage and the hash-bound Stacks ko-KR export are non-overriding evidence. Preserve finite-type/finite-generation distinctions and EGA 준스킴.",
            "publication": {"status": "R36_LOCAL_PACKAGE_AND_PORTABLE_REPLAY_PASS; PUBLICATION_PENDING", "candidate_exact_doi": "10.5281/zenodo.22217711", "record_id": 22217711, "concept_doi": "10.5281/zenodo.21921513", "prior_public_doi": "10.5281/zenodo.22209381", "github": "https://github.com/KokunoYumeto/ega-ko", "active_destinations": ["Zenodo", "GitHub"]},
        },
    )
    write_json(
        evidence / "DATACITE_RELATIONS.json",
        {
            "schema_version": 2,
            "version": "2026-09-05-r36",
            "release_state": "local_package_and_portable_replay_pass_publication_pending",
            "concept_doi": "10.5281/zenodo.21921513",
            "exact_version_doi": "10.5281/zenodo.22217711",
            "record_id": 22217711,
            "previous_exact_version_doi": "10.5281/zenodo.22209381",
            "global_ega_concept_doi": "10.5281/zenodo.20414353",
            "relation_policy": "isVersionOf the existing Korean EGA concept DOI; isNewVersionOf the prior Korean EGA exact release; isPartOf the global EGA concept; no other corpus or language lineage is reused",
            "publication_status": "No public r36 claim until the transaction and anonymous metadata/DOI/download replay receipts exist",
        },
    )


def refresh_private(private: Path, repo: Path) -> None:
    cursor = {
        "schema": "ag-ko-cursor-v3",
        "updated": UPDATED,
        "corpus": "EGA",
        "volume": "II",
        "completed_through": COVERAGE,
        "source": SOURCE,
        "target": {"private": "ega/II/c2s1.tex", **{k: v for k, v in TARGET.items() if k != "path"}, "public_mirror": "pub/ega-ko/source/c2s1.tex", "mirrors_exact": True},
        "next": "Publish the already frozen and portable-replayed R36 checkpoint to its existing GitHub and Zenodo lineages, anonymously replay every public byte, then translate the natural canonical unit lines1537-1605 through Proposition2.1.9.",
        "last_public_checkpoint": "r34 / exact DOI10.5281/zenodo.22209381 / GitHub release ega-ko-2026-08-31-r34; anonymous replay PASS",
        "candidate_reader": PDF,
        "candidate_exact_doi": "10.5281/zenodo.22217711",
        "sequence": "EGA II, then FGA, then the contiguous source-accurate EGA sequence beginning with EGA III; SGA inactive",
        "ega_iii_plus_source_readiness": "EGA III is candidate-ready by direct report and not a waiting blocker, but exact authority admission occurs only after EGA II and FGA; stop before the first later incomplete volume.",
        "terminology": "Use exact French sense, Korean professional usage and non-overriding Stacks ko-KR evidence; finite type=유한형, finite generation=유한 생성, prescheme=준스킴, Noetherian=뇌터.",
        "correction_route": "All possible source-correction candidates go to task01a047ab-fc94-7120-af1d-5701ba37aacd; lines1542,1572,1581,1587 were delivered.",
        "public_links": {"concept_doi": "https://doi.org/10.5281/zenodo.21921513", "github": "https://github.com/KokunoYumeto/ega-ko"},
        "policy": "Advance contiguously once; do not reopen unchanged completed units; no human-dependent hold; publish worthwhile validated cumulative updates through the two named active destinations and anonymously replay them.",
    }
    write_json(private / "cursor.json", cursor)

    authority_path = private / "authority.json"
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    authority["schema"] = "ag-ko-authority-v3"
    authority["updated"] = UPDATED
    authority["ega_i"]["status"] = "complete in Korean and sealed as the cumulative base"
    authority["ega_ii"]["status"] = "canonical five-input packet present; Korean front/programme complete; main input admitted contiguously through lines1-1535 /2.1.7; translation active at line1537"
    authority["ega_ii"]["admitted"] = [
        authority["ega_ii"]["admitted"][0],
        {"source": "source/ega2/ega2-1-fr.tex lines1-1535", "source_slice_bytes": 70120, "source_slice_sha256": SOURCE["admitted_sha256"], "target": "ega/II/c2s1.tex", "bytes": 71548, "sha256": TARGET["sha256"], "source_policy": "French diplomatic; accepted canonical dispositions and explicit translator notes only at proven substantive loci"},
    ]
    authority["ega_ii"]["next"] = "source/ega2/ega2-1-fr.tex line1537, environment2.1.8"
    authority["terminology"]["workflow"] = "terminology/arxiv/2026-08-23/WORKFLOW_RECORD.jsonl through AGKO-TERM-E170"
    authority["publication_lineage"] = {"zenodo_concept_doi": "10.5281/zenodo.21921513", "candidate_exact_doi": "10.5281/zenodo.22217711", "prior_public_exact_doi": "10.5281/zenodo.22209381", "github": "https://github.com/KokunoYumeto/ega-ko", "active_destinations": ["Zenodo", "GitHub"], "status": "R36_LOCAL_PACKAGE_AND_PORTABLE_REPLAY_PASS_PUBLICATION_PENDING"}
    write_json(authority_path, authority)

    state_path = private / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["updated"] = UPDATED
    state["completed"]["latest_public_reader"] = "r34 remains the last public checkpoint until r36 transaction closes:235pages/1462350B/EBC2FB3338619430EAB73AC47D25205D21A8645725C7D2452A5624D0982C83C8"
    state["completed"]["latest_public_scope"] = "r34 public: through EGA II2.1.1; R36 local candidate: through2.1.7 / canonical lines1-1535"
    state["active"] = {
        "corpus": "EGA",
        "volume": "EGA II",
        "admitted": "front/programme complete plus main lines1-1535 through2.1.7; prefix70120/ED3DC79E9408C4D5325D24F3FF1CB06548611C5C8BD79CC67348402D9A0C0D91",
        "target": "ega/II/c2s1.tex and public mirror71548/24274A13350C1D2724F02EB1591CABD5774A9B57A5833108E94F307A2E4869D3",
        "reader": PDF,
        "qa": QA,
        "next_source": "source/ega2/ega2-1-fr.tex line1537; natural unit lines1537-1605 through Proposition2.1.9",
        "next_target": "Close r36 GitHub/Zenodo publication and anonymous replay, then translate lines1537-1605 without reopening sealed bytes",
        "gate": "Preserve exact formulas, labels, references, environments and oldpage markers; route all possible French corrections; SGA remains outside the active task.",
    }
    state["candidate_r36"] = {"status": "PASS_LOCAL_PACKAGE_AND_PORTABLE_REPLAY_PUBLICATION_PENDING", "record_id": 22217711, "exact_doi": "10.5281/zenodo.22217711", "source": SOURCE, "target": TARGET, "reader": PDF, "qa": QA, "next": "same-lineage GitHub/Zenodo publication and anonymous readback"}
    state["later_ega"] = "EGA III candidate-ready by direct report, sequenced after EGA II and FGA; exact source completion must be admitted before translation, and translation stops before the first incomplete later volume."
    state["next_executable_action"] = "Publish the validated r36 package to the existing GitHub and Zenodo lineages, anonymously replay it, then translate canonical lines1537-1605."
    state["continuation_audit"] = {"classification": "progress", "current_progress": "R36 translation, four-pass build, full PDF QA, complete540-record expert-review views, deterministic archives, portable extraction/raster replay and source-correction referrals PASS; public transaction next."}
    write_json(state_path, state)

    hard_section = """
\n## 61. 2026-09-05 R36 closure and controlling continuation\n
This section supersedes all earlier current-cursor and publication-workflow prose without rewriting historical receipts. The active finite order is EGA I (complete), EGA II (active), then FGA. Only after EGA II and FGA are complete may the exact source-accuracy gate admit the contiguous later-EGA sequence beginning with EGA III; stop before the first incomplete volume. SGA is outside this task and will be coordinated separately. Active public preservation uses only the existing Korean EGA Zenodo concept `10.5281/zenodo.21921513` and GitHub repository `https://github.com/KokunoYumeto/ega-ko`.\n
R36 admits EGA II canonical lines 1449--1535, 4,096 LF UTF-8 bytes / `F9AE6849245F4B23482B75B8CD8A4FC0999717A2A1DFB49B160C5EF9F58D07E3`, bringing the contiguous prefix to 70,120 bytes / `ED3DC79E9408C4D5325D24F3FF1CB06548611C5C8BD79CC67348402D9A0C0D91`. The Korean target and public mirror are each 71,548 bytes / `24274A13350C1D2724F02EB1591CABD5774A9B57A5833108E94F307A2E4869D3`. Corollaries 2.1.4--2.1.5, Lemma 2.1.6 with all six assertions and proof, and Corollary 2.1.7 are complete. The printed `m>=m_0` statement versus proof-derived `m>m_0` is preserved with the reversible maximum-plus-one translator note and has been referred to the correction task.\n
The cumulative reader is 237 pages / 1,474,518 bytes / `5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D`. Two clean four-pass XeLaTeX cycles held `Global\\InterlanguageTeXSlotV1`; pass 3 equals pass 4 within each cycle and both cycle finals are byte-identical. Poppler and pypdf each extract 151,372 Hangul syllables with no replacement character; all 1,652 internal links and 574 named destinations resolve; pages 1, 2, 6 and 233--237 pass 200 dpi visual inspection. The portable archive replay reproduces both full extractions and pages 1, 236, 237 raster bytes exactly; its five-byte whole-PDF delta is retained as an unadjudicated container-level difference. The complete expert-review views cover 540 source-ledger records and pass independent replay.\n
The next natural source unit is canonical lines 1537--1605, 3,776 LF bytes / 3,727 characters / `D91203350D0012E008CA3A778DD5ABB1E3A18D70641C753F6F86ECFF51F949FE`, ending after Proposition 2.1.9. Possible French corrections at line 1542 and clarity queries at lines 1572, 1581 and 1587 have already been sent to task `01a047ab-fc94-7120-af1d-5701ba37aacd`; they are nonblocking and must not be silently written into the French authority.\n"""
    for path in (private / "HARDENED.md", repo / "evidence" / "HARDENED.md"):
        text = path.read_text(encoding="utf-8")
        if "## 61. 2026-09-05 R36 closure" in text:
            raise RuntimeError(f"R36 hardening section already present: {path}")
        path.write_text(text.rstrip() + hard_section, encoding="utf-8", newline="\n")

    unresolved_rows = [
        "AGKO-H158\tEGA II Lemma2.1.6 statement/proof\tprinted threshold mismatch\tpreserve m>=m_0 statement and m>m_0 proof with maximum-plus-one translator note\tsilently alter either printed locus\thard.jsonl AGKO-H158; controls/R36_CORRECTION_REFERRAL_AUDIT_20260905.json\tno reader defect; source disposition may later refine wording\tresolved_admitted_nonblocking",
        "AGKO-H159\tEGA II next-unit source lines1542,1572,1581,1587\tsyntax and editorial-compression queries\tpreserve French authority and translate intended mathematics transparently\tsilent source normalization\thard.jsonl AGKO-H159; correction task referral\tnext unit remains translatable; canonical adjudication may later rebase exact loci\topen_nonblocking",
    ]
    unresolved = repo / "evidence" / "UNRESOLVED_ITEMS.tsv"
    text = unresolved.read_text(encoding="utf-8").rstrip("\n")
    for row in unresolved_rows:
        if row.split("\t", 1)[0] not in text:
            text += "\n" + row
    unresolved.write_text(text + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    private = args.private_root.resolve()
    repo = args.repo.resolve()
    refresh_public(repo)
    refresh_private(private, repo)
    print("PASS_R36_PRIVATE_AND_PUBLIC_STATE_ALIAS_REFRESH")


if __name__ == "__main__":
    main()
