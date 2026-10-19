' Hermes Agent Gateway - Messaging Platform Integration
' Umgebung wie gehabt; Start aber ueber cmd -> python.exe statt pythonw:
' pythonw starb im Update-Completion-Tail (03:10-03:30 drei Fehlschlaege,
' darunter 2,5 h Waechter-Neustart-Schleife), python.exe startet durch.
' Der CMD-Weg setzt die Umgebung selbst (setlocal) und startet python.exe
' fensterlos per start /b. Fensterstil 0 mit cmd.exe ist belegt startfaehig.
Option Explicit
Dim sh
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes"
sh.Run "cmd.exe /c ""C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\gateway-service\gateway-direkt.cmd""", 0, False
