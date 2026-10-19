# Aufgaben ohne Anmeldung laufen lassen (S4U)

Seit 18.10.2026 laufen die 30 MaxHirn-Aufgaben (Handel, Sicherung, Wartung,
Dienste) mit `LogonType S4U` — sie starten auch ohne interaktive Sitzung,
ohne Passwort. Ausloeser war ein Windows-Update-Reboot (16.10. 01:07), nach
dem 2,5 Tage niemand angemeldet war: alle InteractiveToken-Aufgaben wurden an
ihren Zeitpunkten stillschweigend uebersprungen, nur SYSTEM-Aufgaben liefen
weiter (siehe systemdiagnose, Pitfall "Alle taeglichen Aufgaben stehen seit
demselben Zeitpunkt still").

## Vor der Umstellung: Ressourcen-Sichtbarkeit mit Wegwerf-Task beweisen

S4U laedt KEIN Benutzerprofil — ob HKCU-Umgebungsvariablen (OKX-/Kraken-Keys)
und die Laufwerke G:/O:/Q: im S4U-Kontext sichtbar sind, ist nicht
selbstverstaendlich. Erst eine Wegwerf-Task bauen, die genau das prueft, sonst
stellt man den Handel auf einen Kontext um, der die Schluessel nicht findet:

1. Probe-Skript (schreibt NUR LAENGEN, nie Werte):
   `[Environment]::GetEnvironmentVariable('OKX_API_KEY','User') | Measure-Object -Character`
   je Key plus `Test-Path 'G:'/'O:'/'Q:'` — Ausgabe in eine Datei.
2. Aufgabe registrieren mit `New-ScheduledTaskPrincipal -LogonType S4U
   -RunLevel Limited`, Start-ScheduledTask, 8 s warten, Ausgabe lesen,
   Unregister. Geprueft 18.10.2026: Keys (36/36/56 Zeichen) und alle drei
   Laufwerke kommen an — die Umstellung war belegt.

## Umstellung (Admin-Skript, EIN UAC)

Fuer jede Aufgabe: `Export-ScheduledTask` -> XML ->
`<LogonType>InteractiveToken</LogonType>` durch `<LogonType>S4U</LogonType>`
ersetzen -> `Register-ScheduledTask -Xml $neu -Force`. Danach je Aufgabe
`Principal.LogonType` nachmessen (darf nicht leer sein).

NICHT umstellen:

- **GUI-Fenster** (Handelszentrale, MoonDev-GUI) — sie brauchen einen
  Bildschirm, ohne Sitzung starten sie in Session 0 und sind unsichtbar.
- **Der Gateway selbst** (`Hermes_Gateway_2ef9d0b7`) — sein Waechter ist S4U
  und startet ihn ohne Anmeldung neu; ein kaltgestarteter Gateway ohne
  Sitzung ist riskanter als der Waechter-Weg.
- Schon SYSTEM-gestellte Aufgaben (`MaxHirn-Datensortierung`) — anfassen
  wuerde eine funktionierende Konfiguration aendern.

## Wirkung pruefen

- Laufende Prozesse werden durch die Umstellung NICHT beendet (Aenderung
  wirkt erst auf den naechsten Trigger).
- `Get-ScheduledTask | Where Principal.LogonType -eq 'S4U'` listet die
  umgestellten; die 15/30-Minuten-Takte (Dauerlauf, Waechter) schreiben
  weiter.
- Der eigentliche Beweis ist der naechste Neustart OHNE Anmeldung:
  ~35 min warten, dann `dauerlauf.log` auf frische Zyklen pruefen — erst dann
  ist belegt, dass der Betrieb wirklich ohne Sitzung traegt.
