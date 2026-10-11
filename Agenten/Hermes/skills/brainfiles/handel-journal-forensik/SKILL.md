---
name: handel-journal-forensik
description: "Phantom-Zeilen im Handelsjournal finden und bereinigen."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Handel, Journal, Forensik, Kill-Switch, Boersenabgleich, BrainFiles]
    related_skills: [befund-zu-fix, handel-spuren, trugschluesse, messwerkzeug-gegenprobe]
---

# Handel-Journal-Forensik: Phantom-Zeilen finden, belegen, bereinigen

Diagnose fuer das Symptom **"eine Spur macht nur Verlust / Positionen werden
geoeffnet und sofort wieder geschlossen"**. Der uebliche Kern: falsche
Journal-Zahlen (Phantom-Zeilen, `nominal_usd == margin_usd`) blahen die
kumulierte Kapitalkurve auf, der Kill-Switch misst seinen Ruecklauf gegen den
aufgeblahten Hoechststand und schliesst echte GEWINNER - die Spur sieht nach
Verlust aus, obwohl sie nur falsch bucht. Der Workflow ist rein lesend bis zum
eigenen Schreibschritt, stellt keine Order, fasst keine Stops an und braucht
keinen Live-Eingriff.

Wie er sich von den Nachbarn abgrenzt: `befund-zu-fix` ist der generische
Symptom->Fix-Weg mit Gegenprobe; dieser Skill ist die handelsspezifische
Journal-Forensik (FIFO-Paarung, Kapitalkurve, Boersenzeugen, Geister-Regel).
`handel-spuren` bindet Spuren an; hier wird ein bestehendes Buch geprueft.

## When to Use

- "Irgendwas macht nur Verlust, Positionen werden geoeffnet und direkt wieder
  geschlossen" (OKX/Boersen-Spur)
- ein Kill-Switch oder Ratsche feuert auf Gewinnern
- ein Ruecklauf/Hoechststand im Bericht erscheint absurd hoch
- Verdacht auf Geister-Positionen: Journal zeigt Positionen, die Boerse nicht
- nach einem Boersen-/Handgriff-Abgleich verschwinden Buchpositionen
- Vor einer Live-Empfehlung kapitalrelevanter Zahlen (excess, kill, ratsche)
- "Journal leert sich / weniger Runden" - die GEGENrichtung: erst pruefen, ob
  es die dokumentierte Bereinigung ist, bevor Datenverlust angenommen wird

## Prerequisites

- Spurordner mit eigenem Python: `Agenten/Handel/xperp` mit
  `../scanner/.venv/Scripts/python.exe` (aus dem Spurordner).
- Lesenden Boersenzugang der Spur (`okxf` bei xperp liest OKX_*-Schluessel
  ueber Registry-Rueckfall; Host ist eea.okx.com).
- Sicherungs-/Spiegelungsziel Q:\Handel_Journal\<spur> (Bedingung 4).
- Das Journal ist eine LAUFEND geschriebene Datei - der Dauerlauf haengt
  Zeilen an, waehrend man liest/schreibt.

## How to Run

1. Verlust-Ranking aus der FIFO-Paarung (`runden_aus_journal`) ziehen
2. Phantom-Fingerabdruck suchen (`nominal_usd == margin_usd` bei schliessen)
3. Boersenzeugen holen (realisedPnl aus positions-history) - je Zeile
4. Zeilen auf den belegten Wert ziehen (Boersenwert ODER neutral), `.bak`,
   Diff gegen Sicherung, Bedingung-4-Spiegelung nachziehen
5. Kurve neu rechnen: Kill muss aufhoeren, Hoechststand real werden
6. Code-Regel pruefen/umsetzen (Geister nur mit Beleg ausbuchen), Tests
   umstellen, Suite fahren, committen

Das fertige Scan-Skript liegt unter `scripts/phantom_scan.py` (Vorschau,
schreibt NICHTS) - aufrufen statt nachbauen.

## Quick Reference

