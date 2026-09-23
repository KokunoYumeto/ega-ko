# 한국어 EGA 누적 독자판 재현 빌드

이 정확판은 `source/main.tex`에서 XeLaTeX, 맑은 고딕, 표준 AMS 패키지,
Xy-pic, TikZ-CD 및 기계 전역 뮤텍스 `Global\InterlanguageTeXSlotV1`을
사용하여 만들었다. Windows에서 모듈식 원본을 빌드하려면 `BUILD.ps1`을
실행한다. 완전히 합쳐진 직접 원본 `01_EGA_ko_CUMULATIVE.tex`을 빌드하려면
`BUILD.ps1 -Direct`를 실행한다. 두 방식은 같은 순서의 본문을 포함한다.

공개판 빌드는 `SOURCE_DATE_EPOCH=1790121600`, `FORCE_SOURCE_DATE=1`,
`TZ=UTC` 아래 네 번 실행되었으며 제3·4회 결과가 바이트 단위로 동일했다.
완전 원본 트리는 주 파일, 순서가 고정된 입력 22개, 범위 명세, 이 빌드
설명과 이식 가능한 빌드 스크립트를 포함한다. 외부 그림, 별도 참고문헌
데이터베이스, 비공개 스타일 또는 비공개 입력은 없다.
