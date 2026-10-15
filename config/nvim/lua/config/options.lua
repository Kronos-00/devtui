-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

-- devtui runs inside Zellij without an X11/Wayland clipboard helper.
-- Force Neovim's built-in OSC 52 provider so "+/* registers reach the host terminal clipboard.
vim.g.clipboard = "osc52"
