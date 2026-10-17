# Unified editor context actions

The editor previously chose between a selection-only Copy/Cut/Delete menu and
a separate symbol menu. It did not implement text double clicks, expose Paste,
or offer formatting in either menu. Copying an unterminated final line also
omitted the newline expected by the default empty-selection clipboard behavior.

## Verified upstream behavior

The pinned VS Code editor controller dispatches a double click to word
selection. Its default separator classes keep underscores and non-ASCII
identifier characters inside a word; whitespace and separator runs have their
own boundaries. This does not depend on the C/C++ extension.

Navigation, formatting and clipboard contributions register in the same
EditorContext menu. Right-clicking inside an existing selection preserves it;
clicking outside moves the caret. With the default emptySelectionClipboard
option, Copy copies a whole line and appends the document line ending, even at
an unterminated final line. Linewise Paste preserves the original caret column.

Format Document requires an available document formatter. Format Selection is
shown for a nonempty selection and requires range-formatting capability. The
Microsoft C/C++ extension supports clang-format and vc_format; its range
provider forwards the returned edits. VS Code applies provider edits without
clipping them to the original selection. clang-format can extend a region to a
larger syntactic entity, so formatting may legitimately change nearby code.

VS Code source revision: `e97039dd9293ef2b9df8876d0bc8c0c8ff87f871`.
The exact editor source paths, URLs and hashes are in
[vscode-reference-manifest.json](vscode-reference-manifest.json).
C/C++ extension references have an independent pinned revision recorded in
[cpp-format-references.json](../tests/cpp-format-references.json).
The clang-format behavior is also documented in the official
[ClangFormat guide](https://clang.llvm.org/docs/ClangFormat.html).

## Implementation

Editor mouse and keyboard requests now share one menu and action dispatcher.
The menu includes navigation, clipboard and formatting actions and uses the
available viewport height before scrolling. The existing pointer placement and
edge avoidance remain active. Single-character selections and column carets
are distinguished from Helix's modal block cursor.

Double clicks select the word under the terminal cell. Word drags extend by
whole words. Click state is scoped to the document, view, cell and interval;
keyboard input, modifiers, dragging and clicks on another surface break a
pending double click.

Copy keeps the selection or caret in place. Empty-selection copies append the
correct line ending and retain linewise Paste metadata. Clipboard cache checks
now require exact equality, preventing a changed external clipboard such as
`alpha` becoming `alphabet` from being truncated to the old cached text.

Paste reads the configured clipboard provider and uses the same selection
replacement and row-spreading transaction as terminal Paste. The default
`termcode` provider writes OSC52 but cannot read the client clipboard; it can
reuse text copied in the editor. When no text is available, the status explains
that terminal Paste is the external-text path. Providers with read support can
paste external clipboard contents through the menu.

For C/C++, Format Document uses the configured clang-format command and passes
the absolute source filename so file type and project style discovery are
correct. Format Selection uses clangd's range formatter, backed by clang-format.
A range-only LSP provider is also accepted. Touching input ranges are merged;
if returned edits overlap, their requested ranges are combined and recomputed.
Returned edits are retained in full. Formatting has its own undo boundary,
keeps the buffer unsaved and reports provider errors. Stale results are dropped
when the document changes or an explicit format's view switches documents.

## Validation

The source-derived word oracle verifies 20 cases, and the context-menu layout
oracle verifies 14 placements with the unified menu dimensions. The new PTY
suite covers 18 methods and 45 case combinations, including real C++ formatters
and controlled language-server responses.

All 41 patches were applied to a fresh pinned upstream checkout, the canonical
source tree was verified, and an offline locked Release build was installed
atomically. The runtime sources are unchanged.

| Suite | Methods | Result |
| --- | ---: | --- |
| Unified editor interactions | 18 | PASS |
| Pointer context menus | 8 | PASS |
| Terminal interaction | 31 | PASS |
| Strict parity | 38 | PASS |
| Permanent deletion | 9 | PASS |
| Unicode column selection | 8 | PASS |
| Isolated deployment | 6 | PASS |
| Total | 118 | PASS |

The six application suites ran against the installed Release. Deployment
checks use disposable configuration. The feature audit passes with 160
checkpoints and 44 pinned source references. Exact methods, durations, source
oracles, formatter versions and fingerprints are recorded in
[editor-context-results.json](editor-context-results.json).

Installed source tree: `929c11e7db13cd8082aafce6d95f6099ae86813d`.
Binary SHA-256: `0581646e4318f89c5b1d917ffa0fa3303ad7a242784066bb2f73bcc3c1edf9c8`.

Restart `devtui-helix` to load the updated binary.
