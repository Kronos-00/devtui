# VS Code source reference map

Behavioral reference revision: `e97039dd9293ef2b9df8876d0bc8c0c8ff87f871`. These are source references, not vendored code. A review against source does not imply pixel-identical GUI rendering in a terminal.

| Source | Reviewed behavior |
|---|---|
| [editorGroupModel](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/workbench/common/editor/editorGroupModel.ts) | preview vs pinned vs sticky; one preview slot and existing-editor reuse |
| [editorGroupView](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/workbench/browser/parts/editor/editorGroupView.ts) | dirty close Save / Do not Save / Cancel; failed saves do not close |
| [multiEditorTabsControl](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/workbench/browser/parts/editor/multiEditorTabsControl.ts) | tab pointer targets; blank-strip double-click and active-tab visibility |
| [fileActions](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/workbench/contrib/files/browser/fileActions.ts) | create, paste, duplicate naming, source/descendant checks, reveal/open after operations |
| [fileCommands](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/workbench/contrib/files/browser/fileCommands.ts) | Explorer actions and context preconditions |
| [listWidget](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/base/browser/ui/list/listWidget.ts) | plain, Ctrl and Shift selection; context target |
| [explorerView](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/workbench/contrib/files/browser/views/explorerView.ts) | open/preserveFocus/pinned and right-click selection routing |
| [cursorColumnSelection](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/editor/common/cursor/cursorColumnSelection.ts) | sparse rows, inclusive EOL boundary, reversed rectangles, all-EOL fallback |
| [cursorMoveOperations](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/editor/common/cursor/cursorMoveOperations.ts) | Left/Right collapse to boundary; vertical movement anchors |
| [cursorTypeOperations](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/editor/common/cursor/cursorTypeOperations.ts) | typing/cut/paste edit operation delegation |
| [multicursor](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/editor/contrib/multicursor/browser/multicursor.ts) | first add-next-match selects word; later invocations add matches |
| [clipboard](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/editor/contrib/clipboard/browser/clipboard.ts) | copy/cut dispatch and clipboard metadata |
| [replaceService](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/workbench/contrib/search/browser/replaceService.ts) | explicit project replace saves target text files |
| [viewModelImpl](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/editor/common/viewModel/viewModelImpl.ts) | getPlainTextToCopy, empty-selection line copy, selection ordering |
| [cursorTypeEditOperations](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/editor/common/cursor/cursorTypeEditOperations.ts) | PasteOperation spread vs full text, selection replacement, undo grouping |
| [decorationsOverviewRuler](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/editor/browser/viewParts/overviewRuler/decorationsOverviewRuler.ts) | document-relative overview decorations without moving the cursor |
| [goToCommands](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/editor/contrib/gotoSymbol/browser/goToCommands.ts) | language capability preconditions for symbol navigation |
| [listService](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/platform/list/browser/listService.ts) | ResourceNavigator: double-click pins and transfers editor focus |
| [uint](https://github.com/microsoft/vscode/blob/e97039dd9293ef2b9df8876d0bc8c0c8ff87f871/src/vs/base/common/uint.ts) | maximum safe small integer used for duplicate-name overflow handling |

## Explicit adaptations

The user requested persistent regions, modal entry with `i`/`Esc`, Ctrl-Q for session exit, Alt-G when Ctrl-G is taken by Zellij, an alternate Alt-click selection modifier inside Explorer, and `.` for the workspace-root relative path. These are devtui contracts, not claimed default VS Code behavior.

Host terminal paste carries text, not the private VS Code HTML/column-selection clipboard metadata. Text selection replacement and multi-cursor spread are implemented; private metadata round trips are outside the terminal protocol. Native Vim marks are represented as document-local navigation marks; Shada and Vim-specific persistence formats are not imported.

The Neovim main branch is retained as the audited baseline. Its delayed Insert-mode multicursor replay, Save As copy behavior, regex-first search mapping and exception-based QuitPre protection are not copied as target semantics. See MAIN_FEATURE_AUDIT.md for corrections.

## Python debug launch reference

The debugger extension was separately reviewed at `44a63c883fd325bebe0b6597f4696441a73127c2`. Its base resolver chooses the workspace/file interpreter, and the launch resolver propagates that interpreter to the debuggee/launcher. The terminal implementation preserves that choice and discovers `python3` before legacy `python` when no environment was selected. Adapter subprocesses are isolated from the editor controlling terminal.

- [base resolver](https://github.com/microsoft/vscode-python-debugger/blob/44a63c883fd325bebe0b6597f4696441a73127c2/src/extension/debugger/configuration/resolvers/base.ts)
- [launch resolver](https://github.com/microsoft/vscode-python-debugger/blob/44a63c883fd325bebe0b6597f4696441a73127c2/src/extension/debugger/configuration/resolvers/launch.ts)
