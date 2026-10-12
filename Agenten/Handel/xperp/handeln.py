"""Der Live-Pfad der zweiten Spur: Ausstiege, Einstiege, Journal, Zustand.

Angelegt am 03.09.2026 auf Max' Anweisung, XPERP auf OKX zum Hauptweg zu
machen. Schliesst T-019: Bis hierher legte bot.py nur vor - kein Journal,
kein Zustand, kein Herzschlag -, und damit hatten die Bedingungen 2/3/5 aus
Wissen/Handelsregeln.md nichts, woran sie greifen konnten. Die Regel lief der
Umsetzung voraus.

Vorbild ist scanner/handeln.py, Zeile fuer Zeile derselbe Ablauf. Gerechnet
wird aber nicht hier: Stop-Abstand, Positionsgroesse, Hebel-Deckel,
Liquidationspreis und die vier Pflichtzahlen stehen in bot.py und werden von
dort geholt. Zwei Fassungen derselben Rechnung waeren die sicherste Art, sie
auseinanderlaufen zu lassen.

VIER DINGE SIND ANDERS ALS BEI SPOT
-----------------------------------
1. **Long und Short.** Jede Prueferei auf "Kurs unter Stop" hat eine zweite
   Haelfte. Die Richtung steht in der Position und im Journal.

2. **Margin statt Einsatz.** Der Rahmen begrenzt den Einschuss, der
   Positionswert liegt beim Hebelfachen. Wer Nominal gegen den Rahmen
   prueft, sperrt bei einem Fuenftel des erlaubten Risikos.

3. **Liquidation ist ein dritter Ausstiegsgrund** - und der einzige, den
   nicht wir setzen, sondern die Boerse. Der Pflicht-Stop liegt immer davor;
   trifft trotzdem zuerst die Liquidation, ist das ein Befund und wird als
   solcher ins Journal geschrieben.

4. **Funding laeuft, auch wenn nichts passiert.** Alle 8 Stunden, als eigene
   Journalzeile. Ein Papierlauf ohne Funding empfiehlt eine Strategie, die
   live verliert - dieselbe Falle wie die Gebuehr bei Spur 3.

DIE VIER PFLICHTZAHLEN STEHEN IM JOURNAL
----------------------------------------
Handelsregeln, Abschnitt Pruefpflicht: Auf dem automatischen Weg liest
niemand mit, deshalb gehoeren Liquidationsabstand, Funding, Gebuehren und
Trefferquote je Position abgelegt. Woertlich dort: "Eine Zahl, die der
Automat nicht ablegt, ist nicht gerechnet worden; eine Position ohne diese
vier Werte im Journal ist ein Befund, kein Trade."

Aufruf:
    python handeln.py --vorschau    # was waere dran, ohne etwas zu tun
    python handeln.py --papier      # Papierlauf mit Journal
    python handeln.py --live        # scharf, wenn alle Sperren offen sind
    python handeln.py --wachen      # Bedingungen 1-5 als Momentaufnahme
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
sys.path.insert(0, os.path.join(HIER, os.pardir))
sys.path.insert(0, os.path.join(HIER, os.pardir, os.pardir, "Bus"))
import ereignis                                            # noqa: E402
# pos_kennung liegt im Handel-Ordner. Der eigene Spurenordner ist beim
# Start sys.path[0], darum wird der Ordner ANGEHAENGT (nicht vorne
# eingefuegt - ein Eintrag vorne koennte ein gleichnamiges Spurenmodul
# verdecken, siehe Handel/grid.py neben gitter/grid.py).
_handel_ordner = os.path.dirname(          # Handel/, nicht der Spurenordner
    os.path.dirname(os.path.abspath(__file__)))
if _handel_ordner not in sys.path:
    sys.path.append(_handel_ordner)
# signal_wechsel liegt ebenfalls im Handel-Ordner - darum NACH dem
# sys.path-Eintrag, nicht bei den uebrigen Standardimporten oben. Dort
# wuerde der Import mit ModuleNotFoundError abbrechen, weil der eigene
# Spurenordner beim Start sys.path[0] ist.
from signal_wechsel import ERLAEUT, zugelassen  # noqa: E402
import mae
import pos_kennung                                          # noqa: E402
import tracking as _tracking

import auswahl
import bot
import indikatoren
import okxf
import wachen_xperp as wx
# Der Trailing-Stop rechnet in EINER Datei fuer alle Spuren (Handel/trailing.py,
# 05.10.2026). Sie ist reines Rechnen - kein Netzzugriff, keine Order -
# damit ist sie ohne Attrappe testbar. Der Boersen-Aufruf bleibt bei okxf.
import trailing as trailing_modul

# Stop-DECKUNG (T-362): `stopdeckung` importierte `handeln`, und `handeln`
# ruft jetzt dessen `deckung()` im Zyklus auf - ein Zirkel. Der Import von
# `handeln` in `stopdeckung` ist deshalb auf `main()` verschoben (siehe dort
# `_lade()`); hier wird nur das Werkzeug geladen, und das braucht nur `okxf`.
import stopdeckung
import llm_filter

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

ZUSTAND = risikostufe.datei(os.path.join(HIER, "zustand.json"))
JOURNAL = risikostufe.datei(os.path.join(HIER, "handelsjournal.csv"))

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "familie", "preis",
           "kontrakte", "nominal_usd", "margin_usd", "hebel", "stop", "ziel",
           "liq", "liq_abstand", "funding_pct", "gebuehr_pct",
           "quote_noetig", "quote_beob", "grund",
           "pos_id",
           # MFE/MAE seit 03.10.2026 (T-119) - xperp ist die einzige Spur
           # mit echten Positionsgroessen an der Boerse.
           "mfe_pct", "mae_pct", "haltetage"]

# Wie oft der Kandidatenscan die Rangliste neu rechnet. Ein voller Lauf ueber
# 164 Kontrakte dauert rund zwei Minuten - bei einem 15-Minuten-Takt waere
# das ein Achtel der Zeit fuer eine Liste, die sich in 4H-Kerzen bewegt.
SCAN_ALTER_MINUTEN = 120


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


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
    return atomar.lade_json(ZUSTAND, lambda: {"positionen": [], "letzte_stops": {}, "letzter_lauf": None,
                "modus": "papier", "rangliste": None})


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    atomar.schreibe_json(ZUSTAND, z)


def journal(**felder):
    neu = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=SPALTEN, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in SPALTEN})


# --- Vorschlaege ------------------------------------------------------------

def rangliste(z, still=True):
    """Die Rangliste, hoechstens SCAN_ALTER_MINUTEN alt.

    Sie wird im Zustand zwischengelagert, weil ein voller Scan zwei Minuten
    kostet. Das ist kein Trick, sondern die Taktung: Das Signal steht auf
    4H-Kerzen, es aendert sich nicht alle 15 Minuten.
    """
    alt = (z.get("rangliste") or {}).get("zeit")
    if alt:
        vergangen = (datetime.now(timezone.utc)
                     - datetime.fromisoformat(alt)).total_seconds() / 60
        if vergangen < SCAN_ALTER_MINUTEN:
            return z["rangliste"]["werte"], vergangen

    d = auswahl.sammle(still=still)
    schlank = [{
        "basis": x["basis"], "instId": x["instId"],
        "kategorie": x.get("kategorie", "krypto"),
        "punkte": x["punkte"], "vola": x["vola"],
        "vola_tor": x.get("vola_tor", 1.20),
        "umsatz": x["umsatz"], "ruhe": x.get("ruhe", 0),
        "mae_long": x["mae_long"], "mae_short": x["mae_short"],
    } for x in d]
    z["rangliste"] = {"zeit": _jetzt(), "werte": schlank}
    return schlank, 0.0


def kandidaten(werte, w, anzahl=6):
    """Die besten Werte je Richtung, die ihre Tore bestehen.

    Eine Rangliste ist ein Vorschlag, keine Anweisung - so steht es im Kopf
    von bot.py. Was sie hier verbindlich macht, ist nicht die Rangfolge,
    sondern wachen.json: Der Automat darf aus ihr eroeffnen, weil die Datei
    den Rahmen setzt. Genau diese Unterscheidung trifft Handelsregeln,
    Spur 2: "bot.py darf aus einer Rangliste heraus eroeffnen, eine
    Chat-Antwort nicht."
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
            if deckel < wx.hebel_mindest(w, x["kategorie"]):
                continue
            aus.append({"basis": x["basis"], "instId": x["instId"],
                        "seite": seite, "kategorie": x["kategorie"],
                        "punkte": x["punkte"][seite], "deckel": deckel})
    return aus


def anlauf(w, kandidat):
    """Ein vollstaendiger Vorschlag samt Pflichtzahlen - oder None.

    Das Signal kommt vom gehandelten Kontrakt selbst, nicht aus der
    Rangliste: Die Rangliste sagt, welcher Wert taugt, indikatoren.lage()
    sagt, ob er jetzt in die gewuenschte Richtung zeigt. Widersprechen sie
    sich, wird nichts eroeffnet - der Bot erfindet kein Signal.
    """
    instr = okxf.instrument(kandidat["basis"])
    if not instr:
        return None
    k = okxf.kerzen(instr["instId"], bot.BAR, 300)
    if len(k) < 60:
        return None

    lage = indikatoren.lage(k, inst=instr["instId"])
    if lage["signal"] != kandidat["seite"]:
        return None

    seite = kandidat["seite"]
    vz = 1 if seite == "long" else -1
    atr = lage["atr"]
    if not atr:
        return None

    einstieg = okxf.auf_tick(instr, lage["kurs"]
                             - vz * w["einstieg_atr_abschlag"] * atr)
    stop = okxf.auf_tick(instr, einstieg - vz * w["stop_atr_faktor"] * atr)
    ziel = okxf.auf_tick(instr, einstieg + vz * w["ziel_atr_faktor"] * atr)

    # Hebel und Stopweite je Familie (Auftrag Max 08.10.2026: Rohstoffe 10x,
    # Stop hoechstens 4 %). Fehlt der Familien-Wert, gilt max_hebel unveraendert.
    smax = wx.stop_max_pct(w, kandidat["kategorie"])
    if smax is not None and abs(einstieg - stop) / einstieg * 100.0 > smax:
        return None
    wf = wx.fuer_familie(w, kandidat["kategorie"])

    g = bot.groesse(wf, instr, einstieg, stop, seite, kandidat["deckel"])
    if not g:
        return None

    p = bot.pruefpflicht(wf, instr, k, seite, einstieg, stop, ziel,
                         g["hebel"], still=True)
    return {"instr": instr, "inst": instr["instId"], "basis": kandidat["basis"],
            "seite": seite, "kategorie": kandidat["kategorie"],
            "einstieg": einstieg, "stop": stop, "ziel": ziel,
            "groesse": g, "pflicht": p, "punkte": kandidat["punkte"],
            "grund": lage["grund"]}


# --- Ausstieg ---------------------------------------------------------------

def _kurs(inst):
    return float(okxf.letzter_kurs(inst))


def _kurs_aktuell(p):
    """Kurs der Position, mit Rollover-Umstellung des Kontrakts.

    XPERP-Kontrakte wechseln ihren instId (OKX legt den Kontrakt neu auf,
    der alte antwortet mit 51001). Ohne die Umstellung bliebe eine offene
    Position auf dem alten Kontrakt ewig ohne Kurs: Stop und Ziel wuerden
    nie geprueft. Ein Wechsel wird gedruckt und als eigene Journalzeile
    (aktion=rollover) gebucht - er ist kein Trade, zaehlt also in keiner
    Runden-Rechnung.
    """
    inst, kurs = okxf.letzter_kurs_mit_fallback(p["inst"], p.get("basis"))
    if inst != p["inst"]:
        alt = p["inst"]
        p["inst"] = inst
        print("  ROLLOVER: %s -> %s (%s), Kontrakt des Basiswerts gewechselt"
              % (alt, inst, p.get("basis")))
        journal(zeit=_jetzt(), modus="papier", aktion="rollover",
                inst=inst, seite=p.get("seite", ""),
                familie=p.get("familie", ""),
                grund="Kontrakt gewechselt: " + alt)
    return float(kurs)


def _hand_erloes(p, preis, menge):
    """(nominal, erloes) einer von Hand verkauften Menge, beides in USD.

    DER FEHLER, DER HIER BEHOBEN IST (gemessen 07.10.2026): die Buchung rechnete
    `preis * menge` und schrieb das in nominal_usd UND margin_usd. Das ist weder
    das eine noch das andere: es fehlen die Kontraktgroesse (ctVal) und der
    Hebel. XAU, 96 Kontrakte @ 4150,2 stand mit 398.419 statt rund 80 USD
    Margin im Journal; die Auswertung meldete damit +438.540 USD und die Spur
    als "belastbar".

    Die Konvention ist die von `_ergebnis` und der schliessen-Zeile sonst:
    margin_usd ist, was von der Margin ZURUECKKOMMT (Einsatz plus Ergebnis),
    nominal_usd das Nominal der Position. Beides aus dem BUCH, nicht aus der
    Boerse - ctVal und Hebel stecken schon im Nominal der Position, ein
    Netzabruf waere eine zweite Quelle. Bei einem Teilverkauf zaehlt nur der
    verkaufte Anteil. Gebuehr ist nicht abgezogen (sie steht an der Boerse;
    gebuehr_pct bleibt leer, wie bei den uebrigen Handschliessungen).

    Ohne Zeugen kommt preis = Einstieg an: Ergebnis 0, die Margin geht zurueck.
    """
    alt = abs(float(p.get("kontrakte") or 0.0))
    anteil = min(1.0, abs(menge) / alt) if alt > 0 else 1.0
    nominal = float(p.get("nominal") or 0.0) * anteil
    margin = float(p.get("margin") or 0.0) * anteil
    einstieg = float(p.get("einstieg") or p.get("preis") or 0.0)
    if not einstieg:
        return nominal, margin                     # ohne Einstieg kein Ergebnis
    vz = 1 if p.get("seite") == "long" else -1
    return nominal, margin + nominal * vz * (preis - einstieg) / einstieg


