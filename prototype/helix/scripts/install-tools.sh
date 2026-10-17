#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

PREFIX="$HOME/.local/opt/devtui/helix-tools"
NODE_PREFIX="$PREFIX/node"
PYTHON_PREFIX="$PREFIX/python"
BIN="$PREFIX/bin"

for command in node npm python3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Missing dependency: $command" >&2
    exit 1
  }
done

mkdir -p "$NODE_PREFIX" "$BIN"

cp "$ROOT/prototype/helix/config/node-tools/"package*.json "$NODE_PREFIX/"
npm ci --silent --no-audit --no-fund --prefix "$NODE_PREFIX" --registry=https://registry.npmjs.org

python3 -I -m venv "$PYTHON_PREFIX"
"$PYTHON_PREFIX/bin/python" -I -m pip install --disable-pip-version-check --quiet -r "$ROOT/prototype/helix/config/python-tools.lock.txt"

link_tool() {
  local source="$1"
  local name="$2"
  ln -sfn "$source" "$BIN/$name"
}

link_tool "$NODE_PREFIX/node_modules/.bin/bash-language-server" bash-language-server
link_tool "$NODE_PREFIX/node_modules/.bin/pyright-langserver" pyright-langserver
link_tool "$NODE_PREFIX/node_modules/.bin/pyright" pyright
# Service dependencies are private. Ignore Python startup injection for the
# service interpreter without changing the environment seen by the user shell.
python3 -I - "$PYTHON_PREFIX" "$BIN" <<'PYWRAP'
from pathlib import Path
import os, shlex, sys
prefix, bindir = map(Path, sys.argv[1:])
for name in ('cmake-language-server','cmake-format','cmakelint','debugpy','debugpy-adapter'):
    target = prefix / 'bin' / name
    if not target.exists():
        continue
    output = bindir / name
    temporary = output.with_name(output.name + '.new')
    temporary.write_text('#!/bin/sh\nexec ' + shlex.quote(str(prefix/'bin/python')) + ' -I ' + shlex.quote(str(target)) + ' "$@"\n')
    temporary.chmod(0o755)
    os.replace(temporary, output)
PYWRAP
link_tool "$PYTHON_PREFIX/bin/ruff" ruff

echo "Installed portable Helix language/debug tools under $PREFIX"

cat > "$BIN/lldb-dap" <<'WRAPPER'
#!/usr/bin/env bash
set -e
for candidate in /usr/bin/lldb-dap /usr/bin/lldb-dap-* /usr/local/bin/lldb-dap /usr/local/bin/lldb-dap-*; do
  if [ -x "$candidate" ]; then
    exec "$candidate" "$@"
  fi
done
echo "lldb-dap was not found; install the distribution lldb package" >&2
exit 127
WRAPPER
chmod 0755 "$BIN/lldb-dap"
