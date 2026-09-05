#!/usr/bin/env python3
"""Seal the exact R37 dual-public closure and advance the live cursor once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


UPDATED = "2026-09-05T15:47:23+02:00"
VERSION = "2026-09-05-r37"
EXACT_DOI = "10.5281/zenodo.22315714"
EXACT_DOI_URL = "https://doi.org/10.5281/zenodo.22315714"
CONCEPT_DOI = "10.5281/zenodo.21921513"
CONCEPT_DOI_URL = "https://doi.org/10.5281/zenodo.21921513"
ZENODO_RECORD = "https://zenodo.org/records/22315714"
GITHUB = "https://github.com/KokunoYumeto/ega-ko"
GITHUB_RELEASE = (
    "https://github.com/KokunoYumeto/ega-ko/releases/tag/ega-ko-2026-09-05-r37"
)
GITHUB_COMMIT = "a7d387fda149b820fdd177ab7cfa33d65e967ce3"
GITHUB_PARENT = "db693fbea41f287e7e9ae8734b6bee6e0dab43e7"
GITHUB_TREE = "6b726824347ec6eccd58ccffb2d23319885a0428"
GITHUB_TAG = "ega-ko-2026-09-05-r37"
GITHUB_TAG_OBJECT = "92b420533f5fae13492a1c315d8ad68f44459acc"

GITHUB_RECEIPT = {
    "path": "github-receipt-r37.json",
    "bytes": 4178,
    "sha256": "4EBF06BBC433C18C7D875333BE45851B907198855C532E66435D25BC122D1429",
}
ZENODO_RECEIPT = {
    "path": "receipt-r37.json",
    "bytes": 2429,
    "sha256": "5C9420C0970F2D38185E00C3C3116FEE491F0CA9FEF8F558A50E5B9F3F06BD05",
}
PACKAGE_RECEIPT = {
    "path": "release/2026-09-05-r37/PACKAGE_RECEIPT.json",
    "bytes": 15338,
    "sha256": "9E0210434919164BB90D331A50A92100845BB8B7FED9B14EA873229889DE70A9",
}
PORTABLE_RECEIPT = {
    "path": "release/2026-09-05-r37/PORTABLE_BUILD_REPLAY.json",
    "bytes": 7812,
    "sha256": "3736C3BE48CC7BE10C936AE2FC2BFE0323379A07C778E3DF9A3B69DEA82C523D",
}

ARTIFACTS = [
    {
        "name": "00_EGA_ko_CUMULATIVE_READER.pdf",
        "bytes": 1479200,
        "sha256": "22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61",
    },
    {
        "name": "01_EGA_ko_EDITABLE_SOURCES.zip",
        "bytes": 350659,
        "sha256": "3A489C7782CAA63D743CD11C704404815AAFD4B162E4A6816140FE79F3DDDF92",
    },
    {
        "name": "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip",
        "bytes": 120035218,
        "sha256": "76826967CD4868E2CA3D98BEE4ACA32088423399947F5307DF4A01B6AFB66A97",
    },
    {
        "name": "03_EGA_ko_SHA256_MANIFEST.txt",
        "bytes": 343,
        "sha256": "5D4B0C61819B3EC2C297245A27989B6EC8B5F177D45E5DACB4EFE113B6EF9072",
    },
]

DECISION_ID = "AGKO-D186"
EVIDENCE_ID = "AGKO-E-R37-PUBLIC-CLOSURE-20260905"
HARD_ID = "AGKO-H161"
HARDENED_MARKER = "## 63. 2026-09-05 R37 public closure and R38 continuation"

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
PRIVATE_ALIAS_NAMES = ("cursor.json", "authority.json", "state.json")

PUBLIC_STATUS = "PASS_R37_PUBLIC_OPEN_DUAL_DESTINATION_AND_ANONYMOUS_BYTE_REPLAY"
NEXT_SOURCE = (
    "EGA II canonical source/ega2/ega2-1-fr.tex line1607, environment2.1.10; "
    "R38 translation candidate pending exact admission"
)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def compact_record(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def file_identity(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return path.stat().st_size, digest.hexdigest().upper()


def bytes_identity(data: bytes) -> tuple[int, str]:
    return len(data), hashlib.sha256(data).hexdigest().upper()


def require_identity(path: Path, identity: dict[str, Any]) -> None:
    actual = file_identity(path)
    expected = (identity["bytes"], identity["sha256"])
    if actual != expected:
        raise RuntimeError(f"identity mismatch for {path}: expected {expected}, got {actual}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise RuntimeError(f"blank JSONL line at {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict) or not isinstance(value.get("id"), str):
            raise RuntimeError(f"invalid JSONL record at {path}:{line_number}")
        rows.append(value)
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"duplicate existing JSONL id in {path}")
    return rows


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def verify_git_objects(repo: Path) -> None:
    if git(repo, "cat-file", "-t", GITHUB_COMMIT) != "commit":
        raise RuntimeError("R37 artifact object is not a commit")
    commit_lines = git(repo, "cat-file", "-p", GITHUB_COMMIT).splitlines()
    if f"tree {GITHUB_TREE}" not in commit_lines or f"parent {GITHUB_PARENT}" not in commit_lines:
        raise RuntimeError("R37 commit tree or parent mismatch")
    if git(repo, "cat-file", "-t", f"refs/tags/{GITHUB_TAG}") != "tag":
        raise RuntimeError("R37 tag is not annotated")
    if git(repo, "rev-parse", f"refs/tags/{GITHUB_TAG}") != GITHUB_TAG_OBJECT:
        raise RuntimeError("R37 annotated tag object mismatch")
    if git(repo, "rev-parse", f"refs/tags/{GITHUB_TAG}^{{}}") != GITHUB_COMMIT:
        raise RuntimeError("R37 annotated tag does not peel to the artifact commit")
    if git(repo, "rev-parse", "refs/remotes/origin/main") != GITHUB_COMMIT:
        raise RuntimeError("origin/main is not the exact R37 artifact commit before closure recording")


def normalized_assets(rows: list[dict[str, Any]], truth_key: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "name": row.get("name"),
                "bytes": row.get("bytes"),
                "sha256": row.get("sha256"),
                truth_key: row.get(truth_key),
            }
        )
    return result


def verify_receipts(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    github_path = repo / GITHUB_RECEIPT["path"]
    zenodo_path = repo / ZENODO_RECEIPT["path"]
    require_identity(github_path, GITHUB_RECEIPT)
    require_identity(zenodo_path, ZENODO_RECEIPT)
    github_receipt = load_json(github_path)
    zenodo_receipt = load_json(zenodo_path)

    expected_github = {
        "version": VERSION,
        "repository": GITHUB,
        "repository_public_active": True,
        "main_commit": GITHUB_COMMIT,
        "artifact_commit": GITHUB_COMMIT,
        "tag": GITHUB_TAG,
        "annotated_tag_object": GITHUB_TAG_OBJECT,
        "tag_peels_to_commit": GITHUB_COMMIT,
        "release_url": GITHUB_RELEASE,
        "credentials_present": False,
        "result": "PASS_GITHUB_PUBLICATION_AND_ANONYMOUS_BYTE_REPLAY",
    }
    for key, expected in expected_github.items():
        if github_receipt.get(key) != expected:
            raise RuntimeError(f"GitHub receipt field mismatch: {key}")
    expected_github_assets = [dict(item, anonymous_byte_identical=True) for item in ARTIFACTS]
    if normalized_assets(github_receipt.get("assets", []), "anonymous_byte_identical") != expected_github_assets:
        raise RuntimeError("GitHub receipt does not prove the exact four anonymous public assets")
    if github_receipt.get("evidence_zip_release_asset_only") is not True:
        raise RuntimeError("GitHub evidence ZIP topology is not explicitly bound")

    expected_zenodo = {
        "version": VERSION,
        "record_id": 22315714,
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "record_url": ZENODO_RECORD,
        "credentials_present": False,
        "result": "PASS_ZENODO_PUBLICATION_AND_ANONYMOUS_BYTE_REPLAY",
    }
    for key, expected in expected_zenodo.items():
        if zenodo_receipt.get(key) != expected:
            raise RuntimeError(f"Zenodo receipt field mismatch: {key}")
    expected_zenodo_assets = [dict(item, byte_identical=True) for item in ARTIFACTS]
    if normalized_assets(zenodo_receipt.get("anonymous_public_readback", []), "byte_identical") != expected_zenodo_assets:
        raise RuntimeError("Zenodo receipt does not prove the exact four anonymous public files")
    resolution = zenodo_receipt.get("doi_resolution", {})
    if resolution != {"status_code": 200, "final_url": ZENODO_RECORD}:
        raise RuntimeError("Zenodo exact DOI resolution is not bound to the public record")
    metadata = zenodo_receipt.get("metadata", {})
    if (
        metadata.get("access") != "public/open"
        or metadata.get("contributors") != ["AI typesetting & translation"]
        or metadata.get("excluded_prose_count") != 0
        or metadata.get("rights_scope_provenance_and_nonendorsement") != "PASS"
    ):
        raise RuntimeError("Zenodo metadata closure assertions are incomplete")
    return github_receipt, zenodo_receipt


def verify_release_artifacts(repo: Path) -> None:
    release = repo / "release" / VERSION
    for artifact in ARTIFACTS:
        require_identity(release / artifact["name"], artifact)
    require_identity(repo / PACKAGE_RECEIPT["path"], PACKAGE_RECEIPT)
    require_identity(repo / PORTABLE_RECEIPT["path"], PORTABLE_RECEIPT)
    package = load_json(repo / PACKAGE_RECEIPT["path"])
    portable = load_json(repo / PORTABLE_RECEIPT["path"])
    package_files = [
        {key: row.get(key) for key in ("name", "bytes", "sha256")}
        for row in package.get("files", [])
    ]
    if package_files != ARTIFACTS or package.get("result") != "PASS_R37_LOCAL_PACKAGE":
        raise RuntimeError("package receipt does not bind the exact four R37 artifacts")
    if portable.get("result") != "PASS_PORTABLE_BUILD_EXACT_TEXT_AND_SELECTED_RENDER_REPLAY":
        raise RuntimeError("portable replay did not pass")
    manifest = (release / "03_EGA_ko_SHA256_MANIFEST.txt").read_text(encoding="utf-8")
    expected_manifest = "filename\tbytes\tsha256\n" + "".join(
        f'{item["name"]}\t{item["bytes"]}\t{item["sha256"]}\n' for item in ARTIFACTS[:3]
    )
    if manifest != expected_manifest:
        raise RuntimeError("outer manifest content does not bind the first three public artifacts exactly")


def closure_control() -> dict[str, Any]:
    return {
        "schema": "ag-ko-public-closure-v3",
        "version": VERSION,
        "closed_at": UPDATED,
        "corpus": "EGA",
        "language": "ko-KR",
        "coverage": (
            "cumulative Korean EGA reader through EGA II2.1.9; canonical "
            "ega2-1-fr.tex lines1-1605; EGA II and the full EGA corpus remain incomplete"
        ),
        "github": {
            "repository": GITHUB,
            "artifact_commit": GITHUB_COMMIT,
            "artifact_parent": GITHUB_PARENT,
            "artifact_tree": GITHUB_TREE,
            "annotated_tag": GITHUB_TAG,
            "annotated_tag_object": GITHUB_TAG_OBJECT,
            "tag_peels_to_commit": GITHUB_COMMIT,
            "release": GITHUB_RELEASE,
            "assets": 4,
            "anonymous_byte_replay": "PASS",
            "evidence_zip_topology": "release asset only; not a repository blob",
            "receipt": GITHUB_RECEIPT,
        },
        "zenodo": {
            "record_id": 22315714,
            "exact_doi": EXACT_DOI,
            "exact_doi_url": EXACT_DOI_URL,
            "concept_doi": CONCEPT_DOI,
            "concept_doi_url": CONCEPT_DOI_URL,
            "record": ZENODO_RECORD,
            "same_lineage": True,
            "access": "public/open",
            "files": 4,
            "anonymous_byte_replay": "PASS",
            "receipt": ZENODO_RECEIPT,
        },
        "artifacts": ARTIFACTS,
        "total_publication_bytes": sum(item["bytes"] for item in ARTIFACTS),
        "release_validation": {
            "package": {**PACKAGE_RECEIPT, "result": "PASS_DETERMINISTIC_ARCHIVES"},
            "portable": {
                **PORTABLE_RECEIPT,
                "result": "PASS_EXACT_TEXT_AND_SELECTED_RENDER_REPLAY",
                "pdf_container_delta": "retained without content or correctness inference",
            },
        },
        "metadata": {
            "historical_creators": ["Grothendieck, Alexander", "Dieudonné, Jean"],
            "sole_project_contributor": "AI typesetting & translation",
            "umbrella_prose_mentions": 0,
            "rights_scope_provenance_and_nonendorsement": "PASS",
        },
        "public_link_evidence": {
            "github_release": "exact URL and four anonymous byte-identical assets bound by GitHub receipt",
            "zenodo_exact_doi": "status-200 public record resolution and four anonymous byte-identical files bound by Zenodo receipt",
            "zenodo_concept_doi": "existing Korean EGA concept lineage retained",
        },
        "ledger_records": {
            "decision": DECISION_ID,
            "evidence": EVIDENCE_ID,
            "hard": HARD_ID,
        },
        "continuation": {
            "ega_ii": "active and incomplete",
            "next_source": "canonical line1607 / environment2.1.10",
            "r38": "translation candidate pending exact admission",
            "order": "finish EGA II, then FGA; later EGA begins with the contiguous admitted sequence from EGA III",
            "sga": "outside active scope",
        },
        "credentials_present": False,
        "result": "PASS_PUBLICATION_AND_ANONYMOUS_DUAL_DESTINATION_BYTE_REPLAY",
    }


def closure_binding(control_bytes: bytes, public_path: bool) -> dict[str, Any]:
    size, digest = bytes_identity(control_bytes)
    return {
        "status": PUBLIC_STATUS,
        "version": VERSION,
        "control": {
            "path": (
                "evidence/controls/R37_PUBLIC_CLOSURE.json"
                if public_path
                else "controls/R37_PUBLIC_CLOSURE.json"
            ),
            "bytes": size,
            "sha256": digest,
            "private_public_mirrors_exact": True,
        },
        "reader": ARTIFACTS[0],
        "github": {
            "artifact_commit": GITHUB_COMMIT,
            "artifact_parent": GITHUB_PARENT,
            "annotated_tag": GITHUB_TAG,
            "release": GITHUB_RELEASE,
            "receipt": GITHUB_RECEIPT,
        },
        "zenodo": {
            "exact_doi": EXACT_DOI,
            "exact_doi_url": EXACT_DOI_URL,
            "concept_doi": CONCEPT_DOI,
            "concept_doi_url": CONCEPT_DOI_URL,
            "record": ZENODO_RECORD,
            "receipt": ZENODO_RECEIPT,
        },
        "public_artifacts": ARTIFACTS,
        "package": PACKAGE_RECEIPT,
        "portable_replay": PORTABLE_RECEIPT,
        "ega_ii_status": "active_incomplete",
        "next_source": "canonical line1607 / environment2.1.10",
        "r38_candidate_status": "pending_exact_admission",
    }


def decision_record() -> dict[str, Any]:
    return {
        "id": DECISION_ID,
        "time": UPDATED,
        "precision": "second",
        "kind": "r37_dual_public_closure_and_r38_continuation_gate",
        "scope": "Korean cumulative EGA R37 through EGA II2.1.9 / canonical lines1-1605",
        "choice": (
            "Close R37 only after the exact deterministic package and portable replay passed, the annotated "
            "GitHub tag peeled to artifact commit a7d387fda149b820fdd177ab7cfa33d65e967ce3 with its exact parent, "
            "and both GitHub and Zenodo receipts proved the same four public artifact identities by anonymous "
            "byte replay. Promote every current cursor/state/authority alias from local-pending to public R37, "
            "then continue at canonical line1607 with the R38 candidate still subject to exact admission."
        ),
        "alternatives": [
            "Leave live aliases at the superseded local-package/publication-pending phase",
            "Infer that the whole of EGA II is complete from one cumulative public checkpoint",
            "Rebuild or republish already verified R37 bytes before continuing translation",
        ],
        "rejected": (
            "Those alternatives would contradict public receipts, overclaim corpus coverage, or reopen sealed "
            "correct work without evidence."
        ),
        "evidence": [
            "github-receipt-r37.json 4178 bytes /4EBF06BBC433C18C7D875333BE45851B907198855C532E66435D25BC122D1429",
            "receipt-r37.json 2429 bytes /5C9420C0970F2D38185E00C3C3116FEE491F0CA9FEF8F558A50E5B9F3F06BD05",
            "four public identities: reader1479200/22EB1097..., sources350659/3A489C..., evidence120035218/76826967..., manifest343/5D4B0C...",
            "release/2026-09-05-r37/PACKAGE_RECEIPT.json and PORTABLE_BUILD_REPLAY.json",
            "controls/R37_PUBLIC_CLOSURE.json",
        ],
        "uncertainty": (
            "The portable PDF container differs from the strict reader while exact full extraction and selected "
            "renders agree; the receipt retains that container-only delta without a content inference. R38 has "
            "not yet passed admission, and EGA II remains incomplete."
        ),
        "consequence": (
            "R37 is publicly preserved in the existing GitHub and Zenodo Korean EGA lineages with four exact "
            "anonymous-replayed artifacts. The next executable translation step is R38 at canonical line1607."
        ),
        "review": "PASS_R37_DUAL_PUBLIC_CLOSURE",
        "next": "Validate and admit the R38 candidate from canonical line1607; do not claim or skip unadmitted content.",
    }


def evidence_record(control_bytes: bytes) -> dict[str, Any]:
    control_size, control_sha = bytes_identity(control_bytes)
    return {
        "id": EVIDENCE_ID,
        "time": UPDATED,
        "precision": "second",
        "kind": "r37_public_github_zenodo_anonymous_replay_closure",
        "coverage": (
            "EGA0_I and EGA I complete; EGA II programme complete and main text contiguous through2.1.9 / "
            "canonical lines1-1605; EGA II and the full corpus remain incomplete"
        ),
        "github": {
            "artifact_commit": GITHUB_COMMIT,
            "artifact_parent": GITHUB_PARENT,
            "annotated_tag": GITHUB_TAG,
            "annotated_tag_object": GITHUB_TAG_OBJECT,
            "release": GITHUB_RELEASE,
            "receipt": GITHUB_RECEIPT,
            "anonymous_byte_replay": "PASS_4_OF_4",
        },
        "zenodo": {
            "record_id": 22315714,
            "exact_doi": EXACT_DOI,
            "concept_doi": CONCEPT_DOI,
            "record": ZENODO_RECORD,
            "access": "public/open",
            "receipt": ZENODO_RECEIPT,
            "anonymous_byte_replay": "PASS_4_OF_4",
        },
        "artifacts": ARTIFACTS,
        "package": PACKAGE_RECEIPT,
        "portable_replay": PORTABLE_RECEIPT,
        "closure_control": {
            "private": "controls/R37_PUBLIC_CLOSURE.json",
            "public": "evidence/controls/R37_PUBLIC_CLOSURE.json",
            "bytes": control_size,
            "sha256": control_sha,
            "mirrors_exact": True,
        },
        "metadata": {
            "creators": ["Grothendieck, Alexander", "Dieudonné, Jean"],
            "sole_project_contributor": "AI typesetting & translation",
            "rights_scope_provenance_and_nonendorsement": "PASS",
            "excluded_prose_count": 0,
        },
        "result": PUBLIC_STATUS,
        "next": NEXT_SOURCE,
    }


def hard_record() -> dict[str, Any]:
    return {
        "id": HARD_ID,
        "time": UPDATED,
        "precision": "second",
        "status": "resolved_r37_public_closure_and_controlling_r38_admission_boundary",
        "scope": "R37 release closure and the next Korean EGA II source boundary",
        "locator": (
            "GitHub artifact commit/tag/release; Zenodo exact22315714/concept21921513; "
            "github-receipt-r37.json; receipt-r37.json; controls/R37_PUBLIC_CLOSURE.json"
        ),
        "symptom": (
            "The public repositories had already closed R37 while current live aliases still described R37 as "
            "local and pending. The next source begins at line1607, but the R38 candidate is not admitted merely "
            "because source preparation or drafting exists."
        ),
        "cause_evidence": (
            "The GitHub receipt binds artifact commit a7d387f... and four anonymous assets; the Zenodo receipt "
            "binds public/open exact DOI22315714 in concept21921513 and the identical four files. Both local "
            "receipts and every release artifact match their required byte counts and SHA-256 identities."
        ),
        "resolution": (
            "Create identical private/public R37 closure controls, append this closure once to both ledger sets, "
            "promote all current aliases to the verified public state, preserve all prior immutable R36 history, "
            "and point the active cursor to line1607 with R38 pending exact admission."
        ),
        "tests": (
            "Local commit type/tree/parent, annotated tag object and peel, origin/main, receipt identity/content, "
            "package and portable receipts, four release files, outer manifest, JSON/JSONL uniqueness, control "
            "mirror equality and all current alias phases PASS."
        ),
        "residual_risk": (
            "No R37 publication gate remains. The portable container-only delta remains recorded without content "
            "inference. R38 remains unadmitted and EGA II remains incomplete."
        ),
        "recurrence": (
            "After every publication, bind exact public bytes and repository topology before promoting live aliases; "
            "advance only to the next source-bounded candidate and require its independent admission gate."
        ),
        "related": [DECISION_ID, EVIDENCE_ID, "AGKO-D185", "AGKO-H160"],
    }


def update_public_alias(name: str, data: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    data["updated"] = UPDATED
    data["version"] = VERSION
    data["publication_phase"] = "public_open_dual_destination_anonymous_byte_replay_pass"
    if "snapshot_phase" in data:
        data["snapshot_phase"] = "public_open_dual_destination_anonymous_byte_replay_pass"
    data["current_public_checkpoint"] = (
        "r37 / exact DOI10.5281/zenodo.22315714 / GitHub release ega-ko-2026-09-05-r37; "
        "four artifacts at both destinations passed anonymous byte replay"
    )
    data["publication_evidence_rule"] = (
        "R37 public status is proved only by the two exact hash-bound receipts and mirrored closure control; "
        "EGA II remains incomplete."
    )
    data["public_r37"] = binding
    data["next_source"] = NEXT_SOURCE
    data["r38_candidate_status"] = "PENDING_EXACT_ADMISSION; no R38 build or publication claim"

    if name in {"STATE.json", "PROGRAM_STATE.json"}:
        data["release_gates"] = {
            "translation": "PASS",
            "build": "PASS",
            "pdf_qa": "PASS",
            "package": "PASS",
            "portable_replay": "PASS",
            "github_publication_and_anonymous_replay": "PASS",
            "zenodo_publication_and_anonymous_replay": "PASS",
        }
        data.setdefault("qa", {})["portable"] = (
            "PASS exact full extraction and selected frozen-render replay; container-only delta retained without "
            "content inference; release/2026-09-05-r37/PORTABLE_BUILD_REPLAY.json"
        )
        data["result"] = PUBLIC_STATUS
    elif name == "QA_STATE.json":
        data.setdefault("qa", {})["portable"] = (
            "PASS exact full extraction and selected frozen-render replay; container-only delta retained without "
            "content inference"
        )
        data["result"] = PUBLIC_STATUS
    elif name == "PROGRAM_AUTHORITY.json":
        data["publication"] = {
            "status": PUBLIC_STATUS,
            "exact_version_doi": EXACT_DOI,
            "record_id": 22315714,
            "concept_doi": CONCEPT_DOI,
            "prior_public_doi": "10.5281/zenodo.22217711",
            "github": GITHUB,
            "github_artifact_commit": GITHUB_COMMIT,
            "annotated_tag": GITHUB_TAG,
            "release": GITHUB_RELEASE,
            "active_destinations": ["Zenodo", "GitHub"],
            "closure": binding["control"],
        }
    elif name == "DATACITE_RELATIONS.json":
        data["release_state"] = "public_open_dual_destination_anonymous_byte_replay_pass"
        data["publication_status"] = PUBLIC_STATUS
        data["public_record_url"] = ZENODO_RECORD
        data["github_release"] = GITHUB_RELEASE
    return data


def update_private_cursor(data: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    data["updated"] = UPDATED
    data["next"] = (
        "R37 public closure is complete. Validate and admit the R38 translation candidate beginning at canonical "
        "line1607 / environment2.1.10, then continue EGA II contiguously without reopening sealed R37 bytes."
    )
    data["last_public_checkpoint"] = (
        "r37 / exact DOI10.5281/zenodo.22315714 / GitHub release ega-ko-2026-09-05-r37; "
        "dual anonymous four-artifact replay PASS"
    )
    data.pop("candidate_reader", None)
    data.pop("candidate_exact_doi", None)
    data.pop("candidate_record_id", None)
    data["public_reader"] = ARTIFACTS[0]
    data["public_exact_doi"] = EXACT_DOI
    data["public_record_id"] = 22315714
    data["local_status"] = PUBLIC_STATUS
    data["public_r37"] = binding
    data["r38_candidate_status"] = "PENDING_EXACT_ADMISSION"
    return data


def update_private_authority(data: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    data["updated"] = UPDATED
    data.setdefault("ega_ii", {})["next"] = (
        "source/ega2/ega2-1-fr.tex line1607, environment2.1.10; R38 candidate pending exact admission"
    )
    data["ega_ii"]["status"] = (
        "canonical five-input packet present; Korean front/programme complete; main input admitted "
        "contiguously through lines1-1605 /2.1.9; EGA II active and incomplete; next admission line1607"
    )
    data["publication_lineage"] = {
        "zenodo_concept_doi": CONCEPT_DOI,
        "exact_version_doi": EXACT_DOI,
        "record_id": 22315714,
        "prior_public_exact_doi": "10.5281/zenodo.22217711",
        "github": GITHUB,
        "github_artifact_commit": GITHUB_COMMIT,
        "annotated_tag": GITHUB_TAG,
        "release": GITHUB_RELEASE,
        "active_destinations": ["Zenodo", "GitHub"],
        "status": PUBLIC_STATUS,
        "closure": binding["control"],
    }
    return data


def update_private_state(data: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    data["updated"] = UPDATED
    completed = data.setdefault("completed", {})
    completed["latest_public_reader"] = (
        "r37:238pages/1479200B/22EB1097A3BD0B9DDAEF5C64D10D06561DFADDBA5FD08B80CE417C85FBF79F61"
    )
    completed["latest_public_scope"] = (
        "r37 public through EGA II2.1.9 / canonical lines1-1605; EGA II and the full corpus remain incomplete"
    )
    completed["qa"] = (
        "PASS_PUBLIC_R37: translation, strict build, PDF QA, deterministic package, portable exact-text/render "
        "replay, and dual anonymous public-byte replay"
    )
    completed["zenodo"] = (
        "PASS_PUBLIC_R37: exact22315714/concept21921513/public-open; four-file anonymous replay exact; "
        "receipt-r37.json2429/5C9420C0970F2D38185E00C3C3116FEE491F0CA9FEF8F558A50E5B9F3F06BD05"
    )
    completed["github"] = (
        "PASS_PUBLIC_R37: artifact a7d387fda149b820fdd177ab7cfa33d65e967ce3; annotated release tag "
        "ega-ko-2026-09-05-r37; four assets anonymous-byte exact; github-receipt-r37.json4178/"
        "4EBF06BBC433C18C7D875333BE45851B907198855C532E66435D25BC122D1429"
    )
    receipts = completed.setdefault("receipts", [])
    for receipt in (
        "pub/ega-ko/receipt-r37.json",
        "pub/ega-ko/github-receipt-r37.json",
        "pub/ega-ko/release/2026-09-05-r37/PACKAGE_RECEIPT.json",
        "pub/ega-ko/release/2026-09-05-r37/PORTABLE_BUILD_REPLAY.json",
        "controls/R37_PUBLIC_CLOSURE.json",
    ):
        if receipt not in receipts:
            receipts.append(receipt)
    data["public_r37"] = binding
    candidate = data.setdefault("candidate_r37", {})
    candidate["status"] = "PROMOTED_TO_PUBLIC_R37_DUAL_ANONYMOUS_REPLAY_PASS"
    candidate["public_closure"] = binding["control"]
    candidate["next"] = "closed; proceed to R38 candidate admission at canonical line1607"
    active = data.setdefault("active", {})
    active["publication"] = binding
    if isinstance(active.get("qa"), dict):
        active["qa"]["portable"] = (
            "PASS exact full extraction and selected frozen-render replay; container-only delta retained "
            "without content inference"
        )
    active["next_source"] = "source/ega2/ega2-1-fr.tex line1607; environment2.1.10"
    active["next_target"] = (
        "R38 translation candidate pending exact source/formula/terminology admission; repair if needed, "
        "then integrate once without reopening sealed R37 bytes"
    )
    active["gate"] = (
        "EGA II remains active and incomplete. Preserve exact formulas, labels, references, environments and "
        "oldpage markers; route possible French corrections; admit R38 before any build or publication claim."
    )
    data["next_executable_action"] = (
        "Validate and admit the R38 translation candidate beginning at canonical line1607 / environment2.1.10, "
        "then continue EGA II contiguously."
    )
    data["continuation_audit"] = {
        "classification": "progress",
        "current_progress": (
            "R37 deterministic package, portable replay, GitHub and Zenodo publication, and anonymous "
            "four-artifact byte replays all PASS; R38 candidate admission is next."
        ),
    }
    return data


def hardened_section() -> str:
    artifacts = "; ".join(
        f'`{item["name"]}` {item["bytes"]:,} bytes / `{item["sha256"]}`' for item in ARTIFACTS
    )
    return f"""