def _ergebnis(p, kurs):
    """Was von der Margin zurueckkommt. Gebuehr beim Schliessen abgezogen."""
    vz = 1 if p["seite"] == "long" else -1
    bewegung = vz * (kurs - p["einstieg"]) / p["einstieg"]
    gewinn = p["nominal"] * bewegung
    gebuehr = p["nominal"] * p.get("gebuehr_taker", 0.0005)
    return p["margin"] + gewinn - gebuehr


def bueche_papier_altlasten_aus(z, w, still=False):
    """Positionen OHNE Live-Herkunft aus dem Live-Buch buchen.

    ANLASS (gemessen 21.09.2026): xperp lief live, sein Buch fuehrte aber vier
    Positionen (ZEC, XAG, LINK, ETC), die an der Boerse NICHT existieren - die
    Abfrage /account/positions kennt nur zwei (die manuelle FIL-Position und
    einen XRP-Rest). Das Journal beweist es: von 14 Live-Zeilen sind ALLE 14
    `funding`, kein einziger Live-Kauf und kein Live-Verkauf. Die vier
    Positionen stammen also aus dem Papierlauf, der Buchmodus stand trotzdem auf
    `live`. Folge ohne diesen Schritt: die Live-Ausstiege versuchen, Kontrakte zu
    verkaufen, die es nicht gibt, und die Funding-Zeilen rechnen Gebuehren fuer
    Positionen, die niemand haelt.

    MASSSTAB ist das Feld `modus` der Position: `live` heisst, sie wurde unter
    `--live` eroeffnet. Aeltere Positionen tragen das Feld nicht - sie sind
    Papier. Dieselbe Rechnung wie scanner/handeln.bueche_papier_altlasten_aus.
    """
    alt = [p for p in z["positionen"] if p.get("modus") != "live"]
    if not alt:
        return 0
    behalten = []
    for p in z["positionen"]:
        if p.get("modus") == "live":
            behalten.append(p)
            continue
        kurs = p.get("letzter_kurs") or p.get("einstieg") or 0.0
        erloes = _ergebnis(p, kurs) if kurs else p.get("margin", 0.0)
        gv = erloes - p.get("margin", 0.0)
        if not still:
            print("  Buchbereinigung: %s %s (Papier, keine Order an der Boerse) "
                  "@ %.6f  G/V %+.2f USD" % (p.get("inst"), p.get("seite"),
                                             kurs, gv))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                inst=p.get("inst", ""),
                pos_id=p.get("pos_id", ""), seite=p.get("seite", ""),
                familie=p.get("familie", ""), preis="%.6f" % kurs,
                kontrakte=p.get("kontrakte", ""),
                nominal_usd="%.2f" % p.get("nominal", 0.0),
                margin_usd="%.2f" % erloes, hebel=p.get("hebel", ""),
                **mae.felder(p),
                grund="buchbereinigung")
    z["positionen"] = behalten
    return len(alt)


def _warten_auf_fuellung(inst, ord_id, kontrakte, versuche=4, warte=2.0):
    """Wie viel dieser Order ist wirklich gehandelt? None = unbekannt.

    ANLASS (21.09.2026, nachgemessen): order_limit() gibt die ordId zurueck,
    sobald die Boerse die Order ANGENOMMEN hat. xperp buchte danach sofort
    eine Position. Bei HBAR-USD_UM_XPERP-310815 stand so eine Position im Buch
    (Einstieg 0.08956), waehrend an der Boerse eine OFFENE, nie gefuellte
    Order lag - accFillSz = 0, state = live, /account/positions kennt das
    Instrument nicht. Folge: die Spur zaehlt einen Platz als belegt, der
    Ausstieg wuerde ins Leere verkaufen, und die Bilanz zeigt eine Position,
    die es nicht gibt.

    Ein Limit kann in Sekundenbruchteilen fuellen, deshalb wird kurz gewartet -
    aber nicht blind gebucht.
    """
    import time as _time
    for i in range(versuche):
        stand = okxf.gefuellte_kontrakte(inst, ord_id)
        if stand is not None and stand > 0:
            return stand
        if i < versuche - 1:
            _time.sleep(warte)
    return 0.0


def wartende_auftraege(z, live, w, still=False):
    """Wartende Limit-Auftraege pflegen: fuellen -> buchen, sonst liegen lassen.

    ANLASS (gemessen 21.09.2026, xperp): Die Spur setzt ihren Einstieg aus der
    eigenen Zonenrechnung - ein Kauflimit UNTER dem Markt (CRCL: Order 93.81/
    93.63/94.46 bei Markt 94.84). Das ist keine kaputte Order, sondern eine
    WARTENDE: sie fillt, wenn der Kurs zurueckkommt. Die Fuellungspruefung vom
    selben Tag hat sie aber nach 8 s storniert und als `order_nicht_gefuellt`
    ins Journal geschrieben - drei Mal an einem Abend, jedes Mal mit demselben
    Ergebnis. Beides zusammen ergibt eine Schleife.

    Die Trennung ist deshalb: ein Limit, das fillen KANN (Kauf ab dem Ask,
    Verkauf bis zum Bid), muss auch fuellen - sonst ist es ein Fehler und wird
    storniert. Ein Limit, das NICHT fillen kann, bleibt liegen und wird hier
    verwaltet: fuellt es spaeter, wird die Position gebucht (Stop und Ziel
    haengen als attachAlgoOrds an der Order und werden beim Fuellen aktiv);
    stirbt es, wird es vergessen.
    """
    wartend = z.get("wartende") or []
    if not wartend:
        return 0
    behalten, gebucht = [], 0
    for a in wartend:
        stand = okxf.order_stand(a["inst"], a["ord_id"]) if a.get("ord_id") else {}
        zustand = (stand or {}).get("state") or ""
        if zustand == "filled":
            try:
                kontrakte = float(stand.get("accFillSz") or a.get("kontrakte") or 0)
            except (TypeError, ValueError):
                kontrakte = float(a.get("kontrakte") or 0)
            fuell_zeit = _iso_aus_ms(stand.get("uTime")) or _jetzt()
            pos = {
                "inst": a["inst"], "basis": a.get("basis", ""),
                "seite": a.get("seite", "long"), "familie": a.get("familie", ""),
                "einstieg": float(stand.get("avgPx") or a.get("einstieg") or 0),
                "stop": a.get("stop"), "ziel": a.get("ziel"),
                "liq": a.get("liq"), "kontrakte": kontrakte,
                "nominal": a.get("nominal", 0.0), "margin": a.get("margin", 0.0),
                "hebel": a.get("hebel", 0.0), "gebuehr_taker": a.get("gebuehr_taker"),
                "modus": "live", "ord_id": a["ord_id"],
                "pos_id": pos_kennung.neu(_jetzt()),
                # EROEFFNET wird mit der FUELLUNG der Order gebucht, nicht mit
                # dem Moment des Abarbeitens (T-277, 01.10.2026): eine ueber
                # Nacht gefuellte Order stand danach mit "jetzt" im Buch - die
                # Haltedauer war zu kurz, und die Geisterpruefung fand kein
                # Boersenergebnis mehr (sie sucht nur Schliessungen NACH dem
                # Eroeffnen). Fehlt die Fuellzeit, bleibt es beim alten Weg.
                "eroeffnet": fuell_zeit[:10], "eroeffnet_zeit": fuell_zeit,
                "funding_zuletzt": _jetzt(), "funding_summe": 0.0,
            }
            z.setdefault("positionen", []).append(pos)
            gebucht += 1
            if not still:
                print("  Wartender Auftrag %s ist GEFUELLT -> Position gebucht "
                      "(%.4f Kontrakte @ %.6f)" % (a["inst"], kontrakte, pos["einstieg"]))
            journal(zeit=_jetzt(), modus="live", aktion="eroeffnen", inst=a["inst"],
                    pos_id=pos["pos_id"],
                    seite=pos["seite"], familie=pos["familie"],
                    preis="%.6f" % pos["einstieg"], kontrakte=kontrakte,
                    nominal_usd="%.2f" % a.get("nominal", 0.0),
                    margin_usd="%.2f" % a.get("margin", 0.0),
                    hebel="%.2f" % a.get("hebel", 0.0),
                    stop="%.6f" % (a.get("stop") or 0.0),
                    ziel="%.6f" % (a.get("ziel") or 0.0),
                    liq="%.6f" % (a.get("liq") or 0.0),
                    grund="order_gefuellt")
            continue
        if zustand in ("canceled", "mmp_canceled"):
            if not still:
                print("  Wartender Auftrag %s ist %s - wird vergessen"
                      % (a["inst"], zustand))
            continue
        behalten.append(a)
    z["wartende"] = behalten
    return gebucht


def _zeit_ms(iso):
    """ISO-Zeitstempel -> Millisekunden seit Epoche (None bei Unlesbarem)."""
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return int(t.timestamp() * 1000)


