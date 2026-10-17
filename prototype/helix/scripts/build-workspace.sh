#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "$ROOT/versions.env"
WORK="${DEVTUI_BUILD_DIR:-$HOME/.cache/devtui/build}"
ARCHIVE="$WORK/zellij-$ZELLIJ_VERSION.tar.gz"
PREFIX="$HOME/.local/opt/devtui/helix-prototype"
mkdir -p "$WORK" "$PREFIX/bin" "$PREFIX/share/zellij/plugins" "$HOME/.local/share/devtui"
if [ -f "${CARGO_HOME:-$HOME/.cargo}/env" ]; then source "${CARGO_HOME:-$HOME/.cargo}/env"; fi
rustup toolchain install "$RUST_VERSION" --profile minimal
rustup target add --toolchain "$RUST_VERSION" wasm32-wasip1
if [ ! -f "$ARCHIVE" ]; then
  curl -fsSL "https://github.com/zellij-org/zellij/archive/refs/tags/v$ZELLIJ_VERSION.tar.gz" -o "$ARCHIVE"
fi
echo "$ZELLIJ_SOURCE_SHA256  $ARCHIVE" | sha256sum -c -
python3 "$ROOT/prototype/helix/shortcuts/generate.py" --check
SRC="$(mktemp -d "$WORK/zellij-helix-workspace-$ZELLIJ_VERSION.XXXXXX")"
tar -xzf "$ARCHIVE" --strip-components=1 -C "$SRC"
cp -a "$ROOT/prototype/helix/shortcuts" "$SRC/default-plugins/devtui-shortcuts"
cd "$SRC"
patch -p1 < "$ROOT/patches/zellij-0.45.1-mouse-passthrough.patch"
patch -p1 < "$ROOT/prototype/helix/zellij/cheatsheet-window.patch"
python3 - "$ROOT/patches/zellij-link-devtui.patch" "$HOME/.local/bin/devtui-helix-open" "$SRC/terminal-links.patch" <<'PYTHON'
from pathlib import Path
import json,sys
text=Path(sys.argv[1]).read_text().replace('__DEVTUI_OPEN__',json.dumps(sys.argv[2],ensure_ascii=False)[1:-1])
Path(sys.argv[3]).write_text(text)
PYTHON
patch -p1 < "$SRC/terminal-links.patch"
patch -p1 < "$ROOT/prototype/helix/zellij/link-paths.patch"
cargo "+$RUST_VERSION" test --locked -p devtui-shortcuts -p link
cargo "+$RUST_VERSION" build --locked --release --target wasm32-wasip1 -p devtui-shortcuts -p link
CARGO_PROFILE_RELEASE_LTO=false CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16 \
  cargo "+$RUST_VERSION" build --locked --release --bin zellij \
    --no-default-features --features disable_automatic_asset_installation
TARGET="${CARGO_TARGET_DIR:-$SRC/target}"
for asset in "$SRC/zellij-utils/assets/plugins/"*.wasm; do
  name="$(basename "$asset")"
  install -m 0644 "$asset" "$PREFIX/share/zellij/plugins/$name.new"
  mv -f "$PREFIX/share/zellij/plugins/$name.new" "$PREFIX/share/zellij/plugins/$name"
done
install -m 0644 "$TARGET/wasm32-wasip1/release/link.wasm" "$PREFIX/share/zellij/plugins/link.wasm.new"
mv -f "$PREFIX/share/zellij/plugins/link.wasm.new" "$PREFIX/share/zellij/plugins/link.wasm"
install -m 0755 "$TARGET/release/zellij" "$PREFIX/bin/zellij.new"
install -m 0644 "$TARGET/wasm32-wasip1/release/devtui-shortcuts.wasm" "$HOME/.local/share/devtui/devtui-shortcuts.wasm.new"
mv -f "$PREFIX/bin/zellij.new" "$PREFIX/bin/zellij"
mv -f "$HOME/.local/share/devtui/devtui-shortcuts.wasm.new" "$HOME/.local/share/devtui/devtui-shortcuts.wasm"
python3 "$ROOT/prototype/helix/shortcuts/fingerprint.py" "$ROOT" "$PREFIX" "$HOME/.local/share/devtui/devtui-shortcuts.wasm"
printf 'Installed Helix workspace and shortcuts; source retained at %s\n' "$SRC"
