# Stille Spuren deuten (bucht wenig oder nichts - Defekt oder Strategie?)

Ausloeser: "Welche Spuren sind still?", "warum steigt die nie aus?", eine
Uebersicht zeigt 0 Ausstiege, oder `auswertung_alle.py` meldet "nur N Runden:
das ist ein Befund, keine Messung".

Abgrenzung: geht es um eine Spur, die GAR NICHT bucht, obwohl `zustand.json`
frisch ist -> `betriebsfehler-spuren.md` (kaputtes wachen.json, Absturz im
Zyklus, `signal()` bildet nie ein Signal). Hier geht es um den haeufigeren
Fall: die Spur arbeitet, sieht aber still aus.

## Ein Etikett nennt den ZUSTAND, ein zweites die AENDERUNG — nie beides in einem Wort

Max liest die Uebersichtszeilen woertlich: „7 Spuren still: … (papier) …
handel_erlaubt=false" wurde als „die sind abgeschaltet" gelesen, obwohl alle sieben
im Papier liefen. Zwei verschiedene Fragen steckten in einer Zeile:

- **„(papier)"** = der MODUS einer Spur.
- **„still"** = der UNTERSCHIED zum letzten Bericht (`rang() == 3`: kein Fehler,
  keine neue Runde, keine neue oder weggefallene Position). Eine stille Spur
  laeuft weiter — sie hatte nur nichts Neues.

