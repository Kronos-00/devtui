#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/versions.env"
WORK="${DEVTUI_BUILD_DIR:-$HOME/.cache/devtui/build}"
SRC="$WORK/zellij-link-helix-$ZELLIJ_VERSION"
ARCHIVE="$WORK/zellij-$ZELLIJ_VERSION.tar.gz"
mkdir -p "$WORK" "$HOME/.local/share/devtui"
if ! command -v rustup >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
fi
# shellcheck disable=SC1090,SC1091
source "$HOME/.cargo/env"
rustup toolchain install "$RUST_VERSION" --profile minimal
rustup target add --toolchain "$RUST_VERSION" wasm32-wasip1
if [ ! -f "$ARCHIVE" ]; then
  curl -fsSL "https://github.com/zellij-org/zellij/archive/refs/tags/v$ZELLIJ_VERSION.tar.gz" -o "$ARCHIVE"
fi
echo "$ZELLIJ_SOURCE_SHA256  $ARCHIVE" | sha256sum -c -
rm -rf "$SRC"; mkdir -p "$SRC"
tar -xzf "$ARCHIVE" --strip-components=1 -C "$SRC"
sed "s|__DEVTUI_OPEN__|$HOME/.local/bin/devtui-helix-open|g" \
  "$ROOT/patches/zellij-link-devtui.patch" > "$WORK/zellij-link-helix.patch"
cd "$SRC"
patch -p1 < "$WORK/zellij-link-helix.patch"
cargo "+$RUST_VERSION" build --release --target wasm32-wasip1 -p link
install -m 0644 target/wasm32-wasip1/release/link.wasm \
  "$HOME/.local/share/devtui/zellij-link-devtui-helix.wasm"
