---
name: messwerkzeug-gegenprobe
description: "Verify a measuring tool before trusting its numbers."
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [Messwerkzeug, Gegenprobe, Verifikation, Belege, Backtest]
    related_skills: [trugschluesse, handel-spur-optimierung, handel-spuren]
---

# Messwerkzeug-Gegenprobe — bevor du einer Zahl glaubst

Destillat aus einer Optimierungs-Sitzung (04.10.2026), in der ein Suchwerkzeug
neun Kandidaten abzuarbeiten vorgab und dabei **neunmal dieselbe Rechnung**
fuhr. Das Werkzeug meldete „kein Hebel" — nicht weil keiner da war, sondern weil
der Schalter, der ihn einstellen sollte, beim Aufruf still verschwand.

Dieser Skill ist die Regel **vor** der Optimierung (`handel-spur-optimierung`),
die Reihenfolge und die Beweisregel fuer Parameteraenderungen. Er ist kein
Handels-Wissen (`handel-spuren`) und keine allgemeine Beweisregel
(`trugschluesse`), sondern der eine Satz: **ein Schalter, dessen Wirkung niemand
geprueft hat, ist kein Schalter.**

## When to Use

- Ein neues Werkzeug liefert eine Zahl, die eine Entscheidung tragen soll
- „kein Hebel", „0 Treffer", „alle Kandidaten identisch", „keine Aenderung"
- Ein Fix aendert Code, **aber die Zahl bleibt dieselbe**
- Ein Hintergrundlauf wurde zur Auswertung herangezogen
- Ein Werkzeug zaehlt Dinge, die eine Spur anders ablegt als eine andere

**Don't use for:** eine Spur anbinden oder betreiben (`handel-spuren`), die
Reihenfolge einer Optimierung (`handel-spur-optimierung`), allgemeine
Zustandsbelege (`trugschluesse`), eine konkrete Bruecke reparieren
(`telegram-bruecke-diagnose`).

## Prerequisites

- Arbeiten aus der Repo-Wurzel `BrainFiles/`; `unset PYTHONHOME PYTHONPATH` vor
  jedem `python`/`hermes`-Aufruf aus dem MCP-Kontext.
- Das Hauswerkzeug der Wahl: `Agenten/Handel/kosten_wendepunkt.py`
  (`kennzahlen()`, `runden_aus_journal()`). **Nicht** selbst Zeilen zaehlen.

## How to Run

Ein Messwerkzeug gilt als geprueft, wenn **zwei Aufrufe mit
bekannt verschiedenen Eingaben verschiedene Zahlen** liefern. Beide Aufrufe
gehoeren in **einem** Lauf, sonst ist keiner von beiden ein Beweis.

Ueber das `terminal`-Werkzeug aufrufen, Ergebnis mit `read_file` oder im
selben Aufruf lesen.

## Quick Reference

| Frage | Werkzeug | Was die Antwort beweist |
|---|---|---|
| Wirkt ein Parameter-Setzer? | zwei Laeufe, ein Wert verschieden | identisch = Schalter tot |
| Welche Zahl gilt? | `kosten_wendepunkt.kennzahlen()` | Rohzeilen sind keine Runden |
| Zaehlt das Werkzeug die Spur? | Ordner-Argument, nicht Datei | Datei -> 0 Positionen, sieht leer aus |
| Ist der Hintergrundlauf fertig? | Prozess beendet, **dann** lesen | geschriebene Datei != fertiges Ergebnis |
| Haelt eine Regel im Betrieb? | Regel im Code beim Anlegen | Handeingetragenes wird ueberschrieben |

## Procedure

1. **Den Werkzeugaufruf pruefen, bevor du die Datenstruktur verdaechtigst.**
   Lief `0 Positionen`, ist die Frage zuerst: **stimmt der Aufruf?** Ein
   geaenderter Code, der dieselbe Zahl liefert, ist kein Fortschritt, sondern
   ein zweiter Irrtum. Belegt 04.10.2026: `beitrag_der_spur('gitter', 'gitter')`
   ergab 2 Positionen / 181,95 USD, `beitrag_der_spur('gitter',
   'gitter/zustand.json')` ergab 0 / 0,00 — dieselbe Funktion, dieselbe Datei.
