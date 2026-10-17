# Unicode column-selection correction

## Confirmed behavior

VS Code column selection is aligned in visible columns, not identical character
indices on every line. A short line that intersects the rectangle is selected
through its end. Only a row entirely outside the rectangle is skipped; when all
rows are beyond EOL, each contributes an EOL caret. Character positions use
half-open ranges, so a line with 39 characters ends at column 40.

A user-reported mixed CJK/ASCII document was tested using an isolated temporary
copy. Its first-line character column 28 maps to visible column 41 (zero-based).
The corresponding fifth-line range is character columns 32–40, not 28–40.
The old installed binary omitted that row; the corrected binary matches the
pinned VS Code source output for copy and replacement. No original document
content or machine-specific path is included in this repository.

## Causes and corrections

1. The old row filter compared the snapped left boundary against the requested
   left column. Inside a CJK character or Tab, snapping can move that boundary
   left even though the row intersects the rectangle. Both snapped boundaries
   now determine intersection.
2. Ordinary pointer hit testing always chooses the start of a glyph. Column
   selection now chooses the nearest rendered grapheme boundary, with ties
   going to the preceding boundary, matching VS Code. It uses the formatter's
   cells, horizontal viewport offset and wrapped rows.
3. The previous Unicode width dependency counted components of complex emoji
   separately. The pinned sequence-aware version treats ZWJ, skin-tone and flag
   graphemes consistently in rendering and hit testing.
4. Scrolloff adjustments during a drag moved its screen-space anchor. Cursor
   visibility adjustments now occur after release.
5. Helix normalizes empty carets into modal block ranges. The logical selection
   is retained and validated against the active document, view and normalized
   range bounds, including Insert-mode direction reversal. Typing, paste,
   arrow movement, copy and cut preserve participating empty carets.
6. With VS Code's default `emptySelectionClipboard=true`, participating empty
   carets copy/cut their entire line; rows excluded from the rectangle do not.

## Evidence and scope

Expected results come from executing fixed VS Code revision
`e97039dd9293ef2b9df8876d0bc8c0c8ff87f871`, with source hashes in
[vscode-reference-manifest.json](vscode-reference-manifest.json).
The adapter and fixtures live in `../tests/vscode_column_oracle.mjs` and
`../tests/column-selection-cases.json`. The algorithms, including Unicode
segmentation, are the upstream code; only their model/data containers are
adapted to the isolated test environment.

The 19 fixtures cover CJK, Japanese, Korean, fullwidth punctuation, accented
letters, combining marks, emoji, ZWJ/skin-tone/flag sequences, Tabs, mixed-width
short lines, sparse rows, EOL fallback and collapsed interior boundaries.
Four drag directions plus editing/viewport checks give 96 case combinations
across 8 real-PTY unittest methods. These do not claim exhaustive Unicode,
proportional-font, bidi or host-terminal rendering equivalence.

## Release verification

The clean upstream tree accepted all 34 ordered patches and matched
`f5af604b88198b97bb98c50e71d2c2aff6f33414`. A locked, offline Release build
was installed with an atomic executable replacement. Existing sessions were
not terminated. Runtime files were unchanged; their source tree was compared
against the previous installed build, so existing parser artifacts were reused.

| Installed-build verification | Result |
| --- | --- |
| Unicode column-selection suite | 8/8 methods; 96 case combinations passed |
| Existing terminal suite | 31/31 passed |
| Existing strict behavior suite | 38/38 passed |
| Executed VS Code source fixture verification | 19/19 matched |
| Isolated reported-document copy / replacement | 3 coordinate variants matched |
| Core and terminal rendering Rust tests | 265 passed; 3 existing doctests ignored |

Exact test names, source hashes and build provenance are in
[unicode-column-results.json](unicode-column-results.json). The installed binary
SHA-256 is `802575a4df5051c0970c94b7259d6eefe87d0ceea136028b61aa306a7475f373`.
Restart an existing `devtui-helix` process to load this executable; verify its
source-tree fingerprint with `devtui-helix --version`.
