@echo off
rem jevgrep-Aufrufer. Installationsordner = %~dp0 (node_modules mit @dzhng/jevgrep).
rem node MUSS auf dem PATH liegen (Node 22+); der Aufruf braucht kein npm.
setlocal
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js nicht gefunden. Node 22 oder neuer installieren oder in den PATH legen.
  exit /b 9009
)
node "%~dp0node_modules\@dzhng\jevgrep\dist\bin\index.js" %*
exit /b %ERRORLEVEL%