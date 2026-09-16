' Hermes Agent Dashboard - Local Web UI (auto-start)
' Umgestellt am 16.09.2026: zeigte auf C:\Hermes (Altanlage). Jetzt derselbe
' Baum wie der Gateway (hermes-agent) - zwei Installationen mit verschiedenen
' Staenden waren die Quelle fuer "laeuft bei mir anders".
Option Explicit
Dim sh, env
Set sh = CreateObject("WScript.Shell")
Set env = sh.Environment("PROCESS")
env.Item("HERMES_HOME") = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes"
env.Item("PYTHONIOENCODING") = "utf-8"
env.Item("VIRTUAL_ENV") = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\hermes-agent\venv"
env.Item("PYTHONPATH") = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\hermes-agent"
sh.CurrentDirectory = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes"
sh.Run "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\hermes-agent\venv\Scripts\python.exe -m hermes_cli.main dashboard --no-open --skip-build --host 127.0.0.1 --port 9119", 0, False
