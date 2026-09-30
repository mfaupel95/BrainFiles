"""Pflege: einrichten, bauen, pruefen und reparieren - je Projekt.

Die Zentrale konnte bisher zeigen, WAS fehlt (Gruppe EINRICHTEN) und starten,
was belegt ist. Hier kommt der naechste Schritt: den Zustand **messen**, den
fehlenden Handgriff **vorschlagen**, ihn auf Klick **ausfuehren** und danach
**belegen**.

Drei Regeln, die dieses Modul durchsetzt:

1. **Ein Vorschlag ist kein geratener Befehl.** Er entsteht aus einer Datei, die
   im Projekt WIRKLICH liegt: `package.json` -> `npm install`,
   `requirements.txt` -> `pip install -r`, `pyproject.toml` -> `pip install -e .`,
   `Cargo.toml` -> `cargo build --release`, `go.mod` -> `go build ./...`.
   Fehlt jeder Anhaltspunkt, sagt der Vorschlag das - er erfindet nichts.
2. **Ein Befehl kommt erst nach einem erfolgreichen Lauf ins Manifest.** Dafuer
   ist `eintragen()` da: sie schreibt den Befehl mit Sicherung `.bak-JJJJMMTT`
   und datierter Notiz - und nur, wenn der Lauf mit Exit-Code 0 endete.
3. **Ein kaputter Zustand wird BENANNT, nicht repariert.** Eine `.venv`, deren
   `python.exe` nicht mehr startet, ist kein Fall fuer `pip install`; sie wird
   gemeldet („neu bauen"), und der Vorschlag lautet `python -m venv .venv`.

Was dieses Modul NICHT tut: es loescht nichts, es veroeffentlicht nichts
(kein `git push`, kein `git reset`), und es fasst keine Datei im Projekt an,
die nicht zum Einrichten/Bauen gehoert.

Ohne Fenster pruefbar: `tests/test_pflege.py`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Frist fuer einen Einrichtungs-/Bau-Lauf. `npm install` und `pip install` auf
# einem grossen Projekt dauern; 15 min sind grosszuegig und verhindern trotzdem,
# dass ein haengender Lauf den Faden ewig haelt.
FRIST_S = 900

# Frist fuer die kurzen Sonden (git, python --version): die duerfen nie lange
# brauchen, sonst haengt der Pruefbericht.
SONDE_FRIST_S = 20

STANDS = ("ok", "fehlt", "warnung", "unbekannt")


@dataclass
class Punkt:
    """Ein Pruefpunkt: was gemessen wurde und was daraus folgt."""

    name: str
    stand: str
    text: str
    schritte: list[list[str]] = field(default_factory=list)

    @property
    def reparabel(self) -> bool:
        return bool(self.schritte)


@dataclass
class Schritt:
    """Ein auszufuehrender Befehl samt Begruendung."""

    was: str
    argv: list[str]
    hinweis: str = ""


def _popen(argv, cwd, frist=SONDE_FRIST_S):
    """Ein Programm kurz laufen lassen; nie eine Ausnahme nach aussen."""
    try:
        p = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=frist,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, f"nicht gefunden: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"Zeitfrist {frist} s"
    except OSError as e:
        return 126, f"{type(e).__name__}: {e}"


def _vorhanden(pfad: Path, name: str) -> bool:
    return (pfad / name).is_file()


# ------------------------------------------------------------------ Vorschlaege
def _python_programm(pfad: Path) -> list[str]:
    """Der Python-Aufruf im Projekt: das venv, sonst der laufende Interpreter."""
    for name in (".venv", "venv"):
        py = pfad / name / "Scripts" / "python.exe"
        if py.is_file():
            return [str(py)]
    return [sys.executable]


def vorschlag_einrichten(pfad: Path) -> list[list[str]]:
    """Die Schritte, die dieses Projekt einrichten - aus seinen eigenen Dateien.

    Rueckgabe: Liste von argv-Listen (in Reihenfolge). Leer heisst: es gibt
    nichts einzurichten ODER nichts, woraus sich ein Befehl ableiten laesst -
    welcher Fall gilt, sagt `einrichten_grund()`.
    """
    pfad = Path(pfad)
    schritte: list[list[str]] = []
    braucht_venv = any(
        _vorhanden(pfad, n) for n in ("pyproject.toml", "requirements.txt", "setup.py")
    )
    if braucht_venv:
        venv_py = pfad / ".venv" / "Scripts" / "python.exe"
        if not venv_py.is_file():
            schritte.append([sys.executable, "-m", "venv", ".venv"])
            schritte.append([str(venv_py), "-m", "pip", "install", "--upgrade", "pip"])
        py = _python_programm(pfad)
        if _vorhanden(pfad, "requirements.txt"):
            schritte.append([*py, "-m", "pip", "install", "-r", "requirements.txt"])
        if _vorhanden(pfad, "pyproject.toml"):
            schritte.append([*py, "-m", "pip", "install", "-e", "."])
        elif _vorhanden(pfad, "setup.py"):
            schritte.append([*py, "-m", "pip", "install", "-e", "."])
    if _vorhanden(pfad, "package.json"):
        if shutil.which("npm"):
            schritte.append(["npm", "install"])
        else:
            schritte.append([])          # Platzhalter: npm fehlt, s. u.
    return [s for s in schritte if s]


def einrichten_grund(pfad: Path) -> str:
    """Warum es (k)einen Einrichtungsvorschlag gibt - in einem Satz."""
    pfad = Path(pfad)
    if not pfad.is_dir():
        return "Ordner fehlt auf der Platte"
    merkmale = [n for n in ("pyproject.toml", "requirements.txt", "setup.py",
                            "package.json", "Cargo.toml", "go.mod")
                if _vorhanden(pfad, n)]
    if not merkmale:
        return ("kein Anhaltspunkt (keine package.json, requirements.txt, "
                "pyproject.toml, Cargo.toml oder go.mod)")
    if _vorhanden(pfad, "package.json") and not shutil.which("npm"):
        return "package.json liegt da, aber npm ist nicht installiert"
    return "aus " + ", ".join(merkmale)


def vorschlag_bauen(pfad: Path) -> list[list[str]]:
    """Die Schritte, die dieses Projekt baut - aus seinen eigenen Dateien."""
    pfad = Path(pfad)
    if _vorhanden(pfad, "Cargo.toml"):
        return [["cargo", "build", "--release"]]
    if _vorhanden(pfad, "go.mod"):
        return [["go", "build", "./..."]]
    if _vorhanden(pfad, "package.json"):
        daten = {}
        try:
            daten = json.loads((pfad / "package.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            daten = {}
        skripte = daten.get("scripts") or {}
        if "build" in skripte:
            return [["npm", "run", "build"]]
    if _vorhanden(pfad, "Makefile"):
        return [["make"]]
    return []


def bauen_grund(pfad: Path) -> str:
    """Warum es (k)einen Bau-Vorschlag gibt."""
    pfad = Path(pfad)
    if _vorhanden(pfad, "Cargo.toml"):
        return "Rust (Cargo.toml)"
    if _vorhanden(pfad, "go.mod"):
        return "Go (go.mod)"
    if _vorhanden(pfad, "package.json"):
        return "Node (package.json mit scripts.build)" if vorschlag_bauen(pfad) \
            else "package.json ohne scripts.build"
    if _vorhanden(pfad, "Makefile"):
        return "Makefile"
    return "kein Bau-Anhaltspunkt"


# ------------------------------------------------------------------ Pruefen
def _git_punkt(pfad: Path) -> Punkt:
    """Der Git-Zustand: Zweig, Aenderungen im Baum, Rueckstand gegen upstream.

    Gemessen, nicht geschaetzt: `git -C <pfad>` (native Pfade, MSYS wird hier
    nicht uebersetzt). Kein Netz - ein `fetch` waere ein Schreibzugriff auf die
    Klon-Metadaten und gehoert nicht in eine Pruefung.
    """
    if not (pfad / ".git").is_dir():
        return Punkt("Git", "unbekannt", "kein eigenes .git")
    code, zweig = _popen(["git", "-C", str(pfad), "rev-parse", "--abbrev-ref", "HEAD"], pfad)
    if code != 0:
        return Punkt("Git", "warnung", f"Zweig nicht lesbar: {zweig.strip()[:60]}")
    zweig = zweig.strip()
    _, roh = _popen(["git", "-C", str(pfad), "status", "--porcelain"], pfad)
    schmutzig = len([z for z in roh.splitlines() if z.strip()])
    _, abstand = _popen(
        ["git", "-C", str(pfad), "rev-list", "--left-right", "--count", "@{u}...HEAD"], pfad)
    teile = abstand.split()
    text = f"Zweig {zweig}"
    stand = "ok"
    if schmutzig:
        text += f", {schmutzig} Datei(en) im Baum"
        stand = "warnung"
    if len(teile) == 2:
        hinter, vor = teile
        text += f", {hinter} hinter / {vor} vor upstream"
        if hinter not in ("0",) and stand == "ok":
            stand = "warnung"
    elif not teile:
        text += ", kein upstream"
    return Punkt("Git", stand, text,
                 schritte=[[str(Path(__file__).resolve().parent.parent / "repos-updaten.py"),
                            "--nur", pfad.name]] if len(teile) == 2 and teile[0] != "0" else [])


def _venv_punkt(pfad: Path) -> Punkt:
    """Nicht nur „da?\", sondern „laeuft?\" - eine kaputte venv ist der haeufige Fall."""
    for name in (".venv", "venv"):
        py = pfad / name / "Scripts" / "python.exe"
        if not py.is_file():
            continue
        code, aus = _popen([str(py), "--version"], pfad)
        if code == 0:
            return Punkt("venv", "ok", f"{name}: {aus.strip().splitlines()[0][:40]}")
        return Punkt("venv", "fehlt",
                     f"{name} da, aber python.exe startet nicht ({aus.strip()[:60]})",
                     schritte=[[sys.executable, "-m", "venv", "--clear", name]])
    return Punkt("venv", "fehlt", "keine .venv",
                 schritte=[[sys.executable, "-m", "venv", ".venv"]])


