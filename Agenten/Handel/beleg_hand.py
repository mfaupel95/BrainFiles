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

    w = handeln.scan.wachen()
    z = handeln.lade_zustand()
    if len(z.get("positionen", [])) >= w["max_offene_positionen"]:
        return {"spur": spur, "kennung": kennung,
                "ergebnis": "abgelehnt: Buch voll (%d/%d)"
                            % (len(z["positionen"]), w["max_offene_positionen"])}

    # Duplikats-Gatter (T-102): schon ein Beleg, eine Position oder eine
    # offene Kauf-Order fuer dasselbe Instrument? Ein zweiter Kauf wuerde
    # denselben Wert doppelt besitzen - genau das war der FILEUR-Fehler am
    # 28.09.2026 (vier Kaeufe fuer EIN Signal, ~200 EUR). Drei Zeugen:
    #   1. die BELEGE (ein ANDERER, noch gueltiger Beleg fuer dasselbe Paar),
    #   2. das BUCH   (eine offene Position - schnell, immer da),
    #   3. die BOERSE (eine offene Kauf-Order fuer dasselbe Paar).
    # Der EIGENE Beleg (kennung) ist kein Duplikat - er ist die Erlaubnis,
    # die wir gerade ausfuehren. Ohne diese Ausnahme wuerde sich jede Hand
    # selbst ablehnen: `offene()` fuehrt den eigenen Beleg bis `verbrauche()`.
    beleg_offen = [e for e in beleg.offene()
                   if e.get("kennung") != kennung
                   and ((e.get("zusatz") or {}).get("inst") == inst
                        or e.get("paar") == inst)]
    if beleg_offen:
        return {"spur": spur, "kennung": kennung,
                "ergebnis": "abgelehnt: Beleg offen fuer %s" % inst}
    positionen = [p for p in z.get("positionen", []) if p.get("paar") == inst]
    if positionen:
        return {"spur": spur, "kennung": kennung,
                "ergebnis": "abgelehnt: Position offen fuer %s" % inst}
    # Die Boerse ist der dritte Zeuge. Fail-closed: kann die Hand sie nicht
    # fragen, kauft sie nicht - eine offene Kauf-Order, die niemand gesehen
    # hat, waere derselbe Doppelkauf, nur eine Stufe spaeter. Eine offene
    # VERKAUF-Order (der Schutz-Stop einer Position) blockiert nicht.
    try:
        offene_orders = handeln.kraken.offene_orders()
    except Exception as e:                                     # noqa: BLE001
        return {"spur": spur, "kennung": kennung,
                "ergebnis": "abgelehnt: offene Orders nicht abrufbar (%s)" % e}
    kaeufe_offen = [o for o in offene_orders.values()
                    if o.get("paar") == inst and o.get("seite") == "buy"]
    if kaeufe_offen:
        return {"spur": spur, "kennung": kennung,
                "ergebnis": "abgelehnt: offene Kauf-Order an der Boerse "
                           "fuer %s" % inst}

    # Einloesen NACH allen Gates: der Beleg ist einmalig. Bliebe er liegen,
    # koennte eine zweite Hand dieselbe Order ein zweites Mal ausfuehren.
    beleg.verbrauche(spur, kennung, ergebnis="beleg_hand")

    try:
        txid = handeln.kraken.markt_kauf(inst, menge, echt=True)
    except Exception as e:                                        # noqa: BLE001
        handeln.journal(_jetzt(), "live", "fehler", inst, "", "", "", "", "",
                        "beleg_hand: Kauf fehlgeschlagen (%s)" % e)
        return {"spur": spur, "kennung": kennung,
                "ergebnis": "Kauf fehlgeschlagen: %s" % e}
    if not txid:
        # AddOrder hat keine Kennung geliefert: es steht nichts an der Boerse.
        handeln.journal(_jetzt(), "live", "fehler", inst, "", "", "", "", "",
                        "beleg_hand: Kauf ohne Kennung")
        return {"spur": spur, "kennung": kennung, "ergebnis": "Kauf ohne Kennung"}

    # Ab hier EXISTIERT eine Order, das Geld ist gebunden. Die Fuellung wird
    # abgewartet - aber aus "noch keine Fuellung" folgt NIE "kein Kauf". Genau
    # diese Verwechslung hat am 28.09.2026 FILEUR viermal gekauft (~200 EUR fuer
    # EIN Signal, T-102): ohne Buchung signalisierte die Spur im naechsten
    # Zyklus erneut. Unbestaetigt heisst jetzt: bestellte Menge buchen und die
    # Fuellung offen lassen - kraken/abgleich.py zieht die Menge auf die Boerse
    # nach, sobald sie dort steht.
    gefuellt, bestaetigt = handeln.kraken.fuellung_abwarten(txid)
    if not bestaetigt:
        gefuellt = menge
        handeln.journal(_jetzt(), "live", "warnung", inst, "", "", "", "", "",
                        "beleg_hand: Fuellung unbestaetigt - %.8f bestellt, "
                        "Kennung %s" % (menge, txid))

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
        "fuellung_offen": not bestaetigt,
    })
    handeln.schreibe_zustand(z)
    handeln.journal(_jetzt(), "live", "kauf", inst, "%.8g" % (kurs or 0.0),
                    "%.2f" % (eur + kosten), "%.8f" % gefuellt,
                    "%.8g" % (float(stop) if stop else 0.0),
                    "%.8g" % (float(ziel) if ziel else 0.0),
                    "beleg %s ueber die Hand" % kennung)
    try:
        handeln._spiegeln(w, z)                      # Bedingung 4
    except Exception as e:                                        # noqa: BLE001
        print("  Spiegelung fehlgeschlagen: %s" % e, file=sys.stderr)
    return {"spur": spur, "kennung": kennung,
            "ergebnis": "ausgefuehrt" if bestaetigt else "ausgefuehrt (Fuellung offen)",
            "paar": inst, "menge": gefuellt, "txid": txid, "stop_txid": stop_txid,
            "stop_fehlt": stop_fehlt, "fuellung_offen": not bestaetigt}


