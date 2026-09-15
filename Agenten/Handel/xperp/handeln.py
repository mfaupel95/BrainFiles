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

import auswahl
import bot
import indikatoren
import okxf
import wachen_xperp as wx

ZUSTAND = os.path.join(HIER, "zustand.json")
JOURNAL = os.path.join(HIER, "handelsjournal.csv")

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "familie", "preis",
           "kontrakte", "nominal_usd", "margin_usd", "hebel", "stop", "ziel",
           "liq", "liq_abstand", "funding_pct", "gebuehr_pct",
           "quote_noetig", "quote_beob", "grund"]

# Wie oft der Kandidatenscan die Rangliste neu rechnet. Ein voller Lauf ueber
# 164 Kontrakte dauert rund zwei Minuten - bei einem 15-Minuten-Takt waere
# das ein Achtel der Zeit fuer eine Liste, die sich in 4H-Kerzen bewegt.
SCAN_ALTER_MINUTEN = 120


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
            if deckel < w["max_hebel"]:
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


def _ergebnis(p, kurs):
    """Was von der Margin zurueckkommt. Gebuehr beim Schliessen abgezogen."""
    vz = 1 if p["seite"] == "long" else -1
    bewegung = vz * (kurs - p["einstieg"]) / p["einstieg"]
    gewinn = p["nominal"] * bewegung
    gebuehr = p["nominal"] * p.get("gebuehr_taker", 0.0005)
    return p["margin"] + gewinn - gebuehr


def pruefe_ausstiege(z, live, w):
    behalten = []
    for p in z["positionen"]:
        try:
            kurs = _kurs_aktuell(p)
        except Exception as e:                           # noqa: BLE001
            print("  Kurs %s nicht abrufbar (%s) - Position bleibt" % (p["inst"], e))
            behalten.append(p)
            continue

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
                aktion="schliessen", inst=p["inst"], seite=p["seite"],
                familie=p.get("familie", ""), preis="%.6f" % kurs,
                kontrakte=p["kontrakte"], nominal_usd="%.2f" % p["nominal"],
                margin_usd="%.2f" % erloes, hebel=p["hebel"], grund=grund)
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


def flach_stellen(z, live, grund):
    """Alle Positionen sofort schliessen - Bedingung 2 und 3."""
    behalten = []
    for p in z["positionen"]:
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
                aktion="schliessen", inst=p["inst"], seite=p["seite"],
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


def pruefe_einstiege(z, kand, w, live, s, faktor=1.0):
    offen = {p["basis"] for p in z["positionen"]}
    margin_gebunden = sum(p["margin"] for p in z["positionen"])
    fam_stand = wx.familien_belegung(z["positionen"], w)
    we = s["wochenende"]

    for kandidat in kand:
        if len(z["positionen"]) >= w["max_offene_anlaeufe"]:
            return
        if kandidat["basis"] in offen or in_abklingzeit(kandidat["basis"], z, w):
            continue

        # Wochenende: keine neuen Anlaeufe in Familien, deren Basiswert
        # nicht handelt. Der Kontrakt liefe weiter, das Gap zum Wochenstart
        # traegt trotzdem niemand.
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
                aktion="eroeffnen", inst=a["inst"], seite=a["seite"],
                familie=a["kategorie"], preis="%.6f" % a["einstieg"],
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
    if s["ev_negativ"] and w.get("handel_erlaubt"):
        if wx.sperre_zu("rollierender EV %.3f USD < 0" % s["rollierender_ev"]):
            print("  EV negativ -> handel_erlaubt auf false gesetzt.")


# --- Hauptlauf --------------------------------------------------------------

def sperren_live(w, s):
    """Alles, was --live gerade verschliesst. Leere Liste = frei."""
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
        import freigabefenster
        if not freigabefenster.lade("xperp").offen():
            g.append("kein offenes Freigabefenster (Handelsregeln Punkt 3)")
    except ImportError:
        g.append("freigabefenster.py nicht erreichbar")
    return g


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

    # Bedingung 2 - Kill-Switch.
    if s["kill"]:
        print("- KILL-SWITCH: Ruecklauf %.2f USD >= %g -> Notausstieg + Sperre -"
              % (s["ruecklauf_usd"], w["kill_switch_gesamt_usd"]))
        flach_stellen(z, live, "kill_switch")
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
        flach_stellen(z, live, "herzschlag_alt")
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
