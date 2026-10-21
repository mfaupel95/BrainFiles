"""Live-Pfad der SWAP-Spur: Einstiege, Ausstiege, Funding, Journal, Zustand.

Dritte Spur neben scanner (Spot) und xperp (XPERP). Seit 12.09.2026 ist die
Spur live-faehig - nach xperp-Muster, mit derselben Freigabekette. Scharf
wird sie nur, wenn ein Mensch ein Freigabefenster oeffnet (Bildschirmfenster
freigabe.py oder Zeitfenster freigabefenster.py via /ja_swap im Dauerlauf) UND
alle sieben Sperren offen sind. Ohne Fenster bleibt jeder Lauf Papier.

WAS SIE UEBERNIMMT (importiert, nicht kopiert)
---------------------------------------------
Rechnungen:  bot.groesse(), bot.pruefpflicht(), bot.BAR
Kennzahlen:  indikatoren.lage()
Zugang:      okxf - Kerzen, Kurse, Ticker, Funding, kontrakte_aus_nominal,
             auf_tick und, im Live-Zweig, hebel_setzen/order_limit/markt_schliessen
Wachen:      wachen_xperp.lage() - Drawdown, Familienbelegung, Wochenende,
             Kill-Switch, rollierender Erwartungswert
Freigabe:    freigabefenster.py - das Zeitfenster, Handelsregeln Punkt 3
Vorrat:      swap/kandidaten.py - dieselbe Kandidatenform wie xperp/auswahl.py,
             nur ueber instType=SWAP

DREI DINGE, DIE ANDERS SIND ALS BEI XPERP
-----------------------------------------
1. Gehandelt wird der XPERP-Kontrakt, nicht der gewoehnliche Perpetual. Auf
   diesem Konto ist nur der XPERP-Zweig handelbar: XAU-USDT-SWAP antwortet auf
   eine Order mit OKX 50124 'does not have trading permission for the market'
   (gemessen am 25.09.2026), waehrend XAU-USD_UM_XPERP-310502 am 24.09.2026 mit
   93 Kontrakten gefuellt wurde. Die Reihen des Vorrats tragen ihren Zwilling
   als handels_instr mit (kandidaten.handels_kontrakte); fehlt er, faellt die
   Reihe aus der Liste.
2. Die Wachen kommen aus swap/wachen.json. bot.wachen() liest die Datei aus
   dem xperp-Ordner - wer sie hier benutzt, handelt nach fremden Grenzen.
3. Der Sperrgrund fuer das Fenster lautet wie in xperp: "kein offenes
   Freigabefenster (Handelsregeln Punkt 3)". Daran haengt
   dauerlauf.nur_fenster_fehlt: genau ein Grund, der dieses Wort traegt,
   und der Dauerlauf stellt die Anfrage. Stehen mehrere Gruende, wird nicht
   gefragt.

BOERSENSEITIGER STOP: Im Live-Zweig gehen Stop und Ziel MIT der Order an die
Boerse (order_limit mit tp/sl). Ein Stop, der nur in zustand.json steht, ist
weg, sobald dieser Rechner weg ist - und die Kernel-Power-41-Abschaltungen aus
Wissen/Hardware.md nehmen ihn ohne Vorwarnung mit.

Aufruf:
    python handeln.py --vorschau   # was waere dran, ohne zu schreiben
    python handeln.py --papier     # Papierlauf mit Journal
    python handeln.py --live       # scharf, wenn alle sieben Sperren offen
    python handeln.py --wachen     # Bedingungen als Momentaufnahme
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
XPERP = os.path.join(HANDEL, "xperp")
BUS = os.path.join(HIER, os.pardir, os.pardir, "Bus")
for p in (HIER, XPERP, HANDEL, BUS):
    if p not in sys.path:
        sys.path.insert(0, p)

# pos_kennung liegt im Handel-Ordner. Der eigene Spurenordner ist beim
# Start sys.path[0], darum wird der Ordner ANGEHAENGT (nicht vorne
# eingefuegt - ein Eintrag vorne koennte ein gleichnamiges Spurenmodul
# verdecken, siehe Handel/grid.py neben gitter/grid.py).
_handel_ordner = os.path.dirname(          # Handel/, nicht der Spurenordner
    os.path.dirname(os.path.abspath(__file__)))
if _handel_ordner not in sys.path:
    sys.path.append(_handel_ordner)
import pos_kennung
import ereignis                                                # noqa: E402
import auswahl                                                 # noqa: E402
import bot                                                     # noqa: E402
import freigabefenster                                         # noqa: E402
import indikatoren                                              # noqa: E402
import kandidaten                                              # noqa: E402
import okxf                                                    # noqa: E402
import wachen_xperp as wx                                      # noqa: E402
import telemetrie                                              # noqa: E402

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

# Dieselben Spalten wie xperp. Ein zweites Schema waere der Anfang zweier
# Auswertungen, die sich nicht mehr vergleichen lassen.
SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "familie", "preis",
           "kontrakte", "nominal_usd", "margin_usd", "hebel", "stop", "ziel",
           "liq", "liq_abstand", "funding_pct", "gebuehr_pct",
           "quote_noetig", "quote_beob", "grund", "pos_id"]

# Wie bei xperp: die Rangliste wird zwischengelagert, weil ein voller Scan
# Minuten kostet. Sie steht auf 4H-Kerzen und aendert sich nicht im Takt.
SCAN_ALTER_MINUTEN = 120


# --- Zeit, Zustand, Journal -------------------------------------------------

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
    """Schreibt den Zustand und setzt damit den Herzschlag (letzter_lauf).

    wachen_xperp liest genau dieses Feld fuer Bedingung 3 - es ist derselbe
    Puls, den der Dauerlauf spaeter beurteilt.
    """
    z["letzter_lauf"] = _jetzt()
    atomar.schreibe_json(ZUSTAND, z)


def spiegeln(z, w):
    """Bedingung 4: Journal und Zustand ausser Haus - nach dem Herzschlag.

    Erst schreiben, dann kopieren: ein haengendes Zweitlaufwerk darf den
    Zyklus verzoegern, aber nicht den Herzschlag verschlucken. Ein fehlendes
    Ziel ist kein Fehler des Laufs (Rueckgabe bleibt 0); der Stand steht im
    Zustand (journal_zweitziel_ok/_info) und in zeige_wachen.
    """
    ziel = w.get("journal_zweitziel")
    ok, info = wx.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if wx.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        # Der Vermerk ist juenger als die Kopie: einmal nachziehen, damit auf
        # Q: derselbe Stand liegt. Sonst waere die Kopie in genau dem Zyklus
        # aelter, in dem sich der Spiegelstand aendert.
        wx.spiegele_journal([ZUSTAND], ziel)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))


def journal(**felder):
    neu = not os.path.exists(JOURNAL)
    # Der Kopf der DATEI entscheidet, was geschrieben wird (T-095): ein
    # Altjournal ohne `pos_id` behaelt seine Spalten (pos_kennung.spalten).
    spalten = SPALTEN if neu else pos_kennung.spalten(JOURNAL, SPALTEN)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in spalten})


# --- Wachen -----------------------------------------------------------------

def wachen():
    """Die Grenzen dieser Spur aus swap/wachen.json.

    Nicht bot.wachen(): das liest die Datei aus dem xperp-Ordner. Zwei Spuren
    mit verschiedenen Grenzen duerfen nicht dieselbe Datei lesen.
    """
    with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
        # Risikostufe: die Betraege tragen den Faktor dieser Stufe.
        return risikostufe.skaliere(json.load(f))


# --- Vorschlaege ------------------------------------------------------------

def rangliste(z, still=True, vorsortiert=60):
    """Die SWAP-Rangliste, hoechstens SCAN_ALTER_MINUTEN alt."""
    alt = (z.get("rangliste") or {}).get("zeit")
    if alt:
        vergangen = (datetime.now(timezone.utc)
                     - datetime.fromisoformat(alt)).total_seconds() / 60
        werte = z["rangliste"].get("werte") or []
        # Ein Stand aus der Zeit VOR dem Zwilling (25.09.2026) traegt ihn
        # nicht - und ohne ihn liefe jede Zeile ueber den Rueckfall auf den
        # nicht handelbaren Perpetual. Der Stand wird deshalb verworfen statt
        # bis zum Ablauf alter zu bleiben.
        ohne_zwilling = [x for x in werte
                         if not (x.get("handels_instr")
                                 or x.get("handels_instId"))]
        if werte and ohne_zwilling:
            print("  Rangliste ohne XPERP-Zwilling (%d von %d Zeilen) - "
                  "wird neu geholt" % (len(ohne_zwilling), len(werte)))
        elif vergangen < SCAN_ALTER_MINUTEN:
            return werte, vergangen

    d = kandidaten.sammle(still=still, vorsortiert=vorsortiert)
    schlank = [{
        "basis": x["basis"], "instId": x["instId"],
        "kategorie": x.get("kategorie", "krypto"),
        "punkte": x["punkte"], "vola": x["vola"],
        "vola_tor": x.get("vola_tor", 1.20),
        "umsatz": x["umsatz"], "ruhe": x.get("ruhe", 0),
        "mae_long": x["mae_long"], "mae_short": x["mae_short"],
        # Der GEHANDELTE Kontrakt muss die Zwischenlagerung ueberleben.
        # Fehlte er hier, loeste anlauf() im naechsten Zyklus den gewoehnlichen
        # Perpetual auf - und der ist auf diesem EEA-Konto nicht handelbar
        # (OKX 50124). Die Rangliste lebt SCAN_ALTER_MINUTEN und wurde aus
        # genau diesem Grund nie handelbar.
        "handels_instId": x.get("handels_instId"),
        "handels_instr": x.get("handels_instr"),
    } for x in d]
    z["rangliste"] = {"zeit": _jetzt(), "werte": schlank}
    return schlank, 0.0


def kandidaten_aus(werte, w, anzahl=6):
    """Die besten Werte je Richtung, die ihre Tore bestehen.

    Gleiche Tore wie xperp: Vola unter dem Tor der Familie, Umsatz ueber dem
    Bezug, Hebel-Deckel mindestens auf Hoehe der Grenze. Die Rangfolge ist ein
    Vorschlag; verbindlich macht sie erst wachen.json.
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
            if deckel < wx.hebel_grenze(w, x["kategorie"]):
                continue
            # Ohne handelbaren Zwilling gibt es keinen Vorschlag: der
            # gewoehnliche Perpetual desselben Basiswerts ist auf diesem Konto
            # nicht handelbar (OKX 50124), und ein Vorschlag, den die Boerse
            # abweist, ist keiner. Der Zwilling kommt aus der Rangliste.
            twin = x.get("handels_instr")
            if not twin:
                continue
            aus.append({"basis": x["basis"], "instId": x["instId"],
                        "handels_instId": x.get("handels_instId")
                        or twin.get("instId"),
                        "handels_instr": twin,
                        "seite": seite, "kategorie": x["kategorie"],
                        "punkte": x["punkte"][seite], "deckel": deckel})
    return aus


