# Spur 4 — ORB Index-CFD (OANDA): Design

Stand: 2026-09-07. Diese Datei ist die Spec vor dem Bau. Nach dem Bau tritt
`README.md` an ihre Stelle (wie bei `kraken/`), diese bleibt als Beleg der
Entwurfsentscheidungen liegen.

## Anlass

Max hat eine „Opening Range Breakout"-Strategie gehört (Video-Ersteller
behauptet **81 % Trefferquote**, profitabel, selbst codiert und
zurückgerechnet). Max hat sie **nicht** selbst geprüft. Auftrag: einen
Handelsagenten daraus bauen — Backtest-Prüfung und Papierhandel-Gerüst
**parallel**, Live-Schalter aus, bis Backtest **und** 6 Wochen Papier bestehen.

Die Strategie ist session-basiert (erste zwei 15-Min-Kerzen nach Eröffnung) und
nennt einen festen Punkt-Take-Profit — ein Großindex-Konzept. Die bestehenden
Spuren tragen das nicht: Spur 2 (OKX-XPERP) hat nur Einzelaktien + 4 Rohstoffe,
Spur 3 (Kraken) nur Krypto-Spot ohne Short. Deshalb eine **neue vierte bewachte
Spur** an einer Börse mit Index-CFDs. Gewählt: **OANDA v20** (Bearer-Token,
echtes Practice-Environment als Papierphase, mehrjährige M15-Historie über
dieselbe API, passt ins stdlib-Muster von `kraken.py`).

## Die Strategie, exakt

| Regel | Festlegung |
|---|---|
| Eröffnung | DE30 09:00 Europe/Berlin · US30/NAS100 15:30 Europe/Berlin (DST-fest über `zoneinfo`, je Handelstag in Börsen-Lokalzeit gerechnet) |
| Opening Range | die ersten **zwei abgeschlossenen** M15-Kerzen (`complete:true`) ab Eröffnung. `hoch = max(H1,H2)`, `tief = min(T1,T2)` |
| Einstieg | erste folgende M15-Kerze **derselben Session**, die über `hoch` schließt → Long; unter `tief` schließt → Short. **Ein** Trade pro Session, keine Wiedereinstiege |
| Stop | Gegenseite der Range (Long → `tief`, Short → `hoch`). Nicht abschaltbar |
| Take-Profit | `ziel_modus` in `wachen.json`: `punkte` (wörtlich N Indexpunkte, je Instrument) **oder** `r_vielfaches` (TP = `k` × Range-Höhe). Startwerte aus dem Backtest |
| Zwangsschluss | zum Cash-Close des Basiswerts. Kein Halten über Nacht |
| letzter Einstieg | `letzter_einstieg_min_vor_schluss` — kein neuer Einstieg in den letzten N Minuten der Session |
| Positionsgröße | XPERP-Regel „Hebel ist Ergebnis, nicht Eingabe": `positionswert = risiko_pro_trade / stop_abstand`, `stop_abstand` = Range-Höhe. Hebel fällt heraus, gedeckelt durch `hebel_deckel` |

