@echo off
rem Auswertung aller omnitrade-Laeufe (rein lesend). Mit "schreibe": Bericht nach Werkstatt\omnitrade\status\auswertung.md
setlocal
set "H=%~dp0Agenten\Handel"
set "PY=%H%\scanner\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if /i "%~1"=="schreibe" ("%PY%" "%H%\omnitrade_auswertung.py" --schreibe) else ("%PY%" "%H%\omnitrade_auswertung.py")
if "%~1"=="" pause
