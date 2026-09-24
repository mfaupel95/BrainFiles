# Schattenarm — eine zweite Messung derselben Spur

Fuer den Auftrag "die Spur handelt nicht / fuellt kein Papierbuch, bau eine
Variante, die Daten erzeugt", und fuer jede Frage der Form "liegt es an den
TOREN oder an der STRATEGIE?". Der Schattenarm faehrt denselben Kern, aber
eigene Buchdateien und (wenn die Quelle ein generierter Bericht ist) eine
eigene Fassung der Tore. Das Hauptbuch bleibt unberuehrt und ist die
Vergleichsgrundlage — ein Vergleich braucht beide Arme, nicht einen.

Vorlage im Haus: `spiegel/spiegel_knapp.py` + `spiegel/spiegel_weit.py`
(Launcher setzen eine Umgebungsvariable und rufen den Kern), umgesetzt fuer
`omniquant` am 24.09.2026 (`omniquant/omniquant_weit.py`).

## 1. Der Kern liest EINEN Arm-Namen — nicht der Launcher

Die Buchdateien entstehen beim IMPORT. Ein Launcher, der spaeter umbiegt, hat
zu spaet gebogen. Also im Kern (z. B. `omniquant/handeln.py`) direkt nach den
Pfadkonstanten:

```python
ARM = (os.environ.get("HANDEL_BUCH") or "").strip()   # "weit" oder ""

def _arm(pfad):            # haengt '.weit' VOR die Endung
    if not ARM:
        return pfad
    stamm, endung = os.path.splitext(pfad)
    return "%s.%s%s" % (stamm, ARM, endung)

WACHEN  = _arm(os.path.join(HIER, "wachen.json"))
ZUSTAND = risikostufe.datei(_arm(os.path.join(HIER, "zustand.json")))
JOURNAL = risikostufe.datei(_arm(os.path.join(HIER, "handelsjournal.csv")))
DEFAULT_BERICHT = os.path.join(HANDEL, "prognose_berichte", _arm("neuester.json"))
```

Reihenfolge `risikostufe.datei(_arm(...))` = erst Arm, dann Risikostufe. Der Arm
laeuft in Basis UND Mittel, seine Dateien heissen also `zustand.weit.json` und
`zustand.weit.mittel.json` — keine Kollision mit dem Hauptarm, aber auch keine
extra Arbeit: die Risikostufe skaliert die Wachen im Speicher, die Wachen-DATEI
bleibt fuer beide Stufen dieselbe.

## 2. Die Startdatei setzt die Variable VOR dem Import

```python
import os, sys
os.environ["HANDEL_BUCH"] = "weit"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import handeln      # noqa: E402
import ereignis     # noqa: E402

def main():
    with ereignis.lauf("handel/omniquant_weit"):
        return handeln._main()      # _main, NICHT main()
```

`handeln.main()` kapselt den Zyklus schon in einen Bus-Lauf; der Aufruf von
`main()` haette den Lauf doppelt gekapselt und einen zweiten Ereignisnamen
erzeugt. Der Bus-Name muss den Arm enthalten (`handel/<spur>_<arm>`), sonst
landen beide Arme unter einem Namen im Journal.

## 3. Weiche Tore: eigene Fassung in der QUELLE erzeugen

Die Tore stehen bei einer Prognose-Spur nicht in der Spur, sondern im Generator.
Deshalb bekommt der Generator einen Fassungs-Schalter statt die Spur einen
zweiten Leser:

```python
FASSUNG = (os.environ.get("PROGNOSE_FASSUNG") or "").strip()

def _fassung(name):
    if not FASSUNG:
        return name
    stamm, endung = os.path.splitext(name)
    return "%s.%s%s" % (stamm, FASSUNG, endung)     # neuester.weit.json
```

- **PUNKT als Trenner, nicht Unterstrich.** Die Buchdateien heissen
  `zustand.weit.json`, `handelsjournal.knapp.csv` — ein `neuester_weit.json`
  waere die dritte Schreibweise im selben Ordner und die erste, die jemand beim
  Suchen uebersieht. Genau daran scheiterte der erste Lauf (Arm suchte
  `neuester.weit.json`, Generator schrieb `neuester_weit.json`, beide Meldungen
  sprachen von "kein Bericht").
- Ohne die Variable aendert sich NICHTS. Das ist die Bedingung dafuer, dass der
  Hauptarm und alle anderen Leser derselben Datei (z. B. ein Papierzweig einer
  anderen Boerse) unberuehrt bleiben.
