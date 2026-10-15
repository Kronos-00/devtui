return {
  {
    "dstein64/nvim-scrollview",
    event = { "BufReadPost", "BufNewFile" },
    opts = {
      current_only = false,
      excluded_filetypes = {
        "snacks_picker_input",
        "snacks_picker_list",
        "snacks_layout_box",
        "mason",
        "mason_backdrop",
        "lazy",
        "help",
        "qf",
        "Trouble",
        "noice",
        "notify",
        "lazygit",
        "dashboard",
      },
      signs_on_startup = { "diagnostics", "search", "marks" },
    },
  },
}
