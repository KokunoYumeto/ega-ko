#!/usr/bin/env python3
"""Replay the frozen R38 source archive under its BUILD.ps1 TeX mutex."""

from __future__ import annotations

import argparse
import atexit
import binascii
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import pypdf
from pypdf import PdfReader


VERSION = "2026-09-05-r38"
EXACT_DOI = "10.5281/zenodo.22346664"
CONCEPT_DOI = "10.5281/zenodo.21921513"
STRICT_PDF_BYTES = 1_485_270
STRICT_PDF_SHA = "FEC06D6723BFE9CC7D3C46E285C7DE8A49929F2797FD2F4F47877D2BDA06FE15"
PAGES = 239
BUILD_SCRIPT_BYTES = 20_370
BUILD_SCRIPT_SHA = "330A0F8337C6019010700088E0D8D398EA0B33CA922D06641D607E2F63D51F77"
MANIFEST_BYTES = 16_250
MANIFEST_SHA = "50C9896A8436E2A381817BA322DE45A5EFCB768F2790E7BC14A206D70AAA81AE"
EVIDENCE_ALLOWLIST_MEMBER = "scripts/r38_evidence_release_cutoff.txt"
EVIDENCE_ALLOWLIST_BYTES = 11_251
EVIDENCE_ALLOWLIST_SHA = "65041CD99A37F92180D5C878061668CF9EC6887CA606DA575934F8174D5B1479"
EVIDENCE_ALLOWLIST_ENTRIES = 501
TARGET_BYTES = 80_222
TARGET_SHA = "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006"
CANDIDATE_BYTES = 4_599
CANDIDATE_SHA = "8D37AF2B8B05D9C938F2D282F58902092FB7FCF55300B0A85B28C9538340CF93"
VALIDATOR_BYTES = 16_396
VALIDATOR_SHA = "3FC051E0944E506E1F6366B84CC3B55B279FA74B7E6F183ED6ECE38E6D830AAC"
INTEGRATION_HELPER_BYTES = 38_677
INTEGRATION_HELPER_SHA = "2156E105DAE509E13556BD6989AE9079FC916A16F68B5E43E2162E8DA777A9F1"
QA_SCRIPT_BYTES = 41_547
QA_SCRIPT_SHA = "CA8449B6FDF0757783F48DC9B969C49B766D4835EDA1223F86CBB2C34268141E"
EXPERT_VALIDATOR_BYTES = 7_676
EXPERT_VALIDATOR_SHA = "5A443803627718C00F4BA77813174686CEB244951039529427A3C61D0031EAD6"
PREPARE_SCRIPT_BYTES = 20_788
PREPARE_SCRIPT_SHA = "342EAA16F884613E2D626C1DA6B5E4BD64125B15DA8AA693DCB8DFC792A8BC51"
PACKAGE_SCRIPT_BYTES = 58_205
PACKAGE_SCRIPT_SHA = "BB0BCBBCFBF2DAC3F3D0B69868A57D998611A80FA8F1FF143E6A875DFD084B3D"
CANONICAL_UNIT_LINES = "1607-1683"
CANONICAL_UNIT_BYTES = 4_191
CANONICAL_UNIT_CHARACTERS = 4_096
CANONICAL_UNIT_SHA = "44583D53F17603797145FE63822F3F78DC6ECFD7ADA1B38EF01813F9E3F22BE6"
CANONICAL_PREFIX_LINES = "1-1683"
CANONICAL_PREFIX_BYTES = 78_088
CANONICAL_PREFIX_SHA = "7DE4ECF8630F2B575C08ED0EE4AEC560F6BD4C6026C4BC894DD057D4AE1B9B75"
HISTORICAL_MARKERS = 228
TERMINAL_HISTORICAL_MARKER = "II|24"
NEXT_CANONICAL_LINE = 1_685
POPPLER_BYTES = 728_827
POPPLER_SHA = "B5A047C7799FD4A741099CE9334797F26CCDDD5EC9D68F9A6A03EFABA6ADDC99"
PYPDF_BYTES = 703_381
PYPDF_SHA = "9207B6B25CBAC5113A6C718C7B970E232E159799AC68CB7C527F908455173AD6"
FROZEN_QA_PYPDF_VERSION = "6.10.0"
SUPPORTED_REPLAY_PYPDF_VERSIONS = {"6.10.0", "6.12.2"}
EXPECTED_PDFTOTEXT_VERSION = "pdftotext version 24.04.0"
EXPECTED_PDFTOPPM_VERSION = "pdftoppm version 26.07.0"
REQUIRED_SOURCE_MEMBERS = {
    "build/BUILD.ps1",
    "source/CUMULATIVE_INPUTS.json",
    "source/c2s1.tex",
    "candidates/r38-c2s1-continuation.tex",
    "candidates/validate_r38_candidate.py",
    "scripts/append_r38_integration_records.py",
    "scripts/package_r38.py",
    "scripts/portable_replay_r38.py",
    "scripts/prepare_r38_release.py",
    "scripts/qa_r38_pdf.py",
    EVIDENCE_ALLOWLIST_MEMBER,
    "scripts/validate_expert_review_log.py",
}
EXCLUDED_POST_R38_EVIDENCE = {
    "controls/EGA2_R63_SOURCE_BASIS_REFRESH_20260905.json",
    "controls/R39_CANONICAL_PREFIX_REBASE.json",
    "controls/R39_TRANSLATION_ADMISSION.json",
    "controls/R40_TRANSLATION_ADMISSION.json",
    "controls/R41_TRANSLATION_ADMISSION.json",
}
RENDER_DPI = 300
RENDER_IDENTITIES = {
    1: (133_699, "8A9C079746DC9D2BAACE84D02E46635FAE87E8073D483A88C962590ED82116E6"),
    2: (494_472, "97F4435291368165C762F357F86E6FCD3AEC2F5ACA41C764D9C0A7D110957723"),
    6: (273_914, "BD71C92D1810D28FE7F9289F4FF20D38452A7970F0CE5BBE742209A7E3B01977"),
    237: (818_805, "F639B832388C5839EA866E69E04479ACCC88FDB9154CE82D75511CBA5D8F10F2"),
    238: (733_896, "3343138791A864AECF7584DB54BA7A375FE5EC613E7D82E6093C210CB66ECDF9"),
    239: (209_400, "8D2157D299589D0A6743DBDF720A2FEF2E5336F2544A5A6C685E5E2DE9ACA834"),
}
RENDER_PAGES = tuple(RENDER_IDENTITIES)
CONTROL_IDENTITIES = {
    "controls/R38_TRANSLATION_ADMISSION.json": (8_103, "23CA8C711E89448D910BCD585BCC815B1A87F56A9890220485F27E3E8377FEC2"),
    "controls/R38_TRANSLATION_INTEGRATION.json": (5_209, "3901DE2B2F9BD1DDB6399D7B35005FAD196F1A3A229061D9D46F3813E58BB020"),
    "controls/R38_CANONICAL_INVENTORY_REFRESH.json": (1_490, "A55400B0236DDB3A32C47C3AA14B45B0ACFF0260EF843779EB0487F6B649ADE3"),
    "controls/R38_POST_CORRECTION_SOURCE_RECONCILIATION.json": (6_698, "C60088AE26B2E33B2CFBCD88044E1F5BDA2636DB2BF93D5E392B62CB4915688C"),
    "controls/R38_STRICT_BUILD.json": (8_533, "E8A844FF6DA59EAFAA890D34E180B81BE2B8D1D639E4801692897B89DA5CD6FB"),
    "controls/R38_PDF_QA.json": (34_043, "5140761219F2C8AFAC7075BEEF1044D4190FA41B590B670FA349DF1EF6B55B45"),
    "controls/R38_ZENODO_DRAFT.json": (676, "F6F543BE6800CD7BED602C6ED928E572A81D25550750919338833E2D9FE64330"),
    "controls/R38_STRICT_BUILD_PRE_CORRECTION.json": (5_677, "2ADAFA3893EA0CD5AD30B730B9C9E99DE074F764A29D08930B3307F9D3410691"),
    "controls/R38_STRICT_BUILD_PRE_PRIVACY.json": (7_613, "98B5AE054414650A7488B98F8DA3A0E20679D1B4036587DAEE05B599707CC8D2"),
}
CONTROL_SCHEMAS = {
    "controls/R38_TRANSLATION_ADMISSION.json": "agko-r38-translation-admission-v1",
    "controls/R38_TRANSLATION_INTEGRATION.json": "agko-r38-translation-integration-v1",
    "controls/R38_CANONICAL_INVENTORY_REFRESH.json": "agko-r38-canonical-inventory-refresh-v1",
    "controls/R38_POST_CORRECTION_SOURCE_RECONCILIATION.json": "agko-r38-post-correction-source-reconciliation-v1",
    "controls/R38_STRICT_BUILD.json": "agko-r38-strict-build-control-v1",
    "controls/R38_PDF_QA.json": "agko-r38-pdf-qa-v1",
    "controls/R38_ZENODO_DRAFT.json": "ag-ko-zenodo-draft-state-v2",
    "controls/R38_STRICT_BUILD_PRE_CORRECTION.json": "agko-r38-strict-build-control-v1",
    "controls/R38_STRICT_BUILD_PRE_PRIVACY.json": "agko-r38-strict-build-control-v1",
}


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