2. **Zwei Kandidaten fahren, ein Wert verschieden.** Nicht die Extreme, nicht
   die ganze Tabelle — **ein** Wert. Der Aufruf muss sich unterscheiden, sonst
   ist der Schalter nicht das Problem und das Messergebnis auch nicht.
3. **Am Ergebnis pruefen, nicht an der Datei.** Die vom Backtest geschriebene
   Wachen-Kopie ist **kein** Beweis: der Patch wird auf das W-Dict im Speicher
   angewandt und nicht in die Kopie geschrieben (gemessen: `lauf_a`,
   `replay.py` 794). Die Kopie zeigt immer die Ausgangswerte — vorher wie
   nachher.
4. **Die Hausrechnung nehmen.** `kosten_wendepunkt.kennzahlen()` rechnet die
   Paarung, Zwangsschluesse und die Marke. Eine selbst gezaehlte
   `AUSSTIEG`-Zeile ist keine Runde: 1181 Zeilen sind 579 Runden. Selbst
   gezaehlte Zahlen sind Zwischenstaende, keine Ergebnisse.
5. **Erst rechnen, wenn der Prozess beendet ist.** Vorher ausgewertete Dateien
   sind Teilstaende und tragen dieselbe Form wie ein fertiges Ergebnis.
6. **Wenn die Zahl gleich bleibt: den Werkzeugweg pruefen, nicht die Daten.**
   Reihenfolge: Aufruf → Prozess beendet → Hausfunktion → Datenstruktur.
   Erst danach darf die Vermutung über Datenformen kommen.
7. **Jeden Nebenbefund getrennt ausweisen.** Ein Befund, der nebenbei auffällt,
   gehört mit eigenem Verdikt in die Antwort und nicht in die Schlussfolgerung
   des Hauptbefunds.
8. **Falsche eigene Zahlen aktiv zurücknehmen.** Steht eine Zahl schon im
   Bericht, wird sie benannt, mit Grund korrigiert und neu gemessen — nicht
   stillschweigend ersetzt.

## Pitfalls

- **Ein stillschweigend verworfener Schalter meldet „kein Hebel".** Gemessen:
  `replay.py` hatte `setzen=` (Familien B/C) und `wachen_patch=` (Familien A/D);
  die Aufrufstelle in `main()` trug kein Patch. Drei Zeilen fehlten.
- **Zwei Namen fuer dasselbe Argument sind kein Tippfehler, sondern ein
  Befund.** Immer den Namen an der Aufrufstelle gegen die Signatur lesen.
- **Eine Regel, die nur in einem Zustandsdatei-Eintrag steht, existiert
  nicht.** Die Spur schreibt ihren Zustand bei jedem Zyklus neu: ein von Hand
  gesetzter Stop war um 01:00 drin und um 01:11 ueberschrieben (gitter,
  `zustand.json`, nicht versioniert). **Regeln gehoeren an die Stelle, wo das
  Ding entsteht** — beim Kauf, nicht in die Datei.
- **Nicht jede Spur legt ihre Positionen gleich ab.** `zustand["positionen"]`
  ist bei den meisten Spuren die Wahrheit; `gitter` fuehrt seine Stufen in
  `z["lose"]` (Dict, Schluessel = Stufennummer) neben einer Position in
  `positionen`. Ein Werkzeug, das nur `positionen` liest, zaehlt diese Spur zu
  niedrig — das Hausrisiko war um 92 USD zu niedrig ausgewiesen und **keine
  Wache fand es**, weil niemand es zaehlte. Beide Formen sind Dict **und**
  Liste — erst messen, dann korrigieren.
- **Ein Optimierer, der erst am Ende schreibt, taugt nicht als
  Zwischenwerkzeug.** 24 Monate x 9 Kandidaten liefen 13 Minuten ohne ein Byte.
  Bei Kandidaten unter etwa einem Dutzend: **je einen Lauf selbst fahren**, das
  ist schneller und liefert sofort Zahlen.
- **Ein geaenderter Code mit derselben Ausgabe ist ein zweiter Irrtum.** Zwei
  Datenstruktur-Fehler wurden „gemessen", ohne den Aufruf zu pruefen — beide
  geraten.
- **Ein Test, der einen alten Zwischenstand einfriert, geht bei jeder
  Verbesserung kaputt** und wird dann zum Verdachtsbericht gegen den richtigen
  Fix. Erwartungen nachziehen, wenn die **Regel** sich aenderte.
