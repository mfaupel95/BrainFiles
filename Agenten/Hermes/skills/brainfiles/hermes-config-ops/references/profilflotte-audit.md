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
