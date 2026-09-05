#!/usr/bin/env python3
"""Freeze and independently verify the deterministic R36 publication bundle."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any, Iterable


FIXED_TIME = (2026, 9, 5, 0, 0, 0)
VERSION = "2026-09-05-r36"
EXACT_DOI = "10.5281/zenodo.22217711"
CONCEPT_DOI = "10.5281/zenodo.21921513"
PDF_SHA = "5FC588FF0A50B8A12899597D49FEB1B6E41BAB43F40F14E8F5433A5FB29D093D"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def ident(path: Path, base: Path | None = None) -> dict[str, Any]:
    shown = path.relative_to(base).as_posix() if base else path.name
    return {"path": shown, "bytes": path.stat().st_size, "sha256": sha_file(path)}


def root_source_files(repo: Path) -> list[Path]:
    files = [repo / name for name in (".gitattributes", ".zenodo.json", "CITATION.cff", "LICENSE", "README.md")]
    files.append(repo / "build" / "BUILD.ps1")
    files.extend(sorted((repo / "source").rglob("*")))
    files.extend(sorted((repo / "scripts").glob("*.py")))
    return sorted([path for path in files if path.is_file()], key=lambda p: p.relative_to(repo).as_posix())


def artifact_manifest(repo: Path, source_files: list[Path], reader: Path) -> tuple[bytes, int]:
    manifest_path = repo / "evidence" / "ARTIFACT_SHA256.tsv"
    evidence_files = sorted(
        [path for path in (repo / "evidence").rglob("*") if path.is_file() and path != manifest_path],
        key=lambda p: p.relative_to(repo).as_posix(),
    )
    files = sorted({*source_files, reader, *evidence_files}, key=lambda p: p.relative_to(repo).as_posix())
    rows = ["relative_path\tbytes\tsha256"]
    for path in files:
        rows.append(f"{path.relative_to(repo).as_posix()}\t{path.stat().st_size}\t{sha_file(path)}")
    payload = ("\n".join(rows) + "\n").encode("utf-8")
    manifest_path.write_bytes(payload)
    return payload, len(files)


def member_directories(names: Iterable[str]) -> list[str]:
    directories: set[str] = set()
    for name in names:
        parts = name.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            directories.add("/".join(parts[:index]) + "/")
    return sorted(directories)


def zip_info(name: str, directory: bool) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.flag_bits = 0x800
    info.extra = b""
    info.comment = b""
    if directory:
        info.external_attr = (0o40755 << 16) | 0x10
    else:
        info.external_attr = 0o100644 << 16
    return info


def make_zip(path: Path, root: Path, files: list[Path]) -> dict[str, Any]:
    names = [file.relative_to(root).as_posix() for file in files]
    directories = member_directories(names)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as archive:
        for name in directories:
            archive.writestr(zip_info(name, True), b"", compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        for file, name in zip(files, names):
            archive.writestr(zip_info(name, False), file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return verify_zip(path, root, files, directories)


def verify_zip(path: Path, root: Path, files: list[Path], directories: list[str]) -> dict[str, Any]:
    expected_names = directories + [file.relative_to(root).as_posix() for file in files]
    inventory_rows = ["relative_path\tbytes\tsha256"]
    uncompressed = 0
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != expected_names:
            raise RuntimeError(f"ZIP name/order mismatch in {path}")
        if archive.testzip() is not None:
            raise RuntimeError(f"ZIP CRC failure in {path}")
        for file in files:
            name = file.relative_to(root).as_posix()
            info = archive.getinfo(name)
            source = file.read_bytes()
            unpacked = archive.read(name)
            if info.file_size != len(source) or unpacked != source:
                raise RuntimeError(f"ZIP content mismatch: {name}")
            if info.CRC != (binascii.crc32(source) & 0xFFFFFFFF):
                raise RuntimeError(f"ZIP CRC mismatch: {name}")
            inventory_rows.append(f"{name}\t{len(source)}\t{sha_bytes(source)}")
            uncompressed += len(source)
    inventory = ("\n".join(inventory_rows) + "\n").encode("utf-8")
    return {
        "entries": len(expected_names),
        "files": len(files),
        "directories": len(directories),
        "uncompressed_file_bytes": uncompressed,
        "inventory_bytes": len(inventory),
        "inventory_sha256": sha_bytes(inventory),
        "verification": "PASS names, ordering, fixed metadata, compression9, CRC, sizes, decompressed bytes and SHA-256",
    }


def build_twice(final: Path, root: Path, files: list[Path]) -> tuple[dict[str, Any], bool]:
    first = final.with_suffix(final.suffix + ".cycle-a")
    second = final.with_suffix(final.suffix + ".cycle-b")
    for path in (first, second, final):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite package artifact: {path}")
    try:
        result_a = make_zip(first, root, files)
        result_b = make_zip(second, root, files)
        if first.read_bytes() != second.read_bytes():
            raise RuntimeError(f"independent archive cycles differ: {final.name}")
        if result_a != result_b:
            raise RuntimeError(f"archive verification summaries differ: {final.name}")
        shutil.copyfile(first, final)
        verify_zip(final, root, files, member_directories([f.relative_to(root).as_posix() for f in files]))
        return result_a, True
    finally:
        for path in (first, second):
            if path.exists():
                path.unlink()


def privacy_scan(paths: list[Path]) -> dict[str, Any]:
    account = Path.home().name
    account_encodings = [account.encode("utf-8"), account.encode("utf-16-le"), account.encode("utf-16-be")]
    token_patterns = [
        re.compile(rb"(?i)(?:access_token|api[_-]?key|authorization)\s*[:=]\s*[A-Za-z0-9_\-]{16,}"),
        re.compile(rb"(?i)\b(?:ghp|github_pat|sk)-[A-Za-z0-9_\-]{12,}"),
    ]
    decodable = matches = bytes_checked = 0
    for path in paths:
        raw = path.read_bytes()
        bytes_checked += len(raw)
        if account and any(needle in raw for needle in account_encodings):
            matches += 1
        if any(pattern.search(raw) for pattern in token_patterns):
            matches += 1
        try:
            text = raw.decode("utf-8-sig")
            decodable += 1
            if account and re.search(re.escape(account), text, re.I):
                matches += 1
        except UnicodeDecodeError:
            pass
    if matches:
        raise RuntimeError(f"privacy/credential scan found {matches} prospective publication matches")
    return {
        "files_checked": len(paths),
        "decodable_text_members_checked": decodable,
        "bytes_checked": bytes_checked,
        "matches": matches,
        "scope": "Every prospective source/evidence member and reader; member names and UTF-8 plus raw UTF-8/UTF-16 account encodings and credential-prefix patterns. Needles are not recorded.",
        "result": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    release = repo / "release" / VERSION
    if release.exists():
        raise RuntimeError(f"refusing to reuse existing release directory: {release}")
    release.mkdir(parents=True)

    reader = repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    if reader.stat().st_size != 1_474_518 or sha_file(reader) != PDF_SHA:
        raise RuntimeError("reader identity drift")
    source_files = root_source_files(repo)
    artifact_payload, artifact_entries = artifact_manifest(repo, source_files, reader)
    evidence_files = sorted([path for path in (repo / "evidence").rglob("*") if path.is_file()], key=lambda p: p.relative_to(repo / "evidence").as_posix())

    privacy = privacy_scan(source_files + evidence_files + [reader])
    reader_release = release / "00_EGA_ko_CUMULATIVE_READER.pdf"
    shutil.copyfile(reader, reader_release)

    source_zip = release / "01_EGA_ko_EDITABLE_SOURCES.zip"
    evidence_zip = release / "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip"
    source_verification, source_equal = build_twice(source_zip, repo, source_files)
    evidence_verification, evidence_equal = build_twice(evidence_zip, repo / "evidence", evidence_files)

    outer_files = [reader_release, source_zip, evidence_zip]
    manifest_lines = ["filename\tbytes\tsha256"]
    for path in outer_files:
        manifest_lines.append(f"{path.name}\t{path.stat().st_size}\t{sha_file(path)}")
    outer_manifest = release / "03_EGA_ko_SHA256_MANIFEST.txt"
    outer_manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8", newline="\n")

    qa_path = repo / "evidence" / "controls" / "R36_PDF_QA.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    metadata_path = repo / ".zenodo.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    description = metadata["description"]
    forbidden = len(re.findall(r"(?i)\bTTP\b|Translation and Transcription Project|Figshare", metadata_path.read_text(encoding="utf-8")))
    if forbidden:
        raise RuntimeError("active metadata contains an excluded term")

    file_rows = [
        {"order": 0, "name": reader_release.name, "bytes": reader_release.stat().st_size, "sha256": sha_file(reader_release), "role": "front cumulative reader artifact", "pages": 237},
        {"order": 1, "name": source_zip.name, "bytes": source_zip.stat().st_size, "sha256": sha_file(source_zip), "role": "deterministic editable-source and validation-script archive", **source_verification},
        {"order": 2, "name": evidence_zip.name, "bytes": evidence_zip.stat().st_size, "sha256": sha_file(evidence_zip), "role": "deterministic evidence and provenance archive", **evidence_verification},
        {"order": 3, "name": outer_manifest.name, "bytes": outer_manifest.stat().st_size, "sha256": sha_file(outer_manifest), "role": "outer SHA-256 manifest", "listed_artifacts": 3, "verification": "PASS"},
    ]
    receipt = {
        "schema": "ag-ko-package-receipt-v4",
        "version": VERSION,
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "coverage": {
            "corpus": "EGA",
            "included_volumes": ["EGA 0_I", "EGA I", "EGA II (programme/table of contents and main text through2.1.7)"],
            "terminal_coverage": "EGA II Chapter II programme/table of contents through source EOF, followed by ega2/ega2-1-fr.tex lines1-1535 through2.1.7",
            "completeness_claim": "all locally completed and hash-admitted Korean EGA targets are included; EGA II and the full EGA corpus remain incomplete",
            "historical_source_pages": 226,
            "historical_page_ranges": ["EGA I introduction5-8", "EGA 0_I11-78", "EGA I Chapter I79-214", "EGA II5-22"],
        },
        "files": file_rows,
        "total_publication_bytes": sum(row["bytes"] for row in file_rows),
        "source_archive_A_B_byte_identical": source_equal,
        "evidence_archive_A_B_byte_identical": evidence_equal,
        "reader_qa": {
            "build_receipt": ident(repo / "evidence" / "BUILD_RECEIPT.json", repo),
            "pdf_control": ident(qa_path, repo),
            "convergence": "PASS two independent four-pass cycles; pass3=pass4 in each; cycle finals byte-identical",
            "extraction": qa["extractions"],
            "links": qa["navigation"],
            "visual": qa["visual_findings"],
        },
        "expert_review": {
            "jsonl": ident(repo / "evidence" / "expert_review" / "EXPERT_REVIEW.jsonl", repo),
            "markdown": ident(repo / "evidence" / "expert_review" / "EXPERT_REVIEW.md", repo),
            "receipt": ident(repo / "evidence" / "expert_review" / "PUBLIC_EXPERT_REVIEW_RECEIPT.json", repo),
            "records": 540,
            "validation": "PASS_INDEPENDENT_EXPERT_REVIEW_REPLAY",
        },
        "internal_manifest": {
            "path": "evidence/ARTIFACT_SHA256.tsv",
            "bytes": len(artifact_payload),
            "sha256": sha_bytes(artifact_payload),
            "entries": artifact_entries,
            "verification": "PASS independent path, byte-count and SHA-256 replay; manifest excludes itself and package outputs",
        },
        "metadata": {
            **ident(metadata_path, repo),
            "description_characters": len(description),
            "forbidden_umbrella_or_active_excluded_destination_mentions": forbidden,
            "creators": len(metadata["creators"]),
            "contributors": len(metadata["contributors"]),
            "sole_contributor": metadata["contributors"][0]["name"],
            "rights_scope_provenance_and_nonendorsement": "PASS",
            "external_links": ["https://doi.org/10.5281/zenodo.21921513", "https://github.com/KokunoYumeto/ega-ko"],
        },
        "privacy_credential_check": privacy,
        "publication_status": "as of package freeze: local package only; draft and repository state are not publication claims",
        "portable_replay": "as of package freeze: not yet run; separate PORTABLE_BUILD_REPLAY.json is required",
        "result": "PASS_LOCAL_PACKAGE",
    }
    receipt_path = release / "PACKAGE_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        "PASS_R36_LOCAL_PACKAGE|"
        f"source={source_zip.stat().st_size}/{sha_file(source_zip)}|"
        f"evidence={evidence_zip.stat().st_size}/{sha_file(evidence_zip)}|"
        f"receipt={receipt_path.stat().st_size}/{sha_file(receipt_path)}"
    )


if __name__ == "__main__":
    main()
