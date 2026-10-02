# Neue klassik-Papierspur aus einer Pine-Vorlage

Wenn Max eine Pine-Strategie reicht ("neue Strategie"), entsteht daraus eine
WEITERE klassik-Spur: gemeinsame Rechnung in `Handel/klassik_regeln.py`, Buch
`spur_buch.py`, Papier, kein Live-Zweig, 4H BTC/ETH/SOL-USDT-SWAP. Vorbild ist
der juengste `klassik_*`-Ordner (dessen handeln.py/wachen.json/README.md
kopieren und anpassen). Die Familie ist ein ZWEIG des allgemeinen Neubauwegs
`references/neue-spur-ende-zu-ende.md` - hier nur das, was KLASSIK-spezifisch
ist.

## Reihenfolge

1. Vorlage nach `MaxHirn/Wiki/Handel/<name>.pine` (Kopf `//@version=6`
   ergaenzen). Die .pine-Dateien sind BEWUSST nicht versioniert (nur
   `MaxHirn/Wiki/**/*.md` ist freigegeben) - sie liegen wie die bestehenden
   nur lokal, kein .gitignore-Eintrag noetig.
2. Regel in `klassik_regeln.py`: `einstieg_<name>(k, w)` -> "long"|"short"|None
   und ein Ausstieg. Kennt die Vorlage keinen eigenen `strategy.close`, ist
   `_gegen_kreuz(einstieg_<name>)` der Ausstieg: der Break auf der Gegenseite
   schliesst die Position. REGELN-Eintrag ergaenzen, Modulkopf-Docstring
   mitziehen.
3. Spur-Ordner: `handeln.py` ruft `spur_main("<name>", HIER,
   bus_name="handel/<name>")` - der Bus-Name steht WOERTLICH in der Datei
   (die Bus-Suite prueft genau die gestartete Datei). `wachen.json` als Kopie
   der juengsten klassik-wachen: Risiko 5 USD x 3 Plaetze, stop 3.0 % im Band
   1.8-6.0, ziel 2R, Ratsche 15.0 = Buchrisiko, kill 45.0, gebuehr_taker
   0.0005, journal_zweitziel `Q:\Handel_Journal\<name>`, handel_erlaubt=false,
   freigabe.erfuellt=false. README.md.
4. Verdrahtung - ACHT STELLEN, alle Pflicht, ueberall dieselbe Liste
   ergaenzen: `dauerlauf.SPUREN`; `lage.py` KLASSIK_SPUREN-Tupel
   (HOLER + befehle-Aufloesung wachsen automatisch aus dem Tupel);
   `befehle.py` FAMILIE ("Indikator") UND INDIKATOREN-Liste (zwei Stellen);
   `auswertung_alle.py` KLASSIK-Liste; `pruefe_ratschen.py`
   (scanner/wachen_pruefung); `.gitignore` (5 Zeilen: `!*.py`, `!*.md`,
   `!wachen.json`, dann `zustand.json` und `handelsjournal.csv` sperren - die
   `.mittel`/`.hoch`-Zustaende deckt die Sammel-Sperre
   `Agenten/Handel/*/zustand.*.json`); Wiki Spuren-Uebersicht (Tabelle UND
   Fliesstext, dort steht "acht" - regelbasiert "die klassik-Spuren"
   formulieren). Gegenprobe nach der Spur-Anlage: `git add --dry-run` auf die
   drei Spur-Dateien muss `add ...` sagen, `git check-ignore -v` auf
   zustand.json/mittel/hoch muss treffen.
5. Tests: neue Klasse in `tests/test_klassik_regeln.py`. Die Vertraege in
   `tests/test_klassik_spuren.py` laufen automatisch mit (SPUREN-glob
   `klassik_*` nimmt den Ordner mit) - die Mengengleichheit Ordner <-> REGELN
   ist die Wahrheit, eine feste Spurenzahl ist KEINE Eigenschaft und wird nie
   eingefroren (siehe `references/test-friert-stand-ein.md`). Traegt die neue
   Regel eigene Indikatorfelder in der wachen, muessen NOETIGE_FELDER und
   `mindestens()` erweitert werden (Pivot-Fenster = pivot_left + pivot_right
   + 1; sonst prueft der Vertrag die Kerzenzahl der neuen Regel nicht).
