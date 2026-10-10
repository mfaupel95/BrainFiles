@echo off
rem ---------------------------------------------------------------------------
rem  omnitrade - aus JEDEM Verzeichnis aufrufbar (liegt in der Wurzel BrainFiles).
rem  Ohne Argument : Stand des Laufs anzeigen (rein lesend, ueber die Bruecke).
rem  Mit "start"   : Live-Lauf im OKX-DEMO starten - nur EINER zur Zeit.
rem  Mit "ui"      : eigenes Fenster omnitrade-ui (Kerzenchart + Orders) starten.
rem  Anleitung: MaxHirn\Wissen\Omnitrade.md   (Stand 30.09.2026: PowerShell-Start
rem  und das Fenster omnitrade-ui sind dort beschrieben.)
rem
rem  ZWEI FALLEN, beide am 30.09.2026 erlebt:
rem  (1) "find"/"tasklist" NICHT mit blossem Namen aufrufen - in einer Shell mit
rem      MSYS/git-bash im PATH gewinnt deren "find" und die Pruefung faellt still
rem      aus, obwohl schon ein Lauf laeuft (zwei Laeufe ordern doppelt).
rem  (2) Der Programmname beweist NICHTS: dasselbe omnitrade-cli.exe faehrt auch
rem      Backtests. Deshalb entscheidet omnitrade_lauf.py an zwei Zeugen
rem      (Statusdatei + PID), ob der LAUF noch lebt.
rem ---------------------------------------------------------------------------
setlocal
set "ROOT=%~dp0"
set "SYS=%SystemRoot%\System32"
set "OMNI=%ROOT%Werkstatt\omnitrade"
if /I "%~1"=="start" goto start
if /I "%~1"=="ui" goto ui
if /I "%~1"=="dashboard" goto dashboard
python "%ROOT%Agenten\Handel\omnitrade_bridge.py" %*
goto :eof

:start
python "%ROOT%Agenten\Handel\omnitrade_lauf.py" >nul 2>&1
if not errorlevel 1 (
  echo Laeuft schon - nur ein Lauf zur Zeit.
  python "%ROOT%Agenten\Handel\omnitrade_lauf.py"
  exit /b 1
)
cd /d "%OMNI%"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set "STAMP=%%i"
echo Starte omnitrade (OKX-Demo, BTCUSDC, ema_cross_20_50)
echo   Log: Werkstatt\omnitrade\logs\live-%STAMP%.log
echo   Fenster: omnitrade.cmd ui      Beenden: Strg+C hier (kein hartes Schliessen)
target\debug\omnitrade-cli.exe live --exchange okx --network testnet --symbol BTCUSDC --script strategien/ema_cross_20_50.omni --status-file status/live.json > "logs\live-%STAMP%.log" 2>&1
echo Lauf beendet mit Code %ERRORLEVEL%.
goto :eof

:ui
"%SYS%\tasklist.exe" /FI "IMAGENAME eq omnitrade-ui.exe" /NH > "%TEMP%\omnitrade_ui.txt" 2>nul
"%SYS%\findstr.exe" /I /C:"omnitrade-ui.exe" "%TEMP%\omnitrade_ui.txt" >nul
if not errorlevel 1 (
  echo Fenster omnitrade-ui laeuft schon.
  exit /b 1
)
cd /d "%OMNI%"
if exist "target\debug\omnitrade-ui.exe" (
  echo Starte omnitrade-ui - liest dieselbe Statusdatei, nur lesend.
  target\debug\omnitrade-ui.exe
) else (
  echo Baue omnitrade-ui (erster Start dauert ein paar Minuten) ...
  cargo run -q -p omnitrade-ui
)
goto :eof

:dashboard
set "DASHPY=%ROOT%Agenten\Handel\dashboard\.venv\Scripts\python.exe"
if not exist "%DASHPY%" (
  echo Dashboard-venv fehlt. Einmal anlegen:
  echo   python -m venv "%ROOT%Agenten\Handel\dashboard\.venv"
  echo   "%ROOT%Agenten\Handel\dashboard\.venv\Scripts\pip.exe" install -r "%ROOT%Agenten\Handel\dashboard\requirements.txt"
  exit /b 1
)
set "DASH_ARGS="
if /I "%~2"=="--lan" set "DASH_ARGS=--lan"
cd /d "%ROOT%Agenten\Handel"
echo Starte Omnitrade Dashboard auf http://localhost:7788   Beenden: Strg+C
"%DASHPY%" -m dashboard %DASH_ARGS%
goto :eof
