# Helix prototype

This branch validates whether devtui can move its editor core from Neovim to a small Helix fork without changing the surrounding Zellij workspace.

## What this prototype validates

- native Helix multiple selections as the multi-cursor data model;
- real-time Insert-mode edits across every selection;
- Insert-mode arrow movement across every selection;
- patched middle-button vertical drag creating native selections rather than clipboard paste;
- mouse-operable Helix picker/file explorer: left-click selection, wheel navigation, double-click open, preview-click open;
- built-in LSP, diagnostics, DAP baseline, file picker, global search, command palette, bufferline and OSC 52 clipboard;
- current Zellij + shell + Lazygit pane arrangement.

## Deliberately not implemented yet

- persistent Explorer sidebar/tree;
- Explorer context menu/file-operation UX;
- VS Code Preview/Pinned editor lifecycle;
- bufferline mouse switching/closing and blank-area double-click;
- Save/Don't Save/Cancel close dialog and scratch Save As dialog;
- right-click symbol menu;
- editor scrollbar;
- custom inactive-code LSP regions;
- project Replace panel;
- terminal/Lazygit open-in-the-already-running-editor IPC.

Those items are assessed in [docs/ASSESSMENT.md](docs/ASSESSMENT.md). They are prototype gaps, not claimed parity.

## Install alongside normal devtui

First install the normal devtui prerequisites from the repository root. Then:

```bash
./prototype/helix/install-prototype.sh
devtui-helix /path/to/project
```

The prototype uses separate Helix and Zellij configuration and does not replace the normal `devtui` launcher.

## Critical test

1. Open a text file.
2. Middle-drag vertically across several visible lines at one column.
3. Press `i` and type characters: all selections should update immediately.
4. While still in Insert mode, use arrow keys: all selections should move together.
5. Press `Esc` to return to normal mode.

This is the behavior the prototype exists to validate before any broader migration decision.
