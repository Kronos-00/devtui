#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$ROOT/versions.env"
CONFIG_ONLY=0
SKIP_MASON=0
for arg in "$@"; do
  case "$arg" in
    --config-only) CONFIG_ONLY=1 ;;
    --skip-mason) SKIP_MASON=1 ;;
    -h|--help)
      cat <<USAGE
Usage: ./install.sh [--config-only] [--skip-mason]

  --config-only  install configs/scripts only; do not download/build pinned binaries
  --skip-mason   skip installation of the pinned editor tools
USAGE
      exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
  echo "This reproducible installer currently targets Linux x86_64." >&2
  exit 1
fi

for cmd in bash curl git patch python3 tar; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing dependency: $cmd" >&2; exit 1; }
done

mkdir -p "$HOME/.local/bin" "$HOME/.local/opt/devtui" "$HOME/.local/share/devtui" "$HOME/.local/state/devtui"
BACKUP="$HOME/.local/state/devtui/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
backup_path() {
  local path="$1"
  [ -e "$path" ] || [ -L "$path" ] || return 0
  local rel="${path#"$HOME"/}"
  mkdir -p "$BACKUP/$(dirname "$rel")"
  cp -a "$path" "$BACKUP/$rel"
}

backup_path "$HOME/.config/nvim"
backup_path "$HOME/.config/zellij/config.kdl"
backup_path "$HOME/.config/zellij/layouts/dev.kdl"
backup_path "$HOME/.config/zellij/layouts/dev-wide.kdl"
backup_path "$HOME/.config/lazygit/config.yml"

rm -rf "$HOME/.config/nvim"
mkdir -p "$HOME/.config/nvim" "$HOME/.config/zellij/layouts" "$HOME/.config/lazygit"
cp -a "$ROOT/config/nvim/." "$HOME/.config/nvim/"
install -m 0755 "$ROOT"/bin/* "$HOME/.local/bin/"

python3 - "$ROOT" "$HOME" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1]); home=sys.argv[2]
def render(src,dst):
    text=Path(src).read_text().replace('__HOME__', home)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text(text)
render(root/'config/zellij/config.kdl.in', Path(home)/'.config/zellij/config.kdl')
render(root/'config/zellij/layouts/dev.kdl.in', Path(home)/'.config/zellij/layouts/dev.kdl')
render(root/'config/zellij/layouts/dev-wide.kdl.in', Path(home)/'.config/zellij/layouts/dev-wide.kdl')
render(root/'config/lazygit/config.yml.in', Path(home)/'.config/lazygit/config.yml')
PY

if [ "$CONFIG_ONLY" -eq 0 ]; then
  NVIM_PREFIX="$HOME/.local/opt/devtui/nvim-$NEOVIM_VERSION"
  rm -rf "$NVIM_PREFIX"
  mkdir -p "$NVIM_PREFIX"
  NVIM_ARCHIVE="$HOME/.cache/devtui/nvim-$NEOVIM_VERSION.tar.gz"
  mkdir -p "$HOME/.cache/devtui"
  curl -fsSL "https://github.com/neovim/neovim/releases/download/v$NEOVIM_VERSION/nvim-linux-x86_64.tar.gz" -o "$NVIM_ARCHIVE"
  echo "$NEOVIM_SHA256  $NVIM_ARCHIVE" | sha256sum -c -
  tar -xzf "$NVIM_ARCHIVE" --strip-components=1 -C "$NVIM_PREFIX"
  ln -sfn "$NVIM_PREFIX/bin/nvim" "$HOME/.local/bin/nvim"

  LG_PREFIX="$HOME/.local/opt/devtui/lazygit-$LAZYGIT_VERSION"
  rm -rf "$LG_PREFIX"
  mkdir -p "$LG_PREFIX"
  LG_ARCHIVE="$HOME/.cache/devtui/lazygit-$LAZYGIT_VERSION.tar.gz"
  curl -fsSL "https://github.com/jesseduffield/lazygit/releases/download/v$LAZYGIT_VERSION/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz" -o "$LG_ARCHIVE"
  echo "$LAZYGIT_SHA256  $LG_ARCHIVE" | sha256sum -c -
  tar -xzf "$LG_ARCHIVE" -C "$LG_PREFIX" lazygit
  chmod 0755 "$LG_PREFIX/lazygit"
  ln -sfn "$LG_PREFIX/lazygit" "$HOME/.local/bin/lazygit"

  "$ROOT/scripts/build-zellij.sh"
fi

if [ "$SKIP_MASON" -eq 0 ]; then
  PATH="$HOME/.local/bin:$PATH" "$ROOT/scripts/install-mason-tools.sh"
fi

cat <<DONE
Installed devtui.
Backup: $BACKUP

Ensure this is in your login shell PATH:
  export PATH="\$HOME/.local/bin:\$PATH"

Then start in any project directory with:
  devtui
DONE