- Die weiche Fassung ist eine KOPIE der strengen mit geaenderten Zahlen und je
  einem datierten `_`-Vermerk. **Die Score-Schwelle bleibt gleich** — sie ist die
  gemeinsame Messlatte; sonst vergleicht der Arm zwei Dinge zugleich.
- Macht der Generator den ganzen Bericht, gehoert der Schalter in die
gemeinsame Aufgabe, die ihn erzeugt (`prognose-lauf.py`): beide Fassungen
hintereinander fahren, jede einzeln auf Frische pruefen, und den Bericht nur
senden, wenn wenigstens EINE Treffer hat.

## 4. Verdrahtung

1. `dauerlauf.SPUREN`: eigener Eintrag mit **gleichem Ordner**, aber eigenem
   Skript (`{"ordner": "omniquant", "waehrung": "USD", "skript": "omniquant_weit.py"}`).
   Danach zaehlen `spiegelstand.py` und die Auswertungen den Arm mit — deren
   Spurliste kommt per `ast` aus `dauerlauf.py`.
2. `lage.py`: die vorhandene Leser-Funktion um einen `arm`-Parameter erweitern
   (`spur_omniquant(arm="")` mit `suf = (".%s" % arm) if arm else ""` fuer
   Wachen/Zustand/Journal) und eine duenne Wrapper-Funktion ergaenzen. Die
   Bilanzzeile ueber die vorhandene Signatur ziehen:
   `_bilanz("omniquant", ordner, os.path.join(ordner, "handelsjournal%s.csv" % suf))`
   — `_bilanz` hat `ordner`/`journal` genau fuer die Schattenbuecher.
3. `befehle.FAMILIE` um den Arm ergaenzen, sonst fehlt er im Bericht.
4. `.gitignore`: die Laufzeitstaende des Arms sperren, die Konfiguration
   freigeben, mit WILDCARDS fuer die Risikostufen:
   `Agenten/Handel/omniquant/zustand.weit*.json`,
   `Agenten/Handel/omniquant/handelsjournal.weit*.csv`; `wachen.weit.json`
   bleibt ueber die vorhandene `*.json`-Freigabe versioniert. **Eine neue
   DOT-Variante trifft eine vorhandene Freigabe NICHT** (`prognose.weit.json`
   war trotz `!…/prognose*.json` ignoriert) — eigene `!`-Zeile setzen und mit
   `git check-ignore -v --no-index <pfad>` sowie
   `git ls-files 'Agenten/Handel/omniquant/zustand*'` gegenpruefen (die Sperre
   muss gewinnen, die Konfiguration muss erscheinen).

## 5. Tests (die Regel, nicht die Werte)

Ablage `Agenten/Handel/tests/test_<spur>_<arm>.py`, Muster aus dem Haus:

- **Pfade in einem KINDPROZESS erfragen.** Die Konstanten entstehen beim Import;
  ein Test im eigenen Prozess misst die zuerst geladene Fassung. Also
  `subprocess.run([sys.executable, "-c", FRAGE, arm], cwd=SPUR)` mit einer FRAGE,
  die `HANDEL_BUCH` setzt und die vier Basenamen ausgibt.
- **Der Hauptarm bleibt unveraendert** (ohne Variable: `wachen.json`,
  `zustand.json`, `handelsjournal.csv`, `neuester.json`) und **die Arme teilen
  keine Datei** (Schnittmenge der Namen = leer).
- **"Jedes Tor ist weiter"** statt eingefrorener Zahlen: `hoechst_rsi >=`,
  `mindest_cr <=`, `ruecksetzer_bis >=` gegen die strenge Fassung, plus die
  Zusicherung, dass mindestens eines WIRKLICH weiter ist (sonst waere es
derselbe Lauf). Ein Test auf die Zahlen selbst meldet jede spaetere
  Nachjustierung als Fehler, ohne dass etwas kaputt ist.
- **Groessen und Risiko sind gleich** (`max_einsatz_je_position_usd`, `max_offen`,
  `max_gesamt_risiko_usd`, `gebuehr_pct`, `slippage_pct`): nur dann misst der
  Vergleich die TORE. Als Schleife ueber die Schluessel, nicht als vier Bloecke.

## 6. Nachweis

```bash
cd Agenten/Handel/omniquant
MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe handeln.py --vorschau       # streng
MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe omniquant_weit.py --vorschau # weit
MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe omniquant_weit.py --papier   # erster Zyklus
MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe omniquant_weit.py --papier   # Gegenprobe
cd .. && MAXHIRN_ROUTINE=1 scanner/.venv/Scripts/python.exe spiegelstand.py
```

