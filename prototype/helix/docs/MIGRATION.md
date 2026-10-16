# Neovim-to-Helix migration map

This document lists the portable, user-visible features that were added to the Neovim edition of devtui and maps them to the Helix edition.

VS Code/VSCodium interaction semantics are the reference for every feature described as VS Code-style. Machine-specific compiler/SDK wrappers, host-only debugger shims, and other environment-only compatibility layers are intentionally excluded.

## Commit plan

The migration is grouped so each commit has one coherent responsibility:

1. **Editor lifecycle and tabs** — Preview/Pinned, dirty close, Untitled Save As, protected editor region, tab mouse behavior.
2. **Persistent Explorer** — always-visible tree, focus model, Preview/Pinned integration, resize/persistence.
3. **Explorer selections and file operations** — Ctrl/Alt/Shift selection, context menu, create/copy/paste/delete/rename/path actions.
4. **Editor context and running-instance navigation** — symbol menu, terminal/Lazygit navigation, editor focus.
5. **Column-selection editing** — middle-drag native multi-selection, short-line/EOL rules, paste/copy semantics.
6. **Visual/editor extras** — scrollbar and inactive preprocessor-region rendering.
7. **VS Code shortcut/search layer** — shortcuts, current-file replace, project replace, occurrence selection.
8. **Adaptive workspace and Explorer keyboard parity** — wide/normal layout and Explorer key behavior.
9. **Portable language/debug integration** — C/C++, CMake, Bash, Python, selected interpreter, DAP actions/UI, LSP info, icons.
10. **Parity validation and deployment** — full regression matrix, installer validation, public-tree scans.

## Workspace and session

- Zellij editor / Git / shell / shortcut-banner workspace.
- Normal and wide layouts selected from terminal dimensions.
- `Ctrl-q` exits the full devtui session; Zellij detach remains available.
- Editor display region remains present when the last file closes.
- Explorer remains structural and cannot be dismissed accidentally.
- Shell pane inherits the environment that launched devtui and does not re-run user shell startup files.
- Portable installer, pinned Helix source revision, reproducible Helix patch build.

## Editor lifecycle and tabs

- Explorer single-click opens/reuses one Preview editor.
- Explorer double-click pins the editor.
- Editing a Preview automatically pins it.
- Preview has distinct tab styling.
- Pinned editors are never replaced by later Preview opens.
- Dirty tab shows a dirty marker without removing the close control.
- Dirty close uses Save / Don't Save / Cancel.
- Untitled buffers participate in dirty-close confirmation.
- Untitled Save uses Save As.
- `q`, `quit`, `close` close only the current buffer/tab and preserve the structural editor.
- `q!`, `quit!`, `close!` discard current changes and close only that buffer/tab.
- `wq`, `wq!` save then close; Untitled uses Save As.
- `x`, `xit`, `exit` save when required then close.
- Whole-editor quit command families are blocked; session exit remains `Ctrl-q`.
- Mouse click switches tabs.
- Tab close control uses the same dirty lifecycle as command close.
- Double-clicking empty tab-strip space creates an Untitled editor.

## Persistent Explorer

- Always-visible Explorer sidebar beside the editor.
- Explicit workspace-root row.
- Hidden and ignored files visible by default.
- Keyboard toggles for hidden / ignored visibility.
- Explorer focus shortcut is focus/open, never toggle-close.
- First mouse click works even when the editor owned focus.
- File single-click Preview keeps Explorer focus.
- File double-click pins.
- Directory expand/collapse.
- Right-edge resize with 3-cell hot zone.
- Minimum width and persistent width state.
- Ctrl/Alt click toggles individual multi-selection.
- Shift click selects a range.
- Right-clicking a selected row preserves multi-selection.
- Right-clicking an unselected row makes it the context target.
- Root/folder/file-specific context action sets.
- New File / New Folder.
- Internal Explorer Copy / Paste clipboard.
- Delete confirmation.
- Rename.
- Copy Path / Copy Relative Path to host clipboard.
- Batch Copy/Delete/path copy for multi-selection.
- Duplicate naming uses `name copy`, `name copy 2`, and so on.
- Keyboard alternatives exist for every Explorer context action.

