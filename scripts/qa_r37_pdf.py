#!/usr/bin/env python3
"""Deterministic structural, extraction and render-binding QA for EGA-ko R37."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject


EDITION = "2026-09-05-r37"
EXPECTED_PDF_SHA256 = "22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61"
EXPECTED_PDF_BYTES = 1_479_200
EXPECTED_PAGES = 238
EXPECTED_MARKERS = 227
EXPECTED_PREFIX_SHA256 = "0815285B46DA35D916612CDDACB92A1DD646153FAF6AC0D15E03417F9D349182"
EXPECTED_PREFIX_BYTES = 73_897
EXPECTED_TARGET_SHA256 = "FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383"
EXPECTED_TARGET_BYTES = 75_622
EXPECTED_TARGET_LINES = 1_627
EXPECTED_CANDIDATE_SHA256 = "A423B075B3483FC84CA580AED46C651F84543F4444805D94388CD5574114063D"
EXPECTED_CANDIDATE_BYTES = 4_073
EXPECTED_FRONT_SHA256 = "78FCF635E8551684CE5710DFFC9FE93DF311A9701A9A09BA6BC0228128AE0DDD"
EXPECTED_FRONT_BYTES = 4_440
EXPECTED_MANIFEST_SHA256 = "21ED41DDE0E7B850C12E9DF7A7839FB3FFE279B5BC205CC4FBE794A9FED4BAED"
EXPECTED_MANIFEST_BYTES = 16_264
EXPECTED_CANONICAL_SHA256 = "84EDBE3E83530AF2959B441796337C9DC21EAFCA6A13114A26778760FBF437AC"
CURRENT_EXACT_DOI = "10.5281/zenodo.22315714"
CONCEPT_DOI = "10.5281/zenodo.21921513"
PRIOR_EXACT_DOI = "10.5281/zenodo.22217711"
GLOBAL_EGA_DOI = "10.5281/zenodo.20414353"
GITHUB_REPOSITORY = "https://github.com/KokunoYumeto/ega-ko"

EXPECTED_RENDER_IDENTITIES = {
    1: (91_501, "E087A30C56F76DF99A1762B4C9C8313453F266759AE38F560036CA7C3836199B"),
    2: (368_720, "2B465597A421963A802C3437CD6CA75B26864974097F0EC01128BACCE9C82252"),
    6: (189_656, "491F22AF36DAB445E1ECA5614D37E137D76A38B98FE3617FF3DCE3345BF4F0C8"),
    236: (478_729, "1D1C0F103A5DFBBAA46E7CDA701713B52D161113FB44C06DFBDFF021753BCFE7"),
    237: (574_945, "BA2C144EA19A407BDD727A373FED338614EA3EE32997293296DCD0ED647F33E9"),
    238: (134_494, "4AEC28026EB31066E39C74C1BF02804D704A132B987F4969282851C1CA9ED7C3"),
}

REQUIRED_LABELS = ("II.2.1.8-ko", "II.2.1.9-ko")
EXACT_CAVEAT_TEX = r"\mathfrak{p}\cap S_{n-mk}=S_{n-mk}"
FORBIDDEN_SILENT_REPAIRS = (
    r"\mathfrak{p}\cap S_{n-k}=S_{n-k}",
    r"\mathfrak{p}\cap S_{n-rk}=S_{n-rk}",
)

EXPECTED_ENVIRONMENT_TEX = r"""
\begin{env}[2.1.8]
\phantomsection
\label{II.2.1.8-ko}
$\mathfrak{p}$를 등급환 $S$의 등급 소아이디얼이라 하자. 그러면
$\mathfrak{p}$는 부분군 $\mathfrak{p}_n=\mathfrak{p}\cap S_n$들의
직합이다. $\mathfrak{p}$가 $S_+$를 포함하지 않는다고 가정하자. 그러면
$\mathfrak{p}$에 속하지 않는 $f\in S_+$에 대하여, 관계
$f^nx\in\mathfrak{p}$는 $x\in\mathfrak{p}$와 동치이다. 특히
$f\in S_d$ ($d>0$)이면, 모든 $x\in S_{m-nd}$에 대하여 관계
$f^nx\in\mathfrak{p}_m$은 $x\in\mathfrak{p}_{m-nd}$와 동치이다.
\end{env}
"""

EXPECTED_PROPOSITION_TEX = r"""
\begin{proposition}[2.1.9]
\phantomsection
\label{II.2.1.9-ko}
$n_0$를 $>0$인 정수라 하고, 각 $n\geq n_0$에 대하여
$\mathfrak{p}_n$을 $S_n$의 부분군이라 하자. $S_+$를 포함하지 않으며
모든 $n\geq n_0$에 대하여
$\mathfrak{p}\cap S_n=\mathfrak{p}_n$을 만족하는 $S$의 등급
소아이디얼 $\mathfrak{p}$가 존재하기 위한 필요충분조건은 다음 조건들이
성립하는 것이다.
\begin{enumerate}
  \item[$1^\circ$] 모든 $m\geq 0$과 모든 $n\geq n_0$에 대하여
    $S_m\mathfrak{p}_n\subset\mathfrak{p}_{m+n}$이다.
  \item[$2^\circ$] $m\geq n_0$, $n\geq n_0$, $f\in S_m$, $g\in S_n$일 때,
    관계 $fg\in\mathfrak{p}_{m+n}$은 $f\in\mathfrak{p}_m$ 또는
    $g\in\mathfrak{p}_n$을 함의한다.
  \item[$3^\circ$] 적어도 하나의 $n\geq n_0$에 대하여
    $\mathfrak{p}_n\neq S_n$이다.
