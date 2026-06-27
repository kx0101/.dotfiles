-- ~/.hammerspoon/init.lua
-- Global launch-or-focus shortcuts, ported from the Windows AutoHotkey setup
-- (shortcuts.ahk). On macOS, Alt is the Option (⌥) key.

-- Load the IPC module so the `hs` CLI can drive this config: hs -c "...".
require("hs.ipc")

-- ⌥ Option is the macOS analog of Alt on Windows/Linux.
local mod = { "alt" }

-- Edit the values to match the app names as they appear in /Applications.
local apps = {
    q = "Brave Browser", -- ⌥Q  browser
    w = "Ghostty",       -- ⌥W  terminal
    r = "Discord",       -- ⌥R  Discord
    a = "Viber",         -- ⌥A  Viber
    v = "WhatsApp",      -- ⌥V  WhatsApp
    z = "Obsidian",      -- ⌥Z  Obsidian
    f = "Spotify",       -- ⌥F  Spotify
}

for key, appName in pairs(apps) do
    hs.hotkey.bind(mod, key, function()
        hs.application.launchOrFocus(appName)
    end)
end

-- Reload config manually (⌥⌃R) and automatically when this file changes.
hs.hotkey.bind({ "alt", "ctrl" }, "r", function()
    hs.reload()
end)

local function reloadConfig(files)
    for _, file in pairs(files) do
        if file:sub(-4) == ".lua" then
            hs.reload()
            return
        end
    end
end

hs.pathwatcher.new(os.getenv("HOME") .. "/.hammerspoon/", reloadConfig):start()
-- Launch at login so the ⌥ shortcuts are always available after a reboot.
hs.autoLaunch(true)

-- Ctrl+W = delete the previous word everywhere EXCEPT the terminal.
-- Chromium browsers ignore ~/Library/KeyBindings and macOS has no global
-- Ctrl+W word-delete, so translate it to Option+Delete (the native
-- delete-word). Ghostty is excluded so zsh's ^W and nvim's Ctrl+W window
-- prefix keep working there.
ctrlWTap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(e)
    local app = hs.application.frontmostApplication()
    if app and app:bundleID() == "com.mitchellh.ghostty" then
        return false
    end

    local f = e:getFlags()
    -- keyCode 13 = "w", 51 = delete (backspace)
    if e:getKeyCode() == 13 and f.ctrl and not f.cmd and not f.alt and not f.shift and not f.fn then
        hs.eventtap.keyStroke({ "alt" }, "delete", 0)
        return true
    end

    return false
end)
ctrlWTap:start()

hs.alert.show("Hammerspoon config loaded")
