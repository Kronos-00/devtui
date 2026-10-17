# Workspace shortcut window

The fixed shortcut banner is replaced by a single workspace floating window.
Press **F4** from the editor, Git or shell pane to open it, and press F4 again,
Esc while the window is focused, or its title's **[x]** button to close it.
The editor frame includes a small F4 hint without reserving any banner rows.

## Window behavior

The window floats over the entire workspace and stays above other floating
panes, including pinned panes. Clicking another pane allows work to continue
under the help window. Drag its title text to move it. Drag any of the four
borders or four corners to resize it. The unused part of the top border is a
resize handle; the title text remains the move handle. Geometry stays inside
the terminal, and terminal resizing keeps the window and close button reachable.
The close button is given space before the title, including very narrow windows.

The F4 keybinding targets one plugin location. The first message shows and
focuses that plugin; the next closes it. Repeated requests reuse the same
instance. Closing the window removes its surface and restores the previous
pane. Help keystrokes are consumed inside the plugin and do not edit underlying
files. Ordinary floating panes retain their native frame behavior.

## Contents and layout

The shipped catalogue has **146 entries** in ten categories. It covers every
explicit editor binding in the shipped configuration across normal, insert and
selection modes, plus mouse and Explorer operations, workspace controls,
formatting, language configuration inspection, debugging and common Helix
operations. The internal F24 transport alias is represented by its user-facing
Ctrl+Shift+Z binding.

Key labels spell out Ctrl, Shift and Alt. Descriptions and contexts distinguish
editor actions from Explorer and workspace actions. The catalogue is generated
from `config/config.toml`; generation fails when an explicit command lacks a
description, and `generate.py --check` detects stale generated content. Native
Helix and Zellij examples are a curated set, rather than an exhaustive list of
all commands in those tools. User-defined remappings require updating the
catalogue inputs.

Window width selects one, two or three columns. Key names, contexts and Chinese
explanations wrap according to their terminal cell widths. An entry stays in
one column. Height determines the visible row count and page size. Use the
mouse wheel, Up/Down, PageUp/PageDown or Home/End to scroll. Press `/` to search
keys, descriptions or contexts, Enter to finish text input, and Ctrl+U to clear
the filter. Esc closes the window even while entering a search.

## Key selection and implementation

Plain F4 was unused in the installed Helix and Zellij configuration. It is
also unbound in the pinned official Windows Terminal defaults. The source URL,
revision and hash are in
[windows-terminal-reference.json](../shortcuts/windows-terminal-reference.json).
F1's command palette and the existing navigation/debug function keys retain
their bindings. The workspace binding also works in locked and management modes. F4 returns
workspace input to normal mode so the window receives Esc and navigation keys.

The implementation uses a dedicated Zellij plugin and a scoped native frame
extension. It runs with no requested plugin permissions: it reads its embedded
catalogue, receives its own key/mouse events and shows or closes its own pane.
It does not need project files, commands, network access or clipboard access.

The Helix edition installs a separate workspace binary, built from the pinned
Zellij archive and the existing mouse passthrough patch plus
`zellij/cheatsheet-window.patch`. The launcher selects this binary and its own
plugin assets. The existing custom terminal-link implementation is preserved.
The main edition's binary and layouts are separate. The editor binary and its
43-patch source tree are unchanged by this feature.

## Deployment and validation

`install-prototype.sh` backs up the previous layouts, configuration and obsolete
banner helper. Both normal and wide layouts remove the banner. A full install
runs `scripts/build-workspace.sh`; a configuration-only install does not build
the native window support or plugin. Independent fingerprints are saved in
`workspace-build-info.json`, and `devtui-helix --version` includes workspace and
shortcut-plugin hashes when they are installed.

Isolated window fixtures disable unrelated background plugins; the installed
workspace smoke test retains the normal terminal-link integration.

The window suite has 16 real-PTY workspace tests, including all eight resize
directions, title dragging, filtering, scrolling, reflow, singleton toggles,
background focus, overlapping pinned windows, tiny and resized terminals,
close-button cleanup and existing control/mouse passthrough. Five Rust tests
cover catalogue, filtering, packing, Unicode widths and scroll limits. The
preserved terminal-link plugin's tests run during the build as well.

Executed results, build inputs and fingerprints are in
[shortcuts-window-results.json](shortcuts-window-results.json).

Start a new `devtui-helix` workspace to load the new binary and banner-free
layout. Already running workspaces keep their current layout and process.

The installed Release passed all 16 window methods and 6 deployment methods.
Five shortcut-plugin Rust tests and 15 terminal-link Rust tests passed. The full
workspace smoke checks passed, including reopening a source file through the
running editor, opening/closing F4 help and saving an edit afterward. Fresh
patch application matched the build inputs, and the feature audit passed.

Workspace binary SHA-256: `82198f75504150dfb4169aa74d44f8e210ac6e236a94223cdb87b722183f6625`.
Shortcut plugin SHA-256: `0086f1f673d05561a054c858c8a7f383414b671d7f535c5c66c28aaecee800c7`.

Find/Replace 的新操作与组合键转发验证见 [FIND_REPLACE_WIDGET.md](FIND_REPLACE_WIDGET.md)。
