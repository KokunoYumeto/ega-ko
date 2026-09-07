#!/usr/bin/env python3
"""Portable replay of the frozen R39 source/evidence package and cumulative reader."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from ctypes import wintypes
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from pypdf import PdfReader


VERSION = "2026-09-06-r39"
EXACT_DOI = "10.5281/zenodo.22416007"
CONCEPT_DOI = "10.5281/zenodo.21921513"
PACKAGE_RECEIPT_SCHEMA = "ag-ko-package-receipt-v7"
PACKAGE_RECEIPT_RESULT = "PASS_R39_LOCAL_PACKAGE"
PACKAGE_CREATED_AT = "2026-09-06T23:43:33+02:00"
PACKAGE_COVERAGE = {
    "terminal": "EGA II \u00a72.2.6 / canonical lines1-1780",
    "next": "line1782 / environment2.2.7",
    "historical_markers": 229,
    "no_completion_claim": True,
}
PACKAGE_CUTOFF = {
    "path": "scripts/r39_evidence_release_cutoff.txt",
    "entries": 533,
    "bytes": 12_223,
    "sha256": "6633FB04EEAF79BEC209A99610A58C6EA788598EC65C7656CFDD90B1C1CCE5C6",
    "jsonl_terminal_ids": {
        "decisions.jsonl": "AGKO-D191",
        "evidence.jsonl": "AGKO-E-R39-BUILD-QA-STATE-SEAL",
        "hard.jsonl": "AGKO-H166",
        "index/units.jsonl": "AGKO-EGA2-S1-R39-IDEAL-TERMINOLOGY-RESEAL-R1",
    },
}
PACKAGE_REQUIRED_CONTROLS = [
    "R39_AUTHORITY_COMMENT_RESEAL.json",
    "R39_BUILD_QA_STATE_SEAL.json",
    "R39_CANONICAL_PREFIX_REBASE.json",
    "R39_CURRENT_AUTHORITY_VALIDATOR.json",
    "R39_IDEAL_TERMINOLOGY_RESEAL.json",
    "R39_KOREAN_WORDING_RESEAL.json",
    "R39_PDF_QA.json",
    "R39_PDF_QA_PRE_TERMINOLOGY.json",
    "R39_STRICT_BUILD.json",
    "R39_STRICT_BUILD_PRE_TERMINOLOGY.json",
    "R39_TRANSLATION_ADMISSION.json",
    "R39_TRANSLATION_INTEGRATION.json",
    "R39_VISUAL_QA_PREPARATION.json",
    "R39_VISUAL_QA_PREPARATION_PRE_TERMINOLOGY.json",
    "R39_ZENODO_DRAFT_RESERVATION.json",
]
ASSETS = [
    "00_EGA_ko_CUMULATIVE_READER.pdf",
    "01_EGA_ko_EDITABLE_SOURCES.zip",
    "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip",
    "03_EGA_ko_SHA256_MANIFEST.txt",
]
STATE_SEAL_NAME = "controls/R39_BUILD_QA_STATE_SEAL.json"
STATE_SEAL_IDENTITY = {
    "bytes": 11_185,
    "sha256": "5924A67C251E7583F4973428D2DAD95BA6D56B0DAECAE3FE77B52A2275270DDD",
}
PACKAGE_STATE_SEAL_IDENTITY = {
    "path": "evidence/controls/R39_BUILD_QA_STATE_SEAL.json",
    **STATE_SEAL_IDENTITY,
    "result": "PASS_R39_BUILD_PDF_QA_STATE_SEAL",
    "transaction_id": "AGKO-R39-BUILD-QA-STATE-SEAL-F3B3D273A6C7E886F741",
    "fresh_preimage_sha256": "F3B3D273A6C7E886F741B49FC8456370EF9888E70A1A9A1CA181B2CD18B580AA",
}
STATE_SEAL_TRANSACTION = "AGKO-R39-BUILD-QA-STATE-SEAL-F3B3D273A6C7E886F741"
STATE_SEAL_FRESH_PREIMAGE = "F3B3D273A6C7E886F741B49FC8456370EF9888E70A1A9A1CA181B2CD18B580AA"
STATE_SEAL_SCRIPT_IDENTITY = {
    "path": "candidates/seal_r39_build_qa_state_exact.py",
    "bytes": 58_345,
    "sha256": "A55B2521C7BC6E55F110B3F498E03DA66E7085363A4AD9B7B2342FBCD84C3DF1",
}
TARGET_IDENTITY = {
    "path": "source/c2s1.tex",
    "bytes": 84_274,
    "sha256": "59D07958D5CE1765F4901202CE97B3AC6257F6DC6C0D114C37B314C6A6EB1943",
}
MANIFEST_IDENTITY = {
    "path": "source/CUMULATIVE_INPUTS.json",
    "bytes": 16_281,
    "sha256": "1F414A48D02837E9999205DC7E1B9468016A687605F5594DADAEDA4616EB21FB",
}
READER_IDENTITY = {
    "path": "00_EGA_ko_CUMULATIVE_READER.pdf",
    "bytes": 1_491_216,
    "sha256": "AB24AAA5A4FBEAC3528892EF998C93276BF6DD38E7520C5F18A316E3FBAEAA6F",
}
FROZEN_PYPDF_IDENTITY = {
    "bytes": 706_537,
    "sha256": "26644E0CF676F459F6E4443ABA02F1353FC110AB1E318D7555DADB7FBABE8FCE",
}
FROZEN_POPPLER_IDENTITY = {
    "bytes": 732_164,
    "sha256": "CBC8D6153E4833B9028721FB9DC2470C9450C07BC0596CBFED8B072FD444C14B",
}
PDF_CONTAINER_DELTA_CLASSIFICATION = "container_only_byte_delta"
MAX_PORTABLE_CONTAINER_SIZE_DELTA = 64
PACKAGE_READER = {**READER_IDENTITY, "pages": 240}
PACKAGE_SOURCE_MANIFEST = dict(MANIFEST_IDENTITY)
PACKAGE_STRICT_BUILD = {
    "path": "evidence/controls/R39_STRICT_BUILD.json",
    "bytes": 14_551,
    "sha256": "BD631DCAE7E8F9C485D9CEB14CE0DFA53CAE3F2BD5F0144ED9C3E0DEA7016BE0",
}
PACKAGE_PDF_QA = {
    "path": "evidence/controls/R39_PDF_QA.json",
    "bytes": 14_710,
    "sha256": "9FF6981048F0F8C632B5F44BEE9437B7B3DA7134CC35D1919B34912C6BAE707B",
}
PACKAGE_TRANSACTION = {
    "same_volume_sibling_stage": True,
    "staged_verification_passes": 2,
    "atomic_directory_rename": True,
    "exact_final_directory_is_idempotent_success": True,
    "differing_final_directory_fails_closed": True,
    "precommit_repository_sidecar_writes": 0,
}
PACKAGE_RECEIPT_KEYS = frozenset(
    {
        "schema",
        "version",
        "created_at",
        "exact_doi",
        "concept_doi",
        "coverage",
        "public_artifact_count",
        "files",
        "source_archive",
        "evidence_archive",
        "r39_evidence_release_cutoff",
        "required_controls",
        "state_seal",
        "state_seal_producer",
        "sealed_alias_postimages",
        "sealed_public_ledger_postimages",
        "sealed_unchanged_ledgers",
        "reader",
        "source_manifest",
        "strict_build",
        "pdf_qa",
        "transaction",
        "result",
    }
)
PACKAGE_CONTROL_IDENTITIES = {
    "evidence/controls/R39_STRICT_BUILD.json": {
        "path": "evidence/controls/R39_STRICT_BUILD.json",
        "bytes": 14_551,
        "sha256": "BD631DCAE7E8F9C485D9CEB14CE0DFA53CAE3F2BD5F0144ED9C3E0DEA7016BE0",
    },
    "evidence/controls/R39_VISUAL_QA_PREPARATION.json": {
        "path": "evidence/controls/R39_VISUAL_QA_PREPARATION.json",
        "bytes": 4_310,
        "sha256": "991D85DB3947110E98FCCF4A12E0570F78D27F092CD47114251BCB58B953412B",
    },
    "evidence/controls/R39_PDF_QA.json": {
        "path": "evidence/controls/R39_PDF_QA.json",
        "bytes": 14_710,
        "sha256": "9FF6981048F0F8C632B5F44BEE9437B7B3DA7134CC35D1919B34912C6BAE707B",
    },
    "evidence/BUILD_RECEIPT.json": {
        "path": "evidence/BUILD_RECEIPT.json",
        "bytes": 5_245,
        "sha256": "4C32901CEEDB6AC59A1924D743B53397D0F0C23E69793BB068B30F071D112928",
    },
    "evidence/controls/R39_ZENODO_DRAFT_RESERVATION.json": {
        "path": "evidence/controls/R39_ZENODO_DRAFT_RESERVATION.json",
        "bytes": 1_444,
        "sha256": "8799F847CCDCD35D93A401F125A830CB1759F8E2D16004E90A185979F398D7CA",
    },
}
STATE_SEAL_POSTIMAGE_IDENTITIES = {
    "private/authority.json": {"bytes": 29_325, "sha256": "F1E73460CFD8EC5795F47156DB1EFA44C6F05C03FAA92B11AFB4E651931B4F74"},
    "private/cursor.json": {"bytes": 30_359, "sha256": "34E43C0ACD3E0B79313F18AF318B2B0CED771CB8B60E2CD6D1BD5A5E44777A7E"},
    "private/decisions.jsonl": {"bytes": 713_178, "sha256": "5AC7368CD3D99A1DB48A3C521B4C49F3B3C49D680A13B14CB1792A83EECCD9E3"},
    "private/evidence.jsonl": {"bytes": 552_291, "sha256": "3800E144EAC1CF2A5B03DC6E5A17B0D2ADA7FC117597801A7BB21082E604DCDF"},
    "private/hard.jsonl": {"bytes": 306_986, "sha256": "E996D02CDC04810222A75B18967A6BF80C023B029EBBDFC24831A37FBE7C188D"},
    "private/state.json": {"bytes": 74_615, "sha256": "A7E036925FF09AAFBD6FCF98FFE19E3006538DA6621E65D85491497317127958"},
    "public/evidence/CURSOR.json": {"bytes": 30_959, "sha256": "5609DAC3405E8F5F0032BA3215AC0B49A9F5F1BA7601FA2080B0AFFBFDF0FBB5"},
    "public/evidence/DATACITE_RELATIONS.json": {"bytes": 31_258, "sha256": "D064BCB888C1E9050CF7C00A0F79F39070982A0BE0B3841513759B4DCBC8FB63"},
    "public/evidence/decisions.jsonl": {"bytes": 716_210, "sha256": "566270F97FB7D2317D24E551A99DFC5D9EF0105820DCC6C78300C974BB3D3626"},
    "public/evidence/evidence.jsonl": {"bytes": 553_405, "sha256": "0C47C199DE360C89CF3D4F012A8B141BC8A1254801B7888A0F266D003B39A3BB"},
    "public/evidence/hard.jsonl": {"bytes": 308_996, "sha256": "EF14FA5E89A9013B4853180EE3DFF279016D4D038283F8A2E66E8948FE2EA980"},
    "public/evidence/PROGRAM_AUTHORITY.json": {"bytes": 38_939, "sha256": "EDB58FF83671C3B8B538C527EE33D62646D6262C3F849B894B2AE198060D6992"},
    "public/evidence/PROGRAM_CURSOR.json": {"bytes": 31_152, "sha256": "5EA5870B376E76EFD9468B1B6C213FE2FEF4038FD05AC2B0835DEA4CD69FCF45"},
    "public/evidence/PROGRAM_STATE.json": {"bytes": 37_578, "sha256": "1ABD59EF44B8A76CF6FAFE2BEDAC893E3DF9F64317A14EE72AF0CCE29E9FD274"},
    "public/evidence/QA_STATE.json": {"bytes": 36_600, "sha256": "C97993C9816996603288D6BB5872DB37A70C7EFD6F0BFF7CC9289E2AFF5F1EE5"},
    "public/evidence/SOURCE_AUTHORITY.json": {"bytes": 31_086, "sha256": "58F08248A4E9BB21E8E1826F0A7BF52FD40703D233556F3ED3FECAFE17CDFCAB"},
    "public/evidence/STATE.json": {"bytes": 37_578, "sha256": "1ABD59EF44B8A76CF6FAFE2BEDAC893E3DF9F64317A14EE72AF0CCE29E9FD274"},
    "public/evidence/VISUAL_QA.json": {"bytes": 32_228, "sha256": "B9E9BE3DA39D2DD1E8089B882C62B19C31B8FE94E4B195A588E0C0E86833B758"},
}
STATE_SEAL_UNCHANGED_LEDGER_IDENTITIES = {
    "private/index/units.jsonl": {"bytes": 1_257_226, "sha256": "C82B56845193A8A20438F78F9924006C82AC84CDC50ABD57BF8F4408160D50E2"},
    "private/terms.jsonl": {"bytes": 263_512, "sha256": "756644F578732E9A41770CB6EE86F3BD6C39331AAA0A39F84A06FCA4A054D250"},
    "public/evidence/index/units.jsonl": {"bytes": 1_257_249, "sha256": "84DB52C484E5DBAF1500C7529F82944739F45D0A1FFBD060E7EE33A58F82095A"},
    "public/evidence/terms.jsonl": {"bytes": 263_512, "sha256": "756644F578732E9A41770CB6EE86F3BD6C39331AAA0A39F84A06FCA4A054D250"},
}
PACKAGE_ALIAS_NAMES = (
    "CURSOR.json",
    "DATACITE_RELATIONS.json",
    "PROGRAM_AUTHORITY.json",
    "PROGRAM_CURSOR.json",
    "PROGRAM_STATE.json",
    "QA_STATE.json",
    "SOURCE_AUTHORITY.json",
    "STATE.json",
    "VISUAL_QA.json",
)
PACKAGE_PUBLIC_LEDGER_NAMES = ("decisions.jsonl", "evidence.jsonl", "hard.jsonl")
STATE_SEAL_WORKING_RELEASE = {
    "version": VERSION,
    "record_id": 22_416_007,
    "exact_doi": EXACT_DOI,
    "exact_doi_url": "https://doi.org/10.5281/zenodo.22416007",
    "concept_doi": CONCEPT_DOI,
    "concept_doi_url": "https://doi.org/10.5281/zenodo.21921513",
    "status": "reserved_unpublished",
    "reservation": {
        "path": "evidence/controls/R39_ZENODO_DRAFT_RESERVATION.json",
        "bytes": 1_444,
        "sha256": "8799F847CCDCD35D93A401F125A830CB1759F8E2D16004E90A185979F398D7CA",
    },
    "latest_public_version_remains": "2026-09-05-r38",
    "latest_public_exact_doi": "10.5281/zenodo.22346664",
    "latest_public_record_id": 22_346_664,
    "latest_public_github_tag": "ega-ko-2026-09-05-r38",
}
STATE_SEAL_LATEST_PUBLIC_CHECKPOINT = {
    "version": "2026-09-05-r38",
    "status": "PASS_R38_PUBLIC_OPEN_DUAL_DESTINATION_AND_ANONYMOUS_BYTE_REPLAY",
    "record_id": 22_346_664,
    "exact_doi": "10.5281/zenodo.22346664",
    "github_tag": "ega-ko-2026-09-05-r38",
}
STATE_SEAL_TARGET = {
    **TARGET_IDENTITY,
    "characters": 58_678,
    "lf_lines": 1_809,
    "separator_line": 1_709,
    "candidate_target_lines": "1710-1809",
    "private_public_exact": True,
}
STATE_SEAL_READER = {
    "name": ASSETS[0],
    "path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf",
    "pages": 240,
    "bytes": READER_IDENTITY["bytes"],
    "sha256": READER_IDENTITY["sha256"],
}
STATE_SEAL_MANIFEST = {
    **MANIFEST_IDENTITY,
    "ordered_inputs": 17,
    "canonical_rows": 23,
    "complete": 16,
    "partial": 1,
    "not_translated": 6,
    "historical_markers": 229,
}
EXPECTED_RENDER_PAGES = (1, 2, 6, 25, 103, 104, 107, 109, 171, 237, 238, 239, 240)
MAX_PROCESS_OUTPUT = 64 * 1024 * 1024
MAX_ZIP_MEMBER_BYTES = 256 * 1024 * 1024
MAX_ZIP_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_RECEIPT_BYTES = 8 * 1024 * 1024

_PROFILE_PATH = re.compile(
    r"(?:[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\\/\r\n]+(?:[\\/]|$)|"
    r"/(?:home|Users)/[^/\r\n]+(?:/|$)|file://)",
    re.I,
)
_UNC_PATH = re.compile(r"(?:\\\\\?\\|\\\\)[^\\/\r\n]+(?:\\|/)", re.I)
_CREDENTIAL_VALUE = re.compile(
    r"(?:\bBearer\s+[A-Za-z0-9._~-]{12,}|"
    r"(?:access[_-]?token|api[_-]?key|client[_-]?secret|password)\s*[:=])",
    re.I,
)
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_FILE_ATTRIBUTE_REPARSE_POINT = 0x0400


def _reparse_component(path: Path) -> bool:
    """Return whether a lexical path component is a link or Windows reparse point."""

    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction) and is_junction():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)
    except FileNotFoundError:
        return False
    except OSError as exc:
        fail(f"cannot inspect a path component for reparse safety: {exc.__class__.__name__}")
    return False


def assert_no_reparse_lexical(path: Path, label: str) -> None:
    """Reject links/reparse points before any resolving operation follows them."""

    raw = Path(path)
    if any(part in (".", "..") for part in raw.parts):
        fail(f"{label} contains non-lexical dot components")
    absolute = Path(os.path.abspath(os.fspath(raw)))
    parts = absolute.parts
    component = Path(absolute.anchor) if absolute.anchor else Path()
    start = 1 if absolute.anchor else 0
    for index in range(start, len(parts)):
        component /= parts[index]
        if _reparse_component(component):
            fail(f"{label} contains a reparse component")


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def ident(path: Path, display: str) -> dict[str, Any]:
    if not path.is_file():
        fail(f"missing required file: {display}")
    return {"path": display, "bytes": path.stat().st_size, "sha256": sha_file(path)}


def strict_json_bytes(data: bytes, label: str) -> Any:
    def pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in rows:
            if key in result:
                fail(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        fail(f"non-finite JSON number in {label}: {value}")

    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"malformed JSON: {label}") from exc


def load(path: Path) -> dict[str, Any]:
    value = strict_json_bytes(path.read_bytes(), str(path))
    if not isinstance(value, dict):
        fail(f"JSON root is not an object: {path}")
    return value


def safe_name(name: str) -> None:
    pure = PurePosixPath(name)
    if (
        not name
        or pure.is_absolute()
        or "\\" in name
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        fail(f"unsafe archive member: {name!r}")
    for part in pure.parts:
        stem = part.rstrip(" .").split(".", 1)[0].upper()
        if (
            ":" in part
            or part != part.rstrip(" .")
            or stem in _WINDOWS_RESERVED
            or any(ord(character) < 32 for character in part)
        ):
            fail(f"Windows-unsafe archive member: {name!r}")


def verify_zip(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            fail(f"ZIP CRC failure at {bad}: {path.name}")
        names = archive.namelist()
        if names != sorted(names) or len(names) != len(set(names)):
            fail(f"ZIP ordering/uniqueness drift: {path.name}")
        normalized = [name.casefold() for name in names]
        if len(normalized) != len(set(normalized)):
            fail(f"ZIP contains Windows-normalized collisions: {path.name}")
        rows = []
        total = 0
        for info in archive.infolist():
            safe_name(info.filename)
            if info.is_dir() or info.flag_bits & 0x1:
                fail(f"ZIP member is a directory or encrypted: {info.filename}")
            if info.file_size < 0 or info.file_size > MAX_ZIP_MEMBER_BYTES:
                fail(f"ZIP member exceeds its bounded-read limit: {info.filename}")
            total += info.file_size
            if total > MAX_ZIP_TOTAL_BYTES:
                fail(f"ZIP exceeds its aggregate uncompressed bound: {path.name}")
            data = archive.read(info.filename)
            if len(data) != info.file_size:
                fail(f"ZIP member size drift: {info.filename}")
            rows.append({"path": info.filename, "bytes": len(data), "sha256": sha_bytes(data)})
    payload = (json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    return {"entries": len(rows), "uncompressed_bytes": sum(row["bytes"] for row in rows), "inventory_sha256": sha_bytes(payload)}


def extract_source(source_zip: Path, stage: Path) -> None:
    assert_no_reparse_lexical(stage, "archive extraction stage")
    with zipfile.ZipFile(source_zip, "r") as archive:
        normalized: set[str] = set()
        for info in archive.infolist():
            safe_name(info.filename)
            folded = info.filename.casefold()
            if folded in normalized:
                fail(f"source archive contains a Windows-normalized collision: {info.filename}")
            normalized.add(folded)
            if info.is_dir():
                continue
            if info.flag_bits & 0x1 or info.file_size < 0 or info.file_size > MAX_ZIP_MEMBER_BYTES:
                fail(f"source archive member is encrypted or oversized: {info.filename}")
            target = stage.joinpath(*PurePosixPath(info.filename).parts)
            assert_no_reparse_lexical(target, "archive extraction target")
            assert_no_reparse_lexical(stage, "archive extraction stage")
            resolved = target.resolve()
            stage_resolved = stage.resolve()
            try:
                resolved.relative_to(stage_resolved)
            except ValueError:
                fail(f"archive extraction escaped stage: {info.filename}")
            assert_no_reparse_lexical(target.parent, "archive extraction parent")
            target.parent.mkdir(parents=True, exist_ok=True)
            assert_no_reparse_lexical(target.parent, "archive extraction parent")
            assert_no_reparse_lexical(target, "archive extraction target")
            target.write_bytes(archive.read(info.filename))


def parse_outer_manifest(path: Path) -> dict[str, tuple[int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "filename\tbytes\tsha256":
        fail("outer manifest header drift")
    rows: dict[str, tuple[int, str]] = {}
    for line in lines[1:]:
        name, size, digest = line.split("\t")
        if name in rows or not re.fullmatch(r"[0-9A-F]{64}", digest):
            fail("outer manifest row drift")
        rows[name] = (int(size), digest)
    return rows


class _JobBasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _JobExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobBasicLimit),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _JobAccounting(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


class _WindowsKillJob:
    KILL_ON_CLOSE = 0x00002000
    EXTENDED_LIMIT_INFORMATION = 9
    BASIC_ACCOUNTING_INFORMATION = 1
    PROCESS_ACCESS = 0x0001 | 0x0100 | 0x0800 | 0x1000 | 0x00100000

    def __init__(self) -> None:
        if os.name != "nt":
            fail("Windows captured process-tree runner required")
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self.kernel.SetInformationJobObject.restype = wintypes.BOOL
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        self.kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel.TerminateJobObject.restype = wintypes.BOOL
        self.kernel.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.kernel.QueryInformationJobObject.restype = wintypes.BOOL
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.restype = wintypes.BOOL
        self.ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
        self.ntdll.NtResumeProcess.restype = ctypes.c_long
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            fail(f"CreateJobObjectW failed: {ctypes.get_last_error()}")
        limits = _JobExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = self.KILL_ON_CLOSE
        if not self.kernel.SetInformationJobObject(
            self.handle,
            self.EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            error = ctypes.get_last_error()
            self.close()
            fail(f"SetInformationJobObject failed: {error}")

    def open_process(self, process_id: int) -> wintypes.HANDLE:
        handle = self.kernel.OpenProcess(self.PROCESS_ACCESS, False, process_id)
        if not handle:
            fail(f"OpenProcess failed: {ctypes.get_last_error()}")
        return handle

    def assign_and_resume(self, process_id: int) -> None:
        process_handle = self.open_process(process_id)
        try:
            if not self.kernel.AssignProcessToJobObject(self.handle, process_handle):
                fail(f"AssignProcessToJobObject failed: {ctypes.get_last_error()}")
            status = self.ntdll.NtResumeProcess(process_handle)
            if status != 0:
                fail(f"NtResumeProcess failed with status 0x{status & 0xFFFFFFFF:08X}")
        finally:
            self.kernel.CloseHandle(process_handle)

    def active_processes(self) -> int:
        accounting = _JobAccounting()
        returned = wintypes.DWORD()
        if not self.kernel.QueryInformationJobObject(
            self.handle,
            self.BASIC_ACCOUNTING_INFORMATION,
            ctypes.byref(accounting),
            ctypes.sizeof(accounting),
            ctypes.byref(returned),
        ):
            fail(f"QueryInformationJobObject failed: {ctypes.get_last_error()}")
        return int(accounting.ActiveProcesses)

    def terminate(self) -> None:
        if self.handle and self.active_processes() and not self.kernel.TerminateJobObject(self.handle, 1):
            fail(f"TerminateJobObject failed: {ctypes.get_last_error()}")

    def close(self) -> None:
        if self.handle:
            handle, self.handle = self.handle, None
            if not self.kernel.CloseHandle(handle):
                fail(f"CloseHandle(job) failed: {ctypes.get_last_error()}")


def run_captured(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int,
) -> tuple[int, bytes, bytes]:
    if os.name != "nt" or not argv or any(not isinstance(item, str) or not item for item in argv):
        fail("invalid Windows captured process-tree invocation")
    executable = shutil.which(argv[0])
    if not executable:
        fail(f"required executable is absent: {argv[0]}")
    executable_path = Path(executable)
    assert_no_reparse_lexical(executable_path, "captured executable")
    command = [str(executable_path.resolve(strict=True)), *argv[1:]]
    assert_no_reparse_lexical(cwd, "captured working directory")
    flags = (
        getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    )
    job = _WindowsKillJob()
    process: subprocess.Popen[bytes] | None = None
    streams: list[threading.Thread] = []
    buffers = [bytearray(), bytearray()]
    total = 0
    overflow = threading.Event()
    guard = threading.Lock()

    def drain(stream: Any, destination: bytearray) -> None:
        nonlocal total
        try:
            while True:
                block = stream.read(64 * 1024)
                if not block:
                    return
                with guard:
                    total += len(block)
                    if total <= MAX_PROCESS_OUTPUT:
                        destination.extend(block)
                    else:
                        overflow.set()
        finally:
            stream.close()

    failure: str | None = None
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=flags,
            close_fds=True,
        )
        assert process.stdout is not None and process.stderr is not None
        streams = [
            threading.Thread(target=drain, args=(process.stdout, buffers[0]), daemon=True),
            threading.Thread(target=drain, args=(process.stderr, buffers[1]), daemon=True),
        ]
        for thread in streams:
            thread.start()
        try:
            job.assign_and_resume(process.pid)
        except Exception:
            # Assignment can fail before the suspended process is in the job.
            # Terminate the captured root explicitly so that this fail-closed
            # path cannot strand a suspended child outside kill-on-close.
            try:
                process.terminate()
                process.wait(timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    process.kill()
                    process.wait(timeout=30)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            try:
                job.terminate()
            except RuntimeError:
                pass
            raise

        deadline = time.monotonic() + timeout
        while job.active_processes() != 0:
            if overflow.is_set():
                failure = f"captured process tree exceeded {MAX_PROCESS_OUTPUT} output bytes"
                job.terminate()
                break
            if time.monotonic() >= deadline:
                failure = f"captured process tree timed out after {timeout}s"
                job.terminate()
                break
            time.sleep(0.05)
        cleanup_deadline = time.monotonic() + 30
        while job.active_processes() != 0 and time.monotonic() < cleanup_deadline:
            time.sleep(0.05)
        if job.active_processes() != 0:
            failure = (failure + "; " if failure else "") + "captured process tree did not terminate"
        return_code = process.wait(timeout=30)
        for thread in streams:
            thread.join(timeout=30)
        if any(thread.is_alive() for thread in streams):
            failure = (failure + "; " if failure else "") + "captured output drain did not terminate"
        if failure:
            fail(failure)
        if return_code != 0:
            fail(f"captured child process failed with exit {return_code}: {Path(command[0]).name}")
        return return_code, bytes(buffers[0]), bytes(buffers[1])
    finally:
        try:
            if process is not None and job.handle and job.active_processes() != 0:
                job.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=30)
                except (OSError, subprocess.TimeoutExpired):
                    try:
                        process.kill()
                        process.wait(timeout=30)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
        finally:
            job.close()


def clean_public_value(value: Any, roots: tuple[Path, ...], operation: str) -> None:
    sensitive_keys = ("token", "authorization", "password", "secret", "credential")
    forbidden_markers: set[str] = set()
    for root in roots:
        raw = os.fspath(root)
        lexical = os.path.abspath(raw)
        for marker in (raw, raw.replace("\\", "/"), lexical, lexical.replace("\\", "/")):
            if marker:
                forbidden_markers.add(marker.casefold())

    def visit(item: Any, key: str | None = None) -> None:
        if key is not None:
            folded = key.casefold()
            if any(word in folded for word in sensitive_keys) and not (
                key == "credentials_present" and item is False
            ):
                fail(f"{operation}: sensitive key is present")
        if isinstance(item, dict):
            for child_key, child in item.items():
                if not isinstance(child_key, str):
                    fail(f"{operation}: non-string JSON key")
                visit(child, child_key)
        elif isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, str):
            folded = item.casefold()
            if any(marker in folded for marker in forbidden_markers):
                fail(f"{operation}: task-local path leaked")
            if _PROFILE_PATH.search(item) or _UNC_PATH.search(item) or _CREDENTIAL_VALUE.search(item):
                fail(f"{operation}: private path or credential-like value leaked")
            if key == "path":
                safe_name(item)

    visit(value)


def parse_build_terminal(stdout: bytes, roots: tuple[Path, ...]) -> tuple[str, dict[str, Any]]:
    try:
        text = stdout.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError as exc:
        raise RuntimeError("portable build output is not strict UTF-8") from exc
    lines = [line for line in text.splitlines() if line.startswith("PASS ")]
    if len(lines) != 1:
        fail("portable build did not emit exactly one PASS terminal")
    terminal = lines[0]
    clean_public_value(terminal, roots, "portable build terminal")
    match = re.fullmatch(r"PASS ([0-9]+) bytes SHA-256 ([0-9A-F]{64}); (.+)", terminal)
    if match is None:
        fail("portable build PASS terminal grammar drift")
    fields: dict[str, str] = {}
    for token in match.group(3).split("; "):
        if "=" not in token:
            fail("portable build PASS field grammar drift")
        key, value = token.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or not value or key in fields:
            fail("portable build PASS field identity drift")
        fields[key] = value
    clean_public_value(fields, roots, "portable build terminal fields")
    if fields.get("mutex") != r"Global\InterlanguageTeXSlotV1" or fields.get("abandoned_recovery") not in ("true", "false"):
        fail("portable build mutex terminal field drift")
    return terminal, {
        "status": "PASS",
        "reader_bytes": int(match.group(1)),
        "reader_sha256": match.group(2),
        "fields": fields,
    }


def archive_member(archive: zipfile.ZipFile, name: str) -> bytes:
    infos = [info for info in archive.infolist() if info.filename == name]
    if len(infos) != 1:
        fail(f"required archive member is absent or duplicated: {name}")
    info = infos[0]
    safe_name(name)
    if info.is_dir() or info.flag_bits & 0x1 or info.file_size > MAX_ZIP_MEMBER_BYTES:
        fail(f"required archive member is unsafe: {name}")
    data = archive.read(info)
    if len(data) != info.file_size:
        fail(f"required archive member size drift: {name}")
    return data


def assert_identity(data: bytes, expected: dict[str, Any], label: str) -> None:
    if {"bytes": len(data), "sha256": sha_bytes(data)} != {
        "bytes": expected.get("bytes"),
        "sha256": expected.get("sha256"),
    }:
        fail(f"exact identity drift: {label}")


def validate_portable_reader_delta(portable_reader: Path, frozen_reader: Path, expected_pages: int) -> dict[str, Any]:
    """Accept only a bounded non-frozen R39 PDF container delta, before content replay."""

    frozen = ident(frozen_reader, READER_IDENTITY["path"])
    if frozen != READER_IDENTITY:
        fail("frozen R39 reader identity drift")
    portable = ident(portable_reader, "portable/reader/00_EGA_ko_CUMULATIVE_READER.pdf")
    size_delta = portable["bytes"] - frozen["bytes"]
    if portable["bytes"] <= 0 or portable["sha256"] == frozen["sha256"] or abs(size_delta) > MAX_PORTABLE_CONTAINER_SIZE_DELTA:
        fail("portable R39 reader container delta sanity drift")
    frozen_pdf = PdfReader(str(frozen_reader))
    portable_pdf = PdfReader(str(portable_reader))
    if frozen_pdf.metadata != portable_pdf.metadata:
        fail("portable R39 reader metadata drift")
    frozen_pages = len(frozen_pdf.pages)
    pages = len(portable_pdf.pages)
    if frozen_pages != expected_pages or pages != expected_pages:
        fail("portable reader page-count drift")
    return {
        "classification": PDF_CONTAINER_DELTA_CLASSIFICATION,
        "byte_identical": False,
        "size_delta_portable_minus_frozen": size_delta,
        "frozen": {**frozen, "pages": expected_pages},
        "portable": {**portable, "pages": pages},
        "metadata_byte_identical": True,
        "inference_rule": "No content, correctness, completion or publication-status inference is made from a container difference.",
    }


def validate_package_receipt_root(receipt: dict[str, Any], release: Path) -> None:
    """Validate the complete immutable v7 package receipt before replay work."""

    if set(receipt) != PACKAGE_RECEIPT_KEYS:
        fail("R39 package receipt top-level schema drift")
    if (
        receipt.get("schema") != PACKAGE_RECEIPT_SCHEMA
        or receipt.get("version") != VERSION
        or receipt.get("created_at") != PACKAGE_CREATED_AT
        or receipt.get("exact_doi") != EXACT_DOI
        or receipt.get("concept_doi") != CONCEPT_DOI
        or receipt.get("coverage") != PACKAGE_COVERAGE
        or receipt.get("public_artifact_count") != len(ASSETS)
        or receipt.get("result") != PACKAGE_RECEIPT_RESULT
    ):
        fail("R39 package receipt identity/status drift")
    files = receipt.get("files")
    if not isinstance(files, list) or len(files) != len(ASSETS):
        fail("R39 package asset inventory drift")
    for order, (expected_name, row) in enumerate(zip(ASSETS, files)):
        if (
            not isinstance(row, dict)
            or set(row) != {"order", "name", "bytes", "sha256"}
            or row.get("order") != order
            or row.get("name") != expected_name
            or not isinstance(row.get("bytes"), int)
            or row.get("bytes") < 0
            or not isinstance(row.get("sha256"), str)
            or not re.fullmatch(r"[0-9A-F]{64}", row["sha256"])
        ):
            fail(f"R39 package asset declaration drift: {expected_name}")
        path = release / expected_name
        assert_no_reparse_lexical(path, "R39 package asset")
        if path.is_symlink() or not path.is_file():
            fail(f"package asset is absent or a symlink: {expected_name}")
        if (path.stat().st_size, sha_file(path)) != (row["bytes"], row["sha256"]):
            fail(f"package asset identity drift: {expected_name}")
    for name, key in ((ASSETS[1], "source_archive"), (ASSETS[2], "evidence_archive")):
        archive_row = receipt.get(key)
        if (
            not isinstance(archive_row, dict)
            or set(archive_row) != {
                "path", "bytes", "sha256", "entries", "uncompressed_bytes",
                "inventory_sha256", "deterministic_second_build_byte_identical",
            }
            or archive_row.get("path") != name
            or archive_row.get("deterministic_second_build_byte_identical") is not True
            or not isinstance(archive_row.get("bytes"), int)
            or not isinstance(archive_row.get("sha256"), str)
            or not re.fullmatch(r"[0-9A-F]{64}", archive_row["sha256"])
        ):
            fail(f"R39 archive receipt identity drift: {name}")
    if receipt.get("r39_evidence_release_cutoff") != PACKAGE_CUTOFF:
        fail("R39 evidence cutoff receipt identity drift")
    if receipt.get("required_controls") != PACKAGE_REQUIRED_CONTROLS:
        fail("R39 package required-control inventory drift")
    if receipt.get("state_seal") != PACKAGE_STATE_SEAL_IDENTITY:
        fail("R39 package state-seal receipt identity drift")
    if receipt.get("state_seal_producer") != STATE_SEAL_SCRIPT_IDENTITY:
        fail("R39 package state-seal producer identity drift")
    if receipt.get("reader") != PACKAGE_READER:
        fail("R39 package reader identity drift")
    if receipt.get("source_manifest") != PACKAGE_SOURCE_MANIFEST:
        fail("R39 package source-manifest identity drift")
    if receipt.get("strict_build") != PACKAGE_STRICT_BUILD or receipt.get("pdf_qa") != PACKAGE_PDF_QA:
        fail("R39 package QA-control identity drift")
    if receipt.get("transaction") != PACKAGE_TRANSACTION:
        fail("R39 package transaction declaration drift")
    for key in ("sealed_alias_postimages", "sealed_public_ledger_postimages", "sealed_unchanged_ledgers"):
        if not isinstance(receipt.get(key), list):
            fail(f"R39 package sealed identity list malformed: {key}")


def validate_package_state_bindings(package: dict[str, Any], seal: dict[str, Any]) -> None:
    """Bind v7 sealed projections to the fixed state-seal bytes and identities."""

    if package.get("created_at") != seal.get("sealed_at"):
        fail("R39 package/state-seal timestamp binding drift")
    if package.get("coverage") != seal.get("coverage"):
        fail("R39 package/state-seal coverage binding drift")
    if package.get("state_seal") != {
        "path": "evidence/controls/R39_BUILD_QA_STATE_SEAL.json",
        **STATE_SEAL_IDENTITY,
        "result": seal.get("result"),
        "transaction_id": seal.get("transaction_id"),
        "fresh_preimage_sha256": seal.get("fresh_preimage_sha256"),
    }:
        fail("R39 package/state-seal root identity drift")
    if package.get("state_seal_producer") != STATE_SEAL_SCRIPT_IDENTITY:
        fail("R39 package/state-seal producer binding drift")

    rows = seal.get("postimages")
    if not isinstance(rows, list) or len(rows) != len(STATE_SEAL_POSTIMAGE_IDENTITIES):
        fail("R39 state-seal postimage inventory drift")
    postimages: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"} or not isinstance(row.get("path"), str):
            fail("R39 state-seal postimage row malformed")
        path = row["path"]
        if path in postimages:
            fail("R39 state-seal postimage duplicated")
        identity = {"bytes": row.get("bytes"), "sha256": row.get("sha256")}
        if identity != STATE_SEAL_POSTIMAGE_IDENTITIES.get(path):
            fail(f"R39 state-seal postimage identity drift: {path}")
        postimages[path] = identity
    if postimages != STATE_SEAL_POSTIMAGE_IDENTITIES:
        fail("R39 state-seal postimage set drift")

    alias_rows = [
        {"path": f"evidence/{name}", **STATE_SEAL_POSTIMAGE_IDENTITIES[f"public/evidence/{name}"]}
        for name in PACKAGE_ALIAS_NAMES
    ]
    if package.get("sealed_alias_postimages") != alias_rows:
        fail("R39 package alias postimage binding drift")
    ledger_rows = [
        {
            "path": f"evidence/{name}",
            **STATE_SEAL_POSTIMAGE_IDENTITIES[f"public/evidence/{name}"],
            "terminal_id": PACKAGE_CUTOFF["jsonl_terminal_ids"][name],
        }
        for name in PACKAGE_PUBLIC_LEDGER_NAMES
    ]
    if package.get("sealed_public_ledger_postimages") != ledger_rows:
        fail("R39 package public-ledger binding drift")
    unchanged_rows = [
        {"path": name, **STATE_SEAL_UNCHANGED_LEDGER_IDENTITIES[name]}
        for name in sorted(STATE_SEAL_UNCHANGED_LEDGER_IDENTITIES)
    ]
    if seal.get("unchanged_ledgers") != unchanged_rows or package.get("sealed_unchanged_ledgers") != unchanged_rows:
        fail("R39 unchanged-ledger binding drift")


def last_jsonl_id(data: bytes, expected: str, label: str) -> None:
    lines = data.splitlines()
    matches = 0
    last: str | None = None
    for raw in lines:
        value = strict_json_bytes(raw, label)
        if not isinstance(value, dict):
            fail(f"non-object JSONL row: {label}")
        row_id = value.get("id")
        if row_id == expected:
            matches += 1
        last = row_id if isinstance(row_id, str) else None
    if matches != 1 or last != expected or not data.endswith(b"\n"):
        fail(f"JSONL terminal binding drift: {label}")


def validate_state_seal(
    source_archive: zipfile.ZipFile,
    evidence_archive: zipfile.ZipFile,
    reader: Path,
    package: dict[str, Any],
    qa: dict[str, Any],
    strict: dict[str, Any],
) -> dict[str, Any]:
    seal_bytes = archive_member(evidence_archive, STATE_SEAL_NAME)
    assert_identity(seal_bytes, STATE_SEAL_IDENTITY, STATE_SEAL_NAME)
    seal = strict_json_bytes(seal_bytes, STATE_SEAL_NAME)
    if not isinstance(seal, dict):
        fail("R39 state seal is not an object")
    validate_package_state_bindings(package, seal)
    if (
        seal.get("schema") != "agko-r39-build-qa-state-seal-v1"
        or seal.get("id") != "AGKO-R39-BUILD-QA-STATE-SEAL"
        or seal.get("transaction_id") != STATE_SEAL_TRANSACTION
        or seal.get("precision") != "second"
        or seal.get("version") != VERSION
        or seal.get("fresh_preimage_sha256") != STATE_SEAL_FRESH_PREIMAGE
        or seal.get("result") != "PASS_R39_BUILD_PDF_QA_STATE_SEAL"
        or seal.get("sealed_at") != "2026-09-06T23:43:33+02:00"
    ):
        fail("R39 state-seal root identity drift")
    if seal.get("appended_records") != {
        "decisions.jsonl": "AGKO-D191",
        "evidence.jsonl": "AGKO-E-R39-BUILD-QA-STATE-SEAL",
        "hard.jsonl": "AGKO-H166",
    }:
        fail("R39 state-seal ledger terminal declarations drift")
    if seal.get("transaction") != {
        "staged_same_volume_replacements": True,
        "per_file_os_replace": True,
        "exact_preimage_backups": True,
        "reverse_order_rollback_on_failure": True,
        "idempotent_replay": True,
        "source_target_unit_and_terms_mutation": False,
    }:
        fail("R39 state-seal transaction declaration drift")
    if seal.get("public_projection") != {
        "relative_paths_only": True,
        "reserved_unpublished_r39_distinct_from_latest_public_r38": True,
        "historical_r39_target_transitions_preserved": True,
    }:
        fail("R39 state-seal public-projection declaration drift")
    if seal.get("working_release") != STATE_SEAL_WORKING_RELEASE:
        fail("R39 state-seal working-release binding drift")
    if seal.get("latest_public_checkpoint") != STATE_SEAL_LATEST_PUBLIC_CHECKPOINT:
        fail("R39 state-seal latest-public checkpoint drift")
    if seal.get("coverage") != PACKAGE_COVERAGE:
        fail("R39 state-seal coverage boundary drift")
    if seal.get("target") != STATE_SEAL_TARGET or seal.get("manifest") != STATE_SEAL_MANIFEST:
        fail("R39 state-seal source/target identity drift")
    expected_controls = {
        "strict_build": PACKAGE_CONTROL_IDENTITIES["evidence/controls/R39_STRICT_BUILD.json"],
        "visual_preparation": PACKAGE_CONTROL_IDENTITIES["evidence/controls/R39_VISUAL_QA_PREPARATION.json"],
        "pdf_qa": PACKAGE_CONTROL_IDENTITIES["evidence/controls/R39_PDF_QA.json"],
        "build_receipt": PACKAGE_CONTROL_IDENTITIES["evidence/BUILD_RECEIPT.json"],
        "zenodo_reservation": PACKAGE_CONTROL_IDENTITIES["evidence/controls/R39_ZENODO_DRAFT_RESERVATION.json"],
    }
    if seal.get("controls") != expected_controls:
        fail("R39 state-seal control identity map drift")
    gates = seal.get("gates")
    if gates != {
        "translation_admission": "PASS",
        "current_authority_validator": "PASS",
        "exact_mirror_integration": "PASS",
        "authority_comment_reseal": "PASS",
        "typed_ideal_terminology_reseal": "PASS",
        "strict_build": "PASS",
        "pdf_qa": "PASS",
        "release_evidence": "PASS",
        "package": "PENDING",
        "portable_replay": "PENDING",
        "github_publication_and_anonymous_readback": "PENDING",
        "zenodo_publication_and_anonymous_readback": "PENDING",
    }:
        fail("R39 state-seal gate matrix drift")
    if len(seal.get("postimages", [])) != 18 or len(seal.get("unchanged_ledgers", [])) != 4:
        fail("R39 state-seal postimage/unchanged inventory cardinality drift")

    assert_identity(reader.read_bytes(), READER_IDENTITY, "R39 reader")
    if seal.get("reader") != STATE_SEAL_READER:
        fail("R39 state-seal reader binding drift")
    manifest_bytes = archive_member(source_archive, "source/CUMULATIVE_INPUTS.json")
    assert_identity(manifest_bytes, MANIFEST_IDENTITY, "source/CUMULATIVE_INPUTS.json")
    if seal.get("manifest") != STATE_SEAL_MANIFEST:
        fail("R39 state-seal manifest binding drift")
    target_bytes = archive_member(source_archive, "source/c2s1.tex")
    assert_identity(target_bytes, TARGET_IDENTITY, "source/c2s1.tex")
    if seal.get("target") != STATE_SEAL_TARGET:
        fail("R39 state-seal target binding drift")
    assert_identity(
        archive_member(source_archive, "candidates/seal_r39_build_qa_state_exact.py"),
        STATE_SEAL_SCRIPT_IDENTITY,
        "state-seal producer",
    )

    required_controls = package.get("required_controls")
    if not isinstance(required_controls, list) or "R39_BUILD_QA_STATE_SEAL.json" not in required_controls:
        fail("R39 package receipt omits the state-seal control")
    control_map = {
        "strict_build": strict,
        "pdf_qa": qa,
    }
    for name, expected in seal.get("controls", {}).items():
        if not isinstance(expected, dict) or not isinstance(expected.get("path"), str):
            fail(f"R39 state-seal control binding malformed: {name}")
        member = expected["path"].removeprefix("evidence/")
        data = archive_member(evidence_archive, member)
        assert_identity(data, expected, f"state-seal control {name}")
        if name in control_map and strict_json_bytes(data, member) != control_map[name]:
            fail(f"state-seal loaded control disagreement: {name}")

    for row in seal["postimages"]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            fail("R39 state-seal postimage row malformed")
        prefix = "public/evidence/"
        if row["path"].startswith(prefix):
            member = row["path"][len(prefix):]
            assert_identity(archive_member(evidence_archive, member), row, member)
    for row in seal["unchanged_ledgers"]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            fail("R39 state-seal unchanged-ledger row malformed")
        prefix = "public/evidence/"
        if row["path"].startswith(prefix):
            member = row["path"][len(prefix):]
            assert_identity(archive_member(evidence_archive, member), row, member)

    last_jsonl_id(archive_member(evidence_archive, "decisions.jsonl"), "AGKO-D191", "decisions.jsonl")
    last_jsonl_id(archive_member(evidence_archive, "evidence.jsonl"), "AGKO-E-R39-BUILD-QA-STATE-SEAL", "evidence.jsonl")
    last_jsonl_id(archive_member(evidence_archive, "hard.jsonl"), "AGKO-H166", "hard.jsonl")
    last_jsonl_id(
        archive_member(evidence_archive, "index/units.jsonl"),
        "AGKO-EGA2-S1-R39-IDEAL-TERMINOLOGY-RESEAL-R1",
        "index/units.jsonl",
    )
    if tuple(int(row.get("physical_page", 0)) for row in qa.get("renders", [])) != EXPECTED_RENDER_PAGES:
        fail("R39 exact render-page sequence drift")
    return seal


def atomic_preserve_receipt(path: Path, fresh: dict[str, Any], existing: bytes | None) -> tuple[bytes, str]:
    clean_public_value(fresh, (), "portable replay receipt")
    payload = (json.dumps(fresh, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(payload) > MAX_RECEIPT_BYTES:
        fail("portable replay receipt exceeds its byte bound")
    assert_no_reparse_lexical(path.parent, "portable replay receipt parent")
    assert_no_reparse_lexical(path, "portable replay receipt")
    if existing is not None:
        if existing != payload:
            fail("existing portable replay receipt differs; refusing overwrite")
        return existing, "UNCHANGED_EXACT"
    if path.exists() or path.is_symlink():
        fail("portable replay receipt appeared concurrently")
    path.parent.mkdir(parents=True, exist_ok=True)
    assert_no_reparse_lexical(path.parent, "portable replay receipt parent")
    assert_no_reparse_lexical(path, "portable replay receipt")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if temporary.read_bytes() != payload:
            fail("staged portable replay receipt differs")
        os.link(temporary, path, follow_symlinks=False)
        temporary.unlink()
    finally:
        temporary.unlink(missing_ok=True)
    if path.read_bytes() != payload:
        fail("installed portable replay receipt differs")
    return payload, "ATOMIC_CREATE_PASS"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    args = parser.parse_args()
    assert_no_reparse_lexical(args.repo, "repository root")
    assert_no_reparse_lexical(args.private_root, "private root")
    repo = args.repo.resolve(strict=True)
    private_root = args.private_root.resolve(strict=True)
    assert_no_reparse_lexical(repo, "repository root")
    assert_no_reparse_lexical(private_root, "private root")
    release = repo / "release" / VERSION
    assert_no_reparse_lexical(release, "R39 release directory")
    receipt_path = release / "PACKAGE_RECEIPT.json"
    output = release / "PORTABLE_REPLAY_RECEIPT.json"
    assert_no_reparse_lexical(receipt_path, "R39 package receipt")
    assert_no_reparse_lexical(output, "portable replay receipt")
    existing_receipt: bytes | None = None
    prior: dict[str, Any] | None = None
    verified_at = datetime.now().astimezone().isoformat(timespec="seconds")
    if output.exists() or output.is_symlink():
        if output.is_symlink() or not output.is_file() or output.stat().st_size > MAX_RECEIPT_BYTES:
            fail("existing portable replay receipt is unsafe or oversized")
        existing_receipt = output.read_bytes()
        prior_value = strict_json_bytes(existing_receipt, "existing portable replay receipt")
        if (
            not isinstance(prior_value, dict)
            or prior_value.get("schema") != "ag-ko-portable-replay-receipt-v5"
            or prior_value.get("version") != VERSION
            or prior_value.get("exact_doi") != EXACT_DOI
            or prior_value.get("concept_doi") != CONCEPT_DOI
            or prior_value.get("result") != "PASS_R39_PORTABLE_REPLAY"
            or not isinstance(prior_value.get("verified_at"), str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", prior_value["verified_at"])
        ):
            fail("existing portable replay receipt identity/status drift")
        prior = prior_value
        clean_public_value(prior, (repo, private_root, release), "existing portable replay receipt")
        verified_at = prior["verified_at"]
    if receipt_path.is_symlink() or not receipt_path.is_file() or receipt_path.stat().st_size > MAX_RECEIPT_BYTES:
        fail("R39 package receipt is unsafe or oversized")
    receipt = load(receipt_path)
    validate_package_receipt_root(receipt, release)
    if prior is not None and prior.get("package_receipt") != ident(receipt_path, f"release/{VERSION}/PACKAGE_RECEIPT.json"):
        fail("existing portable replay receipt package binding drift")
    if prior is not None and prior.get("state_seal") != {
        "path": f"{ASSETS[2]}!/{STATE_SEAL_NAME}",
        **STATE_SEAL_IDENTITY,
        "transaction_id": STATE_SEAL_TRANSACTION,
        "fresh_preimage_sha256": STATE_SEAL_FRESH_PREIMAGE,
        "result": "PASS_R39_BUILD_PDF_QA_STATE_SEAL",
    }:
        fail("existing portable replay receipt state-seal binding drift")
    file_rows = receipt["files"]
    manifest_rows = parse_outer_manifest(release / ASSETS[3])
    if set(manifest_rows) != set(ASSETS[:3]):
        fail("outer manifest asset set drift")
    for name in ASSETS[:3]:
        if manifest_rows[name] != ((release / name).stat().st_size, sha_file(release / name)):
            fail(f"outer manifest identity drift: {name}")

    source_zip = release / ASSETS[1]
    evidence_zip = release / ASSETS[2]
    source_verification = verify_zip(source_zip)
    evidence_verification = verify_zip(evidence_zip)
    for name, key, verification in (
        (ASSETS[1], "source_archive", source_verification),
        (ASSETS[2], "evidence_archive", evidence_verification),
    ):
        expected_archive = receipt[key]
        actual_archive = {
            "path": name,
            "bytes": (release / name).stat().st_size,
            "sha256": sha_file(release / name),
            **verification,
            "deterministic_second_build_byte_identical": True,
        }
        if expected_archive != actual_archive:
            fail(f"archive verification/package receipt drift: {name}")

    with zipfile.ZipFile(source_zip, "r") as source_archive:
        executing_script = Path(__file__)
        assert_no_reparse_lexical(executing_script, "executing portable replay")
        if source_archive.read("scripts/portable_replay_r39.py") != executing_script.resolve(strict=True).read_bytes():
            fail("executing portable replay differs from frozen source member")
        manifest = strict_json_bytes(
            archive_member(source_archive, "source/CUMULATIVE_INPUTS.json"),
            "source/CUMULATIVE_INPUTS.json",
        )
        if not isinstance(manifest, dict) or manifest.get("scope", {}).get("historical_source_pages") != 229 or "lines1-1780" not in str(manifest.get("scope", {}).get("terminal_coverage", "")):
            fail("frozen cumulative manifest coverage drift")
        try:
            allowlist = archive_member(source_archive, "scripts/r39_evidence_release_cutoff.txt").decode("utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise RuntimeError("frozen R39 evidence allowlist is not strict UTF-8") from exc
        if (
            not allowlist
            or any(not name for name in allowlist)
            or allowlist != sorted(allowlist)
            or len(allowlist) != len(set(allowlist))
            or STATE_SEAL_NAME not in allowlist
        ):
            fail("frozen R39 evidence allowlist drift")
    with zipfile.ZipFile(evidence_zip, "r") as evidence_archive:
        evidence_names = set(evidence_archive.namelist())
        if evidence_names != set(allowlist) | {"ARTIFACT_SHA256.tsv"}:
            fail("evidence ZIP differs from frozen allowlist")
        qa = strict_json_bytes(archive_member(evidence_archive, "controls/R39_PDF_QA.json"), "controls/R39_PDF_QA.json")
        strict = strict_json_bytes(archive_member(evidence_archive, "controls/R39_STRICT_BUILD.json"), "controls/R39_STRICT_BUILD.json")
        if not isinstance(qa, dict) or not isinstance(strict, dict) or qa.get("status") != "PASS" or strict.get("status") != "PASS_R39_STRICT_TWO_CYCLE_FOUR_PASS_BUILD":
            fail("frozen R39 QA/strict control did not pass")
        try:
            artifact_manifest = archive_member(evidence_archive, "ARTIFACT_SHA256.tsv").decode("utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise RuntimeError("internal evidence manifest is not strict UTF-8") from exc
        if not artifact_manifest or artifact_manifest[0] != "path\tbytes\tsha256":
            fail("internal evidence manifest header drift")
        declared: dict[str, tuple[int, str]] = {}
        for line in artifact_manifest[1:]:
            fields = line.split("\t")
            if len(fields) != 3:
                fail("internal evidence manifest row grammar drift")
            name, size, digest = fields
            safe_name(name)
            if name in declared or not re.fullmatch(r"0|[1-9][0-9]*", size) or not re.fullmatch(r"[0-9A-F]{64}", digest):
                fail("internal evidence manifest row identity drift")
            declared[name] = (int(size), digest)
        if set(declared) != set(allowlist):
            fail("internal evidence manifest set drift")
        for name, (size, digest) in declared.items():
            data = archive_member(evidence_archive, name)
            if (len(data), sha_bytes(data)) != (size, digest):
                fail(f"internal evidence member drift: {name}")

    frozen_reader = release / ASSETS[0]
    with zipfile.ZipFile(source_zip, "r") as source_archive, zipfile.ZipFile(evidence_zip, "r") as evidence_archive:
        seal = validate_state_seal(source_archive, evidence_archive, frozen_reader, receipt, qa, strict)

    staging_parent = private_root / "release-staging"
    assert_no_reparse_lexical(staging_parent, "portable replay staging parent")
    staging_parent.mkdir(parents=True, exist_ok=True)
    assert_no_reparse_lexical(staging_parent, "portable replay staging parent")
    staging_parent = staging_parent.resolve(strict=True)
    assert_no_reparse_lexical(staging_parent, "portable replay staging parent")
    try:
        staging_parent.relative_to(private_root)
    except ValueError:
        fail("portable replay staging parent escaped private root")
    terminal: str
    terminal_fields: dict[str, Any]
    with tempfile.TemporaryDirectory(prefix="r39-portable-", dir=str(staging_parent)) as temp:
        stage_raw = Path(temp)
        assert_no_reparse_lexical(stage_raw, "portable replay stage")
        stage = stage_raw.resolve(strict=True)
        assert_no_reparse_lexical(stage, "portable replay stage")
        extract_source(source_zip, stage)
        if (stage / "build" / "out").exists():
            fail("source archive contains a pre-existing build/out tree")
        build_script = stage / "build" / "BUILD.ps1"
        script_text = build_script.read_text(encoding="utf-8")
        if "Global\\InterlanguageTeXSlotV1" not in script_text or script_text.count("Invoke-XeLaTeXCycle -Cycle") != 2:
            fail("frozen build script mutex/two-cycle gate drift")
        env = os.environ.copy()
        env["AGKO_REQUIRE_LIVE_COVERAGE"] = "0"
        env.pop("AGKO_CANONICAL_ROOT", None)
        env.pop("AGKO_PRIVATE_ROOT", None)
        _, build_stdout, _ = run_captured(
            ["pwsh", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(build_script)],
            cwd=stage,
            env=env,
            timeout=1800,
        )
        terminal, terminal_fields = parse_build_terminal(build_stdout, (repo, private_root, stage))
        portable_reader = stage / "reader" / ASSETS[0]
        container_delta = validate_portable_reader_delta(
            portable_reader,
            frozen_reader,
            int(strict["reader"]["pages"]),
        )

        portable_page_text = [(page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n") for page in PdfReader(str(portable_reader)).pages]
        portable_pypdf = ("\n\f\n".join(portable_page_text) + "\n").encode("utf-8")
        portable_pypdf_identity = {"bytes": len(portable_pypdf), "sha256": sha_bytes(portable_pypdf)}
        portable_poppler_path = stage / "portable-poppler.txt"
        tool_env = os.environ.copy()
        run_captured(
            ["pdftotext", "-enc", "UTF-8", "-eol", "unix", str(portable_reader), str(portable_poppler_path)],
            cwd=stage,
            env=tool_env,
            timeout=180,
        )
        portable_poppler = portable_poppler_path.read_bytes()
        portable_poppler_identity = {"bytes": len(portable_poppler), "sha256": sha_bytes(portable_poppler)}
        with zipfile.ZipFile(evidence_zip, "r") as evidence_archive:
            frozen_pypdf = archive_member(evidence_archive, "r39-extract-pypdf.txt")
            assert_identity(frozen_pypdf, FROZEN_PYPDF_IDENTITY, "frozen pypdf extraction")
            if portable_pypdf != frozen_pypdf:
                fail("portable pypdf extraction differs")
            frozen_poppler = archive_member(evidence_archive, "r39-extract-poppler.txt")
            assert_identity(frozen_poppler, FROZEN_POPPLER_IDENTITY, "frozen Poppler extraction")
            if portable_poppler != frozen_poppler:
                fail("portable Poppler extraction differs")
            container_delta["extractions"] = {
                "pypdf": {
                    **portable_pypdf_identity,
                    "frozen": dict(FROZEN_PYPDF_IDENTITY),
                    "byte_identical_to_frozen": True,
                },
                "poppler": {
                    **portable_poppler_identity,
                    "frozen": dict(FROZEN_POPPLER_IDENTITY),
                    "byte_identical_to_frozen": True,
                },
            }
            render_rows = qa.get("renders", [])
            render_replays: list[dict[str, Any]] = []
            for row in render_rows:
                page = int(row["physical_page"])
                prefix = stage / f"portable-r39-p{page:03d}"
                rendered = prefix.with_suffix(".png")
                run_captured(
                    ["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-r", "300", "-png", str(portable_reader), str(prefix)],
                    cwd=stage,
                    env=tool_env,
                    timeout=180,
                )
                frozen = archive_member(evidence_archive, f"render/r39-p{page:03d}.png")
                if rendered.read_bytes() != frozen:
                    fail(f"portable render differs on page {page}")
                render_replays.append({"physical_page": page, "bytes": len(frozen), "sha256": sha_bytes(frozen), "byte_identical": True})
            container_delta["render_pages"] = [row["physical_page"] for row in render_replays]
            container_delta["renders_byte_identical_to_frozen"] = True

    final_assets = [ident(release / name, f"release/{VERSION}/{name}") for name in ASSETS]
    for package_row, final_row in zip(file_rows, final_assets):
        if {key: final_row[key] for key in ("bytes", "sha256")} != {
            "bytes": package_row["bytes"],
            "sha256": package_row["sha256"],
        }:
            fail(f"package asset changed during portable replay: {package_row['name']}")
    receipt_out: dict[str, Any] = {
        "schema": "ag-ko-portable-replay-receipt-v5",
        "version": VERSION,
        "verified_at": verified_at,
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "package_receipt": ident(receipt_path, f"release/{VERSION}/PACKAGE_RECEIPT.json"),
        "assets": final_assets,
        "state_seal": {
            "path": f"{ASSETS[2]}!/{STATE_SEAL_NAME}",
            **STATE_SEAL_IDENTITY,
            "transaction_id": seal["transaction_id"],
            "fresh_preimage_sha256": seal["fresh_preimage_sha256"],
            "result": seal["result"],
        },
        "source_archive_verification": source_verification,
        "evidence_archive_verification": evidence_verification,
        "process_tree": {
            "runner": "windows_job_object",
            "root_created_suspended": True,
            "assigned_before_resume": True,
            "kill_on_close": True,
            "complete_tree_wait": True,
            "fail_closed_cleanup": True,
            "combined_output_byte_limit": MAX_PROCESS_OUTPUT,
        },
        "portable_build": {
            "reader": {**ident(release / ASSETS[0], ASSETS[0]), "pages": strict["reader"]["pages"]},
            "portable_reader": container_delta["portable"],
            "container_delta": container_delta,
            "two_clean_four_pass_cycles": True,
            "pass3_equals_pass4_each_cycle": True,
            "two_cycle_finals_byte_identical": True,
            "mutex": r"Global\InterlanguageTeXSlotV1",
            "terminal": terminal,
            "terminal_fields": terminal_fields,
        },
        "extraction_replay": {
            # The generated extraction identities are intentionally dynamic:
            # staging paths can perturb PDF/container bytes, while the content
            # gate below requires exact equality with the frozen evidence.
            "pypdf": dict(container_delta["extractions"]["pypdf"]),
            "poppler": dict(container_delta["extractions"]["poppler"]),
            "pypdf_byte_identical": True,
            "poppler_byte_identical": True,
        },
        "render_replay": render_replays,
        "result": "PASS_R39_PORTABLE_REPLAY",
    }
    clean_public_value(receipt_out, (repo, private_root, staging_parent), "portable replay receipt")
    payload, disposition = atomic_preserve_receipt(output, receipt_out, existing_receipt)
    print(f"PASS_R39_PORTABLE_REPLAY|{len(payload)}|{sha_bytes(payload)}|receipt={disposition}|reader={receipt_out['portable_build']['reader']['bytes']}/{receipt_out['portable_build']['reader']['sha256']}")


if __name__ == "__main__":
    main()
