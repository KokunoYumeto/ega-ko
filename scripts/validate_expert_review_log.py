"""Independently replay the generated Korean EGA expert-review views."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import build_expert_review_log as builder


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    private_root = repo.parent.parent
    public_dir = repo / "evidence" / "expert_review"
    private_dir = private_root / "expert_review"
    public_receipt_path = public_dir / "PUBLIC_EXPERT_REVIEW_RECEIPT.json"
    private_receipt_path = private_root / "controls" / "PUBLIC_EXPERT_REVIEW_RECEIPT.json"
    public_receipt = public_receipt_path.read_bytes()
    private_receipt = private_receipt_path.read_bytes()
    require(public_receipt == private_receipt, "receipt mirrors differ")
    receipt = json.loads(public_receipt)
    require(receipt["schema"] == "agko-public-expert-review-receipt-v1", "receipt schema drift")

    public_jsonl = (public_dir / "EXPERT_REVIEW.jsonl").read_bytes()
    private_jsonl = (private_dir / "EXPERT_REVIEW.jsonl").read_bytes()
    public_markdown = (public_dir / "EXPERT_REVIEW.md").read_bytes()
    private_markdown = (private_dir / "EXPERT_REVIEW.md").read_bytes()
    require(public_jsonl == private_jsonl, "JSONL mirrors differ")
    require(public_markdown == private_markdown, "Markdown mirrors differ")
    for name, payload in [("JSONL", public_jsonl), ("Markdown", public_markdown)]:
        require(not payload.startswith(b"\xef\xbb\xbf"), f"{name} has BOM")
        require(b"\r" not in payload and payload.endswith(b"\n"), f"{name} is not LF-only final-LF")

    for name, payload in [
        ("EXPERT_REVIEW.jsonl", public_jsonl),
        ("EXPERT_REVIEW.md", public_markdown),
    ]:
        declared = receipt["outputs"][name]
        require(len(payload) == declared["bytes"], f"{name} byte count drift")
        require(payload.count(b"\n") == declared["lf_lines"], f"{name} LF count drift")
        require(digest(payload) == declared["sha256"], f"{name} hash drift")

    rows = [json.loads(line) for line in public_jsonl.decode("utf-8").splitlines() if line.strip()]
    declared_total = receipt["records"]["total"]
    require(len(rows) == declared_total, "normalized record count drift")
    require([row["sequence"] for row in rows] == list(range(1, declared_total + 1)), "sequence drift")
    account_name = Path.home().name
    source_pairs = []
    expected_rows = []
    for item in receipt["inputs"]:
        source_path = repo / item["path"]
        source = source_path.read_bytes()
        require(len(source) == item["bytes"], f"{item['ledger']} input byte drift")
        require(digest(source) == item["sha256"], f"{item['ledger']} input hash drift")
        source_lines = [line for line in source.splitlines() if line.strip()]
        require(len(source_lines) == item["records"], f"{item['ledger']} input record drift")
        for index, raw_line in enumerate(source_lines, 1):
            original = json.loads(raw_line.decode("utf-8"))
            clean, replacements = builder.sanitize(original, account_name)
            normalized = builder.normalized_fields(item["ledger"], clean)
            question, provenance = builder.review_question(item["ledger"], clean, normalized)
            expected_rows.append(
                {
                    "ledger": item["ledger"],
                    "index": index,
                    "id": str(original["id"]),
                    "bytes": len(raw_line),
                    "sha256": digest(raw_line),
                    "clean": clean,
                    "replacements": replacements,
                    "normalized": normalized,
                    "question": question,
                    "provenance": provenance,
                }
            )
            source_pairs.append((item["ledger"], str(original["id"])))

    require(
        len(source_pairs) == len(set(source_pairs)) == len(expected_rows) == declared_total,
        "source ledger/id uniqueness drift",
    )
    for row, expected in zip(rows, expected_rows):
        require(row["schema"] == builder.SCHEMA, "row schema drift")
        require(row["source_ledger"] == expected["ledger"], "row ledger drift")
        require(row["source_record_index"] == expected["index"], "row index drift")
        require(row["source_record_id"] == expected["id"], "row id drift")
        require(row["source_line_bytes"] == expected["bytes"], "row source byte drift")
        require(row["source_line_sha256"] == expected["sha256"], "row source hash drift")
        require(row["original_record_sanitized"] == expected["clean"], "sanitized original drift")
        require(row["sanitization_replacements"] == expected["replacements"], "sanitization count drift")
        require(row["normalized"] == expected["normalized"], "normalized field drift")
        require(row["review_question"] == expected["question"], "review question drift")
        require(row["review_question_provenance"] == expected["provenance"], "question provenance drift")
        require(
            row["review_question_provenance"]
            in {"contemporaneous_recorded", "retrospective_generated_from_recorded_fields"},
            "invalid question provenance",
        )

    markdown = public_markdown.decode("utf-8")
    headings = re.findall(r"^### ([0-9]+)\. ([^ ]+) — (terms|decisions|hard|workflow)$", markdown, re.M)
    require(len(headings) == declared_total, "Markdown review-section count drift")
    require(
        [(int(number), identifier, ledger) for number, identifier, ledger in headings]
        == [(row["sequence"], row["source_record_id"], row["source_ledger"]) for row in rows],
        "Markdown review-section identity/order drift",
    )
    require(
        (
            "Canonical continuity: [Zenodo concept DOI]("
            + builder.CONCEPT_DOI
            + ") · [GitHub repository]("
            + builder.GITHUB
            + ")"
        )
        in markdown,
        "canonical continuity link line missing",
    )
    require("complete ledger coverage, not a claim" in markdown, "scope disclaimer missing")
    require("retrospective" in markdown, "retrospective-provenance disclosure missing")

    combined = public_jsonl.decode("utf-8") + markdown
    forbidden = [
        r"(?i)[A-Z]:[\\/]+Users[\\/]+",
        r"(?i)(?:access_token|api[_-]?key|authorization)\s*[:=]\s*[A-Za-z0-9_\-]{16,}",
        r"(?i)\b(?:ghp|github_pat|sk)-[A-Za-z0-9_\-]{12,}",
        r"(?i)\bTTP\b",
        r"(?i)Translation and Transcription Project",
    ]
    for pattern in forbidden:
        require(not re.search(pattern, combined), f"forbidden public pattern: {pattern}")
    if account_name:
        require(not re.search(re.escape(account_name), combined, re.I), "account name leaked")

    print(
        json.dumps(
            {
                "result": "PASS_INDEPENDENT_EXPERT_REVIEW_REPLAY",
                "records": len(rows),
                "jsonl": {"bytes": len(public_jsonl), "sha256": digest(public_jsonl)},
                "markdown": {"bytes": len(public_markdown), "sha256": digest(public_markdown)},
                "receipt": {"bytes": len(public_receipt), "sha256": digest(public_receipt)},
                "mirrors_exact": True,
                "source_line_bindings_replayed": len(expected_rows),
                "privacy_and_metadata_scan": "PASS",
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
