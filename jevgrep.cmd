@echo off
rem Wurzel-Aufrufer (Muster omnitrade.cmd/bestand.cmd): jevgrep aus jedem
rem Verzeichnis. Reicht alle Argumente durch, gibt den Exitcode weiter.
call "%~dp0Agenten\Werkzeuge\jevgrep\jg.cmd" %*
exit /b %ERRORLEVEL%