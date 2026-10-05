"""Cron-Angelpunkt: fuellt die Feed-Historie taeglich auf, OHNE zu melden.

Aufruf aus `historie-wache.py` heraus - dort steht die Regel, hier nur der
Lauf. Getrennt, weil die Wache ein Meldetimer ist und dieser ein Arbeitstimer:
`historie-wache.py` schweigt, wenn alles frisch ist, und dieser schweigt,
wenn er nichts zu tun hatte.

WARUM EIN ZWEITES SKRIPT (Max' Entscheidung 05.10.2026)
-------------------------------------------------------
"Automatisch nachladen bis 30 Reihen, 1x taeglich." Die Regel und die
Rechnung bleiben in `historie-wache.py`, damit es EINEN Ort fuer die
Entscheidung gibt. Was hier passiert, ist nur:

    * `historie-wache.py` befragen (leere Ausgabe = alles frisch = sofort
      fertig, ohne Ausgabe und ohne Prozess),
    * sonst `historie-nachladen.py --anwenden` starten.

BEIDE WERKZEUGE ARBEITEN OHNE MODELL. Das heisst: der Cron traegt den
Nachlade-Auftrag, und ein Fehler des Laufs erscheint in der Ausgabe. Er
schweigt nur dann, wenn er wirklich nichts getan hat.

GRENZEN, die im Auftrag stehen
------------------------------
`--top 30` ist die Vorgabe des Backtests (`replay.lauf_feed`,
`mindest_symbole=30`). Kein Top-300-Universum: die Breite des Nachladens
ist eine Entscheidung, und diese Entscheidung ist "genug fuer den
Backtest". `MAX_GB` im Nachladewerkzeug bricht ab, wenn der Ordner die
Grenze reisst - ein stiller Abbruch mit halber Historie waere schlimmer
als gar keiner.
"""

import subprocess
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # Agenten/Hermes/scripts/ -> BrainFiles
HANDEL = WURZEL / "Agenten" / "Handel"
PYTHON = Path(sys.executable)   # WENDE-PRUEFUNG: zeigt auf den Aufrufer

# HIER ist die DATEI. `HIER / "x.py"` zeigt dann in
# `scripts/historie-auftrag.py/x.py` - zwei Pfade, die es nicht gibt. Die
# Wende-Pruefung fand genau das: `subprocess.run` auf einen fehlenden Pfad
# liefert KEINEN Fehler, sondern leere Ausgabe, und die Wette "leer heisst
# alles frisch" haette daraus "alles ist in Ordnung" gemacht. Ein stiller
# Fehlpfad in einem Watchdog ist die teuerste Form von "gruen".
SCRIPTS = HIER.parent
WACHE = SCRIPTS / "historie-wache.py"
NACHLADEN = SCRIPTS / "historie-nachladen.py"

TOP = 30                                     # Vorgabe des Backtests
TAKT = "1D"
# Zwei Fehlversuche am Tag sind genug fuer einen Befund; danach schweigt die
# Wache bis zum nächsten Tag, statt den Nachladeversuch zu wiederholen. Der
# Zaehler merkt sich nur die Zahl der Fehlversuche seit dem letzten Erfolg.
MERKFILEI = WURZEL / "Agenten" / "Hermes" / "cache" / "historie-nachladen.json"
MAX_FEHLVERSUCHE = 2
PAUSE_NACH_FEHLVERSUCH_S = 6 * 3600


def _merk():
    try:
        import json
        with open(MERKFILEI, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _merke(d):
    try:
        import json
        MERKFILEI.parent.mkdir(parents=True, exist_ok=True)
        with open(MERKFILEI, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
    except OSError:
        pass


def _zu_tun():
    """Was die Wache sieht - ein Unterprozess, weil sie `main()` anbietet.

    Zwei Prozesse statt eines: die Wache liest ihre Pfade aus dem Modul, und
    sie soll den echten Pfad (`HANDEL`) sehen - genau das ist die Regel, die
    im ersten Bau gebrochen wurde (der Test blickte auf eine Attrappe).
    """
    if not WACHE.is_file():
        raise FileNotFoundError("historie-wache.py fehlt: %s" % WACHE)
    r = subprocess.run([str(PYTHON), str(WACHE)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("historie-wache.py endete mit %d: %s"
                           % (r.returncode, (r.stderr or "").strip()[:300]))
    return (r.stdout or "").strip()


def main():
    if not PYTHON.is_file():
        print("FEHLER: %s fehlt - Nachladen abgebrochen." % PYTHON)
        return 2
    m = _merk()
    fehl = int(m.get("fehlversuche", 0) or 0)
    letzter = float(m.get("letzter_fehlversuch", 0) or 0)

    # Zu viele Fehlversuche -> heute schweigen, morgen wieder versuchen.
    if fehl >= MAX_FEHLVERSUCHE:
        if time.time() - letzter < PAUSE_NACH_FEHLVERSUCH_S:
            return 0
        fehl = 0                                     # neue Runde beginnt

    try:
        befund = _zu_tun()
    except (FileNotFoundError, RuntimeError, OSError) as fehler:
        # LIEUT: "alles frisch" waere hier eine Falschaussage. Der Fehler
        # geht nach Telegram, sonst faellt ein toter Wecker nie auf.
        print("FEHLER: die Wache liess sich nicht fragen - %s" % fehler)
        _merke({"fehlversuche": fehl + 1,
                "letzter_fehlversuch": time.time(),
                "bemerkung": "Wache nicht lesbar"})
        return 2
    if not befund:
        # Alles frisch. Kein Wort, kein Prozess - der Normalfall.
        _merke({"fehlversuche": 0, "letzter_lauf_s": int(time.time()),
                "bemerkung": "alles frisch"})
        return 0

    print("Historie veraltet - lade nach (Ziel %d x %s)" % (TOP, TAKT))
    r = subprocess.run([str(PYTHON), str(NACHLADEN), "--anwenden",
                        "--top", str(TOP), "--takt", TAKT],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    ausgabe = ((r.stdout or "") + (r.stderr or "")).strip()
    print(ausgabe)
    if r.returncode == 0:
        _merke({"fehlversuche": 0, "letzter_lauf_s": int(time.time()),
                "bemerkung": "nachgeladen"})
        return 0
    _merke({"fehlversuche": fehl + 1,
            "letzter_fehlversuch": time.time(),
            "bemerkung": "Nachladeversuch %d fehlgeschlagen (Code %d)"
                         % (fehl + 1, r.returncode)})
    return 1


if __name__ == "__main__":
    sys.exit(main())