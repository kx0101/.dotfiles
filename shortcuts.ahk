; Alt + Q - Browser (Google Chrome)
!q::
IfWinExist, ahk_exe chrome.exe ; Chrome browser window class
{
    WinActivate ;
}
else
{
    Run, C:\Program FIles\Google\Chrome\Application\chrome.exe ;
}
return

; Alt + W - WezTerm
!w::
IfWinExist, ahk_exe wezterm-gui.exe ; wezterm
{
    WinActivate
}
else
{
    Run, "C:\Program Files\WezTerm\wezterm-gui.exe" ;
}
return

; Alt + E - Slack
!e::
IfWinExist, ahk_exe slack.exe ; Slack application executable
{
    WinActivate
}
else
{
    Run, C:\Users\el.koulaxis\AppData\Local\slack\slack.exe ;
}
return

; Alt + R - Discord
!r::
IfWinExist, ahk_exe Discord.exe ; Discord application executable
{
    WinActivate
}
else
{
    Run, C:\Users\el.koulaxis\AppData\Local\Discord\Update.exe --processStart Discord.exe ; 
}
return

; Alt + F - Spotify
!f::
IfWinExist, ahk_exe Spotify.exe ; Spotify application executable
{
    WinActivate
}
else
{
    Run, C:\Users\el.koulaxis\AppData\Roaming\Spotify\Spotify.exe ; 
}
return
