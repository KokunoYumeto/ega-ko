#!/usr/bin/env python3
"""Replay the frozen R36 source archive under the global TeX mutex."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader


VERSION = "2026-09-05-r36"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def ident_bytes(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha_bytes(data)}


def pypdf_extract(path: Path) -> bytes:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n") for page in reader.pages]
    return ("\n\f\n".join(pages) + "\n").encode("utf-8")


def poppler_extract(path: Path) -> bytes:
    result = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-eol", "unix", str(path), "-"],
        capture_output=True,
        timeout=300,
        check=True,
    )
    return result.stdout


def render(path: Path, page: int, output_prefix: Path) -> Path:
    subprocess.run(
        ["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-r", "200", "-png", str(path), str(output_prefix)],
        capture_output=True,
        timeout=180,
        check=True,
    )
    return output_prefix.with_suffix(".png")


def safe_remove_stage(stage: Path, expected_parent: Path) -> None:
    resolved_stage = stage.resolve()
    resolved_parent = expected_parent.resolve()
    if resolved_stage.parent != resolved_parent or resolved_stage.name != "r36-portable-replay":
        raise RuntimeError(f"unsafe portable stage target: {resolved_stage}")
    if resolved_stage.exists():
        shutil.rmtree(resolved_stage)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--resume-existing-stage", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    private_root = args.private_root.resolve()
    release = repo / "release" / VERSION
    source_zip = release / "01_EGA_ko_EDITABLE_SOURCES.zip"
    strict_reader = release / "00_EGA_ko_CUMULATIVE_READER.pdf"
    staging_parent = private_root / "release-staging"
    stage = staging_parent / "r36-portable-replay"
    if stage.exists() and not args.resume_existing_stage:
        raise RuntimeError(f"portable replay stage already exists: {stage}")
    if not stage.exists() and args.resume_existing_stage:
        raise RuntimeError(f"requested portable replay resume stage is absent: {stage}")
    if not stage.exists():
        stage.mkdir(parents=True)

    completed = False
    try:
        with zipfile.ZipFile(source_zip, "r") as archive:
            if archive.testzip() is not None:
                raise RuntimeError("source archive CRC verification failed")
            source_entries = len(archive.infolist())
            if not args.resume_existing_stage:
                archive.extractall(stage)
            else:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    staged = stage / Path(info.filename)
                    if not staged.is_file() or staged.read_bytes() != archive.read(info.filename):
                        raise RuntimeError(f"retained replay stage drift: {info.filename}")

        build_script = stage / "build" / "BUILD.ps1"
        script_text = build_script.read_text(encoding="utf-8")
        if not re.search(r"for \(\$pass = 1; \$pass -le 4; \$pass\+\+\)", script_text):
            raise RuntimeError("four-pass loop not proved in frozen BUILD.ps1")
        if script_text.count("Invoke-XeLaTeXCycle -Cycle") != 2:
            raise RuntimeError("two-cycle control flow not proved in frozen BUILD.ps1")
        if "did not converge byte-exactly between passes 3 and 4" not in script_text:
            raise RuntimeError("pass3/pass4 fail-closed gate missing")

        env = os.environ.copy()
        for name in ("AGKO_CANONICAL_ROOT", "AGKO_PRIVATE_ROOT"):
            env.pop(name, None)
        env["AGKO_REQUIRE_LIVE_COVERAGE"] = "0"
        invocation = [
            "pwsh",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(build_script),
        ]
        result = subprocess.run(
            invocation,
            cwd=stage,
            env=env,
            capture_output=True,
            timeout=1800,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "portable build failed: "
                + result.stderr.decode("utf-8", errors="replace")[-2000:]
                + result.stdout.decode("utf-8", errors="replace")[-2000:]
            )
        stdout = result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        stderr = result.stderr.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        terminal_lines = [line for line in stdout.splitlines() if line.startswith("PASS ")]
        if len(terminal_lines) != 1:
            raise RuntimeError(f"unexpected portable terminal output: {stdout!r}")
        terminal = terminal_lines[0]
        if "cycle_a_pass3_final_identical=true" not in terminal or "cycle_b_pass3_final_identical=true" not in terminal:
            raise RuntimeError("portable build did not report pass3/pass4 convergence")

        portable_reader = stage / "reader" / "00_EGA_ko_CUMULATIVE_READER.pdf"
        portable_pdf = portable_reader.read_bytes()
        strict_pdf = strict_reader.read_bytes()
        portable_pages = len(PdfReader(str(portable_reader)).pages)
        if portable_pages != 237:
            raise RuntimeError(f"portable page count drift: {portable_pages}")

        strict_poppler = poppler_extract(strict_reader)
        portable_poppler = poppler_extract(portable_reader)
        frozen_poppler = (repo / "evidence" / "extract.txt").read_bytes()
        if strict_poppler != portable_poppler or strict_poppler != frozen_poppler:
            raise RuntimeError("portable Poppler extraction drift")

        strict_pypdf = pypdf_extract(strict_reader)
        portable_pypdf = pypdf_extract(portable_reader)
        frozen_pypdf = (repo / "evidence" / "extract-pypdf.txt").read_bytes()
        if strict_pypdf != portable_pypdf or strict_pypdf != frozen_pypdf:
            raise RuntimeError("portable pypdf extraction drift")

        render_rows = []
        for page in (1, 236, 237):
            generated = render(portable_reader, page, stage / f"portable-render-r36-p{page:03d}")
            reference = repo / "evidence" / "render" / f"r36-p{page:03d}.png"
            if generated.read_bytes() != reference.read_bytes():
                raise RuntimeError(f"portable render drift on page {page}")
            render_rows.append(
                {
                    "physical_page": page,
                    "bytes": generated.stat().st_size,
                    "sha256": sha_file(generated),
                    "frozen_evidence_entry": f"render/r36-p{page:03d}.png",
                    "byte_identical": True,
                }
            )

        raw_log = stage / "build" / "out" / "main.log"
        receipt = {
            "schema": "ag-ko-portable-replay-v2",
            "version": VERSION,
            "exact_doi": "10.5281/zenodo.22217711",
            "source_archive": {
                "name": source_zip.name,
                "bytes": source_zip.stat().st_size,
                "sha256": sha_file(source_zip),
                "entries_verified": source_entries,
            },
            "build": {
                "invocations": 1,
                "internal_xelatex_passes": 8,
                "pass_count_proof": {
                    "bytes": build_script.stat().st_size,
                    "sha256": sha_file(build_script),
                    "four_pass_loops": 2,
                    "declared_xelatex_invocations": 8,
                    "failure_semantics": "each engine invocation throws on nonzero exit; pass3 must equal pass4 inside each cycle; cycle B final must equal cycle A final",
                    "result": "PASS_EXACT_BUILD_SCRIPT_CONTROL_FLOW",
                },
                "terminal_completion_proof": {
                    "stdout_terminal_record": terminal,
                    "portable_reader": {"bytes": len(portable_pdf), "sha256": sha_bytes(portable_pdf)},
                    "result": "PASS",
                },
                "timeout_seconds": 1800,
                "timed_out": False,
                "live_authority_environment": "omitted; frozen target hashes, declared inputs and admission records enforced",
                "returncode": result.returncode,
                "stdout": ident_bytes(result.stdout),
                "stderr": ident_bytes(result.stderr),
                "log": {"bytes": raw_log.stat().st_size, "sha256": sha_file(raw_log)},
                "result": "PASS",
            },
            "strict_reader": {"bytes": len(strict_pdf), "sha256": sha_bytes(strict_pdf), "pages": 237},
            "portable_reader": {"bytes": len(portable_pdf), "sha256": sha_bytes(portable_pdf), "pages": portable_pages},
            "pdf_byte_identical": strict_pdf == portable_pdf,
            "container_delta": "If strict and portable PDF bytes differ, the delta is retained as an unadjudicated container-level difference; exact same-tool extraction and selected-render identities prove the tested content properties without a path-only claim.",
            "extraction": {
                "poppler": {**ident_bytes(strict_poppler), "strict_portable_and_frozen_byte_identical": True, "hangul": len(re.findall("[가-힣]", strict_poppler.decode("utf-8"))), "replacement_characters": strict_poppler.decode("utf-8").count("\ufffd")},
                "pypdf": {**ident_bytes(strict_pypdf), "strict_portable_and_frozen_byte_identical": True, "hangul": len(re.findall("[가-힣]", strict_pypdf.decode("utf-8"))), "replacement_characters": strict_pypdf.decode("utf-8").count("\ufffd")},
            },
            "extraction_runtime": {
                "python_version": sys.version.split()[0],
                "pypdf_version": pypdf.__version__,
                "pypdf_page_join": "LF+FF+LF with one final LF; CRLF/CR normalized to LF",
                "poppler_options": ["-enc", "UTF-8", "-eol", "unix", "input.pdf", "-"],
            },
            "render_replay": {
                "comparisons": len(render_rows),
                "dpi": 200,
                "pages": render_rows,
                "result": "PASS_EXACT_PORTABLE_FROZEN_RASTER_IDENTITY_3_OF_3",
            },
            "visual_qa": "Portable raster bytes on pages1,236,237 exactly reproduce their already inspected strict-reader counterparts; no new full-document visual rereview is claimed.",
            "result": "PASS_PORTABLE_BUILD_EXACT_TEXT_AND_SELECTED_RENDER_REPLAY",
        }
        receipt_path = release / "PORTABLE_BUILD_REPLAY.json"
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        completed = True
        print(
            "PASS_R36_PORTABLE_REPLAY|"
            f"portable_pdf={len(portable_pdf)}/{sha_bytes(portable_pdf)}|"
            f"pdf_identical={str(strict_pdf == portable_pdf).lower()}|"
            f"receipt={receipt_path.stat().st_size}/{sha_file(receipt_path)}"
        )
    finally:
        if completed:
            safe_remove_stage(stage, staging_parent)


if __name__ == "__main__":
    main()
