# 대수기하학 원론 (EGA) — 한국어 누적판

[이 정확판의 한국어 누적 독자용 PDF 열기](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 이전 정확판 DOI: [10.5281/zenodo.22074926](https://doi.org/10.5281/zenodo.22074926) (r17)
- Figshare 계속 항목(이전 공개 판): [10.6084/m9.figshare.33314679](https://doi.org/10.6084/m9.figshare.33314679) — 현재 계정 비활성화로 새 v7 업로드가 보류되어 있으며, 시도와 재개 조건은 [`figshare-pending-v7.json`](figshare-pending-v7.json)에 기록되어 있다.
- 전역 EGA 자료실 및 프랑스어 원전 계열: [10.5281/zenodo.20414353](https://doi.org/10.5281/zenodo.20414353)
- 언어: 한국어 (`ko`; Zenodo `kor`)
- 정확판: `2026-08-24-r18`, [10.5281/zenodo.22076207](https://doi.org/10.5281/zenodo.22076207), 제10.11절 정리 10.11.3과 바로 뒤의 동치 서술까지(따름정리 10.11.4 직전)
- 정확 범위: EGA I 앞부분과 서론, EGA $0_{\mathrm I}$ 전부, 제I장 머리와 제1절부터 제9절 전부, 제10절 따름정리 10.8.10, 명제 10.8.11, 따름정리 10.8.12·10.8.13·10.8.14와 각각에 붙은 논증, 제10.9절 전부, 제10.10절 환경 10.10.1, 명제 10.10.2와 그 논증 및 바로 뒤의 $\mathfrak{J}^\Delta$ 아이디얼층 동일시, 명제 10.10.3과 그 논증, 환경 10.10.4, 명제 10.10.5와 그 논증, 따름정리 10.10.6, 환경 10.10.7, 명제 10.10.8과 그 논증, 따름정리 10.10.9와 그 논증, 제10.11절 명제 10.11.1과 그 논증, 환경 10.11.2, 정리 10.11.3과 그 논증 및 바로 뒤의 동치 서술까지로서 따름정리 10.11.4 직전까지

이 공개 묶음은 EGA 전체를 한국어로 옮기는 하나의 연속된 언어판을 유지하지만, EGA 전집이 이미 완성되었다고 주장하지 않는다. `release/2026-08-24-r18/`의 네 산출물이 이번 범위의 정확판이며, Zenodo 정확 DOI는 10.5281/zenodo.22076207이다. r17 DOI 22074926은 변경하지 않은 역사로 보존한다. Figshare에는 중복 항목을 만들지 않고 기존 계속 항목의 다음 판만 준비하며, 계정이 복구되면 같은 네 바이트를 v7로 추가한다. 복구된 GitHub 저장소 `https://github.com/KokunoYumeto/ega-ko`에도 동일한 공개 작업 머리를 유지한다. 후속 번역은 같은 한국어 Zenodo 계열과 같은 Figshare 항목의 새 판으로 누적한다. 완성된 EGA 각 권의 독자용 PDF도 이 언어판 안에 함께 두며, 권별로 경쟁하는 DOI를 만들지 않는다.

## English identification

This is the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). The r18 package covers §10 through all of §10.9; environment 10.10.1; Propositions 10.10.2, 10.10.3 and 10.10.5 with their proofs and intervening consequences; Corollary 10.10.6; environment 10.10.7; Proposition 10.10.8 and its proof; Corollary 10.10.9 and its proof; and §10.11 through Proposition 10.11.1 and its proof, environment 10.11.2, Theorem 10.11.3 and its proof, plus the immediately following equivalence statement, ending immediately before Corollary 10.11.4. Exact source, build, extraction and rendered-QA evidence are included; the Zenodo exact DOI is 10.5281/zenodo.22076207. r17 DOI 10.5281/zenodo.22074926 remains immutable history. Figshare DOI 10.6084/m9.figshare.33314679 is the continuing article lineage; its next additive version is prepared but currently blocked by an inactive account, with no duplicate article created. It is not a critical edition or a claim of human certification.

## 공개 구조

- `reader/`: 현재 `main` 작업 머리까지의 한국어 누적 독자용 PDF.
- `source/`: 편집 가능한 한국어 TeX.
- `build/BUILD.ps1`: 서로 독립인 두 번의 3회 XeLaTeX 주기와 바이트 동일성 검증.
- `evidence/`: 원문 권위, 번역·용어·조판 결정, 난점, 구조 색인, 추출 검사, 모든 쪽의 렌더 검사와 해시.
- `release/2026-08-24-r18/`: 이번 정확판의 네 산출물; r17 디렉터리는 변경하지 않은 역사로 보존한다.

한국어 번역과 조판의 단일 프로젝트 기여자 표기는 `AI typesetting & translation`이다. 사람의 검토나 외부 인증을 주장하지 않으며, 미해결 사항은 `evidence/UNRESOLVED_ITEMS.tsv`에 숨김없이 기록한다.

CC BY 4.0은 권리를 보유한 범위의 한국어 번역, 한국어 조판, 프로젝트 작성 메타데이터·색인·결정·QA 증거에만 적용된다. 바탕 수학 저작, 역사적 프랑스어 판, 제3자 서지 자료는 각자의 권리와 귀속을 유지한다. 역사적 저자, NUMDAM과 원출판사는 이 독립 유지 번역을 보증하지 않는다.
