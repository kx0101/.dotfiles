-- This file can be loaded by calling `lua require('plugins')` from your init.vim

-- Only required if you have packer configured as `opt`
vim.cmd [[packadd packer.nvim]]

return require('packer').startup(function(use)
  -- Packer can manage itself
  use 'wbthomason/packer.nvim'

  use {
    'nvim-telescope/telescope.nvim', tag = '0.1.0',
    -- or                            , branch = '0.1.x',
    requires = { { 'nvim-lua/plenary.nvim' } }
  }

  use({
    'EdenEast/nightfox.nvim',
    as = 'nightfox',
    config = function()
      vim.cmd('colorscheme nightfox')
    end
  })

  use('nvim-treesitter/nvim-treesitter', { run = ':TSUpdate' })

  use('nvim-treesitter/playground')
  use('theprimeagen/harpoon')
  use('mbbill/undotree')

  use {
    'VonHeikemen/lsp-zero.nvim',
    requires = {
      -- LSP Support
      { 'neovim/nvim-lspconfig' },
      { 'williamboman/mason.nvim' },
      { 'williamboman/mason-lspconfig.nvim' },

      -- Autocompletion
      { 'hrsh7th/nvim-cmp' },
      { 'hrsh7th/cmp-buffer' },
      { 'hrsh7th/cmp-path' },
      { 'saadparwaiz1/cmp_luasnip' },
      { 'hrsh7th/cmp-nvim-lsp' },
      { 'hrsh7th/cmp-nvim-lua' },

      -- Snippets
      { 'L3MON4D3/LuaSnip' },
      { 'rafamadriz/friendly-snippets' },
    }
  }

  use { "github/copilot.vim" }

  use {
    "windwp/nvim-autopairs",
    config = function() require("nvim-autopairs").setup {} end
  }

  use { 'windwp/nvim-ts-autotag' }
  use("jose-elias-alvarez/null-ls.nvim")
  use { 'voldikss/vim-floaterm' }

  use { 'nvim-tree/nvim-web-devicons',
    config = function() require("nvim-web-devicons").setup {} end
  }

  use { 'nvim-lualine/lualine.nvim' }

  use {
    'terrortylor/nvim-comment',
    config = function()
      require('nvim_comment').setup()
    end
  }

  use {
    'lewis6991/gitsigns.nvim',
    config = function()
      require('gitsigns').setup({ current_line_blame = true })
    end
  }

  use 'simrat39/rust-tools.nvim'

end)
