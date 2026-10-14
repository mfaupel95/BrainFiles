# Repos-Zentrale — Implementierungsplan

**Stand: umgesetzt am 18.09.2026** (alle sieben Aufgaben; Nachweise in
`docs/design/2026-09-18-repos-zentrale-design.md` §10). Der Plan bleibt als
Begruendung der Aufteilung stehen.

**Ziel:** Ein Startfenster fuer alle Projekte unter `Werkstatt/`, mit je
Repo belegtem Startbefehl, Bot-Knopf und sichtbarem Zustand.
**Architektur:** Vier Module mit je einer Verantwortung (Platte lesen, Manifest
und Gruppe bestimmen, Kommandos bauen/ausfuehren, Fenster) plus ein
JSON-Manifest als einzige Quelle der Startbefehle. Kein Fremdpaket, nur
Standardbibliothek.
**Tech-Stack:** Python 3.13, tkinter, unittest; PowerShell nur fuer die zwei
Reparaturen.

## Projektweite Anforderungen

- Nur Standardbibliothek; die Zentrale nutzt **keine** Repo-venv.
- Alle Pfade relativ zur eigenen Datei (Wurzel = `parents[3]`), nie absolut.
- Kein `shell=True`, Kommandos immer als argv-Liste.
- Kein Schreiben in fremde Repos; `npm install` nur als ausdruecklicher
  Einrichtungsbefehl auf Klick.
- Keine Schluesselwerte lesen oder anzeigen; `.env` wird nicht geoeffnet.
- Eine Datei je Verantwortung; kein Modul ueber 300 Zeilen.
- Tests duerfen **nichts** starten: `subprocess.Popen`, `os.startfile` und
  `webbrowser` werden ersetzt und die argv-Liste geprueft.
- Zeilenenden LF; nach jeder Datei Änderung `git diff --stat` gegenpruefen.

## Dateistruktur

| Datei | Verantwortung |
|---|---|
| `scan.py` | Platte lesen: Repos, `.git`, venv, `node_modules`, README, Einstiegsmerkmale (package.json-Skripte, pyproject-Skripte, Cargo, Makefile). Kennt das Manifest nicht. |
| `manifest.py` | `repos-zentrale.json` laden und pruefen; Scan und Manifest zusammenfuehren; Gruppe und Gruende je Zeile; Bot-Profil auf der Platte pruefen. Kennt die Platte nur lesend. |
| `aktionen.py` | argv bauen (Ordner, Terminal, Start, Bot, Doku); Startbefehl ausfuehren, Log schreiben, PID merken. Kennt kein tkinter. |
| `fenster.py` | tkinter-Oberflaeche: Gruppen, Filter, Knopfreihe, Statuszeile. Ruft `aktionen` auf, rechnet nichts selbst. |
| `repos_zentrale.py` | Einstieg: Pfade bestimmen, laden, Fenster starten. |
| `repos-zentrale.json` | Manifest (Startbefehle, Bot, Notizen). |
| `tests/test_scan.py`, `tests/test_manifest.py`, `tests/test_aktionen.py`, `tests/test_fensterzeilen.py` | Unittests ohne echte Starts. |

---

### Aufgabe 1: Platte lesen (`scan.py`)

**Dateien:** Neu `scan.py`, Test `tests/test_scan.py`.

**Interfaces:**
- Produziert: `Repo` (Dataclass: `ordner: str`, `pfad: Path`, `art: str`,
  `git: bool`, `venv: str | None`, `venv_python: Path | None`,
  `node_modules: bool`, `zurueckhaltung: list[str]`, `readme: str | None`)
  und `repos_scannen(basis: Path) -> list[Repo]`.
- `art` ∈ `{"python", "node", "rust", "python+node", "make", "doku"}`.

- [ ] **Schritt 1: Test schreiben** (`tests/test_scan.py`)

