#!/usr/bin/env python3
"""Seal the exact R38 target integration without building or publishing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


UPDATED = "2026-09-05T16:05:35+02:00"
STATUS = "PASS_R38_TRANSLATION_INTEGRATION; build, PDF QA, package and publication pending"
DECISION_ID = "AGKO-D187"
EVIDENCE_ID = "AGKO-E-R38-INTEGRATION-20260905"
HARD_ID = "AGKO-H162"
HARDENED_MARKER = "## 64. 2026-09-05 R38 exact integration and fail-closed append recovery"

WHOLE_SOURCE = {
    "path": "source/ega2/ega2-1-fr.tex",
    "bytes": 820505,
    "lf_lines": 18087,
    "sha256": "84EDBE3E83530AF2959B441796337C9DC21EAFCA6A13114A26778760FBF437AC",
}
SOURCE_UNIT = {
    "lines": "1607-1683",
    "bytes": 4191,
    "characters": 4096,
    "lf_lines": 77,
    "sha256": "44583D53F17603797145FE63822F3F78DC6ECFD7ADA1B38EF01813F9E3F22BE6",
}
SOURCE_PREFIX = {
    "lines": "1-1683",
    "bytes": 78089,
    "characters": 76888,
    "lf_lines": 1683,
    "sha256": "6C9C0EE5DC909DFE7911564F1F982FF0539C923DE706188F7935FC0585549585",
}
CANDIDATE = {
    "path": "candidates/r38-c2s1-continuation.tex",
    "bytes": 4599,
    "characters": 2773,
    "lf_lines": 80,
    "sha256": "8D37AF2B8B05D9C938F2D282F58902092FB7FCF55300B0A85B28C9538340CF93",
}
SEALED_PREIMAGE = {
    "bytes": 75622,
    "lf_lines": 1627,
    "sha256": "FA2AA45404EE63442184A43AD744DE0D03CC053C77C35DA26A0ED8044CB1A383",
}
TARGET = {
    "private_path": "ega/II/c2s1.tex",
    "public_path": "source/c2s1.tex",
    "bytes": 80222,
    "characters": 55906,
    "lf_lines": 1708,
    "sha256": "4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006",
    "separator_line": 1628,
    "candidate_target_lines": "1629-1708",
}
ADMISSION = {
    "private_path": "controls/R38_TRANSLATION_ADMISSION.json",
    "public_path": "evidence/controls/R38_TRANSLATION_ADMISSION.json",
    "bytes": 8103,
    "sha256": "23CA8C711E89448D910BCD585BCC815B1A87F56A9890220485F27E3E8377FEC2",
    "result": "PASS_R38_SOURCE_CANDIDATE_AND_PROSPECTIVE_MIRRORS",
}
VALIDATOR = {
    "path": "candidates/validate_r38_candidate.py",
    "bytes": 16396,
    "lf_lines": 400,
    "sha256": "3FC051E0944E506E1F6366B84CC3B55B279FA74B7E6F183ED6ECE38E6D830AAC",
}
TRANSIENT = {
    "bytes": 80222,
    "sha256": "92696CAAEEB39496CA4A12432D410BBC0124515CC0ED7E52FB1E83D49ACFDAE2",
    "wrong_candidate_start_line": 1046,
}
R37_CONTROL = {
    "private_path": "controls/R37_PUBLIC_CLOSURE.json",
    "public_path": "evidence/controls/R37_PUBLIC_CLOSURE.json",
    "bytes": 4271,
    "sha256": "033D857627D0D5E65F7AF47C0050D7F1B065C816B5B9045BBB3F33AF3D1401C5",
}
WORKING_COVERAGE = (
    "EGA 0_I and EGA I complete; EGA II programme/table of contents complete; EGA II main text "
    "translated contiguously through 2.2.1 / canonical lines1-1683. EGA II and the full corpus remain incomplete."
)
NEXT_SOURCE = (
    "EGA II canonical source/ega2/ega2-1-fr.tex line1685, Lemma2.2.2; line1684 is blank"
)

PUBLIC_ALIAS_NAMES = (
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


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def compact_record(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def identity(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), sha256(data)


def require_identity(path: Path, expected: dict[str, Any]) -> bytes:
    data = path.read_bytes()
    actual = (len(data), sha256(data))
    wanted = (expected["bytes"], expected["sha256"])
    if actual != wanted:
        raise RuntimeError(f"identity mismatch for {path}: expected {wanted}, got {actual}")
    return data


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            raise RuntimeError(f"blank JSONL line {number}: {path}")
        value = json.loads(line)
        if not isinstance(value, dict) or not isinstance(value.get("id"), str):
            raise RuntimeError(f"invalid JSONL record {number}: {path}")
        records.append(value)
    ids = [row["id"] for row in records]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"duplicate JSONL ids: {path}")
    return records


def integration_control() -> dict[str, Any]:
    return {
        "schema": "agko-r38-translation-integration-v1",
        "time": UPDATED,
        "precision": "second",
        "scope": (
            "EGA II canonical lines1607-1683: environments2.1.10-2.1.11, subsection2.2, "
            "and environment2.2.1"
        ),
        "authority": {"whole": WHOLE_SOURCE, "unit": SOURCE_UNIT, "admitted_prefix": SOURCE_PREFIX},
        "admission": {
            **ADMISSION,
            "private_public_exact": True,
            "validator": VALIDATOR,
            "formula_policy": (
                "111 source and target inline formulas have an exact global multiset and exact multisets "
                "inside all22 exhaustive semantic-clause partitions; no formula crosses an environment, "
                "statement, assertion, proof step or definition boundary"
            ),
        },
        "candidate": CANDIDATE,
        "sealed_preimage": {
            **SEALED_PREIMAGE,
            "private_path": "ega/II/c2s1.tex",
            "public_path": "pub/ega-ko/source/c2s1.tex",
            "verified_as_exact_prefix_of_both_final_mirrors": True,
        },
        "fail_closed_recovery": {
            "status": "DETECTED_REJECTED_AND_RECOVERED_BEFORE_BUILD_OR_PUBLICATION",
            "transient": TRANSIENT,
            "transient_observation_provenance": (
                "The integration operator reported the transient identity and locus; this sealing pass "
                "independently reverified the restored sealed prefix and the final correct integration."
            ),
            "cause": (
                "The first append patch matched an earlier nonunique environment terminator and began the "
                "candidate at target line1046 instead of the true end."
            ),
            "detection": (
                "The predetermined whole-target SHA-256 gate rejected the transient 80,222-byte result "
                "before any build, reader update, package or publication."
            ),
            "recovery": (
                "Both target mirrors were restored exactly to the sealed R37 preimage, then the unchanged "
                "candidate was appended after the true terminal line with exactly one LF separator."
            ),
            "content_effect": (
                "No transient byte was admitted, built or published; the recovery introduced no translation "
                "content change and the final target equals the predetermined prospective identity."
            ),
        },
        "final_integration": {
            **TARGET,
            "private_public_exact": True,
            "sealed_prefix_exact": True,
            "line1628": "one LF-only blank separator",
            "target_lines1629_1708_equal_candidate": True,
            "method": "sealed preimage + one LF + exact candidate",
        },
        "source_queries": {
            "destination_task": "01a047ab-fc94-7120-af1d-5701ba37aacd",
            "lines": [1638, 1664],
            "status": "already delivered and nonblocking; no French source byte changed",
        },
        "public_checkpoint": {
            "version": "2026-09-05-r37",
            "exact_doi": "10.5281/zenodo.22315714",
            "concept_doi": "10.5281/zenodo.21921513",
            "github_release": "ega-ko-2026-09-05-r37",
            "status": "preserved as the latest built, QA-checked and public checkpoint",
        },
        "state": {
            "translation_admission": "PASS",
            "exact_mirror_integration": "PASS",
            "build": "PENDING",
            "extraction": "PENDING",
            "rendered_pdf_qa": "PENDING",
            "package_and_portable_replay": "PENDING",
            "publication_and_anonymous_readback": "PENDING",
            "ega_ii": "active_incomplete",
        },
        "ledger_records": {
            "decision": DECISION_ID,
            "evidence": EVIDENCE_ID,
            "hard": HARD_ID,
        },
        "result": STATUS,
        "next": (
            "Refresh cumulative declarations through canonical line1683, then run the serialized cumulative "
            "build and deterministic PDF QA; preserve R37 as the public checkpoint until all R38 release gates pass."
        ),
    }


def binding(control_data: bytes, public: bool) -> dict[str, Any]:
    control_path = (
        "evidence/controls/R38_TRANSLATION_INTEGRATION.json"
        if public
        else "controls/R38_TRANSLATION_INTEGRATION.json"
    )
    target = dict(TARGET)
    if public:
        target["private_path"] = "private:ega/II/c2s1.tex"
    return {
        "status": STATUS,
        "control": {"path": control_path, "bytes": len(control_data), "sha256": sha256(control_data)},
        "source": {**WHOLE_SOURCE, "admitted_lines": "1-1683", "admitted_bytes": SOURCE_PREFIX["bytes"], "admitted_sha256": SOURCE_PREFIX["sha256"]},
        "unit": SOURCE_UNIT,
        "candidate": CANDIDATE,
        "target": target,
        "admission": ADMISSION,
        "recovery": {
            "transient_sha256": TRANSIENT["sha256"],
            "wrong_candidate_start_line": 1046,
            "gate": "rejected before build/publication; restored exact preimage; final prospective hash PASS",
        },
        "gates": {
            "translation_admission": "PASS",
            "exact_mirror_integration": "PASS",
            "build": "PENDING",
            "pdf_qa": "PENDING",
            "package_portable_replay": "PENDING",
            "publication_anonymous_readback": "PENDING",
        },
        "ega_ii_status": "active_incomplete",
        "next_source": NEXT_SOURCE,
    }


def decision_record(control_data: bytes) -> dict[str, Any]:
    return {
        "id": DECISION_ID,
        "time": UPDATED,
        "precision": "second",
        "kind": "r38_exact_translation_integration_and_fail_closed_recovery",
        "scope": "EGA II canonical lines1607-1683 / target lines1629-1708",
        "choice": (
            "Admit the already reviewed R38 candidate only at the true end of the sealed R37 target, with one "
            "LF separator, and require both mirrors to equal the predetermined 80,222-byte whole-target hash. "
            "Record and reject the earlier line1046 misplacement without changing candidate content."
        ),
        "alternatives": [
            "Accept the syntactically plausible line1046 insertion",
            "Edit around the transient file instead of restoring the sealed preimage",
            "Treat translation integration as proof of build, PDF QA or publication",
        ],
        "rejected": (
            "Each would break canonical order, weaken byte provenance, or overclaim an unrun downstream gate."
        ),
        "evidence": [
            f"controls/R38_TRANSLATION_INTEGRATION.json {len(control_data)} bytes /{sha256(control_data)}",
            f"controls/R38_TRANSLATION_ADMISSION.json {ADMISSION['bytes']} bytes /{ADMISSION['sha256']}",
            f"candidate {CANDIDATE['bytes']} bytes /{CANDIDATE['sha256']}",
            f"integrated private/public {TARGET['bytes']} bytes /{TARGET['sha256']}",
            f"sealed prefix {SEALED_PREIMAGE['bytes']} bytes /{SEALED_PREIMAGE['sha256']}",
            f"canonical prefix lines1-1683 {SOURCE_PREFIX['bytes']} bytes /{SOURCE_PREFIX['sha256']}",
        ],
        "uncertainty": (
            "None in the recorded byte integration. Build, extraction, rendered QA, packaging and publication "
            "remain explicitly unperformed for R38."
        ),
        "consequence": (
            "Korean EGA II is translated contiguously through2.2.1 / canonical line1683 in exact private/public "
            "source mirrors; EGA II remains incomplete and R37 remains the latest public checkpoint."
        ),
        "review": "PASS_R38_EXACT_MIRROR_INTEGRATION_ONLY",
        "next": "Refresh cumulative declarations and execute the R38 build/QA/release gates; next source line1685.",
    }


def evidence_record(control_data: bytes) -> dict[str, Any]:
    return {
        "id": EVIDENCE_ID,
        "time": UPDATED,
        "precision": "second",
        "kind": "r38_translation_integration_exact_identity",
        "coverage": WORKING_COVERAGE,
        "authority": {"unit": SOURCE_UNIT, "prefix": SOURCE_PREFIX},
        "candidate": CANDIDATE,
        "target": {**TARGET, "private_public_exact": True},
        "separator": {
            "line": 1628,
            "bytes": 1,
            "sha256": "01BA4719C80B6FE911B091A7C05124B64EEECE964E09C058EF8F9805DACA546B",
            "value": "LF",
        },
        "candidate_binding": "target lines1629-1708 byte-identical to the exact candidate",
        "admission": {**ADMISSION, "validator": VALIDATOR, "private_public_exact": True},
        "recovery": {
            "transient": TRANSIENT,
            "result": "REJECTED_BEFORE_BUILD_PUBLICATION_RESTORED_PREIMAGE_FINAL_EXPECTED_HASH_PASS",
        },
        "control": {
            "private": "controls/R38_TRANSLATION_INTEGRATION.json",
            "public": "evidence/controls/R38_TRANSLATION_INTEGRATION.json",
            "bytes": len(control_data),
            "sha256": sha256(control_data),
            "mirrors_exact": True,
        },
        "result": STATUS,
        "next": NEXT_SOURCE,
    }


def hard_record() -> dict[str, Any]:
    return {
        "id": HARD_ID,
        "time": UPDATED,
        "precision": "second",
        "status": "resolved_r38_append_anchor_misplacement_before_build_or_publication",
        "scope": "R38 append of EGA II2.1.10-2.2.1 to c2s1.tex",
        "locator": "transient candidate start line1046; final separator line1628 and candidate lines1629-1708",
        "symptom": (
            "The first integration produced the expected 80,222-byte length but SHA-256 "
            f"{TRANSIENT['sha256']} because a nonunique anchor placed the candidate at line1046."
        ),
        "cause_evidence": (
            "Length alone could not distinguish the wrong placement. The predetermined prospective whole-target "
            f"hash {TARGET['sha256']} failed, so the transient was not admitted."
        ),
        "attempted": [
            "Build the transient because the byte count and TeX syntax were plausible; rejected.",
            "Move or edit fragments inside the transient; rejected because that would weaken provenance.",
            "Restore both exact R37 preimages and append the unchanged candidate after the true EOF; accepted.",
        ],
        "resolution": (
            "Both mirrors now begin with the exact 75,622-byte R37 preimage, line1628 is one LF-only blank "
            "separator, lines1629-1708 equal the exact 4,599-byte candidate, and both whole mirrors equal "
            f"80,222 bytes /{TARGET['sha256']}."
        ),
        "tests": (
            "Private/public whole mirror identity PASS; sealed-prefix identity PASS; separator identity PASS; "
            "candidate-tail identity PASS; canonical prefix1-1683 PASS; admission-control mirror and validator "
            "identities PASS; no R38 build or publication claim."
        ),
        "residual_risk": (
            "A future append anchored on a common environment terminator could again preserve length while "
            "misordering valid TeX. Downstream build/QA/publication gates for R38 remain pending."
        ),
        "recurrence": (
            "For every cumulative append, derive and gate the complete prospective whole-target SHA-256 from the "
            "sealed preimage plus exact separator and candidate before any build; then prove prefix, insertion locus, "
            "candidate tail and ordered environment labels."
        ),
        "related": [DECISION_ID, EVIDENCE_ID, "AGKO-H114", "AGKO-H117", "AGKO-H161"],
    }


def append_record(path: Path, record: dict[str, Any]) -> bytes:
    existing = path.read_bytes()
    if not existing.endswith(b"\n"):
        raise RuntimeError(f"JSONL lacks terminal LF: {path}")
    return existing + compact_record(record)


def verify_fresh_ids(private: Path, evidence: Path) -> None:
    mappings = (
        ("decisions.jsonl", "AGKO-D", 186, DECISION_ID),
        ("hard.jsonl", "AGKO-H", 161, HARD_ID),
    )
    for name, prefix, expected_max, new_id in mappings:
        for root in (private, evidence):
            rows = load_jsonl(root / name)
            numeric = [int(row["id"][len(prefix):]) for row in rows if row["id"].startswith(prefix) and row["id"][len(prefix):].isdigit()]
            if max(numeric) != expected_max or any(row["id"] == new_id for row in rows):
                raise RuntimeError(f"fresh id gate failed for {root / name}")
    for root in (private, evidence):
        if any(row["id"] == EVIDENCE_ID for row in load_jsonl(root / "evidence.jsonl")):
            raise RuntimeError(f"evidence id already exists: {root / 'evidence.jsonl'}")


def verify_inputs(private: Path, repo: Path, canonical: Path) -> None:
    evidence = repo / "evidence"
    candidate = require_identity(private / CANDIDATE["path"], CANDIDATE)
    private_target = require_identity(private / TARGET["private_path"], TARGET)
    public_target = require_identity(repo / TARGET["public_path"], TARGET)
    if private_target != public_target:
        raise RuntimeError("private/public R38 targets are not exact mirrors")
    if private_target[: SEALED_PREIMAGE["bytes"]] != require_prefix(private_target):
        raise RuntimeError("internal sealed-prefix verifier failed")
    if private_target[SEALED_PREIMAGE["bytes"] : SEALED_PREIMAGE["bytes"] + 1] != b"\n":
        raise RuntimeError("line1628 is not the exact one-LF separator")
    if private_target[SEALED_PREIMAGE["bytes"] + 1 :] != candidate:
        raise RuntimeError("target lines1629-1708 do not equal the candidate")
    if len(private_target.decode("utf-8")) != TARGET["characters"] or private_target.count(b"\n") != TARGET["lf_lines"]:
        raise RuntimeError("target character or LF count mismatch")

    admission_private = require_identity(private / ADMISSION["private_path"], ADMISSION)
    admission_public = require_identity(repo / ADMISSION["public_path"], ADMISSION)
    if admission_private != admission_public:
        raise RuntimeError("admission controls are not exact mirrors")
    require_identity(private / VALIDATOR["path"], VALIDATOR)
    r37_private = require_identity(private / R37_CONTROL["private_path"], R37_CONTROL)
    r37_public = require_identity(repo / R37_CONTROL["public_path"], R37_CONTROL)
    if r37_private != r37_public:
        raise RuntimeError("R37 closure controls are no longer exact mirrors")

    source = require_identity(canonical, WHOLE_SOURCE)
    lines = source.splitlines(keepends=True)
    prefix = b"".join(lines[:1683])
    unit = b"".join(lines[1606:1683])
    if (len(prefix), len(prefix.decode("utf-8")), prefix.count(b"\n"), sha256(prefix)) != (
        SOURCE_PREFIX["bytes"], SOURCE_PREFIX["characters"], SOURCE_PREFIX["lf_lines"], SOURCE_PREFIX["sha256"]
    ):
        raise RuntimeError("canonical prefix1-1683 mismatch")
    if (len(unit), len(unit.decode("utf-8")), unit.count(b"\n"), sha256(unit)) != (
        SOURCE_UNIT["bytes"], SOURCE_UNIT["characters"], SOURCE_UNIT["lf_lines"], SOURCE_UNIT["sha256"]
    ):
        raise RuntimeError("canonical unit1607-1683 mismatch")


def require_prefix(target: bytes) -> bytes:
    prefix = target[: SEALED_PREIMAGE["bytes"]]
    if (len(prefix), prefix.count(b"\n"), sha256(prefix)) != (
        SEALED_PREIMAGE["bytes"], SEALED_PREIMAGE["lf_lines"], SEALED_PREIMAGE["sha256"]
    ):
        raise RuntimeError("sealed R37 prefix mismatch")
    return prefix


def update_private_cursor(data: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    data["updated"] = UPDATED
    data["completed_through"] = WORKING_COVERAGE
    data["source"] = current["source"]
    data["unit"] = SOURCE_UNIT
    data["candidate"] = CANDIDATE
    data["target"] = {
        "private": TARGET["private_path"],
        "public_mirror": f"pub/ega-ko/{TARGET['public_path']}",
        "bytes": TARGET["bytes"],
        "characters": TARGET["characters"],
        "lf_lines": TARGET["lf_lines"],
        "sha256": TARGET["sha256"],
        "mirrors_exact": True,
    }
    data["next"] = (
        "R38 exact mirror integration is complete. Refresh cumulative declarations, then run the serialized "
        "build and deterministic PDF QA; continue source preparation at canonical line1685 without reopening R37."
    )
    data["local_status"] = STATUS
    data["r38_candidate_status"] = "INTEGRATED_EXACT_MIRRORS; build, PDF QA and publication pending"
    data["r38_translation_integration"] = current
    data["ega_ii_status"] = "active_incomplete"
    data["source_caveat"] = (
        "Canonical lines1638 and1664 retain their exact source bytes; the universal/generic reading and integer "
        "exponent including zero are explicit in Korean and the nonblocking queries were already delivered."
    )
    data["correction_route"] = (
        "All possible source-correction candidates go to task01a047ab-fc94-7120-af1d-5701ba37aacd; "
        "R38 lines1638 and1664 were already delivered."
    )
    return data


def update_private_authority(data: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    data["updated"] = UPDATED
    ega = data.setdefault("ega_ii", {})
    ega["status"] = (
        "canonical five-input packet present; Korean front/programme complete; main input translated and "
        "integrated contiguously through lines1-1683 /2.2.1; EGA II active and incomplete; next source line1685"
    )
    ega["next"] = "source/ega2/ega2-1-fr.tex line1685, Lemma2.2.2; line1684 blank"
    for admitted in ega.get("admitted", []):
        if admitted.get("target") == "ega/II/c2s1.tex":
            admitted.update({
                "source": "source/ega2/ega2-1-fr.tex lines1-1683",
                "source_slice_bytes": SOURCE_PREFIX["bytes"],
                "source_slice_sha256": SOURCE_PREFIX["sha256"],
                "bytes": TARGET["bytes"],
                "sha256": TARGET["sha256"],
                "source_policy": (
                    "French diplomatic; exact source/query provenance retained; lines1638 and1664 translated "
                    "with explicit mathematical force and referred nonblockingly without altering French bytes"
                ),
            })
    ega["r38_translation_integration"] = current
    data["current_working_status"] = STATUS
    return data


def update_private_state(data: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    data["updated"] = UPDATED
    data["r38_translation_integration"] = current
    data["candidate_r38"] = current
    active = data.setdefault("active", {})
    if "qa" in active and "last_public_r37_qa" not in active:
        active["last_public_r37_qa"] = active["qa"]
    active["admitted"] = (
        "front/programme complete plus main lines1-1683 through2.2.1; "
        f"prefix{SOURCE_PREFIX['bytes']}/{SOURCE_PREFIX['sha256']}"
    )
    active["unit"] = SOURCE_UNIT
    active["candidate"] = CANDIDATE
    active["target"] = TARGET
    active["qa"] = {
        "translation_admission": "PASS",
        "exact_mirror_integration": "PASS",
        "build": "PENDING",
        "pdf_qa": "PENDING",
        "publication": "PENDING",
    }
    active["next_source"] = "source/ega2/ega2-1-fr.tex line1685; Lemma2.2.2"
    active["next_target"] = (
        "Refresh cumulative declarations, then build and QA R38 under the machine TeX mutex; package and "
        "publish only after all deterministic gates pass."
    )
    active["gate"] = (
        "R38 translation integration is exact; no R38 build, reader, PDF QA, package or publication is yet claimed. "
        "EGA II remains active and incomplete."
    )
    data["next_executable_action"] = active["next_target"] + " Continue source preparation at line1685."
    data["continuation_audit"] = {
        "classification": "progress",
        "current_progress": (
            "R38 source/candidate admission and exact mirror integration through canonical line1683 PASS after "
            "a wrong-anchor transient was rejected and recovered before build/publication."
        ),
    }
    return data


def update_public_alias(name: str, data: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    data["updated"] = UPDATED
    data["current_working_status"] = STATUS
    data["working_translation_coverage"] = WORKING_COVERAGE
    data["r38_translation_integration"] = current
    data["r38_candidate_status"] = "INTEGRATED_EXACT_MIRRORS; build, PDF QA and publication pending"
    data["ega_ii_status"] = "active_incomplete"
    data["next_source"] = NEXT_SOURCE
    data["publication_evidence_rule"] = (
        "R37 remains the latest built, QA-checked and public checkpoint. R38 is only an exact local source-mirror "
        "integration until its build, PDF QA, package, publication and anonymous-readback gates pass."
    )
    data["r38_release_gates"] = current["gates"]

    if name in {"CURSOR.json", "PROGRAM_CURSOR.json", "STATE.json", "PROGRAM_STATE.json", "SOURCE_AUTHORITY.json"}:
        data["source"] = current["source"]
        data["unit"] = SOURCE_UNIT
        data["candidate"] = CANDIDATE
        data["target"] = {
            "path": "source/c2s1.tex",
            "private_mirror": "private:ega/II/c2s1.tex",
            "bytes": TARGET["bytes"],
            "characters": TARGET["characters"],
            "lf_lines": TARGET["lf_lines"],
            "sha256": TARGET["sha256"],
            "mirrors_exact": True,
        }
        data["translation_admission"] = {
            "path": ADMISSION["public_path"],
            "bytes": ADMISSION["bytes"],
            "sha256": ADMISSION["sha256"],
            "result": ADMISSION["result"],
        }
    if name in {"CURSOR.json", "PROGRAM_CURSOR.json", "STATE.json", "PROGRAM_STATE.json"}:
        data["coverage"] = (
            WORKING_COVERAGE
            + " The retained reader/manifest and public DOI fields describe the last public R37 checkpoint, not R38."
        )
        data["reader_scope"] = "R37 last public checkpoint; R38 reader pending build and QA"
        data["coverage_manifest_scope"] = "R37 last public checkpoint; R38 manifest refresh pending"
    if name in {"STATE.json", "PROGRAM_STATE.json"}:
        data["last_public_result"] = data.get("result")
        data["result"] = STATUS
    elif name in {"QA_STATE.json", "VISUAL_QA.json"}:
        data["r38_qa_status"] = "PENDING; retained QA fields apply only to R37"
    elif name == "PROGRAM_AUTHORITY.json":
        data["scope"] = WORKING_COVERAGE
        bindings = data.setdefault("current_bindings", {})
        bindings["canonical_prefix"] = current["source"]
        bindings["translated_unit"] = SOURCE_UNIT
        bindings["translation_candidate"] = CANDIDATE
        bindings["korean_target"] = {
            "path": "source/c2s1.tex",
            "bytes": TARGET["bytes"],
            "lf_lines": TARGET["lf_lines"],
            "sha256": TARGET["sha256"],
            "private_public_exact": True,
        }
        bindings["translation_integration"] = current["control"]
        data["publication"]["working_status"] = STATUS
        data["publication"]["latest_public_checkpoint_remains"] = "2026-09-05-r37"
    elif name == "DATACITE_RELATIONS.json":
        data["working_version_status"] = STATUS
        data["latest_public_version_remains"] = "2026-09-05-r37"
    return data


def hardened_section(control_bytes: bytes) -> str:
    return f"""

