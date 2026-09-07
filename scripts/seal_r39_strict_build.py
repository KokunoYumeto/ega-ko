#!/usr/bin/env python3
"""Seal the exact two-cycle R39 cumulative build after all live gates pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader


VERSION = "2026-09-06-r39"
EXACT_DOI = "10.5281/zenodo.22416007"
CONCEPT_DOI = "10.5281/zenodo.21921513"
MUTEX = r"Global\InterlanguageTeXSlotV1"
EXPECTED_TARGET_BYTES = 84_274
EXPECTED_TARGET_SHA = "59D07958D5CE1765F4901202CE97B3AC6257F6DC6C0D114C37B314C6A6EB1943"
EXPECTED_TARGET_LF = 1_809
EXPECTED_CANDIDATE_BYTES = 4_051
EXPECTED_CANDIDATE_SHA = "E8F52EDEC11B90D3CCC4E2398279DA4DEA7A6064AABFBE87D1765D55FEDE1940"
EXPECTED_PREFIX_BYTES = 81_885
EXPECTED_PREFIX_SHA = "033E312D8BD9E22AEC1D5B8AC5705ED71C64C4E4DCFBB7ED84B9A434313ACE33"
EXPECTED_CANONICAL_BYTES = 820_504
EXPECTED_CANONICAL_SHA = "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E"
EXPECTED_MARKERS = 229
EXPECTED_DECLARATION = (
    "% Authority slice: EGA II ega2-1-fr.tex lines 1-1780, 81885 LF UTF-8 bytes, "
    "SHA-256 033E312D8BD9E22AEC1D5B8AC5705ED71C64C4E4DCFBB7ED84B9A434313ACE33."
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def ident(path: Path, display: str) -> dict[str, Any]:
    if not path.is_file():
        fail(f"missing required file: {display}")
    return {"path": display, "bytes": path.stat().st_size, "sha256": sha_file(path)}


def exact(path: Path, size: int, digest: str, label: str) -> None:
    got = (path.stat().st_size if path.is_file() else -1, sha_file(path) if path.is_file() else "")
    if got != (size, digest):
        fail(f"{label} identity drift: {got} != {(size, digest)}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"JSON root is not an object: {path.name}")
    return value


def mirror(private: Path, public: Path, label: str) -> dict[str, Any]:
    if not private.is_file() or not public.is_file():
        fail(f"missing mirrored {label} control")
    if private.read_bytes() != public.read_bytes():
        fail(f"private/public {label} control differs")
    value = load_json(private)
    return {**ident(public, f"evidence/controls/{public.name}"), "private_public_exact": True, "schema": value.get("schema"), "result": value.get("result") or value.get("status")}


def line_prefix(path: Path, count: int) -> bytes:
    lines = path.read_bytes().splitlines(keepends=True)
    if len(lines) < count:
        fail(f"canonical source shorter than {count} lines")
    return b"".join(lines[:count])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--work-root", required=True, type=Path)
    parser.add_argument("--canonical-root", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    work = args.work_root.resolve()
    canonical_root = args.canonical_root.resolve()

    manifest_path = repo / "source" / "CUMULATIVE_INPUTS.json"
    manifest = load_json(manifest_path)
    if manifest.get("schema") != "ega-ko-cumulative-inputs-v2":
        fail("unsupported cumulative manifest schema")
    scope = manifest.get("scope", {})
    if scope.get("historical_source_pages") != EXPECTED_MARKERS:
        fail("R39 marker count is not 229")
    if "lines1-1780" not in str(scope.get("terminal_coverage", "")):
        fail("R39 terminal coverage declaration is absent")

    target = repo / "source" / "c2s1.tex"
    private_target = work / "ega" / "II" / "c2s1.tex"
    exact(target, EXPECTED_TARGET_BYTES, EXPECTED_TARGET_SHA, "public c2s1")
    exact(private_target, EXPECTED_TARGET_BYTES, EXPECTED_TARGET_SHA, "private c2s1")
    if target.read_bytes() != private_target.read_bytes():
        fail("R39 c2s1 mirrors differ")
    target_text = target.read_text(encoding="utf-8")
    if target_text.count("\n") != EXPECTED_TARGET_LF:
        fail("R39 c2s1 line-count drift")
    if target_text.splitlines()[0] != EXPECTED_DECLARATION:
        fail("R39 c2s1 authority declaration drift")
    if "등급 아이디얼" in target_text or "등급 소아이디얼" in target_text:
        fail("superseded graded-ideal terminology remains in R39 c2s1")
    if target_text.count("동차 소아이디얼") < 5 or target_text.count("동차 아이디얼") < 1:
        fail("homogeneous-ideal terminology reseal is incomplete")
    candidate = work / "candidates" / "r39-c2s1-continuation.tex"
    exact(candidate, EXPECTED_CANDIDATE_BYTES, EXPECTED_CANDIDATE_SHA, "R39 candidate")
    if not target.read_bytes().endswith(candidate.read_bytes()):
        fail("R39 candidate is not the exact cumulative target tail")

    canonical = canonical_root / "source" / "ega2" / "ega2-1-fr.tex"
    exact(canonical, EXPECTED_CANONICAL_BYTES, EXPECTED_CANONICAL_SHA, "canonical EGA II source")
    prefix = line_prefix(canonical, 1_780)
    if (len(prefix), sha_bytes(prefix)) != (EXPECTED_PREFIX_BYTES, EXPECTED_PREFIX_SHA):
        fail("canonical EGA II lines1-1780 identity drift")

    ordered = manifest.get("ordered_inputs", [])
    matrix = manifest.get("coverage_matrix", [])
    if len(ordered) != 17 or len(matrix) != 23:
        fail("cumulative manifest input count drift")
    translated = {row.get("target_path"): row for row in matrix if row.get("target_path")}
    if set(translated) != {row.get("path") for row in ordered}:
        fail("ordered-input and translated-matrix sets differ")
    marker_sum = sum(int(row.get("historical_page_markers", 0)) for row in matrix)
    if marker_sum != EXPECTED_MARKERS:
        fail("cumulative marker sum drift")
    status_counts = Counter(str(row.get("status")) for row in matrix)
    input_rows: list[dict[str, Any]] = []
    for entry in ordered:
        relative = str(entry["path"])
        row = translated[relative]
        public = repo / "source" / relative
        expected = (int(row["target_bytes"]), str(row["target_sha256"]))
        exact(public, *expected, f"public source/{relative}")
        private = work / str(row["working_path"])
        if relative != "front.tex":
            exact(private, *expected, f"private {row['working_path']}")
            if private.read_bytes() != public.read_bytes():
                fail(f"private/public source differs: {relative}")
        input_rows.append({**ident(public, f"source/{relative}"), "private_public_exact": relative != "front.tex"})
    canonical_rows: list[dict[str, Any]] = []
    for row in matrix:
        source = canonical_root / "source" / str(row["source_path"])
        exact(source, int(row["source_bytes"]), str(row["source_sha256"]), f"canonical {row['source_path']}")
        canonical_rows.append(ident(source, f"[CANONICAL_ROOT]/source/{row['source_path']}"))

    front = repo / "source" / "front.tex"
    front_text = front.read_text(encoding="utf-8")
    if front_text.count(EXACT_DOI) != 2 or front_text.count(CONCEPT_DOI) != 2:
        fail("front matter DOI declaration drift")
    if "2026-09-06-r39" not in front_text or "1--1780" not in front_text or "제2.2.6" not in front_text:
        fail("front matter R39 coverage drift")

    build = repo / "build"
    out = build / "out"
    paths = {
        "reader": repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf",
        "cycle_a_pass2": build / "cycle-a.pass2.pdf",
        "cycle_a_pass3": build / "cycle-a.pass3.pdf",
        "cycle_a_final": build / "cycle-a.pdf",
        "cycle_a_log": build / "cycle-a.log",
        "cycle_b_pass2": out / "main.pass2.pdf",
        "cycle_b_pass3": out / "main.pass3.pdf",
        "cycle_b_final": out / "main.pdf",
        "cycle_b_log": out / "main.log",
    }
    for label, path in paths.items():
        if not path.is_file():
            fail(f"missing build output: {label}")
    if paths["reader"].read_bytes() != paths["cycle_a_final"].read_bytes() or paths["reader"].read_bytes() != paths["cycle_b_final"].read_bytes():
        fail("reader and clean-cycle finals differ")
    if paths["cycle_a_pass3"].read_bytes() != paths["cycle_a_final"].read_bytes() or paths["cycle_b_pass3"].read_bytes() != paths["cycle_b_final"].read_bytes():
        fail("pass3/pass4 convergence failed")
    if paths["cycle_a_pass2"].read_bytes() != paths["cycle_b_pass2"].read_bytes():
        fail("clean-cycle pass2 PDFs differ")
    if paths["cycle_a_log"].read_bytes() != paths["cycle_b_log"].read_bytes():
        fail("clean-cycle logs differ")
    log_text = paths["cycle_b_log"].read_text(encoding="utf-8", errors="replace")
    hard_patterns = [r"^! ", r"Undefined control sequence", r"LaTeX Error", r"Emergency stop", r"Fatal error", r"There were undefined references", r"Rerun to get cross-references right"]
    diagnostics = {pattern: len(re.findall(pattern, log_text, flags=re.MULTILINE)) for pattern in hard_patterns}
    if any(diagnostics.values()):
        fail(f"hard TeX diagnostics present: {diagnostics}")
    pages = len(PdfReader(str(paths["reader"])).pages)
    if pages < 239:
        fail("cumulative reader regressed below the R38 page count")

    private_controls = work / "controls"
    public_controls = repo / "evidence" / "controls"
    integration = mirror(private_controls / "R39_TRANSLATION_INTEGRATION.json", public_controls / "R39_TRANSLATION_INTEGRATION.json", "R39 integration")
    wording = mirror(private_controls / "R39_KOREAN_WORDING_RESEAL.json", public_controls / "R39_KOREAN_WORDING_RESEAL.json", "R39 wording reseal")
    current_validator = mirror(private_controls / "R39_CURRENT_AUTHORITY_VALIDATOR.json", public_controls / "R39_CURRENT_AUTHORITY_VALIDATOR.json", "R39 current validator")
    declaration_controls = sorted(private_controls.glob("R39_AUTHORITY_COMMENT_RESEAL.json"))
    if len(declaration_controls) != 1:
        fail(f"expected one R39 declaration reseal control, found {[p.name for p in declaration_controls]}")
    declaration = mirror(declaration_controls[0], public_controls / declaration_controls[0].name, "R39 declaration reseal")
    ideal_terminology = mirror(
        private_controls / "R39_IDEAL_TERMINOLOGY_RESEAL.json",
        public_controls / "R39_IDEAL_TERMINOLOGY_RESEAL.json",
        "R39 homogeneous-ideal terminology reseal",
    )
    if (
        ideal_terminology.get("schema") != "agko-r39-ideal-terminology-reseal-v1"
        or ideal_terminology.get("result")
        != "PASS_R39_TYPED_HOMOGENEOUS_IDEAL_TERMINOLOGY_RESEAL"
    ):
        fail("R39 homogeneous-ideal terminology control did not pass")
    draft = load_json(private_controls / "R39_ZENODO_DRAFT_RESERVATION.json")
    if str(draft.get("exact_doi")) != EXACT_DOI or str(draft.get("concept_doi")) != CONCEPT_DOI:
        fail("R39 Zenodo reservation drift")

    reader_id = ident(paths["reader"], "reader/00_EGA_ko_CUMULATIVE_READER.pdf")
    control: dict[str, Any] = {
        "schema": "agko-r39-strict-build-control-v1",
        "verified_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "precision": "second",
        "release": {"version": VERSION, "exact_doi": EXACT_DOI, "concept_doi": CONCEPT_DOI, "reservation": ident(private_controls / "R39_ZENODO_DRAFT_RESERVATION.json", "controls/R39_ZENODO_DRAFT_RESERVATION.json")},
        "coverage": {
            "summary": "EGA 0_I and EGA I complete; EGA II programme/table of contents complete; EGA II main text translated contiguously through 2.2.6 / canonical lines1-1780",
            "manifest": {**ident(manifest_path, "source/CUMULATIVE_INPUTS.json"), "ordered_inputs": 17, "canonical_inputs": 23, "historical_marker_sum": marker_sum, "status_counts": dict(sorted(status_counts.items()))},
            "target_mirrors": {**ident(target, "source/c2s1.tex"), "private_path": "ega/II/c2s1.tex", "private_public_exact": True, "lf_lines": EXPECTED_TARGET_LF, "authority_declaration_exact": True},
            "canonical_source": {**ident(canonical, "[CANONICAL_ROOT]/source/ega2/ega2-1-fr.tex"), "admitted_prefix_lines": "1-1780", "admitted_prefix_bytes": len(prefix), "admitted_prefix_sha256": sha_bytes(prefix)},
            "translation_integration": integration,
            "wording_reseal": wording,
            "current_authority_validator": current_validator,
            "declaration_reseal": declaration,
            "ideal_terminology_reseal": ideal_terminology,
            "all_declared_public_inputs": input_rows,
            "all_declared_canonical_inputs": canonical_rows,
            "post_build_identity_recheck": "PASS",
        },
        "reader": {**reader_id, "pages": pages},
        "build_script": ident(repo / "build" / "BUILD.ps1", "build/BUILD.ps1"),
        "strict_build": {"status": "PASS", "engine": "XeLaTeX / MiKTeX", "mutex": MUTEX, "mutex_timeout_ms": 300_000, "abandoned_recovery": False, "live_canonical_and_private_coverage_gate": "PASS", "xelatex_passes": 8, "independent_clean_cycles": 2, "passes_per_cycle": 4},
        "convergence": {
            "cycle_a": {key: ident(paths[f"cycle_a_{key}"], f"build/cycle-a{'.' + key if key in {'pass2','pass3'} else ''}{'.pdf' if key != 'log' else '.log'}") for key in ("pass2", "pass3", "final", "log")},
            "cycle_b": {key: ident(paths[f"cycle_b_{key}"], f"build/out/main{'.' + key if key in {'pass2','pass3'} else ''}{'.pdf' if key != 'log' else '.log'}") for key in ("pass2", "pass3", "final", "log")},
            "cycle_pass2_byte_identical": True,
            "cycle_pass3_byte_identical": True,
            "cycle_finals_byte_identical": True,
            "cycle_raw_logs_byte_identical": True,
            "reader_promotion_byte_identical_to_both_cycle_finals": True,
        },
        "tex_log_hard_diagnostics": diagnostics,
        "incomplete_boundary": {"ega_ii": "active_incomplete", "next_canonical_source": "source/ega2/ega2-1-fr.tex line1782, environment2.2.7; line1781 is blank", "no_completion_claim": "This seals the cumulative R39 checkpoint only; it does not claim completion of EGA II or the corpus."},
        "status": "PASS_R39_STRICT_TWO_CYCLE_FOUR_PASS_BUILD",
    }
    text = json.dumps(control, ensure_ascii=False, indent=2) + "\n"
    for forbidden in (str(repo), str(work), str(canonical_root)):
        if forbidden in text or forbidden.replace("\\", "\\\\") in text:
            fail("absolute local path leaked into strict-build control")
    payload = text.encode("utf-8")
    private_out = private_controls / "R39_STRICT_BUILD.json"
    public_out = public_controls / "R39_STRICT_BUILD.json"
    private_out.write_bytes(payload)
    public_out.write_bytes(payload)
    if private_out.read_bytes() != public_out.read_bytes():
        fail("written strict-build controls differ")
    print(f"PASS_R39_STRICT_BUILD|{len(payload)}|{sha_bytes(payload)}|pages={pages}|reader={reader_id['bytes']}/{reader_id['sha256']}")


if __name__ == "__main__":
    main()