def _iso_aus_ms(ms):
    """Millisekunden seit Epoche -> ISO-Zeitstempel (None bei Unlesbarem).

    Gegenstueck zu `_zeit_ms`. Wird gebraucht, wenn die BOERSE den Zeitpunkt
    liefert (Fuellung einer Order, Schliessung einer Position) - die eigene
    Uhr ist dann die falsche Quelle.
    """
    try:
        return datetime.fromtimestamp(int(ms) / 1000.0,
                                      timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _geist_erloes(p):
    """Was kommt fuer eine von HAND geschlossene Position zurueck?

    DIE FALLE, DIE DAS BEHEBT (gemessen 21.09.2026): Die Geisterpruefung buchte
    die Verkaufszeile mit margin_usd = 0.00. wachen_xperp liest die
    schliessen-Zeile als ERLoes - eine von Hand geschlossene Position zaehlte
    damit als TOTALVERLUST in Hoehe des Einsatzes. Bei HBAR waren das -16.84
    USD in der Drawdown-Kurve, die den Kill-Switch auswertet - ein Verlust,
    den es nie gab, und eine Sperre, die dadurch mit ausgeloest werden konnte.

    JETZT: das ECHTE Ergebnis von der Boerse (/account/positions-history,
    `realizedPnl`), plus den Einsatz. Nur wenn die Boerse nichts hergibt
    (kein Eintrag, Netzfehler, unlesbare Zahl), wird NEUTRAL gebucht - der
    Einsatz kommt zurueck, kein erfundenes Ergebnis.

    Anteil: Stand an der Boerse MEHR als im Buch (Max kann von Hand
    aufstocken), wird das Boersenergebnis nur anteilig gerechnet - sonst
    zaehlte die Runde Gewinne, die gar nicht ihr gehoeren.

    Rueckgabe: (erloes_usd, quelle, anteil) mit quelle "boerse" oder "neutral".
    """
    margin = float(p.get("margin") or 0.0)
    kontrakte = abs(float(p.get("kontrakte") or 0.0))
    seit = _zeit_ms(p.get("eroeffnet_zeit"))
    if not seit:
        return margin, "neutral", None
    try:
        satz = okxf.geschlossene_position(p.get("inst", ""), seit)
    except Exception:                                          # noqa: BLE001
        # Ein Netzfehler darf die Ausbuchung nicht verhindern - er darf nur
        # kein Ergebnis erfinden.
        return margin, "neutral", None
    if not satz:
        return margin, "neutral", None
    try:
        pnl = float(satz.get("realizedPnl") or 0.0)
        geschlossen = abs(float(satz.get("closeTotalPos") or 0.0))
    except (TypeError, ValueError):
        return margin, "neutral", None
    anteil = 1.0
    if geschlossen > 0 and kontrakte > 0:
        anteil = min(1.0, kontrakte / geschlossen)
    return margin + pnl * anteil, "boerse", anteil


# Nur in diesem Fenster nach dem Eroeffnen darf eine GEFUELLTE Order eine
# fehlende Position entschuldigen (Wettlauf Order->Position). Danach ist eine
# Order, die irgendwann gefuellt hat, kein Beweis mehr fuer einen Bestand.
_GEIST_FUELLUNG_GRACE_MIN = 10


def _minuten_seit(iso):
    """Minuten seit einem ISO-Zeitstempel (None, wenn unlesbar/leer)."""
    t = _zeit_ms(iso)
    if t is None:
        return None
    return (datetime.now(timezone.utc).timestamp() * 1000 - t) / 60000.0


def buche_verkaeufe_aus_boerse(z, live=True, still=False):
    """Verkaeufe buchen, die die BOERSE bezeugt - VOR `bueche_geister_aus`.

    ANLASS (gemessen in der Nacht 04./05.10.2026): vier echte Live-Positionen
    wurden ueber Nacht von Hand verkauft (Stops). `bueche_geister_aus` sah,
    dass sie an der Boerse fehlen, und buchte sie als
    `grund="buchbereinigung_geist"` mit Erloes 0.00 - weil ein Geist neutral
    gebucht wird (Einsatz zurueck, kein erfundenes Ergebnis). Die Boerse
    fuehrte die Ergebnisse die ganze Zeit:

        STRK   realizedPnl  +70,76 USD
        SOL    realizedPnl   +0,96 USD
        QUANT  realizedPnl  -18,47 USD

    Sie waren nur nicht erreichbar, weil `_geist_erloes` den VERKAUFSKURS aus
    `/account/positions-history` liest und dort `avgPx: None` bekommt. Der
    Kurs steht an genau einer Stelle: `/trade/fills` -> `fillPx`.

    Die Reihenfolge ist der eigentliche Fix. `buche_abgleich` ruft erst die
    Geister (sie loeschen die Position) und DANACH
    `bueche_groessen_abgleichen` (sie zieht das Buch auf die Boersengroesse).
    Bei einer auf null gelaufenen Position hat die erste Stufe schon alles
    entfernt - die zweite konnte nichts mehr angleichen. Diese Funktion geht
    deshalb VOR beiden.

    WAS SIE NICHT TUT: keine Order, kein Stop, kein Storno, kein Kauf. Nur
    Buchhaltung. Und im Papierlauf (`live=False`) exakt nichts - sonst laege
    eine Papierposition am Ende gegen die Boerse gerechnet.

    Ohne `fills` wird NEUTRAL gebucht und als neutral benannt. Ein Verkauf
    braucht den Kurs; ohne Zeugen wird nichts behauptet.
    """
    if not live:
        # Der Papierlauf liest die Boerse nicht - sonst wuerde eine Papier-
        # position gegen den echten Bestand gerechnet und am Ende als
        # "verkauft" dastehen. Das ist die Grenze, die den Papierlauf sicher
        # macht.
        return 0
    import boersen_bruecke as bruecke
    try:
        plan = bruecke.plan(z, live=True)
    except Exception as e:                                     # noqa: BLE001
        if not still:
            print("  Boersen-Bruecke uebersprungen (%s) - Buch bleibt unberuehrt"
                  % e)
        return 0
    if plan is None:
        if not still:
            print("  Boersen-Bruecke: Boerse nicht erreichbar - Buch bleibt "
                  "unberuehrt")
        return 0
    verkaeufe = [e for e in plan if e["aktion"] == "verkauf"]
    if not verkaeufe:
        return 0
    for e in verkaeufe:
        p = next((q for q in z["positionen"] if q.get("pos_id") == e["pos_id"]),
                 None)
        if p is None:
            continue
        v = e.get("verkauf")
        menge = e["differenz"]
        if v:
            preis = v["kurs"]
            grund = "verkauf_von_hand"
            quelle = "boerse"
        else:
            preis = float(p.get("einstieg") or p.get("preis") or 0.0)
            grund = "verkauf_ohne_zeuge_neutral"
            quelle = "neutral"
        nominal, erloes = _hand_erloes(p, preis, menge)
        if not still:
            print("  VERKAUF gebucht: %s %s %.0f Stuecke @ %.6f = %.2f USD "
                  "Margin zurueck (Boerse hat %s)"
                  % (p.get("inst"), p.get("seite"), menge, preis, erloes,
                     "bezeugt" if v else "KEINEN Zeugen -> neutral"))
        journal(zeit=_jetzt(), modus="live", aktion="schliessen",
                inst=p.get("inst", ""), pos_id=p.get("pos_id", ""),
                seite=p.get("seite", ""), familie=p.get("familie", ""),
                preis="%.8g" % preis, kontrakte="%.4f" % menge,
                nominal_usd="%.2f" % nominal,
                margin_usd="%.2f" % erloes, hebel=p.get("hebel", ""),
                grund=grund)
        # Die Position bleibt stehen, wenn an der Boerse noch Rest steht -
        # sie ist dann TEILVERKAUFT, und der Rest gehoert weiter ins Buch.
        if e["boerse"] >= bruecke.MENGEN_TOLERANZ:
            alt = abs(float(p.get("kontrakte") or 0.0))
            if alt > 0:
                faktor = e["boerse"] / alt
                for feld in ("kontrakte",):
                    if p.get(feld) is not None:
                        p[feld] = float(p[feld]) * faktor
                for feld in ("nominal", "margin"):
                    if p.get(feld) is not None:
                        p[feld] = float(p[feld]) * faktor
                if not still:
                    print("    Rest bleibt offen: %.2f Stuecke an der Boerse"
                          % e["boerse"])
        else:
            z["positionen"] = [q for q in z["positionen"]
                               if q.get("pos_id") != e["pos_id"]]
            if p.get("ord_id"):
                try:
                    okxf.order_stornieren(p["inst"], p["ord_id"])
                    if not still:
                        print("    offene Order zu %s storniert (die Position "
                              "ist verkauft)" % p.get("inst"))
                except Exception as e:                         # noqa: BLE001
                    print("    Storno der offenen Order fehlgeschlagen: %s" % e)
    return len(verkaeufe)


def bueche_geister_aus(z, w, still=False, stornieren=True):
    """Positionen aus dem Buch, die an der BOERSE nicht (mehr) existieren.

    Anders als `bueche_papier_altlasten_aus` (die Papier-Positionen ohne
    Live-Herkunft) prueft diese Funktion gegen die BOERSE: /account/positions
    ist die Wahrheit. Eine Position mit modus=live, die dort fehlt oder mit
    Groesse 0 steht, ist ein Geist - sie belegt einen Platz, blockiert
    Kaeufe und laesst jeden Ausstieg fehlschlagen.

    Haeufigster Fall ist ein HANDGRIFF: Max schliesst eine Position in der
    App. Dann gibt es keine Verkaufszeile im eigenen Journal - das Ergebnis
    kommt von der Boerse (siehe `_geist_erloes`).

    Faellt die Abfrage aus, wird NICHTS gebucht: ein Netzfehler darf das Buch
    nicht leeren.

    REGEL (Max, 09.10.2026): ausgebucht wird NUR mit Boersenbeleg. Der Geist
    braucht ein realisiertes Ergebnis von der Boerse (realizedPnl aus
    /account/positions-history, siehe `_geist_erloes`). Fehlt dieser Beleg,
    bleibt die Position als UNKLAR im Buch stehen und wird gemeldet - NICHT
    neutral ausgebucht. Anlass: am 05.10.2026 hat die neutrale Buchung
    (Einsatz zurueck, Erloes 0.00) sechs echte Live-Positionen aus dem Buch
    geloescht, weil die Boersenabfrage sie kurz nicht zeigte; an der Boerse
    blieben sie offen und unbewacht. Eine Karteileiche blockiert hoechstens
    einen Platz, eine echte Position ohne Buch liefe unbewacht weiter.

    `stornieren=False` (Papierlauf): eine offene Order zu einem Geist wird
    NICHT storniert. Das waere ein echter Boerseneingriff - und der Grund,
    warum diese Funktion bis zum 01.10.2026 nur im Live-Zweig lief (T-277).
    Die BUCHUNG selbst ist auch im Papierlauf richtig: fehlt die Position an
    der Boerse, ist sie weg - egal, wer sie geschlossen hat. Die Gegenrichtung
    (ein Papierlauf bucht den Verkauf einer ECHTEN Position) bleibt verboten:
    darum prueft diese Funktion ausschliesslich gegen die Boerse und niemals
    gegen die eigene Kursrechnung.
    """
    try:
        an_der_boerse = {p["instId"]: float(p.get("pos") or 0.0)
                         for p in okxf.positionen()}
    except Exception as e:                                     # noqa: BLE001
        print("  Geisterpruefung uebersprungen (%s) - Buch bleibt unberuehrt" % e)
        return 0
    geister, echte = [], []
    for p in z["positionen"]:
        if p.get("modus") != "live":
            continue
        groesse = an_der_boerse.get(p.get("inst"))
        if groesse is not None and abs(groesse) >= 1e-9:
            echte.append(p)
            continue
        # Fehlt die Position, ist die ORDER die naechste Frage: ein Limit, das
        # genau jetzt fuellt, sieht hier wie ein Geist aus. Am 21.09.2026 ist
        # das passiert (HBAR: beim Pruefen accFillSz=0, Sekunden spaeter
        # gefuellt) - die Position wurde ausgebucht und lief dann OHNE Buch
        # weiter. Darum: gefuellte Order = echte Position, auch wenn
        # /account/positions sie noch nicht zeigt.
        #
        # ABER (gemessen 22.09.2026): diese Entschuldigung darf NICHT ewig
        # gelten. Die Order, die eine Position irgendwann eroeffnet hat, ist
        # immer noch "gefuellt" - auch nachdem Max die Position von Hand
        # geschlossen hat. Damit blieben BZ, CL und CRCL als Karteileichen im
        # Buch (an der Boerse weg, im Buch mit Platz und Stop). Die Fuellung
        # zaehlt deshalb nur im Grace-Fenster nach dem Eroeffnen.
        frisch = _minuten_seit(p.get("eroeffnet_zeit"))
        if frisch is None or frisch <= _GEIST_FUELLUNG_GRACE_MIN:
            gefuellt = (okxf.gefuellte_kontrakte(p["inst"], p["ord_id"])
                        if p.get("ord_id") else 0.0)
            if gefuellt:
                print("  %s steht noch nicht in /account/positions, die Order "
                      "ist aber gefuellt (%.4f) - Position bleibt im Buch"
                      % (p.get("inst"), gefuellt))
                echte.append(p)
                continue
        geister.append(p)
    if not geister:
        return 0
    behalten = [p for p in z["positionen"] if p in echte
                or p.get("modus") != "live"]
    unklar = []
    for p in geister:
        erloes, quelle, anteil = _geist_erloes(p)
        if quelle != "boerse":
            # REGEL (Max, 09.10.2026): ohne Boersenbeleg wird eine Live-Position
            # NICHT ausgebucht. Am 05.10.2026 hat genau dieser Weg sechs echte
            # Positionen aus dem Buch geloescht (TRX, SOL, NIGHT, STRK, QUANT,
            # XAG): die Boersenabfrage zeigte sie kurz nicht, und die neutrale
            # Buchung (Einsatz zurueck) liess sie aus dem Buch verschwinden -
            # an der Boerse blieb die Position offen und unbewacht.
            # Ohne Beleg bleibt die Position als UNKLAR stehen. Eine Karteileiche
            # blockiert hoechstens einen Platz; eine echte Position ohne Buch
            # liefe unbewacht weiter.
            unklar.append(p)
            if not still:
                print("  %s (%s) fehlt an der Boerse, aber KEIN Boersenbeleg "
                      "(realizedPnl) auffindbar - bleibt als UNKLAR im Buch, "
                      "wird NICHT ausgebucht (Regel Max 09.10.2026)"
                      % (p.get("inst"), p.get("seite")))
            continue
        # Die offene Order gehoert dazu: bliebe sie liegen, koennte sie
        # spaeter fuellen und eine Position ohne Buch erzeugen - dann haette
        # niemand einen Ausstieg im Blick. Sie traegt zwar einen
        # boersenseitigen Stop, aber ein Platz im Buch ist besser.
        if p.get("ord_id"):
            if stornieren:
                try:
                    okxf.order_stornieren(p["inst"], p["ord_id"])
                    if not still:
                        print("  offene Order zu %s storniert (ord_id %s)"
                              % (p.get("inst"), str(p["ord_id"])[:14]))
                except Exception as e:                         # noqa: BLE001
                    print("  Storno der offenen Order zu %s fehlgeschlagen: %s"
                          % (p.get("inst"), e))
            elif not still:
                print("  offene Order zu %s bleibt liegen (Papierlauf storniert "
                      "nichts an der Boerse)" % p.get("inst"))
        if not still:
            print("  Geist ausgebucht: %s %s - an der Boerse nicht vorhanden, "
                  "Ergebnis von der Boerse: Einsatz %.2f -> zurueck %.2f "
                  "(Anteil %.0f%%)"
                  % (p.get("inst"), p.get("seite"), p.get("margin") or 0.0,
                     erloes, round((anteil or 0.0) * 100)))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                inst=p.get("inst", ""),
                pos_id=p.get("pos_id", ""), seite=p.get("seite", ""),
                familie=p.get("familie", ""), preis="%.6f" % (p.get("einstieg") or 0.0),
                kontrakte=p.get("kontrakte", ""),
                nominal_usd="%.2f" % (p.get("nominal") or 0.0),
                margin_usd="%.2f" % erloes, hebel=p.get("hebel", ""),
                grund="buchbereinigung_geist")
    z["positionen"] = behalten + unklar
    return len(geister) - len(unklar)


# Kontraktzahlen sind gebrochen (CRCL 1.1), aber nicht beliebig fein: unter
# dieser Schwelle ist es API-Rauschen, kein Handgriff.
_KONTRAKT_TOLERANZ = 1e-6

# Ab welcher relativen Abweichung Margin/Nennwert als "Handgriff" gelten und
# dem Boersenwert folgen. Darunter ist es Rundung (die Boersenwerte sind
# Sekunden aktueller als das Buch).
_WERT_TOLERANZ = 0.01

# Nur die EIGENE Kontraktfamilie wird uebernommen. Alles andere am Konto
# (Spot-Bestaende der scanner-Spur, handelsuebliche Fremdkontrakte) gehoert
# einer anderen Spur und darf hier nicht ins Buch wandern.
_FREMD_MUSTER = "_UM_XPERP-"


