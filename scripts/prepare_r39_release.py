#!/usr/bin/env python3
"""Prepare immutable, sanitized R39 release evidence transactionally.

The build receipt is a pre-state-seal object. Once the exact build/QA state
seal exists this helper becomes verification-only and performs no mutation.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


VERSION = "2026-09-06-r39"
EXACT_DOI = "10.5281/zenodo.22416007"
CONCEPT_DOI = "10.5281/zenodo.21921513"
TARGET = (84_274, "59D07958D5CE1765F4901202CE97B3AC6257F6DC6C0D114C37B314C6A6EB1943")
MANIFEST = (16_281, "1F414A48D02837E9999205DC7E1B9468016A687605F5594DADAEDA4616EB21FB")
READER = (1_491_216, "AB24AAA5A4FBEAC3528892EF998C93276BF6DD38E7520C5F18A316E3FBAEAA6F")
STATE_SEAL_NAME = "R39_BUILD_QA_STATE_SEAL.json"
STATE_SEAL = (11_185, "5924A67C251E7583F4973428D2DAD95BA6D56B0DAECAE3FE77B52A2275270DDD")
TRANSACTION_MUTEX = "Global\\InterlanguageAGKOR39BuildQAStateSealV1"
MAX_INPUT_BYTES = 16 * 1024 * 1024

# Complete immutable set used by the already-sealed build receipt. The later
# state seal and DOI-reservation control are deliberately not members.
PRE_STATE_SEAL_CONTROLS = (
    "R39_AUTHORITY_COMMENT_RESEAL.json",
    "R39_CANONICAL_PREFIX_REBASE.json",
    "R39_CURRENT_AUTHORITY_VALIDATOR.json",
    "R39_IDEAL_TERMINOLOGY_RESEAL.json",
    "R39_KOREAN_WORDING_RESEAL.json",
    "R39_PDF_QA.json",
    "R39_PDF_QA_PRE_TERMINOLOGY.json",
    "R39_R43_SEQUENTIAL_CHAIN_REBASE_20260906.json",
    "R39_STRICT_BUILD.json",
    "R39_STRICT_BUILD_PRE_TERMINOLOGY.json",
    "R39_TRANSLATION_ADMISSION.json",
    "R39_TRANSLATION_INTEGRATION.json",
    "R39_VISUAL_QA_PREPARATION.json",
    "R39_VISUAL_QA_PREPARATION_PRE_TERMINOLOGY.json",
)

_PROFILE_PATH = re.compile(
    r"(?:[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\\/\s]+|"
    r"/(?:home|Users)/[^/\s]+)",
    re.I,
)
_CREDENTIAL_MATERIAL = re.compile(
    r"(?:\bBearer\s+[A-Za-z0-9._~-]{12,}|"
    r"[\"'](?:access[_-]?token|api[_-]?key|client[_-]?secret|password)[\"']\s*:)",
    re.I,
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_regular(path: Path, display: str, maximum: int = MAX_INPUT_BYTES) -> bytes:
    if path.is_symlink() or not path.is_file():
        fail(f"missing, non-regular, or symlink file: {display}")
    size = path.stat().st_size
    if size < 0 or size > maximum:
        fail(f"file exceeds the bounded read limit: {display}")
    with path.open("rb") as stream:
        data = stream.read(size + 1)
        if len(data) != size or stream.read(1):
            fail(f"file changed during bounded read: {display}")
    return data


def sha(path: Path) -> str:
    return sha_bytes(read_regular(path, str(path)))


def ident(path: Path, display: str) -> dict[str, Any]:
    return ident_bytes(read_regular(path, display), display)


def ident_bytes(data: bytes, display: str) -> dict[str, Any]:
    return {"path": display, "bytes": len(data), "sha256": sha_bytes(data)}


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_regular(path, path.name).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"malformed JSON object: {path.name}") from exc
    if not isinstance(value, dict):
        fail(f"JSON root is not an object: {path.name}")
    return value


def identity_matches(path: Path, expected: tuple[int, str], display: str) -> None:
    data = read_regular(path, display)
    if (len(data), sha_bytes(data)) != expected:
        fail(f"exact identity drift: {display}")


def replace_casefold(text: str, source: Path, replacement: str) -> str:
    rendered = str(source)
    for variant in sorted({rendered, rendered.replace("\\", "/")}, key=len, reverse=True):
        text = re.sub(re.escape(variant), lambda _: replacement, text, flags=re.I)
    return text


def reject_private_material(text: str, operation: str, roots: tuple[Path, ...]) -> None:
    for root in roots:
        rendered = str(root)
        variants = {rendered, rendered.replace("\\", "/")}
        if any(re.search(re.escape(item), text, flags=re.I) for item in variants):
            fail(f"{operation}: exact local root remains")
    if _PROFILE_PATH.search(text):
        fail(f"{operation}: local profile path remains")
    if _CREDENTIAL_MATERIAL.search(text):
        fail(f"{operation}: possible credential material remains")


def sanitize_log(raw: str, repo: Path, private_root: Path, canonical_root: Path) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    roots = (
        (repo, "[KOREAN_REPO_ROOT]"),
        (private_root, "[PRIVATE_WORK_ROOT]"),
        (canonical_root, "[CANONICAL_ROOT]"),
    )
    for source, replacement in roots:
        text = replace_casefold(text, source, replacement)
    text = re.sub(
        r"[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\\/\s]+",
        "[USER_PROFILE]",
        text,
        flags=re.I,
    )
    text = re.sub(r"/(?:home|Users)/[^/\s]+", "[USER_PROFILE]", text, flags=re.I)
    reject_private_material(text, "sanitized build log", tuple(source for source, _ in roots))
    return text


@contextmanager
def transaction_mutex() -> Iterator[bool]:
    if os.name != "nt":
        fail("Windows R39 release-evidence transaction mutex required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    kernel.WaitForSingleObject.restype = ctypes.c_uint
    kernel.ReleaseMutex.argtypes = [ctypes.c_void_p]
    kernel.ReleaseMutex.restype = ctypes.c_int
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    handle = kernel.CreateMutexW(None, 0, TRANSACTION_MUTEX)
    if not handle:
        fail("R39 release-evidence mutex creation failed")
    wait = kernel.WaitForSingleObject(handle, 30_000)
    if wait not in (0, 0x80):
        kernel.CloseHandle(handle)
        fail("R39 release-evidence mutex acquisition timeout")
    try:
        yield wait == 0x80
    finally:
        released = kernel.ReleaseMutex(handle)
        closed = kernel.CloseHandle(handle)
        if not released or not closed:
            fail("R39 release-evidence mutex release failed")


def fsync_parent(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def staged_file(path: Path, data: bytes) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".r39-stage", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    if read_regular(temporary, f"staged {path.name}") != data:
        temporary.unlink(missing_ok=True)
        fail(f"staged release-evidence bytes differ: {path.name}")
    return temporary


def current_bytes(path: Path) -> bytes | None:
    if not path.exists() and not path.is_symlink():
        return None
    return read_regular(path, path.name)


def atomic_mirror(rows: list[tuple[Path, bytes]]) -> str:
    paths = [path for path, _ in rows]
    if len(paths) != len(set(paths)):
        fail("release-evidence transaction contains duplicate destinations")
    preimages: dict[Path, bytes | None] = {}
    for path, _ in rows:
        if path.parent.is_symlink() or not path.parent.is_dir():
            fail(f"unsafe release-evidence parent: {path.parent}")
        if path.is_symlink() or (path.exists() and not path.is_file()):
            fail(f"unsafe release-evidence destination: {path.name}")
        preimages[path] = current_bytes(path)
    if all(preimages[path] == data for path, data in rows):
        return "UNCHANGED_EXACT"

    staged: dict[Path, Path] = {}
    try:
        for path, data in rows:
            staged[path] = staged_file(path, data)
    except Exception:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
        raise
    replaced: list[Path] = []
    try:
        for path in paths:
            if current_bytes(path) != preimages[path]:
                fail(f"release-evidence preimage changed concurrently: {path.name}")
        for path, data in rows:
            os.replace(staged[path], path)
            replaced.append(path)
            fsync_parent(path)
            if read_regular(path, path.name) != data:
                fail(f"release-evidence postimage verification failed: {path.name}")
    except Exception as exc:
        row_map = dict(rows)
        rollback_errors: list[str] = []
        for path in reversed(replaced):
            try:
                if current_bytes(path) != row_map[path]:
                    raise RuntimeError("postimage changed before rollback")
                before = preimages[path]
                if before is None:
                    path.unlink(missing_ok=True)
                    fsync_parent(path)
                else:
                    rollback = staged_file(path, before)
                    os.replace(rollback, path)
                    fsync_parent(path)
                    if read_regular(path, path.name) != before:
                        raise RuntimeError("rollback replay differs")
            except Exception as rollback_exc:  # pragma: no cover - catastrophic path
                rollback_errors.append(f"{path.name}: {rollback_exc}")
        if rollback_errors:
            fail("release-evidence rollback failed: " + "; ".join(rollback_errors))
        raise RuntimeError("release-evidence transaction failed and was rolled back") from exc
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
    return "ATOMIC_REPLACE_PASS"


def validate_control_mirrors(controls: Path, private_controls: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in PRE_STATE_SEAL_CONTROLS:
        public = read_regular(controls / name, f"public {name}")
        private = read_regular(private_controls / name, f"private {name}")
        if public != private:
            fail(f"private/public pre-state-seal control differs: {name}")
        rows.append(ident_bytes(public, f"evidence/controls/{name}"))
    return rows


def validate_seal_pair(controls: Path, private_controls: Path) -> dict[str, Any] | None:
    public_path = controls / STATE_SEAL_NAME
    private_path = private_controls / STATE_SEAL_NAME
    present = [path.exists() or path.is_symlink() for path in (public_path, private_path)]
    if not any(present):
        return None
    if present != [True, True]:
        fail("R39 state seal is present in only one mirror")
    public = read_regular(public_path, f"public {STATE_SEAL_NAME}")
    private = read_regular(private_path, f"private {STATE_SEAL_NAME}")
    if public != private or (len(public), sha_bytes(public)) != STATE_SEAL:
        fail("R39 state-seal mirror or identity drift")
    seal = load(public_path)
    if (
        seal.get("schema") != "agko-r39-build-qa-state-seal-v1"
        or seal.get("id") != "AGKO-R39-BUILD-QA-STATE-SEAL"
        or seal.get("version") != VERSION
        or seal.get("result") != "PASS_R39_BUILD_PDF_QA_STATE_SEAL"
        or seal.get("gates", {}).get("release_evidence") != "PASS"
        or seal.get("gates", {}).get("package") != "PENDING"
    ):
        fail("R39 state seal is not the exact pre-package PASS state")
    return seal


def validate_receipt_rows(receipt: dict[str, Any], repo: Path, private_root: Path) -> None:
    if (
        receipt.get("schema") != "ag-ko-r39-build-receipt-v1"
        or receipt.get("version") != VERSION
        or receipt.get("exact_doi") != EXACT_DOI
        or receipt.get("concept_doi") != CONCEPT_DOI
        or receipt.get("result") != "PASS_R39_RELEASE_EVIDENCE"
    ):
        fail("sealed build receipt identity/status drift")
    expected_controls = [f"evidence/controls/{name}" for name in PRE_STATE_SEAL_CONTROLS]
    control_rows = receipt.get("mirrored_r39_controls")
    if (
        not isinstance(control_rows, list)
        or len(control_rows) != len(expected_controls)
        or [row.get("path") for row in control_rows if isinstance(row, dict)] != expected_controls
    ):
        fail("sealed build receipt pre-state-seal control inventory drift")
    for row in control_rows:
        path = repo / str(row["path"])
        if ident(path, str(row["path"])) != row:
            fail(f"sealed build receipt control identity drift: {row['path']}")
        private = private_root / "controls" / Path(str(row["path"])).name
        if read_regular(private, private.name) != read_regular(path, str(row["path"])):
            fail(f"sealed private/public control drift: {row['path']}")

    build = receipt.get("build")
    if not isinstance(build, dict):
        fail("sealed build receipt build section drift")
    raw_log = build.get("raw_log")
    logs = build.get("sanitized_logs")
    extractions = receipt.get("extractions")
    if not isinstance(raw_log, dict) or not isinstance(logs, list) or not isinstance(extractions, list):
        fail("sealed build receipt file inventory drift")
    for row in [raw_log, *logs, *extractions]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            fail("sealed build receipt contains malformed file identity")
        if ident(repo / row["path"], row["path"]) != row:
            fail(f"sealed build receipt file identity drift: {row['path']}")


def verify_sealed_outputs(
    seal: dict[str, Any], repo: Path, private_root: Path, canonical_root: Path
) -> None:
    controls = repo / "evidence" / "controls"
    private_controls = private_root / "controls"
    public_receipt = repo / "evidence" / "BUILD_RECEIPT.json"
    private_receipt = private_controls / "R39_BUILD_RECEIPT.json"
    public = read_regular(public_receipt, "public sealed build receipt")
    private = read_regular(private_receipt, "private sealed build receipt")
    expected = seal.get("controls", {}).get("build_receipt")
    observed = {"bytes": len(public), "sha256": sha_bytes(public)}
    if (
        public != private
        or not isinstance(expected, dict)
        or {"bytes": expected.get("bytes"), "sha256": expected.get("sha256")} != observed
    ):
        fail("sealed build receipt mirrors or state-seal binding drift")
    receipt = json.loads(public.decode("utf-8"))
    if not isinstance(receipt, dict):
        fail("sealed build receipt root drift")
    validate_receipt_rows(receipt, repo, private_root)
    validate_control_mirrors(controls, private_controls)

    reader_row = {**ident(repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf", "reader/00_EGA_ko_CUMULATIVE_READER.pdf"), "pages": 240}
    if receipt.get("reader") != reader_row or seal.get("reader") != {
        "name": "00_EGA_ko_CUMULATIVE_READER.pdf",
        **reader_row,
    }:
        fail("sealed reader binding drift")
    manifest_row = ident(repo / "source" / "CUMULATIVE_INPUTS.json", "source/CUMULATIVE_INPUTS.json")
    if receipt.get("source_manifest") != manifest_row or {
        "path": seal.get("manifest", {}).get("path"),
        "bytes": seal.get("manifest", {}).get("bytes"),
        "sha256": seal.get("manifest", {}).get("sha256"),
    } != manifest_row:
        fail("sealed manifest binding drift")
    target = receipt.get("target")
    if (
        not isinstance(target, dict)
        or {"bytes": target.get("bytes"), "sha256": target.get("sha256")}
        != {"bytes": TARGET[0], "sha256": TARGET[1]}
        or target.get("lf_lines") != 1809
        or {"bytes": seal.get("target", {}).get("bytes"), "sha256": seal.get("target", {}).get("sha256")}
        != {"bytes": TARGET[0], "sha256": TARGET[1]}
    ):
        fail("sealed target binding drift")

    raw_row = receipt["build"]["raw_log"]
    raw = read_regular(repo / raw_row["path"], raw_row["path"])
    try:
        expected_log = sanitize_log(raw.decode("utf-8"), repo, private_root, canonical_root).encode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("sealed raw log is not strict UTF-8") from exc
    for name in ("build-r39.log", "build.log"):
        if read_regular(repo / "evidence" / name, f"evidence/{name}") != expected_log:
            fail(f"sealed sanitized log is not reproducible: {name}")


def prepare_unsealed(repo: Path, private_root: Path, canonical_root: Path) -> None:
    evidence = repo / "evidence"
    controls = evidence / "controls"
    private_controls = private_root / "controls"
    strict_path = controls / "R39_STRICT_BUILD.json"
    qa_path = controls / "R39_PDF_QA.json"
    strict = load(strict_path)
    qa = load(qa_path)
    if strict.get("schema") != "agko-r39-strict-build-control-v1" or strict.get("status") != "PASS_R39_STRICT_TWO_CYCLE_FOUR_PASS_BUILD":
        fail("strict-build control did not pass")
    if qa.get("schema") != "agko-r39-pdf-qa-v1" or qa.get("status") != "PASS" or qa.get("edition") != VERSION:
        fail("PDF-QA control did not pass")
    mirrored_controls = validate_control_mirrors(controls, private_controls)

    reader = repo / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
    identity_matches(reader, READER, "R39 reader")
    if (strict.get("reader", {}).get("bytes"), strict.get("reader", {}).get("sha256")) != READER or strict.get("reader", {}).get("pages") != 240:
        fail("reader/strict-control identity drift")
    if (qa.get("pdf", {}).get("bytes"), qa.get("pdf", {}).get("sha256")) != READER or qa.get("pdf", {}).get("pages") != 240:
        fail("reader/PDF-QA identity drift")
    manifest = repo / "source" / "CUMULATIVE_INPUTS.json"
    identity_matches(manifest, MANIFEST, "R39 cumulative manifest")
    target = repo / "source" / "c2s1.tex"
    private_target = private_root / "ega" / "II" / "c2s1.tex"
    identity_matches(target, TARGET, "R39 target")
    target_bytes = read_regular(target, "public target")
    if target_bytes != read_regular(private_target, "private target"):
        fail("R39 target mirror drift")
    if target_bytes.count(b"\n") != 1809:
        fail("R39 target LF line-count drift")

    qa_extractions = {
        str(row.get("path")): (row.get("bytes"), row.get("sha256"))
        for row in qa.get("extractions", [])
        if isinstance(row, dict)
    }
    sources = {
        "evidence/r39-extract-poppler.txt": evidence / "r39-extract-poppler.txt",
        "evidence/r39-extract-pypdf.txt": evidence / "r39-extract-pypdf.txt",
    }
    extraction_bytes: dict[str, bytes] = {}
    for display, path in sources.items():
        data = read_regular(path, display)
        if qa_extractions.get(display) != (len(data), sha_bytes(data)):
            fail(f"R39 extraction/PDF-QA binding drift: {display}")
        extraction_bytes[display] = data

    raw_log = repo / "build" / "out" / "main.log"
    raw_log_bytes = read_regular(raw_log, "build/out/main.log")
    try:
        sanitized = sanitize_log(raw_log_bytes.decode("utf-8"), repo, private_root, canonical_root).encode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("R39 raw log is not strict UTF-8") from exc

    receipt: dict[str, Any] = {
        "schema": "ag-ko-r39-build-receipt-v1",
        "version": VERSION,
        "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "exact_doi": EXACT_DOI,
        "concept_doi": CONCEPT_DOI,
        "coverage": {"terminal": "EGA II §2.2.6 / canonical lines1-1780", "next": "EGA II line1782 / environment2.2.7", "historical_markers": 229, "no_completion_claim": True},
        "reader": {**ident(reader, "reader/00_EGA_ko_CUMULATIVE_READER.pdf"), "pages": 240},
        "source_manifest": ident(manifest, "source/CUMULATIVE_INPUTS.json"),
        "target": {**ident_bytes(target_bytes, "source/c2s1.tex"), "private_public_exact": True, "lf_lines": 1809},
        "build": {
            "strict_control": ident(strict_path, "evidence/controls/R39_STRICT_BUILD.json"),
            "pdf_qa": ident(qa_path, "evidence/controls/R39_PDF_QA.json"),
            "raw_log": ident_bytes(raw_log_bytes, "build/out/main.log"),
            "sanitized_logs": [ident_bytes(sanitized, "evidence/build-r39.log"), ident_bytes(sanitized, "evidence/build.log")],
        },
        "extractions": [
            ident_bytes(extraction_bytes["evidence/r39-extract-poppler.txt"], "evidence/r39-extract-poppler.txt"),
            ident_bytes(extraction_bytes["evidence/r39-extract-pypdf.txt"], "evidence/r39-extract-pypdf.txt"),
            ident_bytes(extraction_bytes["evidence/r39-extract-poppler.txt"], "evidence/extract.txt"),
            ident_bytes(extraction_bytes["evidence/r39-extract-pypdf.txt"], "evidence/extract-pypdf.txt"),
        ],
        "mirrored_r39_controls": mirrored_controls,
        "result": "PASS_R39_RELEASE_EVIDENCE",
    }
    receipt_text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    reject_private_material(receipt_text, "R39 build receipt", (repo, private_root, canonical_root))
    payload = receipt_text.encode("utf-8")
    result = atomic_mirror(
        [
            (evidence / "build-r39.log", sanitized),
            (evidence / "build.log", sanitized),
            (evidence / "extract.txt", extraction_bytes["evidence/r39-extract-poppler.txt"]),
            (evidence / "extract-pypdf.txt", extraction_bytes["evidence/r39-extract-pypdf.txt"]),
            (evidence / "BUILD_RECEIPT.json", payload),
            (private_controls / "R39_BUILD_RECEIPT.json", payload),
        ]
    )
    print(
        f"PASS_R39_RELEASE_EVIDENCE|{len(payload)}|{sha_bytes(payload)}|"
        f"reader={READER[0]}/{READER[1]}|transaction={result}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--canonical-root", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve(strict=True)
    private_root = args.private_root.resolve(strict=True)
    canonical_root = args.canonical_root.resolve(strict=True)
    controls = repo / "evidence" / "controls"
    private_controls = private_root / "controls"
    with transaction_mutex():
        seal = validate_seal_pair(controls, private_controls)
        if seal is not None:
            verify_sealed_outputs(seal, repo, private_root, canonical_root)
            print(
                "PASS_R39_RELEASE_EVIDENCE_SEALED_IDEMPOTENT|"
                f"seal={STATE_SEAL[0]}/{STATE_SEAL[1]}|mutations=0"
            )
            return
        prepare_unsealed(repo, private_root, canonical_root)
        if validate_seal_pair(controls, private_controls) is not None:
            fail("R39 state seal appeared during pre-seal preparation")


if __name__ == "__main__":
    main()
