# devtui

A reproducible terminal IDE built around Zellij, Neovim/LazyVim, Snacks Explorer, Bufferline, multicursor.nvim, Lazygit, and OSC 52 clipboard integration.

The project focuses on a VS Code-like interaction model while remaining fully terminal-native:

- persistent Explorer + editor workspace
- single-click preview editors and double-click pinned editors
- dirty editor close confirmation: **Save / Don't Save / Cancel**
- `[No Name]` editors and double-click-to-create on empty tab-strip space
- Explorer single/multi-selection with Ctrl/Alt + click
- middle-mouse column selection and multi-cursor editing
- right-click Explorer actions and editor symbol actions
- resizable Explorer with persistent width
- clickable terminal file paths that open in the existing editor
- protected Explorer/editor regions so files can close without dismantling the IDE layout
- shell pane that inherits the launching environment without re-reading shell startup files
- Markdown source punctuation kept visible

## Pinned versions

| Component | Version |
| --- | --- |
| Neovim | 0.12.6 |
| Zellij | 0.45.1 + devtui mouse patch |
| Lazygit | 0.66.1 |
| Rust toolchain used for Zellij | 1.95.0 |
| LazyVim/plugins | pinned by `config/nvim/lazy-lock.json` |

## Quick start

Ubuntu 24.04 / Linux x86_64:

```bash
git clone git@github.com:Kronos-00/devtui.git
cd devtui
./scripts/install-system-deps-ubuntu.sh
./install.sh
export PATH="$HOME/.local/bin:$PATH"
devtui
```

The installer backs up replaced configuration under `~/.local/state/devtui/backup-*`.

For a complete deployment walkthrough, terminal requirements, permissions, validation, and update procedure, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Environment behavior

The shell pane deliberately does **not** source `~/.bashrc`, `~/.profile`, SDK setup scripts, or other startup files. It inherits exported variables from the shell that launched `devtui`, removes only devtui's private RPC bookkeeping variables, and starts:

```bash
bash --noprofile --norc -i
```

This makes the shell pane predictable: prepare any project environment before launching devtui, or configure it manually inside the pane.

## Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ shortcut banner                                              │
├───────────────────────────────┬──────────────────────────────┤
│ Neovim                       │ Lazygit                      │
│ Explorer │ editor            ├──────────────────────────────┤
│          │                   │ shell                        │
└───────────────────────────────┴──────────────────────────────┘
```

The Neovim area contains the Explorer and the protected editor display region. Closing a file/tab is supported. Local `q`/`wq`/`x` command families operate on the current buffer/tab rather than removing the structural editor window; `[No Name]` save-close uses Save As. Whole-process quit commands are kept from dismantling the IDE—use `Ctrl-q` to exit the session.

## Documentation

- [Deployment](DEPLOYMENT.md)
- [Features and interaction model](docs/FEATURES.md)
- [Keybindings](docs/KEYBINDINGS.md)
- [Architecture and rebuild notes](docs/ARCHITECTURE.md)

## License

See [LICENSE](LICENSE).

## Experimental Helix prototype

The `helix-prototype` branch contains a side-by-side Helix edition. It does not replace the normal `devtui` launcher. The portable, user-visible features that were added to the Neovim edition have been migrated into a pinned Helix fork, including native real-time multiple selections, persistent Explorer, Preview/Pinned editors, dirty-close/Save As behavior, editor/Explorer mouse interactions, running-editor IPC, scrollbar, inactive-region rendering, VS Code-style shortcuts/search/replace, and portable language/debug integration.

See [`prototype/helix/README.md`](prototype/helix/README.md), [`prototype/helix/docs/PARITY.md`](prototype/helix/docs/PARITY.md), and [`prototype/helix/docs/MIGRATION.md`](prototype/helix/docs/MIGRATION.md).
