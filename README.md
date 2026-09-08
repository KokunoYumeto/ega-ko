# 대수기하학 원론 (EGA) — 한국어 누적판

[현재까지 완성된 한국어 번역 전체 — 누적 독자용 PDF](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 현재 정확판 DOI: [10.5281/zenodo.22652574](https://doi.org/10.5281/zenodo.22652574)
- 공개 저장소: [KokunoYumeto/ega-ko](https://github.com/KokunoYumeto/ega-ko)
- 현재 판: `2026-09-08-ega2-complete`
- 범위: EGA 0_I, EGA I, EGA II 완역
- 언어: 한국어 (`ko`; Zenodo `kor`)

`reader/00_EGA_ko_CUMULATIVE_READER.pdf`는 이 프로젝트에서 완료되고 원전·번역·조판 증거에 결박된 모든 한국어 EGA 본문을 빠짐없이 수록한 전면 누적 산출물이다. 현재 판은 EGA 0_I, EGA I, EGA II를 완전히 수록한다. EGA II의 장 머리말과 프로그램, 제1절부터 제8절 제8.14.14항의 증명까지인 본문 원전 끝, 서지, 기호·용어 색인과 원 목차, 정오표와 추가 사항이 각각 정본 파일 끝까지 들어 있다. 437쪽 A4 PDF이며 역사적 원전 쪽 경계 423개를 보존한다. 이후 EGA 권들의 번역 완료는 주장하지 않는다.

`source/CUMULATIVE_INPUTS.json`은 각 한국어 입력을 정본 원전의 안정 식별자, 정확한 범위, 해시, 입력 순서와 역사적 쪽수에 결박한다. `source/`에는 편집 가능한 한국어 TeX, 누적 드라이버와 빌드 전제조건이 있다. `release/2026-09-08-ega2-complete/`에는 독자용 PDF, 결정론적 편집 원본 ZIP, 범위가 제한된 증거·출처 ZIP, SHA-256 목록이 있다. 앞선 정확판과 릴리스는 불변 역사로 남는다.

누적 독자용 PDF는 전역 TeX 뮤텍스 아래 한 번의 4회 XeLaTeX 수렴 빌드로 생성되었고, 마지막 두 출력은 바이트 단위로 동일하다. 그 뒤 437쪽 전체에 대한 단 한 번의 집계 검사를 수행했다. 작은 절별 검사 반복도, 전체 독자 재검사도 수행하지 않았다. 릴리스 포장은 이미 검증된 바이트를 복사하고 해시했을 뿐 다시 빌드하거나 렌더링하지 않았다.

## English identification

This repository contains the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). Version `2026-09-08-ega2-complete` contains complete Korean EGA 0_I, EGA I, and EGA II. EGA II includes its front matter and programme, the complete main text through Section 8 and Proposition 8.14.14 with its proof, bibliography, notation and terminology indexes, original contents, and errata and addenda, each through canonical source EOF. The wider EGA corpus remains incomplete.

The primary human-readable artifact is the 437-page cumulative PDF. Editable TeX and a hash-bound coverage matrix accompany it. The bounded evidence package retains source identities, choice records, terminal build and whole-reader check receipts, compact render evidence, provenance, and artifact hashes. Legacy mathematics-font extraction can be lossy; editable TeX and rendered formulas remain authoritative.

This independent edition is not a critical edition and claims neither perfection, infallibility, external human certification, nor endorsement. Confirmed errors and documented uncertainties are corrected in later immutable versions. It remains separate from FGA, SGA, Chinese, and Japanese corpus-language lineages.

Alexander Grothendieck and Jean Dieudonné are the historical creators. `AI typesetting & translation` is the sole standardized project contributor. The historical authors, NUMDAM, IHÉS, publishers, repositories, and cited third parties do not endorse this independently maintained Korean edition.

CC BY 4.0 applies only where the project holds the relevant rights: the Korean translation and typesetting, together with project-authored metadata, indexes, decisions, and verification evidence. The underlying mathematical work, historical French edition, bibliography, and all third-party material retain their exact provenance, attribution, author/source relationships, rights, and licence status.
