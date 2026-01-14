local wezterm = require("wezterm")
local act = wezterm.action

return {
    font = wezterm.font("Iosevka Term Slab", { weight = "Medium" }),
    font_size = 12.5,

    term = "xterm-256color",

    colors = {
        foreground = "#ADD8E6",
        background = "#181818",
        cursor_bg = "#FFDD33",
        cursor_border = "#FFDD33",
        cursor_fg = "#181818",
        selection_bg = "#453D41",
        selection_fg = "#F4F4FF",

        tab_bar = {
            background = "#333333",
            active_tab = {
                bg_color = "#333333",
                fg_color = "#ADD8E6",
                intensity = "Bold",
            },
            inactive_tab = {
                bg_color = "#333333",
                fg_color = "#888888",
            },
            inactive_tab_hover = {
                bg_color = "#444444",
                fg_color = "#ADD8E6",
            },
            new_tab = {
                bg_color = "#333333",
                fg_color = "#ADD8E6",
            },
        },

        ansi = {
            "#181818", "#F43841", "#73D936", "#FFDD33",
            "#96A6C8", "#9E95C7", "#95A99F", "#F5F5F5",
        },
        brights = {
            "#52494E", "#F43841", "#73D936", "#FFDD33",
            "#96A6C8", "#9E95C7", "#95A99F", "#FFFFFF",
        },
    },

    window_decorations = "RESIZE",
    window_background_opacity = 1.0,

    use_fancy_tab_bar = false,
    hide_tab_bar_if_only_one_tab = false,
    tab_bar_at_bottom = true,
    tab_max_width = 32,

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

        -- Session switcher
        {
            key = "f",
            mods = "LEADER",
            action = wezterm.action_callback(function(window, pane)
                local home = os.getenv("HOME")
                local success, stdout, stderr = wezterm.run_child_process({
                    "find",
                    home,
                    "-mindepth", "1",
                    "-maxdepth", "3",
                    "-type", "d"
                })

                if not success then
                    wezterm.log_error("Failed to run find: " .. stderr)
                    return
                end

                local dirs = {}
                for dir in stdout:gmatch("[^\r\n]+") do
                    table.insert(dirs, dir)
                end

                window:perform_action(
                    act.InputSelector {
                        action = wezterm.action_callback(function(win, p, id, label)
                            if not label then
                                return
                            end

                            local workspace_name = label:match("([^/]+)$"):gsub("%.", "_")

                            win:perform_action(
                                act.SwitchToWorkspace {
                                    name = workspace_name,
                                    spawn = {
                                        cwd = label,
                                    },
                                },
                                p
                            )
                        end),
                        title = "Select Project Directory",
                        choices = (function()
                            local choices = {}
                            for _, dir in ipairs(dirs) do
                                table.insert(choices, { label = dir })
                            end
                            return choices
                        end)(),
                        fuzzy = true,
                        fuzzy_description = "Fuzzy find directory: ",
                    },
                    pane
                )
            end)
        },

        -- Reload config
        { key = "r", mods = "LEADER",       action = act.ReloadConfiguration },

        -- Copy mode
        { key = "[", mods = "LEADER",       action = act.ActivateCopyMode },
        { key = "]", mods = "LEADER",       action = act.PasteFrom "Clipboard" },

        -- Detach
        { key = "d", mods = "LEADER",       action = act.QuitApplication },

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
