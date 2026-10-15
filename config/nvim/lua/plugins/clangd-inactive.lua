local ns = vim.api.nvim_create_namespace("devtui_clangd_inactive")

local function inactive_handler(_, result, ctx)
  local uri = result and ((result.textDocument and result.textDocument.uri) or result.uri)
  if not uri then
    return
  end

  local bufnr = vim.uri_to_bufnr(uri)
  if not vim.api.nvim_buf_is_loaded(bufnr) then
    return
  end

  vim.api.nvim_buf_clear_namespace(bufnr, ns, 0, -1)

  local client = vim.lsp.get_client_by_id(ctx.client_id)
  local encoding = (client and client.offset_encoding) or "utf-16"

  for _, range in ipairs(result.regions or {}) do
    local start_col = vim.lsp.util._get_line_byte_from_position(bufnr, range.start, encoding)
    local end_col = vim.lsp.util._get_line_byte_from_position(bufnr, range["end"], encoding)

    pcall(vim.api.nvim_buf_set_extmark, bufnr, ns, range.start.line, start_col, {
      end_row = range["end"].line,
      end_col = end_col,
      hl_group = "DevTuiInactiveCode",
      hl_eol = true,
      hl_mode = "replace",
      priority = 220,
    })
  end
end

local function set_inactive_hl()
  vim.api.nvim_set_hl(0, "DevTuiInactiveCode", { link = "Comment" })
end

set_inactive_hl()
vim.api.nvim_create_autocmd("ColorScheme", {
  group = vim.api.nvim_create_augroup("devtui_inactive_hl", { clear = true }),
  callback = set_inactive_hl,
})

return {
  {
    "neovim/nvim-lspconfig",
    opts = function(_, opts)
      opts.servers = opts.servers or {}
      opts.servers.clangd = opts.servers.clangd or {}

      opts.servers.clangd.capabilities = vim.tbl_deep_extend(
        "force",
        opts.servers.clangd.capabilities or {},
        {
          textDocument = {
            inactiveRegionsCapabilities = {
              inactiveRegions = true,
            },
          },
        }
      )

      opts.servers.clangd.handlers = opts.servers.clangd.handlers or {}
      opts.servers.clangd.handlers["textDocument/inactiveRegions"] = inactive_handler
    end,
  },
}
