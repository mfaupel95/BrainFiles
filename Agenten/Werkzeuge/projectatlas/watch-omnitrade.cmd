@echo off
rem ProjectAtlas-Watcher fuer ein Repository starten - Dauerprozess.
rem Wird von watch-start.ps1 aufgerufen (dort wird geprueft, ob schon einer laeuft).
rem Umleitung macht die Shell selbst; deshalb braucht der Aufrufer kein
rem Start-Process -Redirect (das blockiert bei Dauerprozessen).
setlocal
set EXE=%~dp0bin\projectatlas.exe
set LOG=%~dp0logs
if not exist "%LOG%" mkdir "%LOG%"
cd /d O:\Werkstatt\omnitrade
start "" /b "%EXE%" watch --poll-seconds 2 "O:\Werkstatt\omnitrade" >> "%LOG%\watch-omnitrade.log" 2>&1
endlocal
