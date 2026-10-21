"""Aus der Rangliste des Leichtscans Kandidaten bauen, per LLM sieben und -
im Rahmen der Wachen - ausfuehren (Spur scanner_llm).

Apparat:
    1. scan.py     : Tageskerzen von OKX -> Regel-Score (bewertung) -> Kandidaten
                     hinter den LEICHTEREN Toren dieser Spur.
    2. llm_sieben  : Jeder Kandidat wird dem lokalen Modell (llm_lokal) vorgelegt.
                     Handelbar ist er NUR bei Urteil 'long' UND confidence >=
                     llm_mindest_confidence (65). NOTHING/SELL/zu unsicher wird
                     geloggt und uebersprungen - kein Urteil heisst kein Handel.
    3. handeln     : Offene Positionen gegen Stop/Ziel, dann die LLM-freigegebenen
                     Einstiege buchen (Papierbuch). Journal + Zustand nach Q: spiegeln.

Aufruf:
    <venv>\\python.exe scanner_llm\\handeln.py --vorschau   # nur zeigen
    <venv>\\python.exe scanner_llm\\handeln.py --papier     # Papierhandel (Standard)
    <venv>\\python.exe scanner_llm\\handeln.py --live       # echte Orders, wenn alle Sperren offen
    <venv>\\python.exe scanner_llm\\handeln.py --wachen     # Bedingungen 2-5
    <venv>\\python.exe scanner_llm\\handeln.py --status     # Kurzstatus

Die Sperren fuer --live (Handelsregeln):
    1. wachen.json  handel_erlaubt == true   (diese Spur startet auf false = PAPER)
    2. OKX-Schluessel als Benutzervariablen gesetzt
    3. --live ausdruecklich auf der Kommandozeile
    4. wachen.json  freigabe.erfuellt == true    (Bedingung 1, handgeprueft)
    5. Herzschlag frisch                         (Bedingung 3)
    6. rollierender Erwartungswert nicht negativ (Bedingung 5)
    7. eine Freigabe von Hand: Bildschirmfenster oder Zeitfenster (Bedingung 1)
Fehlt eine, wird Papier gehandelt und gesagt, welche Sperre zu war.

Die gemeinsam genutzten Module (risikostufe, freigabefenster, atomar,
pos_kennung, llm_lokal, wachen_pruefung, scan, okx, ereignis) werden ueber
den PFAD geladen statt ueber sys.path: die Spur startet mit ihrem eigenen
Ordner als sys.path[0]. Ein blankes 'import x' wuerde ein gleichnamiges Modul
falsch aufloesen (Hausmuster wie scanner/handeln.py).
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_HIER = Path(__file__).resolve().parent
_HANDEL = _HIER.parent
_SCANNER = _HANDEL / "scanner"
_BUS = _HANDEL.parent / "Bus"
# ereignis importiert "bus" aus dem Bus-Ordner - der muss auf
# sys.path liegen, sonst scheitert der PFAD-Ladevorgang (wie scanner).
sys.path.insert(0, str(_BUS))

from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec


def _lade(name, datei):
    spec = _rs_spec(name, str(datei))
    modul = _rs_mod(spec)
    spec.loader.exec_module(modul)
    return modul


risikostufe = _lade("risikostufe", _HANDEL / "risikostufe.py")
# wachen_pruefung: Bedingungen 2-5. Dessen sperre_zu() schreibt aber in die
# wachen.json des Marktscanners (scanner/wachen.json, verankert an dessen
# eigenem HIER) - fuer DIESE Spur gibt es deshalb ein eigenes sperre_zu().
wp = _lade("scanner_wachen_pruefung", _SCANNER / "wachen_pruefung.py")
atomar = _lade("atomar", _HANDEL / "atomar.py")
kg = _lade("kill_gemeinsam", _HANDEL / "kill_gemeinsam.py")   # Kill-Frist/Reset/Opt-out
pos_kennung = _lade("pos_kennung", _HANDEL / "pos_kennung.py")
llm = _lade("llm_lokal", _HANDEL / "llm_lokal.py")
okx = _lade("scanner_okx", _SCANNER / "okx.py")
scan = _lade("scanner_llm_scan", _HIER / "scan.py")
ereignis = _lade("ereignis", _BUS / "ereignis.py")

_fw_spec = _rs_spec("freigabefenster", str(_HANDEL / "freigabefenster.py"))
freigabefenster = _rs_mod(_fw_spec)
_fw_spec.loader.exec_module(freigabefenster)

ZUSTAND = risikostufe.datei(_HIER / "zustand.json")
JOURNAL = risikostufe.datei(_HIER / "handelsjournal.csv")

# Spur-Name fuer den Freigabe-Dienst (freigabefenster.py): muss mit dem
# Schluessel in dauerlauf.SPUREN uebereinstimmen (fuegt der Parent hinzu).
SPUR = "scanner_llm"

# 0,05 % OKX Taker (Volumen < 10.000) - Papierlauf ohne Gebuehr waere ein
# Fehler (Handelsregeln.md). Wie scanner/handeln.py.
GEBUEHR_PCT = 0.0005

HERKUNFT = "zyklus"


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def wachen():
    return risikostufe.skaliere(
        json.loads((_HIER / "wachen.json").read_text("utf-8")))


# --- Zustand + Journal -----------------------------------------------------

def lade_zustand():
    z = atomar.lade_json(ZUSTAND, lambda: None)
    if z is not None:
        z.setdefault("letzte_ziele", {})
        return z
    return {"positionen": [], "letzte_stops": {}, "letzte_ziele": {},
            "letzter_lauf": None, "modus": None}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    atomar.schreibe_json(ZUSTAND, z)


def journal(*felder):
    neu = not JOURNAL.exists()
    kopf = None if neu else pos_kennung.kopf(JOURNAL)
    # felder: zeit, modus, aktion, inst, preis, usd, stop, ziel, grund,
    #         mfe_pct, mae_pct, haltetage, pos_id  -> HERKUNFT davor.
    felder_mit_herkunft = list(felder)
    if len(felder_mit_herkunft) >= 13:
        felder_mit_herkunft.insert(-1, HERKUNFT)
    else:
        felder_mit_herkunft.append(HERKUNFT)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        if neu:
            s.writerow(["zeit", "modus", "aktion", "inst", "preis", "usd",
                        "stop", "ziel", "grund", "mfe_pct", "mae_pct",
                        "haltetage", "herkunft", "pos_id"])
        s.writerow(pos_kennung.zeile(felder_mit_herkunft, kopf))


# --- Vorschlaege (Regeltor, KEIN LLM hier) ---------------------------------

def stop_prozent(z, w):
    """Stop-Abstand aus Volatilitaet und Drawdown, hart gedeckelt."""
    vola = z["kennzahlen"]["volatilitaet_pa"]
    roh = 3.0 + 6.0 * min(vola, 1.5)     # ~5 % ruhig, ~12 % wild
    return max(w["pflicht_stop_prozent_min"],
               min(w["pflicht_stop_prozent_max"], round(roh, 1)))


def nominal_fuer(stop_pct, w):
    """Einsatz je Position aus dem Risiko, gedeckelt auf max_pro_trade_usd."""
    deckel = w["max_pro_trade_usd"]
    risiko = w.get("risiko_je_position_usd")
    if not risiko or stop_pct <= 0:
        return deckel
    return round(min(deckel, risiko / (stop_pct / 100.0)), 2)


def marktkurs(inst):
    """Jetzt-Kurs fuer Einstieg/Ausstieg - die EINE Netz-Naht.

    Die Tests biegen diese Funktion um; im Papierzyklus laeuft damit kein
    OKX-Aufruf. Ein nicht abrufbarer Kurs ist eine Ablehnung, kein Abbruch
    (Muster scanner/handeln.py).
    """
    try:
        k = okx.letzter_kurs(inst)
    except Exception as e:  # noqa: BLE001
        print("  Kurs %s nicht abrufbar: %s" % (inst, e), file=sys.stderr)
        return None
    if not k or k <= 0:
        return None
    return k


def vorschlaege(bericht, w):
    """Die Kandidaten hinter den LEICHTEREN Regeltoren dieser Spur.

    Nur die Regel-Tore (score/vola/chance-risiko). Das LLM-Urteil faellt
    danach in llm_sieben() - getrennt, damit der Filter einzeln testbar bleibt.
    """
    aus = []
    for z in bericht["werte"]:
        vola = z["kennzahlen"]["volatilitaet_pa"]
        if z["score"] < w["mindest_score"]:
            continue
        if vola > w["max_volatilitaet_pa"]:
            continue
        if z["verhaeltnis"] < w["mindest_chance_risiko"]:
            continue
        einstieg = marktkurs(z["inst"])
        if einstieg is None:
            continue
        sp = stop_prozent(z, w)
        stop = round(einstieg * (1 - sp / 100.0), 6)
        ziel = round(einstieg + 2.0 * (einstieg - stop), 6)  # C/R 2:1
        aus.append({"inst": z["inst"], "score": z["score"], "einstieg": einstieg,
                    "stop": stop, "stop_pct": sp, "ziel": ziel,
                    "usd": nominal_fuer(sp, w),
                    "chance": z.get("chance"), "risiko": z.get("risiko"),
                    "verhaeltnis": z.get("verhaeltnis"),
                    "kennzahlen": z.get("kennzahlen")})
    return aus


# --- LLM-Qualitaetsfilter --------------------------------------------------

def marktbild(z, w):
    """Der Prompt: Vertrag des Bots (llm.VERTRAG) plus das Marktbild.

    Beschrieben werden Trendrichtung, RSI, Volatilitaet, Regel-Score und
    Chance/Risiko aus der bewertung-Ausgabe. Kommentare sind deutsch, der
    Prompt-Text englisch (wie moondev_sentiment/handeln.py marktbild).
    """
    kz = z.get("kennzahlen") or {}

    def num(key, fmt="{:.2f}", default="?"):
        v = kz.get(key)
        return default if v is None else fmt.format(v)

    return (llm.VERTRAG + """\
