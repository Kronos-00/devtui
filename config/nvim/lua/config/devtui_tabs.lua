local M = {}

local function valid_buf(buf)
  return buf and buf > 0 and vim.api.nvim_buf_is_valid(buf)
end

local function buffer_name(buf)
  if not valid_buf(buf) then
    return "[No Name]"
  end
  local name = vim.api.nvim_buf_get_name(buf)
  if name == "" then
    return "[No Name]"
  end
  return vim.fn.fnamemodify(name, ":t")
end

local function delete_buffer(buf, force)
  if not valid_buf(buf) then
    return
  end
  if _G.Snacks and Snacks.bufdelete then
    Snacks.bufdelete({ buf = buf, force = force == true })
  else
    pcall(vim.cmd, (force and "bdelete! " or "bdelete ") .. buf)
  end
end
local function save_named(buf, force, done)
  local ok, err = pcall(vim.api.nvim_buf_call, buf, function()
    vim.cmd(force and "silent write!" or "silent write")
  end)
  if not ok then
    vim.notify(tostring(err), vim.log.levels.ERROR)
    return
  end
  if done then
    done()
  end
end

local function save_untitled(buf, force, done)
  vim.ui.input({
    prompt = "Save As: ",
    default = vim.fn.getcwd() .. "/",
    completion = "file",
  }, function(path)
    if not path or vim.trim(path) == "" then
      return
    end
    path = vim.fn.fnamemodify(path, ":p")
    local ok, err = pcall(vim.api.nvim_buf_call, buf, function()
      vim.cmd((force and "saveas! " or "saveas ") .. vim.fn.fnameescape(path))
    end)
    if not ok then
      vim.notify(tostring(err), vim.log.levels.ERROR)
      return
    end
    if done then
      done()
    end
  end)
end

function M.save_buffer(buf, opts, done)
  opts = opts or {}
  if not valid_buf(buf) then
    return
  end
  if vim.bo[buf].buftype ~= "" or not vim.bo[buf].modifiable then
    vim.notify("This buffer cannot be saved as a normal file", vim.log.levels.WARN)
    return
  end

  if vim.api.nvim_buf_get_name(buf) == "" then
    save_untitled(buf, opts.force == true, done)
  else
    save_named(buf, opts.force == true, done)
  end
end

function M.save_and_close(buf, opts)
  M.save_buffer(buf, opts or {}, function()
    delete_buffer(buf, false)
  end)
end

function M.close_buffer(buf)
  if not valid_buf(buf) then
    return
  end

  if not vim.bo[buf].modified then
    delete_buffer(buf, false)
    return
  end

  local label = buffer_name(buf)
  local choices = { "Save", "Don't Save", "Cancel" }
  vim.ui.select(choices, {
    prompt = ("Save changes to %s?"):format(label),
  }, function(choice)
    if choice == "Save" then
      local finish = function()
        delete_buffer(buf, false)
      end
      if vim.api.nvim_buf_get_name(buf) == "" then
        save_untitled(buf, false, finish)
      else
        save_named(buf, false, finish)
      end
    elseif choice == "Don't Save" then
      delete_buffer(buf, true)
    end
  end)
end
local function find_editor_win()
  if _G.Snacks and Snacks.picker and Snacks.picker.get then
    for _, picker in ipairs(Snacks.picker.get({ source = "explorer" })) do
      if picker.main and vim.api.nvim_win_is_valid(picker.main) then
        return picker.main
      end
    end
  end

  local current = vim.api.nvim_get_current_win()
  if vim.api.nvim_win_get_config(current).relative == "" then
    local buf = vim.api.nvim_win_get_buf(current)
    if vim.bo[buf].buftype == "" then
      return current
    end
  end

  for _, win in ipairs(vim.api.nvim_list_wins()) do
    if vim.api.nvim_win_get_config(win).relative == "" then
      local buf = vim.api.nvim_win_get_buf(win)
      if vim.bo[buf].buftype == "" then
        return win
      end
    end
  end
end
function M.new_untitled()
  local win = find_editor_win()
  if not win then
    return nil
  end

  local buf = vim.api.nvim_create_buf(true, false)
  vim.bo[buf].buflisted = true
  vim.b[buf].devtui_preview = nil
  vim.api.nvim_win_set_buf(win, buf)
  vim.api.nvim_set_current_win(win)
  return buf
end

local function bufferline_geometry()
  local ok_state, state = pcall(require, "bufferline.state")
  local ok_offset, offset = pcall(require, "bufferline.offset")
  local ok_ui, ui = pcall(require, "bufferline.ui")
  if not (ok_state and ok_offset and ok_ui) then
    return nil
  end

  pcall(ui.refresh)
  local off = offset.get()
  local left = tonumber(off.left_size) or 0
  local cursor = left
  local components = {}

  for _, component in ipairs(state.components or {}) do
    local buf = tonumber(component.id)
    if buf and valid_buf(buf) and vim.bo[buf].buflisted then
      local length = tonumber(component.length) or 0
      local start_col = cursor + 1
      local end_col = cursor + length
      components[#components + 1] = {
        buf = buf,
        start_col = start_col,
        end_col = end_col,
        length = length,
      }
      cursor = end_col
    end
  end

  return {
    left = left,
    used = math.min(cursor, vim.o.columns),
    components = components,
  }
end

local function rendered_tabline_width()
  local geometry = bufferline_geometry()
  return geometry and geometry.used or vim.o.columns
end

function M.handle_left_click(mouse)
  mouse = mouse or vim.fn.getmousepos()
  if mouse.screenrow ~= 1 then
    return false
  end

  local geometry = bufferline_geometry()
  if not geometry then
    return false
  end

  for _, component in ipairs(geometry.components) do
    if mouse.screencol >= component.start_col and mouse.screencol <= component.end_col then
      if vim.bo[component.buf].modified and mouse.screencol >= component.end_col - 3 then
        M.close_buffer(component.buf)
        return true
      end
      return false
    end
  end

  return false
end

function M.handle_double_click(mouse)
  mouse = mouse or vim.fn.getmousepos()
  if mouse.screenrow ~= 1 then
    return false
  end
  local used = rendered_tabline_width()
  if mouse.screencol <= used then
    return false
  end
  M.new_untitled()
  return true
end

return M