Erwartet: der strenge Arm nennt seine Zahl (oft 0), der weiche mehr; der erste
Papierlauf bucht Positionen, der zweite kauft NICHTS nach (die Kandidaten
erscheinen als "gefiltert"); `spiegelstand.py` zaehlt den Arm mit und meldet
byte-gleich.

## Vorher: warum fuellt die Spur ueberhaupt nicht?

Der Arm ist die zweite Messung, nicht die erste Diagnose. Erst die drei Zeugen
lesen, sonst baut man einen Schattenarm fuer ein Problem, das keines ist:

1. **Welches Tor schliesst als erstes?** Die Spur mit der Umgebung des
   Dauerlaufs aufrufen (`MAXHIRN_ROUTINE=1 … --vorschau`) — die Sperrzeile nennt
   einen Grund. Danach jede Schwelle einzeln gegen den GEMESSENEN Wert des
   Instruments halten, nicht gegen ein Gefuehl.
2. **Gibt es ueberhaupt Einstiegszeilen?** Das JOURNAL lesen, nicht
   `zustand.json`. Ein Buch, das am Tagesende flach ist, ist bei einem
   Tagesmuster (Opening Range u. a.) die BAUART, kein Defekt — eine Schwelle
   aufzuweichen, weil "gerade keine Position" dasteht, erzeugt Daten, die nichts
   messen.
3. **Ist eine Zustandsquelle alt?** Haengt die Spur an einem generierten
   Bericht, ist dessen KADENZ das Tor, nicht das Signal (ein sieben Tage alter
   Bericht ist kein Signal; ein fehlender Cron ist ein Betriebsfehler).

Dann erst entscheiden: **Kadenz reparieren** (billigste Aenderung, oft die
richtige), **Tor mit Zahlen verschieben** (Verteilung ueber mehrere Tage messen,
die neue Schwelle ueber den KOSTEN halten — der Spread frisst sonst genau die
Bewegung, die das Tor abbilden soll) oder **Schattenarm bauen** (wenn die
strenge Fassung fuer andere Leser unangetastet bleiben muss).

**Ein historisches Urteil ist keine Messung.** Eine Kennzahl wie "traegt auch
bei 0 % Gebuehr nicht" kann vollstaendig auf `herzschlag`-Ausstiegen beruhen
(Betriebsausfall, keine Handelsentscheidung, `Handel/stoerungen.py`). Vor dem
Weitererzaehlen die Journalzeilen ansehen (`grund`/Ausstiegsspalte); steht die
Zahl auf Zwangsschluessen, ist genau das der Grund fuer einen ehrlichen Lauf.

## Pitfalls

- **Die strenge Fassung NIE an Ort und Stelle aufweichen.** `prognose.json` wird
  auch von anderen Lesern benutzt (Papierzweig einer zweiten Boerse); eine
  Aenderung dort verstellt fremde Messungen. Zweite Datei, zweiter Arm.
- **`dauerlauf.py` wirkt erst nach einem Neustart** (die Tabelle wird beim Start
  gelesen); ein Fix im Spuren-Skript dagegen im naechsten Zyklus. Deshalb den
  ERSTEN Zyklus des Arms von Hand fahren und belegen — sonst ist die Wirkung
  nicht sichtbar und der Arm wartet unbemerkt auf einen Neustart. Den laufenden
  Dauerlauf nicht mitten im Zyklus neu starten, wenn Live-Spuren Positionen
  offen haben (Doppelorder-Risiko): den Neustart anbieten, nicht erzwingen.
- **Kein zweiter Zeitplan fuer denselben Arm.** Ein Cron zusaetzlich zum
  Dauerlauf schreibt in dieselben Buecher (read-modify-write) — ein Buch, EIN
  Schreiber.
- **Ein Fehlertext, der einen festen Dateinamen nennt, ist kein Beleg.**
  "kein Bericht (prognose_berichte/neuester.json fehlt)" stand im Code hart
  verdrahtet, waehrend der Arm in Wahrheit `neuester.weit.json` suchte — die
  Meldung liess den Fehler im Hauptarm vermuten. Beim Bauen den Pfad aus der
  Konstante in die Meldung setzen (`os.path.basename(DEFAULT_BERICHT)`).
- **Ein Arm ist keine zweite Strategie.** Fahren zwei Arme dieselbe Quelle mit
  denselben Instrumenten und derselben Ausstiegsform, messen sie EINE Wette
  zweimal. Vergleichbar werden sie durch unterschiedliche TORE (hier) oder
  unterschiedliche AUSSTIEGSZAHLEN (Trailing-Trigger, Abstand, Frist) — nicht
  durch einen anderen Ticker auf derselben Basis.
