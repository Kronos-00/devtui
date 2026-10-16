# Helix migration assessment

This prototype evaluates replacing the Neovim editor pane while keeping the surrounding Zellij/Lazygit/shell workflow.

## Conclusion

The migration is technically feasible and worth prototyping, but it is not a configuration-only migration. Helix is a substantially better fit for the editing core because multiple selections are native. The remaining cost is concentrated in the IDE shell around the editor, so a small-to-medium Helix fork is the realistic implementation model.

## Feature matrix

| devtui feature | Helix baseline | migration cost | prototype decision |
| --- | --- | ---: | --- |
| Real-time multi-selection insert | Native | Low | Validate directly |
| Insert-mode arrow movement for all selections | Native | Low | Validate directly |
| Middle-drag vertical cursors | Mouse API exists; middle is paste by default | Medium | Rust patch in prototype |
| LSP navigation/hover/rename/actions | Native | Low | Use built-in |
| Diagnostics | Native | Low | Use built-in |
| C/C++/CMake/Bash/Python language support | Native language configs/LSP | Low | Use built-in |
| DAP baseline | Native, experimental | Low-Medium | Use built-in |
| Quick Open/global search/command palette | Native pickers | Low | Remap keys |
| VS Code copy/cut semantics when there is no explicit range | Native selections differ | Medium | Later command patch |
| Bufferline + dirty indicator | Native render | Low | Enable always |
| Bufferline mouse switch/close | No current hit testing | Medium | Later Rust patch |
| OSC 52 clipboard | Native termcode provider | Low | Configure |
| Markdown source punctuation | Native text source view | Low | No special patch |
| Persistent Explorer sidebar | Explorer is currently a picker overlay; prototype adds basic mouse operation | High | Later Rust UI patch |
| Explorer file ops/context menu | Core file create/rename/delete APIs exist; UI missing | Medium-High | Later UI patch |
| Explorer multi-select + mouse semantics | Picker is not a persistent multi-select tree | High | Later UI patch |
| Explorer resize/persist width | No persistent sidebar yet | High | Follows sidebar patch |
| Preview/Pinned editors | Picker preview exists, VS Code lifecycle does not | High | Later editor-state patch |
| Dirty close Save/Don't Save/Cancel | Dirty detection exists; dialog lifecycle differs | Medium | Later UI patch |
| Scratch Save As flow | Explicit path supported; no VS Code Save As dialog | Medium | Later UI patch |
| Empty tab-strip double-click new scratch | Bufferline mouse missing | Medium | Later bufferline patch |
| Right-click symbol menu | LSP actions exist; context UI missing | Medium | Later UI patch |
| Protected editor/Explorer regions | Editor/view lifecycle differs | Medium | Implement after sidebar |
| Interactive editor scrollbar | No editor scrollbar | High | Optional Rust UI patch |
| Inactive preprocessor region highlighting | No matching custom LSP extension | High | Optional LSP extension |
| Project Replace panel | Search exists; dedicated replace panel absent | High | External workflow or UI patch |
| Terminal path -> running editor | No stable running-instance IPC | Medium-High | Add small Unix-socket IPC later |
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
