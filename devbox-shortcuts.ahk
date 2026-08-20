#Requires AutoHotkey v2.0
#SingleInstance Force

; Right Ctrl+W deletes the previous word; Left Ctrl+W keeps native app behavior.
>^w::Send "^{Backspace}"
