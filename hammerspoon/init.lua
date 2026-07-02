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
-- delete-word), which native fields, browser inputs and browser rich-text
-- editors (incl. Messenger/Instagram's Lexical in Brave) all honor.
--
-- IMPORTANT: this is a Carbon hotkey (hs.hotkey), NOT an event tap. Event
-- taps get silently disabled by macOS (kCGEventTapDisabledByTimeout) with
-- isEnabled() still reporting true, so they stop working and no watchdog
-- reliably catches them. Carbon hotkeys stay registered and never suffer
-- this. We disable the hotkey while Ghostty is focused so zsh's ^W and
-- nvim's Ctrl+W window prefix keep working there, and enable it elsewhere.
local GHOSTTY_BID = "com.mitchellh.ghostty"

local function deleteWordBackward()
    hs.eventtap.keyStroke({ "alt" }, "delete", 0)
end

-- pressedfn + repeatfn so holding Ctrl+W keeps deleting words; no releasedfn.
ctrlWHotkey = hs.hotkey.new({ "ctrl" }, "w", deleteWordBackward, nil, deleteWordBackward)

local function syncCtrlWForApp(app)
    local front = app or hs.application.frontmostApplication()
    if front and front:bundleID() == GHOSTTY_BID then
        ctrlWHotkey:disable()
    else
        ctrlWHotkey:enable()
    end
end
syncCtrlWForApp(hs.application.frontmostApplication())

ghosttyFocusWatcher = hs.application.watcher.new(function(_, event, app)
    if event == hs.application.watcher.activated then
        syncCtrlWForApp(app)
    end
end)
ghosttyFocusWatcher:start()

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

-- The language toggle must use event taps (a modifier-only chord can't be a
-- Carbon hotkey). macOS can silently disable an event tap
-- (kCGEventTapDisabledByTimeout) while isEnabled() still reports true, so an
-- isEnabled() check is not enough. Force-restart these taps periodically to
-- guarantee they keep firing. Their callbacks are trivial, so a missed event
-- during the sub-millisecond restart is harmless.
eventTapWatchdog = hs.timer.doEvery(5, function()
    for _, tap in ipairs({ langFlagTap, langKeyTap }) do
        if tap then
            tap:stop()
            tap:start()
        end
    end
end)

hs.alert.show("Hammerspoon config loaded")
