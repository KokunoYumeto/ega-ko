# 대수기하학 원론 (EGA) — 한국어 누적판

[지금까지 완성된 전체 한국어 누적 독자용 PDF 열기](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 이 정확한 판의 DOI: [10.5281/zenodo.21921514](https://doi.org/10.5281/zenodo.21921514)
- 전역 EGA 자료실 및 프랑스어 원전 계열: [10.5281/zenodo.20414353](https://doi.org/10.5281/zenodo.20414353)
- 언어: 한국어 (`ko`; Zenodo `kor`)
- 판: `2026-08-13-r1`
- 현재 범위: EGA I 앞부분과 서론, EGA $0_{\mathrm I}$ 제1행부터 제2313행, 곧 제4.1.7절 끝까지

이 저장소는 EGA 전체를 한국어로 옮기는 하나의 연속된 언어판을 유지한다. 현재 판은 위 범위까지 완성된 모든 번역을 빠짐없이 담지만, EGA 전집이 이미 완성되었다고 주장하지 않는다. 후속 번역은 같은 한국어 DOI 계열과 이 저장소의 `main` 브랜치에서 누적된다. 완성된 EGA 각 권의 독자용 PDF도 이 언어판 안에 함께 두며, 권별로 경쟁하는 DOI를 만들지 않는다.

## English identification

This is the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). The exact release covers EGA I front matter and introduction plus the NUMDAM-based French authority through EGA $0_{\mathrm I}$ §4.1.7. It is an evidence-backed cumulative working edition, not a critical edition or a claim of human certification.

## 공개 구조

- `reader/`: 지금까지 완성한 전체 한국어 누적 독자용 PDF.
- `source/`: 편집 가능한 한국어 TeX.
- `build/BUILD.ps1`: 세 번의 XeLaTeX 실행과 결과 검증.
- `evidence/`: 원문 권위, 번역·용어·조판 결정, 난점, 구조 색인, 추출 검사, 모든 쪽의 렌더 검사와 해시.
- `release/`: Zenodo에 올리는 네 개의 간결한 공개 산출물.

한국어 번역과 조판은 Interlanguage 프로젝트를 위하여 OpenAI Codex가 수행하였다. 사람의 검토나 외부 인증은 출판 전제조건이 아니며, 미해결 사항은 `evidence/UNRESOLVED_ITEMS.tsv`에 숨김없이 기록한다.
