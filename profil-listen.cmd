@echo off
rem ---------------------------------------------------------------------------
rem  profil-listen - aus JEDEM Verzeichnis aufrufbar (liegt in der Wurzel BrainFiles).
rem  Die models:-Listen der Bot-Profile zeigen, kuerzen oder zurueckholen.
rem
rem  Ohne Argument : Trockenlauf - je Profil "vorher -> nachher", schreibt NICHTS
rem  kuerzen       : Listen wirklich kuerzen (je Datei eine Sicherung .bak-JJJJMMTT)
rem  zurueck       : zeigen, welche Sicherungen zurueckgeholt wuerden (Trockenlauf)
rem  zurueck!      : Sicherungen WIRKLICH zurueckholen
rem
rem  Programm : Agenten\Hermes\scripts\profil-modelllisten-kuerzen.py
rem  Es braucht das venv-Python von Hermes (PyYAML + hermes_cli), nicht das
rem  PATH-Python - deshalb steht der Pfad hier fest und wird vorher geprueft.
rem
rem  Regel des Werkzeugs: behalten wird nur, was das Profil SELBST nennt
rem  (model.default, providers.<p>.model/default_model, fallback_providers,
rem  delegation.model, moa). Der models:-Block ist eine Anzeigeliste - die
rem  Modellwahl bleibt vollstaendig, weil discover_models: true bleibt.
rem  Die HAUPTconfig (Agenten\Hermes\config.yaml) wird nie angefasst.
rem ---------------------------------------------------------------------------
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%Agenten\Hermes\hermes-agent\venv\Scripts\python.exe"
set "SKRIPT=%ROOT%Agenten\Hermes\scripts\profil-modelllisten-kuerzen.py"
if not exist "%PY%" (
  echo FEHLT: %PY%
  echo Das venv von Hermes fehlt - erst den Hermes-Checkout herstellen.
  exit /b 2
)
if not exist "%SKRIPT%" (
  echo FEHLT: %SKRIPT%
  exit /b 2
)
if /I "%~1"=="kuerzen"   goto kuerzen
if /I "%~1"=="zurueck"   goto zurueck
if /I "%~1"=="zurueck!"  goto zurueck_echt
"%PY%" "%SKRIPT%"
goto :eof

:kuerzen
"%PY%" "%SKRIPT%" --anwenden
goto :eof

:zurueck
"%PY%" "%SKRIPT%" --zuruecknehmen
goto :eof

:zurueck_echt
"%PY%" "%SKRIPT%" --zuruecknehmen --anwenden
goto :eof