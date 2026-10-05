"""Historie-Auffuell-Wache: laesst die Feed-Historie nicht veralten.

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut**, es wird nichts gesendet (Watchdog-Muster wie breite-wache.py).

WARUM ES SIE GIBT
-----------------
`moondev_historie.py` haelt die historischen Kerzen fuer die Feed-Spuren
(`daten/historie/<sym>_<takt>.json`). Sie ist die Grundlage von

  * `replay.lauf_feed` / `replay.lauf_c` (der historische Backtest),
  * `test_replay_feed.GegenprobeJournalTest` - der EINZIGEN Gegenprobe, die
    die Feed-Preise der Spuren (CoinGecko im Betrieb) gegen eine zweite
    Quelle (Binance) stellt.

BEFUND 05.10.2026: `daten/historie/` enthielt nur DREI `1D`-Dateien (BTC, ETH,
SOL) vom 25.09.2026. `Bestand().symbole()` lieferte 0, `schritte()` fand
keinen Zeitpunkt, und beide Gegenproben meldeten "zu wenige gemeinsame Tage -
nichts geprueft". Die Historie waechst nur, wenn JEMAND sie manuell nachlaedt
- eine Routine, ein Cron oder ein Aufruf gab es nicht (`grep` ueber
`Agenten/Routinen/` und `Agenten/Hermes/scripts/` fand nichts). Ein
waechsender Datenstand mit keinem Nachfuell-Weg ist ein Befund, den erst der
rote Test sichtbar machte.

DIE REGEL
---------
Nachgefüllt wird NICHT nach Kalender, sondern nach ALTER der Reihen: eine
`1D`-Reihe, deren jüngste Kerze mehr als `MAX_ALTER_TAGE` (5) Tage alt ist,
wird geholt. Ein Lauf, bei dem alle Reihen frisch sind, meldet nichts.

DIE ZWEITE HAEUSEREGEL: DER LAUF MELDET, ER RECHNET NICHT.
---------------------------------------------------------
Diese Wache ist kein Nachladewerkzeug. Sie sagt, welche Reihen zu alt sind -
die Breite des Nachladens ist eine Entscheidung (Top-300 Univum heisst
tausende Kerzen und echte Laufzeit), und die gehoert dem Menschen bzw. einem
bewussten Auftrag. Ein stiller Datenverlust ist schlimmer als roter Text.

WAS ES NICHT TUT
----------------
Es holt nichts, schreibt in keine Spur und handelt nicht. Es liest nur die
Reihen auf der Platte und meldet das Alter.
"""

import argparse
import json
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # Agenten/Hermes/scripts/ -> BrainFiles
HANDEL = WURZEL / "Agenten" / "Handel"
MERKDATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "historie-wache.json"

# Eine 1D-Reihe, die aelter ist, deckt das Ende des Backtest-Fensters nicht ab.
# Fuenf Tage ist gross genug fuer ein Tages-Takt-Raster und klein genug, damit
# das Nachladen nicht zur Wochenarbeit wird.
MAX_ALTER_TAGE = 5
# NUR diese Takte werden ueberwacht. `replay.lauf_feed` liest `1D` (Vorgabe)
# und `lauf_c` die `1H`; 5M/4H sind Altbestand aus dem 29.09.-Aufbau und
# werden von keinem Lauf gelesen. Ein Takt, den nichts liest, wird nicht
# gemeldet - sonst waere die Wache am Ende jeder Woche nur noch Rauschen.
# Der Mindestwert ist die Zahl, die `replay.lauf_feed` selbst verlangt
# (`mindest_symbole`, Vorgabe 30) - fuer 1H liegt er darunter, weil dort ein
# Instrument je Reihe genuegt.
TAKTE_BEACHTET = {"1D": 30, "1H": 4}
TAG_MS = 86_400_000


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


