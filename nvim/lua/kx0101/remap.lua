vim.g.mapleader = " "
vim.keymap.set("n", "<leader>pv", vim.cmd.Ex)
vim.keymap.set("v", "J", ":m '>+1<CR>gv=gv")
vim.keymap.set("v", "K", ":m '<-2<CR>gv=gv")

vim.keymap.set("n", "J", "mzJ`z")
vim.keymap.set("n", "<C-d>", "<C-d>zz")
vim.keymap.set("n", "<C-u>", "<C-u>zz")
vim.keymap.set("n", "n", "nzzzv")
vim.keymap.set("n", "N", "Nzzzv")

vim.keymap.set("x", "<leader>p", "\"_dP")

vim.keymap.set("n", "<leader>y", "\"+y")
vim.keymap.set("v", "<leader>y", "\"+y")
vim.keymap.set("n", "<leader>Y", "\"+Y")

vim.keymap.set("n", "<leader>d", "\"_d")
vim.keymap.set("v", "<leader>d", "\"_d")

vim.keymap.set("n", "Q", "<nop>")

vim.keymap.set("n", "<C-k>", "<cmd>cnext<CR>zz")
vim.keymap.set("n", "<C-j>", "<cmd>cprev<CR>zz")
vim.keymap.set("n", "<leader>k", "<cmd>lnext<CR>zz")
vim.keymap.set("n", "<leader>j", "<cmd>lprev<CR>zz")

vim.keymap.set("n", "<leader>s", ":%s/\\<<C-r><C-w>\\>/<C-r><C-w>/gI<Left><Left><Left>")
vim.keymap.set("n", "<leader>x", "<cmd>!chmod +x %<CR>", { silent = true })

vim.keymap.set("n", "<leader>fmt", function() vim.lsp.buf.format({ async = true }) end, { noremap = true, silent = true })

vim.keymap.set("n", "<leader>nc", function()
    vim.api.nvim_put({ "if err != nil {", "\treturn err", "}" }, "l", true, true)
end)

vim.keymap.set("n", "<leader><leader>", function()
    vim.cmd("so")
end)

vim.keymap.set("n", "<leader>pw", "<cmd>vsplit<CR>")
vim.keymap.set("n", "<leader>pe", "<cmd>split<CR>")

vim.api.nvim_del_keymap('n', '<C-w>d')
vim.api.nvim_del_keymap('n', '<C-w><C-D>')

vim.keymap.set("n", "<C-h>", "<C-w>h")
vim.keymap.set("n", "<C-j>", "<C-w>j")
vim.keymap.set("n", "<C-k>", "<C-w>k")
vim.keymap.set("n", "<C-l>", "<C-w>l")

vim.keymap.set("n", "<leader>dvm", ":DiffviewOpen origin/develop..HEAD<CR>")
vim.keymap.set("n", "<leader>dvh", ":DiffviewFileHistory<CR>")
vim.keymap.set("n", "<leader>dvt", ":DiffviewToggleFiles<CR>")
vim.keymap.set("n", "<leader>dvc", ":DiffviewFileHistory %<CR>")

vim.opt.clipboard = "unnamedplus"
vim.opt.shell = "/bin/bash"

-- vim.g.clipboard = {
--     name = "xclip-xfce4-clipman",
--     copy = {
--         ['+'] = "xclip -selection clipboard",
--         ['*'] = "xclip -selection clipboard",
--     },
--     paste = {
--         ['+'] = "xclip -selection clipboard -o",
--         ['*'] = "xclip -selection clipboard -o",
--     },
--     cache_enabled = 1,
-- }

-- vim.g.clipboard = {
--   name = "win32yank-wsl",
--   copy = {
--     ['+'] = 'clip.exe',
--     ['*'] = 'clip.exe',
--   },
--   paste = {
--     ['+'] = 'powershell.exe -c [Console]::Out.Write($(Get-Clipboard -Raw).tostring().replace("`r", ""))',
--     ['*'] = 'powershell.exe -c [Console]::Out.Write($(Get-Clipboard -Raw).tostring().replace("`r", ""))',
--   },
--   cache_enabled = 0,
-- }