{HARDENED_MARKER}

This section supersedes only the earlier current-phase wording; every R36 receipt and historical record remains immutable. R37 is publicly closed in the existing Korean EGA lineages. GitHub binds artifact commit `{GITHUB_COMMIT}` to parent `{GITHUB_PARENT}`; annotated tag `{GITHUB_TAG}` (object `{GITHUB_TAG_OBJECT}`) peels to that commit, and the public release is `{GITHUB_RELEASE}`. Its receipt is 4,178 bytes / `{GITHUB_RECEIPT['sha256']}`. Zenodo exact DOI `{EXACT_DOI_URL}` remains within concept `{CONCEPT_DOI_URL}` at `{ZENODO_RECORD}`; its receipt is 2,429 bytes / `{ZENODO_RECEIPT['sha256']}`. Both receipts prove four anonymous byte-identical public artifacts.

The exact public set is: {artifacts}. The deterministic package receipt is 15,338 bytes / `{PACKAGE_RECEIPT['sha256']}`; the portable replay receipt is 7,812 bytes / `{PORTABLE_RECEIPT['sha256']}`. The portable PDF container-only delta is retained without a content, correctness, completion or publication inference because both full extracts and the selected frozen renders replay exactly. The identical private/public closure control is `R37_PUBLIC_CLOSURE.json`.