```python
import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scan


def baue_repo(basis: Path, name: str, *, git=True, venv=False, node=False,
              pyproject=False, package=None, readme=True):
    d = basis / name
    (d / "src").mkdir(parents=True)
    if git:
        (d / ".git").mkdir()
    if venv:
        (d / ".venv" / "Scripts").mkdir(parents=True)
        (d / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
    if node:
        (d / "node_modules").mkdir()
    if pyproject:
        (d / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    if package:
        (d / "package.json").write_text(package, encoding="utf-8")
    if readme:
        (d / "README.md").write_text("# x\n", encoding="utf-8")
    return d


class ScanTest(unittest.TestCase):
    def test_erkennt_venv_und_art(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            baue_repo(basis, "py-repo", venv=True, pyproject=True)
            baue_repo(basis, "js-repo", node=True,
                      package='{"scripts": {"start": "node x.js"}}')
            (basis / "copilot-worktrees").mkdir()
            (basis / ".vscode").mkdir()
            rs = {r.ordner: r for r in scan.repos_scannen(basis)}
            self.assertNotIn("copilot-worktrees", rs)
            self.assertNotIn(".vscode", rs)
            self.assertEqual(rs["py-repo"].art, "python")
            self.assertEqual(rs["py-repo"].venv, ".venv")
            self.assertTrue(rs["py-repo"].venv_python.exists())
            self.assertEqual(rs["js-repo"].art, "node")
            self.assertFalse(rs["js-repo"].git is False)  # nur Doku-Ordner sind ohne .git

    def test_readme_und_zurueckhaltung(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            baue_repo(basis, "nur-doku", readme=True)
            baue_repo(basis, "ohne-readme", readme=False)
            rs = {r.ordner: r for r in scan.repos_scannen(basis)}
            self.assertEqual(rs["nur-doku"].readme, "README.md")
            self.assertIsNone(rs["ohne-readme"].readme)
            self.assertIn("readme fehlt", rs["ohne-readme"].zurueckhaltung)

    def test_kaputtes_manifest_egal_scan_kennt_es_nicht(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            baue_repo(basis, "einziges", venv=False)
            rs = scan.repos_scannen(basis)
            self.assertEqual(len(rs), 1)
            self.assertIsNone(rs[0].venv)
```

- [ ] **Schritt 2: Test laufen lassen** — `cd Agenten/Werkzeuge/repos-zentrale && .venv/Scripts/python.exe -m unittest discover -s tests -v`; Erwartet: FAIL (`ModuleNotFoundError: scan`).
- [ ] **Schritt 3: `scan.py` schreiben** — `Repo`-Dataclass, `repos_scannen(basis)`:

```python
ORDNER_OHNE_REPO = {"copilot-worktrees", ".vscode"}
VENV_NAMEN = (".venv", "venv")


def _art(d: Path) -> str:
    merkmale = []
    if (d / "pyproject.toml").is_file() or (d / "requirements.txt").is_file():
        merkmale.append("python")
    if (d / "package.json").is_file():
        merkmale.append("node")
    if (d / "Cargo.toml").is_file():
        merkmale.append("rust")
    if (d / "Makefile").is_file():
        merkmale.append("make")
    if not merkmale:
        return "doku"
    if len(merkmale) == 2 and "make" in merkmale:
        merkmale.remove("make")
    return "+".join(sorted(set(merkmale)))


def _venv(d: Path) -> tuple[str | None, Path | None]:
    for name in VENV_NAMEN:
        py = d / name / "Scripts" / "python.exe"
        if py.is_file():
            return name, py
    return None, None
```

- [ ] **Schritt 4: Test laufen lassen** — Erwartet: 3 Tests PASS.
- [ ] **Schritt 5: Committen** — `git add scan.py tests/test_scan.py && git commit`.

### Aufgabe 2: Manifest und Gruppe (`manifest.py`)

**Dateien:** Neu `manifest.py`, `repos-zentrale.json` (Geruest), Test `tests/test_manifest.py`.

**Interfaces:**
- Konsumiert: `scan.Repo`, `scan.repos_scannen`.
- Produziert: `Eintrag`, `Zeile` (Dataclass: `repo: Repo | None`, `ordner: str`,
  `gruppe: str`, `start: list[str] | None`, `einrichten: list[str] | None`,
  `bot: str | None`, `bot_da: bool`, `notiz: str`, `gruende: list[str]`),
  `manifest_laden(pfad) -> list[Eintrag]`,
  `zeilen_bauen(repos, eintraege, profile_dir, repos_basis) -> list[Zeile]`.
- `gruppe` ∈ `{"startbar", "einrichten", "doku", "neu", "fehlt"}`.

- [ ] **Schritt 1: Test schreiben** — Kernpunkte: (a) Eintrag ohne Ordner → Gruppe `fehlt`; (b) Ordner ohne Eintrag → `neu`; (c) `gruppe: "doku"` im Manifest → `doku`; (d) `start` gesetzt, venv noetig und fehlend → `einrichten` mit Grund; (e) `start` gesetzt und Bedingungen erfuellt → `startbar`; (f) `bot` wird klein geschrieben und gegen `profiles/` geprueft, fehlendes Profil setzt `bot_da=False` und einen Grund; (g) ein `start` als Zeichenkette (statt Liste) ist ein Fehler und macht die Zeile `einrichten` mit Grund, statt zu werfen.
- [ ] **Schritt 2: Test laufen lassen** — Erwartet: FAIL.
- [ ] **Schritt 3: `manifest.py` schreiben** — Kern der Gruppenlogik:

