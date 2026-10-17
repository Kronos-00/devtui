# Repeatable migration acceptance

These tests exercise disposable projects, real PTYs, terminal mouse/key input,
rendered selections, clipboard output, saved files and actual protocol clients.
They never use the caller's project for destructive file or Git operations.

## Environment

Create an isolated test environment; use `-I` to avoid importing a caller's
Python startup path:

```bash
python3 -m venv .venv-tests
.venv-tests/bin/python -I -m pip install -r prototype/helix/tests/requirements.txt
```

Install the Helix edition and its language tools before running the suites.
A config-only install does not provide the patched binary or language tools.

```bash
HX="$HOME/.local/opt/devtui/helix-prototype/bin/hx"
RT="$HOME/.local/opt/devtui/helix-prototype/runtime"
TOOLS="$HOME/.local/opt/devtui/helix-tools/bin"
PY=.venv-tests/bin/python
$PY -I prototype/helix/tests/terminal_regression.py --binary "$HX" --runtime "$RT"
$PY -I prototype/helix/tests/strict_parity.py --binary "$HX" --runtime "$RT"
$PY -I prototype/helix/tests/delete_regression.py --binary "$HX" --runtime "$RT"
$PY -I prototype/helix/tests/context_menu_regression.py --binary "$HX" --runtime "$RT"
$PY -I prototype/helix/tests/editor_context_regression.py --binary "$HX" --runtime "$RT"
$PY -I prototype/helix/tests/cpp_properties_regression.py --binary "$HX" --runtime "$RT"
$PY -I prototype/helix/tests/column_selection_regression.py --binary "$HX" --runtime "$RT"
$PY -I prototype/helix/tests/deployment_regression.py
$PY -I prototype/helix/tests/service_smoke.py --tools "$TOOLS"
$PY -I prototype/helix/tests/debugger_regression.py --tools "$TOOLS"
$PY -I prototype/helix/tests/language_editor_regression.py --binary "$HX" --runtime "$RT" --tools "$TOOLS"
$PY -I prototype/helix/tests/editor_debugger_regression.py --binary "$HX" --runtime "$RT" --tools "$TOOLS"
$PY -I prototype/helix/tests/audit_manifest.py
$PY -I prototype/helix/tests/workspace_smoke.py
```

`terminal_regression.py` and `strict_parity.py` accept `--filter NAME` for a
focused rerun. Protocol tests require the configured native tools. Real C
process debugging requires permission to trace a disposable child process.

## Evidence interpretation

The feature inventory contains 160 review checkpoints, not 160 independent
end-to-end tests. A test can exercise several checkpoints. The inventory links
baseline code, VS Code references and migration code; the acceptance report
separately records executed suites and their outcomes.

The debugger suite actually launches temporary Python and C programs, verifies
a breakpoint, stack frames and variables, steps, continues and terminates.
Language initialization is not counted as proof of arbitrary project builds or
hardware debugging. The editor-language suite also checks clangd navigation,
rename edits and overview diagnostics through the actual editor UI.

The Git UI is the existing pinned Lazygit integration, not a new Git engine.
Host clipboard permissions and Windows Terminal input forwarding still need to
be configured on the host; these cannot be inferred from Linux PTY results.

## Build provenance

`devtui-helix --version` prints the installed source-tree and binary hashes.
The editor's `build-info.json` records the ordered patches. The terminal-link
plugin has a separate JSON fingerprint alongside its WASM file. A clean source
build must apply `patches/series` exactly once and match the audited tree.

The workspace smoke test starts and stops only its own disposable named Zellij session. It checks the installed layout, banner, Git pane and navigation helper. It does not automatically grant terminal-link plugin permissions or claim to emulate a host mouse Alt-click.

The editor-debugger suite additionally exercises F9/F5 and debug menu controls inside Helix, checks that the editor retains its terminal foreground group, and verifies the selected virtual environment is used by the debuggee.

To additionally verify an applied source checkout against `HELIX_TREE`, run `audit_manifest.py --source /path/to/applied/helix`. This checks implementation paths, patch order inventory and named regression references, not merely whether a checklist file exists.

## Unicode column-selection oracle

`column_selection_regression.py` checks 19 source-derived fixtures in all four
horizontal/vertical drag directions (76 combinations). Additional cases cover
mixed empty carets, clipboard/cut, Unicode typing and undo/redo, bracketed paste,
arrow collapse, horizontal scrolling, right-edge scrolloff and soft wrapping.
There are 8 unittest methods and 96 case/direction combinations in total.

`column-selection-cases.json` is computed by executing pinned VS Code
`ColumnSelection`, `CursorColumns`, string/grapheme utilities, copy and cut code.
The Node adapter supplies only model access and data containers; it does not
reimplement those algorithms. Source hashes are checked before execution.
Default `emptySelectionClipboard=true` is used. To independently verify:

```bash
node --disable-warning=ExperimentalWarning prototype/helix/tests/vscode_column_oracle.mjs /path/to/reference-cache --fetch
```

