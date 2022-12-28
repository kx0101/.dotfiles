local lsp = require("lsp-zero")
local status, nvim_lsp = pcall(require, "lspconfig")

if (not status) then return end

lsp.preset("recommended")

lsp.ensure_installed({
    'tsserver',
    'eslint',
    'sumneko_lua',
    'rust_analyzer',
})

local cmp = require('cmp')
local cmp_select = { behavior = cmp.SelectBehavior.select }
local cmd_mappings = lsp.defaults.cmp_mappings({
    ['<C-p>'] = cmp.mapping.select_prev_item(cmp_select),
    ['<C-n>'] = cmp.mapping.select_next_item(cmp_select),
    ['<C-y>'] = cmp.mapping.confirm({ select = true }),
    ['<C-Space>'] = cmp.mapping.complete(),
})

lsp.set_preferences({
    sign_icons = {}
})

-- Common flags
local lsp_flags = {
    -- This is the default in Nvim 0.7+
    debounce_text_changes = 150,
}

local capabilities = require('cmp_nvim_lsp').default_capabilities(vim.lsp.protocol.make_client_capabilities())
capabilities.textDocument.completion.completionItem.snippetSupport = true

local on_attach = function(client, bufnr)
    local opts = { buffer = bufnr, remap = false }

    vim.keymap.set("n", "gd", function() vim.lsp.buf.definition() end, opts)
    vim.keymap.set("n", "K", function() vim.lsp.buf.hover() end, opts)
    vim.keymap.set("n", "<leader>vws", function() vim.lsp.buf.workspace_symbol() end, opts)
    vim.keymap.set("n", "<leader>vd", function() vim.diagnostic.open_float() end, opts)
    vim.keymap.set("n", "[d", function() vim.diagnostic.goto_next() end, opts)
    vim.keymap.set("n", "]d", function() vim.diagnostic.goto_prev() end, opts)
    vim.keymap.set("n", "<leader>vca", function() vim.lsp.buf.code_action() end, opts)
    vim.keymap.set("n", "<leader>vrr", function() vim.lsp.buf.references() end, opts)
    vim.keymap.set("n", "<leader>vrn", function() vim.lsp.buf.rename() end, opts)
    vim.keymap.set("i", "<C-h>", function() vim.lsp.buf.signature_help() end, opts)
end

--Lua

require('lspconfig').sumneko_lua.setup {
    on_attach = on_attach,
    settings = {
        Lua = {
            runtime = {
                -- Tell the language server which version of Lua you're using (most likely LuaJIT in the case of Neovim)
                version = 'LuaJIT',
                -- Setup your lua path
                path = runtime_path,
            },
            diagnostics = {
                -- Get the language server to recognize the `vim` global
                globals = { 'vim' },
            },
            workspace = {
                -- Make the server aware of Neovim runtime files
                library = vim.api.nvim_get_runtime_file("", true),
            },
            -- Do not send telemetry data containing a randomized but unique identifier
            telemetry = {
                enable = false,
            },
            format = {
                enable = true,
            },
        },
    },
}

-- Variants
nvim_lsp.clangd.setup({
    capabilities = capabilities,
    lsp_flags = lsp_flags,
})

-- Typescript
nvim_lsp.tsserver.setup({
    on_attach = function(client, bufnr)
        on_attach(client, bufnr)
        vim.keymap.set("n", "<leader>rr", ":lua vim.lsp.buf.rename()<cr>")
    end,
    flags = lsp_flags,
    filetypes = { "typescript", "typescriptreact", "typescript.tsx", "javascript", "javascriptreact" },
    cmd = { "typescript-language-server", "--stdio" },
    capabilities = capabilities,
})

--Json
nvim_lsp.jsonls.setup {
    on_attach = on_attach,
    init_options = {
        provideFormatter = true
    }
}

--Lua
require("lspconfig").sumneko_lua.setup({
    commands = {
        Format = {
            function()
                vim.lsp.buf.format()
            end,
        },
    },
    settings = {
        Lua = {
            runtime = {
                version = "LuaJIT",
            },
            diagnostics = {
                globals = { "vim" },
            },
            workspace = {
                library = vim.api.nvim_get_runtime_file("", true),
            },
            telemetry = {
                enable = false,
            },
        },
    },
    capabilities = capabilities,
    on_attach = function(client, bufnr)
        on_attach(client, bufnr)

        vim.keymap.set("n", "<leader>rr", vim.lsp.buf.rename, { noremap = true, buffer = bufnr })

        -- keymap("n", "<leader>fmt", stylua.format_file, { noremap = true, silent = true, buffer = bufnr })
    end,
})

-- Default lsp configurations
lsp.on_attach(function(client, bufnr)
    local opts = { buffer = bufnr, remap = false }

    local wait_ms = 1000
    local OrgImports = function()
        local params = vim.lsp.util.make_range_params()
        params.context = { only = { "source.organizeImports" } }
        local result = vim.lsp.buf_request_sync(0, "textDocument/codeAction", params, wait_ms)
        for _, res in pairs(result or {}) do
            for _, r in pairs(res.result or {}) do
                if r.edit then
                    vim.lsp.util.apply_workspace_edit(r.edit, "UTF-8")
                else
                    vim.lsp.buf.execute_command(r.command)
                end
            end
        end
    end

    local formatCorrectly = function()
        vim.lsp.buf.format({ async = true })
    end, { silent = true, }

    --vim.api.nvim_create_autocmd("BufWritePre", {
    --callback = function()
    --OrgImports()
    --formatCorrectly()
    --end,
    --})

    vim.keymap.set("n", "gd", function() vim.lsp.buf.definition() end, opts)
    vim.keymap.set("n", "K", function() vim.lsp.buf.hover() end, opts)
    vim.keymap.set("n", "<leader>vws", function() vim.lsp.buf.workspace_symbol() end, opts)
    vim.keymap.set("n", "<leader>vd", function() vim.diagnostic.open_float() end, opts)
    vim.keymap.set("n", "[d", function() vim.diagnostic.goto_next() end, opts)
    vim.keymap.set("n", "]d", function() vim.diagnostic.goto_prev() end, opts)
    vim.keymap.set("n", "<leader>vca", function() vim.lsp.buf.code_action() end, opts)
    vim.keymap.set("n", "<leader>vrr", function() vim.lsp.buf.references() end, opts)
    vim.keymap.set("n", "<leader>vrn", function() vim.lsp.buf.rename() end, opts)
    vim.keymap.set("i", "<C-h>", function() vim.lsp.buf.signature_help() end, opts)
    vim.keymap.set("n", "<leader>f", function() vim.lsp.buf.format { async = true } end, opts)
end)

lsp.setup()
