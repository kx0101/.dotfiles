#Requires AutoHotkey v2.0
#SingleInstance Force

; Logical Right Ctrl+W deletes the previous word.
>^w::Send "^{Backspace}"
