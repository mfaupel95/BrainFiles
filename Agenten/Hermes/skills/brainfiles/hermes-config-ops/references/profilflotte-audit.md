# Profilflotte pruefen und reparieren (viele Profile auf einmal)

Diese Flotte hat 29 Profile (ein Bot je Fremd-Repo unter `profiles/<name>/`). Jedes
ist eine **Insel**: eigene `config.yaml`, eigene `.env`, eigenes `auth.json` - es wird
NICHTS vom Startprofil geerbt. Genau daran scheitern die meisten "Bot antwortet
nicht"-Faelle, nicht an den Kanaelen.

## Reihenfolge: erst Symptom, dann Ursache

1. `hermes profile list` - die Warnungen betreffen nur die **Kanaele** (doppelte
   Telegram-/Photon-Kennung). Das ist nicht kosmetisch (ein zweites Gateway auf
   demselben Token nimmt dem ersten die `getUpdates` weg), macht den `/bot`-Weg
   aber nicht kaputt. Nicht mit der Antwort-Ursache verwechseln.
2. Antwortet ein Bot nicht, ist die Ursache fast immer die **Modellkennung**.
   Ein echter Aufruf sagt sie namentlich:
   `hermes -p NAME chat -q "Antworte nur mit dem einen Wort: fertig" -Q`
   (z. B. `Hermes is not logged into Nous Portal.`).
3. Faellt der Primaerpfad aus, entscheidet die geerbte `fallback_providers`-Kette
   den FEHLERTEXT. Deshalb zuerst den Ketten-Block des Profils lesen, bevor der
   Provider verdaechtigt wird: ein Eintrag auf ein lokales 8k-Modell ergibt
   „context window ... below the minimum" und verdeckt damit den Anmeldefehler.
4. Erst danach Einzelprofile befragen - jeder Aufruf kostet 30-60 s Kaltstart.

## Ein Befehl statt 29 Aufrufe

`skills/brainfiles/hermes-config-ops/scripts/profilflotte-bericht.py` (mit dem
venv-Python von `hermes-agent`, `HERMES_HOME` gesetzt). Es liest nur Dateien und
zeigt je Profil: Modell, hinterlegte Anmeldung, Zahl der Kanalzeilen, Groesse der
Kette und einen Befund; `--nur-probleme` kuerzt auf die auffaelligen Profile. Es
schreibt nichts.

## Vor der Massenaktion: die Einrueckung messen, nicht annehmen

Diese Flotten-Configs sind **gemischt eingerueckt**: Top-Level-Schluessel wie
`delegation:` stehen in Spalte 0, ihre Skalarfelder mit **zwei** Leerzeichen
darunter, Unterfelder von Unterfeldern mit vier. Ein Ersatzzblock, den man nach
dem Muster der Hauptconfig schreibt (Top-Level-Schluessel + vier Leerzeichen),
bricht neben diesen Dateien die YAML-Auswertung:

```
expected <block end>, but found '<block mapping start>'
```

Das ist der teuerste Fehler der ganzen Sektion, weil er **stillschweigend
schreibt**: die Datei ist danach groessenteils ok, nur der ersetzte Schluessel ist
zu einem String geworden - die Gegenprobe `yaml.safe_load` schlaegt erst **nach**
dem Schreiben fehl, zu spaet fuer das Assert auf den Zielwerten. Deshalb zwei
Gates in dieser Reihenfolge:

1. **Den Ersatzzblock ALLEIN gegen `yaml.safe_load` pruefen**, bevor eine Datei
   angefasst wird: `yaml.safe_load("\n".join(neuer_block))`. Faellt er hier,
   ist noch nichts kaputt.
2. **Die Einrueckung aus der Zieldatei ableiten, nicht aus der Hauptconfig.** Die
   Einrueckung des Ersatzzblocks ist der *Inhalt* des Problems: Skalarfelder auf
   derselben Tiefe wie im Ziel, Listenelemente darunter eine Ebene tiefer, ein
   Kommentar auf der Tiefe des Blocks.

Nach dem Lauf **alle** Configs parsen und den Zieltyp asserten, nicht nur die
geaenderten - `assert isinstance(cfg["delegation"], dict)`. Ein Skalar, der wie
ein Block aussieht, ist das einzige Anzeichen.

Sind Dateien trotzdem gekippt: jede byteweise aus `<datei>.bak-JJJJMMTT`
zurueckspielen und `git status --porcelain -- <pfad>` als Gegenprobe lesen. Das
geht in Sekunden und ist billiger als jede Reparatur am Text.