Regel: eine Zeile, die Zustand und Aenderung in EIN Wort legt, erzeugt genau diese
Rueckfrage. Die Sammelzeile nennt die Bedeutung jetzt selbst
(„still = kein Fehler und nichts Neues seit dem letzten Bericht — die Spuren laufen
weiter"); wer sie aendert, prueft, ob beide Aussagen noch lesbar sind.

**Dieselbe Verwechslung im `dauerlauf.log`:** `<spur> (live) ok` ist die ANGEFORDERTE
Betriebsart des Dauerlaufs (er entscheidet sie allein aus dem offenen Freigabefenster),
nicht die Wirkung. Ob die Spur wirklich live geht, entscheidet ihr eigener Riegel
(`wachen.json handel_erlaubt`); sie schrieb selbst „--live angefordert, aber gesperrt:
wachen.json handel_erlaubt=false — es wird Papier gehandelt", waehrend das Log `(live)`
sagte. Gemeldet wird deshalb die WIRKUNG (`_meldungsmodus(modus, ordner)` druckt
`(papier)`, wenn `handel_erlaubt` false ist) — der AUFRUF bleibt der angeforderte
Modus, sonst aendert sich das Verhalten der Spur still (die Buchbereinigung laeuft nur
im Live-Zweig). `istatty`/Konfiguration zu lesen ist kein Beleg fuer den Modus; die
Vorschau-Zeile der Spur mit `MAXHIRN_ROUTINE=1` ist einer.

## Werkzeug statt Handarbeit (Dauerauftrag Max, 21.09.2026)

Die Pruefung ist gebaut und angebunden - nicht jedes Mal neu skripten:

- `Agenten/Handel/stille_spuren.py` - Bericht ueber ALLE Spuren aus
  `dauerlauf.SPUREN`; `--kurz` nur Auffaelliges, `--wache` schweigt bei
  Gesundheit (Watchdog-Muster).
- `Agenten/Hermes/scripts/stille-spuren-wache.py` + Cron `stille-spuren-wache`
  (alle 2 h, no_agent, Telegram). Meldet NUR `TOT` und `UEBERFAELLIG`.
- Tests: `Agenten/Handel/tests/test_stille_spuren_werkzeug.py` (eigener Name -
  `tests/test_stille_spuren.py` gehoert zur Berichtszeile des Tagesberichts).

Regel aus dem Auftrag: solche Pruefungen gelten **fuer alle Spuren und alle
kuenftigen**. Deshalb Spurliste bei JEDEM Lauf frisch aus `dauerlauf.SPUREN`
lesen, nie eine eigene Namensliste pflegen - eine neue Spur erscheint dann von
selbst (belegt: der erste Lauf fand 30 statt der erwarteten 29 Spuren,
`trendwende_btc` war neu dazugekommen). Ein Test nagelt das fest.

Aus-/Einstiegswoerter NIE neu definieren, sondern `stoerungen.teile(spur)`
benutzen - die eine Hausdefinition. Sie kennt die `orbk`/`orb`-Eigenheit
bereits; eine eigene Zaehlung ueber `aktion` weist diese Spuren
faelschlich als still aus (genau dieser Fehler entstand hier im Wegwerfskript
und verschwand mit `stoerungen.teile`).

Weitere Fallen, beide gemessen: `positionen` ist bei `orbk` ein **Dict**
(genau ein Platz), sonst eine Liste - `isinstance(..., dict)` abfangen, sonst
zaehlt Python die Schluessel. Und die nautilus-Felder heissen
`preis_einstieg` / `letzter_kurs` / `hoechster_kurs` / `stop_preis` / `frist`;
wer `einstieg`/`hoch` raet, bekommt ueberall 0 und damit den Scheinbefund
"Einstieg 0, kaputt", obwohl die Positionen gesund sind.

Jede Wache in beide Richtungen beweisen: einmal gesund (0 Zeichen Ausgabe) und
einmal mit kuenstlich verstelltem Zustand (Alarm), danach zuruecknehmen.

## `--vorschau` zeigt bei Eigenspuren KEINE Signale — `--papier` verwenden

Viele handgeschriebene Spuren (supertrend, macd_mtf, squeeze, wavetrend) tun
in `--vorschau` sofort `return` nach `print("Vorschau: keine Dateien geschrieben.")`
— **ohne Kerzen zu laden oder Signale zu rechnen**. Der Modus ist dort nur eine
"nichts schreiben"-Markierung, kein Diagnosemodus. `--vorschau` auf diesen Spuren
zeigt immer Stille, egal ob ein Signal vorliegt oder nicht.

`--papier` laedt Kerzen, rechnet Indikatoren und gibt `EINSTIEG LONG/SHORT ...` aus
— oder schweigt, wenn kein Signal vorliegt. Das ist die einzige Methode, die den
Signalstatus dieser Spuren zeigt.

Ausnahme: Spuren auf Basis von `spur_buch.zyklus` (moondev_\*, iv_wand, iv_waelle,
liq_wand, trendwende_btc) drucken in `--vorschau` echte Signale
(`Vorschau: Einstieg waere LONG XMR`) und dann die Sperrliste
(`Live waere gesperrt durch: ...`). Dort taugt `--vorschau`.

Faustregel: wenn `--vorschau` bei einer stillen Spur keine Sperrliste druckt,
ist es eine Eigenspur — `--papier` einmalig laufen lassen um das Signal zu sehen.

## Eine Spur stilllegen: ZWEI Schalter, und der Erklaertext im selben Schritt

Der Gegenauftrag ("<spur> stillegen bis eine Messung da ist") ist NICHT mit
`handel_erlaubt: false` erledigt:

1. **Beide Schalter setzen** - `handel_erlaubt: false` UND `stillgelegt: true`.
   `handel_erlaubt` allein nimmt nur den Live-Weg; der Papierlauf laeuft weiter
   und kauft in das gemeinsame Buch. Genau dieser Papierbestand ist es, den der
   naechste Live-Lauf als Altlast ausbucht (`bueche_papier_altlasten_aus`, nur
   `if live:`) - jede solche Ausbuchung steht als `buchbereinigung` im Journal
   und zaehlt in der Störungsstatistik mit. Ein einziger Schalter erzeugt also
   im Kreis neue "Betriebsstoerungen", waehrend die Spur als stillgelegt gilt.
2. **Den Erklaertext im selben Schritt nachziehen** (`_stillgelegt`,
   `_stillgelegt_bis_messung`): ein Feld, das eine ueberholte Begruendung traegt,
   ist schlimmer als keines - der naechste Leser entscheidet danach.
3. **Verweigerung in BEIDEN Modi belegen:** `--papier` UND `--live` muessen
   ablehnen (Exit 0, mit Klartext), dazu `0 offene Positionen` im Buch. Ein
   Zustand allein ist kein Beleg.

**Zahlen einer stillgelegten Spur vor dem Urteil trennen.** Die gezaehlten
"Betriebsstoerungen" mischen zwei ganz verschiedene Ursachen:
`herzschlag_alt` (Zwangsschluss, weil der Zustand zu alt war - vor der
Herzschlag-Regel ein Altbestand) und `buchbereinigung` (aus dem Kreislauf
oben). Erst nach `grund` aufschluesseln, dann deuten; die Zahl selbst sagt
nichts ueber die Strategie. Wiedereinschalten: Entscheidungsbaum unten.

## Stille Spuren einschalten: Entscheidungsbaum

Auftrag "stille Spuren untersuchen und einschalten" bedeutet: diagnostizieren,
dann alle bereitgestellten Spuren scharf stellen, ohne nachzufragen.

1. **Signal prufen** (s. o.: `--papier` fuer Eigenspuren, `--vorschau` fuer
   spur_buch-Spuren). Kein Signal heute → Spur wartet korrekt.

2. **Live-Pfad prufen:**
   `grep -c 'markt_kauf\|AddOrder\|place_order\|/trade/order' <spur>/handeln.py`
   (ohne tests/). 0 Treffer = Papier-only, kein Einschalten moeglich.

3. **`handel_erlaubt` blockiert Papier:** Bei spur_buch-Spuren sperrt
   `handel_erlaubt: false` AUCH den Papierlauf (`spur_buch.sperren_live()`
   laeuft bei `--live`). Bei handgeschriebenen Eigenspuren hat `handel_erlaubt`
   haeufig gar keine Wirkung auf Papier — dort laeuft der Papierlauf schon.

4. **Einschalten** (Spur hat Live-Pfad und nur Fenster fehlt):
   - `handel_erlaubt: true` in `wachen.json`
   - `freigabe.erfuellt: true` (von Hand gesetzter Haken, mit datiertem Vermerk)
   - Herzschlag-Reset wenn `letzter_lauf` > herzschlag_max_minuten alt
   - Eintrag in `dauerlauf.AUTO_FREIGABE` (damit der Dauerlauf ohne `/ja` selbst
     oeffnet, sobald nur das Fenster fehlt)
   - Dauerlauf neu starten NUR wenn `AUTO_FREIGABE`-Tupel oder Code geaendert

5. **Kein Signal** → warten. Nicht scharf stellen, weil kein Einstieg sichtbar;
   der naechste Zyklus handelt automatisch sobald das Signal kommt.



| Lage | Merkmal | Urteil |
|---|---|---|
| wartet auf das erste Signal | kein Journal, `zustand.json` frisch (< 2 h) | gesund |
| haelt Positionen | Einstiege > 0, Ausstiege = 0, Stop+Ziel gesetzt, Position jung | gesund |
| Ausstiegsschwelle unerreichbar | Positionen alt, Peak weit unter der Trailing-Schwelle | **Befund** |
| laeuft nicht | kein Journal, Zustand alt oder fehlt | **Betriebsfehler** |

## Reihenfolge

1. **Spurliste aus `dauerlauf.SPUREN` lesen, nie aus dem Kopf.** Es ist ein
   dict `{name: {"ordner":..., "skript":...}}` und enthaelt Funktionsaufrufe
   (`os.path.join` fuer eigene venvs) - `ast.literal_eval` auf den ganzen
   Knoten scheitert mit `malformed node`. Schluessel und `ordner`/`skript`
   einzeln aus dem AST ziehen. Mehrere Spuren teilen sich einen Ordner
   (`nautilus_kraken` und `nautilus_kraken_futures`): der ORDNER zaehlt fuer
   die Dateien, der NAME fuer die Meldung.

2. **Journal zaehlen - aber nicht jede Spur schreibt `aktion`.** Einstiege
   `kauf/eroeffnen/KAUF/EINSTIEG`, Ausstiege `verkauf/schliessen/AUSSTIEG/
   ausgang`. `orbk` und `orb` haben GAR KEINE aktion-Spalte, sondern je Runde
   eine Zeile mit Ausgangsgrund (`...,ziel,...` / `...,stop,...`). Eine
   Zaehlung ueber `aktion` weist sie faelschlich als "still" aus, obwohl sie
   abgeschlossene Runden haben. Vor jedem Stille-Urteil die letzten Zeilen des
   Journals ansehen - das Format ist je Spur verschieden.

3. **Bei offenen Positionen die ECHTE Ausstiegsfunktion befragen**, nicht die
   Formel nachbauen (sonst prueft man die Nachbildung):
   `trailing_stop_strategie.ausstiegsgrund(p, kurs, jetzt, w)`.
   Braucht das nautilus-venv: `Agenten/Handel/nautilus/.venv/Scripts/python.exe`
   - mit dem scanner-venv scheitert schon der Import (`nautilus_trader`).

4. **Feldnamen aus dem Zustand lesen, nicht raten.** Die nautilus-Arme fuehren
   `preis_einstieg`, `letzter_kurs`, `hoechster_kurs`, `stop_preis`, `frist`,
   `eroeffnet` - NICHT `einstieg`/`hoch`. Ein geratener Name liefert `0`, und
   daraus wird ein Scheinbefund ("alle Positionen bei 0, Ausstieg kaputt"),
   der in Wahrheit nur ein Tippfehler ist. Einmal `zustand.json` roh ansehen,
   dann rechnen.

5. **Erst jetzt urteilen.** Aussagekraeftig sind drei Abstaende je Position:
   Gewinn gegen Einstieg, Peak gegen die Trailing-Aktivierung, Kurs gegen
   Stop, dazu die Restfrist.

## Der wiederkehrende echte Befund: unerreichbare Trailing-Schwelle

Gemessen 21.09.2026 an 8 offenen Positionen der nautilus-Arme: alle im Plus
(+5,9 bis +11,6 %), 32-39 % ueber dem Stop, Peak +6,2 bis +12,0 % - die
Trailing-Aktivierung steht bei +30 %. Keine Bedingung greift, also passiert
korrekt nichts. Der wirkliche Ausstiegsmechanismus ist die FRIST.

Das ist kein Defekt, aber auch kein gewollter Zustand: eine Schwelle, die das
Instrument in der Haltedauer nie erreicht, ist wirkungslos. Pruefen mit der
eigenen Historie (welchen Peak erreichen die Positionen tatsaechlich?), dann
die Schwelle an die gemessene Bewegung setzen - nicht an die erhoffte.

Merksatz: eine Ausstiegsregel, die nie ausloest, ist keine Regel. Wenn alle
Runden ueber die Frist enden, ist die Frist die Strategie - dann gehoert sie
ausgesprochen oder die Schwelle gesenkt.