_ZWILLINGE = None


def _zwilling(kandidat):
    """Der handelbare XPERP-Kontrakt zu einem Kandidaten - oder None.

    Reihenfolge: der mitgegebene Kontrakt, die mitgegebene Kennung, zuletzt
    eine frische Abfrage der Zwillingstabelle (ein Aufrufer mit eigener
    Kandidatenzeile und ein Stand aus altem Ranglisten-Schema haben keinen).
    Der gewoehnliche Perpetual wird NIE genommen: er ist auf diesem EEA-Konto
    nicht handelbar (OKX 50124).
    """
    global _ZWILLINGE
    instr = kandidat.get("handels_instr")
    if instr:
        return instr
    if kandidat.get("handels_instId"):
        instr = okxf.instrument(kandidat["handels_instId"])
        if instr:
            return instr
    if _ZWILLINGE is None:
        try:
            _ZWILLINGE = kandidaten.handels_kontrakte()
        except Exception as e:                           # noqa: BLE001
            print("  Zwillingstabelle nicht abrufbar (%s)" % e)
            return None
    return _ZWILLINGE.get(kandidat.get("basis"))


def anlauf(w, kandidat):
    """Ein vollstaendiger Vorschlag samt Pflichtzahlen - oder None.

    Gehandelt wird der Kontrakt aus dem Vorrat (handels_instr = der XPERP-
    Zwilling derselben Familie, siehe kandidaten.handels_kontrakte). Nur wenn
    der fehlt, wird der volle instId aufgeloest. Das Signal kommt vom
    gehandelten Kontrakt selbst, nicht aus der Rangliste.
    """
    instr = _zwilling(kandidat)
    if not instr:
        print("  -- %-22s kein XPERP-Zwilling, kein Anlauf"
              % kandidat["instId"])
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

    # Hebel und Stopweite je Familie (Auftrag Max 08.10.2026), wie xperp.
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


