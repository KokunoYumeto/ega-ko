#!/usr/bin/env python3
"""Fail-closed metadata-only R39 authority-comment reseal.

``--check`` is read-only. ``--execute`` requires the exact wall-clock timestamp
and fresh-preimage digest returned by a successful check.  The transaction
changes only the first comment line of both live c2s1 mirrors, advances the
current R39 declarations that bind those bytes, and appends new evidence.  The
translation body, the original R39 integration journal, and every historical
admission/reseal control remain immutable.
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
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


OLD_LINE = (
    "% Authority slice: EGA II ega2-1-fr.tex lines 1-1535, 70120 LF UTF-8 bytes, "
    "SHA-256 ED3DC79E9408C4D5325D24F3FF1CB06548611C5C8BD79CC67348402D9A0C0D91."
)
NEW_LINE = (
    "% Authority slice: EGA II ega2-1-fr.tex lines 1-1780, 81885 LF UTF-8 bytes, "
    "SHA-256 033E312D8BD9E22AEC1D5B8AC5705ED71C64C4E4DCFBB7ED84B9A434313ACE33."
)
PRE_TARGET = {
    "bytes": 84_274,
    "characters": 58_678,
    "lf_lines": 1_809,
    "sha256": "F3DD70691223B0D35052B4D6F4CF5E77B72AA2C5F352EDE5D9C83E98704C8257",
}
POST_TARGET = {
    "bytes": 84_274,
    "characters": 58_678,
    "lf_lines": 1_809,
    "sha256": "B3F0D07439653AFC8420D6AFEA840725D96A84BACA0C428A1501C2663E7C32AD",
}
BODY_AFTER_FIRST_LINE = {
    "bytes": 84_124,
    "lf_lines": 1_808,
    "sha256": "93A98E2F4895CB4C49D7ADDDBCEA3E4129BE66BF544B116CF64E8597F26F254F",
}
OLD_PREFIX = {"bytes": 80_222, "sha256": "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006"}
NEW_PREFIX = {"bytes": 80_222, "sha256": "003511D24111201FD1FC2E87E8C6804D430BB975D2B71461DC61E03BD7808297"}
R39_TAIL = {"bytes": 4_052, "sha256": "7CF528B90E7D1D50EEAABF714AB185C574F5C8A86520F46A7D697FAFB381186C"}
SOURCE = {
    "path": "source/ega2/ega2-1-fr.tex",
    "bytes": 820_504,
    "sha256": "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E",
    "prefix_lines": "1-1780",
    "prefix_bytes": 81_885,
    "prefix_sha256": "033E312D8BD9E22AEC1D5B8AC5705ED71C64C4E4DCFBB7ED84B9A434313ACE33",
}
ORIGINAL_JOURNAL = {
    "path": "controls/R39_INTEGRATION_TRANSACTION.json",
    "bytes": 18_471,
    "sha256": "CD7D2B4C0FAEC31277F27E5F960CA0B9774220603F474D777A610BA8A8CA792D",
    "transaction_id": "AGKO-R39-INTEGRATION-9021E88AAA1A6C74050E",
}
OLD_INTEGRATION_CONTROL = {
    "bytes": 6_610,
    "sha256": "BA1B7D43FC93365C21F86E7D1494CB59483DA7863EF16E4B5D80BFF48161AF6B",
}
HISTORICAL_CONTROLS = (
    ("R39_TRANSLATION_ADMISSION.json", 8_605, "D7122B74AADB7E26B987AFABAA0D12E59E1342D4F63FEDA0DFE3AB0557330561"),
    ("R39_CANONICAL_PREFIX_REBASE.json", 6_370, "CD9E1E2CF87D2E35C49AE7AF16E797AF146B72C6060869B631019DB8F6782349"),
    ("R39_KOREAN_WORDING_RESEAL.json", 10_118, "9A30C30953B7C118434541FBE8F9A362BB374BB68835E479536073B8DE730451"),
    ("R39_CURRENT_AUTHORITY_VALIDATOR.json", 10_257, "F572BDDCFADAC93EAC01C00E07DBA16D03BEDFE3E14B5E4FADEA1B5A76AC2350"),
)
CHAIN_CONTROL = {
    "path": "R39_R43_SEQUENTIAL_CHAIN_REBASE_20260906.json",
    "bytes": 13_319,
    "sha256": "54ED653F27FF96FECB315BEE0029BD6FFE087898DC37951D4C5F0A2A6255CE6C",
}
CUMULATIVE_MANIFEST = {
    "path": "source/CUMULATIVE_INPUTS.json",
    "bytes": 16_267,
    "sha256": "AFBCB3C4CF8E07C22B1C11BDD953B9257D9E55BC5F7044F95812C6538D58376E",
}
CANDIDATES = (
    ("R39", "r39-c2s1-continuation.tex", 4_051, "E8F52EDEC11B90D3CCC4E2398279DA4DEA7A6064AABFBE87D1765D55FEDE1940"),
    ("R40", "r40-c2s1-continuation.tex", 4_829, "4E3A5FDEFF4DE67EA548232F8A589AFF06023916DB838440A594E9D1FAA3E5AD"),
    ("R41", "r41-c2s1-continuation.tex", 4_544, "5DE6EC9F2560C92DCF6A7B5C76F1FB72749612CCD7C5724FCA65C1EE6C81A971"),
    ("R42", "r42-c2s1-continuation.tex", 4_645, "738F6826A8293EA316C84A59159E74D499C8F9C8B3C20C898D0BA75C68FEBC81"),
    ("R43", "r43-c2s1-continuation.tex", 4_450, "0668CE33E37BFBF854B826958D96AD5CE6C3FD21C4386F7E8E9914424A51288A"),
)
CHAIN_POST = {
    "R39": (84_274, 58_678, 1_809, "B3F0D07439653AFC8420D6AFEA840725D96A84BACA0C428A1501C2663E7C32AD"),
    "R40": (89_104, 61_916, 1_924, "DDCA0A13CD852831A6DFE999DC777FD9F8FCD475B08A84D943F0F6636447269F"),
    "R41": (93_649, 65_119, 2_031, "26C9A76D71D855670B8596FD8AE7E957B1AE5301CECF932E47943BE38B75F9F7"),
    "R42": (98_295, 68_297, 2_139, "338499DABB43EB850F50C1019D9E9D4E9233C00E432EEC1B8DC467D2292CE96C"),
    "R43": (102_746, 71_522, 2_247, "ACD8897FB293367937DB73FEFE389BFAB8D7599D8E52A4BA326E2346EB43FC20"),
}
PUBLIC_ALIASES = (
    "CURSOR.json", "PROGRAM_CURSOR.json", "STATE.json", "PROGRAM_STATE.json",
    "QA_STATE.json", "VISUAL_QA.json", "SOURCE_AUTHORITY.json",
    "PROGRAM_AUTHORITY.json", "DATACITE_RELATIONS.json",
)
LEDGERS = ("decisions.jsonl", "evidence.jsonl", "hard.jsonl")
CONTROL_PRIVATE = Path("controls/R39_AUTHORITY_COMMENT_RESEAL.json")
CONTROL_PUBLIC = Path("evidence/controls/R39_AUTHORITY_COMMENT_RESEAL.json")
JOURNAL_REL = Path("controls/R39_AUTHORITY_COMMENT_RESEAL_TRANSACTION.json")
WORK_REL = Path("controls/.r39-authority-comment-reseal")
MUTEX_NAME = r"Global\InterlanguageAgKoR39AuthorityCommentResealV1"
RESULT = "PASS_R39_AUTHORITY_COMMENT_RESEAL_TRANSLATION_BODY_UNCHANGED"
SHA_RE = re.compile(r"[0-9A-F]{64}\Z")
PRIVATE_RE = re.compile(r"(?i)(?:(?<![A-Z0-9])[A-Z]:[\\/][^\s\"']+|\\\\[^\\/\s\"']+[\\/][^\s\"']+|/(?:home|Users)/[^/\s\"']+/[^\s\"']*)")
EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9._%+-])")
CREDENTIAL_RE = re.compile(r"(?i)(?:gh[pousr]_[A-Za-z0-9]{20,}|bearer\s+[A-Za-z0-9._~-]{16,}|(?:access[_-]?token|api[_-]?key)\s*[:=]\s*[^\s,}\"]{8,})")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def identity(data: bytes) -> dict[str, int | str]:
    return {"bytes": len(data), "sha256": sha(data)}


def file_identity(path: Path) -> dict[str, int | str]:
    return identity(path.read_bytes())


def jbytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def jlbytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, "duplicate JSON key")
        value[key] = item
    return value


def parse(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"malformed JSON: {label}") from exc
    require(isinstance(value, dict), f"JSON root is not an object: {label}")
    return value


def parse_path(path: Path, label: str) -> dict[str, Any]:
    regular(path, label)
    return parse(path.read_bytes(), label)


def parse_jsonl(data: bytes, label: str) -> list[dict[str, Any]]:
    require(data.endswith(b"\n") and b"\r" not in data, f"JSONL framing drift: {label}")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(data.splitlines(), 1):
        require(bool(line), f"blank JSONL row: {label}:{number}")
        rows.append(parse(line, f"{label}:{number}"))
    return rows


def regular(path: Path, label: str) -> None:
    require(path.exists() and path.is_file() and not path.is_symlink(), f"missing/nonregular prerequisite: {label}")


def exact(path: Path, expected: Mapping[str, Any], label: str) -> bytes:
    regular(path, label)
    data = path.read_bytes()
    require(identity(data) == {"bytes": expected["bytes"], "sha256": expected["sha256"]}, f"identity drift: {label}")
    return data


def validate_time(value: str | None) -> str:
    require(value is not None, "an explicit actual wall-clock --at is required")
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError("--at must be ISO-8601") from exc
    require(stamp.tzinfo is not None and stamp.microsecond == 0, "--at must include an offset and second precision")
    require(abs((datetime.now(stamp.tzinfo) - stamp).total_seconds()) <= 300, "--at must be the actual current wall time (within five minutes)")
    return stamp.isoformat(timespec="seconds")


def find_workspace(private: Path) -> Path:
    for item in (private, *private.parents):
        if item.name.casefold() == "interlanguage":
            return item
    raise RuntimeError("bounded workspace root not found")


@dataclass(frozen=True)
class Roots:
    private: Path
    repo: Path
    canonical: Path

    @classmethod
    def make(cls, private: Path, repo: Path | None, canonical: Path | None) -> "Roots":
        private = private.resolve(strict=True)
        repo = (repo or private / "pub/ega-ko").resolve(strict=True)
        canonical = (canonical or find_workspace(private) / "Transcription/03_working_transcriptions/EGA_French_NUMDAM_canonical_TeX_20260801_r1").resolve(strict=True)
        require(repo == (private / "pub/ega-ko").resolve(strict=True), "wrong public repository root")
        return cls(private, repo, canonical)


def role(path: Path, roots: Roots) -> str:
    resolved = path.resolve(strict=False)
    for base, label in ((roots.canonical, "[CANONICAL_ROOT]"), (roots.repo, "[PUBLIC_REPOSITORY_ROOT]"), (roots.private, "[PRIVATE_ROOT]")):
        if resolved == base or resolved.is_relative_to(base):
            suffix = resolved.relative_to(base).as_posix()
            return label + ("/" + suffix if suffix else "")
    raise RuntimeError("path escapes bounded roots")


def resolve_role(locator: str, roots: Roots) -> Path:
    for label, base in (("[CANONICAL_ROOT]", roots.canonical), ("[PUBLIC_REPOSITORY_ROOT]", roots.repo), ("[PRIVATE_ROOT]", roots.private)):
        if locator.startswith(label + "/"):
            parts = Path(locator[len(label) + 1:]).parts
            require(all(part not in {"", ".", ".."} for part in parts), "unsafe locator")
            path = base.joinpath(*parts).resolve(strict=False)
            require(path.is_relative_to(base), "locator escapes root")
            return path
    raise RuntimeError("unknown role locator")


def replace_exact(value: Any, old: str, new: str) -> tuple[Any, int]:
    if isinstance(value, str):
        return (new, 1) if value == old else (value, 0)
    if isinstance(value, list):
        output, count = [], 0
        for item in value:
            changed, seen = replace_exact(item, old, new)
            output.append(changed); count += seen
        return output, count
    if isinstance(value, dict):
        output, count = {}, 0
        for key, item in value.items():
            changed, seen = replace_exact(item, old, new)
            output[key] = changed; count += seen
        return output, count
    return value, 0


def validate_public_delta(old: bytes | None, new: bytes, label: str) -> None:
    before = old.decode("utf-8") if old is not None else ""
    after = new.decode("utf-8")
    for pattern, kind in ((PRIVATE_RE, "private path"), (EMAIL_RE, "email"), (CREDENTIAL_RE, "credential")):
        a = Counter(match.group(0).casefold() for match in pattern.finditer(before))
        b = Counter(match.group(0).casefold() for match in pattern.finditer(after))
        require(all(count <= a[item] for item, count in b.items()), f"public output introduces {kind}: {label}")
    for pattern in (re.compile(r"(?i)(?<![A-Z0-9])TTP(?![A-Z0-9])"), re.compile(r"(?i)Translation and Transcription Project"), re.compile(r"(?i)(?<![A-Z0-9])Figshare(?![A-Z0-9])")):
        require(len(pattern.findall(after)) <= len(pattern.findall(before)), f"public output introduces excluded prose: {label}")


def output_paths(roots: Roots) -> list[Path]:
    paths = [
        roots.private / "ega/II/c2s1.tex", roots.repo / "source/c2s1.tex",
        roots.private / CONTROL_PRIVATE, roots.repo / CONTROL_PUBLIC,
        roots.private / "cursor.json", roots.private / "state.json", roots.private / "authority.json",
        *(roots.repo / "evidence" / name for name in PUBLIC_ALIASES),
        roots.repo / CUMULATIVE_MANIFEST["path"],
        *(roots.private / name for name in LEDGERS),
        *(roots.repo / "evidence" / name for name in LEDGERS),
        roots.private / "index/units.jsonl", roots.repo / "evidence/index/units.jsonl",
    ]
    require(len(paths) == len({path.resolve(strict=False) for path in paths}), "output inventory is not injective")
    return paths


def snapshot(paths: Iterable[Path], roots: Roots) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(paths, key=lambda item: role(item, roots).casefold()):
        locator = role(path, roots)
        if path.exists():
            regular(path, locator); rows.append({"path": locator, "exists": True, **file_identity(path)})
        else:
            require(not path.is_symlink(), f"dangling symlink: {locator}")
            rows.append({"path": locator, "exists": False, "bytes": 0, "sha256": None})
    return rows


def require_snapshot(rows: Sequence[Mapping[str, Any]], roots: Roots) -> None:
    for row in rows:
        path = resolve_role(str(row["path"]), roots)
        if row["exists"]:
            require(path.exists() and file_identity(path) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"fresh-preimage conflict: {row['path']}")
        else:
            require(not path.exists() and not path.is_symlink(), f"expected-absent output appeared: {row['path']}")


def verify_immutable_inputs(roots: Roots) -> dict[str, Any]:
    original_data = exact(roots.private / ORIGINAL_JOURNAL["path"], ORIGINAL_JOURNAL, "original R39 journal")
    original = parse(original_data, "original R39 journal")
    require(original.get("status") == "COMMITTED" and original.get("transaction_id") == ORIGINAL_JOURNAL["transaction_id"], "original R39 journal state drift")
    require(len(original.get("postimages", [])) == 26, "original R39 postimage inventory drift")
    for row in original["postimages"]:
        path = resolve_role(row["path"], roots)
        require(file_identity(path) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"original R39 live postimage drift: {row['path']}")
    for name, size, checksum in HISTORICAL_CONTROLS:
        expected = {"bytes": size, "sha256": checksum}
        a = exact(roots.private / "controls" / name, expected, f"private historical {name}")
        b = exact(roots.repo / "evidence/controls" / name, expected, f"public historical {name}")
        require(a == b, f"historical control mirrors differ: {name}")
    chain_expected = {"bytes": CHAIN_CONTROL["bytes"], "sha256": CHAIN_CONTROL["sha256"]}
    chain_a = exact(roots.private / "controls" / CHAIN_CONTROL["path"], chain_expected, "private current chain control")
    chain_b = exact(roots.repo / "evidence/controls" / CHAIN_CONTROL["path"], chain_expected, "public current chain control")
    require(chain_a == chain_b, "chain control mirrors differ")
    manifest_data = exact(roots.repo / CUMULATIVE_MANIFEST["path"], CUMULATIVE_MANIFEST, "cumulative input manifest")
    source_data = exact(roots.canonical / SOURCE["path"], SOURCE, "canonical EGA II source")
    lines = source_data.decode("utf-8").splitlines()
    prefix = ("\n".join(lines[:1780]) + "\n").encode("utf-8")
    require(identity(prefix) == {"bytes": SOURCE["prefix_bytes"], "sha256": SOURCE["prefix_sha256"]}, "canonical admitted prefix drift")
    candidates: dict[str, bytes] = {}
    for stage, name, size, checksum in CANDIDATES:
        candidates[stage] = exact(roots.private / "candidates" / name, {"bytes": size, "sha256": checksum}, f"{stage} candidate")
    return {"original_journal": original_data, "chain_control": chain_a, "manifest": manifest_data, "candidates": candidates}


def corrected_target(data: bytes) -> bytes:
    require(identity(data) == {"bytes": PRE_TARGET["bytes"], "sha256": PRE_TARGET["sha256"]}, "R39 target preimage drift")
    require(data.count((OLD_LINE + "\n").encode("utf-8")) == 1, "old authority line multiplicity drift")
    require(data.count((NEW_LINE + "\n").encode("utf-8")) == 0, "new authority line already present")
    first, body = data.split(b"\n", 1)
    require(first.decode("utf-8") == OLD_LINE, "old authority line is not exact first line")
    require(identity(body) == {"bytes": BODY_AFTER_FIRST_LINE["bytes"], "sha256": BODY_AFTER_FIRST_LINE["sha256"]} and body.count(b"\n") == BODY_AFTER_FIRST_LINE["lf_lines"], "translation body identity drift")
    result = NEW_LINE.encode("utf-8") + b"\n" + body
    require(len(OLD_LINE.encode("utf-8")) == len(NEW_LINE.encode("utf-8")) == 149, "authority-line byte arithmetic drift")
    require(identity(result) == {"bytes": POST_TARGET["bytes"], "sha256": POST_TARGET["sha256"]}, "predicted corrected target identity mismatch")
    require(len(result.decode("utf-8")) == POST_TARGET["characters"] and result.count(b"\n") == POST_TARGET["lf_lines"], "corrected target metrics drift")
    require(identity(result[:OLD_PREFIX["bytes"]]) == NEW_PREFIX, "corrected prefix identity drift")
    require(identity(result[OLD_PREFIX["bytes"]:]) == R39_TAIL, "R39 translation tail changed")
    return result


def update_manifest(data: bytes) -> bytes:
    value = parse(data, "cumulative input manifest")
    changed, count = replace_exact(value, PRE_TARGET["sha256"], POST_TARGET["sha256"])
    require(count == 1, "manifest target-hash occurrence drift")
    required = changed.get("reconciliation", {}).get("required_latest_records")
    old_id = "AGKO-EGA2-S1-R39-INTEGRATED-R1"
    new_id = "AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1"
    require(isinstance(required, list) and required.count(old_id) == 1, "manifest reconciliation frontier drift")
    require(new_id not in required, "manifest already names reseal unit")
    required[required.index(old_id)] = new_id
    return jbytes(changed)


def build_control(at: str, token: str, manifest_post: bytes) -> bytes:
    stages = []
    for stage in ("R39", "R40", "R41", "R42", "R43"):
        size, chars, lf, checksum = CHAIN_POST[stage]
        stages.append({"stage": stage, "bytes": size, "characters": chars, "lf_lines": lf, "sha256": checksum})
    value = {
        "schema": "agko-r39-authority-comment-reseal-v1",
        "time": at,
        "precision": "second",
        "scope": "Metadata-only first-line authority correction in both live Korean EGA II c2s1 mirrors; translation body unchanged.",
        "authority": dict(SOURCE),
        "old_first_line": OLD_LINE,
        "new_first_line": NEW_LINE,
        "preimage": dict(PRE_TARGET),
        "postimage": dict(POST_TARGET),
        "body_after_first_line": dict(BODY_AFTER_FIRST_LINE),
        "prefix": {"old": dict(OLD_PREFIX), "new": dict(NEW_PREFIX), "change": "first comment line only"},
        "r39_tail": {**dict(R39_TAIL), "status": "exactly unchanged"},
        "cumulative_chain_after_comment_reseal": stages,
        "historical_evidence_preserved": {
            "original_integration_journal": dict(ORIGINAL_JOURNAL),
            "original_integration_controls": {
                "private": "controls/R39_TRANSLATION_INTEGRATION.json",
                "public": "evidence/controls/R39_TRANSLATION_INTEGRATION.json",
                **dict(OLD_INTEGRATION_CONTROL),
                "status": "immutable; nested r39_translation_integration references remain bound here",
            },
            "historical_controls": [{"path": f"controls/{name}", "bytes": size, "sha256": checksum} for name, size, checksum in HISTORICAL_CONTROLS],
            "prior_chain_control": {**dict(CHAIN_CONTROL), "status": "preserved and superseded only for cumulative hashes"},
        },
        "cumulative_manifest_postimage": {"path": CUMULATIVE_MANIFEST["path"], **identity(manifest_post)},
        "transaction": {
            "journal": str(JOURNAL_REL).replace("\\", "/"),
            "fresh_preimage_sha256": token,
            "all_postimages_computed_before_first_write": True,
            "atomic_mirrored_writes_and_rollback": True,
        },
        "ledger_records": {
            "decision": "AGKO-D189", "evidence": "AGKO-E-R39-DECLARATION-RESEAL",
            "hard": "AGKO-H164", "unit": "AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1",
        },
        "limits": "No translation-body, TeX, PDF, Git, UI, publication, or later-unit integration action.",
        "result": RESULT,
    }
    result = jbytes(value)
    validate_public_delta(None, result, "new authority-comment reseal control")
    return result


def reseal_ref(control_id: Mapping[str, Any], public: bool) -> dict[str, Any]:
    return {
        "status": RESULT,
        "control": {
            "path": ("evidence/controls/" if public else "controls/") + CONTROL_PRIVATE.name,
            **dict(control_id), "private_public_mirrors_exact": True,
        },
        "old_target": dict(PRE_TARGET), "current_target": dict(POST_TARGET),
        "translation_body_after_first_line": {**dict(BODY_AFTER_FIRST_LINE), "unchanged": True},
    }


def update_live_state(data: bytes, name: str, ref: Mapping[str, Any], at: str) -> bytes:
    value = parse(data, name)
    require("r39_authority_comment_reseal" not in value, f"state already resealed: {name}")
    if name == "cursor.json":
        require(value.get("target", {}).get("sha256") == PRE_TARGET["sha256"], "private cursor live target drift")
        value["target"]["sha256"] = POST_TARGET["sha256"]
    elif name == "state.json":
        require(value.get("active", {}).get("target", {}).get("sha256") == PRE_TARGET["sha256"], "private state live target drift")
        value["active"]["target"]["sha256"] = POST_TARGET["sha256"]
    elif name == "authority.json":
        admitted = [row for row in value.get("ega_ii", {}).get("admitted", []) if row.get("target") == "ega/II/c2s1.tex"]
        require(len(admitted) == 1 and admitted[0].get("sha256") == PRE_TARGET["sha256"], "private authority live target drift")
        admitted[0]["sha256"] = POST_TARGET["sha256"]
    else:
        require(value.get("target", {}).get("sha256") == PRE_TARGET["sha256"], f"public alias live target drift: {name}")
        value["target"]["sha256"] = POST_TARGET["sha256"]
    # The nested r39_translation_integration object remains an immutable record
    # of the original F3DD transaction; the additive pointer is the live overlay.
    historical = value.get("ega_ii", {}).get("r39_translation_integration", {}) if name == "authority.json" else value.get("r39_translation_integration", {})
    require(historical.get("target", {}).get("sha256") == PRE_TARGET["sha256"], f"historical integration binding drift: {name}")
    require(historical.get("control", {}).get("sha256") == OLD_INTEGRATION_CONTROL["sha256"], f"historical integration control drift: {name}")
    value["r39_authority_comment_reseal"] = copy.deepcopy(ref)
    value["updated"] = at
    if name == "state.json":
        require(value.get("active", {}).get("target", {}).get("sha256") == POST_TARGET["sha256"], "private active target did not advance")
        require(value.get("active", {}).get("next_target") == "Refresh declarations and build the exact integrated R39 mirrors without reopening the translation bytes.", "private state next-target preimage drift")
        require(value.get("next_executable_action") == "Refresh cumulative declarations through canonical line1780 and run the serialized R39 build/QA/release gates.", "private state next-action preimage drift")
        value["active"]["next_target"] = "Run the serialized R39 build/QA/release gates without reopening the translation bytes."
        value["next_executable_action"] = "Run the serialized R39 build/QA/release gates."
    return jbytes(value)


def verify_live_state(data: bytes, name: str, control_sha256: str, at: str) -> None:
    value = parse(data, name)
    if name == "cursor.json":
        current = value.get("target", {})
        historical = value.get("r39_translation_integration", {})
    elif name == "state.json":
        current = value.get("active", {}).get("target", {})
        historical = value.get("r39_translation_integration", {})
        require(value.get("active", {}).get("next_target") == "Run the serialized R39 build/QA/release gates without reopening the translation bytes.", "private state next-target postimage drift")
        require(value.get("next_executable_action") == "Run the serialized R39 build/QA/release gates.", "private state next-action postimage drift")
    elif name == "authority.json":
        admitted = [row for row in value.get("ega_ii", {}).get("admitted", []) if row.get("target") == "ega/II/c2s1.tex"]
        require(len(admitted) == 1, "private authority live target multiplicity drift")
        current = admitted[0]
        historical = value.get("ega_ii", {}).get("r39_translation_integration", {})
    else:
        current = value.get("target", {})
        historical = value.get("r39_translation_integration", {})
    require(current.get("sha256") == POST_TARGET["sha256"], f"live target binding drift: {name}")
    require(historical.get("target", {}).get("sha256") == PRE_TARGET["sha256"], f"historical target binding drift: {name}")
    require(historical.get("control", {}).get("sha256") == OLD_INTEGRATION_CONTROL["sha256"], f"historical control binding drift: {name}")
    reseal = value.get("r39_authority_comment_reseal", {})
    require(reseal.get("status") == RESULT, f"reseal state missing: {name}")
    require(reseal.get("old_target", {}).get("sha256") == PRE_TARGET["sha256"] and reseal.get("current_target", {}).get("sha256") == POST_TARGET["sha256"], f"reseal target transition drift: {name}")
    require(reseal.get("control", {}).get("sha256") == control_sha256, f"reseal control binding drift: {name}")
    require(value.get("updated") == at, f"reseal timestamp drift: {name}")


def append_record(data: bytes, record: Mapping[str, Any], label: str) -> bytes:
    rows = parse_jsonl(data, label)
    require(sum(row.get("id") == record["id"] for row in rows) == 0, f"record already exists: {record['id']}")
    return data + jlbytes(record)


def records(at: str, control_id: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    common = {"time": at, "precision": "second"}
    return {
        "decisions.jsonl": {
            "id": "AGKO-D189", **common, "kind": "r39_authority_comment_metadata_reseal",
            "scope": "Korean EGA II c2s1 first authority-comment line only",
            "choice": "Replace the stale R36 authority declaration with exact canonical lines1-1780 identity in both mirrors while leaving every byte after the first LF unchanged.",
            "evidence": [f"{POST_TARGET['bytes']}B/{POST_TARGET['sha256']}", f"controls/{CONTROL_PRIVATE.name} {control_id['bytes']}B/{control_id['sha256']}", f"immutable predecessor integration control {OLD_INTEGRATION_CONTROL['bytes']}B/{OLD_INTEGRATION_CONTROL['sha256']}"],
            "uncertainty": "None in the byte-level reseal; downstream build and publication remain pending.",
            "review": RESULT,
        },
        "evidence.jsonl": {
            "id": "AGKO-E-R39-DECLARATION-RESEAL", **common,
            "kind": "metadata_only_authority_comment_reseal_evidence",
            "preimage": dict(PRE_TARGET), "postimage": dict(POST_TARGET),
            "old_first_line": OLD_LINE, "new_first_line": NEW_LINE,
            "body_after_first_line": {**dict(BODY_AFTER_FIRST_LINE), "unchanged": True},
            "control": {"private": f"controls/{CONTROL_PRIVATE.name}", "public": f"evidence/controls/{CONTROL_PRIVATE.name}", **dict(control_id)},
            "result": RESULT,
        },
        "hard.jsonl": {
            "id": "AGKO-H164", **common,
            "status": "controlling_r39_authority_comment_reseal",
            "scope": "Every live declaration of the integrated R39 c2s1 target identity",
            "symptom": "The exact live translation body was current through canonical line1780, but its first comment still declared the older lines1-1535 authority slice.",
            "resolution": "Same-length first-line correction, exact body preservation, mirrored target/control/state/manifest transaction and additive evidence.",
            "tests": f"old line once before/new line once after; body {BODY_AFTER_FIRST_LINE['sha256']}; target {POST_TARGET['sha256']}; exact mirrors and rollback journal",
            "recurrence": "When cumulative coverage advances, reseal the embedded authority declaration in the same exact integration transaction.",
            "related": ["AGKO-D189", "AGKO-E-R39-DECLARATION-RESEAL", "AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1"],
        },
    }


def unit_row(control_id: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": "AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1", "kind": "section_state_update",
        "parent": "AGKO-EGA2-S1", "order": 2_135,
        "authority": {"path": SOURCE["path"], "locator": "lines1-1780 through2.2.6", "bytes": SOURCE["prefix_bytes"], "sha256": SOURCE["prefix_sha256"], "whole_bytes": SOURCE["bytes"], "whole_sha256": SOURCE["sha256"]},
        "target": {"path": "ega/II/c2s1.tex", "locator": "metadata-resealed first line; translation body unchanged", **dict(POST_TARGET), "preimage_sha256": PRE_TARGET["sha256"], "identity_status": "exact_private_public_mirrors"},
        "relations": ["supersedes-live-identity:AGKO-EGA2-S1-R39-INTEGRATED-R1", f"controls/{CONTROL_PRIVATE.name} {control_id['sha256']}", "translation body after first LF exact unchanged"],
        "language": "ko-KR",
        "state": {"translation": "complete", "build": "pending", "visual": "pending", "publication": "private_working", "integration": "pass_exact_mirrors_metadata_resealed"},
    }


def append_unit(data: bytes, row: Mapping[str, Any], label: str) -> bytes:
    rows = parse_jsonl(data, label)
    require(sum(item.get("id") == row["id"] for item in rows) == 0, "reseal unit already exists")
    require(sum(item.get("id") == "AGKO-EGA2-S1-R39-INTEGRATED-R1" for item in rows) == 1, "historical R39 unit multiplicity drift")
    require(max(item.get("order", -1) for item in rows if type(item.get("order")) is int) == 2_134, "unit order frontier drift")
    return data + jlbytes(row)


def prerequisite_paths(roots: Roots) -> list[Path]:
    paths = [
        Path(__file__).resolve(strict=True), roots.private / ORIGINAL_JOURNAL["path"],
        roots.canonical / SOURCE["path"], roots.private / "controls" / CHAIN_CONTROL["path"],
        roots.repo / "evidence/controls" / CHAIN_CONTROL["path"],
        roots.private / "controls/R39_TRANSLATION_INTEGRATION.json",
        roots.repo / "evidence/controls/R39_TRANSLATION_INTEGRATION.json",
        *(roots.private / "controls" / name for name, _, _ in HISTORICAL_CONTROLS),
        *(roots.repo / "evidence/controls" / name for name, _, _ in HISTORICAL_CONTROLS),
        *(roots.private / "candidates" / name for _, name, _, _ in CANDIDATES),
    ]
    return list({path.resolve(strict=False): path for path in paths}.values())


def build_outputs(roots: Roots, at: str, token: str, immutable: Mapping[str, Any]) -> dict[Path, bytes]:
    private_target_path = roots.private / "ega/II/c2s1.tex"
    public_target_path = roots.repo / "source/c2s1.tex"
    private_target = private_target_path.read_bytes(); public_target = public_target_path.read_bytes()
    require(private_target == public_target, "R39 target mirrors differ before reseal")
    target = corrected_target(private_target)
    manifest = update_manifest(immutable["manifest"])
    control = build_control(at, token, manifest)
    control_id = identity(control)
    integration_pre = exact(roots.private / "controls/R39_TRANSLATION_INTEGRATION.json", OLD_INTEGRATION_CONTROL, "private R39 integration control")
    require(integration_pre == exact(roots.repo / "evidence/controls/R39_TRANSLATION_INTEGRATION.json", OLD_INTEGRATION_CONTROL, "public R39 integration control"), "integration control mirrors differ")
    outputs: dict[Path, bytes] = {
        private_target_path: target, public_target_path: target,
        roots.private / CONTROL_PRIVATE: control, roots.repo / CONTROL_PUBLIC: control,
        roots.repo / CUMULATIVE_MANIFEST["path"]: manifest,
    }
    private_ref = reseal_ref(control_id, False); public_ref = reseal_ref(control_id, True)
    for name in ("cursor.json", "state.json", "authority.json"):
        path = roots.private / name
        outputs[path] = update_live_state(path.read_bytes(), name, private_ref, at)
    for name in PUBLIC_ALIASES:
        path = roots.repo / "evidence" / name
        outputs[path] = update_live_state(path.read_bytes(), name, public_ref, at)
    rows = records(at, control_id)
    for name in LEDGERS:
        private = roots.private / name; public = roots.repo / "evidence" / name
        outputs[private] = append_record(private.read_bytes(), rows[name], f"private {name}")
        outputs[public] = append_record(public.read_bytes(), rows[name], f"public {name}")
    row = unit_row(control_id)
    private_units = roots.private / "index/units.jsonl"; public_units = roots.repo / "evidence/index/units.jsonl"
    outputs[private_units] = append_unit(private_units.read_bytes(), row, "private units")
    outputs[public_units] = append_unit(public_units.read_bytes(), row, "public units")
    require(set(outputs) == set(output_paths(roots)), "postimage path inventory drift")
    for path, data in outputs.items():
        if path.resolve(strict=False).is_relative_to(roots.repo):
            validate_public_delta(path.read_bytes() if path.exists() else None, data, role(path, roots))
    return outputs


def plan(roots: Roots, at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[Path, bytes], str]:
    immutable = verify_immutable_inputs(roots)
    for path in output_paths(roots):
        if path in (roots.private / CONTROL_PRIVATE, roots.repo / CONTROL_PUBLIC):
            require(not path.exists() and not path.is_symlink(), "authority-comment reseal control already exists")
        else:
            regular(path, role(path, roots))
    inputs = snapshot(prerequisite_paths(roots), roots)
    preimages = snapshot(output_paths(roots), roots)
    token = sha(jbytes({"schema": "agko-r39-authority-comment-reseal-preimage-v1", "time": at, "inputs": inputs, "preimages": preimages}))
    outputs = build_outputs(roots, at, token, immutable)
    return inputs, preimages, outputs, token


def postimages(outputs: Mapping[Path, bytes], roots: Roots) -> list[dict[str, Any]]:
    return [{"path": role(path, roots), **identity(data)} for path, data in sorted(outputs.items(), key=lambda item: role(item[0], roots).casefold())]


def verify_outputs(roots: Roots, journal: Mapping[str, Any]) -> None:
    for row in journal["postimages"]:
        path = resolve_role(row["path"], roots)
        require(file_identity(path) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"postimage drift: {row['path']}")
    a = (roots.private / "ega/II/c2s1.tex").read_bytes(); b = (roots.repo / "source/c2s1.tex").read_bytes()
    require(a == b and identity(a) == {"bytes": POST_TARGET["bytes"], "sha256": POST_TARGET["sha256"]}, "final target mirrors/identity drift")
    require(len(a.decode("utf-8")) == POST_TARGET["characters"] and a.count(b"\n") == POST_TARGET["lf_lines"] and b"\r" not in a, "final target metrics/framing drift")
    require(a.count((OLD_LINE + "\n").encode()) == 0 and a.count((NEW_LINE + "\n").encode()) == 1, "final authority line multiplicity drift")
    first, body = a.split(b"\n", 1)
    require(first.decode() == NEW_LINE and identity(body) == {"bytes": BODY_AFTER_FIRST_LINE["bytes"], "sha256": BODY_AFTER_FIRST_LINE["sha256"]} and body.count(b"\n") == BODY_AFTER_FIRST_LINE["lf_lines"], "final translation body drift")
    require(identity(a[:OLD_PREFIX["bytes"]]) == NEW_PREFIX and identity(a[OLD_PREFIX["bytes"]:]) == R39_TAIL, "final prefix/tail structure drift")
    control_a = (roots.private / CONTROL_PRIVATE).read_bytes(); control_b = (roots.repo / CONTROL_PUBLIC).read_bytes()
    control = parse(control_a, "reseal control")
    require(control_a == control_b and control.get("result") == RESULT, "reseal control mirrors/result drift")
    require(control.get("old_first_line") == OLD_LINE and control.get("new_first_line") == NEW_LINE, "reseal control first-line binding drift")
    require(control.get("preimage", {}).get("sha256") == PRE_TARGET["sha256"] and control.get("postimage", {}).get("sha256") == POST_TARGET["sha256"], "reseal control target transition drift")
    integration_a = (roots.private / "controls/R39_TRANSLATION_INTEGRATION.json").read_bytes(); integration_b = (roots.repo / "evidence/controls/R39_TRANSLATION_INTEGRATION.json").read_bytes()
    require(integration_a == integration_b and identity(integration_a) == OLD_INTEGRATION_CONTROL, "immutable integration control mirrors/identity drift")
    manifest = parse_path(roots.repo / CUMULATIVE_MANIFEST["path"], "updated manifest")
    entries = [row for row in manifest.get("coverage_matrix", []) if row.get("target_path") == "c2s1.tex"]
    require(len(entries) == 1 and entries[0].get("target_sha256") == POST_TARGET["sha256"], "manifest c2s1 binding drift")
    required = manifest.get("reconciliation", {}).get("required_latest_records", [])
    require(required.count("AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1") == 1 and "AGKO-EGA2-S1-R39-INTEGRATED-R1" not in required, "manifest reseal frontier drift")
    control_sha256 = sha(control_a)
    for name in ("cursor.json", "state.json", "authority.json"):
        verify_live_state((roots.private / name).read_bytes(), name, control_sha256, journal["time"])
    for name in PUBLIC_ALIASES:
        verify_live_state((roots.repo / "evidence" / name).read_bytes(), name, control_sha256, journal["time"])
    for name, record_id in (("decisions.jsonl", "AGKO-D189"), ("evidence.jsonl", "AGKO-E-R39-DECLARATION-RESEAL"), ("hard.jsonl", "AGKO-H164")):
        x = [row for row in parse_jsonl((roots.private / name).read_bytes(), name) if row.get("id") == record_id]
        y = [row for row in parse_jsonl((roots.repo / "evidence" / name).read_bytes(), "public " + name) if row.get("id") == record_id]
        require(len(x) == len(y) == 1 and x[0] == y[0], f"ledger reseal record drift: {record_id}")
    for path in (roots.private / "index/units.jsonl", roots.repo / "evidence/index/units.jsonl"):
        found = [row for row in parse_jsonl(path.read_bytes(), str(path)) if row.get("id") == "AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1"]
        require(len(found) == 1 and found[0]["target"]["sha256"] == POST_TARGET["sha256"], "unit reseal row drift")
    exact(roots.private / ORIGINAL_JOURNAL["path"], ORIGINAL_JOURNAL, "immutable original R39 journal after reseal")
    for name, size, checksum in HISTORICAL_CONTROLS:
        expected = {"bytes": size, "sha256": checksum}
        private = exact(roots.private / "controls" / name, expected, f"immutable private historical {name} after reseal")
        public = exact(roots.repo / "evidence/controls" / name, expected, f"immutable public historical {name} after reseal")
        require(private == public, f"immutable historical control mirrors differ after reseal: {name}")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".r39-comment-tmp-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: temporary.unlink(missing_ok=True)
        except OSError: pass
        raise


def write_journal(path: Path, value: Mapping[str, Any]) -> None:
    atomic_write(path, jbytes(value))


def transaction_root(roots: Roots, transaction_id: str) -> Path:
    base = (roots.private / WORK_REL).resolve(strict=False)
    result = (base / transaction_id).resolve(strict=False)
    require(result.parent == base, "unsafe transaction work root")
    return result


def load_journal(roots: Roots) -> dict[str, Any] | None:
    path = roots.private / JOURNAL_REL
    if not path.exists() and not path.is_symlink(): return None
    value = parse_path(path, "authority-comment transaction journal")
    require(value.get("schema") == "agko-r39-authority-comment-reseal-transaction-v1", "transaction journal schema drift")
    require(value.get("status") in {"PREPARING", "PREPARED", "APPLYING", "VERIFYING", "COMMITTED", "ROLLED_BACK", "RECOVERY_CONFLICT"}, "transaction journal status drift")
    expected = {role(path, roots) for path in output_paths(roots)}
    for key in ("preimages", "postimages"):
        rows = value.get(key); require(isinstance(rows, list) and {row.get("path") for row in rows} == expected, f"journal {key} inventory drift")
    return value


def rollback(roots: Roots, journal: dict[str, Any]) -> None:
    pre = {row["path"]: row for row in journal["preimages"]}; post = {row["path"]: row for row in journal["postimages"]}
    order = [row["path"] for row in journal["postimages"]]
    backups = transaction_root(roots, journal["transaction_id"]) / "backups"; conflicts = []
    for index, locator in reversed(list(enumerate(order))):
        path = resolve_role(locator, roots); old = pre[locator]; new = {"bytes": post[locator]["bytes"], "sha256": post[locator]["sha256"]}
        if path.exists():
            actual = file_identity(path)
            if old["exists"] and actual == {"bytes": old["bytes"], "sha256": old["sha256"]}: continue
            if actual != new: conflicts.append(locator); continue
            if old["exists"]:
                backup = backups / f"{index:03d}.bin"
                if not backup.exists() or file_identity(backup) != {"bytes": old["bytes"], "sha256": old["sha256"]}: conflicts.append(locator)
                else: os.replace(backup, path)
            else: path.unlink()
        elif old["exists"]:
            backup = backups / f"{index:03d}.bin"
            if not backup.exists() or file_identity(backup) != {"bytes": old["bytes"], "sha256": old["sha256"]}: conflicts.append(locator)
            else: os.replace(backup, path)
    if conflicts:
        journal["status"] = "RECOVERY_CONFLICT"; journal["conflicts"] = conflicts; write_journal(roots.private / JOURNAL_REL, journal)
        raise RuntimeError("rollback refused unknown concurrent bytes")
    require_snapshot(journal["preimages"], roots)
    journal["status"] = "ROLLED_BACK"; journal["applied"] = []; write_journal(roots.private / JOURNAL_REL, journal)
    work = transaction_root(roots, journal["transaction_id"])
    if work.exists(): shutil.rmtree(work)


@contextmanager
def mutex() -> Iterator[bool]:
    require(os.name == "nt", "Windows transaction mutex required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]; kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]; kernel.WaitForSingleObject.restype = ctypes.c_uint
    handle = kernel.CreateMutexW(None, 0, MUTEX_NAME); require(bool(handle), "mutex creation failed")
    result = kernel.WaitForSingleObject(handle, 30_000); require(result in (0, 0x80), "mutex acquisition timeout")
    try: yield result == 0x80
    finally: kernel.ReleaseMutex(handle); kernel.CloseHandle(handle)


def execute(roots: Roots, at: str, inputs: list[dict[str, Any]], preimages: list[dict[str, Any]], outputs: Mapping[Path, bytes], token: str, expected: str) -> dict[str, Any]:
    require(token == expected, "fresh-preimage token mismatch")
    existing = load_journal(roots); attempt = 1; history = []
    if existing is not None:
        require(existing.get("status") == "ROLLED_BACK", "existing transaction is not recoverable from a fresh check")
        require_snapshot(existing["preimages"], roots)
        attempt = int(existing.get("attempt", 0)) + 1
        history = copy.deepcopy(existing.get("prior_attempts", [])) + [{"transaction_id": existing.get("transaction_id"), "attempt": existing.get("attempt"), "status": existing.get("status"), "fresh_preimage_sha256": existing.get("fresh_preimage_sha256")}]
    require_snapshot(inputs, roots); require_snapshot(preimages, roots)
    transaction_id = "AGKO-R39-COMMENT-RESEAL-" + token[:20]
    work = transaction_root(roots, transaction_id); require(not work.exists(), "transaction work root exists")
    journal = {"schema": "agko-r39-authority-comment-reseal-transaction-v1", "transaction_id": transaction_id, "time": at, "fresh_preimage_sha256": token, "status": "PREPARING", "attempt": attempt, "abandoned_mutex_recovered": False, "inputs": inputs, "preimages": preimages, "postimages": postimages(outputs, roots), "applied": [], "conflicts": [], "prior_attempts": history}
    write_journal(roots.private / JOURNAL_REL, journal)
    try:
        staged = work / "staged"; backups = work / "backups"; staged.mkdir(parents=True); backups.mkdir()
        order = sorted(outputs, key=lambda path: role(path, roots).casefold())
        require([role(path, roots) for path in order] == [row["path"] for row in journal["postimages"]], "transaction order drift")
        before = {row["path"]: row for row in preimages}
        for index, path in enumerate(order):
            stage = staged / f"{index:03d}.bin"
            with stage.open("xb") as stream: stream.write(outputs[path]); stream.flush(); os.fsync(stream.fileno())
            row = before[role(path, roots)]
            if row["exists"]:
                backup = backups / f"{index:03d}.bin"; shutil.copyfile(path, backup)
                with backup.open("r+b") as stream: os.fsync(stream.fileno())
                require(file_identity(backup) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "backup identity drift")
        journal["status"] = "PREPARED"; write_journal(roots.private / JOURNAL_REL, journal)
        require_snapshot(inputs, roots); require_snapshot(preimages, roots)
        for index, path in enumerate(order):
            for remaining in order[index:]:
                row = before[role(remaining, roots)]
                require((remaining.exists() and file_identity(remaining) == {"bytes": row["bytes"], "sha256": row["sha256"]}) if row["exists"] else not remaining.exists(), "concurrent output mutation")
            journal["status"] = "APPLYING"; write_journal(roots.private / JOURNAL_REL, journal)
            os.replace(staged / f"{index:03d}.bin", path)
            require(file_identity(path) == identity(outputs[path]), "post-replace identity drift")
            journal["applied"].append(role(path, roots)); write_journal(roots.private / JOURNAL_REL, journal)
        journal["status"] = "VERIFYING"; write_journal(roots.private / JOURNAL_REL, journal)
        verify_outputs(roots, journal)
        journal["status"] = "COMMITTED"; journal["work_directory_cleanup"] = "PENDING"; write_journal(roots.private / JOURNAL_REL, journal)
    except BaseException as exc:
        try: rollback(roots, journal)
        except BaseException as recovery: raise RuntimeError("reseal failed and exact recovery requires intervention") from recovery
        raise RuntimeError(f"reseal failed and rolled back exactly: {type(exc).__name__}: {exc}") from exc
    try: shutil.rmtree(work); journal["work_directory_cleanup"] = "COMPLETE"
    except OSError as exc: journal["work_directory_cleanup"] = f"PENDING_RETRY:{type(exc).__name__}"
    try: write_journal(roots.private / JOURNAL_REL, journal)
    except OSError: pass
    return journal


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(); mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true"); mode.add_argument("--execute", action="store_true")
    parser.add_argument("--private-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--repo-root", type=Path); parser.add_argument("--canonical-root", type=Path)
    parser.add_argument("--at"); parser.add_argument("--expected-fresh-preimage-sha256")
    return parser.parse_args()


def main() -> None:
    options = args(); roots: Roots | None = None; mutation = False
    try:
        roots = Roots.make(options.private_root, options.repo_root, options.canonical_root)
        at = validate_time(options.at); existing = load_journal(roots)
        if existing is not None and existing.get("status") == "COMMITTED":
            verify_outputs(roots, existing)
            print(json.dumps({"schema": "agko-r39-authority-comment-reseal-report-v1", "mode": "already_committed", "result": RESULT, "transaction_id": existing["transaction_id"], "outputs": existing["postimages"]}, ensure_ascii=True, indent=2)); return
        if existing is not None and existing.get("status") not in {"ROLLED_BACK"}:
            if options.check: raise RuntimeError("incomplete transaction requires --execute recovery")
            with mutex():
                current = load_journal(roots)
                if current is not None and current.get("status") == "COMMITTED": verify_outputs(roots, current); return
                require(current is not None and current.get("status") not in {"ROLLED_BACK"}, "recovery state changed; rerun check")
                mutation = True; rollback(roots, current)
            raise RuntimeError("incomplete transaction rolled back exactly; rerun check")
        inputs, preimages, outputs, token = plan(roots, at)
        report = {"schema": "agko-r39-authority-comment-reseal-report-v1", "mode": "check" if options.check else "execute", "time": at, "fresh_preimage_sha256": token, "preimage": dict(PRE_TARGET), "postimage": dict(POST_TARGET), "outputs": postimages(outputs, roots), "writes_performed": False, "result": "PASS_R39_AUTHORITY_COMMENT_RESEAL_CHECK_READY"}
        if options.check: print(json.dumps(report, ensure_ascii=True, indent=2)); return
        require(options.expected_fresh_preimage_sha256 is not None, "--execute requires fresh-preimage token")
        with mutex() as abandoned:
            inputs, preimages, outputs, token = plan(roots, at)
            require(options.expected_fresh_preimage_sha256 == token, "fresh-preimage token changed under mutex")
            mutation = True; journal = execute(roots, at, inputs, preimages, outputs, token, options.expected_fresh_preimage_sha256)
            if abandoned: journal["abandoned_mutex_recovered"] = True; write_journal(roots.private / JOURNAL_REL, journal)
        report.update({"writes_performed": True, "result": RESULT, "transaction_id": journal["transaction_id"], "outputs": journal["postimages"]})
        print(json.dumps(report, ensure_ascii=True, indent=2))
    except Exception as exc:
        observation = None
        if roots is not None and (roots.private / JOURNAL_REL).exists():
            try: observation = {"status": parse_path(roots.private / JOURNAL_REL, "journal observation").get("status"), **file_identity(roots.private / JOURNAL_REL)}
            except Exception: observation = {"status": "UNREADABLE"}
        print(json.dumps({"schema": "agko-r39-authority-comment-reseal-report-v1", "result": "FAIL_CLOSED", "error": str(exc), "writes_performed": mutation, "journal": observation}, ensure_ascii=True, separators=(",", ":")), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
