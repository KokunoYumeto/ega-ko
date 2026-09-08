# Complete-EGA-II local package task input

## Verbatim delegated task

> Create the complete-EGA-II cumulative release package locally, using the exact validated current artifacts and prior R61 packaging conventions. Work only under C:\Users\Floris\Documents\interlanguage\03_projects\language_management\cjk\03_working_translations\ag_ko\pub\ega-ko plus exact task-local controls/ledgers needed. Do not build, render, run any QA, open UI, publish, authenticate, use Git, or touch Figshare. User forbids repeated or per-section QA: packaging must only copy/hash already validated bytes. Current reader: 437 pages, 2,552,588 B, SHA256 7F9B246E2623FB1992903C76A2AE2E46A7AD9FCC7B1FC7804DF4E0E2ADFBD575. QA receipt: pub\ega-ko\evidence\controls\EGA2_COMPLETE_SINGLE_AGGREGATE_PDF_QA_20260908.json, 6,166 B, SHA EF7E618B8EEB1FF3A7FF1A6D79C94CB8E009500EE02D92C86DB77AC24558DD9F. Build receipt: controls\EGA2_COMPLETE_CUMULATIVE_BUILD_20260908.json, 2,437 B, SHA 877B6163F294BF87490BD7751F609387A83103CFAE979F12E092B7D13560579E. Create a uniquely named release directory for 2026-09-08 complete EGA II; include the pertinent reader PDF as the human preview, deterministic source ZIP, appropriately bounded evidence ZIP that excludes the 212 MB transient full renders unless prior public convention requires them (include QA receipt and compact contact evidence as appropriate), machine-readable release manifest, README/public description, and packaging receipt. Preserve exact license/provenance/non-endorsement. Public metadata: work title only, historical authors creators, sole contributor `AI typesetting & translation`; no TTP prose/title, no user first name, no Figshare. Point to Zenodo concept https://doi.org/10.5281/zenodo.21921513 and GitHub https://github.com/KokunoYumeto/ega-ko. Use apply_patch for authored text/scripts, but ordinary deterministic archive/copy commands are allowed. Verify archive entry names/sizes/hashes and package identities once; this is packaging verification, not content QA. Return exact files, sizes, hashes, and release-version/tag recommendation. Do not publish.

## Executable next action

Completed: `scripts/package_ega2_complete_20260908.py` ran exactly once and created `release/2026-09-08-ega2-complete/`.

- Reader: 2,552,588 bytes; SHA-256 `7F9B246E2623FB1992903C76A2AE2E46A7AD9FCC7B1FC7804DF4E0E2ADFBD575`.
- Source ZIP: 452,998 bytes; SHA-256 `431C079BCAEA823A9979ABB0B19125C5E726E72FF26A94270695E4DD35882140`; 29 entries; inventory SHA-256 `84C610FA06A256FAF39E09A7E6A8B637A6D7F88FA000FB1B9D63CB15B9062758`.
- Evidence ZIP: 23,142,101 bytes; SHA-256 `AFB44BB139306B17C9963581680469713EEDAD1C40F565C19F0118C1D2595B05`; 19 entries; inventory SHA-256 `254C3589597D6B9D1E40C61696604F65ADAADE037F1780D48F2FC4C5F25F41B7`.
- Result: `PASS_COMPLETE_EGA2_LOCAL_PACKAGE_COPY_HASH_ONLY`.
- Recommended version: `2026-09-08-ega2-complete`.
- Recommended Git tag: `ega-ko-2026-09-08-ega2-complete`.

No publication is authorized in this delegated task. The next action is to return the exact package identities to the parent task.
