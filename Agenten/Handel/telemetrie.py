"""Telemetrie des Handelsagenten - drei Aufrufe: nutzer(), spur()/position(), ereignis().

Plan: Werkstatt/Projekte/Tracking/.telemetry/tracking-plan.yaml (v1.0.0).
Regel wie in Bus/ereignis.py: ein totes Ziel darf nie einen Lauf abbrechen.
Jede Funktion faengt alles ab, wirft nie und gibt zurueck, wohin die Zeile ging:
"datei" | "aus" | "nichts".
"""

import json
import os
import sys
import uuid
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.environ.get("TELEMETRIE_DIR") or os.path.join(HIER, "telemetrie")
AUS = os.environ.get("TELEMETRIE_AUS") == "1"
BUS_AN = os.environ.get("TELEMETRIE_BUS") == "1"
BUS = os.path.join(os.path.dirname(HIER), "Bus")

VERSION_PLAN = "1.0.1"
USER_ID = "max"

# --- Ereignisnamen (Plan v1.0.0). Nie als Rohtext im Code schreiben. ---------
LAUF_BEENDET = "lauf.beendet"
SIGNAL_ERKANNT = "signal.erkannt"
POSITION_EROEFFNET = "position.eroeffnet"
POSITION_GESCHLOSSEN = "position.geschlossen"
POSITION_NACHGEZOGEN = "position.nachgezogen"
WACHE_GEAENDERT = "wache.geaendert"
FREIGABE_GEPRUEFT = "freigabe.geprueft"
STOERUNG_ERKANNT = "stoerung.erkannt"

# Pflicht-Properties je Ereignis. Fehlt eines, wird die Zeile trotzdem
# geschrieben und mit "_fehlt" markiert (statt zu werfen).
PFLICHT = {
    LAUF_BEENDET: ("ergebnis", "dauer_s", "modus"),
    SIGNAL_ERKANNT: ("inst", "seite", "abgelehnt_von"),
    # `hebel` ist optional: die Bot-Spuren aus spur_buch.py fuehren keinen.
    POSITION_EROEFFNET: ("pos_id", "modus", "inst", "seite", "nominal_usd",
                         "stop_abstand_pct"),
    POSITION_GESCHLOSSEN: ("pos_id", "modus", "inst", "ausstiegsart",
                           "ergebnis_usd", "ergebnis_pct", "haltetage"),
    POSITION_NACHGEZOGEN: ("pos_id", "stufe", "quelle"),
    WACHE_GEAENDERT: ("feld", "nach", "urheber"),
    FREIGABE_GEPRUEFT: ("bestanden", "bedingung"),
    STOERUNG_ERKANNT: ("art", "flachgestellt"),
}

# Selten und wichtig: nur diese gehen (mit TELEMETRIE_BUS=1) zusaetzlich an den Bus.
BUS_EREIGNISSE = {STOERUNG_ERKANNT, WACHE_GEAENDERT, FREIGABE_GEPRUEFT}


def ausstiegsart(grund):
    """Journal-Spalte `grund` -> Property `ausstiegsart` (Werte aus dem Audit)."""
    erstes = (grund or "").strip().split(" ")[0].lower()
    if "herzschlag" in erstes:
        return "stoerung"
    if erstes.startswith("stop"):
        return "stop"
    if erstes.startswith("ziel"):
        return "ziel"
    if erstes.startswith("trailing"):
        return "trailing"
    if erstes.startswith("handanpassung"):
        return "manuell"
    return "signal"


def _an_bus(zeile):
    """Optional: dieselbe Zeile als Bus-Ereignis (was="telemetrie"). Wirft nie."""
    try:
        if BUS not in sys.path:
            sys.path.insert(0, BUS)
        import ereignis
        import journal
        wer = "handel/%s" % (zeile.get("group_spur") or "telemetrie")
        ereignis.melden(journal.neu(wer, "telemetrie",
                                    text=json.dumps(zeile, ensure_ascii=False)))
    except Exception:                                       # noqa: BLE001
        pass


def _zustellen(methode, payload):
    """Der einzige Weg nach draussen. methode: identify | group | track."""
    if AUS:
        return "aus"
    try:
        zeile = {
            "id": uuid.uuid4().hex,
            "zeit": datetime.now().astimezone().isoformat(timespec="seconds"),
            "methode": methode,
            "plan": VERSION_PLAN,
            "user_id": USER_ID,
        }
        zeile.update(payload)
        os.makedirs(WURZEL, exist_ok=True)
        pfad = os.path.join(WURZEL, datetime.now().strftime("%Y-%m-%d") + ".jsonl")
        with open(pfad, "a", encoding="utf-8") as f:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except Exception:                                       # noqa: BLE001
        return "nichts"
    if BUS_AN and methode == "track" and payload.get("event") in BUS_EREIGNISSE:
        _an_bus(zeile)
    return "datei"


