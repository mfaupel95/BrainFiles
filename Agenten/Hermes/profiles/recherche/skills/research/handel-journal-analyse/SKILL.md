---
name: handel-journal-analyse
description: Use when analyzing trading journals (handelsjournal.csv).
version: 1.0.0
author: recherche
license: MIT
metadata:
  hermes:
    tags: [handel, journal, analyse, recherche]
    related_skills: []
---

# Handel-Journal-Analyse

## When to Use

Analyse der Handelsjournale der Haus-Spuren (`Agenten/Handel/<spur>/handelsjournal.csv`) — Kill-Switch-Ereignisse, Order-Fills, Ausstiegsgründe, G/V-Bilanz, Füllquoten. Rein lesend: als Recherche-Agent wird nichts geschrieben, Befunde werden zur Übergabe formuliert.

## Reihenfolge

1. **Journal-Struktur zuerst prüfen** — Spaltenkopf lesen (`head -1`), nicht annehmen. Die xperp-Journale haben 22 Spalten, `grund` ist die letzte. Andere Spuren (kraken, nautilus) haben eigene Spaltenköpfe.
2. **Ausstiegsgründe gliedern** mit `collections.Counter` über die `grund`-Spalte — das zeigt sofort, was normal ist (ziel/stop) und was Störung (herzschlag_alt, buchbereinigung) oder Sonderfall (kill_switch).
3. **Ereignisse je Tag zählen** — ein Muster, das nur an einem Tag auftritt, ist ein Vorfall; über viele Tage verteilt ist es ein Systemverhalten. Das unterscheidet „behoben" von „offen".
4. **G/V je Position paaren** (siehe Pitfall unten) und die Summe ausweisen.
5. **Befund zuerst, Belege danach** — Ergebnis oben, Quellen (Zeilen, Datei, Code-Kommentar) darunter. Keine erfundenen Zahlen; eine fehlgeschlagene Paarung wird verworfen und als Grenze genannt, nicht als Ergebnis präsentiert.

## Pitfall: G/V-Paarung über `pos_id` allein ist unzuverlässig

`pos_id` ist **leer bei fehlgeschlagenen Einstiegen** (`aktion=fehler`, `grund=order_nicht_gefuellt`) — es wurde nie eine Position eröffnet, also gibt es keine Kennung. Naives Matchen über `pos_id` greift dann falsche Einstiege (beobachtet: CRCL mit Einstieg 4280 USD, offensichtlich ein anderer Kontrakt) und produziert G/V-Summen, die Müll sind.

**Paare über `pos_id` + Instrument + Zeitfenster** (Einstieg zeitlich vor dem Ausstieg, gleiches `inst`), und verifiziere die Plausibilität (Einstiegspreis muss zum Instrument passen). Eine Summe, die um Größenordnungen abweicht (z. B. −18,8 Mio USD bei einem Stop), ist ein Paarungsfehler, kein Marktergebnis — verwerfen, nicht berichten.

## Pitfall: Prüfe, ob ein Muster im Code schon adressiert ist, bevor du einen Fix empfiehlst

Ein auffälliges Journal-Muster (z. B. `order_nicht_gefuellt`) kann der **Anlass eines bereits eingebauten Fixes** sein. Der Code-Kommentar an der betroffenen Stelle nennt oft genau den Fall und das Datum. Vor einer Behebungs-Empfehlung: die Auslöse-Stelle im Code lesen und prüfen, ob das Muster seit dem Fix noch auftritt (Ereignisse je Tag zählen). Ein Muster, das nur am Fix-Tag vorkommt, ist behoben, nicht offen — dann ist die Empfehlung „beobachten", nicht „umbauen".

## Pitfall: Kill-Switch feuert auf Rücklauf vom Peak, nicht auf echte Verluste

Der Kill-Switch (`kill_switch_gesamt_usd`) löst auf **Rücklauf vom realisierten Höchststand** aus (Drawdown vom Peak), nicht auf realisierte Verluste unter dem Einstand. Folge: Er schließt Positionen, die nur Gewinn zurückgeben, aber noch im Plus stehen. Bei der Bewertung eines Kill-Ereignisses immer beide Seiten nennen: Er fängt echte Katastrophenfälle (z. B. Liquidation ohne Börsen-Stop), schließt aber auch Gewinner. Die Auslösegröße (Rücklauf vs. echte Verluste) ist die eigentliche Stellschraube, nicht der Deckel.

