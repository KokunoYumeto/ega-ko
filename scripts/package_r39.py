#!/usr/bin/env python3
"""Build and independently replay the deterministic four-asset R39 bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


VERSION = "2026-09-06-r39"
EXACT_DOI = "10.5281/zenodo.22416007"
CONCEPT_DOI = "10.5281/zenodo.21921513"
TARGET_SHA = "59D07958D5CE1765F4901202CE97B3AC6257F6DC6C0D114C37B314C6A6EB1943"
TARGET_IDENTITY = {
    "path": "source/c2s1.tex",
    "bytes": 84_274,
    "sha256": TARGET_SHA,
}
WORKING_COVERAGE = (
    "EGA 0_I and EGA I complete; EGA II programme/table of contents complete; "
    "EGA II main text translated contiguously through §2.2.6 / canonical lines1-1780. "
    "EGA II and the full EGA corpus remain incomplete."
)
READER_IDENTITY = {
    "name": "00_EGA_ko_CUMULATIVE_READER.pdf",
    "path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf",
    "pages": 240,
    "bytes": 1_491_216,
    "sha256": "AB24AAA5A4FBEAC3528892EF998C93276BF6DD38E7520C5F18A316E3FBAEAA6F",
}
MANIFEST_IDENTITY = {
    "path": "source/CUMULATIVE_INPUTS.json",
    "bytes": 16_281,
    "sha256": "1F414A48D02837E9999205DC7E1B9468016A687605F5594DADAEDA4616EB21FB",
}
STATE_SEAL_IDENTITY = {
    "path": "evidence/controls/R39_BUILD_QA_STATE_SEAL.json",
    "bytes": 11_185,
    "sha256": "5924A67C251E7583F4973428D2DAD95BA6D56B0DAECAE3FE77B52A2275270DDD",
}
STATE_SEAL_PRODUCER_IDENTITY = {
    "path": "candidates/seal_r39_build_qa_state_exact.py",
    "bytes": 58_345,
    "sha256": "A55B2521C7BC6E55F110B3F498E03DA66E7085363A4AD9B7B2342FBCD84C3DF1",
}
ALIAS_POSTIMAGES = {
    "CURSOR.json": {"bytes": 30_959, "sha256": "5609DAC3405E8F5F0032BA3215AC0B49A9F5F1BA7601FA2080B0AFFBFDF0FBB5"},
    "PROGRAM_CURSOR.json": {"bytes": 31_152, "sha256": "5EA5870B376E76EFD9468B1B6C213FE2FEF4038FD05AC2B0835DEA4CD69FCF45"},
    "STATE.json": {"bytes": 37_578, "sha256": "1ABD59EF44B8A76CF6FAFE2BEDAC893E3DF9F64317A14EE72AF0CCE29E9FD274"},
    "PROGRAM_STATE.json": {"bytes": 37_578, "sha256": "1ABD59EF44B8A76CF6FAFE2BEDAC893E3DF9F64317A14EE72AF0CCE29E9FD274"},
    "QA_STATE.json": {"bytes": 36_600, "sha256": "C97993C9816996603288D6BB5872DB37A70C7EFD6F0BFF7CC9289E2AFF5F1EE5"},
    "SOURCE_AUTHORITY.json": {"bytes": 31_086, "sha256": "58F08248A4E9BB21E8E1826F0A7BF52FD40703D233556F3ED3FECAFE17CDFCAB"},
    "PROGRAM_AUTHORITY.json": {"bytes": 38_939, "sha256": "EDB58FF83671C3B8B538C527EE33D62646D6262C3F849B894B2AE198060D6992"},
    "VISUAL_QA.json": {"bytes": 32_228, "sha256": "B9E9BE3DA39D2DD1E8089B882C62B19C31B8FE94E4B195A588E0C0E86833B758"},
    "DATACITE_RELATIONS.json": {"bytes": 31_258, "sha256": "D064BCB888C1E9050CF7C00A0F79F39070982A0BE0B3841513759B4DCBC8FB63"},
}
LEDGER_IDENTITIES = {
    "decisions.jsonl": {"bytes": 716_210, "sha256": "566270F97FB7D2317D24E551A99DFC5D9EF0105820DCC6C78300C974BB3D3626"},
    "evidence.jsonl": {"bytes": 553_405, "sha256": "0C47C199DE360C89CF3D4F012A8B141BC8A1254801B7888A0F266D003B39A3BB"},
    "hard.jsonl": {"bytes": 308_996, "sha256": "EF14FA5E89A9013B4853180EE3DFF279016D4D038283F8A2E66E8948FE2EA980"},
    "index/units.jsonl": {"bytes": 1_257_249, "sha256": "84DB52C484E5DBAF1500C7529F82944739F45D0A1FFBD060E7EE33A58F82095A"},
}
UNCHANGED_LEDGER_IDENTITIES = {
    "private/index/units.jsonl": {
        "bytes": 1_257_226,
        "sha256": "C82B56845193A8A20438F78F9924006C82AC84CDC50ABD57BF8F4408160D50E2",
    },
    "private/terms.jsonl": {
        "bytes": 263_512,
        "sha256": "756644F578732E9A41770CB6EE86F3BD6C39331AAA0A39F84A06FCA4A054D250",
    },
    "public/evidence/index/units.jsonl": LEDGER_IDENTITIES["index/units.jsonl"],
    "public/evidence/terms.jsonl": {
        "bytes": 263_512,
        "sha256": "756644F578732E9A41770CB6EE86F3BD6C39331AAA0A39F84A06FCA4A054D250",
    },
}
SEALED_CONTROL_PATHS = {
    "strict_build": "evidence/controls/R39_STRICT_BUILD.json",
    "visual_preparation": "evidence/controls/R39_VISUAL_QA_PREPARATION.json",
    "pdf_qa": "evidence/controls/R39_PDF_QA.json",
    "build_receipt": "evidence/BUILD_RECEIPT.json",
    "zenodo_reservation": "evidence/controls/R39_ZENODO_DRAFT_RESERVATION.json",
}
FIXED_ZIP_TIME = (2026, 9, 6, 0, 0, 0)
ASSETS = [
    "00_EGA_ko_CUMULATIVE_READER.pdf",
    "01_EGA_ko_EDITABLE_SOURCES.zip",
    "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip",
    "03_EGA_ko_SHA256_MANIFEST.txt",
]
R38_EVIDENCE_ZIP = Path("release/2026-09-05-r38/02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip")
R38_ALLOWLIST = Path("scripts/r38_evidence_release_cutoff.txt")
R39_ALLOWLIST = Path("scripts/r39_evidence_release_cutoff.txt")

SOURCE_ROOT_FILES = [
    ".gitattributes",
    ".zenodo.json",
    "CITATION.cff",
    "LICENSE",
    "README.md",
    "r39-github-release-notes.md",
]
SOURCE_CANDIDATES = [
    "candidates/integrate_r39_exact.py",
    "candidates/r39-c2s1-continuation.tex",
    "candidates/reseal_r39_authority_comment_exact.py",
    "candidates/reseal_r39_ideal_terminology_exact.py",
    "candidates/seal_r39_build_qa_state_exact.py",
    "candidates/validate_r39_candidate.py",
    "candidates/validate_r39_current.py",
]
SOURCE_SCRIPTS = [
    "scripts/append_r36_closure_records.py",
    "scripts/append_r37_closure_records.py",
    "scripts/append_r38_integration_records.py",
    "scripts/build_expert_review_log.py",
    "scripts/package_r36.py",
    "scripts/package_r37.py",
    "scripts/package_r38.py",
    "scripts/package_r39.py",
    "scripts/portable_replay_r36.py",
    "scripts/portable_replay_r37.py",
    "scripts/portable_replay_r38.py",
    "scripts/portable_replay_r39.py",
    "scripts/prepare_r36_release.py",
    "scripts/prepare_r37_release.py",
    "scripts/prepare_r38_release.py",
    "scripts/prepare_r39_release.py",
    "scripts/qa_r36_pdf.py",
    "scripts/qa_r37_pdf.py",
    "scripts/qa_r38_pdf.py",
    "scripts/qa_r39_pdf.py",
    "scripts/r38_evidence_release_cutoff.txt",
    "scripts/r39_evidence_release_cutoff.txt",
    "scripts/refresh_r36_state_aliases.py",
    "scripts/refresh_r37_state_aliases.py",
    "scripts/seal_r39_strict_build.py",
    "scripts/validate_expert_review_log.py",
]
R39_EVIDENCE_FILES = [
    "BUILD_RECEIPT_PRE_TERMINOLOGY.json",
    "build-r39.log",
    "r39-extract-poppler.txt",
    "r39-extract-pypdf.txt",
    "controls/R39_CANONICAL_PREFIX_REBASE.json",
    "controls/R39_AUTHORITY_COMMENT_RESEAL.json",
    "controls/R39_BUILD_QA_STATE_SEAL.json",
    "controls/R39_CURRENT_AUTHORITY_VALIDATOR.json",
    "controls/R39_IDEAL_TERMINOLOGY_RESEAL.json",
    "controls/R39_KOREAN_WORDING_RESEAL.json",
    "controls/R39_PDF_QA.json",
    "controls/R39_PDF_QA_PRE_TERMINOLOGY.json",
    "controls/R39_STRICT_BUILD.json",
    "controls/R39_STRICT_BUILD_PRE_TERMINOLOGY.json",
    "controls/R39_TRANSLATION_ADMISSION.json",
    "controls/R39_TRANSLATION_INTEGRATION.json",
    "controls/R39_VISUAL_QA_PREPARATION.json",
    "controls/R39_VISUAL_QA_PREPARATION_PRE_TERMINOLOGY.json",
    "controls/R39_ZENODO_DRAFT_RESERVATION.json",
]
MUTABLE_R39_EVIDENCE = {
    "BUILD_RECEIPT.json",
    "build.log",
    "extract.txt",
    "extract-pypdf.txt",
    "CURSOR.json",
    "PROGRAM_CURSOR.json",
    "STATE.json",
    "PROGRAM_STATE.json",
    "QA_STATE.json",
    "SOURCE_AUTHORITY.json",
    "PROGRAM_AUTHORITY.json",
    "VISUAL_QA.json",
    "DATACITE_RELATIONS.json",
}
JSONL_CUTOFFS = {
    "decisions.jsonl": "AGKO-D191",
    "evidence.jsonl": "AGKO-E-R39-BUILD-QA-STATE-SEAL",
    "hard.jsonl": "AGKO-H166",
    "index/units.jsonl": "AGKO-EGA2-S1-R39-IDEAL-TERMINOLOGY-RESEAL-R1",
}


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


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"JSON root is not an object: {path}")
    return value


def safe_name(name: str) -> None:
    pure = PurePosixPath(name)
    if not name or pure.is_absolute() or "\\" in name or ".." in pure.parts:
        fail(f"unsafe archive member: {name!r}")


def zip_info(name: str) -> zipfile.ZipInfo:
    safe_name(name)
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    info.flag_bits |= 0x800
    return info


def write_zip(path: Path, rows: list[tuple[str, bytes]]) -> None:
    names = [name for name, _ in rows]
    if names != sorted(names) or len(names) != len(set(names)):
        fail("archive rows are not sorted and unique")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as archive:
        for name, data in rows:
            archive.writestr(zip_info(name), data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify_zip(path: Path, expected: list[tuple[str, bytes]]) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as archive:
        if archive.testzip() is not None:
            fail(f"ZIP CRC failure: {path.name}")
        names = archive.namelist()
        expected_names = [name for name, _ in expected]
        if names != expected_names or len(names) != len(set(names)):
            fail(f"ZIP inventory drift: {path.name}")
        rows = []
        for info, (name, data) in zip(archive.infolist(), expected):
            if info.filename != name or info.file_size != len(data):
                fail(f"ZIP entry size drift: {name}")
            restored = archive.read(name)
            if restored != data:
                fail(f"ZIP entry bytes differ: {name}")
            rows.append({"path": name, "bytes": len(data), "sha256": sha_bytes(data)})
    inventory_payload = (json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    return {"entries": len(rows), "uncompressed_bytes": sum(row["bytes"] for row in rows), "inventory_sha256": sha_bytes(inventory_payload)}


def deterministic_zip(final_path: Path, rows: list[tuple[str, bytes]], stage: Path) -> dict[str, Any]:
    first = stage / (final_path.name + ".a")
    second = stage / (final_path.name + ".b")
    write_zip(first, rows)
    write_zip(second, rows)
    if first.read_bytes() != second.read_bytes():
        fail(f"deterministic ZIP replay failed: {final_path.name}")
    verification = verify_zip(first, rows)
    shutil.copyfile(first, final_path)
    verify_zip(final_path, rows)
    return {**ident(final_path, final_path.name), **verification, "deterministic_second_build_byte_identical": True}


def cutoff_jsonl(path: Path, terminal_id: str) -> bytes:
    raw_lines = path.read_bytes().splitlines(keepends=True)
    matches: list[int] = []
    for index, raw in enumerate(raw_lines):
        value = json.loads(raw.decode("utf-8"))
        if isinstance(value, dict) and value.get("id") == terminal_id:
            matches.append(index)
    if len(matches) != 1:
        fail(f"expected one terminal {terminal_id} in {path.name}, found {len(matches)}")
    payload = b"".join(raw_lines[: matches[0] + 1])
    if not payload.endswith(b"\n") or b"\r" in payload:
        fail(f"noncanonical JSONL cutoff: {path}")
    return payload


def require_identity(path: Path, expected: dict[str, Any], label: str) -> None:
    actual = ident(path, label)
    if actual["bytes"] != expected["bytes"] or actual["sha256"] != expected["sha256"]:
        fail(f"exact identity drift for {label}: {actual['bytes']}/{actual['sha256']}")


def identity_fields(value: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("bytes"), int)
        or not isinstance(value.get("sha256"), str)
    ):
        fail(f"malformed sealed identity: {label}")
    return {"bytes": value["bytes"], "sha256": value["sha256"]}


def validate_alias(path: Path, state_seal_postimages: dict[str, dict[str, Any]]) -> None:
    expected = ALIAS_POSTIMAGES.get(path.name)
    if expected is None:
        fail(f"unknown R39 alias: {path.name}")
    require_identity(path, expected, f"evidence/{path.name}")
    sealed = state_seal_postimages.get(f"public/evidence/{path.name}")
    if sealed != expected:
        fail(f"state-seal postimage binding drift: {path.name}")
    value = load(path)
    target = value.get("target", {})
    if not isinstance(target, dict) or target.get("sha256") != TARGET_SHA:
        fail(f"R39 current-target alias drift: {path.name}")
    if value.get("version") != VERSION:
        fail(f"R39 working-version alias drift: {path.name}")
    if value.get("coverage") != WORKING_COVERAGE:
        fail(f"R39 working-coverage alias drift: {path.name}")
    if value.get("reader") != READER_IDENTITY:
        fail(f"R39 reader alias drift: {path.name}")
    manifest = value.get("coverage_manifest", {})
    if (
        not isinstance(manifest, dict)
        or manifest.get("bytes") != MANIFEST_IDENTITY["bytes"]
        or manifest.get("sha256") != MANIFEST_IDENTITY["sha256"]
        or manifest.get("historical_markers") != 229
    ):
        fail(f"R39 manifest alias drift: {path.name}")
    if value.get("working_exact_version_doi") != EXACT_DOI or value.get("working_record_id") != 22_416_007:
        fail(f"R39 working DOI alias drift: {path.name}")
    if value.get("latest_public_version_remains") != "2026-09-05-r38":
        fail(f"R39/R38 public-boundary alias drift: {path.name}")
    checkpoint = value.get("r39_build_qa_checkpoint", {})
    if not isinstance(checkpoint, dict) or checkpoint.get("version") != VERSION:
        fail(f"R39 state-checkpoint alias drift: {path.name}")
    gates = checkpoint.get("gates", {})
    if (
        not isinstance(gates, dict)
        or gates.get("strict_build") != "PASS"
        or gates.get("pdf_qa") != "PASS"
        or gates.get("release_evidence") != "PASS"
        or gates.get("package") != "PENDING"
        or gates.get("portable_replay") != "PENDING"
        or gates.get("github_publication_and_anonymous_readback") != "PENDING"
        or gates.get("zenodo_publication_and_anonymous_readback") != "PENDING"
    ):
        fail(f"R39 gate alias drift: {path.name}")


def validate_state_seal(repo: Path, private_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    producer = private_root / STATE_SEAL_PRODUCER_IDENTITY["path"]
    private_control = private_root / "controls" / "R39_BUILD_QA_STATE_SEAL.json"
    public_control = repo / STATE_SEAL_IDENTITY["path"]
    require_identity(producer, STATE_SEAL_PRODUCER_IDENTITY, STATE_SEAL_PRODUCER_IDENTITY["path"])
    require_identity(private_control, STATE_SEAL_IDENTITY, "controls/R39_BUILD_QA_STATE_SEAL.json")
    require_identity(public_control, STATE_SEAL_IDENTITY, STATE_SEAL_IDENTITY["path"])
    if private_control.read_bytes() != public_control.read_bytes():
        fail("R39 state-seal control mirrors differ")
    seal = load(public_control)
    if (
        seal.get("schema") != "agko-r39-build-qa-state-seal-v1"
        or seal.get("id") != "AGKO-R39-BUILD-QA-STATE-SEAL"
        or seal.get("result") != "PASS_R39_BUILD_PDF_QA_STATE_SEAL"
        or seal.get("version") != VERSION
    ):
        fail("R39 state-seal schema/result/version drift")
    if seal.get("reader") != READER_IDENTITY:
        fail("R39 state-seal reader drift")
    manifest = seal.get("manifest", {})
    if (
        not isinstance(manifest, dict)
        or manifest.get("path") != MANIFEST_IDENTITY["path"]
        or manifest.get("bytes") != MANIFEST_IDENTITY["bytes"]
        or manifest.get("sha256") != MANIFEST_IDENTITY["sha256"]
        or manifest.get("historical_markers") != 229
    ):
        fail("R39 state-seal manifest drift")
    target = seal.get("target", {})
    if (
        not isinstance(target, dict)
        or target.get("path") != TARGET_IDENTITY["path"]
        or target.get("bytes") != TARGET_IDENTITY["bytes"]
        or target.get("sha256") != TARGET_IDENTITY["sha256"]
        or target.get("private_public_exact") is not True
    ):
        fail("R39 state-seal target drift")
    require_identity(repo / MANIFEST_IDENTITY["path"], MANIFEST_IDENTITY, MANIFEST_IDENTITY["path"])
    require_identity(repo / TARGET_IDENTITY["path"], TARGET_IDENTITY, TARGET_IDENTITY["path"])
    coverage = seal.get("coverage", {})
    if (
        coverage.get("terminal") != "EGA II §2.2.6 / canonical lines1-1780"
        or coverage.get("next") != "line1782 / environment2.2.7"
        or coverage.get("historical_markers") != 229
        or coverage.get("no_completion_claim") is not True
    ):
        fail("R39 state-seal coverage boundary drift")
    working = seal.get("working_release", {})
    if (
        working.get("exact_doi") != EXACT_DOI
        or working.get("concept_doi") != CONCEPT_DOI
        or working.get("record_id") != 22_416_007
        or working.get("status") != "reserved_unpublished"
        or working.get("latest_public_version_remains") != "2026-09-05-r38"
    ):
        fail("R39 state-seal DOI/public-boundary drift")
    gates = seal.get("gates", {})
    if (
        gates.get("strict_build") != "PASS"
        or gates.get("pdf_qa") != "PASS"
        or gates.get("release_evidence") != "PASS"
        or gates.get("package") != "PENDING"
        or gates.get("portable_replay") != "PENDING"
        or gates.get("github_publication_and_anonymous_readback") != "PENDING"
        or gates.get("zenodo_publication_and_anonymous_readback") != "PENDING"
    ):
        fail("R39 state-seal gate drift")
    if seal.get("appended_records") != {
        "decisions.jsonl": "AGKO-D191",
        "evidence.jsonl": "AGKO-E-R39-BUILD-QA-STATE-SEAL",
        "hard.jsonl": "AGKO-H166",
    }:
        fail("R39 state-seal ledger-terminal declaration drift")
    controls = seal.get("controls")
    if not isinstance(controls, dict) or set(controls) != set(SEALED_CONTROL_PATHS):
        fail("R39 state-seal control declaration drift")
    for key, expected_path in SEALED_CONTROL_PATHS.items():
        sealed_control = controls.get(key)
        if not isinstance(sealed_control, dict) or sealed_control.get("path") != expected_path:
            fail(f"R39 state-seal control path drift: {key}")
        require_identity(repo / expected_path, identity_fields(sealed_control, expected_path), expected_path)
    reservation_identity = identity_fields(controls["zenodo_reservation"], SEALED_CONTROL_PATHS["zenodo_reservation"])
    require_identity(
        private_root / "controls" / "R39_ZENODO_DRAFT_RESERVATION.json",
        reservation_identity,
        "controls/R39_ZENODO_DRAFT_RESERVATION.json",
    )
    unchanged_rows = seal.get("unchanged_ledgers")
    if not isinstance(unchanged_rows, list):
        fail("R39 state-seal unchanged-ledger declaration missing")
    sealed_unchanged: dict[str, dict[str, Any]] = {}
    for row in unchanged_rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            fail("malformed R39 state-seal unchanged-ledger identity")
        path = row["path"]
        if path in sealed_unchanged:
            fail(f"duplicate R39 state-seal unchanged ledger: {path}")
        sealed_unchanged[path] = identity_fields(row, path)
    if sealed_unchanged != UNCHANGED_LEDGER_IDENTITIES:
        fail("R39 state-seal unchanged-ledger identity drift")
    for name, expected in UNCHANGED_LEDGER_IDENTITIES.items():
        if name.startswith("private/"):
            path = private_root / name.removeprefix("private/")
        elif name.startswith("public/"):
            path = repo / name.removeprefix("public/")
        else:
            fail(f"unknown sealed unchanged-ledger namespace: {name}")
        require_identity(path, expected, name)
    postimages: dict[str, dict[str, Any]] = {}
    for row in seal.get("postimages", []):
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            fail("malformed R39 state-seal postimage")
        if row["path"] in postimages:
            fail(f"duplicate R39 state-seal postimage: {row['path']}")
        postimages[row["path"]] = {"bytes": row.get("bytes"), "sha256": row.get("sha256")}
    for name in ALIAS_POSTIMAGES:
        validate_alias(repo / "evidence" / name, postimages)
    for name, expected in LEDGER_IDENTITIES.items():
        path = repo / "evidence" / name
        require_identity(path, expected, f"evidence/{name}")
        sealed = postimages.get(f"public/evidence/{name}")
        if name != "index/units.jsonl" and sealed != expected:
            fail(f"state-seal ledger postimage drift: {name}")
        payload = cutoff_jsonl(path, JSONL_CUTOFFS[name])
        if payload != path.read_bytes():
            fail(f"R39 ledger contains records beyond sealed terminal: {name}")
    return seal, postimages


def validate_source_member_policy(names: list[str]) -> None:
    publication_markers = ("publish_", "verify_r39_github", "reserve_r39_", "publication_common", "publication_bindings")
    rejected = [name for name in names if any(marker in PurePosixPath(name).name for marker in publication_markers)]
    if rejected:
        fail(f"publication helpers are excluded from the editable-source archive: {rejected}")


def source_rows(repo: Path, private_root: Path, generated: dict[str, bytes]) -> list[tuple[str, bytes]]:
    manifest = load(repo / "source" / "CUMULATIVE_INPUTS.json")
    source_names = [
        "source/CUMULATIVE_INPUTS.json",
        "source/main.tex",
        *[f"source/{row['path']}" for row in manifest["ordered_inputs"]],
    ]
    names = SOURCE_ROOT_FILES + ["build/BUILD.ps1"] + SOURCE_CANDIDATES + SOURCE_SCRIPTS + source_names
    if len(names) != len(set(names)):
        fail("duplicate source archive path")
    if set(generated) - set(names):
        fail(f"generated source members are not declared: {sorted(set(generated) - set(names))}")
    validate_source_member_policy(names)
    rows: list[tuple[str, bytes]] = []
    for name in sorted(names):
        if name in generated:
            data = generated[name]
        elif name.startswith("candidates/"):
            path = private_root / name
            if not path.is_file():
                fail(f"source archive member absent: {name}")
            data = path.read_bytes()
        else:
            path = repo / name
            if not path.is_file():
                fail(f"source archive member absent: {name}")
            data = path.read_bytes()
        rows.append((name, data))
    return rows


def evidence_rows(repo: Path, state_seal_postimages: dict[str, dict[str, Any]]) -> list[tuple[str, bytes]]:
    evidence = repo / "evidence"
    r38_zip = repo / R38_EVIDENCE_ZIP
    r38_names = [line for line in (repo / R38_ALLOWLIST).read_text(encoding="utf-8").splitlines() if line]
    if r38_names != sorted(r38_names) or len(r38_names) != len(set(r38_names)):
        fail("R38 evidence allowlist drift")
    rows: dict[str, bytes] = {}
    with zipfile.ZipFile(r38_zip, "r") as archive:
        names = set(archive.namelist())
        for name in r38_names:
            if name not in names:
                fail(f"R38 evidence archive lacks inherited member: {name}")
            rows[name] = archive.read(name)
    for name in sorted(MUTABLE_R39_EVIDENCE):
        path = evidence / name
        if name in {"CURSOR.json", "PROGRAM_CURSOR.json", "STATE.json", "PROGRAM_STATE.json", "QA_STATE.json", "SOURCE_AUTHORITY.json", "PROGRAM_AUTHORITY.json", "VISUAL_QA.json", "DATACITE_RELATIONS.json"}:
            validate_alias(path, state_seal_postimages)
        rows[name] = path.read_bytes()
    for name, terminal in JSONL_CUTOFFS.items():
        rows[name] = cutoff_jsonl(evidence / name, terminal)
    terms_path = evidence / "terms.jsonl"
    require_identity(terms_path, UNCHANGED_LEDGER_IDENTITIES["public/evidence/terms.jsonl"], "evidence/terms.jsonl")
    rows["terms.jsonl"] = terms_path.read_bytes()
    for name in R39_EVIDENCE_FILES:
        path = evidence / name
        if not path.is_file():
            fail(f"R39 evidence member absent: {name}")
        rows[name] = path.read_bytes()
    for render in sorted((evidence / "render").glob("r39-p*.png")):
        rows[f"render/{render.name}"] = render.read_bytes()
    qa = load(evidence / "controls" / "R39_PDF_QA.json")
    qa_render_names = {str(row["path"]).removeprefix("evidence/") for row in qa.get("renders", [])}
    actual_render_names = {name for name in rows if name.startswith("render/r39-p")}
    if qa_render_names != actual_render_names:
        fail(f"R39 render evidence set drift: {sorted(actual_render_names ^ qa_render_names)}")
    rows.pop("ARTIFACT_SHA256.tsv", None)
    manifest = "path\tbytes\tsha256\n" + "".join(f"{name}\t{len(data)}\t{sha_bytes(data)}\n" for name, data in sorted(rows.items()))
    rows["ARTIFACT_SHA256.tsv"] = manifest.encode("utf-8")
    return sorted(rows.items())


def manifest_payload(directory: Path) -> bytes:
    text = "filename\tbytes\tsha256\n" + "".join(
        f"{name}\t{(directory / name).stat().st_size}\t{sha_file(directory / name)}\n"
        for name in ASSETS[:3]
    )
    return text.encode("utf-8")


def directory_inventory(directory: Path) -> list[dict[str, Any]]:
    expected = sorted([*ASSETS, "PACKAGE_RECEIPT.json"])
    if not directory.is_dir() or directory.is_symlink():
        fail(f"package path is not a regular directory: {directory}")
    actual = sorted(path.name for path in directory.iterdir())
    if actual != expected:
        fail(f"package directory inventory drift: expected {expected}, got {actual}")
    rows = []
    for name in expected:
        path = directory / name
        if not path.is_file() or path.is_symlink():
            fail(f"package member is not a regular file: {name}")
        rows.append({"name": name, "bytes": path.stat().st_size, "sha256": sha_file(path)})
    return rows


def is_link_or_junction(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def verify_package_directory(
    directory: Path,
    sources_data: list[tuple[str, bytes]],
    evidence_data: list[tuple[str, bytes]],
    expected_manifest: bytes,
    receipt: dict[str, Any],
    receipt_payload: bytes,
) -> dict[str, Any]:
    inventory = directory_inventory(directory)
    require_identity(directory / ASSETS[0], READER_IDENTITY, ASSETS[0])
    source_verification = verify_zip(directory / ASSETS[1], sources_data)
    evidence_verification = verify_zip(directory / ASSETS[2], evidence_data)
    if (directory / ASSETS[3]).read_bytes() != expected_manifest:
        fail("outer SHA-256 manifest bytes drift")
    if manifest_payload(directory) != expected_manifest:
        fail("independent outer SHA-256 manifest replay drift")
    receipt_path = directory / "PACKAGE_RECEIPT.json"
    if receipt_path.read_bytes() != receipt_payload or load(receipt_path) != receipt:
        fail("package receipt replay drift")
    if source_verification != {
        key: receipt["source_archive"][key]
        for key in ("entries", "uncompressed_bytes", "inventory_sha256")
    }:
        fail("source archive verification/receipt drift")
    if evidence_verification != {
        key: receipt["evidence_archive"][key]
        for key in ("entries", "uncompressed_bytes", "inventory_sha256")
    }:
        fail("evidence archive verification/receipt drift")
    payload = (json.dumps(inventory, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    return {
        "files": inventory,
        "tree_inventory_sha256": sha_bytes(payload),
        "source_zip": source_verification,
        "evidence_zip": evidence_verification,
        "receipt": {"bytes": len(receipt_payload), "sha256": sha_bytes(receipt_payload)},
    }


def build_stage(
    stage: Path,
    repo: Path,
    strict: dict[str, Any],
    seal: dict[str, Any],
    state_seal_postimages: dict[str, dict[str, Any]],
    sources_data: list[tuple[str, bytes]],
    evidence_data: list[tuple[str, bytes]],
    allowlist_names: list[str],
    allowlist_payload: bytes,
    r39_control_names: list[str],
) -> tuple[dict[str, Any], bytes, bytes]:
    scratch = stage / ".deterministic-replay"
    scratch.mkdir()
    reader_target = stage / ASSETS[0]
    shutil.copyfile(repo / "reader" / ASSETS[0], reader_target)
    source_info = deterministic_zip(stage / ASSETS[1], sources_data, scratch)
    evidence_info = deterministic_zip(stage / ASSETS[2], evidence_data, scratch)
    outer_manifest = manifest_payload(stage)
    (stage / ASSETS[3]).write_bytes(outer_manifest)
    if manifest_payload(stage) != outer_manifest:
        fail("outer manifest construction replay drift")
    assets = [
        {"order": index, "name": name, "bytes": (stage / name).stat().st_size, "sha256": sha_file(stage / name)}
        for index, name in enumerate(ASSETS)
    ]
    alias_bindings = [
        {"path": f"evidence/{name}", **ALIAS_POSTIMAGES[name]}
        for name in sorted(ALIAS_POSTIMAGES)
    ]
    receipt: dict[str, Any] = {
        "schema": "ag-ko-package-receipt-v7",
        "version": VERSION,
        "created_at": seal["sealed_at"],
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "coverage": {
            "terminal": "EGA II §2.2.6 / canonical lines1-1780",
            "next": "line1782 / environment2.2.7",
            "historical_markers": 229,
            "no_completion_claim": True,
        },
        "public_artifact_count": 4,
        "files": assets,
        "source_archive": source_info,
        "evidence_archive": evidence_info,
        "r39_evidence_release_cutoff": {
            "path": "scripts/r39_evidence_release_cutoff.txt",
            "entries": len(allowlist_names),
            "bytes": len(allowlist_payload),
            "sha256": sha_bytes(allowlist_payload),
            "jsonl_terminal_ids": JSONL_CUTOFFS,
        },
        "required_controls": r39_control_names,
        "state_seal": {
            **STATE_SEAL_IDENTITY,
            "result": seal["result"],
            "transaction_id": seal["transaction_id"],
            "fresh_preimage_sha256": seal["fresh_preimage_sha256"],
        },
        "state_seal_producer": dict(STATE_SEAL_PRODUCER_IDENTITY),
        "sealed_alias_postimages": alias_bindings,
        "sealed_public_ledger_postimages": [
            {"path": f"evidence/{name}", **LEDGER_IDENTITIES[name], "terminal_id": JSONL_CUTOFFS[name]}
            for name in JSONL_CUTOFFS
            if name != "index/units.jsonl"
        ],
        "sealed_unchanged_ledgers": [
            {"path": name, **UNCHANGED_LEDGER_IDENTITIES[name]}
            for name in sorted(UNCHANGED_LEDGER_IDENTITIES)
        ],
        "reader": {**ident(reader_target, ASSETS[0]), "pages": strict["reader"]["pages"]},
        "source_manifest": dict(MANIFEST_IDENTITY),
        "strict_build": ident(repo / "evidence" / "controls" / "R39_STRICT_BUILD.json", "evidence/controls/R39_STRICT_BUILD.json"),
        "pdf_qa": ident(repo / "evidence" / "controls" / "R39_PDF_QA.json", "evidence/controls/R39_PDF_QA.json"),
        "transaction": {
            "same_volume_sibling_stage": True,
            "staged_verification_passes": 2,
            "atomic_directory_rename": True,
            "exact_final_directory_is_idempotent_success": True,
            "differing_final_directory_fails_closed": True,
            "precommit_repository_sidecar_writes": 0,
        },
        "result": "PASS_R39_LOCAL_PACKAGE",
    }
    expected_alias_bindings = {
        row["path"].removeprefix("evidence/"): {"bytes": row["bytes"], "sha256": row["sha256"]}
        for row in receipt["sealed_alias_postimages"]
    }
    if expected_alias_bindings != ALIAS_POSTIMAGES:
        fail("receipt alias binding construction drift")
    if any(
        state_seal_postimages.get(f"public/evidence/{name}") != expected
        for name, expected in ALIAS_POSTIMAGES.items()
    ):
        fail("receipt/state-seal alias binding drift")
    receipt_payload = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (stage / "PACKAGE_RECEIPT.json").write_bytes(receipt_payload)
    shutil.rmtree(scratch)
    return receipt, receipt_payload, outer_manifest


def validate_prerequisites(repo: Path, private_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    seal, postimages = validate_state_seal(repo, private_root)
    strict = load(repo / "evidence" / "controls" / "R39_STRICT_BUILD.json")
    qa = load(repo / "evidence" / "controls" / "R39_PDF_QA.json")
    build_receipt = load(repo / "evidence" / "BUILD_RECEIPT.json")
    if (
        strict.get("status") != "PASS_R39_STRICT_TWO_CYCLE_FOUR_PASS_BUILD"
        or qa.get("status") != "PASS"
        or build_receipt.get("result") != "PASS_R39_RELEASE_EVIDENCE"
    ):
        fail("R39 build/QA/preparation gates did not pass")
    if strict.get("reader") != {key: READER_IDENTITY[key] for key in ("path", "bytes", "sha256", "pages")}:
        fail("R39 strict-build reader identity drift")
    reservation = private_root / "controls" / "R39_ZENODO_DRAFT_RESERVATION.json"
    public_reservation = repo / "evidence" / "controls" / "R39_ZENODO_DRAFT_RESERVATION.json"
    if not reservation.is_file() or not public_reservation.is_file() or reservation.read_bytes() != public_reservation.read_bytes():
        fail("R39 Zenodo reservation mirror drift")
    return seal, postimages, strict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve(strict=True)
    private_root = args.private_root.resolve(strict=True)
    expected_repo = (private_root / "pub" / "ega-ko").resolve(strict=True)
    if repo != expected_repo:
        fail("repository/private-root relationship drift")
    seal, state_seal_postimages, strict = validate_prerequisites(repo, private_root)

    r39_control_names = sorted(PurePosixPath(name).name for name in R39_EVIDENCE_FILES if name.startswith("controls/"))
    required_controls = {
        "R39_AUTHORITY_COMMENT_RESEAL.json",
        "R39_BUILD_QA_STATE_SEAL.json",
        "R39_IDEAL_TERMINOLOGY_RESEAL.json",
        "R39_PDF_QA.json",
        "R39_STRICT_BUILD.json",
        "R39_VISUAL_QA_PREPARATION.json",
        "R39_ZENODO_DRAFT_RESERVATION.json",
    }
    if not required_controls.issubset(r39_control_names):
        fail(f"required R39 controls missing: {sorted(required_controls - set(r39_control_names))}")
    validate_source_member_policy(SOURCE_ROOT_FILES + ["build/BUILD.ps1"] + SOURCE_CANDIDATES + SOURCE_SCRIPTS)
    if args.validate_only:
        print(
            "PASS_R39_PACKAGER_STATIC_BINDINGS"
            f"|state_seal={STATE_SEAL_IDENTITY['bytes']}/{STATE_SEAL_IDENTITY['sha256']}"
            f"|aliases={len(ALIAS_POSTIMAGES)}|ledger_terminals={len(JSONL_CUTOFFS)}"
        )
        return

    evidence_data = evidence_rows(repo, state_seal_postimages)
    allowlist_names = [name for name, _ in evidence_data if name != "ARTIFACT_SHA256.tsv"]
    allowlist_payload = ("\n".join(allowlist_names) + "\n").encode("utf-8")
    sources_data = source_rows(repo, private_root, {R39_ALLOWLIST.as_posix(): allowlist_payload})

    release_parent_lexical = repo / "release"
    if is_link_or_junction(release_parent_lexical):
        fail("release parent is a link or junction")
    release_parent = release_parent_lexical.resolve(strict=True)
    if not release_parent.is_dir() or release_parent != release_parent_lexical:
        fail("release parent is not a regular same-volume directory")
    final = release_parent / VERSION
    if is_link_or_junction(final):
        fail("R39 final release path is a link or junction")
    resolved_final = final.resolve(strict=False)
    if resolved_final.parent != release_parent:
        fail("unsafe R39 final release path")
    stage = Path(tempfile.mkdtemp(prefix=f".{VERSION}.stage-", dir=release_parent))
    promoted = False
    try:
        receipt, receipt_payload, outer_manifest = build_stage(
            stage,
            repo,
            strict,
            seal,
            state_seal_postimages,
            sources_data,
            evidence_data,
            allowlist_names,
            allowlist_payload,
            r39_control_names,
        )
        first = verify_package_directory(stage, sources_data, evidence_data, outer_manifest, receipt, receipt_payload)
        second = verify_package_directory(stage, sources_data, evidence_data, outer_manifest, receipt, receipt_payload)
        if first != second:
            fail("two-pass staged package verification drift")
        if final.exists() or final.is_symlink():
            final_first = verify_package_directory(final, sources_data, evidence_data, outer_manifest, receipt, receipt_payload)
            final_second = verify_package_directory(final, sources_data, evidence_data, outer_manifest, receipt, receipt_payload)
            if final_first != first or final_second != first:
                fail("existing R39 final directory differs from the exact staged package")
            print(
                f"PASS_R39_LOCAL_PACKAGE_IDEMPOTENT|receipt={len(receipt_payload)}/{sha_bytes(receipt_payload)}|"
                + "|".join(f"{row['name']}={row['bytes']}/{row['sha256']}" for row in receipt["files"])
            )
            return
        os.replace(stage, final)
        promoted = True
        final_verification = verify_package_directory(final, sources_data, evidence_data, outer_manifest, receipt, receipt_payload)
        if final_verification != first:
            fail("post-rename final package verification drift")
        print(
            f"PASS_R39_LOCAL_PACKAGE|receipt={len(receipt_payload)}/{sha_bytes(receipt_payload)}|"
            + "|".join(f"{row['name']}={row['bytes']}/{row['sha256']}" for row in receipt["files"])
        )
    finally:
        if not promoted and stage.exists():
            shutil.rmtree(stage)


if __name__ == "__main__":
    main()
