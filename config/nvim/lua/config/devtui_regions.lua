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
function M.setup()
  if setup_done then
    return
  end
  setup_done = true

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
