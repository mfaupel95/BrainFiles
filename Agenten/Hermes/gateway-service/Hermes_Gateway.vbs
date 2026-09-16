' Hermes Agent Gateway - ABGELOEST am 16.09.2026, startet nichts mehr.
'
' Grund: Dieses Skript zeigte auf C:\Hermes (Altanlage, Stand 10.09., 2109
' Commits alt). Der Gateway laeuft aus Agenten\Hermes\hermes-agent, gestartet
' von Hermes_Gateway_2ef9d0b7.vbs (Task Hermes_Gateway_2ef9d0b7).
' Zwei Gateway-Starts bei der Anmeldung waeren ein zweiter Prozess auf
' denselben Sitzungen.
'
' Der Task 'Hermes_Gateway' ruft diese Datei weiter auf, weil er als Admin
' registriert ist und nur mit Admin-Rechten deaktiviert werden kann:
'     Disable-ScheduledTask -TaskName 'Hermes_Gateway'
' Bis dahin endet der Aufruf hier - absichtlich ohne Wirkung.
Option Explicit
WScript.Quit 0
