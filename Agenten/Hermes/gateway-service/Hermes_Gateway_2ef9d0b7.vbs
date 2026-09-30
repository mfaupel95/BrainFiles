' Hermes Agent Gateway - Messaging Platform Integration
Option Explicit
Dim sh, env, existing_pp
Set sh = CreateObject("WScript.Shell")
Set env = sh.Environment("PROCESS")
env.Item("HERMES_HOME") = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes"
env.Item("PYTHONIOENCODING") = "utf-8"
env.Item("HERMES_GATEWAY_DETACHED") = "1"
env.Item("HERMES_SUPERVISED_CHILD") = "1"
env.Item("VIRTUAL_ENV") = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\tools"
existing_pp = env.Item("PYTHONPATH")
If Len(existing_pp) > 0 Then
  env.Item("PYTHONPATH") = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\hermes-agent;" & existing_pp
Else
  env.Item("PYTHONPATH") = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\hermes-agent"
End If
sh.CurrentDirectory = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes"
' Befund 30.09.2026 (gemessen): WScript.Shell.Run mit Fensterstil 0 startet
' KONSOLEN-Programme NICHT - der Prozess entsteht gar nicht, ohne Fehlermeldung.
' pythonw.exe ist ein GUI-Programm und laeuft mit Stil 0 versteckt. Darum hier
' pythonw.exe statt python.exe. Wer den Start von Hand nachsehen will:
'   python.exe -m hermes_cli.main gateway run   (aus dem Ordner Agenten\Hermes)
sh.Run "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\tools\python-3.14.7+20260901-win32-x64\pythonw.exe -m hermes_cli.main gateway run", 0, False
