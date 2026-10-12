"""ORB auf Kraken - Papierzyklus (Spur orbk).

Buch in zustand.json, Kerzen von der oeffentlichen Kraken-API. Der Standard-
lauf ist reine Simulation (kein Order-Call, handel_erlaubt=false); nur --live
mit ALLEN Sperren offen legt echte Orders an die Boerse (unten im Docstring).

--live ist ein gueltiger Aufruf: der Dauerlauf schaltet eine Spur nur scharf,
wenn ihr Zeitfenster offen ist (freigabefenster.py). Ist ALLES sperrenfrei
(handel_erlaubt, freigabe.erfuellt, journal_zweitziel, API-Schluessel,
Freigabefenster), legt dieser Pfad an die Boerse: Einstieg + Boersen-STOP +
Boersen-TAKE-PROFIT (kraken.take_profit_setzen). Das ZIEL hat seit dem
Take-Profit-Ausbau (12.10.2026) eine eigene Boersenorder - es bleibt kein
echter Bestand ohne Exit an Kraken. Fehlt eine Sperre, laeuft der Lauf als
Papier weiter und nennt die Gruende - derselbe Fallsafe wie kraken/handeln.py.

AUSSTIEG (echt): Eine LIVE-Position (p['modus']=='live') schliesst der
Live-Pfad am MARKT, wenn Stop/Ziel/Zwangsschluss feuert. pruefe_ausstiege
stoesst dafuer einen Markt-Close (markt_verkauf, Long) - aber nur, nachdem die
Buch-vs-Boerse-Pruefung (_abgleich_runde) bestaetigt hat, dass die Position
dort noch liegt. Hat die Boerse sie schon geschlossen (Boersen-Stop oder
Take-Profit ausgeloest), wird KEINE zweite Marketorder gestellt (die wuerde
ueberverkaufen und einen Short eroeffnen) - der Boersenschluss wird nur im
Buch nachgezogen. Kann die Boerse nicht gelesen werden, schliesst dieser Lauf
nichts und meldet den Ausstieg als UNGEKLAERT. Ein PAPIERLauf bleibt eine
reine Buchoperation und schliesst eine echte Position nicht.

SHORT auf Kraken-Spot ist unmoeglich (kein echtes Short-Halten): ein
Short-Signal wird im Live-Pfad mit klarem Sperrgrund verweigert (kein
Einstieg). Der Papierlauf simuliert Shorts fuer den Backtest weiter.

Zyklus (alle 15 min):
  1. Ausstiege zuerst: offene Papier-Position gegen Stop/Ziel/Zwangsschluss
  2. Einstieg: wenn Session-Fenster offen und noch nicht gehandelt ->
     Opening Range (00:00-00:30 UTC) fertig -> Breakout pruefen
  3. Journal + Zustand schreiben
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
BUS = HIER.parent.parent / "Bus"
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent))      # mae
import mae
sys.path.insert(0, str(HIER.parent / "kraken"))
sys.path.insert(0, str(BUS))

import ereignis
import kraken
import session as sess
import wachen_orb as wp


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

ZUSTAND = risikostufe.datei(HIER / "zustand.json")
JOURNAL = risikostufe.datei(HIER / "handelsjournal.csv")

# Spur-Name fuer den Freigabe-Dienst (freigabefenster.py / freigabebeleg.py):
# muss mit dem Schluessel in dauerlauf.SPUREN zusammenpassen.
SPUR = "orbk"


def _jetzt():
    return datetime.now(timezone.utc)


def _wachen():
    return risikostufe.skaliere(
        json.loads((HIER / "wachen.json").read_text(encoding="utf-8")))


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

# Freigabefenster ueber den PFAD laden (Hausmuster, s. kraken/handeln.py): ein
# blankes 'import freigabefenster' greift im Spurlauf nicht, weil Handel/ nicht
# auf sys.path liegt (nur <spur>/../../Bus).
_fw_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "freigabefenster.py")
_fw_spec_obj = _rs_spec("freigabefenster", _fw_datei)
freigabefenster = _rs_mod(_fw_spec_obj)
_fw_spec_obj.loader.exec_module(freigabefenster)


def lade_zustand():
    z = atomar.lade_json(ZUSTAND, lambda: None)
    if z is not None:
        z.setdefault("modus", "papier")
        return z
    return {"position": None, "letzter_lauf": None, "herzschlag_ok": True,
            "modus": "papier"}


def schreibe_zustand(z):
    z.setdefault("modus", "papier")
    atomar.schreibe_json(ZUSTAND, z)


def journal(*felder):
    neu = not JOURNAL.exists()
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if neu:
            w.writerow(["zeit", "inst", "richtung", "einstieg", "stop",
                        "ziel", "ausgang", "ausstieg", "gv_punkte", "gv_usd",
                        "mfe_pct", "mae_pct", "haltetage"])
        w.writerow(felder)


def _inst_konf(w):
    key = w.get("instrument_aktiv")
    if not key:
        return None, None
    return key, w["instrumente"][key]


def _punkte_zu_usd(punkte, konf):
    return punkte * konf.get("punkt_wert_usd", 1.0)


def _range_fenster(w, key, tag):
    """(start, ende) der Opening Range fuer den UTC-Tag."""
    start, ende = sess.opening_range_fenster(w["instrumente"][key], tag)
    return start, ende


def pruefe_ausstiege(z, w, jetzt=None, live=False):
    """Offene Position: Stop/Ziel/Zwangsschluss. Rueckgabe (veraendert, grund).

    LIVE-Position (p['modus']=='live') im LIVE-Lauf (live=True): der Ausstieg
    schliesst die ECHTE Position an der Boerse (_exit_live) - verifiziert
    gegen Stop/Ziel-Fuellstand; bei Ungewissheit KEINE Marketorder, der
    Ausstieg bleibt als UNGEKLAERT stehen. Ein PAPIERLAUF (live=False) laesst
    eine echte Position im Buch stehen: sie ist per Boersen-Stop/Ziel
    geschuetzt, und nur der Live-Pfad haelt dort Geld fest. Papier-Positionen
    werden rein im Buch geschlossen (Simulation, keine Order).
    """
    p = z.get("position")
    if not p:
        return False, None
    jetzt = jetzt or _jetzt()
    key = p["inst"]
    konf = w["instrumente"][key]
    tag = p["tag"] if isinstance(p["tag"], date) else date.fromisoformat(p["tag"])
    # MAE/MFE ueber die LEBENDAUER messen, nicht erst beim Ausstieg -
    # sonst waere die Zahl der Ausstiegskurs selbst und damit wertlos.
    if p.get("letzter_kurs"):
        mae.merke_extrem(p, p["letzter_kurs"])

    if p["richtung"] == "long":
        stop_verletzt = p["letzter_kurs"] <= p["stop"]
        ziel_verletzt = p["letzter_kurs"] >= p["ziel"]
    else:
        stop_verletzt = p["letzter_kurs"] >= p["stop"]
        ziel_verletzt = p["letzter_kurs"] <= p["ziel"]
    zwang = jetzt >= sess.zwangsschluss(konf, tag)
    if zwang:
        grund, kurs = "zwangsschluss", p["letzter_kurs"]
    elif stop_verletzt:
        grund, kurs = "stop", p["stop"]
    elif ziel_verletzt:
        grund, kurs = "ziel", p["ziel"]
    else:
        return False, None

    if p.get("modus") == "live" and not live:
        print("  AUSSTIEG %s verschoben: echte Position - nur der Live-Lauf "
              "schliesst sie (Boerse schuetzt per Stop/Ziel)" % key)
        return False, None
    if p.get("modus") == "live":
        ok, effgrund = _exit_live(z, w, p, konf["kraken"], kurs, grund)
        if not ok:
            p["exit_ungeklaert"] = True
            print("  AUSSTIEG %s UNGEKLAERT - keine Marktorder, Position bleibt"
                  % key, file=sys.stderr)
            return False, None
        grund = effgrund
    _schliesse(p, kurs, grund)
    return True, grund

def _schliesse(p, kurs, grund):
    # zustand.json serialisiert alles zu Strings: "tag" kommt beim Lesen als
    # ISO-String zurueck, nicht als date. Ohne das Umparsen scheiterte jeder
    # echte Ausstieg mit AttributeError, die Position liess sich nicht
    # schliessen (aufgefallen 13.09.2026: Ziel erreicht, jeder Papierlauf
    # endete mit Rueckgabe 1).
    tag = p["tag"] if isinstance(p["tag"], date) else date.fromisoformat(p["tag"])
    gv = (kurs - p["einstieg"]) if p["richtung"] == "long" else (p["einstieg"] - kurs)
    gv_usd = _punkte_zu_usd(gv, {})
    journal(tag.isoformat(), p["inst"], p["richtung"], p["einstieg"],
            p["stop"], p["ziel"], grund, kurs, round(gv, 4), round(gv_usd, 2),
            "%.4f" % float(p.get("mfe_pct") or 0.0),
            "%.4f" % float(p.get("mae_pct") or 0.0),
            mae.haltetage(p, heute=tag))
    p["ausgang"] = grund
    p["ausstieg"] = kurs
    p["gv_punkte"] = gv


def _kerzen_heute(w, key):
    """Die heutigen M15-Kerzen des Instruments (Kraken-oeffentlich)."""
    konf = w["instrumente"][key]
    paar = konf["kraken"]
    roh = kraken.kerzen(paar, intervall=15, anzahl=720)
    heute = _jetzt().date()
    return [{"zeit": datetime.fromtimestamp(r[0] / 1000, timezone.utc),
             "o": r[1], "h": r[2], "l": r[3], "c": r[4]}
            for r in roh if datetime.fromtimestamp(r[0] / 1000, timezone.utc).date() == heute]


def opening_range(kerzen, w, key, tag):
    start, ende = _range_fenster(w, key, tag)
    im_fenster = [k for k in kerzen if start <= k["zeit"] < ende]
    if len(im_fenster) < 2:
        return None
    zwei = im_fenster[:2]
    return max(k["h"] for k in zwei), min(k["l"] for k in zwei)


def breakout_signal(kerzen, hoch, tief):
    """Erste Kerze nach der Range, die darueber/darunter schliesst."""
    for k in kerzen:
        if k["c"] > hoch:
            return "long", k["c"]
        if k["c"] < tief:
            return "short", k["c"]
    return None, None


# Test-Seam: Tests ersetzen die Quelle durch synthetische Kerzen.
kerzen_quelle = None  # None -> echte Kraken-Kerzen (ueber _kerzen_heute)


def pruefe_einstieg(z, w, jetzt=None):
    """Papier-Einstieg nach ORB-Regeln. Rueckgabe (einstieg, meldung)."""
    jetzt = jetzt or _jetzt()
    key, konf = _inst_konf(w)
    if not key:
        return None, "kein instrument_aktiv (Backtest-Urteil fehlt)"
    tag = sess.handelstag(jetzt)
    start, ende = _range_fenster(w, key, tag)
    if jetzt < ende:
        return None, "Range laeuft noch (%s bis %s)" % (
            start.strftime("%H:%M"), ende.strftime("%H:%M"))
    if jetzt >= sess.zwangsschluss(konf, tag):
        return None, "Session vorbei"
    if _schon_gehandelt_heute(z, tag):
        return None, "heute schon gehandelt"
    kerzen = (kerzen_quelle(w, key) if kerzen_quelle
              else _kerzen_heute(w, key))
    hr = opening_range(kerzen, w, key, tag)
    if hr is None:
        return None, "keine komplette Range (Daten?)"
    hoch, tief = hr
    if hoch - tief < w["mindest_range_punkte"][key]:
        return None, "Range zu klein (%.2f Pkt)" % (hoch - tief)
    if hoch - tief > w["max_range_punkte"][key]:
        return None, "Range zu gross (%.2f Pkt)" % (hoch - tief)
    richtung, kurs = breakout_signal(kerzen, hoch, tief)
    if not richtung:
        return None, "kein Breakout (Range %.2f..%.2f)" % (tief, hoch)
    stop = tief if richtung == "long" else hoch
    ziel = (kurs + w["ziel_k"] * (hoch - tief) if richtung == "long"
            else kurs - w["ziel_k"] * (hoch - tief))
    z["position"] = {"inst": key, "richtung": richtung, "einstieg": kurs,
                     "stop": stop, "ziel": ziel, "tag": tag.isoformat(),
                     "letzter_kurs": kurs,
                     # Positionsgroesse fuer den Live-Pfad (Buchrisiko teilen).
                     "range_hoehe": hoch - tief,
                     "punkt_wert_usd": konf.get("punkt_wert_usd", 1.0),
                     "risiko_usd": w.get("risiko_pro_trade_usd", 10.0)}
    # Merkzeichen fuer "heute schon gehandelt": muss den Ausstieg
    # ueberleben, sonst steigt derselbe Breakout im selben Zyklus wieder
    # ein (Endloskreis, siehe _schon_gehandelt_heute).
    z["zuletzt_gehandelt_tag"] = tag.isoformat()
    return "papier", "%s %s @ %.4f (Stop %.4f, Ziel %.4f)" % (
        richtung, key, kurs, stop, ziel)


def _schon_gehandelt_heute(z, tag):
    """Ein Trade je UTC-Tag (ORB-Regel).

    Die offene Position traegt den Tag, aber das reicht nicht: nach dem
    Ausstieg wird sie entfernt, und ohne Merkzeichen wuerde derselbe
    Breakout im selben Zyklus sofort wieder eingestiegen - Ausstieg und
    Wiedereinstieg im Endloskreis, Journal voller identischer Zeilen,
    jede Viertelstunde eine AUSSTIEG-Meldung (Befund 13.09.2026). Das
    Merkzeichen wird beim EINstieg gesetzt (zuletzt_gehandelt_tag) und
    ueberlebt den Ausstieg.
    """
    p = z.get("position")
    if p and p.get("tag") == tag.isoformat():
        return True
    return z.get("zuletzt_gehandelt_tag") == tag.isoformat()


def zeitfenster_offen():
    """Hat Max diese Spur zeitlich freigegeben (freigabefenster.py)?

    Ein Lesefehler gilt als *nicht* offen - im Zweifel keine Order. Er wird
    gemeldet statt still geschluckt (Befund scanner 22.09.2026)."""
    try:
        return bool(freigabefenster.lade(SPUR).offen())
    except Exception as e:                                   # noqa: BLE001
        print("  Zeitfenster nicht lesbar (%s: %s) - gilt als zu."
              % (type(e).__name__, e), file=sys.stderr)
        return False


def live_sperren(w):
    """Alle Gruende, die einen --live-Lauf auf Papier zurueckwerfen.

    Leere Liste heisst: scharf. Der Dauerlauf (dauerlauf.nur_fenster_fehlt)
    oeffnet sein Auto-Freigabefenster nur, wenn GENAU EIN Grund fehlt - und
    dieser eine Grund ist das Fenster. Deshalb traegt der Fenster-Grund als
    einziger das Wort 'Freigabefenster'.
    """
    gruende = []
    if not w.get("handel_erlaubt"):
        gruende.append("wachen.json handel_erlaubt=false")
    if not (w.get("freigabe") or {}).get("erfuellt"):
        gruende.append("freigabe.erfuellt=false")
    if not w.get("journal_zweitziel"):
        gruende.append("journal_zweitziel nicht gesetzt (Bedingung 4)")
    if not kraken.schluessel_vorhanden():
        gruende.append("KRAKEN_SPOT_API_KEY/SECRET nicht gesetzt")
    if not zeitfenster_offen():
        gruende.append("Freigabefenster nicht offen")
    return gruende


def positionsgroesse(w, p):
    """Basiswaehrung aus dem Buchrisiko: risiko / (range_hoehe * punkt_wert).

    Reine Rechnung ohne Netz - die Paar-Rundung passiert erst bei der echten
    Order (platziere_einstieg, echt=True). 0 heisst: nicht handelbar.
    """
    range_hoehe = p.get("range_hoehe") or 0.0
    punkt_wert = p.get("punkt_wert_usd", 1.0)
    risiko = p.get("risiko_usd") or w.get("risiko_pro_trade_usd", 0.0) or 0.0
    if range_hoehe <= 0 or punkt_wert <= 0 or risiko <= 0:
        return 0.0
    return risiko / (range_hoehe * punkt_wert)


def platziere_einstieg(z, w, p, echt=True):
    """Einstieg + Boersen-Stop + Boersen-Take-Profit fuer eine Position ordert.

    echt=False (Vorschau/Dry-Run) rechnet die geplante Order durch und zeigt
    sie, ruft aber KEINE Boersenfunktion - Tests und Handlauefe pruefen so
    die Rueckwaertsrechnung, ohne je eine Order zu platzieren. echt=True ist
    der einzige echte Pfad und steht ausschliesslich hinter lauf('live'),
    wenn keine Sperre zu ist.

    Seit dem Take-Profit-Ausbau (12.10.2026) wird bei einer LONG-Live-Position
    zusaetzlich zum Stop auch das ZIEL als take-profit-market-Order an die
    Boerse gelegt (kraken.take_profit_setzen): ein ausgeloestes Ziel raeumt
    die Position an der Boerse selbst ab. Nur Long - ein Short-Signal wird
    verweigert: Kraken-Spot kann kein Short halten, ein Verkauf ohne Bestand
    waere dort ein Fehler.
    """
    key = p["inst"]
    konf = w["instrumente"][key]
    paar = konf["kraken"]
    if p["richtung"] == "short":
        print("  %s: Short auf kraken Spot nicht moeglich - kein Einstieg "
              "(nur Long)" % paar)
        return None
    menge = positionsgroesse(w, p)
    if menge <= 0:
        print("  %s: Positionsgroesse <= 0 - kein Einstieg" % paar)
        return None
    if not echt:
        print("  DRY-RUN %s long %.8f %s @ %.4f (Stop %.4f, Ziel %.4f)"
              % (paar, menge, p["inst"], p["einstieg"], p["stop"], p["ziel"]))
        return None
    # Nur fuer die echte Order: auf Paar-Genauigkeit runden (lot_decimals).
    try:
        stellen = int(kraken.paar_info(paar).get("mengen_stellen", 8))
    except Exception:                                     # noqa: BLE001
        stellen = 8
    menge = int(menge * 10 ** stellen) / 10 ** stellen
    if menge <= 0:
        print("  %s: Positionsgroesse nach Rundung <= 0 - kein Einstieg" % paar)
        return None
    kauf_txid = kraken.markt_kauf(paar, menge, echt=True)
    print("  EINSTIEG LONG %s %.8f %s @ %.4f (Order %s)"
          % (paar, menge, p["inst"], p["einstieg"], kauf_txid))
    stop_txid = kraken.stop_setzen(paar, menge, p["stop"], echt=True)
    print("  Schutz-Stop (%.4f) gesetzt" % p["stop"])
    # Take-Profit an die Boerse. Schlaegt es fehl, bleibt der Stop als
    # Notausstieg (und der Live-Ausstiegspfad kann das Ziel trotzdem per
    # Marketorder schliessen) - die Position wird nur markiert, nicht
    # verworfen.
    try:
        tp_txid = kraken.take_profit_setzen(paar, menge, p["ziel"], echt=True)
    except Exception as e:                                # noqa: BLE001
        print("  Take-Profit fuer %s fehlgeschlagen (%s) - Stop bleibt, "
              "Ausstieg laeuft ueber den Live-Pfad" % (paar, e),
              file=sys.stderr)
        tp_txid = None
    if tp_txid:
        print("  Take-Profit (%.4f) gesetzt" % p["ziel"])
    p["kauf_txid"] = kauf_txid
    p["stop_txid"] = stop_txid
    p["tp_txid"] = tp_txid
    p["tp_fehlt"] = not tp_txid
    p["menge"] = menge
    p["modus"] = "live"
    return p


def _exit_live(z, w, p, paar, kurs, grund):
    """Der ECHTE Ausstieg fuer eine LIVE-Position an der Boerse.

    Rueckgabe (ok, effektiver_grund): ok=True bedeutet, die Position ist an
    der Boerse schlussgeworden - entweder durch eine hier gestellte
    Marketorder, oder weil die Boerse sie schon per Stop/Ziel geschlossen
    hatte - und der Aufrufer darf lokal buchen. ok=False heisst UNGEKLAERT:
    es wird NICHTS geschlossen, keine Marketorder, die Position bleibt stehen.
    Eine zweite Marketorder auf eine bereits geschlossene Position waere ein
    Ueberverkauf und eroeffnete einen Short - deshalb wird die Boerse IMMER
    zuerst gefragt (stop_gefuellt auf Stop und Take-Profit), bevor geschlossen
    wird.
    """
    try:
        stop_weg = bool(p.get("stop_txid")) and kraken.stop_gefuellt(p["stop_txid"])
        tp_weg = bool(p.get("tp_txid")) and kraken.stop_gefuellt(p["tp_txid"])
    except Exception as e:                                # noqa: BLE001
        print("  Live-Ausstieg %s nicht verifizierbar (%s) - KEINE Order, "
              "Position bleibt" % (paar, e), file=sys.stderr)
        return False, None
    if stop_weg or tp_weg:
        fach = "stop" if stop_weg else "ziel"
        print("  Boerse hat %s bereits geschlossen (%s) - keine Marketorder"
              % (paar, fach))
        return True, "%s (boerse)" % fach
    # Noch gehalten: Schutzauftraege abraeumen, dann Markt-Close.
    for txid in (p.get("stop_txid"), p.get("tp_txid")):
        if not txid:
            continue
        try:
            kraken.order_stornieren(txid)
        except Exception as e:                            # noqa: BLE001
            print("  Schutzauftrag %s nicht stornierbar (%s)" % (txid, e),
                  file=sys.stderr)
    try:
        kraken.markt_verkauf(paar, p["menge"], echt=True)
    except Exception as e:                                # noqa: BLE001
        print("  Markt-Close %s fehlgeschlagen (%s) - Position bleibt, "
              "UNGEKLAERT" % (paar, e), file=sys.stderr)
        return False, None
    print("  MARKT-CLOSE %s %.8f (Grund %s)" % (paar, p["menge"], grund))
    return True, grund


def _abgleich_runde(z, w):
    """Buch gegen BOERSE (nur Live-Position): schon geschlossene zurueckspiegeln.

    Hat der Boersen-Stop oder das Boersen-Take-Profit die Position bereits
    ausgeloest, ist sie an der Boerse weg - im Buch wird das nachgezogen,
    OHNE jede Order (ein gefuellter Stop/Ziel hat schon verkauft). Kann die
    Boerse nicht gelesen werden, bleibt die Position stehen und es wird
    nichts behauptet ("keine Aussage" statt einer geratenen Zahl).
    """
    zus = z.get("position")
    if not zus or zus.get("modus") != "live":
        return None
    paar = w["instrumente"][zus["inst"]]["kraken"]
    try:
        stop_weg = bool(zus.get("stop_txid")) and kraken.stop_gefuellt(zus["stop_txid"])
        tp_weg = bool(zus.get("tp_txid")) and kraken.stop_gefuellt(zus["tp_txid"])
    except Exception as e:                                # noqa: BLE001
        print("  Buch-vs-Boerse %s nicht verifizierbar (%s) - keine Aussage"
              % (paar, e), file=sys.stderr)
        return None
    if not (stop_weg or tp_weg):
        print("  Buch-vs-Boerse: Buch und Boerse stimmen ueberein")
        return {"ausgebucht": False}
    fach = "stop" if stop_weg else "ziel"
    trig = zus["stop"] if stop_weg else zus["ziel"]
    _schliesse(zus, zus.get("letzter_kurs") or trig, "%s (boerse)" % fach)
    z.pop("position", None)
    print("  Buch-vs-Boerse: %s WEG an der Boerse (%s) - Boersenschluss "
          "gebucht, keine Marketorder" % (paar, fach))
    return {"ausgebucht": True, "grund": fach}

def lauf(modus="papier"):
    w = _wachen()
    z = lade_zustand()
    jetzt = _jetzt()
    z["letzter_lauf"] = jetzt.isoformat()

    meldungen = []
    # Sicherheits-Gatter AUCH hier (nicht nur in _main): lauf('live') darf nur
    # echt orden, wenn keine Sperre zu ist - doppelter Boden.
    live = (modus == "live") and not live_sperren(w)

    # 1. Buch zuerst gegen BOERSE (nur Live-Positionen): hat die Boerse die
    #    Position schon geschlossen (Boersen-Stop oder Take-Profit ausgeloest),
    #    wird das im Buch nachgezogen - nie eine zweite Marketorder, nie eine
    #    geratene Zahl.
    if (z.get("position") or {}).get("modus") == "live":
        _abgleich_runde(z, w)
    # 2. Ausstiege zuerst (der Live-Ausstieg schliesst die echte Position am
    #    Markt, verifiziert gegen die Boerse).
    veraendert, grund = pruefe_ausstiege(z, w, jetzt, live=live)
    if veraendert:
        p = z.pop("position", None)
        art = "LIVE" if p and p.get("modus") == "live" else "Papier"
        meldungen.append("AUSSTIEG (%s, %s): %s %s, Einstieg %.4f" % (
            art, grund, p["richtung"], p["inst"], p["einstieg"]))

    # 3. Einstieg
    if not z.get("position"):
        einstieg, meldung = pruefe_einstieg(z, w, jetzt)
        if einstieg:
            if live:
                platz = platziere_einstieg(z, w, z["position"], echt=True)
                if platz:
                    meldungen.append("EINSTIEG (LIVE): " + meldung)
                else:
                    # platziere_einstieg hat es verweigert (z.B. Short auf
                    # Spot) und den Grund schon ausgedruckt - keine Position.
                    inst = z["position"]["inst"]
                    z.pop("position", None)
                    meldungen.append("kein Einstieg: %s - Order abgelehnt "
                                     "(Details oben)" % inst)
            else:
                meldungen.append("EINSTIEG (Papier): " + meldung)
        elif meldung:
            meldungen.append("kein Einstieg: " + meldung)

    # Herzschlag + Zustand
    if z.get("position"):
        z["position"]["letzter_kurs"] = _letzter_kurs(w, z["position"]["inst"])
    schreibe_zustand(z)
    return meldungen


def _letzter_kurs(w, key):
    konf = w["instrumente"][key]
    return kraken.letzter_kurs(konf["kraken"])


def zeige_wachen(w):
    key, konf = _inst_konf(w)
    z = lade_zustand()
    kopie = ("   |   Journal-Zweitziel %s%s"
             % (w.get("journal_zweitziel") or "-- nicht gesetzt",
                "" if "journal_zweitziel_ok" not in z
                else " (letzte Kopie %s)" % z["journal_zweitziel_ok"]))
    if not konf:
        return "kein instrument_aktiv - Spur gesperrt (Backtest fehlt)"
    f = w.get("freigabe") or {}
    return ("%s (%s): handel_erlaubt=%s, aktiv=%s, freigabe=%s, backtest=%s%s"
            % (key, konf["kraken"], w["handel_erlaubt"], key,
               f.get("erfuellt"), f.get("backtest_bestanden"), kopie))


def main(argv=None):
    # Der Dauerlauf startet dieses Skript als eigenen Prozess (SPUREN
    # ["orbk"], skript=handeln.py) - Start und Ende melden sich deshalb hier
    # am Bus.
    # Muster: xperp/handeln.py. Ein toter Bus bricht den Lauf nicht ab.
    with ereignis.lauf("handel/orbk"):
        return _main(argv)


def _main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("modus", nargs="?", default="papier",
                   choices=("papier", "--papier", "status", "vorschau",
                            "--status", "--vorschau", "live", "--live"))
    p.add_argument("--papier", dest="flag_papier", action="store_true")
    p.add_argument("--status", dest="flag_status", action="store_true")
    p.add_argument("--vorschau", dest="flag_vorschau", action="store_true")
    p.add_argument("--live", dest="flag_live", action="store_true")
    a = p.parse_args(argv)
    modus = a.modus
    if a.flag_papier:
        modus = "papier"
    if a.flag_status:
        modus = "status"
    if a.flag_vorschau:
        modus = "vorschau"
    if a.flag_live:
        modus = "live"
    w = _wachen()
    if modus == "status":
        print(zeige_wachen(w))
        return 0
    if modus == "vorschau":
        # Der Dauerlauf liest die Sperrgruende aus genau diesem Modus.
        print(zeige_wachen(w))
        print("Live waere gesperrt durch: %s"
              % ("; ".join(live_sperren(w)) or "nichts"))
        return 0
    live_modus = "papier"
    if modus == "live":
        gruende = live_sperren(w)
        if gruende:
            print("--live angefordert, aber gesperrt: " + "; ".join(gruende))
            print("-> es wird Papier gehandelt.")
        else:
            live_modus = "live"
            print("--live: alle Sperren offen - LIVE")
    meldungen = lauf(modus=live_modus)
    for m in meldungen:
        print(m)
    # Bedingung 4: Journal und Zustand ausser Haus - nach dem Herzschlag.
    # Erst schreiben, dann kopieren: ein haengendes Zweitlaufwerk darf den
    # Zyklus verzoegern, aber nicht den Herzschlag verschlucken. Ein fehlendes
    # Ziel ist kein Fehler des Laufs; der Stand steht im Zustand.
    z = lade_zustand()
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        # Der Vermerk ist juenger als die Kopie: einmal nachziehen, damit auf
        # Q: derselbe Stand liegt. Sonst waere die Kopie in genau dem Zyklus
        # aelter, in dem sich der Spiegelstand aendert.
        wp.spiegele_journal([ZUSTAND], ziel)
    print("Journal ausser Haus: %s (%s)" % ("ok" if ok else "--", info))
    return 0


if __name__ == "__main__":
    sys.exit(main())