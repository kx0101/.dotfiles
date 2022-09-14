require('base')
require('highlights')
require('maps')
require('plugins')

vim.cmd('nnoremap <C-q> :NERDTreeFocus<CR>')
vim.cmd('nnoremap <C-e> :NERDTreeToggle<CR>')
vim.cmd('nnoremap <C-p> :Telescope find_files<CR>')
vim.cmd('nnoremap <C-y> :Telescope live_grep<CR>')
vim.cmd([[nmap <C-z> <Nop>]])
vim.cmd [[colorscheme tokyonight]]
vim.cmd('nmap <C-F>f :CtrlSF ')

local has = function(x)
  return vim.fn.has(x) == 1
end

local is_mac = has "macunix"
local is_win = has "win32"

if is_mac then
  require('macos')
end
if is_win then
  require('windows')
end