## Der Befund, der beim Nachziehen auffaellt und nicht im Auftrag stand

Beim Uebertragen einer Hauptprofil-Konfiguration auf die Flotte ist der
wichtigste Befund selten die Modelleinstellung, sondern eine **Luecke in der
Ausnahmeregel**: wer seinen Provider fest **pinnt**, erbt die Hauptkette nicht
mehr (`scoped_fallback_chain` gibt einem gepinnten Kind die geerbte Kette nicht
mit). Ein Profil mit `delegation.provider` und **ohne eigene**
`delegation.fallback_providers` hat damit **gar keinen Rueckfall** - es sieht
vollstaendig konfiguriert aus und ist es nicht.

Pruefung, ein Muster fuer die ganze Flotte:

```python
gepinnt = bool(dl.get("provider")) or bool(dl.get("model"))
eigen   = dl.get("fallback_providers")
if gepinnt and not eigen:
    ...   # echte Luecke, kein kosmetischer Befund
```

Die zweite Luecke derselben Art: ein Aufgaben-Block auf `auto` erbt das
**Hauptmodell des Profils**. Wo dieses ein reines Textmodell ist, ist die
Konfiguration fuer Bild- oder Strukturaufgaben wertlos - korrekt verdrahtet und
doch unbrauchbar.

### Der Provider-Pin ist erst nach dem Aufruf-Ausschluss wert

Bevor "auf nous umstellen" geschrieben wird, **jeden behaupteten Provider
wirklich rufen** - ein toter Zweig ist kein Verdacht, sondern ein Befund mit
Fehlertext:

```python
# GET-Liste zuerst: existiert der Zweig ueberhaupt?
# dann jeder Kandidat einzeln, Key aus der .env, Antwort-Inhalt pruefen
```

Gemessen fielen dabei zwei Sorten heraus: `401 "No active credentials for
provider: X"` (der Zweig braucht eine Anmeldung, die er nicht hat) und `403`
(ein Freemodell, das nur innerhalb seines Anbieters funktioniert). Beides heisst
**nicht**, dass der Provider tot ist - es heisst, dass er nicht nutzbar ist.
Der Unterschied entscheidet die Art der Reparatur: Anmeldung nachziehen
(Provider bleibt) oder auf einen anderen Provider umstellen (Block darf als
Verkabelung fuer den spaeteren Fall liegen bleiben, wird aber nicht mehr als
Aktivposten gefuehrt).

Die Reihenfolge ist damit: **messen, dann umstellen** - und im Bericht die
Fehlertexte nennen, die zur Entscheidung gefuehrt haben. "Der Router ist tot"
ist eine Behauptung; "401 fuer Ollama, 403 fuer oc/big-pickle, 200 fuer nous
in 2,1 s" ist ein Befund.

### Was ein Massenlauf aus einer falschen Absicht nicht mitnehmen darf

Beim Uebertragen einer Hauptprofil-Konfiguration auf die Flotte steht neben dem
Umstellen eine Liste von Werten, die **richtig aussehen und trotzdem nicht
umgestellt** gehoeren. Diese Liste gehoert in den Auftrag und in den Bericht,
sonst wandert der naechste Auftrag mit:

- `cache_ttl: 5m` auf einem maschinell getakteten Profil (`auto` gaebe ihm
  ohnehin 5m) - eine Aenderung ohne Wirkung ist eine zweite Wahrheit.
- `compression.threshold` auf einem Profil mit kurzen Sitzungen: eine Schwelle
  nahe 0.7 schaltet die Kompression praktisch ab, statt sie zu tunen.
- Ein Preset-Block, den das Profil gar nicht hat: MoA auf einem Bot-Profil ist
  eine MoA-Verdrahtung, keine Profilverdrahtung.

Der Nachweis, dass man die Absicht getroffen hat, ist eine **Gegenprobe am
Zielzustand**: je Wert pruefen, dass er in der Flotte UNVERAENDERT ist, und diese
Pruefung im Bericht nennen. Eine Massenaenderung, die belegt was sie tat, aber
nicht was sie liess, ist halb geliefert.

## Beheben: drei Befunde, drei Werkzeuge