6. Beleg ohne Buch: `handeln.py --vorschau` (Sperrentext) plus ein rein
   lesendes Signal-Zaehlen ueber echte OKX-Kerzen - je Praefix
   `signal({"kerzen": k[:n]}, w)` zaehlen und die letzten Treffer anzeigen.
   Das zeigt, dass die Regel lebt (in einem Aufwaertstrend z. B. nur longs),
   ohne ein Journal zu schreiben.
7. Dauerlauf-Neustart aller drei Stufen (references/dauerlauf-neustart.md),
   dann `<name> (papier) ok` im Log und der Q:-Spiegel der neuen Spur
   (`Q:\Handel_Journal\<name>` mit zustand.json je Stufe). Commit + Push;
   nur eigene Pfade stagen, die Wiki-Uebersicht als Folge-Commit.

## Pine -> Python: die Fallen der Pivot-Vorlage

- `ta.pivothigh(left, right)` schreibt den Hochwert der Kerze `i-right` erst
  am Bar `i` in die Serie (Bestaetigung nach `right` Bars); `fixnan` haelt den
  letzten Wert; `[1]` verschiebt die Serie um einen weiteren Bar. Umsetzung:
  Schleife mit Kandidat `j = i - right`, Ergebnis beider Listen mit
  `[None] + liste[:-1]` geschoben.
- **Der Kandidat muss aus dem Vergleichsfenster ausgeschlossen werden**
  (`range(j-left, j+right+1)` nur `if m != j`): mit dem eigenen Hoch im Fenster
  ist `h > max(...)` IMMER falsch und kein Pivot wird je erkannt. Gleichstand
  zaehlt nicht (Pine: streng hoeher/tiefer).
- Volumen-Oszillator `100 * (ema(kurz) - ema(lang)) / ema(lang)`: die
  hauseigene ema() startet mit dem SMA-Seed wie Pine; `b == 0` oder None wird
  None, nie 0.0.
- Die Wick-Formen sind Einstiege OHNE Volumenfilter, die Break-Formen
  brauchen den Oszillator ueber der Schwelle. Die Kerzenform schaltet um:
  unterer Docht `open-low > close-open` (long), oberer Docht
  `open-close < high-open` (short). Beide Varianten sind Long bzw. Short - die
  Vorlage zeichnet sie nur mit verschiedenen Labels.

## Test-Fixture-Muster

- Kleine Pivots im Test (`w = {"pivot_left": 2, "pivot_right": 2}`) halten
  die Serie kurz und deterministisch; die Standardwerte 15/15 brauchen ~31
  Kerzen Vorgeschichte.
- Der Fixture-Helfer bekommt die Endkerze als FERTIGE Liste
  (`k.append(endkerze)`), nicht als Callable - ein Aufruf `endkerze(13)`
  bricht mit TypeError.
- Wick-Fixtures brauchen explizite o/h/l/c - der Standard-Helfer
  `kerzen(closes)` baut o=c und kann keinen Docht bilden.
- Gegenproben je Regel: Spitze ohne Volumen -> kein Break; Schwelle aus der
  wachen wirkt (`dict(W, volumen_schwelle=200.0)`); kein Kreuz -> None;
  Ausstieg ist das Gegensignal (long-Serie endet bei short-Serie).

## Werkzeug

Nach einem `cd` im terminal-Werkzeug relative Pfade an patch/write_file meiden
(das Tool loest sie gegen das Session-cwd auf - `Agenten/Handel/...` wird zu
`Agenten/Handel/Agenten/Handel/...` und die Datei ist nicht lesbar): immer
absolute `C:/Users/...`-Pfade verwenden.
