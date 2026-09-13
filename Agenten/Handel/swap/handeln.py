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
1. Das Instrument wird ueber den VOLLEN instId aufgeloest. okxf.instrument()
   findet fuer einen Basiswert den XPERP-Kontrakt; ohne die Endung -SWAP
   handelte diese Spur still den falschen Kontrakt.
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

import ereignis                                                # noqa: E402
import auswahl                                                 # noqa: E402
import bot                                                     # noqa: E402
import freigabefenster                                         # noqa: E402
import indikatoren                                              # noqa: E402
import kandidaten                                              # noqa: E402
import okxf                                                    # noqa: E402
import wachen_xperp as wx                                      # noqa: E402

ZUSTAND = os.path.join(HIER, "zustand.json")
JOURNAL = os.path.join(HIER, "handelsjournal.csv")

# Dieselben Spalten wie xperp. Ein zweites Schema waere der Anfang zweier
# Auswertungen, die sich nicht mehr vergleichen lassen.
SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "familie", "preis",
           "kontrakte", "nominal_usd", "margin_usd", "hebel", "stop", "ziel",
           "liq", "liq_abstand", "funding_pct", "gebuehr_pct",
           "quote_noetig", "quote_beob", "grund"]

# Wie bei xperp: die Rangliste wird zwischengelagert, weil ein voller Scan
# Minuten kostet. Sie steht auf 4H-Kerzen und aendert sich nicht im Takt.
SCAN_ALTER_MINUTEN = 120


# --- Zeit, Zustand, Journal -------------------------------------------------

def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


def lade_zustand():
    try:
        with open(ZUSTAND, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"positionen": [], "letzte_stops": {}, "letzter_lauf": None,
                "modus": "papier", "rangliste": None}


def schreibe_zustand(z):
    """Schreibt den Zustand und setzt damit den Herzschlag (letzter_lauf).

    wachen_xperp liest genau dieses Feld fuer Bedingung 3 - es ist derselbe
    Puls, den der Dauerlauf spaeter beurteilt.
    """
    z["letzter_lauf"] = _jetzt()
    with open(ZUSTAND, "w", encoding="utf-8") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")


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
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=SPALTEN, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in SPALTEN})


# --- Wachen -----------------------------------------------------------------

def wachen():
    """Die Grenzen dieser Spur aus swap/wachen.json.

    Nicht bot.wachen(): das liest die Datei aus dem xperp-Ordner. Zwei Spuren
    mit verschiedenen Grenzen duerfen nicht dieselbe Datei lesen.
    """
    with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
        return json.load(f)


# --- Vorschlaege ------------------------------------------------------------

def rangliste(z, still=True, vorsortiert=60):
    """Die SWAP-Rangliste, hoechstens SCAN_ALTER_MINUTEN alt."""
    alt = (z.get("rangliste") or {}).get("zeit")
    if alt:
        vergangen = (datetime.now(timezone.utc)
                     - datetime.fromisoformat(alt)).total_seconds() / 60
        if vergangen < SCAN_ALTER_MINUTEN:
            return z["rangliste"]["werte"], vergangen

    d = kandidaten.sammle(still=still, vorsortiert=vorsortiert)
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
            if deckel < w["max_hebel"]:
                continue
            aus.append({"basis": x["basis"], "instId": x["instId"],
                        "seite": seite, "kategorie": x["kategorie"],
                        "punkte": x["punkte"][seite], "deckel": deckel})
    return aus


def anlauf(w, kandidat):
    """Ein vollstaendiger Vorschlag samt Pflichtzahlen - oder None.

    Das Instrument kommt ueber den vollen instId: okxf.instrument("CHIP") findet
    den XPERP, gemeint ist hier CHIP-USDT-SWAP. Das Signal kommt vom gehandelten
    Kontrakt selbst, nicht aus der Rangliste.
    """
    instr = okxf.instrument(kandidat["instId"])
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

    g = bot.groesse(w, instr, einstieg, stop, seite, kandidat["deckel"])
    if not g:
        return None

    p = bot.pruefpflicht(w, instr, k, seite, einstieg, stop, ziel,
                         g["hebel"], still=True)
    return {"instr": instr, "inst": instr["instId"], "basis": kandidat["basis"],
            "seite": seite, "kategorie": kandidat["kategorie"],
            "einstieg": einstieg, "stop": stop, "ziel": ziel,
            "groesse": g, "pflicht": p, "punkte": kandidat["punkte"],
            "grund": lage["grund"]}


# --- Sperren ----------------------------------------------------------------

def sperren_live(w, s):
    """Alles, was --live gerade verschliesst. Leere Liste = frei.

    Dieselben sieben Gruende wie xperp. Der letzte traegt das Wort
    Freigabefenster - daran haengt dauerlauf.nur_fenster_fehlt.
    """
    g = []
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