```bash
# Verlust-Ranking (gv je Runde, groesste zuerst)
PY=../scanner/.venv/Scripts/python.exe
$PY -c "import sys; sys.path.insert(0,'.'); import wachen_xperp as wx;\
import json; w=json.load(open('wachen.json')); z=json.load(open('zustand.json'));\
l=wx.lage(w,'handelsjournal.csv',z); print('Peak', l['hoechststand_usd'],\
'Ruecklauf', l['ruecklauf_usd'], 'Kill', l['kill'])"

# Phantom-Scan (Vorschau, liest nur)
$PY scripts/phantom_scan.py --spur xperp --boerse

# Boersenzeuge der Spur
$PY -c "import sys; sys.path.insert(0,'.'); import okxf;\
print(okxf.geschlossene_position('STRK-USD_UM_XPERP-310919', 1728_000_000_000))"

# Suite (aus dem xperp-Ordner)
$PY -m unittest discover -s tests
```

## Procedure

### 1. Verlust-Ranking: die FIFO-Paarung ist die Wahrheit

Nicht Journalzeilen selbst zaehlen (1181 Ausstieg-Zeilen sind 579 Runden).
Je Spur die HAUS-paarung nehmen:

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel/xperp && \
  ../scanner/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'.')
import wachen_xperp as wx
runden = wx.runden_aus_journal('handelsjournal.csv')
for r in sorted(runden, key=lambda x: -abs(x['gv']))[:15]:
    print(r['zeit'][:16], r['inst'][:22], round(r['gv'],2), r['grund'])"
```

`gv` = Schliess-Margin minus Einstiegs-Einsatz der FIFO-Paarung (je
Instrument, aelteste zuerst). Ausreisser > einige hundert USD bei einer
Papier-/Live-Spur mit 5-50 USD Einsatz sind Phantom-Runden.

### 2. Phantom-Fingerabdruck: nominal == margin bei schliessen

Fingerabdruck des Alt-Bugs (vor dem Fix): **`nominal_usd == margin_usd`** in
einer schliessen-/verkauf_von_hand-/kill_switch-Zeile. Der alte Code schrieb
Preis x Menge in BEIDE Felder - eine 201.900,66-USD-Zeile statt ~193 USD.

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel/xperp && \
  ../scanner/.venv/Scripts/python.exe scripts/phantom_scan.py --spur xperp
```

Das Skript zeigt je Verdachtszeile: Zeit, Instrument, nominal, margin und die
gepaarte Eroeffnen-Zeile (Einsatz). **NICHT alle Zeilen mit dem Merkmal sind
Phantome, die eine Runde bilden** - manche haben keine offene FIFO-Paarung
mehr und fallen aus der Kurve heraus; sie tragen den Alt-Bug, sind aber
wirkungslos (liegen lassen oder dokumentieren).

### 3. Boersenzeugen holen: eine Zahl pro Zeile

Fuer jede Phantom-Zeile fragt die Spur ihren Boersen-Weg nach positions-history
(`okxf.geschlossene_position(inst, seit_ms)` bei xperp). Zurueck kommt
`realizedPnl` + `closeTotalPos`. Regeln:

- Beleg gefunden: ehrlicher Wert = Einsatz + realizedPnl (anteilig, wenn die
  Boerse mehr Kontrakte fuehrt als das Buch)
- **Kein Beleg (None/Netzfehler): NICHT raten** - neutral: Einsatz zurueck.
  Ein Börsenwert, der zu einer anderen (kuerzeren) Position gehoert, ist kein
  Zeuge fuer diese Zeile.
- Vorher pruefen, ob eine naehere Stufe den Verkauf schon bezeugt hat
  (`buche_verkaeufe_aus_boerse` geht VOR der Geisterpruefung).

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel/xperp && \
  ../scanner/.venv/Scripts/python.exe scripts/phantom_scan.py --spur xperp --boerse
