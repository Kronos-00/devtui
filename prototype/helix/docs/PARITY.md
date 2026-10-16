# devtui Helix parity matrix

This document tracks the portable, user-facing features added to the Neovim edition of devtui and their migration to the Helix edition.

Status:
- **Done**: implemented and regression-tested in the Helix fork.
- **Partial**: usable foundation exists, but VS Code parity is incomplete.
- **Pending**: not yet migrated.

VS Code interaction semantics are the reference behavior for features described as VS Code-style.

## Workspace and session

| Feature | Status |
| --- | --- |
| Zellij IDE layout: editor, Git UI, shell, shortcut banner | Done |
| Normal/wide layout behavior | Pending |
| `Ctrl-q` exits the full devtui session; detach remains a Zellij action | Done |
| Editor display region remains present when files/tabs close | Done |
| Explorer remains present and cannot be dismissed accidentally | Done |
| Shell pane inherits the launching environment without re-reading shell startup files | Done |
| Portable installer and pinned editor build | Done |

## Editor lifecycle and tabs

| Feature | Status |
| --- | --- |
| Explorer single-click opens/reuses one Preview editor | Done |
| Explorer double-click pins the editor | Done |
| Editing a Preview automatically pins it | Done |
| Preview tab styling is visually distinct | Done |
| Later previews never replace pinned editors | Done |
| Dirty tab has a dirty marker and a separately usable close control | Done |
| Dirty close prompts Save / Don't Save / Cancel | Done |
| Untitled editor participates in dirty-close confirmation | Done |
| Untitled Save uses Save As | Done |
| `q` / `quit` / `close` close the current buffer/tab, not the structural editor region | Done |
| `q!` / `quit!` / `close!` discard current changes and close only that buffer/tab | Done |
| `wq` / `wq!` save then close; Untitled uses Save As | Done |
| `x` / `xit` / `exit` save when needed then close | Done |
| whole-editor quit command families are protected; session exit remains `Ctrl-q` | Done |
| mouse click switches tabs | Done |
| tab close control uses the same dirty-close lifecycle | Done |
| double-click empty tab-strip space creates an Untitled editor | Done |
| VS Code-style selected-tab multi-actions | Pending |

## Persistent Explorer

| Feature | Status |
| --- | --- |
| Always-visible Explorer sidebar beside the editor | Done |
| Explicit workspace-root row | Done |
| Hidden files shown by default | Done |
| ignored files shown by default | Done |
| toggle hidden / ignored visibility | Done |
| Explorer focus/open shortcut does not toggle the sidebar closed | Done |
| first mouse click works when editor currently owns focus | Done |
| single-click file Preview while Explorer keeps focus | Done |
| double-click file pins editor | Done |
| directory expand/collapse | Done |
| right-edge drag resizes Explorer | Done |
| three-cell resize hot zone | Done |
| minimum Explorer width | Done |
| Explorer width persists across sessions | Done |
| Ctrl/Alt mouse toggles multi-selection | Done |
| Shift range selection | Done |
| right-click selected item preserves current multi-selection | Done |
| right-click unselected item makes it the context target | Done |
| root/folder/file context actions | Done |
| New File / New Folder | Done |
| Copy / Paste internal file clipboard | Done |
| Delete with confirmation | Done |
| Rename | Done |
| Copy Path / Copy Relative Path to system clipboard | Done |
| multi-selection batch Copy/Delete/path copy | Done |
| same-directory duplicate naming (`name copy`, `name copy 2`, ...) | Done |
| keyboard parity for every Explorer context action | Partial |
| drag/drop file moving | Pending |

## Mouse and multiple selections

| Feature | Status |
| --- | --- |
| middle-button vertical drag creates native multiple selections | Done |
| typing updates all selections immediately in Insert mode | Done |
| Insert-mode arrow movement moves all selections immediately | Done |
| starting middle gesture from Insert mode never invokes clipboard paste | Done |
| zero-width vertical drag clamps short lines to EOL | Done |
| non-zero-width rectangular selection | Done |
| skip rows shorter than rectangle left edge | Done |
| all-short-row EOL-caret fallback | Done |
| box-selection Copy / Cut / Delete context menu | Done |
| box copy omits skipped rows | Done |
| multi-cursor paste `spread` semantics | Done |
| keyboard add-cursor above/below | Done |
| keyboard add-next-match / add-all-occurrences | Done |
| normal arrow collapse semantics matching VS Code | Pending |

## Editor mouse and context UI

| Feature | Status |
| --- | --- |
| left-click places editor cursor | Done |
| right-click symbol context menu | Done |
| Definition / Declaration / References / Implementation / Type Definition | Done |
| Hover / Rename / Code Action from context menu | Done |
| keyboard fallback for symbol context menu | Done |
| right-click multi-selection Copy/Cut/Delete | Done |

## VS Code-style shortcut layer

| Feature | Status |
| --- | --- |
| Save / Undo / Redo / Select All / Find / Quick Open / Project Search / Command Palette | Done |
| Save As | Done |
| Copy selection; no selection copies current line | Done |
| Cut selection; no selection cuts current line | Done |
| host-terminal paste workflow | Partial |
| current-file Replace toggle | Done |
| project Replace | Done |
| select current line | Done |
| go to line | Done |
| go to symbol in file | Done |
| Explorer focus | Done |
| toggle line comment | Done |
| add next occurrence / all occurrences | Done |
| Rename / Definition / References / Quick Fix | Done |
| next / previous diagnostic | Done |
| insert line below / above | Done |
| delete current line(s) | Done |

## Search and navigation

| Feature | Status |
| --- | --- |
| file picker / Quick Open | Done |
| workspace text search | Done |
| command palette | Done |
| current-file find | Done |
| current-file replace UI | Done |
| project replace UI | Done |
| go to line | Done |
| document symbols | Done |

## Clipboard

| Feature | Status |
| --- | --- |
| OSC 52 / terminal-code system clipboard writes | Done |
| editor copy does not require a terminal clipboard read | Done |
| Explorer Copy Path / Copy Relative Path | Done |
| multi-selection newline-separated path copy | Done |
| copy/cut current line when there is no explicit selection | Done |
| sparse rectangular copy semantics | Done |
| multi-cursor spread paste | Done |

## External navigation and Git UI

| Feature | Status |
| --- | --- |
| one running editor accepts external file + line + column requests | Done |
| terminal path click can target the running editor | Done |
| relative and absolute path parsing | Done |
| `path:line:column` and `path(line,column)` parsing | Done |
| focus existing Zellij editor pane after external navigation | Done |
| Lazygit edit action opens in running editor | Done |
| Lazygit keyboard/mouse usability baseline | Done |

## Visual/editor extras

| Feature | Status |
| --- | --- |
| Markdown source punctuation remains visible | Done |
| editor scrollbar with draggable thumb | Done |
| scrollbar show/hide command | Done |
| inactive preprocessor-region dimming from language-server data | Done |
| file/buffer icons and Nerd Font presentation | Partial |

## Language and debugging integration

| Feature | Status |
| --- | --- |
| clangd-based C/C++ navigation | Done |
| CMake language support | Partial |
| Bash language server / lint / formatting workflow | Partial |
| Python language server / lint / formatting workflow | Partial |
| DAP breakpoint / continue / step in / step over / step out / terminate | Partial |
| debugger UI parity | Pending |
| source/header switch convenience action | Done |
| LSP health/info convenience UI | Partial |

## Intentionally non-portable items

Machine-specific SDK/compiler wrappers, host-specific debugger shims, and other environment-only compatibility layers are not part of the public Helix migration. The portable editor consumes normal project configuration such as language-server settings and compilation databases.
