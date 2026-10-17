# devtui Helix edition

The `helix-prototype` branch contains the migrated terminal IDE. It installs alongside, rather than replacing, Neovim devtui. The branch name is retained for review; the editor now has a persistent Explorer, not merely a file-picker overlay.

## Audit and scope

[MAIN_FEATURE_AUDIT.md](docs/MAIN_FEATURE_AUDIT.md) contains 160 traceable audit checkpoints derived from the actual Neovim `main` source and explicit configuration. It records baseline differences, VS Code reference behavior, Helix implementation locations, and test entry points. This count is a checklist, not 160 independently invented Neovim features.

The migration covers editor lifecycle, Explorer mouse/keyboard selections and safe file actions, real-time column editing, VS Code-style shortcuts/find/replace, running-instance file navigation, the Git pane, visual extras, language services, debugging, environment isolation and reproducible deployment.

See [PARITY.md](docs/PARITY.md), [VSCODE_REFERENCES.md](docs/VSCODE_REFERENCES.md), [VALIDATION.md](docs/VALIDATION.md), and the machine-readable [feature-audit.json](docs/feature-audit.json). Unsupported host-specific toolchain adapters and functionality never added to Neovim main are not counted as migrated.

## Install/update alongside Neovim

From this branch, with the existing devtui Zellij/Lazygit dependencies:

```bash
./prototype/helix/scripts/install-system-deps-ubuntu.sh
./prototype/helix/install-prototype.sh
devtui-helix --version
devtui-helix --health cpp
devtui-helix /path/to/project
```

For a fresh workstation, read [DEPLOYMENT.md](docs/DEPLOYMENT.md) first. Config-only mode does not update the editor binary, WASM plugin, or language tools.

## Everyday behavior

Single-click a tree file to reuse Preview while retaining tree focus. Double-click or press Enter to keep it open and focus the editor. Edit with `i`; `Esc` leaves Insert mode. Middle-drag creates native multi-selections; typing and Insert-mode arrows act on all cursors immediately.

Dirty close offers Save / Don't Save / Cancel. `[No Name]` uses Save As. `q`, `q!`, `wq`, and `x` operate on the document while preserving the editor/sidebar structure. Ctrl-Q exits the whole Zellij session. Double-click the empty tab strip to create another Untitled editor.

Use Ctrl-F for literal, case-insensitive Find by default. Its case/word/regex controls can be clicked or toggled with Alt-C/W/R. Ctrl-H replaces in the current document without automatically saving. Ctrl-Shift-H applies explicit workspace replacements. Terminal paste replaces selections as one undoable transaction; rows spread when their count matches the cursor count.

The shell pane inherits the caller's exported environment and does not re-run shell startup files. Project-selected Python settings apply only to editor services. Toolchain compilers and compilation databases remain the project's responsibility.

## Validation

Run the bundled [acceptance tests](tests/README.md), rather than relying on the displayed upstream version alone. `devtui-helix --version` reports the patched source tree and binary fingerprint. Replacing a Rust executable does not update a running process: restart an existing Helix session after installing an update.