{HARDENED_MARKER}

R38 admits canonical EGA II lines 1607--1683, 4,191 LF UTF-8 bytes / 4,096 characters / `{SOURCE_UNIT['sha256']}`, bringing the exact canonical prefix through 2.2.1 to 78,089 bytes / `{SOURCE_PREFIX['sha256']}`. The admitted Korean candidate is 4,599 bytes / `{CANDIDATE['sha256']}`. Both live target mirrors are exactly 80,222 bytes / 55,906 characters / 1,708 LF lines / `{TARGET['sha256']}`. Their first 75,622 bytes are the sealed R37 preimage `{SEALED_PREIMAGE['sha256']}`; target line 1628 is exactly one LF-only blank separator; target lines 1629--1708 are byte-identical to the candidate. The private/public admission controls are exact mirrors at 8,103 bytes / `{ADMISSION['sha256']}`, and the validator is 16,396 bytes / `{VALIDATOR['sha256']}`.

The first append attempt is retained as fail-closed evidence, not hidden: it produced the same 80,222-byte length but hash `{TRANSIENT['sha256']}` because the candidate began at line 1046 after a nonunique anchor. The predetermined whole-target hash gate caught that placement before any build, reader update, package or publication. Both mirrors were restored byte-exactly to the sealed R37 preimage and the unchanged candidate was then appended at the true end. The final complete-target, prefix, separator and candidate-tail hashes all pass. Therefore the incident records a detected and recovered placement failure, not an admitted content change.

