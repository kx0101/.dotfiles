local neotest = require("neotest")

neotest.setup({
    adapters = {
        require("neotest-dotnet")({
            dap = {
                adapter_name = "coreclr",
            },
            discovery_root = "project",
        }),
    },
    discovery = {
        enabled = true,
    },
})

-- Auto-discover tests when opening a C# file
vim.api.nvim_create_autocmd("BufEnter", {
    pattern = "*.cs",
    callback = function()
        local cwd = vim.fn.getcwd()
        local csproj = vim.fn.glob(cwd .. "/*.csproj")
        if csproj ~= "" then
            neotest.run.run(cwd)
        end
    end,
    once = true,
})

vim.keymap.set("n", "<leader>tr", function() neotest.run.run() end, { desc = "Run nearest test" })
vim.keymap.set("n", "<leader>tf", function() neotest.run.run(vim.fn.expand("%")) end, { desc = "Run all tests in file" })
vim.keymap.set("n", "<leader>td", function() neotest.run.run({ strategy = "dap" }) end, { desc = "Debug nearest test" })
vim.keymap.set("n", "<leader>ts", function() neotest.summary.toggle() end, { desc = "Toggle test summary" })
vim.keymap.set("n", "<leader>to", function() neotest.output.open({ enter = true }) end, { desc = "Show test output" })
vim.keymap.set("n", "<leader>tp", function() neotest.output_panel.toggle() end, { desc = "Toggle output panel" })
