# Korean algebraic-geometry terminology witnesses — 2026-08-23

This is a bounded, read-only terminology check requested during Korean EGA
production. The papers are primary mathematical sources hosted by arXiv; they
are terminology witnesses, not Korean-language authority and not substitutes
for the canonical French EGA source.

## Downloaded sources

| arXiv | title | local PDF | PDF SHA-256 | extracted text SHA-256 |
|---|---|---|---|---|
| [1505.01307](https://arxiv.org/abs/1505.01307) | *On Noetherian schemes over (C, tensor, 1) and the category of quasi-coherent sheaves* (Abhishek Banerjee, v4) | `1505.01307.pdf` (337,447 bytes) | `8A74E70E4A787EB6008570C633026E87E7B8DA19D93A3BAA61424AB12D74F1B6` | `494F25C6967139F4335AFE19865745537922FDD81CB5C5CE932D533F42516CFB` |
| [0706.0493](https://arxiv.org/abs/0706.0493) | *The derived category of quasi-coherent sheaves and axiomatic stable homotopy* (Alonso, Jeremias, Perez, Vale, v3) | `0706.0493.pdf` (312,459 bytes) | `71314400E6175A4A69B064909C3B4EF5CEB16C9F03716CD5703762D2B357A3E9` | `12E588328F1F01CEA6C4CE724B1D4ECA6E45BE78EF1DFFAFAB2BACCD83DF2DE2` |
| [math/0307189](https://arxiv.org/abs/math/0307189) | *Bousfield localization on formal schemes* (Alonso, Jeremias, Souto, v2) | `math-0307189.pdf` (265,424 bytes) | `E71FDA5D3348E83D8C955A7AA226CB8815C16B4402BDBBBBCC979F4412663DD1` | `003AEBF9CCD292263BD0FF1EE89FA5F3C54E80069E79E04B7DAA3DEDBBF25EF9` |

The extracted `.txt` files were produced with UTF-8 Poppler extraction and
are retained beside the PDFs for bounded grep/context review.

## Findings applied to the workflow

The sources repeatedly preserve the distinctions among **quasi-compact**,
**quasi-separated**, **semi-separated**, **Noetherian**, **quasi-coherent**,
**formal scheme**, **ideal of definition**, **underlying space**, **adic**,
**support**, **morphism**, **restriction**, and **completion**. In particular:

- semi-separated is used for the affine-diagonal/intersection-of-affines
  condition; it is not silently changed to separated;
- formal scheme, ordinary scheme, underlying space, and ideal of definition
  remain typed as different objects;
- quasi-coherent torsion and ordinary quasi-coherent sheaves remain distinct;
- completion and support remain typed constructions, not generic “compactness”
  or an unqualified completion of global sections.

The Korean lane therefore keeps its existing locked forms (`준콤팩트`,
`준연접`, `뇌터`, `형식적 스킴`, `정의 아이디얼`, `바탕공간`, `준아딕`,
`분리 완비화`, and typed `사상`/`연속사상`) and checks every new term against
the French definition and these English usage witnesses. The arXiv papers do
not authorize a Korean spelling by themselves; any Korean change still needs
definition-level evidence in `terms.jsonl` and source-bound review.

## Reusable rule

Before admitting a new Korean term or translating a later SGA/FGA unit, run a
bounded search in these retained texts (or an updated, explicitly logged set of
primary papers), compare the exact object/property type with the French source,
record the decision in the external ledgers, and rerun formula/structure/build/
visual gates. Do not use a surface CJK cognate as Korean authority.
