vim.keymap.set('n', '<leader>gs', vim.cmd.Git);
vim.keymap.set('n', '<leader>gd', [[:vertical Gdiff<CR>]], { noremap = true, silent = true })
vim.keymap.set('n', '<leader>gm', [[:vertical Gdiffsplit!<CR>]], { noremap = true, silent = true })
vim.keymap.set('n', '<leader>gb', [[:Git blame<CR>]], { noremap = true, silent = true })
vim.keymap.set('n', '<leader>gc', [[:Git commit<CR>]])

vim.api.nvim_set_keymap('n', '<leader>gp',
    [[:lua vim.cmd("Git push origin " .. vim.fn.systemlist("git rev-parse --abbrev-ref HEAD")[1])<CR>]],
    { noremap = true, silent = true })

vim.keymap.set('n', '<leader>ga', [[:Git add .<CR>]])

-- Get changes from "ours" into the working file
vim.keymap.set('n', '<leader>go', ':diffget //2<CR>')
-- Get changes from "theirs" into the working file
vim.keymap.set('n', '<leader>gt', ':diffget //3<CR>')
-- Put changes into "ours" (current branch)
vim.keymap.set('n', '<leader>puo', ':diffput //2<CR>')
-- Put changes into "theirs" (incoming branch)
vim.keymap.set('n', '<leader>put', ':diffput //3<CR>')

vim.keymap.set('n', '[c', ':diffget //2<CR>') -- Jump to the next conflict marker
vim.keymap.set('n', ']c', ':diffget //3<CR>') -- Jump to the previous conflict marker
