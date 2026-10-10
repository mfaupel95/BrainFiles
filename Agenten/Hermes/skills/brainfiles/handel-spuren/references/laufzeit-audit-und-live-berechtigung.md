# Laufzeit-Audit aller Spuren, und die Frage: was darf mit echtem Geld handeln

Auftrag der Form "Spuren auswerten und auf Fehler pruefen. Bei Fehlern merken
und pruefen was mit echt Geld handeln kann und darf". Das ist EINE Runde in
neun Schritten, deren Reihenfolge zaehlt: jeder Schritt macht den naechsten
billiger, und die Verdict-Tabelle am Ende laesst sich nur aus Ziffern
schreiben, die vorher gemessen wurden. Nichts davon wird aus dem Journal
gelesen und geglaubt - jede Zahl hat ein Haus-Werkzeug.

Der zweite Teil des Auftrags ("was darf") ist KEINE Auswertungsfrage. Eine
Spur mit dem besten Excess im Haus darf oft nicht, und eine mit mittelmessiger
darf. Unterschieden wird das nicht an der Performance, sondern an drei Dingen,
die alle auf die BORSEN wirken: gibt es einen Orderpfad im Code, ist jede
offene Position an der Boerse geschuetzt, und gibt es echte Live-Zeilen im
Journal. Fehlt eines, ist die Spur nicht scharf, egal welche Zahl ihre
Runden tragen.

## 1. Das Steckbrief-Werkzeug zuerst

```
cd Agenten/Handel
../scanner/.venv/Scripts/python.exe spuren_stand.py
```

Spalten: `erlaubt` (`handel_erlaubt`), `hs` (Herzschlag), `Fenster`
(`offen_bis`, wann es auslaeuft), `frei`, `Order-Code` (welche Datei den
Aufruf enthaelt), `Alter Buch`. Die letzte Spalte nennt `keiner` fuer eine
Spur ohne Orderpfad - das ist die **Handelsfaehigkeit** und sie ist durch
keinen Messwert zu ersetzen. Die Schlusszeile zaehlt, wie viele Spuren
ueberhaupt einen Live-Pfad haben; das ist die Grundgesamtheit aller folgenden
Aussagen.

`frei` als Spalte ist eine Falle: sie liest `true` auch dann, wenn das Tor
hinter `freigabe.erfuellt` zusaetzlich zu ist. Sie sagt "die Sperre ist nicht
das Guthaben", nicht "die Spur handelt".

## 2. Fehler aus dem Lauf, nicht aus dem Buch

```
tail -600 dauerlauf.log | grep -iE "fehler|error|traceback|timeout|abgebrochen"
tail -600 dauerlauf.mittel.log | grep -icE "timeout|error"   # je Risikostufe
```

Nur die letzten 600 Zeilen: eine Suche ueber die ganze Logdatei liefert
Altlasten und verbraucht Minuten. Fehlerzeilen aus dem Log sind **Hinweise**,
keine Befunde - sie beantworten nicht, ob der Fehler noch besteht.

## 3. Jeder Logbefund wird gegen den Ist-Stand geprueft

Jede Logzeile braucht eine Gegenprobe am laufenden System. Ohne sie steht die
Fehlermeldung als Befund im Bericht, auch wenn sie seit Tagen behoben ist.

| Logzeile | Gegenprobe | Ergebnis heisst |
|---|---|---|
| `<spur> TIMEOUT (exceeded 700s limit)` | `<spur>/handeln.py --vorschau` mit Uhr | 1,1 s = **Maschinenlast im Zeitfenster**, kein Spurendefekt. Ein echter Defekt antwortet auch einzeln langsam |
| `<spur> subprocess ERROR: [WinError 267]` | Ordner vorhanden? (`search_files` target=files) | Ordner fehlt = der Eintrag in der Verdrahtung ist tot. Die Spur ist **kein Laufzeitproblem, sondern ein Verdrahtungsproblem** |
| `Rueckgabe 1` bei einer Papierspur | Journal-Zeilen nach der Fehlerzeit | keine neuen Zeilen = gehaeufig harmlos, aber der Grund gehoert ins Protokoll |
| Fehlerzeile im Journal (`aktion=fehler`) | `grund` Spalte, nach Ursache gruppieren | drei Ursachen hinter 32 Zeilen = drei Befunde, nicht einer |

