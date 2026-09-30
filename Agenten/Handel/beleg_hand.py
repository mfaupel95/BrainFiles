"""Die HAND: fuehrt Auftraege aus, die eine Spur mit einem Freigabe-Beleg versehen hat.

Warum es dieses Skript gibt
---------------------------
Seit dem 22.09.2026 darf eine Spur einen Auftrag **abgeben** statt ihn selbst
auszufuehren (`order_ueber: "mcp"` in ihrer wachen.json). Den Beleg stellt sie
aus, die Order legt die Hand - entweder das Kraken-MCP-Werkzeug
`kraken_order_mit_beleg` (aus einer Sitzung) oder dieses Skript (im Betrieb,
ohne Sitzung). Beide pruefen DENSELBEN Beleg ueber denselben Code
(`Agenten/Handel/freigabebeleg.py`); damit gibt es keine zweite Wahrheit
darueber, was erlaubt ist.

Ohne dieses Skript waere der Beleg-Weg im Dauerlauf ein Stillstand: die Spur
gibt ab, und niemand nimmt. Was es NICHT tut: entscheiden. Es fuehrt genau das
aus, was im Beleg steht (Paar, Menge, Hoechstpreis, Stop, Ziel) - und nur,
solange der Beleg gilt.

Aufruf (aus dem Handel-Ordner):
    python beleg_hand.py                 # Vorschau, schreibt nichts
    python beleg_hand.py --anwenden      # fuehrt aus und verbraucht den Beleg
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))


def _lade(name: str, pfad: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


beleg = _lade("freigabebeleg", os.path.join(HIER, "freigabebeleg.py"))


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _kraken_weg():
    """Die Spur kraken: ihr eigenes Modul stellt Order und Journal bereit."""
    ordner = os.path.join(HIER, "kraken")
    if ordner not in sys.path:
        sys.path.insert(0, ordner)
    return _lade("kraken_handeln_hand", os.path.join(ordner, "handeln.py"))


def fuehre_aus(eintrag: dict, anwenden: bool) -> dict:
    """Einen Beleg ausfuehren. Gibt einen Bericht zurueck (nie eine Ausnahme)."""
    spur = eintrag["spur"]
    kennung = eintrag["kennung"]
    if spur != "kraken":
        return {"spur": spur, "kennung": kennung, "ergebnis": "kein Weg fuer diese Spur"}

    handeln = _kraken_weg()
    zusatz = eintrag.get("zusatz") or {}
    inst = zusatz.get("inst") or eintrag["paar"]
    stop = zusatz.get("stop")
    ziel = zusatz.get("ziel")
    menge = float(eintrag["menge"])
    preis_max = eintrag.get("preis_max")

    # Der Beleg muss JETZT noch passen - dieselbe Pruefung wie im MCP-Werkzeug.
    kurs = None
    try:
        kurs = handeln.kraken.letzter_kurs(inst)
    except Exception:                                             # noqa: BLE001
        kurs = None
    ok, warum = beleg.pruefe(kennung, spur, eintrag["seite"], eintrag["paar"],
                             menge, kurs if kurs else preis_max)
    if not ok:
        return {"spur": spur, "kennung": kennung, "ergebnis": "abgelehnt: %s" % warum}
    if not anwenden:
        return {"spur": spur, "kennung": kennung, "ergebnis": "wuerde kaufen",
                "paar": eintrag["paar"], "menge": menge, "stop": stop, "ziel": ziel}

    # Einloesen VOR der Order: der Beleg ist einmalig. Bliebe er liegen,
    # koennte eine zweite Hand dieselbe Order ein zweites Mal ausfuehren.
    beleg.verbrauche(spur, kennung, ergebnis="beleg_hand")

    w = handeln.scan.wachen()
    z = handeln.lade_zustand()
    if len(z.get("positionen", [])) >= w["max_offene_positionen"]:
        return {"spur": spur, "kennung": kennung,
                "ergebnis": "abgelehnt: Buch voll (%d/%d)"
                            % (len(z["positionen"]), w["max_offene_positionen"])}

    try:
        txid = handeln.kraken.markt_kauf(inst, menge, echt=True)
        gefuellt = handeln.kraken.gefuellte_menge(txid) if txid else 0.0
    except Exception as e:                                        # noqa: BLE001
        handeln.journal(_jetzt(), "live", "fehler", inst, "", "", "", "", "",
                        "beleg_hand: Kauf fehlgeschlagen (%s)" % e)
        return {"spur": spur, "kennung": kennung,
                "ergebnis": "Kauf fehlgeschlagen: %s" % e}
    if gefuellt <= 0:
        handeln.journal(_jetzt(), "live", "fehler", inst, "", "", "", "", "",
                        "beleg_hand: Kauf ohne Fuellung")
        return {"spur": spur, "kennung": kennung, "ergebnis": "Kauf ohne Fuellung"}

    stop_txid, stop_fehlt = None, False
    if stop:
        try:
            stop_txid = handeln.kraken.stop_setzen(inst, gefuellt, stop, echt=True)
        except Exception as e:                                    # noqa: BLE001
            # Ohne Notausstieg zurueckverkaufen - lieber kein Eintrag als eine
            # unbewachte Position (dieselbe Regel wie im Spur-Weg).
            try:
                handeln.kraken.markt_verkauf(inst, gefuellt, echt=True)
                handeln.journal(_jetzt(), "live", "fehler", inst, "", "", "", "", "",
                                "beleg_hand: Stop fehlgeschlagen (%s) - zurueckverkauft" % e)
                return {"spur": spur, "kennung": kennung,
                        "ergebnis": "Stop fehlgeschlagen, zurueckverkauft"}
            except Exception as e2:                               # noqa: BLE001
                stop_fehlt = True
                handeln.journal(_jetzt(), "live", "fehler", inst, "", "", "", "", "",
                                "beleg_hand: Stop UND Rueckverkauf fehlgeschlagen (%s)" % e2)

    # Der Einsatz ist GELD, nicht der Stueckpreis. Hier stand bis zum
    # 30.09.2026 `eintrag["preis_max"]` - also der Hoechstpreis JE STUECK.
    # Folge: das Buch fuehrte 1,14 EUR statt 50,05 EUR fuer DOTEUR (und
    # 0,21/0,95/1,60 fuer XLM/FIL/ATOM). Jede Auswertung, jeder Ruecklauf und
    # jede Ratsche rechnen damit falsch, und `eingesetzt` war um Faktor 30 zu
    # klein (Befund T-208). Richtig ist wie im Zyklus-Weg: Menge x Kurs.
    eur = round(gefuellt * float(kurs if kurs else preis_max or 0.0), 2)
    kosten = eur * w.get("gebuehr_taker", 0.0)
    z.setdefault("positionen", []).append({
        "paar": inst, "einstieg": kurs, "eur": round(eur, 2), "menge": gefuellt,
        "stop": stop, "ziel": ziel, "eroeffnet": _jetzt()[:10],
        "kauf_txid": txid, "stop_txid": stop_txid, "boersen_stop_fehlt": stop_fehlt,
    })
    handeln.schreibe_zustand(z)
    handeln.journal(_jetzt(), "live", "kauf", inst, "%.8g" % (kurs or 0.0),
                    "%.2f" % (eur + kosten), "%.8f" % gefuellt,
                    "%.8g" % (stop or 0.0), "%.8g" % (ziel or 0.0),
                    "beleg %s ueber die Hand" % kennung)
    try:
        handeln._spiegeln(w, z)                      # Bedingung 4
    except Exception as e:                                        # noqa: BLE001
        print("  Spiegelung fehlgeschlagen: %s" % e, file=sys.stderr)
    return {"spur": spur, "kennung": kennung, "ergebnis": "ausgefuehrt",
            "paar": inst, "menge": gefuellt, "txid": txid, "stop_txid": stop_txid,
            "stop_fehlt": stop_fehlt}


def lauf(anwenden: bool = False) -> list[dict]:
    berichte = []
    for eintrag in beleg.offene():
        bericht = fuehre_aus(eintrag, anwenden)
        berichte.append(bericht)
        print("%-10s %s %s" % (bericht["spur"], bericht["kennung"],
                               bericht["ergebnis"]))
    if not berichte:
        print("keine offenen Belege - nichts zu tun")
    return berichte


def main() -> int:
    a = argparse.ArgumentParser(description="Fuehrt belegte Auftraege aus (die Hand).")
    a.add_argument("--anwenden", action="store_true",
                   help="wirklich ausfuehren (Standard: nur Vorschau)")
    args = a.parse_args()
    lauf(anwenden=args.anwenden)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())