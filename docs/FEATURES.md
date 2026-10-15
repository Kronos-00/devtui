# Features and interaction model

## Explorer

The first row is the workspace root. Right-click it for root-level actions. Files/folders provide path-copy, copy, and delete actions where applicable. Multi-selection batch operations follow the current selection while New File/New Folder/Paste remain folder-targeted.

A normal click is single-selection. Ctrl/Alt + click toggles multi-selection. Context-clicking a selected row preserves the multi-selection; context-clicking an unselected row makes it the single context target.

## Preview and pinned editors

Single-clicking a file opens a reusable preview editor. Single-clicking another unpinned file replaces that preview. Double-clicking pins the editor. Any text modification also pins a preview. Pinned editors are never reused by subsequent previews.

Dirty editors keep a dirty marker and a usable close control. Closing prompts Save / Don't Save / Cancel. `[No Name]` uses Save As on Save.

Double-clicking empty tab-strip space creates a new `[No Name]` editor.

## Protected layout

Explorer and the main editor display region are structural parts of devtui. Local quit/close attempts are rejected for those windows. Files and tabs remain closable. Explorer Esc/q keeps the sidebar open, and Explorer shortcuts are focus/open actions rather than close toggles.

## Markdown

Markdown source uses `conceallevel=0` in every window, including files opened through preview mode, so source punctuation remains visible.

## Clipboard

Neovim writes the `+` register through OSC 52. Copy does not query the host clipboard. Terminal paste remains the path for reading host clipboard contents.

## Shell environment

The shell pane inherits exported variables from the environment that launched devtui and does not source shell startup files. No compiler/SDK/project environment is injected by devtui.
