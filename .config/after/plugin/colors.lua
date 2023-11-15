function ColorMyPencils(color)
    color = 'rose-pine'
    -- color = color or "kanagawa"
    vim.cmd.colorscheme(color)

    vim.api.nvim_set_hl(0, "Normal", { bg = "none" })
    vim.api.nvim_set_hl(0, "NormalFloat", { bg = "none" })
end

ColorMyPencils()

-- require('kanagawa').setup({
--     compile = false,
--     undercurl = true,
--     commentStyle = { italic = true },
--     keywordStyle = { italic = true },
--     statementStyle = { bold = true },
--     terminalColors = true,
--     background = {
--         dark = "dragon",
--         light = "lotus"
--     },
-- })
