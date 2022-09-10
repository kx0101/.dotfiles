local status, ts = pcall(require, 'nvim-treesitter.configs')
if (not status) then return end

ts.setup {
  highlight = {
    enable = true,
    disable = {},
    additional_vim_regex_highlighting = false,
  },
  indent = {
    enable = true,
    disable = {}
  },
  ensure_installed = {
    'tsx',
    'javascript',
    'lua',
    'json',
    'css'
  },
  autotag = {
    enable = true,
  },
  rainbow = {
    enable = true,
    extended_mode = true
  }
}
