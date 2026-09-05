#!/usr/bin/env python3
"""Freeze and independently verify the deterministic R38 publication bundle."""

from __future__ import annotations

import argparse
import atexit
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
VERSION = "2026-09-05-r38"
EXACT_DOI = "10.5281/zenodo.22346664"
CONCEPT_DOI = "10.5281/zenodo.21921513"
PDF_BYTES = 1_485_270
PDF_SHA = "FEC06D6723BFE9CC7D3C46E285C7DE8A49929F2797FD2F4F47877D2BDA06FE15"
PDF_PAGES = 239
HISTORICAL_MARKERS = 228

MANIFEST_BYTES = 16_250
MANIFEST_SHA = "50C9896A8436E2A381817BA322DE45A5EFCB768F2790E7BC14A206D70AAA81AE"
BUILD_SCRIPT_BYTES = 20_370
BUILD_SCRIPT_SHA = "330A0F8337C6019010700088E0D8D398EA0B33CA922D06641D607E2F63D51F77"
STRICT_BUILD_BYTES = 8_533
STRICT_BUILD_SHA = "E8A844FF6DA59EAFAA890D34E180B81BE2B8D1D639E4801692897B89DA5CD6FB"
ADMISSION_BYTES = 8_103
ADMISSION_SHA = "23CA8C711E89448D910BCD585BCC815B1A87F56A9890220485F27E3E8377FEC2"
INTEGRATION_BYTES = 5_209
INTEGRATION_SHA = "3901DE2B2F9BD1DDB6399D7B35005FAD196F1A3A229061D9D46F3813E58BB020"
RECONCILIATION_BYTES = 6_698
RECONCILIATION_SHA = "C60088AE26B2E33B2CFBCD88044E1F5BDA2636DB2BF93D5E392B62CB4915688C"
PDF_QA_BYTES = 34_043
PDF_QA_SHA = "5140761219F2C8AFAC7075BEEF1044D4190FA41B590B670FA349DF1EF6B55B45"
ZENODO_BYTES = 5_272
ZENODO_SHA = "741D972A235ADD02188A4CEA588AB092BF0B3E60FDFEC6166B0C4F55CEE074FA"
README_BYTES = 6_258
README_SHA = "674CA5FA00B68F4B7D3481F8CBCD8B5576CB769B4BE47AB80BE6BF8F11B57089"
CITATION_BYTES = 993
CITATION_SHA = "89E8A75C7E09856C6FA65146AC5A95118C78E03B31EB8F0536DF33BFD1CE5130"
FRONT_BYTES = 4_440
FRONT_SHA = "1A709228BA6CE5AEACFC6653686234B2961D8309D40BC30F930E066DF048BC72"
RELEASE_NOTES_BYTES = 4_441
RELEASE_NOTES_SHA = "42E1FE448501290BD344C32058BD643F67383802740415CE8460D9FB8E2CB7CA"
QA_SCRIPT_BYTES = 41_547
QA_SCRIPT_SHA = "CA8449B6FDF0757783F48DC9B969C49B766D4835EDA1223F86CBB2C34268141E"
BUILD_RECEIPT_BYTES = 6_402
BUILD_RECEIPT_SHA = "B1287180C5A20E12B6DF4FE7CCD176B8F6FE0270F3219BE7E83538215EC1238A"
INVENTORY_REFRESH_BYTES = 1_490
INVENTORY_REFRESH_SHA = "A55400B0236DDB3A32C47C3AA14B45B0ACFF0260EF843779EB0487F6B649ADE3"
SANITIZED_LOG_BYTES = 51_806
SANITIZED_LOG_SHA = "80F4ECD59AFBC9CFAFD1C5DC63C33E10F1DF72E5FB0766EF4D08EEF6DF4B15A6"
R38_UNITS_CUTOFF_LINES = 2_148
R38_UNITS_BYTES = 1_251_540
R38_UNITS_SHA = "BFEB68EDD9C5B8B324A42652E1F1D329AF7044064CF7125822A04ED17874DC0F"
EVIDENCE_ALLOWLIST_PATH = "scripts/r38_evidence_release_cutoff.txt"
EVIDENCE_ALLOWLIST_BYTES = 11_251
EVIDENCE_ALLOWLIST_SHA = "65041CD99A37F92180D5C878061668CF9EC6887CA606DA575934F8174D5B1479"
EVIDENCE_ALLOWLIST_ENTRIES = 501

CANONICAL_BYTES = 820_504
CANONICAL_LINES = 18_087
CANONICAL_SHA = "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E"
PRE_CORRECTION_CANONICAL_BYTES = 820_505
PRE_CORRECTION_CANONICAL_SHA = "84EDBE3E83530AF2959B441796337C9DC21EAFCA6A13114A26778760FBF437AC"
UNIT_BYTES = 4_191
UNIT_CHARACTERS = 4_096
UNIT_SHA = "44583D53F17603797145FE63822F3F78DC6ECFD7ADA1B38EF01813F9E3F22BE6"
PREFIX_BYTES = 78_088
PREFIX_SHA = "7DE4ECF8630F2B575C08ED0EE4AEC560F6BD4C6026C4BC894DD057D4AE1B9B75"
PRE_CORRECTION_PREFIX_BYTES = 78_089
PRE_CORRECTION_PREFIX_SHA = "6C9C0EE5DC909DFE7911564F1F982FF0539C923DE706188F7935FC0585549585"
CANDIDATE_BYTES = 4_599
CANDIDATE_SHA = "8D37AF2B8B05D9C938F2D282F58902092FB7FCF55300B0A85B28C9538340CF93"
TARGET_BYTES = 80_222
TARGET_LINES = 1_708
TARGET_SHA = "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006"
VALIDATOR_BYTES = 16_396
VALIDATOR_LINES = 400
VALIDATOR_SHA = "3FC051E0944E506E1F6366B84CC3B55B279FA74B7E6F183ED6ECE38E6D830AAC"

POPPLER_BYTES = 728_827
POPPLER_SHA = "B5A047C7799FD4A741099CE9334797F26CCDDD5EC9D68F9A6A03EFABA6ADDC99"
PYPDF_BYTES = 703_381
PYPDF_SHA = "9207B6B25CBAC5113A6C718C7B970E232E159799AC68CB7C527F908455173AD6"

