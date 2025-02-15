local dap = require("dap")
local ui = require("dapui")

require("dapui").setup()

local function get_target_framework(csproj_path)
    local content = vim.fn.readfile(csproj_path)
    for _, line in ipairs(content) do
        local target = line:match("<TargetFramework>(.-)</TargetFramework>")
        if target then
            return target
        end
    end
    return "net8.0"
end

local function joinpath(...)
    local sep = package.config:sub(1, 1)
    return table.concat({ ... }, sep)
end


dap.adapters.coreclr = {
    type = 'executable',
    command = os.getenv("HOME") .. '/.local/netcoredbg/netcoredbg/netcoredbg',
    args = { '--interpreter=vscode' }
}

dap.configurations.cs = {
    {
        type = 'coreclr',
        name = 'Launch',
        request = 'launch',
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

            local build_result = vim.fn.system('dotnet build')
            if vim.v.shell_error ~= 0 then
                error("Build failed: " .. build_result)
            end

            local dll_path = joinpath(cwd, "bin", "Debug", target_framework, project_name .. ".dll")
            if vim.fn.filereadable(dll_path) == 0 then
                error("DLL not found: " .. dll_path)
            end

            return dll_path
        end,
    },
}

vim.keymap.set("n", "<leader>b", dap.toggle_breakpoint)
vim.keymap.set("n", "<leader>gtc", dap.run_to_cursor)

-- eval var under cursor
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
