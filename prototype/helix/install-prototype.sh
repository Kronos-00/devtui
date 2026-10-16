#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_ONLY=0
if [ "${1:-}" = "--help" ]; then
  echo 'Usage: ./prototype/helix/install-prototype.sh [--config-only]'
  echo 'Installs alongside Neovim devtui and backs up previous Helix settings.'
  exit 0
elif [ "${1:-}" = "--config-only" ]; then
  CONFIG_ONLY=1
elif [ $# -gt 0 ]; then
  echo "Usage: ./prototype/helix/install-prototype.sh [--config-only]" >&2
  exit 2
fi
BACKUP="$HOME/.local/state/devtui/helix-backup-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$BACKUP"
for path in .config/devtui-helix .config/zellij/layouts/dev-helix.kdl .config/zellij/layouts/dev-helix-wide.kdl; do
  if [ -e "$HOME/$path" ]; then
    mkdir -p "$BACKUP/$(dirname "$path")"
    cp -a "$HOME/$path" "$BACKUP/$path"
  fi
done
mkdir -p "$HOME/.local/bin" "$HOME/.config/devtui-helix/helix" "$HOME/.config/zellij/layouts"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix" "$HOME/.local/bin/devtui-helix"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix-banner" "$HOME/.local/bin/devtui-helix-banner"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix-editor-pane" "$HOME/.local/bin/devtui-helix-editor-pane"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix-git-pane" "$HOME/.local/bin/devtui-helix-git-pane"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix-open" "$HOME/.local/bin/devtui-helix-open"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix-shell-pane" "$HOME/.local/bin/devtui-helix-shell-pane"
cp "$ROOT/prototype/helix/config/config.toml" "$HOME/.config/devtui-helix/helix/config.toml"
cp "$ROOT/prototype/helix/config/languages.toml" "$HOME/.config/devtui-helix/helix/languages.toml"
python3 - "$ROOT" "$HOME" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1]); home=sys.argv[2]
for src,dst in [
    (root/'prototype/helix/zellij/dev-helix.kdl.in', Path(home)/'.config/zellij/layouts/dev-helix.kdl'),
    (root/'prototype/helix/zellij/dev-helix-wide.kdl.in', Path(home)/'.config/zellij/layouts/dev-helix-wide.kdl'),
    (root/'prototype/helix/zellij/zellij.kdl.in', Path(home)/'.config/devtui-helix/zellij.kdl'),
    (root/'prototype/helix/config/lazygit.yml', Path(home)/'.config/devtui-helix/lazygit.yml'),
]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text().replace('__HOME__', home))
PY
if [ "$CONFIG_ONLY" -eq 0 ]; then
  "$ROOT/prototype/helix/scripts/build-helix.sh"
  "$ROOT/prototype/helix/scripts/build-link-plugin.sh"
  "$ROOT/prototype/helix/scripts/install-tools.sh"
fi
echo "Helix edition installed. Backup: $BACKUP"
echo "Run: devtui-helix [project-directory]"
