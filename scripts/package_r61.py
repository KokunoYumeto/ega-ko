"""Create the exact Korean cumulative EGA R61 release without rebuilding or rerunning QA."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
WORK = REPO.parent.parent
BASE = REPO / "release/2026-09-07-r48"
FINAL = REPO / "release/2026-09-07-r61"
FIXED_TIME = (2026, 9, 7, 0, 0, 0)

READER_ID = (1_618_555, "ED7DE0C7330DD035CA7389B6435C9C7AB16A815237C0750CD241A235DF80DEC6")
C2S1_ID = (181_163, "893C8E4D68134E0F03479D760F916AADD2DA4687CFF8E04DAA300C355023EF9D")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_id(path: Path) -> dict[str, int | str]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": digest(data)}


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def build_archive(base: Path, output: Path, overrides: dict[str, Path]) -> None:
    missing = [str(path) for path in overrides.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"archive inputs missing: {missing}")
    with zipfile.ZipFile(base, "r") as source, zipfile.ZipFile(
        output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True
    ) as target:
        inherited = {entry.filename for entry in source.infolist() if not entry.is_dir()}
        for entry in sorted((item for item in source.infolist() if not item.is_dir()), key=lambda item: item.filename):
            if entry.filename in overrides:
                continue
            target.writestr(zip_info(entry.filename), source.read(entry.filename), compresslevel=9)
        for name, path in sorted(overrides.items()):
            target.writestr(zip_info(name), path.read_bytes(), compresslevel=9)
    expected = inherited | set(overrides)
    with zipfile.ZipFile(output, "r") as check:
        entries = [item for item in check.infolist() if not item.is_dir()]
        names = [item.filename for item in entries]
        if len(names) != len(set(names)) or set(names) != expected:
            raise RuntimeError(f"archive entry-set mismatch: {output}")
        for entry in entries:
            data = check.read(entry.filename)
            if len(data) != entry.file_size:
                raise RuntimeError(f"archive readback size mismatch: {entry.filename}")
        for name, path in overrides.items():
            if check.read(name) != path.read_bytes():
                raise RuntimeError(f"archive override mismatch: {name}")


def archive_inventory(path: Path) -> dict[str, int | str | bool]:
    rows: list[str] = []
    total = 0
    with zipfile.ZipFile(path, "r") as archive:
        entries = sorted((item for item in archive.infolist() if not item.is_dir()), key=lambda item: item.filename)
        for entry in entries:
            data = archive.read(entry.filename)
            if len(data) != entry.file_size:
                raise RuntimeError(f"archive readback size mismatch: {entry.filename}")
            total += len(data)
            rows.append(f"{entry.filename}\0{len(data)}\0{digest(data)}\n")
    return {
        "path": path.name,
        **file_id(path),
        "entries": len(rows),
        "uncompressed_bytes": total,
        "inventory_sha256": digest("".join(rows).encode("utf-8")),
        "single_postwrite_entry_readback": True,
    }


def main() -> None:
    if FINAL.exists():
        raise RuntimeError(f"refusing to overwrite existing release: {FINAL}")
    for required in (
        BASE / "01_EGA_ko_EDITABLE_SOURCES.zip",
        BASE / "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip",
        REPO / "reader/00_EGA_ko_CUMULATIVE_READER.pdf",
        REPO / "source/c2s1.tex",
    ):
        if not required.is_file():
            raise RuntimeError(f"required predecessor/current input missing: {required}")
    if tuple(file_id(REPO / "reader/00_EGA_ko_CUMULATIVE_READER.pdf").values()) != READER_ID:
        raise RuntimeError("current cumulative reader identity mismatch")
    if tuple(file_id(REPO / "source/c2s1.tex").values()) != C2S1_ID:
        raise RuntimeError("current cumulative EGA II target identity mismatch")

    FINAL.mkdir()
    reader_out = FINAL / "00_EGA_ko_CUMULATIVE_READER.pdf"
    shutil.copyfile(REPO / "reader/00_EGA_ko_CUMULATIVE_READER.pdf", reader_out)

    source_overrides = {
        ".zenodo.json": REPO / ".zenodo.json",
        "CITATION.cff": REPO / "CITATION.cff",
        "README.md": REPO / "README.md",
        "build/BUILD.ps1": REPO / "build/BUILD.ps1",
        "source/CUMULATIVE_INPUTS.json": REPO / "source/CUMULATIVE_INPUTS.json",
        "source/c2s1.tex": REPO / "source/c2s1.tex",
        "source/front.tex": REPO / "source/front.tex",
        "r61-github-release-notes.md": REPO / "r61-github-release-notes.md",
        "scripts/package_r61.py": REPO / "scripts/package_r61.py",
        "scripts/single_aggregate_r61.py": WORK / "scripts/single_aggregate_r61.py",
    }
    for revision in range(49, 62):
        name = f"r{revision}-c2s1-continuation.tex"
        source_overrides[f"candidates/{name}"] = WORK / "candidates" / name
    source_zip = FINAL / "01_EGA_ko_EDITABLE_SOURCES.zip"
    build_archive(BASE / source_zip.name, source_zip, source_overrides)

    evidence_overrides: dict[str, Path] = {
        "index/units.jsonl": REPO / "evidence/index/units.jsonl",
        "build-r61.log": REPO / "evidence/build-r61.log",
        "r61-extract-pypdf.txt": REPO / "evidence/r61-extract-pypdf.txt",
        "r61-extract-poppler.txt": REPO / "evidence/r61-extract-poppler.txt",
        "r61-pdffonts.txt": REPO / "evidence/r61-pdffonts.txt",
        "controls/R49_R61_SINGLE_BATCH_INTEGRATION_20260907.json": WORK / "controls/R49_R61_SINGLE_BATCH_INTEGRATION_20260907.json",
        "controls/R61_EGA1_D68_SOURCE_RECONCILIATION.json": WORK / "controls/R61_EGA1_D68_SOURCE_RECONCILIATION.json",
        "controls/R61_SINGLE_AGGREGATE_PDF_QA_20260907.json": REPO / "evidence/controls/R61_SINGLE_AGGREGATE_PDF_QA_20260907.json",
    }
    for page in list(range(1, 9)) + list(range(248, 265)):
        name = f"r61-p-{page:03d}.png"
        evidence_overrides[f"render/{name}"] = REPO / "evidence/render" / name
    for contact in range(1, 5):
        name = f"r61-contact-{contact:02d}.png"
        evidence_overrides[f"render/{name}"] = REPO / "evidence/render" / name
    evidence_zip = FINAL / "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip"
    build_archive(BASE / evidence_zip.name, evidence_zip, evidence_overrides)

    rows = []
    for name in (
        "00_EGA_ko_CUMULATIVE_READER.pdf",
        "01_EGA_ko_EDITABLE_SOURCES.zip",
        "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip",
    ):
        path = FINAL / name
        rows.append({"name": name, **file_id(path)})
    manifest = "filename\tbytes\tsha256\n" + "".join(
        f"{row['name']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows
    )
    manifest_path = FINAL / "03_EGA_ko_SHA256_MANIFEST.txt"
    manifest_path.write_text(manifest, encoding="utf-8", newline="\n")
    public_files = rows + [{"name": manifest_path.name, **file_id(manifest_path)}]

    receipt = {
        "schema": "ag-ko-package-receipt-v9",
        "version": "2026-09-07-r61",
        "created_at": "2026-09-07T19:25:00+02:00",
        "exact_doi": "10.5281/zenodo.22647516",
        "concept_doi": "10.5281/zenodo.21921513",
        "coverage": {
            "terminal": "EGA II §2.9.5 / canonical lines1-4040 / complete Section 2",
            "next": "line4042 / Section 3; line4041 blank",
            "historical_markers": 253,
            "no_completion_claim": True,
        },
        "public_artifact_count": 4,
        "files": [{"order": index, **row} for index, row in enumerate(public_files)],
        "source_archive": archive_inventory(source_zip),
        "evidence_archive": archive_inventory(evidence_zip),
        "reader": {"path": reader_out.name, **file_id(reader_out), "pages": 264},
        "source_manifest": {"path": "source/CUMULATIVE_INPUTS.json", **file_id(REPO / "source/CUMULATIVE_INPUTS.json")},
        "integration_control": {"path": "controls/R49_R61_SINGLE_BATCH_INTEGRATION_20260907.json", **file_id(WORK / "controls/R49_R61_SINGLE_BATCH_INTEGRATION_20260907.json")},
        "source_reconciliation_control": {"path": "controls/R61_EGA1_D68_SOURCE_RECONCILIATION.json", **file_id(WORK / "controls/R61_EGA1_D68_SOURCE_RECONCILIATION.json")},
        "aggregate_qa_control": {"path": "controls/R61_SINGLE_AGGREGATE_PDF_QA_20260907.json", **file_id(REPO / "evidence/controls/R61_SINGLE_AGGREGATE_PDF_QA_20260907.json")},
        "workflow": {
            "translation_units_integrated_in_one_batch": "R49-R61",
            "tex_builds_for_this_reader": 1,
            "whole_reader_qa_passes": 1,
            "small_section_qa_loops": 0,
            "package_constructions": 1,
            "package_entry_readbacks": 1,
        },
        "result": "PASS_R61_LOCAL_PACKAGE_SINGLE_BUILD_SINGLE_AGGREGATE_QA",
    }
    receipt_path = FINAL / "PACKAGE_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"release": str(FINAL), "files": public_files, "receipt": file_id(receipt_path), "result": receipt["result"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
