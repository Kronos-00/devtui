# Helix migration assessment

This prototype evaluates replacing the Neovim editor pane while keeping the surrounding Zellij/Lazygit/shell workflow.

## Conclusion

The migration is technically feasible and worth prototyping, but it is not a configuration-only migration. Helix is a substantially better fit for the editing core because multiple selections are native. The remaining cost is concentrated in the IDE shell around the editor, so a small-to-medium Helix fork is the realistic implementation model.

## Feature matrix

| devtui feature | Helix baseline | migration cost | prototype decision |
| --- | --- | ---: | --- |
| Real-time multi-selection insert | Native | Low | Implemented and validated |
| Insert-mode arrow movement for all selections | Native | Low | Implemented and validated |
| Middle-drag vertical cursors / rectangular selection | Mouse API exists; middle is paste by default | Medium | Implemented with VS Code short-line/EOL rules |
| LSP navigation/hover/rename/actions | Native | Low | Use built-in |
| Diagnostics | Native | Low | Use built-in |
| C/C++/CMake/Bash/Python language support | Native language configs/LSP | Low | Use built-in |
| DAP baseline | Native, experimental | Low-Medium | Use built-in |
| Quick Open/global search/command palette | Native pickers | Low | Remap keys |
| Selection context Copy/Cut/Delete | Native operations exist | Medium | Implemented for mouse-selected ranges |
| Bufferline + dirty indicator | Native render | Low | Enable always |
| Bufferline mouse switch/close | No upstream hit testing | Medium | Implemented in fork |
| OSC 52 clipboard | Native termcode provider | Low | Configure |
| Markdown source punctuation | Native text source view | Low | No special patch |
| Persistent Explorer sidebar | Implemented in EditorView | High | Implemented |
| Explorer file ops/context menu | Core file create/rename/delete APIs exist | Medium-High | Implemented in fork |
| Explorer multi-select + mouse semantics | Persistent tree exists | High | Implemented in fork |
| Explorer resize/persist width | 3-cell drag handle + state file | High | Implemented |
| Preview/Pinned editors | Picker preview exists upstream | High | Implemented in fork with Explorer single-click/double-click wiring |
| Dirty close Save/Don't Save/Cancel | Dirty detection exists | Medium | Implemented |
| Scratch Save As flow | Explicit path supported | Medium | Implemented for write/write-quit |
| Empty tab-strip double-click new scratch | Bufferline needed hit testing | Medium | Implemented |
| Right-click symbol menu | LSP actions exist | Medium | Implemented in fork |
| Protected editor/Explorer regions | Editor/view lifecycle differs | Medium | Implemented in fork |
| Interactive editor scrollbar | No editor scrollbar | High | Optional Rust UI patch |
| Inactive preprocessor region highlighting | No matching custom LSP extension | High | Optional LSP extension |
| Project Replace panel | Search exists; dedicated replace panel absent | High | External workflow or UI patch |
| Terminal path -> running editor | No stable upstream running-instance IPC | Medium-High | Implemented with per-session Unix socket |
| Zellij/Lazygit/shell environment | Editor-independent | Low | Reuse current design |

## Why the editing core is a better fit

Helix stores multiple ranges in the document selection itself. Character insertion builds one transaction across the complete selection, and movement commands transform every range. This means real-time typing and Insert-mode cursor motion do not require replaying edits after leaving Insert mode.

The prototype patch therefore touches only mouse-to-selection creation. It does not implement a second multi-cursor engine.

## Main risks

1. The current file explorer is an overlay picker, not an always-visible tree.
2. Preview/pinned semantics require explicit document state beyond Helix's current picker preview.
3. Bufferline rendering has no mouse hit targets today.
4. External tools need a supported IPC endpoint to target the already-running editor.
5. These extensions currently require maintaining a Helix source fork because a stable plugin API is not available on the mainline used by this prototype.

## Go/no-go recommendation

**Go for prototype.** The difficult work is sizable but localized in the terminal UI layer. The editing model removes the most fundamental mismatch in the current editor implementation, so the long-term trade is favorable if exact multi-cursor behavior is a priority.