RENDER_IDENTITIES = {
    1: (133_699, "8A9C079746DC9D2BAACE84D02E46635FAE87E8073D483A88C962590ED82116E6"),
    2: (494_472, "97F4435291368165C762F357F86E6FCD3AEC2F5ACA41C764D9C0A7D110957723"),
    6: (273_914, "BD71C92D1810D28FE7F9289F4FF20D38452A7970F0CE5BBE742209A7E3B01977"),
    237: (818_805, "F639B832388C5839EA866E69E04479ACCC88FDB9154CE82D75511CBA5D8F10F2"),
    238: (733_896, "3343138791A864AECF7584DB54BA7A375FE5EC613E7D82E6093C210CB66ECDF9"),
    239: (209_400, "8D2157D299589D0A6743DBDF720A2FEF2E5336F2544A5A6C685E5E2DE9ACA834"),
}

REQUIRED_R38_SCRIPTS = {
    "candidates/r38-c2s1-continuation.tex",
    "candidates/validate_r38_candidate.py",
    "scripts/append_r38_integration_records.py",
    "scripts/package_r38.py",
    "scripts/portable_replay_r38.py",
    "scripts/prepare_r38_release.py",
    "scripts/qa_r38_pdf.py",
    EVIDENCE_ALLOWLIST_PATH,
    "scripts/validate_expert_review_log.py",
}
EXCLUDED_CURRENT_RELEASE_SCRIPT_TOKENS = ("publish", "publication", "github", "closure")
PRIMARY_NAMES = {
    "00_EGA_ko_CUMULATIVE_READER.pdf",
    "01_EGA_ko_EDITABLE_SOURCES.zip",
    "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip",
    "03_EGA_ko_SHA256_MANIFEST.txt",
}
EXCLUDED_POST_R38_EVIDENCE = {
    "controls/EGA2_R63_SOURCE_BASIS_REFRESH_20260905.json",
    "controls/R39_CANONICAL_PREFIX_REBASE.json",
    "controls/R39_TRANSLATION_ADMISSION.json",
    "controls/R40_TRANSLATION_ADMISSION.json",
    "controls/R41_TRANSLATION_ADMISSION.json",
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
    files.append(repo / EVIDENCE_ALLOWLIST_PATH)
    files.extend(sorted((repo / "source").rglob("*")))
    public_scripts = sorted((repo / "scripts").glob("*.py"))
    excluded_future = [
        path
        for path in public_scripts
        if "r38" in path.name.lower()
        and any(token in path.name.lower() for token in EXCLUDED_CURRENT_RELEASE_SCRIPT_TOKENS)
    ]
    files.extend(path for path in public_scripts if path not in excluded_future)
    repo_files = sorted([path for path in files if path.is_file()], key=lambda p: p.relative_to(repo).as_posix())
    result: list[ArchiveInput] = [(path, path.relative_to(repo).as_posix()) for path in repo_files]
    validator = private_root / "candidates" / "validate_r38_candidate.py"
    candidate = private_root / "candidates" / "r38-c2s1-continuation.tex"
    assert_ident(validator, VALIDATOR_BYTES, VALIDATOR_SHA, "R38 candidate validator")
    require(validator.read_bytes().count(b"\n") == VALIDATOR_LINES, "R38 candidate-validator LF-line drift")
    assert_ident(candidate, CANDIDATE_BYTES, CANDIDATE_SHA, "R38 admitted candidate")
    assert_ident(repo / "scripts" / "qa_r38_pdf.py", QA_SCRIPT_BYTES, QA_SCRIPT_SHA, "R38 PDF-QA helper")
    result.extend([(candidate, "candidates/r38-c2s1-continuation.tex"), (validator, "candidates/validate_r38_candidate.py")])
    require(len(result) == len({name for _, name in result}), "duplicate source-package archive name")
    for path, name in result:
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and "\\" not in name, f"unsafe source archive name: {name}")
        if path.is_relative_to(repo):
            assert_plain_file(path, repo, release_root)
        else:
            assert_plain_file(path, private_root, release_root)
    result.sort(key=lambda item: item[1])
    names = {name for _, name in result}
    missing = sorted(REQUIRED_R38_SCRIPTS - names)
    require(not missing, f"R38 replay/validation scripts are absent from source archive inputs: {missing}")
    require(
        not ({path.relative_to(repo).as_posix() for path in excluded_future} & names),
        "future R38 publication/closure helper entered source archive inputs",
    )
    return result


def load_evidence_allowlist(repo: Path) -> list[str]:
    path = repo / EVIDENCE_ALLOWLIST_PATH
    assert_ident(path, EVIDENCE_ALLOWLIST_BYTES, EVIDENCE_ALLOWLIST_SHA, "R38 evidence release-cutoff allowlist")
    raw = path.read_bytes()
    require(raw.endswith(b"\n") and b"\r" not in raw, "R38 evidence allowlist is not canonical LF text")
    names = raw.decode("utf-8").splitlines()
    require(len(names) == EVIDENCE_ALLOWLIST_ENTRIES, "R38 evidence allowlist entry-count drift")
    require(names == sorted(names) and len(names) == len(set(names)), "R38 evidence allowlist ordering/uniqueness drift")
    for name in names:
        pure = Path(name)
        require(name and not pure.is_absolute() and "\\" not in name and ".." not in pure.parts, f"unsafe R38 evidence allowlist member: {name!r}")
        require(name != "ARTIFACT_SHA256.tsv" and name not in EXCLUDED_POST_R38_EVIDENCE, f"invalid R38 evidence allowlist classification: {name}")
    return names


def evidence_files(
    repo: Path,
    release_root: Path,
    allowlist: list[str],
    overrides: dict[str, Path] | None = None,
) -> list[ArchiveInput]:
    evidence_root = repo / "evidence"
    overrides = overrides or {}
    live_names = {
        path.relative_to(evidence_root).as_posix()
        for path in evidence_root.rglob("*")
        if path.is_file()
    }
    expected_live_names = set(allowlist) | {"ARTIFACT_SHA256.tsv"} | EXCLUDED_POST_R38_EVIDENCE
    require(
        live_names == expected_live_names,
        "live evidence inventory differs from explicit R38 cutoff classification: "
        f"unclassified={sorted(live_names - expected_live_names)}, missing={sorted(expected_live_names - live_names)}",
    )
    result: list[ArchiveInput] = []
    for name in allowlist:
        path = evidence_root.joinpath(*name.split("/"))
        selected = overrides.get(name, path)
        if selected == path:
            assert_plain_file(selected, evidence_root, release_root)
        else:
            require(selected.is_file() and not selected.is_symlink(), f"invalid evidence snapshot override: {name}")
        require(path.name not in PRIMARY_NAMES, f"primary package output entered evidence inputs: {path}")
        require(path.name not in {"PACKAGE_RECEIPT.json", "PORTABLE_BUILD_REPLAY.json"}, f"current package receipt entered evidence inputs: {path}")
        result.append((selected, name))
    require(set(overrides).issubset({name for _, name in result}), "unused evidence snapshot override")
    return result


