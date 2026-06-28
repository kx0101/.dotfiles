# macOS keyboard: Kinesis Advantage 360 Pro Ctrl <-> Command swap

`runs/keyboard` installs a LaunchAgent that uses `hidutil` to swap Control and
Command on the Kinesis (vendor 10730 / product 866) at the HID level.

Why not System Settings > Keyboard > Modifier Keys? Ghostty (and kitty,
Alacritty) read keys below that layer, so the System Settings remap is ignored
inside the terminal. `hidutil` remaps at the HID driver level, so it is honored
everywhere, including Ghostty.

Mapping (Kinesis only, the MacBook keyboard is untouched):

| Physical key | Sends   |
|--------------|---------|
| Left Ctrl    | Command |
| Left Cmd/Win | Control |
| Right Ctrl   | Command |
| Right Cmd    | Control |

## Install / re-apply

    ./run keyboard          # or directly: ./runs/keyboard

This removes the old System Settings per-device remap (so it does not cancel out
with hidutil in normal apps) and (re)loads the LaunchAgent.

## Apply now without re-login (one-liner)

    hidutil property --matching '{"VendorID":0x29EA,"ProductID":0x362}' \
      --set '{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0x7000000E0,"HIDKeyboardModifierMappingDst":0x7000000E3},{"HIDKeyboardModifierMappingSrc":0x7000000E3,"HIDKeyboardModifierMappingDst":0x7000000E0},{"HIDKeyboardModifierMappingSrc":0x7000000E4,"HIDKeyboardModifierMappingDst":0x7000000E7},{"HIDKeyboardModifierMappingSrc":0x7000000E7,"HIDKeyboardModifierMappingDst":0x7000000E4}]}'

## Revert

    launchctl bootout gui/$(id -u)/com.kx0101.kinesis-ctrl-cmd-swap
    rm ~/Library/LaunchAgents/com.kx0101.kinesis-ctrl-cmd-swap.plist
    hidutil property --matching '{"VendorID":0x29EA,"ProductID":0x362}' --set '{"UserKeyMapping":[]}'

`kinesis-systemsettings-modmap.backup.txt` holds the old System Settings
per-device remap that this replaces, in case you want it back.
