"""Buch gegen BOERSE: hat jede Live-Position ihren Notausstieg noch?

Warum es das gibt (Befund 28.09.2026)
-------------------------------------
Auf dem OKX-Konto standen vier Live-Positionen (BTC, ETH, SOL, HYPE, rund
385 USD), deren Stops am 26.09.2026 zwischen 14:25:59 und 14:26:06 an der
Boerse storniert worden waren. Die Spur merkte es nicht: ``zustand.json``
trug weiter ``stop_ord_id`` und ``boersen_stop_fehlt: false``. Zusaetzlich
war ZEC-USDC am 24.09.2026 um 11:31 vom eigenen Stop verkauft worden
(0,04076 @ 1470,89) - das Buch fuehrte die Position danach weiter, weil nur
der EIGENE Kurs gegen den Stop geprueft wird und der Stop damals unter dem
Markt lag.

Zwei Fragen also, und beide kann nur die BOERSE beantworten:

  1. Ist der Bestand noch da? Wenn nein: Stop gefeuert oder Handverkauf ->
     Position mit dem ECHTEN Ausstiegspreis ausbuchen.
  2. Ist der Notausstieg noch wirksam? Wenn nein und Bestand da -> neu setzen,
     und zwar ueber den TATSCHLICH gehaltenen Bestand.

Ein Feld im Buch (``boersen_stop_fehlt``) wurde bisher nur beim KAUF gesetzt
und nie wieder geprueft - eine Behauptung, die altert.

Aufruf (aus ``Agenten/Handel/scanner``):

    python boersenstops.py               # Vorschau, schreibt und ordert nichts
    python boersenstops.py --anwenden    # fehlende Stops setzen, Weggelaufenes buchen

Im Betrieb ruft ``handeln.py`` ``pruefe(z, anwenden=True)`` am Anfang jedes
Live-Zyklus. Ist die Boerse nicht lesbar, bleibt alles unangetastet: ein
Netzfehler darf weder eine Position loeschen noch einen Stop doppelt setzen.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
ZUSTAND = os.path.join(HIER, "zustand.json")
MIN_ALTER_S = 300          # nicht in einen laufenden Zyklus schreiben
WIRKSAM = ("effective", "live")
# Ein Bestand unter dieser Quote der Buchmenge gilt als "weg". Grosszuegig,
# weil Staking/Umwandlungen und Ordergebuehren kleine Reste hinterlassen.
WEG_QUOTE = 0.02


def _heute():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _haltetage(p):
    try:
        d0 = datetime.strptime(p.get("eroeffnet") or _heute(), "%Y-%m-%d")
    except ValueError:
        return ""
    return (datetime.now(timezone.utc).date() - d0.date()).days


def _ansage(text):
    """Diagnosezeile - der Dauerlauf liest die Ausgabe der Spur."""
    print("  " + text)


def stop_wirksam(okx, p):
    """(wirksam, gefuellt) des gemerkten Boersen-Stops einer Position.

    Ohne Kennung: (False, False) - dann wird gesetzt statt geprueft.
    """
    sid = p.get("stop_ord_id")
    if not sid:
        return False, False
    try:
        d = okx.stop_details(sid) or {}
    except Exception as e:                                     # noqa: BLE001
        _ansage("Stop %s nicht lesbar: %s" % (sid, e))
        return None, None            # unbekannt - NICHT als "fehlt" deuten
    state = (d.get("state") or "").lower()
    gefuellt = float(d.get("accFillSz") or 0) > 0
    return state in WIRKSAM and not gefuellt, gefuellt


def setze_stop(okx, p, menge):
    """Notausstieg neu setzen. Rueckgabe: algoId oder None."""
    try:
        algo = okx.stop_setzen(p["inst"], menge, p["stop"])
    except Exception as e:                                     # noqa: BLE001
        _ansage("Stop fuer %s liess sich NICHT setzen: %s" % (p["inst"], e))
        return None
    p["stop_ord_id"] = algo
    p["boersen_stop_fehlt"] = False
    _ansage("Stop nachgesetzt: %s %.6f ueber %s (algoId %s)"
            % (p["inst"], p["stop"], menge, algo))
    return algo


def _buche_weg(z, p, okx, journal, grund_vermutung):
    """Position ist an der Boerse weg - mit dem ECHTEN Kurs ausbuchen.

    Ohne belegten Ausstiegskurs wird NICHT gebucht (ein geratener Kurs ist ein
    erfundenes Ergebnis). Rueckgabe: True, wenn gebucht wurde.
    """
    f = None
    try:
        f = okx.letzte_fuellung(p["inst"], "sell")
    except Exception as e:                                     # noqa: BLE001
        _ansage("Ausstiegspreis %s nicht lesbar: %s" % (p["inst"], e))
    if not f:
        _ansage("WEG, aber kein Ausstiegspreis belegbar: %s - Buch bleibt "
                "unveraendert (bitte von Hand pruefen)" % p["inst"])
        return False
    kurs = float(f.get("avgPx") or 0)
    menge = float(f.get("accFillSz") or 0)
    if not kurs or not menge:
        _ansage("WEG, Ausstiegsorder ohne Preis/Menge: %s - Buch bleibt "
                "unveraendert" % p["inst"])
        return False
    erloes = menge * kurs * (1 - 0.0005)
    einsatz = float(p.get("usd") or 0.0)
    gv = erloes - einsatz
    _ansage("AUSSTIEG (%s): %s %.6f Stueck @ %.6f  Erloes %.2f  G/V %+.2f USD"
            % (grund_vermutung, p["inst"], menge, kurs, erloes, gv))
    if journal:
        journal(_jetzt(), "live", "verkauf", p["inst"], "%.6f" % kurs,
                "%.2f" % erloes, "", "", grund_vermutung,
                "%.4f" % float(p.get("mfe_pct") or 0.0),
                "%.4f" % float(p.get("mae_pct") or 0.0), _haltetage(p))
    return True


def pruefe(z, okx, anwenden=False, journal=None):
    """Eine Runde Buch <-> Boerse. Rueckgabe: Zahlen fuer den Bericht.

    ``anwenden=False`` (Vorschau) liest nur und sagt, was es taete.
    """
    bilanz = {"geprueft": 0, "ok": 0, "nachgesetzt": 0, "fehlt_weiter": 0,
              "weg": 0, "ausgebucht": 0, "waisen": 0, "unklar": 0}
    behalten = []
    for p in z.get("positionen") or []:
        if not p.get("kauf_ord_id"):
            behalten.append(p)      # Papier-Altlast: nicht Sache dieses Wegs
            continue
        bilanz["geprueft"] += 1
        try:
            eq, frei = okx.bestand(p["inst"])
        except Exception as e:                                 # noqa: BLE001
            _ansage("Bestand %s nicht lesbar: %s - unangetastet" % (p["inst"], e))
            bilanz["unklar"] += 1
            behalten.append(p)
            continue

        buch_menge = 0.0
        try:
            buch_menge = float(p.get("usd") or 0) / float(p.get("einstieg") or 0)
        except ZeroDivisionError:
            pass
        schwelle = max(0.0, buch_menge * WEG_QUOTE)
        wirksam, gefuellt = stop_wirksam(okx, p)

        if eq <= schwelle:
            grund = "boersen_stop" if gefuellt else "handverkauf_boerse"
            bilanz["weg"] += 1
            if not anwenden:
                _ansage("POSITION WEG an der Boerse: %s (Buch %.8f) - wuerde "
                        "als %s ausgebucht" % (p["inst"], buch_menge, grund))
                behalten.append(p)
                continue
            if p.get("stop_ord_id") and wirksam:
                try:
                    okx.stop_stornieren(p["stop_ord_id"], p["inst"])
                except Exception as e:                         # noqa: BLE001
                    _ansage("Waisenstop %s nicht stornierbar: %s"
                            % (p["stop_ord_id"], e))
            if _buche_weg(z, p, okx, journal, grund):
                bilanz["ausgebucht"] += 1
                continue
            bilanz["unklar"] += 1
            behalten.append(p)
            continue

        if wirksam is None:
            bilanz["unklar"] += 1
            behalten.append(p)      # Zustand unbekannt: lieber nichts tun
            continue

        if wirksam:
            bilanz["ok"] += 1
            if p.get("boersen_stop_fehlt"):
                p["boersen_stop_fehlt"] = False
            behalten.append(p)
            continue

        # Bestand da, Stop nicht (mehr) wirksam -> neu setzen.
        menge = okx.menge_gerundet(p["inst"], min(eq, buch_menge) if buch_menge
                                   else eq)
        if not menge:
            _ansage("%s: Bestand %.8f kleiner als die kleinste Ordergroesse - "
                    "kein Stop moeglich" % (p["inst"], eq))
            p["boersen_stop_fehlt"] = True
            bilanz["fehlt_weiter"] += 1
            behalten.append(p)
            continue
        if not anwenden:
            _ansage("STOP FEHLT: %s - wuerde %.8f Stueck bei %.6f sichern"
                    % (p["inst"], menge, p["stop"]))
            p["boersen_stop_fehlt"] = True
            bilanz["fehlt_weiter"] += 1
            behalten.append(p)
            continue
        if setze_stop(okx, p, menge):
            p["boersen_stop_fehlt"] = False
            bilanz["nachgesetzt"] += 1
        else:
            p["boersen_stop_fehlt"] = True
            bilanz["fehlt_weiter"] += 1
        behalten.append(p)

    if anwenden:
        z["positionen"] = behalten

    # Waisenstops: gemerkt, aber zu keiner Position gehoerig.
    gefuehrt = {p.get("stop_ord_id") for p in z.get("positionen") or []}
    rest = []
    for e in z.get("offene_stops") or []:
        sid = e.get("stop_ord_id")
        if not sid or sid in gefuehrt:
            rest.append(e)
            continue
        wirksam, _ = stop_wirksam(okx, {"stop_ord_id": sid})
        if not wirksam:
            continue                      # an der Boerse erledigt - Eintrag faellt
        bilanz["waisen"] += 1
        if anwenden:
            try:
                okx.stop_stornieren(sid, e.get("inst"))
                _ansage("WAISENSTOP %s (%s) storniert" % (sid, e.get("inst")))
                continue
            except Exception as ex:                            # noqa: BLE001
                _ansage("WAISENSTOP %s nicht stornierbar: %s" % (sid, ex))
        else:
            _ansage("WAISENSTOP %s (%s) - wuerde storniert"
                    % (sid, e.get("inst")))
        rest.append(e)
    if anwenden and len(rest) != len(z.get("offene_stops") or []):
        z["offene_stops"] = rest
    return bilanz


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _lade(pfad):
    with open(pfad, "r", encoding="utf-8") as f:
        return json.load(f)


def _speichere(pfad, z):
    with open(pfad, "w", encoding="utf-8", newline="\n") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anwenden", action="store_true",
                    help="fehlende Stops setzen und Weggelaufenes buchen")
    ap.add_argument("--pfad", default=ZUSTAND, help="abweichende zustand.json")
    a = ap.parse_args(argv)

    if not os.path.exists(a.pfad):
        print("keine %s - nichts zu tun" % a.pfad)
        return 0
    if a.anwenden:
        alter = time.time() - os.path.getmtime(a.pfad)
        if alter < MIN_ALTER_S:
            print("zustand.json ist %d s alt (juenger als %d s) - ein Zyklus "
                  "laeuft vermutlich gerade. Spaeter erneut versuchen."
                  % (alter, MIN_ALTER_S))
            return 2

    import okx                                     # noqa: PLC0415
    import handeln                                 # noqa: PLC0415

    z = _lade(a.pfad)
    print("Buch gegen Boerse: %d Positionen, Modus %s"
          % (len(z.get("positionen") or []),
             "ANWENDEN" if a.anwenden else "Vorschau (ordert nichts)"))
    bilanz = pruefe(z, okx, anwenden=a.anwenden, journal=handeln.journal)
    print("geprueft %(geprueft)d  ok %(ok)d  nachgesetzt %(nachgesetzt)d  "
          "stop fehlt weiter %(fehlt_weiter)d  weg %(weg)d  ausgebucht "
          "%(ausgebucht)d  waisen %(waisen)d  unklar %(unklar)d" % bilanz)
    if a.anwenden:
        _speichere(a.pfad, z)
        print("zustand.json geschrieben")
    else:
        print("nichts geschrieben (Vorschau) - mit --anwenden ausfuehren")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())