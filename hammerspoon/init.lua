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
-- This relies on the focused field honoring Option+Backspace, which native
-- fields, browser inputs and browser rich-text editors (incl. Messenger/
-- Instagram's Lexical in Brave) all do.
--
-- The keyDown callback must stay fast: a slow callback makes macOS disable
-- the tap (kCGEventTapDisabledByTimeout), after which it silently stops
-- working. So instead of calling hs.application.frontmostApplication() on
-- every keypress, we cache whether Ghostty is focused via an app watcher.
local GHOSTTY_BID = "com.mitchellh.ghostty"
local function isGhosttyFront()
    local app = hs.application.frontmostApplication()
    return app ~= nil and app:bundleID() == GHOSTTY_BID
end
local ghosttyFocused = isGhosttyFront()

ghosttyFocusWatcher = hs.application.watcher.new(function(_, event, app)
    if event == hs.application.watcher.activated then
        ghosttyFocused = (app ~= nil and app:bundleID() == GHOSTTY_BID)
    end
end)
ghosttyFocusWatcher:start()

ctrlWTap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(e)
    if ghosttyFocused then
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

-- Option+Shift = toggle input source (ABC <-> Greek), like Windows Alt+Shift.
-- macOS can't bind a modifier-only shortcut natively, so we watch flag changes:
-- arm when ONLY alt+shift are held, and fire once on release, unless another
-- key/modifier was pressed in between (that means it was a real shortcut).
local function toggleInputSource()
    if hs.keycodes.currentLayout() == "Greek" then
        hs.keycodes.setLayout("ABC")
    else
        hs.keycodes.setLayout("Greek")
    end
end

local langArmed = false
local langOtherKey = false

langFlagTap = hs.eventtap.new({ hs.eventtap.event.types.flagsChanged }, function(e)
    local f = e:getFlags()
    local pureAltShift = f.alt and f.shift and not f.cmd and not f.ctrl and not f.fn
    if pureAltShift then
        langArmed = true
        langOtherKey = false
    elseif langArmed then
        if f.cmd or f.ctrl or f.fn then
            -- a disqualifying modifier was added: not a plain Option+Shift tap
            langOtherKey = true
            langArmed = false
        else
            -- alt and/or shift released: perform the toggle once
            if not langOtherKey then
                toggleInputSource()
            end
            langArmed = false
        end
    end
    return false
end)

langKeyTap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(e)
    if langArmed then
        langOtherKey = true
    end
    return false
end)

langFlagTap:start()
langKeyTap:start()

-- macOS can silently disable an event tap (e.g. kCGEventTapDisabledByTimeout).
-- Re-arm any that got turned off so Ctrl+W word-delete and the Option+Shift
-- language toggle keep working without needing a manual reload.
eventTapWatchdog = hs.timer.doEvery(5, function()
    for _, tap in ipairs({ ctrlWTap, langFlagTap, langKeyTap }) do
        if tap and not tap:isEnabled() then
            tap:start()
        end
    end
end)

hs.alert.show("Hammerspoon config loaded")
