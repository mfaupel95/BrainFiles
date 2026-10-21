"""Haken von spur_buch.py (und der Herzschlag-Wache) ins bestehende Tracking.

Es gibt EIN Tracking-System im Haus: tracking.py -> tracking.db (SQLite). Dieses
Modul ist nur der Adapter dazwischen: es uebersetzt eine Buchung der Bot-Spuren
in die Ereignisse von tracking.py und gleicht deren Schema an, damit die
KB-Auswertung (kb_snapshot_json) die Spuren mitzaehlt.

    Buchung (spur_buch)        tracking.py-Ereignis
    ------------------------   -------------------------------------------
    Signal -> Einstieg         signal.ausgewaehlt
    Eroeffnen                  position.eroeffnet
    Schliessen                 zyklus.abgeschlossen   (= eine abgeschlossene Runde)
    Zyklus mit Fehler          lauf.fehlgeschlagen    (Erfolge bewusst nicht)
    Herzschlag-Wache           stoerung.erkannt

Regeln:
  * Wirft nie. Ein Fehler in der Telemetrie darf keine Buchung abbrechen.
  * Journale ausserhalb von Agenten/Handel/<spur>/ (Tests, Replay) werden nicht
    protokolliert - sonst schriebe jeder Test in die echte tracking.db.
  * TELEMETRIE_AUS=1 schaltet alles ab.
  * Schema wie der Scanner: ausstiegsgrund = erstes Wort von `grund` (die
    KB-Stop-Quote zaehlt == "stop"), ergebnis_eur = G/V in USD (der Name ist
    historisch), is_paper = modus != "live".

Rueckgabe jeder Funktion: "ok" | "aus" | "fremd" | "nichts".
"""

import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.append(HIER)

import tracking  # noqa: E402

AUS = os.environ.get("TELEMETRIE_AUS") == "1"


def spur_aus_pfad(journal_pfad):
    """Agenten/Handel/<spur>/handelsjournal.csv -> "<spur>"."""
    return os.path.basename(os.path.dirname(os.path.abspath(journal_pfad)))


def _im_haus(journal_pfad):
    """Nur Agenten/Handel/<spur>/<journal>; nicht tests/, nicht tiefer, nicht fremd."""
    ordner = os.path.dirname(os.path.abspath(journal_pfad))
    return (os.path.dirname(ordner) == HIER
            and os.path.basename(ordner) not in ("tests", "telemetrie"))


def _zahl(x):
    try:
        return round(float(x), 4)
    except (TypeError, ValueError):
        return None


def ausstiegsgrund(grund):
    """Erstes Wort von `grund` (wie scanner/handeln.py), klein geschrieben."""
    return (grund or "").strip().split(" ")[0].lower() or "unbekannt"


def _tue(journal_pfad, fn):
    """Gemeinsamer Rahmen: Aus-Schalter, Pfadfilter, nie werfen."""
    if AUS:
        return "aus"
    try:
        if journal_pfad is not None and not _im_haus(journal_pfad):
            return "fremd"
        fn()
        return "ok"
    except Exception:                                       # noqa: BLE001
        return "nichts"


def signal_ausgewaehlt(journal_pfad, inst, seite, modus, stufe="basis"):
    """signal.ausgewaehlt: das Signal fuehrt zu einem Einstieg (oder, im Live-Gatter, zur Queue)."""
    return _tue(journal_pfad, lambda: tracking.track_signal_ausgewaehlt(
        spur_name=spur_aus_pfad(journal_pfad), instrument=inst, richtung=seite,
        is_paper=modus != "live", risikostufe=stufe))


def eroeffnet(journal_pfad, p, modus, inst, seite, stufe="basis"):
    """position.eroeffnet aus der frisch eroeffneten Position `p` (spur_buch.einstieg)."""
    return _tue(journal_pfad, lambda: tracking.track_position_eroeffnet(
        spur_name=spur_aus_pfad(journal_pfad), instrument=inst, richtung=seite,
        einstieg_kurs=_zahl(p.get("einstieg")), stop_kurs=_zahl(p.get("stop")),
        ziel_kurs=_zahl(p.get("ziel")), nominal_eur=_zahl(p.get("nominal")),
        is_paper=modus != "live", risikostufe=stufe, hebel=_zahl(p.get("hebel"))))


def geschlossen(journal_pfad, p, modus, grund, gv, kurs, haltetage, stufe="basis"):
    """zyklus.abgeschlossen aus der beendeten Position `p`; gv = G/V in USD, kurs = Ausstiegskurs."""
    def _senden():
        nominal = _zahl(p.get("nominal"))
        tracking.track_zyklus_abgeschlossen(
            spur_name=spur_aus_pfad(journal_pfad), instrument=p.get("inst"),
            richtung=p.get("seite") or p.get("richtung"),
            einstieg_kurs=_zahl(p.get("einstieg")), ausstieg_kurs=_zahl(kurs),
            # G/V auf den Nominalwert, vorzeichenrichtig fuer long UND short
            ergebnis_pct=round(float(gv) / nominal * 100, 4) if nominal else None,
            ergebnis_eur=_zahl(gv),
            haltedauer_stunden=float(haltetage or 0) * 24,
            ausstiegsgrund=ausstiegsgrund(grund),
            is_paper=modus != "live", risikostufe=stufe, hebel=_zahl(p.get("hebel")))
    return _tue(journal_pfad, _senden)


def lauf_fehlgeschlagen(journal_pfad, dauer_s, modus, stufe="basis"):
    """lauf.fehlgeschlagen: ein Zyklus der Spur endete mit Fehler."""
    return _tue(journal_pfad, lambda: tracking.track_lauf_fehlgeschlagen(
        spur_name=spur_aus_pfad(journal_pfad), dauer_s=_zahl(dauer_s) or 0.0,
        is_paper=modus != "live", risikostufe=stufe))


def konfiguriert(wachen_pfad, feld, alt=None, neu=None):
    """spur.konfiguriert: die wachen.json einer Spur wurde per Skript geaendert.

    `wachen_pfad` = Agenten/Handel/<spur>/wachen.json (gleiche Pfadregel wie bei den Journalen).
    """
    return _tue(wachen_pfad, lambda: tracking.track_spur_konfiguriert(
        spur_name=spur_aus_pfad(wachen_pfad), geaendertes_feld=feld,
        alter_wert=None if alt is None else str(alt),
        neuer_wert=None if neu is None else str(neu)))


def stoerung(spur_id, art, dauer_s=None, flachgestellt=False):
    """stoerung.erkannt: art in herzschlag_alt | abruf_fehler | api_fehler | journal_luecke."""
    return _tue(None, lambda: tracking.track_stoerung_erkannt(
        spur_name=spur_id, art=art, dauer_s=_zahl(dauer_s),
        flachgestellt=bool(flachgestellt)))
