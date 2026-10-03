@echo off
rem Testnet-Laeufe: "omnitrade-laeufe.cmd liste" | "start <name>|alle [--trocken]" - Doppelstart-Schutz je Lauf.
python "%~dp0Agenten\Handel\omnitrade_start.py" %*
