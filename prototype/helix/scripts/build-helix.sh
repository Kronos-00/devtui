#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COMMIT="$(cat "$ROOT/prototype/helix/HELIX_COMMIT")"
WORK="${DEVTUI_BUILD_DIR:-$HOME/.cache/devtui/helix-prototype}"
SRC="$WORK/src"
PREFIX="$HOME/.local/opt/devtui/helix-prototype"
if ! command -v rustup >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
fi
# shellcheck disable=SC1090,SC1091
source "$HOME/.cargo/env"
rustup toolchain install 1.95.0 --profile minimal
rm -rf "$SRC"
mkdir -p "$WORK" "$PREFIX/bin"
git clone -q https://github.com/helix-editor/helix.git "$SRC"
git -C "$SRC" checkout -q "$COMMIT"
git -C "$SRC" apply "$ROOT/prototype/helix/patches/0001-middle-drag-multiselection.patch"
RUSTUP_TOOLCHAIN="${DEVTUI_HELIX_RUST:-1.95.0}" cargo build --release -p helix-term --bin hx --manifest-path "$SRC/Cargo.toml"
install -m 0755 "$SRC/target/release/hx" "$PREFIX/bin/hx"
rm -rf "$PREFIX/runtime"
cp -a "$SRC/runtime" "$PREFIX/runtime"
