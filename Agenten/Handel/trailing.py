"""Stop-Loss an der BOERSE nachziehen, ohne die Position zu schliessen.

AUFTRAG (Max, 05.10.2026): "intelligent an den gehebelten positionen stop loss
nachziehen und anpassen bei gelegenheit. bei allen spuren mit 1-3 takeprofit
ausstiegen arbeiten".

DAS PROBLEM, das dieser Weg loest
--------------------------------
Eine Position mit festem Stop gibt bei einem 1,5R- oder 2R-Ziel Ertrag auf
dem Papier auf, den es real nicht gibt: gewinnt der Markt 2R, ist der alte
Stop 2R tiefer noch immer offen und gibt 2R zurueck - aber auch jeder
Zwischenstand, also auch 0,4R, wird pauschal riskiert. Der Stop wird nicht
nachgezogen, die Position bleibt ein Vollrisiko bis zum Ziel.

DER WEG, den OKX dafuer anbietet (gemessen am 05.10.2026 am echten Account,
sCode=0, ohne den Stop zu verschieben):
    POST /api/v5/trade/amend-algos
        {algoId, instId, newSlTriggerPx, newSlOrdPx: "-1"}
Das ist eine AENDERUNG am bestehenden Algo-Auftrag: die Position laeuft
weiter, nur der Ausstiegspreis wandert. Das ist etwas voellig anderes als
stornieren und neu setzen - dort gaebe es zwischen beiden Aktionen ein
Fenster OHNE Schutz, genau die Lektion aus ZEC (26.09.2026).

Warum das nicht schon xperp/okxf.py erledigt: dort gab es
`hebel_setzen`, `schutz_stop_setzen` und `algo_stornieren` - aber kein
`amend`. Jede Spur, die nachziehen wollte, brauchte eine eigene
Implementierung, und drei Spuren haben genau das (moondev_signalwelle,
nautilus_kraken, omnitrade_futures) mit drei Kopien derselben Logik.
`okxf.stop_nachziehen()` ist seit dem 05.10.2026 die EINE Stelle; diese
Datei ist die EINE Rechnung darueber.

DAS BANDBREITEN-MODELL, nicht das 1-3R-Fenster
----------------------------------------------
Die Aufgabe nennt "1-3 Takeprofit". Als Filter auf geschlossene Runden waere
das die falsche Stelle: R ist eine AUSSTIEGS-Geometrie, kein Zustand einer
offenen Position. Eine offene Position mit Ziel 1,5R und Stop 7 % braucht
denselben Trailing-Stop wie eine mit Ziel 2,0R und Stop 5 %.

Deshalb haengt die Ausloesung an zwei Groessen, die man unabhaengig davon
abfragen kann:
  * `trigger_r`   - wie weit der Kurs GEGEN den Stop gelaufen ist, als
                    Anteil des Stop-Abstands. Erst wenn die Position so weit
                    im Plus ist, dass ihr Stop von einem Verlust zum Gewinn
                    geworden ist, wird ueberhaupt nachgezogen.
  * `halten_pct`  - der Abstand, den der Stop hinter dem erreichten
                    Hochstand bleibt. Das ist die einzige Zahl, die man
                    optimieren kann; `trigger_r` legt nur fest, AB WANN.

Voreinstellungen sind Hauswerte, keine Messung - sie stehen als `vorgabe_*`
im Modul und werden von `auswerten()` nicht angefasst. Wer sie aendert,
aendert eine Wache.

GEFAHREN, die hier behandelt sind
  * Ein Stop, der ZU NAH am Kurs liegt, wird vom Marktrauschen erreicht
    (der haeufigste Fall: Trailing 0,5 % auf einem 2 %-Stundeninstrument).
    `stop_abstand_floor_pct` haelt einen Mindestabstand.
  * Ein Stop, der die LIQUIDATIONSMARKE kreuzt oder dahinter liegt, waere
    kein Schutz, sondern eine Illusion. `stop_vor_liq()` verweigert.
  * Ein Stop kann nur in die RICHTUNG, in der er schuetzt: nach oben bei
    long, nach unten bei short. Nie zurueck - sonst haette eine Position,
    die kurz unter ihrem Stop war, plötzlich einen WENIGER sicheren Stop.
  * Scheitert das Nachziehen, bleibt der ALTE Stop stehen. Ein stiller
    Verlust des Schutzes waere schlimmer als kein Trailing.

WER DAS NICHT BENUTZT
--------------------
Eine Position ohne `stop_id` (kein Boersen-Stop hinterlegt) kann nicht
nachgezogen werden - fuer sie ist zuerst der fehlende Stop zu setzen
(`mosaic/stops_nachziehen.py`, `xperp/stopdeckung.py`). Diese Datei
erfindet keinen Stop.
"""

