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
    z = "Pyxida",        -- ⌥Z  Pyxida
    m = "Windows App",   -- ⌥M  Windows App
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
-- We use a low-level eventtap keyed on the PHYSICAL keycode 13 (W), NOT a
-- Carbon hs.hotkey. hs.hotkey resolves the key through the active keyboard
-- layout, so when Greek is the input source Ctrl+W silently stops firing
-- (the key 'w' isn't in the Greek keymap). A raw keycode is layout-independent.
-- The known downside of eventtaps - macOS disabling them via
-- kCGEventTapDisabledByTimeout - is handled by (a) keeping this callback fast
-- (the slow Option+Delete is deferred, never run inline) and (b) a watchdog
-- that force-restarts the tap.
local GHOSTTY_BID = "com.mitchellh.ghostty"

-- Cache whether Ghostty is focused so the keyDown callback stays cheap; a slow
-- callback is what trips the macOS tap-disable timeout in the first place.
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

-- Send Option+Delete as an explicit hold: Option down, Delete down+up with the
-- Option flag, Option up, with small gaps. A plain keyStroke with no delay gets
-- interpreted as a single-char delete by contenteditable editors (Messenger's
-- word-delete. Verified on this machine: the simple keyStroke below word-deletes
-- in native fields; a fancier held-Option newKeyEvent sequence did NOT. This is
-- fast enough to run from the deferred flush.
local function deleteWordBackward()
    hs.eventtap.keyStroke({ "alt" }, "delete", 0)
end

-- Fire the word-delete immediately on Ctrl+W press. Keycode 13 keeps it
-- layout-independent (works in Greek).
--
-- We do NOT trust the ctrl flag on the W keydown event: this keyboard often
-- fails to co-report the modifier flag on the key event (observed W-down events
-- arriving with mods = alt / cmd / none while the Windows key that produces Ctrl
-- was clearly held). Instead we track Ctrl state independently from flagsChanged
-- events (which DO report reliably) and consult that tracked state.
local KEYCODE_W = 13
local ctrlHeld = false

-- Track Ctrl state from the reliable flagsChanged events.
ctrlTrackTap = hs.eventtap.new({ hs.eventtap.event.types.flagsChanged }, function(e)
    ctrlHeld = e:getFlags().ctrl == true
    return false
end)
ctrlTrackTap:start()

ctrlWTap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(e)
    if ghosttyFocused then
        return false
    end
    local f = e:getFlags()
    -- Fire on physical W while Ctrl is held (tracked OR flagged), as long as no
    -- other disqualifying modifier is present. cmd/alt on the event are ignored
    -- because this keyboard mislabels the modifier; ctrlHeld is the source of truth.
    if e:getKeyCode() == KEYCODE_W
        and (ctrlHeld or f.ctrl) and not f.shift and not f.fn then
        -- Defer so the tap callback returns immediately (a slow callback trips the
        -- macOS tap-disable timeout). Firing on press works even with the physical
        -- Ctrl key held because keyStroke posts a clean Option+Delete.
        hs.timer.doAfter(0, deleteWordBackward)
        return true -- swallow Ctrl+W so it doesn't reach the app
    end
    return false
end)
ctrlWTap:start()

-- After sleep the Kinesis USB keyboard re-enumerates and DROPS its hidutil
-- Ctrl<->Cmd swap, so the key that should send Ctrl sends Cmd and Ctrl+W (plus
-- every other Ctrl chord) breaks outside Ghostty. The LaunchAgent only redoes
-- the swap on its StartInterval, leaving a gap. Re-apply it immediately on wake
-- by kickstarting that same LaunchAgent (single source of truth for the mapping),
-- and re-assert the Ctrl+W hotkey for whatever app is now focused.
-- Use hs.task (not hs.execute with a login shell, which sources ~/.zshrc and can
-- time out); resolve the uid once via a fast non-login shell.
local KINESIS_SWAP_AGENT = "com.kx0101.kinesis-ctrl-cmd-swap"
local uid = (hs.execute("id -u") or "501"):gsub("%s+", "")

local function reapplyKinesisSwap()
    hs.task.new("/bin/launchctl", nil,
        { "kickstart", "-k", "gui/" .. uid .. "/" .. KINESIS_SWAP_AGENT }):start()
end

wakeWatcher = hs.caffeinate.watcher.new(function(event)
    local w = hs.caffeinate.watcher
    if event == w.systemDidWake
        or event == w.screensDidWake
        or event == w.sessionDidBecomeActive then
        reapplyKinesisSwap()
        ghosttyFocused = isGhosttyFront()
    end
end)
wakeWatcher:start()

-- The Kinesis also loses its hidutil swap when unplugged/replugged (a fresh USB
-- enumeration, with no sleep event firing). Re-apply on device attach. The
-- delayed retries let macOS finish creating the HID service before hidutil runs.
kinesisUsbWatcher = hs.usb.watcher.new(function(d)
    if d.eventType == "added" and d.vendorID == 10730 and d.productID == 866 then
        -- The keyboard's HID event service is created a few seconds AFTER the
        -- USB "added" event, so a single quick reapply lands before the service
        -- exists and is lost. Retry across a ~16s window; reapply is idempotent.
        for _, delay in ipairs({ 1.5, 3, 5, 7, 10, 13, 16 }) do
            hs.timer.doAfter(delay, function()
                reapplyKinesisSwap()
                ghosttyFocused = isGhosttyFront()
            end)
        end
    end
end)
kinesisUsbWatcher:start()

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

-- The Ctrl+W and language-toggle event taps can be silently disabled by macOS
-- (kCGEventTapDisabledByTimeout) while isEnabled() still reports true, so an
-- isEnabled() check is not enough. Force-restart them periodically to guarantee
-- they keep firing. Their callbacks are fast (Ctrl+W defers its slow work), so a
-- missed event during the sub-millisecond restart is harmless.
eventTapWatchdog = hs.timer.doEvery(5, function()
    for _, tap in ipairs({ ctrlWTap, ctrlTrackTap, langFlagTap, langKeyTap }) do
        if tap then
            tap:stop()
            tap:start()
        end
    end
end)

hs.alert.show("Hammerspoon config loaded")
