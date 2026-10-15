# Architecture

## Process layout

`devtui` creates a unique Neovim RPC socket, selects the normal or wide Zellij layout, and execs Zellij. The Zellij session inherits the environment that launched devtui.

The user-facing shell pane runs through `devtui-shell-pane`, which removes devtui's private RPC variables and execs `bash --noprofile --norc -i`. This intentionally avoids a second shell-startup pass.

## Neovim

The Neovim configuration is a LazyVim configuration pinned with `lazy-lock.json`. Custom modules implement:

- persistent Snacks Explorer interactions;
- preview/pinned buffer lifecycle;
- protected Explorer/editor display regions;
- dirty-tab and untitled-editor behavior;
- VS Code-style shortcuts;
- column/multicursor mouse editing;
- OSC 52 clipboard writes;
- interactive scrollbar;
- clangd inactive-region highlighting.

## Zellij patches

### Mouse forwarding patch

Stock Zellij 0.45.1 reserves some Ctrl/Alt mouse behavior for pane operations. `patches/zellij-0.45.1-mouse-passthrough.patch` preserves frame behavior while forwarding modified mouse events to mouse-aware terminal applications such as Neovim.

### File-link plugin patch

`patches/zellij-link-devtui.patch` extends the stock link plugin so highlighted paths support line/column locations and invoke `tui-nvim-open` instead of opening a separate editor.

The installer builds the patched link plugin as WASM and installs it under `~/.local/share/devtui`.

## Rebuilding Zellij manually

```bash
./scripts/build-zellij.sh
```

The script downloads the pinned source release, applies both patches, builds the default WASM plugins, builds the patched binary, and updates the `~/.local/bin/zellij` symlink.

## Configuration templates

Zellij and Lazygit configs contain `__HOME__` placeholders. `install.sh` renders them using the target user's actual home directory, so no machine-specific path is committed.
