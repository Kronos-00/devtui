local M = {}

local uv = vim.uv or vim.loop
local Preview = require("config.devtui_preview")
local Tabs = require("config.devtui_tabs")
local Regions = require("config.devtui_regions")
local context = nil
local file_clipboard = { items = {} }
local selection_ns = vim.api.nvim_create_namespace("devtui_explorer_selection")
local resize_state = {
  active = false,
  picker = nil,
  last_col = 0,
  last_width = 0,
  gesture_id = 0,
  save_generation = 0,
}
local resize_listener_installed = false
local mouse_dispatch_installed = false
local resize_key_ns = vim.api.nvim_create_namespace("devtui_explorer_resize")
local RESIZE_HANDLE_CELLS = 3
local EXPLORER_MIN_WIDTH = 12
local RESIZE_STATE_FILE = vim.fn.expand("~/.local/state/devtui/explorer-width")

local function norm(path)
  return vim.fs.normalize(vim.fn.fnamemodify(path, ":p"))
end

local function exists(path)
  return uv.fs_stat(path) ~= nil
end

local function starts_with_path(path, parent)
  path, parent = norm(path), norm(parent)
  return path == parent or path:sub(1, #parent + 1) == parent .. "/"
end

local function copy_text(text)
  vim.fn.setreg("+", text, "v")
  vim.fn.setreg('"', text, "v")
end

local function picker_alive(picker)
  return picker and not picker.closed and picker.list and picker.list.win and picker.list.win:valid()
end

local function load_saved_width()
  local f = io.open(RESIZE_STATE_FILE, "r")
  if not f then
    return nil
  end
  local value = tonumber(vim.trim(f:read("*a") or ""))
  f:close()
  return value and math.floor(value) or nil
end

local function save_width(width)
  vim.fn.mkdir(vim.fs.dirname(RESIZE_STATE_FILE), "p")
  local f = io.open(RESIZE_STATE_FILE, "w")
  if f then
    f:write(tostring(math.floor(width)), "\n")
    f:close()
  end
end

local function explorer_width_bounds(picker)
  -- VS Code constrains the sidebar with an explicit minimum size, but its sash
  -- remains continuously draggable in either direction for the whole gesture.
  -- In a character-cell TUI, 12 columns is the practical equivalent: narrow
  -- enough to collapse the tree aggressively without making the layout invalid.
  local min_width = EXPLORER_MIN_WIDTH
  local current = picker.layout and picker.layout.root:win_valid()
      and vim.api.nvim_win_get_width(picker.layout.root.win)
    or min_width
  local max_width = math.max(min_width, current, vim.o.columns - 12)
  return min_width, max_width
end

local function set_explorer_width(picker, width)
  if not picker_alive(picker) or not picker.layout or not picker.layout.root:win_valid() then
    return false
  end
  local min_width, max_width = explorer_width_bounds(picker)
  width = math.max(min_width, math.min(math.floor(width), max_width))

  picker.opts.layout = picker.opts.layout or {}
  picker.opts.layout.layout = picker.opts.layout.layout or {}
  picker.opts.layout.layout.width = width
  picker.opts.layout.layout.min_width = EXPLORER_MIN_WIDTH

  if picker.resolved_layout and picker.resolved_layout.layout then
    picker.resolved_layout.layout.width = width
    picker.resolved_layout.layout.min_width = EXPLORER_MIN_WIDTH
  end

  picker.layout.opts.layout.width = width
  picker.layout.opts.layout.min_width = EXPLORER_MIN_WIDTH
  if picker.layout.opts.layout[1] then
    picker.layout.opts.layout[1].min_width = EXPLORER_MIN_WIDTH
  end
  picker.layout.root.opts.width = width
  picker.layout.root.opts.min_width = EXPLORER_MIN_WIDTH

  if vim.api.nvim_win_get_width(picker.layout.root.win) ~= width then
    vim.api.nvim_win_set_width(picker.layout.root.win, width)
  end
  picker.layout:update()
  return true
end

local function resize_edge_hit(picker, mouse)
  if not picker_alive(picker) or not picker.layout or not picker.layout.root:win_valid() then
    return false
  end
  mouse = mouse or vim.fn.getmousepos()
  local root = picker.layout.root.win
  local pos = vim.api.nvim_win_get_position(root)
  local width = vim.api.nvim_win_get_width(root)
  local height = vim.api.nvim_win_get_height(root)

  -- Neovim reports screen positions as 1-based while window positions are
  -- 0-based. The real split separator is one cell to the right of the root.
  local boundary = pos[2] + width + 1
  local top = pos[1] + 1
  local bottom = top + height - 1
  return mouse.screenrow >= top
    and mouse.screenrow <= bottom
    and mouse.screencol >= boundary - (RESIZE_HANDLE_CELLS - 1)
    and mouse.screencol <= boundary
end

local function schedule_width_save(width)
  resize_state.save_generation = resize_state.save_generation + 1
  local generation = resize_state.save_generation
  vim.defer_fn(function()
    if resize_state.save_generation == generation then
      save_width(width)
    end
  end, 220)
end

function M.start_resize(picker)
  local mouse = vim.fn.getmousepos()
  if not resize_edge_hit(picker, mouse) then
    return false
  end
  resize_state.active = true
  resize_state.picker = picker
  resize_state.last_col = mouse.screencol
  resize_state.last_width = vim.api.nvim_win_get_width(picker.layout.root.win)
  resize_state.gesture_id = resize_state.gesture_id + 1
  return true
end

function M.resize_drag()
  local picker = resize_state.picker
  if not resize_state.active or not picker_alive(picker) then
    resize_state.active = false
    resize_state.picker = nil
    return false
  end

  local mouse = vim.fn.getmousepos()
  local delta = mouse.screencol - resize_state.last_col
  if delta ~= 0 then
    local desired = resize_state.last_width + delta
    if set_explorer_width(picker, desired) then
      resize_state.last_width = vim.api.nvim_win_get_width(picker.layout.root.win)
      resize_state.last_col = mouse.screencol
      schedule_width_save(resize_state.last_width)
    end
  end
  return true
end

function M.finish_resize()
  local picker = resize_state.picker
  if not resize_state.active then
    return false
  end
  resize_state.active = false
  resize_state.picker = nil
  if picker_alive(picker) and picker.layout and picker.layout.root:win_valid() then
    local width = vim.api.nvim_win_get_width(picker.layout.root.win)
    resize_state.last_width = width
    save_width(width)
  end
  return true
end

local function install_resize_listener()
  if resize_listener_installed then
    return
  end
  resize_listener_installed = true

  vim.on_key(function(key, typed)
    local raw = (typed and typed ~= "") and typed or key
    local text = vim.fn.keytrans(raw)

    if text:find("<LeftDrag>", 1, true) then
      if resize_state.active then
        vim.schedule(function()
          if resize_state.active then
            M.resize_drag()
          end
        end)
      end
      return
    end

    -- Neovim does not expose LeftRelease consistently through mappings/on_key.
    -- Keep the resize session alive across pauses and finish it lazily on the
    -- next ordinary left press that is not on the Explorer resize handle.
    if resize_state.active and text:find("<LeftMouse>", 1, true) then
      vim.schedule(function()
        local picker = resize_state.picker
        if resize_state.active and (not picker_alive(picker) or not resize_edge_hit(picker, vim.fn.getmousepos())) then
          M.finish_resize()
        end
      end)
    end
  end, resize_key_ns)
end

local function render_selection_highlights(picker)
  if not picker_alive(picker) then
    return
  end
  local list = picker.list
  local buf = list.win.buf
  vim.api.nvim_buf_clear_namespace(buf, selection_ns, 0, -1)
  for idx = 1, picker:count() do
    local item = list:get(idx)
    if item and list:is_selected(item) then
      local row = list:idx2row(idx)
      if row >= 1 and row <= list.state.height then
        pcall(vim.api.nvim_buf_set_extmark, buf, selection_ns, row - 1, 0, {
          line_hl_group = "Visual",
          priority = 180,
        })
      end
    end
  end
end

local function ensure_picker_ui(picker)
  if not picker_alive(picker) or picker.list._devtui_ui_wrapped then
    return
  end
  local list = picker.list
  list._devtui_ui_wrapped = true

  local original_render = list.render
  list.render = function(self, ...)
    local ret = original_render(self, ...)
    render_selection_highlights(picker)
    return ret
  end
end
local function refresh_target(picker, path, reveal)
  if not picker_alive(picker) then
    return
  end
  local Tree = require("snacks.explorer.tree")
  local Actions = require("snacks.explorer.actions")
  local parent = vim.fs.dirname(path)
  Tree:refresh(parent)
  Tree:open(parent)
  Actions.update(picker, { target = reveal and path or parent, refresh = true })
end

local function validate_child(base, value)
  value = vim.trim(value or "")
  if value == "" or value:sub(1, 1) == "/" then
    return nil, "Enter a relative name"
  end
  local path = norm(vim.fs.joinpath(base, value))
  local base_n = norm(base)
  if path == base_n or not starts_with_path(path, base_n) then
    return nil, "The new path must stay inside the selected folder"
  end
  return path
end

local function open_created_file(picker, path)
  vim.schedule(function()
    if picker_alive(picker) and picker.main and vim.api.nvim_win_is_valid(picker.main) then
      vim.api.nvim_set_current_win(picker.main)
      vim.cmd.edit(vim.fn.fnameescape(path))
    end
  end)
end
local function new_entry(kind)
  local c = context
  if not c or not c.target_dir or not picker_alive(c.picker) then
    return
  end
  local label = kind == "file" and "New File" or "New Folder"
  Snacks.input({ prompt = label .. ": " }, function(value)
    if value == nil then
      return
    end
    local path, err = validate_child(c.target_dir, value)
    if not path then
      Snacks.notify.warn(err)
      return
    end
    if exists(path) then
      Snacks.notify.warn(("Already exists:\n- %s"):format(path))
      return
    end
    if kind == "folder" then
      vim.fn.mkdir(path, "p")
      refresh_target(c.picker, path, true)
      return
    end
    vim.fn.mkdir(vim.fs.dirname(path), "p")
    local f, ferr = io.open(path, "w")
    if not f then
      Snacks.notify.error(("Failed to create %s:\n%s"):format(path, ferr or "unknown error"))
      return
    end
    f:close()
    refresh_target(c.picker, path, true)
    open_created_file(c.picker, path)
  end)
end
local function split_extension(name, is_dir)
  if is_dir then
    return name, ""
  end
  local dot = name:match("^.*()%.")
  if not dot or dot <= 1 then
    return name, ""
  end
  return name:sub(1, dot - 1), name:sub(dot)
end

local function increment_simple(name, is_dir)
  local stem, ext = split_extension(name, is_dir)
  local base, number = stem:match("^(.- copy) (%d+)$")
  if base and number then
    return base .. " " .. tostring(tonumber(number) + 1) .. ext
  end
  if stem:match(" copy$") then
    return stem .. " 2" .. ext
  end
  return stem .. " copy" .. ext
end

local function paste_target(src, target_dir, is_dir)
  local name = vim.fs.basename(src)
  local candidate = norm(vim.fs.joinpath(target_dir, name))
  while exists(candidate) do
    name = increment_simple(name, is_dir)
    candidate = norm(vim.fs.joinpath(target_dir, name))
  end
  return candidate
end
local function context_items(c)
  if not c then
    return {}
  end
  if c.items and #c.items > 0 then
    return c.items
  end
  return c.item and { c.item } or {}
end

local function distinct_non_root_items(items, root)
  local entries = {}
  for _, item in ipairs(items or {}) do
    if item and item.file then
      local path = norm(item.file)
      if path ~= root and exists(path) then
        entries[#entries + 1] = { path = path, is_dir = item.dir == true }
      end
    end
  end
  table.sort(entries, function(a, b)
    if #a.path == #b.path then
      return a.path < b.path
    end
    return #a.path < #b.path
  end)
  local ret = {}
  for _, entry in ipairs(entries) do
    local nested = false
    for _, parent in ipairs(ret) do
      if parent.is_dir and starts_with_path(entry.path, parent.path) then
        nested = true
        break
      end
    end
    if not nested then
      ret[#ret + 1] = entry
    end
  end
  return ret
end

local function clipboard_has_items()
  for _, entry in ipairs(file_clipboard.items or {}) do
    if entry.path and exists(entry.path) then
      return true
    end
  end
  return false
end

local function copy_item()
  local c = context
  if not c or not c.item or c.is_root then
    return
  end
  local entries = {}
  for _, item in ipairs(context_items(c)) do
    if item and item.file then
      local path = norm(item.file)
      if path ~= c.root and exists(path) then
        entries[#entries + 1] = { path = path, is_dir = item.dir == true }
      end
    end
  end
  file_clipboard.items = vim.deepcopy(entries)
end

local function paste_item()
  local c = context
  if not c or not c.target_dir or not clipboard_has_items() then
    file_clipboard.items = {}
    return
  end
  local copied = {}
  for _, entry in ipairs(file_clipboard.items) do
    local src = norm(entry.path)
    if exists(src) then
      if entry.is_dir and starts_with_path(c.target_dir, src) then
        Snacks.notify.warn(("Cannot paste '%s' into itself or one of its descendants"):format(vim.fs.basename(src)))
      else
        local to = paste_target(src, c.target_dir, entry.is_dir)
        Snacks.picker.util.copy_path(src, to)
        if exists(to) then
          copied[#copied + 1] = to
        end
      end
    end
  end
  if #copied > 0 then
    refresh_target(c.picker, copied[#copied], true)
  end
end

local function copy_path(relative)
  local c = context
  if not c then
    return
  end
  local values = {}
  local items = context_items(c)
  if #items == 0 then
    items = { { file = c.path } }
  end
  for _, item in ipairs(items) do
    local path = norm(item.file or c.path)
    values[#values + 1] = relative and (vim.fs.relpath(c.root, path) or path) or path
  end
  copy_text(table.concat(values, "\n"))
end

local function entry_contains(entry, path)
  path = norm(path)
  return path == entry.path or (entry.is_dir and starts_with_path(path, entry.path))
end

local function modified_buffers_under(entries)
  local ret, seen = {}, {}
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_valid(buf) and vim.bo[buf].modified then
      local name = vim.api.nvim_buf_get_name(buf)
      if name ~= "" then
        for _, entry in ipairs(entries) do
          if entry_contains(entry, name) and not seen[buf] then
            seen[buf] = true
            ret[#ret + 1] = buf
            break
          end
        end
      end
    end
  end
  return ret
end

local function delete_item()
  local c = context
  if not c or not c.item or c.is_root then
    return
  end
  local entries = distinct_non_root_items(context_items(c), c.root)
  if #entries == 0 then
    return
  end
  local dirty = modified_buffers_under(entries)
  local prompt
  if #entries == 1 then
    prompt = ("Delete '%s'?"):format(vim.fs.basename(entries[1].path))
  else
    prompt = ("Delete %d selected items?"):format(#entries)
  end
  if #dirty > 0 then
    prompt = prompt .. (" (%d unsaved buffer%s will be discarded)"):format(#dirty, #dirty == 1 and "" or "s")
  end
  Snacks.picker.util.confirm(prompt, function()
    local Actions = require("snacks.explorer.actions")
    local deleted = {}
    for _, entry in ipairs(entries) do
      local ok, err = Actions.trash(entry.path)
      if ok then
        deleted[#deleted + 1] = entry
      else
        Snacks.notify.error(("Failed to delete %s:\n%s"):format(entry.path, err or "unknown error"))
      end
    end
    for _, buf in ipairs(vim.api.nvim_list_bufs()) do
      if vim.api.nvim_buf_is_valid(buf) then
        local name = vim.api.nvim_buf_get_name(buf)
        if name ~= "" then
          for _, entry in ipairs(deleted) do
            if entry_contains(entry, name) then
              pcall(Snacks.bufdelete, { buf = buf, force = true })
              break
            end
          end
        end
      end
    end
    file_clipboard.items = vim.tbl_filter(function(clip)
      for _, entry in ipairs(deleted) do
        if entry_contains(entry, clip.path) then
          return false
        end
      end
      return exists(clip.path)
    end, file_clipboard.items or {})
    if picker_alive(c.picker) then
      c.picker.list:set_selected({})
      local Tree = require("snacks.explorer.tree")
      local Actions2 = require("snacks.explorer.actions")
      Tree:refresh(c.root)
      Actions2.update(c.picker, { refresh = true })
    end
  end)
end

local function menu_add(priority, label, global_fn)
  local escaped = label:gsub(" ", "\\ ")
  vim.cmd(("anoremenu <silent> %s DevTuiExplorerPopUp.%s <Cmd>lua _G.%s()<CR>"):format(priority, escaped, global_fn))
end

local function menu_sep(priority, name)
  vim.cmd(("anoremenu <silent> %s DevTuiExplorerPopUp.-%s- <Nop>"):format(priority, name))
end

local function build_menu()
  pcall(vim.cmd, "silent! aunmenu DevTuiExplorerPopUp")
  local c = context
  if not c then
    return
  end
  local have_group1 = c.target_dir ~= nil
  if have_group1 then
    menu_add("500.10", "New File", "DevTuiExplorerNewFile")
    menu_add("500.20", "New Folder", "DevTuiExplorerNewFolder")
    menu_add("500.30", "Paste", "DevTuiExplorerPaste")
    if not clipboard_has_items() then
      vim.cmd("menu disable DevTuiExplorerPopUp.Paste")
    end
    menu_sep("500.40", "Path")
  end

  menu_add("500.50", "Copy Path", "DevTuiExplorerCopyPath")
  menu_add("500.60", "Copy Relative Path", "DevTuiExplorerCopyRelativePath")

  if c.item and not c.is_root then
    menu_sep("500.70", "Modify")
    menu_add("500.80", "Copy", "DevTuiExplorerCopy")
    menu_add("500.90", "Delete", "DevTuiExplorerDelete")
  end
end

local function native_mouse(key)
  -- Mouse mappings are resolved against the *current* buffer before Neovim
  -- changes focus to the window under the pointer. Explorer therefore must
  -- explicitly fall through for clicks aimed at the editor/tabline.
  vim.api.nvim_feedkeys(vim.keycode(key), "n", false)
end

local function item_at_mouse(picker)
  local mouse = vim.fn.getmousepos()
  local win = picker.list.win.win
  if mouse.winid ~= win then
    return nil, nil
  end

  -- Resolve only physical rows that correspond to rendered Explorer items.
  local row = tonumber(mouse.winrow) or 0
  if row < 1 or row > picker.list:height() then
    return nil, nil
  end
  local idx = picker.list:row2idx(row)
  if idx < 1 or idx > picker:count() then
    return nil, nil
  end
  local item = picker.list:get(idx)
  if item and item.file then
    return item, idx
  end
  return nil, nil
end

function M.left_mouse(picker)
  if M.start_resize(picker) then
    return
  end
  if resize_state.active then
    M.finish_resize()
  end

  local mouse = vim.fn.getmousepos()
  if mouse.winid ~= picker.list.win.win then
    if not Tabs.handle_left_click(mouse) then
      native_mouse("<LeftMouse>")
    end
    return
  end

  M.single_click(picker)
end

function M.single_click(picker)
  if not picker_alive(picker) then
    return
  end
  ensure_picker_ui(picker)
  local item, idx = item_at_mouse(picker)
  if not item or not idx then
    return
  end

  -- VS Code list semantics: a plain click creates a one-item selection.
  -- This is intentionally different from merely moving Snacks' current cursor:
  -- Ctrl/Alt+Click must be able to extend this selection afterwards.
  picker.list:view(idx, nil, true)
  picker.list:set_selected({ item })
  render_selection_highlights(picker)

  if not item.dir then
    Preview.open_preview(picker, item.file)
  end
end

function M.double_click(picker)
  if resize_state.active then
    M.finish_resize()
  end
  if not picker_alive(picker) then
    return
  end

  local mouse = vim.fn.getmousepos()
  if mouse.winid ~= picker.list.win.win then
    if not Tabs.handle_double_click(mouse) then
      native_mouse("<2-LeftMouse>")
    end
    return
  end
  ensure_picker_ui(picker)
  local item, idx = item_at_mouse(picker)
  if not item or not idx then
    return
  end

  picker.list:view(idx, nil, true)
  picker.list:set_selected({ item })
  render_selection_highlights(picker)

  if item.dir then
    require("snacks.explorer.actions").actions.confirm(picker, item, {})
  else
    Preview.open_pinned(picker, item.file)
  end
end

function M.toggle_click(picker, native_key)
  if resize_state.active then
    M.finish_resize()
  end
  if not picker_alive(picker) then
    return
  end

  local mouse = vim.fn.getmousepos()
  if mouse.winid ~= picker.list.win.win then
    native_mouse(native_key or "<C-LeftMouse>")
    return
  end
  ensure_picker_ui(picker)
  local item, idx = item_at_mouse(picker)
  if not item or not idx then
    return
  end
  picker.list:view(idx, nil, true)
  picker.list:select(item)
  render_selection_highlights(picker)
end

function M.show(picker, test_context)
  if resize_state.active then
    M.finish_resize()
  end
  if not picker_alive(picker) then
    return
  end
  local root = norm(picker:cwd())
  local raw_item, idx
  if test_context and not test_context.from_mouse then
    raw_item = test_context.item
  else
    raw_item, idx = item_at_mouse(picker)
  end

  -- Context menus are attached only to rendered Explorer items. Workspace
  -- operations are exposed by the explicit root item at the top of the tree.
  if not raw_item then
    context = nil
    if not test_context then
      native_mouse("<RightMouse>")
    end
    return
  end

  ensure_picker_ui(picker)
  if idx then
    picker.list:view(idx, nil, true)
  end

  local item = picker:resolve(raw_item)
  local items = {}
  if test_context and test_context.items then
    items = test_context.items
  elseif raw_item and picker.list:is_selected(raw_item) and #picker.list.selected > 0 then
    items = picker:selected({ fallback = false })
  elseif item then
    -- VS Code keeps the whole multi-selection when the context menu is opened
    -- on one of its selected rows. Right-clicking an unselected row first
    -- makes that row the single context selection.
    picker.list:set_selected({})
    items = { item }
  end

  local path = norm(item.file)
  local is_root = path == root
  local target_dir = item.dir and path or nil
  context = {
    picker = picker,
    item = item,
    items = items,
    path = path,
    root = root,
    is_root = is_root,
    target_dir = target_dir,
  }
  build_menu()
  if not (test_context and test_context.no_popup) then
    vim.cmd("popup DevTuiExplorerPopUp")
  end
end

_G.DevTuiExplorerNewFile = function()
  new_entry("file")
end
_G.DevTuiExplorerNewFolder = function()
  new_entry("folder")
end
_G.DevTuiExplorerPaste = paste_item
_G.DevTuiExplorerCopyPath = function()
  copy_path(false)
end
_G.DevTuiExplorerCopyRelativePath = function()
  copy_path(true)
end
_G.DevTuiExplorerCopy = copy_item
_G.DevTuiExplorerDelete = delete_item

local function picker_under_mouse(mouse)
  if not (_G.Snacks and Snacks.picker and Snacks.picker.get) then
    return nil
  end
  for _, picker in ipairs(Snacks.picker.get({ source = "explorer" })) do
    if picker_alive(picker) and mouse.winid == picker.list.win.win then
      return picker
    end
  end
end

function M.dispatch_mouse(key)
  local mouse = vim.fn.getmousepos()

  if key == "<LeftMouse>" and Tabs.handle_left_click(mouse) then
    return true
  end

  if key == "<2-LeftMouse>" and Tabs.handle_double_click(mouse) then
    return true
  end

  local picker = picker_under_mouse(mouse)
  if not picker then
    return false
  end

  if vim.fn.mode():sub(1, 1) == "i" then
    vim.cmd.stopinsert()
  end
  if vim.api.nvim_win_is_valid(picker.list.win.win) then
    vim.api.nvim_set_current_win(picker.list.win.win)
  end

  if key == "<LeftMouse>" then
    M.left_mouse(picker)
  elseif key == "<2-LeftMouse>" then
    M.double_click(picker)
  elseif key == "<C-LeftMouse>" then
    M.toggle_click(picker, key)
  elseif key == "<A-LeftMouse>" then
    M.toggle_click(picker, key)
  elseif key == "<RightMouse>" then
    M.show(picker)
  else
    return false
  end
  return true
end

local function install_mouse_dispatcher()
  if mouse_dispatch_installed then
    return
  end
  mouse_dispatch_installed = true

  for _, key in ipairs({ "<LeftMouse>", "<2-LeftMouse>", "<C-LeftMouse>", "<A-LeftMouse>", "<RightMouse>" }) do
    local mouse_key = key
    vim.keymap.set({ "n", "i", "x" }, mouse_key, function()
      if not M.dispatch_mouse(mouse_key) then
        native_mouse(mouse_key)
      end
    end, {
      silent = true,
      nowait = true,
      desc = "devtui cross-window mouse dispatch",
    })
  end

  _G.DevTuiExplorerMouseDispatch = M.dispatch_mouse
end

function M.attach_picker(picker)
  if not picker_alive(picker) then
    return
  end
  Regions.protect_picker(picker)
  ensure_picker_ui(picker)
  install_resize_listener()

  -- If this picker was resized by the old/native path before this module was
  -- attached, preserve the visible width in Snacks' internal layout state so a
  -- later layout refresh cannot snap it back to the preset's default width.
  if picker.layout and picker.layout.root:win_valid() then
    local current_width = vim.api.nvim_win_get_width(picker.layout.root.win)
    set_explorer_width(picker, current_width)

    -- The separator cell belongs to Snacks' root layout window, not the list
    -- float. Capture it explicitly so both the separator itself and the last
    -- two list cells start the same deterministic resize gesture.
    local root_buf = vim.api.nvim_win_get_buf(picker.layout.root.win)
    vim.keymap.set("n", "<LeftMouse>", function()
      if not M.start_resize(picker) then
        if resize_state.active then
          M.finish_resize()
        end
        vim.api.nvim_feedkeys(vim.keycode("<LeftMouse>"), "n", false)
      end
    end, {
      buffer = root_buf,
      nowait = true,
      silent = true,
      desc = "Explorer resize handle",
    })
  end
end

function M.keep_open(picker)
  if vim.fn.mode():sub(1, 1) == "i" then
    vim.cmd.stopinsert()
  end
  if picker and picker.list and picker.list.win and picker.list.win:valid() then
    picker.list.win:focus()
  end
end

function M.setup_picker(opts)
  Preview.setup()
  Regions.setup()
  install_mouse_dispatcher()
  opts.picker = opts.picker or {}
  opts.picker.sources = opts.picker.sources or {}
  local explorer = opts.picker.sources.explorer or {}

  local saved_width = load_saved_width()
  explorer.layout = vim.tbl_deep_extend("force", explorer.layout or {}, {
    layout = {
      min_width = EXPLORER_MIN_WIDTH,
      width = saved_width,
    },
  })

  local previous_on_show = explorer.on_show
  explorer.on_show = function(picker)
    if previous_on_show then
      previous_on_show(picker)
    end
    M.attach_picker(picker)
  end

  explorer.actions = explorer.actions or {}
  explorer.actions.devtui_context_menu = function(picker)
    M.show(picker)
  end
  explorer.actions.devtui_keep_open = function(picker)
    M.keep_open(picker)
  end
  explorer.actions.devtui_left_mouse = function(picker)
    M.left_mouse(picker)
  end
  explorer.actions.devtui_single_click = function(picker)
    M.single_click(picker)
  end
  explorer.actions.devtui_double_click = function(picker)
    M.double_click(picker)
  end
  explorer.actions.devtui_toggle_ctrl_click = function(picker)
    M.toggle_click(picker, "<C-LeftMouse>")
  end
  explorer.actions.devtui_toggle_alt_click = function(picker)
    M.toggle_click(picker, "<A-LeftMouse>")
  end
  explorer.win = explorer.win or {}
  explorer.win.list = explorer.win.list or {}
  explorer.win.list.keys = explorer.win.list.keys or {}
  explorer.win.list.keys["<Esc>"] = "devtui_keep_open"
  explorer.win.list.keys["q"] = "devtui_keep_open"
  explorer.win.list.keys["<LeftMouse>"] = "devtui_left_mouse"
  explorer.win.list.keys["<2-LeftMouse>"] = "devtui_double_click"
  explorer.win.list.keys["<C-LeftMouse>"] = "devtui_toggle_ctrl_click"
  explorer.win.list.keys["<A-LeftMouse>"] = "devtui_toggle_alt_click"
  explorer.win.list.keys["<RightMouse>"] = "devtui_context_menu"

  explorer.win.input = explorer.win.input or {}
  explorer.win.input.keys = explorer.win.input.keys or {}
  explorer.win.input.keys["<Esc>"] = { "devtui_keep_open", mode = { "n", "i" } }

  opts.picker.sources.explorer = explorer
end

-- Small test hooks used by the local smoke tests.
M._test = {
  increment_simple = increment_simple,
  paste_target = paste_target,
  clipboard = file_clipboard,
  context = function()
    return context
  end,
}

return M
