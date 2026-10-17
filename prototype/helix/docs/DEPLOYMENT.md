# Deploy the Helix edition

## Supported baseline

The installer targets Linux with Bash, Python 3, Git, Cargo/rustup and a modern mouse-reporting terminal. The automated build/acceptance environment is Linux x86_64. Use the pinned, mouse-patched Zellij 0.45.1 and Lazygit supplied by normal devtui. Set a Nerd Font in your host terminal; fonts are not bundled.

## Existing devtui installation

```bash
git fetch origin
git switch helix-prototype
git pull --ff-only
./prototype/helix/scripts/install-system-deps-ubuntu.sh
./prototype/helix/install-prototype.sh
```

The system-dependency script is an explicit installation step. Starting the editor never invokes it. Install as the user who will run the IDE, not by changing HOME under an unrelated login unless intentionally managing a deployment.

## Fresh workstation

The root installer supplies the pinned Zellij/Lazygit workspace. It also installs the baseline Neovim configuration, backing up replaced configuration. Review that scope first:

```bash
git clone --branch helix-prototype git@github.com:Kronos-00/devtui.git
cd devtui
./scripts/install-system-deps-ubuntu.sh
./install.sh --skip-mason
./prototype/helix/scripts/install-system-deps-ubuntu.sh
./prototype/helix/install-prototype.sh
```

The Helix installer itself does not download the main Zellij or Lazygit binary; do not omit the base step on a fresh machine. A config-only installation is useful for development but is not a complete migration deployment:

```bash
./prototype/helix/install-prototype.sh --config-only
```

## Installed paths

Helpers: `~/.local/bin/devtui-helix*`. Editor/runtime/fingerprint: `~/.local/opt/devtui/helix-prototype`. Isolated language tools: `~/.local/opt/devtui/helix-tools`. Helix configuration: `~/.config/devtui-helix/helix`. Layouts: `~/.config/zellij/layouts/dev-helix*.kdl`. Terminal-link plugin: `~/.local/share/devtui/zellij-link-devtui-helix.wasm`.

Previous Helix settings are copied to `~/.local/state/devtui/helix-backup-*`. The Helix installer does not replace normal `devtui`, Neovim configuration or the global Zellij configuration.

Ensure the launching shell already has `~/.local/bin` on PATH. No rc/profile file is edited by the Helix installer. A full install builds pinned Rust sources, applies the ordered patches, builds and tests the link plugin, installs locked tools, and renders paths for the target user.

## Launch and verify

```bash
devtui-helix --version
devtui-helix --health clipboard
devtui-helix --health cpp
devtui-helix --health python
devtui-helix /path/to/project
```

`build-info.json` records the patched tree, binary SHA-256 and all patch SHA-256 values. The upstream `hx --version` may still display the pinned upstream revision even when patches are applied; the fingerprint is authoritative.

After updating, restart an existing Helix session. Do not kill a session containing unsaved work. Ctrl-Q is the full-session exit; normal file close commands preserve the editor region.

## Languages and project data

C/C++/CUDA use clangd and a project compilation database. A typical generic CMake project can generate it with `cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON`; configure the project/clangd to locate that database. Required compiler executables, SDK headers and flags are supplied by the project environment, not injected by devtui.

Python interpreter selection uses the command palette action `devtui_python_venv` (or Space c v) and remembers it for the workspace's editor services. The bottom shell is not changed. CMake, Bash and Python services use locked private dependencies; their runtime launchers do not import project Python startup paths.

Debugging uses LLDB DAP and debugpy. The deployment script installs the generic native adapter dependency, but host permissions may restrict process tracing. Compilation, vendor runtime behavior and GPU/device debugging require project-specific validation.

## Terminal permissions

Grant Zellij's terminal-link plugin its requested permissions when enabling path clicks. The host terminal must forward the desired mouse/key combinations. OSC 52 copying writes to the host clipboard; bracketed paste delivers host text. No clipboard query is sent by the middle-button column-selection path.

## Repeat acceptance checks

See [tests/README.md](../tests/README.md). Keep the installed binary, runtime and configuration from the same build. Do not copy an old binary while updating only the patches or docs.
