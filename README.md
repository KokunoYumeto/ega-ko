# 대수기하학 원론 (EGA) — 한국어 누적판

[현재까지 완성된 한국어 번역 전체 — 00_EGA_ko_CUMULATIVE_READER.pdf](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 이전 정확판 DOI: [10.5281/zenodo.22132582](https://doi.org/10.5281/zenodo.22132582) (r25)
- Figshare 계속 항목(이전 공개 판): [10.6084/m9.figshare.33314679](https://doi.org/10.6084/m9.figshare.33314679) — 현재 계정 비활성화로 다음 추가 업로드를 수행할 수 없으며, 최근 r21 시도와 재개 조건은 [`figshare-pending-v11.json`](figshare-pending-v11.json)에 기록되어 있다.
- 전역 EGA 자료실 및 프랑스어 원전 계열: [10.5281/zenodo.20414353](https://doi.org/10.5281/zenodo.20414353)
- 언어: 한국어 (`ko`; Zenodo `kor`)
- 정확판: `2026-08-28-r26`, [10.5281/zenodo.22134988](https://doi.org/10.5281/zenodo.22134988), EGA I 완역 및 EGA II 제1.5.4항까지
- 정확 범위: `00_EGA_ko_CUMULATIVE_READER.pdf`는 이 공개판의 맨 앞 독자용 산출물이며, 정본 `source/EGA_FR.tex` 드라이버가 EGA I에 대해 열거한 모든 입력의 완전한 한국어 번역에 이어 EGA II 제II장 프로그램 전부와 제1절 제1.1.1--1.5.4항까지의 연속 구간을 담는다. EGA I는 완역되었고 EGA II는 `ega2-1-fr.tex` 1--712행까지 연속해서 포함되지만, EGA II 또는 EGA 전집 전체의 완성을 주장하지 않는다. `source/CUMULATIVE_INPUTS.json`이 17개 TeX 입력과 순서를 명시하며, 빌드는 선언되지 않았거나 빠진 TeX 파일이 있으면 실패한다.

`reader/00_EGA_ko_CUMULATIVE_READER.pdf`는 이 프로젝트에서 지금까지 만든 모든 한국어 EGA 본문을 빠짐없이 수록한 전면 누적 산출물이다. EGA I 완역 뒤에 EGA II의 첫 정본 입력 전부와 둘째 입력의 1--712행을 연속해서 덧붙였다. 이 공개 묶음은 EGA 전체를 한국어로 옮기는 하나의 연속된 언어판을 유지하지만, EGA II나 EGA 전집 전체가 이미 완성되었다고 주장하지 않는다. `release/2026-08-28-r26/`의 네 산출물이 이번 범위의 정확판이며, Zenodo 정확 DOI는 [10.5281/zenodo.22134988](https://doi.org/10.5281/zenodo.22134988)이다. r25 및 이전 DOI는 변경하지 않은 역사로 보존한다. Figshare에는 중복 항목을 만들지 않고 기존 계속 항목의 다음 판만 준비하며, 계정이 복구되면 같은 네 바이트를 다음 추가 판으로 올린다. GitHub 저장소 `https://github.com/KokunoYumeto/ega-ko`에도 동일한 공개 작업 머리를 유지한다. 후속 번역은 같은 한국어 EGA 계열에 누적하며 다른 언어 또는 FGA/SGA 계열과 합치지 않는다.

## English identification

This is the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). `00_EGA_ko_CUMULATIVE_READER.pdf` is the front artifact and contains complete Korean EGA I followed by the complete EGA II Chapter II programme and the contiguous part of §1 through 1.5.4, canonical `ega2-1-fr.tex` lines 1--712. EGA II and the full EGA corpus are not claimed complete. `source/CUMULATIVE_INPUTS.json` binds all 17 TeX inputs and their compilation order, and the build fails closed on any undeclared, missing, duplicate, unsafe, or reordered TeX file. Exact source, build, extraction, terminology, bilingual-audit, and rendered-QA evidence are included; the Zenodo exact DOI is 10.5281/zenodo.22134988. r25 and earlier DOIs remain immutable history. Figshare DOI 10.6084/m9.figshare.33314679 is the continuing article lineage; no duplicate article is created while its account is inactive. It is not a critical edition or a claim of human certification.

## 공개 구조

- `reader/`: 현재 `main` 작업 머리까지의 한국어 누적 독자용 PDF.
- `source/`: 편집 가능한 한국어 TeX.
- `build/BUILD.ps1`: 서로 독립인 두 번의 3회 XeLaTeX 주기와 바이트 동일성 검증.
- `evidence/`: 원문 권위, 번역·용어·조판 결정, 난점, 구조 색인, 추출 검사, 모든 쪽의 렌더 검사와 해시.
- `release/2026-08-28-r26/`: 이번 정확판의 네 산출물; 앞선 릴리스 디렉터리는 변경하지 않은 역사로 보존한다.

한국어 번역과 조판의 단일 프로젝트 기여자 표기는 `AI typesetting & translation`이다. 사람의 검토나 외부 인증을 주장하지 않으며, 미해결 사항은 `evidence/UNRESOLVED_ITEMS.tsv`에 숨김없이 기록한다.

CC BY 4.0은 권리를 보유한 범위의 한국어 번역, 한국어 조판, 프로젝트 작성 메타데이터·색인·결정·QA 증거에만 적용된다. 바탕 수학 저작, 역사적 프랑스어 판, 제3자 서지 자료는 각자의 권리와 귀속을 유지한다. 역사적 저자, NUMDAM과 원출판사는 이 독립 유지 번역을 보증하지 않는다.