\end{enumerate}
또한 이때 등급 소아이디얼 $\mathfrak{p}$는 유일하다.
\end{proposition}
"""


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


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def fold_extracted_math(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text)
    for dash in ("−", "–", "—", "﹣", "－"):
        folded = folded.replace(dash, "-")
    return re.sub(r"\s+", "", folded)


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
        except Exception as exc:  # pragma: no cover - malformed-object defense
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
        # Hyperref labels resolve through the destinations recorded in main.aux;
        # PDF named destinations carry those anchor names, not the TeX labels.
        "required_r37_named_destinations": {
            "II.2.1.8-ko=>section*.316": "section*.316" in named_names,
            "II.2.1.9-ko=>section*.317": "section*.317" in named_names,
        },
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
    unembedded: list[dict[str, str]] = []
    type0_hangul_missing: list[str] = []
    embedded = 0
    for font in seen.values():
        descriptor = font_descriptor(font)
        basefont = str(font.get("/BaseFont", ""))
        subtype = str(font.get("/Subtype", ""))
        if descriptor and any(k in descriptor for k in ("/FontFile", "/FontFile2", "/FontFile3")):
            embedded += 1
        else:
            unembedded.append({"basefont": basefont, "subtype": subtype})
        has_tounicode = "/ToUnicode" in font
        if not has_tounicode:
            missing_tounicode.append({"basefont": basefont, "subtype": subtype, "to_unicode": False})
        if (
            subtype == "/Type0"
            and any(token in basefont.upper() for token in ("MALGUN", "NANUM", "NOTO", "BATANG", "GOTHIC"))
            and not has_tounicode
        ):
            type0_hangul_missing.append(basefont)
    return {
        "font_resources": len(seen),
        "embedded_font_resources": embedded,
        "unembedded_font_resources": sorted(unembedded, key=lambda x: x["basefont"]),
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


def png_dimensions(path: Path) -> list[int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert header[12:16] == b"IHDR"
    return list(struct.unpack(">II", header[16:24]))


def load_build_receipt(path: Path, repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt_edition = receipt.get("version", receipt.get("edition"))
    assert receipt_edition == EDITION
    if "exact_doi" in receipt:
        assert receipt["exact_doi"] == CURRENT_EXACT_DOI
    if "concept_doi" in receipt:
        assert receipt["concept_doi"] == CONCEPT_DOI

    reader_row = receipt.get("reader", receipt.get("pdf"))
    assert isinstance(reader_row, dict), "R37 build receipt/control must contain reader or pdf identity"
    assert reader_row.get("path") == "reader/00_EGA_ko_CUMULATIVE_READER.pdf"
    assert reader_row.get("bytes") == EXPECTED_PDF_BYTES
    assert str(reader_row.get("sha256", "")).upper() == EXPECTED_PDF_SHA256
    assert reader_row.get("pages") == EXPECTED_PAGES

    coverage = receipt.get("coverage_manifest")
    if coverage is not None:
        assert coverage.get("path") == "source/CUMULATIVE_INPUTS.json"
        assert coverage.get("bytes") == EXPECTED_MANIFEST_BYTES
        assert str(coverage.get("sha256", "")).upper() == EXPECTED_MANIFEST_SHA256
        assert coverage.get("historical_markers") == EXPECTED_MARKERS

    pass_evidence = False
    status = str(receipt.get("status", ""))
    if "PASS" in status.upper():
        pass_evidence = True
    convergence = receipt.get("convergence")
    if isinstance(convergence, dict):
        assert convergence.get("cycle_finals_byte_identical") is True
        assert convergence.get("reader_promotion_byte_identical") is True
        for cycle_name in ("cycle_a", "cycle_b"):
            cycle = convergence.get(cycle_name, {})
            assert cycle.get("pass3_equals_pass4") is True
            assert str(cycle.get("pass4_sha256", "")).upper() == EXPECTED_PDF_SHA256
        pass_evidence = True
    strict_build = receipt.get("strict_build")
    if isinstance(strict_build, dict) and str(strict_build.get("status", "")).upper() == "PASS":
        pass_evidence = True
    assert pass_evidence, "build receipt/control contains no explicit strict-build PASS evidence"
    return receipt, file_identity(path, repo)


def validate_translation_control(path: Path, repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    control = json.loads(path.read_text(encoding="utf-8"))
    assert control.get("schema") == "agko-r37-translation-admission-v1"
    authority = control["authority"]
    assert authority["admitted_prefix_lines"] == "1-1605"
    assert authority["admitted_prefix_bytes"] == EXPECTED_PREFIX_BYTES
    assert authority["admitted_prefix_sha256"] == EXPECTED_PREFIX_SHA256
    candidate = control["candidate"]
    assert candidate["bytes"] == EXPECTED_CANDIDATE_BYTES
    assert candidate["sha256"] == EXPECTED_CANDIDATE_SHA256
    target = control["integrated_target"]
    assert target["bytes"] == EXPECTED_TARGET_BYTES
    assert target["lf_lines"] == EXPECTED_TARGET_LINES
    assert target["sha256"] == EXPECTED_TARGET_SHA256
    caveat = control["source_caveat"]
    assert caveat["canonical_line"] == 1572
    assert caveat["formula"] == EXACT_CAVEAT_TEX
    assert caveat["formula_preserved"] is True
    assert caveat["silent_formula_repair"] is False
    return control, file_identity(path, repo)


def extraction_content_checks(text: str) -> dict[str, bool]:
    collapsed = collapse_whitespace(text)
    math_folded = fold_extracted_math(text)
    checks = {
        "environment_2_1_8_heading_present": "(2.1.8)" in text,
        "proposition_2_1_9_heading_present": "(2.1.9)" in text,
        "environment_text_present": "등급환S의등급소아이디얼이라하자" in collapsed,
        "proposition_necessity_sufficiency_text_present": "존재하기위한필요충분조건은다음조건들이성립하는것이다" in collapsed,
        "proposition_uniqueness_text_present": "또한이때등급소아이디얼" in collapsed and "유일하다" in collapsed,
        "proposition_integral_domain_text_present": "등급이주어진환" in collapsed and "정역임을" in collapsed,
        "printed_n_minus_mk_formula_present": "Sn-mk=Sn-mk" in math_folded,
        "guessed_n_minus_k_formula_absent": "Sn-k=Sn-k" not in math_folded,
        "guessed_n_minus_rk_formula_absent": "Sn-rk=Sn-rk" not in math_folded,
        "historical_page_II_23_present": bool(re.search(r"(?<![A-Za-z0-9])II\s*\|\s*23(?!\d)", text)),
    }
    assert all(checks.values()), {key: value for key, value in checks.items() if not value}
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--canonical-root", required=True, type=Path)
    parser.add_argument(
        "--build-receipt",
        type=Path,
        help="Fresh R37 strict-build receipt/control; defaults to REPO/evidence/BUILD_RECEIPT.json",
    )
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
    aux = repo / "build" / "out" / "main.aux"
    translation_control_path = repo / "evidence" / "controls" / "R37_TRANSLATION_ADMISSION.json"
    output = repo / "evidence" / "controls" / "R37_PDF_QA.json"
    build_receipt_path = (
        args.build_receipt.resolve()
        if args.build_receipt
        else repo / "evidence" / "BUILD_RECEIPT.json"
    )

    _, build_receipt_identity = load_build_receipt(build_receipt_path, repo)
    translation_control, translation_control_identity = validate_translation_control(
        translation_control_path, repo
    )

    assert pdf.stat().st_size == EXPECTED_PDF_BYTES
    assert sha256(pdf) == EXPECTED_PDF_SHA256
    assert manifest_path.stat().st_size == EXPECTED_MANIFEST_BYTES
    assert sha256(manifest_path) == EXPECTED_MANIFEST_SHA256
    assert target.stat().st_size == EXPECTED_TARGET_BYTES
    assert sha256(target) == EXPECTED_TARGET_SHA256
    assert front.stat().st_size == EXPECTED_FRONT_BYTES
    assert sha256(front) == EXPECTED_FRONT_SHA256
    assert sha256(canonical) == EXPECTED_CANONICAL_SHA256

    target_text = target.read_text(encoding="utf-8")
    assert target_text.count("\n") == EXPECTED_TARGET_LINES
    for label in REQUIRED_LABELS:
        assert target_text.count(f"\\label{{{label}}}") == 1
    assert collapse_whitespace(EXPECTED_ENVIRONMENT_TEX) in collapse_whitespace(target_text)
    assert collapse_whitespace(EXPECTED_PROPOSITION_TEX) in collapse_whitespace(target_text)
    assert target_text.count(EXACT_CAVEAT_TEX) == 1
    assert all(repair not in target_text for repair in FORBIDDEN_SILENT_REPAIRS)
    assert target_text.count(r"\oldpage[II]{23}") == 1
    assert target_text.count(r"\hyperref[II.2.1.8-ko]{2.1.8}") == 1
    aux_text = aux.read_text(encoding="utf-8", errors="replace")
    assert r"\newlabel{II.2.1.8-ko}" in aux_text and "{section*.316}" in aux_text
    assert r"\newlabel{II.2.1.9-ko}" in aux_text and "{section*.317}" in aux_text

    reader = PdfReader(str(pdf))
    assert len(reader.pages) == EXPECTED_PAGES
    assert not reader.is_encrypted

    page_sizes = [
        (round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2))
        for page in reader.pages
    ]
    unique_page_sizes = sorted(set(page_sizes))
    all_a4 = all(abs(w - 595.28) <= 0.02 and abs(h - 841.89) <= 0.02 for w, h in page_sizes)
    assert all_a4

    page_text = [
        (page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n")
        for page in reader.pages
    ]
    pypdf_text = "\n\f\n".join(page_text) + "\n"
    pypdf_extract.write_text(pypdf_text, encoding="utf-8", newline="\n")

    poppler_run = subprocess.run(
        [
            "pdftotext",
            "-enc",
            "UTF-8",
            "-eol",
            "unix",
            str(pdf),
            str(poppler_extract),
        ],
        capture_output=True,
        text=True,
    )
    assert poppler_run.returncode == 0, poppler_run.stderr
    poppler_text = poppler_extract.read_text(encoding="utf-8")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["scope"]["historical_source_pages"] == EXPECTED_MARKERS
    assert manifest["scope"]["historical_page_ranges"][-1] == "EGA II5-23"
    assert "lines1-1605" in manifest["scope"]["terminal_coverage"]
    expected = expected_markers(repo, manifest)
    assert len(expected) == EXPECTED_MARKERS
    assert expected[-1] == ("II", 23)
    poppler_markers = extracted_markers(poppler_text)
    pypdf_markers = extracted_markers(pypdf_text)
    expected_poppler_numeric = [page for volume, page in expected if not (volume == "0I" and page == 70)]

    canonical_lines = canonical.read_text(encoding="utf-8").splitlines()
    prefix = lf_bytes(canonical_lines[:1605])
    prefix_sha = hashlib.sha256(prefix).hexdigest().upper()
    assert len(prefix) == EXPECTED_PREFIX_BYTES
    assert prefix_sha == EXPECTED_PREFIX_SHA256

    navigation = scan_navigation(reader)
    fonts = scan_fonts(reader)
    assert not navigation["invalid_named_destinations"]
    assert not navigation["invalid_link_destinations"]
    assert not navigation["invalid_outline_destinations"]
    assert all(navigation["required_r37_named_destinations"].values())
    required_uris = {
        f"https://doi.org/{CURRENT_EXACT_DOI}": 1,
        f"https://doi.org/{CONCEPT_DOI}": 1,
        f"https://doi.org/{GLOBAL_EGA_DOI}": 1,
        GITHUB_REPOSITORY: 1,
    }
    assert navigation["uri_targets"] == required_uris
    assert fonts["font_resources"] > 0
    assert fonts["embedded_font_resources"] == fonts["font_resources"]
    assert not fonts["unembedded_font_resources"]
    assert fonts["all_type0_hangul_fonts_have_tounicode"]

    poppler_features = count_text_features(poppler_extract)
    pypdf_features = count_text_features(pypdf_extract)
    for features in (poppler_features, pypdf_features):
        assert features["replacement_characters"] == 0
        assert features["carriage_returns"] == 0
        assert features["current_exact_doi_count"] == 1
        assert features["prior_exact_doi_count"] == 0
        assert features["concept_doi_count"] == 1
    assert poppler_features["hangul_syllables"] == pypdf_features["hangul_syllables"]
    assert poppler_features["hangul_syllables"] > 150_000
    poppler_content_checks = extraction_content_checks(poppler_text)
    pypdf_content_checks = extraction_content_checks(pypdf_text)
    assert pypdf_markers == expected
    assert [page for _, page in poppler_markers] == expected_poppler_numeric

    diagnostics = log_diagnostics(log)
    assert all(value == 0 for value in diagnostics["hard_diagnostics"].values())

    render_pages = list(EXPECTED_RENDER_IDENTITIES)
    assert render_pages == [1, 2, 6, 236, 237, 238]
    renders: list[dict[str, Any]] = []
    for number, (expected_bytes, expected_sha) in EXPECTED_RENDER_IDENTITIES.items():
        path = repo / "evidence" / "render" / f"r37-p{number:03d}.png"
        assert path.stat().st_size == expected_bytes
        assert sha256(path) == expected_sha
        pixels = png_dimensions(path)
        assert pixels == [1654, 2339]
        identity = file_identity(path, repo)
        identity.update(
            {
                "physical_page": number,
                "dpi": 200,
                "pixels": pixels,
                "personal_visual_inspection": "PASS",
            }
        )
        renders.append(identity)

    acroform = deref(reader.trailer["/Root"].get("/AcroForm")) if reader.trailer["/Root"].get("/AcroForm") else None
    names = deref(reader.trailer["/Root"].get("/Names", {}))
    pdftotext_version_run = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True)
    assert pdftotext_version_run.returncode == 0

    qa = {
        "schema": "agko-r37-pdf-qa-v1",
        "edition": EDITION,
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS",
        "scope": "Full-file PDF identity and structure, all destinations, full-text extraction, exact R37 proposition/caveat visibility, historical-marker sequence, and exact six-render identity checks; personal visual inspection covers the stated front, contents and terminal pages. Source-semantic and Korean-register adjudication remain separate controls. No public-byte publication verification is asserted here.",
        "build_receipt_or_control": build_receipt_identity,
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
            "poppler_pdftotext_version": pdftotext_version_run.stderr.splitlines()[0],
            "poppler_command": "pdftotext -enc UTF-8 -eol unix reader/00_EGA_ko_CUMULATIVE_READER.pdf evidence/extract.txt",
            "pypdf_version": pypdf.__version__,
            "pypdf_method": "page.extract_text() or empty string per physical page; CRLF/CR normalized to LF; pages joined with LF+FF+LF; one final LF; UTF-8 without BOM",
            "renderer": "pdftoppm",
            "render_command": "pdftoppm -f N -l N -singlefile -r 200 -png reader/00_EGA_ko_CUMULATIVE_READER.pdf evidence/render/r37-pNNN",
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
                "lines": "1-1605",
                "lf_bytes": len(prefix),
                "sha256": prefix_sha,
                "matches_manifest": True,
            },
            "korean_target": {
                **file_identity(target, repo),
                "lf_lines": target_text.count("\n"),
                "exact_environment_2_1_8_text_present": True,
                "exact_proposition_2_1_9_text_present": True,
                "required_labels_present_once": list(REQUIRED_LABELS),
                "printed_n_minus_mk_formula_present_once": True,
                "silent_formula_repairs_absent": list(FORBIDDEN_SILENT_REPAIRS),
            },
            "candidate_binding": {
                "path": translation_control["candidate"]["path"],
                "bytes": EXPECTED_CANDIDATE_BYTES,
                "sha256": EXPECTED_CANDIDATE_SHA256,
                "verification": "Exact identity and admission fields checked through the public R37 translation control; the private candidate is not required by this public PDF QA script.",
            },
            "front": {
                **file_identity(front, repo),
                "lf_lines": front.read_text(encoding="utf-8").count("\n"),
            },
            "separate_translation_control": translation_control_identity,
        },
        "extractions": [
            {
                **poppler_features,
                "path": "evidence/extract.txt",
                "r37_content_checks": poppler_content_checks,
                "numeric_marker_sequence_matches_with_documented_0I_70_exception": [page for _, page in poppler_markers] == expected_poppler_numeric,
            },
            {
                **pypdf_features,
                "path": "evidence/extract-pypdf.txt",
                "r37_content_checks": pypdf_content_checks,
                "full_marker_sequence_matches": pypdf_markers == expected,
            },
        ],
        "historical_markers": {
            "source_count": len(expected),
            "normalized_sequence_sha256": marker_hash(expected),
            "pypdf_count": len(pypdf_markers),
            "pypdf_full_sequence_matches": pypdf_markers == expected,
            "poppler_count": len(poppler_markers),
            "poppler_numeric_sequence_matches_with_documented_0I_70_exception": [page for _, page in poppler_markers] == expected_poppler_numeric,
            "ranges": ["I|5-8", "0I|11-78", "I|79-214", "II|5-23"],
            "first": expected[:5],
            "last": expected[-5:],
            "terminal_marker": ["II", 23],
            "poppler_specific_limitation": "Inherited EGA 0_I page 70 is extracted as a bare numeric token without its adjacent volume marker. The saved extraction remains verbatim; the full 227-entry volume/page sequence is proved in pypdf and the remaining 226 ordered numeric markers are proved in Poppler.",
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
            "new_environment_2_1_8_readable": True,
            "new_proposition_2_1_9_conditions_and_proof_readable": True,
            "printed_n_minus_mk_formula_readable_and_unaltered": True,
            "historical_page_break_note": "Physical pages 237 and 238 carry printed pages II|22 and II|23. The terminal whitespace follows the genuine completed boundary through Proposition 2.1.9; it is not evidence of omitted admitted content.",
        },
        "limitations": [
            "Plain-text extraction is not lossless for inherited Type1 mathematical/diagram resources lacking ToUnicode. Formula authority remains the source-synchronized TeX plus the rendered PDF.",
            "The printed source formula S_{n-mk} uses an unquantified m. This QA proves diplomatic preservation and excludes silent n-k/n-rk substitution; it does not adjudicate the source reading.",
            "This local QA does not assert archive reproducibility, GitHub/Zenodo publication, or anonymous public-byte replay; those are separate release gates.",
        ],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"PASS_R37_PDF_QA|{output}|{output.stat().st_size}|{sha256(output)}")


if __name__ == "__main__":
    main()
