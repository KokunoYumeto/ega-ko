#!/usr/bin/env python3
"""Fail-closed structural, extraction, navigation, font and visual QA for R39."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader

import qa_r37_pdf as common


VERSION = "2026-09-06-r39"
EXACT_DOI = "10.5281/zenodo.22416007"
CONCEPT_DOI = "10.5281/zenodo.21921513"
GLOBAL_DOI = "10.5281/zenodo.20414353"
GITHUB = "https://github.com/KokunoYumeto/ega-ko"
EXPECTED_MARKERS = 229
EXPECTED_TARGET = (84_274, "59D07958D5CE1765F4901202CE97B3AC6257F6DC6C0D114C37B314C6A6EB1943")
EXPECTED_CANDIDATE = (4_051, "E8F52EDEC11B90D3CCC4E2398279DA4DEA7A6064AABFBE87D1765D55FEDE1940")
EXPECTED_CANONICAL = (820_504, "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E")
EXPECTED_PREFIX = (81_885, "033E312D8BD9E22AEC1D5B8AC5705ED71C64C4E4DCFBB7ED84B9A434313ACE33")
REQUIRED_LABELS = ["II.2.2.2-ko", "II.2.2.3-ko", "II.2.2.4-ko", "II.2.2.5-ko", "II.2.2.6-ko"]
RENDER_DPI = 300


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


def exact(path: Path, expected: tuple[int, str], label: str) -> None:
    if not path.is_file() or (path.stat().st_size, sha_file(path)) != expected:
        got = (path.stat().st_size if path.is_file() else -1, sha_file(path) if path.is_file() else "")
        fail(f"{label} identity drift: {got} != {expected}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"JSON root is not an object: {path}")
    return value


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"command failed {command!r}: {result.stderr[-2000:]} {result.stdout[-2000:]}")
    return result


def version_line(result: subprocess.CompletedProcess[str]) -> str:
    lines = result.stderr.splitlines() or result.stdout.splitlines()
    if not lines:
        fail("tool version output is empty")
    return lines[0].strip()


def text_features(path: Path, display: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        **ident(path, display),
        "characters": len(text),
        "hangul_syllables": len(re.findall(r"[\uac00-\ud7a3]", text)),
        "hangul_jamo": len(re.findall(r"[\u1100-\u11ff\u3130-\u318f]", text)),
        "replacement_characters": text.count("\ufffd"),
        "carriage_returns": text.count("\r"),
        "formfeeds": text.count("\f"),
        "exact_doi_count": text.count(EXACT_DOI),
        "concept_doi_count": text.count(CONCEPT_DOI),
    }


def find_pages(page_text: list[str], pattern: str) -> list[int]:
    rx = re.compile(pattern)
    return [index for index, text in enumerate(page_text, 1) if rx.search(text)]


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def main() -> None:
    if not __debug__:
        fail("qa_r39_pdf.py requires normal Python assertion semantics; optimized mode is forbidden")
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--work-root", required=True, type=Path)
    parser.add_argument("--canonical-root", required=True, type=Path)
    parser.add_argument("--confirm-visual-pass", action="store_true")
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
    manifest = load_json(manifest_path)
    strict_path = repo / "evidence" / "controls" / "R39_STRICT_BUILD.json"
    private_strict = work / "controls" / "R39_STRICT_BUILD.json"
    strict = load_json(strict_path)
    if private_strict.read_bytes() != strict_path.read_bytes():
        fail("private/public R39 strict-build controls differ")
    if strict.get("schema") != "agko-r39-strict-build-control-v1" or strict.get("status") != "PASS_R39_STRICT_TWO_CYCLE_FOUR_PASS_BUILD":
        fail("R39 strict-build control did not pass")
    release = strict.get("release", {})
    if (release.get("version"), release.get("exact_doi"), release.get("concept_doi")) != (VERSION, EXACT_DOI, CONCEPT_DOI):
        fail("R39 strict-build release binding drift")

    reader_expected = (int(strict["reader"]["bytes"]), str(strict["reader"]["sha256"]))
    exact(pdf, reader_expected, "reader")
    exact(build_pdf, reader_expected, "build final")
    exact(pass3, reader_expected, "retained pass3")
    if pdf.read_bytes() != build_pdf.read_bytes() or pdf.read_bytes() != pass3.read_bytes():
        fail("reader/build/pass3 bytes differ")
    exact(pass2, (int(strict["convergence"]["cycle_b"]["pass2"]["bytes"]), str(strict["convergence"]["cycle_b"]["pass2"]["sha256"])), "retained pass2")
    exact(log, (int(strict["convergence"]["cycle_b"]["log"]["bytes"]), str(strict["convergence"]["cycle_b"]["log"]["sha256"])), "raw build log")
    if not aux.is_file():
        fail("build auxiliary file is absent")

    target = repo / "source" / "c2s1.tex"
    private_target = work / "ega" / "II" / "c2s1.tex"
    candidate = work / "candidates" / "r39-c2s1-continuation.tex"
    canonical = canonical_root / "source" / "ega2" / "ega2-1-fr.tex"
    exact(target, EXPECTED_TARGET, "public c2s1")
    exact(private_target, EXPECTED_TARGET, "private c2s1")
    exact(candidate, EXPECTED_CANDIDATE, "R39 candidate")
    exact(canonical, EXPECTED_CANONICAL, "canonical EGA II")
    if target.read_bytes() != private_target.read_bytes() or not target.read_bytes().endswith(candidate.read_bytes()):
        fail("R39 target mirror/tail invariant failed")
    target_text = target.read_text(encoding="utf-8")
    prefix = b"".join(canonical.read_bytes().splitlines(keepends=True)[:1780])
    if (len(prefix), sha_bytes(prefix)) != EXPECTED_PREFIX:
        fail("canonical lines1-1780 identity drift")
    if target_text.count(r"\oldpage[II]{25}") != 1:
        fail("historical page II|25 marker count drift")
    if "등급 아이디얼" in target_text or "등급 소아이디얼" in target_text:
        fail("superseded graded-ideal terminology remains in the R39 target")
    if target_text.count("동차 소아이디얼") < 5 or target_text.count("동차 아이디얼") < 1:
        fail("homogeneous-ideal terminology reseal is incomplete")
    for label in REQUIRED_LABELS:
        if target_text.count(f"\\label{{{label}}}") != 1:
            fail(f"label count drift: {label}")

    if manifest.get("scope", {}).get("historical_source_pages") != EXPECTED_MARKERS:
        fail("manifest marker count drift")
    if "lines1-1780" not in str(manifest.get("scope", {}).get("terminal_coverage", "")):
        fail("manifest terminal coverage drift")
    expected_markers = common.expected_markers(repo, manifest)
    if len(expected_markers) != EXPECTED_MARKERS or expected_markers[-1] != ("II", 25):
        fail("source marker sequence drift")

    aux_text = aux.read_text(encoding="utf-8")
    aux_destinations: dict[str, str] = {}
    for label in REQUIRED_LABELS:
        lines = [line for line in aux_text.splitlines() if line.startswith(f"\\newlabel{{{label}}}")]
        if len(lines) != 1:
            fail(f"aux label occurrence drift: {label}")
        match = re.search(r"\{(section\*\.[^{}]+)\}", lines[0])
        if not match:
            fail(f"aux named destination not parsed: {label}")
        aux_destinations[label] = match.group(1)

    reader = PdfReader(str(pdf))
    pages = len(reader.pages)
    if pages != int(strict["reader"]["pages"]):
        fail("PDF page-count/strict-control drift")
    if reader.pdf_header != "%PDF-1.7" or reader.is_encrypted:
        fail("unexpected PDF header/encryption")
    page_sizes = [(round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2)) for page in reader.pages]
    if not all(abs(w - 595.28) <= 0.02 and abs(h - 841.89) <= 0.02 for w, h in page_sizes):
        fail("non-A4 page detected")
    root = reader.trailer["/Root"]
    if root.get("/AcroForm"):
        fail("unexpected AcroForm")
    names = common.deref(root.get("/Names", {}))
    if "/JavaScript" in names:
        fail("unexpected JavaScript name tree")
    metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
    if metadata.get("/Title") != "대수기하학 원론 – 한국어 누적판" or metadata.get("/Author") != "알렉산더 그로텐디크와 장 디외도네":
        fail("PDF metadata drift")

    page_text = [(page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n") for page in reader.pages]
    pypdf_text = "\n\f\n".join(page_text) + "\n"
    pypdf_extract = repo / "evidence" / "r39-extract-pypdf.txt"
    poppler_extract = repo / "evidence" / "r39-extract-poppler.txt"
    pypdf_extract.write_text(pypdf_text, encoding="utf-8", newline="\n")
    run(["pdftotext", "-enc", "UTF-8", "-eol", "unix", str(pdf), str(poppler_extract)])
    poppler_text = poppler_extract.read_text(encoding="utf-8")
    pypdf_markers = common.extracted_markers(pypdf_text)
    poppler_markers = common.extracted_markers(poppler_text)
    if pypdf_markers != expected_markers:
        fail("pypdf historical marker sequence drift")
    expected_poppler_numeric = [page for volume, page in expected_markers if not (volume == "0I" and page == 70)]
    if [page for _, page in poppler_markers] != expected_poppler_numeric:
        fail("Poppler numeric marker sequence drift")
    extraction_features = [text_features(poppler_extract, "evidence/r39-extract-poppler.txt"), text_features(pypdf_extract, "evidence/r39-extract-pypdf.txt")]
    for features in extraction_features:
        if features["replacement_characters"] or features["carriage_returns"] or features["exact_doi_count"] != 1 or features["concept_doi_count"] != 1 or features["hangul_syllables"] < 150_000:
            fail(f"extraction feature gate failed: {features}")
    if extraction_features[0]["hangul_syllables"] != extraction_features[1]["hangul_syllables"]:
        fail("extraction Hangul count differs")
    folded = normalized(pypdf_text)
    content_checks = {f"environment_2_2_{number}": f"(2.2.{number})" in pypdf_text for number in range(2, 7)}
    content_checks.update({"fraction_ring": "등급환의분수환" in folded, "noetherian": "뇌터" in folded, "historical_II_25": bool(re.search(r"II\s*\|\s*25(?!\d)", pypdf_text))})
    if not all(content_checks.values()):
        fail(f"R39 content extraction check failed: {content_checks}")

    page_locations = {f"environment_2_2_{number}": find_pages(page_text, re.escape(f"(2.2.{number})")) for number in range(2, 7)}
    page_locations["historical_marker_II_25"] = find_pages(page_text, r"II\s*\|\s*25(?!\d)")
    for key, found in page_locations.items():
        if not found:
            fail(f"page location not found: {key}")
    new_pages = sorted({page for found in page_locations.values() for page in found})
    render_pages = sorted({1, 2, 6, 237, 238, max(1, pages - 1), pages, *new_pages})

    navigation = common.scan_navigation(reader)
    required_destinations = {f"{label}=>{destination}": destination in reader.named_destinations for label, destination in aux_destinations.items()}
    if not all(required_destinations.values()) or navigation["invalid_named_destinations"] or navigation["invalid_link_destinations"] or navigation["invalid_outline_destinations"]:
        fail("PDF navigation gate failed")
    expected_uris = {f"https://doi.org/{EXACT_DOI}": 1, f"https://doi.org/{CONCEPT_DOI}": 1, f"https://doi.org/{GLOBAL_DOI}": 1, GITHUB: 1}
    if navigation["uri_targets"] != expected_uris:
        fail(f"PDF URI target drift: {navigation['uri_targets']}")
    navigation["required_r39_named_destinations"] = required_destinations
    navigation.pop("required_r37_named_destinations", None)
    fonts = common.scan_fonts(reader)
    if fonts["font_resources"] <= 0 or fonts["embedded_font_resources"] != fonts["font_resources"] or fonts["unembedded_font_resources"] or not fonts["all_type0_hangul_fonts_have_tounicode"]:
        fail("PDF font/ToUnicode gate failed")
    diagnostics = common.log_diagnostics(log)
    if any(diagnostics["hard_diagnostics"].values()):
        fail("hard diagnostics found in build log")

    render_dir = repo / "evidence" / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    prep_path = repo / "evidence" / "controls" / "R39_VISUAL_QA_PREPARATION.json"
    private_prep = work / "controls" / "R39_VISUAL_QA_PREPARATION.json"
    if not args.confirm_visual_pass:
        render_rows: list[dict[str, Any]] = []
        for number in render_pages:
            prefix_path = render_dir / f"r39-p{number:03d}"
            render = prefix_path.with_suffix(".png")
            run(["pdftoppm", "-f", str(number), "-l", str(number), "-singlefile", "-r", str(RENDER_DPI), "-png", str(pdf), str(prefix_path)])
            if common.png_dimensions(render) != [2481, 3508]:
                fail(f"render dimension drift on page {number}")
            render_rows.append({**ident(render, f"evidence/render/r39-p{number:03d}.png"), "physical_page": number, "dpi": RENDER_DPI, "pixels": [2481, 3508]})
        prep = {"schema": "agko-r39-visual-qa-preparation-v1", "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"), "reader": {**ident(pdf, "reader/00_EGA_ko_CUMULATIVE_READER.pdf"), "pages": pages}, "render_selection": {"fixed_regression_pages": [1, 2, 6], "terminology_reseal_pages": [237, 238], "extraction_discovered_new_pages": new_pages, "terminal_pages": sorted({max(1, pages - 1), pages}), "all_selected_pages": render_pages}, "renders": render_rows, "status": "PENDING_EXPLICIT_VISUAL_INSPECTION"}
        payload = (json.dumps(prep, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        prep_path.write_bytes(payload)
        private_prep.write_bytes(payload)
        print(f"PREPARED_R39_PDF_QA_RENDER_SET|{len(payload)}|{sha_bytes(payload)}|pages={','.join(map(str, render_pages))}")
        return

    prep = load_json(prep_path)
    if private_prep.read_bytes() != prep_path.read_bytes() or prep.get("schema") != "agko-r39-visual-qa-preparation-v1" or prep.get("status") != "PENDING_EXPLICIT_VISUAL_INSPECTION":
        fail("visual preparation control drift")
    if prep.get("reader") != {**ident(pdf, "reader/00_EGA_ko_CUMULATIVE_READER.pdf"), "pages": pages} or prep.get("render_selection", {}).get("all_selected_pages") != render_pages:
        fail("visual preparation reader/page selection drift")
    render_rows = prep.get("renders", [])
    if [row.get("physical_page") for row in render_rows] != render_pages:
        fail("visual preparation render ordering drift")
    for row in render_rows:
        number = int(row["physical_page"])
        render = render_dir / f"r39-p{number:03d}.png"
        exact(render, (int(row["bytes"]), str(row["sha256"])), f"inspected render page {number}")
        if common.png_dimensions(render) != [2481, 3508]:
            fail(f"inspected render dimension drift on page {number}")

    probe = subprocess.run([sys.executable, "-O", "-B", str(Path(__file__).resolve()), "--help"], capture_output=True)
    probe_output = probe.stdout + probe.stderr
    if probe.returncode == 0 or b"PASS_R39_PDF_QA" in probe_output or b"optimized mode is forbidden" not in probe_output:
        fail("optimized-mode negative test failed closed incorrectly")

    qa: dict[str, Any] = {
        "schema": "agko-r39-pdf-qa-v1",
        "edition": VERSION,
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS",
        "scope": "Full cumulative reader/build identities, two-cycle convergence, 17 Korean inputs, 23 canonical inputs, PDF structure/navigation/fonts, dual full extraction, all 229 historical markers, and 300-dpi visual inspection of fixed regression, every extraction-discovered R39-content page, and terminal pages. These hard checks provide reproducible evidence, not a claim of absolute perfection.",
        "required_controls": {"strict_build": ident(strict_path, "evidence/controls/R39_STRICT_BUILD.json"), "visual_preparation": ident(prep_path, "evidence/controls/R39_VISUAL_QA_PREPARATION.json"), "all_private_public_exact": True},
        "pdf": {**ident(pdf, "reader/00_EGA_ko_CUMULATIVE_READER.pdf"), "pages": pages, "version": reader.pdf_header, "page_size_points": sorted(set(page_sizes)), "all_pages_a4": True, "encrypted": False, "metadata": metadata, "acroform_present": False, "javascript_name_tree_present": False, "build_output_pdf": ident(build_pdf, "build/out/main.pdf"), "build_output_pdf_byte_identical": True, "retained_pass2_pdf": ident(pass2, "build/out/main.pass2.pdf"), "retained_pass3_pdf": ident(pass3, "build/out/main.pass3.pdf"), "pass3_equals_final": True},
        "tools": {"pdftotext_version": version_line(run(["pdftotext", "-v"])), "pdftoppm_version": version_line(run(["pdftoppm", "-v"])), "pypdf_version": pypdf.__version__},
        "execution_safety": {"normal_assertion_semantics_required_by_non_assert_startup_guard": True, "optimized_mode_negative_test": {"exit_code": probe.returncode, "pass_token_emitted": False, "explicit_guard_message_observed": True, "result": "PASS_FAIL_CLOSED"}, "confirmation_mode_pdftoppm_render_invocations": 0, "confirmation_reused_exact_inspected_render_bytes": True},
        "source_bindings": {"manifest": ident(manifest_path, "source/CUMULATIVE_INPUTS.json"), "canonical_ega2": ident(canonical, "[CANONICAL_ROOT]/source/ega2/ega2-1-fr.tex"), "canonical_prefix": {"lines": "1-1780", "bytes": len(prefix), "sha256": sha_bytes(prefix)}, "korean_target": {**ident(target, "source/c2s1.tex"), "lf_lines": target_text.count("\n"), "private_public_exact": True, "candidate_tail_exact": True, "required_labels_present_once": REQUIRED_LABELS, "oldpage_II_25_present_once": True}, "candidate": ident(candidate, "candidates/r39-c2s1-continuation.tex")},
        "extractions": [{**features, "content_checks": content_checks} for features in extraction_features],
        "historical_markers": {"source_count": len(expected_markers), "normalized_sequence_sha256": common.marker_hash(expected_markers), "pypdf_count": len(pypdf_markers), "pypdf_full_sequence_matches": True, "poppler_count": len(poppler_markers), "poppler_numeric_sequence_matches_with_documented_0I_70_exception": True, "ranges": ["I|5-8", "0I|11-78", "I|79-214", "II|5-25"], "terminal_marker": ["II", 25]},
        "page_location_binding": {**page_locations, "new_content_pages": new_pages, "terminal_physical_page": pages, "render_selection_was_extraction_bound_not_guessed": True},
        "navigation": navigation,
        "font_unicode": fonts,
        "build_logs": {"raw_retained": ident(log, "build/out/main.log"), **diagnostics},
        "renders": [{**row, "visual_inspection": "PASS_NO_OBSERVED_DEFECTS"} for row in render_rows],
        "visual_findings": {"status": "PASS_NO_OBSERVED_DEFECTS", "selected_physical_pages": render_pages, "dpi": RENDER_DPI, "clipping_or_overlap_observed": False, "missing_or_tofu_glyphs_observed": False, "broken_formula_or_diagram_observed": False, "unreadable_text_observed": False, "title_scope_and_exact_doi_readable": True, "new_environments_and_historical_II_25_marker_readable": True, "sample_boundary": "Visual findings apply to the exact rendered pages; full-document coverage is separately supplied by structural, source, extraction, marker, destination and font checks."},
        "limitations": ["Plain-text extraction is not lossless for inherited mathematical or diagram resources lacking ToUnicode; source-synchronized TeX and rendering remain the formula authority.", "Hard deterministic checks and inspected renders do not constitute a claim that no conceivable defect exists.", "Publication and anonymous public-byte replay remain separate release gates."],
    }
    text = json.dumps(qa, ensure_ascii=False, indent=2) + "\n"
    for forbidden in (str(repo), str(work), str(canonical_root)):
        if forbidden in text or forbidden.replace("\\", "\\\\") in text:
            fail("absolute local path leaked into PDF-QA control")
    payload = text.encode("utf-8")
    public_output = repo / "evidence" / "controls" / "R39_PDF_QA.json"
    private_output = work / "controls" / "R39_PDF_QA.json"
    public_output.write_bytes(payload)
    private_output.write_bytes(payload)
    if public_output.read_bytes() != private_output.read_bytes():
        fail("written PDF-QA controls differ")
    print(f"PASS_R39_PDF_QA|{len(payload)}|{sha_bytes(payload)}|reader={reader_expected[0]}/{reader_expected[1]}")


if __name__ == "__main__":
    main()
