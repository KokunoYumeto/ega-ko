#!/usr/bin/env python3
"""Freeze and independently verify the deterministic R37 publication bundle."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import re
import shutil
import stat
import zipfile
from pathlib import Path
from typing import Any, Iterable


FIXED_TIME = (2026, 9, 5, 0, 0, 0)
VERSION = "2026-09-05-r37"
EXACT_DOI = "10.5281/zenodo.22315714"
CONCEPT_DOI = "10.5281/zenodo.21921513"
PDF_BYTES = 1_479_200
PDF_SHA = "22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61"
PDF_PAGES = 238
HISTORICAL_MARKERS = 227

MANIFEST_BYTES = 16_264
MANIFEST_SHA = "21ED41DDE0E7B850C12E9DF7A7839FB3FFE279B5BC205CC4FBE794A9FED4BAED"
BUILD_SCRIPT_BYTES = 20_370
BUILD_SCRIPT_SHA = "330A0F8337C6019010700088E0D8D398EA0B33CA922D06641D607E2F63D51F77"
BUILD_RECEIPT_BYTES = 5_462
BUILD_RECEIPT_SHA = "5864BCD80AA33AEB906034A1E07F3BDC8710D699588A448D95ACCBBEC49B84A4"
STRICT_BUILD_BYTES = 3_675
STRICT_BUILD_SHA = "F58CAF4FA4BEF1179288007C4F720B2E1CD3AE5D69AA311D1C345859766C9AF2"
ADMISSION_BYTES = 5_919
ADMISSION_SHA = "C4EBA3CA0F94A04815BE6585907D0EFB20A63F999710334F758078626D8A89C4"
PDF_QA_BYTES = 13_472
PDF_QA_SHA = "E3CB3AC1D47F4041ADECDA7942383EF0CA52B921E4AF5F9B97A1FF7EFBA1ACDD"
ZENODO_BYTES = 4_916
ZENODO_SHA = "68022F00B3BD7321DDA9C9F3C2E4F72899E47E9FA61B23DF54058832CE85FB02"

CANONICAL_BYTES = 820_505
CANONICAL_LINES = 18_087
CANONICAL_SHA = "84EDBE3E83530AF2959B441796337C9DC21EAFCA6A13114A26778760FBF437AC"
UNIT_BYTES = 3_776
UNIT_CHARACTERS = 3_727
UNIT_SHA = "D91203350D0012E008CA3A778DD5ABB1E3A18D70641C753F6F86ECFF51F949FE"
PREFIX_BYTES = 73_897
PREFIX_SHA = "0815285B46DA35D916612CDDACB92A1DD646153FAF6AC0D15E03417F9D349182"
CANDIDATE_BYTES = 4_073
CANDIDATE_SHA = "A423B075B3483FC84CA580AED46C651F84543F4444805D94388CD5574114063D"
TARGET_BYTES = 75_622
TARGET_LINES = 1_627
TARGET_SHA = "FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383"
VALIDATOR_BYTES = 9_880
VALIDATOR_LINES = 245
VALIDATOR_SHA = "C62F104DC1DA462F210F3D2661E09E6936817277C5217A8FEE0D3F64608585BC"

POPPLER_BYTES = 724_814
POPPLER_SHA = "DD155CF9FE4B9F7F865E3858387AF4222DA16B41E935D398612670A82953FFBF"
PYPDF_BYTES = 699_470
PYPDF_SHA = "45A9806C13729B3D8E804897B3515FDEAB64E7719B97ADB3C73ED6C5C6AE4B3B"

REQUIRED_R37_SCRIPTS = {
    "candidates/r37-c2s1-continuation.tex",
    "candidates/validate_r37_candidate.py",
    "scripts/package_r37.py",
    "scripts/portable_replay_r37.py",
    "scripts/prepare_r37_release.py",
    "scripts/qa_r37_pdf.py",
    "scripts/validate_expert_review_log.py",
}
PRIMARY_NAMES = {
    "00_EGA_ko_CUMULATIVE_READER.pdf",
    "01_EGA_ko_EDITABLE_SOURCES.zip",
    "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip",
    "03_EGA_ko_SHA256_MANIFEST.txt",
}
ArchiveInput = tuple[Path, str]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


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


def assert_ident(path: Path, expected_bytes: int, expected_sha: str, label: str) -> None:
    require(path.is_file(), f"missing {label}: {path}")
    require(path.stat().st_size == expected_bytes, f"{label} byte-count drift")
    require(sha_file(path) == expected_sha, f"{label} SHA-256 drift")


def assert_plain_file(path: Path, root: Path, release_root: Path) -> None:
    require(path.is_file() and not path.is_symlink(), f"publication input is not a plain file: {path}")
    resolved = path.resolve()
    require(resolved.is_relative_to(root.resolve()), f"publication input escapes its root: {path}")
    require(not resolved.is_relative_to(release_root.resolve()), f"package output entered package input set: {path}")


def root_source_files(repo: Path, private_root: Path, release_root: Path) -> list[ArchiveInput]:
    files = [repo / name for name in (".gitattributes", ".zenodo.json", "CITATION.cff", "LICENSE", "README.md")]
    files.append(repo / "build" / "BUILD.ps1")
    files.extend(sorted((repo / "source").rglob("*")))
    files.extend(sorted((repo / "scripts").glob("*.py")))
    repo_files = sorted([path for path in files if path.is_file()], key=lambda p: p.relative_to(repo).as_posix())
    result: list[ArchiveInput] = [(path, path.relative_to(repo).as_posix()) for path in repo_files]
    validator = private_root / "candidates" / "validate_r37_candidate.py"
    candidate = private_root / "candidates" / "r37-c2s1-continuation.tex"
    assert_ident(validator, VALIDATOR_BYTES, VALIDATOR_SHA, "R37 candidate validator")
    require(validator.read_bytes().count(b"\n") == VALIDATOR_LINES, "R37 candidate-validator LF-line drift")
    assert_ident(candidate, CANDIDATE_BYTES, CANDIDATE_SHA, "R37 admitted candidate")
    result.extend([(candidate, "candidates/r37-c2s1-continuation.tex"), (validator, "candidates/validate_r37_candidate.py")])
    require(len(result) == len({name for _, name in result}), "duplicate source-package archive name")
    for path, name in result:
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and "\\" not in name, f"unsafe source archive name: {name}")
        if path.is_relative_to(repo):
            assert_plain_file(path, repo, release_root)
        else:
            assert_plain_file(path, private_root, release_root)
    result.sort(key=lambda item: item[1])
    names = {name for _, name in result}
    missing = sorted(REQUIRED_R37_SCRIPTS - names)
    require(not missing, f"R37 replay/validation scripts are absent from source archive inputs: {missing}")
    return result


def evidence_files(repo: Path, release_root: Path, manifest_path: Path | None = None) -> list[ArchiveInput]:
    paths = sorted(
        [
            path
            for path in (repo / "evidence").rglob("*")
            if path.is_file() and (manifest_path is None or path != manifest_path)
        ],
        key=lambda p: p.relative_to(repo / "evidence").as_posix(),
    )
    require(len(paths) == len(set(paths)), "duplicate evidence-package input path")
    result: list[ArchiveInput] = []
    for path in paths:
        assert_plain_file(path, repo / "evidence", release_root)
        require(path.name not in PRIMARY_NAMES, f"primary package output entered evidence inputs: {path}")
        require(path.name not in {"PACKAGE_RECEIPT.json", "PORTABLE_BUILD_REPLAY.json"}, f"current package receipt entered evidence inputs: {path}")
        result.append((path, path.relative_to(repo / "evidence").as_posix()))
    return result


def artifact_manifest(repo: Path, source_files: list[ArchiveInput], reader: Path, release_root: Path) -> tuple[bytes, int]:
    manifest_path = repo / "evidence" / "ARTIFACT_SHA256.tsv"
    current_evidence = evidence_files(repo, release_root, manifest_path)
    rows_to_hash: list[ArchiveInput] = list(source_files)
    rows_to_hash.append((reader, "reader/00_EGA_ko_CUMULATIVE_READER.pdf"))
    rows_to_hash.extend((path, f"evidence/{name}") for path, name in current_evidence)
    rows_to_hash.sort(key=lambda item: item[1])
    require(len(rows_to_hash) == len({name for _, name in rows_to_hash}), "duplicate internal-manifest archive name")
    require(all(not path.resolve().is_relative_to(release_root.resolve()) for path, _ in rows_to_hash), "release output entered internal manifest")
    rows = ["relative_path\tbytes\tsha256"]
    for path, name in rows_to_hash:
        rows.append(f"{name}\t{path.stat().st_size}\t{sha_file(path)}")
    payload = ("\n".join(rows) + "\n").encode("utf-8")
    manifest_path.write_bytes(payload)
    return payload, len(rows_to_hash)


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


def verify_zip(path: Path, files: list[ArchiveInput], directories: list[str]) -> dict[str, Any]:
    file_names = [name for _, name in files]
    expected_names = directories + file_names
    inventory_rows = ["relative_path\tbytes\tcrc32\tsha256"]
    uncompressed = 0
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        require(names == expected_names, f"ZIP name/order mismatch in {path}")
        require(len(names) == len(set(names)), f"duplicate ZIP member in {path}")
        require(archive.testzip() is None, f"ZIP CRC failure in {path}")
        for info in infos:
            require(info.date_time == FIXED_TIME, f"ZIP timestamp drift: {info.filename}")
            require(info.create_system == 3, f"ZIP creator-system drift: {info.filename}")
            require(info.compress_type == zipfile.ZIP_DEFLATED, f"ZIP compression drift: {info.filename}")
            require(info.flag_bits == 0, f"ZIP flags drift: {info.filename}")
            require(info.extra == b"" and info.comment == b"", f"ZIP auxiliary metadata drift: {info.filename}")
            mode = stat.S_IFMT(info.external_attr >> 16)
            if info.is_dir():
                require(info.filename in directories, f"unexpected ZIP directory: {info.filename}")
                require(info.file_size == 0 and info.CRC == 0, f"nonempty ZIP directory: {info.filename}")
                require(mode == stat.S_IFDIR, f"ZIP directory mode drift: {info.filename}")
                require(info.external_attr == ((0o40755 << 16) | 0x10), f"ZIP directory attributes drift: {info.filename}")
                inventory_rows.append(f"{info.filename}\t0\t00000000\t{sha_bytes(b'')}")
            else:
                require(mode == stat.S_IFREG, f"ZIP file mode drift: {info.filename}")
                require(info.external_attr == (0o100644 << 16), f"ZIP file attributes drift: {info.filename}")
        for (file, name) in files:
            info = archive.getinfo(name)
            source = file.read_bytes()
            unpacked = archive.read(name)
            crc = binascii.crc32(source) & 0xFFFFFFFF
            require(info.file_size == len(source), f"ZIP uncompressed-size mismatch: {name}")
            require(info.CRC == crc, f"ZIP CRC mismatch: {name}")
            require(unpacked == source, f"ZIP decompressed-byte mismatch: {name}")
            require(sha_bytes(unpacked) == sha_bytes(source), f"ZIP SHA-256 mismatch: {name}")
            inventory_rows.append(f"{name}\t{len(source)}\t{crc:08X}\t{sha_bytes(source)}")
            uncompressed += len(source)
    inventory = ("\n".join(inventory_rows) + "\n").encode("utf-8")
    return {
        "entries": len(expected_names),
        "files": len(files),
        "directories": len(directories),
        "uncompressed_file_bytes": uncompressed,
        "complete_inventory_bytes": len(inventory),
        "complete_inventory_sha256": sha_bytes(inventory),
        "complete_inventory_columns": ["relative_path", "bytes", "crc32", "sha256"],
        "verification": "PASS exact names and order, no duplicates, fixed metadata, DEFLATE, modes, CRC, uncompressed sizes, decompressed bytes, per-file SHA-256 and complete inventory digest",
    }


def make_zip(path: Path, files: list[ArchiveInput]) -> dict[str, Any]:
    names = [name for _, name in files]
    directories = member_directories(names)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as archive:
        for name in directories:
            archive.writestr(zip_info(name, True), b"", compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        for file, name in files:
            archive.writestr(zip_info(name, False), file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return verify_zip(path, files, directories)


def build_twice(final: Path, files: list[ArchiveInput]) -> tuple[dict[str, Any], bool]:
    first = final.with_suffix(final.suffix + ".cycle-a")
    second = final.with_suffix(final.suffix + ".cycle-b")
    for path in (first, second, final):
        require(not path.exists(), f"refusing to overwrite package artifact: {path}")
    try:
        result_a = make_zip(first, files)
        result_b = make_zip(second, files)
        cycle_a_identity = ident(first)
        cycle_b_identity = ident(second)
        require(first.read_bytes() == second.read_bytes(), f"independent archive cycles differ: {final.name}")
        require(result_a == result_b, f"archive verification summaries differ: {final.name}")
        shutil.copyfile(first, final)
        result_final = verify_zip(final, files, member_directories([name for _, name in files]))
        require(result_final == result_a, f"final archive verification differs from cycle results: {final.name}")
        final_identity = ident(final)
        require(final_identity["bytes"] == cycle_a_identity["bytes"] == cycle_b_identity["bytes"], f"archive cycle byte-count drift: {final.name}")
        require(final_identity["sha256"] == cycle_a_identity["sha256"] == cycle_b_identity["sha256"], f"archive cycle SHA-256 drift: {final.name}")
        return {
            **result_a,
            "cycle_a": cycle_a_identity,
            "cycle_b": cycle_b_identity,
            "promoted_final": final_identity,
            "A_B_and_promoted_final_byte_identical": True,
            "builder_compression_level": 9,
            "compression_level_note": "DEFLATE is independently verified; level 9 is a deterministic builder parameter and is not recoverable from ZipInfo.",
        }, True
    finally:
        for path in (first, second):
            if path.exists():
                path.unlink()


def privacy_scan(paths: list[ArchiveInput]) -> dict[str, Any]:
    account = Path.home().name
    account_encodings = [account.encode("utf-8"), account.encode("utf-16-le"), account.encode("utf-16-be")]
    token_patterns = [
        re.compile(rb"(?i)(?:access_token|api[_-]?key|authorization)\s*[:=]\s*[A-Za-z0-9_\-]{16,}"),
        re.compile(rb"(?i)\b(?:ghp|github_pat|sk)-[A-Za-z0-9_\-]{12,}"),
        re.compile(rb"(?i)bearer\s+[A-Za-z0-9._~+/=\-]{16,}"),
    ]
    decodable = matches = bytes_checked = 0
    names_checked = 0
    for path, archive_name in paths:
        name_raw = archive_name.encode("utf-8")
        names_checked += 1
        if account and any(needle in name_raw for needle in account_encodings):
            matches += 1
        if any(pattern.search(name_raw) for pattern in token_patterns):
            matches += 1
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
    require(matches == 0, f"privacy/credential scan found {matches} prospective publication matches")
    return {
        "files_checked": len(paths),
        "relative_archive_names_checked": names_checked,
        "decodable_text_members_checked": decodable,
        "bytes_checked": bytes_checked,
        "matches": matches,
        "scope": "Every prospective source/evidence member and reader; member names and UTF-8 plus raw UTF-8/UTF-16 account encodings and credential-pattern checks. Needles are not recorded.",
        "result": "PASS",
    }


def validate_metadata(repo: Path) -> dict[str, Any]:
    metadata_path = repo / ".zenodo.json"
    assert_ident(metadata_path, ZENODO_BYTES, ZENODO_SHA, "R37 Zenodo metadata")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    active_paths = [metadata_path, repo / "CITATION.cff", repo / "README.md"]
    forbidden_pattern = re.compile(r"(?i)\bTTP\b|Translation and Transcription Project|Figshare")
    forbidden = sum(len(forbidden_pattern.findall(path.read_text(encoding="utf-8"))) for path in active_paths)
    require(forbidden == 0, "active publication metadata contains an excluded umbrella/destination term")
    require(metadata.get("version") == VERSION, "Zenodo metadata version drift")
    require(metadata.get("access_right") == "open", "Zenodo access is not open")
    require(EXACT_DOI in metadata.get("description", ""), "exact DOI absent from Zenodo description")
    require(CONCEPT_DOI in metadata.get("description", ""), "concept DOI absent from Zenodo description")
    require("https://github.com/KokunoYumeto/ega-ko" in metadata.get("description", ""), "canonical GitHub link absent")
    require("through Proposition §2.1.9" in metadata.get("description", ""), "R37 terminal coverage absent from metadata")
    require("lines 1–1605" in metadata.get("description", ""), "R37 canonical line coverage absent from metadata")
    contributors = metadata.get("contributors", [])
    require(contributors == [{"name": "AI typesetting & translation", "type": "Other"}], "standard contributor metadata drift")
    require(len(metadata.get("creators", [])) == 2, "historical creator count drift")
    return {
        **ident(metadata_path, repo),
        "description_characters": len(metadata["description"]),
        "active_metadata_files_scanned": [path.relative_to(repo).as_posix() for path in active_paths],
        "forbidden_umbrella_or_active_excluded_destination_mentions": forbidden,
        "creators": len(metadata["creators"]),
        "contributors": len(contributors),
        "sole_contributor": contributors[0]["name"],
        "rights_scope_provenance_and_nonendorsement": "PASS",
        "external_links": [
            "https://doi.org/10.5281/zenodo.21921513",
            "https://github.com/KokunoYumeto/ega-ko",
        ],
    }


def validate_r37_controls(repo: Path, reader: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest_path = repo / "source" / "CUMULATIVE_INPUTS.json"
    build_script = repo / "build" / "BUILD.ps1"
    build_receipt_path = repo / "evidence" / "BUILD_RECEIPT.json"
    strict_path = repo / "evidence" / "controls" / "R37_STRICT_BUILD.json"
    admission_path = repo / "evidence" / "controls" / "R37_TRANSLATION_ADMISSION.json"
    qa_path = repo / "evidence" / "controls" / "R37_PDF_QA.json"
    target_path = repo / "source" / "c2s1.tex"
    poppler_path = repo / "evidence" / "extract.txt"
    pypdf_path = repo / "evidence" / "extract-pypdf.txt"

    assert_ident(reader, PDF_BYTES, PDF_SHA, "R37 reader")
    assert_ident(manifest_path, MANIFEST_BYTES, MANIFEST_SHA, "R37 cumulative manifest")
    assert_ident(build_script, BUILD_SCRIPT_BYTES, BUILD_SCRIPT_SHA, "R37 build script")
    assert_ident(build_receipt_path, BUILD_RECEIPT_BYTES, BUILD_RECEIPT_SHA, "R37 build receipt")
    assert_ident(strict_path, STRICT_BUILD_BYTES, STRICT_BUILD_SHA, "R37 strict-build control")
    assert_ident(admission_path, ADMISSION_BYTES, ADMISSION_SHA, "R37 translation admission")
    assert_ident(qa_path, PDF_QA_BYTES, PDF_QA_SHA, "R37 PDF QA")
    assert_ident(target_path, TARGET_BYTES, TARGET_SHA, "R37 integrated Korean target")
    assert_ident(poppler_path, POPPLER_BYTES, POPPLER_SHA, "R37 frozen Poppler extraction")
    assert_ident(pypdf_path, PYPDF_BYTES, PYPDF_SHA, "R37 frozen pypdf extraction")
    require(target_path.read_bytes().count(b"\n") == TARGET_LINES, "R37 target LF-line drift")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scope = manifest.get("scope", {})
    require(scope.get("historical_source_pages") == HISTORICAL_MARKERS, "manifest historical-marker count drift")
    require("through2.1.9" in scope.get("terminal_coverage", ""), "manifest omits terminal 2.1.9 coverage")
    require("lines1-1605" in scope.get("terminal_coverage", ""), "manifest omits canonical lines1-1605")

    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    require(admission.get("schema") == "agko-r37-translation-admission-v1", "wrong R37 admission schema")
    require(admission.get("state", {}).get("translation") == "admitted", "R37 translation is not admitted")
    authority = admission.get("authority", {})
    require((authority.get("whole_bytes"), authority.get("whole_lf_lines"), authority.get("whole_sha256")) == (CANONICAL_BYTES, CANONICAL_LINES, CANONICAL_SHA), "R37 canonical whole-file binding drift")
    require(authority.get("unit_lines") == "1537-1605", "R37 admitted unit lines drift")
    require(authority.get("unit_bytes") == UNIT_BYTES, "R37 unit byte-count drift")
    require(authority.get("unit_characters") == UNIT_CHARACTERS, "R37 unit character-count drift")
    require(authority.get("unit_sha256") == UNIT_SHA, "R37 unit SHA-256 drift")
    require(authority.get("admitted_prefix_lines") == "1-1605", "R37 admitted prefix lines drift")
    require(authority.get("admitted_prefix_bytes") == PREFIX_BYTES, "R37 admitted prefix byte-count drift")
    require(authority.get("admitted_prefix_sha256") == PREFIX_SHA, "R37 admitted prefix SHA-256 drift")
    candidate = admission.get("candidate", {})
    require(candidate.get("bytes") == CANDIDATE_BYTES, "R37 candidate byte-count drift")
    require(candidate.get("characters") == 2_783 and candidate.get("lf_lines") == 72, "R37 candidate character/LF-line drift")
    require(candidate.get("sha256") == CANDIDATE_SHA, "R37 candidate SHA-256 drift")
    require(candidate.get("separator_plus_candidate_bytes") == 4_074, "R37 separator-plus-candidate byte-count drift")
    require(candidate.get("separator_plus_candidate_sha256") == "B33A9FBCCFB7822D74F748A32579DDABF903245546690798D9261CB88B527210", "R37 separator-plus-candidate SHA-256 drift")
    integrated = admission.get("integrated_target", {})
    require(integrated.get("bytes") == TARGET_BYTES, "R37 admission target byte-count drift")
    require(integrated.get("lf_lines") == TARGET_LINES, "R37 admission target LF-line drift")
    require(integrated.get("sha256") == TARGET_SHA, "R37 admission target SHA-256 drift")
    require(integrated.get("new_target_lines") == "1556-1627", "R37 new target-range drift")
    require(admission.get("structure_and_formula_validation", {}).get("result") == "PASS_R37_SOURCE_CANDIDATE_AND_INTEGRATED_MIRRORS", "R37 candidate validator did not pass")
    structure = admission.get("structure_and_formula_validation", {})
    require(structure.get("source_inline_formula_count") == structure.get("target_inline_formula_count") == 99, "R37 inline-formula count drift")
    require(structure.get("target_formula_multiset_exact") is True, "R37 target formula multiset drift")
    require(structure.get("labels") == 2 and structure.get("oldpage") == "II23", "R37 label/oldpage binding drift")
    require(admission.get("source_caveat", {}).get("formula_preserved") is True and admission.get("source_caveat", {}).get("silent_formula_repair") is False, "R37 diplomatic formula treatment drift")

    strict = json.loads(strict_path.read_text(encoding="utf-8"))
    require(strict.get("version") == VERSION and strict.get("exact_doi") == EXACT_DOI, "R37 strict-build identity drift")
    require(strict.get("concept_doi") == CONCEPT_DOI, "R37 strict-build concept DOI drift")
    require(strict.get("reader") == {"path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf", "bytes": PDF_BYTES, "sha256": PDF_SHA, "pages": PDF_PAGES}, "R37 strict reader record drift")
    require(strict.get("strict_build", {}).get("xelatex_passes") == 8 and strict.get("strict_build", {}).get("independent_clean_cycles") == 2, "R37 strict-build pass/cycle count drift")
    convergence = strict.get("convergence", {})
    require(convergence.get("cycle_a", {}).get("pass3_equals_pass4") is True, "strict cycle A lacks pass3=pass4")
    require(convergence.get("cycle_b", {}).get("pass3_equals_pass4") is True, "strict cycle B lacks pass3=pass4")
    require(convergence.get("cycle_finals_byte_identical") is True, "strict cycle finals differ")
    require(convergence.get("reader_promotion_byte_identical") is True, "strict reader promotion differs")
    require(strict.get("status") == "PASS_R37_STRICT_TWO_CYCLE_FOUR_PASS_BUILD", "R37 strict build did not pass")

    build_receipt = json.loads(build_receipt_path.read_text(encoding="utf-8"))
    require(build_receipt.get("version") == VERSION, "R37 build-receipt version drift")
    require(build_receipt.get("exact_doi") == EXACT_DOI and build_receipt.get("concept_doi") == CONCEPT_DOI, "R37 build-receipt DOI drift")
    require(build_receipt.get("status") == "PASS_LOCAL_BUILD_AND_PDF_QA", "R37 build/QA receipt did not pass")
    require(build_receipt.get("coverage_manifest", {}).get("historical_markers") == HISTORICAL_MARKERS, "R37 build-receipt marker drift")
    require(build_receipt.get("convergence", {}).get("cycle_finals_byte_identical") is True, "R37 build-receipt cycles differ")

    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    require(qa.get("schema") == "agko-r37-pdf-qa-v1" and qa.get("edition") == VERSION, "wrong R37 PDF QA identity")
    require(qa.get("status") == "PASS", "R37 PDF QA did not pass")
    qa_pdf = qa.get("pdf", {})
    require((qa_pdf.get("bytes"), qa_pdf.get("sha256"), qa_pdf.get("pages")) == (PDF_BYTES, PDF_SHA, PDF_PAGES), "R37 PDF QA reader drift")
    require(qa.get("historical_markers", {}).get("source_count") == HISTORICAL_MARKERS, "R37 PDF QA marker drift")
    require(qa.get("historical_markers", {}).get("pypdf_full_sequence_matches") is True, "R37 full marker sequence failed")
    require(qa.get("historical_markers", {}).get("normalized_sequence_sha256") == "2783908AC4D3B6F5160A8B6082CEAEB277AC150C62C710D6CFAB6575E0AB1A96", "R37 normalized marker-sequence drift")
    require(qa.get("historical_markers", {}).get("ranges") == ["I|5-8", "0I|11-78", "I|79-214", "II|5-23"], "R37 historical marker-range drift")
    require(qa.get("historical_markers", {}).get("terminal_marker") == ["II", 23], "R37 terminal historical marker drift")
    require(qa.get("source_bindings", {}).get("ordered_inputs_checked") == 17, "R37 ordered reader-input count drift")
    require(qa.get("build_receipt_or_control") == {"path": "evidence/controls/R37_STRICT_BUILD.json", "bytes": STRICT_BUILD_BYTES, "sha256": STRICT_BUILD_SHA}, "R37 QA strict-build binding drift")
    require(qa.get("visual_findings", {}).get("status") == "PASS", "R37 rendered visual QA did not pass")
    require(qa.get("font_unicode", {}).get("all_type0_hangul_fonts_have_tounicode") is True, "R37 Hangul ToUnicode gate failed")
    qa_target = qa.get("source_bindings", {}).get("korean_target", {})
    require((qa_target.get("bytes"), qa_target.get("sha256"), qa_target.get("lf_lines")) == (TARGET_BYTES, TARGET_SHA, TARGET_LINES), "R37 QA target binding drift")
    qa_candidate = qa.get("source_bindings", {}).get("candidate_binding", {})
    require((qa_candidate.get("bytes"), qa_candidate.get("sha256")) == (CANDIDATE_BYTES, CANDIDATE_SHA), "R37 QA candidate binding drift")
    render_pages = {row.get("physical_page") for row in qa.get("renders", [])}
    require({1, 237, 238}.issubset(render_pages), "R37 portable replay reference renders are incomplete")
    return admission, qa, strict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    private_root = args.private_root.resolve()
    release_root = repo / "release"
    release = release_root / VERSION
    require(not release.exists(), f"refusing to reuse existing release directory: {release}")

    reader = repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    admission, qa, strict = validate_r37_controls(repo, reader)
    metadata_summary = validate_metadata(repo)
    source_files = root_source_files(repo, private_root, release_root)
    artifact_payload, artifact_entries = artifact_manifest(repo, source_files, reader, release_root)
    current_evidence = evidence_files(repo, release_root)
    privacy = privacy_scan(source_files + current_evidence + [(reader, "reader/00_EGA_ko_CUMULATIVE_READER.pdf")])

    release.mkdir(parents=True, exist_ok=False)
    reader_release = release / "00_EGA_ko_CUMULATIVE_READER.pdf"
    shutil.copyfile(reader, reader_release)
    assert_ident(reader_release, PDF_BYTES, PDF_SHA, "frozen R37 reader")

    source_zip = release / "01_EGA_ko_EDITABLE_SOURCES.zip"
    evidence_zip = release / "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip"
    source_verification, source_equal = build_twice(source_zip, source_files)
    evidence_verification, evidence_equal = build_twice(evidence_zip, current_evidence)

    outer_files = [reader_release, source_zip, evidence_zip]
    manifest_lines = ["filename\tbytes\tsha256"]
    for path in outer_files:
        manifest_lines.append(f"{path.name}\t{path.stat().st_size}\t{sha_file(path)}")
    outer_manifest = release / "03_EGA_ko_SHA256_MANIFEST.txt"
    require(not outer_manifest.exists(), f"refusing to overwrite outer manifest: {outer_manifest}")
    outer_manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8", newline="\n")
    outer_privacy = privacy_scan([(outer_manifest, outer_manifest.name)])

    expert_receipt_path = repo / "evidence" / "expert_review" / "PUBLIC_EXPERT_REVIEW_RECEIPT.json"
    expert_receipt = json.loads(expert_receipt_path.read_text(encoding="utf-8"))
    expert_outputs = expert_receipt.get("outputs", {})
    expert_records = expert_receipt.get("records", {}).get("total")
    require(isinstance(expert_records, int) and expert_records > 0, "expert-review record count missing")
    expert_jsonl_path = repo / "evidence" / "expert_review" / "EXPERT_REVIEW.jsonl"
    expert_ids = {
        json.loads(line)["source_record_id"]
        for line in expert_jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    require({"AGKO-D185", "AGKO-H160"}.issubset(expert_ids), "expert-review snapshot does not contain the controlling R37 decision and hard record")
    for name, record in expert_outputs.items():
        output = repo / "evidence" / "expert_review" / name
        assert_ident(output, record["bytes"], record["sha256"], f"expert-review output {name}")

    file_rows = [
        {"order": 0, "name": reader_release.name, "bytes": reader_release.stat().st_size, "sha256": sha_file(reader_release), "role": "front cumulative reader artifact", "pages": PDF_PAGES},
        {"order": 1, "name": source_zip.name, "bytes": source_zip.stat().st_size, "sha256": sha_file(source_zip), "role": "deterministic editable-source and R37 replay/validation-script archive", **source_verification},
        {"order": 2, "name": evidence_zip.name, "bytes": evidence_zip.stat().st_size, "sha256": sha_file(evidence_zip), "role": "deterministic current public evidence and provenance archive", **evidence_verification},
        {"order": 3, "name": outer_manifest.name, "bytes": outer_manifest.stat().st_size, "sha256": sha_file(outer_manifest), "role": "outer SHA-256 manifest", "listed_artifacts": 3, "verification": "PASS"},
    ]
    receipt = {
        "schema": "ag-ko-package-receipt-v5",
        "version": VERSION,
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "coverage": {
            "corpus": "EGA",
            "included_volumes": ["EGA 0_I", "EGA I", "EGA II (programme/table of contents and main text through2.1.9)"],
            "terminal_coverage": "EGA II Chapter II programme/table of contents through source EOF, followed by ega2/ega2-1-fr.tex lines1-1605 through2.1.9",
            "completeness_claim": "all locally completed and hash-admitted Korean EGA targets are included; EGA II and the full EGA corpus remain incomplete",
            "historical_source_pages": HISTORICAL_MARKERS,
            "historical_page_ranges": ["EGA I introduction5-8", "EGA 0_I11-78", "EGA I Chapter I79-214", "EGA II5-23"],
        },
        "r37_translation_binding": {
            "source_unit": {"lines": "1537-1605", "bytes": UNIT_BYTES, "characters": UNIT_CHARACTERS, "sha256": UNIT_SHA},
            "canonical_prefix": {"lines": "1-1605", "bytes": PREFIX_BYTES, "sha256": PREFIX_SHA},
            "candidate": {"bytes": CANDIDATE_BYTES, "sha256": CANDIDATE_SHA},
            "integrated_target": {"bytes": TARGET_BYTES, "lf_lines": TARGET_LINES, "sha256": TARGET_SHA},
            "admission_control": ident(repo / "evidence" / "controls" / "R37_TRANSLATION_ADMISSION.json", repo),
            "validator_result": admission["structure_and_formula_validation"]["result"],
        },
        "files": file_rows,
        "public_artifact_count": 4,
        "public_artifact_allowlist": [row["name"] for row in file_rows],
        "manifest_listed_artifacts": 3,
        "non_public_support_files": ["PACKAGE_RECEIPT.json", "PORTABLE_BUILD_REPLAY.json"],
        "total_publication_bytes": sum(row["bytes"] for row in file_rows),
        "source_archive_A_B_byte_identical": source_equal,
        "evidence_archive_A_B_byte_identical": evidence_equal,
        "reader_qa": {
            "build_receipt": ident(repo / "evidence" / "BUILD_RECEIPT.json", repo),
            "strict_build_control": ident(repo / "evidence" / "controls" / "R37_STRICT_BUILD.json", repo),
            "pdf_control": ident(repo / "evidence" / "controls" / "R37_PDF_QA.json", repo),
            "convergence": "PASS two independent four-pass cycles; pass3=pass4 in each; cycle finals byte-identical",
            "strict_terminal_record": strict["terminal_record"],
            "extraction": qa["extractions"],
            "links": qa["navigation"],
            "visual": qa["visual_findings"],
        },
        "expert_review": {
            "jsonl": ident(expert_jsonl_path, repo),
            "markdown": ident(repo / "evidence" / "expert_review" / "EXPERT_REVIEW.md", repo),
            "receipt": ident(expert_receipt_path, repo),
            "records": expert_records,
            "r37_records_present": ["AGKO-D185", "AGKO-H160"],
            "receipt_output_bindings": expert_outputs,
            "validation": expert_receipt.get("result"),
        },
        "internal_manifest": {
            "path": "evidence/ARTIFACT_SHA256.tsv",
            "bytes": len(artifact_payload),
            "sha256": sha_bytes(artifact_payload),
            "entries": artifact_entries,
            "verification": "PASS independent path, byte-count and SHA-256 replay; manifest excludes itself and every package/release output",
        },
        "source_archive_required_scripts": sorted(REQUIRED_R37_SCRIPTS),
        "source_archive_required_scripts_present": True,
        "evidence_input_scope": "current files rooted strictly under evidence/, including regenerated ARTIFACT_SHA256.tsv; current release/package outputs excluded",
        "metadata": metadata_summary,
        "privacy_credential_check": privacy,
        "outer_manifest_privacy_credential_check": outer_privacy,
        "publication_status": "as of package freeze: local package only; draft and repository state are not publication claims",
        "portable_replay": "as of package freeze: not yet run; separate PORTABLE_BUILD_REPLAY.json is required",
        "result": "PASS_R37_LOCAL_PACKAGE",
    }
    receipt_path = release / "PACKAGE_RECEIPT.json"
    require(not receipt_path.exists(), f"refusing to overwrite package receipt: {receipt_path}")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    require(json.loads(receipt_path.read_text(encoding="utf-8")) == receipt, "written R37 package receipt replay drift")
    print(
        "PASS_R37_LOCAL_PACKAGE|"
        f"source={source_zip.stat().st_size}/{sha_file(source_zip)}|"
        f"evidence={evidence_zip.stat().st_size}/{sha_file(evidence_zip)}|"
        f"receipt={receipt_path.stat().st_size}/{sha_file(receipt_path)}"
    )


if __name__ == "__main__":
    main()
