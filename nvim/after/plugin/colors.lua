function ColorMyPencils(color)
    color = color or "gruber-darker"
    vim.cmd.colorscheme(color)

    vim.api.nvim_set_hl(0, "Normal", { bg = "none" })
    vim.api.nvim_set_hl(0, "NormalFloat", { bg = "none" })
end

vim.o.background = "dark"

-- ColorMyPencils()

-- require('kanagawa').setup({
--     compile = false,
--     undercurl = true,
--     commentStyle = { italic = true },
--     keywordStyle = { italic = true }, statementStyle = { bold = true },
--     terminalColors = true,
--     theme = "wave",
--     background = {
--         dark = "wave",
--         light = "lotus"
--     },
-- })
--
-- vim.cmd("colorscheme kanagawa")
