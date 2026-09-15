# Ereignis-IDs, die im Systemprotokoll zaehlen

Quelle: `Get-WinEvent -FilterHashtable @{LogName='System'; ...}`.
Level 1 = Kritisch, 2 = Fehler, 3 = Warnung.

| ID | Anbieter | Bedeutung | Was sie wirklich heisst |
|---|---|---|---|
| 41 | Microsoft-Windows-Kernel-Power | Unsauberer Abschuss | Es wurde nicht heruntergefahren. `Properties[15]` = BugcheckCode: **0/False = kein Bluescreen**, also Stromausfall, Reset oder Haenger. `Properties[11]` = PowerButton-Zaehler (kumulativ, nicht die Uhrzeit). |
| 36 | Volsnap | Schattenkopie abgebrochen | „Schattenkopiespeicher konnte nicht auf ein benutzerdefiniertes Limit vergroessert werden“ → Volume zu voll, Wiederherstellungspunkte sterben. Harte Dringlichkeit fuer `C:`. |
| 11 | disk | Controller-Fehler | Der Treiber hat einen Fehler am Datentraeger gemeldet. Zusammen mit einem `UASPStor`-Reset auf einem USB-Wandler: das Geraet ist weggefallen, nicht nur langsam. |
| 153 | disk | Anforderung wiederholt | IO-Retry-Warnung. **Nur bei LBA 0x0** deutet sie auf einen elektrisch toten Datentraeger; an anderen Adressen ist sie ein Retry unter Last. |
| 7000 / 7023 / 7031 / 7034 | Service Control Manager | Dienst startet nicht / endete mit Fehler / wurde unerwartet beendet | Einzeln harmlos. **Derselbe Dienst wiederholt** ueber Tage ist ein echter Befund. |
| 7043 | Service Control Manager | Shutdown fehlgeschlagen | Ein Dienst hat das Preshutdown-Kommando nicht beantwortet — verzoegert das Herunterfahren, mehr nicht. |
| 10010 | DistributedCOM | Server-DCOM-Registrierung abgelaufen | Massenhaft im Normalbetrieb, meist Rauschen. |
| 20 | WindowsUpdateClient | Updatevorgang | Zustandsmeldung, kein Fehler. |

## Leseregeln

- **Meldungen kuerzen mit `[Math]::Min(N, $_.Message.Length)`** — sonst reisst
  `Substring` bei kurzen Meldungen ab.
- **Zuerst die letzten 7 Tage, Level 1 und 2.** Erst wenn dort nichts steht,
  auf Warnungen (Level 3) erweitern.
- **Ein einzelnes Ereignis ist kein Befund.** Erst die Wiederholung ueber Tage
  oder die Kopplung an ein Symptom macht daraus eine Ursache.
- **Disk- und Speicherfehler zusammen lesen:** `disk` 11/153 plus `Volsnap` 36
  plus der freie Platz auf demselben Volume ergeben eine belastbare Aussage;
  jede Zahl allein nicht.
- **Kernel-Power 41 mit Bugcheck 0 nie als Bluescreen berichten.** Ohne Dump
  und ohne WHEA-Eintrag ist die Ursache ausserhalb des Betriebssystems zu
  suchen (Netzteil, Steckdose, Lastspitze) — das ist eine Hardware-Aussage und
  gehoert so in den Bericht.
