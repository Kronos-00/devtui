local M = {}

local setup_done = false

local function valid_win(win)
  return win and win > 0 and vim.api.nvim_win_is_valid(win)
end

function M.mark(win, kind)
  if valid_win(win) then
    vim.w[win].devtui_protected_region = kind
  end
end

function M.protect_picker(picker)
  if not picker then
    return
  end
  M.mark(picker.main, "editor")
  if picker.layout and picker.layout.root and picker.layout.root:win_valid() then
    M.mark(picker.layout.root.win, "explorer")
  end
  if picker.list and picker.list.win and picker.list.win:valid() then
    M.mark(picker.list.win.win, "explorer")
  end
  if picker.input and picker.input.win and picker.input.win:valid() then
    M.mark(picker.input.win.win, "explorer")
  end
end

local function protected_kind(win)
  if not valid_win(win) then
    return nil
  end
  return vim.w[win].devtui_protected_region
end

local function delete_current_buffer(force)
  local buf = vim.api.nvim_get_current_buf()
  if _G.Snacks and Snacks.bufdelete then
    Snacks.bufdelete({ buf = buf, force = force == true })
  else
    pcall(vim.cmd, (force and "bdelete! " or "bdelete ") .. buf)
  end
end

function M.quit_current(opts)
  opts = opts or {}
  local kind = protected_kind(vim.api.nvim_get_current_win())
  if kind == "explorer" then
    M.keep_region()
    return
  elseif kind ~= "editor" then
    return
  end

  if opts.bang then
    delete_current_buffer(true)
  else
    require("config.devtui_tabs").close_buffer(vim.api.nvim_get_current_buf())
  end
end

function M.write_quit_current(opts)
  opts = opts or {}
  local kind = protected_kind(vim.api.nvim_get_current_win())
  if kind == "explorer" then
    M.keep_region()
    return
  elseif kind ~= "editor" then
    return
  end

  require("config.devtui_tabs").save_and_close(vim.api.nvim_get_current_buf(), {
    force = opts.bang == true,
  })
end

function M.xit_current(opts)
  opts = opts or {}
  local kind = protected_kind(vim.api.nvim_get_current_win())
  if kind == "explorer" then
    M.keep_region()
    return
  elseif kind ~= "editor" then
    return
  end

  local buf = vim.api.nvim_get_current_buf()
  if vim.bo[buf].modified then
    require("config.devtui_tabs").save_and_close(buf, {
      force = opts.bang == true,
    })
  else
    delete_current_buffer(false)
  end
end

function M.keep_region()
  local kind = protected_kind(vim.api.nvim_get_current_win())
  if kind then
    vim.notify(("devtui %s region stays open; close files/tabs instead"):format(kind), vim.log.levels.INFO)
  end
end

function M.rewrite_close_command(command, replacement)
  if vim.fn.getcmdtype() ~= ":" or vim.fn.getcmdline() ~= command then
    return command
  end

  if protected_kind(vim.api.nvim_get_current_win()) then
    return replacement
  end
  return command
end

function M.setup()
  if setup_done then
    return
  end
  setup_done = true

  _G.DevTuiRewriteCloseCommand = M.rewrite_close_command

  for _, name in ipairs({
    "DevTuiQuit",
    "DevTuiWriteQuit",
    "DevTuiXit",
    "DevTuiKeepRegion",
    "DevTuiCloseCurrent",
    "DevTuiDiscardCurrent",
  }) do
    pcall(vim.api.nvim_del_user_command, name)
  end
  vim.api.nvim_create_user_command("DevTuiQuit", function(opts)
    M.quit_current({ bang = opts.bang })
  end, { bang = true })
  vim.api.nvim_create_user_command("DevTuiWriteQuit", function(opts)
    M.write_quit_current({ bang = opts.bang })
  end, { bang = true })
  vim.api.nvim_create_user_command("DevTuiXit", function(opts)
    M.xit_current({ bang = opts.bang })
  end, { bang = true })
  vim.api.nvim_create_user_command("DevTuiKeepRegion", M.keep_region, { bang = true })

  -- Map local window/tab-closing command families onto devtui commands that
  -- preserve the structural editor and Explorer windows. Mapping the base
  -- command is intentional: adding ! then produces a valid bang user command.
  local rewrites = {
    q = "DevTuiQuit",
    quit = "DevTuiQuit",
    close = "DevTuiQuit",
    wq = "DevTuiWriteQuit",
    x = "DevTuiXit",
    xit = "DevTuiXit",
    exit = "DevTuiXit",
  }
  for command, replacement in pairs(rewrites) do
    vim.cmd(
      ("cnoreabbrev <expr> %s v:lua.DevTuiRewriteCloseCommand(%s, %s)"):format(
        command,
        vim.fn.string(command),
        vim.fn.string(replacement)
      )
    )
  end

  -- Whole-Neovim quit variants would destroy the devtui editor process.
  -- Keep the IDE structure intact; Ctrl-q remains the supported session exit.
  for _, command in ipairs({ "qa", "qall", "wqa", "wqall", "xa", "xall", "cq", "cquit" }) do
    vim.cmd(
      ("cnoreabbrev <expr> %s v:lua.DevTuiRewriteCloseCommand(%s, %s)"):format(
        command,
        vim.fn.string(command),
        vim.fn.string("DevTuiKeepRegion")
      )
    )
  end

  vim.keymap.set("n", "ZZ", function()
    if protected_kind(vim.api.nvim_get_current_win()) then
      M.xit_current({ bang = false })
    else
      vim.api.nvim_feedkeys("ZZ", "n", false)
    end
  end, { silent = true, desc = "Save and close current devtui tab" })
  vim.keymap.set("n", "ZQ", function()
    if protected_kind(vim.api.nvim_get_current_win()) then
      M.quit_current({ bang = true })
    else
      vim.api.nvim_feedkeys("ZQ", "n", false)
    end
  end, { silent = true, desc = "Discard and close current devtui tab" })

  local group = vim.api.nvim_create_augroup("devtui_protected_regions", { clear = true })

  vim.api.nvim_create_autocmd("QuitPre", {
    group = group,
    callback = function()
      local win = vim.api.nvim_get_current_win()
      local kind = protected_kind(win)
      if not kind then
        return
      end

      vim.schedule(function()
        vim.notify(
          ("devtui %s region is fixed; close the file/tab instead of the UI region"):format(kind),
          vim.log.levels.WARN
        )
      end)
      error(("devtui protected %s region"):format(kind), 0)
    end,
  })
end

return M