def melde_verfallene() -> list[dict]:
    """Verfallene Belege EINMAL melden (Zeile + Journalgrund), dann merken.

    Sie sind kein Schaden - ein verfallener Beleg kauft nicht -, aber sie sind
    unsichtbar: `offene()` laesst sie weg, und niemand sonst sieht nach. Am
    01.10.2026 starben so acht von neun Belegen eines Zyklus an der Frist,
    ohne dass irgendwo stand, welche Order nicht ausgefuehrt wurde (T-283).
    `merke_verfallen` sorgt dafuer, dass dieselbe Feststellung genau EINMAL
    entsteht (der Cron laeuft alle 5 Minuten).
    """
    gemeldet = []
    for e in beleg.verfallene():
        spur = e.get("spur") or ""
        print("%-10s %s VERFALLEN: %s %s, Frist %s, nicht ausgefuehrt (%s)"
              % (spur, e.get("kennung"), e.get("seite"), e.get("paar"),
                 e.get("gueltig_bis"), e.get("grund") or "ohne Grund"))
        if spur == "kraken":
            try:
                handeln = _kraken_weg()
                handeln.journal(_jetzt(), "live", "beleg_verfallen",
                                e.get("paar") or "", "", "", "", "", "",
                                "beleg %s bis %s nicht ausgefuehrt | %s"
                                % (e.get("kennung"), e.get("gueltig_bis"),
                                   e.get("grund") or "ohne Grund"))
            except Exception as ex:                               # noqa: BLE001
                print("  Journalzeile fehlgeschlagen: %s" % ex, file=sys.stderr)
        beleg.merke_verfallen(spur, grund="Frist abgelaufen")
        gemeldet.append(e)
    return gemeldet


def lauf(anwenden: bool = False) -> list[dict]:
    berichte = []
    for eintrag in beleg.offene():
        bericht = fuehre_aus(eintrag, anwenden)
        berichte.append(bericht)
        print("%-10s %s %s" % (bericht["spur"], bericht["kennung"],
                               bericht["ergebnis"]))
    melde_verfallene()
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