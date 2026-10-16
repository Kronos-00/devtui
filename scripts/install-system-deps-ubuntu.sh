#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y \
  build-essential ca-certificates cmake curl file git git-delta gzip patch pkg-config \
  protobuf-compiler python3 python3-venv nodejs npm ripgrep tar unzip xz-utils fzf fd-find \
  clangd clang-format lldb shellcheck shfmt
