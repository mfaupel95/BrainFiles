"""IV-Wand-Spur: der Strike mit dem groessten Open Interest als Magnet.

WAS DIE IV-WAND IST
-------------------
Im Optionsmarkt liegt bei bestimmten Strikes sehr viel offenes Interesse (Open
Interest). Dort sitzen die Absicherungen der Marktmacher, und der Kurs wird von
diesen Zonen angezogen oder abgestossen - die "Wand". Dazu gehoert die
implizite Volatilitaet (IV): Wo viel OI liegt UND die IV hoch ist, ist die
Erwartung des Marktes konzentriert.

Diese Spur rechnet die Wand selbst aus den oeffentlichen OKX-Daten:
Strikes mit Verfall in 7 bis 45 Tagen (die nahen Verfaelle, wo gehandelt wird),
Open Interest in USD je Strike summiert (Call + Put), das groesste davon ist die
Wand. Die IV dieses Strikes steht als Notiz im Zustand.

REGEL
-----
Der Kurs wandert zur Wand (Magnet):

  * Spot UNTER der Wand, Abstand <= 5 %  -> long,  Ziel ist die Wand
  * Spot UEBER der Wand, Abstand <= 5 %  -> short, Ziel ist die Wand
  * weiter weg oder genau darauf        -> kein Geschaeft

Der Stop ist ein fester Prozentsatz (Wachen), die Groesse risiko-normiert. Das
Ziel ist hier ein MARKTPUNKT, kein Vielfaches des Stops - dafuer gibt es im
gemeinsamen Buch (`Handel/spur_buch.py`) den Parameter `ziel_preis`.

WAS SIE NICHT IST
-----------------
Kein Live-Zweig (Papier wie alle Feed-Spuren), kein Optionshandel: gehandelt
wird der Spot-Papierpreis. Keine Prognose ueber den Verfall, nur eine Zone.

Aufruf:
  python handeln.py --vorschau | --papier | --wachen
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HANDEL, os.path.join(HANDEL, "scanner"), HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import spur_buch as buch  # noqa: E402

OPTIONEN = "https://www.okx.com/api/v5"
KOPF = {"User-Agent": "brainfiles-handelsspur/1.0 (privater Papierlauf)"}
ZEITGRENZE = 30

# Test-Seams: None -> echter OKX-Abruf.
options_quelle = None
spot_quelle = None


def hole_json(url, zeitgrenze=ZEITGRENZE):
    anfrage = urllib.request.Request(url, headers=KOPF)
    with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as antwort:
        daten = json.loads(antwort.read().decode("utf-8", "replace"))
    if daten.get("code") not in ("0", 0):
        raise RuntimeError("OKX: %s" % (daten.get("msg") or daten.get("code")))
    return daten.get("data") or []


def _zahl(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None


# --- Die Wand --------------------------------------------------------------

def strike_aus(inst_id):
    """'BTC-USD-260925-79000-C' -> (70000.0, '260925', 'C') oder None."""
    teile = (inst_id or "").split("-")
    if len(teile) < 5:
        return None
    try:
        strike = float(teile[-2])
    except ValueError:
        return None
    return strike, teile[-3], teile[-1]


def tage_bis(expiry, jetzt):
    """Verfall '260925' als Tage ab `jetzt` (None, wenn unlesbar)."""
    try:
        jahr = 2000 + int(expiry[0:2])
        monat = int(expiry[2:4])
        tag = int(expiry[4:6])
        ende = datetime(jahr, monat, tag, 8, 0, tzinfo=timezone.utc)
    except (ValueError, TypeError, IndexError):
        return None
    return (ende - jetzt).total_seconds() / 86400.0


def oi_je_instrument(offen):
    """{instId: Open Interest in USD} aus /public/open-interest."""
    aus = {}
    for z in offen:
        inst = z.get("instId")
        wert = _zahl(z.get("oiUsd"))
        if wert is None:
            # Manche Eintraege haben nur oiUsd als "" - oiCcy * Kurs waere
            # geraten, also gar nicht.
            wert = _zahl(z.get("oiUsd")) or 0.0
        if inst:
            aus[inst] = wert
    return aus


def iv_je_instrument(uebersicht):
    """{instId: IV in Prozent} aus /public/opt-summary (markVol)."""
    aus = {}
    for z in uebersicht:
        inst = z.get("instId")
        vol = _zahl(z.get("markVol"))
        if inst and vol is not None:
            aus[inst] = vol * 100.0
    return aus


def wand_bauen(offen, uebersicht, jetzt, min_tage=7.0, max_tage=45.0):
    """Die IV-Wand: (strike, oi_usd, iv_pct, faellig_in_tagen, strikes).

    Gezaehlt wird ueber Strikes: Call und Put desselben Strikes gehoeren
    zusammen - beide Seiten hedgen am selben Punkt.
    """
    oi = oi_je_instrument(offen)
    iv = iv_je_instrument(uebersicht)
    je_strike, je_iv = {}, {}
    for inst, wert in oi.items():
        zerlegt = strike_aus(inst)
        if not zerlegt:
            continue
        strike, expiry, _typ = zerlegt
        tage = tage_bis(expiry, jetzt)
        if tage is None or not (min_tage <= tage <= max_tage):
            continue
        je_strike[strike] = je_strike.get(strike, 0.0) + wert
        if inst in iv:
            eintrag = je_iv.setdefault(strike, [])
            eintrag.append(iv[inst])
    if not je_strike:
        return None
    strikes = sorted(je_strike.items(), key=lambda kv: kv[1], reverse=True)
    strike, oi_summe = strikes[0]
    werte = je_iv.get(strike) or []
    schnitt_iv = sum(werte) / len(werte) if werte else None
    tage = None
    for inst in oi:
        zerlegt = strike_aus(inst)
        if zerlegt and zerlegt[0] == strike:
            t = tage_bis(zerlegt[1], jetzt)
            # Nur Verfaelle IM FENSTER: der naechste Verfall desselben Strikes
            # kann schon vorbei sein (Strikes leben ueber viele Expiries), und
            # ein negatives Alter waere keine Auskunft.
            if t is not None and min_tage <= t <= max_tage and (tage is None or t < tage):
                tage = t
    return {"strike": strike, "oi_usd": oi_summe, "iv_pct": schnitt_iv,
            "faellig_in_tagen": tage, "strikes": len(je_strike)}


# --- Quelle und Regel ------------------------------------------------------

def quelle(w):
    """Open Interest + IV von OKX plus den Spot-Kurs. Ein Abruf je Endpunkt."""
    if options_quelle:
        roh = options_quelle(w)
    else:
        fehler0 = []
        try:
            offen = hole_json("%s/public/open-interest?%s" % (
                OPTIONEN, urllib.parse.urlencode({"instType": "OPTION",
                                                  "uly": w.get("uly", "BTC-USD")})))
            uebersicht = hole_json("%s/public/opt-summary?%s" % (
                OPTIONEN, urllib.parse.urlencode({"uly": w.get("uly", "BTC-USD")})))
        except Exception as e:                                  # noqa: BLE001
            return {}, {}, ["OKX-Optionen: %s" % str(e)[:120]]
        roh = {"offen": offen, "uebersicht": uebersicht}
    if spot_quelle:
        spot = spot_quelle(w)
    else:
        import okx                                             # noqa: PLC0415
        spot = okx.letzter_kurs(w.get("instrument", "BTC-USDT"))
    if not spot:
        return {}, {}, ["Spot-Kurs nicht abrufbar"]

    jetzt = datetime.now(timezone.utc)
    wand = wand_bauen(roh["offen"], roh["uebersicht"], jetzt,
                      min_tage=float(w.get("wand_min_tage", 7.0)),
                      max_tage=float(w.get("wand_max_tage", 45.0)))
    if not wand:
        return {}, {}, ["keine Wand im Verfallsfenster"]

    inst = w.get("instrument", "BTC-USDT")
    daten = {inst: {"spot": float(spot), "wand": wand}}
    return daten, {inst: float(spot)}, []


def signal(d, w):
    """Long unter der Wand, short darueber - nur innerhalb des Abstands."""
    wand = (d.get("wand") or {}).get("strike")
    spot = d.get("spot")
    if not wand or not spot:
        return None
    abstand = (float(wand) - float(spot)) / float(spot) * 100.0
    grenze = float(w.get("max_abstand_pct", 5.0))
    if 0 < abstand <= grenze:
        return "long"
    if -grenze <= abstand < 0:
        return "short"
    return None


def ziel(d, w):
    """Das Ziel ist die Wand selbst - ein Marktpunkt, kein Vielfaches."""
    return (d.get("wand") or {}).get("strike")


# --- Main -------------------------------------------------------------------

def daten_holen(w):
    return quelle(w)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau", dest="modus")
    ap.add_argument("--papier", action="store_const", const="papier", dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    ap.set_defaults(modus="papier")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.modus == "live":
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier). Gehandelt wird der Spot-Papierpreis, nicht die Option.")
        return 0
    return buch.zyklus(HIER, daten_holen, signal, a.modus, "handel/iv_wand",
                       ziel=ziel)


if __name__ == "__main__":
    raise SystemExit(main())
