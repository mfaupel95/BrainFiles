---
id: 20261013-handel-agenten-befund
title: 'Handel-Agenten: Befund 13.10.2026'
tags: [handel]
created: 2026-10-13
updated: 2026-10-13
related: ['20260902-handelsregeln', '20260830-routinen', '20260830-hardware']
summary: 'Dauerlauf-Überwachung wieder vollständig (alle vier Wächter-Aufgaben Ready, drei Stufen laufen auf Papier), Backtest-Varianten mit Hausfunktionen verglichen und bewusst stehen gelassen, 5,4 GB redundante Hermes-Datenbank-Kopien entfernt.'
---

# Handel-Agenten: Befund 13.10.2026

Prüfung des Handelssystems (Spuren, Dauerlauf, Wächter, Plattenplatz) am
13.10.2026. Alle Zahlen gemessen, keine Vermutung. Kein Live-Handel wurde
angetastet; nur Laufende wurde gelesen und eine begrenzte Menge an
dokumentierten Sicherungen entfernt.

## 1. Dauerlauf: drei Stufen laufen, alle vier Wächter scharf

```
laeuft  --risiko niedrig   auf Papier
laeuft  --risiko mittel    auf Papier (nachmittags neu gestartet)
laeuft  --risiko hoch      auf Papier
```

Vier geplante Aufgaben in der Windows-Aufgabenplanung, alle **Ready**
(`Get-ScheduledTask` am 13.10.2026 nachmittags):

| Aufgabe | Zustand |
|---|---|
| `MaxHirn-Handel-Dauerlauf` | Ready |
| `MaxHirn-Handel-Dauerlauf-Waechter` | Ready |
| `MaxHirn-Handel-Dauerlauf-Mittel-Waechter` | Ready |
| `MaxHirn-Handel-Dauerlauf-Hoch-Waechter` | Ready |

Alle drei Stufen laufen auf Papier: kein offenes Freigabefenster, und die
Stufenläufe (mittel/hoch) sind im Code ohnehin fest auf Papier verdrahtet.
Systemlast zum Zeitpunkt der Reaktivierung: CPU 37 %, ~20 GB RAM frei von
65 GB — die Reaktivierung war also nicht leistungsintensiv.

Der Basislauf (Stufe `niedrig`) führt die Bücher `handelsjournal.csv` und
`zustand.json` — die Aufzeichnung, die zählt. Genau gegen einen Ausfall
dieser Bücher wurden die Wächter am 29.09.2026 nachgerüstet, weil nach
einem Kernel-Power-41-Neustart ohne Anmeldung Basis und Stufen still lagen
(s. [[20260830-routinen]]).

Am Morgen des 13.10. waren drei der vier Aufgaben noch `Disabled` und die
Mittel-Stufe tot (seit 12.10. 17:07). Die Mittel-Abschaltung war dokumentiert
erlaubt (`Disable-ScheduledTask -TaskName
MaxHirn-Handel-Dauerlauf-Mittel-Waechter`, [[20260902-handelsregeln]]); die
Basis-Abschaltung nicht — sie wurde im Laufe des Tages wieder aufgehoben,
und alle drei Stufen sind neu auf Papier gestartet worden.

## 2. Backtest-Varianten: gesichert und bewusst stehen gelassen

63 Variantenordner unter `Agenten/Handel/daten/backtest/<spur>/<lauf>/`
wurden mit den Hausfunktionen verglichen
(`auswertung_alle.runden_indikator()` + `kennzahlen()`), nicht mit einer
eigene PnL-Formel. Sicherung:
`Agenten/Handel/BEFUND-backtest-varianten-20261013.md` und
`Agenten/Handel/daten/backtest/VARIANTEN-VERGLEICH-20261013.json`.

**Die Ordner werden nicht aufgeräumt.** Sie sind die Messgrundlage von
`auswertung_alle.backtest_stand()`, die im Leitstand-Reiter *Backtest* den
Lauf mit den meisten Journal-Zeilen auswählt. Verschieben erzeugt dort
`kein Lauf`.

Ergebnisse der Parameter-Suche: `squeeze/optimierung.json` listet 12
Kandidaten, `ueberlebt: []` — kein Kandidat besteht die 4-Fenster-Prüfung.
`wavetrend/optimierung.json` ebenso. Die Spuren `squeeze` und `swap` sind
deshalb seit 10.10.2026 aus dem Dauerlauf. Positive Einzelfenster
(`squeeze_0b7345f2` +1028,67 USD, `squeeze_94d8d395` +1482,66 USD bei 16–75
Runden) sind kein Fund — dieselbe 4-Fenster-Prüfung verwirft sie.

## 3. Plattenplatz: 5,4 GB entfernt

```
C:  1,2 GB frei  ->  81,3 GB frei   (13.10.2026)
```
Entfernt wurden exakt sieben dokumentierte Sicherungen derselben
Hermes-Datenbank in `Agenten/_Backups/` (5111,0 MB, MD5 je Datei
vormals notiert). Die laufende `Agenten/Hermes/state.db` (830,1 MB) und
die jüngsten Snapshots sind unberührt.

Offen: in `Agenten/_Backups/` liegen weitere, ältere Kopien derselben
Datenbank (2026-08-28 bis 2026-09-25, zusammen ~1,7 GB). Sie sind nicht
Teil der Aufgewänsung und bleiben liegen.

## 4. Was beim Aufräumen der Varianten schiefging (Lektion)

Ein erster Eigenbau zur Auswertung lag Faktor ~1000 daneben, weil
`einsatz_usd` bei skalierten Positionen **kumulativ** ist. Erst die
Hausfunktion ergab die plausiblen Zahlen. Eine eigene Formel wäre als
zweite Wahrheit im Leitstand gelandet — die Regel dazu steht in der
gemeinsamen Stilquelle der Repo-Bots.

Ebenso: Zahlen in `wachen.json` sind in `_..._vermerk`-Feldern
begründet. Ein „Harmonisieren" aus einer Tabelle bricht dokumentierte
Absicht — gemessen an `omnitrade_futures` (90000 USD = Nominalwert
**eines** BTC-Kontrakts) und `moondev_marktlage` (9,0 USD = Anordnung
Max vom 22.09.2026).
