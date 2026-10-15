local function lsp_picker(name, fallback)
  return function()
    if _G.Snacks and Snacks.picker and Snacks.picker[name] then
      Snacks.picker[name]()
    else
      fallback()
    end
  end
end

local function symbol_menu(use_mouse)
  if use_mouse then
    local pos = vim.fn.getmousepos()
    if pos.winid > 0 and vim.api.nvim_win_is_valid(pos.winid) then
      local buf = vim.api.nvim_win_get_buf(pos.winid)
      if vim.bo[buf].buftype == "" then
        vim.api.nvim_set_current_win(pos.winid)
        if pos.line > 0 then
          pcall(vim.api.nvim_win_set_cursor, pos.winid, { pos.line, math.max(pos.column - 1, 0) })
        end
      end
    end
  end

  if #vim.lsp.get_clients({ bufnr = 0 }) == 0 then
    vim.notify("No LSP attached to this buffer", vim.log.levels.WARN)
    return
  end

  local items = {
    { "Go to Definition", lsp_picker("lsp_definitions", vim.lsp.buf.definition) },
    { "Go to Declaration", lsp_picker("lsp_declarations", vim.lsp.buf.declaration) },
    { "Find References", lsp_picker("lsp_references", vim.lsp.buf.references) },
    { "Go to Implementation", lsp_picker("lsp_implementations", vim.lsp.buf.implementation) },
    { "Type Definition", lsp_picker("lsp_type_definitions", vim.lsp.buf.type_definition) },
    { "Hover", vim.lsp.buf.hover },
    { "Rename Symbol", vim.lsp.buf.rename },
    { "Code Action", vim.lsp.buf.code_action },
  }

  vim.ui.select(items, {
    prompt = "Symbol action",
    format_item = function(item)
      return item[1]
    end,
  }, function(choice)
    if choice then
      choice[2]()
    end
  end)
end

return {
  {
    "neovim/nvim-lspconfig",
    init = function()
      vim.opt.mouse = "a"
      -- Keep the editor tab strip present from startup, like VS Code. This
      -- also prevents Explorer rows shifting between the first and second
      -- click of a double-click when bufferline becomes visible.
      vim.opt.showtabline = 2
      vim.api.nvim_create_autocmd("LspAttach", {
        group = vim.api.nvim_create_augroup("devtui_symbol_menu", { clear = true }),
        callback = function(args)
          vim.keymap.set({ "n", "x" }, "<RightMouse>", function()
            if _G.DevTuiExplorerMouseDispatch and _G.DevTuiExplorerMouseDispatch("<RightMouse>") then
              return
            end
            if _G.DevTuiBoxSelectionActive and _G.DevTuiBoxSelectionActive() then
              vim.cmd("popup DevTuiBoxPopUp")
              return
            end
            if vim.fn.mode():match("^[vV\22]") then
              vim.api.nvim_feedkeys(vim.keycode("<RightMouse>"), "n", false)
              return
            end
            symbol_menu(true)
          end, { buffer = args.buf, desc = "Box-selection menu / symbol actions" })
          vim.keymap.set("n", "<leader>cx", function() symbol_menu(false) end, { buffer = args.buf, desc = "Symbol actions menu" })
        end,
      })
    end,
  },
  {
    "akinsho/bufferline.nvim",
    optional = true,
    opts = function(_, opts)
      opts.options = opts.options or {}
      -- VS Code keeps the editor tab strip stable while preview editors are
      -- replaced/pinned. Avoid a one-row layout jump when the second buffer
      -- appears, which can otherwise break the second click of a double-click.
      opts.options.always_show_bufferline = true

      local previous_name_formatter = opts.options.name_formatter
      opts.options.name_formatter = function(info)
        local name = previous_name_formatter and previous_name_formatter(info) or info.name
        if info.bufnr and vim.api.nvim_buf_is_valid(info.bufnr) and vim.bo[info.bufnr].modified then
          name = name .. " ●"
        end
        return name
      end

      -- bufferline normally replaces the close button with modified_icon.
      -- Keep a close glyph in that position and move the dirty dot into the
      -- filename; devtui_tabs makes this suffix clickable for modified buffers.
      opts.options.modified_icon = opts.options.buffer_close_icon or ""

      opts.options.close_command = function(buf)
        require("config.devtui_tabs").close_buffer(buf)
      end
    end,
  },
  {
    "folke/snacks.nvim",
    opts = function(_, opts)
      opts.picker = opts.picker or {}
      opts.picker.sources = opts.picker.sources or {}
      opts.picker.sources.explorer = vim.tbl_deep_extend("force", opts.picker.sources.explorer or {}, {
        hidden = true,
        ignored = true,
      })
      opts.picker.sources.files = vim.tbl_deep_extend("force", opts.picker.sources.files or {}, {
        hidden = true,
        ignored = true,
      })

      -- VS Code-style Explorer interactions. The implementation resolves the
      -- exact item/folder/root mouse target before constructing context actions,
      -- so commands never depend on a stale keyboard cursor position.
      require("config.devtui_explorer_context").setup_picker(opts)

      -- nvim-scrollview already controls the viewport during drag. Disable
      -- Snacks smooth scrolling so mouse release does not replay the move.
      opts.scroll = vim.tbl_deep_extend("force", opts.scroll or {}, {
        enabled = false,
      })
    end,
  },
}
