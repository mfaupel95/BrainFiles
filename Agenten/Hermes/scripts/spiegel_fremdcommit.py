"""Nimmt eine fremde, uncommittete Aenderung in der Spiegel-Spur mit.

Anlass (14.09.2026): In `Agenten/Handel/spiegel/spiegel.py` lag eine
uncommittete Aenderung aus Max' Claude-Sitzung - eine Ablehnungs-
Protokollierung (`ablehnungen.csv`: welche Kandidaten an welchem Tor haengen
blieben). Sie war beim Aufraeumen aufgefallen, aber noch mitten im Schreiben
(die Datei wuchs waehrend der Pruefung weiter). Max' Ansage: "Wenn andere
Session fertig mitnehmen."

Dieses Skript ist der Waechter dafuer. Es laeuft alle 20 Minuten (Hermes-Cron,
no_agent) und schweigt, solange es nichts zu tun gibt - der Cron schickt bei
leerer Ausgabe nichts. Erst wenn die Quelldateien der Spur seit RUHE_MIN
Minuten unberuehrt sind, prueft es und committet.

Sicherheitsnetz statt Automatik, wo es zaehlt:
  - committet werden NUR .py-Dateien der Spur; Laufzeitdaten (zustand.json,
    handelsjournal.csv, ablehnungen.csv, verfolgte.json) sind ohnehin
    ignoriert und werden nie angefasst,
  - vor dem Commit: py_compile und die komplette Testsuite der Spur; rot =
    kein Commit, sondern eine Meldung,
  - eine Meldung ueber einen roten Lauf kommt nur EINMAL je Inhalt (Merker-
    datei), damit der Chat nicht alle 20 Minuten dasselbe hoert,
  - zusaetzlich wird die Kopie ausser Haus (Q:) gegen die lokalen Dateien
    geprueft. Weicht sie ab, wird sie aus den lokalen zurueckgeholt und
    gemeldet - derselbe Schaden, den die Testlaeufe am 14.09.2026 angerichtet
    haben (Bedingung 4).

Direkt ausfuehrbar:  python Agenten/Hermes/scripts/spiegel_fremdcommit.py
"""

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Kein absoluter Benutzerpfad: die Wurzel aus der Lage DIESER Datei ableiten
# (Agenten/Hermes/scripts/ -> drei Ebenen hoch). Ein fester Pfad bricht den
# Umzug auf eine andere Platte still - Systempruefung Block 5 (Portabilitaet).
REPO = Path(__file__).resolve().parents[3]
SPUR = REPO / "Agenten" / "Handel" / "spiegel"
PY = REPO / "Agenten" / "Handel" / "scanner" / ".venv" / "Scripts" / "python.exe"
Q = Path(r"Q:\Handel_Journal\spiegel")
RUHE_MIN = float(os.environ.get("SPIEGEL_FREMDCOMMIT_RUHE_MIN", "20"))
PROBE = "--probe" in sys.argv          # nur pruefen und zeigen, nichts schreiben
MERKER = Path(os.environ.get("LOCALAPPDATA", ".")) / "Temp" / "spiegel_fremdcommit.json"
SPUR_GIT = "Agenten/Handel/spiegel"


