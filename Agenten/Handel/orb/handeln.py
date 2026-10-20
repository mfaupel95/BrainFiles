"""ORB auf OKX-Perpetuals - Papierzyklus (Spur orb).

Reine Simulation: M15-Kerzen von der oeffentlichen OKX-API (okxf, kein
Schluessel), Buch in zustand.json, kein einziger Order-Call. handel_erlaubt
bleibt false - diese Datei kann gar nicht echt handeln.

Vorlage ist `orbk/handeln.py` (dieselbe Strategie auf Kraken, laeuft seit
15.09.2026). Unterschiede: Datenquelle okxf (OKX-Perpetuals, USDT) statt
kraken, Session ist die UTC-Tagesgrenze (orb/session.py), und das Ziel kommt
aus `ziel_modus`/`ziel_k`/`ziel_punkte` der eigenen wachen.json.

--live ist ein gueltiger Aufruf: der Dauerlauf schaltet eine Spur nur scharf,
wenn ihr Zeitfenster offen ist. Ist ALLES sperrenfrei (handel_erlaubt,
freigabe.erfuellt, journal_zweitziel, API-Schluessel, Freigabefenster), legt
dieser Pfad eine ECHTE Order (Einstieg + Boersen-Stop + Ziel) an die Boerse.
Fehlt eine Sperre, laeuft der Lauf als Papier weiter und nennt die Gruende -
derselbe Fallsafe wie kraken/handeln.py.

DAS URTEIL STEHET IM WACHENBUCH UND BLEIBT STEHEN: der OKX-Backtest vom
13.09.2026 (siehe `_backtest` in wachen.json, nachrechenbar mit
`backtest.py`) ergibt fuer BTC_USDT EV -45.1 Punkte und fuer ETH_USDT
EV -3.7 Punkte je Runde - die 81-Prozent-Behauptung haelt auf Krypto NICHT.
Diese Spur laeuft deshalb ausschliesslich als PAPIER und ist nur da, um den
gemessenen Erwartungswert an echten, laufenden Kursen zu beobachten; sie ist
KEIN Kandidat fuer echtes Geld. `freigabe.backtest_bestanden` bleibt false,
damit niemand sie aus Versehen scharf schaltet.

Zyklus (alle 15 min):
  1. Ausstiege zuerst: offene Papier-Position gegen Stop/Ziel/Zwangsschluss
  2. Einstieg: nur wenn die Range fertig ist, heute noch nichts lief, die
     Range innerhalb mindest/max liegt und eine Kerze ueber/unter ihr schliesst
  3. Journal + Zustand schreiben, Journal nach Q: spiegeln (Bedingung 4)
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
sys.path.insert(0, str(HIER.parent / "xperp"))      # okxf
sys.path.insert(0, str(BUS))

import ereignis                                            # noqa: E402
import okxf                                                # noqa: E402
import session as sess                                     # noqa: E402
import wachen_orb as wp                                    # noqa: E402

# Risikostufe (HANDEL_RISIKO) ueber den PFAD laden, wie ratschen.py: die Spur
# hat ihren eigenen Ordner als sys.path[0], ein 'import risikostufe' haenge an
# der Reihenfolge der Eintraege.
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
SPUR = "orb"


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
        z.setdefault("positionen", [])
        return z
    return {"positionen": [], "letzter_lauf": None, "modus": "papier"}


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


def _range_fenster(w, key, tag):
    return sess.opening_range_fenster(w["instrumente"][key], tag)


def ziel_kurs(w, key, richtung, einstieg, range_hoehe):
    """Ziel aus der Wachen-Datei: r_vielfaches (k x Range) oder feste Punkte."""
    if w.get("ziel_modus") == "punkte":
        punkte = w["ziel_punkte"][key]
        return einstieg + punkte if richtung == "long" else einstieg - punkte
    k = w.get("ziel_k", 1.5)
    return (einstieg + k * range_hoehe if richtung == "long"
            else einstieg - k * range_hoehe)


def pruefe_ausstiege(z, w, jetzt=None, live=False):
    """Alle offenen Positionen gegen Stop/Ziel/Zwangsschluss.

    Rueckgabe: Liste (position, grund) der GESCHLOSSENEN Positionen. Die
    offenen bleiben in z['positionen'], die geschlossenen werden entfernt.

    Eine ECHTE Position (modus=live) gehoert der Boerse: im Papierlauf bleibt sie
    stehen (Boersen-Stop/Ziel schuetzen sie), im Live-Lauf schliesst sie nur
    `_exit_live` (gegen die Boerse verifiziert, reduceOnly) - bis 20.10.2026 buchte
    der Zwangsschluss zum Sessionende sie ohne Order aus dem Buch aus, und an der
    Boerse blieb sie ungeschuetzt offen (Muster mosaic 23.09.2026).
    """
    jetzt = jetzt or _jetzt()
    offen, geschlossen = [], []
    for p in z.get("positionen", []):
        konf = w["instrumente"][p["inst"]]
        tag = p["tag"] if isinstance(p["tag"], date) else date.fromisoformat(p["tag"])
        if p.get("letzter_kurs"):
            mae.merke_extrem(p, p["letzter_kurs"])
        if p["richtung"] == "long":
            stop_verletzt = p["letzter_kurs"] <= p["stop"]
            ziel_verletzt = p["letzter_kurs"] >= p["ziel"]
        else:
            stop_verletzt = p["letzter_kurs"] >= p["stop"]
            ziel_verletzt = p["letzter_kurs"] <= p["ziel"]
        if jetzt >= sess.zwangsschluss(konf, tag):
            grund, kurs = "zwangsschluss", p["letzter_kurs"]
        elif stop_verletzt:
            grund, kurs = "stop", p["stop"]
        elif ziel_verletzt:
            grund, kurs = "ziel", p["ziel"]
        else:
            offen.append(p)
            continue
        if p.get("modus") == "live":
            if not live:
                print("  AUSSTIEG %s verschoben: echte Position - nur der Live-Lauf "
                      "schliesst sie (Boerse schuetzt per Stop/Ziel)" % p["inst"])
                offen.append(p)
                continue
            ok, grund = _exit_live(p, konf["okx"], grund)
            if not ok:
                p["exit_ungeklaert"] = True
                print("  AUSSTIEG %s UNGEKLAERT - keine Marktorder, Position bleibt"
                      % p["inst"], file=sys.stderr)
                offen.append(p)
                continue
        _schliesse(p, kurs, grund)
        geschlossen.append((p, grund))
    z["positionen"] = offen
    return geschlossen


def _exit_live(p, paar, grund):
    """Der ECHTE Ausstieg einer LIVE-Position an der Boerse (Muster orbk).

    Rueckgabe (ok, effektiver_grund). ok=True: die Position ist an der Boerse
    schluss - durch eine hier gestellte Marketorder (reduceOnly) oder weil
    Stop/Ziel sie schon geschlossen hatte -, der Aufrufer darf buchen. ok=False:
    UNGEKLAERT, nichts geschlossen. Die Boerse wird IMMER zuerst gefragt: eine
    zweite Marketorder auf eine geschlossene Position eroeffnete einen Short.
    """
    try:
        offen = any(pos.get("instId") == paar for pos in okxf.positionen())
    except Exception as e:                                # noqa: BLE001
        print("  Live-Ausstieg %s nicht verifizierbar (%s) - KEINE Order, "
              "Position bleibt" % (paar, e), file=sys.stderr)
        return False, None
    if not offen:
        print("  Boerse hat %s bereits geschlossen - keine Marketorder" % paar)
        return True, "%s (boerse)" % grund
    try:
        okxf.markt_schliessen(paar, p.get("kontrakte") or p.get("menge"),
                              p["richtung"])
    except Exception as e:                                # noqa: BLE001
        print("  Markt-Close %s fehlgeschlagen (%s) - Position bleibt, "
              "UNGEKLAERT" % (paar, e), file=sys.stderr)
        return False, None
    print("  MARKT-CLOSE %s %s (Grund %s)" % (paar, p.get("kontrakte") or 0, grund))
    return True, grund


def _schliesse(p, kurs, grund):
    """Abschluss buchen. 'tag' kommt aus JSON als String zurueck - umparsen,
    sonst scheitert jeder echte Ausstieg (Befund orbk 13.09.2026)."""
    tag = p["tag"] if isinstance(p["tag"], date) else date.fromisoformat(p["tag"])
    gv = (kurs - p["einstieg"]) if p["richtung"] == "long" else (p["einstieg"] - kurs)
    gv_usd = gv * p.get("punkt_wert_usdt", 1.0)
    journal(tag.isoformat(), p["inst"], p["richtung"], p["einstieg"],
            p["stop"], p["ziel"], grund, kurs, round(gv, 4), round(gv_usd, 2),
            "%.4f" % float(p.get("mfe_pct") or 0.0),
            "%.4f" % float(p.get("mae_pct") or 0.0),
            mae.haltetage(p, heute=tag))
    p["ausgang"] = grund
    p["ausstieg"] = kurs
    p["gv_punkte"] = gv


def _kerzen_heute(w, key):
    """Die heutigen M15-Kerzen des Instruments (OKX-oeffentlich)."""
    konf = w["instrumente"][key]
    roh = okxf.kerzen(konf["okx"], bar="15m", anzahl=300)
    heute = _jetzt().date()
    return [{"zeit": datetime.fromtimestamp(r[0] / 1000, timezone.utc),
             "o": r[1], "h": r[2], "l": r[3], "c": r[4]}
            for r in roh
            if datetime.fromtimestamp(r[0] / 1000, timezone.utc).date() == heute]


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
kerzen_quelle = None


def _schon_gehandelt_heute(z, inst, tag):
    """Ein Trade je Instrument und UTC-Tag (ORB-Regel).

    Das Merkzeichen ueberlebt den Ausstieg - sonst steigt derselbe Breakout
    im selben Zyklus wieder ein. Geprueft wird je Instrument getrennt, damit
    zwei Instrumente unabhaengig je einen Trade pro Tag machen koennen.
    """
    heute = tag.isoformat()
    for p in z.get("positionen", []):
        if p.get("inst") == inst and p.get("tag") == heute:
            return True
    ztl = z.get("zuletzt_gehandelt_tag") or {}
    return ztl.get(inst) == heute


def pruefe_einstieg(z, w, jetzt=None):
    """Einstiege ueber ALLE aktiven Instrumente (BTC_USDT + ETH_USDT).

    Je Instrument: ein Trade pro UTC-Tag, hoechstens max_offene_positionen
    gleichzeitig. Fuer jedes openbare Instrument wird die Position an
    z['positionen'] angehaengt. Rueckgabe: Liste der NEU eroeffneten
    Positionen (nur fuer die Meldung). Kein Signal -> leere Liste.
    """
    jetzt = jetzt or _jetzt()
    tag = sess.handelstag(jetzt)
    offen_insts = {p.get("inst") for p in z.get("positionen", [])}
    max_pos = int(w.get("max_offene_positionen", 2))
    geoeffnet = []
    for key in w.get("instrumente_aktiv", []):
        if len(z.get("positionen", [])) >= max_pos:
            break
        if key in offen_insts:
            continue
        if _schon_gehandelt_heute(z, key, tag):
            continue
        konf = w["instrumente"].get(key)
        if not konf:
            continue
        start, ende = _range_fenster(w, key, tag)
        if jetzt < ende:
            continue
        if jetzt >= sess.zwangsschluss(konf, tag):
            continue
        if jetzt >= sess.letzter_einstieg(konf, tag,
                                          w.get("letzter_einstieg_min_vor_schluss", 60)):
            continue
        kerzen = (kerzen_quelle(w, key) if kerzen_quelle else _kerzen_heute(w, key))
        hr = opening_range(kerzen, w, key, tag)
        if hr is None:
            continue
        hoch, tief = hr
        hoehe = hoch - tief
        mie = w.get("mindest_range_punkte", {}).get(key)
        maxe = w.get("max_range_punkte", {}).get(key)
        if mie is None or maxe is None:
            continue
        if hoehe < mie:
            continue
        if hoehe > maxe:
            continue
        richtung, kurs = breakout_signal(kerzen, hoch, tief)
        if not richtung:
            continue
        stop = tief if richtung == "long" else hoch
        ziel = ziel_kurs(w, key, richtung, kurs, hoehe)
        p = {"inst": key, "richtung": richtung, "einstieg": kurs,
             "stop": stop, "ziel": ziel, "tag": tag.isoformat(),
             "letzter_kurs": kurs,
             "punkt_wert_usdt": konf.get("punkt_wert_usdt", 1.0),
             "range_hoehe": hoehe,
             "risiko_usdt": w.get("risiko_pro_trade_usdt")}
        z.setdefault("positionen", []).append(p)
        z.setdefault("zuletzt_gehandelt_tag", {})[key] = tag.isoformat()
        geoeffnet.append(p)
    return geoeffnet


def _letzter_kurs(w, key):
    return okxf.letzter_kurs(w["instrumente"][key]["okx"])


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
    if not okxf.schluessel_vorhanden():
        gruende.append("OKX_API_KEY/SECRET/PASSPHRASE nicht gesetzt")
    if not zeitfenster_offen():
        gruende.append("Freigabefenster nicht offen")
    return gruende


def positionsgroesse(w, p):
    """Kontrakte aus dem Buchrisiko: risiko / (range_hoehe * punkt_wert).

    Ganzzahlig, weil OKX-Perpetuals ganze Kontrakte handeln. 0 heisst: unter
    einem Kontrakt - nicht handelbar.
    """
    range_hoehe = p.get("range_hoehe") or 0.0
    punkt_wert = p.get("punkt_wert_usdt", 1.0)
    risiko = p.get("risiko_usdt") or w.get("risiko_pro_trade_usdt", 0.0) or 0.0
    if range_hoehe <= 0 or punkt_wert <= 0 or risiko <= 0:
        return 0
    return int(risiko / (range_hoehe * punkt_wert))


def platziere_einstieg(z, w, p, echt=True):
    """Einstieg + Boersen-Stop + Ziel fuer eine Position ordert.

    echt=False (Vorschau/Dry-Run) rechnet die geplante Order durch und zeigt
    sie, ruft aber KEINE Boersenfunktion - Tests und Handlauefe pruefen so
    die Rueckwaertsrechnung, ohne je eine Order zu platzieren. echt=True ist
    der einzige echte Pfad und steht ausschliesslich hinter lauf('live'),
    wenn keine Sperre zu ist.
    """
    key = p["inst"]
    konf = w["instrumente"][key]
    inst = konf["okx"]
    seite = "buy" if p["richtung"] == "long" else "sell"
    kontrakte = positionsgroesse(w, p)
    if kontrakte < 1:
        print("  %s: Positionsgroesse < 1 Kontrakt - kein Einstieg" % inst)
        return None
    if not echt:
        print("  DRY-RUN %s %s %d Kontrakte @ %.4f (Stop %.4f, Ziel %.4f)"
              % (seite, inst, kontrakte, p["einstieg"], p["stop"], p["ziel"]))
        return None
    ord_id = okxf.order_limit(inst, seite, kontrakte, p["einstieg"])
    print("  EINSTIEG %s %s %d Kontrakte @ %.4f (Order %s)"
          % (seite, inst, kontrakte, p["einstieg"], ord_id))
    okxf.schutz_stop_setzen(inst, p["richtung"], kontrakte, p["stop"],
                            p["ziel"])
    print("  Schutz-Stop (Stop %.4f, Ziel %.4f) gesetzt"
          % (p["stop"], p["ziel"]))
    p["ord_id"] = ord_id
    p["kontrakte"] = kontrakte
    p["modus"] = "live"
    return p


def lauf(modus="papier"):
    w = _wachen()
    z = lade_zustand()
    jetzt = _jetzt()
    z["letzter_lauf"] = jetzt.isoformat()
    meldungen = []
    # Sicherheits-Gatter AUCH hier (nicht nur in _main): lauf('live') darf nur
    # echt orden, wenn keine Sperre zu ist - doppelter Boden.
    live = (modus == "live") and not live_sperren(w)

    for p, grund in pruefe_ausstiege(z, w, jetzt, live=live):
        art = "LIVE" if p.get("modus") == "live" else "Papier"
        meldungen.append("AUSSTIEG (%s, %s): %s %s, Einstieg %.4f" % (
            art, grund, p["richtung"], p["inst"], p["einstieg"]))

    for p in pruefe_einstieg(z, w, jetzt):
        if live:
            platziere_einstieg(z, w, p, echt=True)
            meldungen.append("EINSTIEG (LIVE): %s %s @ %.4f" % (
                p["richtung"], p["inst"], p["einstieg"]))
        else:
            meldungen.append("EINSTIEG (Papier): %s %s @ %.4f" % (
                p["richtung"], p["inst"], p["einstieg"]))

    for p in z.get("positionen", []):
        try:
            p["letzter_kurs"] = _letzter_kurs(w, p["inst"])
        except Exception:  # noqa: BLE001
            pass
    schreibe_zustand(z)
    return meldungen


def zeige_wachen(w):
    z = lade_zustand()
    kopie = ("   |   Journal-Zweitziel %s%s"
             % (w.get("journal_zweitziel") or "-- nicht gesetzt",
                "" if "journal_zweitziel_ok" not in z
                else " (letzte Kopie %s)" % z["journal_zweitziel_ok"]))
    aktive = w.get("instrumente_aktiv", [])
    f = w.get("freigabe") or {}
    text = ("handel_erlaubt=%s, aktiv=%s, freigabe=%s, backtest=%s%s"
            % (w["handel_erlaubt"], ",".join(aktive) or "-",
               f.get("erfuellt"), f.get("backtest_bestanden"), kopie))
    offene = z.get("positionen", [])
    if offene:
        text += "\n  Offene Positionen: " + ", ".join(
            "%s %s @ %.4f" % (p["richtung"], p["inst"], p["einstieg"])
            for p in offene)
    return text


def main(argv=None):
    with ereignis.lauf("handel/orb"):
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
    z = lade_zustand()
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        wp.spiegele_journal([ZUSTAND], ziel)
    print("Journal ausser Haus: %s (%s)" % ("ok" if ok else "--", info))
    return 0


if __name__ == "__main__":
    sys.exit(main())

