"""Build deterministic, privacy-sanitized expert-review views from public ledgers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA = "agko-public-expert-review-v1"
CONCEPT_DOI = "https://doi.org/10.5281/zenodo.21921513"
GITHUB = "https://github.com/KokunoYumeto/ega-ko"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def first(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, "", [], {}):
            return record[key]
    return "not_recorded"


def sanitize_string(value: str, account_name: str) -> tuple[str, int]:
    replacements = 0
    patterns = [
        (r"(?i)[A-Z]:\\Users\\[^\\/\r\n]+\\Documents\\interlanguage\\", "<workspace>/"),
        (r"(?i)[A-Z]:/Users/[^/\r\n]+/Documents/interlanguage/", "<workspace>/"),
        (r"(?i)[A-Z]:\\Users\\[^\\/\r\n]+\\", "<user-profile>/"),
        (r"(?i)[A-Z]:/Users/[^/\r\n]+/", "<user-profile>/"),
    ]
    result = value
    for pattern, replacement in patterns:
        result, count = re.subn(pattern, replacement, result)
        replacements += count
    if account_name:
        result, count = re.subn(re.escape(account_name), "<account-name>", result, flags=re.I)
        replacements += count
    return result, replacements


def sanitize(value: Any, account_name: str) -> tuple[Any, int]:
    if isinstance(value, str):
        return sanitize_string(value, account_name)
    if isinstance(value, list):
        output = []
        count = 0
        for item in value:
            clean, item_count = sanitize(item, account_name)
            output.append(clean)
            count += item_count
        return output, count
    if isinstance(value, dict):
        output = {}
        count = 0
        for key, item in value.items():
            clean_key, key_count = sanitize_string(str(key), account_name)
            clean_item, item_count = sanitize(item, account_name)
            output[clean_key] = clean_item
            count += key_count + item_count
        return output, count
    return value, 0


def normalized_fields(ledger: str, record: dict[str, Any]) -> dict[str, Any]:
    if ledger == "terms":
        return {
            "scope": first(record, "source"),
            "source_or_locus": first(record, "evidence", "definition_lock_time"),
            "wording_or_resolution": first(record, "ko"),
            "sense_or_problem": first(record, "sense"),
            "authorities_or_evidence": first(record, "evidence", "cjk_register"),
            "alternatives": first(record, "alternatives"),
            "rationale_or_rejection": first(record, "rejected"),
            "uncertainty_or_residual_risk": first(record, "uncertainty"),
            "status": first(record, "review"),
        }
    if ledger == "decisions":
        return {
            "scope": first(record, "scope"),
            "source_or_locus": first(record, "authority", "source", "cursor"),
            "wording_or_resolution": first(record, "choice", "decision"),
            "sense_or_problem": first(record, "motivation", "scope"),
            "authorities_or_evidence": first(record, "evidence", "validation"),
            "alternatives": first(record, "alternatives"),
            "rationale_or_rejection": first(record, "rejected"),
            "uncertainty_or_residual_risk": first(record, "uncertainty", "adverse_evidence"),
            "status": first(record, "review", "kind"),
        }
    if ledger == "hard":
        return {
            "scope": first(record, "scope"),
            "source_or_locus": first(record, "locator"),
            "wording_or_resolution": first(record, "resolution"),
            "sense_or_problem": first(record, "symptom"),
            "authorities_or_evidence": {
                "cause_evidence": first(record, "cause_evidence"),
                "tests": first(record, "tests"),
            },
            "alternatives": first(record, "attempted"),
            "rationale_or_rejection": first(record, "cause_evidence"),
            "uncertainty_or_residual_risk": first(record, "residual_risk"),
            "status": first(record, "status"),
        }
    if ledger == "workflow":
        return {
            "scope": first(record, "scope"),
            "source_or_locus": first(record, "source", "sources"),
            "wording_or_resolution": first(record, "decision", "corrected", "unchanged"),
            "sense_or_problem": first(record, "finding", "source_issue", "defect", "scope"),
            "authorities_or_evidence": first(record, "sources", "source"),
            "alternatives": first(record, "alternatives"),
            "rationale_or_rejection": first(record, "rejected", "rationale"),
            "uncertainty_or_residual_risk": first(record, "uncertainty"),
            "status": first(record, "result", "review", "kind"),
        }
    raise ValueError(f"unknown ledger {ledger}")


def short(value: Any, limit: int = 240) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def review_question(ledger: str, record: dict[str, Any], normalized: dict[str, Any]) -> tuple[str, str]:
    if "review_question" in record and record["review_question"]:
        return str(record["review_question"]), "contemporaneous_recorded"
    identifier = str(record["id"])
    scope = short(normalized["scope"], 180)
    if ledger == "terms":
        wording = short(normalized["wording_or_resolution"], 100)
        question = (
            f"For {identifier} in {scope}, does the recorded Korean form “{wording}” preserve "
            "the stated mathematical sense, and does any cited authority support a different form?"
        )
    elif ledger == "decisions":
        question = (
            f"For {identifier} in {scope}, does the recorded choice follow from its cited "
            "authority and evidence without changing mathematical type, quantifier scope, or provenance?"
        )
    elif ledger == "hard":
        locator = short(normalized["source_or_locus"], 160)
        question = (
            f"For {identifier} at {locator}, does the recorded resolution fully address the "
            "recorded symptom while preserving the stated residual risk?"
        )
    else:
        question = (
            f"For {identifier} in {scope}, do the listed sources support the recorded workflow "
            "decision without overstating their Korean lexical, source-critical, or validation authority?"
        )
    return question, "retrospective_generated_from_recorded_fields"


def markdown_value(value: Any) -> str:
    if value == "not_recorded":
        return "_not recorded in the source ledger_"
    if isinstance(value, str):
        return value.replace("\r", "").strip()
    return "```json\n" + json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n```"


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    private_root = repo.parent.parent
    public_output = repo / "evidence" / "expert_review"
    private_output = private_root / "expert_review"
    inputs = [
        ("terms", repo / "evidence" / "terms.jsonl"),
        ("decisions", repo / "evidence" / "decisions.jsonl"),
        ("hard", repo / "evidence" / "hard.jsonl"),
        ("workflow", repo / "evidence" / "terminology" / "arxiv" / "2026-08-23" / "WORKFLOW_RECORD.jsonl"),
    ]
    account_name = Path.home().name
    input_receipts = []
    output_records = []
    all_ids = []
    total_sanitizations = 0
    times = []

    for ledger, path in inputs:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
            raise RuntimeError(f"{ledger} ledger is not final-LF, LF-only UTF-8")
        lines = [line for line in raw.splitlines() if line.strip()]
        parsed = []
        for index, raw_line in enumerate(lines, 1):
            record = json.loads(raw_line.decode("utf-8"))
            if not isinstance(record, dict) or not record.get("id"):
                raise RuntimeError(f"{ledger} line {index} has no object id")
            parsed.append(record)
            all_ids.append((ledger, str(record["id"])))
            if record.get("time"):
                times.append(str(record["time"]))
            clean_record, replacements = sanitize(record, account_name)
            total_sanitizations += replacements
            normalized = normalized_fields(ledger, clean_record)
            question, provenance = review_question(ledger, clean_record, normalized)
            output_records.append(
                {
                    "schema": SCHEMA,
                    "sequence": len(output_records) + 1,
                    "source_ledger": ledger,
                    "source_record_index": index,
                    "source_record_id": str(record["id"]),
                    "source_line_bytes": len(raw_line),
                    "source_line_sha256": sha256(raw_line),
                    "normalized": normalized,
                    "review_question": question,
                    "review_question_provenance": provenance,
                    "normalization_note": (
                        "The original source record is authoritative. Field grouping is retrospective; "
                        "missing fields remain not_recorded and are not reconstructed as contemporaneous motives."
                    ),
                    "original_record_sanitized": clean_record,
                    "sanitization_replacements": replacements,
                }
            )
        input_receipts.append(
            {
                "ledger": ledger,
                "path": str(path.relative_to(repo)).replace("\\", "/"),
                "records": len(parsed),
                "bytes": len(raw),
                "sha256": sha256(raw),
            }
        )

    if len(all_ids) != len(set(all_ids)):
        duplicate = [item for item, count in Counter(all_ids).items() if count > 1]
        raise RuntimeError(f"duplicate ledger/id pairs: {duplicate}")
    if not times:
        raise RuntimeError("no source-ledger timestamps")
    generated_at = max(times)
    total_records = len(output_records)

    jsonl_payload = (
        "\n".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for record in output_records
        )
        + "\n"
    ).encode("utf-8")

    md = [
        "# Korean EGA expert-review ledger",
        "",
        f"Generated deterministically from the four public source ledgers at {generated_at}.",
        "",
        f"Canonical continuity: [Zenodo concept DOI]({CONCEPT_DOI}) · [GitHub repository]({GITHUB})",
        "",
        (
            "**Coverage statement.** This view covers every record in the named ledgers through the "
            "current EGA II 2.1.7 cursor. It is complete ledger coverage, not a claim that EGA II, "
            "FGA, or the full EGA corpus translation is complete."
        ),
        "",
        (
            "**Provenance rule.** Each original JSON object is embedded in the companion JSONL after "
            "privacy-only path/account sanitization and remains bound to the exact unsanitized source "
            "line by byte count and SHA-256. Grouped fields and generated questions are retrospective; "
            "they are not presented as contemporaneous motives."
        ),
        "",
        "## Input inventory",
        "",
        "| Ledger | Records | Bytes | SHA-256 |",
        "|---|---:|---:|---|",
    ]
    for item in input_receipts:
        md.append(
            f"| {item['path']} | {item['records']} | {item['bytes']} | {item['sha256']} |"
        )
    md.extend(
        [
            "",
            f"Total normalized records: **{total_records}**.",
            "",
            "## Review records",
            "",
        ]
    )
    labels = [
        ("Scope", "scope"),
        ("Source or locus", "source_or_locus"),
        ("Recorded wording or resolution", "wording_or_resolution"),
        ("Recorded sense or problem", "sense_or_problem"),
        ("Recorded authorities or evidence", "authorities_or_evidence"),
        ("Recorded alternatives", "alternatives"),
        ("Recorded rationale or rejection", "rationale_or_rejection"),
        ("Recorded uncertainty or residual risk", "uncertainty_or_residual_risk"),
        ("Recorded status", "status"),
    ]
    for record in output_records:
        md.extend(
            [
                f"### {record['sequence']}. {record['source_record_id']} — {record['source_ledger']}",
                "",
                (
                    f"Source binding: line {record['source_record_index']}, "
                    f"{record['source_line_bytes']} bytes, "
                    f"SHA-256 {record['source_line_sha256']}."
                ),
                "",
            ]
        )
        for label, key in labels:
            md.extend([f"**{label}**", "", markdown_value(record["normalized"][key]), ""])
        md.extend(
            [
                f"**Expert-review question ({record['review_question_provenance']})**",
                "",
                record["review_question"],
                "",
                f"_Privacy-only replacements in embedded original: {record['sanitization_replacements']}._",
                "",
            ]
        )

    markdown_payload = ("\n".join(md).rstrip() + "\n").encode("utf-8")
    public_jsonl = public_output / "EXPERT_REVIEW.jsonl"
    public_markdown = public_output / "EXPERT_REVIEW.md"
    private_jsonl = private_output / "EXPERT_REVIEW.jsonl"
    private_markdown = private_output / "EXPERT_REVIEW.md"
    for path, payload in [
        (public_jsonl, jsonl_payload),
        (private_jsonl, jsonl_payload),
        (public_markdown, markdown_payload),
        (private_markdown, markdown_payload),
    ]:
        atomic_write(path, payload)

    combined_text = jsonl_payload.decode("utf-8") + markdown_payload.decode("utf-8")
    forbidden = [
        r"(?i)[A-Z]:[\\/]+Users[\\/]+",
        r"(?i)(?:access_token|api[_-]?key|authorization)\s*[:=]\s*[A-Za-z0-9_\-]{16,}",
        r"(?i)\b(?:ghp|github_pat|sk)-[A-Za-z0-9_\-]{12,}",
    ]
    for pattern in forbidden:
        if re.search(pattern, combined_text):
            raise RuntimeError(f"public expert-review privacy/credential scan failed: {pattern}")
    if account_name and re.search(re.escape(account_name), combined_text, re.I):
        raise RuntimeError("public expert-review account-name scan failed")

    receipt = {
        "schema": "agko-public-expert-review-receipt-v1",
        "generated_at": generated_at,
        "coverage": (
            "Every current record in the four named public ledgers through EGA II 2.1.7; "
            "complete ledger coverage, not complete corpus coverage."
        ),
        "canonical_links": {"zenodo_concept": CONCEPT_DOI, "github": GITHUB},
        "inputs": input_receipts,
        "records": {
            "total": total_records,
            "by_ledger": dict(Counter(record["source_ledger"] for record in output_records)),
            "unique_ledger_id_pairs": len(set(all_ids)),
        },
        "outputs": {
            "EXPERT_REVIEW.jsonl": {
                "bytes": len(jsonl_payload),
                "lf_lines": jsonl_payload.count(b"\n"),
                "sha256": sha256(jsonl_payload),
                "records": total_records,
            },
            "EXPERT_REVIEW.md": {
                "bytes": len(markdown_payload),
                "lf_lines": markdown_payload.count(b"\n"),
                "sha256": sha256(markdown_payload),
                "record_sections": total_records,
            },
        },
        "mirrors": {
            "public": "pub/ega-ko/evidence/expert_review",
            "private": "expert_review",
            "jsonl_exact": public_jsonl.read_bytes() == private_jsonl.read_bytes(),
            "markdown_exact": public_markdown.read_bytes() == private_markdown.read_bytes(),
        },
        "provenance": {
            "original_records_embedded": True,
            "original_line_byte_and_sha256_bindings": True,
            "retrospective_grouping_label": True,
            "retrospective_question_label": True,
            "missing_fields_are_not_recorded": True,
        },
        "privacy": {
            "path_or_account_replacements": total_sanitizations,
            "absolute_user_profile_scan": "PASS",
            "account_name_scan": "PASS",
            "credential_pattern_scan": "PASS",
        },
        "result": "PASS_COMPLETE_LEDGER_COVERAGE_WITH_INCOMPLETE_CORPUS_SCOPE",
    }
    receipt_payload = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    atomic_write(private_root / "controls" / "PUBLIC_EXPERT_REVIEW_RECEIPT.json", receipt_payload)
    atomic_write(public_output / "PUBLIC_EXPERT_REVIEW_RECEIPT.json", receipt_payload)
    print(
        json.dumps(
            {
                "result": receipt["result"],
                "records": total_records,
                "jsonl": receipt["outputs"]["EXPERT_REVIEW.jsonl"],
                "markdown": receipt["outputs"]["EXPERT_REVIEW.md"],
                "receipt_bytes": len(receipt_payload),
                "receipt_sha256": sha256(receipt_payload),
                "privacy_replacements": total_sanitizations,
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