| Befund (aus dem Bericht) | Werkzeug | Wirkung |
|---|---|---|
| Kanalzeile doppelt zum Startprofil | `Agenten/Hermes/scripts/profil-kanaele-bereinigen.py` | Telegram-/Photon-Zeilen strippen |
| keine Modellanmeldung / Provider ohne Zugang | `Agenten/Hermes/scripts/bot-modell-auf-router.py` | `model.provider=omniroute`, `model.default=auto/best-coding` |
| Kette nennt Kleinmodell | `Agenten/Hermes/scripts/bot-rueckfallkette-bereinigen.py` | Block byte-genau entfernen |

Alle drei haben dieselbe Bedienung: **ohne Argument Trockenlauf**, `--anwenden`
schreibt, `--zuruecknehmen` holt die Sicherung zurueck; je Profil entsteht
`<datei>.bak-JJJJMMTT`; sie sind idempotent, ein Abbruch mittendrin ist also
einfach ein Neustart. Erledigte Profile melden sie als "schon umgestellt" und
nennen je uebersprungenem Profil den GRUND.

Reihenfolge: Kanaele -> Modell -> Kette. Der Modellwechsel macht die Bots erst
antwortfaehig; die Kette danach nur die Fehlermeldung ehrlich.

## Nachweis-Leiter (jede Stufe ist ein echter Lauf, keine Beschreibung)

1. `hermes profile list` zeigt 0 Warnzeilen.
2. **Gegenprobe:** `--zuruecknehmen` -> Warnungen sind wieder da -> `--anwenden`
   -> 0. Das beweist, dass die Aenderung die Wirkung ist, nicht der Zufall.
3. **Live je Muster:** `hermes -p NAME chat -q "Antworte nur mit dem einen Wort:
   fertig" -Q` -> `fertig`. Stichprobe genuegt (die Profile sind Klone), aber je
   einmal: vorher kaputt, wiederhergestellt, Sonderfall.
4. `git diff --numstat <pfad>` **je Datei** pruefen, nicht die Summe: 2
   Einfuegungen / 3 Loeschungen = Modellwechsel (die `base_url`-Zeile entfaellt),
   8/0 = eingefuegter Block, 0/7 = entfernte Kette. Ein Diff, der wie die ganze
   Datei aussieht, heisst gekippte Zeilenenden oder abgeschnittener Doku-Block -
   in einer Summe ueber 25 Dateien sieht beides wie Erfolg aus.
5. Jede geaenderte `config.yaml` mit `yaml.safe_load` parsen und die Zielwerte
   asserten; `LF-only`-Zeilen zaehlen (muss 0 sein).

## Was NICHT angefasst wird

- Profile mit **eigener Anmeldung** (`providers.nous` im `auth.json`) - sie laufen.
- Profile mit **lokalem Provider** (`llamacpp`) - brauchen keine Konto-Anmeldung.
- `default` - dort gehoeren die Zugangsdaten hin (Hash vorher/nachher vergleichen).
- Geteilte Zeilen **ohne Warnung** (`A2A_*`, `SMS_*`): melden und als Entscheidung
  stellen, nicht stillschweigend mitstrichen.

## Der Sonderfall, der fast durchging

Ein Profil **ohne `providers`-Block und ohne Router-Schluessel in der `.env`**
kann nicht einfach auf den Router umgestellt werden - sonst tauscht der Wechsel
nur die Ursache: aus `gemini`-404 wurde `omniroute` ohne Kennung (`Provider
'omniroute' ohne Block und ohne Zugangsdatei`, genau so gemeldet vom Audit).
Richtig ist, erst den Block nachziehen
(`hermes -p NAME config set providers.omniroute.base_url http://localhost:20128/v1`
und die uebrigen fuenf Schluessel) und die Zugangszeile aus der `.env` des
Startprofils uebernehmen - **Werte nie ausgeben**, nur Name und Laenge. Danach
wie ueberall: Ziel-Fassung byte-genau aus `git show HEAD:<pfad>` bauen, weil
jeder `config set` den Kommentar-Schluss abschneidet.

## Zeitbudget

Ein Massenlauf ueber 25 Profile dauert 7-10 min (zwei `hermes.exe`-Aufrufe je
Profil, je 5-15 s). Im Hintergrund laufen lassen, den Log am Ende auswerten -
und die Live-Pruefungen danach einzeln (je 30-60 s).

---

## Vollstaendiger Abschnitt aus dem SKILL.md-Rumpf

# Profilflotte: pruefen, bevor geheilt wird