def ident_bytes(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha_bytes(data)}


def assert_ident(path: Path, expected_bytes: int, expected_sha: str, label: str) -> None:
    require(path.is_file(), f"missing {label}: {path}")
    require(path.stat().st_size == expected_bytes, f"{label} byte-count drift")
    require(sha_file(path) == expected_sha, f"{label} SHA-256 drift")


def approved_tool(name: str) -> str:
    resolved = shutil.which(name)
    require(resolved is not None, f"required executable is unavailable: {name}")
    path = Path(resolved).resolve()
    require(path.is_file() and not path.is_symlink(), f"unsafe executable resolution: {name}")
    return str(path)


def pypdf_extract(path: Path) -> bytes:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n") for page in reader.pages]
    return ("\n\f\n".join(pages) + "\n").encode("utf-8")


def poppler_extract(path: Path) -> bytes:
    result = subprocess.run(
        [approved_tool("pdftotext"), "-enc", "UTF-8", "-eol", "unix", str(path), "-"],
        capture_output=True,
        timeout=300,
        check=True,
    )
    return result.stdout


def render(path: Path, page: int, output_prefix: Path) -> Path:
    subprocess.run(
        [approved_tool("pdftoppm"), "-f", str(page), "-l", str(page), "-singlefile", "-r", str(RENDER_DPI), "-png", str(path), str(output_prefix)],
        capture_output=True,
        timeout=180,
        check=True,
    )
    return output_prefix.with_suffix(".png")


def safe_member_name(name: str) -> None:
    path = PurePosixPath(name)
    require(name != "" and "\\" not in name, f"unsafe source ZIP member: {name!r}")
    require(not re.match(r"^[A-Za-z]:", name), f"drive-qualified source ZIP member: {name}")
    require(not path.is_absolute(), f"absolute source ZIP member: {name}")
    require(all(part not in {"", ".", ".."} for part in path.parts), f"traversing source ZIP member: {name}")
    canonical = path.as_posix() + ("/" if name.endswith("/") else "")
    require(name == canonical, f"noncanonical ZIP member name: {name}")
    reserved = {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)}, *{f"LPT{i}" for i in range(1, 10)}}
    for part in path.parts:
        require(":" not in part and not part.endswith((".", " ")), f"Windows-unsafe ZIP member segment: {name}")
        require(part.split(".", 1)[0].upper() not in reserved, f"Windows reserved ZIP member segment: {name}")


def privacy_match_count(data: bytes) -> int:
    account = Path.home().name
    matches = 0
    if account:
        matches += int(account.encode("utf-8") in data)
        matches += int(account.encode("utf-16-le") in data)
        matches += int(account.encode("utf-16-be") in data)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = ""
    if account and re.search(re.escape(account), text, re.I):
        matches += 1
    matches += len(
        re.findall(
            r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/](?:Users|Documents and Settings)[\\/]"
            r"[A-Za-z0-9._-]+(?:[\\/]|$)",
            text,
        )
    )
    matches += len(
        re.findall(
            r"(?i)(?<![A-Za-z0-9_])/(?:home|Users)/[A-Za-z0-9._-]+(?:/|$)",
            text,
        )
    )
    matches += len(re.findall(r"(?i)(?:access_token|api[_-]?key|authorization)\s*[:=]\s*[A-Za-z0-9_\-]{16,}", text))
    matches += len(re.findall(r"(?i)\b(?:ghp|github_pat|sk)-[A-Za-z0-9_\-]{12,}", text))
    matches += len(re.findall(r"(?i)bearer\s+[A-Za-z0-9._~+/=\-]{16,}", text))
    return matches


def verify_frozen_zip(path: Path) -> dict[str, Any]:
    inventory_rows = ["relative_path\tbytes\tcrc32\tsha256"]
    files = directories = uncompressed = 0
    privacy_matches = 0
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        require(0 < len(infos) <= 10_000, f"ZIP entry-count bound failed: {path.name}")
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)), f"duplicate ZIP member: {path.name}")
        require(len({name.casefold() for name in names}) == len(names), f"case-folded ZIP member collision: {path.name}")
        require(sum(info.file_size for info in infos) <= 2_000_000_000, f"ZIP expanded-size bound failed: {path.name}")
        require(archive.testzip() is None, f"ZIP CRC verification failed: {path.name}")
        for info in infos:
            safe_member_name(info.filename)
            require(info.file_size <= 1_000_000_000, f"ZIP member-size bound failed: {info.filename}")
            require(info.compress_size > 0 or info.file_size == 0, f"invalid zero compressed size: {info.filename}")
            if info.compress_size:
                require(info.file_size / info.compress_size <= 10_000, f"ZIP compression-ratio bound failed: {info.filename}")
            data = archive.read(info.filename)
            digest = sha_bytes(data)
            crc = binascii.crc32(data) & 0xFFFFFFFF
            require(len(data) == info.file_size and crc == info.CRC, f"ZIP member identity drift: {info.filename}")
            inventory_rows.append(f"{info.filename}\t{len(data)}\t{crc:08X}\t{digest}")
            if info.is_dir():
                require(not data, f"nonempty ZIP directory: {info.filename}")
                directories += 1
            else:
                files += 1
                uncompressed += len(data)
                privacy_matches += privacy_match_count(data)
    require(privacy_matches == 0, f"archive privacy/credential scan failed: {path.name}")
    inventory = ("\n".join(inventory_rows) + "\n").encode("utf-8")
    return {
        "entries": len(infos),
        "files": files,
        "directories": directories,
        "uncompressed_file_bytes": uncompressed,
        "complete_inventory_bytes": len(inventory),
        "complete_inventory_sha256": sha_bytes(inventory),
        "privacy_matches": privacy_matches,
    }


