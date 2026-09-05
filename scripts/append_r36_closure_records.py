#!/usr/bin/env python3
"""Append the hash-bound R36 closure and next-source referral records once."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TIMESTAMP = "2026-09-05T04:10:42+02:00"

HARD = {
    "id": "AGKO-H159",
    "time": TIMESTAMP,
    "precision": "second",
    "status": "open_source_queries_referred_nonblocking",
    "scope": "EGA II next-unit source preparation, canonical lines1537-1605 / environments2.1.8-2.1.9",
    "locator": "canonical source/ega2/ega2-1-fr.tex lines1542,1572,1581 and1587; correction task01a047ab-fc94-7120-af1d-5701ba37aacd",
    "symptom": "Line1542 has a comma that leaves n'appartient without an explicit grammatical subject; line1572 uses S_{n-mk} with m unquantified; lines1581 and1587 leave the range of r implicit in the all-but-finitely-many condition.",
    "cause_evidence": "Exact natural unit lines1537-1605 is3776 LF UTF-8 bytes /3727 characters /D91203350D0012E008CA3A778DD5ABB1E3A18D70641C753F6F86ECFF51F949FE; canonical file820505 bytes /84EDBE3E83530AF2959B441796337C9DC21EAFCA6A13114A26778760FBF437AC. Line1542 is a high-confidence syntax defect; the other loci are mathematically recoverable editorial-compression queries, not demonstrated errors.",
    "resolution": "Do not silently normalize any French source byte. Preserve the intended mathematical meaning in the future Korean translation with an explicit note only if needed, and route all three bounded candidates to the correction task for source/facsimile adjudication. Delivery returned the exact destination task ID.",
    "tests": "Independent read-only source preparation identified the natural69-line boundary through Proposition2.1.9 and inventoried2 environments,2 labels,1 reference,1 enumerate with3 items,1 proof,II23 and99 inline math spans. Direct line readback confirmed all three reported loci.",
    "residual_risk": "The printed authority may select comma deletion, insertion of et, or another diplomatic repair at line1542. The unquantified-variable loci may be retained as accepted mathematical compression. No Korean target has yet been produced for this unit.",
    "recurrence": "For each source-preparation unit, separate high-confidence syntax defects from recoverable clarity queries, refer exact source/hash evidence, and never turn pending adjudication into a translation hold.",
    "related": ["AGKO-D184", "next unit lines1537-1605", "task01a047ab-fc94-7120-af1d-5701ba37aacd"],
}

DECISION = {
    "id": "AGKO-D184",
    "time": TIMESTAMP,
    "precision": "second",
    "kind": "r36_four_pass_convergence_gate_and_release_freeze",
    "scope": "Korean cumulative EGA R36 through EGA II2.1.7 / canonical lines1-1535",
    "choice": "Require two independent clean four-pass XeLaTeX cycles, pass3=pass4 byte-exact within each cycle and final cycle A=cycle B byte-exact, after the initial three-pass observation showed pass2 differed from pass3. Admit the resulting237-page PDF only after dual extraction, complete destination replay and selected-page visual inspection pass; refresh all public metadata from stale r34/r35 scope to exact r36 scope before archive freeze.",
    "alternatives": ["Treat the earlier three-pass cycle finals as proof of a fixed point", "Publish stale metadata while relying on the PDF front matter", "Rebuild already sealed translation content"],
    "rejected": "The first does not prove stabilization between the last two passes, the second misstates public scope, and the third reopens correct source work without evidence. The stronger four-pass gate tests the actual fixed point while preserving the admitted translation bytes.",
    "evidence": ["evidence/BUILD_RECEIPT.json 5201 bytes /77D7D02ACFF6E28EB291B4C05FC1250D20D896A3DEEDDA43AA9CDBBB8FF4BEC8", "evidence/controls/R36_PDF_QA.json 11605 bytes /9FA62E458E9E376B982B0FA5BCF256B053F9E9E5C673A68DA987CC079F3D5BEF", "reader PDF1474518 bytes /5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D", "build/BUILD.ps1 20370 bytes /330A0F8337C6019010700088E0D8D398EA0B33CA922D06641D607E2F63D51F77"],
    "uncertainty": "No known local build, extraction, navigation or rendered-page defect remains. Archive portability and public-byte identity are separate deterministic release gates and are not inferred here.",
    "consequence": "The cumulative reader is locally accepted at237 pages with226 historical source-page markers,151372 Hangul syllables in each extractor, zero replacement characters,1652 valid internal links and574 valid named destinations. Packaging, portable replay and same-lineage publication may proceed without reopening R36 translation.",
    "review": "PASS_LOCAL_BUILD_AND_PDF_QA",
    "next": "Regenerate complete expert-review views, freeze deterministic archives, replay the portable build, then publish and anonymously verify the reserved same-lineage Zenodo version and GitHub release before translating canonical line1537.",
}

EVIDENCE = {
    "id": "AGKO-E-R36-BUILD-QA-20260905",
    "time": TIMESTAMP,
    "precision": "second",
    "kind": "r36_cumulative_build_and_pdf_qa",
    "coverage": "EGA0_I and EGA I complete; EGA II Chapter II programme/table of contents complete; EGA II main text contiguous through2.1.7 / canonical lines1-1535",
    "reader": {"path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf", "pages": 237, "bytes": 1474518, "sha256": "5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D"},
    "build": {"receipt": "evidence/BUILD_RECEIPT.json", "bytes": 5201, "sha256": "77D7D02ACFF6E28EB291B4C05FC1250D20D896A3DEEDDA43AA9CDBBB8FF4BEC8", "cycles": 2, "passes_per_cycle": 4, "pass3_pass4_identical_each": True, "cycle_finals_identical": True, "mutex": "Global\\InterlanguageTeXSlotV1"},
    "qa": {"control": "evidence/controls/R36_PDF_QA.json", "bytes": 11605, "sha256": "9FA62E458E9E376B982B0FA5BCF256B053F9E9E5C673A68DA987CC079F3D5BEF", "historical_markers": 226, "hangul_each_extractor": 151372, "replacement_characters_each": 0, "internal_links": 1652, "named_destinations": 574, "invalid_destinations": 0, "selected_visual_pages": [1, 2, 6, 233, 234, 235, 236, 237], "visual": "PASS"},
    "metadata": {"version": "2026-09-05-r36", "concept_doi": "10.5281/zenodo.21921513", "exact_doi_reserved": "10.5281/zenodo.22217711", "github": "https://github.com/KokunoYumeto/ega-ko", "creators": ["Alexander Grothendieck", "Jean Dieudonné"], "sole_project_contributor": "AI typesetting & translation", "rights_scope_and_nonendorsement": "PASS", "excluded_active_destination_mentions": 0},
    "result": "PASS_LOCAL_BUILD_PDF_QA_AND_METADATA_PREPARATION",
    "next": "Regenerate expert-review views because the source ledgers advanced, then archive, portable replay, publication and anonymous public-byte verification.",
}


def append_once(path: Path, record: dict) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row.get("id") for row in rows]
    if record["id"] in ids:
        raise RuntimeError(f"duplicate id {record['id']} in {path}")
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    roots = [args.private_root.resolve(), (args.repo.resolve() / "evidence")]
    for root in roots:
        append_once(root / "hard.jsonl", HARD)
        append_once(root / "decisions.jsonl", DECISION)
        append_once(root / "evidence.jsonl", EVIDENCE)
    print("PASS_R36_CLOSURE_RECORDS_APPENDED")


if __name__ == "__main__":
    main()
