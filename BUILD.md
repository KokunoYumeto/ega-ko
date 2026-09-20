# Rebuilding the Korean cumulative EGA reader

The exact released reader was produced from `source/main.tex` with XeLaTeX,
Malgun Gothic, the standard AMS packages, Xy-pic, TikZ-CD, and a machine-wide
`Global\InterlanguageTeXSlotV1` mutex. Run `BUILD.ps1` on Windows for the
modular source. Run `BUILD.ps1 -Direct` to compile the fully assembled direct
source `01_EGA_ko_CUMULATIVE.tex`. Both forms contain the same ordered text.

The released build used four passes with `SOURCE_DATE_EPOCH=1789862400`,
`FORCE_SOURCE_DATE=1`, and `TZ=UTC`; passes three and four were byte-identical.
The complete source tree includes the master, all 21 ordered inputs, the
coverage manifest, this build note, and the portable build script. There are
no external figures, bibliography databases, styles, or unpublished inputs.
