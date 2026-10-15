#!/usr/bin/env bash
set -euo pipefail
rm -f "$HOME/.local/bin/devtui" "$HOME/.local/bin/devtui-banner" \
  "$HOME/.local/bin/devtui-editor-pane" "$HOME/.local/bin/devtui-git-pane" \
  "$HOME/.local/bin/devtui-shell-pane" "$HOME/.local/bin/tui-nvim-open" \
  "$HOME/.local/bin/tui-doctor"
for name in nvim zellij lazygit; do
  link="$HOME/.local/bin/$name"
  if [ -L "$link" ]; then
    target="$(readlink -f "$link" || true)"
    case "$target" in "$HOME/.local/opt/devtui/"*) rm -f "$link" ;; esac
  fi
done
rm -rf "$HOME/.local/opt/devtui" "$HOME/.local/share/devtui"
echo "Binaries removed. Config directories were left in place; restore a backup from ~/.local/state/devtui if needed."
