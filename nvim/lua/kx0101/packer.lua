return require('packer').startup(function(use)
    use {
        'wbthomason/packer.nvim',
        config = function()
            require('mason').setup({
                registries = {
                    'github:Crashdummyy/mason-registry',
                    'github:mason-org/mason-registry',
                },
            })
        end
    }

    use "/home/elijahkx/personal/csharp/devbox"

    use {
        'nvim-telescope/telescope.nvim', tag = '0.1.4',
        requires = { 'nvim-lua/plenary.nvim', }
    }

    use { 'nvim-telescope/telescope-file-browser.nvim' }

    use {
        "yanganto/move.vim",
        branch = "sui-move",
    }

    use "sindrets/diffview.nvim"

    use({
        "iamcco/markdown-preview.nvim",
        run = "cd app && npm install",
        setup = function()
            vim.g.mkdp_filetypes = {
                "markdown"
            }
        end,
        ft = { "markdown" },
    })

    -- use {
    --     "briones-gabriel/darcula-solid.nvim",
    --     requires = "rktjmp/lush.nvim",
    --     config = function()
    --         vim.cmd("colorscheme darcula-solid")
    --         vim.cmd("set termguicolors")
    --     end
    -- }

    -- use {
    --     "folke/tokyonight.nvim",
    --     lazy = false,
    --     priority = 1000,
    --     opts = {
    --         style = "moon",
    --         styles = {
    --             comments = { italic = false },
    --             keywords = { italic = false },
    --             functions = {},
    --             variables = {},
    --         },
    --     },
    --     config = function(_, opts)
    --         require("tokyonight").setup(opts)
    --         vim.cmd("colorscheme tokyonight")
    --
    --         local function disable_italics(groups)
    --             for _, group in ipairs(groups) do
    --                 local ok, hl = pcall(vim.api.nvim_get_hl, 0, { name = group, link = false })
    --                 if ok then
    --                     hl.italic = false
    --                     vim.api.nvim_set_hl(0, group, hl)
    --                 end
    --             end
    --         end
    --
    --         vim.api.nvim_create_autocmd("ColorScheme", {
    --             pattern = "tokyonight",
    --             callback = function()
    --                 disable_italics({
    --                     "@keyword",
    --                     "@keyword.function",
    --                     "@keyword.return",
    --                     "@conditional",
    --                     "@repeat",
    --                 })
    --             end,
    --         })
    --
    --         vim.cmd("doautocmd ColorScheme")
    --     end,
    -- }

    --
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
    --     'AlexvZyl/nordic.nvim',
    --     as = "nordic",
    -- })

    -- use({
    --     'sainnhe/everforest',
    --     as = 'everforest',
    --     config = function()
    --         vim.cmd('colorscheme everforest')
    --     end
    -- })

    use { "folke/neodev.nvim", opts = {} }

    use {
        "seblyng/roslyn.nvim",
        ft = "cs",
        config = function()
            require("roslyn").setup({
                on_attach = function(client, bufnr)
                    require("lsp-zero").default_on_attach(client, bufnr)

                    if client.server_capabilities.codeLensProvider then
                        vim.api.nvim_create_autocmd({ "BufEnter", "BufWritePost" }, {
                            buffer = bufnr,
                            callback = vim.lsp.codelens.refresh,
                        })
                    end
                end,
                capabilities = require("lsp-zero").get_capabilities(),
                filewatching = "off",
                cmd = {
                    "dotnet",
                    vim.fn.stdpath("data") .. "/mason/packages/roslyn/libexec/Microsoft.CodeAnalysis.LanguageServer.dll",
                    "--logLevel=Information",
                    "--stdio"
                },
                filetypes = { "cs", "vb" },
                root_dir = require("lspconfig.util").root_pattern("*.sln", "*.csproj", "*.fsproj", ".git"),
                broad_search = false,
                lock_target = true,
                settings = {
                    ["csharp|inlay_hints"] = {
                        csharp_enable_inlay_hints_for_implicit_object_creation = true,
                        csharp_enable_inlay_hints_for_implicit_variable_types = true,
                        csharp_enable_inlay_hints_for_lambda_parameter_types = true,
                        csharp_enable_inlay_hints_for_types = true,
                        dotnet_enable_inlay_hints_for_indexer_parameters = true,
                        dotnet_enable_inlay_hints_for_literal_parameters = true,
                        dotnet_enable_inlay_hints_for_object_creation_parameters = true,
                        dotnet_enable_inlay_hints_for_other_parameters = true,
                        dotnet_enable_inlay_hints_for_parameters = true,
                        dotnet_suppress_inlay_hints_for_parameters_that_differ_only_by_suffix = true,
                        dotnet_suppress_inlay_hints_for_parameters_that_match_argument_name = true,
                        dotnet_suppress_inlay_hints_for_parameters_that_match_method_intent = true,
                    },
                    ["csharp|code_lens"] = {
                        dotnet_enable_references_code_lens = true,
                        dotnet_enable_tests_code_lens = true,
                    },
                    ["csharp|completion"] = {
                        dotnet_provide_regex_completions = true,
                        dotnet_show_completion_items_from_unimported_namespaces = true,
                        dotnet_show_name_completion_suggestions = true,
                    },
                    ["csharp|background_analysis"] = {
                        background_analysis = {
                            dotnet_analyzer_diagnostics_scope = "fullSolution",
                            dotnet_compiler_diagnostics_scope = "fullSolution",
                        },
                    },
                    ["csharp|symbol_search"] = {
                        dotnet_search_reference_assemblies = true,
                    },
                    ["csharp|formatting"] = {
                        dotnet_organize_imports_on_format = true,
                    },
                },
            })
        end
    }

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
            {
                'williamboman/mason-lspconfig.nvim',
                opts = {
                    automatic_enable = {
                        exclude = {
                            'jdtls',
                        }
                    }
                }
            },

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

    use 'mfussenegger/nvim-jdtls'
end)
