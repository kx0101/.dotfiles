local builtin = require('telescope.builtin')

vim.keymap.set('n', '<leader>pf', function()
  builtin.find_files({
    layout_strategy = 'horizontal',
    layout_config = {
      width = 0.9,
      height = 0.9,
      preview_width = 0.6,
    },
  })
end, { silent = true })

vim.keymap.set('n', '<C-p>', builtin.git_files, {})
vim.keymap.set('n', '<leader>ps', function()
  builtin.grep_string({ search = vim.fn.input("Grep > ") });
end)