Bei "ein Bot antwortet nicht" oder einer Liste von `hermes profile list`-Warnungen
gilt eine feste Reihenfolge: **(1)** `hermes profile list` zeigt die KANAELE, nicht
die Antwort-Ursache; **(2)** die Antwort-Ursache ist fast immer die Modellkennung
(Profile erben nichts vom Startprofil) und wird nur durch einen echten Aufruf belegt
(`hermes -p NAME chat -q "Antworte nur mit dem einen Wort: fertig" -Q`); **(3)** den
`fallback_providers`-Block des PROFILS lesen, BEVOR der Provider verdaechtigt wird -
ein Kleinmodell in der Kette verdeckt den Anmeldefehler mit einem
Kontextfenster-Fehler.

**Ein Bot, der nach Sekunden MITTEN im Lauf stirbt, ist eine andere Klasse als
„antwortet nicht".** Im Profil-Log steht dann
`Non-retryable client error: <provider>/<model>: …` und daneben liegt das volle
Request-Dump `profiles/<bot>/sessions/request_dump_<sitzung>_*.json` mit
`reason` und `error.body` — dieselbe Meldung, die der Client gesehen hat; der
Bot-Name steht im Dateinamen, man braucht keinen Live-Lauf. Eine terminale
Fremdklasse (Guthaben/Permission, z. B. `403 free tier can only be used from
within OpenCode`) bricht im Router die ganze `auto/*`-Kombo ab und wird von
Hermes NICHT wiederholt. Erst ueber alle Profile zaehlen
(`grep -h "Non-retryable client error" */logs/errors.log`) und nach Fehlertext
gruppieren: gleicher Text in vielen Profilen = eine gemeinsame Ursache im
Router, kein kaputter Bot. Der Fix gehoert dann dorthin (`omniroute-betrieb`:
terminale Kandidaten abschalten, `POST /api/resilience/reset`) — nicht in die
Bot-Config.

Ein Befehl statt 29 Einzelaufrufe (je 30-60 s Kaltstart):
`scripts/profilflotte-bericht.py` (venv-Python von `hermes-agent`, `HERMES_HOME`
gesetzt) zeigt je Profil Modell, hinterlegte Anmeldung, Kanalzeilen, Kette und
Befund; `--nur-probleme` kuerzt auf die auffaelligen. Es schreibt nichts. Danach
beheben die drei Werkzeuge unter `Agenten/Hermes/scripts/` je Befund
(`profil-kanaele-bereinigen.py`, `bot-rueckfallkette-bereinigen.py`,
`auth-verknuepfen.ps1` = Sitzung, `bot-modell-auf-nous.py` bzw. fuer den
Router-Weg `bot-modell-auf-router.py`): erst Trockenlauf ohne Argument, dann
`--anwenden`, `--zuruecknehmen` holt zurueck; je Profil `.bak-JJJJMMTT`; alle drei
sind idempotent und nennen je uebersprungenem Profil den Grund.

- **Ein Pruefwerkzeug kann den Block an der falschen Stelle suchen - Falschbefund.**
  Der Flottenbericht las `provider`/`model` per Regex aus den ersten zwoelf Zeilen
  der `config.yaml`. Bei einem Profil, dessen `providers:`-Block VOR dem
  `model:`-Block steht (z. B. ein Wartungsprofil), meldete er „kein model-Block;
  Provider ohne Block und ohne Zugangsdatei" - das Profil war gesund und
  antwortete. Regel: `yaml.safe_load` zuerst, den `model:`-Block daraus nehmen,
  das Zeilenmuster nur als Rueckfall fuer unlesbare Dateien. Und: **jeden Befund
  erst am lebenden System nachstellen, dann „reparieren"** - ein echter Aufruf
  des Profils kostet eine Minute und trennt einen Werkzeugfehler von einem
  echten Ausfall. Ein Befund ohne Gegenprobe fuehrt sonst zu Reparaturen an
  gesunden Dateien.

Der Nachweis ist eine Leiter, keine Behauptung: `hermes profile list` mit 0
Warnzeilen - Gegenprobe mit `--zuruecknehmen` (die Warnungen kehren zurueck) - ein
echter Aufruf je Muster (vorher kaputt, wiederhergestellt, Sonderfall) -
`git diff --numstat` JE Datei (2 Einfuegungen/3 Loeschungen = Modellwechsel,
0/7 = entfernte Kette) - jede geaenderte `config.yaml` mit `yaml.safe_load`
geparst und Zielwerte assertiert, LF-only-Zeilen 0. Rezept, Entscheidungstabelle,
Zeitbudget und die Liste "was nicht angefasst wird":
`siehe oben in dieser Datei`.
