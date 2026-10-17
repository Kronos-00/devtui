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
