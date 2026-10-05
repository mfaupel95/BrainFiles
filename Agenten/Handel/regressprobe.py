"""Regressions-Gegenprobe T-097: alte gegen neue Fassung, Runde fuer Runde.

Warum nicht `replay.py --gegenprobe`: das vergleicht lauf_a gegen
backtest_prognose.lauf, also ZWEI Rechenwege derselben neuen Fassung. Hier
geht es um ALT gegen NEU - zwei Fassungen derselben Spur. Genau diese
Neutralitaet ist die Abnahme der Karte.

Weg: die HEAD-Fassung der handeln.py wird als `<spur>/probe_head.py` in den
ECHTEN Spurenordner gelegt und ueber replay.spur_modul geladen. Dort stimmen
HIER/HANDEL, alle Modul-Importe und der Wachen-Pfad - ein temp-Spiegel
haette jedes `import wachen_pruefung` und den per Pfad geladenen ratschen.py
zerlegt.

Der ALT-Lauf liest dabei die NEUE wachen.json. Das ist korrekt und gewollt:
der alte Code kannte die neuen Schluessel nicht und ignoriert sie - die
Regressionsfrage ist ja, ob der neue Code ohne oder mit denselben Werten
dasselbe tut. Der reine Rueckfallweg (signal(k, i) ohne w) ist durch die
Spurentests abgedeckt, nicht hier.

Aufruf aus Agenten/Handel:
    scanner/.venv/Scripts/python.exe <pfad> <spur> <max_kerzen>
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HIER, "..", ".."))
PROBE = "probe_head.py"


def git_show(pfad):
    r = subprocess.run(["git", "-C", REPO, "show", "HEAD:" + pfad],
                       capture_output=True)
    if r.returncode != 0:
        raise SystemExit("git show %s: %s" % (pfad, r.stderr.decode("utf-8", "replace")))
    return r.stdout


def lade(pfad, name):
    s = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


def vergleich(neu, alt):
    abw = []
    if len(neu) != len(alt):
        abw.append("Rundenzahl: neu %d, alt %d" % (len(neu), len(alt)))
    for i, (a, b) in enumerate(zip(neu, alt)):
        for f in ("inst", "seite"):
            if a.get(f) != b.get(f):
                abw.append("Runde %d %s: %r != %r" % (i, f, a.get(f), b.get(f)))
        for f in ("einstieg", "brutto_pct"):
            if abs(float(a.get(f, 0)) - float(b.get(f, 0))) > 1e-9:
                abw.append("Runde %d %s: %.10f != %.10f" % (i, f, a.get(f), b.get(f)))
    return abw


def main():
    spur, max_kerzen = sys.argv[1], int(sys.argv[2])
    sys.path.insert(0, HIER)
    import replay as r

    probepfad = os.path.join(HIER, spur, PROBE)
    alt_ziel = os.path.join(r.wurzel(), spur, "probe_alt")
    shutil.rmtree(alt_ziel, ignore_errors=True)
    with open(probepfad, "wb") as f:
        f.write(git_show("Agenten/Handel/%s/handeln.py" % spur))

    try:
        echtes = r.spur_modul
        r.spur_modul = lambda s: (lade(probepfad, "bt_probe_head")
                                  if s == spur else echtes(s))
        alt, _ = r.lauf_a(spur, 0.1, "probe_alt", max_kerzen=max_kerzen)
    finally:
        r.spur_modul = echtes
        os.remove(probepfad)

    neu, _ = r.lauf_a(spur, 0.1, "probe_neu", max_kerzen=max_kerzen)

    abw = vergleich(neu, alt)
    print(json.dumps({
        "spur": spur,
        "max_kerzen": max_kerzen,
        "gebuehr_pct_je_seite": 0.1,
        "runden_neu": len(neu),
        "runden_alt": len(alt),
        "gleich": not abw,
        "abweichungen": abw[:10],
        # Ohne diese Probe-Datei darf nichts liegen bleiben.
        "probe_entfernt": not os.path.exists(probepfad),
    }, indent=2, ensure_ascii=False))
    return 0 if not abw else 1


if __name__ == "__main__":
    sys.exit(main())