```

### 3b. Position verschwand OHNE Journalzeile: die Boersen-History ist der Zeuge

Gegenrichtung zum Geist: eine Position ist aus dem Buch weg, aber das Journal
hat keinen Ausstieg - und die Spur meldet WEITER (z.B. SICHERHEITSLUECKE,
weil sie den Stop nicht setzen kann), weil sie den Verkauf nicht kennt. Das
ist der Hinweis, dass der Verkauf von aussen kam (Hand in der Boersen-App
oder anderer Prozess), nicht von der Spur. Der Zeuge ist die Boersen-History
(`/fills` bei Kraken-Futures), nicht das Buch.

```bash
# Kraken-Futures: /fills OHNE Query-Parameter (mit ?lastFillTime= -> authenticationError)
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel/nautilus_kraken && \
  python -c "import kraken_futures as kf; d=kf._roh('/fills');\
fl=[f for f in d.get('fills',[]) if f.get('symbol')=='PF_NEARUSD'];\
[print(f.get('fillTime'),f.get('side'),f.get('size'),f.get('price'),f.get('realized_pnl')) for f in fl]"
```

Fills tragen `symbol` (nicht `instrument`). Der Verkauf zeigt Zeit, Menge,
Preis und `realized_pnl` - damit ist der fehlende Ausstieg belegt und der
Verlust (z.B. -9,63 USD) kann als `buchbereinigung` nachgebucht werden.

### 4. Kurve neu rechnen, bevor irgendetwas geschrieben wird

Der Kill misst `ruecklauf = hoechststand - kum` auf der **realisierten
Kurve**. Phantom-Runden blahen hoechststand auf; jeder kleine echte Ruecklauf
>= Decke feuert dann. Deshalb vor dem Umbau zeigen:

```bash
../scanner/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'.')
import wachen_xperp as wx, json
l = wx.lage(json.load(open('wachen.json')),'handelsjournal.csv',json.load(open('zustand.json')))
print('Peak', l['hoechststand_usd'], 'Ruecklauf', l['ruecklauf_usd'], 'Kill', l['kill'], 'Faktor', l['groessenfaktor'])"
```

### 5. Bereinigen: schreiben mit Sicherung + Diff + Spiegelung

1. Sicherung: `cp handelsjournal.csv handelsjournal.bak-JJJJMMTT.csv`
2. Zeilen byte-genau ersetzen (csv-Modul, `newline=''`; Spalten festhalten)
3. **Diff gegen die Sicherung**: nur die gewollten Zeilen duerfen sich
   aendern; Zeilenzahl darf nicht springen (der Dauerlauf haengt an)
4. Kurve erneut rechnen - Kill False, Peak real (Ziel der Aktion)
5. **Bedingung 4 sofort nachziehen**: `wx.spiegele_journal([...],
   w['journal_zweitziel'])` bzw. die Spiegel-Funktion der Spur, dann sha256
   gegen Q: - der lokale `.bak` ist KEIN Zeuge (der Dauerlauf kann ihn
   mitnehmen), die Q:-Kopie ist es.

### 6. Die Code-Regel: Geister nur mit Boersenbeleg ausbuchen

Regel (Max 09.10.2026, Commit c509d766): `bueche_geister_aus` bucht eine
Live-Position, die an der Boerse fehlt, **nur noch** aus, wenn `_geist_erloes`
die Quelle `"boerse"` liefert (realizedPnl vorhanden). Fehlt der Beleg:
Position bleibt als **UNKLAR** im Buch stehen, wird gemeldet, KEINE
Journalzeile, KEIN Storno der offenen Order. Der Anlass: am 05.10.2026 hat
die neutrale Sofort-Ausbuchung sechs echte Live-Positionen geloescht.

Pruefen, ob eine Spur diese Regel schon hat:

```bash
git --no-pager grep -n "Regel Max 09.10.2026\|UNKLAR im Buch" -- Agenten/Handel/xperp/handeln.py
```

### 7. Tests umstellen: die alten Tests frieren das GEFAEFRLICHE Verhalten ein

Die Tests, die die sofortige Ausbuchung erwarteten
(`test_ausbuchung_ohne_satz_schreibt_den_einsatz_zurueck` u.ae.), muessen auf
die neue Regel umgestellt werden - nicht weicher, sondern auf die gemessene
Regel (Position bleibt ohne Beleg, Ausbuchung nur mit Beleg). Routine:

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel/xperp && \
  ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests
```

