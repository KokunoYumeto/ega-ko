from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageDraw
from pypdf import PdfReader


TASK_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(__file__).resolve()
INTERLANGUAGE_ROOT = TASK_ROOT.parents[4]
PUBLIC_ROOT = TASK_ROOT / "pub" / "ega-ko"
SOURCE_ROOT = PUBLIC_ROOT / "source"
EVIDENCE_ROOT = PUBLIC_ROOT / "evidence"
CONTROL_ROOT = EVIDENCE_ROOT / "controls"
RENDER_ROOT = EVIDENCE_ROOT / "render" / "ega2-complete-20260908"

PDF = PUBLIC_ROOT / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
BUILD_ROOT = PUBLIC_ROOT / "build"
BUILD_SCRIPT = BUILD_ROOT / "BUILD.ps1"
BUILD_PDF = BUILD_ROOT / "out" / "main.pdf"
PASS2_PDF = BUILD_ROOT / "out" / "main.pass2.pdf"
PASS3_PDF = BUILD_ROOT / "out" / "main.pass3.pdf"
BUILD_LOG = BUILD_ROOT / "out" / "main.log"
MANIFEST = SOURCE_ROOT / "CUMULATIVE_INPUTS.json"
MAIN_TEX = SOURCE_ROOT / "main.tex"
OUTPUT = CONTROL_ROOT / "EGA2_COMPLETE_SINGLE_AGGREGATE_PDF_QA_20260908.json"
START_MARKER = CONTROL_ROOT / "EGA2_COMPLETE_SINGLE_AGGREGATE_PDF_QA_20260908.started.json"

CANONICAL_ROOT = (
    INTERLANGUAGE_ROOT
    / "Transcription"
    / "03_working_transcriptions"
    / "EGA_French_NUMDAM_canonical_TeX_20260801_r1"
)
BUNDLED_POPPLER_ROOT = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "native"
    / "poppler"
    / "Library"
    / "bin"
)
PDFTOPPM = BUNDLED_POPPLER_ROOT / "pdftoppm.exe"
PDFINFO = BUNDLED_POPPLER_ROOT / "pdfinfo.exe"
PDFTOTEXT = (
    Path.home()
    / "AppData"
    / "Local"
    / "Programs"
    / "MiKTeX"
    / "miktex"
    / "bin"
    / "x64"
    / "pdftotext.exe"
)
PDFFONTS = PDFTOTEXT.with_name("pdffonts.exe")

EXPECTED_BUILD_SCRIPT_BYTES = 18_861
EXPECTED_BUILD_SCRIPT_SHA256 = "E8C5864EFAEE0188B24DCF7F908B2101D8F8429814EE239A6CC9910918EDE1A1"
EXPECTED_PDFTOPPM_BYTES = 65_840
EXPECTED_PDFTOPPM_SHA256 = "50E3C5E703E4F9D21B935A40D278BECD888CEC4BB867E8188AFB4651C638A423"
EXPECTED_PDFINFO_BYTES = 81_712
EXPECTED_PDFINFO_SHA256 = "A623BD30139FD3EFCA3CA31033608C56760FC4118F49FA4034E6485DD9E48BA6"
EXPECTED_PDFTOTEXT_BYTES = 406_016
EXPECTED_PDFTOTEXT_SHA256 = "6F1F7D8DB783BD2FAC74043DCA400A53F42D0A03C4E7F81B2C51ED436C13FAEB"
EXPECTED_PDFFONTS_BYTES = 93_184
EXPECTED_PDFFONTS_SHA256 = "A173AADC0805370F48BD8E7E72BFB1FA2C3E8F4980A1B6CD021C2E83929CB430"
CANONICAL_DOI_URL = "https://doi.org/10.5281/zenodo.21921513"
CANONICAL_REPOSITORY_URL = "https://github.com/KokunoYumeto/ega-ko"
EGA2_BACK_MATTER_SOURCE_PATHS = (
    "ega2/ega2-bibliography-fr.tex",
    "ega2/ega2-indexes-and-contents-fr.tex",
    "ega2/ega2-errata-addenda-fr.tex",
)
HISTORICAL_BLANK_MARKER = ("II", 212)
BACK_MATTER_FIRST_MARKER = ("II", 205)
BACK_MATTER_LAST_MARKER = ("II", 222)

DPI = 200
INK_THRESHOLD = 245
EDGE_THRESHOLD = 225
MIN_NONBLANK_INK_RATIO = 0.0015
MAX_INK_RATIO = 0.65
MAX_PURE_BLACK_RATIO = 0.20
EDGE_BAND_PIXELS = 3
MIN_INK_MARGIN_PIXELS = 3
SOLID_BLOCK_SAMPLE_PIXELS = 12
SOLID_BLOCK_MEAN_FLOOR = 2
CONTACT_COLUMNS = 6
CONTACT_ROWS = 6
CONTACT_PAGES = CONTACT_COLUMNS * CONTACT_ROWS
MAX_CONTACT_SHEETS = 32
CONTACT_THUMBNAIL = (270, 382)
CONTACT_LABEL_HEIGHT = 22