Node 24 or newer is required for its built-in TypeScript transform. Omit `--fetch`
to verify offline against an existing cache. `--write` deliberately regenerates
the fixture after reference changes; normal runs compare without changing it.
All committed fixtures use generic text. User documents are tested only through
isolated temporary copies and are never embedded in the test suite.

## Explorer deletion and status-row regression

`delete_regression.py` uses only disposable files. It verifies one permanent
confirmation, cancellation, recursive and multiple-item deletion, symlinks,
concurrent removal, open-buffer cleanup and preserved terminal geometry.
A stub `gio` proves that neither its presence nor its exit status affects the
terminal provider. Multiline and overlong status messages must stay on one row.

The permission-error fixture runs the same editor binary against a directory
without write permission. When the test runner is root on Linux, only the
fixture's forked child drops to numeric uid/gid 65534; readable binary/theme
copies are placed in its temporary directory. It does not change the caller's
identity, configuration or project permissions.

## Pointer context menus

`context_menu_regression.py` checks Explorer, editor-symbol and selection
context menus at multiple mouse positions and edges. It validates the actual
rendered menu frame, mouse action targets, multiselection preservation,
repeated outside right clicks, cross-region retargeting, resize and short-view
scrolling. Confirmation dialogs and keyboard context requests cannot inherit a
previous mouse anchor. There are 8 unittest methods and 16 case combinations.

The 14 geometry fixtures in `context-menu-cases.json` are generated by executing
pinned VS Code `layout2d` and its `Range` dependency, using one terminal cell as
the mouse anchor. Node 24+ independently verifies the source-derived fixtures:

```bash
node --disable-warning=ExperimentalWarning prototype/helix/tests/vscode_context_menu_oracle.mjs /path/to/reference-cache --fetch
```

Omit `--fetch` for an offline cache check; `--write` deliberately regenerates
fixtures. The shared PTY helper matches exact menu labels inside the visible
menu rectangle, allowing background text outside a moved menu on the same row.


## Unified editor interactions

`editor_context_regression.py` has 18 methods and 45 case combinations. It
checks double-click words and word drags, shared navigation/clipboard menus,
whole-line copy including an unterminated final line, Paste through a disposable
clipboard provider, linewise metadata, external clipboard changes and one-step
undo. It also runs real clang-format and clangd formatting against a project
style, plus isolated LSP fixtures for range-only capability, UTF-16 requests,
overlapping expanded ranges, failures and delayed/stale responses.

The 20 word fixtures execute the pinned upstream `WordOperations.word` and its
real character classifiers. Cursor-state records and the single-line model are
minimal harness objects; the selection algorithm is upstream. The default
separator set and empty word-segmenter locale list are used.

```bash
node --disable-warning=ExperimentalWarning prototype/helix/tests/vscode_editor_word_oracle.mjs /path/to/reference-cache --fetch
```

As with the layout oracle, omit `--fetch` for offline validation, and use
`--write` only when intentionally regenerating the source-derived fixtures.
The fixture provider and custom clipboard programs run only inside disposable
test configuration and directories. They do not modify the caller's settings.
The default terminal clipboard provider cannot read external clipboard text;
menu Paste can reuse editor-copied text, and terminal bracketed Paste remains
the external-text path for that provider.

## Workspace C/C++ properties

`cpp_properties_regression.py` has 14 methods. A recording server verifies exact
compile commands, initialization settings and command-before-didOpen ordering.
A proxy to real clangd verifies diagnostics and definition navigation under
different macro, header and database configurations. Workspace priority,
external-project isolation, JSONC variables, configuration selection, fallback,
warnings, C/C++ standards and `:lsp-restart` reload are covered. The fixtures
use disposable projects and configuration; they do not edit user projects.
The matching translator unit tests are selected with
`cargo test -p helix-lsp cpp_properties` in an applied source checkout.
See [CPP_PROPERTIES.md](../docs/CPP_PROPERTIES.md) for supported fields and limits.

## Workspace shortcut window

```bash
$PY -I prototype/helix/tests/shortcuts_regression.py \
  --zellij "$HOME/.local/opt/devtui/helix-prototype/bin/zellij" \
  --plugin "$HOME/.local/share/devtui/devtui-shortcuts.wasm" \
  --assets "$HOME/.local/opt/devtui/helix-prototype/share/zellij"
python3 prototype/helix/shortcuts/generate.py --check
```

The 16 window methods use disposable named sessions and pane surfaces that log
only their own input. They verify actual native window geometry, title dragging,
all eight resize handles, z-order, close cleanup, singleton requests, responsive
columns, Unicode search and shifted-key input, scrolling and terminal resizing.
They also verify existing control-key and Ctrl/Alt/middle-mouse passthrough.
Only sessions created by a test are stopped. The suite never closes a user's
workspace. The full installed workspace is checked by `workspace_smoke.py`.