def _node_punkt(pfad: Path) -> Punkt:
    if not _vorhanden(pfad, "package.json"):
        return Punkt("node_modules", "unbekannt", "kein package.json")
    module = pfad / "node_modules"
    if module.is_dir() and any(module.iterdir()):
        return Punkt("node_modules", "ok", "vorhanden")
    if not shutil.which("npm"):
        return Punkt("node_modules", "fehlt", "fehlt - und npm ist nicht installiert")
    return Punkt("node_modules", "fehlt", "fehlt", schritte=[["npm", "install"]])


def _port_punkt(port) -> Punkt:
    """Ist der Port frei? (nur wenn das Manifest einen nennt)"""
    if not isinstance(port, int):
        return Punkt("Port", "unbekannt", "kein Port im Manifest")
    try:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            belegt = s.connect_ex(("127.0.0.1", port)) == 0
    except OSError as e:
        return Punkt("Port", "unbekannt", f"{port}: {type(e).__name__}")
    return Punkt("Port", "warnung" if belegt else "ok",
                 f"{port} " + ("belegt (laeuft schon?)" if belegt else "frei"))


def pruefen(zeile, *, log_ordner: Path | None = None, jetzt: datetime | None = None) -> list[Punkt]:
    """Alle Punkte eines Projekts messen - rein lesend.

    `zeile` ist eine `manifest.Zeile`; gebraucht werden `repo`, `start`,
    `bot_da`, `gruppe` und die Manifest-Felder. Ohne Ordner auf der Platte
    (Gruppe FEHLT) kommt nur ein Punkt zurueck.
    """
    punkte: list[Punkt] = []
    repo = getattr(zeile, "repo", None)
    if repo is None:
        return [Punkt("Ordner", "fehlt",
                      "Eintrag ohne Ordner - erst den Klon wiederherstellen")]
    pfad = Path(repo.pfad)

    eintrag = getattr(zeile, "_eintrag", None)
    pflicht = getattr(zeile, "pfad_pflicht", None) or (
        getattr(eintrag, "pfad_pflicht", None) if eintrag is not None else None)
    port = getattr(zeile, "port", None)
    if port is None and eintrag is not None:
        port = getattr(eintrag, "port", None)

    punkte.append(Punkt("Ordner", "ok", str(pfad)))
    if getattr(zeile, "venv_pflicht", False) or (
        pfad / ".venv" / "Scripts" / "python.exe"
    ).is_file() or (pfad / "pyproject.toml").is_file() or (pfad / "requirements.txt").is_file():
        punkte.append(_venv_punkt(pfad))
    if _vorhanden(pfad, "package.json"):
        punkte.append(_node_punkt(pfad))
    if pflicht:
        da = (pfad / pflicht).exists()
        punkte.append(Punkt(
            pflicht, "ok" if da else "fehlt",
            "vorhanden" if da else "fehlt",
            schritte=[] if da else vorschlag_bauen(pfad),
        ))
    if getattr(repo, "git", False):
        punkte.append(_git_punkt(pfad))
    punkte.append(Punkt("README", "ok" if repo.readme else "warnung",
                        repo.readme or "keine README"))
    punkte.append(Punkt("Bot-Profil", "ok" if getattr(zeile, "bot_da", False) else "unbekannt",
                        getattr(zeile, "bot", None) or "kein Bot"))
    if getattr(zeile, "start", None):
        beleg = _letzter_beleg(log_ordner, zeile.ordner)
        punkte.append(Punkt(
            "Startbeleg", "ok" if beleg else "warnung",
            f"zuletzt {beleg}" if beleg else "noch nie gestartet (kein Log)",
        ))
    punkte.append(_port_punkt(port))
    return punkte


