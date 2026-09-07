"""Fail-closed exact R39 integration transaction.

This private operator never builds, renders, invokes Git, contacts a hosting
service, or opens a user-interface surface.  ``--check`` (also
``--dry-run``) is read-only.  ``--execute`` is accepted only with the fresh
preimage digest printed by a successful check.  Every postimage is computed
before the first write; an exact preimage snapshot and a durable journal make
ordinary failures exactly reversible.

The final R39 translation bindings are intentionally collected in one table.
They are populated only after the corrected Korean wording has been resealed;
the earlier candidate/prospective identities are historical and must never be
used for integration.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


VERSION = "2026-09-05-r38"
PREVIOUS_VERSION = "2026-09-05-r37"
R38_TAG = "ega-ko-2026-09-05-r38"
R38_RECORD_ID = 22_346_664
R38_EXACT_DOI = "10.5281/zenodo.22346664"
R38_CONCEPT_DOI = "10.5281/zenodo.21921513"
R38_REPOSITORY = "https://github.com/KokunoYumeto/ega-ko"
R38_RELEASE = f"{R38_REPOSITORY}/releases/tag/{R38_TAG}"
R38_ZENODO = f"https://zenodo.org/records/{R38_RECORD_ID}"
R38_PUBLIC_STATUS = "PASS_R38_PUBLIC_OPEN_DUAL_DESTINATION_AND_ANONYMOUS_BYTE_REPLAY"
R38_ARTIFACT_COMMIT = "f9fdf4fccbadda75dbdb74505336c6fd33975baa"
R38_ARTIFACT_PARENT = "2eb01c1656c37a818fcbbc05bb431be7f5905506"
R38_ARTIFACT_TREE = "5c52ce8fb6929786b1fa28db2ceea434dab3c662"
R38_ANNOTATED_TAG = "fd1affa7b12d4a7bcbdd386186ceeb0addeb0f8c"
R38_TARGET = {
    "bytes": 80_222,
    "characters": 55_906,
    "lf_lines": 1_708,
    "sha256": "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006",
}
CURRENT_SOURCE = {
    "path": "source/ega2/ega2-1-fr.tex",
    "bytes": 820_504,
    "characters": 809_277,
    "lf_lines": 18_087,
    "sha256": "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E",
}
SOURCE_UNIT = {
    "lines": "1685-1780",
    "bytes": 3_796,
    "characters": 3_740,
    "lf_lines": 96,
    "sha256": "BE7EC704F82B9283A48AFF1A01D7CF34F14A2C29F1B50269511DD699514BBC21",
    "admitted_prefix_bytes": 81_885,
    "admitted_prefix_characters": 80_628,
    "admitted_prefix_lf_lines": 1_780,
    "admitted_prefix_sha256": "033E312D8BD9E22AEC1D5B8AC5705ED71C64C4E4DCFBB7ED84B9A434313ACE33",
}
HISTORICAL_ADMISSION = {
    "private": "controls/R39_TRANSLATION_ADMISSION.json",
    "public": "evidence/controls/R39_TRANSLATION_ADMISSION.json",
    "bytes": 8_605,
    "sha256": "D7122B74AADB7E26B987AFABAA0D12E59E1342D4F63FEDA0DFE3AB0557330561",
    "schema": "agko-r39-translation-admission-v1",
    "result": "PASS_R39_SOURCE_CANDIDATE_AND_PROSPECTIVE_MIRRORS",
}
HISTORICAL_REBASE = {
    "private": "controls/R39_CANONICAL_PREFIX_REBASE.json",
    "public": "evidence/controls/R39_CANONICAL_PREFIX_REBASE.json",
    "bytes": 6_370,
    "sha256": "CD9E1E2CF87D2E35C49AE7AF16E797AF146B72C6060869B631019DB8F6782349",
    "schema": "agko-r39-canonical-prefix-rebase-v1",
    "result": "PASS_R39_CANONICAL_PREFIX_REBASE_CANDIDATE_AND_PROSPECTIVE_TARGET_UNAFFECTED",
}

# Populated only from the corrected, independently reviewed reseal.  None of
# these identities is inherited from the superseded R39 candidate.
SEALED: dict[str, Any] = {
    "candidate": {
        "path": "candidates/r39-c2s1-continuation.tex",
        "bytes": 4_051,
        "characters": 2_771,
        "lf_lines": 100,
        "sha256": "E8F52EDEC11B90D3CCC4E2398279DA4DEA7A6064AABFBE87D1765D55FEDE1940",
    },
    "separator_plus_candidate": {
        "bytes": 4_052,
        "sha256": "7CF528B90E7D1D50EEAABF714AB185C574F5C8A86520F46A7D697FAFB381186C",
    },
    "postimage": {
        "bytes": 84_274,
        "characters": 58_678,
        "lf_lines": 1_809,
        "sha256": "F3DD70691223B0D35052B4D6F4CF5E77B72AA2C5F352EDE5D9C83E98704C8257",
    },
    "validator": {
        "path": "candidates/validate_r39_current.py",
        "bytes": 31_085,
        "sha256": "8040EC2CD547EDD2187FFA3398AEFF991069F5409E077ADD9677D8B2BEFA1366",
        "result": "PASS_R39_CURRENT_AUTHORITY_CANDIDATE_AND_PROSPECTIVE_TARGET",
    },
    "validator_receipt": {
        "path": "controls/R39_CURRENT_AUTHORITY_VALIDATOR.json",
        "bytes": 10_257,
        "sha256": "F572BDDCFADAC93EAC01C00E07DBA16D03BEDFE3E14B5E4FADEA1B5A76AC2350",
        "schema": "agko-r39-current-authority-validator-receipt-v2",
        "result": "PASS_R39_CURRENT_AUTHORITY_WORDING_RESEAL_READY",
    },
    "reseal_control": {
        "private": "controls/R39_KOREAN_WORDING_RESEAL.json",
        "public": "evidence/controls/R39_KOREAN_WORDING_RESEAL.json",
        "bytes": 10_118,
        "sha256": "9A30C30953B7C118434541FBE8F9A362BB374BB68835E479536073B8DE730451",
        "schema": "agko-r39-korean-wording-reseal-v1",
        "result": "PASS_R39_KOREAN_WORDING_RESEALED_CURRENT_CANDIDATE_AND_PROSPECTIVE_TARGET",
    },
}

R38_ARTIFACTS = (
    {
        "name": "00_EGA_ko_CUMULATIVE_READER.pdf",
        "bytes": 1_485_270,
        "sha256": "FEC06D6723BFE9CC7D3C46E285C7DE8A49929F2797FD2F4F47877D2BDA06FE15",
    },
    {
        "name": "01_EGA_ko_EDITABLE_SOURCES.zip",
        "bytes": 430_517,
        "sha256": "A9C0178A361150C3E0A7E0A57534C40E14FDAC91511F8910EC240D69969B01C2",
    },
    {
        "name": "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip",
        "bytes": 122_840_828,
        "sha256": "871FFCB2E53B27384CB88595E593A1A446361D462E657C92360D32EC805F0197",
    },
    {
        "name": "03_EGA_ko_SHA256_MANIFEST.txt",
        "bytes": 343,
        "sha256": "63F478687E239426236D07C1FD4DA0CBCADA6C8990F018776722610C9FAB9988",
    },
)
R38_READER = {
    "name": "00_EGA_ko_CUMULATIVE_READER.pdf",
    "path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf",
    "pages": 239,
    "bytes": 1_485_270,
    "sha256": "FEC06D6723BFE9CC7D3C46E285C7DE8A49929F2797FD2F4F47877D2BDA06FE15",
}
R38_PREDECESSOR_RECORD_ID = 22_315_714
R38_PREDECESSOR_EXACT_DOI = "10.5281/zenodo.22315714"
R38_PACKAGE = {
    "bytes": 35_345,
    "sha256": "6357FD948CEE1054FBA56AC84CB321FFC0C6C3773A0378212D5B478156C4F63C",
}
R38_PORTABLE = {
    "bytes": 12_695,
    "sha256": "777EA4337DB3A9E213402A1B14CEC9C2E2460CE6AC293A99CF7AC63ED60D162B",
}
R38_ZENODO_RECEIPT = {
    "bytes": 4_328,
    "sha256": "2750F62CA7A87A3C72A2D997290B103CC2F40E8298EB0E842439353FEA37BAA5",
}
R38_GITHUB_RECEIPT = {
    "bytes": 78_362,
    "sha256": "E7528B33A0CC000268E72AAD77D6612FF6931098D57E39F7E5FF9238EE35057F",
}

PUBLIC_ALIASES = (
    "CURSOR.json",
    "PROGRAM_CURSOR.json",
    "STATE.json",
    "PROGRAM_STATE.json",
    "QA_STATE.json",
    "VISUAL_QA.json",
    "SOURCE_AUTHORITY.json",
    "PROGRAM_AUTHORITY.json",
    "DATACITE_RELATIONS.json",
)
PUBLIC_SCHEMAS: Mapping[str, tuple[str, Any]] = {
    "CURSOR.json": ("schema_version", 4),
    "PROGRAM_CURSOR.json": ("schema_version", 4),
    "STATE.json": ("schema_version", 4),
    "PROGRAM_STATE.json": ("schema_version", 4),
    "QA_STATE.json": ("schema_version", 4),
    "VISUAL_QA.json": ("schema_version", 4),
    "SOURCE_AUTHORITY.json": ("schema_version", 4),
    "PROGRAM_AUTHORITY.json": ("schema", "ag-ko-program-authority-public-v3"),
    "DATACITE_RELATIONS.json": ("schema_version", 2),
}
PRIVATE_SCHEMAS: Mapping[str, tuple[str, Any]] = {
    "cursor.json": ("schema", "ag-ko-cursor-v3"),
    "state.json": ("schema", "ag-ko-state-v2"),
}
LEDGERS = ("decisions.jsonl", "evidence.jsonl", "hard.jsonl")
R39_RESULT = "PASS_R39_TRANSLATION_INTEGRATION"
R39_STATUS = f"{R39_RESULT}; build, PDF QA, package and publication pending"
R39_CANDIDATE_STATUS = "INTEGRATED_EXACT_MIRRORS_PENDING_BUILD_QA_PACKAGE_PUBLICATION"
WORKING_COVERAGE = (
    "Complete Korean EGA 0_I and EGA I; complete EGA II programme/table of "
    "contents and main text contiguously through §2.2.6 / canonical lines "
    "1-1780. EGA II and the full EGA corpus remain incomplete."
)
NEXT_SOURCE = (
    "EGA II canonical source/ega2/ega2-1-fr.tex line1782, environment §2.2.7; "
    "line1781 is blank"
)
MUTEX_NAME = r"Global\InterlanguageAgKoR39IntegrationV1"
JOURNAL_REL = Path("controls/R39_INTEGRATION_TRANSACTION.json")
WORK_REL = Path("controls/.r39-integration")
CONTROL_PRIVATE_REL = Path("controls/R39_TRANSLATION_INTEGRATION.json")
CONTROL_PUBLIC_REL = Path("evidence/controls/R39_TRANSLATION_INTEGRATION.json")

EXPECTED_CLOSURE_PATHS = tuple(
    sorted(
        [
            "evidence/controls/R38_PUBLIC_CLOSURE.json",
            "github-receipt-r38.json",
            "receipt-r38.json",
            f"release/{VERSION}/GITHUB_PUBLICATION_RECEIPT.json",
            f"release/{VERSION}/ZENODO_PUBLICATION_RECEIPT.json",
        ]
    )
)
PUBLICATION_PHASES = (
    "prepared",
    "zenodo_draft_mutation_intent",
    "zenodo_draft_ready",
    "zenodo_publish_intent",
    "zenodo_published",
    "zenodo_verified",
    "github_artifact_commit_intent",
    "github_artifact_commit_ready",
    "github_push_intent",
    "github_pushed",
    "github_release_intent",
    "github_release_published",
    "github_verified",
    "closure_intent",
    "closure_pushed",
    "complete",
)
SHA_RE = re.compile(r"[0-9A-F]{64}\Z")
GIT_RE = re.compile(r"[0-9a-f]{40}\Z")
PRIVATE_PATH_RE = re.compile(
    r"(?i)(?:(?<![A-Z0-9])[A-Z]:[\\/][^\s\"']+|\\\\[^\\/\s\"']+[\\/][^\s\"']+|/(?:home|Users)/[^/\s\"']+/[^\s\"']*)"
)
EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9._%+-])")
CREDENTIAL_RE = re.compile(r"(?i)(?:gh[pousr]_[A-Za-z0-9]{20,}|bearer\s+[A-Za-z0-9._~-]{16,}|(?:access[_-]?token|api[_-]?key)\s*[:=]\s*[^\s,}\"]{8,})")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def ident_bytes(data: bytes) -> dict[str, int | str]:
    return {"bytes": len(data), "sha256": digest(data)}


def ident(path: Path) -> dict[str, int | str]:
    return ident_bytes(path.read_bytes())


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def jsonl_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_bytes(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=reject_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid JSON: {label}") from exc
    require(isinstance(value, dict), f"JSON root is not an object: {label}")
    return value


def parse_json(path: Path, label: str) -> dict[str, Any]:
    regular(path, label)
    return parse_json_bytes(path.read_bytes(), label)


def parse_jsonl(data: bytes, label: str) -> list[dict[str, Any]]:
    require(data.endswith(b"\n"), f"JSONL lacks terminal LF: {label}")
    require(b"\r" not in data, f"JSONL is not LF-only: {label}")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, line in enumerate(data.splitlines(), start=1):
        require(bool(line), f"blank JSONL row: {label}:{number}")
        row = parse_json_bytes(line, f"{label}:{number}")
        row_id = row.get("id")
        require(isinstance(row_id, str) and row_id, f"missing JSONL id: {label}:{number}")
        require(row_id not in seen, f"duplicate JSONL id: {label}:{row_id}")
        seen.add(row_id)
        rows.append(row)
    return rows


def regular(path: Path, label: str) -> None:
    require(path.exists(), f"missing prerequisite: {label}")
    require(path.is_file() and not path.is_symlink(), f"not a regular file: {label}")


def directory(path: Path, label: str) -> None:
    require(path.exists(), f"missing directory: {label}")
    require(path.is_dir() and not path.is_symlink(), f"not a plain directory: {label}")


def require_ident(path: Path, expected: Mapping[str, Any], label: str) -> bytes:
    regular(path, label)
    data = path.read_bytes()
    require(ident_bytes(data) == {"bytes": expected["bytes"], "sha256": expected["sha256"]}, f"identity drift: {label}")
    return data


def require_sha(value: Any, label: str) -> str:
    require(isinstance(value, str) and SHA_RE.fullmatch(value) is not None, f"invalid SHA-256 binding: {label}")
    return value


def validate_time(value: str | None) -> str:
    if value is None:
        value = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError("--at must be an ISO-8601 timestamp") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "--at must include a UTC offset")
    require(parsed.microsecond == 0, "--at precision must be exactly one second")
    return parsed.isoformat(timespec="seconds")


def require_sealed_bindings() -> None:
    for section in ("candidate", "separator_plus_candidate", "postimage", "validator", "validator_receipt", "reseal_control"):
        require(section in SEALED and isinstance(SEALED[section], dict), f"missing sealed section: {section}")
        require("PENDING" not in SEALED[section].values(), "corrected R39 reseal bindings are not populated")
    for section in ("candidate", "separator_plus_candidate", "postimage", "validator", "validator_receipt", "reseal_control"):
        item = SEALED[section]
        require(isinstance(item.get("bytes"), int) and item["bytes"] > 0, f"invalid byte binding: {section}")
        require_sha(item.get("sha256"), section)
    for key in ("characters", "lf_lines"):
        require(isinstance(SEALED["candidate"].get(key), int) and SEALED["candidate"][key] > 0, f"invalid candidate {key}")
        require(isinstance(SEALED["postimage"].get(key), int) and SEALED["postimage"][key] > 0, f"invalid postimage {key}")
    require(SEALED["postimage"]["bytes"] == R38_TARGET["bytes"] + SEALED["separator_plus_candidate"]["bytes"], "sealed postimage size arithmetic drift")
    require(SEALED["separator_plus_candidate"]["bytes"] == SEALED["candidate"]["bytes"] + 1, "sealed separator size arithmetic drift")


def find_workspace_root(private: Path) -> Path:
    for item in (private, *private.parents):
        if item.name.casefold() == "interlanguage":
            return item
    raise RuntimeError("could not derive the bounded workspace root")


@dataclass(frozen=True)
class Roots:
    private: Path
    repo: Path
    canonical: Path

    @classmethod
    def make(cls, private: Path, repo: Path | None, canonical: Path | None) -> "Roots":
        private = private.resolve(strict=True)
        repo = (repo or private / "pub" / "ega-ko").resolve(strict=True)
        if canonical is None:
            workspace = find_workspace_root(private)
            canonical = workspace / "Transcription" / "03_working_transcriptions" / "EGA_French_NUMDAM_canonical_TeX_20260801_r1"
        canonical = canonical.resolve(strict=True)
        directory(private, "private root")
        directory(repo, "public repository root")
        directory(canonical, "canonical root")
        require(repo == (private / "pub" / "ega-ko").resolve(strict=True), "repository root is not the exact Korean EGA public tree")
        require(private not in canonical.parents and canonical not in private.parents, "private and canonical roots overlap")
        return cls(private=private, repo=repo, canonical=canonical)


def role(path: Path, roots: Roots) -> str:
    resolved = path.resolve(strict=False)
    for base, prefix in (
        (roots.canonical, "[CANONICAL_ROOT]"),
        (roots.repo, "[PUBLIC_REPOSITORY_ROOT]"),
        (roots.private, "[PRIVATE_ROOT]"),
    ):
        if resolved == base or resolved.is_relative_to(base):
            suffix = resolved.relative_to(base).as_posix()
            return prefix + ("/" + suffix if suffix else "")
    raise RuntimeError("path escapes the three exact roots")


def resolve_role(locator: str, roots: Roots) -> Path:
    for prefix, base in (
        ("[CANONICAL_ROOT]", roots.canonical),
        ("[PUBLIC_REPOSITORY_ROOT]", roots.repo),
        ("[PRIVATE_ROOT]", roots.private),
    ):
        if locator == prefix:
            return base
        marker = prefix + "/"
        if locator.startswith(marker):
            parts = Path(locator[len(marker) :]).parts
            require(all(part not in {"", ".", ".."} for part in parts), "unsafe role locator")
            result = base.joinpath(*parts).resolve(strict=False)
            require(result == base or result.is_relative_to(base), "role locator escapes root")
            return result
    raise RuntimeError("unknown role locator")


def normalized_inventory(rows: Any, flag: str | None, label: str) -> list[dict[str, Any]]:
    require(isinstance(rows, list), f"inventory is not a list: {label}")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        require(isinstance(row, dict), f"inventory row is not an object: {label}")
        name = row.get("name")
        require(isinstance(name, str) and name not in seen, f"duplicate/malformed inventory row: {label}")
        seen.add(name)
        normalized = {"name": name, "bytes": row.get("bytes"), "sha256": row.get("sha256")}
        if flag is not None:
            normalized[flag] = row.get(flag)
        result.append(normalized)
    return result


def normalized_paths(rows: Any, label: str) -> list[dict[str, Any]]:
    require(isinstance(rows, list), f"path inventory is not a list: {label}")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        require(isinstance(row, dict), f"path row is not an object: {label}")
        path = row.get("path")
        require(isinstance(path, str) and path not in seen, f"duplicate/malformed path row: {label}")
        seen.add(path)
        require(isinstance(row.get("bytes"), int) and row["bytes"] >= 0, f"invalid byte count: {label}")
        require_sha(row.get("sha256"), f"{label}:{path}")
        result.append({"path": path, "bytes": row["bytes"], "sha256": row["sha256"]})
    return result


def contains_value(value: Any, needle: Any) -> bool:
    if value == needle:
        return True
    if isinstance(value, dict):
        return any(contains_value(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(contains_value(item, needle) for item in value)
    return False


def require_control_pair(
    private: Path,
    public: Path,
    expected: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    private_data = require_ident(private, expected, f"private {label}")
    public_data = require_ident(public, expected, f"public {label}")
    require(private_data == public_data, f"control mirrors differ: {label}")
    value = parse_json_bytes(private_data, label)
    require(value.get("schema") == expected["schema"], f"control schema drift: {label}")
    observed_result = value.get("result")
    if observed_result is None:
        observed_result = value.get("structure_and_formula_validation", {}).get("result")
    require(observed_result == expected["result"], f"control result drift: {label}")
    return value


def verify_current_source(roots: Roots) -> dict[str, Any]:
    queue_path = roots.canonical / "controls" / "EGA_CANON_QUEUE.json"
    regular(queue_path, "current canonical queue")
    require(queue_path.stat().st_size <= 2_000_000, "current canonical queue exceeds the bounded size limit")
    queue_data = queue_path.read_bytes()
    queue = parse_json_bytes(queue_data, "current canonical queue")
    require(queue.get("schema") == "ega_central_canon_queue_v1", "canonical queue schema drift")
    require(
        isinstance(queue.get("id"), str)
        and re.fullmatch(r"EGA-CANON-QUEUE-[0-9]{8}-R[0-9]+", queue["id"]) is not None,
        "canonical queue ID drift",
    )

    source_path = roots.canonical / CURRENT_SOURCE["path"]
    raw = require_ident(source_path, CURRENT_SOURCE, "current EGA II source")
    require(not raw.startswith(b"\xef\xbb\xbf"), "canonical source has a BOM")
    require(b"\r" not in raw and raw.endswith(b"\n"), "canonical source is not final-LF LF-only")
    text = raw.decode("utf-8")
    lines = text.splitlines()
    require(len(text) == CURRENT_SOURCE["characters"], "canonical character count drift")
    require(len(lines) == CURRENT_SOURCE["lf_lines"], "canonical line count drift")
    unit_text = "\n".join(lines[1684:1780]) + "\n"
    unit = unit_text.encode("utf-8")
    require(
        {
            "bytes": len(unit),
            "characters": len(unit_text),
            "lf_lines": unit.count(b"\n"),
            "sha256": digest(unit),
        }
        == {key: SOURCE_UNIT[key] for key in ("bytes", "characters", "lf_lines", "sha256")},
        "R39 source-unit identity drift",
    )
    prefix_text = "\n".join(lines[:1780]) + "\n"
    prefix = prefix_text.encode("utf-8")
    require(
        {
            "bytes": len(prefix),
            "characters": len(prefix_text),
            "lf_lines": prefix.count(b"\n"),
            "sha256": digest(prefix),
        }
        == {
            "bytes": SOURCE_UNIT["admitted_prefix_bytes"],
            "characters": SOURCE_UNIT["admitted_prefix_characters"],
            "lf_lines": SOURCE_UNIT["admitted_prefix_lf_lines"],
            "sha256": SOURCE_UNIT["admitted_prefix_sha256"],
        },
        "current admitted-prefix identity drift",
    )
    require(lines[1683] == "", "canonical line1684 is no longer blank")
    require(lines[1684] == r"\begin{lemma}[2.2.2]", "R39 source start boundary drift")
    require(lines[1779] == r"\end{proof}", "R39 source end boundary drift")
    require(lines[1780] == "", "canonical line1781 is no longer blank")
    require(lines[1781] == r"\begin{env}[2.2.7]", "next source boundary drift")
    return {
        "queue": {"path": "controls/EGA_CANON_QUEUE.json", "id": queue["id"], **ident_bytes(queue_data)},
        "source": dict(CURRENT_SOURCE),
        "unit": {key: SOURCE_UNIT[key] for key in ("lines", "bytes", "characters", "lf_lines", "sha256")},
        "admitted_prefix": {
            "lines": "1-1780",
            "bytes": SOURCE_UNIT["admitted_prefix_bytes"],
            "characters": SOURCE_UNIT["admitted_prefix_characters"],
            "lf_lines": SOURCE_UNIT["admitted_prefix_lf_lines"],
            "sha256": SOURCE_UNIT["admitted_prefix_sha256"],
        },
    }


def run_current_validator(roots: Roots) -> dict[str, Any]:
    validator_path = roots.private / SEALED["validator"]["path"]
    require_ident(validator_path, SEALED["validator"], "corrected current-authority validator")
    command = [
        sys.executable,
        str(validator_path),
        str(roots.canonical / CURRENT_SOURCE["path"]),
        "--candidate",
        str(roots.private / SEALED["candidate"]["path"]),
        "--private-target",
        str(roots.private / "ega" / "II" / "c2s1.tex"),
        "--public-target",
        str(roots.repo / "source" / "c2s1.tex"),
        "--rebase-control",
        str(roots.private / HISTORICAL_REBASE["private"]),
        "--reseal-control",
        str(roots.private / SEALED["reseal_control"]["private"]),
    ]
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=roots.private,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout)[-2_000:].decode("utf-8", errors="replace")
        raise RuntimeError(f"current-authority validator rejected the inputs: {detail.strip()}")
    result = parse_json_bytes(completed.stdout, "current-authority validator output")
    require(result.get("result") == SEALED["validator"]["result"], "current validator result drift")
    require(result.get("candidate", {}).get("sha256") == SEALED["candidate"]["sha256"], "validator candidate binding drift")
    require(result.get("prospective_target", {}).get("sha256") == SEALED["postimage"]["sha256"], "validator postimage binding drift")
    require(result.get("target_preimage", {}).get("sha256") == R38_TARGET["sha256"], "validator preimage binding drift")
    return result


def verify_translation_inputs(roots: Roots) -> dict[str, Any]:
    require_sealed_bindings()
    source = verify_current_source(roots)
    candidate = require_ident(
        roots.private / SEALED["candidate"]["path"],
        SEALED["candidate"],
        "corrected sealed R39 candidate",
    )
    require(not candidate.startswith(b"\xef\xbb\xbf"), "R39 candidate has a BOM")
    require(b"\r" not in candidate and candidate.endswith(b"\n"), "R39 candidate is not final-LF LF-only")
    candidate_text = candidate.decode("utf-8")
    require(len(candidate_text) == SEALED["candidate"]["characters"], "candidate character count drift")
    require(candidate.count(b"\n") == SEALED["candidate"]["lf_lines"], "candidate LF count drift")
    require("법 동치류" not in candidate_text, "rejected spaced wording remains in corrected R39 candidate")

    private_target = require_ident(
        roots.private / "ega" / "II" / "c2s1.tex", R38_TARGET, "private R38 target preimage"
    )
    public_target = require_ident(
        roots.repo / "source" / "c2s1.tex", R38_TARGET, "public R38 target preimage"
    )
    require(private_target == public_target, "R38 target preimages differ")
    require(b"\r" not in private_target and private_target.endswith(b"\n"), "R38 target is not final-LF LF-only")
    require(private_target.count(b"\n") == R38_TARGET["lf_lines"], "R38 target LF count drift")

    historical_admission = require_control_pair(
        roots.private / HISTORICAL_ADMISSION["private"],
        roots.repo / HISTORICAL_ADMISSION["public"],
        HISTORICAL_ADMISSION,
        "historical R39 admission",
    )
    historical_rebase = require_control_pair(
        roots.private / HISTORICAL_REBASE["private"],
        roots.repo / HISTORICAL_REBASE["public"],
        HISTORICAL_REBASE,
        "historical R39 canonical rebase",
    )
    require(
        historical_admission.get("candidate", {}).get("sha256") != SEALED["candidate"]["sha256"],
        "corrected candidate was not additively resealed over the historical admission",
    )
    require(
        historical_rebase.get("candidate", {}).get("sha256") != SEALED["candidate"]["sha256"],
        "corrected candidate unexpectedly equals the historical rebase candidate",
    )

    reseal_data = require_ident(
        roots.private / SEALED["reseal_control"]["private"],
        SEALED["reseal_control"],
        "corrected R39 reseal",
    )
    reseal = parse_json_bytes(reseal_data, "corrected R39 reseal")
    require(reseal.get("schema") == SEALED["reseal_control"]["schema"], "corrected reseal schema drift")
    require(reseal.get("result") == SEALED["reseal_control"]["result"], "corrected reseal result drift")
    public_reseal = roots.repo / SEALED["reseal_control"]["public"]
    require(not public_reseal.exists() and not public_reseal.is_symlink(), "corrected R39 reseal public mirror already exists")
    for needle, label in (
        (SEALED["candidate"]["sha256"], "candidate"),
        (SEALED["postimage"]["sha256"], "postimage"),
        (CURRENT_SOURCE["sha256"], "current source"),
        (SOURCE_UNIT["sha256"], "source unit"),
    ):
        require(contains_value(reseal, needle), f"reseal control does not bind {label}")

    receipt_data = require_ident(
        roots.private / SEALED["validator_receipt"]["path"],
        SEALED["validator_receipt"],
        "corrected current-validator receipt",
    )
    receipt = parse_json_bytes(receipt_data, "corrected current-validator receipt")
    require(receipt.get("schema") == SEALED["validator_receipt"]["schema"], "validator receipt schema drift")
    require(receipt.get("result") == SEALED["validator_receipt"]["result"], "validator receipt result drift")
    for needle, label in (
        (SEALED["validator"]["sha256"], "validator"),
        (SEALED["candidate"]["sha256"], "candidate"),
        (SEALED["postimage"]["sha256"], "postimage"),
        (SEALED["reseal_control"]["sha256"], "reseal control"),
    ):
        require(contains_value(receipt, needle), f"validator receipt does not bind {label}")
    public_validator_receipt = roots.repo / "evidence" / "controls" / Path(SEALED["validator_receipt"]["path"]).name
    require(not public_validator_receipt.exists() and not public_validator_receipt.is_symlink(), "corrected current-validator public mirror already exists")

    separator = b"\n" + candidate
    require(ident_bytes(separator) == SEALED["separator_plus_candidate"], "separator-plus-candidate identity drift")
    postimage = private_target + separator
    require(ident_bytes(postimage) == {"bytes": SEALED["postimage"]["bytes"], "sha256": SEALED["postimage"]["sha256"]}, "prospective target identity drift")
    postimage_text = postimage.decode("utf-8")
    require(len(postimage_text) == SEALED["postimage"]["characters"], "prospective target character count drift")
    require(postimage.count(b"\n") == SEALED["postimage"]["lf_lines"], "prospective target LF count drift")
    lines = postimage_text.splitlines()
    require(lines[R38_TARGET["lf_lines"]] == "", "prospective separator line drift")
    require(lines[R38_TARGET["lf_lines"] + 1] == r"\begin{lemma}[2.2.2]", "prospective candidate start drift")
    require(lines[-1] == r"\end{proof}", "prospective candidate end drift")

    validator = run_current_validator(roots)
    return {
        "source": source,
        "candidate": {
            "private_working_path": SEALED["candidate"]["path"],
            "public_integrated_path": "source/c2s1.tex",
            "public_integrated_locator": "target lines1710-1809 after separator line1709",
            **{key: SEALED["candidate"][key] for key in ("bytes", "characters", "lf_lines", "sha256")},
        },
        "historical_admission": {"bytes": HISTORICAL_ADMISSION["bytes"], "sha256": HISTORICAL_ADMISSION["sha256"]},
        "historical_rebase": {"bytes": HISTORICAL_REBASE["bytes"], "sha256": HISTORICAL_REBASE["sha256"]},
        "reseal_control": {"bytes": SEALED["reseal_control"]["bytes"], "sha256": SEALED["reseal_control"]["sha256"]},
        "validator": {"bytes": SEALED["validator"]["bytes"], "sha256": SEALED["validator"]["sha256"], "result": validator["result"]},
        "validator_receipt": {"bytes": SEALED["validator_receipt"]["bytes"], "sha256": SEALED["validator_receipt"]["sha256"]},
        "preimage": dict(R38_TARGET),
        "postimage": postimage,
    }


def verify_r38_public_closure(roots: Roots) -> dict[str, Any]:
    release = roots.repo / "release" / VERSION
    directory(release, "R38 release directory")
    expected_release = {
        *(row["name"] for row in R38_ARTIFACTS),
        "PACKAGE_RECEIPT.json",
        "PORTABLE_BUILD_REPLAY.json",
        "GITHUB_PUBLICATION_RECEIPT.json",
        "ZENODO_PUBLICATION_RECEIPT.json",
    }
    found = {item.name for item in release.iterdir() if item.is_file() and not item.is_symlink()}
    require(found == expected_release, "R38 release inventory is not exact")
    for row in R38_ARTIFACTS:
        require_ident(release / row["name"], row, f"R38 release asset {row['name']}")
    require_ident(release / "PACKAGE_RECEIPT.json", R38_PACKAGE, "R38 package receipt")
    require_ident(release / "PORTABLE_BUILD_REPLAY.json", R38_PORTABLE, "R38 portable replay receipt")

    github_data = require_ident(roots.repo / "github-receipt-r38.json", R38_GITHUB_RECEIPT, "R38 GitHub receipt")
    require_ident(release / "GITHUB_PUBLICATION_RECEIPT.json", R38_GITHUB_RECEIPT, "R38 GitHub receipt mirror")
    require(github_data == (release / "GITHUB_PUBLICATION_RECEIPT.json").read_bytes(), "R38 GitHub receipt mirrors differ")
    github = parse_json_bytes(github_data, "R38 GitHub receipt")
    require(github.get("schema") == "ag-ko-github-publication-receipt-v4", "R38 GitHub receipt schema drift")
    require(github.get("version") == VERSION, "R38 GitHub receipt version drift")
    require(github.get("repository") == R38_REPOSITORY, "R38 GitHub repository drift")
    require(github.get("repository_public_active") is True, "R38 GitHub repository is not proven public/active")
    require(github.get("main_commit") == R38_ARTIFACT_COMMIT, "R38 GitHub main commit drift")
    require(github.get("artifact_commit") == R38_ARTIFACT_COMMIT, "R38 GitHub artifact commit drift")
    require(github.get("artifact_parent") == R38_ARTIFACT_PARENT, "R38 GitHub artifact parent drift")
    require(github.get("artifact_tree_sha") == R38_ARTIFACT_TREE, "R38 GitHub artifact tree drift")
    require(github.get("tag") == R38_TAG, "R38 GitHub tag drift")
    require(github.get("annotated_tag_object") == R38_ANNOTATED_TAG, "R38 annotated tag drift")
    require(github.get("tag_peels_to_commit") == R38_ARTIFACT_COMMIT, "R38 tag peel drift")
    require(github.get("release_url") == R38_RELEASE, "R38 release URL drift")
    require(github.get("credentials_present") is False, "R38 GitHub receipt contains credentials")
    require(github.get("result") == "PASS_GITHUB_PUBLICATION_AND_ANONYMOUS_BYTE_REPLAY", "R38 GitHub result drift")
    expected_github = [dict(row, anonymous_byte_identical=True) for row in R38_ARTIFACTS]
    require(normalized_inventory(github.get("assets"), "anonymous_byte_identical", "R38 GitHub assets") == expected_github, "R38 GitHub asset replay drift")

    zenodo_data = require_ident(roots.repo / "receipt-r38.json", R38_ZENODO_RECEIPT, "R38 Zenodo receipt")
    require_ident(release / "ZENODO_PUBLICATION_RECEIPT.json", R38_ZENODO_RECEIPT, "R38 Zenodo receipt mirror")
    require(zenodo_data == (release / "ZENODO_PUBLICATION_RECEIPT.json").read_bytes(), "R38 Zenodo receipt mirrors differ")
    zenodo = parse_json_bytes(zenodo_data, "R38 Zenodo receipt")
    require(zenodo.get("schema") == "ag-ko-zenodo-publication-receipt-v3", "R38 Zenodo receipt schema drift")
    require(zenodo.get("version") == VERSION, "R38 Zenodo receipt version drift")
    require(zenodo.get("record_id") == R38_RECORD_ID, "R38 Zenodo record drift")
    require(zenodo.get("exact_doi") == R38_EXACT_DOI, "R38 exact DOI drift")
    require(zenodo.get("concept_doi") == R38_CONCEPT_DOI, "R38 concept DOI drift")
    require(zenodo.get("record_url") == R38_ZENODO, "R38 Zenodo URL drift")
    require(zenodo.get("doi_resolution") == {"status_code": 200, "final_url": R38_ZENODO}, "R38 DOI resolution proof drift")
    require(zenodo.get("metadata", {}).get("access") == "public/open", "R38 Zenodo access is not public/open")
    require(zenodo.get("credentials_present") is False, "R38 Zenodo receipt contains credentials")
    require(zenodo.get("result") == "PASS_ZENODO_PUBLICATION_AND_ANONYMOUS_BYTE_REPLAY", "R38 Zenodo result drift")
    expected_zenodo = [dict(row, byte_identical=True) for row in R38_ARTIFACTS]
    require(normalized_inventory(zenodo.get("anonymous_public_readback"), "byte_identical", "R38 Zenodo assets") == expected_zenodo, "R38 Zenodo asset replay drift")

    private_control_path = roots.private / "controls" / "R38_PUBLIC_CLOSURE.json"
    public_control_path = roots.repo / "evidence" / "controls" / "R38_PUBLIC_CLOSURE.json"
    regular(private_control_path, "private R38 closure control")
    regular(public_control_path, "public R38 closure control")
    private_control_data = private_control_path.read_bytes()
    require(private_control_data == public_control_path.read_bytes(), "R38 closure control mirrors differ")
    closure = parse_json_bytes(private_control_data, "R38 closure control")
    require(closure.get("schema") == "ag-ko-r38-minimal-public-closure-v1", "R38 closure schema drift")
    require(closure.get("version") == VERSION and closure.get("result") == R38_PUBLIC_STATUS, "R38 closure result drift")
    require(closure.get("target", {}).get("sha256") == R38_TARGET["sha256"], "R38 closure target binding drift")
    require(closure.get("source", {}).get("whole_sha256") == CURRENT_SOURCE["sha256"], "R38 closure source binding drift")
    require(normalized_inventory(closure.get("artifacts"), None, "R38 closure artifacts") == list(R38_ARTIFACTS), "R38 closure artifact inventory drift")
    github_ref = closure.get("github", {}).get("receipt", {})
    zenodo_ref = closure.get("zenodo", {}).get("receipt", {})
    require(github_ref == {"path": "github-receipt-r38.json", **R38_GITHUB_RECEIPT}, "R38 closure GitHub receipt binding drift")
    require(zenodo_ref == {"path": "receipt-r38.json", **R38_ZENODO_RECEIPT}, "R38 closure Zenodo receipt binding drift")
    require(closure.get("github", {}).get("artifact_commit") == R38_ARTIFACT_COMMIT, "R38 closure GitHub commit drift")
    require(closure.get("github", {}).get("anonymous_byte_replay") == "PASS_4_OF_4", "R38 closure GitHub replay drift")
    require(closure.get("zenodo", {}).get("access") == "public/open", "R38 closure Zenodo access drift")
    require(closure.get("zenodo", {}).get("anonymous_byte_replay") == "PASS_4_OF_4", "R38 closure Zenodo replay drift")

    commit_receipt_path = roots.private / "controls" / "R38_CLOSURE_COMMIT_RECEIPT.json"
    commit_receipt_data = commit_receipt_path.read_bytes() if commit_receipt_path.exists() else b""
    regular(commit_receipt_path, "R38 closure commit receipt")
    commit_receipt = parse_json_bytes(commit_receipt_data, "R38 closure commit receipt")
    require(commit_receipt.get("schema") == "ag-ko-r38-closure-commit-receipt-v1", "R38 closure commit schema drift")
    require(commit_receipt.get("version") == VERSION, "R38 closure commit version drift")
    require(commit_receipt.get("repository") == R38_REPOSITORY, "R38 closure repository drift")
    require(commit_receipt.get("artifact_preimage") == R38_ARTIFACT_COMMIT, "R38 closure artifact preimage drift")
    closure_commit = commit_receipt.get("closure_commit")
    closure_tree = commit_receipt.get("closure_tree")
    require(isinstance(closure_commit, str) and GIT_RE.fullmatch(closure_commit) is not None, "malformed R38 closure commit")
    require(isinstance(closure_tree, str) and GIT_RE.fullmatch(closure_tree) is not None, "malformed R38 closure tree")
    require(commit_receipt.get("closure_parent") == R38_ARTIFACT_COMMIT, "R38 closure parent drift")
    require(commit_receipt.get("path_inventory_exact") == list(EXPECTED_CLOSURE_PATHS), "R38 closure path inventory drift")
    require(
        commit_receipt.get("push") == "EXACT_LEASE_OR_OBSERVED_EXACT_POSTIMAGE",
        "R38 closure push proof drift",
    )
    anonymous = commit_receipt.get("anonymous_public_readback", {})
    require(anonymous.get("main") == closure_commit, "R38 closure anonymous main drift")
    require(anonymous.get("parent") == R38_ARTIFACT_COMMIT, "R38 closure anonymous parent drift")
    require(anonymous.get("tree") == closure_tree, "R38 closure anonymous tree drift")
    require(
        anonymous.get("result")
        == "PASS_ANONYMOUS_MAIN_PARENT_TREE_EXACT_OVERLAY_AND_ALL_CHANGED_RAW_BYTES",
        "R38 closure anonymous result drift",
    )
    overlay = anonymous.get("tree_overlay", {})
    require(overlay.get("artifact_tree") == R38_ARTIFACT_TREE, "R38 closure overlay preimage tree drift")
    require(overlay.get("closure_tree") == closure_tree, "R38 closure overlay postimage tree drift")
    require(overlay.get("changed_paths_exact") == list(EXPECTED_CLOSURE_PATHS), "R38 closure overlay inventory drift")
    require(
        overlay.get("result") == "PASS_EXACT_FIVE_PATH_OVERLAY_ON_BOUND_ARTIFACT_TREE",
        "R38 closure overlay result drift",
    )
    require(commit_receipt.get("credentials_present") is False, "R38 closure receipt contains credentials")
    require(commit_receipt.get("result") == "PASS_R38_NARROW_CLOSURE_COMMIT_AND_ANONYMOUS_REPLAY", "R38 closure commit result drift")

    changed = normalized_paths(commit_receipt.get("changed_paths"), "R38 closure changed paths")
    require([row["path"] for row in changed] == list(EXPECTED_CLOSURE_PATHS), "R38 closure changed-path ordering drift")
    replay = normalized_paths(anonymous.get("raw"), "R38 closure anonymous raw replay")
    require(replay == changed, "R38 closure changed paths and anonymous replay differ")
    for row in changed:
        require_ident(roots.repo.joinpath(*Path(row["path"]).parts), row, f"R38 closure local path {row['path']}")
    closure_row = next(row for row in changed if row["path"] == "evidence/controls/R38_PUBLIC_CLOSURE.json")
    require(closure_row == {"path": closure_row["path"], **ident(public_control_path)}, "R38 closure control is not commit-bound")

    journal_path = roots.private / "controls" / "R38_FRESH_CLOSURE_TRANSACTION.json"
    journal = parse_json(journal_path, "R38 closure transaction journal")
    require(journal.get("schema") == "ag-ko-r38-fresh-closure-transaction-v1", "R38 closure journal schema drift")
    require(journal.get("status") == "COMMITTED", "R38 closure journal is not committed")
    publication = journal.get("publication", {})
    require(publication.get("result") == "PASS", "R38 closure journal publication status drift")
    require(publication.get("closure_commit") == closure_commit, "R38 closure journal commit drift")
    require(publication.get("parent") == R38_ARTIFACT_COMMIT, "R38 closure journal parent drift")
    require(publication.get("tree") == closure_tree, "R38 closure journal tree drift")
    require(publication.get("receipt", {}).get("sha256") == digest(commit_receipt_data), "R38 closure journal receipt binding drift")

    publication_journal_path = roots.private / "controls" / "R38_PUBLICATION_TRANSACTION.json"
    publication_journal = parse_json(publication_journal_path, "R38 publication transaction journal")
    require(publication_journal.get("schema") == "ag-ko-r38-publication-transaction-v1", "R38 publication journal schema drift")
    require(publication_journal.get("version") == VERSION, "R38 publication journal version drift")
    require(publication_journal.get("record_id") == R38_RECORD_ID, "R38 publication journal record drift")
    require(publication_journal.get("exact_doi") == R38_EXACT_DOI, "R38 publication journal DOI drift")
    require(publication_journal.get("concept_doi") == R38_CONCEPT_DOI, "R38 publication journal concept drift")
    require(publication_journal.get("repository") == R38_REPOSITORY, "R38 publication journal repository drift")
    require(publication_journal.get("tag") == R38_TAG, "R38 publication journal tag drift")
    require(publication_journal.get("credentials_present") is False, "R38 publication journal contains credentials")
    require(publication_journal.get("phase") == "complete", "R38 publication journal has not reached complete")
    history = publication_journal.get("history")
    require(isinstance(history, list) and len(history) == len(PUBLICATION_PHASES), "R38 publication journal phase cardinality drift")
    require(publication_journal.get("sequence") == len(history) - 1, "R38 publication journal sequence drift")
    previous: str | None = None
    for index, event in enumerate(history):
        require(isinstance(event, dict), "R38 publication journal event is not an object")
        require(
            set(event) == {"sequence", "phase", "recorded_at_utc", "previous_event_sha256", "evidence", "event_sha256"},
            "R38 publication journal event schema drift",
        )
        require(event.get("sequence") == index, "R38 publication journal event sequence drift")
        require(event.get("phase") == PUBLICATION_PHASES[index], "R38 publication journal phase order drift")
        require(event.get("previous_event_sha256") == previous, "R38 publication journal chain pointer drift")
        try:
            stamp = datetime.fromisoformat(str(event.get("recorded_at_utc")))
        except ValueError as exc:
            raise RuntimeError("R38 publication journal timestamp drift") from exc
        require(stamp.tzinfo is not None, "R38 publication journal timestamp lacks timezone")
        without_hash = dict(event)
        observed_hash = without_hash.pop("event_sha256")
        canonical = (json.dumps(without_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        require(observed_hash == digest(canonical), "R38 publication journal event hash drift")
        previous = observed_hash
    complete_evidence = history[-1].get("evidence", {})
    require(contains_value(complete_evidence, closure_commit), "R38 complete event does not bind closure commit")
    require(contains_value(complete_evidence, digest(commit_receipt_data)), "R38 complete event does not bind closure receipt")
    require(contains_value(publication_journal, R38_GITHUB_RECEIPT["sha256"]), "R38 journal does not bind GitHub receipt")
    require(contains_value(publication_journal, R38_ZENODO_RECEIPT["sha256"]), "R38 journal does not bind Zenodo receipt")

    closure_identity = ident_bytes(private_control_data)
    # The deliberately narrow R38 closure commit changes only five proof files;
    # the broader aliases remain at their exact R37 public snapshot until this
    # R39 local integration transaction advances them coherently in one step.
    for name in PUBLIC_ALIASES:
        path = roots.repo / "evidence" / name
        value = parse_json(path, f"pre-R39 public alias {name}")
        key, expected = PUBLIC_SCHEMAS[name]
        require(value.get(key) == expected, f"public alias schema drift: {name}")
        require(value.get("version") == PREVIOUS_VERSION, f"public alias is not the exact pre-R39 R37 snapshot: {name}")
        require("public_r38" not in value, f"public alias already has an uncoordinated R38 closure binding: {name}")
    for name in PRIVATE_SCHEMAS:
        value = parse_json(roots.private / name, f"pre-R39 private alias {name}")
        key, expected = PRIVATE_SCHEMAS[name]
        require(value.get(key) == expected, f"private alias schema drift: {name}")
        require("public_r38" not in value, f"private alias already has an uncoordinated R38 closure binding: {name}")

    return {
        "closure_control": {"bytes": closure_identity["bytes"], "sha256": closure_identity["sha256"]},
        "github_receipt": dict(R38_GITHUB_RECEIPT),
        "zenodo_receipt": dict(R38_ZENODO_RECEIPT),
        "closure_commit_receipt": {**ident_bytes(commit_receipt_data), "closure_commit": closure_commit, "closure_tree": closure_tree},
        "journal": {**ident(journal_path), "status": journal["status"], "publication": publication["result"]},
        "publication_journal": {**ident(publication_journal_path), "phase": publication_journal["phase"], "sequence": publication_journal["sequence"]},
    }


def r38_public_binding(closure: Mapping[str, Any], *, public: bool) -> dict[str, Any]:
    control_path = ("evidence/controls/" if public else "controls/") + "R38_PUBLIC_CLOSURE.json"
    return {
        "status": R38_PUBLIC_STATUS,
        "version": VERSION,
        "control": {
            "path": control_path,
            **dict(closure["closure_control"]),
            "private_public_mirrors_exact": True,
        },
        "reader": dict(R38_READER),
        "github": {
            "artifact_commit": R38_ARTIFACT_COMMIT,
            "artifact_parent": R38_ARTIFACT_PARENT,
            "artifact_tree": R38_ARTIFACT_TREE,
            "annotated_tag_object": R38_ANNOTATED_TAG,
            "tag": R38_TAG,
            "release": R38_RELEASE,
            "receipt": {"path": "github-receipt-r38.json", **dict(R38_GITHUB_RECEIPT)},
        },
        "zenodo": {
            "record_id": R38_RECORD_ID,
            "exact_doi": R38_EXACT_DOI,
            "exact_doi_url": "https://doi.org/" + R38_EXACT_DOI,
            "concept_doi": R38_CONCEPT_DOI,
            "concept_doi_url": "https://doi.org/" + R38_CONCEPT_DOI,
            "record": R38_ZENODO,
            "predecessor_record_id": R38_PREDECESSOR_RECORD_ID,
            "predecessor_exact_doi": R38_PREDECESSOR_EXACT_DOI,
            "receipt": {"path": "receipt-r38.json", **dict(R38_ZENODO_RECEIPT)},
        },
        "public_artifacts": [dict(row) for row in R38_ARTIFACTS],
        "package": {"path": f"release/{VERSION}/PACKAGE_RECEIPT.json", **dict(R38_PACKAGE)},
        "portable_replay": {
            "path": f"release/{VERSION}/PORTABLE_BUILD_REPLAY.json",
            **dict(R38_PORTABLE),
        },
        "coverage": (
            "Complete Korean EGA 0_I and EGA I; complete EGA II programme/table of contents "
            "and main text contiguously through §2.2.1 / canonical lines1-1683."
        ),
        "ega_ii_status": "active_incomplete",
        "next_source": "canonical line1685 / environment2.2.2",
    }


def public_candidate_ref() -> dict[str, Any]:
    return {
        "path": "source/c2s1.tex",
        "locator": "exact integrated target slice lines1710-1809 after separator line1709",
        "role": "sealed R39 candidate recoverable as an exact public-target slice",
        **{key: SEALED["candidate"][key] for key in ("bytes", "characters", "lf_lines", "sha256")},
    }


def integration_ref(control_identity: Mapping[str, Any], *, public: bool) -> dict[str, Any]:
    return {
        "status": R39_STATUS,
        "control": {
            "path": ("evidence/controls/" if public else "controls/") + "R39_TRANSLATION_INTEGRATION.json",
            **dict(control_identity),
            "private_public_mirrors_exact": True,
        },
        "source": {
            "path": CURRENT_SOURCE["path"],
            "whole_bytes": CURRENT_SOURCE["bytes"],
            "whole_lf_lines": CURRENT_SOURCE["lf_lines"],
            "whole_sha256": CURRENT_SOURCE["sha256"],
            "admitted_lines": "1-1780",
            "admitted_bytes": SOURCE_UNIT["admitted_prefix_bytes"],
            "admitted_sha256": SOURCE_UNIT["admitted_prefix_sha256"],
        },
        "unit": {key: SOURCE_UNIT[key] for key in ("lines", "bytes", "characters", "lf_lines", "sha256")},
        "candidate": public_candidate_ref() if public else dict(SEALED["candidate"]),
        "target": {
            "private_path": "ega/II/c2s1.tex",
            "public_path": "source/c2s1.tex",
            **dict(SEALED["postimage"]),
            "separator_line": 1_709,
            "candidate_target_lines": "1710-1809",
            "private_public_exact": True,
        },
        "reseal": {
            "path": ("evidence/controls/" if public else "controls/")
            + Path(SEALED["reseal_control"]["private"]).name,
            "bytes": SEALED["reseal_control"]["bytes"],
            "sha256": SEALED["reseal_control"]["sha256"],
            "result": SEALED["reseal_control"]["result"],
        },
        "gates": {
            "corrected_reseal": "PASS",
            "current_authority_validator": "PASS",
            "r38_public_closure": "PASS",
            "exact_mirror_integration": "PASS",
            "build": "PENDING",
            "pdf_qa": "PENDING",
            "package_portable_replay": "PENDING",
            "publication_anonymous_readback": "PENDING",
        },
        "ega_ii_status": "active_incomplete",
        "next_source": NEXT_SOURCE,
    }


def build_control(
    integrated_at: str,
    translation: Mapping[str, Any],
    closure: Mapping[str, Any],
    preimage_snapshot_sha256: str,
) -> bytes:
    value = {
        "schema": "agko-r39-translation-integration-v1",
        "time": integrated_at,
        "precision": "second",
        "scope": "EGA II canonical lines1685-1780 / environments2.2.2-2.2.6",
        "authority": {
            "whole": dict(CURRENT_SOURCE),
            "unit": {key: SOURCE_UNIT[key] for key in ("lines", "bytes", "characters", "lf_lines", "sha256")},
            "admitted_prefix": {
                "lines": "1-1780",
                "bytes": SOURCE_UNIT["admitted_prefix_bytes"],
                "characters": SOURCE_UNIT["admitted_prefix_characters"],
                "lf_lines": SOURCE_UNIT["admitted_prefix_lf_lines"],
                "sha256": SOURCE_UNIT["admitted_prefix_sha256"],
            },
            "queue": dict(translation["source"]["queue"]),
        },
        "historical_inputs": {
            "admission": {
                "private_path": HISTORICAL_ADMISSION["private"],
                "public_path": HISTORICAL_ADMISSION["public"],
                "bytes": HISTORICAL_ADMISSION["bytes"],
                "sha256": HISTORICAL_ADMISSION["sha256"],
                "status": "preserved_historical_and_superseded_for_candidate_identity",
            },
            "canonical_rebase": {
                "private_path": HISTORICAL_REBASE["private"],
                "public_path": HISTORICAL_REBASE["public"],
                "bytes": HISTORICAL_REBASE["bytes"],
                "sha256": HISTORICAL_REBASE["sha256"],
                "status": "preserved_historical_and_superseded_for_candidate_identity",
            },
        },
        "corrected_reseal": {
            "private_path": SEALED["reseal_control"]["private"],
            "public_path": SEALED["reseal_control"]["public"],
            "bytes": SEALED["reseal_control"]["bytes"],
            "sha256": SEALED["reseal_control"]["sha256"],
            "result": SEALED["reseal_control"]["result"],
        },
        "current_validator": {
            "path": SEALED["validator"]["path"],
            "bytes": SEALED["validator"]["bytes"],
            "sha256": SEALED["validator"]["sha256"],
            "execution_result": SEALED["validator"]["result"],
            "receipt": {
                "private_path": SEALED["validator_receipt"]["path"],
                "public_path": "evidence/controls/" + Path(SEALED["validator_receipt"]["path"]).name,
                "bytes": SEALED["validator_receipt"]["bytes"],
                "sha256": SEALED["validator_receipt"]["sha256"],
                "schema": SEALED["validator_receipt"]["schema"],
                "result": SEALED["validator_receipt"]["result"],
            },
        },
        "candidate": dict(SEALED["candidate"]),
        "sealed_preimage": {
            "private_path": "ega/II/c2s1.tex",
            "public_path": "source/c2s1.tex",
            **dict(R38_TARGET),
            "private_public_exact": True,
            "state": "exact R38 public source mirrors",
        },
        "r38_publication_prerequisite": {
            "status": R38_PUBLIC_STATUS,
            "closure_control": dict(closure["closure_control"]),
            "github_receipt": dict(closure["github_receipt"]),
            "zenodo_receipt": dict(closure["zenodo_receipt"]),
            "closure_commit_receipt": dict(closure["closure_commit_receipt"]),
            "closure_journal": dict(closure["journal"]),
            "publication_journal": dict(closure["publication_journal"]),
            "verified_offline_from_exact_anonymous_readback_receipts": True,
        },
        "final_integration": {
            "method": "sealed R38 preimage + exactly one LF + corrected sealed R39 candidate",
            "private_path": "ega/II/c2s1.tex",
            "public_path": "source/c2s1.tex",
            **dict(SEALED["postimage"]),
            "separator_line": 1_709,
            "candidate_target_lines": "1710-1809",
            "private_public_exact": True,
            "sealed_prefix_exact": True,
            "target_tail_equal_corrected_candidate": True,
        },
        "source_queries": {
            "destination_task": "01a047ab-fc94-7120-af1d-5701ba37aacd",
            "lines": [1_709, 1_738],
            "status": "already delivered and nonblocking; no French source byte changed",
        },
        "state": {
            "corrected_reseal": "PASS",
            "current_authority_validation": "PASS",
            "r38_public_closure": "PASS",
            "exact_mirror_integration": "PASS",
            "build": "PENDING",
            "extraction": "PENDING",
            "rendered_pdf_qa": "PENDING",
            "package_and_portable_replay": "PENDING",
            "publication_and_anonymous_readback": "PENDING",
            "ega_ii": "active_incomplete",
        },
        "transaction": {
            "journal": "controls/R39_INTEGRATION_TRANSACTION.json",
            "fresh_preimage_snapshot_sha256": preimage_snapshot_sha256,
            "all_postimages_computed_before_first_write": True,
            "rollback_on_failure": True,
        },
        "ledger_records": {
            "decision": "AGKO-D188",
            "evidence": "AGKO-E-R39-INTEGRATION-20260906",
            "hard": "AGKO-H163",
            "unit": "AGKO-EGA2-S1-R39-INTEGRATED-R1",
        },
        "result": R39_STATUS,
        "next": "Refresh cumulative declarations through canonical line1780, then run the serialized R39 build, extraction, rendered QA, packaging, portable replay and same-lineage publication gates; continue source preparation at line1782 without reopening sealed correct units.",
    }
    data = json_bytes(value)
    require(PRIVATE_PATH_RE.search(data.decode("utf-8")) is None, "integration control contains a private absolute path")
    return data


def update_cursor(
    original: dict[str, Any], integrated_at: str, ref: Mapping[str, Any], closure: Mapping[str, Any]
) -> dict[str, Any]:
    key, expected = PRIVATE_SCHEMAS["cursor.json"]
    require(original.get(key) == expected, "private cursor schema drift")
    data = copy.deepcopy(original)
    data["updated"] = integrated_at
    data["completed_through"] = (
        "EGA 0_I and EGA I complete; EGA II programme/table of contents complete; "
        "EGA II main text translated contiguously through 2.2.6 / canonical lines1-1780. "
        "EGA II and the full corpus remain incomplete."
    )
    data["source"] = {
        "path": CURRENT_SOURCE["path"],
        "bytes": CURRENT_SOURCE["bytes"],
        "characters": CURRENT_SOURCE["characters"],
        "lf_lines": CURRENT_SOURCE["lf_lines"],
        "sha256": CURRENT_SOURCE["sha256"],
        "admitted_lines": "1-1780",
        "admitted_bytes": SOURCE_UNIT["admitted_prefix_bytes"],
        "admitted_sha256": SOURCE_UNIT["admitted_prefix_sha256"],
    }
    data["unit"] = {key: SOURCE_UNIT[key] for key in ("lines", "bytes", "characters", "lf_lines", "sha256")}
    data["candidate"] = dict(SEALED["candidate"])
    data["target"] = {
        "private": "ega/II/c2s1.tex",
        "public_mirror": "pub/ega-ko/source/c2s1.tex",
        **dict(SEALED["postimage"]),
        "mirrors_exact": True,
        "separator_line": 1_709,
        "candidate_target_lines": "1710-1809",
    }
    data["next"] = "Run the R39 cumulative build/QA/release gates; continue source preparation at canonical line1782 / §2.2.7."
    data["next_source"] = NEXT_SOURCE
    data["local_status"] = R39_STATUS
    data["r39_candidate_status"] = R39_CANDIDATE_STATUS
    data["r39_translation_integration"] = copy.deepcopy(ref)
    data["ega_ii_status"] = "active_incomplete"
    data["public_r38"] = r38_public_binding(closure, public=False)
    data["last_public_checkpoint"] = (
        "r38 / exact DOI10.5281/zenodo.22346664 / GitHub release "
        "ega-ko-2026-09-05-r38; dual anonymous four-artifact replay PASS"
    )
    data["public_reader"] = dict(R38_READER)
    data["public_exact_doi"] = R38_EXACT_DOI
    data["public_record_id"] = R38_RECORD_ID
    return data


def update_state(
    original: dict[str, Any], integrated_at: str, ref: Mapping[str, Any], closure: Mapping[str, Any]
) -> dict[str, Any]:
    key, expected = PRIVATE_SCHEMAS["state.json"]
    require(original.get(key) == expected, "private state schema drift")
    data = copy.deepcopy(original)
    data["updated"] = integrated_at
    data["candidate_r39"] = copy.deepcopy(ref)
    data["r39_translation_integration"] = copy.deepcopy(ref)
    data["public_r38"] = r38_public_binding(closure, public=False)
    active = data.setdefault("active", {})
    active["admitted"] = (
        f"front/programme complete plus main lines1-1780 through2.2.6; "
        f"prefix{SOURCE_UNIT['admitted_prefix_bytes']}/{SOURCE_UNIT['admitted_prefix_sha256']}"
    )
    active["unit"] = {key: SOURCE_UNIT[key] for key in ("lines", "bytes", "characters", "lf_lines", "sha256")}
    active["candidate"] = dict(SEALED["candidate"])
    active["target"] = {
        "private_path": "ega/II/c2s1.tex",
        "public_path": "source/c2s1.tex",
        **dict(SEALED["postimage"]),
        "separator_line": 1_709,
        "candidate_target_lines": "1710-1809",
    }
    active["reader"] = dict(R38_READER)
    active["publication"] = r38_public_binding(closure, public=False)
    active["next_source"] = NEXT_SOURCE
    active["next_target"] = "Refresh declarations and build the exact integrated R39 mirrors without reopening the translation bytes."
    active["gate"] = "R39 exact mirror integration PASS; downstream build, PDF QA, package and publication pending."
    active["qa"] = {
        "r38_public_closure": "PASS",
        "r39_corrected_reseal": "PASS",
        "r39_current_authority_validation": "PASS",
        "r39_integration": "PASS",
        "r39_build_pdf_package_publication": "PENDING",
    }
    data["next_executable_action"] = "Refresh cumulative declarations through canonical line1780 and run the serialized R39 build/QA/release gates."
    data["current_working_status"] = R39_STATUS
    completed = data.setdefault("completed", {})
    completed["working_translation_scope"] = WORKING_COVERAGE
    return data


def update_authority(original: dict[str, Any], integrated_at: str, ref: Mapping[str, Any], closure: Mapping[str, Any]) -> dict[str, Any]:
    require(original.get("schema") == "ag-ko-authority-v3", "private authority schema drift")
    data = copy.deepcopy(original)
    data["updated"] = integrated_at
    ega = data.get("ega_ii")
    require(isinstance(ega, dict), "private authority lacks ega_ii")
    ega["status"] = (
        "canonical five-input packet present; Korean front/programme complete; main input translated "
        "and integrated contiguously through lines1-1780 /2.2.6; EGA II active and incomplete; next source line1782"
    )
    source_rows = [row for row in ega.get("inputs", []) if row.get("path") == CURRENT_SOURCE["path"]]
    require(len(source_rows) == 1, "private authority EGA II source row is not unique")
    source_rows[0].update(
        {
            "lines": CURRENT_SOURCE["lf_lines"],
            "bytes": CURRENT_SOURCE["bytes"],
            "sha256": CURRENT_SOURCE["sha256"],
        }
    )
    admitted_rows = [row for row in ega.get("admitted", []) if row.get("target") == "ega/II/c2s1.tex"]
    require(len(admitted_rows) == 1, "private authority EGA II admitted row is not unique")
    admitted_rows[0].update(
        {
            "source": "source/ega2/ega2-1-fr.tex lines1-1780",
            "source_slice_bytes": SOURCE_UNIT["admitted_prefix_bytes"],
            "source_slice_sha256": SOURCE_UNIT["admitted_prefix_sha256"],
            "bytes": SEALED["postimage"]["bytes"],
            "sha256": SEALED["postimage"]["sha256"],
            "source_policy": "French diplomatic; exact source/query provenance retained; corrected Korean wording is bound by the R39 reseal control; no French source byte changed for the already routed lines1709/1738 queries.",
        }
    )
    ega["next"] = "source/ega2/ega2-1-fr.tex line1782, environment2.2.7; line1781 blank"
    ega["r39_translation_integration"] = copy.deepcopy(ref)
    lineage = data.get("publication_lineage")
    require(isinstance(lineage, dict), "private authority publication lineage is missing")
    require(
        lineage.get("exact_version_doi") == R38_PREDECESSOR_EXACT_DOI,
        "private authority predecessor publication identity drift",
    )
    lineage.update(
        {
            "zenodo_concept_doi": R38_CONCEPT_DOI,
            "prior_public_exact_doi": R38_PREDECESSOR_EXACT_DOI,
            "exact_version_doi": R38_EXACT_DOI,
            "record_id": R38_RECORD_ID,
            "github": R38_REPOSITORY,
            "github_artifact_commit": R38_ARTIFACT_COMMIT,
            "annotated_tag": R38_TAG,
            "release": R38_RELEASE,
            "active_destinations": ["Zenodo", "GitHub"],
            "status": R38_PUBLIC_STATUS,
            "closure": {
                "path": "controls/R38_PUBLIC_CLOSURE.json",
                **dict(closure["closure_control"]),
                "private_public_mirrors_exact": True,
            },
        }
    )
    data["public_r38"] = r38_public_binding(closure, public=False)
    data["current_working_status"] = R39_STATUS
    return data


def update_public_alias(
    name: str,
    original: dict[str, Any],
    integrated_at: str,
    ref: Mapping[str, Any],
    closure: Mapping[str, Any],
) -> dict[str, Any]:
    key, expected = PUBLIC_SCHEMAS[name]
    require(original.get(key) == expected, f"public alias schema drift: {name}")
    require(original.get("version") == PREVIOUS_VERSION, f"public alias is not the exact R37 preimage: {name}")
    require("public_r38" not in original, f"public alias already carries an uncoordinated R38 binding: {name}")
    data = copy.deepcopy(original)
    data["version"] = VERSION
    data["updated"] = integrated_at
    data["public_r38"] = r38_public_binding(closure, public=True)
    data["source"] = {
        "path": CURRENT_SOURCE["path"],
        "whole_bytes": CURRENT_SOURCE["bytes"],
        "whole_lf_lines": CURRENT_SOURCE["lf_lines"],
        "whole_sha256": CURRENT_SOURCE["sha256"],
        "admitted_lines": "1-1780",
        "admitted_bytes": SOURCE_UNIT["admitted_prefix_bytes"],
        "admitted_sha256": SOURCE_UNIT["admitted_prefix_sha256"],
    }
    data["unit"] = {key: SOURCE_UNIT[key] for key in ("lines", "bytes", "characters", "lf_lines", "sha256")}
    data["candidate"] = public_candidate_ref()
    data["target"] = {
        "path": "source/c2s1.tex",
        **dict(SEALED["postimage"]),
        "separator_line": 1_709,
        "candidate_target_lines": "1710-1809",
        "private_public_exact": True,
    }
    data["reader"] = dict(R38_READER)
    if "exact_doi" in data:
        data["exact_doi"] = R38_EXACT_DOI
    if "exact_version_doi" in data:
        data["previous_exact_version_doi"] = R38_PREDECESSOR_EXACT_DOI
        data["exact_version_doi"] = R38_EXACT_DOI
    if "record_id" in data:
        data["record_id"] = R38_RECORD_ID
    data["current_public_checkpoint"] = (
        "r38 / exact DOI10.5281/zenodo.22346664 / GitHub release ega-ko-2026-09-05-r38; "
        "four artifacts at both destinations passed anonymous byte replay"
    )
    data["publication_phase"] = "public_open_dual_destination_anonymous_byte_replay_pass"
    data["working_translation_coverage"] = WORKING_COVERAGE
    data["current_working_status"] = R39_STATUS
    data["working_result"] = R39_STATUS
    data["r39_candidate_status"] = R39_CANDIDATE_STATUS
    data["r39_translation_integration"] = copy.deepcopy(ref)
    data["next_source"] = NEXT_SOURCE
    data["ega_ii_status"] = "active_incomplete; latest public checkpoint R38; working translation through §2.2.6 / lines1-1780"
    if name in {"CURSOR.json", "PROGRAM_CURSOR.json"}:
        data["completed_through"] = "working Korean EGA II through §2.2.6 / canonical lines1-1780"
    elif name in {"STATE.json", "PROGRAM_STATE.json"}:
        data["working_release_gates"] = copy.deepcopy(ref["gates"])
    elif name == "QA_STATE.json":
        data["working_translation_gate"] = "PASS_R39_EXACT_MIRROR_INTEGRATION_ONLY"
    elif name == "PROGRAM_AUTHORITY.json":
        publication = data.setdefault("publication", {})
        publication.update(r38_public_binding(closure, public=True))
        publication["working_status"] = R39_STATUS
    elif name == "DATACITE_RELATIONS.json":
        data["release_state"] = "public_open_dual_destination_anonymous_byte_replay_pass"
        data["publication_status"] = R38_PUBLIC_STATUS
        data["public_record_url"] = R38_ZENODO
        data["github_release"] = R38_RELEASE
        data["working_version_status"] = R39_STATUS
        data["latest_public_version_remains"] = VERSION
    return data


def ledger_records(integrated_at: str, control_identity: Mapping[str, Any], closure: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    decision = {
        "id": "AGKO-D188",
        "time": integrated_at,
        "precision": "second",
        "kind": "r39_corrected_reseal_and_exact_translation_integration",
        "scope": "EGA II canonical lines1685-1780 / target lines1710-1809",
        "choice": "Supersede the defective historical R39 candidate additively, admit only the corrected independently validated reseal, and append it once after the exact public R38 source preimage with one LF separator in both mirrors.",
        "alternatives": [
            "Integrate the superseded candidate whose Korean wording was rejected",
            "Modify the already public R38 prefix",
            "Treat exact integration as proof of build, PDF QA, packaging or publication",
        ],
        "rejected": "Those alternatives preserve a known Korean defect, break public-prefix provenance, or overclaim downstream gates.",
        "evidence": [
            f"controls/R39_TRANSLATION_INTEGRATION.json {control_identity['bytes']} bytes /{control_identity['sha256']}",
            f"corrected candidate {SEALED['candidate']['bytes']} bytes /{SEALED['candidate']['sha256']}",
            f"integrated mirrors {SEALED['postimage']['bytes']} bytes /{SEALED['postimage']['sha256']}",
            f"R38 closure {closure['closure_control']['bytes']} bytes /{closure['closure_control']['sha256']}",
        ],
        "uncertainty": "None in the recorded byte integration. Build, extraction, rendered QA, package portability and R39 publication remain unperformed.",
        "consequence": "Working Korean EGA II is contiguous through §2.2.6 / canonical line1780 while R38 remains the latest public checkpoint.",
        "review": "PASS_R39_CORRECTED_RESEAL_CURRENT_AUTHORITY_AND_EXACT_MIRROR_INTEGRATION",
        "next": "Run the serialized R39 build/QA/release gates, then continue canonical line1782.",
    }
    evidence = {
        "id": "AGKO-E-R39-INTEGRATION-20260906",
        "time": integrated_at,
        "precision": "second",
        "kind": "translation_integration_evidence",
        "scope": "EGA II R39 corrected candidate and exact mirror transaction",
        "authority": f"{SOURCE_UNIT['lines']}/{SOURCE_UNIT['bytes']}B/{SOURCE_UNIT['sha256']}; prefix1-1780/{SOURCE_UNIT['admitted_prefix_bytes']}B/{SOURCE_UNIT['admitted_prefix_sha256']}",
        "candidate": f"{SEALED['candidate']['bytes']}B/{SEALED['candidate']['sha256']}",
        "preimage": f"{R38_TARGET['bytes']}B/{R38_TARGET['sha256']}",
        "postimage": f"{SEALED['postimage']['bytes']}B/{SEALED['postimage']['sha256']}",
        "controls": [
            {"private": "controls/R39_TRANSLATION_INTEGRATION.json", "public": "evidence/controls/R39_TRANSLATION_INTEGRATION.json", **dict(control_identity)},
            {"private": SEALED["reseal_control"]["private"], "public": SEALED["reseal_control"]["public"], "bytes": SEALED["reseal_control"]["bytes"], "sha256": SEALED["reseal_control"]["sha256"]},
        ],
        "r38_public_closure": {
            "control": dict(closure["closure_control"]),
            "commit_receipt": dict(closure["closure_commit_receipt"]),
            "publication_journal": dict(closure["publication_journal"]),
        },
        "validation": "PASS: current canonical source/unit/prefix, corrected reseal, current validator, one-LF append, complete postimage, mirror identity and R38 public closure receipts.",
        "limits": "No TeX, PDF, Git, network, UI or publication action; downstream gates pending.",
        "result": R39_RESULT,
    }
    hard = {
        "id": "AGKO-H163",
        "time": integrated_at,
        "precision": "second",
        "status": "controlling_r39_corrected_reseal_and_exact_eof_transaction",
        "scope": "Every R39 append to the cumulative Korean EGA II c2s1 mirrors",
        "locator": "sealed R38 EOF, separator line1709, corrected candidate lines1710-1809",
        "symptom": "The historical R39 candidate contained rejected Korean spacing and therefore could not be promoted merely because its earlier mathematical validator passed.",
        "cause_evidence": "The corrected reseal changes candidate and prospective whole-target identities; the historical admission/rebase rows are preserved as superseded evidence rather than silently rewritten.",
        "resolution": "Require the corrected reseal, current-authority validator, complete R38 public closure receipts and predetermined complete postimage before one atomic mirrored append transaction.",
        "tests": f"private/public postimage exact {SEALED['postimage']['bytes']} bytes /{SEALED['postimage']['sha256']}; rollback journal and exact ledger/control mirrors verified",
        "residual_risk": "R39 build, rendered QA, packaging, portable replay and publication remain pending and are not inferred from integration.",
        "recurrence": "Never integrate a candidate from a historical admission after its bytes change; add a hash-bound reseal and regenerate the complete prospective identity.",
        "related": ["AGKO-D188", "AGKO-E-R39-INTEGRATION-20260906", "AGKO-EGA2-S1-R39-INTEGRATED-R1"],
    }
    return {"decisions.jsonl": decision, "evidence.jsonl": evidence, "hard.jsonl": hard}


def unit_row() -> dict[str, Any]:
    return {
        "id": "AGKO-EGA2-S1-R39-INTEGRATED-R1",
        "kind": "section_state_update",
        "parent": "AGKO-EGA2-S1",
        "order": 2_134,
        "authority": {
            "path": CURRENT_SOURCE["path"],
            "locator": "lines1-1780 through2.2.6; next executable1782;1781 blank",
            "bytes": SOURCE_UNIT["admitted_prefix_bytes"],
            "sha256": SOURCE_UNIT["admitted_prefix_sha256"],
            "whole_bytes": CURRENT_SOURCE["bytes"],
            "whole_sha256": CURRENT_SOURCE["sha256"],
        },
        "target": {
            "path": "ega/II/c2s1.tex",
            "locator": "integrated lines1-1809; separator1709; corrected candidate1710-1809",
            "bytes": SEALED["postimage"]["bytes"],
            "sha256": SEALED["postimage"]["sha256"],
            "identity_status": "exact_private_public_integrated_mirrors",
            "appended_bytes": SEALED["candidate"]["bytes"],
            "appended_sha256": SEALED["candidate"]["sha256"],
        },
        "relations": [
            "supersedes:AGKO-EGA2-S1-R39-COVERAGE",
            "controls/R39_TRANSLATION_INTEGRATION.json",
            Path(SEALED["reseal_control"]["private"]).name,
            "R38 public closure PASS before integration",
            "source queries1709/1738 already delivered nonblocking",
        ],
        "language": "ko-KR",
        "state": {
            "translation": "complete",
            "build": "pending",
            "visual": "pending",
            "publication": "private_working",
            "integration": "pass_exact_mirrors",
        },
    }


def append_jsonl_record(original: bytes, record: Mapping[str, Any], label: str) -> bytes:
    rows = parse_jsonl(original, label)
    record_id = record["id"]
    require(sum(row.get("id") == record_id for row in rows) == 0, f"record already exists: {label}:{record_id}")
    return original + jsonl_bytes(record)


def append_unit_row(original: bytes, row: Mapping[str, Any], label: str) -> bytes:
    rows = parse_jsonl(original, label)
    require(sum(item.get("id") == row["id"] for item in rows) == 0, f"unit row already exists: {label}")
    existing = [item for item in rows if item.get("id") == "AGKO-EGA2-S1-R39-COVERAGE"]
    require(len(existing) == 1, f"historical R39 coverage row is not unique: {label}")
    require(max(item.get("order", 0) for item in rows if isinstance(item.get("order"), int)) == 2_133, f"unit order frontier drift: {label}")
    require(row["state"]["translation"] == "complete", "unit-row translation state is not schema-valid")
    require(row["state"]["build"] == "pending", "unit-row build state is not schema-valid")
    require(row["state"]["visual"] == "pending", "unit-row visual state is not schema-valid")
    require(row["state"]["publication"] == "private_working", "unit-row publication state is not schema-valid")
    return original + jsonl_bytes(row)


def output_paths(roots: Roots) -> list[Path]:
    paths = [
        roots.private / "ega" / "II" / "c2s1.tex",
        roots.repo / "source" / "c2s1.tex",
        roots.private / CONTROL_PRIVATE_REL,
        roots.repo / CONTROL_PUBLIC_REL,
        roots.repo / SEALED["reseal_control"]["public"],
        roots.repo / "evidence" / "controls" / Path(SEALED["validator_receipt"]["path"]).name,
        roots.private / "cursor.json",
        roots.private / "state.json",
        roots.private / "authority.json",
        *(roots.repo / "evidence" / name for name in PUBLIC_ALIASES),
        *(roots.private / name for name in LEDGERS),
        *(roots.repo / "evidence" / name for name in LEDGERS),
        roots.private / "index" / "units.jsonl",
        roots.repo / "evidence" / "index" / "units.jsonl",
    ]
    resolved = [path.resolve(strict=False) for path in paths]
    require(len(resolved) == len(set(resolved)), "R39 output path inventory is not injective")
    return paths


def prerequisite_paths(roots: Roots) -> list[Path]:
    release = roots.repo / "release" / VERSION
    paths = [
        Path(__file__).resolve(strict=True),
        roots.canonical / CURRENT_SOURCE["path"],
        roots.canonical / "controls" / "EGA_CANON_QUEUE.json",
        roots.private / SEALED["candidate"]["path"],
        roots.private / SEALED["validator"]["path"],
        roots.private / SEALED["validator_receipt"]["path"],
        roots.private / SEALED["reseal_control"]["private"],
        roots.private / HISTORICAL_ADMISSION["private"],
        roots.repo / HISTORICAL_ADMISSION["public"],
        roots.private / HISTORICAL_REBASE["private"],
        roots.repo / HISTORICAL_REBASE["public"],
        roots.private / "controls" / "R38_PUBLIC_CLOSURE.json",
        roots.repo / "evidence" / "controls" / "R38_PUBLIC_CLOSURE.json",
        roots.private / "controls" / "R38_CLOSURE_COMMIT_RECEIPT.json",
        roots.private / "controls" / "R38_FRESH_CLOSURE_TRANSACTION.json",
        roots.private / "controls" / "R38_PUBLICATION_TRANSACTION.json",
        roots.repo / "github-receipt-r38.json",
        roots.repo / "receipt-r38.json",
        *(release / row["name"] for row in R38_ARTIFACTS),
        release / "PACKAGE_RECEIPT.json",
        release / "PORTABLE_BUILD_REPLAY.json",
        release / "GITHUB_PUBLICATION_RECEIPT.json",
        release / "ZENODO_PUBLICATION_RECEIPT.json",
        roots.repo / "evidence" / "index" / "schema.json",
    ]
    unique: dict[Path, Path] = {}
    for path in paths:
        unique[path.resolve(strict=False)] = path
    return list(unique.values())


def snapshot(paths: Iterable[Path], roots: Roots) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda item: role(item, roots).casefold()):
        locator = role(path, roots)
        if path.exists():
            regular(path, locator)
            rows.append({"path": locator, "exists": True, **ident(path)})
        else:
            require(not path.is_symlink(), f"dangling symlink at expected-absent path: {locator}")
            rows.append({"path": locator, "exists": False, "bytes": 0, "sha256": None})
    return rows


def require_snapshot(rows: Sequence[Mapping[str, Any]], roots: Roots) -> None:
    for row in rows:
        path = resolve_role(str(row["path"]), roots)
        if row["exists"]:
            require(path.exists() and path.is_file() and not path.is_symlink(), f"snapshot prerequisite disappeared: {row['path']}")
            require(ident(path) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"fresh-preimage conflict: {row['path']}")
        else:
            require(not path.exists() and not path.is_symlink(), f"fresh-preimage expected absence drift: {row['path']}")


def snapshot_digest(integrated_at: str, inputs: list[dict[str, Any]], preimages: list[dict[str, Any]]) -> str:
    return digest(
        json_bytes(
            {
                "schema": "agko-r39-integration-fresh-preimage-v1",
                "integrated_at": integrated_at,
                "inputs": inputs,
                "preimages": preimages,
            }
        )
    )


def validate_public_delta(old: bytes | None, new: bytes, label: str) -> None:
    text = new.decode("utf-8")
    old_text = old.decode("utf-8") if old is not None else ""
    for pattern, description in (
        (PRIVATE_PATH_RE, "private absolute path"),
        (EMAIL_RE, "email address"),
        (CREDENTIAL_RE, "credential-shaped material"),
    ):
        new_hits = Counter(match.group(0).casefold() for match in pattern.finditer(text))
        old_hits = Counter(match.group(0).casefold() for match in pattern.finditer(old_text))
        require(
            all(count <= old_hits[value] for value, count in new_hits.items()),
            f"public postimage introduces {description}: {label}",
        )
    for excluded in (
        re.compile(r"(?i)(?<![A-Z0-9])TTP(?![A-Z0-9])"),
        re.compile(r"(?i)Translation and Transcription Project"),
        re.compile(r"(?i)(?<![A-Z0-9])Figshare(?![A-Z0-9])"),
    ):
        require(
            len(excluded.findall(text)) <= len(excluded.findall(old_text)),
            f"public postimage introduces excluded prose: {label}",
        )


def build_outputs(
    roots: Roots,
    integrated_at: str,
    translation: Mapping[str, Any],
    closure: Mapping[str, Any],
    fresh_digest: str,
) -> tuple[dict[Path, bytes], dict[str, Any]]:
    control = build_control(integrated_at, translation, closure, fresh_digest)
    control_identity = ident_bytes(control)
    private_ref = integration_ref(control_identity, public=False)
    public_ref = integration_ref(control_identity, public=True)
    records = ledger_records(integrated_at, control_identity, closure)
    row = unit_row()
    outputs: dict[Path, bytes] = {
        roots.private / "ega" / "II" / "c2s1.tex": translation["postimage"],
        roots.repo / "source" / "c2s1.tex": translation["postimage"],
        roots.private / CONTROL_PRIVATE_REL: control,
        roots.repo / CONTROL_PUBLIC_REL: control,
        roots.repo / SEALED["reseal_control"]["public"]: (
            roots.private / SEALED["reseal_control"]["private"]
        ).read_bytes(),
        roots.repo / "evidence" / "controls" / Path(SEALED["validator_receipt"]["path"]).name: (
            roots.private / SEALED["validator_receipt"]["path"]
        ).read_bytes(),
        roots.private / "cursor.json": json_bytes(
            update_cursor(
                parse_json(roots.private / "cursor.json", "private cursor"),
                integrated_at,
                private_ref,
                closure,
            )
        ),
        roots.private / "state.json": json_bytes(
            update_state(
                parse_json(roots.private / "state.json", "private state"),
                integrated_at,
                private_ref,
                closure,
            )
        ),
        roots.private / "authority.json": json_bytes(
            update_authority(
                parse_json(roots.private / "authority.json", "private authority"),
                integrated_at,
                private_ref,
                closure,
            )
        ),
    }
    for name in PUBLIC_ALIASES:
        path = roots.repo / "evidence" / name
        outputs[path] = json_bytes(
            update_public_alias(
                name,
                parse_json(path, f"public alias {name}"),
                integrated_at,
                public_ref,
                closure,
            )
        )
    for name in LEDGERS:
        private = roots.private / name
        public = roots.repo / "evidence" / name
        outputs[private] = append_jsonl_record(private.read_bytes(), records[name], f"private {name}")
        outputs[public] = append_jsonl_record(public.read_bytes(), records[name], f"public {name}")
    private_units = roots.private / "index" / "units.jsonl"
    public_units = roots.repo / "evidence" / "index" / "units.jsonl"
    outputs[private_units] = append_unit_row(private_units.read_bytes(), row, "private unit index")
    outputs[public_units] = append_unit_row(public_units.read_bytes(), row, "public unit index")
    require(set(outputs) == set(output_paths(roots)), "R39 postimage inventory drift")
    for path, data in outputs.items():
        if path.resolve(strict=False).is_relative_to(roots.repo):
            old = path.read_bytes() if path.exists() else None
            validate_public_delta(old, data, role(path, roots))
    return outputs, {
        "control": control_identity,
        "private_ref": private_ref,
        "public_ref": public_ref,
        "records": records,
        "unit": row,
    }


def postimage_rows(outputs: Mapping[Path, bytes], roots: Roots) -> list[dict[str, Any]]:
    return [
        {"path": role(path, roots), **ident_bytes(data)}
        for path, data in sorted(outputs.items(), key=lambda item: role(item[0], roots).casefold())
    ]


def build_plan(
    roots: Roots, integrated_at: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[Path, bytes], dict[str, Any], str]:
    translation = verify_translation_inputs(roots)
    closure = verify_r38_public_closure(roots)
    for path in prerequisite_paths(roots):
        regular(path, role(path, roots))
    for path in (roots.private / CONTROL_PRIVATE_REL, roots.repo / CONTROL_PUBLIC_REL):
        require(not path.exists() and not path.is_symlink(), "R39 integration control already exists")
    inputs = snapshot(prerequisite_paths(roots), roots)
    preimages = snapshot(output_paths(roots), roots)
    fresh_digest = snapshot_digest(integrated_at, inputs, preimages)
    outputs, evidence = build_outputs(roots, integrated_at, translation, closure, fresh_digest)
    evidence["translation"] = translation
    evidence["closure"] = closure
    return inputs, preimages, outputs, evidence, fresh_digest


def verify_outputs(roots: Roots, journal: Mapping[str, Any]) -> None:
    for row in journal["postimages"]:
        path = resolve_role(row["path"], roots)
        require(path.exists() and ident(path) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"R39 postimage mismatch: {row['path']}")
    private_target = roots.private / "ega" / "II" / "c2s1.tex"
    public_target = roots.repo / "source" / "c2s1.tex"
    require(private_target.read_bytes() == public_target.read_bytes(), "R39 target mirrors differ after transaction")
    require(ident(private_target) == {"bytes": SEALED["postimage"]["bytes"], "sha256": SEALED["postimage"]["sha256"]}, "R39 target final identity drift")
    final = private_target.read_bytes()
    candidate = (roots.private / SEALED["candidate"]["path"]).read_bytes()
    require(
        ident_bytes(final[: R38_TARGET["bytes"]])
        == {"bytes": R38_TARGET["bytes"], "sha256": R38_TARGET["sha256"]},
        "R39 final target does not preserve the exact R38 prefix",
    )
    require(final[R38_TARGET["bytes"] :] == b"\n" + candidate, "R39 target tail is not exact separator plus candidate")
    private_control = roots.private / CONTROL_PRIVATE_REL
    public_control = roots.repo / CONTROL_PUBLIC_REL
    require(private_control.read_bytes() == public_control.read_bytes(), "R39 integration controls differ")
    require(
        (roots.private / SEALED["reseal_control"]["private"]).read_bytes()
        == (roots.repo / SEALED["reseal_control"]["public"]).read_bytes(),
        "R39 reseal control mirrors differ",
    )
    require(
        (roots.private / SEALED["validator_receipt"]["path"]).read_bytes()
        == (
            roots.repo
            / "evidence"
            / "controls"
            / Path(SEALED["validator_receipt"]["path"]).name
        ).read_bytes(),
        "R39 current-validator receipt mirrors differ",
    )
    control = parse_json(private_control, "R39 integration control")
    require(control.get("schema") == "agko-r39-translation-integration-v1", "R39 integration control schema drift")
    require(control.get("result") == R39_STATUS, "R39 integration control result drift")
    require(control.get("final_integration", {}).get("sha256") == SEALED["postimage"]["sha256"], "R39 control target binding drift")
    control_identity = ident(private_control)
    for name in PUBLIC_ALIASES:
        value = parse_json(roots.repo / "evidence" / name, f"R39 public alias {name}")
        require(value.get("version") == VERSION, f"public R38 checkpoint changed during R39 integration: {name}")
        require(value.get("public_r38", {}).get("status") == R38_PUBLIC_STATUS, f"public R38 status lost: {name}")
        require(value.get("public_r38", {}).get("control", {}).get("sha256") == journal["closure_control_sha256"], f"public R38 control binding drift: {name}")
        require(value.get("r39_translation_integration", {}).get("control", {}).get("sha256") == control_identity["sha256"], f"R39 public alias binding drift: {name}")
        require(value.get("current_working_status") == R39_STATUS, f"R39 public alias status drift: {name}")
        require(value.get("source", {}).get("whole_sha256") == CURRENT_SOURCE["sha256"], f"R39 public source binding drift: {name}")
        require(value.get("unit", {}).get("sha256") == SOURCE_UNIT["sha256"], f"R39 public unit binding drift: {name}")
        require(value.get("candidate", {}).get("sha256") == SEALED["candidate"]["sha256"], f"R39 public candidate binding drift: {name}")
        require(value.get("candidate", {}).get("path") == "source/c2s1.tex", f"R39 public candidate locator drift: {name}")
        require(value.get("target", {}).get("sha256") == SEALED["postimage"]["sha256"], f"R39 public target binding drift: {name}")
    for name in PRIVATE_SCHEMAS:
        value = parse_json(roots.private / name, f"R39 private alias {name}")
        require(value.get("r39_translation_integration", {}).get("control", {}).get("sha256") == control_identity["sha256"], f"R39 private alias binding drift: {name}")
        require(value.get("public_r38", {}).get("control", {}).get("sha256") == journal["closure_control_sha256"], f"private R38 control binding drift: {name}")
    state = parse_json(roots.private / "state.json", "R39 private state")
    active = state.get("active", {})
    require(active.get("unit", {}).get("sha256") == SOURCE_UNIT["sha256"], "private active R39 unit binding drift")
    require(active.get("candidate", {}).get("sha256") == SEALED["candidate"]["sha256"], "private active R39 candidate binding drift")
    require(active.get("target", {}).get("sha256") == SEALED["postimage"]["sha256"], "private active R39 target binding drift")
    authority = parse_json(roots.private / "authority.json", "R39 private authority")
    require(authority.get("ega_ii", {}).get("r39_translation_integration", {}).get("control", {}).get("sha256") == control_identity["sha256"], "private authority R39 binding drift")
    lineage = authority.get("publication_lineage", {})
    require(lineage.get("exact_version_doi") == R38_EXACT_DOI, "private authority current DOI drift")
    require(lineage.get("prior_public_exact_doi") == R38_PREDECESSOR_EXACT_DOI, "private authority predecessor DOI lost")
    for name, record_id in (
        ("decisions.jsonl", "AGKO-D188"),
        ("evidence.jsonl", "AGKO-E-R39-INTEGRATION-20260906"),
        ("hard.jsonl", "AGKO-H163"),
    ):
        private_rows = parse_jsonl((roots.private / name).read_bytes(), f"private {name}")
        public_rows = parse_jsonl((roots.repo / "evidence" / name).read_bytes(), f"public {name}")
        private_matches = [row for row in private_rows if row.get("id") == record_id]
        public_matches = [row for row in public_rows if row.get("id") == record_id]
        require(len(private_matches) == len(public_matches) == 1, f"R39 ledger record multiplicity drift: {record_id}")
        require(private_matches[0] == public_matches[0], f"R39 ledger record payload mismatch: {record_id}")
    for path, label in (
        (roots.private / "index" / "units.jsonl", "private unit index"),
        (roots.repo / "evidence" / "index" / "units.jsonl", "public unit index"),
    ):
        matches = [row for row in parse_jsonl(path.read_bytes(), label) if row.get("id") == "AGKO-EGA2-S1-R39-INTEGRATED-R1"]
        require(len(matches) == 1 and matches[0]["target"]["sha256"] == SEALED["postimage"]["sha256"], f"R39 integrated unit row drift: {label}")


def fsync_file(path: Path) -> None:
    # Windows' CRT rejects ``fsync`` on a read-only descriptor (EBADF).
    # Backups are transaction-owned writable files, so flush through r+b.
    with path.open("r+b") as stream:
        os.fsync(stream.fileno())


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".r39-tmp-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def write_journal(path: Path, value: Mapping[str, Any]) -> None:
    atomic_write(path, json_bytes(value))


def load_journal(roots: Roots) -> dict[str, Any] | None:
    path = roots.private / JOURNAL_REL
    if not path.exists() and not path.is_symlink():
        return None
    value = parse_json(path, "R39 integration transaction journal")
    require(value.get("schema") == "agko-r39-integration-transaction-v1", "R39 journal schema drift")
    require(
        isinstance(value.get("transaction_id"), str)
        and re.fullmatch(r"AGKO-R39-INTEGRATION-[0-9A-F]{20}", value["transaction_id"]) is not None,
        "R39 journal transaction ID drift",
    )
    require(value.get("status") in {"PREPARING", "PREPARED", "APPLYING", "VERIFYING", "COMMITTED", "ROLLED_BACK", "RECOVERY_CONFLICT"}, "R39 journal status drift")
    require_sha(value.get("fresh_preimage_sha256"), "R39 journal fresh preimage")
    require_sha(value.get("closure_control_sha256"), "R39 journal closure control")
    expected_paths = {role(item, roots) for item in output_paths(roots)}
    for key in ("preimages", "postimages"):
        rows = value.get(key)
        require(isinstance(rows, list) and len(rows) == len(expected_paths), f"R39 journal {key} cardinality drift")
        locators: list[str] = []
        for row in rows:
            require(isinstance(row, dict) and isinstance(row.get("path"), str), f"R39 journal {key} row drift")
            resolve_role(row["path"], roots)
            locators.append(row["path"])
            require(type(row.get("bytes")) is int and row["bytes"] >= 0, f"R39 journal {key} byte drift")
            if key == "preimages":
                require(type(row.get("exists")) is bool, "R39 journal preimage existence drift")
                if row["exists"]:
                    require_sha(row.get("sha256"), "R39 journal preimage")
                else:
                    require(row.get("sha256") is None and row["bytes"] == 0, "R39 absent preimage identity drift")
            else:
                require_sha(row.get("sha256"), "R39 journal postimage")
        require(len(locators) == len(set(locators)) and set(locators) == expected_paths, f"R39 journal {key} path inventory drift")
    applied = value.get("applied")
    require(isinstance(applied, list) and len(applied) == len(set(applied)), "R39 journal applied inventory drift")
    require(set(applied).issubset(expected_paths), "R39 journal applied path escapes output inventory")
    require(isinstance(value.get("prior_attempts"), list), "R39 journal prior-attempt history drift")
    return value


def transaction_root(roots: Roots, transaction_id: str) -> Path:
    root = (roots.private / WORK_REL / transaction_id).resolve(strict=False)
    base = (roots.private / WORK_REL).resolve(strict=False)
    require(root.is_relative_to(base) and root.parent == base, "unsafe R39 transaction work directory")
    return root


def rollback(roots: Roots, journal: dict[str, Any]) -> None:
    preimages = {row["path"]: row for row in journal["preimages"]}
    postimages = {row["path"]: row for row in journal["postimages"]}
    # Backup filenames are positional.  Preserve the exact case-folded order
    # persisted in ``postimages`` instead of re-sorting it differently here.
    ordered = [row["path"] for row in journal["postimages"]]
    root = transaction_root(roots, journal["transaction_id"])
    backups = root / "backups"
    conflicts: list[str] = []
    for index, locator in reversed(list(enumerate(ordered))):
        path = resolve_role(locator, roots)
        old = preimages[locator]
        new_identity = {"bytes": postimages[locator]["bytes"], "sha256": postimages[locator]["sha256"]}
        if path.exists():
            actual = ident(path)
            if old["exists"] and actual == {"bytes": old["bytes"], "sha256": old["sha256"]}:
                continue
            if actual != new_identity:
                conflicts.append(locator)
                continue
            if old["exists"]:
                backup = backups / f"{index:03d}.bin"
                if not backup.exists() or ident(backup) != {"bytes": old["bytes"], "sha256": old["sha256"]}:
                    conflicts.append(locator)
                else:
                    os.replace(backup, path)
            else:
                path.unlink()
        elif old["exists"]:
            backup = backups / f"{index:03d}.bin"
            if not backup.exists() or ident(backup) != {"bytes": old["bytes"], "sha256": old["sha256"]}:
                conflicts.append(locator)
            else:
                os.replace(backup, path)
    if conflicts:
        journal["status"] = "RECOVERY_CONFLICT"
        journal["conflicts"] = conflicts
        write_journal(roots.private / JOURNAL_REL, journal)
        raise RuntimeError("rollback refused to overwrite unknown concurrent bytes")
    require_snapshot(journal["preimages"], roots)
    journal["status"] = "ROLLED_BACK"
    journal["applied"] = []
    write_journal(roots.private / JOURNAL_REL, journal)
    if root.exists():
        shutil.rmtree(root)


@contextmanager
def mutex(name: str, timeout_ms: int = 30_000) -> Iterator[bool]:
    if os.name != "nt":
        raise RuntimeError("the R39 integration mutex requires Windows")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    kernel.WaitForSingleObject.restype = ctypes.c_uint
    kernel.ReleaseMutex.argtypes = [ctypes.c_void_p]
    kernel.ReleaseMutex.restype = ctypes.c_int
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.CreateMutexW(None, 0, name)
    require(bool(handle), "could not create the R39 integration mutex")
    result = kernel.WaitForSingleObject(handle, timeout_ms)
    require(result in (0x00000000, 0x00000080), "R39 integration mutex acquisition timed out")
    try:
        yield result == 0x00000080
    finally:
        kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def execute_plan(
    roots: Roots,
    integrated_at: str,
    inputs: list[dict[str, Any]],
    preimages: list[dict[str, Any]],
    outputs: Mapping[Path, bytes],
    fresh_digest: str,
    expected_digest: str,
) -> dict[str, Any]:
    require(expected_digest == fresh_digest, "operator-bound fresh-preimage SHA-256 mismatch")
    existing = load_journal(roots)
    prior_attempt = 0
    history: list[dict[str, Any]] = []
    if existing is not None:
        if existing.get("status") == "COMMITTED":
            verify_outputs(roots, existing)
            return existing
        if existing.get("status") not in {"ROLLED_BACK"}:
            rollback(roots, existing)
            raise RuntimeError("an incomplete earlier transaction was rolled back; rerun --check before execution")
        require_snapshot(existing["preimages"], roots)
        prior_attempt = int(existing.get("attempt", 0))
        history = copy.deepcopy(existing.get("prior_attempts", [])) + [
            {
                "transaction_id": existing.get("transaction_id"),
                "attempt": prior_attempt,
                "status": existing.get("status"),
                "fresh_preimage_sha256": existing.get("fresh_preimage_sha256"),
            }
        ]
    require_snapshot(inputs, roots)
    require_snapshot(preimages, roots)
    transaction_id = "AGKO-R39-INTEGRATION-" + fresh_digest[:20]
    root = transaction_root(roots, transaction_id)
    require(not root.exists(), "R39 transaction work directory already exists")
    journal = {
        "schema": "agko-r39-integration-transaction-v1",
        "transaction_id": transaction_id,
        "integrated_at": integrated_at,
        "fresh_preimage_sha256": fresh_digest,
        "closure_control_sha256": ident(roots.private / "controls" / "R38_PUBLIC_CLOSURE.json")["sha256"],
        "status": "PREPARING",
        "attempt": prior_attempt + 1,
        "abandoned_mutex_recovered": False,
        "work_directory": role(root, roots),
        "inputs": inputs,
        "preimages": preimages,
        "postimages": postimage_rows(outputs, roots),
        "applied": [],
        "conflicts": [],
        "prior_attempts": history,
        "concurrency_model": (
            "All cooperating writers use Global\\InterlanguageAgKoR39IntegrationV1; "
            "fresh snapshots are rechecked immediately before every replace and all postimages are verified."
        ),
    }
    write_journal(roots.private / JOURNAL_REL, journal)
    try:
        staged = root / "staged"
        backups = root / "backups"
        staged.mkdir(parents=True)
        backups.mkdir()
        preimage_map = {row["path"]: row for row in preimages}
        ordered = sorted(outputs, key=lambda path: role(path, roots).casefold())
        require(
            [role(path, roots) for path in ordered] == [row["path"] for row in journal["postimages"]],
            "R39 journal/application ordering drift",
        )
        for index, path in enumerate(ordered):
            locator = role(path, roots)
            stage = staged / f"{index:03d}.bin"
            with stage.open("xb") as stream:
                stream.write(outputs[path])
                stream.flush()
                os.fsync(stream.fileno())
            row = preimage_map[locator]
            if row["exists"]:
                backup = backups / f"{index:03d}.bin"
                shutil.copyfile(path, backup)
                fsync_file(backup)
                require(ident(backup) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "backup identity drift")
        journal["status"] = "PREPARED"
        write_journal(roots.private / JOURNAL_REL, journal)
        require_snapshot(inputs, roots)
        require_snapshot(preimages, roots)
        for index, path in enumerate(ordered):
            for remaining in ordered[index:]:
                row = preimage_map[role(remaining, roots)]
                if row["exists"]:
                    require(remaining.exists() and ident(remaining) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "concurrent output mutation before replace")
                else:
                    require(not remaining.exists() and not remaining.is_symlink(), "concurrent output creation before replace")
            journal["status"] = "APPLYING"
            write_journal(roots.private / JOURNAL_REL, journal)
            os.replace(staged / f"{index:03d}.bin", path)
            require(ident(path) == ident_bytes(outputs[path]), "post-replace identity mismatch")
            journal["applied"].append(role(path, roots))
            write_journal(roots.private / JOURNAL_REL, journal)
        journal["status"] = "VERIFYING"
        write_journal(roots.private / JOURNAL_REL, journal)
        verify_outputs(roots, journal)
        journal["status"] = "COMMITTED"
        journal["work_directory_cleanup"] = "PENDING"
        write_journal(roots.private / JOURNAL_REL, journal)
    except BaseException as exc:
        try:
            rollback(roots, journal)
        except BaseException as rollback_error:
            raise RuntimeError("R39 integration failed and exact recovery requires intervention") from rollback_error
        raise RuntimeError(
            f"R39 integration failed and rolled back exactly: {type(exc).__name__}: {exc}"
        ) from exc
    # Work-directory removal is post-commit housekeeping and can never trigger
    # rollback of already verified committed outputs.
    try:
        shutil.rmtree(root)
        journal["work_directory_cleanup"] = "COMPLETE"
    except OSError as cleanup_error:
        journal["work_directory_cleanup"] = f"PENDING_RETRY: {type(cleanup_error).__name__}"
    try:
        write_journal(roots.private / JOURNAL_REL, journal)
    except OSError:
        pass
    return journal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", "--dry-run", dest="check", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--private-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--canonical-root", type=Path)
    parser.add_argument("--at")
    parser.add_argument("--expected-fresh-preimage-sha256")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roots: Roots | None = None
    mutation_attempted = False
    try:
        require_sealed_bindings()
        roots = Roots.make(args.private_root, args.repo_root, args.canonical_root)
        integrated_at = validate_time(args.at)
        existing = load_journal(roots)
        if existing is not None and existing.get("status") == "COMMITTED":
            verify_outputs(roots, existing)
            print(
                json.dumps(
                    {
                        "schema": "agko-r39-integration-report-v1",
                        "mode": "already_committed",
                        "result": R39_RESULT,
                        "transaction_id": existing["transaction_id"],
                        "fresh_preimage_sha256": existing["fresh_preimage_sha256"],
                        "outputs": existing["postimages"],
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )
            return
        if existing is not None and existing.get("status") not in {"ROLLED_BACK"}:
            if args.check:
                raise RuntimeError("an incomplete R39 transaction journal requires --execute recovery")
            with mutex(MUTEX_NAME):
                current = load_journal(roots)
                if current is None or current.get("status") == "ROLLED_BACK":
                    raise RuntimeError("R39 recovery state changed while acquiring the mutex; rerun --check")
                if current.get("status") == "COMMITTED":
                    verify_outputs(roots, current)
                    print(
                        json.dumps(
                            {
                                "schema": "agko-r39-integration-report-v1",
                                "mode": "already_committed_after_mutex_wait",
                                "result": R39_RESULT,
                                "transaction_id": current["transaction_id"],
                                "fresh_preimage_sha256": current["fresh_preimage_sha256"],
                                "outputs": current["postimages"],
                            },
                            ensure_ascii=True,
                            indent=2,
                        )
                    )
                    return
                mutation_attempted = True
                rollback(roots, current)
            raise RuntimeError("the incomplete R39 transaction was rolled back exactly; rerun --check before execution")
        inputs, preimages, outputs, evidence, fresh_digest = build_plan(roots, integrated_at)
        report = {
            "schema": "agko-r39-integration-report-v1",
            "mode": "check" if args.check else "execute",
            "integrated_at": integrated_at,
            "fresh_preimage_sha256": fresh_digest,
            "r38_public_closure": evidence["closure"],
            "candidate": dict(SEALED["candidate"]),
            "target_preimage": dict(R38_TARGET),
            "target_postimage": dict(SEALED["postimage"]),
            "control": evidence["control"],
            "outputs": postimage_rows(outputs, roots),
            "writes_performed": False,
            "result": "PASS_R39_INTEGRATION_CHECK_READY",
        }
        if args.check:
            print(json.dumps(report, ensure_ascii=True, indent=2))
            return
        require(args.at is not None, "--execute requires the exact --at printed by --check")
        require(args.expected_fresh_preimage_sha256 is not None, "--execute requires --expected-fresh-preimage-sha256 from --check")
        with mutex(MUTEX_NAME) as abandoned:
            # Rebuild the entire plan while holding the mutex.  The operator
            # token must still match the freshly observed state.
            inputs, preimages, outputs, evidence, fresh_digest = build_plan(roots, integrated_at)
            require(
                args.expected_fresh_preimage_sha256 == fresh_digest,
                "operator-bound fresh-preimage SHA-256 mismatch",
            )
            mutation_attempted = True
            journal = execute_plan(
                roots,
                integrated_at,
                inputs,
                preimages,
                outputs,
                fresh_digest,
                args.expected_fresh_preimage_sha256,
            )
            if abandoned:
                journal["abandoned_mutex_recovered"] = True
                write_journal(roots.private / JOURNAL_REL, journal)
        report.update(
            {
                "writes_performed": True,
                "result": R39_RESULT,
                "transaction_id": journal["transaction_id"],
                "outputs": journal["postimages"],
            }
        )
        print(json.dumps(report, ensure_ascii=True, indent=2))
    except Exception as exc:
        journal_observation: dict[str, Any] | None = None
        if roots is not None:
            journal_path = roots.private / JOURNAL_REL
            if journal_path.exists() and journal_path.is_file() and not journal_path.is_symlink():
                try:
                    observed = json.loads(journal_path.read_text(encoding="utf-8"))
                    journal_observation = {
                        "status": observed.get("status") if isinstance(observed, dict) else "MALFORMED",
                        **ident(journal_path),
                    }
                except Exception:
                    journal_observation = {"status": "UNREADABLE_OR_MALFORMED"}
        print(
            json.dumps(
                {
                    "schema": "agko-r39-integration-report-v1",
                    "result": "FAIL_CLOSED",
                    "error": str(exc),
                    "writes_performed": mutation_attempted,
                    "transaction_journal_observation": journal_observation,
                },
                ensure_ascii=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
