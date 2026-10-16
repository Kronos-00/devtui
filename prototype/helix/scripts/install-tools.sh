#!/usr/bin/env bash
set -euo pipefail

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

npm install --silent --no-audit --no-fund --prefix "$NODE_PREFIX"   bash-language-server@5.8.1   pyright@1.1.414

python3 -m venv "$PYTHON_PREFIX"
"$PYTHON_PREFIX/bin/python" -m pip install --disable-pip-version-check --quiet   cmake-language-server==0.1.11   cmakelang==0.6.13   debugpy==1.8.22   ruff==0.17.0

link_tool() {
  local source="$1"
  local name="$2"
  ln -sfn "$source" "$BIN/$name"
}

link_tool "$NODE_PREFIX/node_modules/.bin/bash-language-server" bash-language-server
link_tool "$NODE_PREFIX/node_modules/.bin/pyright-langserver" pyright-langserver
link_tool "$NODE_PREFIX/node_modules/.bin/pyright" pyright
for name in cmake-language-server cmake-format cmakelint debugpy debugpy-adapter ruff; do
  if [ -x "$PYTHON_PREFIX/bin/$name" ]; then
    link_tool "$PYTHON_PREFIX/bin/$name" "$name"
  fi
done

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
