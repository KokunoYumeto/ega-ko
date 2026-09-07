from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader


TASK_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = TASK_ROOT / "pub" / "ega-ko"
SOURCE_ROOT = PUBLIC_ROOT / "source"
EVIDENCE_ROOT = PUBLIC_ROOT / "evidence"
CONTROL_ROOT = EVIDENCE_ROOT / "controls"
RENDER_ROOT = EVIDENCE_ROOT / "render"
PDF = PUBLIC_ROOT / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
BUILD_PDF = PUBLIC_ROOT / "build" / "out" / "main.pdf"
PASS3_PDF = PUBLIC_ROOT / "build" / "out" / "main.pass3.pdf"
BUILD_LOG = PUBLIC_ROOT / "build" / "out" / "main.log"
MANIFEST = SOURCE_ROOT / "CUMULATIVE_INPUTS.json"
PRIVATE_C2S1 = TASK_ROOT / "ega" / "II" / "c2s1.tex"
PUBLIC_C2S1 = SOURCE_ROOT / "c2s1.tex"
OUTPUT = CONTROL_ROOT / "R61_SINGLE_AGGREGATE_PDF_QA_20260907.json"
PUBLIC_LOG = EVIDENCE_ROOT / "build-r61.log"
PYPDF_PATH = EVIDENCE_ROOT / "r61-extract-pypdf.txt"
POPPLER_PATH = EVIDENCE_ROOT / "r61-extract-poppler.txt"
FONT_PATH = EVIDENCE_ROOT / "r61-pdffonts.txt"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def file_record(path: Path, relative_to: Path = TASK_ROOT) -> dict:
    return {
        "path": path.relative_to(relative_to).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def normalized_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def run_text(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.stdout.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


for required in (PDF, BUILD_PDF, PASS3_PDF, BUILD_LOG, MANIFEST, PRIVATE_C2S1, PUBLIC_C2S1):
    require(required.is_file(), f"Missing required input: {required}")

require(not OUTPUT.exists(), "R61 aggregate-QA receipt already exists; refusing a second QA loop.")
RENDER_ROOT.mkdir(parents=True, exist_ok=True)
CONTROL_ROOT.mkdir(parents=True, exist_ok=True)
require(not list(RENDER_ROOT.glob("r61-p-*.png")), "R61 render pages already exist; refusing a second QA loop.")
require(not list(RENDER_ROOT.glob("r61-contact-*.png")), "R61 contact sheets already exist; refusing a second QA loop.")
continuing_after_font_parser_error = all(path.is_file() for path in (PUBLIC_LOG, PYPDF_PATH, POPPLER_PATH, FONT_PATH))

pdf_hash = sha256(PDF)
require(PDF.stat().st_size == 1_618_555, "Reader byte count differs from the mutex-held cumulative build result.")
require(pdf_hash == "ED7DE0C7330DD035CA7389B6435C9C7AB16A815237C0750CD241A235DF80DEC6", "Reader hash differs from the mutex-held cumulative build result.")
require(PDF.read_bytes() == BUILD_PDF.read_bytes(), "Promoted reader differs from build output.")
require(PDF.read_bytes() == PASS3_PDF.read_bytes(), "Pass 3 and final reader are not byte-identical.")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
declared_inputs = [row["path"] for row in manifest["ordered_inputs"]]
tex_paths = [SOURCE_ROOT / name for name in declared_inputs]
for tex_path in tex_paths:
    require(tex_path.is_file(), f"Declared TeX input is absent: {tex_path}")
all_tex = "\n".join(normalized_text(path) for path in tex_paths)
labels = re.findall(r"\\label\{([^}]+)\}", all_tex)
hyperrefs = re.findall(r"\\hyperref\[([^]]+)\]", all_tex)
missing_hyperrefs = sorted(set(hyperrefs) - set(labels))
oldpages = re.findall(r"\\oldpage(?:\[[^]]+\])?\{[^}]+\}", all_tex)
declared_markers = sum(int(row.get("historical_page_markers", 0)) for row in manifest["coverage_matrix"])
require(len(missing_hyperrefs) == 0, f"Missing hyperreference targets: {missing_hyperrefs[:10]}")
require(len(oldpages) == declared_markers, "Manifest historical-page count differs from compiled input count.")
for required_label in (
    "II.2.5.13-ko",
    "II.2.6.1-ko",
    "II.2.7.11-ko",
    "II.2.8.15-ko",
    "II.2.9.5-ko",
):
    require(required_label in labels, f"Required R49-R61 label missing: {required_label}")

private_c2s1_hash = sha256(PRIVATE_C2S1)
public_c2s1_hash = sha256(PUBLIC_C2S1)
require(PRIVATE_C2S1.read_bytes() == PUBLIC_C2S1.read_bytes(), "Private/public c2s1 mirrors differ.")
require(PUBLIC_C2S1.stat().st_size == 181_163, "c2s1 byte count differs from the admitted R49-R61 integration.")
require(public_c2s1_hash == "893C8E4D68134E0F03479D760F916AADD2DA4687CFF8E04DAA300C355023EF9D", "c2s1 hash differs from the admitted R49-R61 integration.")

build_log_private = BUILD_LOG.read_text(encoding="utf-8", errors="replace")
profile_pattern = re.compile(r"(?i)C:[\\/]+Users[\\/]+[^\\/\r\n]+")
sanitized_log, profile_replacements = profile_pattern.subn("[USER_PROFILE]", build_log_private)
sanitized_log = sanitized_log.replace("\r\n", "\n").replace("\r", "\n")
require(not re.search(r"(?i)C:[\\/]+Users[\\/]", sanitized_log), "Public log projection still contains a user-profile path.")
public_log = PUBLIC_LOG
if continuing_after_font_parser_error:
    require(normalized_text(public_log) == sanitized_log, "Existing sanitized build log differs during same-pass continuation.")
else:
    public_log.write_text(sanitized_log, encoding="utf-8", newline="\n")

diagnostic_patterns = {
    "fatal_errors": re.compile(r"(?m)^! "),
    "undefined_control_sequences": re.compile(r"Undefined control sequence", re.I),
    "undefined_references": re.compile(r"undefined references|Reference .* undefined", re.I),
    "rerun_requests": re.compile(r"Rerun to get cross-references right", re.I),
    "missing_characters": re.compile(r"Missing character", re.I),
    "overfull_or_underfull_boxes": re.compile(r"(?:Over|Under)full \\[hv]box", re.I),
    "multiply_defined_labels": re.compile(r"multiply defined", re.I),
}
diagnostics = {name: len(pattern.findall(build_log_private)) for name, pattern in diagnostic_patterns.items()}
require(all(count == 0 for count in diagnostics.values()), f"Build diagnostics are nonzero: {diagnostics}")

reader = PdfReader(str(PDF), strict=True)
pages = len(reader.pages)
require(pages >= 249, "Cumulative reader regressed below the public R48 page count.")
a4_pages = 0
pypdf_pages: list[str] = []
link_annotations = 0
internal_links = 0
external_urls: list[str] = []
for page in reader.pages:
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    if abs(width - 595.276) < 2.0 and abs(height - 841.89) < 2.0:
        a4_pages += 1
    if not continuing_after_font_parser_error:
        pypdf_pages.append(page.extract_text() or "")
    for annotation_reference in page.get("/Annots", []):
        annotation = annotation_reference.get_object()
        if str(annotation.get("/Subtype")) != "/Link":
            continue
        link_annotations += 1
        action = annotation.get("/A")
        if action is not None:
            action = action.get_object()
            if str(action.get("/S")) == "/URI":
                external_urls.append(str(action.get("/URI")))
            elif str(action.get("/S")) == "/GoTo":
                internal_links += 1
        elif annotation.get("/Dest") is not None:
            internal_links += 1
require(a4_pages == pages, "Not every reader page is A4-sized.")

pypdf_path = PYPDF_PATH
if continuing_after_font_parser_error:
    pypdf_text = normalized_text(pypdf_path)
else:
    pypdf_text = "\n\f\n".join(pypdf_pages) + "\n"
    pypdf_path.write_text(pypdf_text, encoding="utf-8", newline="\n")

pdftotext = shutil.which("pdftotext")
pdffonts = shutil.which("pdffonts")
pdfinfo = shutil.which("pdfinfo")
pdftoppm = shutil.which("pdftoppm")
for tool_name, tool_path in (("pdftotext", pdftotext), ("pdffonts", pdffonts), ("pdfinfo", pdfinfo), ("pdftoppm", pdftoppm)):
    require(tool_path is not None, f"Required Poppler tool is unavailable: {tool_name}")

poppler_path = POPPLER_PATH
if not continuing_after_font_parser_error:
    subprocess.run([pdftotext, "-layout", "-enc", "UTF-8", str(PDF), str(poppler_path)], check=True)
poppler_text = normalized_text(poppler_path)
if not continuing_after_font_parser_error:
    poppler_path.write_text(poppler_text, encoding="utf-8", newline="\n")

font_path = FONT_PATH
if continuing_after_font_parser_error:
    font_text = normalized_text(font_path)
else:
    font_text = run_text([pdffonts, str(PDF)])
    font_path.write_text(font_text, encoding="utf-8", newline="\n")
font_lines = [line for line in font_text.splitlines() if line.strip()]
separator_index = next(index for index, line in enumerate(font_lines) if re.fullmatch(r"-+(?: +-+)+", line.strip()))
font_rows = font_lines[separator_index + 1 :]
embedded_values = []
unicode_values = []
for row in font_rows:
    parts = row.split()
    require(len(parts) >= 7, f"Unparseable pdffonts row: {row}")
    embedded_values.append(parts[-5].lower())
    unicode_values.append(parts[-3].lower())
require(all(value == "yes" for value in embedded_values), "At least one PDF font is not embedded.")

pdfinfo_text = run_text([pdfinfo, str(PDF)])
pdfinfo_map = {}
for line in pdfinfo_text.splitlines():
    if ":" in line:
        key, value = line.split(":", 1)
        pdfinfo_map[key.strip()] = value.strip()
require(int(pdfinfo_map["Pages"]) == pages, "pdfinfo and pypdf page counts differ.")
require(pdfinfo_map.get("Encrypted", "").lower().startswith("no"), "Reader is encrypted.")

combined_text = pypdf_text + "\n" + poppler_text
required_text = [
    "2.5.13",
    "2.6.1",
    "2.7.11",
    "2.8.15",
    "2.9.5",
    "등급 아이디얼",
    "닫힌 몰입 사상",
]
for probe in required_text:
    require(probe in combined_text, f"Required cumulative extraction probe missing: {probe}")
replacement_characters = combined_text.count("\ufffd")
require(replacement_characters == 0, "Extraction contains Unicode replacement characters.")
hangul_pattern = re.compile(r"[\uac00-\ud7a3]")
pypdf_hangul = len(hangul_pattern.findall(pypdf_text))
poppler_hangul = len(hangul_pattern.findall(poppler_text))
require(pypdf_hangul > 100_000 and poppler_hangul > 100_000, "Extracted Hangul volume is implausibly low.")

required_urls = [
    "https://doi.org/10.5281/zenodo.21921513",
    "https://doi.org/10.5281/zenodo.22647516",
    "https://github.com/KokunoYumeto/ega-ko",
]
for url in required_urls:
    require(url in external_urls, f"Required reader URL annotation is absent: {url}")

try:
    named_destinations = len(reader.named_destinations)
except Exception:
    named_destinations = -1
require(named_destinations > 0, "Reader contains no named destinations.")

render_pages = list(range(1, min(8, pages) + 1)) + list(range(248, pages + 1))
render_pages = sorted(set(page for page in render_pages if 1 <= page <= pages))
render_records = []
for page_number in render_pages:
    prefix = RENDER_ROOT / f"r61-p-{page_number:03d}"
    subprocess.run(
        [pdftoppm, "-f", str(page_number), "-l", str(page_number), "-r", "200", "-png", "-singlefile", str(PDF), str(prefix)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    image_path = prefix.with_suffix(".png")
    with Image.open(image_path) as rendered:
        gray = rendered.convert("L")
        histogram = gray.histogram()
        dark_pixels = sum(histogram[:245])
        width, height = rendered.size
    require(width > 1000 and height > 1500, f"Rendered page {page_number} has implausible dimensions.")
    require(dark_pixels > 10_000, f"Rendered page {page_number} appears blank.")
    render_records.append({
        **file_record(image_path),
        "page": page_number,
        "width": width,
        "height": height,
        "dark_pixels_below_245": dark_pixels,
    })

contact_records = []
contact_groups = [render_pages[index : index + 8] for index in range(0, len(render_pages), 8)]
for sheet_index, page_group in enumerate(contact_groups, start=1):
    thumb_width = 620
    thumb_height = 877
    label_height = 28
    columns = 2
    rows = (len(page_group) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    for group_index, page_number in enumerate(page_group):
        image_path = RENDER_ROOT / f"r61-p-{page_number:03d}.png"
        with Image.open(image_path) as rendered:
            rendered = rendered.convert("RGB")
            rendered.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            x = (group_index % columns) * thumb_width + (thumb_width - rendered.width) // 2
            y = (group_index // columns) * (thumb_height + label_height) + label_height
            sheet.paste(rendered, (x, y))
        draw.text(((group_index % columns) * thumb_width + 8, (group_index // columns) * (thumb_height + label_height) + 6), f"physical page {page_number}", fill="black")
    contact_path = RENDER_ROOT / f"r61-contact-{sheet_index:02d}.png"
    sheet.save(contact_path, format="PNG", optimize=True)
    contact_records.append({**file_record(contact_path), "pages": page_group, "width": sheet.width, "height": sheet.height})

manifest_row = next(row for row in manifest["coverage_matrix"] if row["target_path"] == "c2s1.tex")
source_reconciliation = TASK_ROOT / "controls" / "R61_EGA1_D68_SOURCE_RECONCILIATION.json"
require(source_reconciliation.is_file(), "D68 source-reconciliation control is missing.")

receipt = {
    "schema": "agko-r61-single-aggregate-pdf-qa-v1",
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "One whole-reader QA after one substantial R49-R61 integration and one mutex-held cumulative convergence build; no per-unit QA and no repeated whole-reader QA loop.",
    "reader": {
        **file_record(PDF),
        "pages": pages,
        "a4_pages": a4_pages,
        "encrypted": False,
        "pdf_version": pdfinfo_map.get("PDF version"),
        "pass3_and_final_byte_identical": True,
    },
    "source_and_manifest": {
        "manifest": file_record(MANIFEST),
        "declared_inputs": len(declared_inputs),
        "labels": len(labels),
        "hyperreferences": len(hyperrefs),
        "missing_hyperreference_targets": len(missing_hyperrefs),
        "historical_page_markers": len(oldpages),
        "frontier": "ega2-1-fr.tex lines 1-4040 through complete section 2 / proof 2.9.5",
        "next": "line 4041 blank; line 4042 begins Section 3",
        "target": {
            **file_record(PUBLIC_C2S1),
            "lf_lines": normalized_text(PUBLIC_C2S1).count("\n"),
            "private_public_exact": private_c2s1_hash == public_c2s1_hash,
            "manifest_row": manifest_row,
        },
        "ega1_d68_source_reconciliation": file_record(source_reconciliation),
    },
    "build_log": {
        **file_record(public_log),
        "sanitized_public_projection": True,
        "profile_path_replacements": profile_replacements,
        "private_original_bytes": BUILD_LOG.stat().st_size,
        "private_original_sha256": sha256(BUILD_LOG),
        **diagnostics,
    },
    "extraction": {
        "pypdf": file_record(pypdf_path),
        "poppler": file_record(poppler_path),
        "pypdf_hangul_syllables": pypdf_hangul,
        "poppler_hangul_syllables": poppler_hangul,
        "combined_hangul_syllables": pypdf_hangul + poppler_hangul,
        "replacement_characters": replacement_characters,
        "required_new_text_found": required_text,
    },
    "navigation": {
        "named_destinations": named_destinations,
        "link_annotations": link_annotations,
        "internal_links": internal_links,
        "required_source_labels": [
            "II.2.5.13-ko",
            "II.2.6.1-ko",
            "II.2.7.11-ko",
            "II.2.8.15-ko",
            "II.2.9.5-ko",
        ],
        "required_external_urls": required_urls,
    },
    "fonts": {
        "font_rows": len(font_rows),
        "all_embedded": all(value == "yes" for value in embedded_values),
        "to_unicode_yes_rows": sum(value == "yes" for value in unicode_values),
        "inventory": file_record(font_path),
    },
    "focused_visual_inspection": {
        "physical_pages": render_pages,
        "dpi": 200,
        "machine_render_and_nonblank_gate": "PASS",
        "human_view_status": "PENDING_SINGLE_CONTACT_SHEET_INSPECTION",
        "renders": render_records,
        "contact_sheets": contact_records,
    },
    "policy": {
        "small_section_qa_loops": 0,
        "whole_reader_qa_loops": 1,
        "rerun_guard": "The script refuses execution when this receipt or any R61 render already exists.",
        "continued_after_font_parser_error": continuing_after_font_parser_error,
        "continuation_semantics": "Existing build-log, dual-extraction, and font outputs were consumed without regeneration; the stopped machine pass continued from its font-table parser boundary.",
    },
    "result": "MACHINE_PASS_VISUAL_INSPECTION_PENDING",
}

OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({
    "result": receipt["result"],
    "reader": receipt["reader"],
    "pages_rendered": render_pages,
    "contact_sheets": [record["path"] for record in contact_records],
    "receipt": file_record(OUTPUT),
}, ensure_ascii=True))