PROFILE_PATH = re.compile(r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\r\n]+")
SHA256_RE = re.compile(r"[0-9A-F]{64}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def normalized_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def relative_path(path: Path, base: Path = TASK_ROOT) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def file_record(path: Path, base: Path = TASK_ROOT) -> dict:
    return {
        "path": relative_path(path, base),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def canonical_file_record(path: Path) -> dict:
    return {
        "path": relative_path(path, CANONICAL_ROOT),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def same_bytes(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as left_stream, right.open("rb") as right_stream:
        while True:
            left_chunk = left_stream.read(1024 * 1024)
            right_chunk = right_stream.read(1024 * 1024)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return True


def validate_public_url(url: str) -> None:
    parsed = urlsplit(url)
    require(parsed.scheme == "https", f"Non-HTTPS external URL in reader: {url}")
    require(parsed.username is None and parsed.password is None, "Reader URL contains user-info credentials.")
    require(
        not re.search(r"(?i)(?:access[_-]?token|api[_-]?key|secret|password)=", parsed.query),
        "Reader URL query appears to contain a credential.",
    )


def marker_pattern(volume: str, printed_page: int) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Z]){re.escape(volume)}\s*[|｜]\s*{printed_page}(?!\d)")


def flatten_outline(reader: PdfReader, items: list, depth: int = 0) -> list[dict]:
    records: list[dict] = []
    for item in items:
        if isinstance(item, list):
            records.extend(flatten_outline(reader, item, depth + 1))
            continue
        title = str(getattr(item, "title", "")).strip()
        try:
            page_index = reader.get_destination_page_number(item)
        except Exception:
            page_index = None
        records.append({"title": title, "depth": depth, "physical_page": None if page_index is None else page_index + 1})
    return records


def edge_dark_pixels(gray: Image.Image) -> int:
    width, height = gray.size
    bands = (
        gray.crop((0, 0, width, EDGE_BAND_PIXELS)),
        gray.crop((0, height - EDGE_BAND_PIXELS, width, height)),
        gray.crop((0, 0, EDGE_BAND_PIXELS, height)),
        gray.crop((width - EDGE_BAND_PIXELS, 0, width, height)),
    )
    return sum(sum(band.histogram()[:EDGE_THRESHOLD]) for band in bands)


def save_contact_sheet(sheet: Image.Image, sheet_number: int, pages: list[int]) -> dict:
    path = RENDER_ROOT / f"contact-{sheet_number:02d}.png"
    sheet.save(path, format="PNG", optimize=True)
    return {
        **file_record(path),
        "physical_pages": pages,
        "width": sheet.width,
        "height": sheet.height,
    }


# The receipt and render directory are deliberately unique and terminal.  Any
# prior existence means a whole-reader pass has started or finished; this
# script never resumes or repeats that pass.
require(not OUTPUT.exists(), "Final complete-EGA-II QA receipt already exists; refusing another QA loop.")
require(not RENDER_ROOT.exists(), "Complete-EGA-II render root already exists; refusing another QA loop.")
require(not START_MARKER.exists(), "Complete-EGA-II aggregate QA already started; refusing another QA loop.")

for directory in (PUBLIC_ROOT, SOURCE_ROOT, EVIDENCE_ROOT, CONTROL_ROOT, BUILD_ROOT):
    require(directory.is_dir(), f"Required task directory is missing: {directory}")
for path in (
    PDF,
    BUILD_SCRIPT,
    BUILD_PDF,
    PASS2_PDF,
    PASS3_PDF,
    BUILD_LOG,
    MANIFEST,
    MAIN_TEX,
    PDFTOPPM,
    PDFINFO,
    PDFTOTEXT,
    PDFFONTS,
):
    require(path.is_file(), f"Required aggregate-QA input is missing: {path}")

require(BUILD_SCRIPT.stat().st_size == EXPECTED_BUILD_SCRIPT_BYTES, "The approved one-cycle builder byte count drifted.")
require(sha256(BUILD_SCRIPT) == EXPECTED_BUILD_SCRIPT_SHA256, "The approved one-cycle builder hash drifted.")
for tool, expected_bytes, expected_sha256 in (
    (PDFTOPPM, EXPECTED_PDFTOPPM_BYTES, EXPECTED_PDFTOPPM_SHA256),
    (PDFINFO, EXPECTED_PDFINFO_BYTES, EXPECTED_PDFINFO_SHA256),
    (PDFTOTEXT, EXPECTED_PDFTOTEXT_BYTES, EXPECTED_PDFTOTEXT_SHA256),
    (PDFFONTS, EXPECTED_PDFFONTS_BYTES, EXPECTED_PDFFONTS_SHA256),
):
    require(tool.stat().st_size == expected_bytes, f"Approved PDF tool byte count drifted: {tool.name}")
    require(sha256(tool) == expected_sha256, f"Approved PDF tool hash drifted: {tool.name}")
require(same_bytes(PDF, BUILD_PDF), "Promoted cumulative reader differs from the final build PDF.")
require(same_bytes(PDF, PASS3_PDF), "Final build and pass 3 did not converge byte-exactly.")

manifest_text = normalized_text(MANIFEST)
manifest = json.loads(manifest_text)
require(manifest.get("schema") == "ega-ko-cumulative-inputs-v2", "Unsupported cumulative manifest schema.")
require(manifest.get("reader") == PDF.name, "Manifest reader filename differs from the cumulative reader.")
require(manifest.get("entrypoint") == MAIN_TEX.name, "Manifest entrypoint differs from source/main.tex.")

authority_driver = manifest.get("authority_driver") or {}
coverage_rows = manifest.get("coverage_matrix") or []
ordered_inputs = manifest.get("ordered_inputs") or []
require(isinstance(coverage_rows, list) and coverage_rows, "Coverage matrix is empty.")
require(isinstance(ordered_inputs, list) and ordered_inputs, "Ordered input list is empty.")
require(len(coverage_rows) == int(authority_driver.get("content_input_count", -1)), "Coverage row count differs from canonical driver count.")

source_paths = [str(row.get("source_path")) for row in coverage_rows]
driver_lines = [int(row.get("driver_line", -1)) for row in coverage_rows]
require(len(source_paths) == len(set(source_paths)), "Coverage matrix repeats a canonical source path.")
require(len(driver_lines) == len(set(driver_lines)), "Coverage matrix repeats a canonical driver line.")
require(driver_lines == sorted(driver_lines), "Coverage matrix is not in canonical driver order.")

rows_by_source = {str(row["source_path"]): row for row in coverage_rows}
for required_source in EGA2_BACK_MATTER_SOURCE_PATHS:
    require(required_source in rows_by_source, f"Complete-EGA-II manifest omits {required_source}.")
    require(rows_by_source[required_source].get("status") == "complete", f"Back matter is not complete: {required_source}")
for row in coverage_rows:
    source_path = str(row["source_path"])
    status = str(row.get("status"))
    require(status in {"complete", "partial", "not_translated"}, f"Unsupported coverage status for {source_path}: {status}")
    if source_path.startswith("ega2/"):
        require(status == "complete", f"Complete-EGA-II run refuses incomplete EGA II input: {source_path}")
    if source_path.startswith("ega3/"):
        require(status == "not_translated", "Complete-EGA-II run refuses premature EGA III inclusion.")
    if status == "not_translated":
        require(row.get("target_path") is None and row.get("target_sha256") is None, f"Untranslated row claims a target: {source_path}")

driver_relative = str(authority_driver.get("path", ""))
require(driver_relative and not Path(driver_relative).is_absolute() and ".." not in Path(driver_relative).parts, "Unsafe canonical driver path.")
canonical_driver = CANONICAL_ROOT / driver_relative
require(canonical_driver.is_file(), "Canonical EGA authority driver is missing.")
require(canonical_driver.stat().st_size == int(authority_driver["bytes"]), "Canonical driver byte identity drifted.")
require(sha256(canonical_driver) == str(authority_driver["sha256"]), "Canonical driver hash identity drifted.")

driver_text_lines = normalized_text(canonical_driver).splitlines()
live_driver_rows = []
declared_driver_line_set = set(driver_lines)
for line_number, line in enumerate(driver_text_lines, start=1):
    if line_number not in declared_driver_line_set:
        continue
    match = re.fullmatch(r"\\input\{([^}]+)\}", line.strip())
    if match:
        live_driver_rows.append((line_number, match.group(1)))
require(live_driver_rows == list(zip(driver_lines, source_paths)), "Canonical driver order differs from the coverage matrix.")

declared_targets = [str(row["path"]) for row in ordered_inputs]
translated_targets = [str(row["target_path"]) for row in coverage_rows if row.get("status") != "not_translated"]
require(declared_targets == translated_targets, "Ordered inputs do not exactly equal translated coverage targets.")
require(len(declared_targets) == len(set(declared_targets)), "Ordered inputs contain duplicate target paths.")

target_records = []
canonical_records = []
private_mirror_records = []
target_texts: dict[str, str] = {}
for row in coverage_rows:
    source_relative = str(row["source_path"])
    canonical_path = canonical_driver.parent / source_relative
    require(canonical_path.is_file(), f"Canonical source is missing: {source_relative}")
    require(canonical_path.stat().st_size == int(row["source_bytes"]), f"Canonical source byte mismatch: {source_relative}")
    require(sha256(canonical_path) == str(row["source_sha256"]), f"Canonical source hash mismatch: {source_relative}")
    canonical_records.append({**canonical_file_record(canonical_path), "driver_line": int(row["driver_line"])})

    if row.get("status") == "not_translated":
        continue
    target_relative = str(row["target_path"])
    target_parts = Path(target_relative).parts
    require(not Path(target_relative).is_absolute() and ".." not in target_parts, f"Unsafe public target path: {target_relative}")
    target_path = SOURCE_ROOT / target_relative
    require(target_path.is_file(), f"Public target is missing: {target_relative}")
    target_text = normalized_text(target_path)
    target_texts[target_relative] = target_text
    require(target_path.stat().st_size == int(row["target_bytes"]), f"Public target byte mismatch: {target_relative}")
    require(sha256(target_path) == str(row["target_sha256"]), f"Public target hash mismatch: {target_relative}")
    require(target_text.count("\n") == int(row["target_lf_lines"]), f"Public target LF count mismatch: {target_relative}")
    require(len(re.findall(r"\\oldpage(?:\[[^]]+\])?\{[^}]+\}", target_text)) == int(row["historical_page_markers"]), f"Public target old-page count mismatch: {target_relative}")
    target_records.append({**file_record(target_path), "working_path": row.get("working_path"), "status": row["status"]})

    working_relative = row.get("working_path")
    if working_relative and target_relative != "front.tex":
        working_path = TASK_ROOT / str(working_relative)
        require(working_path.is_file(), f"Private Korean mirror is missing: {working_relative}")
        require(same_bytes(working_path, target_path), f"Private/public Korean mirrors differ: {target_relative}")
        private_mirror_records.append(file_record(working_path))

main_text = normalized_text(MAIN_TEX)
compiled_inputs = re.findall(r"\\input\{([^}]+)\}", main_text)
require(compiled_inputs == declared_targets, "source/main.tex input order differs from the manifest.")
present_tex = sorted(relative_path(path, SOURCE_ROOT) for path in SOURCE_ROOT.rglob("*.tex") if path.is_file())
known_tex = sorted([MAIN_TEX.name, *declared_targets])
require(present_tex == known_tex, "Public source tree contains undeclared or missing TeX inputs.")

all_tex = "\n".join(target_texts[path] for path in declared_targets)
labels = re.findall(r"\\label\{([^}]+)\}", all_tex)
hyperrefs = re.findall(r"\\hyperref\[([^]]+)\]", all_tex)
agrefs = re.findall(r"\\agref\{([^}]+)\}", all_tex)
duplicate_labels = sorted(label for label, count in Counter(labels).items() if count > 1)
missing_references = sorted(set(hyperrefs) - set(labels))
unresolved_forward_fallbacks = sorted(set(agrefs) - set(labels))
oldpages = re.findall(r"\\oldpage(?:\[[^]]+\])?\{[^}]+\}", all_tex)
declared_marker_count = sum(int(row.get("historical_page_markers", 0)) for row in coverage_rows)
require(not duplicate_labels, f"Duplicate TeX labels: {duplicate_labels[:10]}")
require(not missing_references, f"Missing internal reference targets: {missing_references[:10]}")
require(len(oldpages) == declared_marker_count, "Compiled old-page count differs from manifest coverage.")
require(declared_marker_count == int(manifest["scope"]["historical_source_pages"]), "Manifest historical-page total is inconsistent.")
require(CANONICAL_DOI_URL in all_tex, "Canonical Zenodo concept DOI is absent from cumulative TeX.")
require(CANONICAL_REPOSITORY_URL in all_tex, "Canonical public repository link is absent from cumulative TeX.")
require(not re.search(r"(?i)(?:TODO|FIXME|TRANSLATION[ _-]PENDING)", all_tex), "Cumulative TeX contains an unresolved placeholder.")

back_matter_target_texts = []
for source_path in EGA2_BACK_MATTER_SOURCE_PATHS:
    target_path = str(rows_by_source[source_path]["target_path"])
    back_matter_target_texts.append(target_texts[target_path])
back_matter_tex = "\n".join(back_matter_target_texts)
require(
    re.search(r"\\oldpage\[II\]\{212\}\s*\\thispagestyle\{empty\}\s*\\mbox\{\}", back_matter_tex),
    "The sole historical blank-page declaration II|212 is absent or malformed.",
)
back_matter_markers = sorted({int(value) for value in re.findall(r"\\oldpage\[II\]\{(\d+)\}", back_matter_tex)})
require(BACK_MATTER_FIRST_MARKER[1] in back_matter_markers, "Back matter lacks historical marker II|205.")
require(BACK_MATTER_LAST_MARKER[1] in back_matter_markers, "Back matter lacks historical marker II|222.")

diagnostic_patterns = {
    "fatal_errors": re.compile(r"(?m)^! |Fatal error|Emergency stop", re.I),
    "latex_errors": re.compile(r"LaTeX Error", re.I),
    "undefined_control_sequences": re.compile(r"Undefined control sequence", re.I),
    "undefined_references": re.compile(r"undefined references|Reference .* undefined", re.I),
    "rerun_requests": re.compile(r"Rerun to get|Label\(s\) may have changed", re.I),
    "missing_characters": re.compile(r"Missing character", re.I),
    "box_warnings": re.compile(r"(?:Over|Under)full \\[hv]box", re.I),
    "multiply_defined_labels": re.compile(r"multiply defined", re.I),
}
build_log_text = BUILD_LOG.read_text(encoding="utf-8", errors="replace")
diagnostics = {name: len(pattern.findall(build_log_text)) for name, pattern in diagnostic_patterns.items()}
require(all(count == 0 for count in diagnostics.values()), f"Build diagnostics are nonzero: {diagnostics}")

# Snapshot every exact build/input identity before the sole PDF open and render.
stable_paths = [SCRIPT_PATH, MANIFEST, MAIN_TEX, PDF, BUILD_PDF, PASS2_PDF, PASS3_PDF, BUILD_LOG, *[SOURCE_ROOT / path for path in declared_targets]]
initial_identities = {relative_path(path): (path.stat().st_size, sha256(path)) for path in stable_paths}

# This exclusive marker is the irreversible beginning of the one authorized
# whole-reader QA.  Even a failure after this point may not be converted into
# a second loop by simply rerunning the script.
start_record = {
    "schema": "agko-ega2-complete-single-aggregate-pdf-qa-start-v1",
    "started_at_utc": datetime.now(timezone.utc).isoformat(),
    "reader_bytes": PDF.stat().st_size,
    "reader_sha256": sha256(PDF),
    "manifest_sha256": sha256(MANIFEST),
    "policy": "exactly one whole-reader aggregate QA; zero sectional or repeated loops",
}
with START_MARKER.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(start_record, ensure_ascii=False, indent=2) + "\n")

# Exactly one strict pypdf open and exactly one linear extraction traversal.
reader = PdfReader(str(PDF), strict=True)
page_count = len(reader.pages)
require(page_count >= declared_marker_count, "Reader page count is below the declared historical-page count.")

metadata = reader.metadata or {}
metadata_fields = {
    "title": str(metadata.get("/Title", "")),
    "author": str(metadata.get("/Author", "")),
    "subject": str(metadata.get("/Subject", "")),
    "creator": str(metadata.get("/Creator", "")),
    "producer": str(metadata.get("/Producer", "")),
}
require("대수기하학 원론" in metadata_fields["title"] and "한국어 누적판" in metadata_fields["title"], "PDF title metadata is wrong.")
require("그로텐디크" in metadata_fields["author"] and "디외도네" in metadata_fields["author"], "PDF historical-author metadata is wrong.")
require("EGA" in metadata_fields["subject"] and "NUMDAM" in metadata_fields["subject"], "PDF subject metadata is wrong.")
require(not PROFILE_PATH.search("\n".join(metadata_fields.values())), "PDF metadata contains a private profile path.")

page_texts: list[str] = []
page_geometries: list[dict] = []
external_urls: list[str] = []
link_annotations = 0
internal_links = 0
for page_index, page in enumerate(reader.pages, start=1):
    width_points = float(page.mediabox.width)
    height_points = float(page.mediabox.height)
    rotation = int(page.get("/Rotate", 0) or 0) % 360
    require(abs(width_points - 595.276) < 2.0 and abs(height_points - 841.89) < 2.0, f"Physical page {page_index} is not A4.")
    require(rotation == 0, f"Physical page {page_index} has unexpected rotation {rotation}.")
    page_geometries.append({"physical_page": page_index, "width_points": width_points, "height_points": height_points, "rotation": rotation})
    page_texts.append(page.extract_text() or "")
    for annotation_reference in page.get("/Annots", []) or []:
        annotation = annotation_reference.get_object()
        if str(annotation.get("/Subtype")) != "/Link":
            continue
        link_annotations += 1
        action = annotation.get("/A")
        if action is not None:
            action = action.get_object()
            if str(action.get("/S")) == "/URI":
                url = str(action.get("/URI"))
                validate_public_url(url)
                external_urls.append(url)
            elif str(action.get("/S")) == "/GoTo":
                internal_links += 1
        elif annotation.get("/Dest") is not None:
            internal_links += 1

extracted_text = "\n\f\n".join(page_texts) + "\n"
replacement_characters = extracted_text.count("\ufffd")
hangul_pattern = re.compile(r"[\uac00-\ud7a3]")
source_hangul = len(hangul_pattern.findall(all_tex))
extracted_hangul = len(hangul_pattern.findall(extracted_text))
require(replacement_characters == 0, "Strict pypdf extraction contains Unicode replacement characters.")
require(source_hangul > 100_000, "Cumulative source Hangul volume is implausibly low.")
require(extracted_hangul >= int(source_hangul * 0.80), "Extracted Hangul volume is implausibly low relative to cumulative source.")

# The following three deterministic subprocesses are components of this same
# aggregate pass, not separate QA loops.  Each tool is invoked exactly once.
pdfinfo_process = subprocess.run(
    [str(PDFINFO), "-enc", "UTF-8", str(PDF)],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
require(pdfinfo_process.returncode == 0, f"pdfinfo failed once with exit code {pdfinfo_process.returncode}.")
pdfinfo_text = pdfinfo_process.stdout.decode("utf-8", errors="strict").replace("\r\n", "\n")
require(not PROFILE_PATH.search(pdfinfo_text), "pdfinfo output contains a private profile path.")
pdfinfo_pages_match = re.search(r"(?m)^Pages:\s+(\d+)\s*$", pdfinfo_text)
require(pdfinfo_pages_match is not None and int(pdfinfo_pages_match.group(1)) == page_count, "pdfinfo page count differs from pypdf.")
require(re.search(r"(?m)^Encrypted:\s+no\s*$", pdfinfo_text, re.I) is not None, "pdfinfo reports an encrypted reader.")
pdfinfo_size_match = re.search(r"(?m)^Page size:\s+([0-9.]+) x ([0-9.]+) pts", pdfinfo_text)
require(pdfinfo_size_match is not None, "pdfinfo omitted the page size.")
require(abs(float(pdfinfo_size_match.group(1)) - 595.276) < 2.0, "pdfinfo page width is not A4.")
require(abs(float(pdfinfo_size_match.group(2)) - 841.89) < 2.0, "pdfinfo page height is not A4.")

pdftotext_process = subprocess.run(
    [str(PDFTOTEXT), "-enc", "UTF-8", "-layout", str(PDF), "-"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
require(pdftotext_process.returncode == 0, f"pdftotext failed once with exit code {pdftotext_process.returncode}.")
poppler_text = pdftotext_process.stdout.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
poppler_pages = poppler_text.split("\f")
if poppler_pages and not poppler_pages[-1].strip():
    poppler_pages.pop()
require(len(poppler_pages) == page_count, "Poppler extraction page count differs from the PDF.")
poppler_replacement_characters = poppler_text.count("\ufffd")
poppler_hangul = len(hangul_pattern.findall(poppler_text))
require(poppler_replacement_characters == 0, "Poppler extraction contains Unicode replacement characters.")
require(poppler_hangul >= int(source_hangul * 0.80), "Poppler Hangul volume is implausibly low relative to cumulative source.")
critical_extraction_probes = (
    "대수기하학 원론",
    "참고문헌",
    "기호 색인",
    "용어 색인",
    "정오표 및 추록",
    "국소환 달린 공간",
)
for probe in critical_extraction_probes:
    require(probe in extracted_text, f"pypdf extraction lacks the critical probe: {probe}")
    require(probe in poppler_text, f"Poppler extraction lacks the critical probe: {probe}")

pdffonts_process = subprocess.run(
    [str(PDFFONTS), str(PDF)],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
require(pdffonts_process.returncode == 0, f"pdffonts failed once with exit code {pdffonts_process.returncode}.")
pdffonts_text = pdffonts_process.stdout.decode("utf-8", errors="strict").replace("\r\n", "\n")
font_lines = pdffonts_text.splitlines()
separator_indexes = [index for index, line in enumerate(font_lines) if re.fullmatch(r"-+(?:\s+-+)*", line.strip())]
require(len(separator_indexes) == 1, "pdffonts output has an unexpected header structure.")
font_rows = []
for line in font_lines[separator_indexes[0] + 1 :]:
    if not line.strip():
        continue
    parts = line.split()
    require(len(parts) >= 8, f"Malformed pdffonts row: {line}")
    require(parts[-2].isdigit() and parts[-1].isdigit(), f"Malformed pdffonts object identifier: {line}")
    font_rows.append(
        {
            "name": parts[0],
            "embedded": parts[-5].lower(),
            "subset": parts[-4].lower(),
            "to_unicode": parts[-3].lower(),
        }
    )
require(font_rows, "pdffonts returned no font rows.")
require(all(row["embedded"] == "yes" for row in font_rows), "At least one PDF font is not embedded.")
to_unicode_yes_rows = sum(row["to_unicode"] == "yes" for row in font_rows)
require(to_unicode_yes_rows >= 28, "ToUnicode coverage regressed below the prior cumulative-reader floor.")
korean_font_rows = [row for row in font_rows if "malgun" in row["name"].lower()]
require(korean_font_rows, "The expected Korean text font is absent.")
require(all(row["to_unicode"] == "yes" for row in korean_font_rows), "A Korean text font lacks ToUnicode mapping.")
require(CANONICAL_DOI_URL in external_urls, "Canonical Zenodo concept DOI annotation is absent.")
require(CANONICAL_REPOSITORY_URL in external_urls, "Canonical repository annotation is absent.")

doi_urls = sorted(set(url for url in external_urls if re.fullmatch(r"https://doi\.org/10\.5281/zenodo\.\d+", url)))
require(CANONICAL_DOI_URL in doi_urls, "Canonical Zenodo DOI is absent from the DOI inventory.")

marker_to_physical: dict[str, int] = {}
poppler_marker_to_physical: dict[str, int] = {}
for printed_page in back_matter_markers:
    matches = [index for index, text in enumerate(page_texts, start=1) if marker_pattern("II", printed_page).search(text)]
    require(len(matches) == 1, f"Historical marker II|{printed_page} maps to {len(matches)} physical pages.")
    marker_to_physical[f"II|{printed_page}"] = matches[0]
    poppler_matches = [index for index, text in enumerate(poppler_pages, start=1) if marker_pattern("II", printed_page).search(text)]
    require(len(poppler_matches) == 1, f"Poppler maps historical marker II|{printed_page} to {len(poppler_matches)} physical pages.")
    poppler_marker_to_physical[f"II|{printed_page}"] = poppler_matches[0]
require(poppler_marker_to_physical == marker_to_physical, "Independent extractors disagree on back-matter marker pages.")
ordered_marker_physical = [marker_to_physical[f"II|{number}"] for number in back_matter_markers]
require(ordered_marker_physical == sorted(ordered_marker_physical), "Back-matter historical markers are out of physical order.")
blank_physical_page = marker_to_physical[f"{HISTORICAL_BLANK_MARKER[0]}|{HISTORICAL_BLANK_MARKER[1]}"]
back_matter_first_physical = marker_to_physical[f"{BACK_MATTER_FIRST_MARKER[0]}|{BACK_MATTER_FIRST_MARKER[1]}"]
back_matter_last_marker_physical = marker_to_physical[f"{BACK_MATTER_LAST_MARKER[0]}|{BACK_MATTER_LAST_MARKER[1]}"]
require(back_matter_first_physical < blank_physical_page <= back_matter_last_marker_physical <= page_count, "Back-matter physical boundaries are inconsistent.")

catalog = reader.trailer["/Root"]
has_page_labels = "/PageLabels" in catalog
page_labels = list(reader.page_labels) if has_page_labels else []
if has_page_labels:
    require(len(page_labels) == page_count and all(str(label) for label in page_labels), "PDF page-label tree is malformed.")
has_outlines = "/Outlines" in catalog
outline_records = flatten_outline(reader, list(reader.outline)) if has_outlines else []
if has_outlines:
    require(outline_records, "PDF advertises an outline but exposes no bookmarks.")
    require(all(row["title"] for row in outline_records), "PDF contains an untitled bookmark.")
    require(all(row["physical_page"] is None or 1 <= row["physical_page"] <= page_count for row in outline_records), "PDF bookmark destination is outside the document.")
named_destinations = len(reader.named_destinations)
require(named_destinations > 0, "PDF contains no named destinations.")

expected_width = round(595.276 / 72 * DPI)
expected_height = round(841.89 / 72 * DPI)
expected_contacts = (page_count + CONTACT_PAGES - 1) // CONTACT_PAGES
require(expected_contacts <= MAX_CONTACT_SHEETS, "Reader exceeds the bounded contact-sheet capacity.")

# The render root is the irreversible start marker for the sole aggregate pass.
RENDER_ROOT.mkdir(parents=False, exist_ok=False)
render_prefix = RENDER_ROOT / "page"
render_invocations = 0
render_invocations += 1
render_process = subprocess.run(
    [str(PDFTOPPM), "-r", str(DPI), "-png", str(PDF), str(render_prefix)],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
    check=False,
)
require(render_invocations == 1, "Internal error: bundled pdftoppm invocation count differs from one.")
require(render_process.returncode == 0, f"Bundled pdftoppm failed once with exit code {render_process.returncode}.")

render_paths: dict[int, Path] = {}
for path in RENDER_ROOT.glob("page-*.png"):
    match = re.fullmatch(r"page-(\d+)\.png", path.name)
    require(match is not None, f"Unexpected full-resolution render filename: {path.name}")
    page_number = int(match.group(1))
    require(page_number not in render_paths, f"Duplicate render page number: {page_number}")
    render_paths[page_number] = path
require(sorted(render_paths) == list(range(1, page_count + 1)), "One-shot render inventory does not exactly cover every PDF page.")

contact_width = CONTACT_COLUMNS * CONTACT_THUMBNAIL[0]
contact_height = CONTACT_ROWS * (CONTACT_THUMBNAIL[1] + CONTACT_LABEL_HEIGHT)
contact_sheet: Image.Image | None = None
contact_draw: ImageDraw.ImageDraw | None = None
contact_pages: list[int] = []
contact_records: list[dict] = []
full_resolution_back_matter_inventory: list[dict] = []
near_blank_pages: list[int] = []
render_dimensions: Counter[str] = Counter()
render_tree_hash = hashlib.sha256()
max_edge_dark = 0
minimum_ink_margin = None
minimum_block_mean = 255
maximum_ink_ratio = 0.0
maximum_pure_black_ratio = 0.0

for page_number in range(1, page_count + 1):
    image_path = render_paths[page_number]
    image_identity = file_record(image_path)
    render_tree_hash.update(f"{page_number}\t{image_path.name}\t{image_identity['bytes']}\t{image_identity['sha256']}\n".encode("ascii"))
    with Image.open(image_path) as rendered:
        rendered.load()
        require(rendered.format == "PNG", f"Physical page {page_number} is not a PNG render.")
        width, height = rendered.size
        require((width, height) == (expected_width, expected_height), f"Physical page {page_number} render dimensions are wrong: {width}x{height}")
        render_dimensions[f"{width}x{height}"] += 1
        gray = rendered.convert("L")
        histogram = gray.histogram()
        total_pixels = width * height
        ink_pixels = sum(histogram[:INK_THRESHOLD])
        pure_black_pixels = sum(histogram[:8])
        ink_ratio = ink_pixels / total_pixels
        pure_black_ratio = pure_black_pixels / total_pixels
        maximum_ink_ratio = max(maximum_ink_ratio, ink_ratio)
        maximum_pure_black_ratio = max(maximum_pure_black_ratio, pure_black_ratio)
        if ink_ratio < MIN_NONBLANK_INK_RATIO:
            near_blank_pages.append(page_number)
        require(ink_ratio <= MAX_INK_RATIO, f"Physical page {page_number} has implausibly dense ink/corruption.")
        require(pure_black_ratio <= MAX_PURE_BLACK_RATIO, f"Physical page {page_number} has implausibly large black corruption.")

        ink_mask = gray.point(lambda value: 255 if value < INK_THRESHOLD else 0)
        ink_bbox = ink_mask.getbbox()
        page_edge_dark = edge_dark_pixels(gray)
        max_edge_dark = max(max_edge_dark, page_edge_dark)
        require(page_edge_dark == 0, f"Physical page {page_number} has dark content on the outer edge (clipping heuristic).")
        if ink_bbox is not None:
            left, top, right, bottom = ink_bbox
            page_minimum_margin = min(left, top, width - right, height - bottom)
            minimum_ink_margin = page_minimum_margin if minimum_ink_margin is None else min(minimum_ink_margin, page_minimum_margin)
            require(page_minimum_margin >= MIN_INK_MARGIN_PIXELS, f"Physical page {page_number} touches the clipping guard band.")

        block_probe = gray.resize(
            (max(1, width // SOLID_BLOCK_SAMPLE_PIXELS), max(1, height // SOLID_BLOCK_SAMPLE_PIXELS)),
            Image.Resampling.BOX,
        )
        page_minimum_block_mean = block_probe.getextrema()[0]
        minimum_block_mean = min(minimum_block_mean, page_minimum_block_mean)
        require(page_minimum_block_mean > SOLID_BLOCK_MEAN_FLOOR, f"Physical page {page_number} contains a suspicious solid-black block.")

        contact_offset = (page_number - 1) % CONTACT_PAGES
        if contact_offset == 0:
            contact_sheet = Image.new("RGB", (contact_width, contact_height), "white")
            contact_draw = ImageDraw.Draw(contact_sheet)
            contact_pages = []
        require(contact_sheet is not None and contact_draw is not None, "Internal contact-sheet state is absent.")
        thumbnail = rendered.convert("RGB")
        thumbnail.thumbnail(CONTACT_THUMBNAIL, Image.Resampling.LANCZOS)
        column = contact_offset % CONTACT_COLUMNS
        row = contact_offset // CONTACT_COLUMNS
        cell_x = column * CONTACT_THUMBNAIL[0]
        cell_y = row * (CONTACT_THUMBNAIL[1] + CONTACT_LABEL_HEIGHT)
        paste_x = cell_x + (CONTACT_THUMBNAIL[0] - thumbnail.width) // 2
        paste_y = cell_y + CONTACT_LABEL_HEIGHT + (CONTACT_THUMBNAIL[1] - thumbnail.height) // 2
        contact_sheet.paste(thumbnail, (paste_x, paste_y))
        contact_draw.text((cell_x + 5, cell_y + 4), f"physical {page_number}", fill="black")
        contact_pages.append(page_number)

    if page_number >= back_matter_first_physical:
        full_resolution_back_matter_inventory.append({**image_identity, "physical_page": page_number})
    if contact_offset == CONTACT_PAGES - 1 or page_number == page_count:
        require(contact_sheet is not None, "Internal contact-sheet image is absent.")
        contact_records.append(save_contact_sheet(contact_sheet, len(contact_records) + 1, list(contact_pages)))
        contact_sheet = None
        contact_draw = None
        contact_pages = []

require(near_blank_pages == [blank_physical_page], f"Near-blank page inventory is not exactly historical II|212: {near_blank_pages}")
require(len(contact_records) == expected_contacts, "Contact-sheet count differs from the bounded plan.")
require(len(contact_records) <= MAX_CONTACT_SHEETS, "Contact-sheet output exceeded its fixed bound.")
require(full_resolution_back_matter_inventory[-1]["physical_page"] == page_count, "Final physical page is absent from the back-matter inventory.")

# Fail if any source, manifest, build output, or final reader changed during the
# one aggregate pass.  This is an identity-stability check, not a second QA.
final_identities = {relative_path(path): (path.stat().st_size, sha256(path)) for path in stable_paths}
require(final_identities == initial_identities, "A bound input or build artifact changed during aggregate QA.")

receipt = {
    "schema": "agko-ega2-complete-single-aggregate-pdf-qa-v1",
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Exactly one complete-EGA-II whole-reader QA after one aggregate integration and one mutex-serialized four-pass convergence build; zero per-section or repeated QA loops.",
    "reader": {
        **file_record(PDF),
        "pages": page_count,
        "a4_pages": page_count,
        "encrypted": bool(reader.is_encrypted),
        "strict_pypdf_opens": 1,
        "linear_page_extraction_passes": 1,
        "pass3_and_final_byte_identical": True,
        "promoted_reader_and_build_byte_identical": True,
    },
    "document_metadata_and_public_identity": {
        **metadata_fields,
        "canonical_concept_doi": CANONICAL_DOI_URL,
        "doi_annotations": doi_urls,
        "canonical_repository": CANONICAL_REPOSITORY_URL,
    },
    "source_and_manifest": {
        "aggregate_qa_script": file_record(SCRIPT_PATH),
        "manifest": file_record(MANIFEST),
        "entrypoint": file_record(MAIN_TEX),
        "canonical_driver": canonical_file_record(canonical_driver),
        "coverage_rows": len(coverage_rows),
        "declared_inputs": len(declared_targets),
        "translated_target_records": target_records,
        "private_mirror_records": private_mirror_records,
        "canonical_source_records": canonical_records,
        "labels": len(labels),
        "hyperreferences": len(hyperrefs),
        "agrefs": len(agrefs),
        "duplicate_labels": 0,
        "missing_reference_targets": 0,
        "unresolved_forward_fallbacks": unresolved_forward_fallbacks,
        "forward_fallback_policy": "Untranslated EGA III targets remain visible non-linking references through agref; no destination is fabricated.",
        "historical_page_markers": len(oldpages),
        "ega2_back_matter_sources": list(EGA2_BACK_MATTER_SOURCE_PATHS),
        "input_identity_stable_during_qa": True,
    },
    "build": {
        "builder": file_record(BUILD_SCRIPT),
        "contract": "One four-pass XeLaTeX convergence build under Global\\InterlanguageTeXSlotV1; passes 3 and 4 byte-identical.",
        "build_pdf": file_record(BUILD_PDF),
        "pass2_pdf": file_record(PASS2_PDF),
        "pass3_pdf": file_record(PASS3_PDF),
        "build_log": file_record(BUILD_LOG),
        "private_profile_paths_not_copied": len(PROFILE_PATH.findall(build_log_text)),
        "diagnostics": diagnostics,
    },
    "extraction": {
        "method": "pypdf strict mode plus one independent Poppler pdftotext invocation; each physical page extracted exactly once in document order by each extractor",
        "utf8_text_sha256": text_sha256(extracted_text),
        "characters": len(extracted_text),
        "source_hangul_syllables": source_hangul,
        "extracted_hangul_syllables": extracted_hangul,
        "source_to_extracted_hangul_ratio": extracted_hangul / source_hangul,
        "replacement_characters": replacement_characters,
        "poppler_utf8_text_sha256": text_sha256(poppler_text),
        "poppler_characters": len(poppler_text),
        "poppler_pages": len(poppler_pages),
        "poppler_hangul_syllables": poppler_hangul,
        "poppler_source_to_extracted_hangul_ratio": poppler_hangul / source_hangul,
        "poppler_replacement_characters": poppler_replacement_characters,
        "critical_probes_independently_present": list(critical_extraction_probes),
    },
    "pdfinfo": {
        "tool": "[CODEX_PRIMARY_RUNTIME]/dependencies/native/poppler/Library/bin/pdfinfo.exe",
        "bytes": PDFINFO.stat().st_size,
        "sha256": sha256(PDFINFO),
        "invocations": 1,
        "output_sha256": text_sha256(pdfinfo_text),
        "page_count_matches": True,
        "a4_matches": True,
        "encrypted": False,
    },
    "fonts": {
        "tool": "[MIKTEX]/bin/x64/pdffonts.exe",
        "bytes": PDFFONTS.stat().st_size,
        "sha256": sha256(PDFFONTS),
        "invocations": 1,
        "font_rows": len(font_rows),
        "all_embedded": True,
        "to_unicode_yes_rows": to_unicode_yes_rows,
        "korean_font_rows": korean_font_rows,
        "korean_fonts_have_to_unicode": True,
        "inventory_sha256": text_sha256(pdffonts_text),
    },
    "navigation": {
        "named_destinations": named_destinations,
        "link_annotations": link_annotations,
        "internal_links": internal_links,
        "external_links": len(external_urls),
        "page_labels_present": has_page_labels,
        "page_labels": page_labels,
        "bookmarks_present": has_outlines,
        "bookmark_count": len(outline_records),
        "bookmarks": outline_records,
    },
    "historical_back_matter": {
        "marker_to_physical_page": marker_to_physical,
        "declared_blank": "II|212",
        "declared_blank_physical_page": blank_physical_page,
        "first_physical_page": back_matter_first_physical,
        "last_historical_marker_physical_page": back_matter_last_marker_physical,
        "final_physical_page": page_count,
        "full_resolution_final_and_back_matter_page_inventory": full_resolution_back_matter_inventory,
    },
    "single_aggregate_render": {
        "bundled_renderer": {
            "path": "[CODEX_PRIMARY_RUNTIME]/dependencies/native/poppler/Library/bin/pdftoppm.exe",
            "bytes": PDFTOPPM.stat().st_size,
            "sha256": sha256(PDFTOPPM),
        },
        "invocations": render_invocations,
        "dpi": DPI,
        "pages_rendered": page_count,
        "render_dimensions": dict(render_dimensions),
        "full_resolution_render_tree_sha256": render_tree_hash.hexdigest().upper(),
        "near_blank_physical_pages": near_blank_pages,
        "allowed_near_blank_physical_pages": [blank_physical_page],
        "heuristics": {
            "ink_threshold": INK_THRESHOLD,
            "minimum_nonblank_ink_ratio": MIN_NONBLANK_INK_RATIO,
            "maximum_observed_ink_ratio": maximum_ink_ratio,
            "maximum_allowed_ink_ratio": MAX_INK_RATIO,
            "maximum_observed_pure_black_ratio": maximum_pure_black_ratio,
            "maximum_allowed_pure_black_ratio": MAX_PURE_BLACK_RATIO,
            "edge_band_pixels": EDGE_BAND_PIXELS,
            "maximum_observed_edge_dark_pixels": max_edge_dark,
            "minimum_observed_ink_margin_pixels": minimum_ink_margin,
            "solid_black_block_sample_pixels": SOLID_BLOCK_SAMPLE_PIXELS,
            "minimum_observed_block_mean": minimum_block_mean,
            "minimum_allowed_block_mean_exclusive": SOLID_BLOCK_MEAN_FLOOR,
            "result": "PASS_DIMENSIONS_BLANK_CLIPPING_BLACK_BLOCK_AND_CORRUPTION_HEURISTICS",
        },
        "contact_sheet_bound": MAX_CONTACT_SHEETS,
        "contact_sheets": contact_records,
    },
    "policy": {
        "small_section_qa_loops": 0,
        "whole_reader_qa_loops": 1,
        "render_process_invocations": 1,
        "pdfinfo_process_invocations": 1,
        "pdftotext_process_invocations": 1,
        "pdffonts_process_invocations": 1,
        "per_section_scripts_invoked": 0,
        "recursive_self_invocations": 0,
        "publication_actions": 0,
        "deletions": 0,
        "rerun_guard": "The script refuses execution if the exclusive start marker, unique receipt, or unique render root exists.",
        "start_marker": file_record(START_MARKER),
    },
    "result": "PASS_EGA2_COMPLETE_SINGLE_AGGREGATE_PDF_QA",
}

serialized_receipt = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
require(not PROFILE_PATH.search(serialized_receipt), "Sanitized receipt would contain a private profile path.")
require(not re.search(r"(?i)(?:access[_-]?token|api[_-]?key|password|secret)[\"']?\s*[:=]\s*[\"'][^\"']+", serialized_receipt), "Sanitized receipt would contain credential-like material.")
with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(serialized_receipt)

print(json.dumps({
    "result": receipt["result"],
    "reader": receipt["reader"],
    "rendered_pages": page_count,
    "contact_sheets": len(contact_records),
    "receipt": file_record(OUTPUT),
}, ensure_ascii=True))
