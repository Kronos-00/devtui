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

function M.close_current_buffer()
  if protected_kind(vim.api.nvim_get_current_win()) ~= "editor" then
    return
  end
  require("config.devtui_tabs").close_buffer(vim.api.nvim_get_current_buf())
end

function M.discard_current_buffer()
  if protected_kind(vim.api.nvim_get_current_win()) ~= "editor" then
    return
  end
  delete_current_buffer(true)
end

function M.keep_region()
  local kind = protected_kind(vim.api.nvim_get_current_win())
  if kind then
    vim.notify(("devtui %s region stays open; close files/tabs instead"):format(kind), vim.log.levels.INFO)
  end
end

function M.rewrite_close_command(command)
  if vim.fn.getcmdtype() ~= ":" or vim.fn.getcmdline() ~= command then
    return command
  end

  local kind = protected_kind(vim.api.nvim_get_current_win())
  if kind == "editor" then
    if command:sub(-1) == "!" then
      return "DevTuiDiscardCurrent"
    end
    return "DevTuiCloseCurrent"
  elseif kind == "explorer" then
    return "DevTuiKeepRegion"
  end
  return command
end

function M.setup()
  if setup_done then
    return
  end
  setup_done = true

  _G.DevTuiRewriteCloseCommand = M.rewrite_close_command

  for _, name in ipairs({ "DevTuiCloseCurrent", "DevTuiDiscardCurrent", "DevTuiKeepRegion" }) do
    pcall(vim.api.nvim_del_user_command, name)
  end
  vim.api.nvim_create_user_command("DevTuiCloseCurrent", M.close_current_buffer, {})
  vim.api.nvim_create_user_command("DevTuiDiscardCurrent", M.discard_current_buffer, {})
  vim.api.nvim_create_user_command("DevTuiKeepRegion", M.keep_region, {})

  -- Reinterpret forced window-closing Ex commands when the current window is
  -- one of devtui's structural regions. Do not also abbreviate the non-bang
  -- prefixes (q, quit, close): Vim would expand the shorter prefix as soon as
  -- ! is typed and turn q! into an invalid UserCommand!.
  for _, command in ipairs({ "q!", "quit!", "close!" }) do
    vim.cmd(
      ("cnoreabbrev <expr> %s v:lua.DevTuiRewriteCloseCommand(%s)"):format(
        command,
        vim.fn.string(command)
      )
    )
  end

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
