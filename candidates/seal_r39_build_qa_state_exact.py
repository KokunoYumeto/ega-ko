#!/usr/bin/env python3
"""Hash-guarded R39 build/PDF-QA state projection transaction.

This transaction advances only live/current state projections from the exact
R39 translation-integration preimage to the already-proven build/PDF-QA and
release-evidence checkpoint.  It deliberately preserves the historical R39
integration and reseal objects, the public R38 closure, and every still-pending
package, portable replay, GitHub, Zenodo, and anonymous-readback gate.

No TeX, Git, network, publication, source, target, unit-index, or terminology
operation is performed here.
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
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Mapping


VERSION = "2026-09-06-r39"
RESULT = "PASS_R39_BUILD_PDF_QA_STATE_SEAL"
WORKING_STATUS = (
    "PASS_R39_BUILD_PDF_QA_AND_RELEASE_EVIDENCE; package, portable replay, "
    "GitHub, Zenodo and anonymous public-byte readback pending"
)
WORKING_PHASE = "working_r39_build_pdf_qa_release_evidence_pass_package_portable_publication_pending"
R39_CANDIDATE_STATUS = "BUILD_PDF_QA_RELEASE_EVIDENCE_PASS_PACKAGE_PORTABLE_PUBLICATION_PENDING"
MUTEX_NAME = "Global\\InterlanguageAGKOR39BuildQAStateSealV1"

EXACT_DOI = "10.5281/zenodo.22416007"
RECORD_ID = 22_416_007
CONCEPT_DOI = "10.5281/zenodo.21921513"
R38_VERSION = "2026-09-05-r38"
R38_EXACT_DOI = "10.5281/zenodo.22346664"
R38_RECORD_ID = 22_346_664
R38_TAG = "ega-ko-2026-09-05-r38"
R38_RELEASE = "https://github.com/KokunoYumeto/ega-ko/releases/tag/ega-ko-2026-09-05-r38"
R38_RECORD = "https://zenodo.org/records/22346664"
R38_STATUS = "PASS_R38_PUBLIC_OPEN_DUAL_DESTINATION_AND_ANONYMOUS_BYTE_REPLAY"
R38_PREVIOUS_DOI = "10.5281/zenodo.22315714"

COVERAGE = (
    "EGA 0_I and EGA I complete; EGA II programme/table of contents complete; "
    "EGA II main text translated contiguously through §2.2.6 / canonical lines1-1780. "
    "EGA II and the full EGA corpus remain incomplete."
)
NEXT_SOURCE = (
    "EGA II canonical source/ega2/ega2-1-fr.tex line1782, environment §2.2.7; "
    "line1781 is blank"
)
NEXT_ACTION = (
    "Package the exact R39 checkpoint, run its serialized portable replay, then publish the "
    "same four hash-bound artifacts to the existing GitHub and Zenodo Korean EGA lineages "
    "and complete anonymous byte readback."
)
CURRENT_PUBLIC_CHECKPOINT = (
    "r38 / exact DOI10.5281/zenodo.22346664 / GitHub release "
    "ega-ko-2026-09-05-r38; four artifacts at both destinations passed anonymous byte replay"
)
PUBLICATION_RULE = (
    "R39 is a reserved, unpublished working checkpoint whose strict build, PDF QA and release-"
    "evidence gates pass. R38 remains the latest public checkpoint until R39 packaging, portable "
    "replay, both publications and anonymous public-byte readback pass."
)

SOURCE = {
    "path": "source/ega2/ega2-1-fr.tex",
    "whole_bytes": 820_504,
    "whole_lf_lines": 18_087,
    "whole_sha256": "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E",
    "admitted_lines": "1-1780",
    "admitted_bytes": 81_885,
    "admitted_sha256": "033E312D8BD9E22AEC1D5B8AC5705ED71C64C4E4DCFBB7ED84B9A434313ACE33",
}
UNIT = {
    "lines": "1685-1780",
    "bytes": 3_796,
    "characters": 3_740,
    "lf_lines": 96,
    "sha256": "BE7EC704F82B9283A48AFF1A01D7CF34F14A2C29F1B50269511DD699514BBC21",
}
CANDIDATE = {
    "path": "candidates/r39-c2s1-continuation.tex",
    "bytes": 4_051,
    "characters": 2_771,
    "lf_lines": 100,
    "sha256": "E8F52EDEC11B90D3CCC4E2398279DA4DEA7A6064AABFBE87D1765D55FEDE1940",
}
TARGET = {
    "path": "source/c2s1.tex",
    "bytes": 84_274,
    "characters": 58_678,
    "lf_lines": 1_809,
    "sha256": "59D07958D5CE1765F4901202CE97B3AC6257F6DC6C0D114C37B314C6A6EB1943",
    "separator_line": 1_709,
    "candidate_target_lines": "1710-1809",
    "private_public_exact": True,
}
READER = {
    "name": "00_EGA_ko_CUMULATIVE_READER.pdf",
    "path": "reader/00_EGA_ko_CUMULATIVE_READER.pdf",
    "pages": 240,
    "bytes": 1_491_216,
    "sha256": "AB24AAA5A4FBEAC3528892EF998C93276BF6DD38E7520C5F18A316E3FBAEAA6F",
}
MANIFEST = {
    "path": "source/CUMULATIVE_INPUTS.json",
    "bytes": 16_281,
    "sha256": "1F414A48D02837E9999205DC7E1B9468016A687605F5594DADAEDA4616EB21FB",
    "ordered_inputs": 17,
    "canonical_rows": 23,
    "complete": 16,
    "partial": 1,
    "not_translated": 6,
    "historical_markers": 229,
}
GATES = {
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
}

CONTROL_PRIVATE_REL = Path("controls/R39_BUILD_QA_STATE_SEAL.json")
CONTROL_PUBLIC_REL = Path("pub/ega-ko/evidence/controls/R39_BUILD_QA_STATE_SEAL.json")

PRIVATE_JSONS = ("cursor.json", "state.json", "authority.json")
PUBLIC_ALIASES = (
    "CURSOR.json",
    "PROGRAM_CURSOR.json",
    "STATE.json",
    "PROGRAM_STATE.json",
    "QA_STATE.json",
    "SOURCE_AUTHORITY.json",
    "PROGRAM_AUTHORITY.json",
    "VISUAL_QA.json",
    "DATACITE_RELATIONS.json",
)
LEDGERS = ("decisions.jsonl", "evidence.jsonl", "hard.jsonl")
LEDGER_IDS = {
    "decisions.jsonl": "AGKO-D191",
    "evidence.jsonl": "AGKO-E-R39-BUILD-QA-STATE-SEAL",
    "hard.jsonl": "AGKO-H166",
}

# These are the exact live inputs after the R39 ideal-terminology reseal.
PREIMAGE_EXPECTED: dict[str, dict[str, Any]] = {
    "private/cursor.json": {"bytes": 17_642, "sha256": "47DC989FC00DB30891334EEE1F6EDF173DFE0EC32DD4FE0B7AAEE7746721E3E1"},
    "private/state.json": {"bytes": 60_903, "sha256": "634F3B8F642C9507DF6AA02D6A9E0A9CBD79908EA8F9AAC91A0195A6A175981F"},
    "private/authority.json": {"bytes": 15_222, "sha256": "DA339D1455CDD2A6A46348CC373C67549BF672296544488DB6CF58F867A89F3D"},
    "private/decisions.jsonl": {"bytes": 711_878, "sha256": "6701FD6C3161E86C0398518317A2861E9BFC3A49E2574493579AC5E2563A5392"},
    "private/evidence.jsonl": {"bytes": 549_327, "sha256": "25B0C8FD2E5790CE473BF74CEC3F1BBC3A7272FF5A1861A81B8448F5C1597DFE"},
    "private/hard.jsonl": {"bytes": 305_970, "sha256": "F3D2908D494AB7ABC929E4FF33FB9880ADA127CE8D74401699F1CA8F57BE187E"},
    "public/evidence/CURSOR.json": {"bytes": 18_298, "sha256": "FA0A7890F1554CEC67E270E45E616DA6BBD08167D836854CC8308A3E939D67EF"},
    "public/evidence/PROGRAM_CURSOR.json": {"bytes": 18_491, "sha256": "34E0B808F6EA6F465A3A513F913E3C304673D67182CE8B4DF5C4B777996A6B3F"},
    "public/evidence/STATE.json": {"bytes": 21_065, "sha256": "1247DE40241F46223B0FA3E18E7B733646821AD16F7A111B7F460FFC256BD3FD"},
    "public/evidence/PROGRAM_STATE.json": {"bytes": 21_065, "sha256": "1247DE40241F46223B0FA3E18E7B733646821AD16F7A111B7F460FFC256BD3FD"},
    "public/evidence/QA_STATE.json": {"bytes": 19_168, "sha256": "A52083D87C6FF19E1A9BC40A3CDC504E948E1385653A5B991CB4E426887D460D"},
    "public/evidence/SOURCE_AUTHORITY.json": {"bytes": 17_772, "sha256": "E7BDFBC8F9371A9FF28A581CC8FBEA903564EADD4BB7D92AF43461A7153CBE8D"},
    "public/evidence/PROGRAM_AUTHORITY.json": {"bytes": 22_985, "sha256": "565FE9752F983B3F779EE78C4153F92B9BF23A7E3A4BD93F192ECBBA036B4166"},
    "public/evidence/VISUAL_QA.json": {"bytes": 17_881, "sha256": "7E6533B215E3A81153E8AFB39287E272F57044C096804722EEFCAFE81662B24D"},
    "public/evidence/DATACITE_RELATIONS.json": {"bytes": 17_104, "sha256": "6D355A9150634A4345D10B92C175BFA2E67AF825E31D120C3E173CEEC7A00C0F"},
    "public/evidence/decisions.jsonl": {"bytes": 714_910, "sha256": "2E3503E2DE343FCA1AE2D7D6825A2617DDFF7E848196CEA5D47AA5F174DDFC23"},
    "public/evidence/evidence.jsonl": {"bytes": 550_441, "sha256": "BE3A533DA36BD97C5105FDA039C31C8D93EDF75FF625E75BA3E788C0A4FA1C5D"},
    "public/evidence/hard.jsonl": {"bytes": 307_980, "sha256": "B3CF641E81035D4CC0245F559F54E6669E6BECEFAAB545C17415FDCD59B8AF56"},
    "private/controls/R39_BUILD_QA_STATE_SEAL.json": {"exists": False},
    "public/evidence/controls/R39_BUILD_QA_STATE_SEAL.json": {"exists": False},
}

UNCHANGED_EXPECTED: dict[str, dict[str, Any]] = {
    "private/index/units.jsonl": {"bytes": 1_257_226, "sha256": "C82B56845193A8A20438F78F9924006C82AC84CDC50ABD57BF8F4408160D50E2"},
    "public/evidence/index/units.jsonl": {"bytes": 1_257_249, "sha256": "84DB52C484E5DBAF1500C7529F82944739F45D0A1FFBD060E7EE33A58F82095A"},
    "private/terms.jsonl": {"bytes": 263_512, "sha256": "756644F578732E9A41770CB6EE86F3BD6C39331AAA0A39F84A06FCA4A054D250"},
    "public/evidence/terms.jsonl": {"bytes": 263_512, "sha256": "756644F578732E9A41770CB6EE86F3BD6C39331AAA0A39F84A06FCA4A054D250"},
}

PREREQUISITES: dict[str, dict[str, Any]] = {
    "private/controls/R39_STRICT_BUILD.json": {"bytes": 14_551, "sha256": "BD631DCAE7E8F9C485D9CEB14CE0DFA53CAE3F2BD5F0144ED9C3E0DEA7016BE0"},
    "public/evidence/controls/R39_STRICT_BUILD.json": {"bytes": 14_551, "sha256": "BD631DCAE7E8F9C485D9CEB14CE0DFA53CAE3F2BD5F0144ED9C3E0DEA7016BE0"},
    "private/controls/R39_VISUAL_QA_PREPARATION.json": {"bytes": 4_310, "sha256": "991D85DB3947110E98FCCF4A12E0570F78D27F092CD47114251BCB58B953412B"},
    "public/evidence/controls/R39_VISUAL_QA_PREPARATION.json": {"bytes": 4_310, "sha256": "991D85DB3947110E98FCCF4A12E0570F78D27F092CD47114251BCB58B953412B"},
    "private/controls/R39_PDF_QA.json": {"bytes": 14_710, "sha256": "9FF6981048F0F8C632B5F44BEE9437B7B3DA7134CC35D1919B34912C6BAE707B"},
    "public/evidence/controls/R39_PDF_QA.json": {"bytes": 14_710, "sha256": "9FF6981048F0F8C632B5F44BEE9437B7B3DA7134CC35D1919B34912C6BAE707B"},
    "private/controls/R39_BUILD_RECEIPT.json": {"bytes": 5_245, "sha256": "4C32901CEEDB6AC59A1924D743B53397D0F0C23E69793BB068B30F071D112928"},
    "public/evidence/BUILD_RECEIPT.json": {"bytes": 5_245, "sha256": "4C32901CEEDB6AC59A1924D743B53397D0F0C23E69793BB068B30F071D112928"},
    "private/controls/R39_ZENODO_DRAFT_RESERVATION.json": {"bytes": 1_444, "sha256": "8799F847CCDCD35D93A401F125A830CB1759F8E2D16004E90A185979F398D7CA"},
    "public/evidence/controls/R39_ZENODO_DRAFT_RESERVATION.json": {"bytes": 1_444, "sha256": "8799F847CCDCD35D93A401F125A830CB1759F8E2D16004E90A185979F398D7CA"},
    "private/ega/II/c2s1.tex": {"bytes": 84_274, "sha256": "59D07958D5CE1765F4901202CE97B3AC6257F6DC6C0D114C37B314C6A6EB1943"},
    "public/source/c2s1.tex": {"bytes": 84_274, "sha256": "59D07958D5CE1765F4901202CE97B3AC6257F6DC6C0D114C37B314C6A6EB1943"},
    "public/source/CUMULATIVE_INPUTS.json": {"bytes": 16_281, "sha256": "1F414A48D02837E9999205DC7E1B9468016A687605F5594DADAEDA4616EB21FB"},
    "public/reader/00_EGA_ko_CUMULATIVE_READER.pdf": {"bytes": 1_491_216, "sha256": "AB24AAA5A4FBEAC3528892EF998C93276BF6DD38E7520C5F18A316E3FBAEAA6F"},
}

PRIVATE_SCHEMAS = {
    "cursor.json": ("schema", "ag-ko-cursor-v3"),
    "state.json": ("schema", "ag-ko-state-v2"),
    "authority.json": ("schema", "ag-ko-authority-v3"),
}
PUBLIC_SCHEMAS = {
    "CURSOR.json": ("schema_version", 4),
    "PROGRAM_CURSOR.json": ("schema_version", 4),
    "STATE.json": ("schema_version", 4),
    "PROGRAM_STATE.json": ("schema_version", 4),
    "QA_STATE.json": ("schema_version", 4),
    "SOURCE_AUTHORITY.json": ("schema_version", 4),
    "PROGRAM_AUTHORITY.json": ("schema", "ag-ko-program-authority-public-v3"),
    "VISUAL_QA.json": ("schema_version", 4),
    "DATACITE_RELATIONS.json": ("schema_version", 2),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def identity_bytes(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha_bytes(data)}


def identity_file(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"required regular file absent: {path}")
    return identity_bytes(path.read_bytes())


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def jsonl_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def parse_json(data: bytes, label: str) -> dict[str, Any]:
    require(data.startswith(b"{") and data.endswith(b"\n"), f"noncanonical JSON envelope: {label}")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid JSON: {label}: {exc}") from exc
    require(isinstance(value, dict), f"JSON root is not an object: {label}")
    return value


def parse_jsonl(data: bytes, label: str) -> list[dict[str, Any]]:
    require(data.endswith(b"\n"), f"JSONL lacks terminal LF: {label}")
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(data.splitlines(), 1):
        require(bool(raw), f"blank JSONL record: {label}:{number}")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"invalid JSONL: {label}:{number}: {exc}") from exc
        require(isinstance(value, dict), f"JSONL row is not an object: {label}:{number}")
        rows.append(value)
    return rows


def validate_time(value: str | None) -> str:
    if value is None:
        value = datetime.now().astimezone().isoformat(timespec="seconds")
    require(
        bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", value)),
        "--at must be a timezone-qualified ISO timestamp at second precision",
    )
    return value


@dataclass(frozen=True)
class Roots:
    private: Path
    repo: Path

    @classmethod
    def make(cls, private: Path) -> "Roots":
        root = private.resolve(strict=True)
        repo = (root / "pub/ega-ko").resolve(strict=True)
        require(repo.parent.parent == root, "unexpected Korean EGA repository location")
        return cls(root, repo)


def resolve_role(role: str, roots: Roots) -> Path:
    if role.startswith("private/"):
        base, relative = roots.private, role.removeprefix("private/")
    elif role.startswith("public/"):
        base, relative = roots.repo, role.removeprefix("public/")
    else:
        raise RuntimeError(f"unknown path role: {role}")
    path = (base / Path(relative)).resolve(strict=False)
    require(path.is_relative_to(base), f"unsafe path role: {role}")
    return path


def role_for(path: Path, roots: Roots) -> str:
    resolved = path.resolve(strict=False)
    if resolved.is_relative_to(roots.repo):
        return "public/" + resolved.relative_to(roots.repo).as_posix()
    if resolved.is_relative_to(roots.private):
        return "private/" + resolved.relative_to(roots.private).as_posix()
    raise RuntimeError(f"path outside exact roots: {path}")


def expected_identity(path: Path, expected: Mapping[str, Any], label: str) -> None:
    if expected.get("exists") is False:
        require(not path.exists() and not path.is_symlink(), f"expected absent preimage exists: {label}")
        return
    actual = identity_file(path)
    require(actual == {"bytes": expected["bytes"], "sha256": expected["sha256"]}, f"identity drift: {label}: {actual}")


def validate_fixed_inputs(roots: Roots) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    script = Path(__file__).resolve(strict=True)
    rows.append({"path": "private/candidates/seal_r39_build_qa_state_exact.py", **identity_file(script)})
    for role, expected in PREREQUISITES.items():
        path = resolve_role(role, roots)
        expected_identity(path, expected, role)
        rows.append({"path": role, **identity_file(path)})
    for role, expected in UNCHANGED_EXPECTED.items():
        expected_identity(resolve_role(role, roots), expected, role)
    require(
        (roots.private / "controls/R39_STRICT_BUILD.json").read_bytes()
        == (roots.repo / "evidence/controls/R39_STRICT_BUILD.json").read_bytes(),
        "strict-build control mirrors differ",
    )
    require(
        (roots.private / "controls/R39_PDF_QA.json").read_bytes()
        == (roots.repo / "evidence/controls/R39_PDF_QA.json").read_bytes(),
        "PDF-QA control mirrors differ",
    )
    require(
        (roots.private / "controls/R39_BUILD_RECEIPT.json").read_bytes()
        == (roots.repo / "evidence/BUILD_RECEIPT.json").read_bytes(),
        "build-receipt mirrors differ",
    )
    require(
        (roots.private / "controls/R39_VISUAL_QA_PREPARATION.json").read_bytes()
        == (roots.repo / "evidence/controls/R39_VISUAL_QA_PREPARATION.json").read_bytes(),
        "visual-preparation control mirrors differ",
    )
    require(
        (roots.private / "controls/R39_ZENODO_DRAFT_RESERVATION.json").read_bytes()
        == (roots.repo / "evidence/controls/R39_ZENODO_DRAFT_RESERVATION.json").read_bytes(),
        "Zenodo-reservation control mirrors differ",
    )
    require(
        (roots.private / "ega/II/c2s1.tex").read_bytes() == (roots.repo / "source/c2s1.tex").read_bytes(),
        "current R39 target mirrors differ",
    )
    strict = parse_json((roots.private / "controls/R39_STRICT_BUILD.json").read_bytes(), "R39 strict build")
    qa = parse_json((roots.private / "controls/R39_PDF_QA.json").read_bytes(), "R39 PDF QA")
    receipt = parse_json((roots.private / "controls/R39_BUILD_RECEIPT.json").read_bytes(), "R39 build receipt")
    reservation = parse_json((roots.private / "controls/R39_ZENODO_DRAFT_RESERVATION.json").read_bytes(), "R39 reservation")
    require(strict.get("status") == "PASS_R39_STRICT_TWO_CYCLE_FOUR_PASS_BUILD", "strict-build status drift")
    require(qa.get("status") == "PASS", "PDF-QA status drift")
    require(receipt.get("result") == "PASS_R39_RELEASE_EVIDENCE", "build-receipt status drift")
    require(reservation.get("status") == "reserved_unpublished", "reservation state drift")
    require(reservation.get("record_id") == RECORD_ID and reservation.get("exact_doi") == EXACT_DOI, "reserved DOI drift")
    require(strict.get("reader", {}).get("sha256") == READER["sha256"], "strict-build reader drift")
    require(qa.get("pdf", {}).get("sha256") == READER["sha256"], "PDF-QA reader drift")
    require(receipt.get("reader", {}).get("sha256") == READER["sha256"], "build-receipt reader drift")
    require(receipt.get("target", {}).get("sha256") == TARGET["sha256"], "build-receipt target drift")
    require(receipt.get("source_manifest", {}).get("sha256") == MANIFEST["sha256"], "build-receipt manifest drift")
    return rows


def working_release() -> dict[str, Any]:
    return {
        "version": VERSION,
        "record_id": RECORD_ID,
        "exact_doi": EXACT_DOI,
        "exact_doi_url": f"https://doi.org/{EXACT_DOI}",
        "concept_doi": CONCEPT_DOI,
        "concept_doi_url": f"https://doi.org/{CONCEPT_DOI}",
        "status": "reserved_unpublished",
        "reservation": {
            "path": "evidence/controls/R39_ZENODO_DRAFT_RESERVATION.json",
            "bytes": 1_444,
            "sha256": "8799F847CCDCD35D93A401F125A830CB1759F8E2D16004E90A185979F398D7CA",
        },
        "latest_public_version_remains": R38_VERSION,
        "latest_public_exact_doi": R38_EXACT_DOI,
        "latest_public_record_id": R38_RECORD_ID,
        "latest_public_github_tag": R38_TAG,
    }


def control_refs(public: bool) -> dict[str, Any]:
    prefix = "evidence/controls/" if public else "controls/"
    return {
        "strict_build": {"path": prefix + "R39_STRICT_BUILD.json", "bytes": 14_551, "sha256": "BD631DCAE7E8F9C485D9CEB14CE0DFA53CAE3F2BD5F0144ED9C3E0DEA7016BE0"},
        "visual_preparation": {"path": prefix + "R39_VISUAL_QA_PREPARATION.json", "bytes": 4_310, "sha256": "991D85DB3947110E98FCCF4A12E0570F78D27F092CD47114251BCB58B953412B"},
        "pdf_qa": {"path": prefix + "R39_PDF_QA.json", "bytes": 14_710, "sha256": "9FF6981048F0F8C632B5F44BEE9437B7B3DA7134CC35D1919B34912C6BAE707B"},
        "build_receipt": {
            "path": "evidence/BUILD_RECEIPT.json" if public else "controls/R39_BUILD_RECEIPT.json",
            "bytes": 5_245,
            "sha256": "4C32901CEEDB6AC59A1924D743B53397D0F0C23E69793BB068B30F071D112928",
        },
        "zenodo_reservation": {"path": prefix + "R39_ZENODO_DRAFT_RESERVATION.json", "bytes": 1_444, "sha256": "8799F847CCDCD35D93A401F125A830CB1759F8E2D16004E90A185979F398D7CA"},
    }


def qa_summary(roots: Roots) -> dict[str, Any]:
    qa = parse_json((roots.private / "controls/R39_PDF_QA.json").read_bytes(), "R39 PDF QA")
    return {
        "translation": "PASS exact current-authority and mirrored R39 target validation through §2.2.6 / canonical lines1-1780",
        "build": "PASS two independent clean four-pass XeLaTeX cycles under Global\\InterlanguageTeXSlotV1; final cycles byte-identical; hard diagnostics0",
        "extractions": copy.deepcopy(qa["extractions"]),
        "historical_markers": copy.deepcopy(qa["historical_markers"]),
        "navigation": copy.deepcopy(qa["navigation"]),
        "fonts": copy.deepcopy(qa["font_unicode"]),
        "visual": copy.deepcopy(qa["visual_findings"]),
        "portable_replay": "PENDING",
        "detailed_control": "evidence/controls/R39_PDF_QA.json",
        "human_certification": "not claimed or required",
        "limitations": copy.deepcopy(qa["limitations"]),
    }


def checkpoint(roots: Roots, public: bool, at: str) -> dict[str, Any]:
    summary = qa_summary(roots)
    return {
        "status": WORKING_STATUS,
        "version": VERSION,
        "sealed_at": at,
        "coverage": {
            "terminal": "EGA II §2.2.6 / canonical lines1-1780",
            "next": "EGA II line1782 / environment2.2.7",
            "historical_markers": 229,
            "no_completion_claim": True,
        },
        "source": copy.deepcopy(SOURCE),
        "target": copy.deepcopy(TARGET),
        "reader": copy.deepcopy(READER),
        "manifest": copy.deepcopy(MANIFEST),
        "working_release": working_release(),
        "controls": control_refs(public),
        "qa": summary,
        "gates": copy.deepcopy(GATES),
        "latest_public_checkpoint": {
            "version": R38_VERSION,
            "status": R38_STATUS,
            "record_id": R38_RECORD_ID,
            "exact_doi": R38_EXACT_DOI,
            "github_tag": R38_TAG,
            "github_release": R38_RELEASE,
        },
        "claim_boundary": (
            "The recorded deterministic checks establish only the tested R39 build, extraction, "
            "navigation, font and inspected-render properties; they do not claim absolute perfection "
            "or completion of EGA II."
        ),
    }


def current_build_receipt(public: bool) -> dict[str, Any]:
    return {
        "receipt": "evidence/BUILD_RECEIPT.json" if public else "controls/R39_BUILD_RECEIPT.json",
        "receipt_bytes": 5_245,
        "receipt_sha256": "4C32901CEEDB6AC59A1924D743B53397D0F0C23E69793BB068B30F071D112928",
        "strict_control": ("evidence/controls/" if public else "controls/") + "R39_STRICT_BUILD.json",
        "strict_control_bytes": 14_551,
        "strict_control_sha256": "BD631DCAE7E8F9C485D9CEB14CE0DFA53CAE3F2BD5F0144ED9C3E0DEA7016BE0",
        "pdf_qa": ("evidence/controls/" if public else "controls/") + "R39_PDF_QA.json",
        "pdf_qa_bytes": 14_710,
        "pdf_qa_sha256": "9FF6981048F0F8C632B5F44BEE9437B7B3DA7134CC35D1919B34912C6BAE707B",
    }


def mutate_private(name: str, original: bytes, roots: Roots, at: str) -> bytes:
    data = parse_json(original, f"private {name}")
    key, expected = PRIVATE_SCHEMAS[name]
    require(data.get(key) == expected, f"private schema drift: {name}")
    require(data.get("r39_build_qa_checkpoint") is None, f"unexpected preexisting R39 state seal: {name}")
    data["updated"] = at
    data["current_working_status"] = WORKING_STATUS
    data["working_version"] = VERSION
    data["working_exact_doi"] = EXACT_DOI
    data["working_record_id"] = RECORD_ID
    data["working_reader"] = copy.deepcopy(READER)
    data["working_manifest"] = copy.deepcopy(MANIFEST)
    data["working_release_gates"] = copy.deepcopy(GATES)
    data["r39_build_qa_checkpoint"] = checkpoint(roots, False, at)
    data["next_executable_action"] = NEXT_ACTION
    if name == "cursor.json":
        data["local_status"] = WORKING_STATUS
        data["next"] = NEXT_ACTION
        data["r39_candidate_status"] = R39_CANDIDATE_STATUS
        data["latest_public_version_remains"] = R38_VERSION
        data["latest_public_exact_doi"] = R38_EXACT_DOI
        data["latest_public_record_id"] = R38_RECORD_ID
    elif name == "state.json":
        active = data.setdefault("active", {})
        active["reader"] = copy.deepcopy(READER)
        active["coverage_manifest"] = copy.deepcopy(MANIFEST)
        active["qa"] = {
            "r38_public_closure": "PASS_LATEST_PUBLIC",
            "r39_translation_and_reseals": "PASS",
            "r39_strict_build": "PASS",
            "r39_pdf_qa": "PASS",
            "r39_release_evidence": "PASS",
            "r39_package_and_portable_replay": "PENDING",
            "r39_github_zenodo_and_anonymous_readback": "PENDING",
        }
        active["next_target"] = NEXT_ACTION
        active["gate"] = WORKING_STATUS
        active["working_release"] = working_release()
        data["r39_candidate_status"] = R39_CANDIDATE_STATUS
    elif name == "authority.json":
        ega_ii = data.setdefault("ega_ii", {})
        require("lines1-1780" in str(ega_ii.get("status", "")), "private authority EGA II live coverage drift")
        ega_ii["status"] = (
            "canonical five-input packet present; Korean front/programme complete; main input translated "
            "and integrated contiguously through lines1-1780 /2.2.6; R39 strict build, PDF QA and release "
            "evidence PASS; package, portable replay and publication pending; EGA II active and incomplete; "
            "next source line1782"
        )
        data["working_release"] = working_release()
        data["publication_lineage"]["working_status"] = WORKING_STATUS
        data["publication_lineage"]["working_release"] = working_release()
    return json_bytes(data)


def mutate_public_generic(name: str, original: bytes, roots: Roots, at: str) -> dict[str, Any]:
    data = parse_json(original, f"public {name}")
    key, expected = PUBLIC_SCHEMAS[name]
    require(data.get(key) == expected, f"public schema drift: {name}")
    require(data.get("r39_build_qa_checkpoint") is None, f"unexpected preexisting R39 state seal: {name}")
    data["version"] = VERSION
    data["updated"] = at
    data["snapshot_phase"] = WORKING_PHASE
    data["coverage"] = COVERAGE
    data["reader"] = copy.deepcopy(READER)
    data["coverage_manifest"] = copy.deepcopy(MANIFEST)
    data["source"] = copy.deepcopy(SOURCE)
    data["unit"] = copy.deepcopy(UNIT)
    data["candidate"] = copy.deepcopy(CANDIDATE)
    data["target"] = copy.deepcopy(TARGET)
    data["concept_doi"] = CONCEPT_DOI
    if "exact_doi" in data:
        data["exact_doi"] = EXACT_DOI
    if "exact_version_doi" in data:
        data["exact_version_doi"] = EXACT_DOI
    if "record_id" in data:
        data["record_id"] = RECORD_ID
    if "previous_exact_version_doi" in data:
        data["previous_exact_version_doi"] = R38_EXACT_DOI
    data["working_exact_version_doi"] = EXACT_DOI
    data["working_record_id"] = RECORD_ID
    data["working_release"] = working_release()
    data["prior_public_checkpoint"] = CURRENT_PUBLIC_CHECKPOINT
    data["current_public_checkpoint"] = CURRENT_PUBLIC_CHECKPOINT
    data["publication_phase"] = WORKING_PHASE
    data["publication_evidence_rule"] = PUBLICATION_RULE
    data["current_working_status"] = WORKING_STATUS
    data["working_result"] = WORKING_STATUS
    data["r39_candidate_status"] = R39_CANDIDATE_STATUS
    data["working_translation_coverage"] = COVERAGE
    data["ega_ii_status"] = (
        "active_incomplete; R39 build/PDF QA/release evidence PASS through §2.2.6 / lines1-1780; "
        "package, portable replay and publication pending; latest public checkpoint R38"
    )
    data["next_source"] = NEXT_SOURCE
    data["working_release_gates"] = copy.deepcopy(GATES)
    data["validation_checkpoint"] = "evidence/controls/R39_PDF_QA.json"
    data["build_receipt"] = current_build_receipt(True)
    data["reader_scope"] = "R39 exact working reader; build and PDF QA PASS; publication pending"
    data["coverage_manifest_scope"] = "R39 exact working manifest through §2.2.6 / canonical lines1-1780"
    data["latest_public_version_remains"] = R38_VERSION
    data["latest_public_exact_doi"] = R38_EXACT_DOI
    data["latest_public_record_id"] = R38_RECORD_ID
    data["latest_public_github_tag"] = R38_TAG
    data["r39_build_qa_checkpoint"] = checkpoint(roots, True, at)
    return data


def r38_publication_from(data: Mapping[str, Any]) -> dict[str, Any]:
    public = copy.deepcopy(data.get("public_r38"))
    require(isinstance(public, dict) and public.get("version") == R38_VERSION, "public R38 binding drift")
    result = {
        "status": R38_STATUS,
        "version": R38_VERSION,
        "exact_version_doi": R38_EXACT_DOI,
        "record_id": R38_RECORD_ID,
        "concept_doi": CONCEPT_DOI,
        "prior_public_doi": R38_PREVIOUS_DOI,
        "github": copy.deepcopy(public["github"]),
        "github_artifact_commit": public["github"]["artifact_commit"],
        "annotated_tag": public["github"]["tag"],
        "release": public["github"]["release"],
        "active_destinations": ["Zenodo", "GitHub"],
        "control": copy.deepcopy(public["control"]),
        "reader": copy.deepcopy(public["reader"]),
        "zenodo": copy.deepcopy(public["zenodo"]),
        "public_artifacts": copy.deepcopy(public["public_artifacts"]),
        "package": copy.deepcopy(public["package"]),
        "portable_replay": copy.deepcopy(public["portable_replay"]),
        "coverage": public["coverage"],
        "ega_ii_status": public["ega_ii_status"],
        "next_source": public["next_source"],
        "working_status": WORKING_STATUS,
        "latest_public_checkpoint_remains": R38_VERSION,
        "working_release": working_release(),
    }
    return result


def mutate_public(name: str, original: bytes, roots: Roots, at: str) -> bytes:
    data = mutate_public_generic(name, original, roots, at)
    summary = qa_summary(roots)
    if name in {"CURSOR.json", "PROGRAM_CURSOR.json"}:
        data["completed_through"] = "working Korean EGA II through §2.2.6 / canonical lines1-1780"
    if name in {"STATE.json", "PROGRAM_STATE.json"}:
        data["result"] = WORKING_STATUS
        data["qa"] = summary
        data["release_gates"] = copy.deepcopy(GATES)
        data["last_public_result"] = R38_STATUS
    elif name == "QA_STATE.json":
        data["result"] = WORKING_STATUS
        data["qa"] = summary
        data["working_translation_gate"] = "PASS_R39_TRANSLATION_BUILD_PDF_QA_RELEASE_EVIDENCE"
        data["r39_qa_status"] = "PASS_BUILD_PDF_QA_RELEASE_EVIDENCE; portable replay and publication pending"
    elif name == "VISUAL_QA.json":
        visual = summary["visual"]
        data["dpi"] = visual["dpi"]
        data["pages"] = copy.deepcopy(visual["selected_physical_pages"])
        data["dimensions"] = "2481x3508"
        data["result"] = (
            "PASS on thirteen inspected 300-dpi pages: no observed clipping, overlap, tofu, broken formula "
            "or unreadable text; deterministic whole-document checks are separately bound by R39_PDF_QA.json"
        )
        data["detailed_render_identities"] = "evidence/controls/R39_PDF_QA.json"
        data["historical_markers"] = copy.deepcopy(summary["historical_markers"])
        data["links"] = copy.deepcopy(summary["navigation"])
        data["r39_qa_status"] = "PASS_NO_OBSERVED_DEFECTS_ON_EXACT_SELECTED_RENDERS"
    elif name == "PROGRAM_AUTHORITY.json":
        data["scope"] = COVERAGE
        data["canonical_source"] = "[CANONICAL_SOURCE_ROOT]/source/ega2/ega2-1-fr.tex"
        data["canonical_source_bytes"] = SOURCE["whole_bytes"]
        data["canonical_source_sha256"] = SOURCE["whole_sha256"]
        data["current_bindings"] = {
            "canonical_prefix": copy.deepcopy(SOURCE),
            "translated_unit": copy.deepcopy(UNIT),
            "translation_candidate": copy.deepcopy(CANDIDATE),
            "korean_target": copy.deepcopy(TARGET),
            "cumulative_manifest": copy.deepcopy(MANIFEST),
            "reader": copy.deepcopy(READER),
            "translation_integration": {
                "path": "evidence/controls/R39_TRANSLATION_INTEGRATION.json",
                "bytes": 6_610,
                "sha256": "BA1B7D43FC93365C21F86E7D1494CB59483DA7863EF16E4B5D80BFF48161AF6B",
            },
            "authority_comment_reseal": {
                "path": "evidence/controls/R39_AUTHORITY_COMMENT_RESEAL.json",
                "bytes": 5_469,
                "sha256": "63B55B0B04FA708E31434A84EE5CE57A66157380BB82615F872E83E8028A8080",
            },
            "ideal_terminology_reseal": {
                "path": "evidence/controls/R39_IDEAL_TERMINOLOGY_RESEAL.json",
                "bytes": 12_197,
                "sha256": "2F88570A3523DE0718F3952C842FE00D5D8337DC0D9DF4AC93C20D9D263AF624",
            },
            "strict_build": control_refs(True)["strict_build"],
            "pdf_qa": control_refs(True)["pdf_qa"],
            "release_evidence": control_refs(True)["build_receipt"],
        }
        data["publication"] = r38_publication_from(data)
    elif name == "DATACITE_RELATIONS.json":
        data["release_state"] = "reserved_unpublished_build_pdf_qa_pass_package_portable_publication_pending"
        data["publication_status"] = "R39_RESERVED_UNPUBLISHED_BUILD_PDF_QA_RELEASE_EVIDENCE_PASS"
        data["public_record_url"] = R38_RECORD
        data["github_release"] = R38_RELEASE
        data["working_version_status"] = WORKING_STATUS
        data["latest_public_version_remains"] = R38_VERSION
        data["latest_public_record_id"] = R38_RECORD_ID
        data["latest_public_exact_doi"] = R38_EXACT_DOI
        data["working_record_id"] = RECORD_ID
        data["working_exact_version_doi"] = EXACT_DOI
    return json_bytes(data)


def ledger_records(at: str, token: str) -> dict[str, dict[str, Any]]:
    common = {"time": at, "precision": "second"}
    return {
        "decisions.jsonl": {
            "id": "AGKO-D191",
            **common,
            "kind": "r39_build_pdf_qa_state_seal",
            "scope": "R39 cumulative Korean EGA live state projections and immutable build/PDF-QA evidence",
            "choice": (
                "Promote only the live R39 aliases to the exact 240-page reader, current manifest, current "
                "target and proven build/PDF-QA/release-evidence status; preserve R38 as the latest public "
                "checkpoint and keep package, portable replay, GitHub, Zenodo and anonymous readback pending."
            ),
            "evidence": [
                f"reader {READER['bytes']}B/{READER['sha256']}",
                f"source/CUMULATIVE_INPUTS.json {MANIFEST['bytes']}B/{MANIFEST['sha256']}",
                "controls/R39_STRICT_BUILD.json 14551B/BD631DCAE7E8F9C485D9CEB14CE0DFA53CAE3F2BD5F0144ED9C3E0DEA7016BE0",
                "controls/R39_PDF_QA.json 14710B/9FF6981048F0F8C632B5F44BEE9437B7B3DA7134CC35D1919B34912C6BAE707B",
                "controls/R39_BUILD_RECEIPT.json 5245B/4C32901CEEDB6AC59A1924D743B53397D0F0C23E69793BB068B30F071D112928",
            ],
            "fresh_preimage_sha256": token,
            "uncertainty": (
                "The deterministic and inspected-render checks establish only their tested properties; "
                "they do not claim absolute perfection or completion of EGA II."
            ),
            "review": RESULT,
        },
        "evidence.jsonl": {
            "id": "AGKO-E-R39-BUILD-QA-STATE-SEAL",
            **common,
            "kind": "build_pdf_qa_state_projection_evidence",
            "version": VERSION,
            "coverage": "EGA II through §2.2.6 / canonical lines1-1780; next1782; incomplete",
            "target": copy.deepcopy(TARGET),
            "reader": copy.deepcopy(READER),
            "manifest": copy.deepcopy(MANIFEST),
            "working_release": working_release(),
            "controls": control_refs(False),
            "gates": copy.deepcopy(GATES),
            "fresh_preimage_sha256": token,
            "latest_public_version_remains": R38_VERSION,
            "result": RESULT,
        },
        "hard.jsonl": {
            "id": "AGKO-H166",
            **common,
            "status": "controlling_r39_build_pdf_qa_state_projection",
            "scope": "Every live metadata projection of the current R39 reader, manifest, target, DOI and release gates",
            "symptom": (
                "The exact R39 reader and QA receipts passed, but live aliases still exposed R37/R38 reader, "
                "manifest, QA, DOI or pending-build values."
            ),
            "resolution": (
                "Atomically project the exact R39 build/PDF-QA evidence while retaining historical target "
                "transitions and the R38 public closure, and distinguish the reserved unpublished R39 DOI "
                "from the latest public R38 DOI."
            ),
            "tests": (
                "fixed preimages; staged atomic replacements; exact rollback; normal and optimized replay; "
                "public-path sanitization; D191/E-state/H166 uniqueness; unit and terminology ledgers unchanged"
            ),
            "recurrence": (
                "After each immutable build/QA gate, seal live aliases before packaging; never promote pending "
                "package or publication gates by inference."
            ),
            "related": ["AGKO-D191", "AGKO-E-R39-BUILD-QA-STATE-SEAL"],
        },
    }


def append_record(original: bytes, record: Mapping[str, Any], label: str) -> bytes:
    rows = parse_jsonl(original, label)
    record_id = record["id"]
    require(sum(row.get("id") == record_id for row in rows) == 0, f"record already present: {record_id}")
    return original + jsonl_bytes(record)


def output_paths(roots: Roots) -> list[Path]:
    paths = [
        *(roots.private / name for name in PRIVATE_JSONS),
        *(roots.repo / "evidence" / name for name in PUBLIC_ALIASES),
        *(roots.private / name for name in LEDGERS),
        *(roots.repo / "evidence" / name for name in LEDGERS),
        roots.private / CONTROL_PRIVATE_REL,
        roots.private / CONTROL_PUBLIC_REL,
    ]
    require(len(paths) == len({path.resolve(strict=False) for path in paths}), "output inventory is not injective")
    return paths


def snapshot_preimages(roots: Roots) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for role, expected in PREIMAGE_EXPECTED.items():
        path = resolve_role(role, roots)
        expected_identity(path, expected, role)
        if expected.get("exists") is False:
            rows.append({"path": role, "exists": False})
        else:
            rows.append({"path": role, "exists": True, **identity_file(path)})
    require({row["path"] for row in rows} == {role_for(path, roots) for path in output_paths(roots)}, "preimage inventory drift")
    return sorted(rows, key=lambda row: row["path"].casefold())


def transaction_token(at: str, inputs: list[dict[str, Any]], preimages: list[dict[str, Any]]) -> str:
    payload = json_bytes({
        "schema": "agko-r39-build-qa-state-seal-preimage-v1",
        "sealed_at": at,
        "inputs": inputs,
        "preimages": preimages,
        "unchanged": [{"path": role, **value} for role, value in sorted(UNCHANGED_EXPECTED.items())],
    })
    return sha_bytes(payload)


def build_outputs(roots: Roots, at: str, token: str) -> tuple[dict[Path, bytes], bytes]:
    outputs: dict[Path, bytes] = {}
    for name in PRIVATE_JSONS:
        path = roots.private / name
        outputs[path] = mutate_private(name, path.read_bytes(), roots, at)
    for name in PUBLIC_ALIASES:
        path = roots.repo / "evidence" / name
        outputs[path] = mutate_public(name, path.read_bytes(), roots, at)
    records = ledger_records(at, token)
    for name in LEDGERS:
        private = roots.private / name
        public = roots.repo / "evidence" / name
        outputs[private] = append_record(private.read_bytes(), records[name], f"private {name}")
        outputs[public] = append_record(public.read_bytes(), records[name], f"public {name}")
    postimages = [
        {"path": role_for(path, roots), **identity_bytes(data)}
        for path, data in sorted(outputs.items(), key=lambda item: role_for(item[0], roots).casefold())
    ]
    control = {
        "schema": "agko-r39-build-qa-state-seal-v1",
        "id": "AGKO-R39-BUILD-QA-STATE-SEAL",
        "transaction_id": "AGKO-R39-BUILD-QA-STATE-SEAL-" + token[:20],
        "sealed_at": at,
        "precision": "second",
        "version": VERSION,
        "fresh_preimage_sha256": token,
        "working_release": working_release(),
        "coverage": {
            "terminal": "EGA II §2.2.6 / canonical lines1-1780",
            "next": "line1782 / environment2.2.7",
            "historical_markers": 229,
            "no_completion_claim": True,
        },
        "target": copy.deepcopy(TARGET),
        "reader": copy.deepcopy(READER),
        "manifest": copy.deepcopy(MANIFEST),
        "controls": control_refs(True),
        "gates": copy.deepcopy(GATES),
        "latest_public_checkpoint": {
            "version": R38_VERSION,
            "status": R38_STATUS,
            "record_id": R38_RECORD_ID,
            "exact_doi": R38_EXACT_DOI,
            "github_tag": R38_TAG,
        },
        "preimages": [
            {"path": role, **value} for role, value in sorted(PREIMAGE_EXPECTED.items())
            if value.get("exists") is not False
        ],
        "postimages": postimages,
        "unchanged_ledgers": [{"path": role, **value} for role, value in sorted(UNCHANGED_EXPECTED.items())],
        "appended_records": copy.deepcopy(LEDGER_IDS),
        "transaction": {
            "staged_same_volume_replacements": True,
            "per_file_os_replace": True,
            "exact_preimage_backups": True,
            "reverse_order_rollback_on_failure": True,
            "idempotent_replay": True,
            "source_target_unit_and_terms_mutation": False,
        },
        "public_projection": {
            "relative_paths_only": True,
            "reserved_unpublished_r39_distinct_from_latest_public_r38": True,
            "historical_r39_target_transitions_preserved": True,
        },
        "result": RESULT,
    }
    control_data = json_bytes(control)
    outputs[roots.private / CONTROL_PRIVATE_REL] = control_data
    outputs[roots.private / CONTROL_PUBLIC_REL] = control_data
    require(set(outputs) == set(output_paths(roots)), "output path inventory drift")
    return outputs, control_data


def validate_public_bytes(path: Path, data: bytes) -> None:
    text = data.decode("utf-8")
    require(
        re.search(r"(?<![A-Za-z0-9+.-])[A-Za-z]:[\\/]", text) is None,
        f"absolute Windows path leaked into public JSON: {path.name}",
    )
    require("C:/Users/" not in text and "C:\\Users\\" not in text, f"private user path leaked into public JSON: {path.name}")


def validate_outputs_in_memory(outputs: Mapping[Path, bytes], roots: Roots) -> None:
    for path, data in outputs.items():
        role = role_for(path, roots)
        if path.suffix == ".json":
            parse_json(data, role)
        elif path.suffix == ".jsonl":
            parse_jsonl(data, role)
        if role.startswith("public/") and path.suffix == ".json":
            validate_public_bytes(path, data)
    private_control = outputs[roots.private / CONTROL_PRIVATE_REL]
    require(private_control == outputs[roots.private / CONTROL_PUBLIC_REL], "state-seal control outputs differ")
    for name, record_id in LEDGER_IDS.items():
        a = [row for row in parse_jsonl(outputs[roots.private / name], f"private {name}") if row.get("id") == record_id]
        b = [row for row in parse_jsonl(outputs[roots.repo / "evidence" / name], f"public {name}") if row.get("id") == record_id]
        require(len(a) == len(b) == 1 and a[0] == b[0], f"ledger append mirror/multiplicity drift: {record_id}")
        require(parse_jsonl(outputs[roots.private / name], name)[-1]["id"] == record_id, f"private ledger tail drift: {name}")
        require(parse_jsonl(outputs[roots.repo / "evidence" / name], name)[-1]["id"] == record_id, f"public ledger tail drift: {name}")


def committed_controls(roots: Roots) -> tuple[Path, Path] | None:
    private = roots.private / CONTROL_PRIVATE_REL
    public = roots.private / CONTROL_PUBLIC_REL
    present = [private.exists() or private.is_symlink(), public.exists() or public.is_symlink()]
    require(present[0] == present[1], "partial state-seal control pair")
    return (private, public) if present[0] else None


def verify_committed(roots: Roots) -> dict[str, Any] | None:
    pair = committed_controls(roots)
    if pair is None:
        return None
    private, public = pair
    require(private.is_file() and public.is_file() and not private.is_symlink() and not public.is_symlink(), "state-seal controls are not regular files")
    private_data = private.read_bytes()
    require(private_data == public.read_bytes(), "state-seal controls differ")
    control = parse_json(private_data, "R39 build/QA state seal")
    require(control.get("schema") == "agko-r39-build-qa-state-seal-v1", "state-seal schema drift")
    require(control.get("result") == RESULT and control.get("version") == VERSION, "state-seal result/version drift")
    listed = control.get("postimages")
    require(isinstance(listed, list), "state-seal postimage inventory absent")
    expected_roles = {role_for(path, roots) for path in output_paths(roots)} - {
        "private/controls/R39_BUILD_QA_STATE_SEAL.json",
        "public/evidence/controls/R39_BUILD_QA_STATE_SEAL.json",
    }
    require({row.get("path") for row in listed} == expected_roles, "state-seal postimage inventory drift")
    for row in listed:
        actual = identity_file(resolve_role(row["path"], roots))
        require(actual == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"committed postimage drift: {row['path']}")
    for role, expected in UNCHANGED_EXPECTED.items():
        expected_identity(resolve_role(role, roots), expected, role)
    validate_fixed_inputs(roots)
    for name, record_id in LEDGER_IDS.items():
        a = [row for row in parse_jsonl((roots.private / name).read_bytes(), f"private {name}") if row.get("id") == record_id]
        b = [row for row in parse_jsonl((roots.repo / "evidence" / name).read_bytes(), f"public {name}") if row.get("id") == record_id]
        require(len(a) == len(b) == 1 and a[0] == b[0], f"committed ledger record drift: {record_id}")
        require(parse_jsonl((roots.private / name).read_bytes(), name)[-1]["id"] == record_id, f"committed ledger tail drift: {name}")
        require(parse_jsonl((roots.repo / "evidence" / name).read_bytes(), name)[-1]["id"] == record_id, f"committed public ledger tail drift: {name}")
    for name in PRIVATE_JSONS:
        value = parse_json((roots.private / name).read_bytes(), name)
        require(value.get("current_working_status") == WORKING_STATUS, f"private current status drift: {name}")
        require(value.get("r39_build_qa_checkpoint", {}).get("reader", {}).get("sha256") == READER["sha256"], f"private checkpoint drift: {name}")
    for name in PUBLIC_ALIASES:
        path = roots.repo / "evidence" / name
        value = parse_json(path.read_bytes(), name)
        validate_public_bytes(path, path.read_bytes())
        require(value.get("version") == VERSION, f"public working version drift: {name}")
        require(value.get("reader", {}).get("sha256") == READER["sha256"], f"public reader drift: {name}")
        require(value.get("target", {}).get("sha256") == TARGET["sha256"], f"public target drift: {name}")
        require(value.get("r39_build_qa_checkpoint", {}).get("gates", {}).get("pdf_qa") == "PASS", f"public checkpoint drift: {name}")
        require(value.get("latest_public_version_remains") == R38_VERSION, f"latest-public boundary drift: {name}")
    return {
        "control": {"private": role_for(private, roots), "public": role_for(public, roots), **identity_bytes(private_data)},
        "transaction_id": control["transaction_id"],
        "sealed_at": control["sealed_at"],
        "fresh_preimage_sha256": control["fresh_preimage_sha256"],
        "postimages": listed,
    }


@contextmanager
def transaction_mutex() -> Iterator[bool]:
    require(os.name == "nt", "Windows state transaction mutex required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    kernel.WaitForSingleObject.restype = ctypes.c_uint
    handle = kernel.CreateMutexW(None, 0, MUTEX_NAME)
    require(bool(handle), "state-seal mutex creation failed")
    wait = kernel.WaitForSingleObject(handle, 30_000)
    require(wait in (0, 0x80), "state-seal mutex acquisition timeout")
    try:
        yield wait == 0x80
    finally:
        kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def verify_current_preimages(roots: Roots, preimages: list[dict[str, Any]]) -> None:
    for row in preimages:
        path = resolve_role(row["path"], roots)
        if not row["exists"]:
            require(not path.exists() and not path.is_symlink(), f"preimage appeared concurrently: {row['path']}")
        else:
            require(identity_file(path) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"preimage changed concurrently: {row['path']}")


def execute_transaction(
    roots: Roots,
    outputs: Mapping[Path, bytes],
    preimages: list[dict[str, Any]],
    transaction_id: str,
) -> None:
    validate_outputs_in_memory(outputs, roots)
    base = (roots.private / "tmp").resolve(strict=True)
    work = (base / transaction_id).resolve(strict=False)
    require(work.parent == base, "unsafe transaction staging path")
    require(not work.exists(), "transaction staging path already exists")
    staged = work / "staged"
    backups = work / "backups"
    staged.mkdir(parents=True)
    backups.mkdir()
    before = {row["path"]: row for row in preimages}
    order = sorted(
        outputs,
        key=lambda path: (
            role_for(path, roots).endswith("R39_BUILD_QA_STATE_SEAL.json"),
            role_for(path, roots).casefold(),
        ),
    )
    applied: list[tuple[int, Path]] = []
    try:
        for index, path in enumerate(order):
            role = role_for(path, roots)
            stage = staged / f"{index:03d}.bin"
            with stage.open("xb") as stream:
                stream.write(outputs[path])
                stream.flush()
                os.fsync(stream.fileno())
            require(identity_file(stage) == identity_bytes(outputs[path]), f"staged output drift: {role}")
            row = before[role]
            if row["exists"]:
                backup = backups / f"{index:03d}.bin"
                shutil.copyfile(path, backup)
                with backup.open("r+b") as stream:
                    os.fsync(stream.fileno())
                require(identity_file(backup) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"backup drift: {role}")
        verify_current_preimages(roots, preimages)
        for index, path in enumerate(order):
            for remaining in order[index:]:
                row = before[role_for(remaining, roots)]
                if row["exists"]:
                    require(identity_file(remaining) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"concurrent mutation: {row['path']}")
                else:
                    require(not remaining.exists() and not remaining.is_symlink(), f"concurrent creation: {row['path']}")
            os.replace(staged / f"{index:03d}.bin", path)
            require(identity_file(path) == identity_bytes(outputs[path]), f"post-replace drift: {role_for(path, roots)}")
            applied.append((index, path))
        committed = verify_committed(roots)
        require(committed is not None, "transaction controls absent after apply")
    except BaseException as exc:
        rollback_errors: list[str] = []
        for index, path in reversed(applied):
            role = role_for(path, roots)
            row = before[role]
            try:
                require(identity_file(path) == identity_bytes(outputs[path]), f"unknown concurrent bytes at rollback: {role}")
                if row["exists"]:
                    backup = backups / f"{index:03d}.bin"
                    require(identity_file(backup) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"rollback backup drift: {role}")
                    os.replace(backup, path)
                else:
                    path.unlink()
            except BaseException as recovery:
                rollback_errors.append(f"{role}:{type(recovery).__name__}:{recovery}")
        if not rollback_errors:
            try:
                verify_current_preimages(roots, preimages)
            except BaseException as recovery:
                rollback_errors.append(f"preimage-verification:{type(recovery).__name__}:{recovery}")
        if rollback_errors:
            raise RuntimeError("state seal failed; exact rollback conflict: " + " | ".join(rollback_errors)) from exc
        raise RuntimeError(f"state seal failed and rolled back exactly: {type(exc).__name__}: {exc}") from exc
    finally:
        try:
            shutil.rmtree(work)
        except OSError:
            pass


def plan(roots: Roots, at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, dict[Path, bytes]]:
    inputs = validate_fixed_inputs(roots)
    preimages = snapshot_preimages(roots)
    token = transaction_token(at, inputs, preimages)
    outputs, _ = build_outputs(roots, at, token)
    validate_outputs_in_memory(outputs, roots)
    return inputs, preimages, token, outputs


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--private-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--at")
    parser.add_argument("--expected-fresh-preimage-sha256")
    return parser.parse_args()


def main() -> None:
    options = arguments()
    roots: Roots | None = None
    writes = False
    try:
        roots = Roots.make(options.private_root)
        existing = verify_committed(roots)
        if existing is not None:
            print(json.dumps({
                "schema": "agko-r39-build-qa-state-seal-report-v1",
                "mode": "already_committed",
                "writes_performed": False,
                "result": RESULT,
                **existing,
            }, ensure_ascii=True, indent=2))
            return
        at = validate_time(options.at)
        _, preimages, token, outputs = plan(roots, at)
        report = {
            "schema": "agko-r39-build-qa-state-seal-report-v1",
            "mode": "check" if options.check else "execute",
            "sealed_at": at,
            "fresh_preimage_sha256": token,
            "writes_performed": False,
            "planned_outputs": [
                {"path": role_for(path, roots), **identity_bytes(data)}
                for path, data in sorted(outputs.items(), key=lambda item: role_for(item[0], roots).casefold())
            ],
            "result": "PASS_R39_BUILD_QA_STATE_SEAL_CHECK_READY",
        }
        if options.check:
            print(json.dumps(report, ensure_ascii=True, indent=2))
            return
        require(options.expected_fresh_preimage_sha256 is not None, "--execute requires --expected-fresh-preimage-sha256")
        require(options.expected_fresh_preimage_sha256 == token, "fresh-preimage token mismatch before mutex")
        with transaction_mutex() as abandoned:
            existing = verify_committed(roots)
            if existing is not None:
                print(json.dumps({
                    "schema": "agko-r39-build-qa-state-seal-report-v1",
                    "mode": "already_committed_under_mutex",
                    "writes_performed": False,
                    "result": RESULT,
                    **existing,
                }, ensure_ascii=True, indent=2))
                return
            _, preimages, token, outputs = plan(roots, at)
            require(options.expected_fresh_preimage_sha256 == token, "fresh-preimage token changed under mutex")
            transaction_id = "AGKO-R39-BUILD-QA-STATE-SEAL-" + token[:20]
            writes = True
            execute_transaction(roots, outputs, preimages, transaction_id)
            committed = verify_committed(roots)
            require(committed is not None, "state seal did not commit")
        report.update({
            "writes_performed": True,
            "abandoned_mutex_recovered": abandoned,
            "result": RESULT,
            **committed,
        })
        print(json.dumps(report, ensure_ascii=True, indent=2))
    except Exception as exc:
        print(json.dumps({
            "schema": "agko-r39-build-qa-state-seal-report-v1",
            "result": "FAIL_CLOSED",
            "writes_performed": writes,
            "error": f"{type(exc).__name__}: {exc}",
        }, ensure_ascii=True, separators=(",", ":")), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