def extract_and_verify_source(source_zip: Path, stage: Path) -> dict[str, Any]:
    inventory_rows = ["relative_path\tbytes\tcrc32\tsha256"]
    file_count = 0
    directory_count = 0
    with zipfile.ZipFile(source_zip, "r") as archive:
        require(archive.testzip() is None, "source archive CRC verification failed")
        infos = archive.infolist()
        require(0 < len(infos) <= 10_000, "source archive entry-count bound failed")
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)), "source archive contains duplicate member names")
        require(len({name.casefold() for name in names}) == len(names), "source archive contains case-folded member collision")
        require(sum(info.file_size for info in infos) <= 2_000_000_000, "source archive expanded-size bound failed")
        for name in names:
            safe_member_name(name)
        normalized = [name.rstrip("/") for name in names]
        require(len(normalized) == len(set(normalized)), "source archive contains file/directory name collisions")
        normalized_set = set(normalized)
        for name in normalized:
            parts = PurePosixPath(name).parts
            for index in range(1, len(parts)):
                require("/".join(parts[:index]) not in normalized_set or "/".join(parts[:index]) + "/" in names, f"source archive file/directory prefix collision: {name}")
        file_names = {info.filename for info in infos if not info.is_dir()}
        require(REQUIRED_SOURCE_MEMBERS.issubset(file_names), f"source archive lacks R38 replay/validation members: {sorted(REQUIRED_SOURCE_MEMBERS - file_names)}")
        for info in infos:
            require(info.file_size <= 1_000_000_000, f"source archive member-size bound failed: {info.filename}")
            require(info.compress_size > 0 or info.file_size == 0, f"invalid source member compressed size: {info.filename}")
            if info.compress_size:
                require(info.file_size / info.compress_size <= 10_000, f"source member compression-ratio bound failed: {info.filename}")
            mode = stat.S_IFMT(info.external_attr >> 16)
            require(mode in {stat.S_IFREG, stat.S_IFDIR}, f"source archive contains non-file/non-directory member: {info.filename}")
            destination = stage.joinpath(*PurePosixPath(info.filename).parts)
            require(destination.resolve().is_relative_to(stage.resolve()), f"source member escapes replay stage: {info.filename}")
            if info.is_dir():
                require(mode == stat.S_IFDIR and info.file_size == 0 and info.CRC == 0, f"invalid source directory member: {info.filename}")
                destination.mkdir(parents=True, exist_ok=True)
                inventory_rows.append(f"{info.filename}\t0\t00000000\t{sha_bytes(b'')}")
                directory_count += 1
                continue
            require(mode == stat.S_IFREG, f"invalid source file mode: {info.filename}")
            data = archive.read(info.filename)
            crc = binascii.crc32(data) & 0xFFFFFFFF
            require(len(data) == info.file_size, f"source member size drift: {info.filename}")
            require(crc == info.CRC, f"source member CRC drift: {info.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            require(destination.read_bytes() == data, f"extracted source member byte drift: {info.filename}")
            inventory_rows.append(f"{info.filename}\t{len(data)}\t{crc:08X}\t{sha_bytes(data)}")
            file_count += 1
    inventory = ("\n".join(inventory_rows) + "\n").encode("utf-8")
    return {
        "entries_verified": len(infos),
        "files_verified": file_count,
        "directories_verified": directory_count,
        "complete_inventory_bytes": len(inventory),
        "complete_inventory_sha256": sha_bytes(inventory),
        "verification": "PASS safe names, no duplicates, member types, CRC, sizes, extracted bytes and per-file SHA-256 inventory",
    }


def safe_remove_stage(stage: Path, expected_parent: Path) -> None:
    require(not stage.is_symlink(), f"portable replay stage is a symlink/reparse path: {stage}")
    require(not expected_parent.is_symlink(), f"portable staging parent is a symlink/reparse path: {expected_parent}")
    resolved_stage = stage.resolve()
    resolved_parent = expected_parent.resolve()
    require(resolved_stage.parent == resolved_parent, f"unsafe portable stage parent: {resolved_stage}")
    require(resolved_stage.name == "r38-portable-replay", f"unsafe portable stage leaf: {resolved_stage}")
    require(resolved_parent.name == "release-staging", f"unexpected portable staging parent: {resolved_parent}")
    if resolved_stage.exists():
        shutil.rmtree(resolved_stage)
    require(not resolved_stage.exists(), f"portable replay stage cleanup failed: {resolved_stage}")


def parse_terminal(terminal: str) -> tuple[int, str, dict[str, str]]:
    match = re.fullmatch(r"PASS (\d+) bytes SHA-256 ([0-9A-F]{64}); (.+)", terminal)
    require(match is not None, f"malformed BUILD.ps1 terminal record: {terminal!r}")
    fields: dict[str, str] = {}
    for item in match.group(3).split("; "):
        require("=" in item, f"malformed terminal field: {item!r}")
        key, value = item.split("=", 1)
        require(key not in fields, f"duplicate terminal field: {key}")
        fields[key] = value
    return int(match.group(1)), match.group(2), fields


def frozen_evidence_allowlist(source_zip: Path) -> list[str]:
    with zipfile.ZipFile(source_zip, "r") as archive:
        data = archive.read(EVIDENCE_ALLOWLIST_MEMBER)
    require((len(data), sha_bytes(data)) == (EVIDENCE_ALLOWLIST_BYTES, EVIDENCE_ALLOWLIST_SHA), "frozen R38 evidence allowlist identity drift")
    require(data.endswith(b"\n") and b"\r" not in data, "frozen R38 evidence allowlist is not canonical LF text")
    names = data.decode("utf-8").splitlines()
    require(len(names) == EVIDENCE_ALLOWLIST_ENTRIES, "frozen R38 evidence allowlist entry-count drift")
    require(names == sorted(names) and len(names) == len(set(names)), "frozen R38 evidence allowlist ordering/uniqueness drift")
    require("ARTIFACT_SHA256.tsv" not in names and not (set(names) & EXCLUDED_POST_R38_EVIDENCE), "frozen R38 evidence allowlist classification drift")
    return names


def preflight_control_chain(evidence_zip: Path, evidence_allowlist: list[str]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    stats = verify_frozen_zip(evidence_zip)
    payloads: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(evidence_zip, "r") as archive:
        names = {info.filename for info in archive.infolist() if not info.is_dir()}
        expected_names = set(evidence_allowlist) | {"ARTIFACT_SHA256.tsv"}
        require(names == expected_names, f"evidence archive differs from explicit R38 cutoff allowlist: extra={sorted(names - expected_names)}, missing={sorted(expected_names - names)}")
        require(not (names & EXCLUDED_POST_R38_EVIDENCE), "post-R38 evidence leaked into evidence archive")
        required = set(CONTROL_IDENTITIES) | {"ARTIFACT_SHA256.tsv", "index/units.jsonl"}
        require(required.issubset(names), f"R38 evidence preflight members missing: {sorted(required - names)}")
        for name, expected in CONTROL_IDENTITIES.items():
            data = archive.read(name)
            require((len(data), sha_bytes(data)) == expected, f"R38 preflight control identity drift: {name}")
            payloads[name] = json.loads(data)
        units = archive.read("index/units.jsonl")
        unit_lines = units.splitlines()
        require((len(units), sha_bytes(units), len(unit_lines)) == (1_251_540, "BFEB68EDD9C5B8B324A42652E1F1D329AF7044064CF7125822A04ED17874DC0F", 2_148), "R38 unit-index cutoff drift")
        require(json.loads(unit_lines[-1]).get("id") == "AGKO-EGA2-S1-R38-COVERAGE", "R38 unit-index terminal record drift")
    for name, schema in CONTROL_SCHEMAS.items():
        require(payloads[name].get("schema") == schema, f"R38 preflight control schema drift: {name}")
    strict = payloads["controls/R38_STRICT_BUILD.json"]
    reconciliation = payloads["controls/R38_POST_CORRECTION_SOURCE_RECONCILIATION.json"]
    qa = payloads["controls/R38_PDF_QA.json"]
    draft = payloads["controls/R38_ZENODO_DRAFT.json"]
    require(strict.get("status") == "PASS_R38_STRICT_TWO_CYCLE_FOUR_PASS_BUILD", "R38 preflight strict-build status failed")
    require(reconciliation.get("result") == "PASS_R38_POST_CORRECTION_SOURCE_RECONCILIATION_REBUILD_REQUIRED", "R38 preflight reconciliation failed")
    require((qa.get("edition"), qa.get("status")) == (VERSION, "PASS"), "R38 preflight PDF QA failed")
    require((draft.get("status"), draft.get("exact_doi"), draft.get("concept_doi")) == ("reserved_unpublished", EXACT_DOI, CONCEPT_DOI), "R38 Zenodo draft reservation drift")
    require((strict.get("superseded_pre_correction_seal", {}).get("bytes"), strict.get("superseded_pre_correction_seal", {}).get("sha256")) == CONTROL_IDENTITIES["controls/R38_STRICT_BUILD_PRE_CORRECTION.json"], "R38 pre-correction strict-seal binding drift")
    require((strict.get("superseded_pre_privacy_seal", {}).get("bytes"), strict.get("superseded_pre_privacy_seal", {}).get("sha256")) == CONTROL_IDENTITIES["controls/R38_STRICT_BUILD_PRE_PRIVACY.json"], "R38 pre-privacy strict-seal binding drift")
    return stats, payloads


def verify_internal_manifest(source_zip: Path, evidence_zip: Path, strict_reader: Path, declared: dict[str, Any]) -> None:
    with zipfile.ZipFile(evidence_zip, "r") as evidence_archive:
        payload = evidence_archive.read("ARTIFACT_SHA256.tsv")
        require((len(payload), sha_bytes(payload)) == (declared.get("bytes"), declared.get("sha256")), "internal manifest/package-receipt identity drift")
        lines = payload.decode("utf-8").splitlines()
        require(lines and lines[0] == "relative_path\tbytes\tsha256", "internal manifest header drift")
        rows: dict[str, tuple[int, str]] = {}
        for line in lines[1:]:
            parts = line.split("\t")
            require(len(parts) == 3, "malformed internal manifest row")
            name, byte_text, digest = parts
            require(name not in rows and re.fullmatch(r"[0-9A-F]{64}", digest), f"invalid internal manifest row: {name}")
            rows[name] = (int(byte_text), digest)
        require(list(rows) == sorted(rows), "internal manifest row order drift")
        require(len(rows) == declared.get("entries"), "internal manifest entry-count drift")
        expected: dict[str, tuple[int, str]] = {}
        with zipfile.ZipFile(source_zip, "r") as source_archive:
            for info in source_archive.infolist():
                if not info.is_dir():
                    data = source_archive.read(info.filename)
                    expected[info.filename] = (len(data), sha_bytes(data))
        reader_data = strict_reader.read_bytes()
        expected["reader/00_EGA_ko_CUMULATIVE_READER.pdf"] = (len(reader_data), sha_bytes(reader_data))
        for info in evidence_archive.infolist():
            if not info.is_dir() and info.filename != "ARTIFACT_SHA256.tsv":
                data = evidence_archive.read(info.filename)
                expected[f"evidence/{info.filename}"] = (len(data), sha_bytes(data))
    require(rows == dict(sorted(expected.items())), "internal manifest does not bind the exact source/evidence/reader member set")


def write_receipt_exclusive(path: Path, payload: bytes) -> None:
    require(not path.exists() and not path.is_symlink(), f"portable receipt target already exists or is a symlink: {path}")
    require(path.parent.is_dir() and not path.parent.is_symlink(), f"unsafe portable receipt parent: {path.parent}")
    temporary = path.parent / f".{path.name}.tmp"
    require(not temporary.exists() and not temporary.is_symlink(), f"portable receipt temporary target exists: {temporary}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        require(json.loads(temporary.read_text(encoding="utf-8")), "temporary portable receipt parse failed")
        os.rename(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    private_root = args.private_root.resolve()
    release = repo / "release" / VERSION
    source_zip = release / "01_EGA_ko_EDITABLE_SOURCES.zip"
    evidence_zip = release / "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip"
    strict_reader = release / "00_EGA_ko_CUMULATIVE_READER.pdf"
    receipt_path = release / "PORTABLE_BUILD_REPLAY.json"
    package_receipt_path = release / "PACKAGE_RECEIPT.json"
    outer_manifest_path = release / "03_EGA_ko_SHA256_MANIFEST.txt"
    staging_parent = private_root / "release-staging"
    stage = staging_parent / "r38-portable-replay"

    require(release.is_dir(), f"R38 release directory is absent: {release}")
    require(source_zip.is_file(), f"R38 frozen source archive is absent: {source_zip}")
    require(evidence_zip.is_file(), f"R38 frozen evidence archive is absent: {evidence_zip}")
    assert_ident(strict_reader, STRICT_PDF_BYTES, STRICT_PDF_SHA, "strict frozen R38 reader")
    require(package_receipt_path.is_file(), f"R38 package receipt is absent: {package_receipt_path}")
    require(outer_manifest_path.is_file(), f"R38 outer manifest is absent: {outer_manifest_path}")
    require(not receipt_path.exists(), f"refusing to overwrite portable replay receipt: {receipt_path}")
    require(not stage.exists(), f"fresh portable replay stage already exists: {stage}")
    package_receipt = json.loads(package_receipt_path.read_text(encoding="utf-8"))
    require(package_receipt.get("schema") == "ag-ko-package-receipt-v5", "R38 package receipt schema drift")
    require(package_receipt.get("version") == VERSION and package_receipt.get("exact_doi") == EXACT_DOI, "R38 package receipt identity drift")
    require(package_receipt.get("concept_doi") == CONCEPT_DOI, "R38 package receipt concept DOI drift")
    require(package_receipt.get("result") == "PASS_R38_LOCAL_PACKAGE", "R38 package did not pass")
    require(package_receipt.get("public_artifact_count") == 4, "R38 package does not declare four public artifacts")
    file_rows = package_receipt.get("files", [])
    require(isinstance(file_rows, list) and len(file_rows) == 4 and all(isinstance(row, dict) for row in file_rows), "R38 package file-row shape drift")
    require([row.get("order") for row in file_rows] == [0, 1, 2, 3], "R38 package file order drift")
    require(len({row.get("name") for row in file_rows}) == 4, "duplicate R38 package file row")
    for row in file_rows:
        require(isinstance(row.get("bytes"), int) and row["bytes"] >= 0, f"invalid package byte count: {row.get('name')}")
        require(isinstance(row.get("sha256"), str) and re.fullmatch(r"[0-9A-F]{64}", row["sha256"]), f"invalid package digest: {row.get('name')}")
    rows = {row["name"]: row for row in file_rows}
    require(set(rows) == {"00_EGA_ko_CUMULATIVE_READER.pdf", "01_EGA_ko_EDITABLE_SOURCES.zip", "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip", "03_EGA_ko_SHA256_MANIFEST.txt"}, "R38 package public-artifact allowlist drift")
    source_row = rows[source_zip.name]
    evidence_row = rows[evidence_zip.name]
    require((rows[strict_reader.name]["bytes"], rows[strict_reader.name]["sha256"]) == (STRICT_PDF_BYTES, STRICT_PDF_SHA), "reader/package-receipt identity drift")
    require((source_zip.stat().st_size, sha_file(source_zip)) == (source_row["bytes"], source_row["sha256"]), "source ZIP/package-receipt identity drift")
    require((evidence_zip.stat().st_size, sha_file(evidence_zip)) == (evidence_row["bytes"], evidence_row["sha256"]), "evidence ZIP/package-receipt identity drift")
    manifest_rows: dict[str, tuple[int, str]] = {}
    manifest_lines = outer_manifest_path.read_text(encoding="utf-8").splitlines()
    require(manifest_lines and manifest_lines[0] == "filename\tbytes\tsha256", "outer manifest header drift")
    for line in manifest_lines[1:]:
        name, byte_text, digest = line.split("\t")
        require(name not in manifest_rows, f"duplicate outer-manifest row: {name}")
        manifest_rows[name] = (int(byte_text), digest)
    require(manifest_rows.get(source_zip.name) == (source_zip.stat().st_size, sha_file(source_zip)), "source ZIP/outer-manifest identity drift")
    require(manifest_rows.get(evidence_zip.name) == (evidence_zip.stat().st_size, sha_file(evidence_zip)), "evidence ZIP/outer-manifest identity drift")
    require(manifest_rows.get(strict_reader.name) == (STRICT_PDF_BYTES, STRICT_PDF_SHA), "reader/outer-manifest identity drift")
    require(set(manifest_rows) == {"00_EGA_ko_CUMULATIVE_READER.pdf", "01_EGA_ko_EDITABLE_SOURCES.zip", "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip"}, "outer manifest must list exactly the three non-self artifacts")
    require(rows[outer_manifest_path.name]["bytes"] == outer_manifest_path.stat().st_size and rows[outer_manifest_path.name]["sha256"] == sha_file(outer_manifest_path), "outer-manifest/package-receipt identity drift")
    require(package_receipt.get("public_artifact_allowlist") == [row["name"] for row in file_rows], "package allowlist/order drift")
    require(package_receipt.get("manifest_listed_artifacts") == 3, "package outer-manifest count drift")
    require(package_receipt.get("source_archive_A_B_byte_identical") is True and package_receipt.get("evidence_archive_A_B_byte_identical") is True, "package archive cycle equality failed")
    require(package_receipt.get("total_publication_bytes") == sum(row["bytes"] for row in file_rows), "package total-byte sum drift")
    require(package_receipt.get("privacy_credential_check", {}).get("result") == "PASS" and package_receipt.get("privacy_credential_check", {}).get("matches") == 0, "package privacy gate failed")
    require(package_receipt.get("outer_manifest_privacy_credential_check", {}).get("result") == "PASS" and package_receipt.get("outer_manifest_privacy_credential_check", {}).get("matches") == 0, "outer-manifest privacy gate failed")
    require(package_receipt.get("package_receipt_privacy_credential_check", {}).get("result") == "PASS_POST_SERIALIZATION_FAIL_CLOSED" and package_receipt.get("package_receipt_privacy_credential_check", {}).get("matches") == 0, "package-receipt privacy gate failed")
    require(privacy_match_count(package_receipt_path.read_bytes()) == 0, "serialized package receipt privacy/credential scan failed")
    require(package_receipt.get("metadata", {}).get("forbidden_umbrella_or_active_excluded_destination_mentions") == 0, "package metadata exclusion gate failed")
    require(package_receipt.get("metadata", {}).get("sole_contributor") == "AI typesetting & translation", "package contributor metadata drift")
    source_archive_preflight = verify_frozen_zip(source_zip)
    evidence_allowlist = frozen_evidence_allowlist(source_zip)
    cutoff_receipt = package_receipt.get("r38_evidence_release_cutoff", {})
    require(cutoff_receipt.get("allowlist") == {"path": EVIDENCE_ALLOWLIST_MEMBER, "bytes": EVIDENCE_ALLOWLIST_BYTES, "sha256": EVIDENCE_ALLOWLIST_SHA}, "package evidence-allowlist identity drift")
    require(cutoff_receipt.get("allowlisted_live_members") == len(evidence_allowlist), "package evidence-allowlist count drift")
    require(cutoff_receipt.get("allowlisted_live_member_names") == evidence_allowlist, "package evidence-allowlist member inventory drift")
    require(cutoff_receipt.get("generated_members") == ["ARTIFACT_SHA256.tsv"], "package generated-evidence classification drift")
    final_evidence_names = sorted(evidence_allowlist + ["ARTIFACT_SHA256.tsv"])
    require(cutoff_receipt.get("final_archive_file_members") == len(final_evidence_names), "package final-evidence count drift")
    require(cutoff_receipt.get("final_archive_member_names_sha256") == sha_bytes(("\n".join(final_evidence_names) + "\n").encode("utf-8")), "package final-evidence inventory hash drift")
    require(cutoff_receipt.get("live_inventory_exactly_classified") is True and cutoff_receipt.get("verification") == "PASS", "package evidence-cutoff classification failed")
    excluded_receipt = package_receipt.get("future_unit_evidence_excluded_from_r38_snapshot", [])
    require({row.get("path") for row in excluded_receipt if isinstance(row, dict)} == EXCLUDED_POST_R38_EVIDENCE and len(excluded_receipt) == len(EXCLUDED_POST_R38_EVIDENCE), "package post-R38 exclusion inventory drift")
    evidence_archive_preflight, preflight_controls = preflight_control_chain(evidence_zip, evidence_allowlist)
    for row, stats, label in ((source_row, source_archive_preflight, "source"), (evidence_row, evidence_archive_preflight, "evidence")):
        require((row.get("entries"), row.get("files"), row.get("directories"), row.get("uncompressed_file_bytes"), row.get("complete_inventory_sha256")) == (stats["entries"], stats["files"], stats["directories"], stats["uncompressed_file_bytes"], stats["complete_inventory_sha256"]), f"{label} ZIP/package inventory drift")
    verify_internal_manifest(source_zip, evidence_zip, strict_reader, package_receipt.get("internal_manifest", {}))
    require(len(PdfReader(str(strict_reader)).pages) == PAGES, "strict frozen R38 reader page-count drift")
    require(pypdf.__version__ in SUPPORTED_REPLAY_PYPDF_VERSIONS, f"unsupported replay pypdf version: {pypdf.__version__}")
    pdftotext_tool = approved_tool("pdftotext")
    pdftoppm_tool = approved_tool("pdftoppm")
    pwsh_tool = approved_tool("pwsh")
    pdftotext_version = subprocess.run([pdftotext_tool, "-v"], capture_output=True, timeout=30, check=True)
    pdftotext_version_text = (pdftotext_version.stderr or pdftotext_version.stdout).decode("utf-8", errors="replace").splitlines()[0].strip()
    require(pdftotext_version_text == EXPECTED_PDFTOTEXT_VERSION, f"pdftotext version drift: {pdftotext_version_text}")
    pdftoppm_version = subprocess.run([pdftoppm_tool, "-v"], capture_output=True, timeout=30, check=True)
    pdftoppm_version_text = (pdftoppm_version.stderr or pdftoppm_version.stdout).decode("utf-8", errors="replace").splitlines()[0].strip()
    require(pdftoppm_version_text == EXPECTED_PDFTOPPM_VERSION, f"pdftoppm version drift: {pdftoppm_version_text}")
    require(not staging_parent.is_symlink(), f"portable staging parent is a symlink/reparse path: {staging_parent}")
    staging_parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir()
    stage_cleanup = lambda: safe_remove_stage(stage, staging_parent)
    atexit.register(stage_cleanup)

    archive_verification = extract_and_verify_source(source_zip, stage)
    require(archive_verification["entries_verified"] == source_row["entries"], "source ZIP entry-count/package-receipt drift")
    require(archive_verification["files_verified"] == source_row["files"], "source ZIP file-count/package-receipt drift")
    require(archive_verification["complete_inventory_sha256"] == source_row["complete_inventory_sha256"], "source ZIP inventory/package-receipt drift")
    require(not (stage / "build" / "out").exists(), "frozen source archive contains a pre-existing build/out tree")
    build_script = stage / "build" / "BUILD.ps1"
    manifest_path = stage / "source" / "CUMULATIVE_INPUTS.json"
    target_path = stage / "source" / "c2s1.tex"
    assert_ident(build_script, BUILD_SCRIPT_BYTES, BUILD_SCRIPT_SHA, "frozen R38 build script")
    assert_ident(manifest_path, MANIFEST_BYTES, MANIFEST_SHA, "frozen R38 cumulative manifest")
    assert_ident(target_path, TARGET_BYTES, TARGET_SHA, "frozen R38 target")
    assert_ident(stage / "candidates" / "r38-c2s1-continuation.tex", CANDIDATE_BYTES, CANDIDATE_SHA, "frozen R38 candidate")
    assert_ident(stage / "candidates" / "validate_r38_candidate.py", VALIDATOR_BYTES, VALIDATOR_SHA, "frozen R38 candidate validator")
    assert_ident(stage / "scripts" / "append_r38_integration_records.py", INTEGRATION_HELPER_BYTES, INTEGRATION_HELPER_SHA, "frozen R38 integration helper")
    assert_ident(stage / "scripts" / "qa_r38_pdf.py", QA_SCRIPT_BYTES, QA_SCRIPT_SHA, "frozen R38 PDF-QA helper")
    assert_ident(stage / "scripts" / "validate_expert_review_log.py", EXPERT_VALIDATOR_BYTES, EXPERT_VALIDATOR_SHA, "frozen expert-review validator")
    assert_ident(stage / "scripts" / "prepare_r38_release.py", PREPARE_SCRIPT_BYTES, PREPARE_SCRIPT_SHA, "frozen R38 release-preparation helper")
    assert_ident(stage / "scripts" / "package_r38.py", PACKAGE_SCRIPT_BYTES, PACKAGE_SCRIPT_SHA, "frozen R38 package builder")
    require((stage / "scripts" / "portable_replay_r38.py").read_bytes() == Path(__file__).resolve().read_bytes(), "executing portable replay differs from frozen source member")
    script_text = build_script.read_text(encoding="utf-8")
    require(len(re.findall(r"for \(\$pass = 1; \$pass -le 4; \$pass\+\+\)", script_text)) == 1, "four-pass loop not proved in frozen BUILD.ps1")
    require(script_text.count("Invoke-XeLaTeXCycle -Cycle") == 2, "two-cycle control flow not proved in frozen BUILD.ps1")
    require("did not converge byte-exactly between passes 3 and 4" in script_text, "pass3/pass4 fail-closed gate missing")
    require("Global\\InterlanguageTeXSlotV1" in script_text, "global TeX mutex name missing from frozen BUILD.ps1")
    require("The two independent clean builds are not byte-identical." in script_text, "cycle-final equality fail-closed gate missing")

    allowed_environment = {
        "PATH", "PATHEXT", "SystemRoot", "WINDIR", "ComSpec", "TEMP", "TMP", "TMPDIR",
        "LOCALAPPDATA", "APPDATA", "PROGRAMDATA", "ProgramFiles", "ProgramFiles(x86)",
        "CommonProgramFiles", "CommonProgramFiles(x86)", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
        "PSModulePath", "LANG", "LC_ALL",
    }
    env = {name: value for name, value in os.environ.items() if name in allowed_environment}
    env["AGKO_REQUIRE_LIVE_COVERAGE"] = "0"
    invocation = [pwsh_tool, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(build_script)]
    result = subprocess.run(invocation, cwd=stage, env=env, capture_output=True, timeout=1800)
    if result.returncode != 0:
        raise RuntimeError(
            "portable build failed: "
            + result.stderr.decode("utf-8", errors="replace")[-2000:]
            + result.stdout.decode("utf-8", errors="replace")[-2000:]
        )
    stdout = result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    terminal_lines = [line for line in stdout.splitlines() if line.startswith("PASS ")]
    require(len(terminal_lines) == 1, f"unexpected portable terminal output: {stdout!r}")
    terminal = terminal_lines[0]
    terminal_bytes, terminal_sha, terminal_fields = parse_terminal(terminal)
    expected_terminal_fields = {
        "cycle_a_sha256", "cycle_b_sha256", "cycle_a_pass2_sha256", "cycle_b_pass2_sha256",
        "cycle_a_pass3_sha256", "cycle_b_pass3_sha256", "cycle_a_pass2_final_identical",
        "cycle_b_pass2_final_identical", "cycle_a_pass3_final_identical", "cycle_b_pass3_final_identical",
        "mutex", "timeout_ms", "abandoned_recovery",
    }
    require(set(terminal_fields) == expected_terminal_fields, "portable build terminal field set drift")
    require(all(re.fullmatch(r"[0-9A-F]{64}", terminal_fields[name]) for name in expected_terminal_fields if name.endswith("sha256")), "portable build terminal hash syntax drift")
    require(terminal_fields.get("timeout_ms") == "300000", "portable build mutex timeout drift")
    require(terminal_fields.get("abandoned_recovery") in {"true", "false"}, "portable build abandoned-recovery field drift")

    portable_reader = stage / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    portable_pdf = portable_reader.read_bytes()
    strict_pdf = strict_reader.read_bytes()
    portable_sha = sha_bytes(portable_pdf)
    portable_pages = len(PdfReader(str(portable_reader)).pages)
    require(portable_pages == PAGES, f"portable page count drift: {portable_pages}")
    require(terminal_bytes == len(portable_pdf) and terminal_sha == portable_sha, "terminal PDF identity does not match portable reader")
    require(terminal_fields.get("cycle_a_pass3_final_identical") == "true", "portable cycle A lacks pass3=pass4")
    require(terminal_fields.get("cycle_b_pass3_final_identical") == "true", "portable cycle B lacks pass3=pass4")
    require(terminal_fields.get("cycle_a_sha256") == terminal_fields.get("cycle_b_sha256") == portable_sha, "portable cycle finals are not identical to promoted reader")
    require(terminal_fields.get("cycle_a_pass3_sha256") == terminal_fields.get("cycle_a_sha256"), "portable cycle A pass3/final hash drift")
    require(terminal_fields.get("cycle_b_pass3_sha256") == terminal_fields.get("cycle_b_sha256"), "portable cycle B pass3/final hash drift")
    require(terminal_fields.get("mutex") == r"Global\InterlanguageTeXSlotV1", "portable build terminal mutex identity drift")

    with zipfile.ZipFile(evidence_zip, "r") as frozen_evidence:
        require(frozen_evidence.testzip() is None, "frozen evidence archive CRC verification failed")
        evidence_names = [info.filename for info in frozen_evidence.infolist()]
        require(len(evidence_names) == len(set(evidence_names)), "frozen evidence archive contains duplicate names")
        required_evidence = (
            set(CONTROL_IDENTITIES)
            | {"r38-extract-poppler.txt", "r38-extract-pypdf.txt"}
            | {f"render/r38-p{page:03d}.png" for page in RENDER_PAGES}
        )
        require(required_evidence.issubset(evidence_names), f"frozen evidence archive lacks replay references: {sorted(required_evidence - set(evidence_names))}")
        frozen_controls: dict[str, bytes] = {}
        for name, expected in CONTROL_IDENTITIES.items():
            data = frozen_evidence.read(name)
            require((len(data), sha_bytes(data)) == expected, f"frozen R38 control identity drift: {name}")
            frozen_controls[name] = data
        frozen_poppler = frozen_evidence.read("r38-extract-poppler.txt")
        frozen_pypdf = frozen_evidence.read("r38-extract-pypdf.txt")
        frozen_renders = {
            page: frozen_evidence.read(f"render/r38-p{page:03d}.png")
            for page in RENDER_PAGES
        }
    control_payloads = {name: json.loads(data) for name, data in frozen_controls.items()}
    for name, schema in CONTROL_SCHEMAS.items():
        require(control_payloads[name].get("schema") == schema, f"frozen R38 control schema drift: {name}")
    admission = control_payloads["controls/R38_TRANSLATION_ADMISSION.json"]
    integration = control_payloads["controls/R38_TRANSLATION_INTEGRATION.json"]
    inventory = control_payloads["controls/R38_CANONICAL_INVENTORY_REFRESH.json"]
    reconciliation = control_payloads["controls/R38_POST_CORRECTION_SOURCE_RECONCILIATION.json"]
    strict = control_payloads["controls/R38_STRICT_BUILD.json"]
    pdf_qa = control_payloads["controls/R38_PDF_QA.json"]
    require(
        (admission["candidate"]["bytes"], admission["candidate"]["sha256"])
        == (CANDIDATE_BYTES, CANDIDATE_SHA),
        "frozen R38 admission candidate binding drift",
    )
    require(
        str(integration.get("result", "")).startswith("PASS_R38_TRANSLATION_INTEGRATION"),
        "frozen R38 integration control did not pass",
    )
    require(
        str(inventory.get("result", "")).startswith("PASS_EXACT_23_DRIVER_INPUTS"),
        "frozen R38 inventory control did not pass",
    )
    source_span = reconciliation["source_span_replay"]
    unit = source_span["r38_unit_lines1607_1683"]
    prefix = source_span["admitted_prefix_lines1_1683"]
    require(
        (unit["bytes"], unit["characters"], unit["sha256"], unit["unchanged"])
        == (CANONICAL_UNIT_BYTES, CANONICAL_UNIT_CHARACTERS, CANONICAL_UNIT_SHA, True),
        "frozen R38 canonical-unit reconciliation drift",
    )
    require(
        (prefix["postimage_bytes"], prefix["postimage_sha256"])
        == (CANONICAL_PREFIX_BYTES, CANONICAL_PREFIX_SHA),
        "frozen R38 canonical-prefix reconciliation drift",
    )
    require(
        (
            reconciliation["manifest_reconciliation"]["postimage_bytes"],
            reconciliation["manifest_reconciliation"]["postimage_sha256"],
            reconciliation["manifest_reconciliation"]["historical_markers"],
        )
        == (MANIFEST_BYTES, MANIFEST_SHA, HISTORICAL_MARKERS),
        "frozen R38 manifest reconciliation drift",
    )
    require(
        (reconciliation["korean_target"]["bytes"], reconciliation["korean_target"]["sha256"])
        == (TARGET_BYTES, TARGET_SHA),
        "frozen R38 target reconciliation drift",
    )
    require(
        reconciliation.get("result")
        == "PASS_R38_POST_CORRECTION_SOURCE_RECONCILIATION_REBUILD_REQUIRED",
        "frozen R38 reconciliation control did not pass",
    )
    strict_manifest = strict["coverage"]["manifest"]
    strict_reconciliation = strict["coverage"]["post_correction_source_reconciliation"]
    require(
        (strict_manifest["bytes"], strict_manifest["sha256"], strict_manifest["historical_marker_sum"])
        == (MANIFEST_BYTES, MANIFEST_SHA, HISTORICAL_MARKERS),
        "frozen R38 strict-build manifest binding drift",
    )
    require(
        (strict_reconciliation["bytes"], strict_reconciliation["sha256"])
        == CONTROL_IDENTITIES["controls/R38_POST_CORRECTION_SOURCE_RECONCILIATION.json"],
        "frozen R38 strict-build reconciliation binding drift",
    )
    require(
        strict.get("status") == "PASS_R38_STRICT_TWO_CYCLE_FOUR_PASS_BUILD",
        "frozen R38 strict-build control did not pass",
    )
    require(
        (
            strict["reader"]["bytes"],
            strict["reader"]["sha256"],
            strict["reader"]["pages"],
        )
        == (STRICT_PDF_BYTES, STRICT_PDF_SHA, PAGES),
        "frozen R38 strict-build reader binding drift",
    )
    require(
        (pdf_qa.get("edition"), pdf_qa.get("status"))
        == (VERSION, "PASS"),
        "frozen R38 PDF-QA control did not pass",
    )
    markers = pdf_qa["historical_markers"]
    require(
        (
            markers["source_count"], markers["normalized_sequence_sha256"], markers["ranges"], markers["terminal_marker"]
        )
        == (
            HISTORICAL_MARKERS,
            "15805A340D0B9133B7787951F07930F9E7473C90ACDE78AE916525E9A3388F3E",
            ["I|5-8", "0I|11-78", "I|79-214", "II|5-24"],
            ["II", 24],
        ),
        "frozen R38 marker coverage drift",
    )
    input_validation = pdf_qa["source_bindings"]["input_validation"]
    require(input_validation["ordered_input_count"] == 17 and input_validation["canonical_driver_input_count"] == 23, "frozen R38 input-count drift")
    require(all(pdf_qa["navigation"]["required_r38_named_destinations"].values()), "frozen R38 named-destination gate failed")
    require(pdf_qa["font_unicode"]["all_type0_hangul_fonts_have_tounicode"] is True, "frozen R38 Hangul ToUnicode gate failed")
    require("line1685" in strict["incomplete_boundary"]["next_canonical_source"], "frozen R38 incomplete boundary drift")
    require(
        (
            pdf_qa["pdf"]["bytes"],
            pdf_qa["pdf"]["sha256"],
            pdf_qa["pdf"]["pages"],
        )
        == (STRICT_PDF_BYTES, STRICT_PDF_SHA, PAGES),
        "frozen R38 PDF-QA reader binding drift",
    )
    qa_prefix = pdf_qa["source_bindings"]["canonical_prefix"]
    qa_target = pdf_qa["source_bindings"]["korean_target"]
    require(
        (qa_prefix["lines"], qa_prefix["bytes"], qa_prefix["sha256"])
        == (CANONICAL_PREFIX_LINES, CANONICAL_PREFIX_BYTES, CANONICAL_PREFIX_SHA),
        "frozen R38 PDF-QA canonical-prefix binding drift",
    )
    require(
        (qa_target["bytes"], qa_target["sha256"]) == (TARGET_BYTES, TARGET_SHA),
        "frozen R38 PDF-QA target binding drift",
    )
    qa_extractions = {row["path"]: row for row in pdf_qa["extractions"]}
    expected_qa_extractions = {
        "evidence/r38-extract-poppler.txt": (POPPLER_BYTES, POPPLER_SHA),
        "evidence/r38-extract-pypdf.txt": (PYPDF_BYTES, PYPDF_SHA),
    }
    require(
        set(qa_extractions) == set(expected_qa_extractions),
        "frozen R38 PDF-QA extraction set drift",
    )
    for path, expected in expected_qa_extractions.items():
        row = qa_extractions[path]
        require(
            (row["bytes"], row["sha256"]) == expected,
            f"frozen R38 PDF-QA extraction binding drift: {path}",
        )
    qa_tools = pdf_qa["tools"]
    require(
        (
            qa_tools["pypdf_version"],
            qa_tools["pdftotext_version"],
            qa_tools["pdftoppm_version"],
        )
        == (
            FROZEN_QA_PYPDF_VERSION,
            EXPECTED_PDFTOTEXT_VERSION,
            EXPECTED_PDFTOPPM_VERSION,
        ),
        "frozen R38 PDF-QA tool-version binding drift",
    )
    qa_renders = {row["physical_page"]: row for row in pdf_qa["renders"]}
    require(set(qa_renders) == set(RENDER_PAGES), "frozen R38 PDF-QA render page set drift")
    for page, expected in RENDER_IDENTITIES.items():
        row = qa_renders[page]
        require(
            (row["bytes"], row["sha256"], row["dpi"]) == (*expected, RENDER_DPI),
            f"frozen R38 PDF-QA render binding drift on page {page}",
        )
    visual_findings = pdf_qa["visual_findings"]
    require(
        visual_findings["status"] == "PASS_NO_OBSERVED_DEFECTS"
        and visual_findings["selected_physical_pages"] == list(RENDER_PAGES)
        and visual_findings["dpi"] == RENDER_DPI
        and visual_findings["all_selected_source_pixels_presented_at_native_scale_via_lossless_tiles"] is True
        and visual_findings["confirmation_run_reused_exact_inspected_render_bytes_without_rerendering"] is True,
        "frozen R38 visual-inspection binding drift",
    )
    require((len(frozen_poppler), sha_bytes(frozen_poppler)) == (POPPLER_BYTES, POPPLER_SHA), "frozen R38 Poppler extraction identity drift")
    require((len(frozen_pypdf), sha_bytes(frozen_pypdf)) == (PYPDF_BYTES, PYPDF_SHA), "frozen R38 pypdf extraction identity drift")
    strict_poppler = poppler_extract(strict_reader)
    portable_poppler = poppler_extract(portable_reader)
    require(strict_poppler == portable_poppler == frozen_poppler, "portable Poppler extraction drift")
    strict_pypdf = pypdf_extract(strict_reader)
    portable_pypdf = pypdf_extract(portable_reader)
    require(strict_pypdf == portable_pypdf == frozen_pypdf, "portable pypdf extraction drift")

    render_rows = []
    for page in RENDER_PAGES:
        strict_generated = render(strict_reader, page, stage / f"strict-render-r38-p{page:03d}")
        portable_generated = render(portable_reader, page, stage / f"portable-render-r38-p{page:03d}")
        expected_bytes, expected_sha = RENDER_IDENTITIES[page]
        reference = frozen_renders[page]
        require((len(reference), sha_bytes(reference)) == (expected_bytes, expected_sha), f"frozen R38 render page {page} identity drift")
        require(strict_generated.read_bytes() == reference, f"strict/frozen render drift on page {page}")
        require(portable_generated.read_bytes() == reference, f"portable/frozen render drift on page {page}")
        render_rows.append(
            {
                "physical_page": page,
                "bytes": len(reference),
                "sha256": sha_bytes(reference),
                "dpi": RENDER_DPI,
                "frozen_evidence_entry": f"render/r38-p{page:03d}.png",
                "strict_frozen_byte_identical": True,
                "portable_frozen_byte_identical": True,
                "strict_portable_byte_identical": True,
            }
        )

    raw_log = stage / "build" / "out" / "main.log"
    require(raw_log.is_file(), "portable build log is absent")
    pdf_equal = strict_pdf == portable_pdf
    receipt = {
        "schema": "ag-ko-portable-replay-v4",
        "version": VERSION,
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "source_archive": {
            "name": source_zip.name,
            "bytes": source_zip.stat().st_size,
            "sha256": sha_file(source_zip),
            **archive_verification,
            "required_r38_replay_and_validation_members": sorted(REQUIRED_SOURCE_MEMBERS),
        },
        "evidence_archive": {
            "name": evidence_zip.name,
            "bytes": evidence_zip.stat().st_size,
            "sha256": sha_file(evidence_zip),
            "package_receipt_and_outer_manifest_identity": "PASS",
            "frozen_replay_members": [
                "r38-extract-poppler.txt",
                "r38-extract-pypdf.txt",
                *sorted(CONTROL_IDENTITIES),
                *[f"render/r38-p{page:03d}.png" for page in RENDER_PAGES],
            ],
            "r38_control_bindings": {
                name: {"bytes": len(data), "sha256": sha_bytes(data)}
                for name, data in frozen_controls.items()
            },
        },
        "frozen_source_bindings": {
            "cumulative_manifest": {
                "bytes": MANIFEST_BYTES,
                "sha256": MANIFEST_SHA,
                "coverage": "through2.2.1 / canonical lines1-1683 / 228 historical markers",
                "terminal_historical_marker": TERMINAL_HISTORICAL_MARKER,
                "next_canonical_line": NEXT_CANONICAL_LINE,
            },
            "canonical_r38_unit": {
                "lines": CANONICAL_UNIT_LINES,
                "bytes": CANONICAL_UNIT_BYTES,
                "characters": CANONICAL_UNIT_CHARACTERS,
                "sha256": CANONICAL_UNIT_SHA,
            },
            "canonical_admitted_prefix": {
                "lines": CANONICAL_PREFIX_LINES,
                "bytes": CANONICAL_PREFIX_BYTES,
                "sha256": CANONICAL_PREFIX_SHA,
                "binding_control": "controls/R38_POST_CORRECTION_SOURCE_RECONCILIATION.json",
            },
            "korean_candidate": {"bytes": CANDIDATE_BYTES, "sha256": CANDIDATE_SHA},
            "korean_target": {"bytes": TARGET_BYTES, "sha256": TARGET_SHA},
            "build_script": {"bytes": BUILD_SCRIPT_BYTES, "sha256": BUILD_SCRIPT_SHA},
        },
        "build": {
            "invocations": 1,
            "internal_xelatex_passes": 8,
            "mutex": "Global\\InterlanguageTeXSlotV1",
            "pass_count_proof": {
                "bytes": build_script.stat().st_size,
                "sha256": sha_file(build_script),
                "four_pass_loop_definition": 1,
                "cycle_invocations": 2,
                "declared_xelatex_invocations": 8,
                "failure_semantics": "each engine invocation throws on nonzero exit; pass3 must equal pass4 inside each cycle; cycle B final must equal cycle A final",
                "result": "PASS_EXACT_BUILD_SCRIPT_CONTROL_FLOW",
            },
            "terminal_completion_proof": {
                "stdout_terminal_record": terminal,
                "cycle_a_pass3_equals_pass4": True,
                "cycle_b_pass3_equals_pass4": True,
                "cycle_finals_byte_identical": True,
                "portable_reader": {"bytes": len(portable_pdf), "sha256": portable_sha},
                "result": "PASS",
            },
            "timeout_seconds": 1800,
            "timed_out": False,
            "live_authority_environment": "omitted; frozen target hashes, declared inputs and admission records enforced",
            "returncode": result.returncode,
            "stdout": ident_bytes(result.stdout),
            "stderr": ident_bytes(result.stderr),
            "log": {"bytes": raw_log.stat().st_size, "sha256": sha_file(raw_log)},
            "result": "PASS",
        },
        "strict_reader": {"bytes": len(strict_pdf), "sha256": sha_bytes(strict_pdf), "pages": PAGES},
        "portable_reader": {"bytes": len(portable_pdf), "sha256": portable_sha, "pages": portable_pages},
        "pdf_byte_identical": pdf_equal,
        "container_delta": {
            "observed": not pdf_equal,
            "strict": {"bytes": len(strict_pdf), "sha256": sha_bytes(strict_pdf)},
            "portable": {"bytes": len(portable_pdf), "sha256": portable_sha},
            "byte_identical": pdf_equal,
            "size_delta_portable_minus_strict": len(portable_pdf) - len(strict_pdf),
            "classification": "none; containers are byte-identical" if pdf_equal else "unadjudicated container-level delta only",
            "retention": "portable container identity is retained in this receipt; its staging bytes are deliberately deleted after all content-property replays pass",
            "inference_rule": "No content, correctness, completion or publication-status inference is made from a container difference.",
        },
        "extraction": {
            "poppler": {**ident_bytes(strict_poppler), "strict_portable_and_frozen_byte_identical": True, "hangul": len(re.findall("[가-힣]", strict_poppler.decode("utf-8"))), "replacement_characters": strict_poppler.decode("utf-8").count("\ufffd")},
            "pypdf": {**ident_bytes(strict_pypdf), "strict_portable_and_frozen_byte_identical": True, "hangul": len(re.findall("[가-힣]", strict_pypdf.decode("utf-8"))), "replacement_characters": strict_pypdf.decode("utf-8").count("\ufffd")},
        },
        "extraction_runtime": {
            "python_version": sys.version.split()[0],
            "pypdf_version": pypdf.__version__,
            "pypdf_version_frozen_qa": FROZEN_QA_PYPDF_VERSION,
            "pypdf_replay_versions_accepted": sorted(SUPPORTED_REPLAY_PYPDF_VERSIONS),
            "pdftotext_version": pdftotext_version_text,
            "pdftotext_version_required": EXPECTED_PDFTOTEXT_VERSION,
            "pdftoppm_version": pdftoppm_version_text,
            "pdftoppm_version_required": EXPECTED_PDFTOPPM_VERSION,
            "pypdf_page_join": "LF+FF+LF with one final LF; CRLF/CR normalized to LF",
            "poppler_options": ["-enc", "UTF-8", "-eol", "unix", "input.pdf", "-"],
        },
        "render_replay": {
            "comparisons": len(render_rows),
            "dpi": RENDER_DPI,
            "pages": render_rows,
            "result": "PASS_EXACT_STRICT_FROZEN_PORTABLE_RASTER_IDENTITY_6_OF_6",
        },
        "visual_qa": "Fresh strict and portable full-page raster bytes at 300 dpi on pages1,2,6,237,238,239 exactly reproduce the frozen already-inspected strict-reader evidence; no new full-document visual rereview is claimed.",
        "staging_cleanup": {
            "exact_target": "[PRIVATE_ROOT]/release-staging/r38-portable-replay",
            "scope": "only the fresh task-owned replay staging directory after all replay gates passed",
            "deleted": True,
        },
        "receipt_privacy_credential_check": {
            "scope": "The final serialized PORTABLE_BUILD_REPLAY.json is scanned before exclusive creation for concrete account/profile locators and credential patterns.",
            "matches": 0,
            "result": "PASS_PREWRITE_FAIL_CLOSED",
        },
        "result": "PASS_PORTABLE_BUILD_EXACT_TEXT_AND_SELECTED_RENDER_REPLAY",
    }
    receipt_payload = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    require(privacy_match_count(receipt_payload) == 0, "portable replay receipt privacy/credential gate failed")
    safe_remove_stage(stage, staging_parent)
    atexit.unregister(stage_cleanup)
    write_receipt_exclusive(receipt_path, receipt_payload)
    require(json.loads(receipt_path.read_text(encoding="utf-8")) == receipt, "written R38 portable receipt replay drift")
    print(
        "PASS_R38_PORTABLE_REPLAY|"
        f"portable_pdf={len(portable_pdf)}/{portable_sha}|"
        f"pdf_identical={str(pdf_equal).lower()}|"
        f"receipt={receipt_path.stat().st_size}/{sha_file(receipt_path)}"
    )


if __name__ == "__main__":
    main()
