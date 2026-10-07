"""Ruecktest-Engine fuer Spur 2 (XPERP), Trend-Modus. Ruft die bestehenden
PUREN Rechenfunktionen aus xperp/ direkt auf (siehe Spec, Architektur-
entscheidung) statt Signal-/Groessen-/Trailing-Logik zweimal zu schreiben.

Nur Standardbibliothek.
"""

import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
_XPERP = WURZEL.parent / "xperp"
_HANDEL = WURZEL.parent
for _p in (_HANDEL, _XPERP, WURZEL):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import auswahl  # noqa: E402
import bot  # noqa: E402
import cvd  # noqa: E402
import indikatoren  # noqa: E402
import okxf  # noqa: E402
import trailing as trailing_modul  # noqa: E402
import wachen_xperp as wx  # noqa: E402
from signal_wechsel import ERLAEUT, zugelassen  # noqa: E402

MIN_KERZEN_4H = auswahl.MIN_KERZEN


def schnitt_bis(kerzen, zeit_ms):
    """Alle Kerzen mit ts <= zeit_ms - kein Vorgriff auf die Zukunft."""
    return [k for k in kerzen if k[0] <= zeit_ms]


def rangliste_schritt(universum, kerzen_4h_je_inst, kerzen_1d_je_inst,
                      umsatz_je_inst, zeit_ms):
    """Kennzahlen+Punkte aller Instrumente mit genuegend Historie BIS zeit_ms.

    Punkt-in-Zeit-Aequivalent zu auswahl.sammle(): derselbe kennzahlen()/
    bewerte()-Aufruf, aber auf einem auf zeit_ms geschnittenen Fenster.
    """
    aus = []
    for x in universum:
        iid = x["instId"]
        k4 = schnitt_bis(kerzen_4h_je_inst.get(iid, []), zeit_ms)
        if len(k4) < MIN_KERZEN_4H:
            continue
        z = auswahl.kennzahlen(k4)
        kt = schnitt_bis(kerzen_1d_je_inst.get(iid, []), zeit_ms)
        if len(kt) >= 14:
            z["mae_long"], z["mae_short"] = auswahl.mae_tage(kt, 7)
        kat = auswahl.KATEGORIEN[x["kategorie"]]
        umsatz = umsatz_je_inst.get(iid, 0.0)
        z.update(basis=x["basis"], instId=iid, umsatz=umsatz,
                 kategorie=x["kategorie"], vola_tor=kat["vola_tor"],
                 punkte=auswahl.bewerte(z, umsatz, kat["umsatz_bezug"]))
        aus.append(z)
    return aus


def kandidaten_schritt(werte, w, anzahl=6):
    """Die besten Werte je Richtung, die ihre Tore bestehen.

    1:1 die Filterkette aus handeln.kandidaten() - Vola-Tor, Familie aktiv,
    Umsatz-Bezug der Familie, Hebel-Deckel >= max_hebel.
    """
    aus = []
    for seite in ("long", "short"):
        beste = sorted(werte, key=lambda x: -x["punkte"][seite])
        for x in beste:
            if len(aus) >= anzahl * 2:
                break
            if x["vola"] > x["vola_tor"]:
                continue
            fam = (w.get("familien") or {}).get(x["kategorie"], {})
            if not fam.get("aktiv", True):
                continue
            if x["umsatz"] < fam.get("umsatz_bezug_usd",
                                     w["min_umsatz_24h_usd"]):
                continue
            mae = x["mae_short"] if seite == "short" else x["mae_long"]
            deckel = auswahl.hebel_deckel(mae)
            if deckel < w["max_hebel"]:
                continue
            aus.append({"basis": x["basis"], "instId": x["instId"],
                        "seite": seite, "kategorie": x["kategorie"],
                        "punkte": x["punkte"][seite], "deckel": deckel})
    return aus