Danach die volle Spur-Suite (hier 184) und Bedingung 4 (Q: byte-gleich).

## Pitfalls

- **Der Kill misst gegen den kumulierten realisierten Hoechststand, nicht
  gegen die Position.** Phantom-Runden blahen den Peak auf - bereits der
  naechste kleine echte Ruecklauf feuert. Deckel erhoehen daempft nur; die
  Wurzel sind die Phantom-Zeilen.
- **`nominal == margin` ist der Fingerabdruck, nicht jede Zeile ist eine
  Runde.** Manche haben keine offene FIFO-Paarung und wirken nicht auf die
  Kurve; sie tragen den Alt-Bug aber weiter. Nicht blind alle korrigieren.
- **Ein Boersenwert gehoert zur richtigen Zeile.** Eine kuerzere Position mit
  realizedPnl bezeugt NUR ihre eigene Schliessung - wer sie auf eine andere
  Zeile projiziert, erfindet ein Ergebnis.
- **Eine Position, die aus dem Buch verschwindet ohne Journalzeile, aber an
  der Boerse verkauft wurde, ist ein Buchhaltungs-Geist - und die Spur meldet
  weiter, weil sie den Verkauf nicht kennt.** Wenn eine Spur eine Position
  weiter ueberwacht (z.B. SICHERHEITSLUECKE), die an der Boerse laengst weg
  ist, kam der Verkauf von aussen (Hand/anderer Prozess), nicht von der Spur.
  Der Zeuge ist die Boersen-History (`/fills`), nicht das Buch. Es gibt
  keinen Code-Weg, der eine Live-Position ohne Journalzeile entfernt -
  verschwindet sie trotzdem, wurde sie manuell entfernt oder durch einen
  unerkannten Prozess.
- **Kraken-Futures `/fills` schlaegt mit Query-Parameter fehl.**
  `?lastFillTime=` (und jeder Query-String) in der Signatur ->
  authenticationError, obwohl der Schluessel gueltig ist. Ohne Parameter
  liefert `/fills` die letzten 100 Fills (Zeitraum ~1 Monat). `/orders` ist
  404, `/accountlogcsv` 401 (keine Berechtigung), `/orders/status` ohne
  Parameter = nur offene Orders. Fills tragen `symbol`, nicht `instrument`.
- **Die Hausfunktion nutzen statt die Signatur nachzubauen.** Ein manuell
  nachgebauter signierter Aufruf (eigene HMAC-Konstruktion) kann
  authenticationError liefern, waehrend der Haus-Weg (`kraken_futures.py`)
  denselben Schluessel korrekt signiert - erst den Haus-Weg pruefen, bevor
  ein Schluessel fuer tot erklaert wird.
- **Der lokale `.bak` ist kein Zeuge.** Der Dauerlauf schreibt das Journal
  weiter; Bedingung-4-Kopie (Q:) sofort nachziehen und gegen DIESE
  verifizieren.
- **Tests, die das alte Verhalten einfrieren, sind Teil des Befunds.**
  `test_ausbuchung_ohne_satz...` erwartete die gefaehrliche Sofort-Ausbuchung
  und musste auf die Regel umgestellt werden - ein Test, der eine
  Falschaussage festschreibt, ist eine zweite falsche Wahrheit.
- **Waehrend man das Journal schreibt, laeuft ein Zyklus.** Vor dem Schreiben
  die Zeilenzahl merken, nach dem Schreiben gegen die Sicherung diffen. Ein
  Zwischen-Zyklus haengt Zeilen an - kein Fehler.
