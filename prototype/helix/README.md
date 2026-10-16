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
- middle-drag VS Code-style zero-width and rectangular selections, including short-line skip and all-EOL fallback;
- selection right-click Copy / Cut / Delete;
- VS Code-style spread paste when pasted row count matches the active selection count;
- mouse-operable picker/file explorer overlay;
- VS Code-style Preview/Pinned editor state foundation;
- preview edit-to-pin;
- bufferline mouse switching/closing, dirty marker + close control, and blank-area double-click Untitled;
- dirty close Save / Don't Save / Cancel;
- Untitled Save As for write/write-quit;
- protected local quit/write-quit/exit command families;
- persistent Explorer sidebar with explicit workspace root, folder expansion, file Preview/Pin wiring, focus protection, hidden/ignored toggles, mouse wheel scrolling, and persistent drag-resize width;
- Explorer Ctrl/Alt toggle-selection and Shift range selection;
- VS Code-style Explorer context targeting for selected/unselected rows;
- root/folder/file context actions for New File, New Folder, Copy, Paste, Rename, Delete, Copy Path, and Copy Relative Path;
- internal Explorer file clipboard with incremental `copy` naming and batch operations;
- editor right-click Symbol menu for Definition, Declaration, References, Implementation, Type Definition, Hover, Rename, and Code Action;
- interactive right-edge editor scrollbar with proportional thumb and mouse drag scrolling;
- per-session Unix-socket navigation into the already-running editor;
- Lazygit edit actions routed to that editor;
- dedicated Helix terminal-link plugin build for path/line/column navigation.

## Deliberately not implemented yet

- custom inactive-code LSP regions;
- project Replace panel.

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
