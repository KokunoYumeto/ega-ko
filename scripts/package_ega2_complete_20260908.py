"""Package the validated complete-EGA-II Korean cumulative release.

This script performs packaging only: it copies the sealed reader, creates two
deterministic ZIP archives, and checks every archive entry exactly once after
writing. It does not build, render, run content QA, publish, authenticate, or
invoke Git.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
WORK = REPO.parent.parent
FINAL = REPO / "release/2026-09-08-ega2-complete"
FIXED_TIME = (2026, 9, 8, 0, 0, 0)
VERSION = "2026-09-08-ega2-complete"
TAG_RECOMMENDATION = "ega-ko-2026-09-08-ega2-complete"
TITLE = "대수기하학 원론 (EGA) — 한국어 누적판 / Éléments de géométrie algébrique — Korean Cumulative Edition"
CONCEPT_DOI = "https://doi.org/10.5281/zenodo.21921513"
GITHUB = "https://github.com/KokunoYumeto/ega-ko"

EXPECTED = {
    "reader": (2_552_588, "7F9B246E2623FB1992903C76A2AE2E46A7AD9FCC7B1FC7804DF4E0E2ADFBD575"),
    "qa_receipt": (6_166, "EF7E618B8EEB1FF3A7FF1A6D79C94CB8E009500EE02D92C86DB77AC24558DD9F"),
    "build_receipt": (2_437, "877B6163F294BF87490BD7751F609387A83103CFAE979F12E092B7D13560579E"),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_id(path: Path) -> dict[str, int | str]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": digest(data)}


def assert_id(label: str, path: Path) -> None:
    identity = file_id(path)
    expected_bytes, expected_hash = EXPECTED[label]
    if identity != {"bytes": expected_bytes, "sha256": expected_hash}:
        raise RuntimeError(f"{label} identity mismatch: {path}: {identity}")


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def write_deterministic_zip(output: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(
        output,
        "x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        allowZip64=True,
    ) as archive:
        for name in sorted(entries):
            archive.writestr(zip_info(name), entries[name], compresslevel=9)


def verify_archive_once(path: Path, expected: dict[str, bytes]) -> dict[str, int | str | bool]:
    rows: list[str] = []
    total = 0
    with zipfile.ZipFile(path, "r") as archive:
        members = sorted((item for item in archive.infolist() if not item.is_dir()), key=lambda item: item.filename)
        names = [item.filename for item in members]
        if names != sorted(expected) or len(names) != len(set(names)):
            raise RuntimeError(f"archive entry-name mismatch: {path}")
        for member in members:
            data = archive.read(member.filename)
            if data != expected[member.filename] or len(data) != member.file_size:
                raise RuntimeError(f"archive entry identity mismatch: {path}: {member.filename}")
            entry_hash = digest(data)
            total += len(data)
            rows.append(f"{member.filename}\0{len(data)}\0{entry_hash}\n")
    return {
        "path": path.name,
        **file_id(path),
        "entries": len(rows),
        "uncompressed_bytes": total,
        "inventory_sha256": digest("".join(rows).encode("utf-8")),
        "single_postwrite_entry_readback": True,
    }


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def public_description() -> str:
    return f"""# {TITLE}

Version `{VERSION}` is the cumulative Korean edition through complete EGA II. The reader contains complete Korean EGA 0_I, EGA I, and EGA II, including the EGA II front matter and programme, main text through §8.14.14 and its source EOF, bibliography, indexes and contents, and errata and addenda. The wider EGA corpus remains incomplete.

The pertinent human-readable preview is `00_EGA_ko_CUMULATIVE_READER.pdf`: 437 A4 pages, 2,552,588 bytes, SHA-256 `7F9B246E2623FB1992903C76A2AE2E46A7AD9FCC7B1FC7804DF4E0E2ADFBD575`. It preserves 423 historical source-page markers. Editable TeX and the hash-bound coverage matrix are in `01_EGA_ko_EDITABLE_SOURCES.zip`. The bounded evidence archive contains the terminal build and single whole-reader aggregate-QA receipts, 13 contact sheets, and the two full-resolution pages used to dispose the sparse-page heuristic. It intentionally excludes the 212 MB transient full-render set.

The reader was produced by one mutex-serialized four-pass XeLaTeX convergence build. Exactly one complete-reader aggregate PDF QA was then performed, with no per-section QA loops and no repeated whole-reader QA. Packaging copied and hashed those already validated bytes; it did not rebuild, render, or rerun content QA.

- Stable Korean EGA DOI: {CONCEPT_DOI}
- Repository: {GITHUB}
- Recommended GitHub tag: `{TAG_RECOMMENDATION}`

Alexander Grothendieck and Jean Dieudonné are the historical creators. `AI typesetting & translation` is the sole standardized project contributor. This independently maintained Korean edition is not endorsed by the historical authors, NUMDAM, IHÉS, publishers, repositories, or cited third parties.