# --- Sperren ----------------------------------------------------------------

def marge_frei_usd():
    """Freie Margin in der Kontowaehrung (USDC) - None, wenn die Abfrage scheitert.

    Anlass (25.09.2026): geplant sind 50 USD Margin je Anlauf, das OKX-Konto
    trug aber 0,15 USDC frei - die uebrigen 757 USDC sind die Besicherung
    laufender XPERP-Positionen. Ohne diese Frage geht der Auftrag an die Boerse
    und kommt als 51008 zurueck; jede Runde waere ein Fehlerprotokolleintrag
    ohne Entscheidung. Eine gescheiterte Abfrage sperrt NICHT (None).
    """
    try:
        return float(okxf.guthaben_usdc())
    except Exception:                                    # noqa: BLE001
        return None


def sperren_live(w, s):
    """Alles, was --live gerade verschliesst. Leere Liste = frei.

    Dieselben Gruende wie xperp, dazu die freie Margin. Der letzte traegt das
    Wort Freigabefenster - daran haengt dauerlauf.nur_fenster_fehlt.
    """
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
    if s["ev_negativ"]:
        g.append("rollierender EV %.3f USD < 0 (Bedingung 5)"
                 % s["rollierender_ev"])
    if w.get("journal_zweitziel") is None:
        g.append("journal_zweitziel nicht gesetzt (Bedingung 4)")

    # Freie Margin. Das ist keine Bedingung, sondern fehlendes Geld - der Grund
    # gehoert trotzdem in diese Liste: sonst oeffnet AUTO_FREIGABE ein Fenster
    # fuer einen Lauf, der nicht handeln kann (Muster mosaic: erst den Einsatz
    # deckeln, dann das Freigabefenster zeigen). Er traegt bewusst NICHT das
    # Wort Freigabefenster.
    frei = marge_frei_usd()
    noetig = float(w.get("max_margin_je_anlauf_usd") or 0)
    if frei is not None and noetig and frei < noetig:
        g.append("nur %.2f USDC frei, noetig %.2f (max_margin_je_anlauf_usd)"
                 % (frei, noetig))

    # Punkt 3 der Handelsregeln, in der Fassung fuer den Dauerbetrieb: Ohne
    # offenes Zeitfenster ist nichts scharf. Ein Zeitplan legt den Schalter
    # nicht um, und ein Dauerlauf ist nur ein sehr enger Zeitplan.
    try:
        if not freigabefenster.lade("swap").offen():
            g.append("kein offenes Freigabefenster (Handelsregeln Punkt 3)")
    except ImportError:
        g.append("freigabefenster.py nicht erreichbar")
    return g