def future_evidence(repo: Path) -> list[ArchiveInput]:
    evidence_root = repo / "evidence"
    result = []
    for name in sorted(EXCLUDED_POST_R38_EVIDENCE):
        path = evidence_root / Path(name)
        require(path.is_file(), f"classified post-R38 evidence is absent: {name}")
        result.append((path, name))
    return result


def prepare_release_cutoff_snapshot(repo: Path, private_root: Path) -> tuple[Path, dict[str, Path], dict[str, Any]]:
    staging_parent = private_root / "release-staging"
    snapshot_root = staging_parent / "r38-package-evidence-snapshot"
    require(not staging_parent.is_symlink(), f"release staging parent is a symlink: {staging_parent}")
    staging_parent.mkdir(parents=True, exist_ok=True)
    require(not snapshot_root.exists() and not snapshot_root.is_symlink(), f"R38 evidence snapshot stage already exists: {snapshot_root}")
    snapshot_root.mkdir()
    live_units = repo / "evidence" / "index" / "units.jsonl"
    raw_lines = live_units.read_bytes().splitlines(keepends=True)
    require(len(raw_lines) >= R38_UNITS_CUTOFF_LINES, "live unit index is shorter than the R38 cutoff")
    payload = b"".join(raw_lines[:R38_UNITS_CUTOFF_LINES])
    require(payload.endswith(b"\n") and b"\r" not in payload, "R38 unit-index snapshot is not LF-only/final-LF")
    require((len(payload), sha_bytes(payload)) == (R38_UNITS_BYTES, R38_UNITS_SHA), "R38 unit-index cutoff identity drift")
    last = json.loads(raw_lines[R38_UNITS_CUTOFF_LINES - 1])
    require(last.get("id") == "AGKO-EGA2-S1-R38-COVERAGE", "R38 unit-index terminal record drift")
    require(all(b"R39" not in line and b"R40" not in line and b"R41" not in line for line in raw_lines[:R38_UNITS_CUTOFF_LINES]), "future round leaked before R38 unit-index cutoff")
    units_snapshot = snapshot_root / "index" / "units.jsonl"
    units_snapshot.parent.mkdir(parents=True)
    units_snapshot.write_bytes(payload)
    return snapshot_root, {"index/units.jsonl": units_snapshot}, {
        "path": "index/units.jsonl",
        "cutoff_lf_lines": R38_UNITS_CUTOFF_LINES,
        "terminal_record": last["id"],
        "bytes": len(payload),
        "sha256": sha_bytes(payload),
        "live_post_cutoff_records_excluded": len(raw_lines) - R38_UNITS_CUTOFF_LINES,
    }


def safe_remove_owned_stage(path: Path, private_root: Path, expected_leaf: str) -> None:
    expected_parent = (private_root / "release-staging").resolve()
    resolved = path.resolve()
    require(resolved.parent == expected_parent and resolved.name == expected_leaf, f"unsafe staging cleanup target: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def materialize_evidence_cutoff(
    repo: Path,
    release_root: Path,
    snapshot_root: Path,
    initial_overrides: dict[str, Path],
    allowlist: list[str],
) -> list[ArchiveInput]:
    selected = evidence_files(repo, release_root, allowlist, initial_overrides)
    result: list[ArchiveInput] = []
    for source, name in selected:
        destination = snapshot_root.joinpath(*name.split("/"))
        if destination.resolve() != source.resolve():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        require(destination.is_file() and destination.read_bytes() == source.read_bytes(), f"evidence cutoff copy drift: {name}")
        result.append((destination, name))
    names = [name for _, name in result]
    require(len(names) == len(set(names)), "duplicate path in R38 evidence cutoff")
    require(not (set(names) & EXCLUDED_POST_R38_EVIDENCE), "post-R38 evidence leaked into R38 evidence cutoff")
    return sorted(result, key=lambda item: item[1])


def safe_remove_release_stage(path: Path, release_root: Path) -> None:
    resolved = path.resolve()
    parent = release_root.resolve()
    require(resolved.parent == parent and resolved.name == ".2026-09-05-r38-staging", f"unsafe release-stage cleanup target: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def artifact_manifest(
    repo: Path,
    source_files: list[ArchiveInput],
    reader: Path,
    release_root: Path,
    evidence_inputs: list[ArchiveInput],
    output_path: Path,
) -> tuple[bytes, int]:
    rows_to_hash: list[ArchiveInput] = list(source_files)
    rows_to_hash.append((reader, "reader/00_EGA_ko_CUMULATIVE_READER.pdf"))
    rows_to_hash.extend((path, f"evidence/{name}") for path, name in evidence_inputs)
    rows_to_hash.sort(key=lambda item: item[1])
    require(len(rows_to_hash) == len({name for _, name in rows_to_hash}), "duplicate internal-manifest archive name")
    require(all(not path.resolve().is_relative_to(release_root.resolve()) for path, _ in rows_to_hash), "release output entered internal manifest")
    rows = ["relative_path\tbytes\tsha256"]
    for path, name in rows_to_hash:
        rows.append(f"{name}\t{path.stat().st_size}\t{sha_file(path)}")
    payload = ("\n".join(rows) + "\n").encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    require(output_path.read_bytes() == payload, "staged internal manifest write drift")
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
    # Flag actual user-profile locators, not every drive-qualified path.  The
    # corpus legitimately contains TeX constructs such as ``C:/...`` and
    # historical tool locators that are neither private nor profile-specific.
    # Requiring a conventional profile root and a concrete account segment
    # keeps this gate strict without treating regex literals or ``[USER]``
    # placeholders as disclosures.
    windows_profile = re.compile(
        r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/](?:Users|Documents and Settings)[\\/]"
        r"[A-Za-z0-9._-]+(?:[\\/]|$)"
    )
    posix_profile = re.compile(
        r"(?i)(?<![A-Za-z0-9_])/(?:home|Users)/[A-Za-z0-9._-]+(?:/|$)"
    )
    decodable = matches = bytes_checked = profile_locator_matches = 0
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
            locator_hits = len(windows_profile.findall(text)) + len(posix_profile.findall(text))
            profile_locator_matches += locator_hits
            matches += locator_hits
        except UnicodeDecodeError:
            pass
    require(matches == 0, f"privacy/credential scan found {matches} prospective publication matches")
    return {
        "files_checked": len(paths),
        "relative_archive_names_checked": names_checked,
        "decodable_text_members_checked": decodable,
        "bytes_checked": bytes_checked,
        "matches": matches,
        "profile_locator_matches": profile_locator_matches,
        "scope": "Every prospective source/evidence member and reader; member names and UTF-8 plus raw UTF-8/UTF-16 account encodings, concrete Windows/POSIX profile locators and credential-pattern checks. Generic drive-qualified mathematical/tool strings and placeholder profile labels are not disclosures. Needles are not recorded.",
        "result": "PASS",
    }


