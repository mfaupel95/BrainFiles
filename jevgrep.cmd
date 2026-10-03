@echo off
rem Wurzel-Aufrufer (Muster omnitrade.cmd/bestand.cmd): jevgrep aus jedem Verzeichnis.
rem Suchen laufen ueber den Vorschalter jg_sicher.py (Anbieter, Wurzelgroesse, Kosten);
rem Subkommandos wie "files" gehen direkt durch. --trotzdem und --leise versteht nur
rem der Vorschalter, jevgrep selbst nicht.
python "%~dp0Agenten\Werkzeuge\jevgrep\jg_sicher.py" %*
exit /b %ERRORLEVEL%