## Multiple selections and column editing

- Middle-button vertical drag creates native Helix selections.
- Typing updates every selection immediately in Insert mode.
- Insert-mode Left/Right/Up/Down moves every selection immediately.
- Starting a middle gesture from Insert mode never enters clipboard-paste behavior.
- Zero-width vertical drag creates a caret on each crossed row and clamps short rows to EOL.
- Non-zero-width rectangular selection.
- Rows shorter than the rectangle's left boundary are skipped.
- If every crossed row is too short, use the VS Code EOL-caret fallback.
- Box-selection Copy / Cut / Delete context menu.
- Sparse box copy omits skipped rows rather than inserting empty clipboard rows.
- Multi-cursor paste uses VS Code `spread`: row-per-cursor when counts match, otherwise full content at every cursor.
- Keyboard add-cursor above/below.
- Add next matching occurrence and select all matching occurrences.
- Plain arrow movement collapses selections to cursors first, then moves all cursors.

## Editor mouse and context actions

- Left-click positions the editor cursor.
- Right-click symbol menu.
- Definition, Declaration, References, Implementation, Type Definition.
- Hover, Rename, Code Action.
- Keyboard fallback for the same symbol menu.
- Right-click multi-selection Copy / Cut / Delete.

## VS Code-style shortcuts and search

- Save, Save As, Undo, Redo.
- Copy / Cut; when no explicit selection exists, operate on the current line.
- Select All.
- Find and current-file Replace.
- Quick Open.
- Project Search and Project Replace.
- Command Palette.
- Select current line.
- Go to Line.
- Go to Symbol in File.
- Focus Explorer.
- Toggle line comment.
- Add next occurrence / all occurrences.
- Rename, Definition, References, Quick Fix.
- Next / previous diagnostic.
- Insert line below / above.
- Delete current line(s).

## Clipboard

- OSC 52 / terminal-code clipboard writes.
- Copy does not need a terminal clipboard read.
- Explorer Copy Path / Copy Relative Path.
- Multi-selection path copy uses newline-separated values.
- Current-line fallback for Copy/Cut.
- Sparse rectangular copy behavior.
- Multi-cursor spread paste.

## External navigation and Git UI

- One running Helix editor accepts external path + line + column requests.
- Terminal file links target the running editor.
- Relative and absolute path parsing.
- `path:line:column` and `path(line,column)` forms.
- Existing Zellij editor pane is focused after external navigation.
- Lazygit edit action opens in the running editor.
- Lazygit remains in its dedicated pane.

## Visual/editor extras

- Markdown remains source text with punctuation visible.
- Interactive editor scrollbar with draggable thumb.
- Scrollbar show/hide command.
- Inactive preprocessor-region dimming from language-server data.
- Nerd Font icons in Explorer and bufferline.

## Language and debugging integration

- clangd C/C++ navigation and formatting.
- Source/header switch action.
- CMake language server and formatter.
- Bash language server, shellcheck-aware diagnostics path, shfmt formatting.
- Python Pyright + Ruff language/format/lint workflow.
- Workspace-selected Python virtual environment is remembered and reused for language services and debugging.
- DAP breakpoint, Start/Continue, Pause, Step Over, Step Into, Step Out, Restart, Stop.
- Variables and call-stack access.
- VS Code debug shortcuts: F5/F6/F9/F10/F11/Shift+F11/Ctrl+Shift+F5/Shift+F5.
- `Ctrl+Shift+D` opens the Run and Debug action UI.
- LSP info UI lists language servers attached to the current buffer.

## Not part of the Neovim baseline

The following are useful future enhancements, but are not migration blockers because the Neovim edition did not implement them:

- multi-selecting editor tabs for batch tab actions;
- Explorer drag/drop file moving.