Mehrdeutigkeit im Backtest (M15 löst nicht auf, ob Hoch oder Tief zuerst kam):
Session, in der die Kerze **Stop und TP zugleich** berührt → als **Stop**
gezählt (konservativ, „am Tief prüfen, nicht am Schluss"). Anzahl wird gemeldet.

## Ordnerinhalt

```
Agenten/Handel/orb/
  wachen.json          Grenzen — einzige Wahrheit. Gelesen, nie geschrieben,
                       ausser handel_erlaubt true->false (wachen_orb.py)
  oanda.py             API: M15-Kerzen, Preise, Instrumentdetails, signierte
                       Orders. stdlib urllib, ein Bearer-Header. Practice- und
                       Live-Host aus Konfig/Env, nie hartkodiert
  session.py           Eroeffnungszeit + DST + Zwangsschluss + letzter Einstieg
                       je Instrument
  backtest.py          Pruef-Mechanik ueber DE30/US30/NAS100
  handeln.py           Zyklus: Ausstiege zuerst, dann Einstieg, Journal, Zustand
  wachen_orb.py        Bedingungen dieser Spur; ruft ../scanner/wachen_pruefung.py
                       fuer die waehrungsneutrale Rechnung
  daten/*.json         zwischengespeicherte M15-Kerzen (Backtest-Cache)
  handelsjournal.csv   jede Aktion, Spread in den Betraegen
  zustand.json         offener Bestand, letzter Stop, letzter Lauf (Herzschlag)
  README.md            tritt nach dem Bau an die Stelle dieser Spec
```

Kein eigenes `.venv` — OANDA ist REST+JSON, die Backtest-Mathematik ist stdlib.
Wie `kraken.py`.

## backtest.py

Zieht per OANDA `/v3/instruments/{inst}/candles?granularity=M15` **≥ 1 Jahr**
(Standard 2), paginiert, Cache unter `daten/`. Simuliert die Regeln je Session
für DE30, US30, NAS100.

Zwei Einstiegsmodelle gerechnet, Spanne angegeben:
- Füllung zum **Schlusskurs** der Breakout-Kerze
- Füllung zur **Eröffnung** der nächsten Kerze

TP: bei `--raster` ein Gitter über `punkte` und `k` (r_vielfaches).

Bericht je Instrument:

| Kennzahl | Quelle der Pflicht |
|---|---|
| beobachtete Trefferquote, Ø Gewinn, Ø Verlust | — |
| **nötige** Trefferquote (Break-even), Erwartungswert je Runde | `Wissen/Handelsbots.md` |
| **Zahl der Verlierer** (seltenere Seite) — Warnung bei < 10 | `Wissen/XPERP-Handel.md`: „Trefferquote ohne Gegenereignisse ist keine Zahl" |
| Quartalsaufschlüsselung + Kursverlauf des Testfensters | `Wissen/Handelsbots.md`: „nie über weniger als ein Jahr bewerten" |
| Spread-Sensitivität 1× / 1,5× / 2× | „Papierlauf ohne Gebühren empfiehlt live-Verlierer" |
| max. Rückschlag, mehrdeutige Kerzen | — |

Kostenmodell: OANDA-Index-CFD = **Spread** (kein Kommission auf Standard),
je Instrument als Punktwert (Startannahmen: DE30 ~1,2 · US30 ~1,6 · NAS100 ~1,0,
im ersten Umsetzungsschritt an echten `pricing`-Daten geeicht) + Slippage-Zuschlag.
Finanzierung nur bei Halten — Strategie geht täglich flat, wird aber trotzdem
modelliert.

**Abschlussurteil** (eine Zeile je Instrument): Hält die 81-%-Behauptung? Ist
der Erwartungswert nach Spread **im ganzen Fenster und im schlechtesten
Quartal** positiv? Sind ≥ 10 Verlierer im Sample?

## handeln.py

`--vorschau | --papier | --live | --wachen`, wie `kraken/handeln.py`.
Reihenfolge im Zyklus: **erst Ausstiege prüfen** (Stop / TP / Zwangsschluss),
dann höchstens ein Einstieg. Jede Aktion ins Journal mit Spread im Betrag; nach
jedem Lauf `zustand.json` schreiben (Herzschlag).

Ausstiege laufen **nie** durch das Freigabefenster — ein Stop muss auch greifen,
wenn niemand davorsitzt. Bestätigt wird nur, was Kapital bindet (der Einstieg).

### Neun Sperren vor der ersten echten Order

Alle offen, sonst handelt auch `--live` nur auf Papier und nennt die zu-e Sperre:

1. `wachen.json` → `handel_erlaubt: true`
2. `OANDA_TOKEN` + `OANDA_KONTO_ID` gesetzt (Windows-Benutzervariablen, per
   `winreg` gelesen wie bei Kraken)
3. `--live` ausdrücklich auf der Kommandozeile
4. `freigabe.erfuellt: true` = **Backtest bestanden** (Erwartungswert > 0 im
   ganzen Fenster **und** schlechtesten Quartal, Verlierer ≥ 10) **und**
   6 Wochen Papier, ≥ 50 gehandelte Sessions, netto positiv
5. Herzschlag frisch (`zustand.json`)
6. rollierender Erwartungswert ≥ 0
7. `journal_zweitziel` gesetzt (Kopie außer Haus)
8. mindestens `mindest_marge_frei` frei auf dem Konto
9. Sitzung am Bildschirm für `freigabe.py` (oder offenes Telegram-Zeitfenster)

Pflicht-Stop nicht abschaltbar, darüber `kill_switch_gesamt_eur`.
`wachen_orb.py` darf `handel_erlaubt` nur `true`→`false` kippen, nie zurück.

Scharfschalten: `../freigabe.py --spur orb` (Bildschirm) bzw.
`../freigabefenster.py` (Telegram, ≤ 24 h). Beide zeigen die Werte aus
`wachen.json`, Obergrenze jedes Reglers ist der Wachen-Wert, Hebeldeckel
senkbar nie hebbar.

## wachen.json — Felder

Rechnet in **EUR** (Feld `_usd` je Wert für die neutrale Rechnung, Muster Spur 3).

| Feld | Bedeutung |
|---|---|
| `handel_erlaubt` | Live-Schalter. Start `false` |
| `instrument_aktiv` | welcher Index die Papierphase fährt (nach Backtest gesetzt) |
| `risiko_pro_trade_eur` | Risikobetrag je Trade → Positionsgröße |
| `ziel_modus` | `punkte` \| `r_vielfaches` |
| `ziel_punkte` | je Instrument, bei `ziel_modus=punkte` |
| `ziel_k` | Vielfaches der Range-Höhe, bei `ziel_modus=r_vielfaches` |
| `hebel_deckel` | Obergrenze, die aus der Positionsrechnung fallende Hebelzahl wird nur gedeckelt |
| `letzter_einstieg_min_vor_schluss` | N Minuten |
| `mindest_range_punkte` | Range darunter → Session aussetzen (Rauschen, Spread frisst TP) |
| `max_range_punkte` | Range darüber → aussetzen (Stop zu weit, Risiko/Positionsgröße unbrauchbar) |
| `mindest_marge_frei` | Sperre 8 |
| `kill_switch_gesamt_eur` | Gesamtverlust-Riegel |
| `_freigabe` | die vier Papier-Bedingungen aus Sperre 4, maschinenlesbar |
| `journal_zweitziel` | Pfad/Ziel der Kopie außer Haus, Start `null` |
| `oanda_host_papier` / `oanda_host_live` | Basis-URLs |

## Fehlerbehandlung & Fallen

- **Nie auf `complete:false`-Kerzen handeln** — laufende M15 ist kein Signal.
- **DST**: Eröffnung je Tag in Börsen-Lokalzeit rechnen, nicht in fester UTC.
- **401 von OANDA** = Token abgelaufen **oder** Practice-Token gegen Live-Host.
  Meldung muss beides unterscheiden.
- **Wochenend-Gap**: CFD schließt Fr ~23:00, öffnet So ~23:00 CET — keine
  ORB-Session überspannt das. `letzter_einstieg` deckt den Sessionrand ab.
- **Rundung**: `units` ganzzahlig, Vorzeichen = Richtung; `minimumTradeSize` und
  Preis-Präzision aus Instrumentdetails; immer abrunden.
- **Slippage**: echten `fillTransaction`-Preis ins Journal, nicht den Wunsch.
- **Spread im Journal-Betrag**: Einstieg mit Aufschlag, Ausstieg nach Abzug.
- **DE30-Zugang**: OANDA Practice muss von Deutschland aus `DE30/EUR` zulassen.
  Erster Umsetzungsschritt verifiziert das an einem echten Practice-Konto;
  fällt es aus, läuft die Spur mit `US30`/`NAS100` und `DE30` entfällt (kein
  Blocker für den Rest).
- **Kerzen-Pagination**: OANDA gibt max. 5000 Kerzen je Abruf; `backtest.py`
  paginiert über `from`/`to` und schreibt lückenfrei in den Cache.

## Routine

`Agenten/Routinen/orb-papier.ps1` — läuft **alle 15 Min im Session-Fenster**
(Eröffnung bis Zwangsschluss) über die **Windows-Aufgabenplanung**, nicht
`/schedule` (Cloud-Agent hätte keinen Zugriff auf `wachen.json`/Token). Setzt
`MAXHIRN_ROUTINE=1`. Ruft `handeln.py --papier`.

Wöchentlich deckt `Agenten/Routinen/handel-wachen.ps1` diese Spur mit ab
(bestehende Routine erweitern).

## Änderungen außerhalb des Ordners

| Datei | Änderung | Werkzeug |
|---|---|---|
| `.gitignore` | Whitelist `!Agenten/Handel/orb/*.py|*.md|*.json`; Blacklist `orb/zustand.json`, `orb/handelsjournal.csv`, `orb/daten/**` | Edit |
| `MaxHirn/Wissen/Handelsregeln.md` | Spur 4 in die Tabelle + Sperrenliste, `related` | Edit (kein Python-Rewrite — CRLF) |
| `MaxHirn/Wissen/ORB-Handel.md` | neue Notiz nach Muster `XPERP-Handel.md`: „10 Punkte"-Übersetzung, Backtest-Urteil, Fallen | Write |
| `MaxHirn/Wissen/Routinen.md` | die neue Routine | Edit |
| `MaxHirn/Wissen/INDEX.md` | Verweis auf die neue Notiz | Edit |
| `Agenten/Handel/README.md` | Absatz „Spur 4 — ORB Index" mit Aufrufen | Edit |
| `../freigabe.py` | Spur `orb` ergänzen (Fenstertitel, EUR-Beträge) | Edit |

## Was bewusst wegbleibt (YAGNI)

Keine Overnight-Positionen · keine Pyramidisierung · kein zweiter Einstieg pro
Session · keine weiteren Indizes als die drei · kein eigener Feiertagskalender
(Zwangsschluss + `letzter_einstieg` reichen) · keine GUI über `freigabe.py`
hinaus · keine Rasteroptimierung der Range-Länge (zwei Kerzen **ist** die
Strategie) — gerastert wird nur der TP-Modus.

## Reihenfolge der Umsetzung (grob, Detailplan folgt über writing-plans)

1. `oanda.py` + echtes Practice-Konto: Kerzen, Preise, Instrumentdetails, DE30-Check
2. `session.py` mit DST-Tests
3. `backtest.py` — Regeln, beide Einstiegsmodelle, Bericht, Spread-Eichung
4. Backtest über 2 Jahre fahren, Urteil, `instrument_aktiv` + TP-Startwerte setzen
5. `wachen.json` + `wachen_orb.py` + `.gitignore`
6. `handeln.py` — Zyklus, Journal, Zustand, `--vorschau`/`--papier`
7. `freigabe.py`-Anbindung, `--live` mit den neun Sperren
8. Routine + KB-Notiz + Handelsregeln-Eintrag
