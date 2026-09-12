"""Papierpfad der SWAP-Spur: Einstiege, Ausstiege, Funding, Journal, Zustand.

Dritte Spur neben scanner (Spot) und xperp (XPERP). Diese Fassung ist
PAPIERFEST: es gibt keinen Live-Zweig. Die Order-Funktionen von okxf werden
beim Import durch Stummel ersetzt, die eine Ausnahme werfen - aus diesem
Prozess heraus ist eine Order nicht moeglich, auch nicht durch einen Fehler in
der Steuerung. Der Test test_handeln_papier.py belegt das.

WAS SIE UEBERNIMMT (importiert, nicht kopiert)
---------------------------------------------
Rechnungen:  bot.groesse(), bot.pruefpflicht(), bot.BAR
Kennzahlen:  indikatoren.lage()
Zugang:      okxf - nur lesende Funktionen (Kerzen, Kurs, Ticker, Funding,
             kontrakte_aus_nominal, auf_tick)
Wachen:      wachen_xperp.lage() - Drawdown, Familienbelegung, Wochenende,
             Kill-Switch, rollierender Erwartungswert
Vorrat:      swap/kandidaten.py liefert dieselbe Kandidatenform wie
             xperp/auswahl.py, nur ueber instType=SWAP

WAS SIE BEWUSST NICHT UEBERNIMMT
--------------------------------
xperp/handeln.py. Dort steht der Live-Order-Pfad (hebel_setzen, order_limit).
Eine Papierspur, die dieses Modul importiert - und sei es nur, um seine
Pfadkonstanten umzubiegen -, haengt an derselben Leitung: ein Fehler in der
Steuerung waere dann eine echte Order. Der Live-Zweig entsteht spaeter
bewusst nach xperp-Muster, mit Max am Bildschirmfenster.

DREI DINGE, DIE ANDERS SIND ALS BEI XPERP
-----------------------------------------
1. Das Instrument wird ueber den VOLLEN instId aufgeloest. okxf.instrument()
   nimmt einen Basiswert und findet dann den XPERP-Kontrakt; ohne die Endung
   -SWAP wuerde diese Spur still den falschen Kontrakt handeln.
2. Die Wachen kommen aus swap/wachen.json. bot.wachen() liest die Datei aus
   dem xperp-Ordner - wer sie hier benutzt, handelt nach fremden Grenzen.
3. --live verweigert mit genau einem Grund, in dem das Wort Freigabefenster
   NICHT vorkommt. So fragt der Dauerlauf keine Freigabe an, die nichts
   oeffnen koennte (dauerlauf.nur_fenster_fehlt liest diese Zeile).

PAPIER HEISST: Die Position steht im eigenen Zustand, nicht an der Boerse. Der
Ausstieg schliesst sie hier; an OKX existiert nichts zu schliessen. Deshalb
zahlt der Papierlauf auch keine echten Gebuehren - sie werden gerechnet und ins
Journal geschrieben, damit die Zahlen vergleichbar bleiben.

Aufruf:
    python handeln.py --vorschau   # was waere dran, ohne etwas zu schreiben
    python handeln.py --papier     # Papierlauf mit Journal
    python handeln.py --wachen     # Bedingungen als Momentaufnahme
    python handeln.py --live       # verweigert, nennt den Grund, laeuft Papier
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
for p in (HIER, XPERP):
    if p not in sys.path:
        sys.path.insert(0, p)

import auswahl                                                 # noqa: E402
import bot                                                     # noqa: E402
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


# --- Sicherheitsnetz --------------------------------------------------------

class Papierfehler(RuntimeError):
    """Eine Order wurde aus der Papierspur heraus versucht. Das ist ein Fehler."""


def _keine_order(*a, **kw):
    raise Papierfehler(
        "Diese Spur ist papierfest: Order-Funktionen sind stillgelegt.")


# Genau die vier Funktionen, die Geld bewegen. Nach diesem Block kann kein Code
# in diesem Prozess eine Order ausloesen - auch kein importiertes Modul.
for _name in ("order_limit", "markt_schliessen", "hebel_setzen",
              "order_stornieren"):
    if hasattr(okxf, _name):
        setattr(okxf, _name, _keine_order)


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

    lage = indikatoren.lage(k)
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


def pruefe_ausstiege(z, w):
    """Stop, Ziel, Liquidation - gerechnet aus dem eigenen Zustand.

    Ausstiege laufen nie durch eine Freigabe: Ein Stop muss auch dann greifen,
    wenn niemand davorsitzt. Hier wird nichts an der Boerse geschlossen, weil
    dort nichts offen ist.
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

        erloes = _ergebnis(p, kurs)
        gv = erloes - p["margin"]
        print("  ZU  %-22s %-5s @ %.6f  (%s)  G/V %+.2f USD auf %.2f Margin"
              % (p["inst"], p["seite"], kurs, grund, gv, p["margin"]))
        journal(zeit=_jetzt(), modus="papier",
                aktion="schliessen", inst=p["inst"], seite=p["seite"],
                familie=p.get("familie", ""), preis="%.6f" % kurs,
                kontrakte=p["kontrakte"], nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.2f" % erloes, hebel=p["hebel"], grund=grund)
        if grund in ("stop", "LIQUIDATION"):
            z["letzte_stops"][p["basis"]] = _heute()
    z["positionen"] = behalten


def buche_funding(z, w):
    """Faelliges Funding je offener Position ins Journal.

    OKX rechnet alle 8 Stunden ab. Der Papierlauf rechnet es, damit die
    Empfehlung nicht besser aussieht als die Wirklichkeit - dieselbe Falle wie
    die Gebuehren.
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
        journal(zeit=_jetzt(), modus="papier", aktion="funding",
                inst=p["inst"], seite=p["seite"],
                familie=p.get("familie", ""),
                nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.4f" % betrag,
                funding_pct="%.6f" % satz,
                grund="%d Periode(n) a 8h" % perioden)
        print("  Funding %-22s %+.4f USD (%d x %.4f%%)"
              % (p["inst"], betrag, perioden, satz * 100))


def flach_stellen(z, grund):
    """Alle Papierpositionen schliessen - Bedingung 2 und 3."""
    behalten = []
    for p in z["positionen"]:
        try:
            kurs = _kurs(p["inst"])
        except Exception as e:                            # noqa: BLE001
            print("  Notausstieg %s: Kurs nicht abrufbar (%s)" % (p["inst"], e),
                  file=sys.stderr)
            behalten.append(p)
            continue
        erloes = _ergebnis(p, kurs)
        print("  NOT-ZU %-22s %-5s @ %.6f  G/V %+.2f USD  (%s)"
              % (p["inst"], p["seite"], kurs, erloes - p["margin"], grund))
        journal(zeit=_jetzt(), modus="papier",
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


def pruefe_einstiege(z, kand, w, s, faktor=1.0):
    """Papier-Einstiege. Kein Order-Zweig - es kann keinen geben."""
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
        # nicht, wird auch im Papierlauf nicht eroeffnet - sonst empfiehlt die
        # Spur eine Strategie, die sie selbst nicht spielen wuerde.
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

        journal(zeit=_jetzt(), modus="papier",
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

    if modus == "live":
        # Genau ein Grund, und das Wort Freigabefenster kommt darin nicht vor:
        # dauerlauf.nur_fenster_fehlt stellt nur dann eine Anfrage, wenn der
        # Grund dieses Wort traegt. Eine Anfrage waere hier eine Freigabe, die
        # nichts oeffnen kann - eine Sperre, die nur so aussieht.
        print("--live angefordert, aber gesperrt: "
              "kein Live-Pfad in dieser Spur (Papier)")
        print("-> es wird Papier gehandelt.")

    # Ausstiege und Notausstiege zuerst. Ein Stop muss auch dann greifen, wenn
    # niemand davorsitzt.
    pruefe_ausstiege(z, w)
    buche_funding(z, w)

    if s["kill"]:
        print("- Kill-Schwelle erreicht (%.2f USD Ruecklauf) -> alles flach -"
              % s["ruecklauf_usd"])
        flach_stellen(z, "kill_switch")
        schreibe_zustand(z)
        return
    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel dieser "
              "Lauf -" % ("?" if s["herzschlag_alter_min"] is None
                          else "%.0f" % s["herzschlag_alter_min"],
                          w.get("herzschlag_max_minuten", 30)))
        flach_stellen(z, "herzschlag_alt")
        schreibe_zustand(z)
        return

    werte, alter = rangliste(z)
    kand = kandidaten_aus(werte, w)
    gebunden = sum(p["margin"] for p in z["positionen"])
    print("=== SWAP handeln (PAPIER%s) | %d Werte, %d Kandidaten | "
          "Rangliste %.0f min alt | %.2f von %g USD Margin gebunden ==="
          % ("" if modus != "vorschau" else ", Vorschau", len(werte), len(kand),
             alter, gebunden, w["max_margin_gesamt_usd"]))

    if modus == "vorschau":
        for k in kand[:10]:
            print("  %-22s %-5s Punkte %.1f  Deckel %.1fx  (%s)"
                  % (k["instId"], k["seite"], k["punkte"], k["deckel"],
                     k["kategorie"]))
        print("\nOffener Bestand: %d Papierpositionen, %.2f USD Margin"
              % (len(z["positionen"]), gebunden))
        print("Live waere gesperrt durch: kein Live-Pfad in dieser Spur (Papier)")
        schreibe_zustand(z)
        return

    pruefe_einstiege(z, kand, w, s, s["groessenfaktor"])
    print("Offener Bestand danach: %d Papierpositionen, %.2f USD Margin"
          % (len(z["positionen"]),
             sum(p["margin"] for p in z["positionen"])))
    schreibe_zustand(z)


def main():
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