import math
import sys

# VORGABEN - Hauswerte, keine Messung. Jede Spur kann sie ueberschreiben.
VORGABE_TRIGGER_R = 1.0        # so weit gegen den Stop, dann erst nachziehen
VORGABE_HALTEN_PCT = 1.50      # Stop so weit hinter dem Hochstand (Max 09.10.2026; vorher 0,40)
VORGABE_ABSTAND_FLOOR_PCT = 0.25   # Mindestabstand Stop<->Kurs (Marktrauschen)
VORGABE_MIN_HUB_R = 0.25       # Mindestgewinn, um eine Verlegung zu rechtfertigen
VORGABE_MIN_HALTUNG_S = 120    # nicht haufiger als alle zwei Minuten
MAX_HALTEN_PCT = 5.0           # Stop nie weiter als 5 % hinter dem Hochstand


class StopPfadFehler(RuntimeError):
    """Der Pfad des Boersen-Wegs kann den Stop nicht aendern."""


def _round_tick(preis, tick, richtung="auf"):
    if not tick or tick <= 0:
        return float(preis)
    stellen = max(0, len(("%.10f" % tick).rstrip("0").split(".")[1]))
    faktor = 10 ** stellen
    x = round(float(preis) * faktor, 6)
    ganz = math.ceil(x) if richtung == "auf" else math.floor(x)
    return round(ganz / faktor, stellen)


def _tick(inst, okxf):
    for leser in ("tick_fuer", "tick_sz", "instrument", "instrument_info"):
        fn = getattr(okxf, leser, None)
        if fn is None:
            continue
        try:
            info = fn(inst)
        except Exception:                                          # noqa: BLE001
            continue
        if isinstance(info, dict):
            if info.get("tickSz"):
                return float(info["tickSz"])
        elif info:
            try:
                return float(info)
            except (TypeError, ValueError):
                continue
    return 0.0


def neu(ziel_pct=None):
    """Voreinstellungen als Wachen-Feldersatz."""
    return {
        "trailing_stop_prozent": VORGABE_HALTEN_PCT,
        "trailing_trigger_r": VORGABE_TRIGGER_R,
        "trailing_abstand_floor_pct": VORGABE_ABSTAND_FLOOR_PCT,
        "trailing_min_hub_r": VORGABE_MIN_HUB_R,
        "trailing_max_halten_pct": MAX_HALTEN_PCT,
    }


def verdrahtung(w):
    """Die Felder, die eine Spur braucht, mit den Werten aus ihrer Wache."""
    return {
        "halten_pct": float(w.get("trailing_stop_prozent")
                            or VORGABE_HALTEN_PCT),
        "trigger_r": float(w.get("trailing_trigger_r")
                           or VORGABE_TRIGGER_R),
        "floor_pct": float(w.get("trailing_abstand_floor_pct")
                           or VORGABE_ABSTAND_FLOOR_PCT),
        "min_hub_r": float(w.get("trailing_min_hub_r")
                           or VORGABE_MIN_HUB_R),
        "max_halten_pct": float(w.get("trailing_max_halten_pct")
                                or MAX_HALTEN_PCT),
    }


# --- Die Rechnung -----------------------------------------------------------

