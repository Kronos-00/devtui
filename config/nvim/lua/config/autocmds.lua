-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
--
-- Add any additional autocmds here
-- with `vim.api.nvim_create_autocmd`
--
-- Or remove existing autocmds by their group name (which is prefixed with `lazyvim_` for the defaults)
-- e.g. vim.api.nvim_del_augroup_by_name("lazyvim_wrap_spell")

-- Keep Markdown source punctuation visible at all times. conceallevel is
-- window-local, so FileType alone is insufficient when a Markdown buffer is
-- loaded in the background by the VS Code-style preview editor.
local markdown_visible_group = vim.api.nvim_create_augroup("devtui_markdown_source_visible", { clear = true })

local function reveal_markdown_source(buf)
  if not buf or not vim.api.nvim_buf_is_valid(buf) then
    return
  end
  local ft = vim.bo[buf].filetype
  if ft ~= "markdown" and ft ~= "markdown.mdx" then
    return
  end
  for _, win in ipairs(vim.fn.win_findbuf(buf)) do
    if vim.api.nvim_win_is_valid(win) then
      vim.wo[win].conceallevel = 0
      vim.wo[win].concealcursor = ""
    end
  end
end

vim.api.nvim_create_autocmd("FileType", {
  group = markdown_visible_group,
  pattern = { "markdown", "markdown.mdx" },
  callback = function(args)
    vim.schedule(function()
      reveal_markdown_source(args.buf)
    end)
  end,
})

vim.api.nvim_create_autocmd({ "BufWinEnter", "WinEnter" }, {
  group = markdown_visible_group,
  callback = function(args)
    reveal_markdown_source(args.buf)
  end,
})

-- Make Grug FAR behave like a single VS Code Replace panel: Esc or Ctrl-H
-- closes the active instance immediately, even while editing an input field.
vim.api.nvim_create_autocmd("FileType", {
  group = vim.api.nvim_create_augroup("devtui_grug_far_close", { clear = true }),
  pattern = "grug-far",
  callback = function(args)
    local function close_grug()
      local ok, grug = pcall(require, "grug-far")
      if not ok then
        return
      end
      local instance = grug.get_instance(0)
      if instance then
        instance:close()
      end
    end

    vim.keymap.set({ "n", "i", "x" }, "<Esc>", close_grug, {
      buffer = args.buf,
      nowait = true,
      desc = "Close Replace panel",
    })
    vim.keymap.set({ "n", "i", "x" }, "<C-h>", close_grug, {
      buffer = args.buf,
      nowait = true,
      desc = "Toggle Replace panel",
    })
  end,
})
