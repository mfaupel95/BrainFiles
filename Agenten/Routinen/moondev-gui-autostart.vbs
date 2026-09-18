' Startet die MoonDev-GUI beim Anmelden ueber den Wrapper moondev-gui.ps1.
' Autostart ohne Admin: der Startup-Ordner des Benutzers braucht keine
' Erhoehung. Der Wrapper erkennt eine schon laufende GUI und tut nichts.
' Eleganter Weg (geplante Aufgabe MaxHirn-MoonDev-GUI) braucht einmalig
' Admin: Agenten\Routinen\moondev-gui-aufgabe.ps1 in erhoehter PowerShell.
Set sh = CreateObject("WScript.Shell")
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\Users\faupe\Documents\BrainFiles\Agenten\Routinen\moondev-gui.ps1""", 0, False