def kandidat(p, kurs, w, liq=None, jetzt=None):
    """(neu, grund) - wohin der Stop wandern wuerde. rein, kein Netzzugriff.

    `p` braucht einstieg, stop, seite und optional stop_id. Der alte Stop
    bleibt der Massstab: nur wenn der neue SICHTBAR weiter weg vom Kurs ist
    als der alte, wird er vorgeschlagen. Ein Stop, der nur um einen Tick
    wandert, kostet eine Order und bringt nichts - das ist der Grund fuer
    `min_hub_r`.
    """
    v = verdrahtung(w)
    einstieg = float(p.get("einstieg") or 0.0)
    alt = float(p.get("stop") or 0.0)
    seite = str(p.get("seite") or "long").lower()
    if einstieg <= 0 or alt <= 0:
        return None, "Einstieg oder Stop fehlt"
    if abs(einstieg - alt) < 1e-12:
        return None, "Stop liegt auf dem Einstieg"
    if not p.get("stop_id") and not p.get("stop_txid"):
        return None, ("kein Boersen-Stop hinterlegt - erst den Stop setzen "
                      "(stopdeckung.py / stops_nachziehen.py)")

    abstand = abs(einstieg - alt)
    vz = 1.0 if seite == "long" else -1.0

    # 1) Trigger: die Position muss so weit im Plus sein, dass ihr Stop vom
    #    Verlust zum moeglichen Gewinn geworden ist. Gemessen vom Einstieg.
    plus = (kurs - einstieg) * vz
    plus_r = plus / abstand
    if plus_r < v["trigger_r"]:
        return None, ("noch nicht im Trigger (%.2fR erreicht, noetig %.2fR)"
                      % (plus_r, v["trigger_r"]))

    # 2) Hochstand fuehren (der Stop folgt dem HOCH, nicht dem aktuellen
    #    Kurs - sonst wuerde ein Ruecksetzer den Stop wieder zurueckziehen).
    hoch = float(p.get("hoechstkurs") or kurs)
    hoch = max(hoch, kurs) if vz > 0 else min(hoch, kurs)
    hoch_r = ((hoch - einstieg) * vz) / abstand

    # 3) Wohin? Hinter den Hochstand, um `halten_pct`.
    ziel = hoch - vz * abs(hoch) * v["halten_pct"] / 100.0
    # 4) Nie weiter als max_halten_pct hinter den Hochstand. Der Stop liegt
    #    also HOECHSTENS so weit weg: long -> nicht unter `grenze` (max),
    #    short -> nicht ueber `grenze` (min).
    #    BIS 09.10.2026 STAND HIER min/max VERTAUSCHT: der Stop nahm den
    #    TIEFEREN Wert (long), also immer `grenze` - ein eingestelltes
    #    halten_pct unter max_halten_pct (0,4 % in xperp) war wirkungslos, der
    #    Stop lag real 5 % hinter dem Hochstand (Hoch 112 -> Stop 106,4 statt
    #    111,55). Gefunden beim Backtest (trailing_backtest.py).
    grenze = hoch - vz * abs(hoch) * v["max_halten_pct"] / 100.0
    if vz > 0:
        ziel = max(ziel, grenze)
    else:
        ziel = min(ziel, grenze)
    # 5) Mindestabstand zum Kurs (Marktrauschen).
    floor = abs(kurs) * v["floor_pct"] / 100.0
    if vz > 0:
        ziel = min(ziel, kurs - floor)
    else:
        ziel = max(ziel, kurs + floor)

    # 6) Nur in die schuetzende Richtung. Ein Stop, der naeher am Einstieg
    #    laege als der alte, waere eine VERLOCKUNG, kein Schutz.
    verbessert = (ziel > alt + 1e-12) if vz > 0 else (ziel < alt - 1e-12)
    if not verbessert:
        return None, "kein Abstand zum alten Stop (%.6f)" % alt
    hub_r = abs(ziel - alt) / abstand
    if hub_r < v["min_hub_r"]:
        return None, ("Hub zu klein (%.2fR, noetig %.2fR)"
                      % (hub_r, v["min_hub_r"]))

    # 7) Der Stop muss immer noch zwischen Liquidationsmarke und Kurs liegen.
    if liq is not None:
        if vz > 0 and ziel <= liq:
            return None, ("Ziel-Stop %.6f liegt an/unter der "
                          "Liquidationsmarke %.6f" % (ziel, liq))
        if vz < 0 and ziel >= liq:
            return None, ("Ziel-Stop %.6f liegt an/ueber der "
                          "Liquidationsmarke %.6f" % (ziel, liq))

    # IMMER (kandidat, grund) - auch im Erfolgsfall. Eine Funktion, die mal
    # ein Tupel und mal ein Dict zurueckgibt, zwingt jeden Aufrufer zu
    # `if isinstance(...)`; genau das hat die erste Testfassung gemacht und
    # sieben echte Fehler als Testfehler getarnt.
    return ({"stop": ziel, "hoechstkurs": hoch, "plus_r": plus_r,
             "hoch_r": hoch_r, "hub_r": hub_r,
             "abstand_kurs": abs(kurs - ziel)}, None)


