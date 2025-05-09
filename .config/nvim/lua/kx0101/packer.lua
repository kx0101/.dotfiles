return require('packer').startup(function(use)
    use 'wbthomason/packer.nvim'

    use {
        'nvim-telescope/telescope.nvim', tag = '0.1.4',
        requires = { 'nvim-lua/plenary.nvim', }
    }

    use { 'nvim-telescope/telescope-file-browser.nvim' }

    -- use {
    --     "folke/tokyonight.nvim",
    --     lazy = false,
    --     priority = 1000,
    --     opts = {},
    --     config = function()
    --         vim.cmd('colorscheme tokyonight')
    --     end
    -- }

    -- use({
    --     'rebelot/kanagawa.nvim',
    --     as = 'kanagawa',
    --     config = function()
    --         vim.cmd('colorscheme kanagawa-wave')
    --     end
    -- })

    -- use {
    --     "catppuccin/nvim",
    --     as = "catppuccin",
    --     config = function()
    --         vim.cmd('colorscheme catppuccin-macchiato')
    --     end
    -- }

    -- use({
    --     'sainnhe/gruvbox-material',
    --     as = 'gruvbox-material',
    --     config = function()
    --         vim.cmd('colorscheme gruvbox-material')
    --     end
    -- })

    use({
        'rose-pine/neovim',
        as = 'rose-pine',
    })

    -- use({
    --     'sainnhe/everforest',
    --     as = 'everforest',
    --     config = function()
    --         vim.cmd('colorscheme everforest')
    --     end
    -- })

    use { "folke/neodev.nvim", opts = {} }

    use { "rcarriga/nvim-dap-ui", requires = { "mfussenegger/nvim-dap", "nvim-neotest/nvim-nio" } }

    use({
        "mfussenegger/nvim-dap",
        dependencies = {
            "rcarriga/nvim-dap-ui",
            "theHamsta/nvim-dap-virtual-text",
            "nvim-neotest/nvim-nio",
            "williamboman/mason.nvim",
        },
    })

    use('nvim-treesitter/nvim-treesitter', { run = ':TSUpdate' })
    use('nvim-treesitter/playground')
    use {
        "ThePrimeagen/harpoon",
        branch = "harpoon2",
        requires = { { "nvim-lua/plenary.nvim" } }
    }
    use('mbbill/undotree')
    use('tpope/vim-fugitive')
    use('Hoffs/omnisharp-extended-lsp.nvim')
    use('saghen/blink.cmp')

    use { 'neovim/nvim-lspconfig',
        dependencies = { 'saghen/blink.cmp' },
    }

    use {
        'VonHeikemen/lsp-zero.nvim',
        branch = 'v4.x',
        requires = {
            -- LSP Support
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
        },
    }

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
    use { 'anuvyklack/pretty-fold.nvim',
        config = function()
            require('pretty-fold').setup({})
        end
    }
end)
