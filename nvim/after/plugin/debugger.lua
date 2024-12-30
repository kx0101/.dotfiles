local dap = require("dap")
local ui = require("dapui")

require("dapui").setup()
-- require("dap-go").setup()

dap.adapters.coreclr = {
    type = 'executable',
    command = '/home/elijahkx/.local/netcoredbg/netcoredbg/netcoredbg',
    args = { '--interpreter=vscode' }
}

dap.configurations.cs = {
    {
        type = 'coreclr',
        name = 'Launch',
        request = 'launch',
        program = function()
            local cwd = vim.fn.getcwd()

            local csproj_file = nil

            for _, file in ipairs(vim.fn.readdir(cwd)) do
                if file:match("%.csproj$") then
                    csproj_file = file
                    break
                end
            end

            if not csproj_file then
                error("No .csproj file found in " .. cwd)
            end

            local project_name = csproj_file:gsub("%.csproj$", "")

            local dll_path = cwd .. "/bin/Debug/net8.0/" .. project_name .. ".dll"

            return dll_path
        end,
    },
}

local elixir_ls_debugger = vim.fn.exepath "elixir-ls-debugger"
if elixir_ls_debugger ~= "" then
    dap.adapters.mix_task = {
        type = "executable",
        command = elixir_ls_debugger,
    }

    dap.configurations.elixir = {
        {
            type = "mix_task",
            name = "phoenix server",
            task = "phx.server",
            request = "launch",
            projectDir = "${workspaceFolder}",
            exitAfterTaskReturns = false,
            debugAutoInterpretAllModules = false,
        },
    }
end

vim.keymap.set("n", "<leader>b", dap.toggle_breakpoint)
vim.keymap.set("n", "<leader>gtc", dap.run_to_cursor)

-- Eval var under cursor
vim.keymap.set("n", "<leader>?", function()
    require("dapui").eval(nil, { enter = true })
end)

vim.keymap.set("n", "<leader>dc", dap.continue)
vim.keymap.set("n", "<F2>", dap.step_into)
vim.keymap.set("n", "<F3>", dap.step_over)
vim.keymap.set("n", "<F4>", dap.step_out)
vim.keymap.set("n", "<F5>", dap.step_back)
vim.keymap.set("n", "<F13>", dap.restart)

dap.listeners.before.attach.dapui_config = function()
    ui.open()
end
dap.listeners.before.launch.dapui_config = function()
    ui.open()
end
dap.listeners.before.event_terminated.dapui_config = function()
    ui.close()
end
dap.listeners.before.event_exited.dapui_config = function()
    ui.close()
end
