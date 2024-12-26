require("neodev").setup({})

local lsp = require("lsp-zero")

require('mason').setup({})
require('mason-lspconfig').setup({
    ensure_installed = {
        'eslint',
        -- 'tsserver',
        'lua_ls',
        -- 'sqls',
        -- 'jdtls',
        'rust_analyzer',
        'gopls',
    },
    handlers = {
        function(server_name)
            local capabilities = require('blink.cmp').get_lsp_capabilities()

            require('lspconfig')[server_name].setup({
                capabilities = capabilities
            })
        end
    }
})

lsp.configure('gopls', {
    cmd = { 'gopls' },
    filetypes = { 'go', 'gomod' },
    root_dir = require("lspconfig.util").root_pattern("go.mod", ".git"),
    settings = {
        gopls = {
            analyses = {
                unusedparams = true,
                shadow = true,
            },
            staticcheck = true,
        }
    },
})

lsp.configure('lua_ls', {
    Lua = {
        workspace = { checkThirdParty = false },
        telemetry = { enable = false },
    },
})

lsp.configure('rust_analyzer', {
    settings = {
        ["rust-analyzer"] = {
            cargo = {
                allFeatures = true,
            },
            check = {
                command = "clippy",
                extraArgs = { "--all", "--", "-W", "clippy::all" }
            }
        }
    }
})

-- require 'lspconfig'.omnisharp.setup {
--     defaultConfig = {
--         settings = {
--             FormattingOptions = {
--                 -- Enables support for reading code style, naming convention and analyzer
--                 -- settings from .editorconfig.
--                 EnableEditorConfigSupport = true,
--                 -- Specifies whether 'using' directives should be grouped and sorted during
--                 -- document formatting.
--                 OrganizeImports = nil,
--             },
--             MsBuild = {
--                 -- If true, MSBuild project system will only load projects for files that
--                 -- were opened in the editor. This setting is useful for big C# codebases
--                 -- and allows for faster initialization of code navigation features only
--                 -- for projects that are relevant to code that is being edited. With this
--                 -- setting enabled OmniSharp may load fewer projects and may thus display
--                 -- incomplete reference lists for symbols.
--                 LoadProjectsOnDemand = nil,
--             },
--             RoslynExtensionsOptions = {
--                 -- Enables support for roslyn analyzers, code fixes and rulesets.
--                 EnableAnalyzersSupport = nil,
--                 -- Enables support for showing unimported types and unimported extension
--                 -- methods in completion lists. When committed, the appropriate using
--                 -- directive will be added at the top of the current file. This option can
--                 -- have a negative impact on initial completion responsiveness,
--                 -- particularly for the first few completion sessions after opening a
--                 -- solution.
--                 EnableImportCompletion = nil,
--                 -- Only run analyzers against open files when 'enableRoslynAnalyzers' is
--                 -- true
--                 AnalyzeOpenDocumentsOnly = nil,
--             },
--             Sdk = {
--                 -- Specifies whether to include preview versions of the .NET SDK when
--                 -- determining which version to use for project loading.
--                 IncludePrereleases = true,
--             },
--         },
--     }
-- }

lsp.use('omnisharp', {
    enable_roslyn_analysers = true,
    enable_import_completion = true,
    organize_imports_on_format = true,
    filetypes = { 'cs', 'vb', 'csproj', 'sln', 'slnx', 'props' },
    handlers = {
        ["textDocument/definition"] = require('omnisharp_extended').handler
    },
})

local cmp = require('cmp')

cmp.setup({
    sources = {
        { name = 'nvim_lsp' },
    },
    mapping = {
        ['<C-y>'] = cmp.mapping.confirm({ select = false }),
        ['<C-e>'] = cmp.mapping.abort(),
        ['<Up>'] = cmp.mapping.select_prev_item({ behavior = 'select' }),
        ['<Down>'] = cmp.mapping.select_next_item({ behavior = 'select' }),
        ['<C-p>'] = cmp.mapping(function()
            if cmp.visible() then
                cmp.select_prev_item({ behavior = 'insert' })
            else
                cmp.complete()
            end
        end),
        ['<C-n>'] = cmp.mapping(function()
            if cmp.visible() then
                cmp.select_next_item({ behavior = 'insert' })
            else
                cmp.complete()
            end
        end),
    },
    snippet = {
        expand = function(args)
            require('luasnip').lsp_expand(args.body)
        end,
    },
})

-- vim.api.nvim_command([[
--   autocmd BufWritePre *.java lua vim.loop.spawn("mvn", { args = { "compile" }})
-- ]])

lsp.on_attach(function(_client, bufnr)
    local opts = { buffer = bufnr, remap = false }

    vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts)
    vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
    vim.keymap.set("n", "<leader>vws", vim.lsp.buf.workspace_symbol, opts)
    vim.keymap.set("n", "<leader>vd", vim.diagnostic.open_float, opts)
    vim.keymap.set("n", "[d", vim.diagnostic.goto_next, opts)
    vim.keymap.set("n", "]d", vim.diagnostic.goto_prev, opts)
    vim.keymap.set("n", "<leader>vca", vim.lsp.buf.code_action, opts)
    vim.keymap.set("n", "<leader>vrr", vim.lsp.buf.references, opts)
    vim.keymap.set("n", "<leader>vrn", vim.lsp.buf.rename, opts)
end)

lsp.setup()

vim.diagnostic.config({
    virtual_text = true,
})
