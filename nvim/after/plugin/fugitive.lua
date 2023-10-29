vim.keymap.set('n', '<leader>gs', vim.cmd.Git);
vim.keymap.set('n', '<leader>gd', [[:vertical Gdiff<CR>]], { noremap = true, silent = true })
vim.keymap.set('n', '<leader>gb', [[:Git blame<CR>]], { noremap = true, silent = true })
vim.keymap.set('n', '<leader>gc', [[:Git commit<CR>]])
vim.keymap.set('n', '<leader>gp', [[:Git push<CR>]])
vim.keymap.set('n', '<leader>ga', [[:Git add .<CR>]])
