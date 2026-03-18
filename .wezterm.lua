local wezterm = require("wezterm")
local act = wezterm.action
local rose_pine = wezterm.plugin.require('https://github.com/neapsix/wezterm').moon

function get_dirs(base_path, max_depth)
    local dirs = {}

    local escaped_path = base_path:gsub("'", "''")

    local ps_command = string.format(
        "Get-ChildItem -Path '%s' -Directory -Recurse -Depth %d -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName",
        escaped_path,
        max_depth - 1
    )

    local success, stdout, stderr = wezterm.run_child_process({
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        ps_command
    })

    table.insert(dirs, base_path)

    if success and stdout then
        for line in stdout:gmatch("[^\r\n]+") do
            if line and line ~= "" and line ~= base_path then
                table.insert(dirs, line)
            end
        end
    else
        wezterm.log_error("Failed to get directories: " .. (stderr or "unknown error"))
    end

    return dirs
end

return {
    font = wezterm.font("JetBrainsMono Nerd Font", { weight = "Regular" }),
    font_size = 12.5,

    default_prog = { "C:/Program Files/PowerShell/7/pwsh.exe" },

    term = "xterm-256color",

    colors = rose_pine.colors(),

    window_decorations = "RESIZE",
    window_background_opacity = 1.0,

    window_padding = {
        left = 0,
        right = 0,
        top = 0,
        bottom = 0,
    },

    use_fancy_tab_bar = false,
    hide_tab_bar_if_only_one_tab = false,
    tab_bar_at_bottom = true,
    tab_max_width = 32,

    enable_wayland = false,
    enable_scroll_bar = false,
    enable_tab_bar = true,

    front_end = "WebGpu",
    max_fps = 120,
    scrollback_lines = 10000,

    leader = { key = "a", mods = "CTRL", timeout_milliseconds = 1000 },

    keys = {
        -- Pane splits (tmux-style)
        { key = '"',  mods = "LEADER|SHIFT", action = act.SplitVertical { domain = "CurrentPaneDomain" } },
        { key = "%",  mods = "LEADER|SHIFT", action = act.SplitHorizontal { domain = "CurrentPaneDomain" } },
        { key = "-",  mods = "LEADER",       action = act.SplitVertical { domain = "CurrentPaneDomain" } },
        { key = "\\", mods = "LEADER",       action = act.SplitHorizontal { domain = "CurrentPaneDomain" } },

        -- Quit
        { key = "q",  mods = "LEADER|SHIFT", action = wezterm.action.QuitApplication },

        -- Pane navigation (hjkl)
        { key = "h",  mods = "LEADER",       action = act.ActivatePaneDirection("Left") },
        { key = "j",  mods = "LEADER",       action = act.ActivatePaneDirection("Down") },
        { key = "k",  mods = "LEADER",       action = act.ActivatePaneDirection("Up") },
        { key = "l",  mods = "LEADER",       action = act.ActivatePaneDirection("Right") },

        -- Pane closing
        { key = "x",  mods = "LEADER",       action = act.CloseCurrentPane { confirm = true } },
        { key = "z",  mods = "LEADER",       action = act.TogglePaneZoomState },

        -- Tab management
        { key = "c",  mods = "LEADER",       action = act.SpawnTab "CurrentPaneDomain" },
        { key = "n",  mods = "LEADER",       action = act.ActivateTabRelative(1) },
        { key = "p",  mods = "LEADER",       action = act.ActivateTabRelative(-1) },
        { key = "1",  mods = "LEADER",       action = act.ActivateTab(0) },
        { key = "2",  mods = "LEADER",       action = act.ActivateTab(1) },
        { key = "3",  mods = "LEADER",       action = act.ActivateTab(2) },
        { key = "4",  mods = "LEADER",       action = act.ActivateTab(3) },
        { key = "5",  mods = "LEADER",       action = act.ActivateTab(4) },
        { key = "6",  mods = "LEADER",       action = act.ActivateTab(5) },
        { key = "7",  mods = "LEADER",       action = act.ActivateTab(6) },
        { key = "8",  mods = "LEADER",       action = act.ActivateTab(7) },
        { key = "9",  mods = "LEADER",       action = act.ActivateTab(8) },
        { key = "&",  mods = "LEADER|SHIFT", action = act.CloseCurrentTab { confirm = true } },

        {
            key = ",",
            mods = "LEADER",
            action = act.PromptInputLine {
                description = "Enter new name for tab",
                action = wezterm.action_callback(function(window, pane, line)
                    if line then
                        window:active_tab():set_title(line)
                    end
                end),
            }
        },

        -- Workspace management
        { key = ")", mods = "LEADER|SHIFT", action = act.SwitchWorkspaceRelative(1) },
        { key = "(", mods = "LEADER|SHIFT", action = act.SwitchWorkspaceRelative(-1) },
        { key = "n", mods = "LEADER|CTRL",  action = act.SwitchWorkspaceRelative(1) },
        { key = "p", mods = "LEADER|CTRL",  action = act.SwitchWorkspaceRelative(-1) },
        { key = "s", mods = "LEADER",       action = act.ShowLauncherArgs { flags = "FUZZY|WORKSPACES" } },

        {
            key = "m",
            mods = "LEADER",
            action = wezterm.action_callback(function(window, pane)
                local screen = window:screen()
                local dims = screen:get_dimensions()
                window:set_config_overrides({
                    initial_cols = dims.cols,
                    initial_rows = dims.rows,
                })
            end)
        },

        -- Session switcher
        {
            key = "f",
            mods = "LEADER",
            action = wezterm.action_callback(function(window, pane)
                local dirs = get_dirs("C:/Users/ekoulaxis/Code", 3)

                wezterm.log_info("Found " .. #dirs .. " directories")

                if #dirs == 0 then
                    wezterm.log_error("No directories found!")
                    return
                end

                local choices = {}
                for _, dir in ipairs(dirs) do
                    table.insert(choices, { label = dir })
                end

                window:perform_action(
                    act.InputSelector {
                        title = "Select Project Directory",
                        fuzzy = true,
                        fuzzy_description = "Fuzzy find directory: ",
                        choices = choices,
                        action = wezterm.action_callback(function(win, p, id, label)
                            if not label then
                                wezterm.log_info("No directory selected")
                                return
                            end

                            wezterm.log_info("Selected directory: " .. label)

                            -- Extract workspace name from path
                            local workspace_name = label:match("([^/\\]+)$")
                            if workspace_name then
                                workspace_name = workspace_name:gsub("%.", "_"):gsub("%s", "_")
                                wezterm.log_info("Workspace name: " .. workspace_name)

                                win:perform_action(
                                    act.SwitchToWorkspace {
                                        name = workspace_name,
                                        spawn = { cwd = label }
                                    },
                                    p
                                )

                                wezterm.time.call_after(0.5, function()
                                    win:active_tab():set_title(workspace_name)
                                end)
                            end
                        end),
                    },
                    pane
                )
            end)
        },

        -- New named workspace
        {
            key = "S",
            mods = "LEADER|SHIFT",
            action = act.PromptInputLine {
                description = "New workspace name",
                action = wezterm.action_callback(function(window, pane, line)
                    if line then
                        window:perform_action(
                            act.SwitchToWorkspace { name = line },
                            pane
                        )
                    end
                end),
            }
        },

        -- Reload config
        { key = "r", mods = "LEADER",       action = act.ReloadConfiguration },

        -- Copy mode
        { key = "[", mods = "LEADER",       action = act.ActivateCopyMode },
        { key = "]", mods = "LEADER",       action = act.PasteFrom "Clipboard" },

        -- Detach
        { key = "d", mods = "LEADER",       action = act.CloseCurrentPane { confirm = false } },

        -- Command palette
        { key = ":", mods = "LEADER|SHIFT", action = act.ActivateCommandPalette },

        -- Fullscreen
        { key = "f", mods = "CTRL|SHIFT",   action = act.ToggleFullScreen },
    },

    -- Copy mode configuration
    key_tables = {
        copy_mode = {
            { key = "v", mods = "NONE",  action = act.CopyMode "MoveToStartOfLineContent" },
            { key = "V", mods = "SHIFT", action = act.CopyMode { SetSelectionMode = "Line" } },
            { key = "v", mods = "CTRL",  action = act.CopyMode { SetSelectionMode = "Block" } },

            -- Vi motions
            { key = "h", mods = "NONE",  action = act.CopyMode "MoveLeft" },
            { key = "j", mods = "NONE",  action = act.CopyMode "MoveDown" },
            { key = "k", mods = "NONE",  action = act.CopyMode "MoveUp" },
            { key = "l", mods = "NONE",  action = act.CopyMode "MoveRight" },
            { key = "w", mods = "NONE",  action = act.CopyMode "MoveForwardWord" },
            { key = "b", mods = "NONE",  action = act.CopyMode "MoveBackwardWord" },
            { key = "0", mods = "NONE",  action = act.CopyMode "MoveToStartOfLine" },
            { key = "$", mods = "SHIFT", action = act.CopyMode "MoveToEndOfLineContent" },
            { key = "g", mods = "NONE",  action = act.CopyMode "MoveToScrollbackTop" },
            { key = "G", mods = "SHIFT", action = act.CopyMode "MoveToScrollbackBottom" },

            -- Copy/paste
            {
                key = "y",
                mods = "NONE",
                action = act.Multiple {
                    { CopyTo = "ClipboardAndPrimarySelection" },
                    { CopyMode = "Close" },
                }
            },
            { key = "Enter",  mods = "NONE", action = act.CopyMode "MoveToStartOfNextLine" },
            { key = "Escape", mods = "NONE", action = act.CopyMode "Close" },
            { key = "q",      mods = "NONE", action = act.CopyMode "Close" },
        },

        search_mode = {
            { key = "Enter",  mods = "NONE", action = act.CopyMode "PriorMatch" },
            { key = "Escape", mods = "NONE", action = act.CopyMode "Close" },
            { key = "n",      mods = "CTRL", action = act.CopyMode "NextMatch" },
            { key = "p",      mods = "CTRL", action = act.CopyMode "PriorMatch" },
            { key = "r",      mods = "CTRL", action = act.CopyMode "CycleMatchType" },
            { key = "u",      mods = "CTRL", action = act.CopyMode "ClearPattern" },
        },
    },
}