CC BY 4.0 applies only where the project holds the relevant rights: the Korean translation and typesetting, and project-authored metadata, indexes, decisions, and QA evidence. The underlying mathematical work, historical French edition, bibliographic material, and other third-party content retain their exact provenance, attribution, author/source relationships, rights, and licence status.
"""


def citation_cff() -> str:
    return f'''cff-version: 1.2.0
message: "Please cite this exact Korean EGA cumulative edition."
title: "{TITLE}"
type: book
authors:
  - family-names: "Grothendieck"
    given-names: "Alexander"
  - family-names: "Dieudonné"
    given-names: "Jean"
version: "{VERSION}"
date-released: 2026-09-08
doi: "10.5281/zenodo.21921513"
url: "{CONCEPT_DOI}"
preferred-citation:
  type: book
  title: "{TITLE}"
  authors:
    - family-names: "Grothendieck"
      given-names: "Alexander"
    - family-names: "Dieudonné"
      given-names: "Jean"
  translators:
    - name: "AI typesetting & translation"
  languages:
    - "ko"
  doi: "10.5281/zenodo.21921513"
  version: "{VERSION}"
  year: "2026"
  url: "{CONCEPT_DOI}"
'''


def zenodo_metadata(description: str) -> dict[str, object]:
    paragraphs = [paragraph.strip().replace("\n", " ") for paragraph in description.split("\n\n")[1:] if paragraph.strip()]
    html_description = "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs if not paragraph.startswith("- "))
    return {
        "creators": [
            {"name": "Grothendieck, Alexander"},
            {"name": "Dieudonné, Jean"},
        ],
        "contributors": [
            {"name": "AI typesetting & translation", "type": "Other"},
        ],
        "title": TITLE,
        "version": VERSION,
        "access_right": "open",
        "description": html_description,
        "related_identifiers": [
            {
                "identifier": "https://doi.org/10.5281/zenodo.20414353",
                "relation": "isPartOf",
                "resource_type": "publication-other",
            }
        ],
        "keywords": [
            "Éléments de géométrie algébrique",
            "EGA",
            "algebraic geometry",
            "대수기하학",
            "한국어",
            "Korean translation",
            "Grothendieck",
            "Dieudonné",
        ],
        "license": "cc-by-4.0",
        "upload_type": "publication",
        "publication_type": "book",
        "language": "kor",
    }


def main() -> None:
    if FINAL.exists():
        raise RuntimeError(f"refusing to overwrite existing release: {FINAL}")

    reader = REPO / "reader/00_EGA_ko_CUMULATIVE_READER.pdf"
    qa_receipt = REPO / "evidence/controls/EGA2_COMPLETE_SINGLE_AGGREGATE_PDF_QA_20260908.json"
    build_receipt = WORK / "controls/EGA2_COMPLETE_CUMULATIVE_BUILD_20260908.json"
    assert_id("reader", reader)
    assert_id("qa_receipt", qa_receipt)
    assert_id("build_receipt", build_receipt)

    description = public_description()
    source_entries: dict[str, bytes] = {
        ".gitattributes": (REPO / ".gitattributes").read_bytes(),
        ".zenodo.json": json_bytes(zenodo_metadata(description)),
        "CITATION.cff": citation_cff().encode("utf-8"),
        "LICENSE": (REPO / "LICENSE").read_bytes(),
        "README.md": description.encode("utf-8"),
        "build/BUILD.ps1": (REPO / "build/BUILD.ps1").read_bytes(),
        "scripts/package_ega2_complete_20260908.py": Path(__file__).read_bytes(),
    }
    for path in sorted((REPO / "source").glob("*")):
        if path.is_file():
            source_entries[f"source/{path.name}"] = path.read_bytes()

    render_root = REPO / "evidence/render/ega2-complete-20260908"
    evidence_entries: dict[str, bytes] = {
        "LICENSE": (REPO / "LICENSE").read_bytes(),
        "controls/EGA2_COMPLETE_CUMULATIVE_BUILD_20260908.json": build_receipt.read_bytes(),
        "controls/EGA2_COMPLETE_SINGLE_AGGREGATE_PDF_QA_20260908.json": qa_receipt.read_bytes(),
        "source/CUMULATIVE_INPUTS.json": (REPO / "source/CUMULATIVE_INPUTS.json").read_bytes(),
    }
    for name in [*(f"contact-{index:02d}.png" for index in range(1, 14)), "page-013.png", "page-427.png"]:
        evidence_entries[f"render/{name}"] = (render_root / name).read_bytes()

    FINAL.mkdir(parents=True)
    reader_out = FINAL / "00_EGA_ko_CUMULATIVE_READER.pdf"
    shutil.copyfile(reader, reader_out)
    if reader_out.read_bytes() != reader.read_bytes():
        raise RuntimeError("reader copy is not byte-identical")

    source_zip = FINAL / "01_EGA_ko_EDITABLE_SOURCES.zip"
    evidence_zip = FINAL / "02_EGA_ko_EVIDENCE_AND_PROVENANCE.zip"
    write_deterministic_zip(source_zip, source_entries)
    write_deterministic_zip(evidence_zip, evidence_entries)

    # The only post-write archive-entry verification pass.
    source_inventory = verify_archive_once(source_zip, source_entries)
    evidence_inventory = verify_archive_once(evidence_zip, evidence_entries)

    asset_names = [reader_out.name, source_zip.name, evidence_zip.name]
    asset_rows = [{"order": index, "name": name, **file_id(FINAL / name)} for index, name in enumerate(asset_names)]
    manifest_text = "filename\tbytes\tsha256\n" + "".join(
        f"{row['name']}\t{row['bytes']}\t{row['sha256']}\n" for row in asset_rows
    )
    sha_manifest = FINAL / "03_EGA_ko_SHA256_MANIFEST.txt"
    sha_manifest.write_text(manifest_text, encoding="utf-8", newline="\n")
    public_assets = asset_rows + [{"order": 3, "name": sha_manifest.name, **file_id(sha_manifest)}]

    readme_path = FINAL / "README.md"
    readme_path.write_text(description, encoding="utf-8", newline="\n")

    release_manifest = {
        "schema": "agko-complete-ega2-release-manifest-v1",
        "version": VERSION,
        "release_date": "2026-09-08",
        "title": TITLE,
        "recommended_git_tag": TAG_RECOMMENDATION,
        "concept_doi": CONCEPT_DOI,
        "repository": GITHUB,
        "human_preview": reader_out.name,
        "coverage": {
            "complete": ["EGA 0_I", "EGA I", "EGA II"],
            "ega2_terminal": "section 8 / proposition 8.14.14 proof / canonical source EOF, with bibliography, indexes/contents, and errata/addenda through their source EOFs",
            "historical_source_page_markers": 423,
            "wider_ega_corpus_complete": False,
        },
        "creators": ["Alexander Grothendieck", "Jean Dieudonné"],
        "contributors": ["AI typesetting & translation"],
        "public_assets": public_assets,
        "source_archive": source_inventory,
        "evidence_archive": {
            **evidence_inventory,
            "full_render_set_included": False,
            "full_render_set_exclusion": "The 212 MB transient full-render set is excluded; 13 contact sheets and the two sparse-page disposition renders are retained.",
        },
        "license_and_provenance": {
            "project_material": "CC BY 4.0 only where the project holds the relevant rights",
            "underlying_material": "retains exact provenance, attribution, author/source relationship, rights, and licence status",
            "endorsement": "none claimed from the historical authors, NUMDAM, IHÉS, publishers, repositories, or cited third parties",
        },
    }
    release_manifest_path = FINAL / "RELEASE_MANIFEST.json"
    release_manifest_path.write_text(
        json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    receipt = {
        "schema": "agko-complete-ega2-package-receipt-v1",
        "version": VERSION,
        "created_at": "2026-09-08T00:00:00+02:00",
        "result": "PASS_COMPLETE_EGA2_LOCAL_PACKAGE_COPY_HASH_ONLY",
        "input_identities": {
            "reader": {"path": "pub/ega-ko/reader/00_EGA_ko_CUMULATIVE_READER.pdf", "pages": 437, **file_id(reader)},
            "qa_receipt": {"path": "pub/ega-ko/evidence/controls/EGA2_COMPLETE_SINGLE_AGGREGATE_PDF_QA_20260908.json", **file_id(qa_receipt)},
            "build_receipt": {"path": "controls/EGA2_COMPLETE_CUMULATIVE_BUILD_20260908.json", **file_id(build_receipt)},
        },
        "public_assets": public_assets,
        "source_archive": source_inventory,
        "evidence_archive": evidence_inventory,
        "support_files": {
            "README.md": file_id(readme_path),
            "RELEASE_MANIFEST.json": file_id(release_manifest_path),
        },
        "workflow": {
            "reader_copy_byte_identical": True,
            "deterministic_zip_timestamp": "2026-09-08T00:00:00",
            "package_constructions": 1,
            "archive_postwrite_entry_readbacks": 1,
            "content_builds": 0,
            "content_renders": 0,
            "content_qa_runs": 0,
            "publication_actions": 0,
            "git_actions": 0,
            "ui_actions": 0,
        },
        "recommended_git_tag": TAG_RECOMMENDATION,
    }
    receipt_path = FINAL / "PACKAGE_RECEIPT.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    package_files = []
    for path in sorted(FINAL.iterdir(), key=lambda item: item.name):
        if path.is_file():
            package_files.append({"name": path.name, **file_id(path)})
    print(
        json.dumps(
            {
                "release": str(FINAL),
                "version": VERSION,
                "recommended_git_tag": TAG_RECOMMENDATION,
                "files": package_files,
                "source_archive": source_inventory,
                "evidence_archive": evidence_inventory,
                "result": receipt["result"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