The identical integration control is `R38_TRANSLATION_INTEGRATION.json`, {len(control_bytes):,} bytes / `{sha256(control_bytes)}`. R38 translation admission and exact mirror integration pass. No R38 cumulative build, extraction, rendered PDF QA, package, portable replay, publication or anonymous readback is claimed. R37 remains the latest built and public checkpoint. EGA II remains active and incomplete; the next source begins at canonical line 1685, Lemma 2.2.2, after blank line 1684.
"""


def atomic_replace_all(outputs: dict[Path, bytes], originals: dict[Path, tuple[int, str]]) -> None:
    for path, expected in originals.items():
        if identity(path) != expected:
            raise RuntimeError(f"concurrent input change before seal: {path}")
    staged: list[tuple[Path, Path]] = []
    try:
        for path in sorted(outputs, key=lambda value: str(value).casefold()):
            temporary = path.with_name(path.name + ".r38-integration-tmp")
            if temporary.exists():
                raise RuntimeError(f"stale temporary file: {temporary}")
            with temporary.open("xb") as stream:
                stream.write(outputs[path])
                stream.flush()
                os.fsync(stream.fileno())
            staged.append((temporary, path))
        for temporary, path in staged:
            os.replace(temporary, path)
    finally:
        for temporary, _ in staged:
            if temporary.exists():
                temporary.unlink()


def verify_outputs(private: Path, repo: Path, outputs: list[Path], control_data: bytes) -> None:
    evidence = repo / "evidence"
    private_control = private / "controls" / "R38_TRANSLATION_INTEGRATION.json"
    public_control = evidence / "controls" / "R38_TRANSLATION_INTEGRATION.json"
    if private_control.read_bytes() != control_data or public_control.read_bytes() != control_data:
        raise RuntimeError("integration controls are not exact mirrors")
    for name, record_id in (
        ("decisions.jsonl", DECISION_ID),
        ("evidence.jsonl", EVIDENCE_ID),
        ("hard.jsonl", HARD_ID),
    ):
        for root in (private, evidence):
            rows = load_jsonl(root / name)
            if sum(row["id"] == record_id for row in rows) != 1:
                raise RuntimeError(f"record id not unique after seal: {record_id} in {root / name}")
    for path in (private / "HARDENED.md", evidence / "HARDENED.md"):
        if path.read_text(encoding="utf-8").count(HARDENED_MARKER) != 1:
            raise RuntimeError(f"hardening marker count is not one: {path}")
    private_cursor = load_json(private / "cursor.json")
    private_authority = load_json(private / "authority.json")
    private_state = load_json(private / "state.json")
    if private_cursor.get("r38_translation_integration", {}).get("status") != STATUS:
        raise RuntimeError("private cursor lacks R38 integration status")
    if private_authority.get("ega_ii", {}).get("r38_translation_integration", {}).get("status") != STATUS:
        raise RuntimeError("private authority lacks R38 integration status")
    if private_state.get("r38_translation_integration", {}).get("status") != STATUS:
        raise RuntimeError("private state lacks R38 integration status")
    for name in PUBLIC_ALIAS_NAMES:
        data = load_json(evidence / name)
        if data.get("r38_translation_integration", {}).get("status") != STATUS:
            raise RuntimeError(f"public alias lacks R38 integration status: {name}")
        if data.get("public_r37", {}).get("status") != "PASS_R37_PUBLIC_OPEN_DUAL_DESTINATION_AND_ANONYMOUS_BYTE_REPLAY":
            raise RuntimeError(f"public alias lost R37 closure: {name}")
    prohibited = ("Fig" + "share", "T" + "TP", "Translation and Transcription " + "Project")
    current_metadata_paths = {
        private_control,
        public_control,
        private / "cursor.json",
        private / "authority.json",
        private / "state.json",
        *[evidence / name for name in PUBLIC_ALIAS_NAMES],
    }
    for path in current_metadata_paths:
        text = path.read_text(encoding="utf-8")
        for token in prohibited:
            if token in text:
                raise RuntimeError(f"excluded current-metadata token in {path}")
    report = {
        "result": "PASS_R38_INTEGRATION_STATE_LEDGER_AND_ALIAS_SEAL",
        "records": {"decision": DECISION_ID, "evidence": EVIDENCE_ID, "hard": HARD_ID},
        "control": {"bytes": len(control_data), "sha256": sha256(control_data), "mirrors_exact": True},
        "changed": [
            {"path": str(path), "bytes": identity(path)[0], "sha256": identity(path)[1]}
            for path in sorted(outputs, key=lambda value: str(value).casefold())
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--canonical-source", required=True, type=Path)
    args = parser.parse_args()
    private = args.private_root.resolve()
    repo = args.repo.resolve()
    canonical = args.canonical_source.resolve()
    evidence = repo / "evidence"

    private_control = private / "controls" / "R38_TRANSLATION_INTEGRATION.json"
    public_control = evidence / "controls" / "R38_TRANSLATION_INTEGRATION.json"
    if private_control.exists() or public_control.exists():
        raise RuntimeError("R38 integration control already exists; helper is one-shot")
    for path in (private / "HARDENED.md", evidence / "HARDENED.md"):
        if HARDENED_MARKER in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"R38 hardening section already exists: {path}")

    verify_inputs(private, repo, canonical)
    verify_fresh_ids(private, evidence)
    control_data = json_bytes(integration_control())
    private_binding = binding(control_data, False)
    public_binding = binding(control_data, True)
    decision = decision_record(control_data)
    evidence_value = evidence_record(control_data)
    hard = hard_record()

    mutable_paths = [
        private / "decisions.jsonl",
        evidence / "decisions.jsonl",
        private / "evidence.jsonl",
        evidence / "evidence.jsonl",
        private / "hard.jsonl",
        evidence / "hard.jsonl",
        private / "cursor.json",
        private / "authority.json",
        private / "state.json",
        private / "HARDENED.md",
        evidence / "HARDENED.md",
        *[evidence / name for name in PUBLIC_ALIAS_NAMES],
    ]
    originals = {path: identity(path) for path in mutable_paths}
    outputs: dict[Path, bytes] = {
        private_control: control_data,
        public_control: control_data,
        private / "decisions.jsonl": append_record(private / "decisions.jsonl", decision),
        evidence / "decisions.jsonl": append_record(evidence / "decisions.jsonl", decision),
        private / "evidence.jsonl": append_record(private / "evidence.jsonl", evidence_value),
        evidence / "evidence.jsonl": append_record(evidence / "evidence.jsonl", evidence_value),
        private / "hard.jsonl": append_record(private / "hard.jsonl", hard),
        evidence / "hard.jsonl": append_record(evidence / "hard.jsonl", hard),
        private / "cursor.json": json_bytes(update_private_cursor(load_json(private / "cursor.json"), private_binding)),
        private / "authority.json": json_bytes(update_private_authority(load_json(private / "authority.json"), private_binding)),
        private / "state.json": json_bytes(update_private_state(load_json(private / "state.json"), private_binding)),
    }
    for name in PUBLIC_ALIAS_NAMES:
        path = evidence / name
        outputs[path] = json_bytes(update_public_alias(name, load_json(path), public_binding))
    section = hardened_section(control_data)
    for path in (private / "HARDENED.md", evidence / "HARDENED.md"):
        outputs[path] = (path.read_text(encoding="utf-8").rstrip() + section).encode("utf-8")

    prohibited = ("Fig" + "share", "T" + "TP", "Translation and Transcription " + "Project")
    for value in (control_data, compact_record(decision), compact_record(evidence_value), compact_record(hard), section.encode("utf-8")):
        text = value.decode("utf-8")
        for token in prohibited:
            if token in text:
                raise RuntimeError("excluded token in new R38 integration content")

    atomic_replace_all(outputs, originals)
    verify_inputs(private, repo, canonical)
    verify_outputs(private, repo, list(outputs), control_data)


if __name__ == "__main__":
    main()