def bueche_fremde_positionen_uebernehmen(z, w, still=False, schutz=True):
    """BOERSE -> BUCH: von Hand eroeffnete Positionen ins Buch holen.

    ANLASS (24.09.2026, gemessen): Max eroeffnet Positionen in der OKX-App;
    OKX kennzeichnet solche Auftraege mit tag='OTversionB' (eigene Auftraege
    haben kein tag). Die Spur sieht sie nie - sie kennt nur ihr eigenes
    Journal. Am 23.09.2026 lagen so BZ (1467 Kontrakte aus drei Fillungen,
    13:19-14:22 UTC) und CL (133 aus drei Fillungen, 13:15-14:18 UTC)
    unbemerkt offen: Margin belegt, kein Buchplatz, keine Ausstiegslogik, und
    zwei von drei BZ-Fillungen trugen NUR ein Ziel, keinen Stop.

    `bueche_geister_aus` raeumt die Gegenrichtung auf (Buchposition, die an
    der Boerse fehlt). Diese Funktion ist die fehlende Richtung. Sie ist
    bewusst kein Einstieg: sie kauft nichts, sie macht Vorhandenes sichtbar
    und schuetzt es.

    Grenzen, damit daraus keine wilde Position wird:
      * nur Instrumente der eigenen Kontraktfamilie (_UM_XPERP-)
      * Einstieg ist der Boersenschnitt (avgPx), nie geschaetzt
      * Stop/Ziel aus derselben Rechnung wie ein eigener Einstieg
        (stop_atr_faktor / ziel_atr_faktor mal ATR 1H)
      * existiert an der Boerse schon ein Stop (Position oder Auftrag), wird
        KEIN zweiter gestellt
      * laesst sich der ATR nicht rechnen, wird NICHT gebucht (lieber ein
        gemeldeter Fremdbestand als ein erfundener Stop)
      * faellt die Boersenfrage aus, bleibt das Buch unberuehrt
      * `schutz=False` (Papierlauf): die Position wird ins Buch geholt und
        im Journal vermerkt, aber KEIN Stop gestellt - eine Order ist ein
        echter Boerseneingriff. Die Zeile sagt dann, dass der Schutz im
        naechsten Live-Lauf gesetzt wird.
    """
    try:
        roh = okxf.positionen()
    except Exception as e:                                     # noqa: BLE001
        print("  Fremdbestand-Pruefung uebersprungen (%s) - Buch bleibt unberuehrt" % e)
        return 0
    an_der_boerse = {}
    for p in roh or []:
        try:
            groesse = float(p.get("pos") or 0.0)
        except (TypeError, ValueError):
            continue
        if abs(groesse) >= 1e-9:
            an_der_boerse[p.get("instId")] = (groesse, p)
    if not an_der_boerse:
        return 0
    bekannt = {p.get("inst") for p in z.get("positionen") or []}
    neu = []
    for inst, (groesse, roh_pos) in sorted(an_der_boerse.items()):
        if _FREMD_MUSTER not in (inst or ""):
            continue
        if inst in bekannt:
            continue
        seite = "long" if groesse > 0 else "short"
        vz = 1.0 if seite == "long" else -1.0
        try:
            einstieg = float(roh_pos.get("avgPx") or 0.0)
        except (TypeError, ValueError):
            einstieg = 0.0
        if einstieg <= 0:
            print("  %s: kein Boersenschnitt (avgPx) - NICHT uebernommen" % inst)
            continue
        try:
            kerzen = okxf.kerzen(inst, "1H", 300)
            # atr() liefert eine REIHE (None in der Aufwaermphase) - gebraucht
            # wird der letzte fertige Wert, nicht die Liste.
            reihe = [x for x in indikatoren.atr(kerzen) if x]
            spanne = reihe[-1] if reihe else None
        except Exception as e:                                 # noqa: BLE001
            spanne = None
            print("  %s: ATR nicht rechenbar (%s) - NICHT uebernommen" % (inst, e))
        if not spanne or spanne <= 0:
            print("  %s: ATR leer - NICHT uebernommen" % inst)
            continue
        try:
            instr = okxf.instrument(inst)
        except Exception as e:                                 # noqa: BLE001
            print("  %s: Kontrakt nicht lesbar (%s) - NICHT uebernommen" % (inst, e))
            continue
        stop = okxf.auf_tick(instr, einstieg - vz * w["stop_atr_faktor"] * spanne)
        ziel = okxf.auf_tick(instr, einstieg + vz * w["ziel_atr_faktor"] * spanne)
        kontrakte = abs(groesse)
        try:
            margin = float(roh_pos.get("margin") or roh_pos.get("imr") or 0.0)
        except (TypeError, ValueError):
            margin = 0.0
        try:
            nominal = float(roh_pos.get("notionalUsd") or 0.0)
        except (TypeError, ValueError):
            nominal = 0.0
        pos = {
            "inst": inst, "basis": inst.split("-")[0], "seite": seite,
            "familie": _familie_von(inst, z), "einstieg": einstieg,
            "stop": stop, "ziel": ziel, "liq": 0.0, "kontrakte": kontrakte,
            "nominal": nominal, "margin": margin, "hebel": 0.0,
            "gebuehr_taker": 0.0005, "modus": "live", "ord_id": "",
            "eroeffnet": _heute(), "eroeffnet_zeit": _jetzt(),
            "funding_zuletzt": _jetzt(), "funding_summe": 0.0,
            "herkunft": "boerse_handgriff",
            # Die Kennung gehoert in JEDE Buchposition (T-095). Der
            # Uebernahmepfad vergab sie nicht - gemessen am 03.10.2026:
            # STRK und TRX standen als LIVE-Positionen ohne pos_id im Buch.
            # Ohne sie kann die Paarung ihren Ausstieg nicht eindeutig
            # zuordnen, sobald zwei Positionen auf demselben XPERP-Markt
            # liegen.
            "pos_id": pos_kennung.neu(_jetzt()),
        }
        geschuetzt = _stop_vorhanden(inst, roh_pos)
        # Auch in der Vorschau sichtbar: die Uebernahme selbst (Journal, Stop,
        # Zustand) passiert nur mit still=False.
        print("  %sFREMDER BESTAND: %s %s %.4f Kontrakte @ %.6f (Boersenschnitt) "
              "%s Stop %.6f, Ziel %.6f (Familie %s)"
              % ("VORSCHAU - " if still else "", inst, seite, kontrakte, einstieg,
                 "-> ins Buch,", stop, ziel, pos["familie"] or "unbekannt"))
        print("    Stop an der Boerse: %s"
              % ("schon vorhanden" if geschuetzt else
                 ("wird gestellt" if (not still and schutz) else
                  ("fehlt - Order setzt nur der Live-Lauf (Werkzeug stopdeckung.py)"
                   if not schutz else "fehlt - wuerde gestellt"))))
        if not geschuetzt and not still and schutz:
            try:
                okxf.schutz_stop_setzen(inst, seite, kontrakte, stop, ziel)
                print("    Schutz-Stop gestellt (%s)" % inst)
            except Exception as e:                             # noqa: BLE001
                print("    Schutz-Stop FEHLGESCHLAGEN (%s): %s - Position steht "
                      "im Buch und wird gemeldet" % (inst, e))
        z.setdefault("positionen", []).append(pos)
        neu.append(inst)
        if not still:
            journal(zeit=_jetzt(), modus="live", aktion="eroeffnen", inst=inst,
                    seite=seite, familie=pos["familie"], preis="%.6f" % einstieg,
                    kontrakte=kontrakte, nominal_usd="%.2f" % nominal,
                    margin_usd="%.2f" % margin, hebel="",
                    stop="%.6f" % stop, ziel="%.6f" % ziel,
                    grund="fremdposition_uebernommen")
    return len(neu)


def _familie_von(inst, z=None):
    """Die Kategorie eines Instruments - aus der Rangliste des Zustands.

    Die Familie ist keine Anzeige: die Wachen deckeln sie
    (max_anteil_gesamt je Familie). Eine uebernommene Position mit leerer
    Familie wuerde diesen Deckel umgehen, deshalb wird sie hier aus derselben
    Quelle gelesen, aus der auch ein eigener Einstieg sie hat: der Rangliste.
    """
    basis = (inst or "").split("-")[0].upper()
    for e in ((z or {}).get("rangliste") or {}).get("werte") or []:
        if str(e.get("basis", "")).upper() == basis:
            return e.get("kategorie") or ""
    return ""


def _stop_vorhanden(inst, roh_pos):
    """Hat die Position an der Boerse schon einen Stop?

    Zwei Wege, weil OKX zwei Bauarten kennt: ein Stop direkt an der Position
    (Feld slTriggerPx in /account/positions) oder ein bedingter Auftrag mit
    gefuelltem Stop-Preis. Ein angehaengter Stop (attachAlgoOrds einer
    gefuellten Order) erscheint in KEINER der beiden Listen - deshalb zaehlt
    auch das Positionsfeld.

    WELCHER Preis ein Stop ist, entscheidet `okxf.ist_schutz_stop` - nicht
    dieses Werkzeug. Grund (T-278, gemessen 01.10.2026): ein Trailing-Stop
    (`ordType=move_order_stop`) fuehrt `moveTriggerPx` und KEIN slTriggerPx;
    eine Pruefung nur auf slTriggerPx meldete fuer ADA "Stop fehlt" und
    stellte einen zweiten Stop neben den laufenden.
    """
    if okxf.ist_schutz_stop(roh_pos):
        return True
    try:
        for s in okxf.schutz_stops(inst) or []:
            if okxf.ist_schutz_stop(s):
                return True
    except Exception:                                          # noqa: BLE001
        return True                        # im Zweifel keinen zweiten Stop stellen
    return False


def bueche_groessen_abgleichen(z, w, still=False):
    """Buch und Boerse auf DIESELBE Kontraktzahl bringen.

    ANLASS (Auftrag Max, 22.09.2026): "Auch zukuenftig moechte ich noch per
    Hand Positionen veraendern koennen." Ein Handgriff aendert die Kontraktzahl
    an der Boerse - das Buch merkte davon bisher NICHTS, geprueft wurde nur, ob
    eine Position ueberhaupt existiert. Gemessen am 22.09.2026:

        CL    Buch 20.0   Boerse 19    (41 von 60 Kontrakten von Hand zu)
        BZ    Buch 208    Boerse 727   (aufgestockt)
        HBAR  Buch 9.4    Boerse 47.1  (aufgestockt)

    Der gefaehrliche Fall ist ein zu KLEINES Buch: der Ausstieg schloesse nur
    den Buchteil und liesse den Rest unbewacht an der Boerse stehen. Darum ist
    die BOERSE die Wahrheit und das Buch folgt ihr - in beide Richtungen.

    Was NICHT passiert: Stop, Ziel und Einstieg bleiben unangetastet (die
    Handelsentscheidung bleibt die der Spur), es wird KEINE Order geschickt,
    und die Buchhaltung der Runde bleibt unberuehrt - die kommt aus der
    eroeffnen-Zeile im Journal, nicht aus diesem Zustand. `margin`/`nominal`
    werden nur im Verhaeltnis mitgezogen, damit die Anzeige nicht luegt.

    Fehlt die Position ganz, ist das nicht die Aufgabe dieser Funktion - das
    erledigt die Geisterpruefung.
    """
    try:
        roh = {p["instId"]: p for p in okxf.positionen()}
        an_der_boerse = {k: float(v.get("pos") or 0.0) for k, v in roh.items()}
    except Exception as e:                                     # noqa: BLE001
        print("  Groessenabgleich uebersprungen (%s) - Buch bleibt unberuehrt"
              % e)
        return []
    abweichungen = []
    for p in z["positionen"]:
        if p.get("modus") != "live" or p.get("inst") not in an_der_boerse:
            continue
        soll = abs(float(p.get("kontrakte") or 0.0))
        ist = abs(an_der_boerse[p["inst"]])
        grosse = soll > 0 and abs(ist - soll) > _KONTRAKT_TOLERANZ
        faktor = (ist / soll) if (grosse and soll > 0) else 1.0
        # Margin und Nennwert nennt die BOERSE SELBST (Felder margin und
        # notionalUsd der Position). Sie sind genauer als eine Verhaeltnis-
        # rechnung auf einem Buchwert, der aus einer alten Groesse stammt:
        # gemessen am 01.10.2026 schrieb die Verhaeltnisrechnung fuer ZEC
        # 298.02 USD ins Buch, waehrend an der Boerse 238.45 gebunden waren -
        # und an diesen Zahlen haengt die Anzeige "gebunden von ...".
        # Deshalb folgen sie der Boerse auch dann, wenn die Kontraktzahl schon
        # stimmt (eine Hand kann nur nominell geaendert haben). Fehlt das Feld,
        # bleibt es beim Verhaeltnis (alte Boersenformen).
        werte = False
        geaendert = []
        for feld, schluessel in (("nominal", "notionalUsd"), ("margin", "margin")):
            if p.get(feld) is None:
                continue
            try:
                wert = float((roh.get(p["inst"]) or {}).get(schluessel) or 0.0)
            except (TypeError, ValueError):
                wert = 0.0
            alt = float(p[feld] or 0.0)
            if wert > 0:
                neu = wert
            elif grosse:
                neu = alt * faktor
            else:
                continue
            if alt > 0 and abs(neu - alt) / alt <= _WERT_TOLERANZ:
                continue                     # Rundung, kein Handgriff
            p[feld] = round(neu, 4)
            geaendert.append((feld, alt, round(neu, 4)))
            werte = True
        if not (grosse or werte):
            continue
        if grosse:
            p["kontrakte"] = ist
            abweichungen.append({"inst": p["inst"], "buch": soll, "boerse": ist})
        if not still:
            if grosse:
                print("  Groessenabgleich %s: Buch %.4f -> Boerse %.4f Kontrakte%s"
                      % (p["inst"], soll, ist,
                         "  (Handgriff: aufgestockt)"
                         if faktor > 1 else "  (Handgriff: teilweise geschlossen)"))
            if not grosse and geaendert:
                print("  Werteabgleich %s: %s (Boersenwerte)"
                      % (p["inst"], ", ".join(
                          "%s %.2f -> %.2f" % (f, a, n) for f, a, n in geaendert)))
        journal(zeit=_jetzt(), modus="live", aktion="anpassen",
                inst=p.get("inst", ""),
                pos_id=p.get("pos_id", ""), seite=p.get("seite", ""),
                familie=p.get("familie", ""),
                kontrakte="%.4f" % float(p.get("kontrakte") or 0.0),
                nominal_usd="%.2f" % (p.get("nominal") or 0.0),
                margin_usd="%.2f" % (p.get("margin") or 0.0),
                hebel=p.get("hebel", ""), grund="handanpassung")
    return abweichungen


