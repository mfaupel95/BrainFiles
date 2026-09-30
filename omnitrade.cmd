@echo off
rem ---------------------------------------------------------------------------
rem  omnitrade - aus JEDEM Verzeichnis aufrufbar (liegt in der Wurzel BrainFiles).
rem  Ohne Argument : Stand des Laufs anzeigen (rein lesend, ueber die Bruecke).
rem  Mit "start"   : Live-Lauf im OKX-DEMO starten - nur EINER zur Zeit.
rem  Anleitung: MaxHirn\Wissen\Omnitrade.md
rem
rem  FALLE (30.09.2026 erlebt): "find"/"tasklist" NICHT mit blossem Namen aufrufen -
rem  in einer Shell mit MSYS/git-bash im PATH gewinnt deren "find" und die Pruefung
rem  "laeuft schon" faellt still aus, obwohl schon ein Lauf laeuft (zwei Laeufe
rem  ordern doppelt und schreiben in dieselbe Statusdatei). Darum voller Pfad.
rem ---------------------------------------------------------------------------
setlocal
set "ROOT=%~dp0"
set "SYS=%SystemRoot%\System32"
if /I "%~1"=="start" goto start
python "%ROOT%Agenten\Handel\omnitrade_bridge.py" %*
goto :eof

:start
"%SYS%\tasklist.exe" /FI "IMAGENAME eq omnitrade-cli.exe" /NH > "%TEMP%\omnitrade_task.txt" 2>nul
"%SYS%\findstr.exe" /I /C:"omnitrade-cli.exe" "%TEMP%\omnitrade_task.txt" >nul
if not errorlevel 1 (
  echo Laeuft schon - nur ein Lauf zur Zeit. Stand:
  echo   python "%ROOT%Agenten\Handel\omnitrade_bridge.py"
  exit /b 1
)
cd /d "%ROOT%Werkstatt\omnitrade"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set "STAMP=%%i"
echo Starte omnitrade (OKX-Demo, BTCUSDC, ema_cross_20_50)
echo   Log: Werkstatt\omnitrade\logs\live-%STAMP%.log
echo   Anzeige: Handelszentrale, Reiter "omnitrade" - oder erneut omnitrade.cmd
echo   Beenden: Strg+C in diesem Fenster (kein hartes Schliessen, sonst bleibt der Zustand "running")
target\debug\omnitrade-cli.exe live --exchange okx --network testnet --symbol BTCUSDC --script strategien/ema_cross_20_50.omni --status-file status/live.json > "logs\live-%STAMP%.log" 2>&1
echo Lauf beendet mit Code %ERRORLEVEL%.
