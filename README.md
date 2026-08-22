# 대수기하학 원론 (EGA) — 한국어 누적판

[이 정확판의 한국어 누적 독자용 PDF 열기](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 이 판의 정확 DOI: [10.5281/zenodo.22062866](https://doi.org/10.5281/zenodo.22062866)
- 동일 바이트 Figshare 보존본: [10.6084/m9.figshare.33314679](https://doi.org/10.6084/m9.figshare.33314679)
- 전역 EGA 자료실 및 프랑스어 원전 계열: [10.5281/zenodo.20414353](https://doi.org/10.5281/zenodo.20414353)
- 언어: 한국어 (`ko`; Zenodo `kor`)
- 정확판: `2026-08-23-r9`, 제10절 환경 10.8.7까지(명제 10.8.8 직전)
- 정확 범위: EGA I 앞부분과 서론, EGA $0_{\mathrm I}$ 전부, 제I장 머리와 제1절부터 제9절 전부, 제10절 명제 10.8.5와 증명, 따름정리 10.8.6과 이에 붙은 증명, 환경 10.8.7까지로서 명제 10.8.8 직전까지

이 공개 묶음은 EGA 전체를 한국어로 옮기는 하나의 연속된 언어판을 유지하지만, EGA 전집이 이미 완성되었다고 주장하지 않는다. DOI 22062866과 `release/2026-08-23-r9/`의 네 산출물이 이 범위의 정확판이며, 같은 네 바이트를 Figshare의 같은 항목에 계속 거울 보존한다. 복구된 GitHub 저장소 `https://github.com/KokunoYumeto/ega-ko`에도 동일한 공개 작업 머리를 유지한다. 후속 번역은 같은 한국어 Zenodo 계열과 같은 Figshare 항목의 새 판으로 누적한다. 완성된 EGA 각 권의 독자용 PDF도 이 언어판 안에 함께 두며, 권별로 경쟁하는 DOI를 만들지 않는다.

## English identification

This is the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). Exact DOI 10.5281/zenodo.22062866 covers §10 through Proposition 10.8.5 with proof, Corollary 10.8.6 and its attached proof, and environment 10.8.7, ending immediately before Proposition 10.8.8, with exact source, build, extraction and rendered-QA evidence. DOI 10.6084/m9.figshare.33314679 is the continuing byte-identical preservation mirror. It is not a critical edition or a claim of human certification.

## 공개 구조

- `reader/`: 현재 `main` 작업 머리까지의 한국어 누적 독자용 PDF.
- `source/`: 편집 가능한 한국어 TeX.
- `build/BUILD.ps1`: 세 번의 XeLaTeX 실행과 결과 검증.
- `evidence/`: 원문 권위, 번역·용어·조판 결정, 난점, 구조 색인, 추출 검사, 모든 쪽의 렌더 검사와 해시.
- `release/2026-08-23-r9/`: 정확판 DOI 22062866과 같은 Figshare 항목의 계속되는 거울판에 놓는 변경하지 않은 네 산출물.

한국어 번역과 조판의 단일 프로젝트 기여자 표기는 `AI typesetting & translation`이다. 사람의 검토나 외부 인증을 주장하지 않으며, 미해결 사항은 `evidence/UNRESOLVED_ITEMS.tsv`에 숨김없이 기록한다.

CC BY 4.0은 권리를 보유한 범위의 한국어 번역, 한국어 조판, 프로젝트 작성 메타데이터·색인·결정·QA 증거에만 적용된다. 바탕 수학 저작, 역사적 프랑스어 판, 제3자 서지 자료는 각자의 권리와 귀속을 유지한다. 역사적 저자, NUMDAM과 원출판사는 이 독립 유지 번역을 보증하지 않는다.
