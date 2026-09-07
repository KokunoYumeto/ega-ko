"""Fail-closed current-authority validator for the R39 Korean candidate.

This additive checker preserves the historical pre-D54 validator and admission
while binding the current EGA II authority and the additive Korean-wording
reseal.  It proves that D54 is exactly the deletion of one scan-absent comma at
canonical line 1542, that the R39 source unit is unchanged, that the candidate
diff is exactly the authorized register repair, and that the R38 target preimage
plus the resealed candidate has the predetermined R39 postimage.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


CURRENT_BYTES = 820_504
CURRENT_SHA256 = "91685C9C53FD77171677CA3E490F84DE3B84EE983C84B334440B64679BC2E26E"
PRE_D54_BYTES = 820_505
PRE_D54_SHA256 = "84EDBE3E83530AF2959B441796337C9DC21EAFCA6A13114A26778760FBF437AC"
UNIT_SHA256 = "BE7EC704F82B9283A48AFF1A01D7CF34F14A2C29F1B50269511DD699514BBC21"
HISTORICAL_CANDIDATE_SHA256 = "811AD490FC21AE287D0AD67FA897E8F47D5592B98234291B640A0AFCCAED0F26"
CANDIDATE_SHA256 = "E8F52EDEC11B90D3CCC4E2398279DA4DEA7A6064AABFBE87D1765D55FEDE1940"
TARGET_PREIMAGE_SHA256 = "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006"
HISTORICAL_TARGET_POSTIMAGE_SHA256 = "D08D6AD60E00CE72AC6D64BB1D95F0AB63836F8B50D065631DC4FCD044D4F67C"
TARGET_POSTIMAGE_SHA256 = "F3DD70691223B0D35052B4D6F4CF5E77B72AA2C5F352EDE5D9C83E98704C8257"
REBASE_CONTROL_SHA256 = "CD9E1E2CF87D2E35C49AE7AF16E797AF146B72C6060869B631019DB8F6782349"
RESEAL_CONTROL_BYTES = 10_118
RESEAL_CONTROL_SHA256 = "9A30C30953B7C118434541FBE8F9A362BB374BB68835E479536073B8DE730451"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def exact_prefix(lines: list[str], last_line: int) -> bytes:
    return ("\n".join(lines[:last_line]) + "\n").encode("utf-8")


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


def parse_args() -> argparse.Namespace:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("canonical", type=Path)
    parser.add_argument(
        "--candidate",
        type=Path,
        default=project / "candidates" / "r39-c2s1-continuation.tex",
    )
    parser.add_argument(
        "--private-target", type=Path, default=project / "ega" / "II" / "c2s1.tex"
    )
    parser.add_argument(
        "--public-target",
        type=Path,
        default=project / "pub" / "ega-ko" / "source" / "c2s1.tex",
    )
    parser.add_argument(
        "--rebase-control",
        type=Path,
        default=project / "controls" / "R39_CANONICAL_PREFIX_REBASE.json",
    )
    parser.add_argument(
        "--reseal-control",
        type=Path,
        default=project / "controls" / "R39_KOREAN_WORDING_RESEAL.json",
    )
    parser.add_argument(
        "--self-test-negatives",
        action="store_true",
        help="prove fail-closed behavior with six bounded temporary witnesses",
    )
    return parser.parse_args()


def run_negative_tests(args: argparse.Namespace) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    def mutated_copy(source: Path, destination: Path, offset: int) -> None:
        payload = bytearray(source.read_bytes())
        require(payload, f"cannot mutate empty negative witness: {source.name}")
        payload[offset] ^= 1
        destination.write_bytes(payload)

    def expect_failure(name: str, invocation: list[str], expected: str) -> None:
        completed = subprocess.run(
            invocation,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        combined = completed.stdout + completed.stderr
        require(completed.returncode != 0, f"negative witness unexpectedly passed: {name}")
        require(expected in combined, f"negative witness failed for wrong reason: {name}")
        results.append(
            {
                "witness": name,
                "exit_code_nonzero": True,
                "expected_failure": expected,
            }
        )

    with tempfile.TemporaryDirectory(prefix="agko-r39-current-negative-") as temporary:
        root = Path(temporary)
        wrong_source = root / "wrong-source.tex"
        wrong_candidate = root / "wrong-candidate.tex"
        wrong_private = root / "wrong-private-target.tex"
        wrong_public = root / "wrong-public-target.tex"
        wrong_rebase = root / "wrong-rebase-control.json"
        wrong_reseal = root / "wrong-reseal-control.json"
        mutated_copy(args.canonical, wrong_source, -2)
        mutated_copy(args.candidate, wrong_candidate, -2)
        mutated_copy(args.private_target, wrong_private, -2)
        mutated_copy(args.public_target, wrong_public, -2)
        mutated_copy(args.rebase_control, wrong_rebase, -2)
        mutated_copy(args.reseal_control, wrong_reseal, -2)

        common = [
            "--candidate",
            str(args.candidate),
            "--private-target",
            str(args.private_target),
            "--public-target",
            str(args.public_target),
            "--rebase-control",
            str(args.rebase_control),
            "--reseal-control",
            str(args.reseal_control),
        ]
        executable = [sys.executable, str(Path(__file__).resolve())]
        expect_failure(
            "wrong-current-source",
            executable + [str(wrong_source)] + common,
            "canonical hash drift",
        )
        expect_failure(
            "wrong-candidate",
            executable
            + [str(args.canonical), "--candidate", str(wrong_candidate)]
            + common[2:],
            "candidate hash drift",
        )
        expect_failure(
            "wrong-private-target",
            executable
            + [str(args.canonical)]
            + common[:2]
            + ["--private-target", str(wrong_private)]
            + common[4:],
            "integrated R38 private/public preimages differ",
        )
        expect_failure(
            "wrong-public-target",
            executable
            + [str(args.canonical)]
            + common[:4]
            + ["--public-target", str(wrong_public)]
            + common[6:],
            "integrated R38 private/public preimages differ",
        )
        expect_failure(
            "wrong-rebase-control",
            executable
            + [str(args.canonical)]
            + common[:6]
            + ["--rebase-control", str(wrong_rebase)]
            + common[8:],
            "R39 rebase-control hash drift",
        )
        expect_failure(
            "wrong-reseal-control",
            executable
            + [str(args.canonical)]
            + common[:8]
            + ["--reseal-control", str(wrong_reseal)],
            "R39 wording-reseal hash drift",
        )
    return results


def main() -> None:
    args = parse_args()

    rebase_raw = args.rebase_control.read_bytes()
    require(len(rebase_raw) == 6370, "R39 rebase-control byte count drift")
    require(digest(rebase_raw) == REBASE_CONTROL_SHA256, "R39 rebase-control hash drift")
    rebase = json.loads(rebase_raw.decode("utf-8"))
    require(rebase["schema"] == "agko-r39-canonical-prefix-rebase-v1", "rebase schema drift")
    require(
        rebase["result"]
        == "PASS_R39_CANONICAL_PREFIX_REBASE_CANDIDATE_AND_PROSPECTIVE_TARGET_UNAFFECTED",
        "rebase result drift",
    )
    require(
        rebase["canonical_source"]["whole"]["postimage_sha256"] == CURRENT_SHA256,
        "rebase current-source binding drift",
    )
    require(
        rebase["canonical_source"]["whole"]["preimage_sha256"] == PRE_D54_SHA256,
        "rebase pre-D54 binding drift",
    )
    require(
        rebase["canonical_source"]["r39_unit_lines_1685_1780"]["sha256"] == UNIT_SHA256,
        "rebase R39-unit binding drift",
    )
    require(
        rebase["candidate"]["sha256"] == HISTORICAL_CANDIDATE_SHA256,
        "historical rebase candidate binding drift",
    )
    require(
        rebase["prospective_integration"]["sha256"]
        == HISTORICAL_TARGET_POSTIMAGE_SHA256,
        "historical rebase prospective-target binding drift",
    )

    reseal_raw = args.reseal_control.read_bytes()
    require(len(reseal_raw) == RESEAL_CONTROL_BYTES, "R39 wording-reseal byte count drift")
    require(digest(reseal_raw) == RESEAL_CONTROL_SHA256, "R39 wording-reseal hash drift")
    reseal = json.loads(reseal_raw.decode("utf-8"))
    require(
        reseal["schema"] == "agko-r39-korean-wording-reseal-v1",
        "wording-reseal schema drift",
    )
    require(
        reseal["result"]
        == "PASS_R39_KOREAN_WORDING_RESEALED_CURRENT_CANDIDATE_AND_PROSPECTIVE_TARGET",
        "wording-reseal result drift",
    )
    require(
        reseal["authority"]["sha256"] == CURRENT_SHA256
        and reseal["authority"]["unit_sha256"] == UNIT_SHA256,
        "wording-reseal source binding drift",
    )
    require(
        reseal["preserved_historical_evidence"]["canonical_prefix_rebase"]["sha256"]
        == REBASE_CONTROL_SHA256,
        "wording-reseal historical rebase binding drift",
    )
    require(
        reseal["candidate_transition"]["preimage"]["sha256"]
        == HISTORICAL_CANDIDATE_SHA256,
        "wording-reseal candidate preimage binding drift",
    )
    require(
        reseal["candidate_transition"]["postimage"]["sha256"] == CANDIDATE_SHA256,
        "wording-reseal candidate postimage binding drift",
    )
    require(
        reseal["prospective_integration"]["sha256"] == TARGET_POSTIMAGE_SHA256,
        "wording-reseal prospective-target binding drift",
    )

    raw = args.canonical.read_bytes()
    require(len(raw) == CURRENT_BYTES, "canonical byte count drift")
    require(digest(raw) == CURRENT_SHA256, "canonical hash drift")
    require(not raw.startswith(b"\xef\xbb\xbf"), "canonical source unexpectedly has a BOM")
    require(b"\r" not in raw, "canonical source is not LF-only")
    require(raw.endswith(b"\n"), "canonical source lacks final LF")
    canonical_text = raw.decode("utf-8")
    canonical_lines = canonical_text.splitlines()
    require(len(canonical_text) == 809277, "canonical character count drift")
    require(len(canonical_lines) == 18087, "canonical LF-line count drift")

    # D54 proof: insert exactly the scan-absent comma at its sole postimage
    # locus and recover every bound byte of the historical authority.
    post_marker = b"Alors, si $f\\in S_+$ n'appartient"
    require(raw.count(post_marker) == 1, "D54 postimage locus is not unique")
    comma_offset = raw.index(post_marker) + len(b"Alors, si $f\\in S_+$")
    pre_d54 = raw[:comma_offset] + b"," + raw[comma_offset:]
    require(len(pre_d54) == PRE_D54_BYTES, "reconstructed pre-D54 byte count drift")
    require(digest(pre_d54) == PRE_D54_SHA256, "reconstructed pre-D54 hash drift")
    require(pre_d54[comma_offset] == ord(","), "reconstructed D54 byte is not ASCII comma")
    require(
        pre_d54[:comma_offset] + pre_d54[comma_offset + 1 :] == raw,
        "D54 is not an exact single-byte deletion",
    )
    require(
        canonical_lines[1541]
        == "contienne pas $S_+$. Alors, si $f\\in S_+$ n'appartient pas à",
        "current line 1542 literal drift",
    )
    pre_d54_lines = pre_d54.decode("utf-8").splitlines()
    require(
        pre_d54_lines[1541]
        == "contienne pas $S_+$. Alors, si $f\\in S_+$, n'appartient pas à",
        "reconstructed pre-D54 line 1542 literal drift",
    )

    source_text = "\n".join(canonical_lines[1684:1780]) + "\n"
    source = source_text.encode("utf-8")
    require(len(source) == 3796, "source slice byte count drift")
    require(len(source_text) == 3740, "source slice character count drift")
    require(source.count(b"\n") == 96, "source slice LF count drift")
    require(digest(source) == UNIT_SHA256, "source slice hash drift")
    require(
        source == ("\n".join(pre_d54_lines[1684:1780]) + "\n").encode("utf-8"),
        "R39 unit changed across D54",
    )

    current_preunit = exact_prefix(canonical_lines, 1684)
    pre_d54_preunit = exact_prefix(pre_d54_lines, 1684)
    require(len(current_preunit) == 78089, "current pre-unit prefix byte count drift")
    require(current_preunit.count(b"\n") == 1684, "current pre-unit prefix LF drift")
    require(
        digest(current_preunit) == "3A2B507F3CEBB0B6201A30A36D595FFC4CF726DEF231F4228B06F6A5F6DE28FE",
        "current pre-unit prefix hash drift",
    )
    require(len(pre_d54_preunit) == 78090, "pre-D54 pre-unit prefix byte count drift")
    require(
        digest(pre_d54_preunit)
        == "245FBEC6615FCB67B21CDD796D30DD2FC350BF4FB22B46F7D9F45B3DAEA5BEC6",
        "pre-D54 pre-unit prefix hash drift",
    )

    current_admitted = exact_prefix(canonical_lines, 1780)
    pre_d54_admitted = exact_prefix(pre_d54_lines, 1780)
    require(len(current_admitted) == 81885, "current admitted prefix byte count drift")
    require(current_admitted.count(b"\n") == 1780, "current admitted prefix LF drift")
    require(
        digest(current_admitted)
        == "033E312D8BD9E22AEC1D5B8AC5705ED71C64C4E4DCFBB7ED84B9A434313ACE33",
        "current admitted prefix hash drift",
    )
    require(len(pre_d54_admitted) == 81886, "pre-D54 admitted prefix byte count drift")
    require(
        digest(pre_d54_admitted)
        == "1F95FEC43B19B90C975F97EFAD3ECEA255FF92BBDBA97E605A0F25CD18572A43",
        "pre-D54 admitted prefix hash drift",
    )

    require(canonical_lines[1683] == "", "canonical line 1684 is no longer blank")
    require(canonical_lines[1684] == r"\begin{lemma}[2.2.2]", "source start boundary drift")
    require(canonical_lines[1779] == r"\end{proof}", "source end boundary drift")
    require(canonical_lines[1780] == "", "canonical line 1781 is no longer blank")
    require(canonical_lines[1781] == r"\begin{env}[2.2.7]", "next source boundary drift")

    candidate = args.candidate.read_bytes()
    require(len(candidate) == 4051, "candidate byte count drift")
    require(digest(candidate) == CANDIDATE_SHA256, "candidate hash drift")
    require(not candidate.startswith(b"\xef\xbb\xbf"), "candidate has UTF-8 BOM")
    require(b"\r" not in candidate and candidate.endswith(b"\n"), "candidate is not final-LF LF-only")
    require(candidate.count(b"\n") == 100, "candidate LF count drift")
    candidate_text = candidate.decode("utf-8")
    require(len(candidate_text) == 2771, "candidate character count drift")
    require("\ufffd" not in candidate_text, "candidate contains U+FFFD")
    require(len(re.findall(r"[\uac00-\ud7a3]", candidate_text)) == 640, "Hangul count drift")
    require(candidate_text.count("$") == 148, "candidate dollar-delimiter count drift")
    require(candidate_text.count("{") == candidate_text.count("}") == 105, "candidate brace count drift")
    require(candidate_text.count(r"\phantomsection") == 5, "navigation-anchor count drift")
    require(source_text.count(r"\emph{") == candidate_text.count(r"\emph{") == 1, "emphasis count drift")
    require("-fr" not in candidate_text, "French label/reference suffix remains in candidate")
    assert_balanced_braces(candidate_text)

    # Reverse only the authorized wording changes and recover the exact
    # historical admitted candidate.  This proves that no formula, structure,
    # navigation marker, or unrelated Korean prose changed in the reseal.
    reverse_edits = [
        ("환의 표준 동형", "환의 표준적 동형", 1),
        ("환의\n표준 동형", "환의\n표준적 동형", 1),
        ("가군의 표준 동형", "가군의 표준적 동형", 2),
        ("표준 상들의", "표준적 상들의", 1),
        ("안에서의 표준\n상에", "안에서의 표준적\n상에", 1),
        ("다음 도식은\n가환한다.", "다음 도표는\n가환이다.", 1),
        (
            r"$\overline{x}$, 곧 $x$의 $(f-1)S^{(d)}$에 대한 잉여류를 대응시켜 정의한다.",
            r"$\overline{x}$, 곧 $x$의 $(f-1)S^{(d)}$ 법 동치류를 대응시켜 정의한다.",
            1,
        ),
        (
            "따라서 $x\\in S_{nd}$인 원소가\n"
            "나타내는 $(f-1)S^{(d)}$에 대한 각 잉여류 $\\overline{x}$에 $S_{(f)}$의 원소\n"
            "$x/f^n$을 대응시킬 수 있다.",
            "따라서 각 동치류\n"
            "$\\overline{x}$가 $(f-1)S^{(d)}$ 법 동치류이고 $x\\in S_{nd}$인 원소로\n"
            "대표되면, 그 동치류에 $x/f^n$을 $S_{(f)}$의 원소로 대응시킬 수 있다.",
            1,
        ),
    ]
    historical_candidate_text = candidate_text
    for postimage, preimage, expected_count in reverse_edits:
        require(
            historical_candidate_text.count(postimage) == expected_count,
            f"authorized wording postimage count drift: {postimage}",
        )
        historical_candidate_text = historical_candidate_text.replace(postimage, preimage)
    historical_candidate = historical_candidate_text.encode("utf-8")
    require(len(historical_candidate) == 4094, "reconstructed historical candidate byte drift")
    require(len(historical_candidate_text) == 2788, "reconstructed historical candidate character drift")
    require(
        len(re.findall(r"[\uac00-\ud7a3]", historical_candidate_text)) == 653,
        "reconstructed historical candidate Hangul drift",
    )
    require(
        digest(historical_candidate) == HISTORICAL_CANDIDATE_SHA256,
        "reconstructed historical candidate hash drift",
    )

    source_math = normalized_inline_math(source_text)
    target_math = normalized_inline_math(candidate_text)
    require(len(source_math) == len(target_math) == 74, "source/target inline-formula count drift")
    require(collections.Counter(source_math) == collections.Counter(target_math), "global formula multiset drift")
    source_displays = normalized_display_math(source_text)
    target_displays = normalized_display_math(candidate_text)
    require(len(source_displays) == len(target_displays) == 3, "display count drift")
    require(source_displays == target_displays, "display formula/xymatrix content or order drift")
    require(source_text.count(r"\xymatrix{") == candidate_text.count(r"\xymatrix{") == 1, "xymatrix count drift")

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
    require(clause_ranges[0][1] == 1 and clause_ranges[-1][2] == 74, "clause endpoints drift")
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
        "II.2.2.2-fr", "II.2.2.3-fr", "II.2.2.4-fr", "II.2.2.5-fr", "II.2.2.6-fr"
    ]
    expected_target_labels = [item.removesuffix("-fr") + "-ko" for item in expected_source_labels]
    require(source_labels == expected_source_labels, "source label order drift")
    require(target_labels == expected_target_labels, "target label mapping drift")

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
        ("begin", "lemma"), ("end", "lemma"), ("begin", "proof"), ("end", "proof"),
        ("begin", "env"), ("end", "env"), ("begin", "lemma"), ("end", "lemma"),
        ("begin", "proof"), ("end", "proof"), ("begin", "proposition"),
        ("end", "proposition"), ("begin", "proof"), ("end", "proof"),
        ("begin", "corollary"), ("end", "corollary"), ("begin", "proof"), ("end", "proof"),
    ]
    require(source_events == target_events == expected_events, "ordered environment-event drift")
    stack: list[str] = []
    for action, environment in target_events:
        if action == "begin":
            stack.append(environment)
        else:
            require(bool(stack) and stack.pop() == environment, "target environment nesting drift")
    require(not stack, "unclosed target environment")
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
        "환의표준동형", "가군의표준동형", "등급환", "부분환", "표준준동형", "동차원소",
        "표준상들의합집합에의해생성", "합동식", "잉여류", "환준동형", "서로역", "뇌터",
    ]:
        require(phrase in compact, f"required terminology/sense guard missing: {phrase}")
    for forbidden in ["표준적동형", "표준적상", "법동치류", "동치류"]:
        require(forbidden not in compact, f"superseded wording remains: {forbidden}")
    require(candidate_text.count("표준적으로") == 3, "actual adverbial 표준적으로 count drift")
    require("이는명제의첫번째부분을증명한다." in compact, "line 1709 wording normalized")
    require("$1/(g^d/f^e)=f^{d+e}/(fg)^d$" in candidate_text, "line 1738 formula normalized")
    require("역주" not in candidate_text, "candidate inserts an unbound translator note")
    for phrase in [
        "$fg$는$f^eg^d$의약수이고,후자는$(fg)^{de}$의약수이므로",
        "$g^d/f^e$는차수가$0$인$S_{f^e}$의원소이다.",
        "두번째부분도같은방식으로확립된다.",
        "다음도식은가환한다.",
        "상에속함을보이면충분하며",
        "모든양의정수지수에대하여합동식",
        "따라서$f^hx=0$인$h>0$가있으면",
        "반드시$h=n$이고$x=-y_{hd}$이며",
        r"$\overline{x}$,곧$x$의$(f-1)S^{(d)}$에대한잉여류를대응시켜정의한다.",
        r"따라서$x\inS_{nd}$인원소가나타내는$(f-1)S^{(d)}$에대한각잉여류$\overline{x}$에$S_{(f)}$의원소$x/f^n$을대응시킬수있다.",
        "$S$가뇌터이면,차수가$>0$인임의의동차원소$f$에대하여$S_{(f)}$도뇌터이다.",
    ]:
        require(phrase in compact, f"logical/quantifier guard missing: {phrase}")

    private = args.private_target.read_bytes()
    public = args.public_target.read_bytes()
    require(private == public, "integrated R38 private/public preimages differ")
    require(len(private) == 80222, "integrated R38 preimage byte count drift")
    require(private.count(b"\n") == 1708, "integrated R38 preimage LF count drift")
    require(b"\r" not in private and private.endswith(b"\n"), "R38 preimage is not LF-only")
    require(digest(private) == TARGET_PREIMAGE_SHA256, "integrated R38 preimage hash drift")
    require(private.rstrip().endswith(b"\\end{env}"), "integrated R38 end boundary drift")
    require(not private.endswith(candidate), "R39 candidate is already integrated")

    separator_plus_candidate = b"\n" + candidate
    prospective = private + separator_plus_candidate
    require(len(separator_plus_candidate) == 4052, "separator-plus-candidate byte count drift")
    require(
        digest(separator_plus_candidate)
        == "7CF528B90E7D1D50EEAABF714AB185C574F5C8A86520F46A7D697FAFB381186C",
        "separator-plus-candidate hash drift",
    )
    require(len(prospective) == 84274, "prospective integrated byte count drift")
    require(len(prospective.decode("utf-8")) == 58678, "prospective character count drift")
    require(prospective.count(b"\n") == 1809, "prospective LF count drift")
    require(digest(prospective) == TARGET_POSTIMAGE_SHA256, "prospective integrated hash drift")
    prospective_lines = prospective.decode("utf-8").splitlines()
    require(prospective_lines[1708] == "", "prospective separator line 1709 drift")
    require(prospective_lines[1709] == r"\begin{lemma}[2.2.2]", "prospective start-line drift")
    require(prospective_lines[1808] == r"\end{proof}", "prospective end-line drift")

    negative_results = run_negative_tests(args) if args.self_test_negatives else []
    print(
        json.dumps(
            {
                "schema": "agko-r39-current-authority-validation-v2",
                "result": "PASS_R39_CURRENT_AUTHORITY_CANDIDATE_AND_PROSPECTIVE_TARGET",
                "current_canonical": {
                    "bytes": len(raw), "characters": len(canonical_text),
                    "lf_lines": len(canonical_lines), "sha256": digest(raw),
                },
                "d54_single_byte_rebase": {
                    "line": 1542, "operation": "delete one ASCII comma",
                    "preimage_bytes": len(pre_d54), "preimage_sha256": digest(pre_d54),
                    "postimage_bytes": len(raw), "postimage_sha256": digest(raw),
                    "exact_single_byte_inverse": True,
                    "preunit_prefix_byte_delta": -1,
                    "admitted_prefix_byte_delta": -1,
                    "r39_unit_byte_identical": True,
                },
                "source_unit": {
                    "lines": "1685-1780", "bytes": len(source),
                    "characters": len(source_text), "lf_lines": source.count(b"\n"),
                    "sha256": digest(source),
                },
                "candidate": {
                    "bytes": len(candidate), "characters": len(candidate_text),
                    "lf_lines": candidate.count(b"\n"), "sha256": digest(candidate),
                    "historical_preimage_exactly_reconstructed": True,
                    "historical_preimage_sha256": digest(historical_candidate),
                },
                "math_and_structure": {
                    "inline_formula_count": len(source_math), "display_count": len(source_displays),
                    "inline_formula_multiset_exact": True,
                    "display_content_and_order_exact": True,
                    "clause_local_formula_audit": clause_audit,
                    "labels_references_environments_oldpage_exact": True,
                    "terminology_and_logical_guards": "PASS",
                },
                "target_preimage": {
                    "private_public_exact": True, "bytes": len(private),
                    "lf_lines": private.count(b"\n"), "sha256": digest(private),
                },
                "prospective_target": {
                    "bytes": len(prospective), "characters": len(prospective.decode("utf-8")),
                    "lf_lines": prospective.count(b"\n"), "sha256": digest(prospective),
                    "integrated_now": False,
                },
                "historical_validator_preserved": True,
                "wording_reseal": {
                    "control_bytes": len(reseal_raw),
                    "control_sha256": digest(reseal_raw),
                    "exact_reverse_reconstruction": True,
                    "quotient_class_register": "잉여류",
                    "canonical_noun_compounds": "표준 동형; 표준 준동형; 표준 상",
                    "commutative_diagram": "다음 도식은 가환한다",
                    "actual_adverbial_standardly_count": candidate_text.count("표준적으로"),
                },
                "negative_tests": negative_results,
            },
            ensure_ascii=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
