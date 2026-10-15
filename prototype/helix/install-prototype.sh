#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_ONLY=0
if [ "${1:-}" = "--config-only" ]; then
  CONFIG_ONLY=1
elif [ $# -gt 0 ]; then
  echo "Usage: ./prototype/helix/install-prototype.sh [--config-only]" >&2
  exit 2
fi
mkdir -p "$HOME/.local/bin" "$HOME/.config/devtui-helix/helix" "$HOME/.config/zellij/layouts"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix" "$HOME/.local/bin/devtui-helix"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix-banner" "$HOME/.local/bin/devtui-helix-banner"
install -m 0755 "$ROOT/bin/devtui-shell-pane" "$HOME/.local/bin/devtui-shell-pane"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix-editor-pane" "$HOME/.local/bin/devtui-helix-editor-pane"
install -m 0755 "$ROOT/prototype/helix/bin/devtui-helix-git-pane" "$HOME/.local/bin/devtui-helix-git-pane"
cp "$ROOT/prototype/helix/config/config.toml" "$HOME/.config/devtui-helix/helix/config.toml"
cp "$ROOT/prototype/helix/config/lazygit.yml" "$HOME/.config/devtui-helix/lazygit.yml"
python3 - "$ROOT" "$HOME" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1]); home=sys.argv[2]
for src,dst in [
    (root/'prototype/helix/zellij/dev-helix.kdl.in', Path(home)/'.config/zellij/layouts/dev-helix.kdl'),
    (root/'prototype/helix/zellij/zellij.kdl.in', Path(home)/'.config/devtui-helix/zellij.kdl'),
]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text().replace('__HOME__', home))
PY
if [ "$CONFIG_ONLY" -eq 0 ]; then
  "$ROOT/prototype/helix/scripts/build-helix.sh"
fi
echo "Prototype installed. Run: devtui-helix [project-directory]"