def git(*args):
    return subprocess.run(["git", "-C", str(REPO)] + list(args),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def uncommittete_py():
    """Uncommittete .py-Dateien der Spur (geaendert oder neu)."""
    st = git("status", "--porcelain", SPUR_GIT)
    aus = []
    for zeile in st.stdout.splitlines():
        pfad = zeile[3:].strip().strip('"').replace("\\", "/")
        if pfad.endswith(".py"):
            aus.append(pfad)
    return aus


def juengste_aenderung():
    t = 0.0
    for p in list(SPUR.glob("*.py")) + list((SPUR / "tests").glob("*.py")):
        try:
            t = max(t, p.stat().st_mtime)
        except OSError:
            pass
    return t


def inhaltsschluessel(pfade):
    h = hashlib.sha256()
    for p in sorted(pfade):
        f = REPO / p
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


def merker_schreiben(d):
    if PROBE:
        return
    try:
        MERKER.parent.mkdir(parents=True, exist_ok=True)
        MERKER.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


def kopie_ausser_haus():
    """Q: gegen die lokalen Dateien pruefen - und zurueckholen, wenn sie
    abweicht. Zurueckgegeben wird eine Meldung oder None."""
    meldungen = []
    for name in ("zustand.json", "handelsjournal.csv"):
        lokal, weit = SPUR / name, Q / name
        if not lokal.exists():
            continue
        try:
            if weit.exists() and weit.read_bytes() == lokal.read_bytes():
                continue
            import shutil
            shutil.copy2(lokal, weit)
            meldungen.append("Q:/%s war abweichend - aus dem lokalen Bestand "
                             "zurueckgeholt" % name)
        except OSError as e:
            meldungen.append("Q:/%s nicht pruefbar (%s)" % (name, e))
    return "\n".join(meldungen) or None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    pfade = uncommittete_py()
    if not pfade:
        return 0                                   # nichts zu tun: still bleiben

    ruhe = (time.time() - juengste_aenderung()) / 60.0
    if ruhe < RUHE_MIN:
        return 0                                   # schreibt noch: warten

    kennung = inhaltsschluessel(pfade)
    merker = merker_lesen()
    zeilen = ["Spiegel-Spur: fremde Aenderung ist seit %.0f Minuten unberuehrt "
              "(%s)." % (ruhe, ", ".join(pfade))]

    # 1) laesst sich die Datei uebersetzen?
    r = subprocess.run([str(PY), "-m", "py_compile",
                        str(SPUR / "spiegel.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        if merker.get("letzter_roter") != kennung:
            merker["letzter_roter"] = kennung
            merker_schreiben(merker)
            print("\n".join(zeilen + ["py_compile ist rot - NICHT committet:",
                                      (r.stderr or r.stdout).strip()[:800]]))
        return 0

    # 2) Testsuite der Spur
    t = subprocess.run([str(PY), "-m", "unittest", "discover", "-s", "tests",
                        "-p", "test_*.py"],
                       cwd=str(SPUR), capture_output=True, text=True)
    zusammen = (t.stdout or "") + (t.stderr or "")
    if t.returncode != 0:
        if merker.get("letzter_roter") != kennung:
            merker["letzter_roter"] = kennung
            merker_schreiben(merker)
            print("\n".join(zeilen + ["Testsuite ist rot - NICHT committet:",
                                      zusammen.strip()[-800:]]))
        return 0

    kurz = [z for z in zusammen.splitlines() if z.startswith(("Ran", "OK"))]
    zeilen.append("py_compile ok, Tests: %s" % " | ".join(kurz))

    # 3) committen - nur diese .py-Dateien
    if PROBE:
        print("\n".join(zeilen + ["PROBE: es wuerde committet werden "
                                  "(nur diese Dateien: %s)" % ", ".join(pfade)]))
        return 0
    for p in pfade:
        git("add", p)
    nachricht = (
        "spiegel: Ablehnungs-Protokollierung (aus Max' Claude-Sitzung)\n\n"
        "Was das Journal nicht hergibt: WIE VIELE Kandidaten an welchem Tor\n"
        "haengen blieben. Ein volles Buch und ein zu strenges Tor sahen im\n"
        "Journal gleich aus. ablehnungen.csv schreibt je Zyklus, was die\n"
        "billigen Tore verworfen haben, was das Buch mit den bewerteten\n"
        "Kandidaten getan hat und je Kandidat bis zum Risiko-Scan eine Zeile\n"
        "mit Grund (ABLEHNUNG_TAIL begrenzt die Datei).\n\n"
        "Diese Aenderung ist nicht von Hermes: sie lag uncommittet im Baum und\n"
        "wurde hier nur geprueft (py_compile + komplette Testsuite) und\n"
        "mitgenommen. Inhaltlich nicht bewertet.")
    c = git("commit", "-q", "-m", nachricht)
    if c.returncode != 0:
        print("\n".join(zeilen + ["Commit fehlgeschlagen:",
                                  (c.stderr or c.stdout).strip()[:400]]))
        return 0
    hash_ = git("log", "--oneline", "-1").stdout.strip()
    zeilen.append("committet: %s" % hash_)

    # 4) Kopie ausser Haus in Ordnung bringen
    kopie = kopie_ausser_haus()
    if kopie:
        zeilen.append(kopie)

    merker["letzter_commit"] = kennung
    merker_schreiben(merker)
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