def erst_hoch(p, kurs):
    """Den Hochstand einer Position pflegen. Rein, kein Netz.

    Schreibt das Feld IMMER - auch wenn sich der Wert nicht aendert. Ein
    Aufrufer, der den Hochstand nur als Fuehlgroesse liest, wuerde sonst
    bei der ersten Position ohne das Feld eine KeyError bekommen (im
    Verdrahtungstest vom 05.10.2026 so aufgefallen).
    """
    vz = 1.0 if str(p.get("seite") or "long").lower() == "long" else -1.0
    alt = p.get("hoechstkurs")
    if alt in (None, ""):
        p["hoechstkurs"] = float(kurs)
        return True
    alt = float(alt)
    hoch = max(alt, float(kurs)) if vz > 0 else min(alt, float(kurs))
    if hoch != alt:
        p["hoechstkurs"] = hoch
        return True
    return False


# --- Der Weg zur Boerse -----------------------------------------------------

def nachziehen(p, kurs, weg, w, liq=None, jetzt=None, tick=None, trocken=False,
              deckung_pruefen=None):
    """Den Stop an der BOERSE aendern. Gibt (neu, grund) zurueck.

    `weg` ist das Boersen-Modul der Spur. Es braucht ZWEI Faehigkeiten, die
    nicht jeder Weg hat: `stop_nachziehen` (aendern) und eine Liquidations-
    marke, falls der Weg gehebelt handelt. Fehlt `stop_nachziehen`, sagt
    dieser Weg das laut, statt einen Stop zu stornieren und neu zu setzen -
    das Fenster OHNE Schutz dazwischen ist der Grund.

    `deckung_pruefen` (optional) ist eine Funktion (p) -> dict mit
    gedeckt/soll/fehlt. Sie wird als ERSTE Bedingung abgefragt (Referenz
    trailing-stop-gehebelt.md Abschnitt 5.1: 'erst zusammenfuehren, dann
    trailingen'). Eine Position, deren Schutz-Menge an der Boerse die
    Buchmenge nicht deckt, ist nicht trailingbar: der engste Stop feuert
    zuerst, die uebrigen bleiben als Waisen zurueck. Bei Unterdeckung bricht
    dieser Weg ab, statt einen aufgeteilten Stop weiter zu verschieben.
    """
    if deckung_pruefen is not None:
        try:
            d = deckung_pruefen(p)
        except Exception as e:                                   # noqa: BLE001
            return None, ("Deckungspruefung fehlgeschlagen (%s) - der alte "
                          "Stop %.6f bleibt stehen" % (e, float(p.get("stop") or 0)))
        fehlt = float((d or {}).get("fehlt") or 0.0)
        if fehlt > 1e-6:
            return None, ("Position nicht voll gedeckt (geschuetzt %.2f von "
                          "%.2f, fehlt %.2f) - erst mit stopdeckung.py "
                          "zusammenfuehren, dann trailingen"
                          % (float(d.get("gedeckt") or 0.0),
                             float(d.get("soll") or 0.0), fehlt))
    k, grund = kandidat(p, kurs, w, liq=liq, jetzt=jetzt)
    if k is None:
        return None, grund
    gr = getattr(weg, "stop_nachziehen", None)
    if gr is None:
        return None, ("dieser Weg kann keinen Stop aendern "
                      "(kein stop_nachziehen) - Storno und Neuaufbau liesse "
                      "ein Fenster OHNE Schutz")
    inst = p.get("venue_inst") or p.get("inst")
    kennung_arg = p.get("stop_id") or p.get("stop_txid") or p.get("stop_algo_id")
    # DIE MENGE HEISST JE SPUR ANDERS. xperp fuehrt Kontrakte unter
    # `kontrakte`, die Buch-Spuren unter `menge`, Kraken unter `menge`.
    # Nur `menge` zu lesen hiesse: bei xperp griffe der Trailing nie, und
    # es faelle nicht auf - der Weg sagt "keine Menge in der Position" und
    # die Spur laeuft weiter. Gefunden am 05.10.2026 im Verdrahtungstest.
    menge = 0.0
    for feld in ("menge", "kontrakte", "groesse", "size"):
        roh = p.get(feld)
        try:
            menge = float(roh or 0.0)
        except (TypeError, ValueError):
            menge = 0.0
        if menge > 0:
            break
    if menge <= 0:
        return None, ("keine Menge in der Position (Felder: %s)"
                      % ", ".join(f for f in ("menge", "kontrakte", "groesse")
                                  if p.get(f)) or "keine")
    ziel = _round_tick(k["stop"], tick, "auf")
    if ziel <= 0:
        return None, "Tickgroesse nicht lesbar"
    if trocken:
        return k, ("TROCKENLAUF: Stop %.6f -> %.6f (Hoch %.6f, %.2fR, "
                   "Hub %.2fR)" % (float(p.get("stop") or 0), ziel,
                                   k["hoechstkurs"], k["hoch_r"],
                                   k["hub_r"]))
    # DIE MENGE GEHOERT NICHT IN DEN AUFTRAG. Sie steckt schon im
    # Algo-Auftrag an der Boerse - amend-algos aendert nur den
    # Ausloesepreis. Die Wege im Haus nehmen deshalb drei Parameter:
    #   okxf.stop_nachziehen(algo_id, inst, preis)
    #   moondev_signalwelle/weg.py: stop_nachziehen(order_id, inst, preis)
    # Ein Weg, der eine MENGE zusaetzlich will (die Kraken-Futures-
    # Variante), gehoert hier nicht hin: dort traegt der Auftrag die Menge
    # ebenfalls.
    try:
        kennung = gr(kennung_arg, inst, ziel)
    except Exception as e:                                         # noqa: BLE001
        return None, ("Nachziehen fehlgeschlagen (%s) - der alte Stop %.6f "
                      "bleibt stehen" % (e, float(p.get("stop") or 0)))
    if not kennung:
        return None, ("Weg lieferte keine Kennung - der alte Stop %.6f bleibt"
                      % float(p.get("stop") or 0))
    return {"stop": ziel, "kennung": str(kennung),
            "hoechstkurs": k["hoechstkurs"], "hoch_r": k["hoch_r"],
            "hub_r": k["hub_r"], "plus_r": k["plus_r"]}, "Stop nachgezogen"