def validate_metadata(repo: Path) -> dict[str, Any]:
    metadata_path = repo / ".zenodo.json"
    assert_ident(metadata_path, ZENODO_BYTES, ZENODO_SHA, "R38 Zenodo metadata")
    assert_ident(repo / "README.md", README_BYTES, README_SHA, "R38 README")
    assert_ident(repo / "CITATION.cff", CITATION_BYTES, CITATION_SHA, "R38 citation metadata")
    assert_ident(repo / "source" / "front.tex", FRONT_BYTES, FRONT_SHA, "R38 front matter")
    assert_ident(repo / "r38-github-release-notes.md", RELEASE_NOTES_BYTES, RELEASE_NOTES_SHA, "R38 release notes")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    active_paths = [metadata_path, repo / "CITATION.cff", repo / "README.md", repo / "r38-github-release-notes.md", repo / "source" / "front.tex"]
    forbidden_pattern = re.compile(r"(?i)\bTTP\b|Translation and Transcription Project|Figshare")
    forbidden = sum(len(forbidden_pattern.findall(path.read_text(encoding="utf-8"))) for path in active_paths)
    require(forbidden == 0, "active publication metadata contains an excluded umbrella/destination term")
    require(metadata.get("version") == VERSION, "Zenodo metadata version drift")
    require(metadata.get("access_right") == "open", "Zenodo access is not open")
    require(EXACT_DOI in metadata.get("description", ""), "exact DOI absent from Zenodo description")
    require(CONCEPT_DOI in metadata.get("description", ""), "concept DOI absent from Zenodo description")
    require("https://github.com/KokunoYumeto/ega-ko" in metadata.get("description", ""), "canonical GitHub link absent")
    require("through §2.2.1" in metadata.get("description", ""), "R38 terminal coverage absent from metadata")
    require("lines 1–1683" in metadata.get("description", ""), "R38 canonical line coverage absent from metadata")
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


