#!/usr/bin/env bash
set -euo pipefail
nvim --headless '+Lazy! sync' +qa
nvim --headless \
  '+MasonInstall clangd@23.1.0 cmakelang@0.6.13 cmakelint@1.4.3 debugpy@1.8.22 lua-language-server@3.19.1 neocmakelsp@0.11.2 shellcheck@0.11.0 shfmt@3.14.1 stylua@2.6.0' \
  +qa
