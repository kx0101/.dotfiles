require("kx0101.remap")
require("kx0101.set")
require("kx0101.lazy")

vim.api.nvim_create_autocmd({ "BufWritePre" }, {
    pattern = "*.cs",
    callback = function()
        vim.bo.bomb = true
    end,
})
