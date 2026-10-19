@echo off
rem Startet den OKX Agent Trade Kit (MCP, stdio) ausschliesslich im DEMO-Modus.
rem Die Demo-Zugaenge stammen aus OKX_DEMO_API_KEY / _SECRET / _PASSPHRASE (Benutzervariablen).
rem Sie werden NUR in diesem Prozess auf die Namen abgebildet, die das Werkzeug liest;
rem der Live-Schluessel (OKX_API_KEY u. a.) wird dadurch ueberschrieben und nie benutzt.
rem Keine Schluessel in Dateien. Kein --live. Zusatzargumente (z. B. --read-only) gehen durch.
setlocal
if "%OKX_DEMO_API_KEY%"=="" goto fehlt
if "%OKX_DEMO_API_SECRET%"=="" goto fehlt
if "%OKX_DEMO_API_PASSPHRASE%"=="" goto fehlt
set "OKX_API_KEY=%OKX_DEMO_API_KEY%"
set "OKX_SECRET_KEY=%OKX_DEMO_API_SECRET%"
set "OKX_PASSPHRASE=%OKX_DEMO_API_PASSPHRASE%"
set "OKX_API_SECRET=%OKX_DEMO_API_SECRET%"
rem Werkstatt liegt auf O: (Junction fehlt auf diesem Rechner, 10.10.2026): erst relativ, dann O:.
set "KIT=%~dp0..\..\..\Werkstatt\agent-trade-kit\packages\mcp\dist\index.js"
if not exist "%KIT%" set "KIT=O:\Werkstatt\agent-trade-kit\packages\mcp\dist\index.js"
node "%KIT%" --demo --site eea --modules market,spot,swap,account %*
exit /b %errorlevel%
:fehlt
echo OKX_DEMO_API_KEY/_SECRET/_PASSPHRASE fehlen - Abbruch. 1>&2
exit /b 2
