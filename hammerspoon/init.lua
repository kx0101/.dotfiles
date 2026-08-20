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
    f = "Spotify",       -- ⌥F  Spotify
}

for key, appName in pairs(apps) do
    hs.hotkey.bind(mod, key, function()
        hs.application.launchOrFocus(appName)
    end)
end

local WINDOWS_APP_BID = "com.microsoft.rdc.macos"
local KEYCODE_M = 46

local function focusDevBox()
    local app = hs.application.get(WINDOWS_APP_BID)
    if app == nil then
        hs.application.launchOrFocusByBundleID(WINDOWS_APP_BID)
        return
    end

    local window = app:mainWindow()
    if window ~= nil and window:isMinimized() then
        window:unminimize()
    end

    -- Let the Option chord finish before activating the fullscreen window.
    hs.timer.doAfter(0.15, function()
        app:activate(true)
        if window ~= nil then
            window:raise()
            window:focus()
        end
    end)
end

-- Use the physical M key so the shortcut also works with the Greek layout.
hs.hotkey.bind(mod, KEYCODE_M, focusDevBox)

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

-- Ctrl+W = delete the previous word everywhere EXCEPT Ghostty and the Dev Box.
-- The Dev Box handles logical Right Ctrl+W inside Windows via AutoHotkey.
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

-- Cache the focused app so the keyDown callback stays cheap; a slow callback is
-- what trips the macOS tap-disable timeout.
local ghosttyFocused = false
local devBoxFocused = false

local function refreshCtrlWFocus()
    local app = hs.application.frontmostApplication()
    local bundleID = app and app:bundleID()
    ghosttyFocused = bundleID == GHOSTTY_BID
    devBoxFocused = bundleID == WINDOWS_APP_BID
end
refreshCtrlWFocus()