def _reihen():
    """(takt -> [(symbol, letzte_kerze_ms, kerzen)]) aus dem Ordner.

    Gelesen wird die PLATTE, nicht der Stand in `_stand.json`: der Ordner ist
    die Wahrheit (dieselbe Regel wie in `moondev_historie._lade_universum`).
    Der `_stand.json`-Eintrag darf aelter sein als die Datei daneben.
    """
    # `moondev_historie.ORDNER` ist `daten/historie/FEED` - dort schreibt der
    # Abruf und von dort liest `replay.lauf_feed` (ueber
    # `moondev_historie.lade_feed`). Die erste Fassung las `daten/historie`
    # OHNE `feed`: sie zaehlte drei verwaiste Dateien vom 25.09. und meldete
    # "zu wenig Reihen", waehrend im echten Ordner 30 lagen (Befund
    # 05.10.2026, gefunden durch: Abruf meldete "30 geschrieben", Dateizahl
    # blieb 3). Der Pfad wird hier bewusst als KONSTANTE aus dem
    # Abrufmodul geholt, nicht geraten - sonst genau dieser Fehler beim
    # naechsten Umbau.
    ordner = _feed_ordner()
    if not ordner.is_dir():
        return None, []
    aus = {}
    for pfad in sorted(ordner.glob("*_*.json")):
        if pfad.name.startswith("_"):
            continue
        teile = pfad.stem.rsplit("_", 1)
        if len(teile) != 2:
            continue
        sym, takt = teile
        try:
            with open(pfad, encoding="utf-8") as f:
                reihe = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(reihe, list) or not reihe:
            continue
        aus.setdefault(takt, []).append((sym, reihe[-1][0], len(reihe)))
    return ordner, aus


def _alter_tage(ts_ms, jetzt_ms):
    return (jetzt_ms - int(ts_ms)) / float(TAG_MS)


def befunde(jetzt_ms=None):
    """Was zu alt ist. Rueckgabe: (zeilen, merker)."""
    jetzt_ms = jetzt_ms or int(time.time() * 1000)
    ordner, takte = _reihen()
    if ordner is None:
        return (["Historie fehlt: %s/%s liegt nicht da - Feed-Backtest und "
                 "die Binance-Gegenprobe koennen nichts messen."
                 % (HANDEL.name, "daten/historie")], {})

    merker = {"takte": {}, "jetzt_ms": jetzt_ms}
    zeilen = []
    for takt, reihen in sorted(takte.items()):
        if takt not in TAKTE_BEACHTET:
            continue                      # niemand liest diesen Takt
        alt = []
        for sym, letzte, _anzahl in reihen:
            tage = _alter_tage(letzte, jetzt_ms)
            if tage > MAX_ALTER_TAGE:
                alt.append((sym, tage))
        merker["takte"][takt] = {"n": len(reihen),
                                 "juengste_tage": round(min(
                                     (_alter_tage(l, jetzt_ms)
                                      for _s, l, _a in reihen), default=0.0), 2),
                                 "zu_alt": sorted(s for s, _ in alt)}
        n_woll = TAKTE_BEACHTET[takt]
        if len(reihen) < n_woll:
            zeilen.append("%s: nur %d von %d noetigen Reihen auf der Platte - "
                          "der Backtest verlangt %d gleichzeitige Reihen und "
                          "bricht sonst mit 'kein Schritt' ab"
                          % (takt, len(reihen), n_woll, n_woll))
        if alt:
            zeilen.append("%s: %d von %d Reihen aelter als %d Tage"
                          % (takt, len(alt), len(reihen), MAX_ALTER_TAGE))
            for sym, tage in sorted(alt, key=lambda x: -x[1])[:5]:
                zeilen.append("  %s: %.1f Tage" % (sym, tage))
    return zeilen, merker


def _merke(stand):
    try:
        MERKDATEI.parent.mkdir(parents=True, exist_ok=True)
        with open(MERKDATEI, "w", encoding="utf-8", newline="\n") as f:
            json.dump(stand, f, ensure_ascii=False, indent=1, sort_keys=True)
    except OSError:
        pass                                   # Merken ist Komfort


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--stand", action="store_true",
                   help="Lage immer zeigen, auch wenn alles frisch ist")
    a = p.parse_args(argv)

    zeilen, merker = befunde()
    _merke(merker)
    if zeilen:
        print("\n".join(zeilen))
    elif a.stand:
        for takt, m in sorted((merker.get("takte") or {}).items()):
            print("%s: %d Reihen, juengste %.2f Tage alt - alles frisch"
                  % (takt, m["n"], m["juengste_tage"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())