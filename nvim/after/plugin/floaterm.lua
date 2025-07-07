vim.o.termguicolors = true       -- Ensure 24-bit color support
vim.g.floaterm_width = 0.8       -- Set the width of the floating terminal (80% of screen width)
vim.g.floaterm_height = 0.8      -- Set the height of the floating terminal (80% of screen height)
vim.g.floaterm_wintype = 'float' -- Use floating windows
vim.g.floaterm_autoclose = 1     -- Automatically close terminal after exiting
vim.g.floaterm_position = 'center'

vim.g.floaterm_borderchars = { '+', '-', '+', '|', '+', '-', '+', '|' }

vim.g.floaterm_title = 'Terminal ($1/$2)'

vim.keymap.set('n', '<leader>ft', ':FloatermToggle<CR>', { noremap = true, silent = true, desc = 'Toggle Floaterm' })

vim.g.floaterm_shell = 'zsh'
