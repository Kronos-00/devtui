#!/usr/bin/env bash
set -euo pipefail
# Explicit deployment step, never called when starting the IDE or shell pane.
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  build-essential clangd clang-format lldb-18 cmake ninja-build \
  python3 python3-venv python3-pip nodejs npm shellcheck shfmt \
  git curl ca-certificates pkg-config protobuf-compiler