def bueche_stopdeckung(z, w, live, still=False):
    """Wie viele Kontrakte einer Live-Position sind an der BOERSE geschuetzt?

    Die vierte Abgleichsstufe (T-362). Die ersten drei fragen OB: steht die
    Position da (Geister), stimmt die Kontraktzahl (Groesse), liegt EIN
    Schutzauftrag (`_stop_vorhanden`). Keine davon fragt, WIEVIELE Kontrakte
    dieser Schutz abdeckt. Gemessen am 02.10.2026: ZEC mit 145 Kontrakten,
    sechs OCO-Stops ueber zusammen 126 - **19 Kontrakte bis zur
    Liquidation**, waehrend Spur, Bericht und Abgleich "ok" sagten. Am
    26.09. waren es vier Stops (rund 385 USD), die an der Boerse
    weggestorner wurden, ohne dass das Buch es merkte.

    Warum das hier steht und nicht im Werkzeug `stopdeckung.py`: der Abgleich
    laeuft in JEDEM Zyklus (T-277), das Werkzeug nur, wenn jemand es von
    Hand startet. Eine Pruefung, die niemand aufruft, meldet eine Luecke nur
    dann, wenn sie zufaellig aufgefaellt wird.

    **Hier wird NICHTS gestellt.** Diese Funktion liest und meldet. Ein
    Nachsetzen braucht einen Schutzpreis, den niemand genannt hat - das
    Werkzeug nimmt ihn ueber `--stop` und verweigert ohne den Schalter.
    Ein geratener Notausstieg ist eine Order, die jemand nicht bestellt hat.

    Rueckgabe: (befunde, abfrage_ok). `abfrage_ok=False` heisst "nicht
    lesbar" - der Aufrufer darf daraus KEIN "kein Stop" ableiten.
    """
    try:
        roh = {p["instId"]: p for p in okxf.positionen()}
    except Exception as e:                                   # noqa: BLE001
        print("  Stop-Deckung nicht abrufbar (%s) - es wird nichts gemacht"
              % e)
        return [], False
    befunde = []
    for p in z.get("positionen") or []:
        if p.get("modus") != "live":
            continue
        inst = p.get("inst")
        if inst not in roh:
            continue                     # das ist die Geisterpruefung
        d = stopdeckung.deckung(p, roh)
        liq = None
        try:
            liq = float(roh[inst].get("liqPx") or 0.0) or None
        except (TypeError, ValueError):
            liq = None
        tote = stopdeckung.tote_stops(inst, p.get("seite") or "long", liq)
        if d["fehlt"] <= stopdeckung._MENGE_TOLERANZ and not tote:
            continue
        befunde.append({"position": p, "deckung": d, "liq": liq, "tote": tote})
    if befunde and not still:
        for b in befunde:
            d = b["deckung"]
            print("  %-26s %6.1f Kontrakte, geschuetzt %6.1f -> UNGESCHUETZT "
                  "%.1f" % (b["position"]["inst"], d["soll"], d["gedeckt"],
                            d["fehlt"]))
            for t in b["tote"]:
                print("      TOT: %-14s %8.1f  Stop %s liegt an/unter der "
                      "Liquidation %s" % (t.get("ordType"), t["menge"],
                                          t.get("stop"), t.get("liq")))
            print("      Nachsetzen: ../scanner/.venv/Scripts/python.exe "
                  "stopdeckung.py --anwenden --stop <preis>")
    z["stopdeckung"] = {"geprueft": len(roh),
                        "luecken": len(befunde)}
    return befunde, True


