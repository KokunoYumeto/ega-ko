#!/usr/bin/env python3
"""Create sanitized build evidence and the pre-publication R36 build receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


PDF_SHA = "5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D"
PASS2_SHA = "7E5DE54ACD3AEE0F114AC6AD5013C49A023401525BAC7C4665B22BA46F40FD31"
MANIFEST_SHA = "C2004B6109417CAE7F8B53513C12C78CF9C23D99BEFD2A8AEDE3F83AAC36196C"


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
    qa_path = repo / "evidence" / "controls" / "R36_PDF_QA.json"
    admission_path = repo / "evidence" / "controls" / "R36_TRANSLATION_ADMISSION.json"
    build_script = repo / "build" / "BUILD.ps1"
    qa_script = repo / "scripts" / "qa_r36_pdf.py"

    assert reader.stat().st_size == 1_474_518 and sha256(reader) == PDF_SHA
    assert sha256(manifest_path) == MANIFEST_SHA
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    assert qa["status"] == "PASS" and qa["pdf"]["sha256"] == PDF_SHA

    sanitized = sanitize_log(raw_log.read_text(encoding="utf-8", errors="replace"), repo, private_root, canonical_root)
    log_r36 = repo / "evidence" / "build-r36.log"
    log_current = repo / "evidence" / "build.log"
    for path in (log_r36, log_current):
        path.write_text(sanitized, encoding="utf-8", newline="\n")
    assert log_r36.read_bytes() == log_current.read_bytes()
    assert not re.search(r"(?i)C:[\\/]Users[\\/]", sanitized)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matrix = manifest["coverage_matrix"]
    counts = {status: sum(1 for row in matrix if row["status"] == status) for status in ("complete", "partial", "not_translated")}
    marker_count = sum(int(row["historical_page_markers"]) for row in matrix)
    receipt = {
        "schema_version": 4,
        "version": "2026-09-05-r36",
        "snapshot_phase": "local_qa_checkpoint_before_archive_freeze",
        "coverage": "EGA 0_I and EGA I complete; EGA II Chapter II programme/table of contents complete; EGA II main text contiguous through 2.1.7 at canonical lines 1-1535. Full EGA II and the EGA corpus remain incomplete.",
        "reader": {**ident(reader, repo), "pages": 237},
        "coverage_manifest": {
            **ident(manifest_path, repo),
            "ordered_inputs": len(manifest["ordered_inputs"]),
            "canonical_rows": len(matrix),
            **counts,
            "historical_markers": marker_count,
        },
        "exact_doi": "10.5281/zenodo.22217711",
        "concept_doi": "10.5281/zenodo.21921513",
        "prior_public_checkpoint": "r34 / 10.5281/zenodo.22209381; Zenodo and GitHub anonymous byte replay PASS",
        "next_source": "EGA II source/ega2/ega2-1-fr.tex line 1537, environment 2.1.8; line 1536 blank",
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
                "pass2_bytes": 1_474_536,
                "pass2_sha256": PASS2_SHA,
                "pass3_bytes": 1_474_518,
                "pass3_sha256": PDF_SHA,
                "pass4_bytes": 1_474_518,
                "pass4_sha256": PDF_SHA,
                "pass2_equals_final": False,
                "pass3_equals_pass4": True,
            },
            "cycle_b": {
                "pass2_bytes": 1_474_536,
                "pass2_sha256": PASS2_SHA,
                "pass3_bytes": 1_474_518,
                "pass3_sha256": PDF_SHA,
                "pass4_bytes": 1_474_518,
                "pass4_sha256": PDF_SHA,
                "pass2_equals_final": False,
                "pass3_equals_pass4": True,
            },
            "cycle_finals_byte_identical": True,
            "reader_promotion_byte_identical": True,
            "initial_three_pass_observation": "An earlier three-pass run produced byte-identical cycle finals but pass 2 differed from pass 3, so three passes did not itself prove a fixed point. BUILD.ps1 was repaired to require pass 3 = pass 4 in both clean cycles; the accepted build satisfies that stronger gate.",
        },
        "build_script": ident(build_script, repo),
        "logs": {
            "raw_retained": ident(raw_log, repo),
            "public_sanitized": [ident(log_r36, repo), ident(log_current, repo)],
            "public_logs_equal": True,
            "sanitization": "Exact Korean repository, private-work, canonical and local user-profile paths replaced by bracketed role labels; derivatives normalized to LF. The raw log remains under build/out and no historical log was edited.",
            "local_absolute_profile_absent": True,
        },
        "extraction": {
            "poppler": ident(repo / "evidence" / "extract.txt", repo),
            "pypdf": ident(repo / "evidence" / "extract-pypdf.txt", repo),
            "each_hangul_syllables": 151372,
            "each_replacement_characters": 0,
            "full_historical_sequence_pypdf": True,
            "poppler_documented_0I_page70_exception": True,
        },
        "translation_admission": ident(admission_path, repo),
        "pdf_qa": ident(qa_path, repo),
        "qa_script": ident(qa_script, repo),
        "portable_replay": "Required after frozen source archive; not claimed by this snapshot",
        "status": "PASS_LOCAL_BUILD_AND_PDF_QA",
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    assert marker_count == 226
    build_receipt = repo / "evidence" / "BUILD_RECEIPT.json"
    build_receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    private_qa = private_root / "controls" / "R36_PDF_QA.json"
    private_build = private_root / "controls" / "R36_BUILD_RECEIPT.json"
    shutil.copyfile(qa_path, private_qa)
    shutil.copyfile(build_receipt, private_build)

    print(
        "PASS_R36_RELEASE_EVIDENCE|"
        f"build_receipt={build_receipt.stat().st_size}/{sha256(build_receipt)}|"
        f"qa={qa_path.stat().st_size}/{sha256(qa_path)}|"
        f"log={log_r36.stat().st_size}/{sha256(log_r36)}"
    )


if __name__ == "__main__":
    main()
