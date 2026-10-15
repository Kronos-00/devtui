# Keybindings

## Session

| Input | Action |
| --- | --- |
| `Ctrl-q` | Quit the full Zellij/devtui session |
| `Ctrl-o`, then `d` | Detach Zellij session |
| `Ctrl-Shift-E` | Focus/open Explorer |

## Editor-style shortcuts

| Input | Action |
| --- | --- |
| `Ctrl-s` | Save |
| `Ctrl-Shift-S` | Save As |
| `Ctrl-z` | Undo |
| `Ctrl-y` / `Ctrl-Shift-Z` | Redo |
| `Ctrl-c` | Copy selection; with no selection, copy current line |
| `Ctrl-x` | Cut |
| `Ctrl-v` | Terminal/system paste path used by the configured workflow |
| `Ctrl-a` | Select all |
| `Ctrl-f` | Find |
| `Ctrl-h` | Replace in current file |
| `Ctrl-Shift-F` | Project search |
| `Ctrl-Shift-H` | Project replace |
| `Ctrl-p` | Quick Open |
| `Ctrl-Shift-P` / `F1` | Command palette |
| `Alt-g` | Go to line |
| `F12` | Definition |
| `Shift-F12` | References |
| `F8` / `Shift-F8` | Next / previous diagnostic |

## Explorer mouse model

- Left click: single selection; files open/reuse a preview editor.
- Double left click: pin a file editor; directories use the normal tree action.
- Ctrl+left click: toggle multi-selection.
- Alt+left click: alternate multi-selection modifier.
- Right click: context menu.
- Drag the right 3-cell handle: resize Explorer.
- Esc/q: keep Explorer open.

## Column selection

- Middle-mouse drag creates one selection/cursor per participating line.
- Copy keeps the selection active.
- Arrow keys collapse the highlighted ranges, keep the cursors, then move them.
- `Ctrl-Up` / `Ctrl-Down` add an ordinary multicursor above/below.

## Terminal links

Alt+click highlighted file paths such as:

```text
src/main.cpp:42:7
src/main.cpp(42,7)
```

The path opens in the existing Neovim editor pane at the requested location.
