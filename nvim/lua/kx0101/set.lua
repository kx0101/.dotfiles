vim.opt.termguicolors = true

-- vim.opt.guicursor = "n-v-c:block-Cursor,i:ver25-CursorInsert"
vim.opt.guicursor = "n-v-c:block-Cursor,i:block-CursorInsert"
vim.api.nvim_create_autocmd("ColorScheme", {
    callback = function()
        vim.api.nvim_set_hl(0, "Cursor", { fg = "black", bg = "white" })
        vim.api.nvim_set_hl(0, "CursorInsert", { fg = "black", bg = "white" })
    end,
})

vim.opt.nu = true
vim.opt.relativenumber = true

vim.opt.tabstop = 4
vim.opt.softtabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true

vim.opt.smartindent = true

vim.opt.wrap = false

vim.opt.swapfile = false
vim.opt.backup = false
vim.opt.undodir = os.getenv("HOME") .. "/.vim/undodir"
vim.opt.undofile = true

vim.opt.hlsearch = false
vim.opt.incsearch = true

vim.opt.scrolloff = 8
vim.opt.signcolumn = "yes"
vim.opt.smartcase = true
vim.opt.ignorecase = true

vim.opt.updatetime = 50

vim.opt.colorcolumn = "80"
vim.opt.fileformat = "dos" -- for CRLF

vim.o.foldcolumn = '1'
vim.o.foldlevel = 99
vim.o.foldlevelstart = 99
vim.o.foldenable = true

vim.o.cursorline = true

vim.g.netrw_banner = 0
