# Deployment

This guide reproduces the checked-in devtui environment on Ubuntu 24.04 / Linux x86_64 without requiring system-wide installation of Neovim, Zellij, or Lazygit.

## 1. Terminal prerequisites

Use a terminal with modern mouse reporting and Kitty keyboard-protocol support. Windows Terminal 1.25+ is recommended when connecting to a Linux host because devtui relies on combinations such as Ctrl/Alt + mouse and Ctrl+Shift+Z.

Use a Nerd Font in the host terminal if you want all tab/file icons to render correctly.

## 2. Clone

```bash
git clone git@github.com:Kronos-00/devtui.git
cd devtui
```

## 3. Install system build/runtime dependencies

On Ubuntu 24.04:

```bash
./scripts/install-system-deps-ubuntu.sh
```

This installs the generic build/runtime utilities used by the checked-in configuration: compiler toolchain, CMake, Git, curl, protobuf compiler, Python, ripgrep, fzf, fd, and delta.

## 4. Install devtui

```bash
./install.sh
```

The installer:

1. backs up existing Neovim/Zellij/Lazygit configuration into `~/.local/state/devtui/backup-<timestamp>`;
2. installs devtui helper commands under `~/.local/bin`;
3. installs Neovim 0.12.6 under `~/.local/opt/devtui`;
4. installs Lazygit 0.66.1 under `~/.local/opt/devtui`;
5. installs Rust 1.95.0 through rustup if necessary;
6. downloads Zellij 0.45.1 source, applies the checked-in mouse/link patches, builds its WASM plugins and main binary, and installs them under `~/.local/opt/devtui`;
7. renders Zellij/Lazygit templates using the target user's `$HOME`;
8. copies the pinned Neovim/LazyVim configuration and synchronizes plugins;
9. installs the editor tooling versions used by this configuration through Mason.

No shell rc file is modified.

### Config-only install

When the pinned binaries already exist and only configuration/scripts should be deployed:

```bash
./install.sh --config-only
```

To skip the Mason tools as well:

```bash
./install.sh --config-only --skip-mason
```

## 5. PATH

The install does not edit your shell startup files. Ensure your login environment includes:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Restart/login again if necessary.

## 6. First launch

From a project directory:

```bash
devtui
```

Or:

```bash
devtui /path/to/project
```

On the first launch Zellij may ask for permissions for the custom file-link plugin. Grant the requested permissions if you want Alt+click terminal paths to open in the existing Neovim editor.

## 7. Verify

```bash
tui-doctor
zellij setup --check
```

Inside devtui, verify:

- Explorer is visible and cannot be dismissed with Esc/q.
- Single-clicking a file opens/reuses a preview editor.
- Double-clicking pins the editor.
- Editing a preview pins it automatically.
- Ctrl/Alt + click toggles Explorer multi-selection.
- Middle-mouse drag creates column selections.
- Explorer right-edge drag resizes the sidebar in either direction.
- Dirty tabs keep a close control and prompt Save / Don't Save / Cancel.
- Double-clicking empty tab-strip space creates `[No Name]`.
- Alt+clicking a highlighted path in a terminal pane opens the file in the existing editor.
- The shell pane inherits the exported environment that launched devtui and does not re-read shell startup files.

## 8. Updating

Pull the repository and rerun the installer:

```bash
git pull --ff-only
./install.sh
```

A new backup is created before configuration is replaced.

## 9. Restore / uninstall

The installer prints the backup directory it created. Restore files from that backup as needed.

To remove the installed devtui binaries/data while leaving config directories untouched:

```bash
./uninstall.sh
```