No R37 publication gate remains. EGA II and the full EGA corpus remain incomplete. Continue at canonical `source/ega2/ega2-1-fr.tex` line 1607, environment 2.1.10; the R38 translation candidate is pending exact source, formula, terminology and mirror admission. The production order remains finish EGA II, then FGA; only afterward may the contiguous admitted later-EGA sequence begin with EGA III. SGA remains outside active scope.
"""


def verify_fresh_ids(private: Path, repo: Path) -> None:
    evidence = repo / "evidence"
    ledgers = {
        "decision": [private / "decisions.jsonl", evidence / "decisions.jsonl"],
        "evidence": [private / "evidence.jsonl", evidence / "evidence.jsonl"],
        "hard": [private / "hard.jsonl", evidence / "hard.jsonl"],
    }
    for paths in ledgers.values():
        for path in paths:
            load_jsonl(path)
    decision_numbers: list[int] = []
    hard_numbers: list[int] = []
    for path in ledgers["decision"]:
        for row in load_jsonl(path):
            identifier = row["id"]
            if identifier.startswith("AGKO-D") and identifier[6:].isdigit():
                decision_numbers.append(int(identifier[6:]))
    for path in ledgers["hard"]:
        for row in load_jsonl(path):
            identifier = row["id"]
            if identifier.startswith("AGKO-H") and identifier[6:].isdigit():
                hard_numbers.append(int(identifier[6:]))
    if max(decision_numbers) != 185 or max(hard_numbers) != 160:
        raise RuntimeError("fresh next ledger IDs are no longer D186 and H161")
    for path in ledgers["decision"]:
        if any(row["id"] == DECISION_ID for row in load_jsonl(path)):
            raise RuntimeError(f"closure decision already exists in {path}")
    for path in ledgers["evidence"]:
        if any(row["id"] == EVIDENCE_ID for row in load_jsonl(path)):
            raise RuntimeError(f"closure evidence already exists in {path}")
    for path in ledgers["hard"]:
        if any(row["id"] == HARD_ID for row in load_jsonl(path)):
            raise RuntimeError(f"closure hard record already exists in {path}")


def append_record_bytes(path: Path, record: dict[str, Any]) -> bytes:
    existing = path.read_bytes()
    if not existing.endswith(b"\n"):
        raise RuntimeError(f"JSONL lacks terminal LF: {path}")
    return existing + compact_record(record)


def atomic_replace_all(outputs: dict[Path, bytes]) -> None:
    staged: list[tuple[Path, Path]] = []
    try:
        for path in sorted(outputs, key=lambda item: str(item).casefold()):
            temporary = path.with_name(path.name + ".r37-closure-tmp")
            if temporary.exists():
                raise RuntimeError(f"stale closure temporary file: {temporary}")
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


def verify_output(
    private: Path,
    repo: Path,
    output_paths: list[Path],
    control_bytes: bytes,
) -> None:
    private_control = private / "controls" / "R37_PUBLIC_CLOSURE.json"
    public_control = repo / "evidence" / "controls" / "R37_PUBLIC_CLOSURE.json"
    if private_control.read_bytes() != control_bytes or public_control.read_bytes() != control_bytes:
        raise RuntimeError("private/public closure controls are not exact mirrors")

    ledger_checks = (
        ("decisions.jsonl", DECISION_ID),
        ("evidence.jsonl", EVIDENCE_ID),
        ("hard.jsonl", HARD_ID),
    )
    for name, identifier in ledger_checks:
        for root in (private, repo / "evidence"):
            rows = load_jsonl(root / name)
            if sum(row["id"] == identifier for row in rows) != 1:
                raise RuntimeError(f"closure id {identifier} is not present exactly once in {root / name}")

    for name in PUBLIC_ALIAS_NAMES:
        data = load_json(repo / "evidence" / name)
        if data.get("public_r37", {}).get("status") != PUBLIC_STATUS:
            raise RuntimeError(f"public alias does not expose public R37: {name}")
        if data.get("r38_candidate_status") != "PENDING_EXACT_ADMISSION; no R38 build or publication claim":
            raise RuntimeError(f"public alias lacks the exact R38 admission boundary: {name}")
    private_cursor = load_json(private / "cursor.json")
    private_authority = load_json(private / "authority.json")
    private_state = load_json(private / "state.json")
    if private_cursor.get("public_r37", {}).get("status") != PUBLIC_STATUS:
        raise RuntimeError("private cursor does not expose public R37")
    if private_authority.get("publication_lineage", {}).get("status") != PUBLIC_STATUS:
        raise RuntimeError("private authority does not expose public R37")
    if private_state.get("public_r37", {}).get("status") != PUBLIC_STATUS:
        raise RuntimeError("private state does not expose public R37")
    if private_state.get("candidate_r37", {}).get("status") != "PROMOTED_TO_PUBLIC_R37_DUAL_ANONYMOUS_REPLAY_PASS":
        raise RuntimeError("private state retains a stale R37 candidate phase")

    for path in (private / "HARDENED.md", repo / "evidence" / "HARDENED.md"):
        if path.read_text(encoding="utf-8").count(HARDENED_MARKER) != 1:
            raise RuntimeError(f"R37 closure hardening section count is not one in {path}")

    blocked = ("Fig" + "share", "T" + "TP", "Translation and Transcription " + "Project")
    inserted_paths = [
        private_control,
        public_control,
        private / "cursor.json",
        private / "authority.json",
        private / "state.json",
        *[repo / "evidence" / name for name in PUBLIC_ALIAS_NAMES],
    ]
    for path in inserted_paths:
        text = path.read_text(encoding="utf-8")
        for token in blocked:
            if token in text:
                raise RuntimeError(f"excluded current-metadata token in {path}")

    report = {
        "result": "PASS_R37_PUBLIC_CLOSURE_STATE_AND_LEDGER_REFRESH",
        "records": {"decision": DECISION_ID, "evidence": EVIDENCE_ID, "hard": HARD_ID},
        "changed": [
            {"path": str(path), "bytes": file_identity(path)[0], "sha256": file_identity(path)[1]}
            for path in sorted(output_paths, key=lambda item: str(item).casefold())
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    private = args.private_root.resolve()
    repo = args.repo.resolve()
    evidence = repo / "evidence"

    private_control = private / "controls" / "R37_PUBLIC_CLOSURE.json"
    public_control = evidence / "controls" / "R37_PUBLIC_CLOSURE.json"
    if private_control.exists() or public_control.exists():
        raise RuntimeError("R37 closure control already exists; this helper is one-shot")
    for path in (private / "HARDENED.md", evidence / "HARDENED.md"):
        if HARDENED_MARKER in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"R37 closure hardening section already exists in {path}")

    verify_git_objects(repo)
    verify_release_artifacts(repo)
    verify_receipts(repo)
    verify_fresh_ids(private, repo)

    control_bytes = json_bytes(closure_control())
    public_binding = closure_binding(control_bytes, True)
    private_binding = closure_binding(control_bytes, False)
    decision = decision_record()
    evidence_record_value = evidence_record(control_bytes)
    hard = hard_record()

    outputs: dict[Path, bytes] = {
        private_control: control_bytes,
        public_control: control_bytes,
        private / "decisions.jsonl": append_record_bytes(private / "decisions.jsonl", decision),
        evidence / "decisions.jsonl": append_record_bytes(evidence / "decisions.jsonl", decision),
        private / "evidence.jsonl": append_record_bytes(private / "evidence.jsonl", evidence_record_value),
        evidence / "evidence.jsonl": append_record_bytes(evidence / "evidence.jsonl", evidence_record_value),
        private / "hard.jsonl": append_record_bytes(private / "hard.jsonl", hard),
        evidence / "hard.jsonl": append_record_bytes(evidence / "hard.jsonl", hard),
    }
    for name in PUBLIC_ALIAS_NAMES:
        path = evidence / name
        outputs[path] = json_bytes(update_public_alias(name, load_json(path), public_binding))
    outputs[private / "cursor.json"] = json_bytes(
        update_private_cursor(load_json(private / "cursor.json"), private_binding)
    )
    outputs[private / "authority.json"] = json_bytes(
        update_private_authority(load_json(private / "authority.json"), private_binding)
    )
    outputs[private / "state.json"] = json_bytes(
        update_private_state(load_json(private / "state.json"), private_binding)
    )
    section = hardened_section()
    for path in (private / "HARDENED.md", evidence / "HARDENED.md"):
        outputs[path] = (path.read_text(encoding="utf-8").rstrip() + section).encode("utf-8")

    blocked = ("Fig" + "share", "T" + "TP", "Translation and Transcription " + "Project")
    for value in (control_bytes, compact_record(decision), compact_record(evidence_record_value), compact_record(hard), section.encode("utf-8")):
        text = value.decode("utf-8")
        for token in blocked:
            if token in text:
                raise RuntimeError("excluded token in new R37 closure content")
    if "EGA II and the full EGA corpus remain incomplete" not in control_bytes.decode("utf-8"):
        raise RuntimeError("closure control lacks the explicit incomplete-corpus boundary")

    atomic_replace_all(outputs)
    verify_output(private, repo, list(outputs), control_bytes)


if __name__ == "__main__":
    main()
