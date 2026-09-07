"""Create the exact Korean cumulative EGA R48 release without rebuilding or rerunning QA."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
WORK = REPO.parent.parent
BASE = REPO / "release/2026-09-06-r39"
FINAL = REPO / "release/2026-09-07-r48"
FIXED_TIME = (2026, 9, 7, 0, 0, 0)

READER_ID = (1542495, "668E8008D24C5B676D18BCA933D3DD57159877F2B45BD778EA1CE28204A4623E")


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
        for entry in sorted((x for x in source.infolist() if not x.is_dir()), key=lambda x: x.filename):
            if entry.filename in overrides:
                continue
            target.writestr(zip_info(entry.filename), source.read(entry.filename), compresslevel=9)
        for name, path in sorted(overrides.items()):
            target.writestr(zip_info(name), path.read_bytes(), compresslevel=9)
    expected = inherited | set(overrides)
    with zipfile.ZipFile(output, "r") as check:
        names = [x.filename for x in check.infolist() if not x.is_dir()]
        if len(names) != len(set(names)) or set(names) != expected:
            raise RuntimeError(f"archive entry-set mismatch: {output}")
        for name, path in overrides.items():
            if check.read(name) != path.read_bytes():
                raise RuntimeError(f"archive override mismatch: {name}")


def archive_inventory(path: Path) -> dict[str, int | str]:
    rows: list[str] = []
    total = 0
    with zipfile.ZipFile(path, "r") as archive:
        entries = sorted((x for x in archive.infolist() if not x.is_dir()), key=lambda x: x.filename)
        for entry in entries:
            data = archive.read(entry.filename)
            if len(data) != entry.file_size:
                raise RuntimeError(f"archive readback size mismatch: {entry.filename}")
            total += len(data)
            rows.append(f"{entry.filename}\0{len(data)}\0{digest(data)}\n")
    identity = file_id(path)
    return {
        "path": path.name,
        **identity,
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
    ):
        if not required.is_file():
            raise RuntimeError(f"required predecessor/current input missing: {required}")
    if tuple(file_id(REPO / "reader/00_EGA_ko_CUMULATIVE_READER.pdf").values()) != READER_ID:
        raise RuntimeError("current cumulative reader identity mismatch")

    FINAL.mkdir()
    reader_out = FINAL / "00_EGA_ko_CUMULATIVE_READER.pdf"
    shutil.copyfile(REPO / "reader/00_EGA_ko_CUMULATIVE_READER.pdf", reader_out)

    source_overrides = {
        ".zenodo.json": REPO / ".zenodo.json",
        "README.md": REPO / "README.md",
        "build/BUILD.ps1": REPO / "build/build.ps1",
        "source/CUMULATIVE_INPUTS.json": REPO / "source/CUMULATIVE_INPUTS.json",
        "source/c2s1.tex": REPO / "source/c2s1.tex",
        "source/front.tex": REPO / "source/front.tex",
        "r48-github-release-notes.md": REPO / "r48-github-release-notes.md",
        "scripts/package_r48.py": REPO / "scripts/package_r48.py",
        "candidates/r40-c2s1-continuation-homogeneous-reseal.tex": WORK / "candidates/r40-c2s1-continuation-homogeneous-reseal.tex",
        "candidates/r41-c2s1-continuation-homogeneous-reseal.tex": WORK / "candidates/r41-c2s1-continuation-homogeneous-reseal.tex",
        "candidates/r42-c2s1-continuation-homogeneous-reseal.tex": WORK / "candidates/r42-c2s1-continuation-homogeneous-reseal.tex",
        "candidates/r43-c2s1-continuation-homogeneous-reseal.tex": WORK / "candidates/r43-c2s1-continuation-homogeneous-reseal.tex",
        "candidates/r44-c2s1-continuation.tex": WORK / "candidates/r44-c2s1-continuation.tex",
        "candidates/r45-c2s1-continuation.tex": WORK / "candidates/r45-c2s1-continuation.tex",
        "candidates/r46-c2s1-continuation.tex": WORK / "candidates/r46-c2s1-continuation.tex",
        "candidates/r47-c2s1-continuation.tex": WORK / "candidates/r47-c2s1-continuation.tex",
        "candidates/r48-c2s1-continuation.tex": WORK / "candidates/r48-c2s1-continuation.tex",
    }
    source_zip = FINAL / "01_EGA_ko_EDITABLE_SOURCES.zip"
    build_archive(BASE / source_zip.name, source_zip, source_overrides)

    control_names = (
        "R40_HOMOGENEOUS_IDEAL_WORDING_RESEAL_20260906.json",
        "R40_INTEGRATION_20260907.json",
        "R40_LIVE_ADMISSION_20260907.json",
        "R40_R48_SINGLE_BATCH_INTEGRATION_20260907.json",
        "R40_TRANSLATION_ADMISSION.json",
        "R40_ZENODO_DRAFT_RESERVATION.json",
        "R41_HOMOGENEOUS_IDEAL_WORDING_RESEAL_20260906.json",
        "R41_TRANSLATION_ADMISSION.json",
        "R42_HOMOGENEOUS_IDEAL_WORDING_RESEAL_20260906.json",
        "R42_TRANSLATION_ADMISSION.json",
        "R42_TRANSLATION_CANDIDATE_RESEAL_20260906.json",
        "R42_TRANSLATION_CANDIDATE_RESEAL_V2_20260906.json",
        "R42_TRANSLATION_CANDIDATE_RESEAL_V3_20260906.json",
        "R43_HOMOGENEOUS_IDEAL_WORDING_RESEAL_20260906.json",
        "R43_TRANSLATION_ADMISSION.json",
        "R44_TRANSLATION_ADMISSION.json",
        "R45_TRANSLATION_ADMISSION.json",
        "R46_TRANSLATION_ADMISSION.json",
        "R47_STACKS_TERMINOLOGY_COORDINATION.json",
        "R47_TRANSLATION_ADMISSION.json",
        "R48_SINGLE_AGGREGATE_PDF_QA_20260907.json",
        "R48_TRANSLATION_ADMISSION.json",
        "EGA_CORRECTION_JSON_BACKFILL_FOLLOWUP_AUDIT_20260907.json",
    )
    evidence_overrides: dict[str, Path] = {
        "index/units.jsonl": REPO / "evidence/index/units.jsonl",
        "build-r48.log": REPO / "evidence/build-r48.log",
        "r48-extract-pypdf.txt": REPO / "evidence/r48-extract-pypdf.txt",
        "r48-extract-poppler.txt": REPO / "evidence/r48-extract-poppler.txt",
        "r48-pdffonts.txt": REPO / "evidence/r48-pdffonts.txt",
    }
    for name in control_names:
        source = REPO / "evidence/controls" / name
        if not source.is_file():
            raise RuntimeError(f"required R48 control missing: {source}")
        evidence_overrides[f"controls/{name}"] = source
    for page in range(238, 250):
        name = f"r48-p-{page}.png"
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
        identity = file_id(path)
        rows.append({"name": name, **identity})
    manifest = "filename\tbytes\tsha256\n" + "".join(
        f"{row['name']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows
    )
    manifest_path = FINAL / "03_EGA_ko_SHA256_MANIFEST.txt"
    manifest_path.write_text(manifest, encoding="utf-8", newline="\n")
    public_files = rows + [{"name": manifest_path.name, **file_id(manifest_path)}]

    source_inventory = archive_inventory(source_zip)
    evidence_inventory = archive_inventory(evidence_zip)
    receipt = {
        "schema": "ag-ko-package-receipt-v8",
        "version": "2026-09-07-r48",
        "created_at": "2026-09-07T17:20:00+02:00",
        "exact_doi": "10.5281/zenodo.22645017",
        "concept_doi": "10.5281/zenodo.21921513",
        "coverage": {
            "terminal": "EGA II §2.5.12 / canonical lines1-2694",
            "next": "line2696 / Proposition2.5.13; line2695 blank",
            "historical_markers": 238,
            "no_completion_claim": True,
        },
        "public_artifact_count": 4,
        "files": [{"order": i, **row} for i, row in enumerate(public_files)],
        "source_archive": source_inventory,
        "evidence_archive": evidence_inventory,
        "reader": {"path": reader_out.name, **file_id(reader_out), "pages": 249},
        "source_manifest": {"path": "source/CUMULATIVE_INPUTS.json", **file_id(REPO / "source/CUMULATIVE_INPUTS.json")},
        "integration_control": {"path": "controls/R40_R48_SINGLE_BATCH_INTEGRATION_20260907.json", **file_id(WORK / "controls/R40_R48_SINGLE_BATCH_INTEGRATION_20260907.json")},
        "aggregate_qa_control": {"path": "controls/R48_SINGLE_AGGREGATE_PDF_QA_20260907.json", **file_id(WORK / "controls/R48_SINGLE_AGGREGATE_PDF_QA_20260907.json")},
        "workflow": {
            "translation_units_integrated_in_one_batch": "R40-R48",
            "tex_builds_for_this_reader": 1,
            "whole_reader_qa_passes": 1,
            "per_unit_qa_loops": 0,
            "package_constructions": 1,
            "package_entry_readbacks": 1,
        },
        "result": "PASS_R48_LOCAL_PACKAGE_SINGLE_BUILD_SINGLE_AGGREGATE_QA",
    }
    receipt_path = FINAL / "PACKAGE_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"release": str(FINAL), "files": public_files, "receipt": file_id(receipt_path), "result": receipt["result"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
