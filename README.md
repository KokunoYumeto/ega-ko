# 대수기하학 원론 (EGA) — 한국어 누적판

[이 정확판의 한국어 누적 독자용 PDF 열기](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 이 판의 정확 DOI: [10.5281/zenodo.22062589](https://doi.org/10.5281/zenodo.22062589)
- 동일 바이트 Figshare 보존본: [10.6084/m9.figshare.33314679](https://doi.org/10.6084/m9.figshare.33314679)
- 전역 EGA 자료실 및 프랑스어 원전 계열: [10.5281/zenodo.20414353](https://doi.org/10.5281/zenodo.20414353)
- 언어: 한국어 (`ko`; Zenodo `kor`)
- 정확판: `2026-08-22-r8`, 제10절 명제 10.8.5 직전의 완비화 함자 문단까지
- 정확 범위: EGA I 앞부분과 서론, EGA $0_{\mathrm I}$ 전부, 제I장 머리와 제1절부터 제9절 전부, 제10절 보조정리 10.8.2와 증명, 환경 10.8.3, 정의 10.8.4 및 명제 10.8.5 직전의 제한·위상적 역극한·가법 공변 완비화 함자 문단까지

이 공개 묶음은 EGA 전체를 한국어로 옮기는 하나의 연속된 언어판을 유지하지만, EGA 전집이 이미 완성되었다고 주장하지 않는다. DOI 22062589와 `release/2026-08-22-r8/`의 네 산출물이 이 범위의 정확판이며, 같은 네 바이트를 Figshare에도 거울 보존한다. 복구된 GitHub 저장소 `https://github.com/KokunoYumeto/ega-ko`에도 동일한 공개 작업 머리를 유지한다. 후속 번역은 같은 한국어 Zenodo 계열과 같은 Figshare 항목의 새 판으로 누적한다. 완성된 EGA 각 권의 독자용 PDF도 이 언어판 안에 함께 두며, 권별로 경쟁하는 DOI를 만들지 않는다.

## English identification

This is the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). Exact DOI 10.5281/zenodo.22062589 covers §10 through Lemma 10.8.2 with proof, environment 10.8.3, Definition 10.8.4, and the attached completion-functor paragraphs immediately before Proposition 10.8.5, with exact source, build, extraction and rendered-QA evidence. DOI 10.6084/m9.figshare.33314679 is the continuing byte-identical preservation mirror. It is not a critical edition or a claim of human certification.

## 공개 구조

- `reader/`: 현재 `main` 작업 머리까지의 한국어 누적 독자용 PDF.
- `source/`: 편집 가능한 한국어 TeX.
- `build/BUILD.ps1`: 세 번의 XeLaTeX 실행과 결과 검증.
- `evidence/`: 원문 권위, 번역·용어·조판 결정, 난점, 구조 색인, 추출 검사, 모든 쪽의 렌더 검사와 해시.
- `release/2026-08-22-r8/`: 정확판 DOI 22062589와 Figshare v4 거울의 변경하지 않은 네 산출물.

한국어 번역과 조판의 단일 프로젝트 기여자 표기는 `AI typesetting & translation`이다. 사람의 검토나 외부 인증을 주장하지 않으며, 미해결 사항은 `evidence/UNRESOLVED_ITEMS.tsv`에 숨김없이 기록한다.