def nutzer(freigabe_stufe):
    """identify(): Trait freigabe_stufe in papier | demo | live. Bei Aenderung."""
    return _zustellen("identify", {"traits": {"freigabe_stufe": freigabe_stufe}})


def spur(spur_id, **traits):
    """group() Ebene spur. Traits: risikostufe, modus, handelsrunden_count,
    stoerungs_ausstiege_count, letzter_lauf_at. Bei Anlage, Wachen-Aenderung, Tagessnapshot."""
    return _zustellen("group", {"group_type": "spur", "group_id": spur_id,
                                "traits": traits})


def position(pos_id, spur_id):
    """group() Ebene position. Elternbezug ueber parent_group_id."""
    return _zustellen("group", {"group_type": "position", "group_id": pos_id,
                                "parent_group_id": spur_id, "traits": {}})


def ereignis(name, spur_id=None, **props):
    """track(): Ereignis aus dem Plan. Attribution: group_spur aus spur_id,
    group_position aus props["pos_id"] (falls vorhanden)."""
    fehlt = [p for p in PFLICHT.get(name, ()) if props.get(p) is None]
    zeile = {"event": name, "group_spur": spur_id,
             "group_position": props.get("pos_id"), "properties": props}
    if name not in PFLICHT:
        zeile["_unbekannt"] = True
    if fehlt:
        zeile["_fehlt"] = fehlt
    return _zustellen("track", zeile)


# --- Haken fuer spur_buch.py -------------------------------------------------
# Ein Aufruf je Buchung. Alles Ableiten steht hier und ist in try gefasst: ein
# Fehler in der Telemetrie darf nie eine Buchung (Journal + Zustand) abbrechen.
# Journale ausserhalb von Agenten/Handel (Tests, Replay in Wegwerfordnern)
# werden nicht protokolliert.

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


def eroeffnet(journal_pfad, p, modus, inst, seite):
    """position.eroeffnet aus der frisch eroeffneten Position `p` (spur_buch.einstieg)."""
    try:
        if not _im_haus(journal_pfad):
            return "fremd"
        sp = spur_aus_pfad(journal_pfad)
        einstieg = _zahl(p.get("einstieg"))
        ziel = _zahl(p.get("ziel"))
        ziel_pct = None
        if einstieg and ziel:
            ziel_pct = round(abs(ziel - einstieg) / einstieg * 100, 4)
        position(p.get("pos_id"), sp)
        return ereignis(POSITION_EROEFFNET, sp, pos_id=p.get("pos_id"),
                        modus=modus, inst=inst, seite=seite,
                        nominal_usd=_zahl(p.get("nominal")),
                        hebel=_zahl(p.get("hebel")),
                        stop_abstand_pct=_zahl(p.get("stop_pct")),
                        ziel_abstand_pct=ziel_pct)
    except Exception:                                       # noqa: BLE001
        return "nichts"


def lauf_beendet(journal_pfad, ergebnis, dauer_s, modus):
    """lauf.beendet: ein Zyklus der Spur ist durch (spur_buch.zyklus)."""
    try:
        if not _im_haus(journal_pfad):
            return "fremd"
        return ereignis(LAUF_BEENDET, spur_aus_pfad(journal_pfad),
                        ergebnis=ergebnis, dauer_s=_zahl(dauer_s), modus=modus)
    except Exception:                                       # noqa: BLE001
        return "nichts"


def stoerung(spur_id, art, dauer_s=None, flachgestellt=False):
    """stoerung.erkannt: art in herzschlag_alt | abruf_fehler | api_fehler | journal_luecke."""
    try:
        return ereignis(STOERUNG_ERKANNT, spur_id, art=art,
                        dauer_s=_zahl(dauer_s), flachgestellt=bool(flachgestellt))
    except Exception:                                       # noqa: BLE001
        return "nichts"


def geschlossen(journal_pfad, p, modus, grund, gv, haltetage):
    """position.geschlossen aus der beendeten Position `p`; gv = G/V in USD."""
    try:
        if not _im_haus(journal_pfad):
            return "fremd"
        sp = spur_aus_pfad(journal_pfad)
        nominal = _zahl(p.get("nominal"))
        pct = round(float(gv) / nominal * 100, 4) if nominal else None
        return ereignis(POSITION_GESCHLOSSEN, sp, pos_id=p.get("pos_id"),
                        modus=modus, inst=p.get("inst"),
                        ausstiegsart=ausstiegsart(grund),
                        ergebnis_usd=_zahl(gv), ergebnis_pct=pct,
                        haltetage=_zahl(haltetage),
                        mfe_pct=_zahl(p.get("mfe_pct")),
                        mae_pct=_zahl(p.get("mae_pct")))
    except Exception:                                       # noqa: BLE001
        return "nichts"