```python
def _bedingungen(repo, eintrag) -> list[str]:
    grund = []
    if eintrag.start is None:
        grund.append("kein Startbefehl belegt")
    if eintrag.venv_pflicht and repo is not None and repo.venv is None:
        grund.append("venv fehlt")
    if eintrag.node_modules_pflicht and repo is not None and not repo.node_modules:
        grund.append("node_modules fehlt (npm install)")
    return grund


def zeilen_bauen(repos, eintraege, profile_dir, repos_basis):
    nach_ordner = {e.ordner: e for e in eintraege}
    zeilen = []
    for repo in repos:
        e = nach_ordner.get(repo.ordner)
        if e is None:
            zeilen.append(Zeile(repo=repo, ordner=repo.ordner, gruppe="neu",
                                gruende=["kein Eintrag im Manifest"]))
            continue
        zeilen.append(_zeile(repo, e, profile_dir))
    for e in eintraege:
        if not (repos_basis / e.ordner).is_dir():
            zeilen.append(Zeile(repo=None, ordner=e.ordner, gruppe="fehlt",
                                gruende=["Ordner fehlt"]))
    return zeilen
```

- [ ] **Schritt 4: Test laufen lassen** — Erwartet: PASS.
- [ ] **Schritt 5: Committen.**

### Aufgabe 3: Aktionen (`aktionen.py`)

**Dateien:** Neu `aktionen.py`, Test `tests/test_aktionen.py`.

**Interfaces:**
- Produziert: `argv_ordner(pfad) -> list[str]`, `argv_terminal(pfad) -> list[str]`,
  `argv_bot(bot, pfad) -> list[str]`, `argv_doku(datei) -> list[str]`,
  `start_ausfuehren(zeile, log_ordner, *, popen=subprocess.Popen, jetzt=None)`
  → `StartErgebnis` (Dataclass: `pid: int | None`, `log: Path`, `argv: list[str]`,
  `fehler: str | None`), `log_pfad(ordner, name, jetzt)`.

- [ ] **Schritt 1: Test schreiben** — Kernpunkte: (a) `argv_terminal` enthaelt `wt.exe`, `-d` und den Repo-Pfad; (b) `argv_bot` ist `[hermes, -p, <bot>, chat]` und der Bot-Name ist klein; (c) `start_ausfuehren` mit ersetztem `popen` ruft es **einmal** mit `cwd=` und der argv-Liste auf, ohne `shell=True`; (d) fehlender Startbefehl gibt `fehler` zurueck und ruft `popen` **nicht**; (e) Dateiname des Logs enthaelt Repo und Zeitstempel; (f) ein nicht gefundenes Programm (`FileNotFoundError`) wird als `fehler` zurueckgegeben statt zu werfen.
- [ ] **Schritt 2: Test laufen lassen** — Erwartet: FAIL.
- [ ] **Schritt 3: `aktionen.py` schreiben** — Start ohne Shell, Ausgabe in Logdatei:

```python
def start_ausfuehren(zeile, log_ordner, *, popen=subprocess.Popen, jetzt=None):
    if not zeile.start:
        return StartErgebnis(None, Path(), [], "kein Startbefehl belegt")
    jetzt = jetzt or datetime.now()
    log = log_ordner / f"{zeile.ordner}-{jetzt:%Y%m%d-%H%M}.log"
    log_ordner.mkdir(parents=True, exist_ok=True)
    argv = list(zeile.start)
    cwd = Path(zeile.repo.pfad) if zeile.repo else Path()
    try:
        with open(log, "ab") as f:
            f.write(f"# {zeile.ordner} {jetzt:%Y-%m-%d %H:%M:%S} {' '.join(argv)}\n".encode())
            p = popen(argv, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT,
                      creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
        return StartErgebnis(None, log, argv, f"{type(e).__name__}: {e}")
    return StartErgebnis(p.pid, log, argv, None)
```

- [ ] **Schritt 4: Test laufen lassen** — Erwartet: PASS.
- [ ] **Schritt 5: Committen.**

### Aufgabe 4: Fenster (`fenster.py`, `repos_zentrale.py`)

**Dateien:** Neu `fenster.py`, `repos_zentrale.py`, Test `tests/test_fensterzeilen.py`.

**Interfaces:**
- Produziert: `sichtbare_zeilen(zeilen, suchtext) -> list[Zeile]` (reine Funktion),
  `nach_gruppen(zeilen) -> dict[str, list[Zeile]]`, `Fenster(basis, profile_dir, lang)`.
- Konsumiert: `scan`, `manifest`, `aktionen`.

