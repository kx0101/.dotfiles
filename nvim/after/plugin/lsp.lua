-- neodev for Lua dev setup
require("neodev").setup({
    library = { plugins = { "nvim-dap-ui" }, types = true },
})

-- mason setup
require('mason').setup({
    registries = {
        "github:mason-org/mason-registry",
        "github:Crashdummyy/mason-registry",
    },
})

-- mason-lspconfig setup
require('mason-lspconfig').setup({
    ensure_installed = {
        'eslint',
        'lua_ls',
        'gopls',
        'clangd',
    }
})

-- Lua

vim.lsp.config('lua_ls', {
    settings = {
        Lua = {
            diagnostics = {
                globals = { 'vim' },
            },
            workspace = {
                checkThirdParty = false,
            },
            telemetry = { enable = false },
        },
    },
})

-- Go
vim.lsp.config("gopls", {
    cmd = { "gopls" },
    filetypes = { "go", "gomod" },
    root_dir = vim.fs.dirname(vim.fs.find({ "go.mod", ".git" }, { upward = true })[1]),
    settings = {
        gopls = {
            analyses = {
                unusedparams = true,
                shadow = true,
            },
            staticcheck = true,
        },
    },
})

-- C/C++
vim.lsp.config("clangd", {
    cmd = { "clangd", "--background-index" },
    filetypes = { "c", "cpp", "objc", "objcpp" },
    root_dir = vim.fs.dirname(vim.fs.find({ "compile_commands.json", "compile_flags.txt", ".git" }, { upward = true })
        [1]),
    init_options = {
        clangdFileStatus = true,
        usePlaceholders = true,
        completeUnimported = true,
        semanticHighlighting = true,
    },
})

-- Move
vim.lsp.config("move_analyzer", {
    cmd = { os.getenv("HOME") .. "/.cargo/bin/move-analyzer" },
    filetypes = { "move" },
    root_dir = vim.fs.dirname(vim.fs.find({ "Move.toml", ".git" }, { upward = true })[1]),
})

-- Rust
vim.lsp.config("rust_analyzer", {
    settings = {
        ["rust-analyzer"] = {
            cargo = { allFeatures = true },
            check = {
                command = "clippy",
                extraArgs = { "--all", "--", "-W", "clippy::all" },
            },
        },
    },
})

-- enable all defined servers
vim.lsp.enable({ "lua_ls", "gopls", "clangd", "move_analyzer", "rust_analyzer" })

-- === CMP SETUP ===
local cmp = require("cmp")

cmp.setup({
    sources = {
        { name = "nvim_lsp" },
    },
    mapping = {
        ["<C-y>"] = cmp.mapping.confirm({ select = false }),
        ["<C-e>"] = cmp.mapping.abort(),
        ["<Up>"] = cmp.mapping.select_prev_item({ behavior = "select" }),
        ["<Down>"] = cmp.mapping.select_next_item({ behavior = "select" }),
        ["<C-p>"] = cmp.mapping(function()
            if cmp.visible() then
                cmp.select_prev_item({ behavior = "insert" })
            else
                cmp.complete()
            end
        end),
        ["<C-n>"] = cmp.mapping(function()
            if cmp.visible() then
                cmp.select_next_item({ behavior = "insert" })
            else
                cmp.complete()
            end
        end),
    },
    snippet = {
        expand = function(args)
            require("luasnip").lsp_expand(args.body)
        end,
    },
})

-- === ON ATTACH ===
vim.api.nvim_create_autocmd("LspAttach", {
    callback = function(args)
        local opts = { buffer = args.buf, silent = true, noremap = true }

        vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts)
        vim.keymap.set("n", "gD", vim.lsp.buf.declaration, opts)
        vim.keymap.set("n", "gi", vim.lsp.buf.implementation, opts)
        vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
        vim.keymap.set("n", "<leader>vws", vim.lsp.buf.workspace_symbol, opts)
        vim.keymap.set("n", "<leader>vd", vim.diagnostic.open_float, opts)
        vim.keymap.set("n", "[d", vim.diagnostic.goto_prev, opts)
        vim.keymap.set("n", "]d", vim.diagnostic.goto_next, opts)
        vim.keymap.set("n", "<leader>vca", vim.lsp.buf.code_action, opts)
        vim.keymap.set("n", "<leader>vrr", vim.lsp.buf.references, opts)
        vim.keymap.set("n", "<leader>vrn", vim.lsp.buf.rename, opts)
    end,
})

-- diagnostics config
vim.diagnostic.config({
    virtual_text = true,
    signs = true,
    update_in_insert = false,
    severity_sort = true,
})

-- java
vim.api.nvim_create_autocmd("FileType", {
    pattern = "java",
    callback = function()
        require("jdtls.jdtls_setup").setup()
    end,
})

vim.api.nvim_create_user_command("CleanJdtls", function()
    vim.fn.delete(vim.fn.expand("~/.cache/nvim/jdtls"), "rf")
    vim.fn.delete(vim.fn.expand("~/.cache/jdtls"), "rf")
    vim.fn.delete(vim.fn.expand("~/.local/share/jdtls"), "rf")
    print("Deleted cache!")
end, {})