Analyze this daily-candle technical setup and decide whether to go LONG.

Instrument: {inst}
Trend (0.0 = price below all SMAs .. 1.0 = above all SMAs): {trend}
RSI(14): {rsi}
Annualized volatility (p.a.): {vola}
Rule score (0-100): {score}
Chance/Risiko ratio: {cr}
30d return (%): {ret}
Distance to 60d high (%): {hoch}

The setup already passed a light rule filter. Your job is QUALITATIVE
confirmation. Only answer BUY if the trend is up and the risk looks
contained. If the picture is mixed, unclear or not confirming, answer
NOTHING. Never answer SELL for a long-only book.
""".format(
        inst=z.get("inst"),
        trend=num("trend_ueber_sma"),
        rsi=num("rsi14", "{:.1f}"),
        vola=num("volatilitaet_pa"),
        score=z.get("score", "?"),
        cr=z.get("verhaeltnis", "?"),
        ret=num("rendite_30t_pct", "{:+.1f}"),
        hoch=num("abstand_60t_hoch_pct", "{:+.1f}")))


# Test-Seam: None -> echtes Modell (llm.entscheide). Kein Test darf das
# echte LLM rufen - Tests setzen diese Funktion.
entscheide_override = None


def richte(z, w):
    """Modell-Urteil zu einem Kandidaten. Gibt (seite, info), wirft nie."""
    if entscheide_override is not None:
        return entscheide_override(marktbild(z, w), w)
    return llm.entscheide(marktbild(z, w), w)


def llm_sieben(vs, w):
    """Nur Kandidaten mit Urteil 'long' UND confidence >= Schwelle handelbar.

    NOTHING/SELL/zu unsicher wird geloggt (llm.zeile) und uebersprungen -
    kein Urteil heisst kein Handel. llm.entscheide wendet die Schwelle schon
    selbst an, hier wird sie zusaetzlich geprueft, damit der Filter auch bei
    einem Test-Stub eindeutig bleibt. Alle Listenfelder duerfen None sein.
    """
    schwelle = float(w.get("llm_mindest_confidence", 65.0))
    handelbar = []
    for v in vs or []:
        seite, info = richte(v, w)
        v["llm"] = info or {}
        zeile = llm.zeile(info) if info else "-"
        conf = (info or {}).get("confidence")
        if conf is None and seite == "long":
            # entscheide liefert bei fehlender Confidence keinen seite-Wert;
            # hier ist nur der Test-Stub der Fall.
            conf = None
        if seite == "long" and conf is not None and conf >= schwelle:
            print("  LLM HANDELBAR   %-10s (Conf %.0f%%): %s"
                  % (v["inst"], conf, zeile))
            handelbar.append(v)
        else:
            grund = ("kein long" if seite != "long"
                     else "Conf unter %g%s" % (schwelle,
                                               "" if conf is None
                                               else " (%.0f)" % conf))
            v["llm_grund"] = grund
            print("  LLM uebersprungen %-10s: %s <- %s"
                  % (v["inst"], zeile, grund))
    return handelbar


# --- Ausstieg / Einstieg ---------------------------------------------------

def _haltetage(p):
    try:
        return (date.fromisoformat(_heute())
                - date.fromisoformat(p["eroeffnet"])).days
    except (KeyError, TypeError, ValueError):
        return ""


def _merke_extrem(p, kurs):
    bewegung = (kurs - p["einstieg"]) / p["einstieg"] * 100.0
    p["mfe_pct"] = max(p.get("mfe_pct", 0.0), bewegung)
    p["mae_pct"] = min(p.get("mae_pct", 0.0), bewegung)


def pruefe_ausstiege(z, live):
    behalten = []
    z["positionen"] = z.get("positionen") or []
    for p in z["positionen"]:
        kurs = marktkurs(p["inst"])
        if kurs is None:
            behalten.append(p)
            continue
        _merke_extrem(p, kurs)
        grund = None
        if kurs <= p["stop"]:
            grund = "stop"
        elif kurs >= p["ziel"]:
            grund = "ziel"
        if not grund:
            behalten.append(p)
            continue
        erloes = p["usd"] * kurs / p["einstieg"] * (1 - GEBUEHR_PCT)
        gv = erloes - p["usd"]
        if live and p.get("kauf_ord_id"):
            try:
                okx.markt_verkauf(p["inst"], p["usd"] / p["einstieg"])
            except Exception as e:  # noqa: BLE001
                print("  Verkauf %s fehlgeschlagen: %s" % (p["inst"], e),
                      file=sys.stderr)
                behalten.append(p)
                continue
        print("  AUSSTIEG (%s): %s @ %.6f  G/V %+.2f USD"
              % (grund, p["inst"], kurs, gv))
        journal(_jetzt(), "live" if live else "papier", "verkauf", p["inst"],
                "%.6f" % kurs, "%.2f" % erloes, "", "", grund,
                "%.4f" % p.get("mfe_pct", 0.0), "%.4f" % p.get("mae_pct", 0.0),
                _haltetage(p), p.get("pos_id", ""))
        if grund.startswith("stop"):
            z["letzte_stops"][p["inst"]] = _heute()
        elif grund == "ziel":
            z.setdefault("letzte_ziele", {})[p["inst"]] = _jetzt()
    z["positionen"] = behalten


def _live_einstieg(v, usd):
    """Echte OKX-Order fuer einen Einstieg. Nur bei live=True erreichbar."""
    kauf_id = okx.markt_kauf(v["inst"], usd)
    menge = 0.0
    try:
        d = okx.order_details(v["inst"], kauf_id)
        menge = float(d.get("accFillSz") or 0)
    except Exception:  # noqa: BLE001
        pass
    stop_id = None
    if menge > 0:
        try:
            stop_id = okx.stop_setzen(v["inst"], round(menge, 8), v["stop"])
        except Exception:  # noqa: BLE001
            pass
    return kauf_id, stop_id, menge <= 0


def pruefe_einstiege(z, vs, w, live, faktor=1.0):
    z["positionen"] = z.get("positionen") or []
    gehalten = {p["inst"] for p in z["positionen"]}
    eingesetzt = sum(p["usd"] for p in z["positionen"])
    for v in vs or []:
        if len(z["positionen"]) >= w["max_offene_positionen"]:
            print("  Buch voll (%d) - Rest nicht angesehen"
                  % w["max_offene_positionen"])
            break
        usd = round(v["usd"] * faktor, 2)
        if eingesetzt + usd > w["max_gesamt_usd"]:
            print("  Gesamtdeckel %g USD erreicht - %s nicht gekauft"
                  % (w["max_gesamt_usd"], v["inst"]))
            continue
        if v["inst"] in gehalten:
            print("  %s schon im Buch" % v["inst"])
            continue
        kauf_id = stop_id = None
        stop_fehlt = False
        if live:
            try:
                kauf_id, stop_id, stop_fehlt = _live_einstieg(v, usd)
            except Exception as e:  # noqa: BLE001
                print("  Kauf %s fehlgeschlagen: %s" % (v["inst"], e),
                      file=sys.stderr)
                continue
        _pos = {
            "inst": v["inst"], "einstieg": v["einstieg"], "usd": usd,
            "stop": v["stop"], "ziel": v["ziel"], "stop_pct": v["stop_pct"],
            "eroeffnet": _heute(), "kauf_ord_id": kauf_id,
            "stop_ord_id": stop_id, "boersen_stop_fehlt": stop_fehlt,
            "mfe_pct": 0.0, "mae_pct": 0.0,
            "pos_id": pos_kennung.neu(_jetzt()),
        }
        z["positionen"].append(_pos)
        eingesetzt += usd
        gehalten.add(v["inst"])
        print("  AUF %-10s @ %.6f  Stop %.6f (-%.1f%%)  Ziel %.6f  %.2f USD"
              % (v["inst"], v["einstieg"], v["stop"], v["stop_pct"],
                 v["ziel"], usd))
        journal(_jetzt(), "live" if live else "papier", "kauf", v["inst"],
                "%.6f" % v["einstieg"], "%.2f" % (usd * (1 + GEBUEHR_PCT)),
                "%.6f" % v["stop"], "%.6f" % v["ziel"],
                "score %.1f" % v["score"],
                "", "", "", _pos["pos_id"])


def kill_verkauf_ohne_freigabe(w):
    """Darf der KILL echte Live-Positionen auch bei geschlossener Freigabekette
    verkaufen? Nur mit ausdruecklichem Schalter, Basisstufe und gesetztem
    Schluessel (Muster xperp/spur_buch, Auftrag Max 14.10.2026)."""
    return bool(w.get("kill_verkauf_ohne_freigabekette")
                and risikostufe.live_erlaubt() and okx.schluessel_vorhanden())


def flach_stellen(z, live, grund, notaus_live=False):
    """Alle Positionen zum Marktkurs schliessen und buchen.

    Eine Live-Position (kauf_ord_id) gehoert der Boerse: sie wird nur echt
    verkauft, wenn `live` oder `notaus_live` gilt. Sonst bleibt sie im Buch -
    ein Papierlauf darf sie nicht mit einer Papier-Zeile ausbuchen, an der
    Boerse bliebe sie offen (Fall mosaic 23.09.2026). Papier-Positionen werden
    immer gebucht; ohne Kurs bleibt jede Position stehen.
    Rueckgabe: Zahl der im Buch verbliebenen Positionen.
    """
    behalten = []
    z["positionen"] = z.get("positionen") or []
    for p in z["positionen"]:
        echt = bool(p.get("kauf_ord_id"))
        if echt and not (live or notaus_live):
            print("  %s: Live-Position bleibt (kein Live-Lauf, kein Notausstieg)"
                  % p["inst"])
            behalten.append(p)
            continue
        kurs = marktkurs(p["inst"])
        if kurs is None:
            behalten.append(p)
            continue
        _merke_extrem(p, kurs)
        erloes = p["usd"] * kurs / p["einstieg"] * (1 - GEBUEHR_PCT)
        if echt:
            try:
                okx.markt_verkauf(p["inst"], p["usd"] / p["einstieg"])
            except Exception as e:  # noqa: BLE001
                print("  Verkauf %s fehlgeschlagen: %s" % (p["inst"], e),
                      file=sys.stderr)
                behalten.append(p)
                continue
        print("  AUSSTIEG (%s): %s @ %.6f  G/V %+.2f USD"
              % (grund, p["inst"], kurs, erloes - p["usd"]))
        journal(_jetzt(), "live" if echt else "papier", "verkauf", p["inst"],
                "%.6f" % kurs, "%.2f" % erloes, "", "", grund,
                "%.4f" % p.get("mfe_pct", 0.0), "%.4f" % p.get("mae_pct", 0.0),
                _haltetage(p), p.get("pos_id", ""))
    z["positionen"] = behalten
    return len(behalten)


# --- Freigabe von Hand (Handelsregeln Punkt 3) -----------------------------

FREIGABE_ZEITLIMIT_S = 600


def sitzung_da():
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


def zeitfenster_offen():
    try:
        return bool(freigabefenster.lade(SPUR).offen())
    except Exception as e:  # noqa: BLE001
        print("  Zeitfenster nicht lesbar (%s: %s) - gilt als zu."
              % (type(e).__name__, e), file=sys.stderr)
        return False


def sperren_live(w, s):
    """Alles, was --live gerade verschliesst. Leere Liste = frei.

    Der Fenster-Grund traegt als EINZIGER das Wort 'Freigabefenster' -
    dauerlauf.nur_fenster_fehlt prueft genau darauf und fragt am Handy nach,
    wenn nur noch dieses eine fehlt.
    """
    g = []
    if not risikostufe.live_erlaubt():
        g.append("Risikostufe %s: kein Live-Pfad in einer Stufe"
                 % risikostufe.stufe())
    if not w.get("handel_erlaubt"):
        g.append("wachen.json handel_erlaubt=false")
    if not okx.schluessel_vorhanden():
        g.append("OKX-Schluessel nicht gesetzt")
    if not s["freigabe_erfuellt"]:
        g.append("freigabe.erfuellt=false (Bedingung 1)")
    if not s["herzschlag_frisch"]:
        g.append("Herzschlag alt (Bedingung 3)")
    if s["ev_negativ"]:
        g.append("rollierender EV %.3f USD < 0 (Bedingung 5)"
                 % s["rollierender_ev"])
    # Punkt 3: Bildschirmfenster ODER Zeitfenster. Eine muss offen sein.
    if not sitzung_da() and not zeitfenster_offen():
        g.append("Freigabefenster nicht offen - keine Sitzung am "
                 "Bildschirm und kein Zeitfenster (Handelsregeln Punkt 3)")
    return g


def sperre_zu(grund):
    """handel_erlaubt dieser Spur von true auf false. Nur diese Richtung.

    Eigene Fassung statt wp.sperre_zu: jenes Modul schreibt in die wachen.json
    des Marktscanners. Dieses liest/schreibt die EIGENE wachen.json.
    """
    p = _HIER / "wachen.json"
    w = json.loads(p.read_text("utf-8"))
    if not w.get("handel_erlaubt"):
        return False
    w["handel_erlaubt"] = False
    w["_sperre_zu_ausgeloest"] = {"zeit": _jetzt(), "grund": grund}
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(w, f, ensure_ascii=False, indent=2)
    return True


# --- Wachen-Status (Bedingungen 2-5) ---------------------------------------

def _spiegeln(w):
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))


def zeige_wachen(w):
    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)
    print("=== Wachen-Status  %s ===" % _jetzt())
    print("  1 Freigabe erfuellt      %s   (Handelsrunden %d)" % (
        s["freigabe_erfuellt"], s["runden_echt"]))
    print("  2 Ruecklauf              %.2f USD von Hoechststand %.2f  -> Faktor %.2f%s"
          % (s["ruecklauf_usd"], s["hoechststand_usd"], s["groessenfaktor"],
             "   >>> KILL-SWITCH" if s["kill"] else ""))
    print("  3 Herzschlag frisch     %s"
          % s["herzschlag_frisch"])
    if s["herzschlag_alter_min"] is not None:
        print("                           (%d min alt, Grenze %d)"
              % (s["herzschlag_alter_min"], w.get("herzschlag_max_minuten", 30)))
    print("  4 Journal-Zweitziel     %s"
          % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  5 Rollierender EV       %s%s"
          % ("n/a (zu wenig Runden)" if s["rollierender_ev"] is None
             else "%+.3f USD/Runde" % s["rollierender_ev"],
             "   >>> NEGATIV" if s["ev_negativ"] else ""))
    print()
    _spiegeln(w)


# --- Hauptlauf -------------------------------------------------------------

def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = wachen()

    # Bedingung 4 an der ERSTEN Stelle des Zyklus (Hausmuster: auch fruehe
    # Ausgaenge ziehen die Kopie des letzten Standes nach Q: nach).
    if w.get("journal_zweitziel"):
        _spiegeln(w)

    if modus == "wachen":
        zeige_wachen(w)
        return

    z = lade_zustand()
    if modus == "status":
        print("scanner_llm: %d offene Positionen, %d USD gebunden, "
              "handel_erlaubt=%s"
              % (len(z["positionen"] or []),
                 sum(p["usd"] for p in z["positionen"] or []),
                 w.get("handel_erlaubt")))
        return

    bpfad = scan.BERICHTE / "neuester.json"
    if not bpfad.exists():
        print("Kein Bericht. Erst scan.py laufen lassen.")
        return
    bericht = json.loads(bpfad.read_text("utf-8"))

    s = wp.lage(w, JOURNAL, z)

    live = False
    if modus == "live":
        gruende = sperren_live(w, s)
        if gruende:
            print("--live angefordert, aber gesperrt: " + "; ".join(gruende))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    vs = vorschlaege(bericht, w)
    handelbar = llm_sieben(vs, w) if vs else []
    print("=== Handeln (%s) | Bericht %s | %d Kandidaten, %d LLM-handelbar ==="
          % ("LIVE" if live else "Papier", bericht["datum"], len(vs),
             len(handelbar)))

    z["modus"] = "live" if live else "papier"

    if modus == "vorschau":
        for v in handelbar:
            print("  %-10s Score %.1f  Einstieg %.6f  Stop %.6f (-%.1f%%)  "
                  "Ziel %.6f"
                  % (v["inst"], v["score"], v["einstieg"], v["stop"],
                     v["stop_pct"], v["ziel"]))
        eing = sum(p["usd"] for p in z["positionen"] or [])
        print("\nOffener Bestand: %d Positionen, %d USD gebunden"
              % (len(z["positionen"] or []), eing))
        # IMMER die Sperrgruende nennen - dauerlauf.nur_fenster_fehlt liest
        # genau diese Zeile und fragt nur, wenn GENAU das Freigabefenster
        # fehlt (Hausmuster, auch hier).
        g = sperren_live(w, s)
        print("Live waere gesperrt durch: " + ("; ".join(g) or "nichts"))
        if w.get("journal_zweitziel"):
            _spiegeln(w)
        return

    if s["kill"]:
        status, _rueck = kg.phase(z, w, s["ruecklauf_usd"],
                                  s.get("runden_gesamt", 0), _jetzt)
        if status == "frei":
            s = wp.lage(w, JOURNAL, z)          # Ruecklauf beginnt bei 0
        else:
            flach_stellen(z, live, kg.KILL_GRUND,
                          notaus_live=kill_verkauf_ohne_freigabe(w))
            if sperre_zu("kill_switch: Ruecklauf %.2f USD" % s["ruecklauf_usd"]):
                print("  wachen.json handel_erlaubt -> false")
            schreibe_zustand(z)
            if w.get("journal_zweitziel"):
                _spiegeln(w)
            return

    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel "
              "dieser Lauf -"
              % ("?" if s["herzschlag_alter_min"] is None
                 else "%.0f" % s["herzschlag_alter_min"],
                 w.get("herzschlag_max_minuten", 30)))
        flach_stellen(z, live, "herzschlag_alt")
        z["modus"] = "papier"
        schreibe_zustand(z)
        if w.get("journal_zweitziel"):
            _spiegeln(w)
        return

    print("- Ausstiege -")
    pruefe_ausstiege(z, live)

    print("- Einstiege -")
    pruefe_einstiege(z, handelbar, w, live, s["groessenfaktor"])

    eing = sum(p["usd"] for p in z["positionen"] or [])
    print("\nStand: %d/%d Positionen, %d/%d USD gebunden"
          % (len(z["positionen"] or []), w["max_offene_positionen"],
             eing, w["max_gesamt_usd"]))
    schreibe_zustand(z)

    if w.get("journal_zweitziel"):
        _spiegeln(w)


def main():
    with ereignis.lauf("handel/scanner_llm"):
        return _main()


def _main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau", help="nur zeigen")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier", help="Papierhandel (Standard)")
    g.add_argument("--live", action="store_const", dest="modus",
                   const="live", help="echte Orders, wenn alle Sperren offen")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen", help="Bedingungen 2-5 zeigen (Wochenlauf)")
    g.add_argument("--status", action="store_const", dest="modus",
                   const="status", help="Kurzstatus")
    a = p.parse_args()
    return lauf(a.modus or "papier")


if __name__ == "__main__":
    main()
