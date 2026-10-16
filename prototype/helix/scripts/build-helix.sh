#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COMMIT="$(cat "$ROOT/prototype/helix/HELIX_COMMIT")"
WORK="${DEVTUI_BUILD_DIR:-$HOME/.cache/devtui/helix-prototype}"
PREFIX="$HOME/.local/opt/devtui/helix-prototype"
TOOLCHAIN="${DEVTUI_HELIX_RUST:-1.95.0}"
if ! command -v rustup >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --no-modify-path
fi
# shellcheck disable=SC1090,SC1091
source "$HOME/.cargo/env"
rustup toolchain install "$TOOLCHAIN" --profile minimal
mkdir -p "$WORK" "$PREFIX/bin"
# Never delete an interrupted or user-edited checkout. Each build owns a new one.
SRC="$(mktemp -d "$WORK/source.XXXXXX")"
git -C "$SRC" init -q
git -C "$SRC" remote add origin https://github.com/helix-editor/helix.git
git -C "$SRC" fetch -q --depth 1 origin "$COMMIT"
git -C "$SRC" checkout -q --detach FETCH_HEAD
"$ROOT/prototype/helix/scripts/apply-patches.sh" "$SRC"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$WORK/target}"
RUSTUP_TOOLCHAIN="$TOOLCHAIN" cargo build --locked --release -p helix-term --bin hx --manifest-path "$SRC/Cargo.toml"
# Rename, rather than overwrite the executable of a running editor.
install -m 0755 "$CARGO_TARGET_DIR/release/hx" "$PREFIX/bin/hx.new"
cp -a "$SRC/runtime" "$PREFIX/runtime.new"
if [ -d "$PREFIX/runtime" ]; then mv "$PREFIX/runtime" "$WORK/runtime-$(date +%s%N)"; fi
mv "$PREFIX/runtime.new" "$PREFIX/runtime"
mv -f "$PREFIX/bin/hx.new" "$PREFIX/bin/hx"
python3 - "$ROOT" "$SRC" "$PREFIX" "$TOOLCHAIN" <<'PY'
import hashlib,json,pathlib,subprocess,sys
root,src,prefix=map(pathlib.Path,sys.argv[1:4])
patches=root/'prototype/helix/patches'
names=[n for n in (patches/'series').read_text().splitlines() if n and not n.startswith('#')]
meta={'upstream':(root/'prototype/helix/HELIX_COMMIT').read_text().strip(),
      'patched_tree':subprocess.check_output(['git','-C',str(src),'write-tree'],text=True).strip(),
      'rust':sys.argv[4], 'patches':{n:hashlib.sha256((patches/n).read_bytes()).hexdigest() for n in names}}
(prefix/'build-info.json').write_text(json.dumps(meta,indent=2)+'\n')
PY
printf 'Installed Helix; source retained at %s\n' "$SRC"
