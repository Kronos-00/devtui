#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/versions.env"
WORK="${DEVTUI_BUILD_DIR:-$HOME/.cache/devtui/build}"
ARCHIVE="$WORK/zellij-$ZELLIJ_VERSION.tar.gz"
mkdir -p "$WORK" "$HOME/.local/share/devtui"
if ! command -v rustup >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --no-modify-path
fi
# shellcheck disable=SC1090,SC1091
if [ -f "${CARGO_HOME:-$HOME/.cargo}/env" ]; then source "${CARGO_HOME:-$HOME/.cargo}/env"; fi
rustup toolchain install "$RUST_VERSION" --profile minimal
rustup target add --toolchain "$RUST_VERSION" wasm32-wasip1
if [ ! -f "$ARCHIVE" ]; then
  curl -fsSL "https://github.com/zellij-org/zellij/archive/refs/tags/v$ZELLIJ_VERSION.tar.gz" -o "$ARCHIVE"
fi
echo "$ZELLIJ_SOURCE_SHA256  $ARCHIVE" | sha256sum -c -
SRC="$(mktemp -d "$WORK/zellij-link-helix-$ZELLIJ_VERSION.XXXXXX")"
tar -xzf "$ARCHIVE" --strip-components=1 -C "$SRC"
python3 - "$ROOT/patches/zellij-link-devtui.patch" "$HOME/.local/bin/devtui-helix-open" "$SRC/devtui-link.patch" <<'PYTHON'
from pathlib import Path
import json,sys
text=Path(sys.argv[1]).read_text().replace('__DEVTUI_OPEN__',json.dumps(sys.argv[2],ensure_ascii=False)[1:-1])
Path(sys.argv[3]).write_text(text)
PYTHON
cd "$SRC"
patch -p1 < "$SRC/devtui-link.patch"
patch -p1 < "$ROOT/prototype/helix/zellij/link-paths.patch"
cargo "+$RUST_VERSION" test --locked -p link
cargo "+$RUST_VERSION" build --locked --release --target wasm32-wasip1 -p link
ASSET="$HOME/.local/share/devtui/zellij-link-devtui-helix.wasm"
install -m 0644 "${CARGO_TARGET_DIR:-$SRC/target}/wasm32-wasip1/release/link.wasm" "$ASSET.new"
mv -f "$ASSET.new" "$ASSET"
python3 - "$ROOT" "$ASSET" "$ZELLIJ_VERSION" <<'META'
import hashlib,json,pathlib,sys
root,asset=map(pathlib.Path,sys.argv[1:3])
paths=['patches/zellij-link-devtui.patch','prototype/helix/zellij/link-paths.patch']
meta={'zellij_version':sys.argv[3],'binary_sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),
      'patches':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}}
asset.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
META
printf 'Installed terminal-link plugin; source retained at %s\n' "$SRC"
