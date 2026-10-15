local M = {}

local state = {
  preview_buf = nil,
  setup_done = false,
}

local function valid_buf(buf)
  return buf and buf > 0 and vim.api.nvim_buf_is_valid(buf)
end

local function valid_main_win(picker)
  return picker and picker.main and vim.api.nvim_win_is_valid(picker.main)
end

local function normalize(path)
  return vim.fs.normalize(vim.fn.fnamemodify(path, ":p"))
end

local function redraw_tabs()
  pcall(function()
    require("bufferline.ui").refresh()
  end)
  vim.cmd.redrawtabline()
end

local function mark_preview(buf, value)
  if not valid_buf(buf) then
    return
  end
  vim.b[buf].devtui_preview = value and true or nil

  if value and not vim.b[buf].devtui_preview_watch then
    vim.b[buf].devtui_preview_watch = true
    vim.api.nvim_buf_attach(buf, false, {
      on_lines = function(_, changed_buf)
        vim.schedule(function()
          if state.preview_buf == changed_buf
            and valid_buf(changed_buf)
            and vim.bo[changed_buf].modified
          then
            M.pin(changed_buf)
          end
        end)
      end,
      on_detach = function(_, detached_buf)
        if valid_buf(detached_buf) then
          vim.b[detached_buf].devtui_preview_watch = nil
        end
      end,
    })
  end

  redraw_tabs()
end
local function ensure_loaded(path)
  path = normalize(path)
  local existing = vim.fn.bufnr(path, false)
  local was_listed = existing > 0 and valid_buf(existing) and vim.bo[existing].buflisted
  local buf = existing

  if not valid_buf(buf) then
    buf = vim.fn.bufadd(path)
  end
  vim.fn.bufload(buf)
  vim.bo[buf].buflisted = true
  return buf, was_listed
end

local function promote_preview(buf)
  if not valid_buf(buf) then
    return
  end
  if state.preview_buf == buf then
    state.preview_buf = nil
  end
  mark_preview(buf, false)
end

local function empty_placeholder(buf)
  return valid_buf(buf)
    and vim.bo[buf].buftype == ""
    and not vim.bo[buf].modified
    and vim.api.nvim_buf_get_name(buf) == ""
    and vim.api.nvim_buf_line_count(buf) == 1
    and (vim.api.nvim_buf_get_lines(buf, 0, 1, false)[1] or "") == ""
end

local function cleanup_placeholder(previous, target)
  if previous == target or not empty_placeholder(previous) then
    return
  end
  vim.schedule(function()
    if valid_buf(previous) and #vim.fn.win_findbuf(previous) == 0 then
      pcall(vim.api.nvim_buf_delete, previous, { force = true })
    end
  end)
end

local function old_preview_can_close(buf, main_win)
  if not valid_buf(buf) then
    return false
  end
  if vim.bo[buf].modified then
    return false
  end
  for _, win in ipairs(vim.fn.win_findbuf(buf)) do
    if win ~= main_win then
      return false
    end
  end
  return true
end
local function replace_preview_if_needed(main_win, target)
  local old = state.preview_buf
  if not valid_buf(old) then
    state.preview_buf = nil
    return
  end
  if old == target then
    return
  end

  if old_preview_can_close(old, main_win) then
    state.preview_buf = nil
    mark_preview(old, false)
    vim.schedule(function()
      if valid_buf(old) and vim.api.nvim_win_get_buf(main_win) ~= old then
        pcall(vim.api.nvim_buf_delete, old, { force = false })
      end
    end)
  else
    promote_preview(old)
  end
end

function M.pin(buf)
  buf = buf or state.preview_buf
  if not valid_buf(buf) then
    return false
  end
  if state.preview_buf == buf then
    state.preview_buf = nil
  end
  mark_preview(buf, false)
  return true
end

function M.is_preview(buf)
  return valid_buf(buf) and state.preview_buf == buf and vim.b[buf].devtui_preview == true
end
function M.open_preview(picker, path)
  if not valid_main_win(picker) then
    return nil
  end
  local main_win = picker.main
  local previous = vim.api.nvim_win_get_buf(main_win)
  local target, was_listed = ensure_loaded(path)

  if target == state.preview_buf then
    vim.api.nvim_win_set_buf(main_win, target)
    cleanup_placeholder(previous, target)
    return target
  end

  -- A buffer that was already listed and is not the active preview is treated
  -- as a pinned editor. Selecting it focuses that tab without consuming preview.
  if was_listed and target ~= state.preview_buf then
    vim.api.nvim_win_set_buf(main_win, target)
    cleanup_placeholder(previous, target)
    return target
  end

  replace_preview_if_needed(main_win, target)
  vim.api.nvim_win_set_buf(main_win, target)
  cleanup_placeholder(previous, target)
  state.preview_buf = target
  mark_preview(target, true)
  return target
end

function M.open_pinned(picker, path)
  if not valid_main_win(picker) then
    return nil
  end
  local target = vim.fn.bufnr(normalize(path), false)

  if valid_buf(target) and target ~= state.preview_buf and vim.bo[target].buflisted then
    vim.api.nvim_win_set_buf(picker.main, target)
    return target
  end

  target = M.open_preview(picker, path)
  if target then
    M.pin(target)
  end
  return target
end
function M.setup()
  if state.setup_done then
    return
  end
  state.setup_done = true

  local group = vim.api.nvim_create_augroup("devtui_preview_editor", { clear = true })

  vim.api.nvim_create_autocmd("BufModifiedSet", {
    group = group,
    callback = function(args)
      local bufnr = args.buf
      vim.schedule(function()
        if bufnr == state.preview_buf
          and valid_buf(bufnr)
          and vim.bo[bufnr].modified
        then
          M.pin(bufnr)
        end
      end)
    end,
  })

  vim.api.nvim_create_autocmd({ "BufDelete", "BufWipeout" }, {
    group = group,
    callback = function(args)
      if args.buf == state.preview_buf then
        state.preview_buf = nil
      end
    end,
  })
end

M._state = state

return M
