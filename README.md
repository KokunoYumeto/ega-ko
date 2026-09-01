# 대수기하학 원론 (EGA) — 한국어 누적판

[현재까지 완성된 한국어 번역 전체 — 00_EGA_ko_CUMULATIVE_READER.pdf](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 이전 정확판 DOI: [10.5281/zenodo.22208685](https://doi.org/10.5281/zenodo.22208685) (`2026-08-31-r33`)
- 전역 EGA 자료실 및 프랑스어 원전 계열: [10.5281/zenodo.20414353](https://doi.org/10.5281/zenodo.20414353)
- 공개 GitHub 저장소: [KokunoYumeto/ega-ko](https://github.com/KokunoYumeto/ega-ko)
- 언어: 한국어 (`ko`; Zenodo `kor`)
- 정확판: `2026-08-31-r34`, [10.5281/zenodo.22209381](https://doi.org/10.5281/zenodo.22209381), EGA I 완역 및 EGA II 제2.1.1항까지

`reader/00_EGA_ko_CUMULATIVE_READER.pdf`는 이 프로젝트에서 현재까지 완료되고 해시로 승인된 모든 한국어 EGA 본문을 빠짐없이 수록한 전면 누적 산출물이다. 정본 `source/EGA_FR.tex` 드라이버가 EGA I에 대해 열거한 모든 입력의 완전한 한국어 번역에 이어 EGA II 제II장 프로그램 전부와 제1절 전부와 제2절 제2.1.1항까지의 연속 구간을 담는다. EGA II 본문은 정본 `ega2-1-fr.tex` 1–1358행까지 연속해서 포함된다. 역사적 원전의 쪽 경계 224개를 출력 쪽 리듬으로 보존한다. EGA I는 완역되었지만 EGA II 또는 EGA 전집 전체의 완성은 주장하지 않는다.

`source/CUMULATIVE_INPUTS.json`의 v2 범위 행렬은 정본 드라이버 23행을 완전 번역 16행, 부분 번역 1행, 명시적 미번역 6행으로 결박한다. 빌드는 대상 파일, 입력 순서, 정본 해시, 승인된 연속 부분 경계 또는 필수 승인 기록이 어긋나면 실패한다. 파일 존재, 물리적 쪽수 또는 대략적인 완성 인상은 번역 완료의 증거로 취급하지 않는다. 현재 다음 실행 경계는 정본 1360행의 제2.1.2항이며 1359행은 빈 줄이다.

이번 증분은 명제 제1.7.15항과 그 증명 및 제2장 제2절의 표기 제2.1.1항을 완전히 추가한다. 바탕의 두 대안—`Y`의 위상공간이 뇌터이거나 `Y`가 준콤팩트 스킴임—을 보존하고, 유한형 아핀 `Y`-스킴을 유한형 준연접 가군층 `E`에 대한 `V(E)`의 닫힌 `Y`-부분스킴으로 실현한다. 증명에서는 유한형 대수, 이를 생성하는 유한형 준연접 부분가군, 대칭대수의 전사 사상과 그에 따른 닫힌 몰입 사상을 구별한다. 이어 양의 차수로 등급화된 환과 정수 차수 가군, `S_+`, 베로네제 환 `S^(d)`, 잉여류 가군 `M^(d,k)`, 이동 `M(n)`, 동차 기저와 차수 0 사상에 의한 유한 표시를 원문과 동기화했다. 음의 차수에서 `S_n=0`인 규약, 모든 지표 범위, 미래 제2.1.2항 참조와 원 인쇄면 20을 보존했다.

`release/2026-08-31-r34/`의 네 산출물이 이 범위의 정확한 보존 묶음이다. 앞선 DOI와 릴리스 디렉터리는 불변 역사로 남는다. 후속 번역은 같은 한국어 EGA corpus-language 계열에 누적하며 FGA, SGA, 중국어 또는 일본어 계열과 합치지 않는다.

## English identification

This is the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). The front reader contains complete Korean EGA 0_I and EGA I, the complete EGA II Chapter II programme, and contiguous EGA II §1 through 2.1.1, canonical `ega2-1-fr.tex` lines 1–1358. Its 224 historical source-page markers establish the retained output-page rhythm. EGA II and the complete EGA corpus are not claimed complete.

The v2 matrix binds all 23 canonical driver rows as 16 complete translations, one admitted contiguous partial translation, and six explicit untranslated rows. The build fails closed on target, order, source-hash, or boundary drift. Exact source identities, editable TeX, terminology decisions, independent audits, reproducible build logs, dual text extraction, link resolution, selected high-resolution renders, and SHA-256 inventories are preserved with each release. The exact r34 DOI is `10.5281/zenodo.22209381`; the stable continuity DOI is `10.5281/zenodo.21921513`.

Legacy Type1 mathematics fonts do not have complete ToUnicode mappings. Text extraction is checked but is not a lossless mathematical representation; editable TeX and rendered formulas remain authoritative.

This is not a critical edition, a claim of external human certification, or a claim of perfection, infallibility, finality, endorsement, or corpus completion. Confirmed errors and documented uncertainties are corrected in later immutable versions.

## 공개 구조

- `reader/`: 현재 승인 경계까지의 한국어 누적 독자용 PDF.
- `source/`: 편집 가능한 한국어 TeX와 정본 범위 행렬.
- `build/BUILD.ps1`: 서로 독립인 두 번의 3회 XeLaTeX 주기와 바이트 동일성 검증.
- `evidence/`: 원문 권위, 번역·용어·조판 결정, 구조 색인, 추출·링크·렌더 검사와 SHA-256 목록.
- `release/2026-08-31-r34/`: 이번 정확판의 네 산출물; 앞선 릴리스는 변경하지 않는다.

한국어 번역과 조판의 단일 프로젝트 기여자 표기는 `AI typesetting & translation`이다. 사람의 검토나 외부 인증을 전제하지 않으며, 미해결 사항은 `evidence/UNRESOLVED_ITEMS.tsv`에 숨김없이 기록한다.

CC BY 4.0은 권리를 보유한 범위의 한국어 번역, 한국어 조판, 프로젝트 작성 메타데이터·색인·결정·QA 증거에만 적용된다. 바탕 수학 저작, 역사적 프랑스어 판, NUMDAM 자료와 제3자 서지는 각자의 정확한 권리, 라이선스, 귀속, 출처 및 저자 관계를 유지한다. 역사적 저자, NUMDAM과 원출판사는 이 독립 유지 번역을 보증하지 않는다.
