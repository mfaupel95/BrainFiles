# Offene Liste messen, bevor Karten entstehen

Werkzeug, mit dem eine offene TASKS.md vor der Kartenanlage inventarisiert wird.
Alle Kommandos aus der WURZEL (`cd "$HERMES_HOME/../.."`), Python-Pfade als
C:-Pfad (ein nativer Interpreter bildet MSYS-Pfade nicht ab).

## 1. Was ist ueberhaupt offen

```bash
python Agenten/Hermes/skills/aufgabenliste-pflegen/scripts/doppelte_nummern.py
```

Liefert Bloeckezahl, Zeilenenden, vorhandene Abschnitte, hoechste und naechste
freie Nummer - und **alle doppelt vergebenen Nummern mit beiden Zeilen**. Der
Pruefer ist der erste Schritt, nicht der letzte: er liest auch `- [?]`/`- [!]`/
`- [✓]`, die ein blosses `grep '^- \[ \]'` uebersieht.

Doppelte Nummern sind im Haus Normalfall (parallele Sitzungen vergeben
unabhaengig dieselbe). Regel aus dem Pruefer: **der JUENGERE Eintrag weicht**
(neue Nummer ab der naechsten freien), der aeltere behaelt seine Nummer. Wer
Karten zu Nummern anlegt, muss den Jetzigen Stand kennen - die Karten-Bodies
nennen die Nummern woertlich, und eine doppelt vergebene Nummer macht den Body
un eindeutig.

## 2. Welche offenen Punkte haben schon eine Karte

```python
import re, os, subprocess, json
env = dict(os.environ); env.pop("PYTHONHOME", None); env.pop("PYTHONPATH", None)
hermes = "C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/bin/hermes.exe"
txt = "".join(subprocess.run([hermes, "kanban", "--board", b, "list", "--json"],
          capture_output=True, text=True, env=env).stdout
          for b in ("default", "repos", "wartung", "handel", "wissen"))
erwaehnt = set(re.findall(r'T-\d+', txt))
```

`list --json` ueber ALLE Boards in einer Kette, dann `T-\d+` daraus - das ist
die Abdeckungsmessung. Ein Punkt ohne Kartenbezug ist der Kandidat; ein Punkt
mit Kartenbezug gehoert NICHT in eine neue Karte (dort laeuft oder wartet
bereits Arbeit).

Grundmenge ist der echte `## Offen`-Abschnitt: TASKS.md traegt historisch
mehrere Ueberschriften mit diesem Namen (Regeln/Format stehen dazwischen).
Bloecke an den **Zeilen** festmachen und nur die unterhalb der LETZTEN
`## Offen`-Ueberschrift nehmen - ein Block, der in der Datei zweimal als
Kopfabschnitt auftaucht, sonst doppelt gezaehlt und doppelt kartiert.

## 3. Was in eine Karte gehoert und was nicht

Je Punkt den `Naechster Schritt:`, `Wartet auf:` und `Betrifft:`-Block lesen.
Der Block entscheidet die Karte:

| Block | Folge |
|---|---|
| `Naechster Schritt` = konkrete Handlung | Karte |
| `Naechster Schritt` = "entscheiden ..." / `Wartet auf: Max` | KEINE Karte - Entscheidung, bleibt in TASKS.md |
| mehrere T-Nummern mit gleichem Werkzeug/Ordner | in EIN Karte buendeln |
| Punkt ist Umweg/Fremdarbeit einer anderen Sitzung | nicht aufnehmen, nur nennen |

## 4. Blockierte Karten: fachlich oder technisch

```python
r = subprocess.run([hermes, "kanban", "--board", b, "show", tid], ...).stdout
```

Drei Befunde unterscheiden - sie verlangen verschiedene Antworten:

- **Worker-Absturz an der Token-Grenze** ("Agent crash", "raise max_tokens"):
  KEIN Fachproblem. Die Aufgabe wurde nie angefasst. Alle betroffenen Karten
  in EINE Karte "Ursache der Worker-Abstuerze" buendeln, mit Messauftrag
  (Profil-`config.yaml`: `model.default`, `provider`, Kontext) und einer
  Gegenprobe, dass dieselbe Karte danach durchlaeuft.
- **`needs_input` / UAC / Zugangsdaten**: berechtigt blockiert. Bleibt liegen,
  wird als Entscheidung von Max genannt, NICHT entblockt.
- **Lange blockiert ohne Kommentar** (`blocked for 109h`, "Add a comment"):
  braucht eine Einordnung (bleibt liegen mit Grund / wieder startbar), sonst
  bleibt es dieselbe tote Karte.

Beim Abschluss der Messung ist die Anzahl je Art die eigentliche Erkenntnis -
"10 blockierte Karten, davon 5 technisch, 3 UAC, 2 alt" ist die Meldung.

## 5. Karten erzeugen: Schleife, nicht Einzelschreibbefehle

Karten-Spezifikationen als Liste (slug, assignee, prio, key, titel, body)
fahren und je Eintrag `hermes.exe kanban --board <slug> create <titel>
--body-file <C:/pfad> --assignee <profil> --priority <n> --workspace
dir:<wurzel> --triage --idempotency-key <key> --skill <name> --json`.

- `--json` gibt die ID direkt zurueck - kein Nachschlagen in `list`.
- `--idempotency-key` macht den Lauf wiederholbar; der Key ist thematisch
  (`<thema>-YYYYMMDD`), nicht `card1`, sonst behaelt ein zweiter Lauf eine
  Karte, die inhaltlich anders gemeint war.
- Nach dem Lauf je Karte `show`: Status, Assignee, `workspace_kind: dir`,
  Eltern/Children. Erst dann ist die Anlage belegt (siehe SKILL.md).

## 6. Was die Messung NICHT loest

Ein Punkt, der nur als Karte existiert, ist nicht geschlossen. TASKS.md bleibt
die Liste des Hauses; die Karten fuehren aus. Beim Sammeln also immer beide
Zaehler nennen: "N offene Punkte, davon M durch Karten abgedeckt, K neue
Karten fuer R Punkte".