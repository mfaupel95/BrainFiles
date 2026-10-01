@echo off
rem jev-Bruecke mit Inception Mercury 2.5 starten (Fenster offen lassen).
rem Solange sie laeuft, sucht jevgrep ueber Mercury; der Schluessel kommt aus der
rem Windows-Benutzervariable INCEPTION_API_KEY und wird hier nicht angezeigt.
setlocal
set "JEVCREP_BRUECKE_PORT=8742"
set "JEVCREP_BRUECKE_BASIS=https://api.inceptionlabs.ai/v1"
set "JEVCREP_BRUECKE_MODELL=mercury-2.5"
set "JEVCREP_BRUECKE_FRIST=300"
set "PYTHONIOENCODING=utf-8"
set "PYTHONHOME="
set "PYTHONPATH="
cd /d "%~dp0"
echo jev-Bruecke startet auf 127.0.0.1:8742 mit Mercury 2.5 ...
python jev_bruecke.py
echo.
echo Bruecke beendet. Fenster mit einer Taste schliessen.
pause >nul