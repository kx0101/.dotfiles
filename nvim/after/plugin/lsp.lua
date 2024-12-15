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
            require('lspconfig')[server_name].setup({})
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
        ['<CR>'] = cmp.mapping.confirm({ select = false }),
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

    -- if client.name == "eslint" then
    --   vim.cmd.LspStop('eslint')
    --   return
    -- end

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