def meldezeile(p, k, spur=""):
    """Eine Zeile fuer das Journal. Dasselbe Format wie die uebrigen
    Trailing-Meldungen im Haus, damit die Auswertung sie liest."""
    return ("trailing %s%s Stop %.6f -> %.6f (Hoch %.6f, %.2fR)"
            % (p.get("inst") or "?", (" " + spur) if spur else "",
               float(p.get("stop") or 0), float(k["stop"]),
               float(k["hoechstkurs"]), float(k["hoch_r"])))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("trailing.py - reines Rechenmodul. Kein Netzzugriff, keine Order.")
    w = neu()
    print("Vorgaben:", {k: v for k, v in w.items()})
    p = {"inst": "BTC-USDC", "seite": "long", "einstieg": 100.0,
         "stop": 95.0, "stop_id": "x", "menge": 1.0}
    # Die Demo zeigt eine GANZE KURVE mit dem Hochstand: erst 1R erreicht,
    # dann wandert der Stop mit, und ein Ruecksetzer holt ihn nicht zurueck.
    # Genau das ist der Unterschied zu einem Stop, der nur beim Ziel steht.
    hoch = 0.0
    for kurs in (95.5, 99.0, 102.0, 104.0, 106.0, 105.0, 103.0, 110.0):
        erst_hoch(p, kurs)
        p["stop"] = min(float(p["stop"]), float(p["hoechstkurs"]) * 0.96)
        k, g = kandidat(p, kurs, w)
        hoch = max(hoch, kurs)
        print("  Kurs %7.2f  Stop alt %7.4f  -> %s"
              % (kurs, float(p["stop"]),
                 ("Stop -> %.4f (Hoch %.2f, %.2fR)" % (k["stop"],
                                                        k["hoechstkurs"],
                                                        k["hoch_r"]))
                 if k else g))