#Requires AutoHotkey v2.0

tableURL := "https://docs.google.com/spreadsheets/d/1ZLAVhT1vXYmg_FStuqbzyjbG_CXgkZVqava0QNbUp88/edit?pli=1&gid=1935802222#gid=1935802222"

; Активируем Chrome
if WinExist("ahk_exe chrome.exe")
{
    WinActivate
    Sleep(200)
}

; Открываем таблицу по ссылке
; Chrome сам переключится на уже открытую вкладку, если она есть
Run('"C:\Program Files\Google\Chrome\Application\chrome.exe" ' tableURL)