def _letzter_beleg(log_ordner: Path | None, ordner: str) -> str:
    if not log_ordner:
        return ""
    treffer = sorted(Path(log_ordner).glob(f"{ordner}-*.log"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    if not treffer:
        return ""
    return f"{datetime.fromtimestamp(treffer[0].stat().st_mtime):%d.%m. %H:%M}"


def offene_punkte(punkte: list[Punkt]) -> list[Punkt]:
    """Nur was nicht ok ist (und nicht ausdruecklich unbekannt)."""
    return [p for p in punkte if p.stand in ("fehlt", "warnung")]


def zeichen(stand: str) -> str:
    """Drei Zeichen je Zustand - gleiche Schreibweise wie im Handelsstand."""
    return {"ok": "ok  ", "fehlt": "FEHLT", "warnung": "WARN ", "unbekannt": "?   "}.get(
        stand, "?   ")


def bericht(zeile, punkte: list[Punkt]) -> str:
    """Die Pruefpunkte als Text fuer die Karte."""
    kopf = [getattr(zeile, "ordner", ""), getattr(zeile, "art", "")]
    zeilen = [" · ".join(t for t in kopf if t), ""]
    zeilen += [f"{zeichen(p.stand)} {p.name}: {p.text}" for p in punkte]
    offen = offene_punkte(punkte)
    zeilen.append("")
    if not offen:
        zeilen.append("Nichts zu tun - alle Punkte in Ordnung.")
    else:
        zeilen.append(f"{len(offen)} Punkt(e) offen:")
        for p in offen:
            if p.reparabel:
                zeilen.append(f"  - {p.name}: reparierbar ({' '.join(p.schritte[0])} ...)")
            else:
                zeilen.append(f"  - {p.name}: {p.text}")
    return "\n".join(zeilen)


def sammelbericht(zeilen, *, log_ordner: Path | None = None,
                  jetzt: datetime | None = None) -> tuple[str, list[tuple[str, list[Punkt]]]]:
    """Alle Projekte pruefen und einen Bericht bauen.

    Rueckgabe: (Text, [(ordner, offene Punkte)]) - nur Projekte MIT offenen
    Punkten stehen im Text. Das ist der Lauf fuer „reparatur ueberpruefen\".
    """
    jetzt = jetzt or datetime.now()
    zeilen_offen: list[str] = []
    auffaellig: list[tuple[str, list[Punkt]]] = []
    geprueft = 0
    for z in zeilen:
        if getattr(z, "repo", None) is None:
            continue
        geprueft += 1
        punkte = pruefen(z, log_ordner=log_ordner, jetzt=jetzt)
        offen = offene_punkte(punkte)
        if not offen:
            continue
        auffaellig.append((z.ordner, offen))
        zeilen_offen.append(f"### {z.bereich}/{z.ordner}")
        zeilen_offen += [f"- {p.name}: {p.text}" for p in offen]
        zeilen_offen.append("")
    kopf = [
        f"# Pruefbericht {jetzt:%Y-%m-%d %H:%M}",
        "",
        f"{geprueft} Projekte geprueft, {len(auffaellig)} mit offenen Punkten.",
        "",
    ]
    return "\n".join(kopf + zeilen_offen), auffaellig


# ------------------------------------------------------------------ Ausfuehren
def umgebung() -> dict:
    """Die Umgebung fuer Einrichtungs-/Bau-Laeufe.

    `PYTHONHOME`/`PYTHONPATH` werden entfernt (eine geerbte Vergiftung laesst
    jeden Python-Start scheitern), UTF-8 gesetzt, `MAXHIRN_ROUTINE=1` gesetzt -
    damit sich ein gestartetes Projekt nicht fuer eine Sitzung am Bildschirm
    haelt.
    """
    import os

    umg = dict(os.environ)
    for name in ("PYTHONHOME", "PYTHONPATH"):
        umg.pop(name, None)
    umg["PYTHONIOENCODING"] = "utf-8"
    umg["MAXHIRN_ROUTINE"] = "1"
    return umg


def ausfuehren(schritte: list[list[str]], cwd: Path, log: Path | None = None,
               frist: int = FRIST_S, jetzt: datetime | None = None) -> tuple[bool, str]:
    """Die Schritte nacheinander ausfuehren; bricht beim ersten Fehler ab.

    Rueckgabe: (alle erfolgreich, Ausgabe). Die Ausgabe wird vollstaendig
    zurueckgegeben und - wenn ein Logpfad genannt ist - dort angehaengt. Ein
    fehlendes Programm ist ein Ergebnis, kein Absturz.
    """
    jetzt = jetzt or datetime.now()
    cwd = Path(cwd)
    teile: list[str] = [f"# {jetzt:%Y-%m-%d %H:%M:%S} Pflege in {cwd}"]
    erfolg = True
    for argv in schritte:
        if not argv:
            teile.append("!! leerer Schritt - uebersprungen")
            erfolg = False
            continue
        teile.append(f"$ {' '.join(argv)}")
        try:
            p = subprocess.run(argv, cwd=str(cwd), env=umgebung(), capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=frist)
            code = p.returncode
            aus = (p.stdout or "") + (p.stderr or "")
        except FileNotFoundError:
            code, aus = 127, f"nicht gefunden: {argv[0]}"
        except subprocess.TimeoutExpired:
            code, aus = 124, f"Zeitfrist {frist} s - abgebrochen"
        except OSError as e:                                  # noqa: BLE001
            code, aus = 126, f"{type(e).__name__}: {e}"
        teile.append(aus.rstrip() or "(keine Ausgabe)")
        teile.append(f"-> Exit-Code {code}")
        if code != 0:
            erfolg = False
            break
    text = "\n".join(teile)
    if log is not None:
        try:
            Path(log).parent.mkdir(parents=True, exist_ok=True)
            with open(log, "a", encoding="utf-8", newline="\n") as f:
                f.write(text + "\n\n")
        except OSError:
            pass
    return erfolg, text


# ------------------------------------------------------------------ Belegen
def eintragen(manifest_pfad: Path | str, ordner: str, feld: str, cmd: list[str],
              *, wurzel: str = "", vermerk: str = "", jetzt: datetime | None = None) -> bool:
    """Einen BEFEHL nach einem erfolgreichen Lauf ins Manifest schreiben.

    Erlaubt sind nur die Felder, die die Zentrale ausfuehrt: `start`,
    `einrichten`, `bauen` und die beiden Ketten-Felder (`einrichten_kette`,
    `bauen_kette`) fuer mehrere Befehle nacheinander. Geschrieben wird mit Sicherung
    `.bak-JJJJMMTT` und datierter Notiz im Eintrag (`_<feld>_belegt`), damit
    spaeter erkennbar ist, wann und wodurch der Befehl belegt wurde.

    Die Datei wird - anders als eine `wachen.json` - komplett neu geschrieben
    (so macht es `fuellen.py` auch): sie ist eine Tabelle, keine handgesetzte
    Konfiguration. Die Feldreihenfolge bleibt dabei erhalten.
    """
    import shutil

    import fuellen

    if feld not in ("start", "einrichten", "einrichten_kette",
                    "bauen", "bauen_kette"):
        return False
    if not cmd:
        return False
    jetzt = jetzt or datetime.now()
    pfad = Path(manifest_pfad)
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    eintraege = daten.get("repos")
    if not isinstance(eintraege, list):
        return False
    ziel = None
    for e in eintraege:
        if not isinstance(e, dict) or e.get("ordner") != ordner:
            continue
        if wurzel and e.get("wurzel", "repos") != wurzel:
            continue
        ziel = e
        break
    if ziel is None:
        return False
    if ziel.get(feld) == list(cmd):
        return False
    ziel[feld] = list(cmd)
    ziel[f"_{feld}_belegt"] = (
        f"{jetzt:%Y-%m-%d} aus der Zentrale gelaufen ({vermerk or 'ok'})"
    )
    daten["repos"] = [fuellen.felder_ordnen(e) for e in eintraege]
    daten["stand"] = f"{jetzt:%Y-%m-%d}"
    sicherung = pfad.with_name(f"{pfad.stem}.bak-{jetzt:%Y%m%d}{pfad.suffix}")
    try:
        if not sicherung.exists():
            shutil.copy2(pfad, sicherung)
        pfad.write_bytes(
            (json.dumps(daten, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    except OSError:
        return False
    return True