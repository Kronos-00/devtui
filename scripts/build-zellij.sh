#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/versions.env"
PREFIX="${1:-$HOME/.local/opt/devtui/zellij-$ZELLIJ_VERSION}"
WORK="${DEVTUI_BUILD_DIR:-$HOME/.cache/devtui/build}"
SRC="$WORK/zellij-$ZELLIJ_VERSION"
mkdir -p "$WORK" "$PREFIX/bin" "$PREFIX/share/zellij/plugins" "$HOME/.local/share/devtui"

if ! command -v rustup >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
fi
# shellcheck disable=SC1090,SC1091
source "$HOME/.cargo/env"
rustup toolchain install "$RUST_VERSION" --profile minimal
rustup target add --toolchain "$RUST_VERSION" wasm32-wasip1

rm -rf "$SRC"
mkdir -p "$SRC"
ARCHIVE="$WORK/zellij-$ZELLIJ_VERSION.tar.gz"
curl -fsSL "https://github.com/zellij-org/zellij/archive/refs/tags/v$ZELLIJ_VERSION.tar.gz" -o "$ARCHIVE"
echo "$ZELLIJ_SOURCE_SHA256  $ARCHIVE" | sha256sum -c -
tar -xzf "$ARCHIVE" --strip-components=1 -C "$SRC"
cd "$SRC"
patch -p1 < "$ROOT/patches/zellij-0.45.1-mouse-passthrough.patch"
python3 - "$ROOT/patches/zellij-link-devtui.patch" "$HOME/.local/bin/tui-nvim-open" <<'PY'
from pathlib import Path
import sys
src=Path(sys.argv[1]).read_text().replace('__DEVTUI_OPEN__', sys.argv[2])
Path('/tmp/devtui-link.patch').write_text(src)
PY
patch -p1 < /tmp/devtui-link.patch

cargo "+$RUST_VERSION" build --release --target wasm32-wasip1 \
  -p status-bar -p tab-bar -p compact-bar -p strider -p session-manager \
  -p configuration -p plugin-manager -p about -p share -p multiple-select \
  -p layout-manager -p link
cp target/wasm32-wasip1/release/*.wasm "$PREFIX/share/zellij/plugins/"
cp target/wasm32-wasip1/release/link.wasm "$HOME/.local/share/devtui/zellij-link-devtui.wasm"

PREFIX="$PREFIX" CARGO_PROFILE_RELEASE_LTO=false CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16 \
  cargo "+$RUST_VERSION" build --release --bin zellij \
  --no-default-features --features disable_automatic_asset_installation
install -m 0755 target/release/zellij "$PREFIX/bin/zellij"
ln -sfn "$PREFIX/bin/zellij" "$HOME/.local/bin/zellij"