def validate_expert_review(repo: Path) -> tuple[Path, Path, dict[str, Any], int]:
    expert_dir = repo / "evidence" / "expert_review"
    receipt_path = expert_dir / "PUBLIC_EXPERT_REVIEW_RECEIPT.json"
    jsonl_path = expert_dir / "EXPERT_REVIEW.jsonl"
    markdown_path = expert_dir / "EXPERT_REVIEW.md"
    for path in (receipt_path, jsonl_path, markdown_path):
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe expert-review file: {path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    outputs = receipt.get("outputs", {})
    records = receipt.get("records", {}).get("total")
    require(receipt.get("schema") == "agko-public-expert-review-receipt-v1", "expert-review receipt schema drift")
    require(receipt.get("result") == "PASS_COMPLETE_LEDGER_COVERAGE_WITH_INCOMPLETE_CORPUS_SCOPE", "expert-review generation did not pass")
    require("through EGA II 2.2.1" in receipt.get("coverage", ""), "expert-review coverage is stale")
    require(records == 546, "R38 expert-review record count drift")
    for name, path in (("EXPERT_REVIEW.jsonl", jsonl_path), ("EXPERT_REVIEW.md", markdown_path)):
        row = outputs.get(name, {})
        assert_ident(path, row.get("bytes"), row.get("sha256"), f"expert-review output {name}")
    ids = {
        json.loads(line)["source_record_id"]
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    require({"AGKO-D187", "AGKO-H162"}.issubset(ids), "expert-review snapshot lacks the controlling R38 records")
    for item in ids:
        match = re.fullmatch(r"AGKO-([DH])(\d+)", item)
        if match:
            cutoff = 187 if match.group(1) == "D" else 162
            require(int(match.group(2)) <= cutoff, f"post-R38 expert-review record leaked: {item}")
    return receipt_path, jsonl_path, receipt, records


def validate_r38_controls(repo: Path, private_root: Path, reader: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest_path = repo / "source" / "CUMULATIVE_INPUTS.json"
    build_script = repo / "build" / "BUILD.ps1"
    build_receipt_path = repo / "evidence" / "BUILD_RECEIPT.json"
    strict_path = repo / "evidence" / "controls" / "R38_STRICT_BUILD.json"
    admission_path = repo / "evidence" / "controls" / "R38_TRANSLATION_ADMISSION.json"
    integration_path = repo / "evidence" / "controls" / "R38_TRANSLATION_INTEGRATION.json"
    inventory_path = repo / "evidence" / "controls" / "R38_CANONICAL_INVENTORY_REFRESH.json"
    reconciliation_path = repo / "evidence" / "controls" / "R38_POST_CORRECTION_SOURCE_RECONCILIATION.json"
    qa_path = repo / "evidence" / "controls" / "R38_PDF_QA.json"
    target_path = repo / "source" / "c2s1.tex"
    poppler_path = repo / "evidence" / "extract.txt"
    pypdf_path = repo / "evidence" / "extract-pypdf.txt"
    log_r38_path = repo / "evidence" / "build-r38.log"
    log_current_path = repo / "evidence" / "build.log"

    assert_ident(reader, PDF_BYTES, PDF_SHA, "R38 reader")
    assert_ident(manifest_path, MANIFEST_BYTES, MANIFEST_SHA, "R38 cumulative manifest")
    assert_ident(build_script, BUILD_SCRIPT_BYTES, BUILD_SCRIPT_SHA, "R38 build script")
    assert_ident(build_receipt_path, BUILD_RECEIPT_BYTES, BUILD_RECEIPT_SHA, "R38 build receipt")
    assert_ident(strict_path, STRICT_BUILD_BYTES, STRICT_BUILD_SHA, "R38 strict-build control")
    assert_ident(admission_path, ADMISSION_BYTES, ADMISSION_SHA, "R38 translation admission")
    assert_ident(integration_path, INTEGRATION_BYTES, INTEGRATION_SHA, "R38 translation integration")
    assert_ident(inventory_path, INVENTORY_REFRESH_BYTES, INVENTORY_REFRESH_SHA, "R38 canonical inventory refresh")
    assert_ident(reconciliation_path, RECONCILIATION_BYTES, RECONCILIATION_SHA, "R38 source reconciliation")
    assert_ident(qa_path, PDF_QA_BYTES, PDF_QA_SHA, "R38 PDF QA")
    assert_ident(target_path, TARGET_BYTES, TARGET_SHA, "R38 integrated Korean target")
    assert_ident(poppler_path, POPPLER_BYTES, POPPLER_SHA, "R38 frozen Poppler extraction")
    assert_ident(pypdf_path, PYPDF_BYTES, PYPDF_SHA, "R38 frozen pypdf extraction")
    assert_ident(log_r38_path, SANITIZED_LOG_BYTES, SANITIZED_LOG_SHA, "R38 sanitized build log")
    assert_ident(log_current_path, SANITIZED_LOG_BYTES, SANITIZED_LOG_SHA, "current sanitized build-log alias")
    require(log_r38_path.read_bytes() == log_current_path.read_bytes(), "R38 sanitized build-log aliases differ")
    for page, (expected_bytes, expected_sha) in RENDER_IDENTITIES.items():
        assert_ident(repo / "evidence" / "render" / f"r38-p{page:03d}.png", expected_bytes, expected_sha, f"R38 render page {page}")
    require(target_path.read_bytes().count(b"\n") == TARGET_LINES, "R38 target LF-line drift")
    assert_ident(private_root / "ega" / "II" / "c2s1.tex", TARGET_BYTES, TARGET_SHA, "private R38 integrated Korean target")
    require((private_root / "ega" / "II" / "c2s1.tex").read_bytes() == target_path.read_bytes(), "private/public R38 target mirrors differ")
    for control_name, public_path in (
        ("R38_TRANSLATION_ADMISSION.json", admission_path),
        ("R38_TRANSLATION_INTEGRATION.json", integration_path),
        ("R38_CANONICAL_INVENTORY_REFRESH.json", inventory_path),
        ("R38_POST_CORRECTION_SOURCE_RECONCILIATION.json", reconciliation_path),
        ("R38_STRICT_BUILD.json", strict_path),
        ("R38_PDF_QA.json", qa_path),
    ):
        private_path = private_root / "controls" / control_name
        require(private_path.is_file() and private_path.read_bytes() == public_path.read_bytes(), f"private/public control mirrors differ: {control_name}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scope = manifest.get("scope", {})
    require(scope.get("historical_source_pages") == HISTORICAL_MARKERS, "manifest historical-marker count drift")
    require("through2.2.1" in scope.get("terminal_coverage", ""), "manifest omits terminal 2.2.1 coverage")
    require("lines1-1683" in scope.get("terminal_coverage", ""), "manifest omits canonical lines1-1683")
    c2_rows = [row for row in manifest.get("coverage_matrix", []) if row.get("target_path") == "c2s1.tex"]
    require(len(c2_rows) == 1, "manifest c2s1 coverage row absent or duplicated")
    c2_row = c2_rows[0]
    admitted_slice = c2_row.get("admitted_source_slice", {})
    require((admitted_slice.get("lines"), admitted_slice.get("lf_bytes"), admitted_slice.get("sha256")) == ("1-1683", PREFIX_BYTES, PREFIX_SHA), "manifest current admitted-prefix drift")
    require((c2_row.get("target_bytes"), c2_row.get("target_sha256")) == (TARGET_BYTES, TARGET_SHA), "manifest target drift")

    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    require(admission.get("schema") == "agko-r38-translation-admission-v1", "wrong R38 admission schema")
    require(admission.get("state", {}).get("translation") == "admitted_candidate", "R38 candidate is not admitted")
    authority = admission.get("authority", {})
    require((authority.get("whole_bytes"), authority.get("whole_lf_lines"), authority.get("whole_sha256")) == (PRE_CORRECTION_CANONICAL_BYTES, CANONICAL_LINES, PRE_CORRECTION_CANONICAL_SHA), "historical R38 admission whole-file binding drift")
    require(authority.get("unit_lines") == "1607-1683", "R38 admitted unit lines drift")
    require(authority.get("unit_bytes") == UNIT_BYTES, "R38 unit byte-count drift")
    require(authority.get("unit_characters") == UNIT_CHARACTERS, "R38 unit character-count drift")
    require(authority.get("unit_sha256") == UNIT_SHA, "R38 unit SHA-256 drift")
    require(authority.get("admitted_prefix_lines") == "1-1683", "R38 historical admitted prefix lines drift")
    require(authority.get("admitted_prefix_bytes") == PRE_CORRECTION_PREFIX_BYTES, "R38 historical prefix byte-count drift")
    require(authority.get("admitted_prefix_sha256") == PRE_CORRECTION_PREFIX_SHA, "R38 historical prefix SHA-256 drift")
    candidate = admission.get("candidate", {})
    require(candidate.get("bytes") == CANDIDATE_BYTES, "R38 candidate byte-count drift")
    require(candidate.get("characters") == 2_773 and candidate.get("lf_lines") == 80, "R38 candidate character/LF-line drift")
    require(candidate.get("sha256") == CANDIDATE_SHA, "R38 candidate SHA-256 drift")
    require(candidate.get("separator_plus_candidate_bytes") == 4_600, "R38 separator-plus-candidate byte-count drift")
    require(candidate.get("separator_plus_candidate_sha256") == "028E9D2AF3D2297C5F8D93AE07C3C2F48B499FFAA33A1FCD38BB7D9B2BC31DF4", "R38 separator-plus-candidate SHA-256 drift")
    require(admission.get("integrated_target") is None, "historical candidate-only admission unexpectedly claims integration")
    require(admission.get("structure_and_formula_validation", {}).get("result") == "PASS_R38_SOURCE_CANDIDATE_AND_PROSPECTIVE_MIRRORS", "R38 candidate validator did not pass")
    structure = admission.get("structure_and_formula_validation", {})
    require(structure.get("source_inline_formula_count") == structure.get("target_inline_formula_count") == 111, "R38 inline-formula count drift")
    require(structure.get("global_formula_multiset_exact") is True, "R38 target formula multiset drift")
    require(structure.get("labels") == ["II.2.1.10-ko", "II.2.1.11-ko", "subsection:II.2.2-ko", "II.2.2.1-ko"] and structure.get("oldpage") == "II24", "R38 label/oldpage binding drift")

    integration = json.loads(integration_path.read_text(encoding="utf-8"))
    require(integration.get("schema") == "agko-r38-translation-integration-v1", "wrong R38 integration schema")
    final_integration = integration.get("final_integration", {})
    require((final_integration.get("bytes"), final_integration.get("lf_lines"), final_integration.get("sha256")) == (TARGET_BYTES, TARGET_LINES, TARGET_SHA), "R38 final integration identity drift")
    require(final_integration.get("candidate_target_lines") == "1629-1708" and final_integration.get("private_public_exact") is True, "R38 final integration boundary drift")
    require(str(integration.get("result", "")).startswith("PASS_R38_TRANSLATION_INTEGRATION"), "R38 integration did not pass")

    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    require(reconciliation.get("schema") == "agko-r38-post-correction-source-reconciliation-v1", "wrong R38 reconciliation schema")
    current_source = reconciliation.get("canonical_source", {}).get("postimage", {})
    require((current_source.get("bytes"), current_source.get("sha256")) == (CANONICAL_BYTES, CANONICAL_SHA), "current canonical source reconciliation drift")
    unit = reconciliation["source_span_replay"]["r38_unit_lines1607_1683"]
    prefix = reconciliation["source_span_replay"]["admitted_prefix_lines1_1683"]
    require((unit.get("bytes"), unit.get("characters"), unit.get("sha256"), unit.get("unchanged")) == (UNIT_BYTES, UNIT_CHARACTERS, UNIT_SHA, True), "reconciled R38 unit drift")
    require((prefix.get("postimage_bytes"), prefix.get("postimage_sha256")) == (PREFIX_BYTES, PREFIX_SHA), "reconciled R38 prefix drift")
    require((reconciliation["korean_target"].get("bytes"), reconciliation["korean_target"].get("sha256"), reconciliation["korean_target"].get("translation_change_required")) == (TARGET_BYTES, TARGET_SHA, False), "reconciled Korean target drift")
    require(reconciliation.get("result") == "PASS_R38_POST_CORRECTION_SOURCE_RECONCILIATION_REBUILD_REQUIRED", "R38 reconciliation did not pass")

    strict = json.loads(strict_path.read_text(encoding="utf-8"))
    require(strict.get("schema") == "agko-r38-strict-build-control-v1", "wrong R38 strict-build schema")
    release = strict.get("release", {})
    require((release.get("version"), release.get("exact_doi"), release.get("concept_doi")) == (VERSION, EXACT_DOI, CONCEPT_DOI), "R38 strict release identity drift")
    require(strict.get("reader") == {"path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf", "bytes": PDF_BYTES, "sha256": PDF_SHA, "pages": PDF_PAGES}, "R38 strict reader record drift")
    require(strict.get("strict_build", {}).get("xelatex_passes") == 8 and strict.get("strict_build", {}).get("independent_clean_cycles") == 2, "R38 strict-build pass/cycle count drift")
    convergence = strict.get("convergence", {})
    require(convergence.get("cycle_a", {}).get("pass3_equals_pass4") is True, "strict cycle A lacks pass3=pass4")
    require(convergence.get("cycle_b", {}).get("pass3_equals_pass4") is True, "strict cycle B lacks pass3=pass4")
    require(convergence.get("cycle_finals_byte_identical") is True, "strict cycle finals differ")
    require(convergence.get("reader_promotion_byte_identical_to_both_cycle_finals") is True, "strict reader promotion differs")
    require(strict.get("status") == "PASS_R38_STRICT_TWO_CYCLE_FOUR_PASS_BUILD", "R38 strict build did not pass")

    build_receipt = json.loads(build_receipt_path.read_text(encoding="utf-8"))
    require(build_receipt.get("version") == VERSION, "R38 build-receipt version drift")
    require(build_receipt.get("exact_doi") == EXACT_DOI and build_receipt.get("concept_doi") == CONCEPT_DOI, "R38 build-receipt DOI drift")
    require(build_receipt.get("status") == "PASS_LOCAL_BUILD_AND_PDF_QA", "R38 build/QA receipt did not pass")
    require(build_receipt.get("coverage_manifest", {}).get("historical_markers") == HISTORICAL_MARKERS, "R38 build-receipt marker drift")
    require(build_receipt.get("convergence", {}).get("cycle_finals_byte_identical") is True, "R38 build-receipt cycles differ")
    require(build_receipt.get("post_correction_source_reconciliation") == ident(reconciliation_path, repo), "R38 build-receipt reconciliation binding drift")
    public_logs = build_receipt.get("logs", {}).get("public_sanitized", [])
    require(public_logs == [ident(log_r38_path, repo), ident(log_current_path, repo)], "R38 build-receipt sanitized-log binding drift")

    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    require(qa.get("schema") == "agko-r38-pdf-qa-v1" and qa.get("edition") == VERSION, "wrong R38 PDF QA identity")
    require(qa.get("status") == "PASS", "R38 PDF QA did not pass")
    qa_pdf = qa.get("pdf", {})
    require((qa_pdf.get("bytes"), qa_pdf.get("sha256"), qa_pdf.get("pages")) == (PDF_BYTES, PDF_SHA, PDF_PAGES), "R38 PDF QA reader drift")
    require(qa.get("historical_markers", {}).get("source_count") == HISTORICAL_MARKERS, "R38 PDF QA marker drift")
    require(qa.get("historical_markers", {}).get("pypdf_full_sequence_matches") is True, "R38 full marker sequence failed")
    require(qa.get("historical_markers", {}).get("normalized_sequence_sha256") == "15805A340D0B9133B7787951F07930F9E7473C90ACDE78AE916525E9A3388F3E", "R38 normalized marker-sequence drift")
    require(qa.get("historical_markers", {}).get("ranges") == ["I|5-8", "0I|11-78", "I|79-214", "II|5-24"], "R38 historical marker-range drift")
    require(qa.get("historical_markers", {}).get("terminal_marker") == ["II", 24], "R38 terminal historical marker drift")
    require(qa.get("source_bindings", {}).get("input_validation", {}).get("ordered_input_count") == 17, "R38 ordered reader-input count drift")
    required_controls = qa.get("required_controls", {})
    require(required_controls.get("strict_build") == {"path": "evidence/controls/R38_STRICT_BUILD.json", "bytes": STRICT_BUILD_BYTES, "sha256": STRICT_BUILD_SHA}, "R38 QA strict-build binding drift")
    require(required_controls.get("post_correction_source_reconciliation") == {"path": "evidence/controls/R38_POST_CORRECTION_SOURCE_RECONCILIATION.json", "bytes": RECONCILIATION_BYTES, "sha256": RECONCILIATION_SHA}, "R38 QA reconciliation binding drift")
    require(required_controls.get("all_private_public_exact") is True, "R38 QA control mirrors are not exact")
    require(qa.get("visual_findings", {}).get("status") == "PASS_NO_OBSERVED_DEFECTS", "R38 rendered visual QA did not pass")
    require(qa.get("font_unicode", {}).get("all_type0_hangul_fonts_have_tounicode") is True, "R38 Hangul ToUnicode gate failed")
    qa_target = qa.get("source_bindings", {}).get("korean_target", {})
    require((qa_target.get("bytes"), qa_target.get("sha256"), qa_target.get("lf_lines")) == (TARGET_BYTES, TARGET_SHA, TARGET_LINES), "R38 QA target binding drift")
    qa_candidate = qa.get("source_bindings", {}).get("candidate", {})
    require((qa_candidate.get("bytes"), qa_candidate.get("sha256")) == (CANDIDATE_BYTES, CANDIDATE_SHA), "R38 QA candidate binding drift")
    render_pages = {row.get("physical_page") for row in qa.get("renders", [])}
    require(render_pages == set(RENDER_IDENTITIES), "R38 portable replay reference renders are incomplete")
    return admission, integration, qa, strict, reconciliation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    private_root = args.private_root.resolve()
    release_root = repo / "release"
    release = release_root / VERSION
    release_stage = release_root / f".{VERSION}-staging"
    require(not release.exists(), f"refusing to reuse existing release directory: {release}")
    require(not release_stage.exists() and not release_stage.is_symlink(), f"refusing to reuse R38 release stage: {release_stage}")

    reader = repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    admission, integration, qa, strict, reconciliation = validate_r38_controls(repo, private_root, reader)
    metadata_summary = validate_metadata(repo)
    evidence_allowlist = load_evidence_allowlist(repo)
    excluded_future = future_evidence(repo)
    expert_receipt_path, expert_jsonl_path, expert_receipt, expert_records = validate_expert_review(repo)
    expert_outputs = expert_receipt["outputs"]
    source_files = root_source_files(repo, private_root, release_root)
    snapshot_root, initial_overrides, unit_cutoff = prepare_release_cutoff_snapshot(repo, private_root)
    snapshot_cleanup = lambda: safe_remove_owned_stage(snapshot_root, private_root, "r38-package-evidence-snapshot")
    atexit.register(snapshot_cleanup)
    cutoff_evidence = materialize_evidence_cutoff(repo, release_root, snapshot_root, initial_overrides, evidence_allowlist)
    artifact_snapshot = snapshot_root / "ARTIFACT_SHA256.tsv"
    artifact_payload, artifact_entries = artifact_manifest(repo, source_files, reader, release_root, cutoff_evidence, artifact_snapshot)
    current_evidence = sorted(cutoff_evidence + [(artifact_snapshot, "ARTIFACT_SHA256.tsv")], key=lambda item: item[1])
    privacy = privacy_scan(source_files + current_evidence + [(reader, "reader/00_EGA_ko_CUMULATIVE_READER.pdf")])

    release_root.mkdir(parents=True, exist_ok=True)
    release_stage.mkdir()
    release_cleanup = lambda: safe_remove_release_stage(release_stage, release_root)
    atexit.register(release_cleanup)
    reader_release = release_stage / "00_EGA_ko_CUMULATIVE_READER.pdf"
    shutil.copyfile(reader, reader_release)
    assert_ident(reader_release, PDF_BYTES, PDF_SHA, "frozen R38 reader")

    source_zip = release_stage / "01_EGA_ko_EDITABLE_SOURCES.zip"
    evidence_zip = release_stage / "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip"
    source_verification, source_equal = build_twice(source_zip, source_files)
    evidence_verification, evidence_equal = build_twice(evidence_zip, current_evidence)

    outer_files = [reader_release, source_zip, evidence_zip]
    manifest_lines = ["filename\tbytes\tsha256"]
    for path in outer_files:
        manifest_lines.append(f"{path.name}\t{path.stat().st_size}\t{sha_file(path)}")
    outer_manifest = release_stage / "03_EGA_ko_SHA256_MANIFEST.txt"
    require(not outer_manifest.exists(), f"refusing to overwrite outer manifest: {outer_manifest}")
    outer_manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8", newline="\n")
    outer_privacy = privacy_scan([(outer_manifest, outer_manifest.name)])

    file_rows = [
        {"order": 0, "name": reader_release.name, "bytes": reader_release.stat().st_size, "sha256": sha_file(reader_release), "role": "front cumulative reader artifact", "pages": PDF_PAGES},
        {"order": 1, "name": source_zip.name, "bytes": source_zip.stat().st_size, "sha256": sha_file(source_zip), "role": "deterministic editable-source and R38 replay/validation-script archive", **source_verification},
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
            "included_volumes": ["EGA 0_I", "EGA I", "EGA II (programme/table of contents and main text through2.2.1)"],
            "terminal_coverage": "EGA II Chapter II programme/table of contents through source EOF, followed by ega2/ega2-1-fr.tex lines1-1683 through2.2.1",
            "completeness_claim": "all locally completed and hash-admitted Korean EGA targets are included; EGA II and the full EGA corpus remain incomplete",
            "historical_source_pages": HISTORICAL_MARKERS,
            "historical_page_ranges": ["EGA I introduction5-8", "EGA 0_I11-78", "EGA I Chapter I79-214", "EGA II5-24"],
        },
        "r38_translation_binding": {
            "source_unit": {"lines": "1607-1683", "bytes": UNIT_BYTES, "characters": UNIT_CHARACTERS, "sha256": UNIT_SHA},
            "canonical_prefix": {"lines": "1-1683", "bytes": PREFIX_BYTES, "sha256": PREFIX_SHA, "binding_control": ident(repo / "evidence" / "controls" / "R38_POST_CORRECTION_SOURCE_RECONCILIATION.json", repo)},
            "candidate": {"bytes": CANDIDATE_BYTES, "sha256": CANDIDATE_SHA},
            "integrated_target": {"bytes": TARGET_BYTES, "lf_lines": TARGET_LINES, "sha256": TARGET_SHA},
            "admission_control": ident(repo / "evidence" / "controls" / "R38_TRANSLATION_ADMISSION.json", repo),
            "integration_control": ident(repo / "evidence" / "controls" / "R38_TRANSLATION_INTEGRATION.json", repo),
            "validator_result": admission["structure_and_formula_validation"]["result"],
            "integration_result": integration["result"],
            "reconciliation_result": reconciliation["result"],
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
            "strict_build_control": ident(repo / "evidence" / "controls" / "R38_STRICT_BUILD.json", repo),
            "pdf_control": ident(repo / "evidence" / "controls" / "R38_PDF_QA.json", repo),
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
            "r38_records_present": ["AGKO-D187", "AGKO-H162"],
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
        "source_archive_required_scripts": sorted(REQUIRED_R38_SCRIPTS),
        "source_archive_required_scripts_present": True,
        "r38_evidence_release_cutoff": {
            "allowlist": ident(repo / EVIDENCE_ALLOWLIST_PATH, repo),
            "allowlisted_live_members": len(evidence_allowlist),
            "allowlisted_live_member_names": evidence_allowlist,
            "generated_members": ["ARTIFACT_SHA256.tsv"],
            "final_archive_file_members": len(current_evidence),
            "final_archive_member_names_sha256": sha_bytes(("\n".join(name for _, name in current_evidence) + "\n").encode("utf-8")),
            "live_inventory_exactly_classified": True,
            "verification": "PASS",
        },
        "evidence_input_scope": "Exact, explicit R38 release-cutoff allowlist; every live evidence file is classified as included, regenerated manifest, or named post-R38 exclusion. Included members are copied to a stable snapshot before archive mutation; regenerated ARTIFACT_SHA256.tsv binds every included member; current release/package outputs are excluded.",
        "r38_unit_index_cutoff": unit_cutoff,
        "future_unit_evidence_excluded_from_r38_snapshot": [ident(path, repo / "evidence") for path, _ in excluded_future],
        "future_unit_evidence_exclusion_reason": "Preserved in the live tree but outside the immutable R38 evidence snapshot because it belongs to post-R38 R39/R40/R41 translation or later source-basis support work.",
        "metadata": metadata_summary,
        "privacy_credential_check": privacy,
        "outer_manifest_privacy_credential_check": outer_privacy,
        "package_receipt_privacy_credential_check": {
            "scope": "The final serialized PACKAGE_RECEIPT.json is scanned immediately after writing and before promotion with the same account/profile/credential gate.",
            "matches": 0,
            "result": "PASS_POST_SERIALIZATION_FAIL_CLOSED",
        },
        "publication_status": "as of package freeze: local package only; draft and repository state are not publication claims",
        "portable_replay": "as of package freeze: not yet run; separate PORTABLE_BUILD_REPLAY.json is required",
        "result": "PASS_R38_LOCAL_PACKAGE",
    }
    receipt_path = release_stage / "PACKAGE_RECEIPT.json"
    require(not receipt_path.exists(), f"refusing to overwrite package receipt: {receipt_path}")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    require(json.loads(receipt_path.read_text(encoding="utf-8")) == receipt, "written R38 package receipt replay drift")
    receipt_privacy = privacy_scan([(receipt_path, receipt_path.name)])
    require(receipt_privacy["matches"] == 0 and receipt_privacy["result"] == "PASS", "written R38 package receipt privacy gate failed")
    final_source = {path.name: (path.stat().st_size, sha_file(path)) for path in release_stage.iterdir() if path.is_file()}
    require(set(final_source) == {"00_EGA_ko_CUMULATIVE_READER.pdf", "01_EGA_ko_EDITABLE_SOURCES.zip", "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip", "03_EGA_ko_SHA256_MANIFEST.txt", "PACKAGE_RECEIPT.json"}, "R38 staged release inventory drift")
    safe_remove_owned_stage(snapshot_root, private_root, "r38-package-evidence-snapshot")
    atexit.unregister(snapshot_cleanup)
    release_stage.rename(release)
    atexit.unregister(release_cleanup)
    require(release.is_dir() and not release_stage.exists(), "R38 release promotion failed")
    source_zip = release / source_zip.name
    evidence_zip = release / evidence_zip.name
    receipt_path = release / receipt_path.name
    require((source_zip.stat().st_size, sha_file(source_zip)) == final_source[source_zip.name], "promoted R38 source ZIP drift")
    require((evidence_zip.stat().st_size, sha_file(evidence_zip)) == final_source[evidence_zip.name], "promoted R38 evidence ZIP drift")
    require((receipt_path.stat().st_size, sha_file(receipt_path)) == final_source[receipt_path.name], "promoted R38 package receipt drift")
    print(
        "PASS_R38_LOCAL_PACKAGE|"
        f"source={source_zip.stat().st_size}/{sha_file(source_zip)}|"
        f"evidence={evidence_zip.stat().st_size}/{sha_file(evidence_zip)}|"
        f"receipt={receipt_path.stat().st_size}/{sha_file(receipt_path)}"
    )


if __name__ == "__main__":
    main()
