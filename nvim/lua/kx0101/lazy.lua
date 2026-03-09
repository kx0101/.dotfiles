-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
    vim.fn.system({
        "git", "clone", "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable", lazypath,
    })
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup({

    -- =============================================
    -- COLORSCHEMES
    -- =============================================
    {
        "blazkowolf/gruber-darker.nvim",
        lazy = true,
        opts = {
            bold = true,
            invert = { signs = false, tabline = false, visual = false },
            italic = { strings = false, comments = false, operators = false, folds = false },
            undercurl = true,
            underline = true,
        },
    },

    {
        "rose-pine/neovim",
        name = "rose-pine",
        lazy = false,
        priority = 1000,
        config = function()
            require("rose-pine").setup({
                variant = "main",
                dark_variant = "main",
                disable_background = false,
                dim_inactive_windows = false,
                extend_background_behind_borders = true,
                enable = { terminal = true, legacy_highlights = true, migrations = true },
                styles = { bold = true, italic = false, transparency = false },
                groups = {
                    border = "muted", link = "iris", panel = "surface",
                    error = "love", hint = "iris", info = "foam", note = "pine", todo = "rose", warn = "gold",
                    git_add = "foam", git_change = "rose", git_delete = "love", git_dirty = "rose",
                    git_ignore = "muted", git_merge = "iris", git_rename = "pine", git_stage = "iris",
                    git_text = "rose", git_untracked = "subtle",
                    h1 = "iris", h2 = "foam", h3 = "rose", h4 = "gold", h5 = "pine", h6 = "foam",
                },
            })

            vim.cmd.colorscheme("rose-pine")
            vim.o.background = "dark"
            vim.cmd [[highlight CopilotSuggestion guifg=#555555 ctermfg=8]]
        end,
    },

    -- =============================================
    -- MASON & LSP
    -- =============================================
    {
        "williamboman/mason.nvim",
        lazy = false,
        config = function()
            require("mason").setup({
                registries = {
                    "github:mason-org/mason-registry",
                    "github:Crashdummyy/mason-registry",
                },
            })
        end,
    },

    {
        "williamboman/mason-lspconfig.nvim",
        lazy = false,
        dependencies = { "williamboman/mason.nvim", "neovim/nvim-lspconfig" },
        opts = {
            ensure_installed = { "lua_ls", "gopls", "clangd" },
            automatic_enable = {
                exclude = { "volar", "vscoqtop", "jdtls" },
            },
        },
    },

    {
        "neovim/nvim-lspconfig",
        lazy = false,
        dependencies = { "saghen/blink.cmp" },
        config = function()
            local capabilities = require("blink.cmp").get_lsp_capabilities()

            vim.lsp.config("lua_ls", {
                capabilities = capabilities,
                settings = {
                    Lua = {
                        diagnostics = { globals = { "vim" } },
                        workspace = { checkThirdParty = false },
                        telemetry = { enable = false },
                    },
                },
            })

            vim.lsp.config("gopls", {
                capabilities = capabilities,
                cmd = { "gopls" },
                filetypes = { "go", "gomod" },
                root_dir = vim.fs.dirname(vim.fs.find({ "go.mod", ".git" }, { upward = true })[1]),
                settings = {
                    gopls = {
                        analyses = { unusedparams = true, shadow = true },
                        staticcheck = true,
                    },
                },
            })

            vim.lsp.config("clangd", {
                capabilities = capabilities,
                cmd = { "clangd", "--background-index" },
                filetypes = { "c", "cpp", "objc", "objcpp" },
                root_dir = vim.fs.dirname(vim.fs.find({ "compile_commands.json", "compile_flags.txt", ".git" }, { upward = true })[1]),
                init_options = {
                    clangdFileStatus = true,
                    usePlaceholders = true,
                    completeUnimported = true,
                    semanticHighlighting = true,
                },
            })

            vim.lsp.config("move_analyzer", {
                capabilities = capabilities,
                cmd = { vim.fn.expand("~") .. "/.cargo/bin/move-analyzer" },
                filetypes = { "move" },
                root_dir = vim.fs.dirname(vim.fs.find({ "Move.toml", ".git" }, { upward = true })[1]),
            })

            vim.lsp.config("rust_analyzer", {
                capabilities = capabilities,
                settings = {
                    ["rust-analyzer"] = {
                        cargo = { allFeatures = true },
                        check = {
                            command = "clippy",
                            extraArgs = { "--all", "--", "-W", "clippy::all" },
                        },
                        files = {
                            watcherExclude = { "**/target/**", "**/.git/**" },
                            excludeDirs = { "**/target/**", "**/.git/**" },
                        },
                    },
                },
            })

            vim.lsp.enable({ "lua_ls", "gopls", "clangd", "move_analyzer", "rust_analyzer" })

            -- LspAttach keybindings
            vim.api.nvim_create_autocmd("LspAttach", {
                callback = function(args)
                    local client = vim.lsp.get_client_by_id(args.data.client_id)
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

                    if client and client.server_capabilities.codeLensProvider then
                        vim.api.nvim_create_autocmd({ "BufEnter", "BufWritePost" }, {
                            buffer = args.buf,
                            callback = vim.lsp.codelens.refresh,
                        })
                    end
                end,
            })

        end,
    },

    {
        "folke/lazydev.nvim",
        ft = "lua",
        opts = {
            library = {
                { path = "${3rd}/luv/library", words = { "vim%.uv" } },
            },
        },
    },

    -- =============================================
    -- COMPLETION
    -- =============================================
    {
        "saghen/blink.cmp",
        dependencies = { "rafamadriz/friendly-snippets" },
        version = "*",
        opts = {
            keymap = { preset = "default" },
            appearance = { nerd_font_variant = "mono" },
            completion = {
                documentation = {
                    auto_show = true,
                    auto_show_delay_ms = 200,
                },
            },
            sources = {
                default = { "lazydev", "lsp", "path", "snippets", "buffer" },
                providers = {
                    lazydev = {
                        name = "LazyDev",
                        module = "lazydev.integrations.blink",
                        score_offset = 100,
                    },
                },
            },
            signature = { enabled = true },
        },
    },

    -- =============================================
    -- C# (ROSLYN)
    -- =============================================
    {
        "seblyng/roslyn.nvim",
        ft = "cs",
        dependencies = { "saghen/blink.cmp" },
        config = function()
            vim.lsp.config("roslyn", {
                capabilities = require("blink.cmp").get_lsp_capabilities(),
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

            require("roslyn").setup({
                filewatching = "off",
                broad_search = false,
                lock_target = true,
                choose_target = function(targets)
                    for _, target in ipairs(targets) do
                        if target:match("dirs%.sln$") then
                            return target
                        end
                    end
                    return targets[1]
                end,
            })
        end,
    },

    -- =============================================
    -- TREESITTER
    -- =============================================
    {
        "nvim-treesitter/nvim-treesitter",
        lazy = false,
        build = ":TSUpdate",
        config = function()
            local ts = require("nvim-treesitter")
            ts.setup({})

            local ensure_installed = { "c", "lua", "rust", "javascript", "typescript", "go", "c_sharp" }
            local installed = ts.get_installed()
            for _, lang in ipairs(ensure_installed) do
                if not vim.tbl_contains(installed, lang) then
                    ts.install({ lang })
                end
            end

            -- On Windows, symlink creation for queries can silently fail.
            -- Create junctions for any parsers missing query links.
            if vim.fn.has("win32") == 1 then
                local site_queries = vim.fs.joinpath(vim.fn.stdpath("data"), "site", "queries")
                local runtime_queries = vim.fs.joinpath(
                    vim.fn.stdpath("data"),
                    "lazy",
                    "nvim-treesitter",
                    "runtime",
                    "queries"
                )
                for _, lang in ipairs(ensure_installed) do
                    local link = vim.fs.joinpath(site_queries, lang)
                    local target = vim.fs.joinpath(runtime_queries, lang)
                    if not vim.uv.fs_stat(link) and vim.uv.fs_stat(target) then
                        vim.fn.system({ "cmd", "/c", "mklink", "/J", link, target })
                    end
                end
            end

            vim.api.nvim_create_autocmd("FileType", {
                callback = function()
                    pcall(vim.treesitter.start)
                end,
            })
        end,
    },

    -- =============================================
    -- NAVIGATION
    -- =============================================
    {
        "nvim-telescope/telescope.nvim",
        dependencies = { "nvim-lua/plenary.nvim" },
        keys = {
            { "<leader>pf", desc = "Find files" },
            { "<leader>pg", desc = "Git files" },
            { "<C-p>", desc = "Git files" },
            { "<leader>ps", desc = "Grep string" },
            { "<leader>nc", desc = "Nvim config files" },
        },
        config = function()
            local builtin = require("telescope.builtin")

            vim.keymap.set("n", "<leader>pf", function()
                builtin.find_files({
                    layout_strategy = "horizontal",
                    layout_config = { width = 0.9, height = 0.9, preview_width = 0.6 },
                    previewer = false,
                })
            end, { silent = true })

            vim.keymap.set("n", "<leader>pg", function()
                builtin.git_files({
                    layout_strategy = "horizontal",
                    layout_config = { width = 0.9, height = 0.9, preview_width = 0.6 },
                    previewer = false,
                })
            end, { silent = true })

            vim.keymap.set("n", "<C-p>", builtin.git_files, {})

            vim.keymap.set("n", "<leader>ps", function()
                builtin.grep_string({
                    search = vim.fn.input("Grep > "),
                    layout_strategy = "horizontal",
                    layout_config = { width = 0.9, height = 0.9, preview_width = 0.6 },
                })
            end)

            vim.keymap.set("n", "<leader>nc", function()
                builtin.find_files({
                    cwd = "~/.config/nvim",
                    layout_strategy = "horizontal",
                    layout_config = { width = 0.9, height = 0.9, preview_width = 0.6 },
                })
            end, { silent = true })
        end,
    },

    { "nvim-telescope/telescope-file-browser.nvim", lazy = true },

    {
        "ThePrimeagen/harpoon",
        branch = "harpoon2",
        dependencies = { "nvim-lua/plenary.nvim" },
        keys = {
            { "<C-s>", desc = "Harpoon menu" },
            { "<leader>a", desc = "Harpoon add" },
            { "<C-q>", desc = "Harpoon 1" },
            { "<C-w>", desc = "Harpoon 2" },
            { "<C-e>", desc = "Harpoon 3" },
            { "<C-f>", desc = "Harpoon 4" },
            { "<C-n>", desc = "Harpoon prev" },
            { "<C-p>", desc = "Harpoon next" },
        },
        config = function()
            local harpoon = require("harpoon")
            harpoon:setup()

            vim.keymap.set("n", "<C-s>", function() harpoon.ui:toggle_quick_menu(harpoon:list()) end)
            vim.keymap.set("n", "<leader>a", function() harpoon:list():add() end)
            vim.keymap.set("n", "<C-q>", function() harpoon:list():select(1) end)
            vim.keymap.set("n", "<C-w>", function() harpoon:list():select(2) end)
            vim.keymap.set("n", "<C-e>", function() harpoon:list():select(3) end)
            vim.keymap.set("n", "<C-f>", function() harpoon:list():select(4) end)
            vim.keymap.set("n", "<C-n>", function() harpoon:list():prev() end)
            vim.keymap.set("n", "<C-p>", function() harpoon:list():next() end)
        end,
    },

    {
        "mbbill/undotree",
        keys = {
            { "<leader>u", "<cmd>UndotreeToggle<CR>", desc = "Toggle undotree" },
        },
    },

    -- =============================================
    -- UI
    -- =============================================
    {
        "nvim-lualine/lualine.nvim",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        event = "VeryLazy",
        opts = { options = { theme = "auto" } },
    },

    {
        "nvim-tree/nvim-web-devicons",
        lazy = true,
        config = function()
            require("nvim-web-devicons").setup({})
        end,
    },

    -- =============================================
    -- GIT
    -- =============================================
    {
        "tpope/vim-fugitive",
        cmd = { "Git", "G", "Gdiffsplit", "Gvdiffsplit" },
        keys = {
            { "<leader>gs", desc = "Git status" },
            { "<leader>gd", desc = "Git diff" },
            { "<leader>gm", desc = "Git merge diff" },
            { "<leader>gb", desc = "Git blame" },
            { "<leader>gc", desc = "Git commit" },
            { "<leader>gp", desc = "Git push" },
            { "<leader>ga", desc = "Git add" },
            { "<leader>go", desc = "Diffget ours" },
            { "<leader>gt", desc = "Diffget theirs" },
            { "<leader>puo", desc = "Diffput ours" },
            { "<leader>put", desc = "Diffput theirs" },
            { "[c", desc = "Diff next" },
            { "]c", desc = "Diff prev" },
        },
        config = function()
            vim.keymap.set("n", "<leader>gs", vim.cmd.Git)
            vim.keymap.set("n", "<leader>gd", ":vertical Gdiff<CR>", { noremap = true, silent = true })
            vim.keymap.set("n", "<leader>gm", ":vertical Gdiffsplit!<CR>", { noremap = true, silent = true })
            vim.keymap.set("n", "<leader>gb", ":Git blame<CR>", { noremap = true, silent = true })
            vim.keymap.set("n", "<leader>gc", ":Git commit<CR>")
            vim.keymap.set("n", "<leader>gp", ":Git push<CR>")
            vim.keymap.set("n", "<leader>ga", ":Git add .<CR>")
            vim.keymap.set("n", "<leader>go", ":diffget //2<CR>")
            vim.keymap.set("n", "<leader>gt", ":diffget //3<CR>")
            vim.keymap.set("n", "<leader>puo", ":diffput //2<CR>")
            vim.keymap.set("n", "<leader>put", ":diffput //3<CR>")
            vim.keymap.set("n", "[c", ":diffget //2<CR>")
            vim.keymap.set("n", "]c", ":diffget //3<CR>")
        end,
    },

    {
        "lewis6991/gitsigns.nvim",
        event = "VeryLazy",
        opts = { current_line_blame = true },
    },

    {
        "sindrets/diffview.nvim",
        cmd = { "DiffviewOpen", "DiffviewFileHistory", "DiffviewToggleFiles" },
        config = function()
            require("diffview").setup({
                enhanced_diff_hl = true,
                use_icons = true,
                signs = { fold_closed = "", fold_open = "" },
                file_panel = {
                    listing_style = "tree",
                    tree_options = { flatten_dirs = true, folder_statuses = "only_folded" },
                },
            })
        end,
    },

    { "kokusenz/deltaview.nvim", cmd = { "DeltaView", "DeltaMenu" } },

    -- =============================================
    -- TERMINAL
    -- =============================================
    {
        "akinsho/toggleterm.nvim",
        version = "*",
        keys = {
            { "<leader>ft", "<cmd>ToggleTerm<CR>", desc = "Toggle terminal" },
        },
        opts = {
            direction = "float",
            float_opts = {
                border = "single",
                width = function() return math.floor(vim.o.columns * 0.8) end,
                height = function() return math.floor(vim.o.lines * 0.8) end,
            },
            shell = vim.fn.has("win32") == 1 and "cmd.exe" or vim.o.shell,
        },
    },

    -- =============================================
    -- COMMENTS
    -- =============================================
    {
        "terrortylor/nvim-comment",
        event = "VeryLazy",
        config = function()
            require("nvim_comment").setup()
        end,
    },

    -- =============================================
    -- DEBUG & TEST
    -- =============================================
    {
        "mfussenegger/nvim-dap",
        dependencies = {
            { "rcarriga/nvim-dap-ui", dependencies = { "nvim-neotest/nvim-nio" } },
        },
        keys = {
            { "<leader>b", desc = "Toggle breakpoint" },
            { "<leader>dc", desc = "Debug continue" },
            { "<leader>gtc", desc = "Run to cursor" },
            { "<leader>?", desc = "DAP eval" },
            { "<F2>", desc = "Step into" },
            { "<F3>", desc = "Step over" },
            { "<F4>", desc = "Step out" },
            { "<F5>", desc = "Step back" },
            { "<F13>", desc = "Restart" },
        },
        config = function()
            local dap = require("dap")
            local ui = require("dapui")

            ui.setup()

            local function get_target_framework(csproj_path)
                local content = vim.fn.readfile(csproj_path)
                for _, line in ipairs(content) do
                    local target = line:match("<TargetFramework>(.-)</TargetFramework>")
                    if target then return target end
                end
                return "net8.0"
            end

            local function joinpath(...)
                local sep = package.config:sub(1, 1)
                return table.concat({ ... }, sep)
            end

            local netcoredbg_cmd
            if vim.fn.has("win32") == 1 then
                netcoredbg_cmd = vim.fn.stdpath("data") .. "\\mason\\packages\\netcoredbg\\netcoredbg\\netcoredbg.exe"
            else
                netcoredbg_cmd = os.getenv("HOME") .. "/.local/netcoredbg/netcoredbg/netcoredbg"
            end

            dap.adapters.coreclr = {
                type = "executable",
                command = netcoredbg_cmd,
                args = { "--interpreter=vscode" },
            }

            dap.configurations.cs = {
                {
                    type = "coreclr",
                    name = "Launch",
                    request = "launch",
                    cwd = function() return vim.fn.getcwd() end,
                    program = function()
                        local cwd = vim.fn.getcwd()
                        local csproj_files = {}

                        for _, file in ipairs(vim.fn.readdir(cwd)) do
                            if file:match("%.csproj$") then
                                table.insert(csproj_files, file)
                            end
                        end

                        if #csproj_files == 0 then
                            error("No .csproj file found in " .. cwd)
                        end

                        local csproj_file
                        if #csproj_files > 1 then
                            csproj_file = csproj_files[vim.fn.inputlist(
                                "Select a project: ",
                                vim.tbl_map(function(f) return f end, csproj_files)
                            )]
                        else
                            csproj_file = csproj_files[1]
                        end

                        local project_name = csproj_file:gsub("%.csproj$", "")
                        local csproj_path = joinpath(cwd, csproj_file)
                        local target_framework = get_target_framework(csproj_path)

                        local build_result = vim.fn.system("dotnet build -nologo --verbosity quiet 2>&1")
                        if build_result:match("Build FAILED") then
                            error("Build failed: " .. build_result)
                        end

                        local dll_path = joinpath(cwd, "bin", "Debug", target_framework, project_name .. ".dll")
                        if vim.fn.filereadable(dll_path) == 0 then
                            local exe_path = joinpath(cwd, "bin", "Debug", target_framework, project_name .. ".exe")
                            if vim.fn.filereadable(exe_path) == 0 then
                                error("DLL/EXE not found: " .. dll_path)
                            end
                            dll_path = exe_path
                        end

                        return dll_path
                    end,
                    stopAtEntry = true,
                },
                {
                    type = "coreclr",
                    name = "Attach to Process",
                    request = "attach",
                    processId = require("dap.utils").pick_process,
                },
            }

            vim.keymap.set("n", "<leader>b", dap.toggle_breakpoint)
            vim.keymap.set("n", "<leader>gtc", dap.run_to_cursor)
            vim.keymap.set("n", "<leader>?", function() ui.eval(nil, { enter = true }) end)
            vim.keymap.set("n", "<leader>dc", dap.continue)
            vim.keymap.set("n", "<F2>", dap.step_into)
            vim.keymap.set("n", "<F3>", dap.step_over)
            vim.keymap.set("n", "<F4>", dap.step_out)
            vim.keymap.set("n", "<F5>", dap.step_back)
            vim.keymap.set("n", "<F13>", dap.restart)

            dap.listeners.before.attach.dapui_config = function() ui.open() end
            dap.listeners.before.launch.dapui_config = function() ui.open() end
            dap.listeners.before.event_terminated.dapui_config = function() ui.close() end
            dap.listeners.before.event_exited.dapui_config = function() ui.close() end
        end,
    },

    {
        "nvim-neotest/neotest",
        dependencies = {
            "nvim-neotest/nvim-nio",
            "nvim-lua/plenary.nvim",
            "nvim-treesitter/nvim-treesitter",
            "Issafalcon/neotest-dotnet",
        },
        ft = "cs",
        keys = {
            { "<leader>tr", desc = "Run nearest test" },
            { "<leader>tf", desc = "Run file tests" },
            { "<leader>td", desc = "Debug nearest test" },
            { "<leader>ts", desc = "Toggle test summary" },
            { "<leader>to", desc = "Show test output" },
            { "<leader>tp", desc = "Toggle output panel" },
        },
        config = function()
            local neotest = require("neotest")

            neotest.setup({
                adapters = {
                    require("neotest-dotnet")({
                        dap = { adapter_name = "coreclr" },
                        discovery_root = "project",
                    }),
                },
                discovery = { enabled = true },
            })

            -- Auto-discover tests when in a .NET project
            vim.defer_fn(function()
                local cwd = vim.fn.getcwd()
                local csproj = vim.fn.glob(cwd .. "/*.csproj")
                if csproj ~= "" then
                    neotest.run.run(cwd)
                end
            end, 100)

            vim.keymap.set("n", "<leader>tr", function() neotest.run.run() end, { desc = "Run nearest test" })
            vim.keymap.set("n", "<leader>tf", function() neotest.run.run(vim.fn.expand("%")) end, { desc = "Run all tests in file" })
            vim.keymap.set("n", "<leader>td", function() neotest.run.run({ strategy = "dap" }) end, { desc = "Debug nearest test" })
            vim.keymap.set("n", "<leader>ts", function() neotest.summary.toggle() end, { desc = "Toggle test summary" })
            vim.keymap.set("n", "<leader>to", function() neotest.output.open({ enter = true }) end, { desc = "Show test output" })
            vim.keymap.set("n", "<leader>tp", function() neotest.output_panel.toggle() end, { desc = "Toggle output panel" })
        end,
    },

    -- =============================================
    -- JAVA
    -- =============================================
    {
        "mfussenegger/nvim-jdtls",
        ft = "java",
        config = function()
            vim.api.nvim_create_autocmd("FileType", {
                pattern = "java",
                callback = function()
                    require("jdtls.jdtls_setup").setup()
                end,
            })

            -- Also set up for the current buffer that triggered the load
            if vim.bo.filetype == "java" then
                require("jdtls.jdtls_setup").setup()
            end

            vim.api.nvim_create_user_command("CleanJdtls", function()
                vim.fn.delete(vim.fn.expand("~/.cache/nvim/jdtls"), "rf")
                vim.fn.delete(vim.fn.expand("~/.cache/jdtls"), "rf")
                vim.fn.delete(vim.fn.expand("~/.local/share/jdtls"), "rf")
                print("Deleted cache!")
            end, {})
        end,
    },

    -- =============================================
    -- MARKDOWN
    -- =============================================
    {
        "iamcco/markdown-preview.nvim",
        build = "cd app && npm install",
        ft = "markdown",
        init = function()
            vim.g.mkdp_filetypes = { "markdown" }
        end,
    },

    -- =============================================
    -- MOVE LANGUAGE
    -- =============================================
    {
        "yanganto/move.vim",
        branch = "sui-move",
        ft = "move",
    },

    -- =============================================
    -- AI
    -- =============================================
    {
        "ThePrimeagen/99",
        event = "VeryLazy",
        config = function()
            local _99 = require("99")
            local cwd = vim.uv.cwd()
            local basename = vim.fs.basename(cwd)
            local log_dir = vim.fn.has("win32") == 1 and vim.fn.stdpath("cache") or "/tmp"

            _99.setup({
                model = "opencode/gpt-5-nano",
                logger = {
                    level = _99.DEBUG,
                    path = log_dir .. "/" .. basename .. ".99.debug",
                    print_on_error = true,
                },
                md_files = { "AGENT.md" },
            })

            vim.keymap.set("n", "<leader>9f", function() _99.fill_in_function() end)
            vim.keymap.set("v", "<leader>9v", function() _99.visual() end)
            vim.keymap.set("v", "<leader>9s", function() _99.stop_all_requests() end)
        end,
    },

}, {
    -- lazy.nvim options
    checker = { enabled = false },
    change_detection = { notify = false },
})

-- Diagnostic signs (after all plugins loaded)
local signs = {
    Error = " ",
    Warn  = " ",
    Hint  = "󰠠 ",
    Info  = " ",
}

vim.diagnostic.config({
    virtual_text = {
        source = "if_many",
        prefix = function(diagnostic)
            if diagnostic.severity == vim.diagnostic.severity.ERROR then
                return signs.Error
            elseif diagnostic.severity == vim.diagnostic.severity.WARN then
                return signs.Warn
            elseif diagnostic.severity == vim.diagnostic.severity.HINT then
                return signs.Hint
            else
                return signs.Info
            end
        end,
    },
    signs = {
        text = {
            [vim.diagnostic.severity.ERROR] = signs.Error,
            [vim.diagnostic.severity.WARN]  = signs.Warn,
            [vim.diagnostic.severity.HINT]  = signs.Hint,
            [vim.diagnostic.severity.INFO]  = signs.Info,
        },
    },
    update_in_insert = false,
    severity_sort = true,
})
