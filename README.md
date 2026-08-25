# 대수기하학 원론 (EGA) — 한국어 누적판

[현재까지 완성된 한국어 번역 전체 — 00_EGA_ko_CUMULATIVE_READER.pdf](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 이전 정확판 DOI: [10.5281/zenodo.22101727](https://doi.org/10.5281/zenodo.22101727) (r21)
- Figshare 계속 항목(이전 공개 판): [10.6084/m9.figshare.33314679](https://doi.org/10.6084/m9.figshare.33314679) — 현재 계정 비활성화로 다음 추가 업로드를 수행할 수 없으며, 최근 r21 시도와 재개 조건은 [`figshare-pending-v11.json`](figshare-pending-v11.json)에 기록되어 있다.
- 전역 EGA 자료실 및 프랑스어 원전 계열: [10.5281/zenodo.20414353](https://doi.org/10.5281/zenodo.20414353)
- 언어: 한국어 (`ko`; Zenodo `kor`)
- 정확판: `2026-08-25-r22`, [10.5281/zenodo.22102429](https://doi.org/10.5281/zenodo.22102429), 제10.13절 끝까지(제10.14절 직전)
- 정확 범위: `00_EGA_ko_CUMULATIVE_READER.pdf`는 이 공개판의 맨 앞 독자용 산출물이며, 현재까지 완성된 한국어 번역을 빠짐없이 담는다. 범위는 EGA I 앞부분과 서론, EGA $0_{\mathrm I}$ 전부, 제I장 프로그램, 제I장 제1–9절 전부, 그리고 제10절 처음부터 제10.13절 끝까지이다. 번역은 제10.14절 직전에 끝나며, EGA I 또는 EGA 전집의 완성을 주장하지 않는다. `source/CUMULATIVE_INPUTS.json`이 모든 TeX 입력과 순서를 명시하며, 빌드는 선언되지 않았거나 빠진 TeX 파일이 있으면 실패한다.

`reader/00_EGA_ko_CUMULATIVE_READER.pdf`는 이 프로젝트에서 지금까지 만든 모든 한국어 EGA 본문을 빠짐없이 수록한 전면 누적 산출물이다. 이 공개 묶음은 EGA 전체를 한국어로 옮기는 하나의 연속된 언어판을 유지하지만, EGA 전집이 이미 완성되었다고 주장하지 않는다. `release/2026-08-25-r22/`의 네 산출물이 이번 범위의 정확판이며, Zenodo 정확 DOI는 10.5281/zenodo.22102429이다. r21 DOI 22101727은 변경하지 않은 역사로 보존한다. Figshare에는 중복 항목을 만들지 않고 기존 계속 항목의 다음 판만 준비하며, 계정이 복구되면 같은 네 바이트를 다음 추가 판으로 올린다. GitHub 저장소 `https://github.com/KokunoYumeto/ega-ko`에도 동일한 공개 작업 머리를 유지한다. 후속 번역은 같은 한국어 Zenodo 계열과 같은 Figshare 항목의 새 판으로 누적한다. 완성된 EGA 각 권의 독자용 PDF도 이 언어판 안에 함께 두며, 권별로 경쟁하는 DOI를 만들지 않는다.

## English identification

This is the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). `00_EGA_ko_CUMULATIVE_READER.pdf` is the front artifact of this release and contains the complete Korean translation available to date in this lineage: EGA I front matter and introduction, all of EGA 0_I, the Chapter I programme, Chapter I §§1–9 in full, and §10 from its beginning through the end of §10.13. It ends immediately before §10.14; neither EGA I nor the EGA corpus is claimed complete. `source/CUMULATIVE_INPUTS.json` binds every TeX input and its compilation order, and the build fails closed on any undeclared or missing TeX file. Exact source, build, extraction and rendered-QA evidence are included; the Zenodo exact DOI is 10.5281/zenodo.22102429. r21 DOI 10.5281/zenodo.22101727 remains immutable history. Figshare DOI 10.6084/m9.figshare.33314679 is the continuing article lineage; its next additive version is prepared but currently blocked by an inactive account, with no duplicate article created. It is not a critical edition or a claim of human certification.

## 공개 구조

- `reader/`: 현재 `main` 작업 머리까지의 한국어 누적 독자용 PDF.
- `source/`: 편집 가능한 한국어 TeX.
- `build/BUILD.ps1`: 서로 독립인 두 번의 3회 XeLaTeX 주기와 바이트 동일성 검증.
- `evidence/`: 원문 권위, 번역·용어·조판 결정, 난점, 구조 색인, 추출 검사, 모든 쪽의 렌더 검사와 해시.
- `release/2026-08-25-r22/`: 이번 정확판의 네 산출물; 앞선 릴리스 디렉터리는 변경하지 않은 역사로 보존한다.

한국어 번역과 조판의 단일 프로젝트 기여자 표기는 `AI typesetting & translation`이다. 사람의 검토나 외부 인증을 주장하지 않으며, 미해결 사항은 `evidence/UNRESOLVED_ITEMS.tsv`에 숨김없이 기록한다.

CC BY 4.0은 권리를 보유한 범위의 한국어 번역, 한국어 조판, 프로젝트 작성 메타데이터·색인·결정·QA 증거에만 적용된다. 바탕 수학 저작, 역사적 프랑스어 판, 제3자 서지 자료는 각자의 권리와 귀속을 유지한다. 역사적 저자, NUMDAM과 원출판사는 이 독립 유지 번역을 보증하지 않는다.