- **Ein alter Hintergrundlauf meldet sich spaeter** und sieht nach einem neuen
  Ergebnis aus. Immer am Kommandozeilen-Präfix erkennen, ob es der
  ausgetauschte Lauf ist.

## Fall: Backtest gegen die Prognose-Rechnung

Wenn zwei Rechenwege (`replay.gegenprobe`) dieselben Kerzen gegen dieselbe Spur
fahren und auseinanderlaufen, ist **die erste Frage nie der Parameter** — sie
lautet: **fehlt in einem der Wege eine Hausregel?**

Gemessen 04.10.2026 (`backtest_prognose.py` gegen `replay.lauf_a`): Runde 0 und 1
identisch, ab Runde 2 nahmen die Wege verschiedene Instrumente und Seiten.
Ursache war **nicht** die Geometrie, die Skalierung oder die Uhr, sondern die
**Docht-Regel T-202/T-177** — der Ausloeser der Spuren ist der *Kerzenschluss*,
eine Kerze, die Stop oder Ziel nur mit dem Docht streift und darueber schliesst,
loest dort nichts aus. `replay.lauf_a` rief `docht_ausstiege_anwenden()`,
`backtest_prognose.lauf` nie. Eine Regel war eingebaut und an der anderen Stelle
vergessen.

Die Regel gilt fuer **jede** Aenderung an einer Hausregel: eine neue Regel geht
in alle Wege, die dieselbe Sache rechnen. Sonst widersprechen sich die Zahlen
und beide sehen richtig aus.

Nach dem Nachziehen stimmen Rundenzahl, Instrumente und Seiten wieder. Der
Ausstiegskurs wich noch ab (`brutto_pct`, gemessen bis 1,5 Prozentpunkte) — das
ist eine echte offene Abweichung und wird als solche ausgewiesen, nicht als
geklaert.

## Eine Ausnahme, die man trotzdem meldet: die falsche Naht

Der Satz aus der Einleitung gilt fuer **Wirkung** am Werkzeug. Zwei eigene
Fehler desselben Tages gehoeren trotzdem hierher, weil beide das Werkzeug selbst
betrafen und beide erst durch eine Gegenprobe auffielen.

### 1. Ein gruener Kanal verdeckt einen toten

- Behauptung (von mir): „mindestens eine Anbindung lebt" — Exit 0.
- Entstehung: das Urteil war „irgendwas lebt". Im Status gab es zwei
  Telegram-Eintraege: `telegram` (der tote Hauptbot) und `bots:telegram`
  (verbunden). Ein `any()` liest nur, dass **irgendeiner** connected ist, und
  meldet den toten daneben im Detail - ohne ihn zum Befund zu machen.
- Auffiel: die Gegenprobe mit genau dieser Besetzung (Hauptbot `retrying`,
  `bots` connected) lieferte **Exit 0** und das Wort „lebt". Das Werkzeug war
  nicht falsch in der Messung, sondern in der **Aggregation**: es beantwortete
  eine andere Frage als die gestellte.
- Beleg: nach dem Umbau meldet derselbe Aufbau `1 Anbindung(en) nicht gesund:
  Gateway telegram` und Exit 1; die Messwerte darueber bleiben unveraendert.
- **Regel: das Urteil traegt die Frage, die gestellt wurde.** „Laeuft es ueber
 haupt" und „laeuft jede Anbindung" sind zwei Fragen mit zwei Antworten.
  Entscheidet man sich fuer die weiche, gehoert der Name des toten Eintrags in
  die Antwort — nicht in eine Detailzeile, die man ueberliest.