ghosttyFocusWatcher = hs.application.watcher.new(function(_, event, app)
    if event == hs.application.watcher.activated then
        local bundleID = app and app:bundleID()
        ghosttyFocused = bundleID == GHOSTTY_BID
        devBoxFocused = bundleID == WINDOWS_APP_BID
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
    if ghosttyFocused or devBoxFocused then
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

local KEYCODE_LEFT = 123
local KEYCODE_RIGHT = 124
local CTRL_ARROW_EVENT_MARKER = 0x4B583031
local EVENT_SOURCE_USER_DATA = hs.eventtap.event.properties.eventSourceUserData

-- Mission Control reserves Ctrl+Left/Right for switching macOS Spaces. In the
-- Dev Box, swallow that global shortcut and post the same event directly to
-- Windows App so Ctrl+Arrow navigates by word instead.
devBoxCtrlArrowTap = hs.eventtap.new({
    hs.eventtap.event.types.keyDown,
    hs.eventtap.event.types.keyUp,
}, function(event)
    if event:getProperty(EVENT_SOURCE_USER_DATA) == CTRL_ARROW_EVENT_MARKER then
        return false
    end

    local keycode = event:getKeyCode()
    local isArrow = keycode == KEYCODE_LEFT or keycode == KEYCODE_RIGHT
    if not devBoxFocused or not isArrow or not event:getFlags().ctrl then
        return false
    end

    local app = hs.application.get(WINDOWS_APP_BID)
    if app == nil then
        return false
    end

    event:setProperty(EVENT_SOURCE_USER_DATA, CTRL_ARROW_EVENT_MARKER)
    event:post(app)
    return true
end)
devBoxCtrlArrowTap:start()

-- Left Ctrl acts as Command in macOS, but as Ctrl in the Dev Box. In the Dev
-- Box, physical Right Ctrl and the Windows key are swapped so Right Ctrl is the
-- Windows key and the physical Windows key is Ctrl. Apply the mapping at the
-- HID layer because Windows App reads modifiers before Hammerspoon can rewrite.
local KINESIS_MATCHING = '{"VendorID":0x29EA,"ProductID":0x362}'
local KINESIS_LEFT_SWAP = '{"UserKeyMapping":['
    .. '{"HIDKeyboardModifierMappingSrc":0x7000000E0,'
    .. '"HIDKeyboardModifierMappingDst":0x7000000E3},'
    .. '{"HIDKeyboardModifierMappingSrc":0x7000000E3,'
    .. '"HIDKeyboardModifierMappingDst":0x7000000E0}]}'
local KINESIS_DEVBOX_WINDOWS_CTRL_SWAP = '{"UserKeyMapping":['
    .. '{"HIDKeyboardModifierMappingSrc":0x7000000E4,'
    .. '"HIDKeyboardModifierMappingDst":0x7000000E3},'
    .. '{"HIDKeyboardModifierMappingSrc":0x7000000E3,'
    .. '"HIDKeyboardModifierMappingDst":0x7000000E4}]}'
local KINESIS_OPTION_SPACE_MAPPING = '{"UserKeyMapping":['
    .. '{"HIDKeyboardModifierMappingSrc":0x7000000E4,'
    .. '"HIDKeyboardModifierMappingDst":0x7000000E3},'
    .. '{"HIDKeyboardModifierMappingSrc":0x7000000E3,'
    .. '"HIDKeyboardModifierMappingDst":0x7000000E4},'
    .. '{"HIDKeyboardModifierMappingSrc":0x70000002C,'
    .. '"HIDKeyboardModifierMappingDst":0x7000000E1}]}'
local kinesisMappingTask = nil

local function applyKinesisMapping(inDevBox, optionHeld)
    if inDevBox == nil then
        local app = hs.application.frontmostApplication()
        inDevBox = app ~= nil and app:bundleID() == WINDOWS_APP_BID
    end
    local mapping = KINESIS_LEFT_SWAP
    if inDevBox then
        mapping = optionHeld and KINESIS_OPTION_SPACE_MAPPING
            or KINESIS_DEVBOX_WINDOWS_CTRL_SWAP
    end

    if kinesisMappingTask ~= nil and kinesisMappingTask:isRunning() then
        kinesisMappingTask:terminate()
    end
    kinesisMappingTask = hs.task.new("/usr/bin/hidutil", nil,
        { "property", "--matching", KINESIS_MATCHING, "--set", mapping })
    kinesisMappingTask:start()
end

kinesisFocusWatcher = hs.application.watcher.new(function(_, event, app)
    if event == hs.application.watcher.activated then
        applyKinesisMapping(app ~= nil and app:bundleID() == WINDOWS_APP_BID)
    end
end)
kinesisFocusWatcher:start()
applyKinesisMapping()

local LEFT_OPTION_KEYCODE = 58
local RIGHT_OPTION_KEYCODE = 61

-- Windows App does not forward Option+Space. While Option is held in the Dev
-- Box, map the physical Space key to Shift so RDP receives native Alt+Shift.
devBoxOptionSpaceTap = hs.eventtap.new({
    hs.eventtap.event.types.flagsChanged,
}, function(event)
    if not devBoxFocused then
        return false
    end

    local keycode = event:getKeyCode()
    if keycode == LEFT_OPTION_KEYCODE or keycode == RIGHT_OPTION_KEYCODE then
        applyKinesisMapping(true, event:getFlags().alt == true)
    end
    return false
end)
devBoxOptionSpaceTap:start()

wakeWatcher = hs.caffeinate.watcher.new(function(event)
    local w = hs.caffeinate.watcher
    if event == w.systemDidWake
        or event == w.screensDidWake
        or event == w.sessionDidBecomeActive then
        applyKinesisMapping()
        refreshCtrlWFocus()
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
                applyKinesisMapping()
                refreshCtrlWFocus()
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
    if devBoxFocused then
        langArmed = false
        langOtherKey = false
        return false
    end

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
    if devBoxFocused then
        langArmed = false
        langOtherKey = false
        return false
    end

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
    for _, tap in ipairs({
        ctrlWTap,
        ctrlTrackTap,
        langFlagTap,
        langKeyTap,
        devBoxOptionSpaceTap,
        devBoxCtrlArrowTap,
    }) do
        if tap then
            tap:stop()
            tap:start()
        end
    end
end)

hs.alert.show("Hammerspoon config loaded")