- **Erst bezeugen, dann pruefen:** `buche_verkaeufe_aus_boerse` (echte
  Verkaeufe mit fills) muss VOR der Geisterpruefung laufen, sonst sieht die
  Geisterpruefung eine Position, die an der Boerse fehlt, und bucht sie
  neutral aus.
- **Datum/Uhrzeit:** Die Session kann ueber Tage laufen - vor einer
  Zustandsaussage die Hostzeit pruefen (`Get-Date`), nicht den
  Sitzungsbeginn.
- **Eine buchbereinigung mit ECHTEM Verlust ist kein neutraler Geist.** Das
  vorhandene Werkzeug (z.B. `omniquant/buch_bereinigen.py`) bucht NEUTRAL
  (Wert = Einsatz), weil es fuer Geister gebaut wurde - Positionen, die an der
  Boerse NIE existierten. Eine Position, die an der Boerse WIRKLICH verkauft
  wurde (realized_pnl aus `/fills`), bucht den ECHTEN Verlust: `wert_usd =
  einsatz - verlust` in der Journalzeile UND `verluste_usd += verlust` in
  zustand.json. Wer das neutrale Werkzeug auf einen echten Verkauf anwendet,
  versteckt den Verlust vor der Kapitalkurve. Erst belegen (Boersen-History),
  dann entscheiden: neutral (Geist) oder echter Verlust (real verkauft).
- **Eine Spur mit 0 Runden in der Auswertung, aber Eintraegen im Journal, hat
  ein Aktionsnamen-Problem, kein Datenproblem.** `runden_fuer()` paart je
  Rechenweg feste Aktionsnamen (kauf/verkauf, eroeffnen/schliessen,
  EINSTIEG/AUSSTIEG). Schreibt eine Spur andere Namen als ihr Rechenweg
  erwartet (z.B. omniquant in BOT_SPUREN, aber EINSTIEG/AUSSTIEG statt
  kauf/verkauf), meldet die Auswertung still 0 Runden - kein Fehler, keine
  Meldung. Diagnose: `Counter(r.get('aktion') for r in zeilen)` gegen die
  Aktionsmengen des Rechenwegs halten; passt nichts, bekommt die Spur einen
  eigenen Rechenweg statt in den generischen zu fallen.
- **"Journal leert sich" ist meist die dokumentierte Bereinigung, kein
  Datenverlust.** `spur_buch.journal()` schreibt ausschliesslich mit `"a"`
  (append) - ein Journal leert sich nie von selbst. Ein "leeres" Journal
  (nur Kopfzeile, 80-254 B) ist eine Spur, die nie gehandelt hat, kein
  Defekt. "Weniger Runden" in der Auswertung heisst: Phantom-Zeilen wurden
  in `handelsjournal.verworfen-*.csv` verschoben (dokumentierte Forensik).
  Diagnose-Reihenfolge, bevor ein Befund gemeldet wird: (1) existieren
  `.verworfen-*.csv`-Dateien? (2) schreibt die Spur das Journal nur mit
  `"a"`? (3) ist die Q:-Spiegelung byte-gleich? Erst wenn alle drei nein
  sind, ist es ein echter Verlust. Die einzigen `"w"`-Schreiber sind
  `replay.py` (Backtest-Ordner) und Tests (Temp-Ordner) - nie echte Spuren.

## Verification

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel/xperp && \
  ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests | tail -2
python -c "import sys,hashlib;sys.path.insert(0,'.');import wachen_xperp as wx,json;\
l=wx.lage(json.load(open('wachen.json')),'handelsjournal.csv',json.load(open('zustand.json')));\
print('Kill', l['kill'], 'Peak', round(l['hoechststand_usd'],2))"
```

Erwartet: `OK` ueber der Suite, `Kill False` und ein Peak, der zur
Einsatzgroesse der Spur passt. Dazu Bedingung 4: Journal und zustand.json
byte-gleich zu Q:\Handel_Journal\<spur> (sha256). Diese Sitzung: Peak 690,19
statt 639.977, 0 kill_switch seit der Bereinigung, 184 Tests gruen.
