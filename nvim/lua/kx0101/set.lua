vim.opt.termguicolors = true

if vim.fn.has("win32") == 1 then
    vim.opt.shell = "cmd.exe"
    vim.opt.shellcmdflag = "/s /c"
    vim.opt.shellquote = ""
    vim.opt.shellxquote = "("
else
    vim.opt.shell = "/usr/bin/zsh"
    vim.opt.shellcmdflag = "-c"
    vim.opt.shellquote = ""
    vim.opt.shellxquote = ""
end

vim.opt.wildignore:append("*/target/*")
vim.opt.backupskip:append("*/target/*")
vim.opt.undodir = vim.fn.stdpath("state") .. "/undodir"

-- vim.opt.guicursor = "n-v-c:block-Cursor,i:ver25-CursorInsert"
vim.opt.guicursor = "n-v-c:block-Cursor,i:block-CursorInsert"
vim.api.nvim_create_autocmd("ColorScheme", {
    callback = function()
        vim.api.nvim_set_hl(0, "Cursor", { fg = "black", bg = "white" })
        vim.api.nvim_set_hl(0, "CursorInsert", { fg = "black", bg = "white" })
    end,
})

local last_term_cmd = "cargo build"


vim.keymap.set("n", "<leader>bt", function()
    local cmd = vim.fn.input("Terminal command: ", last_term_cmd)
    if cmd == "" then
        return
    end

    last_term_cmd = cmd

    vim.cmd("botright 10split | terminal")
    local job_id = vim.b.terminal_job_id
    vim.fn.chansend(job_id, cmd .. "\n")
    vim.cmd("startinsert")
end, { silent = true })

vim.keymap.set("n", "<leader>bb", function()
    vim.cmd("botright 10split | terminal")
    vim.fn.chansend(vim.b.terminal_job_id, last_term_cmd .. "\n")
    vim.cmd("startinsert")
end, { silent = true })

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
-- vim.opt.undodir = os.getenv("HOME") .. "/.vim/undodir"
vim.opt.undofile = true

vim.opt.hlsearch = false
vim.opt.incsearch = true

vim.opt.scrolloff = 8
vim.opt.signcolumn = "yes"
vim.opt.smartcase = true
vim.opt.ignorecase = true

vim.opt.updatetime = 200

vim.opt.colorcolumn = "80"
if vim.fn.has("win32") == 1 then
    vim.opt.fileformat = "dos"
end

vim.o.foldcolumn = '0'
vim.o.foldlevel = 99
vim.o.foldlevelstart = 99
vim.o.foldenable = true

vim.o.cursorline = true

-- Disable expensive features for large files
vim.api.nvim_create_autocmd("BufRead", {
    callback = function()
        local size = vim.fn.getfsize(vim.fn.expand("<afile>"))
        if size > 1000000 then
            vim.opt_local.cursorline = false
            vim.opt_local.syntax = "off"
            vim.opt_local.foldmethod = "manual"
        end
    end,
})

vim.g.netrw_banner = 0
