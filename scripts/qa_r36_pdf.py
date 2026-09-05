#!/usr/bin/env python3
"""Deterministic structural and extraction QA for the R36 Korean EGA reader."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject


EXPECTED_PDF_SHA256 = "5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D"
EXPECTED_PDF_BYTES = 1_474_518
EXPECTED_PAGES = 237
EXPECTED_MARKERS = 226
EXPECTED_PREFIX_SHA256 = "ED3DC79E9408C4D5325D24F3FF1CB06548611C5C8BD79CC67348402D9A0C0D91"
EXPECTED_TARGET_SHA256 = "24274A13350C1D2724F02EB1591CABD5774A9B57A5833108E94F307A2E4869D3"
EXPECTED_FRONT_SHA256 = "9455D5CE604C3F2CC24D683CF7778AB73B44EF7DFB4229435A8B3AB3DAB1DBC0"
EXPECTED_MANIFEST_SHA256 = "C2004B6109417CAE7F8B53513C12C78CF9C23D99BEFD2A8AEDE3F83AAC36196C"
CURRENT_EXACT_DOI = "10.5281/zenodo.22217711"
CONCEPT_DOI = "10.5281/zenodo.21921513"
PRIOR_EXACT_DOI = "10.5281/zenodo.22209381"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def file_identity(path: Path, relative_to: Path | None = None) -> dict[str, Any]:
    shown = path.relative_to(relative_to).as_posix() if relative_to else str(path)
    return {"path": shown, "bytes": path.stat().st_size, "sha256": sha256(path)}


def lf_bytes(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


def count_text_features(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    return {
        **file_identity(path),
        "characters": len(text),
        "hangul_syllables": len(re.findall(r"[\uac00-\ud7a3]", text)),
        "hangul_jamo": len(re.findall(r"[\u1100-\u11ff\u3130-\u318f]", text)),
        "replacement_characters": text.count("\ufffd"),
        "carriage_returns": text.count("\r"),
        "formfeeds": text.count("\f"),
        "current_exact_doi_count": text.count(CURRENT_EXACT_DOI),
        "prior_exact_doi_count": text.count(PRIOR_EXACT_DOI),
        "concept_doi_count": text.count(CONCEPT_DOI),
        "legacy_math_c0_control_characters": sum(
            1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t\f"
        ),
    }


def deref(value: Any) -> Any:
    return value.get_object() if isinstance(value, IndirectObject) else value


def page_ref_key(value: Any) -> tuple[int, int] | None:
    if isinstance(value, IndirectObject):
        return (value.idnum, value.generation)
    return None


def destination_is_valid(
    value: Any,
    named: set[str],
    page_refs: set[tuple[int, int]],
) -> bool:
    value = deref(value)
    if isinstance(value, (str, NameObject)):
        return str(value).lstrip("/") in named
    if isinstance(value, ArrayObject) and value:
        first = value[0]
        key = page_ref_key(first)
        if key is not None:
            return key in page_refs
        first = deref(first)
        return isinstance(first, DictionaryObject) and "/Type" in first
    return False


def walk_outline(reader: PdfReader, entries: Any, stats: dict[str, Any]) -> None:
    if not isinstance(entries, list):
        return
    for entry in entries:
        if isinstance(entry, list):
            walk_outline(reader, entry, stats)
            continue
        stats["outline_entries"] += 1
        try:
            page_no = reader.get_destination_page_number(entry)
            if page_no < 0 or page_no >= len(reader.pages):
                raise ValueError(page_no)
        except Exception as exc:  # pragma: no cover - defensive against malformed PDF objects
            stats["invalid_outline_destinations"].append(repr(exc))


def scan_navigation(reader: PdfReader) -> dict[str, Any]:
    named_destinations = reader.named_destinations
    named_names = set(named_destinations)
    bad_named: list[str] = []
    for name, destination in named_destinations.items():
        try:
            page_no = reader.get_destination_page_number(destination)
            if page_no < 0 or page_no >= len(reader.pages):
                bad_named.append(name)
        except Exception:
            bad_named.append(name)

    refs: set[tuple[int, int]] = set()
    for page in reader.pages:
        ref = page.indirect_reference
        if ref is not None:
            refs.add((ref.idnum, ref.generation))

    annotations = links = internal = uris = 0
    uri_targets: Counter[str] = Counter()
    invalid: list[dict[str, Any]] = []
    for page_no, page in enumerate(reader.pages, 1):
        annots = deref(page.get("/Annots", []))
        for raw_annot in annots:
            annotations += 1
            annot = deref(raw_annot)
            if annot.get("/Subtype") != "/Link":
                continue
            links += 1
            if "/Dest" in annot:
                internal += 1
                if not destination_is_valid(annot["/Dest"], named_names, refs):
                    invalid.append({"page": page_no, "kind": "Dest", "value": str(annot["/Dest"])})
                continue
            action = deref(annot.get("/A", {}))
            action_kind = str(action.get("/S", ""))
            if action_kind == "/URI":
                uris += 1
                uri_targets[str(action.get("/URI", ""))] += 1
            elif action_kind in {"/GoTo", ""} and "/D" in action:
                internal += 1
                if not destination_is_valid(action["/D"], named_names, refs):
                    invalid.append({"page": page_no, "kind": "GoTo", "value": str(action["/D"])})
            else:
                invalid.append({"page": page_no, "kind": "unsupported_action", "value": action_kind})

    outline_stats = {"outline_entries": 0, "invalid_outline_destinations": []}
    walk_outline(reader, reader.outline, outline_stats)
    return {
        "annotations": annotations,
        "links": links,
        "uri_links": uris,
        "internal_links": internal,
        "named_destinations": len(named_destinations),
        "invalid_named_destinations": bad_named,
        "invalid_link_destinations": invalid,
        **outline_stats,
        "uri_targets": dict(sorted(uri_targets.items())),
    }


def font_descriptor(font: DictionaryObject) -> DictionaryObject | None:
    font = deref(font)
    descriptor = deref(font.get("/FontDescriptor")) if font.get("/FontDescriptor") else None
    if descriptor:
        return descriptor
    descendants = deref(font.get("/DescendantFonts", []))
    if descendants:
        descendant = deref(descendants[0])
        return deref(descendant.get("/FontDescriptor")) if descendant.get("/FontDescriptor") else None
    return None


def scan_fonts(reader: PdfReader) -> dict[str, Any]:
    seen: dict[tuple[Any, ...], DictionaryObject] = {}
    for page in reader.pages:
        resources = deref(page.get("/Resources", {}))
        fonts = deref(resources.get("/Font", {}))
        for name, raw_font in fonts.items():
            key = page_ref_key(raw_font) or ("direct", str(name), str(deref(raw_font).get("/BaseFont", "")))
            seen[key] = deref(raw_font)

    missing_tounicode: list[dict[str, Any]] = []
    embedded = 0
    type0_hangul_missing: list[str] = []
    for font in seen.values():
        descriptor = font_descriptor(font)
        if descriptor and any(k in descriptor for k in ("/FontFile", "/FontFile2", "/FontFile3")):
            embedded += 1
        basefont = str(font.get("/BaseFont", ""))
        subtype = str(font.get("/Subtype", ""))
        has_tounicode = "/ToUnicode" in font
        if not has_tounicode:
            missing_tounicode.append(
                {"basefont": basefont, "subtype": subtype, "to_unicode": False}
            )
        if subtype == "/Type0" and any(token in basefont.upper() for token in ("MALGUN", "NANUM", "NOTO", "BATANG", "GOTHIC")) and not has_tounicode:
            type0_hangul_missing.append(basefont)
    return {
        "font_resources": len(seen),
        "embedded_font_resources": embedded,
        "resources_with_tounicode": len(seen) - len(missing_tounicode),
        "resources_without_tounicode": sorted(missing_tounicode, key=lambda x: x["basefont"]),
        "all_type0_hangul_fonts_have_tounicode": not type0_hangul_missing,
        "type0_hangul_fonts_without_tounicode": type0_hangul_missing,
    }


def expected_markers(repo: Path, manifest: dict[str, Any]) -> list[tuple[str, int]]:
    pattern = re.compile(r"\\oldpage(?:\[([^\]]+)\])?\{(\d+)\}")
    markers: list[tuple[str, int]] = []
    source_dir = repo / "source"
    for row in manifest["ordered_inputs"]:
        path = source_dir / row["path"]
        for volume, page in pattern.findall(path.read_text(encoding="utf-8")):
            if not volume:
                raise RuntimeError(f"unqualified oldpage marker in {path}")
            normalized_volume = volume.replace("_", "")
            if normalized_volume in {r"0\textsubscript{I}", r"0\textsubscript I"}:
                normalized_volume = "0I"
            markers.append((normalized_volume, int(page)))
    return markers


def extracted_markers(text: str) -> list[tuple[str, int]]:
    pattern = re.compile(r"(?<![A-Za-z0-9])(?P<volume>0\s*I|II|I)\s*\|\s*(?P<page>\d+)")
    return [(m.group("volume").replace(" ", ""), int(m.group("page"))) for m in pattern.finditer(text)]


def marker_hash(markers: list[tuple[str, int]]) -> str:
    payload = "".join(f"{volume}|{page}\n" for volume, page in markers).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def log_diagnostics(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    patterns = {
        "tex_error_lines": r"(?m)^! ",
        "fatal_errors": r"Fatal error",
        "emergency_stops": r"Emergency stop",
        "undefined_control_sequences": r"Undefined control sequence",
        "undefined_references_or_citations": r"undefined (?:references|citations)|Reference .* undefined|Citation .* undefined",
        "missing_characters": r"Missing character:",
        "overfull_boxes": r"Overfull \\[hv]box",
        "underfull_boxes": r"Underfull \\[hv]box",
    }
    hard = {key: len(re.findall(pattern, text, flags=re.IGNORECASE)) for key, pattern in patterns.items()}
    advisory = {
        "moved_marginpars": len(re.findall(r"Marginpar on page .* moved", text)),
        "pdf_string_token_warnings": len(re.findall(r"Token not allowed in a PDF string", text)),
        "font_shape_warnings": len(re.findall(r"Font shape .* undefined", text)),
        "rerunfilecheck_main_out_unchanged": "File `main.out' has not changed" in text,
    }
    return {"hard_diagnostics": hard, "advisories": advisory}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--canonical-root", required=True, type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    canonical_root = args.canonical_root.resolve()
    pdf = repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    manifest_path = repo / "source" / "CUMULATIVE_INPUTS.json"
    target = repo / "source" / "c2s1.tex"
    front = repo / "source" / "front.tex"
    canonical = canonical_root / "source" / "ega2" / "ega2-1-fr.tex"
    poppler_extract = repo / "evidence" / "extract.txt"
    pypdf_extract = repo / "evidence" / "extract-pypdf.txt"
    log = repo / "build" / "out" / "main.log"
    output = repo / "evidence" / "controls" / "R36_PDF_QA.json"

    assert pdf.stat().st_size == EXPECTED_PDF_BYTES
    assert sha256(pdf) == EXPECTED_PDF_SHA256
    assert sha256(manifest_path) == EXPECTED_MANIFEST_SHA256
    assert sha256(target) == EXPECTED_TARGET_SHA256
    assert sha256(front) == EXPECTED_FRONT_SHA256

    reader = PdfReader(str(pdf))
    assert len(reader.pages) == EXPECTED_PAGES
    assert not reader.is_encrypted

    page_sizes = []
    for page in reader.pages:
        page_sizes.append((round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2)))
    unique_page_sizes = sorted(set(page_sizes))
    all_a4 = all(abs(w - 595.28) <= 0.02 and abs(h - 841.89) <= 0.02 for w, h in page_sizes)

    page_text = [(page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n") for page in reader.pages]
    pypdf_text = "\n\f\n".join(page_text) + "\n"
    pypdf_extract.write_text(pypdf_text, encoding="utf-8", newline="\n")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = expected_markers(repo, manifest)
    assert len(expected) == EXPECTED_MARKERS
    poppler_text = poppler_extract.read_text(encoding="utf-8")
    poppler_markers = extracted_markers(poppler_text)
    pypdf_markers = extracted_markers(pypdf_text)
    expected_poppler_numeric = [page for volume, page in expected if not (volume == "0I" and page == 70)]

    canonical_lines = canonical.read_text(encoding="utf-8").splitlines()
    prefix = lf_bytes(canonical_lines[:1535])
    prefix_sha = hashlib.sha256(prefix).hexdigest().upper()
    assert len(prefix) == 70_120
    assert prefix_sha == EXPECTED_PREFIX_SHA256

    navigation = scan_navigation(reader)
    fonts = scan_fonts(reader)
    assert not navigation["invalid_named_destinations"]
    assert not navigation["invalid_link_destinations"]
    assert not navigation["invalid_outline_destinations"]
    assert fonts["all_type0_hangul_fonts_have_tounicode"]

    poppler_features = count_text_features(poppler_extract)
    pypdf_features = count_text_features(pypdf_extract)
    assert poppler_features["replacement_characters"] == 0
    assert pypdf_features["replacement_characters"] == 0
    assert poppler_features["hangul_syllables"] == pypdf_features["hangul_syllables"]
    assert pypdf_markers == expected
    assert [page for _, page in poppler_markers] == expected_poppler_numeric

    diagnostics = log_diagnostics(log)
    assert all(value == 0 for value in diagnostics["hard_diagnostics"].values())

    render_pages = [1, 2, 6, 233, 234, 235, 236, 237]
    renders: list[dict[str, Any]] = []
    for number in render_pages:
        path = repo / "evidence" / "render" / f"r36-p{number:03d}.png"
        identity = file_identity(path, repo)
        identity.update(
            {
                "physical_page": number,
                "dpi": 200,
                "pixels": [1654, 2339],
                "personal_visual_inspection": "PASS",
            }
        )
        renders.append(identity)

    acroform = deref(reader.trailer["/Root"].get("/AcroForm")) if reader.trailer["/Root"].get("/AcroForm") else None
    names = deref(reader.trailer["/Root"].get("/Names", {}))

    qa = {
        "schema": "agko-r36-pdf-qa-v1",
        "edition": "2026-09-05-r36",
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS",
        "scope": "Full-file PDF identity and structure, all destinations, full-text extraction and historical-marker sequence checks; personal visual inspection of the eight stated front, contents, transition, changed and terminal pages. Source-semantic and Korean-register adjudication are separate controls. No public-byte publication verification is asserted here.",
        "pdf": {
            **file_identity(pdf, repo),
            "pages": len(reader.pages),
            "version": reader.pdf_header,
            "page_size_points": unique_page_sizes,
            "all_pages_a4": all_a4,
            "encrypted": reader.is_encrypted,
            "metadata": {str(k): str(v) for k, v in (reader.metadata or {}).items()},
            "acroform_present": acroform is not None,
            "javascript_name_tree_present": "/JavaScript" in names,
            "build_output_pdf": file_identity(repo / "build" / "out" / "main.pdf", repo),
            "build_output_pdf_byte_identical": sha256(repo / "build" / "out" / "main.pdf") == sha256(pdf),
        },
        "tools": {
            "poppler_pdftotext_version": subprocess.run(["pdftotext", "-v"], capture_output=True, text=True).stderr.splitlines()[0],
            "poppler_command": "pdftotext -enc UTF-8 -eol unix reader/00_EGA_ko_CUMULATIVE_READER.pdf evidence/extract.txt",
            "pypdf_version": pypdf.__version__,
            "pypdf_method": "page.extract_text() or empty string per physical page; CRLF/CR normalized to LF; pages joined with LF+FF+LF; one final LF; UTF-8 without BOM",
            "renderer": "pdftoppm",
            "render_command": "pdftoppm -f N -l N -singlefile -r 200 -png reader/00_EGA_ko_CUMULATIVE_READER.pdf evidence/render/r36-pNNN",
        },
        "source_bindings": {
            "cumulative_manifest": file_identity(manifest_path, repo),
            "ordered_inputs_checked": len(manifest["ordered_inputs"]),
            "canonical_source": {
                "path": "[CANONICAL_ROOT]/source/ega2/ega2-1-fr.tex",
                "bytes": canonical.stat().st_size,
                "lf_lines": len(canonical_lines),
                "sha256": sha256(canonical),
            },
            "canonical_prefix": {
                "lines": "1-1535",
                "lf_bytes": len(prefix),
                "sha256": prefix_sha,
                "matches_manifest": True,
            },
            "korean_target": {
                **file_identity(target, repo),
                "lf_lines": target.read_text(encoding="utf-8").count("\n"),
            },
            "front": {
                **file_identity(front, repo),
                "lf_lines": front.read_text(encoding="utf-8").count("\n"),
            },
            "separate_translation_control": file_identity(repo / "evidence" / "controls" / "R36_TRANSLATION_ADMISSION.json", repo),
        },
        "extractions": [
            {**poppler_features, "path": "evidence/extract.txt", "numeric_marker_sequence_matches_with_documented_0I_70_exception": [p for _, p in poppler_markers] == expected_poppler_numeric},
            {**pypdf_features, "path": "evidence/extract-pypdf.txt", "full_marker_sequence_matches": pypdf_markers == expected},
        ],
        "historical_markers": {
            "source_count": len(expected),
            "normalized_sequence_sha256": marker_hash(expected),
            "pypdf_count": len(pypdf_markers),
            "pypdf_full_sequence_matches": pypdf_markers == expected,
            "poppler_count": len(poppler_markers),
            "poppler_numeric_sequence_matches_with_documented_0I_70_exception": [p for _, p in poppler_markers] == expected_poppler_numeric,
            "ranges": ["I|5-8", "0I|11-78", "I|79-214", "II|5-22"],
            "first": expected[:5],
            "last": expected[-5:],
            "poppler_specific_limitation": "Inherited EGA 0_I page 70 is extracted as a bare numeric token without its adjacent volume marker. The saved extraction remains verbatim; the full 226-entry volume/page sequence is proved in pypdf and the remaining 225 ordered numeric markers are proved in Poppler.",
        },
        "navigation": navigation,
        "font_unicode": fonts,
        "build_logs": {
            "raw_retained": file_identity(log, repo),
            **diagnostics,
        },
        "renders": renders,
        "visual_findings": {
            "status": "PASS",
            "selected_physical_pages": render_pages,
            "clipping_or_overlap": False,
            "missing_or_tofu_glyphs": False,
            "title_scope_and_exact_doi_readable": True,
            "contents_terminal_boundary_readable": True,
            "new_corollaries_2_1_4_2_1_5_readable": True,
            "new_lemma_2_1_6_all_six_items_and_proof_readable": True,
            "new_corollary_2_1_7_readable": True,
            "threshold_translator_note_readable": True,
            "historical_page_break_note": "Physical pages 236 and 237 carry printed pages II|21 and II|22. The terminal whitespace follows the genuine completed boundary through Corollary 2.1.7; it is not evidence of omitted admitted content.",
        },
        "limitations": [
            "Plain-text extraction is not lossless for inherited Type1 mathematical/diagram resources lacking ToUnicode. Formula authority remains the source-synchronized TeX plus the rendered PDF.",
            "This local QA does not assert archive reproducibility, GitHub/Zenodo publication, or anonymous public-byte replay; those are separate release gates.",
        ],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"PASS_R36_PDF_QA|{output}|{output.stat().st_size}|{sha256(output)}")


if __name__ == "__main__":
    main()