def pruefe_ausstiege(z, live, w):
    """Stop, Ziel, Liquidation - gerechnet aus dem eigenen Zustand.

    Ausstiege laufen nie durch eine Freigabe: Ein Stop muss auch dann greifen,
    wenn niemand davorsitzt. Live wird boersenseitig glattgestellt, Papier nur
    im Zustand geschlossen.
    """
    behalten = []
    for p in z["positionen"]:
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
        print("  ZU  %-22s %-5s @ %.6f  (%s)  G/V %+.2f USD auf %.2f Margin"
              % (p["inst"], p["seite"], kurs, grund, gv, p["margin"]))
        journal(zeit=_jetzt(), modus="live" if live else "papier",
                aktion="schliessen", inst=p["inst"], seite=p["seite"],
                familie=p.get("familie", ""), preis="%.6f" % kurs,
                kontrakte=p["kontrakte"], nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.2f" % erloes, hebel=p["hebel"], grund=grund)
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
    for p in z["positionen"]:
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
        print("  NOT-ZU %-22s %-5s @ %.6f  G/V %+.2f USD  (%s)"
              % (p["inst"], p["seite"], kurs, erloes - p["margin"], grund))
        journal(zeit=_jetzt(), modus="live" if live else "papier",
                aktion="schliessen", inst=p["inst"], seite=p["seite"],
                familie=p.get("familie", ""), preis="%.6f" % kurs,
                kontrakte=p["kontrakte"], nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.2f" % erloes, hebel=p["hebel"], grund=grund)
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
    offen = {p["basis"] for p in z["positionen"]}
    margin_gebunden = sum(p["margin"] for p in z["positionen"])
    fam_stand = wx.familien_belegung(z["positionen"], w)
    we = s["wochenende"]

    for kandidat in kand:
        if len(z["positionen"]) >= w["max_offene_anlaeufe"]:
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
        }
        z["positionen"].append(pos)
        margin_gebunden += g["margin"]
        offen.add(a["basis"])
        fam_stand = wx.familien_belegung(z["positionen"], w)

        print("  AUF %-22s %-5s @ %.6f  %g Kontrakte, %.1fx, "
              "%.2f Margin (%.2f nominal)" % (
                  a["inst"], a["seite"], a["einstieg"], kontrakte,
                  g["hebel"], g["margin"], g["nominal"]))
        # Instrument und Seite stehen in jeder Zeile. Der Dauerlauf meldet jede
        # Zeile mit dem Wort Stop einzeln weiter - eine Fortsetzungszeile ohne
        # Subjekt ist dort nicht zuzuordnen.
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
            ("Runden gesamt", s["runden_gesamt"]),
            ("davon Papier", s["runden_papier"]),
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

    # Ausstiege und Notausstiege zuerst. Ein Stop muss auch dann greifen, wenn
    # niemand davorsitzt.
    pruefe_ausstiege(z, live, w)
    buche_funding(z, live, w)

    if s["kill"]:
        print("- Kill-Schwelle erreicht (%.2f USD Ruecklauf) -> alles flach -"
              % s["ruecklauf_usd"])
        flach_stellen(z, live, "kill_switch")
        schreibe_zustand(z)
        spiegeln(z, w)
        return
    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel dieser "
              "Lauf -" % ("?" if s["herzschlag_alter_min"] is None
                          else "%.0f" % s["herzschlag_alter_min"],
                          w.get("herzschlag_max_minuten", 30)))
        flach_stellen(z, live, "herzschlag_alt")
        schreibe_zustand(z)
        spiegeln(z, w)
        return

    werte, alter = rangliste(z)
    kand = kandidaten_aus(werte, w)
    gebunden = sum(p["margin"] for p in z["positionen"])
    print("=== SWAP handeln (%s) | %d Werte, %d Kandidaten | Rangliste %.0f "
          "min alt | %.2f von %g USD Margin gebunden ==="
          % ("LIVE" if live else "Papier", len(werte), len(kand), alter,
             gebunden, w["max_margin_gesamt_usd"]))

    if modus == "vorschau":
        for k in kand[:10]:
            print("  %-22s %-5s Punkte %.1f  Deckel %.1fx  (%s)"
                  % (k["instId"], k["seite"], k["punkte"], k["deckel"],
                     k["kategorie"]))
        print("\nOffener Bestand: %d Positionen, %.2f USD Margin"
              % (len(z["positionen"]), gebunden))
        g = sperren_live(w, s)
        if g:
            print("Live waere gesperrt durch: " + "; ".join(g))
        # Bewusst KEIN schreibe_zustand: eine Vorschau schreibt nicht (so
        # halten es omniquant, spiegel und nautilus). Vorher setzte jeder
        # Vorschau-Lauf einen frischen Herzschlag - und weil der Dauerlauf
        # jede Spur zusaetzlich mit --vorschau abfragt, war die Kopie auf Q:
        # danach scheinbar aelter als der eigene Zustand.
        return

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
