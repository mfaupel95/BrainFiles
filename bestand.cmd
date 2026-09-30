@echo off
rem ---------------------------------------------------------------------------
rem  bestand - aus JEDEM Verzeichnis aufrufbar (liegt in der Wurzel BrainFiles).
rem
rem  Ohne Argument      : eigener Code, ohne Fremd-Material
rem  --mit-fremd        : alles, zum Vergleich (Klone, Fremdprojekte)
rem  --bereich <pfad>   : nur ein Bereich (mehrfach moeglich)
rem  --json             : Maschinenlesbar
rem
rem  Warum es diesen Aufrufer gibt (30.09.2026): Der direkte Aufruf
rem  "Agenten\Werkzeuge\repos-zentrale\.venv\Scripts\python.exe ..." scheitert in
rem  PowerShell ohne ".\" bzw. "&" - ein relativer Programmpfad wird dort nicht
rem  als Programm gelesen ("Das Modul 'Agenten' konnte nicht geladen werden").
rem  Hier steht der Weg EINMAL, mit %~dp0 (dem eigenen Ordner) - der Aufruf
rem  funktioniert aus jedem Verzeichnis und trifft immer dasselbe venv.
rem
rem  Anzeigen/lesen: MaxHirn\Wiki\Betrieb\Fremd-Material.md
rem ---------------------------------------------------------------------------
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%Agenten\Werkzeuge\repos-zentrale\.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo Fehlt: "%PY%"
  echo Das venv der Zentrale ist noetig - es traegt die Standardbibliothek,
  echo die bestand.py braucht. Anlegen: Agenten\Werkzeuge\repos-zentrale
  echo ^(dort liegt auch repos_zentrale.py^).
  exit /b 2
)

"%PY%" "%ROOT%Agenten\Werkzeuge\bestand.py" %*
exit /b %ERRORLEVEL%