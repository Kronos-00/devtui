return {
  {
    "jake-stewart/multicursor.nvim",
    branch = "1.0",
    event = "VeryLazy",
    config = function()
      local mc = require("multicursor-nvim")
      mc.setup()

      -- Allow a real caret one position past EOL, matching VS Code's caret model.
      vim.opt.virtualedit:append("onemore")

      local preview_ns = vim.api.nvim_create_namespace("devtui_box_preview")

      local box = {
        dragging = false,
        present = false,
        winid = nil,
        bufnr = nil,
        anchor_row = nil,
        anchor_vcol = nil,
        current_row = nil,
        current_vcol = nil,
        ranges = nil,
        tick = nil,
        generation = 0,
      }

      local install_box_keymaps
      local remove_box_keymaps

      local function clear_box_state()
        if box.bufnr and vim.api.nvim_buf_is_valid(box.bufnr) then
          pcall(vim.api.nvim_buf_clear_namespace, box.bufnr, preview_ns, 0, -1)
          if remove_box_keymaps then
            remove_box_keymaps(box.bufnr)
          end
        end
        box.dragging = false
        box.present = false
        box.winid = nil
        box.bufnr = nil
        box.anchor_row = nil
        box.anchor_vcol = nil
        box.current_row = nil
        box.current_vcol = nil
        box.ranges = nil
        box.tick = nil
      end

      local function valid_edit_window(winid)
        if winid <= 0 or not vim.api.nvim_win_is_valid(winid) then
          return false
        end
        local bufnr = vim.api.nvim_win_get_buf(winid)
        return vim.bo[bufnr].buftype == "" and vim.bo[bufnr].modifiable
      end

      local function mouse_vcol(mouse)
        if mouse.line <= 0 or mouse.column <= 0 then
          return nil
        end
        local ok, col = pcall(vim.fn.virtcol, { mouse.line, mouse.column })
        if not ok then
          return nil
        end
        return col + math.max(mouse.coladd or 0, 0)
      end

      -- Return a 0-based byte insertion offset, clamped to EOL.
      local function caret_offset(winid, bufnr, row, vcol)
        local line = vim.api.nvim_buf_get_lines(bufnr, row - 1, row, false)[1] or ""
        local eol_vcol = vim.fn.virtcol({ row, "$" })
        local target = math.max(1, math.min(vcol, eol_vcol))

        if target >= eol_vcol then
          return #line, line
        end

        local col1 = vim.fn.virtcol2col(winid, row, target)
        if col1 <= 0 then
          return 0, line
        end
        return col1 - 1, line
      end

      -- end_off is a 0-based exclusive byte offset. Return the 1-based byte
      -- column of the preceding UTF-8 character for inclusive Visual mode.
      local function previous_char_col1(line, end_off)
        if end_off <= 0 then
          return 1
        end
        local i = end_off
        while i > 1 do
          local b = line:byte(i)
          if not b or b < 0x80 or b >= 0xC0 then
            break
          end
          i = i - 1
        end
        return i
      end

      local function actual_vcol_for_offset(row, off)
        local line = vim.api.nvim_buf_get_lines(box.bufnr, row - 1, row, false)[1] or ""
        if off >= #line then
          return vim.fn.virtcol({ row, "$" })
        end
        return vim.fn.virtcol({ row, off + 1 })
      end

      -- Mirror VS Code's ColumnSelection.columnSelect logic:
      -- * zero-width vertical drag keeps one caret on every crossed line,
      --   clamped to EOL;
      -- * non-zero box selection skips lines that never reach the rectangle;
      -- * if every line is skipped, VS Code falls back to EOL carets on all lines.
      local function calculate_ranges()
        local first_row = math.min(box.anchor_row, box.current_row)
        local last_row = math.max(box.anchor_row, box.current_row)
        local is_ltr = box.anchor_vcol < box.current_vcol
        local is_rtl = box.anchor_vcol > box.current_vcol
        local ranges = {}

        for row = first_row, last_row do
          local anchor_off, line = caret_offset(box.winid, box.bufnr, row, box.anchor_vcol)
          local current_off = caret_offset(box.winid, box.bufnr, row, box.current_vcol)
          local visible_anchor = actual_vcol_for_offset(row, anchor_off)
          local visible_current = actual_vcol_for_offset(row, current_off)

          local include = true
          if is_ltr then
            if visible_anchor > box.current_vcol or visible_current < box.anchor_vcol then
              include = false
            end
          elseif is_rtl then
            if visible_current > box.anchor_vcol or visible_anchor < box.current_vcol then
              include = false
            end
          end

          if include then
            ranges[#ranges + 1] = {
              row = row,
              line = line,
              start_off = math.min(anchor_off, current_off),
              end_off = math.max(anchor_off, current_off),
              anchor_off = anchor_off,
              current_off = current_off,
              fallback = false,
            }
          end
        end

        if #ranges == 0 then
          for row = first_row, last_row do
            local line = vim.api.nvim_buf_get_lines(box.bufnr, row - 1, row, false)[1] or ""
            local eol = #line
            ranges[#ranges + 1] = {
              row = row,
              line = line,
              start_off = eol,
              end_off = eol,
              anchor_off = eol,
              current_off = eol,
              fallback = true,
            }
          end
        end

        return ranges
      end

      local function apply_range_to_cursor(cursor, range)
        cursor:setMode("n")
        if range.start_off < range.end_off then
          local start_pos = { range.row, range.start_off + 1 }
          local end_pos = { range.row, previous_char_col1(range.line, range.end_off) }

          if box.current_vcol >= box.anchor_vcol then
            cursor:setPos(end_pos):setVisualAnchor(start_pos):setMode("v")
          else
            cursor:setPos(start_pos):setVisualAnchor(end_pos):setMode("v")
          end
        else
          cursor:setPos({ range.row, range.current_off + 1 })
        end
      end

      local function nearest_main_index(ranges)
        local best_idx = 1
        local best_dist = math.huge
        for i, range in ipairs(ranges) do
          local dist = math.abs(range.row - box.current_row)
          if dist < best_dist then
            best_dist = dist
            best_idx = i
          end
        end
        return best_idx
      end

      local function render_preview()
        if not box.present or not box.bufnr or not vim.api.nvim_buf_is_valid(box.bufnr) then
          return
        end
        vim.api.nvim_buf_clear_namespace(box.bufnr, preview_ns, 0, -1)
        box.ranges = calculate_ranges()
        box.tick = vim.api.nvim_buf_get_changedtick(box.bufnr)

        for _, range in ipairs(box.ranges) do
          if range.start_off < range.end_off then
            vim.api.nvim_buf_set_extmark(box.bufnr, preview_ns, range.row - 1, range.start_off, {
              end_row = range.row - 1,
              end_col = range.end_off,
              hl_group = "MultiCursorVisual",
              hl_mode = "combine",
              priority = 250,
            })
          end
        end
      end

      local function finalize_box(generation)
        if not box.present or box.generation ~= generation or not valid_edit_window(box.winid) then
          return
        end

        vim.api.nvim_set_current_win(box.winid)
        box.ranges = calculate_ranges()
        box.tick = vim.api.nvim_buf_get_changedtick(box.bufnr)
        local main_idx = nearest_main_index(box.ranges)

        vim.api.nvim_buf_clear_namespace(box.bufnr, preview_ns, 0, -1)
        mc.clearCursors()

        mc.action(function(ctx)
          local main = ctx:mainCursor()
          apply_range_to_cursor(main, box.ranges[main_idx])

          for i, range in ipairs(box.ranges) do
            if i ~= main_idx then
              local cursor = ctx:addCursor()
              apply_range_to_cursor(cursor, range)
            end
          end
        end)

        if install_box_keymaps then
          install_box_keymaps()
        end
      end

      local function update_from_mouse(mouse)
        if mouse.winid ~= box.winid or mouse.line <= 0 then
          return false
        end
        local vcol = mouse_vcol(mouse)
        if not vcol then
          return false
        end
        box.current_row = mouse.line
        box.current_vcol = vcol
        render_preview()
        return true
      end

      local function middle_start()
        local mouse = vim.fn.getmousepos()
        if not valid_edit_window(mouse.winid) then
          return
        end
        local vcol = mouse_vcol(mouse)
        if not vcol then
          return
        end

        mc.clearCursors()
        vim.api.nvim_set_current_win(mouse.winid)
        if vim.fn.mode():match("^[vVsS\22\19]") then
          vim.cmd("normal! " .. vim.keycode("<Esc>"))
        end

        box.generation = box.generation + 1
        box.dragging = true
        box.present = true
        box.winid = mouse.winid
        box.bufnr = vim.api.nvim_win_get_buf(mouse.winid)
        box.anchor_row = mouse.line
        box.anchor_vcol = vcol
        box.current_row = mouse.line
        box.current_vcol = vcol
        render_preview()
      end

      local function middle_drag()
        if not box.dragging then
          return
        end
        update_from_mouse(vim.fn.getmousepos())
      end

      local function middle_release()
        if not box.dragging then
          return
        end
        update_from_mouse(vim.fn.getmousepos())
        box.dragging = false
        box.present = true
        box.tick = vim.api.nvim_buf_get_changedtick(box.bufnr)

        local generation = box.generation
        vim.schedule(function()
          finalize_box(generation)
        end)
      end

      local function box_is_current()
        return box.present
          and box.bufnr
          and vim.api.nvim_get_current_buf() == box.bufnr
          and box.tick == vim.api.nvim_buf_get_changedtick(box.bufnr)
          and box.ranges
          and #box.ranges > 0
      end

      local function selected_lines()
        local result = {}
        for _, range in ipairs(box.ranges or {}) do
          result[#result + 1] = range.line:sub(range.start_off + 1, range.end_off)
        end
        return result
      end

      local function copy_box()
        if not box_is_current() then
          return false
        end
        local lines = selected_lines()
        local text = table.concat(lines, "\n")
        vim.fn.setreg("+", text, "v")
        vim.fn.setreg('"', text, "v")

        -- VS Code copy is non-destructive: selections remain active after the
        -- clipboard action. The temporary buffer-local Ctrl-C mapping below
        -- prevents multicursor.nvim from replaying Ctrl-C into every virtual
        -- cursor; this delayed restore is the popup-menu/right-mouse fallback.
        local generation = box.generation
        local bufnr = box.bufnr
        local tick = box.tick
        vim.defer_fn(function()
          if box.present
            and box.generation == generation
            and box.bufnr == bufnr
            and vim.api.nvim_buf_is_valid(bufnr)
            and vim.api.nvim_buf_get_changedtick(bufnr) == tick
          then
            finalize_box(generation)
          end
        end, 40)

        vim.notify(("Copied %d column selection%s"):format(#lines, #lines == 1 and "" or "s"))
        return true
      end

      local box_copy_key_guard = false

      local box_arrow_keys = {
        ["<Left>"] = "<Left>",
        ["<Right>"] = "<Right>",
        ["<Up>"] = "<Up>",
        ["<Down>"] = "<Down>",
      }

      local function collapse_box_and_move(key)
        if not box_is_current() then
          return false
        end

        -- VS Code's ordinary cursorMove commands use select=false: an existing
        -- selection is collapsed first, then every cursor moves in the requested
        -- direction. Keep the multicursors, but discard the box/Visual ranges.
        clear_box_state()
        mc.action(function(ctx)
          ctx:forEachCursor(function(cursor)
            cursor:setMode("n")
            cursor:feedkeys(key, { keycodes = true })
          end)
        end)
        return true
      end

      remove_box_keymaps = function(bufnr)
        if not bufnr or not vim.api.nvim_buf_is_valid(bufnr) then
          return
        end
        for _, mode in ipairs({ "n", "x" }) do
          pcall(vim.keymap.del, mode, "<C-c>", { buffer = bufnr })
          for lhs in pairs(box_arrow_keys) do
            pcall(vim.keymap.del, mode, lhs, { buffer = bufnr })
          end
        end
      end

      install_box_keymaps = function()
        local bufnr = box.bufnr
        if not bufnr or not vim.api.nvim_buf_is_valid(bufnr) then
          return
        end

        vim.keymap.set({ "n", "x" }, "<C-c>", function()
          if not box_is_current() then
            remove_box_keymaps(bufnr)
            if _G.DevTuiCopyVscode then
              _G.DevTuiCopyVscode()
            end
            return
          end

          -- multicursor.nvim replays the typed key for every virtual cursor.
          -- Swallow those replays and execute one logical VS Code Copy action.
          if box_copy_key_guard then
            return
          end
          box_copy_key_guard = true
          copy_box()
          vim.schedule(function()
            box_copy_key_guard = false
          end)
        end, {
          buffer = bufnr,
          nowait = true,
          silent = true,
          desc = "VS Code: Copy column selection without clearing it",
        })

        for lhs, key in pairs(box_arrow_keys) do
          vim.keymap.set({ "n", "x" }, lhs, function()
            if not collapse_box_and_move(key) then
              remove_box_keymaps(bufnr)
              vim.api.nvim_feedkeys(vim.keycode(key), "n", false)
            end
          end, {
            buffer = bufnr,
            nowait = true,
            silent = true,
            desc = "VS Code: Collapse column selection and move cursors",
          })
        end
      end

      _G.DevTuiBoxSelectionCopy = copy_box
      _G.DevTuiBoxSelectionActive = function()
        return box_is_current()
      end

      local function merge_paste_chunk(dst, src)
        if not dst then
          return vim.deepcopy(src)
        end
        if #src == 0 then
          return dst
        end
        if #dst == 0 then
          return vim.deepcopy(src)
        end
        dst[#dst] = dst[#dst] .. src[1]
        for i = 2, #src do
          dst[#dst + 1] = src[i]
        end
        return dst
      end

      local function rebuild_cursors_after_paste(final_positions, main_idx)
        mc.clearCursors()
        mc.action(function(ctx)
          local main = ctx:mainCursor()
          main:setMode("n"):setPos(final_positions[main_idx])

          for i, pos in ipairs(final_positions) do
            if i ~= main_idx then
              local cursor = ctx:addCursor()
              cursor:setMode("n"):setPos(pos)
            end
          end
        end)
      end

      local cut_paste_anchor = nil

      _G.DevTuiArmCutPasteAnchor = function(spec)
        if not spec or not spec.bufnr or not vim.api.nvim_buf_is_valid(spec.bufnr) then
          cut_paste_anchor = nil
          return
        end
        spec.tick = vim.api.nvim_buf_get_changedtick(spec.bufnr)
        cut_paste_anchor = spec
      end

      local function cut_anchor_is_current()
        local a = cut_paste_anchor
        if not a then
          return false
        end
        if not vim.api.nvim_buf_is_valid(a.bufnr)
          or vim.api.nvim_get_current_buf() ~= a.bufnr
          or vim.api.nvim_buf_get_changedtick(a.bufnr) ~= a.tick
        then
          cut_paste_anchor = nil
          return false
        end
        if a.main_pos then
          local cur = vim.api.nvim_win_get_cursor(0)
          if cur[1] ~= a.main_pos[1] or cur[2] ~= a.main_pos[2] then
            cut_paste_anchor = nil
            return false
          end
        end
        return true
      end

      local function smart_cut_anchor_paste(lines)
        if not cut_anchor_is_current() then
          return false
        end

        local a = cut_paste_anchor
        cut_paste_anchor = nil
        local count = #a.positions
        if count == 0 then
          return false
        end

        local spread = #lines == count
        local ops = {}
        for i, pos in ipairs(a.positions) do
          ops[i] = {
            row0 = pos.row0,
            col0 = pos.col0,
            replacement = spread and { lines[i] } or vim.deepcopy(lines),
          }
        end

        for i = #ops, 1, -1 do
          local op = ops[i]
          if i ~= #ops then
            pcall(vim.cmd, "undojoin")
          end
          vim.api.nvim_buf_set_text(a.bufnr, op.row0, op.col0, op.row0, op.col0, op.replacement)
        end

        local final_positions = {}
        local prefix_delta = 0
        for i, op in ipairs(ops) do
          local repl = op.replacement
          local delta = #repl - 1
          local final_row0 = op.row0 + prefix_delta + delta
          local final_col0
          if #repl == 1 then
            final_col0 = op.col0 + #(repl[1] or "")
          else
            final_col0 = #(repl[#repl] or "")
          end
          final_positions[i] = { final_row0 + 1, final_col0 + 1 }
          prefix_delta = prefix_delta + delta
        end

        local main_idx = a.main_idx or 1
        if #final_positions > 1 then
          rebuild_cursors_after_paste(final_positions, main_idx)
        else
          local pos = final_positions[1]
          local line = vim.api.nvim_buf_get_lines(a.bufnr, pos[1] - 1, pos[1], false)[1] or ""
          vim.api.nvim_win_set_cursor(0, { pos[1], math.min(pos[2] - 1, #line) })
        end
        return true
      end

      local function delete_box(copy_first)
        if not box_is_current() then
          return false
        end

        local ranges = vim.deepcopy(box.ranges)
        local main_idx = nearest_main_index(ranges)
        local copied_text = nil
        if copy_first then
          copied_text = table.concat(selected_lines(), "\n")
          vim.fn.setreg("+", copied_text, "v")
          vim.fn.setreg('"', copied_text, "v")
        end

        if vim.fn.mode():match("^[vVsS\22\19]") then
          vim.cmd("normal! " .. vim.keycode("<Esc>"))
        end
        mc.clearCursors()

        for i = #ranges, 1, -1 do
          local range = ranges[i]
          if range.start_off < range.end_off then
            if i ~= #ranges then
              pcall(vim.cmd, "undojoin")
            end
            vim.api.nvim_buf_set_text(
              box.bufnr,
              range.row - 1,
              range.start_off,
              range.row - 1,
              range.end_off,
              {}
            )
          end
        end

        local positions = {}
        for i, range in ipairs(ranges) do
          positions[i] = { range.row, range.start_off + 1 }
        end

        clear_box_state()
        rebuild_cursors_after_paste(positions, main_idx)

        if copy_first and _G.DevTuiArmCutPasteAnchor then
          local anchor_positions = {}
          for i, pos in ipairs(positions) do
            anchor_positions[i] = { row0 = pos[1] - 1, col0 = pos[2] - 1 }
          end
          local main_pos = positions[main_idx]
          _G.DevTuiArmCutPasteAnchor({
            bufnr = vim.api.nvim_get_current_buf(),
            positions = anchor_positions,
            main_idx = main_idx,
            main_pos = { main_pos[1], main_pos[2] - 1 },
          })
        end

        if copied_text then
          -- multicursor keeps cursor-specific register snapshots; restore the
          -- cut payload after rebuilding cursors so both + and unnamed stay correct.
          vim.fn.setreg("+", copied_text, "v")
          vim.fn.setreg('"', copied_text, "v")
          vim.notify(("Cut %d column selection%s"):format(#ranges, #ranges == 1 and "" or "s"))
        end
        return true
      end

      _G.DevTuiBoxSelectionCut = function()
        return delete_box(true)
      end
      _G.DevTuiBoxSelectionDelete = function()
        return delete_box(false)
      end

      pcall(vim.cmd, "silent! aunmenu DevTuiBoxPopUp")
      vim.cmd([[
        anoremenu <silent> 1.10 DevTuiBoxPopUp.Copy   <Cmd>lua _G.DevTuiBoxSelectionCopy()<CR>
        anoremenu <silent> 1.20 DevTuiBoxPopUp.Cut    <Cmd>lua _G.DevTuiBoxSelectionCut()<CR>
        anoremenu <silent> 1.30 DevTuiBoxPopUp.Delete <Cmd>lua _G.DevTuiBoxSelectionDelete()<CR>
      ]])

      local function smart_box_paste(lines)
        if not box_is_current() then
          return false
        end

        local count = #box.ranges
        local spread = #lines == count
        local ops = {}
        local main_idx = 1

        for i, range in ipairs(box.ranges) do
          if range.row == box.current_row then
            main_idx = i
          end
          ops[i] = {
            idx = i,
            row0 = range.row - 1,
            start_off = range.start_off,
            end_off = range.end_off,
            replacement = spread and { lines[i] } or vim.deepcopy(lines),
          }
        end

        -- Apply bottom-up so edits on earlier lines cannot invalidate lower ranges.
        for i = #ops, 1, -1 do
          local op = ops[i]
          if i ~= #ops then
            pcall(vim.cmd, "undojoin")
          end
          vim.api.nvim_buf_set_text(
            box.bufnr,
            op.row0,
            op.start_off,
            op.row0,
            op.end_off,
            op.replacement
          )
        end

        -- VS Code keeps one caret per selection after paste. Account for line
        -- insertions above each destination when computing final positions.
        local final_positions = {}
        local prefix_delta = 0
        for i, op in ipairs(ops) do
          local repl = op.replacement
          local delta = #repl - 1
          local final_row0 = op.row0 + prefix_delta + delta
          local final_col0
          if #repl == 1 then
            final_col0 = op.start_off + #(repl[1] or "")
          else
            final_col0 = #(repl[#repl] or "")
          end
          final_positions[i] = { final_row0 + 1, final_col0 + 1 }
          prefix_delta = prefix_delta + delta
        end

        clear_box_state()
        rebuild_cursors_after_paste(final_positions, main_idx)
        return true
      end

      local original_paste = vim.paste
      local paste_stream = nil

      local paste_stream_kind = nil

      vim.paste = function(lines, phase)
        if phase == -1 then
          if smart_cut_anchor_paste(lines) then
            return true
          end
          if smart_box_paste(lines) then
            return true
          end
          return original_paste(lines, phase)
        end

        if phase == 1 then
          if cut_anchor_is_current() then
            paste_stream = vim.deepcopy(lines)
            paste_stream_kind = "cut"
            return true
          elseif box_is_current() then
            paste_stream = vim.deepcopy(lines)
            paste_stream_kind = "box"
            return true
          end
        elseif paste_stream and phase == 2 then
          paste_stream = merge_paste_chunk(paste_stream, lines)
          return true
        elseif paste_stream and phase == 3 then
          paste_stream = merge_paste_chunk(paste_stream, lines)
          local all = paste_stream
          local kind = paste_stream_kind
          paste_stream = nil
          paste_stream_kind = nil
          if kind == "cut" then
            return smart_cut_anchor_paste(all)
          elseif kind == "box" then
            return smart_box_paste(all)
          end
        end

        return original_paste(lines, phase)
      end

      vim.keymap.set({ "n", "x" }, "<MiddleMouse>", middle_start, {
        desc = "Start VS Code-style column selection",
      })
      vim.keymap.set({ "n", "x" }, "<MiddleDrag>", middle_drag, {
        desc = "Extend VS Code-style column selection",
      })
      vim.keymap.set({ "n", "x" }, "<MiddleRelease>", middle_release, {
        desc = "Finish VS Code-style column selection",
      })

      vim.keymap.set({ "n", "x" }, "<RightMouse>", function()
        if box_is_current() then
          vim.cmd("popup DevTuiBoxPopUp")
          return
        end
        vim.api.nvim_feedkeys(vim.keycode("<RightMouse>"), "n", false)
      end, { desc = "Box-selection actions / default right mouse" })

      -- Keyboard alternatives for ordinary multicursors.
      vim.keymap.set({ "n", "x" }, "<C-Up>", function()
        clear_box_state()
        mc.lineAddCursor(-1)
      end, { desc = "Add multicursor above" })
      vim.keymap.set({ "n", "x" }, "<C-Down>", function()
        clear_box_state()
        mc.lineAddCursor(1)
      end, { desc = "Add multicursor below" })

      mc.addKeymapLayer(function(layer_set)
        layer_set({ "n", "x" }, "<Esc>", function()
          clear_box_state()
          if not mc.cursorsEnabled() then
            mc.enableCursors()
          else
            mc.clearCursors()
          end
        end)
      end)

      local function set_hl()
        local hl = vim.api.nvim_set_hl
        hl(0, "MultiCursorCursor", { reverse = true })
        hl(0, "MultiCursorVisual", { link = "Visual" })
        hl(0, "MultiCursorSign", { link = "SignColumn" })
        hl(0, "MultiCursorMatchPreview", { link = "Search" })
        hl(0, "MultiCursorDisabledCursor", { reverse = true })
        hl(0, "MultiCursorDisabledVisual", { link = "Visual" })
        hl(0, "MultiCursorDisabledSign", { link = "SignColumn" })
      end
      set_hl()
      vim.api.nvim_create_autocmd("ColorScheme", {
        group = vim.api.nvim_create_augroup("devtui_multicursor_hl", { clear = true }),
        callback = set_hl,
      })
    end,
  },
}
