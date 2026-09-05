"""Fail-closed exact-source R38 Korean candidate/admission validator.

The checker binds the complete canonical source, the bounded R38 source slice,
the sealed R37 Korean preimage, and the exact candidate.  Formula order may
change only inside an explicitly audited semantic clause where Korean syntax
requires it; formulas may not migrate across clauses or statements.
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


require(len(sys.argv) == 2, "usage: validate_r38_candidate.py CANONICAL_EGA2_TEX")
canonical = Path(sys.argv[1])
base = Path(__file__).parent.parent
candidate_path = Path(__file__).with_name("r38-c2s1-continuation.tex")

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

# Canonical lines 1607--1683 inclusive, with a reconstructed terminal LF.
source_text = "\n".join(canonical_lines[1606:1683]) + "\n"
source = source_text.encode("utf-8")
require(len(source) == 4191, "source slice byte count drift")
require(len(source_text) == 4096, "source slice character count drift")
require(source.count(b"\n") == 77, "source slice LF count drift")
require(
    digest(source)
    == "44583D53F17603797145FE63822F3F78DC6ECFD7ADA1B38EF01813F9E3F22BE6",
    "source slice hash drift",
)

preunit_prefix = ("\n".join(canonical_lines[:1606]) + "\n").encode("utf-8")
require(len(preunit_prefix) == 73898, "pre-unit source-prefix byte count drift")
require(preunit_prefix.count(b"\n") == 1606, "pre-unit source-prefix LF count drift")
require(
    digest(preunit_prefix)
    == "A134AA34BE77E80D873B994BB5B6EDE13A94D12F3EB56571BBD4142F0C980A51",
    "pre-unit source-prefix hash drift",
)

admitted_prefix = ("\n".join(canonical_lines[:1683]) + "\n").encode("utf-8")
require(len(admitted_prefix) == 78089, "post-unit source-prefix byte count drift")
require(admitted_prefix.count(b"\n") == 1683, "post-unit source-prefix LF count drift")
require(
    digest(admitted_prefix)
    == "6C9C0EE5DC909DFE7911564F1F982FF0539C923DE706188F7935FC0585549585",
    "post-unit source-prefix hash drift",
)

require(canonical_lines[1605] == "", "canonical line 1606 is no longer blank")
require(canonical_lines[1606] == r"\begin{env}[2.1.10]", "source start boundary drift")
require(canonical_lines[1682] == r"\end{env}", "source end boundary drift")
require(canonical_lines[1683] == "", "canonical line 1684 is no longer blank")
require(canonical_lines[1684] == r"\begin{lemma}[2.2.2]", "next source boundary drift")

candidate = candidate_path.read_bytes()
require(len(candidate) == 4599, "candidate byte count drift")
require(
    digest(candidate)
    == "8D37AF2B8B05D9C938F2D282F58902092FB7FCF55300B0A85B28C9538340CF93",
    "candidate hash drift",
)
require(not candidate.startswith(b"\xef\xbb\xbf"), "candidate has UTF-8 BOM")
require(b"\r" not in candidate and candidate.endswith(b"\n"), "candidate is not final-LF LF-only")
require(candidate.count(b"\n") == 80, "candidate LF count drift")
candidate_text = candidate.decode("utf-8")
require(len(candidate_text) == 2773, "candidate character count drift")
require("\ufffd" not in candidate_text, "candidate contains U+FFFD")
require(len(re.findall(r"[\uac00-\ud7a3]", candidate_text)) == 913, "Hangul count drift")
require(candidate_text.count("$") == 222, "candidate dollar-delimiter count drift")
require(candidate_text.count("{") == candidate_text.count("}") == 70, "candidate brace count drift")
require(candidate_text.count(r"\phantomsection") == 3, "navigation-anchor count drift")
require(
    source_text.count(r"\emph{") == candidate_text.count(r"\emph{") == 14,
    "emphasis-command count drift",
)
require("-fr" not in candidate_text, "French label/reference suffix remains in candidate")
assert_balanced_braces(candidate_text)

source_math = normalized_inline_math(source_text)
target_math = normalized_inline_math(candidate_text)
require(len(source_math) == len(target_math) == 111, "source/target inline-formula count drift")
require(
    collections.Counter(source_math) == collections.Counter(target_math),
    "global source/target inline-formula multiset drift",
)
require(
    not re.findall(r"\\\[(.*?)\\\]", source_text, re.S)
    and not re.findall(r"\\\[(.*?)\\\]", candidate_text, re.S),
    "unexpected display math",
)

# Same one-based formula ranges in the source and target identify corresponding
# semantic clauses.  Each clause must preserve its complete formula multiset;
# a permutation is permitted only within that clause.  The ranges partition all
# 111 formulas, so this also proves that no formula crossed a statement boundary.
clause_ranges = [
    ("2.1.10 ideal definition", 1, 4),
    ("2.1.10 graded-prime-ideal definition and uniqueness", 5, 11),
    ("2.1.10 radical definition", 12, 16),
    ("2.1.10 nilradical definition", 17, 21),
    ("2.1.10 graded-radical assertion", 22, 24),
    ("2.1.10 quotient and homogeneous-component proof", 25, 34),
    ("2.1.10 essentially-reduced definition", 35, 38),
    ("2.1.11 highest-component zero-divisor assertion", 39, 41),
    ("2.1.11 essentially-integral definition", 42, 45),
    ("2.1.11 universal homogeneous-element sufficiency", 46, 48),
    ("2.1.11 prime-quotient assertion", 49, 51),
    ("2.1.11 degree-zero annihilator argument", 52, 60),
    ("2.1.11 integral-domain equivalence", 61, 65),
    ("2.2.1 localization grading", 66, 75),
    ("2.2.1 degree-zero subring notation", 76, 79),
    ("2.2.1 Laurent monomial free-system assertion", 80, 84),
    ("2.2.1 Laurent polynomial isomorphism", 85, 87),
    ("2.2.1 linear-independence proof", 88, 97),
    ("2.2.1 localized graded-module assertion", 98, 101),
    ("2.2.1 localized component definition", 102, 105),
    ("2.2.1 degree-zero module notation", 106, 108),
    ("2.2.1 scalar-extension identity", 109, 111),
]
require(clause_ranges[0][1] == 1 and clause_ranges[-1][2] == 111, "clause audit endpoints drift")
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
    "II.2.1.10-fr",
    "II.2.1.11-fr",
    "subsection:II.2.2-fr",
    "II.2.2.1-fr",
]
expected_target_labels = [item.removesuffix("-fr") + "-ko" for item in expected_source_labels]
require(source_labels == expected_source_labels, "source label order drift")
require(target_labels == expected_target_labels, "target label order or -fr/-ko mapping drift")

source_refs = re.findall(r"\\hyperref\[([^]]+)\]\{([^}]+)\}", source_text)
target_refs = re.findall(r"\\hyperref\[([^]]+)\]\{([^}]+)\}", candidate_text)
require(source_refs == [("II.2.1.9-fr", "2.1.9")], "source reference drift")
require(target_refs == [("II.2.1.9-ko", "2.1.9")], "target reference drift")
require(
    [(label.removesuffix("-fr") + "-ko", visible) for label, visible in source_refs]
    == target_refs,
    "reference target/text/order drift",
)

source_events = re.findall(r"\\(begin|end)\{([^}]+)\}", source_text)
target_events = re.findall(r"\\(begin|end)\{([^}]+)\}", candidate_text)
expected_events = [
    ("begin", "env"),
    ("end", "env"),
    ("begin", "env"),
    ("end", "env"),
    ("begin", "env"),
    ("end", "env"),
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
    re.findall(r"\\begin\{env\}\[([^]]+)\]", source_text)
    == re.findall(r"\\begin\{env\}\[([^]]+)\]", candidate_text)
    == ["2.1.10", "2.1.11", "2.2.1"],
    "numbered environment order drift",
)
require(
    re.findall(r"\\oldpage\[([^]]+)\]\{([^}]+)\}", source_text)
    == re.findall(r"\\oldpage\[([^]]+)\]\{([^}]+)\}", candidate_text)
    == [("II", "24")],
    "oldpage marker drift",
)
require(
    re.findall(r"\\subsection\{([^}]+)\}", source_text)
    == ["Anneaux de fractions d'un anneau gradué."],
    "source subsection heading drift",
)
require(
    re.findall(r"\\subsection\{([^}]+)\}", candidate_text) == ["등급환의 분수환."],
    "target subsection heading drift",
)

for phrase in [
    "등급 소아이디얼",
    "근기",
    "멱영근기",
    "멱영원",
    "본질적으로 축소",
    "영인자",
    "본질적으로 정역",
    "소멸자",
    "분수환",
    "동차",
    "자유계",
]:
    require(phrase in candidate_text, f"required terminology/sense guard missing: {phrase}")
require("기저" not in candidate_text, "système libre was mistranslated as a basis")

universal_guard = re.sub(r"\s+", "", candidate_text)
require(
    "$S_+$의동차원소가운데$\\neq0$인것은모두이환에서영인자가아니어서"
    "어떤영이아닌원소와곱해도$0$이되지않으면충분하다."
    in universal_guard,
    "canonical line 1638 was not rendered with universal homogeneous-element force",
)
require(
    "$f\\inS_d$이면$S_f$의단항식$(f/1)^h$들($h$는영을포함한임의의정수)"
    "은환$S_{(f)}$위의\\emph{자유계}를이루며"
    in universal_guard,
    "Laurent exponent/free-system sentence does not bind h to every integer including zero",
)

private_path = base / "ega/II/c2s1.tex"
public_path = base / "pub/ega-ko/source/c2s1.tex"
private = private_path.read_bytes()
public = public_path.read_bytes()
require(private == public, "sealed R37 private/public preimages differ")
require(len(private) == 75622, "sealed R37 preimage byte count drift")
require(private.count(b"\n") == 1627, "sealed R37 preimage LF count drift")
require(b"\r" not in private and private.endswith(b"\n"), "sealed R37 preimage is not LF-only")
require(
    digest(private)
    == "FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383",
    "sealed R37 preimage hash drift",
)
require(private.rstrip().endswith(b"\\end{proof}"), "sealed R37 preimage end boundary drift")

separator_plus_candidate = b"\n" + candidate
prospective = private + separator_plus_candidate
require(len(separator_plus_candidate) == 4600, "separator-plus-candidate byte count drift")
require(
    digest(separator_plus_candidate)
    == "028E9D2AF3D2297C5F8D93AE07C3C2F48B499FFAA33A1FCD38BB7D9B2BC31DF4",
    "separator-plus-candidate hash drift",
)
require(len(prospective) == 80222, "prospective integrated byte count drift")
require(prospective.count(b"\n") == 1708, "prospective integrated LF count drift")
require(
    digest(prospective)
    == "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006",
    "prospective integrated hash drift",
)
prospective_lines = prospective.decode("utf-8").splitlines()
require(prospective_lines[1627] == "", "prospective separator line 1628 drift")
require(prospective_lines[1628] == r"\begin{env}[2.1.10]", "prospective target start-line drift")
require(prospective_lines[1707] == r"\end{env}", "prospective target end-line drift")

print(
    json.dumps(
        {
            "schema": "agko-r38-candidate-validation-v1",
            "result": "PASS_R38_SOURCE_CANDIDATE_AND_PROSPECTIVE_MIRRORS",
            "canonical": {"bytes": len(raw), "sha256": digest(raw)},
            "source_lines": "1607-1683",
            "source": {
                "bytes": len(source),
                "characters": len(source_text),
                "lf_lines": source.count(b"\n"),
                "sha256": digest(source),
            },
            "preunit_source_prefix": {
                "lines": "1-1606",
                "bytes": len(preunit_prefix),
                "sha256": digest(preunit_prefix),
            },
            "admitted_source_prefix": {
                "lines": "1-1683",
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
            "formula_count": len(source_math),
            "formula_multiset_exact": True,
            "formula_global_order_identical": source_math == target_math,
            "formula_order_policy": (
                "global exact 111-formula multiset; permutation allowed only inside each "
                "explicit corresponding semantic clause; no cross-clause or cross-statement migration"
            ),
            "formula_clause_local_audit": clause_audit,
            "labels": target_labels,
            "references": target_refs,
            "environments": ["2.1.10", "2.1.11", "2.2.1"],
            "subsection": "2.2",
            "oldpage": "II24",
            "terminology": {
                "essentially_reduced": "본질적으로 축소",
                "zero_divisor": "영인자",
                "free_system": "자유계",
                "basis_not_used": True,
                "line_1638_universal_force": True,
                "line_1664_h_all_integers_including_zero": True,
            },
            "preimage": {
                "private_public_exact": True,
                "bytes": len(private),
                "lf_lines": private.count(b"\n"),
                "sha256": digest(private),
            },
            "separator_plus_candidate": {
                "bytes": len(separator_plus_candidate),
                "sha256": digest(separator_plus_candidate),
            },
            "prospective_integration": {
                "target_range": "lines1629-1708; line1628 separator",
                "bytes": len(prospective),
                "characters": len(prospective.decode("utf-8")),
                "lf_lines": prospective.count(b"\n"),
                "sha256": digest(prospective),
                "private_public_if_identically_written": True,
            },
            "next_source_line": 1685,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
)
