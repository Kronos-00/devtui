# Final migration acceptance

The subsequent permanent-delete and status-row correction is recorded in [DELETE_BEHAVIOR.md](DELETE_BEHAVIOR.md).

This is the original migration acceptance snapshot. The subsequent Unicode column-selection correction and its installed-build evidence are recorded in [UNICODE_COLUMN_SELECTION.md](UNICODE_COLUMN_SELECTION.md).

This report supersedes the early overlay-picker prototype results. The migrated edition now includes the persistent Explorer and complete portable custom-feature scope recorded in [MAIN_FEATURE_AUDIT.md](MAIN_FEATURE_AUDIT.md). Machine-readable executed results, test names and build provenance are in [acceptance-results.json](acceptance-results.json).

## Frozen inputs and installed build

| Input | Verified value |
| --- | --- |
| Neovim main baseline | `b10574bee0c85ef6ed51b620729d212760ee2520` |
| Baseline files hashed | 45 |
| Audit checkpoints | 160 |
| VS Code source revision | `e97039dd9293ef2b9df8876d0bc8c0c8ff87f871` |
| Pinned source reference files | 21, downloaded and SHA-256 verified |
| Helix upstream | `ba40e547426b0f9896c8bdc699a4ab11f2b37dbc` |
| Ordered patches | 32 |
| Canonical patched source tree | `9d038c3072a7d71ab177e8228ba92b97eaa6eed6` |
| Release build Rust | 1.95.0 |
| Tested installed binary SHA-256 | `87d69c3fc2cc2068454078ac96e22fb9d501a1a78e07148216acdc1729340aa5` |

The final binary was built with Cargo's lockfile from a fresh worktree of the pinned upstream after applying every patch in `patches/series` once. `apply-patches.sh` checks the result against `HELIX_TREE` and aborts on mismatch. The binary was installed by atomic rename, then the entire acceptance batch ran again against the installed binary and matching runtime. All 46 captured Neovim configuration/launcher files remained unchanged.

The binary fingerprint identifies this audited build; it is not a claim that different host paths or linkers will produce identical executable bytes. The canonical source tree is the portable reproducibility check.

## Executed final suites

| Suite | Result | Coverage |
| --- | --- | --- |
| `terminal_regression.py` | 31 / 31 | PTY mouse/keys, tabs, previews, saves, safe file operations, column editing, IPC, Markdown, scrollbar |
| `strict_parity.py` | 38 / 38 | Exact selection boundaries, clipboard replacement, focus, search defaults, replacement persistence, edge filenames |
| `deployment_regression.py` | 6 / 6 | Isolated homes, backups, unchanged shell startup, exported environment, helper isolation, banner lifecycle |
| `language_editor_regression.py` | 1 / 1 | Actual editor clangd definition, rename and overview diagnostics |
| `editor_debugger_regression.py` | 2 / 2 | Editor F9/F5/debug controls, selected Python environment, terminal foreground isolation |
| Terminal-link native tests | 15 / 15 | Highlight/parse paths, quoted and Unicode names, environment expansion, line/column formats |

The Python suites above contain **78 test methods**. Subcases are not added again to inflate that count. The terminal-link crate contributes **15 separate native tests**. The following are additional protocol/workspace checks, not counted as extra Python test methods:

- Language/service initialization: clangd, Pyright, Bash, CMake, Ruff, debugpy and LLDB DAP; isolated CMake/debugpy runtime checks also passed. clangd inactive-region notifications were received and verified.
- Real debuggee tests: disposable Python and compiled C programs reached a breakpoint, reported a call stack and variables, stepped, continued and terminated through debugpy / LLDB DAP.
- Complete installed workspace: a disposable Zellij session showed Explorer, shortcut banner and Git pane, recorded its editor pane, and opened an external file in that existing pane.
- Manifest audit: all 45 baseline files and 160 checkpoints, 21 reference entries, 32 ordered patches, implementation paths and named regression links were valid; the applied source tree matched the canonical tree.
- Terminal-link WASM: installed bytes and both source-patch hashes matched its build fingerprint.

## Independent final audit defect and retest

The final source review found that duplicate-name generation accepted suffixes that VS Code treats as literal names and mishandled zero. More seriously, saturating a numeric counter could retry the same existing filename forever. Four suffix subcases were first reproduced as failures on the old binary. The fix follows `fileActions.incrementFileName` and `Constants.MAX_SAFE_SMALL_INTEGER`, adds a new name suffix when the integer limit is reached, and checks the next distinct candidate.

The release now passes ten focused subcases across three added tests: zero counters, absent/multiple spaces, an empty prefix, large counters, existing numbered copies, dotfiles and compound extensions. Every pre-existing suite was then rerun, not only the added tests.

## What "complete migration" covers

Every in-scope checkpoint has an implementation or an explicitly reused component, plus baseline/source references and verification entry points. This is not a promise that all imaginable edge cases are bug-free or that a 160-row checklist equals 160 independent end-to-end tests.

Persistent editor/Explorer regions, modal `i`/`Esc`, Ctrl-Q session exit, alternate tree Alt-click, Alt-G, visible ignored files and root-relative `.` remain explicit devtui choices. They are not represented as VS Code defaults. Host terminal permissions/keyboard reporting, arbitrary project compiler databases and hardware debugging need their actual host/project configuration. Plain terminal clipboard text cannot preserve private GUI rich-clipboard metadata.

## Repeat the verification

Follow [tests/README.md](../tests/README.md). Check `devtui-helix --version` for the canonical source tree and local binary hash. A config-only install does not update the compiled editor. Restart an existing Helix session after updating; installation does not terminate unsaved editor sessions. Neovim main remains the unchanged parallel fallback.
