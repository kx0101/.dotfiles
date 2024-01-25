local builtin = require('telescope.builtin')

vim.keymap.set('n', '<leader>pf', function()
    local is_git_repo = vim.fn.system('git rev-parse --is-inside-work-tree 2>/dev/null') == 'true\n'
    if is_git_repo then
        builtin.git_files({
            layout_strategy = 'vertical',
            layout_config = {
                width = 0.9,
                height = 0.8,
            },
            previewer = false,
        })
    else
        builtin.find_files({
            layout_strategy = 'vertical',
            layout_config = {
                width = 0.9,
                height = 0.8,
            },
            previewer = false,
        })
    end
end, { silent = true })

-- vim.keymap.set('n', '<C-p>', builtin.git_files, {})
vim.keymap.set('n', '<leader>pg', function()
    builtin.grep_string({
        layout_strategy = 'horizontal',
        layout_config = {
            width = 0.9,
            height = 0.9,
            preview_width = 0.6,
        }
    });
end)

vim.keymap.set('n', '<leader>ps', function()
    builtin.grep_string({
        search = vim.fn.input("Grep > "),
        layout_strategy = 'horizontal',
        layout_config = {
            width = 0.9,
            height = 0.9,
            preview_width = 0.6,
        }
    });
end)
