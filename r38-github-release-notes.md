# 대수기하학 원론 (EGA) — 한국어 누적판 / Éléments de géométrie algébrique — Korean Cumulative Edition

Release `2026-09-05-r38` advances the source-synchronized Korean EGA II translation through §2.2.1 while preserving all previously admitted material. The cumulative reader contains complete Korean EGA 0_I and EGA I, the complete EGA II Chapter II programme/table of contents, and a contiguous EGA II main-text translation of canonical French source `ega2-1-fr.tex` lines 1–1683. EGA II and the full EGA corpus remain incomplete. The next source work begins at canonical line 1685.

The evolving Korean edition is identified by [concept DOI 10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513); this immutable checkpoint is identified by [exact-version DOI 10.5281/zenodo.22346664](https://doi.org/10.5281/zenodo.22346664). The public working lineage remains [KokunoYumeto/ega-ko](https://github.com/KokunoYumeto/ega-ko).

## R38 increment

The new unit covers §§2.1.10–2.1.11, the heading for §2.2, and §2.2.1, canonical lines 1607–1683. It develops ideals and radicals inside `S_+`, the nilradical, essentially reduced rings, zero divisors and essentially integral domains. It then introduces the grading on the fraction ring `S_f`, the degree-zero subring `S_{(f)}`, the Laurent-polynomial description of `(S^{(d)})_f`, and the corresponding localized construction for graded modules.

The structural admission checks bind all 111 inline formulas and 14 emphasis spans, the reference to §2.1.9, and the single historical printed-page marker `II:24`. The translation controls explicitly record potentially ambiguous source readings at canonical lines 1638 and 1664. Those clarifications preserve the universal scope at line 1638 and the arbitrary integral exponent—including zero—at line 1664 without silently repairing or altering the canonical French source.

The exact source and target identities are:

- R38 source slice: 4,096 characters; 4,191 LF-terminal UTF-8 bytes; SHA-256 `44583D53F17603797145FE63822F3F78DC6ECFD7ADA1B38EF01813F9E3F22BE6`.
- Admitted canonical prefix through line 1683: 78,088 bytes; SHA-256 `7DE4ECF8630F2B575C08ED0EE4AEC560F6BD4C6026C4BC894DD057D4AE1B9B75`.
- Admitted Korean candidate: 4,599 bytes; SHA-256 `8D37AF2B8B05D9C938F2D282F58902092FB7FCF55300B0A85B28C9538340CF93`.
- Cumulative Korean EGA II target: 80,222 bytes; SHA-256 `4E6C76FDA3FBADCDA044DCD11A38D0BF0764CAACA3D29CD8A3F8067D13B3F006`.

## Reproducible reader checks

The cumulative reader is 239 pages and 1,485,270 bytes, SHA-256 `FEC06D6723BFE9CC7D3C46E285C7DE8A49929F2797FD2F4F47877D2BDA06FE15`, with 228 historical printed-page markers. Two clean four-pass XeLaTeX cycles converged: passes 3 and 4 are byte-identical within each cycle, and the two final PDFs are byte-identical across cycles. The expected pass-2 delta is disclosed in the evidence rather than hidden.

The evidence set binds editable TeX, exact source coverage and authority, terminology and translation controls, formula and emphasis structure, references, historical markers, build logs, independent extraction paths, selected rendered pages, link checks, and SHA-256 inventories. Legacy Type1 mathematics fonts do not provide complete ToUnicode mappings, so extracted mathematical text is not lossless; the editable TeX and rendered formulas remain authoritative. These hard checks prove the properties they test, not perfection, corpus completion, finality, infallibility, or external human certification. Defects and uncertainties remain correctable in later immutable versions.

## Attribution, provenance, and rights

Alexander Grothendieck and Jean Dieudonné are the historical creators. `AI typesetting & translation` is the sole standardized project contributor. This is an independent translation and is not endorsed by the historical authors, NUMDAM, IHÉS, source publishers, repositories, or cited third parties.

CC BY 4.0 applies only where this project holds the relevant rights: the Korean translation and typesetting, project-authored metadata, indexes, decisions, and QA evidence. It does not relicense the underlying mathematical work, historical French edition, NUMDAM files, bibliography, or third-party content and makes no blanket public-domain or open-license claim about them. Every source retains its exact provenance, attribution, author/source relationship, rights, and licence status.
