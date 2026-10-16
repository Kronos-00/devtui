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

## Migration status

Implemented and validated in the fork:

- native real-time multiple selections and Insert-mode movement;
- middle-drag native selections;
- mouse-operable picker/file explorer overlay;
- VS Code-style Preview/Pinned editor state foundation;
- preview edit-to-pin;
- bufferline mouse switching/closing, dirty marker + close control, and blank-area double-click Untitled;
- dirty close Save / Don't Save / Cancel;
- Untitled Save As for write/write-quit;
- protected local quit/write-quit/exit command families;
- persistent Explorer sidebar with explicit workspace root, folder expansion, file Preview/Pin wiring, focus protection, hidden/ignored toggles, mouse wheel scrolling, and persistent drag-resize width.

## Deliberately not implemented yet

- Explorer context menu/file-operation UX;
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