# --- Ausstieg ---------------------------------------------------------------

def _kurs(inst):
    return float(okxf.letzter_kurs(inst))


def _ergebnis(p, kurs):
    """Was von der Margin zurueckkommt. Gebuehr beim Schliessen abgezogen."""
    vz = 1 if p["seite"] == "long" else -1
    bewegung = vz * (kurs - p["einstieg"]) / p["einstieg"]
    gewinn = p["nominal"] * bewegung
    gebuehr = p["nominal"] * p.get("gebuehr_taker", 0.0005)
    return p["margin"] + gewinn - gebuehr


def _tage(p):
    """Haltedauer in Tagen (Bruchteil) seit dem Einstieg; 0, wenn die Zeit fehlt."""
    try:
        return (datetime.now(timezone.utc)
                - datetime.fromisoformat(p["eroeffnet_zeit"])).total_seconds() / 86400
    except (KeyError, TypeError, ValueError):
        return 0


def bueche_papier_altlasten_aus(z):
    """ALTBESTAENDE ohne modus-Feld aus dem Buch buchen (Live-Lauf).

    Anlass (22.09.2026): Das Buch ist EINES fuer Papier und Live. Laeuft
    die Spur mit geschlossenem Freigabefenster im Papier, fuellt sie dasselbe
    Buch; wird das Fenster geoeffnet, stehen diese Positionen im Live-Buch.
    pruefe_ausstiege() pruefte kein modus-Feld und haette im naechsten
    Stop-Ausstieg ein echtes okxf.markt_schliessen() auf eine Position
    geschickt, die an der Boerse nie existiert hat.

    Seit dem 25.09.2026 traegt JEDE Position ein modus-Feld und
    pruefe_ausstiege()/flach_stellen() fassen nur noch den eigenen Zweig an -
    damit ist eine Papier-Position im Live-Buch harmlos. Diese Bereinigung
    raeumt deshalb nur noch, was das Feld GAR NICHT hat (Altbestand): eine
    solche Position laesst sich keinem Zweig zuordnen, und der Zweig ohne
    Zuordnung waere der teure Fall (echter Verkauf einer Scheinposition).

    Idempotent: eine zweite Bereinigung findet nichts mehr.
    """
    altlasten = [p for p in z["positionen"] if not p.get("modus")]
    if not altlasten:
        return 0
    behalten = []
    for p in z["positionen"]:
        if p.get("modus"):
            behalten.append(p)
            continue
        # Aktuellen Kurs holen; scheitert das, Altlast zum Einstiegspreis buchen.
        try:
            kurs = _kurs(p["inst"])
        except Exception:                                  # noqa: BLE001
            kurs = p["einstieg"]
        erloes = _ergebnis(p, kurs) if kurs else p["margin"]
        gv = erloes - p["margin"]
        print("  Buchbereinigung: %s (ohne Live-Order) @ %.6f  G/V %+.2f USD"
              % (p["inst"], kurs or p["einstieg"], gv))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                pos_id=p.get("pos_id", ""),
                inst=p["inst"], seite=p["seite"],
                familie=p.get("familie", ""),
                preis="%.6f" % (kurs or p["einstieg"]),
                kontrakte=p["kontrakte"],
                nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.2f" % erloes,
                hebel=p["hebel"],
                grund="buchbereinigung")
        telemetrie.geschlossen(JOURNAL, p, "papier", "buchbereinigung", gv,
                               kurs or p["einstieg"], _tage(p), risikostufe.stufe())
    z["positionen"] = behalten
    return len(altlasten)


