"""Fail-closed exact-source R39 Korean candidate/admission validator.

This checker binds the complete canonical source, canonical lines 1685--1780,
the exact integrated R38 Korean mirrors, and the exact R39 candidate.  Formula
reordering is permitted only inside an explicitly corresponding semantic
clause; formulas may not migrate across clauses or numbered statements.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
import sys
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def normalized_inline_math(text: str) -> list[str]:
    return [
        re.sub(r"\s+", "", item)
        for item in re.findall(r"(?<!\\)\$(.*?)(?<!\\)\$", text, re.S)
    ]


def normalized_display_math(text: str) -> list[str]:
    return [
        re.sub(r"\s+", "", item)
        for item in re.findall(r"\\\[(.*?)\\\]", text, re.S)
    ]


def assert_balanced_braces(text: str) -> None:
    depth = 0
    for position, character in enumerate(text):
        if character not in "{}":
            continue
        preceding_backslashes = 0
        cursor = position - 1
        while cursor >= 0 and text[cursor] == "\\":
            preceding_backslashes += 1
            cursor -= 1
        if preceding_backslashes % 2:
            continue
        if character == "{":
            depth += 1
        else:
            require(depth > 0, f"unmatched closing brace at character {position}")
            depth -= 1
    require(depth == 0, "unclosed target brace")


require(len(sys.argv) == 2, "usage: validate_r39_candidate.py CANONICAL_EGA2_TEX")
canonical = Path(sys.argv[1])
base = Path(__file__).parent.parent
candidate_path = Path(__file__).with_name("r39-c2s1-continuation.tex")

raw = canonical.read_bytes()
require(len(raw) == 820505, "canonical byte count drift")
require(
    digest(raw)
    == "84EDBE3E83530AF2959B441796337C9DC21EAFCA6A13114A26778760FBF437AC",
    "canonical hash drift",
)
require(not raw.startswith(b"\xef\xbb\xbf"), "canonical source unexpectedly has a BOM")
require(b"\r" not in raw, "canonical source is not LF-only")
canonical_text = raw.decode("utf-8")
canonical_lines = canonical_text.splitlines()
require(len(canonical_lines) == 18087, "canonical LF-line count drift")

# Canonical lines 1685--1780 inclusive, with a reconstructed terminal LF.
source_text = "\n".join(canonical_lines[1684:1780]) + "\n"
source = source_text.encode("utf-8")
require(len(source) == 3796, "source slice byte count drift")
require(len(source_text) == 3740, "source slice character count drift")
require(source.count(b"\n") == 96, "source slice LF count drift")
require(
    digest(source)
    == "BE7EC704F82B9283A48AFF1A01D7CF34F14A2C29F1B50269511DD699514BBC21",
    "source slice hash drift",
)

preunit_prefix = ("\n".join(canonical_lines[:1684]) + "\n").encode("utf-8")
require(len(preunit_prefix) == 78090, "pre-unit source-prefix byte count drift")
require(preunit_prefix.count(b"\n") == 1684, "pre-unit source-prefix LF count drift")
require(
    digest(preunit_prefix)
    == "245FBEC6615FCB67B21CDD796D30DD2FC350BF4FB22B46F7D9F45B3DAEA5BEC6",
    "pre-unit source-prefix hash drift",
)

admitted_prefix = ("\n".join(canonical_lines[:1780]) + "\n").encode("utf-8")
require(len(admitted_prefix) == 81886, "post-unit source-prefix byte count drift")
require(admitted_prefix.count(b"\n") == 1780, "post-unit source-prefix LF count drift")
require(
    digest(admitted_prefix)
    == "1F95FEC43B19B90C975F97EFAD3ECEA255FF92BBDBA97E605A0F25CD18572A43",
    "post-unit source-prefix hash drift",
)

require(canonical_lines[1683] == "", "canonical line 1684 is no longer blank")
require(canonical_lines[1684] == r"\begin{lemma}[2.2.2]", "source start boundary drift")
require(canonical_lines[1779] == r"\end{proof}", "source end boundary drift")
require(canonical_lines[1780] == "", "canonical line 1781 is no longer blank")
require(canonical_lines[1781] == r"\begin{env}[2.2.7]", "next source boundary drift")

candidate = candidate_path.read_bytes()
require(len(candidate) == 4094, "candidate byte count drift")
require(
    digest(candidate)
    == "811AD490FC21AE287D0AD67FA897E8F47D5592B98234291B640A0AFCCAED0F26",
    "candidate hash drift",
)
require(not candidate.startswith(b"\xef\xbb\xbf"), "candidate has UTF-8 BOM")
require(b"\r" not in candidate and candidate.endswith(b"\n"), "candidate is not final-LF LF-only")
require(candidate.count(b"\n") == 100, "candidate LF count drift")
candidate_text = candidate.decode("utf-8")
require(len(candidate_text) == 2788, "candidate character count drift")
require("\ufffd" not in candidate_text, "candidate contains U+FFFD")
require(len(re.findall(r"[\uac00-\ud7a3]", candidate_text)) == 653, "Hangul count drift")
require(candidate_text.count("$") == 148, "candidate dollar-delimiter count drift")
require(candidate_text.count("{") == candidate_text.count("}") == 105, "candidate brace count drift")
require(candidate_text.count(r"\phantomsection") == 5, "navigation-anchor count drift")
require(
    source_text.count(r"\emph{") == candidate_text.count(r"\emph{") == 1,
    "emphasis-command count drift",
)
require("-fr" not in candidate_text, "French label/reference suffix remains in candidate")
assert_balanced_braces(candidate_text)

source_math = normalized_inline_math(source_text)
target_math = normalized_inline_math(candidate_text)
require(len(source_math) == len(target_math) == 74, "source/target inline-formula count drift")
require(
    collections.Counter(source_math) == collections.Counter(target_math),
    "global source/target inline-formula multiset drift",
)

source_displays = normalized_display_math(source_text)
target_displays = normalized_display_math(candidate_text)
require(len(source_displays) == len(target_displays) == 3, "display count drift")
require(source_displays == target_displays, "display formula/xymatrix content or order drift")
require(source_text.count(r"\xymatrix{") == candidate_text.count(r"\xymatrix{") == 1, "xymatrix count drift")

# These one-based ranges are an exhaustive partition of the 74 inline formulas.
# A clause-local permutation is allowed for Korean syntax, but each range must
# preserve its exact multiset.  This proves that no formula migrated across a
# numbered statement, proof step, implication, condition, or conclusion.
clause_ranges = [
    ("2.2.2 hypotheses", 1, 5),
    ("2.2.2 divisibility and first graded-ring identification", 6, 10),
    ("2.2.2 iterated-localization identifications", 11, 16),
    ("2.2.2 degree-zero subring conclusion", 17, 23),
    ("2.2.3 canonical ring homomorphism", 24, 28),
    ("2.2.3 canonical module homomorphism", 29, 29),
    ("2.2.4 generation statement", 30, 35),
    ("2.2.4 proof membership assertion", 36, 38),
    ("2.2.5 ring and module isomorphisms", 39, 43),
    ("2.2.5 forward-map definition", 44, 48),
    ("2.2.5 forward-map well-definedness", 49, 53),
    ("2.2.5 kernel-element decomposition", 54, 58),
    ("2.2.5 homogeneous coefficient relations", 59, 63),
    ("2.2.5 annihilation conclusion", 64, 64),
    ("2.2.5 inverse-map definition and well-definedness", 65, 69),
    ("2.2.5 module case", 70, 70),
    ("2.2.6 Noetherian corollary", 71, 74),
]
require(clause_ranges[0][1] == 1 and clause_ranges[-1][2] == 74, "clause audit endpoints drift")
require(
    all(left[2] + 1 == right[1] for left, right in zip(clause_ranges, clause_ranges[1:])),
    "clause audit is not a contiguous partition",
)
clause_audit: list[dict[str, object]] = []
for name, first, last in clause_ranges:
    source_clause = source_math[first - 1 : last]
    target_clause = target_math[first - 1 : last]
    require(
        collections.Counter(source_clause) == collections.Counter(target_clause),
        f"formula crossed or changed semantic clause: {name}",
    )
    clause_audit.append(
        {
            "clause": name,
            "formula_index_range": f"{first}-{last}",
            "count": len(source_clause),
            "order_identical": source_clause == target_clause,
            "multiset_exact": True,
        }
    )

source_labels = re.findall(r"\\label\{([^}]+)\}", source_text)
target_labels = re.findall(r"\\label\{([^}]+)\}", candidate_text)
expected_source_labels = [
    "II.2.2.2-fr",
    "II.2.2.3-fr",
    "II.2.2.4-fr",
    "II.2.2.5-fr",
    "II.2.2.6-fr",
]
expected_target_labels = [item.removesuffix("-fr") + "-ko" for item in expected_source_labels]
require(source_labels == expected_source_labels, "source label order drift")
require(target_labels == expected_target_labels, "target label order or -fr/-ko mapping drift")

source_refs = re.findall(r"\\hyperref\[([^]]+)\]\{([^}]+)\}", source_text)
target_refs = re.findall(r"\\hyperref\[([^]]+)\]\{([^}]+)\}", candidate_text)
expected_source_refs = [
    ("0.1.4.6-fr", "0, I.4.6"),
    ("II.2.2.2-fr", "2.2.2"),
    ("0.1.4.1-fr", "0, I.4.1"),
    ("II.2.2.2-fr", "2.2.2"),
    ("II.2.1.7-fr", "2.1.7"),
    ("II.2.2.5-fr", "2.2.5"),
]
require(source_refs == expected_source_refs, "source reference drift")
require(
    [(label.removesuffix("-fr") + "-ko", visible) for label, visible in source_refs]
    == target_refs,
    "reference target/text/order drift",
)

source_events = re.findall(r"\\(begin|end)\{([^}]+)\}", source_text)
target_events = re.findall(r"\\(begin|end)\{([^}]+)\}", candidate_text)
expected_events = [
    ("begin", "lemma"),
    ("end", "lemma"),
    ("begin", "proof"),
    ("end", "proof"),
    ("begin", "env"),
    ("end", "env"),
    ("begin", "lemma"),
    ("end", "lemma"),
    ("begin", "proof"),
    ("end", "proof"),
    ("begin", "proposition"),
    ("end", "proposition"),
    ("begin", "proof"),
    ("end", "proof"),
    ("begin", "corollary"),
    ("end", "corollary"),
    ("begin", "proof"),
    ("end", "proof"),
]
require(source_events == target_events == expected_events, "ordered environment-event drift")
environment_stack: list[str] = []
for action, environment in target_events:
    if action == "begin":
        environment_stack.append(environment)
    else:
        require(
            bool(environment_stack) and environment_stack.pop() == environment,
            "target environment nesting drift",
        )
require(not environment_stack, "unclosed target environment")
require(
    re.findall(r"\\begin\{(?:lemma|env|proposition|corollary)\}\[([^]]+)\]", source_text)
    == re.findall(r"\\begin\{(?:lemma|env|proposition|corollary)\}\[([^]]+)\]", candidate_text)
    == ["2.2.2", "2.2.3", "2.2.4", "2.2.5", "2.2.6"],
    "numbered environment order drift",
)
require(
    re.findall(r"\\oldpage\[([^]]+)\]\{([^}]+)\}", source_text)
    == re.findall(r"\\oldpage\[([^]]+)\]\{([^}]+)\}", candidate_text)
    == [("II", "25")],
    "oldpage marker drift",
)

compact = re.sub(r"\s+", "", candidate_text)
for phrase in [
    "환의표준적동형",
    "가군의표준적동형",
    "등급환",
    "부분환",
    "표준준동형",
    "동차원소",
    "표준적상들의합집합에의해생성",
    "합동식",
    "동치류",
    "환준동형",
    "서로역",
    "뇌터",
]:
    require(phrase in compact, f"required terminology/sense guard missing: {phrase}")

# Preserve the two known historical-source oddities diplomatically.
require(
    "이는명제의첫번째부분을증명한다." in compact,
    "line 1709 proposition wording was silently normalized",
)
require(
    "$1/(g^d/f^e)=f^{d+e}/(fg)^d$" in candidate_text,
    "line 1738 printed formula was silently normalized",
)
require("역주" not in candidate_text, "candidate inserts an unbound translator note")

# Guard core logical relations and quantifier scopes in prose as well as math.
for phrase in [
    "$fg$는$f^eg^d$의약수이고,후자는$(fg)^{de}$의약수이므로",
    "$g^d/f^e$는차수가$0$인$S_{f^e}$의원소이다.",
    "두번째부분도같은방식으로확립된다.",
    "다음도표는가환이다.",
    "상에속함을보이면충분하며",
    "모든양의정수지수에대하여합동식",
    "따라서$f^hx=0$인$h>0$가있으면",
    "반드시$h=n$이고$x=-y_{hd}$이며",
    r"각동치류$\overline{x}$가$(f-1)S^{(d)}$법동치류이고$x\inS_{nd}$인원소로대표되면",
    "$S$가뇌터이면,차수가$>0$인임의의동차원소$f$에대하여$S_{(f)}$도뇌터이다.",
]:
    require(phrase in compact, f"logical/quantifier guard missing: {phrase}")

private_path = base / "ega/II/c2s1.tex"
public_path = base / "pub/ega-ko/source/c2s1.tex"
private = private_path.read_bytes()
public = public_path.read_bytes()
require(private == public, "integrated R38 private/public preimages differ")
require(len(private) == 80222, "integrated R38 preimage byte count drift")
require(private.count(b"\n") == 1708, "integrated R38 preimage LF count drift")
require(b"\r" not in private and private.endswith(b"\n"), "integrated R38 preimage is not LF-only")
require(
    digest(private)
    == "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006",
    "integrated R38 preimage hash drift",
)
require(private.rstrip().endswith(b"\\end{env}"), "integrated R38 preimage end boundary drift")
require(not private.endswith(candidate), "R39 candidate is already integrated")

separator_plus_candidate = b"\n" + candidate
prospective = private + separator_plus_candidate
require(len(separator_plus_candidate) == 4095, "separator-plus-candidate byte count drift")
require(
    digest(separator_plus_candidate)
    == "E08631C2FC3D7C51A0CE1553547A688D35B8B1D349A2B26C14BDF5B302AD5021",
    "separator-plus-candidate hash drift",
)
require(len(prospective) == 84317, "prospective integrated byte count drift")
require(len(prospective.decode("utf-8")) == 58695, "prospective integrated character count drift")
require(prospective.count(b"\n") == 1809, "prospective integrated LF count drift")
require(
    digest(prospective)
    == "D08D6AD60E00CE72AC6D64BB1D95F0AB63836F8B50D065631DC4FCD044D4F67C",
    "prospective integrated hash drift",
)
prospective_lines = prospective.decode("utf-8").splitlines()
require(prospective_lines[1708] == "", "prospective separator line 1709 drift")
require(prospective_lines[1709] == r"\begin{lemma}[2.2.2]", "prospective target start-line drift")
require(prospective_lines[1808] == r"\end{proof}", "prospective target end-line drift")

print(
    json.dumps(
        {
            "schema": "agko-r39-candidate-validation-v1",
            "result": "PASS_R39_SOURCE_CANDIDATE_AND_PROSPECTIVE_MIRRORS",
            "canonical": {"bytes": len(raw), "lf_lines": len(canonical_lines), "sha256": digest(raw)},
            "source_lines": "1685-1780",
            "source": {
                "bytes": len(source),
                "characters": len(source_text),
                "lf_lines": source.count(b"\n"),
                "sha256": digest(source),
            },
            "preunit_source_prefix": {
                "lines": "1-1684",
                "bytes": len(preunit_prefix),
                "sha256": digest(preunit_prefix),
            },
            "admitted_source_prefix": {
                "lines": "1-1780",
                "bytes": len(admitted_prefix),
                "sha256": digest(admitted_prefix),
            },
            "candidate": {
                "bytes": len(candidate),
                "characters": len(candidate_text),
                "lf_lines": candidate.count(b"\n"),
                "sha256": digest(candidate),
                "hangul_syllables": len(re.findall(r"[\uac00-\ud7a3]", candidate_text)),
            },
            "math": {
                "inline_formula_count": len(source_math),
                "display_count": len(source_displays),
                "total_spans": len(source_math) + len(source_displays),
                "inline_formula_multiset_exact": True,
                "inline_formula_global_order_identical": source_math == target_math,
                "display_content_and_order_exact": True,
                "xymatrix_exact": True,
                "formula_order_policy": (
                    "global exact 74-inline-formula multiset; permutation allowed only inside each "
                    "explicit corresponding semantic clause; no cross-clause or cross-statement migration"
                ),
                "clause_local_audit": clause_audit,
            },
            "labels": target_labels,
            "references": target_refs,
            "environments": ["2.2.2", "2.2.3", "2.2.4", "2.2.5", "2.2.6"],
            "oldpage": "II25",
            "diplomatic_source_oddities": {
                "line_1709_proposition_wording_preserved": True,
                "line_1738_printed_formula_preserved": True,
            },
            "preimage": {
                "private_public_exact": True,
                "bytes": len(private),
                "lf_lines": private.count(b"\n"),
                "sha256": digest(private),
                "r39_not_integrated": True,
            },
            "separator_plus_candidate": {
                "bytes": len(separator_plus_candidate),
                "sha256": digest(separator_plus_candidate),
            },
            "prospective_integration": {
                "target_range": "lines1710-1809; line1709 separator",
                "bytes": len(prospective),
                "characters": len(prospective.decode("utf-8")),
                "lf_lines": prospective.count(b"\n"),
                "sha256": digest(prospective),
                "private_public_if_identically_written": True,
                "integrated_now": False,
            },
            "next_source_line": 1782,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
)
