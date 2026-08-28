# 대수기하학 원론 (EGA) — 한국어 누적판

[현재까지 완성된 한국어 번역 전체 — 00_EGA_ko_CUMULATIVE_READER.pdf](reader/00_EGA_ko_CUMULATIVE_READER.pdf)

- 한국어판 안정 DOI: [10.5281/zenodo.21921513](https://doi.org/10.5281/zenodo.21921513)
- 이전 정확판 DOI: [10.5281/zenodo.22143603](https://doi.org/10.5281/zenodo.22143603) (`2026-08-28-r29`)
- 전역 EGA 자료실 및 프랑스어 원전 계열: [10.5281/zenodo.20414353](https://doi.org/10.5281/zenodo.20414353)
- 공개 GitHub 저장소: [KokunoYumeto/ega-ko](https://github.com/KokunoYumeto/ega-ko)
- 언어: 한국어 (`ko`; Zenodo `kor`)
- 정확판: `2026-08-29-r30`, [10.5281/zenodo.22151007](https://doi.org/10.5281/zenodo.22151007), EGA I 완역 및 EGA II 제1.7.8항까지

`reader/00_EGA_ko_CUMULATIVE_READER.pdf`는 이 프로젝트에서 현재까지 완료되고 해시로 승인된 모든 한국어 EGA 본문을 빠짐없이 수록한 전면 누적 산출물이다. 정본 `source/EGA_FR.tex` 드라이버가 EGA I에 대해 열거한 모든 입력의 완전한 한국어 번역에 이어 EGA II 제II장 프로그램 전부와 제1절 제1.1.1–1.7.8항까지의 연속 구간을 담는다. EGA II 본문은 정본 `ega2-1-fr.tex` 1–1047행까지 연속해서 포함된다. 역사적 원전의 쪽 경계 220개를 출력 쪽 리듬으로 보존한다. EGA I는 완역되었지만 EGA II 또는 EGA 전집 전체의 완성은 주장하지 않는다.

`source/CUMULATIVE_INPUTS.json`의 v2 범위 행렬은 정본 드라이버 23행을 완전 번역 16행, 부분 번역 1행, 명시적 미번역 6행으로 결박한다. 빌드는 대상 파일, 입력 순서, 정본 해시, 승인된 연속 부분 경계 또는 필수 승인 기록이 어긋나면 실패한다. 파일 존재, 물리적 쪽수 또는 대략적인 완성 인상은 번역 완료의 증거로 취급하지 않는다. 현재 다음 실행 경계는 정본 1049행이며, 제1.7.9항으로 이어지는 표상 문단에서 시작한다.

이번 증분은 제1.7.5–1.7.8항을 추가한다. 환 달린 공간의 사상에 대한 대칭 대수의 역상 호환성, 아핀 소 스펙트럼에서 가군에 대응하는 대칭 대수, 준연접성과 각 등급 성분의 유한 생성, 그리고 역사적 정의
`V(E) = Spec(S(E))`를 원문과 동기화했다. 마지막 정의에는 현대적 관습을 맞추기 위한 쌍대, 국소 자유성, 유한 랭크 또는 다발 아틀라스를 삽입하지 않았다. 환경 유형, 네 라벨, 아홉 상호참조, 수식과 사상 방향은 독립된 원문·한국어·기계 검사를 통과했다.

`release/2026-08-29-r30/`의 네 산출물이 이 범위의 정확한 보존 묶음이다. 앞선 DOI와 릴리스 디렉터리는 불변 역사로 남는다. 후속 번역은 같은 한국어 EGA corpus-language 계열에 누적하며 FGA, SGA, 중국어 또는 일본어 계열과 합치지 않는다.

## English identification

This is the independently maintained Korean cumulative edition of Grothendieck and Dieudonné's *Éléments de géométrie algébrique* (EGA). The front reader contains complete Korean EGA 0_I and EGA I, the complete EGA II Chapter II programme, and contiguous EGA II §1 through 1.7.8, canonical `ega2-1-fr.tex` lines 1–1047. Its 220 historical source-page markers establish the retained output-page rhythm. EGA II and the complete EGA corpus are not claimed complete.

The v2 matrix binds all 23 canonical driver rows as 16 complete translations, one admitted contiguous partial translation, and six explicit untranslated rows. The build fails closed on target, order, source-hash, or boundary drift. Exact source identities, editable TeX, terminology decisions, independent audits, reproducible build logs, dual text extraction, link resolution, selected high-resolution renders, and SHA-256 inventories are preserved with each release. The exact r30 DOI is `10.5281/zenodo.22151007`; the stable continuity DOI is `10.5281/zenodo.21921513`.

This is not a critical edition, a claim of external human certification, or a claim of perfection, infallibility, finality, endorsement, or corpus completion. Confirmed errors and documented uncertainties are corrected in later immutable versions.

## 공개 구조

- `reader/`: 현재 승인 경계까지의 한국어 누적 독자용 PDF.
- `source/`: 편집 가능한 한국어 TeX와 정본 범위 행렬.
- `build/BUILD.ps1`: 서로 독립인 두 번의 3회 XeLaTeX 주기와 바이트 동일성 검증.
- `evidence/`: 원문 권위, 번역·용어·조판 결정, 구조 색인, 추출·링크·렌더 검사와 SHA-256 목록.
- `release/2026-08-29-r30/`: 이번 정확판의 네 산출물; 앞선 릴리스는 변경하지 않는다.

한국어 번역과 조판의 단일 프로젝트 기여자 표기는 `AI typesetting & translation`이다. 사람의 검토나 외부 인증을 전제하지 않으며, 미해결 사항은 `evidence/UNRESOLVED_ITEMS.tsv`에 숨김없이 기록한다.

CC BY 4.0은 권리를 보유한 범위의 한국어 번역, 한국어 조판, 프로젝트 작성 메타데이터·색인·결정·QA 증거에만 적용된다. 바탕 수학 저작, 역사적 프랑스어 판, NUMDAM 자료와 제3자 서지는 각자의 정확한 권리, 라이선스, 귀속, 출처 및 저자 관계를 유지한다. 역사적 저자, NUMDAM과 원출판사는 이 독립 유지 번역을 보증하지 않는다.