- [ ] **Schritt 1: Test schreiben** — `sichtbare_zeilen` filtert ueber Ordnername und Notiz, ohne Beachtung der Gross-/Kleinschreibung; `nach_gruppen` liefert die vier Gruppen in fester Reihenfolge (`startbar`, `einrichten`, `neu`, `doku`, `fehlt`) und keine leeren Eintraege.
- [ ] **Schritt 2: Test laufen lassen** — Erwartet: FAIL.
- [ ] **Schritt 3: Schreibtisch bauen** — Aufbau: `Tk` → Suchfeld + „Aktualisieren" → `ttk.Treeview` je Gruppe (mit `Text`-Ueberschrift `STARTBAR (4)`) → Statuszeile. Je Zeile fuenf Knoepfe in einer `Frame` (Ordner, Terminal, Starten, Bot, Doku). Deaktivierte Knoepfe tragen den Grund als `textvariable`-Tooltip-Ersatz in der Statuszeile (tkinter hat keinen Tooltip; der Grund steht in der Spalte „Hinweis"). Start und Bot laufen in einem Thread, damit das Fenster nicht einfriert; die Statuszeile wird ueber `root.after` aktualisiert.
- [ ] **Schritt 4: Test laufen lassen** — Erwartet: PASS; danach **echter Start** `.\\.venv\\Scripts\\pythonw.exe repos_zentrale.py` aus dem Ordner, Fenster muss die 28 Repos zeigen.
- [ ] **Schritt 5: Committen.**

### Aufgabe 5: Manifest mit belegten Startbefehlen fuellen

**Dateien:** Ändern `repos-zentrale.json`.

- [ ] **Schritt 1:** Je Repo der Gruppe STARTBAR den Befehl **echt** einmal laufen lassen, Dauer und erste Ausgabe notieren, Log in `logs/` behalten.
- [ ] **Schritt 2:** Nur Befehle eintragen, die in Schritt 1 Ausgabe erzeugt haben. Alles andere bleibt ohne `start` und erscheint als `einrichten` mit Grund.
- [ ] **Schritt 3:** Gegenprobe: Fuer jeden `start` im Manifest existiert eine Logdatei. Als Test in `tests/test_manifest_gegenprobe.py` formulieren (Manifest gegen `logs/`), Erwartet: PASS.
- [ ] **Schritt 4: Committen.**

### Aufgabe 6: Die zwei Reparaturen

**Dateien:** Ändern `Agenten/Routinen/repos-launcher.ps1`; Desktop-Verknuepfung ausserhalb des Repos.

- [ ] **Schritt 1:** `repos-launcher.ps1`: `Get-ExecutablePath` bekommt einen zweiten Parameter `-Pflicht:$false`; fehlt ein Werkzeug, wird es uebersprungen und im Klartext in das Protokoll geschrieben statt zu werfen (`throw` nur noch, wenn `wt.exe` fehlt und Modus Terminal gewuenscht ist). Beleg: Skript einmal mit `-Mode Gui` laufen lassen — es darf nicht abbrechen, sondern muss „code.exe fehlt, uebersprungen" melden.
- [ ] **Schritt 2:** Desktop-Verknuepfung „Hermes" per WScript.Shell auf
  `Agenten\Hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`
  umbiegen, Arbeitsverzeichnis auf den Ordner der App. Beleg: Verknuepfung
  auslesen, Ziel existiert (`Test-Path`).
- [ ] **Schritt 3: Committen** (nur die `.ps1`; die Verknuepfung liegt nicht im Repo und wird im Bericht genannt).

### Aufgabe 7: Doku und Nachweis

- [ ] **Schritt 1:** `README.md` der Zentrale: was sie ist, wie man sie startet, wie man ein Repo ergaenzt (Manifest-Feld fuer Feld), was sie absichtlich nicht tut.
- [ ] **Schritt 2:** Skill `repo-flotte` um einen kurzen Absatz ergaenzen (Startbefehle gehoeren ins Manifest, nie ins Skript) und den Skill `fremd-agenten-betrieb` auf die Zentrale verweisen.
- [ ] **Schritt 3:** Nachweisliste aus der Spezifikation §10 abarbeiten und die Ergebnisse in `docs/design/2026-09-18-repos-zentrale-design.md` unter „Nachweis (gemessen)" eintragen.
- [ ] **Schritt 4: Committen und (auf Wunsch) pushen.**

## Self-Review (frisch gelesen)

1. **Spezifikations-Abdeckung:** §4 Dateien → Aufgaben 1–4; §5 Fenster → Aufgabe 4; §6 Manifest → Aufgaben 2 und 3; §7 Regeln → Aufgaben 3 (argv, kein shell), 5 (kein geratener Befehl), 6 (deaktivierter Knopf); §9 Reparaturen → Aufgabe 6; §10 Nachweis → Aufgabe 7; §12 offene Punkte → bewusst keine Aufgabe (Autostart erst nach Freigabe).
2. **Platzhalter:** keine.
3. **Typ-Konsistenz:** `Zeile.start` ist in Aufgabe 2 als `list[str] | None` eingefuehrt und in Aufgabe 3 (`start_ausfuehren`) genauso benutzt; `Repo.venv`/`Repo.node_modules` stammen aus Aufgabe 1 und werden in Aufgabe 2 gelesen.
