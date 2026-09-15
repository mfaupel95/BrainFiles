"""Waechter: nimmt die uncommittete Arbeit einer anderen Sitzung mit, wenn sie fertig ist.

Das Skript laeuft als Hermes-Cron mit `no_agent=True` (leere Ausgabe schickt
NICHTS - Watchdog-Muster) und committet erst, wenn die Quelldateien einer Spur
seit RUHE_MIN Minuten unberuehrt sind und `py_compile` sowie die Testsuite der
Spur gruen sind. Vorlage: Agenten/Hermes/scripts/spiegel_fremdcommit.py (erste
Fassung, spiegel-spezifisch, 14.09.2026).

Sicherheitsnetz statt Automatik:
  - committet werden NUR .py-Dateien der Spur; Laufzeitdaten (zustand.json,
    handelsjournal.csv, ablehnungen.csv, verfolgte.json) sind per Whitelist
    ignoriert und werden nie angefasst,
  - vor dem Commit py_compile und die Testsuite der Spur; rot = kein Commit,
    sondern eine Meldung,
  - eine rote Meldung kommt nur EINMAL je Inhalt (Merkerdatei),
  - die Commit-Nachricht sagt, wessen Arbeit es ist.

Aufruf (Hermes-Cron: script=<pfad> + no_agent=True):
    python fremdarbeit_waechter.py --spur <spurordner> --repo <git-wurzel> \
           --python <venv-python> [--ruhe 20] [--probe]

Nur Standardbibliothek.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

MERKER = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("TMPDIR") or ".") / "fremdarbeit_waechter.json"

NACHRICHT = """{titel}

Diese Aenderung ist nicht von Hermes: sie lag uncommittet im Baum und wurde
hier nur geprueft (py_compile + komplette Testsuite) und mitgenommen. Inhaltlich
nicht bewertet.

{tests}"""


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo)] + list(args),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def uncommittete_py(repo, spur_rel):
    """Uncommittete .py-Dateien der Spur (geaendert oder neu)."""
    st = git(repo, "status", "--porcelain", spur_rel)
    aus = []
    for zeile in st.stdout.splitlines():
        pfad = zeile[3:].strip().strip('"').replace("\\", "/")
        if pfad.endswith(".py"):
            aus.append(pfad)
    return aus


def juengste_aenderung(spur):
    t = 0.0
    for p in list(spur.glob("*.py")) + list((spur / "tests").glob("*.py")):
        try:
            t = max(t, p.stat().st_mtime)
        except OSError:
            pass
    return t


def inhaltsschluessel(repo, pfade):
    h = hashlib.sha256()
    for p in sorted(pfade):
        f = repo / p
        h.update(p.encode())
        if f.exists():
            h.update(str(f.stat().st_size).encode())
            h.update(f.read_bytes()[:20000])
    return h.hexdigest()[:16]


def merker_lesen():
    try:
        return json.loads(MERKER.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def merker_schreiben(d, probe):
    if probe:
        return
    try:
        MERKER.parent.mkdir(parents=True, exist_ok=True)
        MERKER.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


def pruefe(repo, spur, py, probe, ruhe_min):
    """Gibt die zu meldenden Zeilen zurueck (leer = schweigen)."""
    rel = str(spur.relative_to(repo)).replace("\\", "/")
    pfade = uncommittete_py(repo, rel)
    if not pfade:
        return []
    ruhe = (time.time() - juengste_aenderung(spur)) / 60.0
    if ruhe < ruhe_min:
        return []                       # schreibt noch: warten

    kennung = inhaltsschluessel(repo, pfade)
    merker = merker_lesen()
    zeilen = ["%s: fremde Aenderung seit %.0f Minuten unberuehrt (%s)."
              % (spur.name, ruhe, ", ".join(pfade))]

    erste = repo / pfade[0]
    r = subprocess.run([str(py), "-m", "py_compile", str(erste)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        if merker.get("letzter_roter") != kennung:
            merker["letzter_roter"] = kennung
            merker_schreiben(merker, probe)
            return zeilen + ["py_compile ist rot - NICHT committet:",
                             (r.stderr or r.stdout).strip()[:800]]
        return []

    if (spur / "tests").is_dir():
        t = subprocess.run([str(py), "-m", "unittest", "discover", "-s", "tests",
                            "-p", "test_*.py"],
                           cwd=str(spur), capture_output=True, text=True)
        zusammen = (t.stdout or "") + (t.stderr or "")
        if t.returncode != 0:
            if merker.get("letzter_roter") != kennung:
                merker["letzter_roter"] = kennung
                merker_schreiben(merker, probe)
                return zeilen + ["Testsuite ist rot - NICHT committet:",
                                 zusammen.strip()[-800:]]
            return []
        kurz = [z for z in zusammen.splitlines() if z.startswith(("Ran", "OK"))]
    else:
        kurz = ["keine tests/ im Spurordner - nur py_compile geprueft"]
    zeilen.append("py_compile ok, Tests: %s" % " | ".join(kurz))

    if probe:
        return zeilen + ["PROBE: es wuerde committet werden (nur %s)." % ", ".join(pfade)]

    for p in pfade:
        git(repo, "add", p)
    c = git(repo, "commit", "-q", "-m",
            NACHRICHT.format(titel="%s: fremde Aenderung mitgenommen" % spur.name,
                             tests="Tests: %s" % " | ".join(kurz)))
    if c.returncode != 0:
        return zeilen + ["Commit fehlgeschlagen:", (c.stderr or c.stdout).strip()[:400]]
    zeilen.append("committet: %s" % git(repo, "log", "--oneline", "-1").stdout.strip())
    merker["letzter_commit"] = kennung
    merker_schreiben(merker, probe)
    return zeilen


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Fremdarbeit mitnehmen, wenn sie fertig ist")
    p.add_argument("--spur", required=True, help="Ordner der Spur")
    p.add_argument("--repo", default=None, help="Git-Wurzel (Default: Elternsuche)")
    p.add_argument("--python", default=sys.executable, help="Interpreter fuer Tests")
    p.add_argument("--ruhe", type=float, default=20.0, help="Ruhezeit in Minuten")
    p.add_argument("--probe", action="store_true", help="nur zeigen, nichts schreiben")
    a = p.parse_args()

    spur = Path(a.spur).resolve()
    repo = Path(a.repo).resolve() if a.repo else next(
        (q for q in [spur, *spur.parents] if (q / ".git").exists()), None)
    if repo is None:
        print("%s liegt in keinem Git-Baum - nichts zu committen." % spur)
        return 1
    zeilen = pruefe(repo, spur, Path(a.python), a.probe, a.ruhe)
    if zeilen:
        print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