## Pitfall: Spur-Ordner können unter anderem Namen liegen

Ein in `MaxHirn/Wissen/Handelsregeln.md` dokumentierter Arm (z. B. `nautilus_kraken_futures`) muss nicht unter dem erwarteten Pfad liegen. Vor einer Aussage über eine Spur: den tatsächlichen Ordner suchen (`search_files`), nicht annehmen. Ein „Path not found" ist ein offener Punkt, kein Befund über die Spur. Gemessen 11.10.2026: der Kraken-Futures-Code liegt in `omnitrade_futures/` (Adapter `weg.py` → `nautilus_kraken/kraken_futures.py`), nicht unter `nautilus_kraken_futures/`. Der Adapter setzt Hebel über `/leveragepreferences` + `leverage`-Feld, aber **keinen Margin-Modus** (`mgnMode`/isolated/cross existiert nicht) — isoliert/cross ist bei Kraken Futures eine Kontoeinstellung, kein Order-Parameter. `kraken_futures.py` hat `markt_kauf`/`markt_verkauf`/`stop_setzen`, aber **keine TP-Order-Funktion**; `spur_buch` nutzt `ziel` nur als Journal-Spalte. Die `fib_retrace`-Spur läuft auf OKX (`scanner/okx.py`), nicht Kraken, und setzt `ziel_pct` (fester Prozentsatz), nicht das Fibonacci-23,6-%-Level als TP-Preis.

## Pitfall: Spot-Spuren haben keinen Margin-Modus

Die isoliert/cross-Frage existiert nur bei gehebelten Spuren. Eine Spot-Spur (`kraken/`, nur Long, kein Hebel) hat keinen Margin-Modus — die Frage ist dort nicht anwendbar, nicht „beantwortet mit nein".

## Pitfall: Kraken-Futures-Adapter hat keinen Margin-Modus und keine TP-Order

Der Kraken-Futures-Code liegt unter `omnitrade_futures/` (Adapter `weg.py` -> `nautilus_kraken/kraken_futures.py`), NICHT unter `nautilus_kraken_futures/`. Der Adapter setzt den Hebel ueber `/leveragepreferences` (PUT) und das `leverage`-Feld in `/sendorder`, aber **keinen `mgnMode`/`isolated`/`cross`** — der Margin-Modus ist eine Kraken-Kontoeinstellung, kein Order-Feld. Es gibt `markt_kauf`, `markt_verkauf`, `stop_setzen` (stp-Order, reduceOnly, triggerSignal mark), aber **keine TP-Funktion** (`ziel`/`take_profit`/`lmt` = 0 Treffer). `spur_buch.py` nutzt `ziel` nur als Journal-Spalte, nicht als Order. Ein TP nach Fibonacci muesste als `orderType lmt` + `limitPrice` gebaut und an `spur_buch` verdrahtet werden.

## Pitfall: fib_retrace-Spur setzt KEIN Fibonacci-TP

`fib_retrace/wachen.json` hat `ziel_pct: 2.0` (fester Prozentsatz), nicht das 23,6 %-Level. Die Spur nutzt Fibonacci nur fuer das Einstiegs-Signal, das Ziel ist ein Prozentwert. Fuer ein echtes Fibonacci-TP muss `fib_preise()[0.236]` als `limitPrice` an die Order gehen. Das Modul `fibonacci_retracement.py` ist plattformneutral (braucht nur Kerzen), aber `kraken_futures.py` hat keine Kerzen-Funktion (nur `letzter_kurs`).

## Übergabe-Format

Befund als kompakten Übergabeblock an den Haupt-Agenten formulieren: was belegt ist (mit Datei/Zeile), was offen ist, und die Empfehlung. „Ich habe nichts geschrieben" als Abschluss, weil der Recherche-Agent nicht schreibt.