- **Uebertragbar:** jedes Werkzeug mit Sammelausgabe („mindestens einer",
  „irgendeiner"). Der Fehler ist nicht die Messung, sondern das fehlende
  Aufzaehlen der failures.

### 2. Ein Gegenlauf prueft gegen nichts, wenn der Pfad falsch ist

- Behauptung (von mir): die Gegenprobe belege „keine Anbindung lebt".
- Entstehung: die Attrappe lag unter `$TMPDIR` — ein **MSYS**-Pfad. Das
  Werkzeug laeuft als **native** Windows-Version und bildet den Pfad nicht ab;
  die Datei wurde nie gefunden, `os.path.isfile` lieferte `False`, und das
  Werkzeug meldete ehrlich „gateway_state.json fehlt". Die Gegenprobe war
  gruen, weil sie nichts fand.
- Auffiel: der Fehlertext war **richtig** — er sagte, was er sah. Falsch war
  meine Deutung: ich las „fehlt" als Befund ueber die Attrappe, obwohl die
  Attrappe unter einem anderen Namen als dem gesuchten Pfad existierte. Der
  ehrliche Fehlertext ist keine Garantie, dass man die richtige Instanz
  befragt hat.
- Beleg: derselbe Aufbau mit `C:/…`-Pfaden lieferte die vollstaendige Tabelle
  mit Logzeilen und Urteil.
- **Regel: ein Fehlertext „Datei fehlt" beweist, dass du die FALSCHE Datei
  gesucht hast.** Er beweist nicht, dass sie fehlt. Bei jedem Gegenlauf den
  Pfad, unter dem die Attrappe wirklich liegt, gegen den Pfad halten, den das
  Werkzeug aufloest — auf Windows gegen ein `C:`-Pfad, nicht gegen ein
  `$TMPDIR`/`/tmp`-Pfad.
- **Uebertragbar:** jeder Attrappenlauf. Die Gegenprobe muss die Instanz treffen,
  die der Aufruf wirklich sieht.

- **Ein Werkzeug darf nie eine echte Aktion ausloesen.** Der erste Entwurf
  eines Status-Skripts wird gern gegen das echte System gebaut; eine
  End-to-End-Sonde, die eine echte Nachricht sendet, gehoert in ein Skript mit
  eigenem Namesraum und wird **einmal von Hand** gefahren, nicht im Testlauf.
- **Kein Test darf eine echte Order ausloesen.** Am 05.10.2026 rief der erste
  Entwurf `markt_kauf()` ungedeckt auf → `OKX 1: All operations failed`. Nichts
  passierte, es haette etwas passieren koennen. Jede Boersenfunktion im Test
  abfangen **und** zusaetzlich pruefen, dass im Ablehnungsfall **kein** Aufruf
  an die Boerse ging.

## Zwei Werkzeugarten, die man nicht gleich behandelt

| Art | Was prueft | Wie |
|---|---|---|
| **Zahlwerkzeug** (rechnet, aggregiert, klassifiziert) | die Rechnung | zwei Laeufe, **ein** Wert verschieden; Ergebnis gegen die Hausfunktion |
| **Statuswerkzeug** (liest Zustand, meldet je Eintrag) | die **Aggregation** | eine Attrappe, in der genau EIN Eintrag kaputt ist und alle anderen leben — die weiche Frage („lebt ueberhaupt\") muss daran scheitern |

Ein Statuswerkzeug wird durch die erste Art von Gegenprobe **nicht** geprueft:
zwei verschiedene Zustaende ergeben verschiedene Ausgaben, aber beide koennen
gleichzeitig falsch aggregieren. Die zweite Art ist die, die den Fehler findet —
und sie ist ein Lauf von Sekunden.

## Verification

Ein Werkzeug ist geprueft, wenn in **einem** Lauf zwei verschiedene Eingaben
zwei verschiedene Zahlen liefern und beide durch die Hausfunktion gerechnet
sind. Fuer den konkreten Fall des Setzers:

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && unset PYTHONHOME PYTHONPATH && \
./scanner/.venv/Scripts/python.exe replay.py --spur squeeze --lauf g1 --gebuehr 0.10 \
  --setzen pflicht_stop_prozent_min=5.0 --setzen ziel_r_vielfaches=2.0 > "$TMPDIR/g1.txt" 2>&1 && \
./scanner/.venv/Scripts/python.exe replay.py --spur squeeze --lauf g2 --gebuehr 0.10 \
  --setzen pflicht_stop_prozent_min=3.0 --setzen ziel_r_vielfaches=1.5 > "$TMPDIR/g2.txt" 2>&1
```

Erwartet: **unterschiedliche** `runden`/`ergebnis_summe` in den beiden
`kennzahlen`-Bloecken (gemessen 579 / −464,18 gegen 1007 / −75,74). Sind beide
Bloecke gleich, ist der Setzer tot — nicht der Markt.