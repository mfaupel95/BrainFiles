"""Nachlade-Werkzeug fuer die Feed-Historie: was `historie-wache.py` meldet.

`historie-wache.py` sagt, welche Reihen zu alt sind oder fehlen. dieses
Werkzeug laedt sie nach - aber NUR auf ausdruecklichen Aufruf, mit Vorschau
als Vorgabe.

WARUM ES EIN EIGENES WERKZEUG IST UND NICHT DER ARGUMENT `--universum`
-------------------------------------------------------------------------
Ein Nachlade-Lauf ist nicht billig und nicht harmlos. Er schreibt Hunderte
Megabyte in `daten/historie/` und laeuft je nach Universum mehrere Minuten.
Deshalb gilt hier die Hausregel aus `Agenten/Routinen/handel-tests.ps1` und
den Wachen: **Vorschau ist der Vorgabe, `--anwenden` schreibt.** Der Cron
darf dieses Skript NIE mit `--anwenden` aufrufen; die Wache meldet, dieser
Auftrag hier laedt.

DIE ZAHLEN SIND GEMESSEN, NICHT GESCHAETZT (05.10.2026)
--------------------------------------------------------
`--stunden 3 --faeden 4`  -> 7 Symbole, 86 s          (~12 s/Symbol)
`--universum 5 --takt 1D`  -> 5 Symbole,  10 s          (~ 2 s/Symbol)

Der Unterschied ist die Datenmenge: 1H-Reihen haben tausende Kerzen je
Abruf, 1D-Reihen wenige. Fuer die Schätzung hier wird deshalb die 1D-Zahl
genommen, mit einem Sicherheitsfaktor - und die Waechter-Schwelle meldet
danach, ob es geklappt hat.

WAS ES NICHT TUT
----------------
Es handelt nicht, es schreibt in keine Spur, es loescht nichts. Es fuellt
ausschliesslich die Historie auf, aus der der Backtest liest.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # Agenten/Hermes/scripts/ -> BrainFiles
HANDEL = WURZEL / "Agenten" / "Handel"
WERKZEUG = HANDEL / "moondev_historie.py"
PYTHON = HANDEL / "scanner" / ".venv" / "Scripts" / "python.exe"

# Gemessen 05.10.2026, s/Symbol bei 1D. Der Faktor 3 deckt die Faeden-Latenz
# und ein langsameres Netz ab, ohne den Timeout sinnlos hoch zu setzen: ein
# zu kleiner Timeout haelt den Lauf nach 900 s ab und laesst die Historie
# halb gefuellt zurueck - das war der Befund am 04.10. beim radar-sammler
# (349 s Lauf bei 300 s Timeout, danach stundenlang falsche Zahlen).
SEKUNDEN_PRO_SYMBOL = 2
SICHERHEIT = 3
MAX_GB = 4                                   # darueber wird abgebrochen


def _groesse_gb(ordner):
    if not ordner.is_dir():
        return 0.0
    return sum(p.stat().st_size for p in ordner.glob("*.json")) / (1024 ** 3)


# Der ECHTE Ablageort. Als Modulwert, nicht als Funktionsweg: sonst
# umgeht der Importweg jedes Umbiegen von `HANDEL` im Test (der eigene
# Erstlauf: 15 Fehlschlaege, alle mit "Historie fehlt" - die Attrappe lag am
# richtigen Ort, gelesen wurde trotzdem der echte Ordner).
FEED_ORDNER = None


def _feed_ordner():
    """Der Ordner, in dem `moondev_historie` wirklich schreibt.

    Quelle der Wahrheit ist das Abrufmodul (`ORDNER`), nicht eine
    Pfadannahme: `daten/historie` und `daten/historie/feed` sind zwei
    verschiedene Orte, und nur der zweite gehoert dem Backtest
    (Befund 05.10.2026).
    """
    global FEED_ORDNER
    if FEED_ORDNER is not None:
        return FEED_ORDNER
    import importlib.util
    modul_pfad = HANDEL / "moondev_historie.py"
    ergebnis = HANDEL / "daten" / "historie" / "feed"
    if modul_pfad.is_file():
        try:
            spec = importlib.util.spec_from_file_location(
                "mh_ordner", str(modul_pfad))
            modul = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modul)
            ergebnis = Path(modul.ORDNER)
        except Exception:
            pass
    FEED_ORDNER = ergebnis
    return FEED_ORDNER


def vorschau(top=30, takt="1D", jetzt=None):
    """Was der Lauf tun wuerde. Reine Rechnung, kein Abruf.

    `jetzt` ist ein PARAMETER, nicht `time.time()`: dieselbe Naht wie in
    `historie-wache.befunde()`. Ohne sie ist die Regel nicht pruefbar - die
    Attrappen eines Tests liegen in der Zukunft, `time.time()` faellt dann
    darunter und JEDE Reihe gilt als jung (gemessen: 2 Fehlschlaege, die Zahl
    "zu alt" blieb 0).
    """
    # Derselbe Ordner wie in `historie-wache._feed_ordner()`: die Quelle
    # der Wahrheit ist `moondev_historie.ORDNER`. `daten/historie` OHNE
    # `feed` ist ein zweiter, verwaister Ort (Befund 05.10.2026).
    ordner = _feed_ordner()
    jetzt = jetzt if jetzt is not None else time.time()
    alt, vorhanden = [], 0
    for pfad in sorted(ordner.glob("*_%s.json" % takt)):
        try:
            with open(pfad, encoding="utf-8") as f:
                reihe = json.load(f)
        except (OSError, ValueError):
            continue
        # JEDE lesbare Datei ist eine Reihe - auch eine, die nicht zu alt ist.
        # (Die erste Fassung zaehlte `len(alt)` PLUS alle Dateien und kam bei
        # drei alten Reihen auf "6 vorhanden": jeder Doppelzaehler verschiebt
        # `fehlend` und damit die geschaetzte Laufzeit. Gefunden vom Test
        # test_drei_alte_und_27_fehlende.)
        vorhanden += 1
        if not reihe:
            continue
        tage = (jetzt - int(reihe[-1][0]) / 1000.0) / 86400.0
        if tage > 5:
            alt.append((pfad.stem.rsplit("_", 1)[0], tage))
    fehlend = max(0, top - vorhanden)

    dauer = int((vorhanden + fehlend) * SEKUNDEN_PRO_SYMBOL * SICHERHEIT)
    zeilen = ["Nachladen %d x %s (Ziel: %d Reihen)" % (top, takt, top),
              "  zu alt (>5 Tage): %d" % len(alt),
              "  fehlend:          %d" % fehlend,
              "  geschaetzte Laufzeit: %d s (gemessen: %d s/Symbol x %d)"
              % (dauer, SEKUNDEN_PRO_SYMBOL, SICHERHEIT),
              "  Ordner jetzt: %.2f GB" % _groesse_gb(ordner)]
    if _groesse_gb(ordner) + fehlend * 0.01 > MAX_GB:
        zeilen.append("  ! ueberschreitet die Grenze von %d GB - abgebrochen, "
                      "erst --weniger nutzen" % MAX_GB)
    for sym, tage in sorted(alt, key=lambda x: -x[1])[:8]:
        zeilen.append("    %s: %.1f Tage alt" % (sym, tage))
    return zeilen, dauer, (fehlend > 0 or bool(alt))


def anwenden(top=30, takt="1D", faeden=4):
    """Der echte Lauf. Gibt den Kindprozess-Code zurueck."""
    if not PYTHON.is_file():
        print("FEHLER: %s fehlt - das ist der Haus-Interpreter fuer Handel."
              % PYTHON)
        return 2
    kommando = [str(PYTHON), str(WERKZEUG), "--universum", str(top),
                "--takt", takt, "--faeden", str(faeden)]
    print("Fuehre aus: %s" % " ".join(kommando), flush=True)
    # Kein Timeout auf der Kommandozeile: der Aufrufer (Cron) setzt ihn. Ein
    # eigener `timeout` wuerde den Lauf abwuergen und die Historie halb
    # gefuellt zuruecklassen - Lehre vom radar-sammler.
    return subprocess.call(kommando, cwd=str(HANDEL))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--top", type=int, default=30,
                   help="Zahl der Symbole fuer 1D (Vorgabe 30 = Vorgabe des "
                        "Backtests)")
    p.add_argument("--takt", default="1D", choices=["1D", "1H"])
    p.add_argument("--faeden", type=int, default=4)
    p.add_argument("--anwenden", action="store_true",
                   help="wirklich nachladen (Vorgabe: nur Vorschau)")
    a = p.parse_args(argv)

    zeilen, dauer, _tut = vorschau(a.top, a.takt)
    print("\n".join(zeilen))
    if not a.anwenden:
        print("\nVorschau - nichts geschrieben. Mit --anwenden wirklich laden.")
        return 0
    code = anwenden(a.top, a.takt, a.faeden)
    if code == 0:
        # Gegenprobe: die Wache muss danach schweigen.
        zurueck, _, _ = vorschau(a.top, a.takt)
        print("\nNach dem Lauf:")
        print("\n".join(zurueck[0]))
    return code


if __name__ == "__main__":
    sys.exit(main())