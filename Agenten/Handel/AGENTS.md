# Agenten/Handel — Karte für Agenten

**Git im geteilten Arbeitsbaum (seit 08.10.2026):** Nie `git stash` — der
Stash friert Arbeit ein, während andere Sitzungen weiter committen; das
spätere `stash pop` konfligiert dann gegen Zwischencommits (Fall
„Vault-Schutzschicht": 7 Konflikte). Eigenen Arbeitsschritt sofort committen
statt stashen. Vollständig in [../../CLAUDE.md](../../CLAUDE.md), Abschnitt
„Bereichs-Besitz".

**Diese Datei sagt, was NICHT zu lesen ist.** Der Ordner ist klein, aber er
enthält zwei Brocken, die jede Sitzung teuer machen, wenn man sie versehentlich
mitliest. Wer hier arbeitet, liest zuerst das hier.

## Zwei Ordner, die man nie mitliest

| Ordner | Größe | Warum nicht |
|---|---|---|
| `OpenAlice/` | 112 MB, 482 `.py` | Fremdes Projekt, eigener Baum. Nur lesen, wenn die Aufgabe ausdrücklich OpenAlice betrifft. |
| `.venv/`, `scanner/.venv/`, `nautilus/.venv/` | ~110 MB, 2651 `.py` | Interpreter, kein Projektcode. Nie nach Symbolen durchsuchen. |

Auch liegen lassen: `__pycache__/`, `kerzen_*.json` (474 KB Kursdaten),
`daten/` (7,4 MB), und **`README.md` (53 KB)** — das ist die ausführliche
Dokumentation, kein Einstieg. Für einen Überblick reicht diese Datei.

## Wonach sucht man was

| Aufgabe | Lesen | Nicht lesen |
|---|---|---|
| Eine Spur verstehen | `<spur>/wachen.json` (Tore und Zahlen), `<spur>/handeln.py`, `<spur>/README.md` | andere Spuren, `dauerlauf.py` |
| Eine Spur verändern | dieselben + `<spur>/tests/` | `OpenAlice/` |
| Den Betrieb verstehen | `dauerlauf.py` **ab Zeile 140** (Dict `SPUREN`: Ordner, Skript, Interpreter je Spur) | `dauerlauf.py` ganz (32 KB) |
| Zahlen einer Spur | `<spur>/handelsjournal.csv`, `<spur>/auswertung.py`, `auswertung_alle.py` | `tagesbericht.py` |
| Journal-Spiegelung prüfen | `spiegelstand.py` (vergleicht byte-genau gegen `Q:`) | — |
| Wachen/Ratschen prüfen | `pruefe_ratschen.py` (befragt jede Spur über ihr eigenes `lage()`), `scanner/wachen_pruefung.py` | — |
| Marktweit günstige Einstiege | `prognose.py` + `prognose.json` (Marktscanner über USDT/USDC, **keine Spur**) | — |
| GUI/Anzeige | `handelszentrale.py` (rein lesend) | — |
| Depot-/Buchauswertung | `buchauswertung.py`, `freigabe.py` | — |

## Die Spuren

Laufender Betrieb steht in `dauerlauf.py` im Dict `SPUREN` (ab Zeile 140) — das
ist die einzige Wahrheit, welche Spur mit welchem Skript läuft. Jede Spur hat
ihren eigenen Ordner mit `wachen.json` (Zahlen), Journal und Tests; die
spurspezifische Beschreibung steht in ihrem `README.md`, nicht hier.

Faustregel: **Zahlen gehören in `wachen.json`, nicht in den Code** — wer eine
Schwelle im Code findet, hat eine zweite Wahrheit gefunden und sollte das melden.

## Bedingung 4 (Spiegelung)

Jede Spur spiegelt Journal und Zustand nach `Q:\Handel_Journal\<spur>`.
`spiegelstand.py` vergleicht byte-genau und ist der Nachweis. Eine Änderung, die
einen Schreibpfad anfasst, muss danach `spiegelstand.py` laufen lassen — und
darf in Tests **nie** in ein echtes Ziel schreiben (eigene `journal_zweitziel`
auf einen Temp-Ordner umbiegen).

## Ein Arbeitsbaum je Aufgabe

Dieses Verzeichnis ist **zugleich Betriebsverzeichnis und Coderepo**, und
mehrere Sitzungen schreiben parallel hinein (Desktop, CLI, Hermes, Bots).
`.git/index` gehört dem Verzeichnis, nicht der Sitzung: was eine andere Sitzung
gerade stagt, geht mit dem eigenen Commit mit. Deshalb die Zweiteilung.

| Arbeit | Wo | Warum |
|---|---|---|
| Betrieb: Dauerlauf, Journale, Orders | **nur hier**, höchstens eine Sitzung | `zustand.json`, `handelsjournal.csv` und `daten/` vertragen keinen zweiten Schreiber |
| Codearbeit: Umbau, Review, Planausführung | eigener Worktree | braucht nur Code und Tests — beides versioniert |
| Lesen, Befunde, Analysen | hier, aber mit festgehaltenem Stand | sonst altern Zeilenangaben unbemerkt |

Ein Worktree bildet das **ganze** Repo ab, nicht nur diesen Ordner. Er gehört
deshalb neben `BrainFiles/`, nicht hinein — anlegen und entfernen aus der
Repowurzel:

```bash
git worktree add ../Handel-<kuerzel> -b arbeit/<kuerzel> origin/HEAD
```

```bash
git worktree remove ../Handel-<kuerzel>
```

Der Worktree hat **kein `.venv`** — das ist ungetrackt und bleibt hier. Tests
laufen über den Interpreter des Hauptbaums; aus `<worktree>/Agenten/Handel`
heraus ist das

```bash
../../../BrainFiles/Agenten/Handel/.venv/Scripts/python -m unittest discover -s tests -p "test_*.py"
```

Ebenso fehlen `daten/` und die Journale; wer sie braucht, arbeitet nicht im
Worktree, sondern hier.

Ein **Befunddokument** trägt im Kopf die Zeile `Stand: <commit> vom <datum>`
(`git rev-parse --short HEAD`). Ohne sie ist später nicht entscheidbar, ob eine
Zeilenangabe falsch war oder nur veraltet ist.

Was im Hauptbaum trotzdem gilt, wenn dort committet wird, steht in
`MaxHirn/Wissen/Schutzregeln.md`, Abschnitt *Mehrere Sitzungen gleichzeitig*.