Der WinError-267-Fall ist der typische: eine Fremdarbeit-Sitzung committet die
Loeschung eines Spur-Ordners, die Verdrahtungsliste bleibt, und von da an
schreibt jede Risikostufe in jeder Viertelstunde dieselbe Fehlermeldung. Der
Ordner ist weg, aber die Daten liegen noch auf `Q:\Handel_Journal\<spur>` -
also ist die Frage "wiederherstellen oder aufgeben" eine **Buchfrage**, keine
Codefrage, und sie gehoert in den Bericht.

## 4. Die Sperrgruende: die eine Zeile, die alles entscheidet

```
MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe sperrgruende.py
```

Die Umgebungsvariable ist Pflicht. `sitzung_da()` prueft ein TTY, und unter
MAXHIRN_ROUTINE ist das immer false - ohne sie nennt die Vorschau einen
Sperrgrund, den der echte Betrieb gar nicht hat (gemessen: "keine Sitzung am
Bildschirm" bei einer Spur, deren Zeitfenster offen war).

Die Auswertung liest sich in drei Klassen, und die Klasse entscheidet, wer
handeln darf:

- **`nichts`** = alle Tore offen. Das ist die einzige Zeile, die ein Klarnamen
  "darf" traegt.
- **`freigabe.erfuellt=false (Bedingung 1)`** = der Haken des Menschen fehlt.
  Technisch bereit, von Hand nicht abgenommen. Getrennt nennen von der Zeile
  darunter: steht `handel_erlaubt=false` ZUSAETZLICH, ist der Auftrag nicht
  technisch, sondern politisch gesperrt.
- **`kein Live-Pfad in dieser Spur (Papier)`** = die Spur kann strukturell
  nicht handeln. Der Schalter `handel_erlaubt` ist dort wirkungslos, und ein
  darauf gesetzter Wert erzeugt keine Faehigkeit, sondern einen Widerspruch.

## 5. Zwei Auswertungen, zwei verschiedene Fragen

```
../scanner/.venv/Scripts/python.exe kosten_wendepunkt.py   # Gebuehrenkante
../scanner/.venv/Scripts/python.exe spur_audit.py          # Excess, ~15 min
```

`kosten_wendepunkt` beantwortet "ab welcher Gebuehr kippt die Spur" (f_max je
Runde) und braucht Sekunden. `spur_audit` beantwortet "verdient die Spur mehr,
als das Instrument getragen haette" (Excess) und braucht Minuten - **im
Hintergrund starten**, die Ausgabe in eine Datei, und den unabhaengigen Teil
des Auftrags beantworten, statt auf einen scheinbar haengenden Prozess zu
warten.

Der Excess ist die groessere Zahl, und er entwertet die anderen: eine Spur mit
13,97 % Rundenergebnis und 77 % Treffer kann einen Excess von 0,01 % haben.
Die Spalten `<1h` / `>=1h` sind der eigentliche Befund, nicht die Zahl: weichen
sie um mehr als ein paar Prozentpunkte ab, misst der Gesamtwert die **Auswahl**
(nach welcher Haltedauer ausgesucht wurde), nicht die Spur.

## 6. Buch gegen Boerse: vier Werkzeuge, vier Fragen

```
../scanner/.venv/Scripts/python.exe spiegelstand.py            # Bedingung 4
../scanner/.venv/Scripts/python.exe scanner/boersenstops.py    # scanner
../scanner/.venv/Scripts/python.exe xperp/stopdeckung.py       # xperp
../scanner/.venv/Scripts/python.exe kraken/abgleich.py        # Kraken
```

Jedes beantwortet eine eigene Frage, und keine beantwortet eine andere:

| Werkzeug | Frage | Fehlmeldung |
|---|---|---|
| `spiegelstand` | ist die Ausser-Haus-Kopie byte-gleich | `ABWEICHUNG` mit Dateinamen - meist Test-Nebenwirkung, zwei Zyklen abwarten |
| `boersenstops` / `stopdeckung` | hat JEDE Live-Position ihren Stop, und decken die Stops die MENGE | `nachgesetzt 0 / stop fehlt weiter 0` = sauber; ein Treffer genuegt NICHT |
| `abgleich.py` | stimmen Geister, Teilstuecke und Waisen | `Geister: 0 / Waisen: 0 / Teils: 0` |

Der Stop-Deckungsgrad ist eine eigene Pruefdimension: eine Position mit 145
Kontrakten und OCO-Stops ueber 126 Kontrakte ist 19 Kontrakte ungeschuetzt, und
bool-Rueckgaben melden sie als gedeckt. Die geschuetzte MENGE ist die **Summe**
der Stop-Groessen, nicht der groesste Einzelwert.

## 7. Das Journal: der zweite Zeuge fuer "echt"

Die Spuren-Gueterin ist unzuverlaessig (Schritt 1), also zaehlt man die Zeilen
selbst - und zwar je Aktion, weil eine Spur mit 109 `kauf_beleg` und 58 `kauf`
dieselbe Bestellung zweimal gebucht hat:

```python
import csv, collections
rows = list(csv.DictReader(open("kraken/handelsjournal.csv", encoding="utf-8")))
live = [r for r in rows if (r.get("modus") or "").strip() == "live"]
print(collections.Counter(r["aktion"] for r in live))
```

Drei Muster kommen dabei regelmaessig heraus und jedes ist ein eigener Befund:

- **`eroeffnen`/`kauf` mit `modus=live`, an der Boerse nicht vorhanden** = Geist.
  Die Probe gehoert an die Borsenhistorie (`orders-history-archive`, nicht nur
  `-history` - die Standard-Historie kann leer sein) und an den Bestand
  (`spotBal`/`frozenBal`). Ein `51008 balance insufficient` beim Verkauf ist
  haeufig die FOLGE eines Geists, nicht einer Kontolage.
- **`funding`/`zyklus` als einzige Live-Aktion** = die Live-Pfade sind nie
  gelaufen. Die Positionen im Buch stammen dann aus dem Papierlauf.
- **N Ausstiegszeilen ohne Partner / N Einstiege ohne `pos_id`** = die Kennzahlen
  zaehlen diese Runden nicht. Als Luecke ausweisen, nicht als Verlust.

## 8. Die Boerse selbst: Positionen, die keine Spur fuehrt

```
../scanner/.venv/Scripts/python.exe okx_positionen_live.py
../scanner/.venv/Scripts/python.exe okx_bot_waechter/waechter.py
```

Das ist der Schritt, der die eigentliche Frage beantwortet und der sonst
fehlt: **es gibt Positionen mit echtem Geld, die zu keiner Spur gehoeren.**
Trading-Bots auf dem Konto (Future-DCA, Grid) tragen Margin, Liquidation und
Pnl, und keine Spur der 47 beruehrt sie. Ihre Lage wird nur
`okx_bot_waechter` liest.

Die Befunde, die dort herauskommen und die keine Spur-Auswertung liefert:

- ein Bot **ohne boersenseitigen Stop** (`slPx` leer) ist eine Margin ohne
  Notaus - dieselbe Luecke, an der die Kernel-Power-41-Abschaltungen teuer
  wurden
- **unter 8 % Luft bis zur Liquidation** ist die einzige Zahl, die im Betrieb
  wirklich zaehlt; sie steht in keinem Journal
- **Meldung 0/9 Munition** heisst "die Leiter ist voll gefuellt, kein Nachkauf
  mehr", nicht "gesund"

Die Waechter-Datei `okx_bot_waechter/wachen.json` traegt `stop_erlaubt: false`
und je Bot eine datierte Entscheidung. Diese Schranke wird nicht eigenmaechtig
geoeffnet - sie gehoert Max.

## 9. Die Verdict-Tabelle, und was in ihr steht

Jede Zeile traegt **drei** Belege, nicht einen:

| Spur | darf | handel_erlaubt | Orderpfad | Stops an der Boerse | echte Live-Zeilen |
|---|---|---|---|---|---|
| scanner | ja | true | `handeln.py` | 8/8 Positionen, Menge gedeckt | 14 Kauf + 4 Verkauf |
| omniquant | ja, mit Instrumentsperre | true | `live_perp.py` | - | 2 Eroeffnungen, 31 Fehler historisch |
| moondev_listingarb | Fenster offen, **0** Live-Zeilen | true | `spur_buch` | - | 0 |
| xperp | nein | false | `bot.py` | 2/2 gedeckt | 255, davon 43 nur funding |
| 31 weitere | nein | true | `keiner` | - | - |

Die Spalte, die entscheidet, ist die letzte. **Ein offenes Fenster heisst, dass
eine Spur es koennte - nicht, dass es sich lohnt.** Eine Spur mit 0 Live-Zeilen
hat eine ungetestete Kette, und ihre Behauptung "darf" ist eine Behauptung ueber
Code, den niemand gelaufen ist.

Umgekehrt bleibt eine Spur mit dem besten Excess des Hauses unter Umstaenden
gesperrt - das ist kein Widerspruch, sondern der Unterschied zwischen einer
Messung und einer Freigabe. Der Excess gehoert in die Begruendung, nicht in
die Spalte "darf".

## "War das ein Bug eines Waechters?" - erst die Live-Flags pruefen

Meldet Max einen unerwarteten Verkauf ("Position direkt nach dem Oeffnen mit
Verlust verkauft"), ist die erste Frage NICHT der Waechter-Code, sondern ob
die Spur zu dem Zeitpunkt LIVE war. Ein `schliessen` mit `modus=live` und
`grund=stop` ist die normale Schutzlogik, kein fehlgeleiteter Waechter.

Reihenfolge der Diagnose:

1. **Die Journalzeile mit `modus` und `grund` lesen** - nicht nur die Aktion.
   `modus=live` + `grund=stop` = die Spur hat den Stop ausgefuehrt, weil der
   Kurs ihn beruehrte. `modus=papier` + `grund=stop` = nur im Buch gebucht,
   die echte Position steht noch.
2. **Die Wachen-Flags pruefen, bevor man "Bug" sagt:** `handel_erlaubt`,
   `freigabe.erfuellt`, `trailing_aktiv` in `wachen.json`. Sind alle true,
   war die Spur scharf und der Stop-Ausstieg ist erwartetes Verhalten.
   Eine Annahme "die Spur war doch Papier" ist ein Fehlschluss - die Flags
   sind die Wahrheit, nicht das Gefuehl.
3. **Die Herkunft der Position ansehen.** Eine von Hand auf OKX eroeffnete
   Position wird als `fremdposition_uebernommen` / `herkunft=boerse_handgriff`
   ins Buch geholt und bekommt einen Stop aus der ATR-Rechnung
   (`stop_atr_faktor`). Sie ist damit dem Spur-Stop-Regime unterworfen - ein
   Kursfall unter diesen Stop schliesst sie, auch wenn Max sie selbst
   eroeffnet hat. Das ist die Schutzlogik, nicht ein Bug.
4. **Die Kennungsluecke als eigener Befund nennen.** Der wiederholte Vermerk
   `trailing nicht ausgefuehrt: keine Boersen-Stop-Kennung in der Position`
   heisst: der Stop liegt nur hausintern im Buch, nicht als echter
   OKX-Algo-Stop an der Boerse. Ausgeloest hat ihn der Kursfall, aber der
   Schutz war nicht dort, wo er hingehört. Der Fix ist, beim Uebernehmen
   sofort einen echten Boersen-Stop zu setzen (`okxf.schutz_stop_setzen`),
   nicht den Waechter-Code zu verdaechtigen.

Merksatz: **Ein Live-Stop-Ausstieg ist kein Waechter-Bug.** Die Frage ist
immer zuerst "war die Spur live und hat der Stop gegriffen", dann "warum
fehlte die Boersen-Stop-Kennung".

## Was in diesem Ablauf NICHT geaendert wird

- **`handel_erlaubt`, `freigabe.erfuellt`, Freigabefenster.** Ein Audit liest
  diese Felder. Sie zu setzen ist ein eigener Auftrag mit drei getrennten
  Belegen (Haken, Vorschau mit MAXHIRN_ROUTINE, echter Zyklus im Log).
- **Offene Positionen.** Sie werden gemessen, nie geschlossen - das ist eine
  Order und gehoert in die Freigabekette.
- **`stop_erlaubt` in den Bot-Wachen.**
- **Fremdarbeit im Baum.** Ein Fremdarbeit-Commit kann ein Feature entfernt
  haben, das eine Testsuite braucht (gemessen: `order_stornieren` aus dem
  OKX-Weg entfernt, 19 Tests mit `has no attribute` rot). Das wird als
  Reparatur mit Beleg aufgenommen, im Bericht aber als **Fremdarbeit**
  benannt und nicht als eigener Fund.

## Gegenproben, die diese Runde tragen

- **Ein roter Test in der Suite beweist nicht, dass die eigene Aenderung ihn
  verursacht hat.** Der Beweis ist ein `git stash` nur auf die eigenen Dateien,
  Suite laufen lassen, stash zurueck: sind es OHNE die Aenderung mehr Fehler,
  gehoert der Rest nicht zur Aenderung. Der verbleibende Fehler wird als
  vorbestehend ausgewiesen mit dem Beleg, dass er auch am unveraenderten Stand
  auftritt.
- **Ein Test, der einzeln gruen und im Verbund rot ist, ist ein
  Reihenfolgeproblem im `sys.path`, kein Codefehler.** Zwei Testordner mit
  gleichem Dateinamen (`test_handeln_altlasten.py` unter `scanner/tests` UND
  `xperp/tests`): der erste im Suchpfad gewinnt, und die Assertions des falschen
  Moduls schlagen fehl. Der Pfad der Fehlermeldung ist der Befund.