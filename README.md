# 대수기하학 원론 (EGA) — 한국어 누적판

[현재 `main` 작업 머리의 한국어 누적 독자용 PDF 열기](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 최근 공개 정확판 DOI: [10.5281/zenodo.22051764](https://doi.org/10.5281/zenodo.22051764)
- 전역 EGA 자료실 및 프랑스어 원전 계열: [10.5281/zenodo.20414353](https://doi.org/10.5281/zenodo.20414353)
- 언어: 한국어 (`ko`; Zenodo `kor`)
- 최근 공개 정확판: `2026-08-22-r1`, 제10절 명제 10.5.6까지
- `main` 작업 머리 범위: EGA I 앞부분과 서론, EGA $0_{\mathrm I}$ 전부, 제I장 머리와 제1절부터 제9절 전부, 제10절 명제 10.6.2의 명제문까지

이 저장소는 EGA 전체를 한국어로 옮기는 하나의 연속된 언어판을 유지한다. `main`은 위 작업 머리 범위까지 완성된 모든 번역을 빠짐없이 담지만, EGA 전집이 이미 완성되었다고 주장하지 않는다. DOI 22051764와 `release/`의 네 산출물은 변경하지 않은 최근 공개 정확판이며, 후속 번역은 같은 한국어 DOI 계열과 이 저장소의 `main` 브랜치에서 누적된다. 완성된 EGA 각 권의 독자용 PDF도 이 언어판 안에 함께 두며, 권별로 경쟁하는 DOI를 만들지 않는다.

## English identification

This is the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). The immutable exact DOI release covers §10 through Proposition 10.5.6. The current `main` working head continues through the statement of Proposition 10.6.2, with exact source, build, extraction and rendered-QA evidence. It is not a critical edition or a claim of human certification.

## 공개 구조

- `reader/`: 현재 `main` 작업 머리까지의 한국어 누적 독자용 PDF.
- `source/`: 편집 가능한 한국어 TeX.
- `build/BUILD.ps1`: 세 번의 XeLaTeX 실행과 결과 검증.
- `evidence/`: 원문 권위, 번역·용어·조판 결정, 난점, 구조 색인, 추출 검사, 모든 쪽의 렌더 검사와 해시.
- `release/`: 최근 공개 정확판 DOI 22051764의 변경하지 않은 네 산출물.

한국어 번역과 조판의 단일 프로젝트 기여자 표기는 `AI typesetting & translation`이다. 사람의 검토나 외부 인증을 주장하지 않으며, 미해결 사항은 `evidence/UNRESOLVED_ITEMS.tsv`에 숨김없이 기록한다.
