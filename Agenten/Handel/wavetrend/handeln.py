"""WaveTrend-Spur: Mean-Reversion im ueberzogenen Bereich.

Signal: wavetrend(k) aus ti_indikatoren.py -> (wt1, wt2).
LONG wenn wt1[i-1] <= wt2[i-1] und wt1[i] > wt2[i] (Kreuzung von unten)
      UND wt1[i] < -40 (ueberverkauft).
SHORT spiegelbildlich (Kreuzung von oben UND wt1[i] > 40).

Zeitrahmen: 1H. Instrumente: BTC-USDT, ETH-USDT, SOL-USDT.
Papier-Handel: handel_erlaubt=false. Keine Orders.

Aufruf:
  python handeln.py --vorschau   waere dran, ohne schreiben
  python handeln.py --papier     Papierlauf mit Journal
  python handeln.py --wachen     Grenzen als Momentaufnahme
  python handeln.py --live       verweigert, nennt den Grund
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
# Reihenfolge zaehlt: sys.path.insert(0, ...) dreht die Liste um, deshalb
# rueckwaerts einfuegen. HIER muss ganz vorne stehen, sonst gewinnt
# scanner/handeln.py gegen das handeln.py dieser Spur.
for p in (os.path.join(HANDEL, os.pardir, "Bus"),
          os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import wachen_pruefung as wp  # noqa: E402
import ereignis  # noqa: E402
# pos_kennung liegt im Handel-Ordner. Der eigene Spurenordner ist beim
# Start sys.path[0], darum wird der Ordner ANGEHAENGT (nicht vorne
# eingefuegt - ein Eintrag vorne koennte ein gleichnamiges Spurenmodul
# verdecken, siehe Handel/grid.py neben gitter/grid.py).
_handel_ordner = os.path.dirname(          # Handel/, nicht der Spurenordner
    os.path.dirname(os.path.abspath(__file__)))
if _handel_ordner not in sys.path:
    sys.path.append(_handel_ordner)
import pos_kennung  # noqa: E402  # die Kennung einer Position (T-095)
import kill_gemeinsam as kg  # noqa: E402  # Kill-Frist/Reset/Opt-out

# ratschen.py ueber den PFAD laden, nicht ueber sys.path: die Datei liegt
# eine Ebene hoeher und heisst wie kein Paket. Ein Import ueber sys.path
# haenge davon ab, wer vorher was eingefuegt hat.
from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402

_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "ratschen.py")
_s = spec_from_file_location("ratschen", _p)
ratschen = module_from_spec(_s)
_s.loader.exec_module(ratschen)

# Risikostufe (HANDEL_RISIKO): Faktor auf die Betraege, Suffix auf Zustand
# und Journal. OHNE die Variable aendert sich nichts (Faktor 1.0, kein
# Suffix) - das ist die Bedingung, unter der diese Umstellung in laufenden
# Handelscode darf. Ueber den PFAD geladen wie ratschen.py: die Spur hat ihren
# eigenen Ordner als sys.path[0], ein 'import risikostufe' haenge an der
# Reihenfolge der Eintraege.
from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec
_rs_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "risikostufe.py")
_rs_spec_obj = _rs_spec("risikostufe", _rs_datei)
risikostufe = _rs_mod(_rs_spec_obj)
_rs_spec_obj.loader.exec_module(risikostufe)

WACHEN = os.path.join(HIER, "wachen.json")
ZUSTAND = risikostufe.datei(os.path.join(HIER, "zustand.json"))
JOURNAL = risikostufe.datei(os.path.join(HIER, "handelsjournal.csv"))

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           # MFE/MAE seit 03.10.2026 - Grundlage jedes
           # datengetriebenen Stop-Vorschlags (T-119).
           "mfe_pct", "mae_pct", "haltetage",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund",
           "pos_id"]

SCHREIBEN = True

# --- Test-Seams -----------------------------------------------------------
kerzen_quelle = None
zeit_quelle = None


# --- Zeit ------------------------------------------------------------------

def _jetzt():
    if zeit_quelle:
        return zeit_quelle()
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Dateien ---------------------------------------------------------------

def lade_wachen():
    with open(WACHEN, encoding="utf-8") as f:
        return risikostufe.skaliere(json.load(f))


# Zustand atomar schreiben und laut lesen (atomar.py, 30.09.2026). Ueber den
# PFAD geladen wie risikostufe.py: die Spur hat ihren eigenen Ordner als
# sys.path[0]. Defekte Datei -> Sicherung .bak, sonst laute Ausnahme statt
# leerem Bestand.
from importlib.util import module_from_spec as _at_mod, \
    spec_from_file_location as _at_spec
_at_obj = _at_spec("atomar", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "atomar.py"))
atomar = _at_mod(_at_obj)
_at_obj.loader.exec_module(atomar)


def lade_zustand():
    return atomar.lade_json(ZUSTAND, lambda: {"positionen": [], "modus": "papier", "letzter_lauf": None,
                "verluste_usd": 0.0})


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    atomar.schreibe_json(ZUSTAND, z)


def journal(**felder):
    if not SCHREIBEN:
        return
    neu = not os.path.exists(JOURNAL)
    # Der Kopf der DATEI entscheidet, was geschrieben wird (T-095): ein
    # Altjournal ohne `pos_id` behaelt seine Spalten, die Kennung wird dann
    # NICHT geschrieben - sichtbar als Warnung, statt alle Spalten zu
    # verschieben (siehe pos_kennung.spalten).
    spalten = SPALTEN if neu else pos_kennung.spalten(JOURNAL, SPALTEN)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
        if neu:
            w.writeheader()
        w.writerow(felder)


def spiegeln(z, w):
    """Bedingung 4: Journal und Zustand ausser Haus.

    Erst schreiben, dann kopieren. Der Vermerk ist juenger als die Kopie:
    wechselt er, wird der Zustand einmal nachgezogen, damit auf Q: derselbe
    Stand liegt. Ohne den Nachzug meldet `spiegelstand.py` in JEDEM Zyklus eine
    Abweichung, in dem sich der Spiegelstand aendert (Muster: swap/handeln.py).
    """
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        wp.spiegele_journal([ZUSTAND], ziel)


# --- Kerzen ----------------------------------------------------------------

def lade_kerzen(inst, intervall, anzahl):
    if kerzen_quelle:
        k = kerzen_quelle(inst, intervall, anzahl)
    else:
        try:
            import okx
            k = okx.kerzen(inst, intervall, anzahl)
        except Exception as e:
            print("Netzfehler: Kerzen fuer %s nicht abrufbar (%s)" % (inst, e),
                  file=sys.stderr)
            return []
    return [r if len(r) == 6 else r + [0.0] for r in k]


# --- Signallogik -----------------------------------------------------------

def atr_abs(k, idx, n=14):
    if idx < n:
        return None
    summ = 0.0
    for j in range(idx - n + 1, idx + 1):
        summ += k[j][2] - k[j][3]
    return summ / n


# Indikatorschwellen (T-097, 05.10.2026). Bis hierher standen sie fest im
# Vergleich des WaveTrend-Oszillators (-40 / +40); der Optimierer konnte sie
# deshalb nicht anfassen. Die Zahl im Default ist der alte Wert - ein
# Weglassen des Schluessels erzeugt exakt das alte Signal.
WT_BAND = 40.0
WT_N1 = 10
WT_N2 = 21
ATR_N = 14


def signal(k, idx, w=None):
    """WaveTrend-Signal an Kerze idx. Gibt 'long', 'short' oder None."""
    if idx < 1:
        return None
    try:
        import ti_indikatoren as ti
    except ImportError:
        return None
    if w is None:
        w = lade_wachen()
    wt1, wt2 = ti.wavetrend(
        k,
        n1=int(w.get("wt_n1", WT_N1)),
        n2=int(w.get("wt_n2", WT_N2)),
    )
    # Alle Werte muessen gesetzt sein
    if None in (wt1[idx - 1], wt2[idx - 1], wt1[idx], wt2[idx]):
        return None
    band = float(w.get("wt_ueberverkauft", WT_BAND))
    # LONG: wt1 kreuzt wt2 von unten, im ueberverkauften Bereich
    if wt1[idx - 1] <= wt2[idx - 1] and wt1[idx] > wt2[idx] and wt1[idx] < -band:
        return "long"
    # SHORT: wt1 kreuzt wt2 von oben, im ueberkauften Bereich
    if wt1[idx - 1] >= wt2[idx - 1] and wt1[idx] < wt2[idx] and wt1[idx] > band:
        return "short"
    return None


# --- Positionen ------------------------------------------------------------

def pruefe_einstieg(inst, k, z, w, faktor):
    # Skalieren statt doppeln: liegt fuer dieses Signal schon eine Position
    # mit gleichem Instrument UND gleicher Seite, wird sie vergroessert
    # (Regel in Handel/skalieren.py, gemessen 03.10.2026). Ein Seiten-
    # wechsel ist kein Skalieren - das ist ein neues Signal.
    sys.path.insert(0, HANDEL)
    import skalieren as skal

    if not z.get("positionen"):
        z["positionen"] = []
    if len(z["positionen"]) >= w.get("max_offene_positionen", 4):
        return
    if not k or len(k) < w.get("mindest_kerzen", 300):
        return

    idx = len(k) - 1
    sig = signal(k, idx, w)
    if not sig:
        return

    einstieg = k[idx][4]
    atr = atr_abs(k, idx, int(w.get("atr_n", ATR_N)))
    if not atr or atr <= 0:
        return

    # Der Stop-Abstand kommt aus dem ATR, wird aber in den Pflichtrahmen
    # gezwungen. Stop UND Ziel entstehen danach aus demselben Prozentsatz -
    # sonst stuende im Journal ein Stop-Preis, der nicht zu stop_pct passt,
    # und die Groesse waere gegen eine andere Zahl gerechnet als der Ausstieg.
    stop_pct = atr / einstieg * 100.0
    stop_pct = max(stop_pct, w.get("pflicht_stop_prozent_min", 5.0))
    stop_pct_eff = min(stop_pct, w.get("pflicht_stop_prozent_max", 12.0))

    vz = 1 if sig == "long" else -1
    abstand = einstieg * stop_pct_eff / 100.0
    r = w.get("ziel_r_vielfaches", 2.0)
    stop = einstieg - vz * abstand
    ziel = einstieg + vz * r * abstand

    nominel = w["risiko_je_position_usd"] / (stop_pct_eff / 100.0)
    nominel = min(nominel, w["max_pro_trade_usd"])
    nominel *= faktor
    if nominel <= 0:
        return

    # Die Kennung dieser Position (T-095). Sie entsteht beim Einstieg und
    # steht in JEDER Zeile dieser Position (Kauf UND Verkauf) - sonst
    # waeren zwei gleichzeitige Positionen im selben Instrument im
    # Journal nicht auseinanderzuhalten.
    _p = {
        "inst": inst, "seite": sig, "einstieg": einstieg,
        "stop": stop, "ziel": ziel, "stop_pct": stop_pct_eff,
        "nominal": nominel, "eroeffnet_zeit": _jetzt(),
        "pos_id": pos_kennung.neu(_jetzt()),
    }
    _offen = skal.finde_offene(z["positionen"], inst, sig)
    if _offen is not None:
        _f = skal.skaliere(_offen, einstieg, nominel, stop_pct_eff, r)
        if _f is not None:
            print("SKALIERUNG %s %s auf %.2f USD (war %.2f)  Stop %.2f  Ziel %.2f"
                  % (_offen.get("seite", "long").upper(), inst,
                     _f["einsatz_usd"], _f["alt_nominal"], _f["stop"],
                     _f["ziel"]))
            # KUMULATIVER Einsatz und GEWOGENER Einstieg, gleiche pos_id: die
            # Zeile ist der Stand dieser Position nach der Vergroesserung.
            journal(zeit=_jetzt(), modus="papier", aktion="kauf", inst=inst,
                    pos_id=_offen["pos_id"], seite=sig,
                    preis="%.6f" % _f["preis"],
                    einsatz_usd="%.2f" % _f["einsatz_usd"],
                    stop="%.6f" % _f["stop"], ziel="%.6f" % _f["ziel"],
                    stop_pct="%.2f" % _f["stop_pct"],
                    grund="wavetrend+skaliert")
        return

    z["positionen"].append(_p)

    print("EINSTIEG %s %.6f Stop %.2f%% Ziel R=2 (%.6f) Nominal %.2f USD" % (
        sig.upper(), einstieg, stop_pct_eff, ziel, nominel))
    journal(zeit=_jetzt(), modus="papier", aktion="kauf", inst=inst,
            pos_id=_p["pos_id"], seite=sig,
            preis="%.6f" % einstieg, einsatz_usd="%.2f" % nominel,
            stop="%.6f" % stop, ziel="%.6f" % ziel,
            stop_pct="%.2f" % stop_pct_eff, grund="wavetrend")


def pruefe_ausstiege(z, k, w, nur=None, erzwinge=None):
    """Prueft offene Positionen gegen die Kerzen von `nur`.

    `k` sind die Kerzen EINES Instruments. Ohne die Einschraenkung wurde jede
    offene Position gegen diesen einen Kurs geprueft - eine SOL-Position mit
    dem BTC-Kurs bewertet (15.09.2026). `nur=None` behaelt das alte Verhalten
    fuer Aufrufer, die wirklich alle Positionen meinen.
    """
    behalten = []
    for p in z.get("positionen", []):
        if nur is not None and p.get("inst") != nur:
            behalten.append(p)
            continue
        kurs = k[-1][4] if k else None
        if not kurs:
            behalten.append(p)
            continue

        # MAE/MFE ueber die LEBENSDAUER messen, nicht erst beim Ausstieg -
        # sonst waere die Zahl der Ausstiegskurs selbst und damit wertlos.
        sys.path.insert(0, HANDEL)
        import mae
        mae.merke_extrem(p, kurs)

        grund = None
        vz = 1 if p["seite"] == "long" else -1
        if p["seite"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif kurs >= p["ziel"]:
                grund = "ziel"
        else:
            if kurs >= p["stop"]:
                grund = "stop"
            elif kurs <= p["ziel"]:
                grund = "ziel"

        if erzwinge and not grund:
            grund = erzwinge       # Kill: Zwangsschluss zum Kurs, Stop/Ziel haben Vorrang

        if not grund:
            behalten.append(p)
            continue

        # G/V auf den NOMINALWERT: eine Kursbewegung von x Prozent bewegt
        # x Prozent des Nominalwerts. Bis zum 15.09.2026 stand hier die rohe
        # Kursdifferenz - bei BTC ein Faktor von rund 70.000, der Erloes
        # landete in Kurshoehe im Journal.
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
        erloes = p["nominal"] + gv
        print("AUSSTIEG (%s) %.6f G/V %+.2f USD" % (grund, kurs, gv))
        journal(zeit=_jetzt(), modus="papier", aktion="verkauf", inst=p["inst"],
                pos_id=p.get("pos_id", ""),
                seite=p["seite"], preis="%.6f" % kurs,
                einsatz_usd="%.2f" % erloes, stop="%.6f" % p["stop"],
                ziel="%.6f" % p["ziel"],
                stop_pct="%.2f" % p["stop_pct"], grund=grund,
                **mae.felder(p))

    z["positionen"] = behalten


# --- Laeuf -----------------------------------------------------------------

def lauf(modus):
    w = lade_wachen()
    z = lade_zustand()
    z.setdefault("positionen", [])

    if modus == "wachen":
        print(json.dumps(wp.lage(w, JOURNAL, z), indent=2, ensure_ascii=False))
        return

    s = wp.lage(w, JOURNAL, z)
    ruecklauf = s.get("ruecklauf_usd", 0.0)
    faktor = groessenfaktor(ruecklauf, w)

    if s.get("kill") and modus != "vorschau":
        status, ruecklauf = kg.phase(z, w, ruecklauf, s.get("runden_gesamt", 0), _jetzt)
        if status == "frei":
            faktor = groessenfaktor(ruecklauf, w)
        else:
            # Offene Positionen zum Marktkurs schliessen UND buchen (bis 09.10.2026
            # wurden sie ungebucht geleert und die Spur blieb fuer immer gesperrt).
            kg.schliesse_alle(
                z, lambda inst: lade_kerzen(inst, w.get("kerzen_takt", "1H"),
                                            w.get("mindest_kerzen", 300)),
                lambda k, inst: pruefe_ausstiege(z, k, w, nur=inst,
                                                 erzwinge=kg.KILL_GRUND))
            schreibe_zustand(z)
            spiegeln(z, w)
            return

    if modus == "vorschau":
        print("Vorschau: keine Dateien geschrieben.")
        # Die Sperrenzeile gehoert in JEDE Vorschau. dauerlauf.nur_fenster_
        # fehlt liest genau sie; fehlt sie, wird diese Spur nie nach einem
        # Freigabefenster gefragt (T-313, 02.10.2026).
        print("Live waere gesperrt durch: kein Live-Zweig in dieser "
              "Spur (Papier)")
        return

    # Ausstiege ueber ALLE Instrumente mit offener Position, Einstiege nur
    # ueber die des Plans. Eine Position auf einem entfernten Instrument wurde
    # sonst nie geprueft und belegte ihren Platz dauerhaft (Befund 28.09.2026;
    # Begruendung in wachen_pruefung.pruef_instrumente).
    plan = wp.plan_instrumente(w)
    verwaist = wp.verwaiste_instrumente(w, z)
    if verwaist:
        print("Verwaiste Instrumente (nicht mehr im Plan, Ausstieg laeuft "
              "weiter): %s" % ", ".join(verwaist), file=sys.stderr)
    for inst in wp.pruef_instrumente(w, z):
        intervall = w.get("kerzen_takt", "1H")
        anzahl = w.get("mindest_kerzen", 300)
        try:
            k = lade_kerzen(inst, intervall, anzahl)
        except Exception as e:
            print("Uebersprungen (%s): %s" % (inst, e), file=sys.stderr)
            continue
        if not k:
            print("Uebersprungen (%s): keine Kerzen" % inst, file=sys.stderr)
            continue

        bestehend = [p for p in z["positionen"] if p["inst"] == inst]
        if bestehend:
            z["positionen"] = [p for p in z["positionen"] if p["inst"] != inst]
            z["positionen"].extend(bestehend)
            pruefe_ausstiege(z, k, w, nur=inst)

        if inst in plan:
            pruefe_einstieg(inst, k, z, w, faktor)

    schreibe_zustand(z)
    spiegeln(z, w)


def groessenfaktor(ruecklauf, w):
    """Drawdown-Ratsche aus ratschen.py - eine Umsetzung fuer alle Spuren."""
    return ratschen.groessenfaktor(ruecklauf, w)


# --- Main -------------------------------------------------------------------

def main():
    # Meldet sich am Bus wie jede andere Spur im Dauerlauf (Muster
    # kraken/handeln.py). Ein toter Bus bricht den Lauf nicht ab.
    with ereignis.lauf("handel/wavetrend"):
        return _main()


def _main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau",
                    dest="modus", help="was waere dran, ohne schreiben")
    ap.add_argument("--papier", action="store_const", const="papier", dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    ap.set_defaults(modus="vorschau")
    a = ap.parse_args()

    if a.modus == "live":
        print("--live verweigert: Papier-Spur, keine Orders moeglich.")
        return 1

    lauf(a.modus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
