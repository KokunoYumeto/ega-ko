# EGA 한국어판: 그로텐디크의 『대수기하학 원론』(Éléments de géométrie algébrique)

알렉상드르 그로텐디크(Alexandre Grothendieck)가 장 디외도네(Jean Dieudonné)의 협력을 받아 쓴 『대수기하학 원론』
(*Éléments de géométrie algébrique*, EGA)의 한국어 번역입니다. 원문은 1960–1967년에 *Publications mathématiques
de l'IHÉS* 4, 8, 11, 17, 20, 24, 28, 32호로 나왔습니다. 이 저장소에는 EGA I, II, III(제0장 §§1–13 포함)의 완역과,
EGA IV 제1분책 가운데 제0장 §§14–23과 제IV장 §1의 번역이 있습니다.

## 만든 방법

번역, 교정, 편집, 조판은 AI가 했습니다. EGA I–III 누적판은 OpenAI Codex의 GPT-5.6 Sol(Ultra 추론 강도)이
전사, 번역, 교정, 편집, 조판했습니다. EGA IV 제1분책은 OpenAI Codex의 GPT-5.6 Sol이 번역하고 GPT-6 Astra가
검토·교정·조립했습니다(Ultra). 번역의 기준은 프랑스어 원문이며, 영어 공동체 번역(ryankeleti/ega)을 참고 자료로
썼습니다(「출처와 기여」 참조). 공개판 PDF는 같은 결과가 바이트 단위로 재현되도록 빌드했습니다([BUILD.md](BUILD.md)).

## 상태

EGA I–III은 완역되었고, EGA IV는 제1분책의 일부만 번역되었습니다. 오류가 남아 있을 수 있습니다.

## 다른 언어판

- 프랑스어: [ega-fr](https://github.com/KokunoYumeto/ega-fr) — 원 인쇄본의 완전한 전사(외교판과 교정판).
- 영어: [ega-en](https://github.com/KokunoYumeto/ega-en) — 완역(서론, 제0장–제IV장).
- 스페인어: [ega-fga-es](https://github.com/KokunoYumeto/ega-fga-es) — EGA II, EGA III, EGA IV 제3·4분책;
  EGA IV 제1분책은 제0장만.
- 브라질 포르투갈어: [ega-fga-sga-pt-br](https://github.com/KokunoYumeto/ega-fga-sga-pt-br) — EGA II, EGA III
  제1분책, EGA IV 제3분책, EGA I 제I장; 나머지는 일부 절만.
- 베트남어: [ega-fga-sga-vi](https://github.com/KokunoYumeto/ega-fga-sga-vi) — EGA II, EGA III 제1분책,
  EGA I 제I장; 나머지는 일부 절만.
- 중국어(간체): [ega-zh-hans-cn](https://github.com/KokunoYumeto/ega-zh-hans-cn) — EGA I–III; EGA IV 제1분책의
  제0장 §§14–23과 제IV장 §1.

이 프로젝트의 EGA, FGA, SGA 판 전체 목록은 [ega-fga-sga](https://github.com/KokunoYumeto/ega-fga-sga)에 있습니다.

## 내용

- [누적 PDF](reader/00_EGA_ko_CUMULATIVE_READER.pdf): EGA I(제0장 §§1–7 포함), EGA II, EGA III 제1분책(제0장
  §§8–13 포함)과 제2분책.
- [편집 가능한 누적 LaTeX](01_EGA_ko_CUMULATIVE.tex): 누적판 본문 전체를 한 파일에 담았습니다.
- [전체 소스 ZIP](02_EGA_ko_COMPLETE_SOURCES.zip)과 [source/](source): 모듈식 원본(`source/main.tex`). 빌드 방법은
  [BUILD.md](BUILD.md)에 있습니다(XeLaTeX, `BUILD.ps1`).
- [editions/EGA_IV_1](editions/EGA_IV_1/README.md): EGA IV 제1분책의 편집 가능한 번역(`xelatex main.tex`).
- 이전 판은 [GitHub 릴리스](https://github.com/KokunoYumeto/ega-ko/releases)와 [release/](release) 폴더에 있습니다.

## 출처와 기여

- 원전: Alexandre Grothendieck, avec la collaboration de Jean Dieudonné, *Éléments de géométrie algébrique*,
  *Publications mathématiques de l'IHÉS* (1960–1967), [NUMDAM](https://www.numdam.org/journals/PMIHES/). EGA IV
  제1분책은 *Publications mathématiques de l'IHÉS* 20 (1964), 5–259쪽
  ([프랑스어 원문](https://numdam.org/item/PMIHES_1964__20__5_0/))입니다.
- 참고 자료: [프랑스어 EGA 판](https://github.com/KokunoYumeto/ega-fr/releases/tag/ega-fr-2026-10-24-r19)과 영어
  공동체 번역 [ryankeleti/ega](https://github.com/ryankeleti/ega/tree/3d7afe28c99d1887ccdb85acf2ca1afd93fb1971)
  (버전 3d7afe2). 영어 번역의 기여자는 Mateo Carmona, Tim Holzschuh, Tim Hosgood, Ryan Keleti, Thiago Solovera &
  Nery, Wayne Yang이며, 각자의 기여 범위는
  [절별 기여 목록](https://github.com/ryankeleti/ega/blob/3d7afe28c99d1887ccdb85acf2ca1afd93fb1971/README.md)에
  있습니다. 이들은 한국어 번역의 번역자가 아닙니다.
- EGA IV 제1분책은 프랑스어 TeX의 수학 기호와 원본 레이블을 그대로 씁니다.

## 권리

출판자가 AI가 만든 번역, 교정, 조판에 대해 권리를 가지는 범위에서, 그 권리는
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/deed.ko)에 따라 퍼블릭 도메인에 헌정합니다. 이 헌정은
원저작물과 위에 적은 인간 번역에 대한 권리에 영향을 주지 않으며, 그것들을 이용할 권한을 부여하지 않습니다.
전체 고지: [LICENSE](LICENSE).
