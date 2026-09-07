#!/usr/bin/env python3
"""Fail-closed, additive R39 homogeneous-ideal terminology reseal.

Check mode performs no writes. Execute mode requires the exact timestamp and
fresh-preimage digest from a successful check. Only nine independently mapped
Korean ideal-adjective spans may change; all other bytes and all historical R39
controls and journals remain immutable.
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


PRE_TARGET = {
    "bytes": 84_274, "characters": 58_678, "lf_lines": 1_809,
    "sha256": "B3F0D07439653AFC8420D6AFEA840725D96A84BACA0C428A1501C2663E7C32AD",
}
POST_TARGET = {
    "bytes": 84_274, "characters": 58_678, "lf_lines": 1_809,
    "sha256": "59D07958D5CE1765F4901202CE97B3AC6257F6DC6C0D114C37B314C6A6EB1943",
}
SOURCE = {
    "path": "source/ega2/ega2-1-fr.tex", "bytes": 820_504,
    "sha256": "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E",
    "prefix_lines": "1-1780", "prefix_bytes": 81_885,
    "prefix_sha256": "033E312D8BD9E22AEC1D5B8AC5705ED71C64C4E4DCFBB7ED84B9A434313ACE33",
}
PRE_COUNTS = {"등급": 56, "동차": 22}
POST_COUNTS = {"등급": 47, "동차": 31}
OLD_FORMS = (
    ("등급 소아이디얼", 5),
    ("등급\n소아이디얼", 1),
    ("등급\n아이디얼", 1),
    (r"\emph{등급} 아이디얼", 1),
    ("등급 아이디얼", 1),
)
NEW_FORMS = tuple((old.replace("등급", "동차"), count) for old, count in OLD_FORMS)

LOCI = (
    {
        "id": "R39-IDEAL-001", "source_lines": [1326],
        "source_text": [r"$1\in S_0$, $S_0$ est un sous-anneau de $S$, $S_+$ un idéal gradué de $S$ et"],
        "target_lines": [1336, 1337],
        "old": [
            r"$1\in S_0$이고, $S_0$는 $S$의 부분환이며, $S_+$는 $S$의 등급",
            r"아이디얼이고, $S$는 $S_0$와 $S_+$의 직합이다. $M$이 $S$ 위의",
        ],
        "new": [
            r"$1\in S_0$이고, $S_0$는 $S$의 부분환이며, $S_+$는 $S$의 동차",
            r"아이디얼이고, $S$는 $S_0$와 $S_+$의 직합이다. $M$이 $S$ 위의",
        ],
        "concept": "idéal gradué",
    },
    {
        "id": "R39-IDEAL-002", "source_lines": [1539],
        "source_text": [r"Soit $\mathfrak{p}$ un idéal premier gradué de l'anneau gradué $S$~;"],
        "target_lines": [1559],
        "old": [r"$\mathfrak{p}$를 등급환 $S$의 등급 소아이디얼이라 하자. 그러면"],
        "new": [r"$\mathfrak{p}$를 등급환 $S$의 동차 소아이디얼이라 하자. 그러면"],
        "concept": "idéal premier gradué",
    },
    {
        "id": "R39-IDEAL-003", "source_lines": [1552],
        "source_text": [r"sous-groupe de $S_n$. Pour qu'il existe un idéal premier gradué"],
        "target_lines": [1574, 1575],
        "old": [
            r"$\mathfrak{p}\cap S_n=\mathfrak{p}_n$을 만족하는 $S$의 등급",
            r"소아이디얼 $\mathfrak{p}$가 존재하기 위한 필요충분조건은 다음 조건들이",
        ],
        "new": [
            r"$\mathfrak{p}\cap S_n=\mathfrak{p}_n$을 만족하는 $S$의 동차",
            r"소아이디얼 $\mathfrak{p}$가 존재하기 위한 필요충분조건은 다음 조건들이",
        ],
        "concept": "idéal premier gradué",
    },
    {
        "id": "R39-IDEAL-004", "source_lines": [1564],
        "source_text": [r"En outre l'idéal premier gradué $\mathfrak{p}$ est alors unique."],
        "target_lines": [1586],
        "old": [r"또한 이때 등급 소아이디얼 $\mathfrak{p}$는 유일하다."],
        "new": [r"또한 이때 동차 소아이디얼 $\mathfrak{p}$는 유일하다."],
        "concept": "idéal premier gradué",
    },
    {
        "id": "R39-IDEAL-005", "source_lines": [1612],
        "source_text": [r"d'un idéal premier gradué de $S$ \emph{ne contenant pas $S_+$} (cet idéal"],
        "target_lines": [1634],
        "old": [r"\emph{$S_+$를 포함하지 않는} $S$의 등급 소아이디얼의 교집합이면 이를"],
        "new": [r"\emph{$S_+$를 포함하지 않는} $S$의 동차 소아이디얼의 교집합이면 이를"],
        "concept": "idéal premier gradué",
    },
    {
        "id": "R39-IDEAL-006", "source_lines": [1611],
        "source_text": [r"\emph{idéal premier gradué de $S_+$} si elle est l'intersection de $S_+$ et"],
        "target_lines": [1635],
        "old": [r"\emph{$S_+$의 등급 소아이디얼}이라 한다(더욱이 이 소아이디얼은"],
        "new": [r"\emph{$S_+$의 동차 소아이디얼}이라 한다(더욱이 이 소아이디얼은"],
        "concept": "idéal premier gradué",
    },
    {
        "id": "R39-IDEAL-007", "source_lines": [1620],
        "source_text": [r"$S_+$. Si $\mathfrak{J}$ est un idéal \emph{gradué} de $S_+$, sa racine"],
        "target_lines": [1642],
        "old": [r"집합이다. $\mathfrak{J}$가 $S_+$의 \emph{등급} 아이디얼이면 그 근기"],
        "new": [r"집합이다. $\mathfrak{J}$가 $S_+$의 \emph{동차} 아이디얼이면 그 근기"],
        "concept": r"idéal \emph{gradué}",
    },
    {
        "id": "R39-IDEAL-008", "source_lines": [1621],
        "source_text": [r"$r_+(\mathfrak{J})$ est un idéal gradué~: en passant à l'anneau quotient"],
        "target_lines": [1643],
        "old": [r"$r_+(\mathfrak{J})$도 등급 아이디얼이다. 실제로 몫환"],
        "new": [r"$r_+(\mathfrak{J})$도 동차 아이디얼이다. 실제로 몫환"],
        "concept": "idéal gradué",
    },
    {
        "id": "R39-IDEAL-009", "source_lines": [1640],
        "source_text": [r"est un idéal premier gradué de $S_+$, $S/\mathfrak{p}$ est essentiellement"],
        "target_lines": [1664, 1665],
        "old": [
            r"$\mathfrak{p}$가 $S_+$의",
            r"등급 소아이디얼이면 $S/\mathfrak{p}$가 본질적으로 정역임은 명백하다.",
        ],
        "new": [
            r"$\mathfrak{p}$가 $S_+$의",
            r"동차 소아이디얼이면 $S/\mathfrak{p}$가 본질적으로 정역임은 명백하다.",
        ],
        "concept": "idéal premier gradué",
    },
)
EXPECTED_SOURCE_LOCUS_LINES = [1326, 1539, 1552, 1564, 1611, 1612, 1620, 1621, 1640]
PREDECESSORS = (
    ("private", "controls/R39_INTEGRATION_TRANSACTION.json", 18_471, "CD7D2B4C0FAEC31277F27E5F960CA0B9774220603F474D777A610BA8A8CA792D"),
    ("private", "controls/R39_TRANSLATION_INTEGRATION.json", 6_610, "BA1B7D43FC93365C21F86E7D1494CB59483DA7863EF16E4B5D80BFF48161AF6B"),
    ("public", "evidence/controls/R39_TRANSLATION_INTEGRATION.json", 6_610, "BA1B7D43FC93365C21F86E7D1494CB59483DA7863EF16E4B5D80BFF48161AF6B"),
    ("private", "controls/R39_AUTHORITY_COMMENT_RESEAL_TRANSACTION.json", 15_633, "1967B49B19B299B93F621838A61BB65177119DA25877B8F21C925C089EB23819"),
    ("private", "controls/R39_AUTHORITY_COMMENT_RESEAL.json", 5_469, "63B55B0B04FA708E31434A84EE5CE57A66157380BB82615F872E83E8028A8080"),
    ("public", "evidence/controls/R39_AUTHORITY_COMMENT_RESEAL.json", 5_469, "63B55B0B04FA708E31434A84EE5CE57A66157380BB82615F872E83E8028A8080"),
    ("private", "controls/R39_R43_SEQUENTIAL_CHAIN_REBASE_20260906.json", 13_319, "54ED653F27FF96FECB315BEE0029BD6FFE087898DC37951D4C5F0A2A6255CE6C"),
    ("public", "evidence/controls/R39_R43_SEQUENTIAL_CHAIN_REBASE_20260906.json", 13_319, "54ED653F27FF96FECB315BEE0029BD6FFE087898DC37951D4C5F0A2A6255CE6C"),
)
CROSSWALK = {
    "path": "controls/EGA_STACKS_KO_TERMINOLOGY_CROSSWALK_20260906.json",
    "bytes": 35_543, "sha256": "844FA08B97F5B8CF206925F443DD218B8378B30A2E376D2664F9F1DEF3572A26",
}
R45_CONTROL = {
    "path": "controls/R45_TRANSLATION_ADMISSION.json",
    "public_path": "evidence/controls/R45_TRANSLATION_ADMISSION.json",
    "bytes": 16_807, "sha256": "47D257599805B6045168743EAB2A96CCB68D0C7CC932535F0BA66BA6C87E50EC",
}
MANIFEST_PRE = {
    "path": "source/CUMULATIVE_INPUTS.json", "bytes": 16_275,
    "sha256": "2C75A0AC2430D38CBBEF69E3A7EDBCD67AA090C534B5F29A4A7CC61E14CF4E59",
}
PUBLIC_ALIASES = (
    "CURSOR.json", "PROGRAM_CURSOR.json", "STATE.json", "PROGRAM_STATE.json",
    "QA_STATE.json", "VISUAL_QA.json", "SOURCE_AUTHORITY.json",
    "PROGRAM_AUTHORITY.json", "DATACITE_RELATIONS.json",
)
LEDGERS = ("decisions.jsonl", "evidence.jsonl", "hard.jsonl")
CONTROL_PRIVATE = Path("controls/R39_IDEAL_TERMINOLOGY_RESEAL.json")
CONTROL_PUBLIC = Path("evidence/controls/R39_IDEAL_TERMINOLOGY_RESEAL.json")
JOURNAL_REL = Path("controls/R39_IDEAL_TERMINOLOGY_RESEAL_TRANSACTION.json")
WORK_REL = Path("controls/.r39-ideal-terminology-reseal")
MUTEX_NAME = r"Global\InterlanguageAgKoR39IdealTerminologyResealV1"
RESULT = "PASS_R39_TYPED_HOMOGENEOUS_IDEAL_TERMINOLOGY_RESEAL"
DECISION_ID = "AGKO-D190"
EVIDENCE_ID = "AGKO-E-R39-IDEAL-TERMINOLOGY-RESEAL"
HARD_ID = "AGKO-H165"
UNIT_ID = "AGKO-EGA2-S1-R39-IDEAL-TERMINOLOGY-RESEAL-R1"
UNIT_ORDER = 2_136
PRIVATE_RE = re.compile(r"(?i)(?:(?<![A-Z0-9])[A-Z]:[\\/][^\s\"']+|\\\\[A-Z0-9._-]+[\\/][^\s\"']+|/(?:home|Users)/[^/\s\"']+/[^\s\"']*)")
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


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
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
    require(abs((datetime.now(stamp.tzinfo) - stamp).total_seconds()) <= 300, "--at must be actual current wall time (within five minutes)")
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
        roots.repo / MANIFEST_PRE["path"],
        *(roots.private / name for name in LEDGERS),
        *(roots.repo / "evidence" / name for name in LEDGERS),
        roots.private / "index/units.jsonl", roots.repo / "evidence/index/units.jsonl",
    ]
    require(len(paths) == 25 and len(paths) == len({path.resolve(strict=False) for path in paths}), "output inventory drift")
    return paths


def snapshot(paths: Iterable[Path], roots: Roots) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(paths, key=lambda item: role(item, roots).casefold()):
        locator = role(path, roots)
        if path.exists():
            regular(path, locator)
            rows.append({"path": locator, "exists": True, **file_identity(path)})
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


def predecessor_path(roots: Roots, domain: str, locator: str) -> Path:
    require(domain in {"private", "public"}, "unknown predecessor domain")
    return (roots.private if domain == "private" else roots.repo) / locator


def verify_authorities(roots: Roots) -> dict[str, bytes]:
    source = exact(roots.canonical / SOURCE["path"], SOURCE, "canonical EGA II source")
    source_lines = source.decode("utf-8").splitlines()
    require(len(source_lines) >= 1780, "canonical source is too short")
    prefix = ("\n".join(source_lines[:1780]) + "\n").encode("utf-8")
    require(identity(prefix) == {"bytes": SOURCE["prefix_bytes"], "sha256": SOURCE["prefix_sha256"]}, "canonical admitted prefix drift")
    regex = re.compile(r"idéal(?: premier)? (?:\\emph\{)?gradué(?:\})?")
    found = []
    for number, line in enumerate(source_lines[:1780], 1):
        found.extend([number] * len(regex.findall(line)))
    require(found == EXPECTED_SOURCE_LOCUS_LINES, f"canonical homogeneous-ideal locus inventory drift: {found}")
    for locus in LOCI:
        actual = [source_lines[number - 1] for number in locus["source_lines"]]
        require(actual == locus["source_text"], f"canonical source locus drift: {locus['id']}")
    predecessor_bytes: dict[str, bytes] = {}
    for domain, locator, size, checksum in PREDECESSORS:
        key = f"{domain}:{locator}"
        predecessor_bytes[key] = exact(predecessor_path(roots, domain, locator), {"bytes": size, "sha256": checksum}, key)
    crosswalk = exact(roots.private / CROSSWALK["path"], CROSSWALK, "typed CJK/Korean crosswalk")
    crosswalk_value = parse(crosswalk, "typed crosswalk")
    matches = [row for row in crosswalk_value.get("recommended_typed_mappings", []) if row.get("id") == "XW-KO-005"]
    require(len(matches) == 1 and matches[0] == {
        "id": "XW-KO-005", "concept": "homogeneous",
        "source_type": "graded element, ideal, or component",
        "ega_ko": "동차", "stacks_ko": "동차", "recommendation": "동차",
        "relation": "shared_exact", "confidence": "high",
    }, "XW-KO-005 policy drift")
    r45_private = exact(roots.private / R45_CONTROL["path"], R45_CONTROL, "private R45 terminology evidence")
    r45_public = exact(roots.repo / R45_CONTROL["public_path"], R45_CONTROL, "public R45 terminology evidence")
    require(r45_private == r45_public, "R45 terminology evidence mirrors differ")
    r45 = parse(r45_private, "R45 terminology evidence")
    repairs = r45.get("wording_reseal", {}).get("repairs", [])
    mapped = [row for row in repairs if row.get("id") == "R45-WORD-001"]
    require(len(mapped) == 1 and mapped[0].get("preimage") == r"등급\n    소아이디얼" and mapped[0].get("postimage") == r"동차\n    소아이디얼" and "XW-KO-005" in mapped[0].get("reason", ""), "R45 homogeneous-ideal evidence drift")
    return {"source": source, "crosswalk": crosswalk, "r45": r45_private, **predecessor_bytes}


def mask_hangul(text: str) -> str:
    return "".join("H" if "\uac00" <= char <= "\ud7a3" else char for char in text)


def reseal_target(data: bytes) -> bytes:
    require(identity(data) == {"bytes": PRE_TARGET["bytes"], "sha256": PRE_TARGET["sha256"]}, "R39 ideal-reseal target preimage drift")
    require(b"\r" not in data and data.count(b"\n") == PRE_TARGET["lf_lines"], "target LF framing drift")
    text = data.decode("utf-8")
    require(len(text) == PRE_TARGET["characters"], "target character count drift")
    for word, count in PRE_COUNTS.items():
        require(text.count(word) == count, f"preimage typed-token count drift: {word}")
    for form, count in OLD_FORMS:
        require(text.count(form) == count, f"old ideal-form multiplicity drift: {form!r}")
    for form, _ in NEW_FORMS:
        require(text.count(form) == 0, f"new ideal form already present: {form!r}")
    lines = text.splitlines()
    require(len(lines) == PRE_TARGET["lf_lines"], "target physical-line count drift")
    touched: list[int] = []
    for locus in LOCI:
        indexes = [number - 1 for number in locus["target_lines"]]
        require([lines[index] for index in indexes] == locus["old"], f"target locus preimage drift: {locus['id']}")
        require(len(indexes) == len(locus["new"]), f"target locus arity drift: {locus['id']}")
        for index, replacement in zip(indexes, locus["new"]):
            lines[index] = replacement
            touched.append(index)
    require(len(set(touched)) == len(touched), "target locus lines overlap")
    result_text = "\n".join(lines) + "\n"
    result = result_text.encode("utf-8")
    require(identity(result) == {"bytes": POST_TARGET["bytes"], "sha256": POST_TARGET["sha256"]}, "predicted ideal-reseal target identity mismatch")
    require(len(result_text) == POST_TARGET["characters"] and result.count(b"\n") == POST_TARGET["lf_lines"] and b"\r" not in result, "postimage metrics drift")
    for word, count in POST_COUNTS.items():
        require(result_text.count(word) == count, f"postimage typed-token count drift: {word}")
    for form, _ in OLD_FORMS:
        require(result_text.count(form) == 0, f"old ideal form survives: {form!r}")
    for form, count in NEW_FORMS:
        require(result_text.count(form) == count, f"new ideal-form multiplicity drift: {form!r}")
    require(mask_hangul(text) == mask_hangul(result_text), "non-Hangul or Hangul-position structure changed")
    require(re.findall(r"\$[^$\n]*\$", text) == re.findall(r"\$[^$\n]*\$", result_text), "inline formula sequence changed")
    require(re.findall(r"\\[A-Za-z]+", text) == re.findall(r"\\[A-Za-z]+", result_text), "TeX command sequence changed")
    require((text.count("{"), text.count("}"), text.count("$"), text.count("\\")) == (result_text.count("{"), result_text.count("}"), result_text.count("$"), result_text.count("\\")), "TeX delimiter structure changed")
    reverse_lines = result_text.splitlines()
    for locus in reversed(LOCI):
        indexes = [number - 1 for number in locus["target_lines"]]
        require([reverse_lines[index] for index in indexes] == locus["new"], f"reverse locus preimage drift: {locus['id']}")
        for index, replacement in zip(indexes, locus["old"]):
            reverse_lines[index] = replacement
    reverse = ("\n".join(reverse_lines) + "\n").encode("utf-8")
    require(reverse == data and identity(reverse) == {"bytes": PRE_TARGET["bytes"], "sha256": PRE_TARGET["sha256"]}, "exact reverse reconstruction failed")
    return result


def update_manifest(data: bytes) -> bytes:
    value = parse(data, "cumulative input manifest")
    matrix = [row for row in value.get("coverage_matrix", []) if row.get("target_path") == "c2s1.tex"]
    require(len(matrix) == 1 and matrix[0].get("target_sha256") == PRE_TARGET["sha256"], "manifest live target drift")
    matrix[0]["target_sha256"] = POST_TARGET["sha256"]
    required = value.get("reconciliation", {}).get("required_latest_records")
    previous = "AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1"
    require(isinstance(required, list) and required.count(previous) == 1 and UNIT_ID not in required, "manifest latest-record frontier drift")
    required[required.index(previous)] = UNIT_ID
    return jbytes(value)


def build_control(at: str, token: str, manifest: bytes) -> bytes:
    value = {
        "schema": "agko-r39-ideal-terminology-reseal-v1",
        "time": at,
        "precision": "second",
        "scope": "Exactly nine source-mapped Korean homogeneous-ideal adjective spans in EGA II canonical lines1-1780; all non-ideal graded terminology and all other bytes remain unchanged.",
        "policy": {
            "typed_mapping": {
                "id": "XW-KO-005", "concept": "homogeneous",
                "source_type": "graded element, ideal, or component",
                "preimage": "등급", "postimage": "동차",
                "confidence": "high", "control": dict(CROSSWALK),
            },
            "independent_later_unit": {
                "control": dict(R45_CONTROL),
                "repair": "R45-WORD-001: exact idéal premier gradué context corrected from 등급 소아이디얼 to 동차 소아이디얼",
            },
            "professional_korean_thesis_attestation": "동차 아이디얼 attested; supplied as corroborating evidence in the current authority directive.",
            "negative_evidence": "No primary evidence supports 등급 아이디얼 for these homogeneous-ideal loci.",
            "preservation_rule": "Keep 등급 for graded rings, modules, algebras, grading structures, and every non-ideal concept.",
        },
        "authority": dict(SOURCE),
        "exhaustive_source_inventory": {
            "regex_semantics": r"idéal(?: premier)? (?:\emph{)?gradué(?:})?",
            "count": len(LOCI), "source_lines": EXPECTED_SOURCE_LOCUS_LINES,
            "loci": copy.deepcopy(LOCI),
        },
        "target_transition": {
            "preimage": dict(PRE_TARGET), "postimage": dict(POST_TARGET),
            "old_form_counts": [{"form": form, "count": count} for form, count in OLD_FORMS],
            "new_form_counts": [{"form": form, "count": count} for form, count in NEW_FORMS],
            "global_typed_counts": {"preimage": dict(PRE_COUNTS), "postimage": dict(POST_COUNTS)},
            "exact_reverse_reconstruction": True,
            "non_hangul_projection": "exactly unchanged",
            "formula_and_tex_command_sequences": "exactly unchanged",
            "bytes_characters_lf": "exactly unchanged",
            "private_public_mirrors": "exact",
        },
        "historical_evidence_preserved": [
            {"domain": domain, "path": locator, "bytes": size, "sha256": checksum}
            for domain, locator, size, checksum in PREDECESSORS
        ],
        "cumulative_manifest_postimage": {"path": MANIFEST_PRE["path"], **identity(manifest)},
        "transaction": {
            "journal": str(JOURNAL_REL).replace("\\", "/"),
            "fresh_preimage_sha256": token,
            "all_postimages_computed_before_first_write": True,
            "atomic_mirrored_writes_and_exact_rollback": True,
        },
        "ledger_records": {
            "decision": DECISION_ID, "evidence": EVIDENCE_ID,
            "hard": HARD_ID, "unit": UNIT_ID, "unit_order": UNIT_ORDER,
        },
        "downstream": "Any prospective R40+ cumulative hash rooted in B3F0 is historical after this reseal and requires additive recomputation before later integration.",
        "limits": "No unrelated terminology, TeX build, PDF, Git, UI, publication, or later-unit integration action.",
        "result": RESULT,
    }
    result = jbytes(value)
    validate_public_delta(None, result, "new R39 ideal-terminology control")
    return result


def reseal_ref(control_id: Mapping[str, Any], public: bool) -> dict[str, Any]:
    return {
        "status": RESULT,
        "control": {
            "path": ("evidence/controls/" if public else "controls/") + CONTROL_PRIVATE.name,
            **dict(control_id), "private_public_mirrors_exact": True,
        },
        "old_target": dict(PRE_TARGET), "current_target": dict(POST_TARGET),
        "source_loci": {"count": len(LOCI), "lines": EXPECTED_SOURCE_LOCUS_LINES},
        "terminology": {"typed_mapping": "XW-KO-005", "old": "등급", "new": "동차", "ideal_only": True},
        "exact_reverse_reconstruction": True,
    }


def historical_overlay(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    integration = value.get("ega_ii", {}).get("r39_translation_integration", {}) if name == "authority.json" else value.get("r39_translation_integration", {})
    require(integration.get("target", {}).get("sha256") == "F3DD70691223B0D35052B4D6F4CF5E77B72AA2C5F352EDE5D9C83E98704C8257", f"historical integration target drift: {name}")
    require(integration.get("control", {}).get("sha256") == "BA1B7D43FC93365C21F86E7D1494CB59483DA7863EF16E4B5D80BFF48161AF6B", f"historical integration control drift: {name}")
    declaration = value.get("r39_authority_comment_reseal", {})
    require(declaration.get("current_target", {}).get("sha256") == PRE_TARGET["sha256"], f"authority-comment predecessor target drift: {name}")
    require(declaration.get("control", {}).get("sha256") == "63B55B0B04FA708E31434A84EE5CE57A66157380BB82615F872E83E8028A8080", f"authority-comment predecessor control drift: {name}")
    return declaration


def update_live_state(data: bytes, name: str, ref: Mapping[str, Any], at: str) -> bytes:
    value = parse(data, name)
    require("r39_ideal_terminology_reseal" not in value, f"state already contains ideal reseal: {name}")
    historical_overlay(value, name)
    if name == "cursor.json":
        current = value.get("target", {})
    elif name == "state.json":
        current = value.get("active", {}).get("target", {})
    elif name == "authority.json":
        admitted = [row for row in value.get("ega_ii", {}).get("admitted", []) if row.get("target") == "ega/II/c2s1.tex"]
        require(len(admitted) == 1, "private authority target multiplicity drift")
        current = admitted[0]
    else:
        current = value.get("target", {})
    require(current.get("sha256") == PRE_TARGET["sha256"], f"live target pointer drift: {name}")
    current["sha256"] = POST_TARGET["sha256"]
    value["r39_ideal_terminology_reseal"] = copy.deepcopy(ref)
    value["updated"] = at
    return jbytes(value)


def verify_live_state(data: bytes, name: str, control_sha256: str, at: str) -> None:
    value = parse(data, name)
    historical_overlay(value, name)
    if name == "cursor.json":
        current = value.get("target", {})
    elif name == "state.json":
        current = value.get("active", {}).get("target", {})
    elif name == "authority.json":
        admitted = [row for row in value.get("ega_ii", {}).get("admitted", []) if row.get("target") == "ega/II/c2s1.tex"]
        require(len(admitted) == 1, "private authority postimage multiplicity drift")
        current = admitted[0]
    else:
        current = value.get("target", {})
    require(current.get("sha256") == POST_TARGET["sha256"], f"live target postimage drift: {name}")
    ref = value.get("r39_ideal_terminology_reseal", {})
    require(ref.get("status") == RESULT, f"ideal-reseal overlay status drift: {name}")
    require(ref.get("old_target", {}).get("sha256") == PRE_TARGET["sha256"] and ref.get("current_target", {}).get("sha256") == POST_TARGET["sha256"], f"ideal-reseal overlay transition drift: {name}")
    require(ref.get("control", {}).get("sha256") == control_sha256, f"ideal-reseal overlay control drift: {name}")
    require(value.get("updated") == at, f"ideal-reseal overlay timestamp drift: {name}")


def append_record(data: bytes, record: Mapping[str, Any], label: str) -> bytes:
    rows = parse_jsonl(data, label)
    require(sum(row.get("id") == record["id"] for row in rows) == 0, f"record already exists: {record['id']}")
    return data + jlbytes(record)


def records(at: str, control_id: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    common = {"time": at, "precision": "second"}
    return {
        "decisions.jsonl": {
            "id": DECISION_ID, **common, "kind": "r39_typed_homogeneous_ideal_terminology_reseal",
            "scope": "Nine exact canonical EGA II homogeneous-ideal loci within source lines1-1780",
            "choice": "Use 동차 아이디얼 / 동차 소아이디얼 only where the French source denotes idéal gradué / idéal premier gradué; preserve 등급 for graded rings, modules, algebras, and grading structures.",
            "evidence": [f"XW-KO-005 {CROSSWALK['sha256']}", f"R45-WORD-001 {R45_CONTROL['sha256']}", f"{POST_TARGET['bytes']}B/{POST_TARGET['sha256']}", f"controls/{CONTROL_PRIVATE.name} {control_id['bytes']}B/{control_id['sha256']}"],
            "uncertainty": "None at the nine exact source-typed loci; no broad lexical replacement was performed.",
            "review": RESULT,
        },
        "evidence.jsonl": {
            "id": EVIDENCE_ID, **common, "kind": "typed_homogeneous_ideal_terminology_reseal_evidence",
            "source_lines": EXPECTED_SOURCE_LOCUS_LINES, "locus_count": len(LOCI),
            "preimage": dict(PRE_TARGET), "postimage": dict(POST_TARGET),
            "global_counts": {"preimage": dict(PRE_COUNTS), "postimage": dict(POST_COUNTS)},
            "reverse_reconstruction": PRE_TARGET["sha256"],
            "control": {"private": f"controls/{CONTROL_PRIVATE.name}", "public": f"evidence/controls/{CONTROL_PRIVATE.name}", **dict(control_id)},
            "result": RESULT,
        },
        "hard.jsonl": {
            "id": HARD_ID, **common, "status": "controlling_r39_typed_homogeneous_ideal_reseal",
            "scope": "Every admitted source occurrence of idéal gradué / idéal premier gradué through canonical line1780",
            "symptom": "Nine ideal-denoting Korean loci used the general graded-object adjective 등급 despite the high-confidence typed homogeneous mapping 동차.",
            "resolution": "Source-map each exact locus, change only the ideal adjective, reverse-reconstruct B3F0 exactly, and preserve all non-ideal graded terminology.",
            "tests": f"9/9 source loci; target {POST_TARGET['sha256']}; exact mirrors, non-Hangul projection, formulas, TeX commands, reverse reconstruction and rollback",
            "recurrence": "Never replace 등급 globally; require source-type evidence that the object is a homogeneous ideal.",
            "related": [DECISION_ID, EVIDENCE_ID, UNIT_ID],
        },
    }


def unit_row(control_id: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": UNIT_ID, "kind": "section_state_update", "parent": "AGKO-EGA2-S1", "order": UNIT_ORDER,
        "authority": {
            "path": SOURCE["path"], "locator": "lines1-1780 through2.2.6; nine homogeneous-ideal loci",
            "bytes": SOURCE["prefix_bytes"], "sha256": SOURCE["prefix_sha256"],
            "whole_bytes": SOURCE["bytes"], "whole_sha256": SOURCE["sha256"],
        },
        "target": {
            "path": "ega/II/c2s1.tex", "locator": "nine exact ideal-adjective spans; all other bytes structurally unchanged",
            **dict(POST_TARGET), "preimage_sha256": PRE_TARGET["sha256"],
            "identity_status": "exact_private_public_mirrors_reverse_reconstructed",
        },
        "relations": [
            "supersedes-live-identity:AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1",
            f"controls/{CONTROL_PRIVATE.name} {control_id['sha256']}",
            "XW-KO-005 homogeneous ideal -> 동차 아이디얼",
        ],
        "language": "ko-KR",
        "state": {
            "translation": "complete", "build": "pending", "visual": "pending",
            "publication": "private_working", "integration": "pass_exact_mirrors_typed_terminology_resealed",
        },
    }


def append_unit(data: bytes, row: Mapping[str, Any], label: str) -> bytes:
    rows = parse_jsonl(data, label)
    require(sum(item.get("id") == UNIT_ID for item in rows) == 0, "ideal-reseal unit already exists")
    require(sum(item.get("id") == "AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1" for item in rows) == 1, "predecessor unit multiplicity drift")
    require(max(item.get("order", -1) for item in rows if type(item.get("order")) is int) == 2_135, "unit order frontier drift")
    return data + jlbytes(row)


def prerequisite_paths(roots: Roots) -> list[Path]:
    paths = [
        Path(__file__).resolve(strict=True),
        roots.canonical / SOURCE["path"],
        roots.private / CROSSWALK["path"],
        roots.private / R45_CONTROL["path"],
        roots.repo / R45_CONTROL["public_path"],
        *(predecessor_path(roots, domain, locator) for domain, locator, _, _ in PREDECESSORS),
    ]
    unique = {path.resolve(strict=False): path for path in paths}
    return list(unique.values())


def build_outputs(roots: Roots, at: str, token: str, authorities: Mapping[str, bytes]) -> dict[Path, bytes]:
    require(bool(authorities), "authority inventory missing")
    private_target_path = roots.private / "ega/II/c2s1.tex"
    public_target_path = roots.repo / "source/c2s1.tex"
    private_target = private_target_path.read_bytes()
    public_target = public_target_path.read_bytes()
    require(private_target == public_target, "R39 target mirrors differ before ideal reseal")
    target = reseal_target(private_target)
    manifest_pre = exact(roots.repo / MANIFEST_PRE["path"], MANIFEST_PRE, "cumulative manifest preimage")
    manifest = update_manifest(manifest_pre)
    control = build_control(at, token, manifest)
    control_id = identity(control)
    outputs: dict[Path, bytes] = {
        private_target_path: target,
        public_target_path: target,
        roots.private / CONTROL_PRIVATE: control,
        roots.repo / CONTROL_PUBLIC: control,
        roots.repo / MANIFEST_PRE["path"]: manifest,
    }
    private_ref = reseal_ref(control_id, False)
    public_ref = reseal_ref(control_id, True)
    for name in ("cursor.json", "state.json", "authority.json"):
        path = roots.private / name
        outputs[path] = update_live_state(path.read_bytes(), name, private_ref, at)
    for name in PUBLIC_ALIASES:
        path = roots.repo / "evidence" / name
        outputs[path] = update_live_state(path.read_bytes(), name, public_ref, at)
    new_records = records(at, control_id)
    for name in LEDGERS:
        private = roots.private / name
        public = roots.repo / "evidence" / name
        outputs[private] = append_record(private.read_bytes(), new_records[name], f"private {name}")
        outputs[public] = append_record(public.read_bytes(), new_records[name], f"public {name}")
    row = unit_row(control_id)
    private_units = roots.private / "index/units.jsonl"
    public_units = roots.repo / "evidence/index/units.jsonl"
    outputs[private_units] = append_unit(private_units.read_bytes(), row, "private units")
    outputs[public_units] = append_unit(public_units.read_bytes(), row, "public units")
    require(set(outputs) == set(output_paths(roots)), "postimage path inventory drift")
    for path, data in outputs.items():
        if path.resolve(strict=False).is_relative_to(roots.repo):
            validate_public_delta(path.read_bytes() if path.exists() else None, data, role(path, roots))
    return outputs


def plan(roots: Roots, at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[Path, bytes], str]:
    authorities = verify_authorities(roots)
    for path in output_paths(roots):
        if path in (roots.private / CONTROL_PRIVATE, roots.repo / CONTROL_PUBLIC):
            require(not path.exists() and not path.is_symlink(), "ideal-terminology reseal control already exists")
        else:
            regular(path, role(path, roots))
    inputs = snapshot(prerequisite_paths(roots), roots)
    preimages = snapshot(output_paths(roots), roots)
    token = sha(jbytes({
        "schema": "agko-r39-ideal-terminology-reseal-preimage-v1",
        "time": at, "inputs": inputs, "preimages": preimages,
    }))
    outputs = build_outputs(roots, at, token, authorities)
    return inputs, preimages, outputs, token


def postimages(outputs: Mapping[Path, bytes], roots: Roots) -> list[dict[str, Any]]:
    return [
        {"path": role(path, roots), **identity(data)}
        for path, data in sorted(outputs.items(), key=lambda item: role(item[0], roots).casefold())
    ]


def verify_outputs(roots: Roots, journal: Mapping[str, Any]) -> None:
    for row in journal["postimages"]:
        path = resolve_role(row["path"], roots)
        require(file_identity(path) == {"bytes": row["bytes"], "sha256": row["sha256"]}, f"postimage drift: {row['path']}")
    private = (roots.private / "ega/II/c2s1.tex").read_bytes()
    public = (roots.repo / "source/c2s1.tex").read_bytes()
    require(private == public and identity(private) == {"bytes": POST_TARGET["bytes"], "sha256": POST_TARGET["sha256"]}, "final target mirrors/identity drift")
    text = private.decode("utf-8")
    require(len(text) == POST_TARGET["characters"] and private.count(b"\n") == POST_TARGET["lf_lines"] and b"\r" not in private, "final target metrics drift")
    for form, _ in OLD_FORMS:
        require(text.count(form) == 0, f"final old form survives: {form!r}")
    for form, count in NEW_FORMS:
        require(text.count(form) == count, f"final new form multiplicity drift: {form!r}")
    lines = text.splitlines()
    for locus in LOCI:
        require([lines[number - 1] for number in locus["target_lines"]] == locus["new"], f"final target locus drift: {locus['id']}")
    control_private = (roots.private / CONTROL_PRIVATE).read_bytes()
    control_public = (roots.repo / CONTROL_PUBLIC).read_bytes()
    control = parse(control_private, "ideal-reseal control")
    require(control_private == control_public and control.get("result") == RESULT, "ideal-reseal control mirror/result drift")
    require(control.get("target_transition", {}).get("preimage", {}).get("sha256") == PRE_TARGET["sha256"] and control.get("target_transition", {}).get("postimage", {}).get("sha256") == POST_TARGET["sha256"], "control target transition drift")
    control_sha256 = sha(control_private)
    for name in ("cursor.json", "state.json", "authority.json"):
        verify_live_state((roots.private / name).read_bytes(), name, control_sha256, journal["time"])
    for name in PUBLIC_ALIASES:
        verify_live_state((roots.repo / "evidence" / name).read_bytes(), name, control_sha256, journal["time"])
    manifest = parse_path(roots.repo / MANIFEST_PRE["path"], "updated manifest")
    entries = [row for row in manifest.get("coverage_matrix", []) if row.get("target_path") == "c2s1.tex"]
    require(len(entries) == 1 and entries[0].get("target_sha256") == POST_TARGET["sha256"], "manifest c2s1 binding drift")
    required = manifest.get("reconciliation", {}).get("required_latest_records", [])
    require(required.count(UNIT_ID) == 1 and "AGKO-EGA2-S1-R39-DECLARATION-RESEAL-R1" not in required, "manifest unit frontier drift")
    for name, record_id in (("decisions.jsonl", DECISION_ID), ("evidence.jsonl", EVIDENCE_ID), ("hard.jsonl", HARD_ID)):
        a = [row for row in parse_jsonl((roots.private / name).read_bytes(), f"private {name}") if row.get("id") == record_id]
        b = [row for row in parse_jsonl((roots.repo / "evidence" / name).read_bytes(), f"public {name}") if row.get("id") == record_id]
        require(len(a) == len(b) == 1 and a[0] == b[0], f"ledger record mirror/multiplicity drift: {record_id}")
    unit_records = []
    for path in (roots.private / "index/units.jsonl", roots.repo / "evidence/index/units.jsonl"):
        found = [row for row in parse_jsonl(path.read_bytes(), str(path)) if row.get("id") == UNIT_ID]
        require(len(found) == 1 and found[0].get("order") == UNIT_ORDER and found[0].get("target", {}).get("sha256") == POST_TARGET["sha256"], "unit record drift")
        unit_records.append(found[0])
    require(unit_records[0] == unit_records[1], "unit record mirrors differ")
    verify_authorities(roots)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".r39-ideal-tmp-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
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
    atomic_write(path, jbytes(value))


def transaction_root(roots: Roots, transaction_id: str) -> Path:
    base = (roots.private / WORK_REL).resolve(strict=False)
    result = (base / transaction_id).resolve(strict=False)
    require(result.parent == base, "unsafe transaction work root")
    return result


def load_journal(roots: Roots) -> dict[str, Any] | None:
    path = roots.private / JOURNAL_REL
    if not path.exists() and not path.is_symlink():
        return None
    value = parse_path(path, "ideal-terminology transaction journal")
    require(value.get("schema") == "agko-r39-ideal-terminology-reseal-transaction-v1", "transaction journal schema drift")
    require(value.get("status") in {"PREPARING", "PREPARED", "APPLYING", "VERIFYING", "COMMITTED", "ROLLED_BACK", "RECOVERY_CONFLICT"}, "transaction journal status drift")
    expected = {role(path, roots) for path in output_paths(roots)}
    for key in ("preimages", "postimages"):
        rows = value.get(key)
        require(isinstance(rows, list) and {row.get("path") for row in rows} == expected, f"journal {key} inventory drift")
    return value


def rollback(roots: Roots, journal: dict[str, Any]) -> None:
    pre = {row["path"]: row for row in journal["preimages"]}
    post = {row["path"]: row for row in journal["postimages"]}
    order = [row["path"] for row in journal["postimages"]]
    backups = transaction_root(roots, journal["transaction_id"]) / "backups"
    conflicts = []
    for index, locator in reversed(list(enumerate(order))):
        path = resolve_role(locator, roots)
        old = pre[locator]
        new = {"bytes": post[locator]["bytes"], "sha256": post[locator]["sha256"]}
        if path.exists():
            actual = file_identity(path)
            if old["exists"] and actual == {"bytes": old["bytes"], "sha256": old["sha256"]}:
                continue
            if actual != new:
                conflicts.append(locator)
                continue
            if old["exists"]:
                backup = backups / f"{index:03d}.bin"
                if not backup.exists() or file_identity(backup) != {"bytes": old["bytes"], "sha256": old["sha256"]}:
                    conflicts.append(locator)
                else:
                    os.replace(backup, path)
            else:
                path.unlink()
        elif old["exists"]:
            backup = backups / f"{index:03d}.bin"
            if not backup.exists() or file_identity(backup) != {"bytes": old["bytes"], "sha256": old["sha256"]}:
                conflicts.append(locator)
            else:
                os.replace(backup, path)
    if conflicts:
        journal["status"] = "RECOVERY_CONFLICT"
        journal["conflicts"] = conflicts
        write_journal(roots.private / JOURNAL_REL, journal)
        raise RuntimeError("rollback refused unknown concurrent bytes")
    require_snapshot(journal["preimages"], roots)
    journal["status"] = "ROLLED_BACK"
    journal["applied"] = []
    write_journal(roots.private / JOURNAL_REL, journal)
    work = transaction_root(roots, journal["transaction_id"])
    if work.exists():
        shutil.rmtree(work)


@contextmanager
def mutex() -> Iterator[bool]:
    require(os.name == "nt", "Windows transaction mutex required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    kernel.WaitForSingleObject.restype = ctypes.c_uint
    handle = kernel.CreateMutexW(None, 0, MUTEX_NAME)
    require(bool(handle), "mutex creation failed")
    result = kernel.WaitForSingleObject(handle, 30_000)
    require(result in (0, 0x80), "mutex acquisition timeout")
    try:
        yield result == 0x80
    finally:
        kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def execute(roots: Roots, at: str, inputs: list[dict[str, Any]], preimages: list[dict[str, Any]], outputs: Mapping[Path, bytes], token: str, expected: str) -> dict[str, Any]:
    require(token == expected, "fresh-preimage token mismatch")
    existing = load_journal(roots)
    attempt = 1
    history = []
    if existing is not None:
        require(existing.get("status") == "ROLLED_BACK", "existing transaction is not recoverable from a fresh check")
        require_snapshot(existing["preimages"], roots)
        attempt = int(existing.get("attempt", 0)) + 1
        history = copy.deepcopy(existing.get("prior_attempts", [])) + [{
            "transaction_id": existing.get("transaction_id"), "attempt": existing.get("attempt"),
            "status": existing.get("status"), "fresh_preimage_sha256": existing.get("fresh_preimage_sha256"),
        }]
    require_snapshot(inputs, roots)
    require_snapshot(preimages, roots)
    transaction_id = "AGKO-R39-IDEAL-RESEAL-" + token[:20]
    work = transaction_root(roots, transaction_id)
    require(not work.exists(), "transaction work root exists")
    journal = {
        "schema": "agko-r39-ideal-terminology-reseal-transaction-v1",
        "transaction_id": transaction_id, "time": at,
        "fresh_preimage_sha256": token, "status": "PREPARING",
        "attempt": attempt, "abandoned_mutex_recovered": False,
        "inputs": inputs, "preimages": preimages,
        "postimages": postimages(outputs, roots), "applied": [],
        "conflicts": [], "prior_attempts": history,
    }
    write_journal(roots.private / JOURNAL_REL, journal)
    try:
        staged = work / "staged"
        backups = work / "backups"
        staged.mkdir(parents=True)
        backups.mkdir()
        order = sorted(outputs, key=lambda path: role(path, roots).casefold())
        require([role(path, roots) for path in order] == [row["path"] for row in journal["postimages"]], "transaction order drift")
        before = {row["path"]: row for row in preimages}
        for index, path in enumerate(order):
            stage = staged / f"{index:03d}.bin"
            with stage.open("xb") as stream:
                stream.write(outputs[path])
                stream.flush()
                os.fsync(stream.fileno())
            row = before[role(path, roots)]
            if row["exists"]:
                backup = backups / f"{index:03d}.bin"
                shutil.copyfile(path, backup)
                with backup.open("r+b") as stream:
                    os.fsync(stream.fileno())
                require(file_identity(backup) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "backup identity drift")
        journal["status"] = "PREPARED"
        write_journal(roots.private / JOURNAL_REL, journal)
        require_snapshot(inputs, roots)
        require_snapshot(preimages, roots)
        for index, path in enumerate(order):
            for remaining in order[index:]:
                row = before[role(remaining, roots)]
                expected_pre = {"bytes": row["bytes"], "sha256": row["sha256"]}
                require((remaining.exists() and file_identity(remaining) == expected_pre) if row["exists"] else not remaining.exists(), "concurrent output mutation")
            journal["status"] = "APPLYING"
            write_journal(roots.private / JOURNAL_REL, journal)
            os.replace(staged / f"{index:03d}.bin", path)
            require(file_identity(path) == identity(outputs[path]), "post-replace identity drift")
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
        except BaseException as recovery:
            raise RuntimeError("ideal reseal failed and exact recovery requires intervention") from recovery
        raise RuntimeError(f"ideal reseal failed and rolled back exactly: {type(exc).__name__}: {exc}") from exc
    try:
        shutil.rmtree(work)
        journal["work_directory_cleanup"] = "COMPLETE"
    except OSError as exc:
        journal["work_directory_cleanup"] = f"PENDING_RETRY:{type(exc).__name__}"
    try:
        write_journal(roots.private / JOURNAL_REL, journal)
    except OSError:
        pass
    return journal


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--private-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--canonical-root", type=Path)
    parser.add_argument("--at")
    parser.add_argument("--expected-fresh-preimage-sha256")
    return parser.parse_args()


def main() -> None:
    options = arguments()
    roots: Roots | None = None
    mutation = False
    try:
        roots = Roots.make(options.private_root, options.repo_root, options.canonical_root)
        at = validate_time(options.at)
        existing = load_journal(roots)
        if existing is not None and existing.get("status") == "COMMITTED":
            verify_outputs(roots, existing)
            print(json.dumps({
                "schema": "agko-r39-ideal-terminology-reseal-report-v1",
                "mode": "already_committed", "result": RESULT,
                "transaction_id": existing["transaction_id"],
                "outputs": existing["postimages"],
            }, ensure_ascii=True, indent=2))
            return
        if existing is not None and existing.get("status") not in {"ROLLED_BACK"}:
            if options.check:
                raise RuntimeError("incomplete transaction requires --execute recovery")
            with mutex():
                current = load_journal(roots)
                if current is not None and current.get("status") == "COMMITTED":
                    verify_outputs(roots, current)
                    return
                require(current is not None and current.get("status") not in {"ROLLED_BACK"}, "recovery state changed; rerun check")
                mutation = True
                rollback(roots, current)
            raise RuntimeError("incomplete transaction rolled back exactly; rerun check")
        inputs, preimages, outputs, token = plan(roots, at)
        report = {
            "schema": "agko-r39-ideal-terminology-reseal-report-v1",
            "mode": "check" if options.check else "execute",
            "time": at, "fresh_preimage_sha256": token,
            "preimage": dict(PRE_TARGET), "postimage": dict(POST_TARGET),
            "source_loci": EXPECTED_SOURCE_LOCUS_LINES,
            "outputs": postimages(outputs, roots),
            "writes_performed": False,
            "result": "PASS_R39_IDEAL_TERMINOLOGY_RESEAL_CHECK_READY",
        }
        if options.check:
            print(json.dumps(report, ensure_ascii=True, indent=2))
            return
        require(options.expected_fresh_preimage_sha256 is not None, "--execute requires fresh-preimage token")
        with mutex() as abandoned:
            inputs, preimages, outputs, token = plan(roots, at)
            require(options.expected_fresh_preimage_sha256 == token, "fresh-preimage token changed under mutex")
            mutation = True
            journal = execute(roots, at, inputs, preimages, outputs, token, options.expected_fresh_preimage_sha256)
            if abandoned:
                journal["abandoned_mutex_recovered"] = True
                write_journal(roots.private / JOURNAL_REL, journal)
        report.update({
            "writes_performed": True, "result": RESULT,
            "transaction_id": journal["transaction_id"],
            "outputs": journal["postimages"],
        })
        print(json.dumps(report, ensure_ascii=True, indent=2))
    except Exception as exc:
        observation = None
        if roots is not None and (roots.private / JOURNAL_REL).exists():
            try:
                observation = {"status": parse_path(roots.private / JOURNAL_REL, "journal observation").get("status"), **file_identity(roots.private / JOURNAL_REL)}
            except Exception:
                observation = {"status": "UNREADABLE"}
        print(json.dumps({
            "schema": "agko-r39-ideal-terminology-reseal-report-v1",
            "result": "FAIL_CLOSED", "error": str(exc),
            "writes_performed": mutation, "journal": observation,
        }, ensure_ascii=True, separators=(",", ":")), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
