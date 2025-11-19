require("rose-pine").setup({
    variant = "main",
    dark_variant = "main",
    disable_background = true,
    dim_inactive_windows = false,
    extend_background_behind_borders = true,
    styles = {
        italic = false,
        bold = true,
    }
})

vim.cmd("colorscheme rose-pine")