def _abgleich_stufe(name, fn, *args, standard=0, **kwargs):
    """Eine Stufe des Buchabgleichs, die den Zyklus nie abbrechen darf.

    ANLASS (Review 09.10.2026): `lauf()` ruft `buche_abgleich` VOR Kill-Switch
    und Herzschlag-Notausstieg. Vier der fuenf Stufen fangen Boersenfehler
    selbst ab, `wartende_auftraege` aber nicht (`okxf.order_stand` wirft bei
    fehlenden Schluesseln oder Netzfehler). Die Ausnahme lief durch `lauf()`
    und uebersprang den Kill - ausgerechnet dann, wenn die Boerse nicht
    antwortet. Der Abgleich ist Buchhaltung; fehlt er, bleibt das Buch
    unberuehrt (wie bei den anderen Stufen), der Schutz laeuft trotzdem.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as e:                                     # noqa: BLE001
        print("  Abgleich-Stufe %s uebersprungen (%s: %s)"
              % (name, type(e).__name__, e))
        return standard


def buche_abgleich(z, w, live, still=False):
    """Buch gegen BOERSE - in JEDEM Zyklus, nicht nur im Live-Lauf (T-277).

    ANLASS (gemessen 01.10.2026): xperp lief seit dem 29.09.2026 12:00 Papier.
    Alle vier Abgleichsfunktionen standen aber im `if live:`-Zweig - ein
    HANDGRIFF in der App (XRP von 704 auf 0, ADA 235 auf 0, VVV 217 auf 0,
    ZEC von 38 auf 145) erreichte das Buch nie. Es fuehrte vier Positionen und
    zwei wartende Auftraege, waehrend an der Boerse EINE Position stand. Der
    Abgleich ist keine Handelsentscheidung, sondern Buchhaltung - er gehoert
    in jeden Zyklus. Wer ihn nur live laufen laesst, baut ein Buch, das genau
    dann veraltet, wenn die Spur pausiert.

    Was hier NICHT passiert (die Grenze, die den Papierlauf sicher macht):
      * keine Order. `schutz=False` stellt keinen Stop, `stornieren=False`
        storniert nichts an der Boerse.
      * kein Ausstieg auf eigene Rechnung: geprueft wird gegen
        /account/positions, nie gegen die eigene Kursrechnung. Eine Position
        wird nur ausgebucht, wenn die BOERSE sagt, dass sie weg ist.
      * faellt eine Abfrage aus, bleibt das Buch unberuehrt (jede der drei
        Funktionen kehrt bei einem Netzfehler ohne Aenderung zurueck).

    Reihenfolge ist Absicht: erst die wartenden Auftraege (aus einem gefuellten
    Auftrag wird eine Position), dann die Geister (eine soeben gebuchte
    Position, die an der Boerse schon wieder weg ist, wird in DEMSELBEN Zyklus
    mit dem Boersenergebnis ausgebucht), dann die Fremdpositionen, zuletzt die
    Groesse.
    """
    stand = {"wartende": 0, "geister": 0, "fremde": 0, "groessen": 0}
    stand["wartende"] = _abgleich_stufe(
        "wartende", wartende_auftraege, z, live, w, still=still)
    if stand["wartende"] and not still:
        print("  %d wartende(r) Auftrag/Auftraege gefuellt und gebucht"
              % stand["wartende"])
    # ERSTE Stufe, und die Reihenfolge ist der Fix (04./05.10.2026): ein
    # Verkauf, den die Boerse bezeugt, muss VOR der Geisterpruefung gebucht
    # werden. Andernfalls sieht die Geisterpruefung eine Position, die an der
    # Boerse fehlt, und bucht sie neutral (Einsatz zurueck, Erloes 0.00) -
    # vier echte Positionen verloren so ueber Nacht ihren Erloes.
    stand["verkaeufe"] = _abgleich_stufe(
        "verkaeufe", buche_verkaeufe_aus_boerse, z, live, still=still)
    if stand["verkaeufe"] and not still:
        print("  %d Verkauf/Verkaeufe von der Boerse gebucht (echter Kurs)"
              % stand["verkaeufe"])
    stand["geister"] = _abgleich_stufe(
        "geister", bueche_geister_aus, z, w, still=still, stornieren=live)
    if stand["geister"] and not still:
        print("  %d Geist(er) aus dem Live-Buch gebucht (kein Bestand an "
              "der Boerse)" % stand["geister"])
    # NUR DIE BASIS uebernimmt Fremdpositionen (Auftrag Max 12.10.2026).
    # Alle drei Risikostufen (niedrig/mittel/hoch) fragen dasselbe Boersenkonto
    # (`okxf.positionen()` kennt keine Stufe). Ohne diese Bedingung holte jede
    # Stufe die Handpositionen in ihr EIGENES Buch und buchte sie spaeter als
    # Geist wieder aus: dieselben Ereignisse standen bis zu dreimal in
    # verschiedenen Journalen, belegten in jedem Buch einen Platz und zaehlten
    # in jeder Kapitalkurve (Drawdown, Kill). Eine Stufe ist ein Messwerkzeug
    # mit Papiergeld und darf nie live gehen (`risikostufe.live_erlaubt`) - es
    # gibt dort keine Boersenposition, die ein Buch fuehren muesste. Die
    # Geisterpruefung oben laeuft weiter: sie raeumt Altbestand ab und ist
    # ohne Live-Positionen im Buch ein No-op.
    if risikostufe.ist_basis():
        stand["fremde"] = _abgleich_stufe(
            "fremde", bueche_fremde_positionen_uebernehmen, z, w, still=still,
            schutz=live)
    else:
        stand["fremde"] = 0
    if stand["fremde"] and not still:
        print("  %d fremde Position(en) von der Boerse ins Buch uebernommen"
              % stand["fremde"])
    stand["groessen"] = len(_abgleich_stufe(
        "groessen", bueche_groessen_abgleichen, z, w, still=still,
        standard=[]))
    if stand["groessen"] and not still:
        print("  %d Position(en) auf die Boersengroesse gezogen"
              % stand["groessen"])
    # Vierte Stufe: die MENGE des Schutzes. Nur lesend - der Preis fuer ein
    # Nachsetzen kommt vom Menschen (T-362). Ein stiller Zwischenstand zaehlt
    # als Befund, damit `--wachen` und die Vorschau die Luecke zeigen.
    deckung, deckung_abfrage = _abgleich_stufe(
        "stopdeckung", bueche_stopdeckung, z, w, live, still=still,
        standard=([], False))
    stand["deckung"] = len(deckung)
    stand["deckung_abfrage"] = deckung_abfrage
    if deckung and not still:
        print("  %d Position(en) OHNE vollen Schutz-Stop (T-323) - kein "
              "Nachsetzen im Zyklus, der Preis ist eine Freigabe" % len(deckung))
    return stand


def _trailing_versuch(p, kurs, w):
    """Den Stop dieser Position nachziehen, wenn der Weg es kann.

    Drei Bedingungen muessen ALLE stimmen, und jede einzelne traegt eine
    Fehlermeldung in den Journal - nicht nach stdout:

    1. Die Wache muss den Trailing ueberhaupt einschalten. Vorgabe ist aus
       (`trailing_aktiv` fehlt), damit keine Spur durch ein vergessenes
       Feld plötzlich nachzieht.
    2. Die Position braucht EINE Boersen-Stop-Kennung. Liegen drei Stops
       auf derselben Position (der HYPE-Fall vom 05.10.2026: 33+22+12 auf
       67 Kontrakte), ist das KEIN Trailing-Fall: der engste Stop feuert
       beim naechsten Tick, die anderen bleiben als Waisen liegen. Solche
       Positionen sagt dieser Weg ab und ruft stopdeckung.py auf.
    3. Der Weg muss `stop_nachziehen` haben - sonst waere es Storno und
       Neuaufbau, mit einem Fenster OHNE Schutz dazwischen.

    Rueckgabe: True, wenn der Stop an der Boerse gewandert wurde.
    """
    # Den Hochstand IMMER pflegen, auch wenn nicht nachgezogen wird - ohne
    # ihn waere der naechste Vergleich gegen einen zu neuen Wert. Deshalb
    # VOR der Aktivitaetspruefung: sonst faellt die Pflege bei einer Spur
    # aus, die den Trailing noch nicht freigeschaltet hat, und der Wert
    # fehlt beim ersten echten Lauf.
    trailing_modul.erst_hoch(p, kurs)
    if not w.get("trailing_aktiv"):
        return False
    boerse_ids = []
    if not p.get("stop_id") and not p.get("stop_ids"):
        # Beim Eroeffnen wird keine Kennung gebucht (der Stop haengt als
        # attachAlgoOrds an der Einstiegsorder und bekommt seine algoId erst
        # beim Fuellen). Ohne diese Nachfrage war Trailing bei JEDER Position
        # tot (gefunden 11.10.2026: ETH, BZ, HYPE). Lesend; im Fehlerfall
        # bleibt es beim Vermerk unten.
        try:
            boerse_ids = [s.get("algoId") for s in
                             okxf.schutz_stops(p.get("inst")) or []
                             if okxf.ist_schutz_stop(s) and s.get("algoId")]
        except Exception:                                   # noqa: BLE001
            pass
    kennungen = [x for x in (p.get("stop_ids") or boerse_ids) if x]
    if len(kennungen) > 1:
        journal(zeit=_jetzt(), modus="live", aktion="vermerkt",
                inst=p.get("inst") or "", seite=p.get("seite") or "",
                preis="%.6f" % kurs, einsatz_usd="", stop="", ziel="",
                stop_pct="",
                grund="trailing nicht ausgefuehrt: %d Boersen-Stops auf "
                      "einer Position (%s) - erst mit stopdeckung.py auf "
                      "einen zusammenfuehren"
                      % (len(kennungen), ", ".join(str(x) for x in kennungen)))
        return False
    kennung = p.get("stop_id") or (kennungen[0] if kennungen else None)
    if not kennung:
        journal(zeit=_jetzt(), modus="live", aktion="vermerkt",
                inst=p.get("inst") or "", seite=p.get("seite") or "",
                preis="%.6f" % kurs, einsatz_usd="", stop="", ziel="",
                stop_pct="",
                grund="trailing nicht ausgefuehrt: keine Boersen-Stop-Kennung "
                      "in der Position (stopdeckung.py / stops_nachziehen.py)")
        return False
    p["stop_id"] = kennung
    tick = _tick_fuer(p.get("inst"))
    # T-365: die Mengen-Deckung ist die ERSTE Bedingung (Referenz
    # trailing-stop-gehebelt.md 5.1: 'erst zusammenfuehren, dann trailingen').
    # Eine Position, deren Schutz-Menge an der Boerse die Buchmenge nicht
    # deckt, ist nicht trailingbar - der engste Stop feuert zuerst, die
    # uebrigen bleiben als Waisen zurueck. stopdeckung.deckung() misst das.
    def _deckung_pruefen(pos):
        try:
            roh = {x["instId"]: x for x in okxf.positionen()}
        except Exception as e:                              # noqa: BLE001
            raise RuntimeError("Boersenfrage fehlgeschlagen (%s)" % e)
        # stopdeckung.okxf auf das okxf DIESER Spur setzen - sonst laedt
        # deckung() das echte okxf (Netzaufruf) statt der Testattrappe.
        stopdeckung.okxf = okxf
        return stopdeckung.deckung(pos, roh)
    ergebnis, grund = trailing_modul.nachziehen(
        p, kurs, okxf, w, liq=float(p.get("liq") or 0.0) or None,
        tick=tick, deckung_pruefen=_deckung_pruefen)
    if ergebnis is None:
        # Kein Trailing ist der NORMALFALL (vor dem Trigger, Hub zu klein,
        # Stop zu nah am Kurs). Das ist kein Fehler und gehoert NICHT ins
        # Journal - sonst waende sich die Auswertung mit jedem Zyklus.
        return False
    alt = float(p.get("stop") or 0.0)
    p["stop"] = float(ergebnis["stop"])
    if ergebnis.get("kennung"):
        p["stop_id"] = ergebnis["kennung"]
    print("    TRAILING %s Stop %.6f -> %.6f (Hoch %.6f, %.2fR)"
          % (p.get("inst"), alt, p["stop"],
             float(ergebnis["hoechstkurs"]), float(ergebnis["hoch_r"])))
    journal(zeit=_jetzt(), modus="live", aktion="trailing",
            inst=p.get("inst") or "", seite=p.get("seite") or "",
            preis="%.6f" % kurs, einsatz_usd="", stop="%.6f" % p["stop"],
            ziel="", stop_pct="",
            grund=("Stop %.6f -> %.6f (Hoch %.6f, %.2fR)"
                   % (alt, p["stop"], float(ergebnis["hoechstkurs"]),
                      float(ergebnis["hoch_r"]))))
    return True


def _tick_fuer(inst):
    """Tick-Groesse des Kontrakts (0.0 = nicht lesbar, dann ungerundet)."""
    try:
        return float(okxf._instrument_tick(inst))
    except Exception:                                              # noqa: BLE001
        return 0.0


def _ist_handposition(p):
    """Eine von Max von Hand an der OKX-Boerse eroeffnete Position.

    ERKENNUNG: Bei der Uebernahme traegt die Position das Feld
    `herkunft == "boerse_handgriff"` (siehe bueche_fremde_positionen_uebernehmen).
    Solche Positionen werden von der Spur NICHT automatisch geschlossen:
    kein Stop, kein Ziel, kein Trailing, kein Kill/Kill-Switch - Max
    verwaltet sie selbst (Auftrag 06.10.2026, Journal-Vermerk
    "das wollte ich"). Die Spur fuehrt sie nur im Buch (Funding, Journal,
    Bilanz) und meldet sie.
    """
    return (p or {}).get("herkunft") == "boerse_handgriff"


def _handpositionen_automatisch_schliessen(w):
    """Schalter in wachen.json: handpositionen_automatisch_schliessen.

    true  = Handpositionen (herkunft=boerse_handgriff) werden wieder automatisch
            geschlossen - Stop/Ziel/Trailing/Kill greifen wie bei jeder Position.
    false/fehlt = sie bleiben stehen (Max verwaltet selbst, Auftrag 06.10.2026).
    """
    return bool((w or {}).get("handpositionen_automatisch_schliessen"))


def pruefe_ausstiege(z, live, w):
    behalten = []
    for p in z["positionen"]:
        # HANDPOSITION (Auftrag 06.10.2026): von Hand eroeffnete OKX-Positionen
        # werden von pruefe_ausstiege NICHT geschlossen. Der NIGHT-Fall:
        # 06.10. 16:31:59 UTC schloss der Haus-Stop eine von Max von Hand
        # eroeffnete XPERP-Position mit grund=stop, obwohl er sie halten
        # wollte (Journal: "ja war meine und das wollte ich"). Handpositionen
        # bleiben stehen - egal wie der Kurs laeuft. Max schliesst sie selbst.
        if _ist_handposition(p) and not _handpositionen_automatisch_schliessen(w):
            behalten.append(p)
            continue
        if not live and p.get("modus") == "live":
            # Siehe flach_stellen: ein Papierlauf schliesst keine echte Position.
            behalten.append(p)
            continue
        try:
            kurs = _kurs_aktuell(p)
        except Exception as e:                           # noqa: BLE001
            print("  Kurs %s nicht abrufbar (%s) - Position bleibt" % (p["inst"], e))
            behalten.append(p)
            continue

        # MAE/MFE ueber die LEBENDAUER messen, nicht erst beim Ausstieg -
        # sonst waere die Zahl der Ausstiegskurs selbst und damit wertlos.
        mae.merke_extrem(p, kurs)

        vz = 1 if p["seite"] == "long" else -1
        grund = None
        # Reihenfolge nach Schwere. Die Liquidation ist kein "darf nicht
        # vorkommen"-Fall: Liegt der Kurs hinter der Liquidationsschwelle, hat
        # er den Stop auf dem Weg dorthin schon durchlaufen - die Schwelle liegt
        # immer hinter dem Stop. Stuende der Stop zuerst, stuende bei einem
        # Totalverlust "stop" im Journal, und die Liquidationszeile waere
        # unerreichbar. Die Rechnung bleibt davon unberuehrt: gerechnet wird mit
        # dem echten Kurs, geschlossen wird unabhaengig vom Grund.
        if p.get("liq") and vz * (kurs - p["liq"]) <= 0:
            grund = "LIQUIDATION"
        elif vz * (kurs - p["stop"]) <= 0:
            grund = "stop"
        elif vz * (kurs - p["ziel"]) >= 0:
            grund = "ziel"

        if not grund and live:
            # TRAILING (Auftrag Max 05.10.2026: "intelligent an den
            # gehebelten Positionen Stop-Loss nachziehen"). Nur im
            # Live-Zweig: ein Papierlauf aendert keinen Boersen-Auftrag.
            # `trailing.stop_nachziehen()` rechnet und ruft die Boerse; ein
            # Fehler laesst den ALTEN Stop stehen (dort ist der Grund nicht
            # Zufall, sondern eine Eigenschaft des Wegs).
            _trailing_versuch(p, kurs, w)

        if not grund:
            behalten.append(p)
            continue

        erloes = _ergebnis(p, kurs)
        gv = erloes - p["margin"]

        if live:
            try:
                okxf.markt_schliessen(p["inst"], p["kontrakte"], p["seite"])
            except Exception as e:                       # noqa: BLE001
                print("  Schliessen %s fehlgeschlagen: %s" % (p["inst"], e),
                      file=sys.stderr)
                behalten.append(p)
                continue

        print("  AUSSTIEG (%s): %s %s @ %.6f  G/V %+.2f USD auf %.2f Margin"
              % (grund, p["inst"], p["seite"], kurs, gv, p["margin"]))
        journal(zeit=_jetzt(), modus="live" if live else "papier",
                aktion="schliessen", inst=p["inst"],
                pos_id=p.get("pos_id", ""), seite=p["seite"],
                familie=p.get("familie", ""), preis="%.6f" % kurs,
                kontrakte=p["kontrakte"], nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.2f" % erloes, hebel=p["hebel"], grund=grund)
        _halte_h = 0.0
        try:
            _dt_start = datetime.fromisoformat(p["eroeffnet_zeit"])
            _halte_h = round((datetime.now(timezone.utc) - _dt_start).total_seconds() / 3600, 1)
        except Exception:  # noqa: BLE001
            pass
        _tracking.track_zyklus_abgeschlossen(
            spur_name="xperp",
            instrument=p["inst"],
            richtung=p["seite"],
            einstieg_kurs=p["einstieg"],
            ausstieg_kurs=kurs,
            ergebnis_pct=round(gv / p["margin"] * 100, 4) if p.get("margin") else 0.0,
            ergebnis_eur=round(gv, 2),
            haltedauer_stunden=_halte_h,
            ausstiegsgrund=grund.lower(),
            is_paper=not live,
            risikostufe=risikostufe.stufe(),
            hebel=p.get("hebel"),
        )
        if grund in ("stop", "LIQUIDATION"):
            z["letzte_stops"][p["basis"]] = _heute()
    z["positionen"] = behalten


def buche_funding(z, live, w):
    """Faelliges Funding je offener Position ins Journal.

    OKX rechnet alle 8 Stunden ab. Gebucht wird, was seit der letzten Buchung
    faellig geworden ist - im Papierlauf gerechnet, live spaeter aus dem
    Ledger nachzutragen. Positiv heisst gezahlt.
    """
    jetzt = datetime.now(timezone.utc)
    for p in z["positionen"]:
        letzte = p.get("funding_zuletzt") or p.get("eroeffnet_zeit")
        if not letzte:
            p["funding_zuletzt"] = _jetzt()
            continue
        stunden = (jetzt - datetime.fromisoformat(letzte)).total_seconds() / 3600
        if stunden < 8:
            continue
        try:
            satz = okxf.funding(p["inst"])
        except Exception:                                # noqa: BLE001
            continue
        if satz is None:
            continue
        perioden = int(stunden // 8)
        vz = 1 if p["seite"] == "long" else -1
        betrag = p["nominal"] * satz * perioden * vz
        p["funding_zuletzt"] = _jetzt()
        p["funding_summe"] = p.get("funding_summe", 0.0) + betrag
        journal(zeit=_jetzt(), modus="live" if live else "papier",
                aktion="funding", inst=p["inst"], seite=p["seite"],
                familie=p.get("familie", ""),
                nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.4f" % betrag,
                funding_pct="%.6f" % satz,
                grund="%d Periode(n) a 8h" % perioden)
        print("  Funding %-22s %+.4f USD (%d x %.4f%%)"
              % (p["inst"], betrag, perioden, satz * 100))


def flach_stellen(z, live, grund, w=None):
    """Alle Positionen sofort schliessen - Bedingung 2 und 3.

    ECHTE POSITIONEN GEHOEREN DEM LIVE-LAUF (21.09.2026): Laeuft die Spur im
    Papier (kein Freigabefenster oder handel_erlaubt=false) und loest dabei der
    Kill-Switch aus, schloss diese Funktion BISHER auch Positionen mit
    modus=live - aber nur im BUCH. An der Boerse blieb die Position offen.
    Genau das ist am HBAR passiert: um 20:52 stand "papier,schliessen,grund
    kill_switch" im Journal, waehrend /account/positions die 9.4 Kontrakte
    unveraendert hielt. Ergebnis: eine echte, gehebelte Position ohne Buch -
    kein Ausstieg, kein Funding, keine Bilanz.

    Deshalb: im Papierlauf bleiben Positionen mit modus=live stehen und werden
    ausdruecklich gemeldet. Geschlossen werden sie nur vom Live-Lauf.

    HANDPOSITIONEN (Auftrag 06.10.2026): Positionen mit herkunft==
    "boerse_handgriff" (von Max von Hand an der OKX-Boerse eroeffnet) werden
    auch vom Kill/Notaus NICHT geschlossen - weder im Papier- noch im
    Live-Lauf. Sie gehoeren Max, nicht der Spur; er verwaltet sie selbst.
    """
    behalten = []
    for p in z["positionen"]:
        if _ist_handposition(p) and not _handpositionen_automatisch_schliessen(w):
            print("  %s bleibt im Buch: Handposition (herkunft=boerse_handgriff)"
                  " wird auch von %s nicht geschlossen (Max verwaltet selbst)"
                  % (p.get("inst"), grund))
            behalten.append(p)
            continue
        if not live and p.get("modus") == "live":
            print("  %s bleibt im Buch: echte Position (modus=live) wird nur "
                  "vom Live-Lauf geschlossen" % p.get("inst"))
            behalten.append(p)
            continue
        try:
            kurs = _kurs_aktuell(p)
        except Exception as e:                           # noqa: BLE001
            print("  Notausstieg %s: Kurs nicht abrufbar (%s)" % (p["inst"], e),
                  file=sys.stderr)
            behalten.append(p)
            continue
        if live:
            try:
                okxf.markt_schliessen(p["inst"], p["kontrakte"], p["seite"])
            except Exception as e:                       # noqa: BLE001
                print("  Notausstieg %s fehlgeschlagen: %s" % (p["inst"], e),
                      file=sys.stderr)
                behalten.append(p)
                continue
        erloes = _ergebnis(p, kurs)
        print("  AUSSTIEG (%s): %s %s @ %.6f  G/V %+.2f USD"
              % (grund, p["inst"], p["seite"], kurs, erloes - p["margin"]))
        journal(zeit=_jetzt(), modus="live" if live else "papier",
                aktion="schliessen", inst=p["inst"],
                pos_id=p.get("pos_id", ""), seite=p["seite"],
                familie=p.get("familie", ""), preis="%.6f" % kurs,
                kontrakte=p["kontrakte"], nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.2f" % erloes, hebel=p["hebel"], grund=grund)
    z["positionen"] = behalten


# --- Einstieg ---------------------------------------------------------------

def in_abklingzeit(basis, z, w):
    tag = z.get("letzte_stops", {}).get(basis)
    if not tag:
        return False
    d = (datetime.now(timezone.utc).date()
         - datetime.fromisoformat(tag).date()).days
    return d < w.get("abklingzeit_tage", 3)


def papier_w(w, live):
    """Papier-Vergroesserung: skaliert die Sizing-Werte NUR im Papierlauf.

    `papier_faktor` (wachen.json, hier 4.0) vergroessert die Positionsgroesse
    im Papier, damit die Freigabe-Kriterien (netto_positiv, groesster
    Ruecklauf) aussagekraeftigere Werte liefern. Live bleibt bei den echten
    Werten. Die Runden-ZAHL (Bedingung 1, 50 Runden) aendert das nicht - ein
    Zaehler, keine Groesse.
    """
    if live:
        return w
    pf = w.get("papier_faktor", 1.0)
    if pf == 1.0:
        return w
    w2 = dict(w)
    for k in ("risiko_je_anlauf_usd", "max_margin_je_anlauf_usd",
              "max_margin_gesamt_usd"):
        if k in w2:
            w2[k] = w2[k] * pf
    return w2


def pruefe_einstiege(z, kand, w, live, s, faktor=1.0):
    w = papier_w(w, live)

    # WARTENDE AUFTRAEGE BELEGEN EINEN PLATZ (gemessen 21.09.2026).
    # Vorher zaehlte hier nur z["positionen"]. Ein Limit hinter dem
    # Markt wird aber als WARTENDER Auftrag gefuehrt und ist noch
    # keine Position - nach dem Stellen war fuer Platz, Margin und
    # Familie alles unveraendert, und der naechste Zyklus legte fuer
    # denselben Basiswert nach. Ergebnis an der Boerse: 13 offene
    # Limit-Auftraege, CL sechsmal und XAU fuenfmal, aus einem
    # einzigen Abend. Ein wartender Auftrag bindet denselben Platz,
    # dieselbe Margin und denselben Familienanteil wie die Position,
    # die aus ihm wird.
    wartend = [a for a in (z.get("wartende") or [])
               if isinstance(a, dict)]
    belegt = list(z["positionen"]) + wartend

    offen = {p.get("basis") for p in belegt}
    margin_gebunden = sum(float(p.get("margin") or 0.0) for p in belegt)
    fam_stand = wx.familien_belegung(belegt, w)
    wochenende_gesperrt = s["wochenende"]

    for kandidat in kand:
        if len(belegt) >= w["max_offene_anlaeufe"]:
            return
        # Signal-Wechsel-Gatter (03.10.2026, Auftrag Max "Erweitern"): ein
        # Einstieg nur, wenn sich die Richtung fuer diese Basis seit dem
        # letzten Einstieg geaendert hat. Es steht VOR `anlauf()`, also vor
        # jedem Orderaufruf - ein Gatter hinter der Order waere bei Live
        # genau ein Zyklus zu spaet.
        #
        # Der Schluessel ist die BASIS, nicht das Instrument: derselbe
        # Markt erscheint als XBT-USD und als BTC-USD-um_XPERP. Am
        # Instrument-Schluessel wuerde jeder Richtungswechsel als Wechsel
        # zaehlen und die Regel waere wirkungslos.
        if zugelassen(z, w, kandidat["basis"], kandidat["seite"]) is not ERLAEUT:
            continue
        if kandidat["basis"] in offen or in_abklingzeit(kandidat["basis"], z, w):
            continue

        # Wochenende: keine neuen Anlaeufe in Familien, deren Basiswert
        # nicht handelt. Der Kontrakt liefe weiter, das Gap zum Wochenstart
        # traegt trotzdem niemand.
        if wochenende_gesperrt and kandidat["kategorie"] in ("aktie", "rohstoff"):
            continue

        fam = fam_stand.get(kandidat["kategorie"])
        if fam and fam["voll"]:
            continue

        a = anlauf(w, kandidat)
        if not a:
            continue

        g = a["groesse"]
        margin = g["margin"] * faktor
        kontrakte = g["kontrakte"]
        if faktor != 1.0:
            kontrakte, nominal = okxf.kontrakte_aus_nominal(
                a["instr"], g["nominal"] * faktor, a["einstieg"])
            if kontrakte <= 0:
                continue
            g = dict(g, kontrakte=kontrakte, nominal=nominal,
                     margin=nominal / g["hebel"])
            margin = g["margin"]

        if margin_gebunden + margin > w["max_margin_gesamt_usd"]:
            continue

        p = a["pflicht"]
        # Die Pruefpflicht ist keine Zierde: Traegt die Trefferquote die
        # Kosten nicht, wird nicht eroeffnet. Das ist die Umsetzung der
        # Grundlinie aus Wissen/Handelsbots.md im Automaten - dort lagen
        # noetige und erreichte Quote immer ein bis zwei Punkte auseinander.
        if not p.get("traegt"):
            print("  -- %-10s %-5s: Trefferquote traegt die Kosten nicht "
                  "(noetig %s, beobachtet %s) - kein Anlauf" % (
                      a["basis"], a["seite"],
                      "n/a" if p["quote_noetig"] is None
                      else "%.1f%%" % (p["quote_noetig"] * 100),
                      "n/a" if p["quote_beobachtet"] is None
                      else "%.1f%%" % (p["quote_beobachtet"] * 100)))
            continue
        if not p.get("hebel_traegt"):
            print("  -- %-10s %-5s: Hebel %.1fx ueber Deckel %.1fx - kein Anlauf"
                  % (a["basis"], a["seite"], p["hebel"], p["hebel_deckel"]))
            continue

        ord_antwort = None
        o_preis = a["einstieg"]          # live ggf. von maker_preis verbessert
        if live:
            try:
                okxf.hebel_setzen(a["inst"], g["hebel"])
                # Stop und Ziel gehen MIT der Order an die Boerse, nicht nur
                # in zustand.json. Das ist der "nicht abschaltbare Stop" aus
                # den Handelsregeln, woertlich genommen: Ein Stop, der nur
                # hier steht, ist weg, sobald dieser Rechner weg ist - und
                # die Kernel-Power-41-Abschaltungen aus Wissen/Hardware.md
                # nehmen ihn ohne Vorwarnung mit. Eine gehebelte Position
                # ohne boersenseitigen Stop laeuft dann bis zur Liquidation.
                # Bestpreis-Ausfuehrung (11.10.2026): nie ueber den Spread,
                # post_only = nur Maker-Gebuehr. Siehe okxf.maker_preis.
                o_seite = "buy" if a["seite"] == "long" else "sell"
                _, bid, ask = okxf.kurs_und_spanne(a["inst"])
                o_preis = okxf.maker_preis(o_seite, a["einstieg"], bid, ask)
                ord_antwort = okxf.order_limit(
                    a["inst"], o_seite, kontrakte, o_preis,
                    tp=a["ziel"], sl=a["stop"], post_only=True)
            except Exception as e:                       # noqa: BLE001
                print("  Eroeffnen %s fehlgeschlagen: %s" % (a["inst"], e),
                      file=sys.stderr)
                continue

        if live:
            # ERST die Fuellung, dann das Buch. Eine angenommene Order ist
            # keine Position (siehe _warten_auf_fuellung).
            gehandelt = _warten_auf_fuellung(a["inst"], ord_antwort, kontrakte)
            if not gehandelt:
                # Kann das Limit hier ueberhaupt fillen? Ein Kauflimit unter
                # dem Ask ist eine WARTENDE Order (der Einstieg kommt aus der
                # Zonenrechnung), kein Fehler.
                # Gegen den TATSAECHLICHEN Orderpreis pruefen: maker_preis kann
                # ihn auf Bid/Ask gesetzt haben (post_only wartet dann im Buch).
                _, bid, ask = okxf.kurs_und_spanne(a["inst"])
                marktbar = False
                if ask and bid:
                    if a["seite"] == "long":
                        marktbar = o_preis >= ask
                    else:
                        marktbar = o_preis <= bid
                if not marktbar:
                    print("  Eroeffnen %s: Limit %.6f liegt hinter dem Markt "
                          "(bid %s / ask %s) und wartet - Auftrag bleibt liegen"
                          % (a["inst"], o_preis, bid, ask))
                    z.setdefault("wartende", []).append({
                        "inst": a["inst"], "basis": a["basis"], "seite": a["seite"],
                        "familie": a["kategorie"], "einstieg": o_preis,
                        "stop": a["stop"], "ziel": a["ziel"], "liq": g["liq"],
                        "kontrakte": kontrakte, "nominal": g["nominal"],
                        "margin": g["margin"], "hebel": g["hebel"],
                        "gebuehr_taker": w["gebuehr_taker"],
                        "ord_id": ord_antwort, "gestellt": _jetzt(),
                    })
                    journal(zeit=_jetzt(), modus="live", aktion="order_offen",
                            inst=a["inst"], seite=a["seite"],
                            familie=a["kategorie"], preis="%.6f" % o_preis,
                            kontrakte=kontrakte,
                            nominal_usd="%.2f" % g["nominal"],
                            margin_usd="%.2f" % g["margin"],
                            stop="%.6f" % a["stop"], ziel="%.6f" % a["ziel"],
                            grund="limit_wartet")
                    continue
                print("  Eroeffnen %s: Order war marktbar (Limit %.6f gegen "
                      "ask %s), ist aber NICHT gefuellt - wird storniert"
                      % (a["inst"], o_preis, ask), file=sys.stderr)
                try:
                    okxf.order_stornieren(a["inst"], ord_antwort)
                except Exception as e:                         # noqa: BLE001
                    print("  Storno %s fehlgeschlagen: %s" % (a["inst"], e),
                          file=sys.stderr)
                journal(zeit=_jetzt(), modus="live", aktion="fehler",
                        inst=a["inst"], seite=a["seite"],
                        familie=a["kategorie"], preis="%.6f" % o_preis,
                        kontrakte=kontrakte,
                        nominal_usd="%.2f" % g["nominal"],
                        margin_usd="%.2f" % g["margin"],
                        grund="order_nicht_gefuellt")
                continue
            if gehandelt < kontrakte:
                # Teilverfuellung: den Rest stornieren, nur das Gehandelte buchen.
                print("  Eroeffnen %s: nur %.4f von %g Kontrakten gefuellt - "
                      "Rest wird storniert" % (a["inst"], gehandelt, kontrakte))
                try:
                    okxf.order_stornieren(a["inst"], ord_antwort)
                except Exception as e:                         # noqa: BLE001
                    print("  Storno %s fehlgeschlagen: %s" % (a["inst"], e),
                          file=sys.stderr)
                kontrakte = gehandelt
                g["nominal"] = gehandelt * (o_preis / max(a["hebel"], 1e-9))

        pos = {
            "inst": a["inst"], "basis": a["basis"], "seite": a["seite"],
            "familie": a["kategorie"], "einstieg": o_preis,
            "stop": a["stop"], "ziel": a["ziel"], "liq": g["liq"],
            "kontrakte": kontrakte, "nominal": g["nominal"],
            "margin": g["margin"], "hebel": g["hebel"],
            "gebuehr_taker": w["gebuehr_taker"],
            # WOHER DIESE POSITION KOMMT. Bis zum 21.09.2026 stand hier nichts -
            # damit liess sich im Buch nicht unterscheiden, ob eine Position echt
            # an der Boerse liegt oder aus dem Papierlauf stammt (genau der
            # Zustand, den das Aufraeumen unten bereinigt).
            "modus": "live" if live else "papier",
            "ord_id": str(ord_antwort)[:40] if live and ord_antwort else "",
            # Die Kennung dieser Position (T-095): sie entsteht beim
            # Einstieg und steht in JEDER Zeile dieser Position.
            "pos_id": pos_kennung.neu(_jetzt()),
            "eroeffnet": _heute(), "eroeffnet_zeit": _jetzt(),
            "funding_zuletzt": _jetzt(), "funding_summe": 0.0,
        }
        z["positionen"].append(pos)
        margin_gebunden += g["margin"]
        offen.add(a["basis"])
        fam_stand = wx.familien_belegung(z["positionen"], w)

        print("  AUF %-22s %-5s @ %.6f  %g Kontrakte, %.1fx, "
              "%.2f Margin (%.2f nominal)" % (
                  a["inst"], a["seite"], o_preis, kontrakte,
                  g["hebel"], g["margin"], g["nominal"]))
        # Instrument und Seite stehen auch hier. Der Dauerlauf meldet jede
        # Zeile mit dem Wort Stop einzeln nach Telegram - eine
        # Fortsetzungszeile ohne Subjekt ist dort nicht zuzuordnen. Die
        # anderen Spuren nennen den Wert in derselben Zeile.
        print("      %-22s %-5s  Stop %.6f (%.2f%%)  Ziel %.6f  Liq %.6f "
              "(%.1f%% weg)"
              % (a["inst"], a["seite"], a["stop"], g["abstand"] * 100,
                 a["ziel"], g["liq"], p["liq_abstand"] * 100))
        print("      %-22s %-5s  Pflicht: Funding %s, Gebuehr %.3f%%, "
              "Quote noetig %.1f%% / beobachtet %.1f%%"
              % (a["inst"], a["seite"],
                 "n/a" if p["funding_pct"] is None
                 else "%+.3f%%" % (p["funding_pct"] * 100),
                 p["gebuehren_pct"] * 100, p["quote_noetig"] * 100,
                 p["quote_beobachtet"] * 100))

        journal(zeit=_jetzt(), modus="live" if live else "papier",
                aktion="eroeffnen", inst=a["inst"],
                pos_id=pos["pos_id"], seite=a["seite"],
                familie=a["kategorie"], preis="%.6f" % o_preis,
                kontrakte=kontrakte, nominal_usd="%.2f" % g["nominal"],
                margin_usd="%.2f" % g["margin"], hebel="%.2f" % g["hebel"],
                stop="%.6f" % a["stop"], ziel="%.6f" % a["ziel"],
                liq="%.6f" % g["liq"],
                liq_abstand="%.4f" % p["liq_abstand"],
                funding_pct=("" if p["funding_pct"] is None
                             else "%.6f" % p["funding_pct"]),
                gebuehr_pct="%.6f" % p["gebuehren_pct"],
                quote_noetig="%.4f" % p["quote_noetig"],
                quote_beob="%.4f" % p["quote_beobachtet"],
                grund="punkte %.1f, %s" % (a["punkte"], a["grund"]))
        _tracking.track_position_eroeffnet(
            spur_name="xperp",
            instrument=a["inst"],
            richtung=a["seite"],
            einstieg_kurs=o_preis,
            stop_kurs=a["stop"],
            ziel_kurs=a["ziel"],
            nominal_eur=g["nominal"],
            is_paper=not live,
            risikostufe=risikostufe.stufe(),
            hebel=g.get("hebel"),
        )


# --- Wachen -----------------------------------------------------------------

def _spiegeln(w, z=None):
    """Bedingung 4: Journal und Zustand ausser Haus.

    Mit uebergebenem Zustand wird das Ergebnis auch dort vermerkt
    (journal_zweitziel_ok/_info) - nur beim Wechsel, und die Kopie wird
    danach einmal nachgezogen. Ohne diesen Vermerk ist eine ausgefallene
    Kopie unsichtbar: der Dauerlauf protokolliert bei Rueckgabe 0 nur "ok",
    und die Spurausgabe zeigt er nicht. Dieselbe Rechnung wie in
    swap/handeln.py - nicht eine zweite Fassung derselben Sache.
    """
    ziel = w.get("journal_zweitziel")
    if not ziel:
        return "-- (journal_zweitziel nicht gesetzt)"
    # spiegele_journal liefert (ok, Grund-oder-Pfad) - hier auf eine Zeile
    # bringen, damit die Aufrufer sie direkt ausgeben koennen.
    ok, info = wx.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if z is not None and wx.vermerke_spiegelung(z, ziel, ok, info,
                                                schreibe_zustand) and ok:
        # Der Vermerk ist juenger als die Kopie: einmal nachziehen.
        wx.spiegele_journal([ZUSTAND], ziel)
    return info if ok else "fehlgeschlagen: %s" % info


def zeige_wachen(w):
    z = lade_zustand()
    s = wx.lage(w, JOURNAL, z)
    print("=== Wachen-Status XPERP  %s ===" % _jetzt())
    # Die Rundenzahl fuer Bedingung 1 zaehlt Handelsrunden, nicht Buchungen:
    # ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung. Die Kurve
    # (Ruecklauf unten) bleibt ungefiltert - sie ist gebucht.
    print("  1 Freigabe erfuellt      %s   (Handelsrunden %d, davon Papier %d, "
          "dazu %d Betriebsstoerung(en), seit %s)"
          % (s["freigabe_erfuellt"], s["runden_echt"], s["runden_papier_echt"],
             s["runden_stoerung"], s["erste_runde"] or "-"))
    print("  2 Ruecklauf              %.2f USD von Hoechststand %.2f  -> Faktor %.2f"
          % (s["ruecklauf_usd"], s["hoechststand_usd"], s["groessenfaktor"]))
    print("  3 Herzschlag frisch      %s   (%s min alt, Grenze %d)"
          % (s["herzschlag_frisch"],
             "?" if s["herzschlag_alter_min"] is None
             else "%.0f" % s["herzschlag_alter_min"],
             w.get("herzschlag_max_minuten", 30)))
    print("  4 Journal-Zweitziel      %s"
          % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  5 Rollierender EV        %s"
          % ("n/a (zu wenig Runden)" if s["rollierender_ev"] is None
             else "%+.3f USD" % s["rollierender_ev"]))
    print("  + Funding gesamt         %+.2f USD" % s["funding_gesamt"])
    print("  + Wochenende             %s"
          % ("ja - keine neuen Aktien/Rohstoffe" if s["wochenende"] else "nein"))
    for name, f in s["familien"].items():
        print("    %-9s %6.2f von %6.2f USD Margin%s"
              % (name, f["margin"], f["grenze"], "  VOLL" if f["voll"] else ""))
    print()
    print("  Journal ausser Haus:  %s" % _spiegeln(w, z))

    if s["kill"]:
        print()
        print("  KILL-SWITCH erreicht - der naechste Lauf stellt flach.")
    if s["ev_negativ"] and w.get("handel_erlaubt") and not _ev_sperre_entfaellt(w):
        if wx.sperre_zu("rollierender EV %.3f USD < 0" % s["rollierender_ev"]):
            print("  EV negativ -> handel_erlaubt auf false gesetzt.")


# --- Hauptlauf --------------------------------------------------------------

def _ev_sperre_entfaellt(w):
    """Vermerk _ev_entfaellt in wachen.json (Bedingung 5, Auftrag Max 11.10.2026).

    true/gesetzt = die EV-Sperre greift nicht mehr - die Spur laeuft auch bei
    negativem rollierendem EV live. freigabe.erfuellt bleibt der Haken.
    """
    return bool((w or {}).get("_ev_entfaellt"))


def sperren_live(w, s):
    """Alles, was --live gerade verschliesst. Leere Liste = frei."""
    g = []
    if not risikostufe.live_erlaubt():
        # Eine Risikostufe geht NIE live (siehe risikostufe.live_erlaubt): ihre
        # groesseren Betraege sind zum Messen da, und ihr Buch ist getrennt -
        # live gehandeltes Geld stuende in keiner Auswertung. Der Grund traegt
        # bewusst NICHT das Wort Freigabefenster: sonst haelt der Dauerlauf ihn
        # fuer eine Fenster-Bitte und fragt nach einer Freigabe, die es in
        # einer Stufe gar nicht geben darf.
        g.append("Risikostufe %s: kein Live-Pfad in einer Stufe"
                   % risikostufe.stufe())
    if not w.get("handel_erlaubt"):
        g.append("wachen.json handel_erlaubt=false")
    if not okxf.schluessel_vorhanden():
        g.append("OKX-Schluessel nicht gesetzt")
    if not s["freigabe_erfuellt"]:
        g.append("freigabe.erfuellt=false (Bedingung 1)")
    if not s["herzschlag_frisch"]:
        g.append("Herzschlag alt (Bedingung 3)")
    if s["ev_negativ"] and not _ev_sperre_entfaellt(w):
        g.append("rollierender EV %.3f USD < 0 (Bedingung 5)"
                 % s["rollierender_ev"])
    if w.get("journal_zweitziel") is None:
        g.append("journal_zweitziel nicht gesetzt (Bedingung 4)")

    # Punkt 3 der Handelsregeln, in der Fassung fuer den Dauerbetrieb: Ohne
    # offenes Zeitfenster ist nichts scharf. Ein Zeitplan legt den Schalter
    # nicht um, und ein Dauerlauf ist nur ein sehr enger Zeitplan.
    try:
        import freigabefenster
        if not freigabefenster.lade("xperp").offen():
            g.append("kein offenes Freigabefenster (Handelsregeln Punkt 3)")
    except ImportError:
        g.append("freigabefenster.py nicht erreichbar")
    return g


def stopluecken_sperre(z, stand, live):
    """True, wenn neue Live-Einstiege wegen fehlender Boersen-Stops ruhen.

    ANLASS (Review 09.10.2026): `bueche_stopdeckung` misst ungeschuetzte
    Kontrakte, aber nichts wertete das aus - `lauf()` verwarf den Rueckgabewert,
    die Luecke stand nur auf der Konsole. Jetzt gilt (Variante A):
      * Luecke (`deckung > 0`): keine neuen Einstiege im Live-Lauf. Ausstiege,
        Abgleich, Kill und Herzschlag laufen unveraendert weiter; nachgesetzt
        wird weiterhin nur von Hand (`stopdeckung.py --stop`, der Preis ist
        eine Freigabe).
      * Abfrage nicht lesbar (`deckung_abfrage` falsch): KEINE Sperre. Ein
        Netzfehler ist Rauschen, aus ihm folgt kein "kein Stop".
    Gemeldet wird beim Wechsel (Luecke neu / Luecke weg), nicht in jedem Zyklus;
    der Merker liegt im Zustand (`stopluecke_gemeldet`).
    """
    luecke = bool(live and stand and stand.get("deckung")
                  and stand.get("deckung_abfrage"))
    gemeldet = bool(z.get("stopluecke_gemeldet"))
    if luecke and not gemeldet:
        z["stopluecke_gemeldet"] = True
        ereignis.hinweis(
            "handel/xperp",
            "Stop-Luecke: %d Live-Position(en) ohne vollen Boersen-Stop - "
            "neue Einstiege gesperrt. Nachsetzen: stopdeckung.py --anwenden "
            "--stop <preis>" % stand["deckung"])
    elif not luecke and gemeldet and stand and stand.get("deckung_abfrage"):
        z["stopluecke_gemeldet"] = False
        ereignis.hinweis("handel/xperp",
                         "Stop-Luecke geschlossen: Einstiege wieder frei.")
    return luecke


def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = bot.wachen()

    if modus == "wachen":
        zeige_wachen(w)
        return

    z = lade_zustand()
    s = wx.lage(w, JOURNAL, z)

    live = False
    if modus == "live":
        g = sperren_live(w, s)
        if g:
            print("--live angefordert, aber gesperrt: " + "; ".join(g))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    werte, alter = rangliste(z, still=True)
    kand = kandidaten(werte, w)
    print("=== XPERP handeln (%s) | %d Werte, %d Kandidaten | Rangliste %.0f min alt ==="
          % ("LIVE" if live else "Papier", len(werte), len(kand), alter))

    if modus == "vorschau":
        for kandidat in kand[:10]:
            print("  %-10s %-5s Punkte %.1f  Deckel %.1fx  (%s)"
                  % (kandidat["basis"], kandidat["seite"], kandidat["punkte"],
                     kandidat["deckel"], kandidat["kategorie"]))
        gebunden = sum(p["margin"] for p in z["positionen"])
        print("\nOffener Bestand: %d Positionen, %.2f von %g USD Margin"
              % (len(z["positionen"]), gebunden, w["max_margin_gesamt_usd"]))
        g = sperren_live(w, s)
        if g:
            print("Live waere gesperrt durch: " + "; ".join(g))
        # Bewusst KEIN schreibe_zustand: eine Vorschau schreibt nicht (so
        # halten es omniquant, spiegel und nautilus). Vorher setzte jeder
        # Vorschau-Lauf einen frischen Herzschlag - und weil der Dauerlauf
        # jede Spur zusaetzlich mit --vorschau abfragt, war die Kopie auf Q:
        # danach scheinbar aelter als der eigene Zustand.
        return

    z["modus"] = "live" if live else "papier"
    if live:
        # ERST aufraeumen, dann handeln: ein Live-Lauf uebernimmt kein Papierbuch.
        n_alt = bueche_papier_altlasten_aus(z, w, still=False)
        if n_alt:
            print("  %d Papier-Altlast(en) aus dem Live-Buch gebucht" % n_alt)
    # BUCH GEGEN BOERSE - in JEDEM Zyklus (T-277, 01.10.2026).
    # Vorher standen diese vier Schritte im `if live:`-Zweig. Folge: solange
    # xperp Papier lief (seit 29.09.2026 12:00), erreichte kein Handgriff aus
    # der App das Buch - es fuehrte vier Positionen und zwei wartende
    # Auftraege, waehrend an der Boerse EINE stand. Der Abgleich ist
    # Buchhaltung, keine Handelsentscheidung; im Papierlauf stellt er keinen
    # Stop und storniert nichts (siehe buche_abgleich).
    stand = buche_abgleich(z, w, live, still=False)
    # Bedingung 2 - Kill-Switch.
    if s["kill"]:
        print("- KILL-SWITCH: Ruecklauf %.2f USD >= %g -> Notausstieg + Sperre -"
              % (s["ruecklauf_usd"], w["kill_switch_gesamt_usd"]))
        flach_stellen(z, live, "kill_switch", w)
        if wx.sperre_zu("kill_switch: Ruecklauf %.2f USD" % s["ruecklauf_usd"]):
            print("  wachen.json handel_erlaubt -> false")
        schreibe_zustand(z)
        if w.get("journal_zweitziel"):
            _spiegeln(w, z)
        return

    # Bedingung 3 - Herzschlag alt. Deckt die Kernel-Power-41-Abschaltungen
    # ab: eine Position, die einen Neustart "ueberlebt", ist unbewacht.
    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel dieser Lauf -"
              % ("?" if s["herzschlag_alter_min"] is None
                 else "%.0f" % s["herzschlag_alter_min"],
                 w.get("herzschlag_max_minuten", 30)))
        flach_stellen(z, live, "herzschlag_alt", w)
        z["modus"] = "papier"
        schreibe_zustand(z)
        if w.get("journal_zweitziel"):
            _spiegeln(w, z)
        return

    buche_funding(z, live, w)
    pruefe_ausstiege(z, live, w)

    faktor = s["groessenfaktor"]
    if faktor != 1.0:
        print("- Drawdown-Ratsche: Ruecklauf %.2f USD -> Positionen halbiert -"
              % s["ruecklauf_usd"])
    if stopluecken_sperre(z, stand, live):
        print("- Stop-Luecke: neue Einstiege gesperrt, Ausstiege laufen weiter -")
    else:
        pruefe_einstiege(z, kand, w, live, s, faktor)

    gebunden = sum(p["margin"] for p in z["positionen"])
    print("\nBestand: %d Positionen, %.2f von %g USD Margin gebunden"
          % (len(z["positionen"]), gebunden, w["max_margin_gesamt_usd"]))
    schreibe_zustand(z)
    if w.get("journal_zweitziel"):
        print("Journal ausser Haus: %s" % _spiegeln(w, z))


def main():
    # xperp/handeln.py ist der automatische Einstieg (dauerlauf.py ruft
    # dieses Skript per subprocess auf, siehe zyklus_spur/nur_fenster_fehlt)
    # - genau wie orb/handeln.py und scanner/handeln.py meldet es sich damit
    # am Bus. bot.py importiert dieses Modul nie und ruft main() hier nie
    # auf; umgekehrt importiert handeln.py bot nur als Rechenmodul und ruft
    # bot.main() nie auf (siehe Kopfkommentar) - beide Meldewege laufen
    # deshalb nie im selben Prozess zusammen, keine Doppelmeldung moeglich.
    with ereignis.lauf("handel/xperp"):
        return _main()


def _main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier")
    g.add_argument("--live", action="store_const", dest="modus", const="live")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen")
    a = p.parse_args()
    lauf(a.modus or "papier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
