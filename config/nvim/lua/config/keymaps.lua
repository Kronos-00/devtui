-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- This layer intentionally mirrors common VS Code Windows/Linux editor shortcuts.

local map = vim.keymap.set

local function load_plugin(name)
  pcall(function()
    require("lazy").load({ plugins = { name } })
  end)
end

local function stop_insert()
  local mode = vim.fn.mode()
  if mode == "i" or mode == "R" or mode == "Rv" then
    vim.cmd.stopinsert()
  end
end

local function save_as()
  local current = vim.api.nvim_buf_get_name(0)
  local default = current ~= "" and current or (vim.fn.getcwd() .. "/")
  vim.ui.input({ prompt = "Save As: ", default = default, completion = "file" }, function(path)
    if not path or path == "" then
      return
    end
    local ok, err = pcall(vim.cmd, "write " .. vim.fn.fnameescape(path))
    if not ok then
      vim.notify(err, vim.log.levels.ERROR)
    end
  end)
end

local function save()
  if vim.bo.buftype ~= "" or not vim.bo.modifiable then
    vim.notify("This buffer cannot be saved as a normal file", vim.log.levels.WARN)
    return
  end
  if vim.api.nvim_buf_get_name(0) == "" then
    save_as()
    return
  end
  local ok, err = pcall(vim.cmd, "silent update")
  if not ok then
    vim.notify(err, vim.log.levels.ERROR)
  end
end

local function select_all()
  stop_insert()
  pcall(function()
    require("multicursor-nvim").clearCursors()
  end)
  vim.cmd("normal! ggVG")
end

local function set_clipboard(value, regtype)
  vim.fn.setreg("+", value, regtype)
  vim.fn.setreg('"', value, regtype)
end