def pruefe_ausstiege(z, live, w):
    """Stop, Ziel, Liquidation - gerechnet aus dem eigenen Zustand.

    Ausstiege laufen nie durch eine Freigabe: Ein Stop muss auch dann greifen,
    wenn niemand davorsitzt. Live wird boersenseitig glattgestellt, Papier nur
    im Zustand geschlossen.
    """
    behalten = []
    eigen = "live" if live else "papier"
    for p in z["positionen"]:
        # Nur der eigene Zweig. Sonst schickt ein Live-Lauf ein echtes
        # markt_schliessen() fuer eine Papier-Position (die es an der Boerse nie
        # gab) - und ein Papierlauf bucht eine echte Position aus dem Buch, die
        # an der Boerse offen weiterlaeuft (Geister-Muster, 21./22.09.2026).
        # Positionen aus der Zeit vor dem modus-Feld gelten als Papier; sie
        # raeumt bueche_papier_altlasten_aus() zu Beginn eines Live-Laufs aus.
        if (p.get("modus") or "papier") != eigen:
            behalten.append(p)
            continue
        try:
            kurs = _kurs(p["inst"])
        except Exception as e:                            # noqa: BLE001
            print("  Kurs %s nicht abrufbar (%s) - Position bleibt" % (p["inst"], e))
            behalten.append(p)
            continue

        vz = 1 if p["seite"] == "long" else -1
        grund = None
        # Reihenfolge nach Schwere, nicht nach Naehe: Beruehrt der Kurs die
        # Liquidationsschwelle, hat er den Stop auf dem Weg dorthin schon
        # durchlaufen. Stuende der Stop zuerst, stuende bei einem Totalverlust
        # "stop" im Journal, und letzte_stops zaehlte ihn wie einen gewoehnlichen
        # Stop - die Liquidationsschwelle liegt immer hinter dem Stop, der Zweig
        # waere also nie zu erreichen.
        if p.get("liq") and vz * (kurs - p["liq"]) <= 0:
            grund = "LIQUIDATION"
        elif vz * (kurs - p["stop"]) <= 0:
            grund = "stop"
        elif vz * (kurs - p["ziel"]) >= 0:
            grund = "ziel"

        if not grund:
            behalten.append(p)
            continue

        if live:
            try:
                okxf.markt_schliessen(p["inst"], p["kontrakte"], p["seite"])
            except Exception as e:                       # noqa: BLE001
                print("  Schliessen %s fehlgeschlagen: %s" % (p["inst"], e),
                      file=sys.stderr)
                behalten.append(p)
                continue

        erloes = _ergebnis(p, kurs)
        gv = erloes - p["margin"]
        print("  AUSSTIEG (%s): %s %s @ %.6f  G/V %+.2f USD auf %.2f Margin"
              % (grund, p["inst"], p["seite"], kurs, gv, p["margin"]))
        journal(zeit=_jetzt(), modus="live" if live else "papier",
                pos_id=p.get("pos_id", ""),
                aktion="schliessen", inst=p["inst"], seite=p["seite"],
                familie=p.get("familie", ""), preis="%.6f" % kurs,
                kontrakte=p["kontrakte"], nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.2f" % erloes, hebel=p["hebel"], grund=grund)
        telemetrie.geschlossen(JOURNAL, p, "live" if live else "papier", grund, gv,
                               kurs, _tage(p), risikostufe.stufe())
        if grund in ("stop", "LIQUIDATION"):
            z["letzte_stops"][p["basis"]] = _heute()
    z["positionen"] = behalten


def buche_funding(z, live, w):
    """Faelliges Funding je offener Position ins Journal.

    OKX rechnet alle 8 Stunden ab. Im Papierlauf wird gerechnet, live spaeter
    aus dem Ledger nachgetragen. Positiv heisst gezahlt.
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
        except Exception:                                 # noqa: BLE001
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


def flach_stellen(z, live, grund):
    """Alle Positionen schliessen - Bedingung 2 und 3."""
    behalten = []
    eigen = "live" if live else "papier"
    for p in z["positionen"]:
        if (p.get("modus") or "papier") != eigen:
            behalten.append(p)      # fremder Zweig: siehe pruefe_ausstiege()
            continue
        try:
            kurs = _kurs(p["inst"])
        except Exception as e:                            # noqa: BLE001
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
                pos_id=p.get("pos_id", ""),
                aktion="schliessen", inst=p["inst"], seite=p["seite"],
                familie=p.get("familie", ""), preis="%.6f" % kurs,
                kontrakte=p["kontrakte"], nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.2f" % erloes, hebel=p["hebel"], grund=grund)
        telemetrie.geschlossen(JOURNAL, p, "live" if live else "papier", grund,
                               erloes - p["margin"], kurs, _tage(p), risikostufe.stufe())
    z["positionen"] = behalten


# --- Einstieg ---------------------------------------------------------------

def in_abklingzeit(basis, z, w):
    """Nach einem Stop dieselbe Reihe eine Weile nicht wieder anfassen."""
    tag = z.get("letzte_stops", {}).get(basis)
    if not tag:
        return False
    d = (datetime.now(timezone.utc).date()
         - datetime.fromisoformat(tag).date()).days
    return d < w.get("abklingzeit_tage", 3)


def pruefe_einstiege(z, kand, w, live, s, faktor=1.0):
    """Einstiege. Live geht der Auftrag an die Boerse, Papier nur ins Journal."""
    eigen = "live" if live else "papier"
    meine = [p for p in z["positionen"]
             if (p.get("modus") or "papier") == eigen]
    offen = {p["basis"] for p in meine}
    margin_gebunden = sum(p["margin"] for p in meine)
    fam_stand = wx.familien_belegung(meine, w)
    plaetze = len(meine)
    we = s["wochenende"]

    for kandidat in kand:
        if plaetze >= w["max_offene_anlaeufe"]:
            return
        if kandidat["basis"] in offen or in_abklingzeit(kandidat["basis"], z, w):
            continue

        # Wochenende: keine neuen Anlaeufe in Familien, deren Basiswert nicht
        # handelt. Der Kontrakt laeuft weiter, das Gap zum Wochenstart traegt
        # trotzdem niemand.
        if we and kandidat["kategorie"] in ("aktie", "rohstoff"):
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
        # Die Pruefpflicht ist keine Zierde: Traegt die Trefferquote die Kosten
        # nicht, wird nicht eroeffnet. Die Grundlinie aus Wissen/Handelsbots.md
        # im Automaten - dort lagen noetige und erreichte Quote immer ein bis
        # zwei Punkte auseinander.
        if not p.get("traegt"):
            print("  -- %-22s %-5s: Trefferquote traegt die Kosten nicht "
                  "(noetig %s, beobachtet %s) - kein Anlauf" % (
                      a["inst"], a["seite"],
                      "n/a" if p["quote_noetig"] is None
                      else "%.1f%%" % (p["quote_noetig"] * 100),
                      "n/a" if p["quote_beobachtet"] is None
                      else "%.1f%%" % (p["quote_beobachtet"] * 100)))
            continue
        if not p.get("hebel_traegt"):
            print("  -- %-22s %-5s: Hebel %.1fx ueber Deckel %.1fx - kein Anlauf"
                  % (a["inst"], a["seite"], p["hebel"], p["hebel_deckel"]))
            continue

        if live:
            # Stop und Ziel gehen MIT der Order an die Boerse, nicht nur in
            # zustand.json. Das ist der "nicht abschaltbare Stop" aus den
            # Handelsregeln, woertlich genommen: Ein Stop, der nur hier steht,
            # ist weg, sobald dieser Rechner weg ist - und die
            # Kernel-Power-41-Abschaltungen nehmen ihn ohne Vorwarnung mit.
            try:
                okxf.hebel_setzen(a["inst"], g["hebel"])
                okxf.order_limit(a["inst"], "buy" if a["seite"] == "long"
                                 else "sell", kontrakte, a["einstieg"],
                                 tp=a["ziel"], sl=a["stop"])
            except Exception as e:                       # noqa: BLE001
                print("  Eroeffnen %s fehlgeschlagen: %s" % (a["inst"], e),
                      file=sys.stderr)
                continue

        pos = {
            "inst": a["inst"], "basis": a["basis"], "seite": a["seite"],
            "familie": a["kategorie"], "einstieg": a["einstieg"],
            "stop": a["stop"], "ziel": a["ziel"], "liq": g["liq"],
            "kontrakte": kontrakte, "nominal": g["nominal"],
            "margin": g["margin"], "hebel": g["hebel"],
            "gebuehr_taker": w["gebuehr_taker"],
            "eroeffnet": _heute(), "eroeffnet_zeit": _jetzt(),
            "funding_zuletzt": _jetzt(), "funding_summe": 0.0,
            # OHNE dieses Feld gilt die Position als PAPIER-Altlast:
            # bueche_papier_altlasten_aus() bucht sie im naechsten Live-Zyklus
            # aus, der naechste Papier-Zyklus eroeffnet sie neu - Journal
            # 22.-24.09.2026 dreimal: eroeffnen, 13 bis 28 Minuten spaeter
            # buchbereinigung. Die Papierstrecke kam so nie an Stop oder Ziel.
            # Umgekehrt haengt eine ECHTE Position ohne dieses Feld nach dem
            # naechsten Live-Zyklus ohne Buch an der Boerse. Muster scanner
            # (kauf_ord_id) und xperp (modus).
            "modus": "live" if live else "papier",
        }
        z["positionen"].append(pos)
        meine.append(pos)       # eigener Zweig, siehe oben
        margin_gebunden += g["margin"]
        plaetze += 1
        offen.add(a["basis"])
        fam_stand = wx.familien_belegung(meine, w)

        print("  AUF %-22s %-5s @ %.6f  %g Kontrakte, %.1fx, "
              "%.2f Margin (%.2f nominal)" % (
                  a["inst"], a["seite"], a["einstieg"], kontrakte,
                  g["hebel"], g["margin"], g["nominal"]))
        # Instrument und Seite stehen im Subjekt der AUF-Zeile. Der Dauerlauf
        # meldet aus diesem Block nur diese eine Zeile weiter (ereigniszeilen);
        # eine Fortsetzungszeile ohne Subjekt waere im Chat nicht zuzuordnen,
        # und "Stop" als Spaltenueberschrift ist kein Geschehen.
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
                pos_id=pos.setdefault("pos_id", pos_kennung.neu(_jetzt())),
                aktion="eroeffnen", inst=a["inst"], seite=a["seite"],
                familie=a["kategorie"], preis="%.6f" % a["einstieg"],
                kontrakte=kontrakte, nominal_usd="%.2f" % g["nominal"],
                margin_usd="%.2f" % g["margin"], hebel=g["hebel"],
                stop="%.6f" % a["stop"], ziel="%.6f" % a["ziel"],
                liq="%.6f" % g["liq"],
                liq_abstand="%.4f" % p["liq_abstand"],
                funding_pct="" if p["funding_pct"] is None
                else "%.6f" % p["funding_pct"],
                gebuehr_pct="%.6f" % p["gebuehren_pct"],
                quote_noetig="" if p["quote_noetig"] is None
                else "%.4f" % p["quote_noetig"],
                quote_beob="" if p["quote_beobachtet"] is None
                else "%.4f" % p["quote_beobachtet"],
                grund="eroeffnet")


# --- Ausgabe und Lauf -------------------------------------------------------

def zeige_wachen(s, w):
    print("Bedingungen (Momentaufnahme, aus dem eigenen Zustand):")
    for i, (name, wert) in enumerate((
            ("Handelsrunden", s["runden_echt"]),
            ("davon Papier", s["runden_papier_echt"]),
            ("Betriebsstoerungen", s["runden_stoerung"]),
            ("Buchungen gesamt", s["runden_gesamt"]),
            ("Hoechststand", "%.2f USD" % s["hoechststand_usd"]),
            ("Ruecklauf", "%.2f USD" % s["ruecklauf_usd"]),
            ("Groessenfaktor", "%.2f" % s["groessenfaktor"]),
            ("Kill ausgeloest", s["kill"]),
            ("Herzschlag frisch", "%s (Grenze %d min, Alter %s)"
             % (s["herzschlag_frisch"], w.get("herzschlag_max_minuten", 30),
                "?" if s["herzschlag_alter_min"] is None
                else "%.0f" % s["herzschlag_alter_min"])),
            ("Rollierender EV", "n/a" if s["rollierender_ev"] is None
             else "%+.2f USD" % s["rollierender_ev"]),
            ("Wochenende sperrt", s["wochenende"]))):
        print("  %d  %-20s %s" % (i + 1, name, wert))
    for name, f in sorted(s["familien"].items()):
        print("     Familie %-9s %.2f von %.2f gebunden%s"
              % (name, f["margin"], f["grenze"], " - VOLL" if f["voll"] else ""))
    z = lade_zustand()
    print("  Journal-Zweitziel         %s"
          % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  Letzte Kopie ausser Haus  %s (%s)"
          % (z.get("journal_zweitziel_ok"), z.get("journal_zweitziel_info")))

    if s["kill"]:
        print()
        print("  KILL-SWITCH erreicht - der naechste Lauf stellt flach.")
    if s["ev_negativ"] and w.get("handel_erlaubt"):
        if wx.sperre_zu("rollierender EV %.3f USD < 0" % s["rollierender_ev"]):
            print("  EV negativ -> handel_erlaubt auf false gesetzt.")


def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = wachen()

    if modus == "wachen":
        z = lade_zustand()
        zeige_wachen(wx.lage(w, JOURNAL, z), w)
        return

    z = lade_zustand()
    z.setdefault("positionen", [])
    z.setdefault("letzte_stops", {})
    s = wx.lage(w, JOURNAL, z)

    live = False
    if modus == "live":
        g = sperren_live(w, s)
        if g:
            print("--live angefordert, aber gesperrt: " + "; ".join(g))
            print("-> es wird Papier gehandelt.")
        else:
            live = True
            n_alt = bueche_papier_altlasten_aus(z)
            if n_alt:
                print("  %d Papier-Altlast(en) aus dem Live-Buch gebucht"
                      % n_alt)

    werte, alter = rangliste(z)
    kand = kandidaten_aus(werte, w)
    gebunden = sum(p["margin"] for p in z["positionen"])
    print("=== SWAP handeln (%s) | %d Werte, %d Kandidaten | Rangliste %.0f "
          "min alt | %.2f von %g USD Margin gebunden ==="
          % ("LIVE" if live else "Papier", len(werte), len(kand), alter,
             gebunden, w["max_margin_gesamt_usd"]))

    if modus == "vorschau":
        for k in kand[:10]:
            # Der GEHANDELTE Kontrakt, nicht der Reihenname: die Kennzahlen
            # kommen vom umsatzstaerkeren Perpetual, die Order geht an den
            # XPERP-Zwilling. Eine Vorschau, die nur den Reihennamen zeigt,
            # liest sich, als wuerde der gewoehnliche Perpetual gehandelt.
            print("  %-22s %-30s %-5s Punkte %.1f  Deckel %.1fx  (%s)"
                  % (k["instId"], k.get("handels_instId") or "-- kein Zwilling",
                     k["seite"], k["punkte"], k["deckel"], k["kategorie"]))
        print("\nOffener Bestand: %d Positionen, %.2f USD Margin"
              % (len(z["positionen"]), gebunden))
        g = sperren_live(w, s)
        # Immer drucken: eine fehlende Zeile ist von "nicht geprueft" nicht zu
        # unterscheiden, und der Dauerlauf parst genau diese Zeile.
        print("Live waere gesperrt durch: " + ("; ".join(g) if g else "nichts"))
        # Bewusst KEIN schreibe_zustand: eine Vorschau schreibt nicht (so
        # halten es omniquant, spiegel und nautilus). Vorher setzte jeder
        # Vorschau-Lauf einen frischen Herzschlag - und weil der Dauerlauf
        # jede Spur zusaetzlich mit --vorschau abfragt, war die Kopie auf Q:
        # danach scheinbar aelter als der eigene Zustand.
        return

    z["modus"] = "live" if live else "papier"

    # Bedingung 2 - Kill-Switch. Er schliesst auch das Wachen-Tor: ein
    # Ruecklauf in dieser Hoehe ist kein Grund weiterzuhandeln.
    if s["kill"]:
        print("- KILL-SWITCH: Ruecklauf %.2f USD -> Notausstieg + Sperre -"
              % s["ruecklauf_usd"])
        flach_stellen(z, live, "kill_switch")
        if wx.sperre_zu("kill_switch: Ruecklauf %.2f USD" % s["ruecklauf_usd"]):
            print("  wachen.json handel_erlaubt -> false")
        schreibe_zustand(z)
        spiegeln(z, w)
        return

    # Bedingung 3 - Herzschlag alt. Deckt die Kernel-Power-41-Abschaltungen
    # ab: eine Position, die einen Neustart ueberlebt, ist unbewacht.
    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel dieser "
              "Lauf -" % ("?" if s["herzschlag_alter_min"] is None
                          else "%.0f" % s["herzschlag_alter_min"],
                          w.get("herzschlag_max_minuten", 30)))
        flach_stellen(z, live, "herzschlag_alt")
        z["modus"] = "papier"
        schreibe_zustand(z)
        spiegeln(z, w)
        return

    buche_funding(z, live, w)
    pruefe_ausstiege(z, live, w)

    pruefe_einstiege(z, kand, w, live, s, s["groessenfaktor"])
    print("Offener Bestand danach: %d Positionen, %.2f USD Margin"
          % (len(z["positionen"]),
             sum(p["margin"] for p in z["positionen"])))
    schreibe_zustand(z)
    spiegeln(z, w)


def main():
    # Der Dauerlauf startet dieses Skript als eigenen Prozess (dauerlauf.py,
    # zyklus_spur) - Start und Ende melden sich deshalb hier am Bus. Muster:
    # xperp/handeln.py, scanner/handeln.py, dauerlauf.py. Ein toter Bus
    # bricht den Lauf nicht ab: ereignis.lauf faengt das selbst ab.
    with ereignis.lauf("handel/swap"):
        return _main()


def _main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vorschau", action="store_const", const="vorschau",
                   dest="modus", help="was waere dran, ohne zu schreiben")
    p.add_argument("--papier", action="store_const", const="papier", dest="modus")
    p.add_argument("--live", action="store_const", const="live", dest="modus")
    p.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    p.set_defaults(modus="vorschau")
    a = p.parse_args()
    lauf(a.modus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