local function copy_vscode()
  if _G.DevTuiBoxSelectionActive and _G.DevTuiBoxSelectionActive() then
    _G.DevTuiBoxSelectionCopy()
    return
  end

  if vim.fn.mode():match("^[vV\22]") then
    -- Never read back from the + register: with the OSC52 provider that
    -- triggers a clipboard query and waits for a terminal response.
    -- Yank into an internal register first, then write the payload outward.
    vim.cmd([[normal! "zygv]])
    local contents = vim.fn.getreg("z", 1, true)
    local regtype = vim.fn.getregtype("z")
    vim.fn.setreg("+", contents, regtype)
    vim.fn.setreg('"', contents, regtype)
    return
  end

  -- VS Code copies the entire current line when there is no selection.
  set_clipboard({ vim.api.nvim_get_current_line() }, "V")
end

-- Expose the same copy semantics to multicursor.nvim's temporary keymap layer.
-- The normal/global Ctrl-C mapping below still calls this local function.
_G.DevTuiCopyVscode = copy_vscode

local function cut_vscode()
  if _G.DevTuiBoxSelectionActive and _G.DevTuiBoxSelectionActive() then
    _G.DevTuiBoxSelectionCut()
    return
  end

  if vim.fn.mode():match("^[vV\22]") then
    -- Cut through an internal register, then push the result to OSC52.
    -- Reading + would invoke OSC52 paste/query and block waiting for a reply.
    vim.cmd([[normal! "zx]])
    local contents = vim.fn.getreg("z", 1, true)
    local regtype = vim.fn.getregtype("z")
    vim.fn.setreg("+", contents, regtype)
    vim.fn.setreg('"', contents, regtype)

    load_plugin("multicursor.nvim")
    if _G.DevTuiArmCutPasteAnchor then
      local cur = vim.api.nvim_win_get_cursor(0)
      _G.DevTuiArmCutPasteAnchor({
        bufnr = vim.api.nvim_get_current_buf(),
        positions = { { row0 = cur[1] - 1, col0 = cur[2] } },
        main_idx = 1,
        main_pos = { cur[1], cur[2] },
      })
    end
    return
  end

  if vim.bo.buftype ~= "" or not vim.bo.modifiable then
    vim.notify("This buffer is not editable", vim.log.levels.WARN)
    return
  end

  local was_insert = vim.fn.mode():match("^[iR]") ~= nil
  local source_buf = vim.api.nvim_get_current_buf()
  if was_insert then
    vim.cmd.stopinsert()
  end

  local row = vim.api.nvim_win_get_cursor(0)[1]
  local col = vim.api.nvim_win_get_cursor(0)[2]
  local line = vim.api.nvim_get_current_line()
  set_clipboard({ line }, "V")

  local count = vim.api.nvim_buf_line_count(0)
  if count <= 1 then
    vim.api.nvim_set_current_line("")
    vim.api.nvim_win_set_cursor(0, { 1, 0 })
  else
    vim.api.nvim_buf_set_lines(0, row - 1, row, false, {})
    local new_row = math.min(row, vim.api.nvim_buf_line_count(0))
    local new_line = vim.api.nvim_buf_get_lines(0, new_row - 1, new_row, false)[1] or ""
    vim.api.nvim_win_set_cursor(0, { new_row, math.min(col, #new_line) })
  end

  load_plugin("multicursor.nvim")
  if _G.DevTuiArmCutPasteAnchor then
    local cur = vim.api.nvim_win_get_cursor(0)
    _G.DevTuiArmCutPasteAnchor({
      bufnr = vim.api.nvim_get_current_buf(),
      positions = { { row0 = cur[1] - 1, col0 = cur[2] } },
      main_idx = 1,
      main_pos = { cur[1], cur[2] },
    })
  end

  if was_insert then
    vim.schedule(function()
      if vim.api.nvim_buf_is_valid(source_buf) and vim.api.nvim_get_current_buf() == source_buf then
        vim.cmd.startinsert()
      end
    end)
  end
end

local CURRENT_REPLACE_INSTANCE = "devtui-current-file-replace"
local PROJECT_REPLACE_INSTANCE = "devtui-project-replace"

local function toggle_grug_instance(name, opts, use_visual)
  load_plugin("grug-far.nvim")
  local grug = require("grug-far")

  if grug.has_instance(name) then
    local instance = grug.get_instance(name)
    if instance then
      instance:close()
    end
    return
  end

  opts = vim.tbl_deep_extend("force", opts or {}, {
    instanceName = name,
    transient = false,
  })

  if use_visual and vim.fn.mode():match("^[vV\22]") then
    grug.with_visual_selection(opts)
  else
    grug.open(opts)
  end
end

local function replace_current_file()
  load_plugin("grug-far.nvim")
  local grug = require("grug-far")

  -- Toggle first, before looking at the current buffer path. This also means
  -- Ctrl-H closes the existing Replace UI when focus is already inside it.
  if grug.has_instance(CURRENT_REPLACE_INSTANCE) then
    local instance = grug.get_instance(CURRENT_REPLACE_INSTANCE)
    if instance then
      instance:close()
    end
    return
  end

  local path = vim.fn.expand("%:p")
  if path == "" or vim.bo.buftype ~= "" then
    vim.notify("Open/save a normal file before using current-file Replace", vim.log.levels.WARN)
    return
  end

  toggle_grug_instance(CURRENT_REPLACE_INSTANCE, {
    staticTitle = "Replace in Current File",
    prefills = { paths = path },
  }, true)
end

local function replace_project()
  toggle_grug_instance(PROJECT_REPLACE_INSTANCE, {
    staticTitle = "Replace in Project",
  }, false)
end

local function goto_line()
  vim.ui.input({ prompt = "Go to line: " }, function(value)
    local line = tonumber(value)
    if not line then
      return
    end
    line = math.max(1, math.min(line, vim.api.nvim_buf_line_count(0)))
    vim.api.nvim_win_set_cursor(0, { line, 0 })
    vim.cmd("normal! zz")
  end)
end

local function lsp_call(fn, message)
  if #vim.lsp.get_clients({ bufnr = 0 }) == 0 then
    vim.notify(message or "No LSP attached to this buffer", vim.log.levels.WARN)
    return
  end
  fn()
end

local function definition()
  lsp_call(function()
    if _G.Snacks and Snacks.picker and Snacks.picker.lsp_definitions then
      Snacks.picker.lsp_definitions()
    else
      vim.lsp.buf.definition()
    end
  end)
end

local function references()
  lsp_call(function()
    if _G.Snacks and Snacks.picker and Snacks.picker.lsp_references then
      Snacks.picker.lsp_references()
    else
      vim.lsp.buf.references()
    end
  end)
end

local function next_diagnostic(count)
  if vim.diagnostic.jump then
    vim.diagnostic.jump({ count = count, float = true })
  else
    local fn = count > 0 and vim.diagnostic.goto_next or vim.diagnostic.goto_prev
    fn({ float = true })
  end
end

-- Basic editing
map("n", "<C-z>", "u", { desc = "VS Code: Undo" })
map("i", "<C-z>", "<C-o>u", { desc = "VS Code: Undo" })
map("x", "<C-z>", "<Esc>u", { desc = "VS Code: Undo" })
map("n", "<C-y>", "<C-r>", { desc = "VS Code: Redo" })
map("i", "<C-y>", "<C-o><C-r>", { desc = "VS Code: Redo" })
map("x", "<C-y>", "<Esc><C-r>", { desc = "VS Code: Redo" })
map("n", "<C-S-z>", "<C-r>", { desc = "VS Code: Redo" })
map("i", "<C-S-z>", "<C-o><C-r>", { desc = "VS Code: Redo" })
map("x", "<C-S-z>", "<Esc><C-r>", { desc = "VS Code: Redo" })

-- Zellij uses F24 as an internal carrier for Ctrl-Shift-Z. This avoids
-- ambiguity in legacy terminal control-key encoding and works in all Nvim modes.
map("n", "<F24>", "<C-r>", { desc = "VS Code: Redo (terminal bridge)" })
map("i", "<F24>", "<C-o><C-r>", { desc = "VS Code: Redo (terminal bridge)" })
map("x", "<F24>", "<Esc><C-r>", { desc = "VS Code: Redo (terminal bridge)" })
map({ "n", "i", "x" }, "<C-c>", copy_vscode, { desc = "VS Code: Copy" })
map({ "n", "i", "x" }, "<C-x>", cut_vscode, { desc = "VS Code: Cut" })
map({ "n", "i", "x" }, "<C-s>", save, { desc = "VS Code: Save" })
map({ "n", "i", "x" }, "<C-S-s>", save_as, { desc = "VS Code: Save As" })
map({ "n", "i", "x" }, "<C-a>", select_all, { desc = "VS Code: Select All" })

local function discard_close_buffer()
  stop_insert()
  if _G.Snacks and Snacks.bufdelete then
    Snacks.bufdelete({ buf = vim.api.nvim_get_current_buf(), force = true })
  else
    vim.cmd("bdelete!")
  end
end

map("n", "<leader>bX", discard_close_buffer, { desc = "Discard Changes & Close Buffer" })
pcall(vim.api.nvim_del_user_command, "Bdiscard")
vim.api.nvim_create_user_command("Bdiscard", discard_close_buffer, {
  desc = "Discard all unsaved changes and close the current buffer",
})

-- Find / replace
map({ "n", "x" }, "<C-f>", "/", { desc = "VS Code: Find" })
map("i", "<C-f>", "<Esc>/", { desc = "VS Code: Find" })
map({ "n", "i", "x" }, "<C-h>", replace_current_file, { desc = "VS Code: Replace in File" })
map({ "n", "i", "x" }, "<C-S-f>", function()
  Snacks.picker.grep()
end, { desc = "VS Code: Search in Files" })
map({ "n", "i", "x" }, "<C-S-h>", replace_project, { desc = "VS Code: Replace in Files" })

-- Navigation / workbench-like actions
map({ "n", "i", "x" }, "<C-p>", function()
  Snacks.picker.files()
end, { desc = "VS Code: Quick Open" })
map({ "n", "i", "x" }, "<C-S-p>", function()
  Snacks.picker.commands()
end, { desc = "VS Code: Command Palette" })
map({ "n", "i", "x" }, "<F1>", function()
  Snacks.picker.commands()
end, { desc = "VS Code: Command Palette" })
map({ "n", "i", "x" }, "<A-g>", goto_line, { desc = "Go to Line (Ctrl-G reserved by Zellij)" })

local function focus_or_open_explorer(opts)
  stop_insert()
  if _G.Snacks and Snacks.picker and Snacks.picker.get then
    for _, picker in ipairs(Snacks.picker.get({ source = "explorer" })) do
      if not picker.closed and picker.list and picker.list.win and picker.list.win:valid() then
        picker.list.win:focus()
        return
      end
    end
  end
  Snacks.explorer(opts or {})
end

map({ "n", "i", "x" }, "<C-S-e>", function()
  focus_or_open_explorer({ cwd = LazyVim.root() })
end, { desc = "VS Code: Focus/Open Explorer" })
map("n", "<leader>e", function()
  focus_or_open_explorer({ cwd = LazyVim.root() })
end, { desc = "Focus/Open Explorer (root)" })
map("n", "<leader>fe", function()
  focus_or_open_explorer({ cwd = LazyVim.root() })
end, { desc = "Focus/Open Explorer (root)" })
map("n", "<leader>E", function()
  focus_or_open_explorer()
end, { desc = "Focus/Open Explorer (cwd)" })
map("n", "<leader>fE", function()
  focus_or_open_explorer()
end, { desc = "Focus/Open Explorer (cwd)" })
map({ "n", "i", "x" }, "<C-S-o>", function()
  stop_insert()
  if _G.Snacks and Snacks.picker and Snacks.picker.lsp_symbols and #vim.lsp.get_clients({ bufnr = 0 }) > 0 then
    Snacks.picker.lsp_symbols()
  elseif _G.Snacks and Snacks.picker and Snacks.picker.treesitter then
    Snacks.picker.treesitter()
  else
    vim.notify("No document-symbol provider available", vim.log.levels.WARN)
  end
end, { desc = "VS Code: Go to Symbol in Editor" })

map("n", "<C-l>", "V", { desc = "VS Code: Select Current Line" })
map("i", "<C-l>", "<Esc>V", { desc = "VS Code: Select Current Line" })
map("x", "<C-l>", "<Esc>V", { desc = "VS Code: Select Current Line" })

-- Comments. Ctrl+/ is commonly encoded as Ctrl-_ by terminal protocols.
for _, lhs in ipairs({ "<C-/>", "<C-_>" }) do
  map("n", lhs, "gcc", { remap = true, desc = "VS Code: Toggle Line Comment" })
  map("x", lhs, "gc", { remap = true, desc = "VS Code: Toggle Line Comment" })
  map("i", lhs, "<Esc>gccgi", { remap = true, desc = "VS Code: Toggle Line Comment" })
end

-- Multi-cursor / occurrences
map({ "n", "x" }, "<C-d>", function()
  load_plugin("multicursor.nvim")
  require("multicursor-nvim").matchAddCursor(1)
end, { desc = "VS Code: Add Selection to Next Find Match" })
map({ "n", "x" }, "<C-S-l>", function()
  load_plugin("multicursor.nvim")
  require("multicursor-nvim").matchAllAddCursors()
end, { desc = "VS Code: Select All Occurrences" })
map({ "n", "x" }, "<C-F2>", function()
  load_plugin("multicursor.nvim")
  require("multicursor-nvim").matchAllAddCursors()
end, { desc = "VS Code: Change All Occurrences" })

-- Rich language editing
map({ "n", "i", "x" }, "<F2>", function()
  lsp_call(vim.lsp.buf.rename)
end, { desc = "VS Code: Rename Symbol" })
map({ "n", "i", "x" }, "<F12>", definition, { desc = "VS Code: Go to Definition" })
map({ "n", "i", "x" }, "<S-F12>", references, { desc = "VS Code: Go to References" })
map({ "n", "i", "x" }, "<C-.>", function()
  lsp_call(vim.lsp.buf.code_action)
end, { desc = "VS Code: Quick Fix / Code Action" })
map({ "n", "i", "x" }, "<F8>", function()
  next_diagnostic(1)
end, { desc = "VS Code: Next Problem" })
map({ "n", "i", "x" }, "<S-F8>", function()
  next_diagnostic(-1)
end, { desc = "VS Code: Previous Problem" })

-- Line editing
map("n", "<C-CR>", "o", { desc = "VS Code: Insert Line Below" })
map("i", "<C-CR>", "<Esc>o", { desc = "VS Code: Insert Line Below" })
map("x", "<C-CR>", "<Esc>o", { desc = "VS Code: Insert Line Below" })
map("n", "<C-S-CR>", "O", { desc = "VS Code: Insert Line Above" })
map("i", "<C-S-CR>", "<Esc>O", { desc = "VS Code: Insert Line Above" })
map("x", "<C-S-CR>", "<Esc>O", { desc = "VS Code: Insert Line Above" })
map("n", "<C-S-k>", "dd", { desc = "VS Code: Delete Line" })
map("i", "<C-S-k>", "<Esc>ddi", { desc = "VS Code: Delete Line" })
map("x", "<C-S-k>", ":delete<CR>", { desc = "VS Code: Delete Lines" })
