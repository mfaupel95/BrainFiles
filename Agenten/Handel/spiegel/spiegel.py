"""Die Spiegel-Spur: was waere, wenn man den Wallets des Feeds nachkauft?

Sie kopiert **nichts** und sie kauft **nichts**. Sie fuehrt ein Papierbuch:
Jeder Kauf eines verfolgten Wallets wird zu einer Buchzeile mit Slippage,
Gebuehr und eigenen Ausstiegsgrenzen. Was am Ende uebrig bleibt, ist die
Antwort auf die Frage, ob Nachahmen nach Kosten traegt - die einzige Frage,
die vor einem echten Kauf beantwortet sein muss.

Kein Orderpfad
--------------
Der Schreibbefehl des CLI (`swap`) wird beim Import stillgelegt: Ein Fehler in
der Steuerung kann aus diesem Prozess heraus kein Geld bewegen. `--live`
verweigert mit genau einem Grund, in dem das Wort Freigabefenster NICHT
vorkommt - so fragt der Dauerlauf keine Freigabe an, die nichts oeffnen kann.

Kosten, ehrlich gerechnet
-------------------------
Slippage und Gebuehr stehen in wachen.json und wirken zweimal: beim Kauf
teurer, beim Verkauf billiger. Ein Papierbuch mit glatten Kursen ist eine
Wunschrechnung, und genau daran scheitern Nachahmer in der Wirklichkeit.

Aufruf:
    python spiegel.py --waehlen     # verfolgte.json aus dem Feed neu bauen
    python spiegel.py --wachen      # Grenzen als Momentaufnahme
    python spiegel.py --vorschau    # was waere dran, ohne zu schreiben
    python spiegel.py --papier      # ein Papierzyklus mit Journal
    python spiegel.py --bilanz      # welche Wallets haben getragen
    python spiegel.py --live        # verweigert, nennt den Grund
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
BUS = os.path.join(HIER, os.pardir, os.pardir, "Bus")
for p in (HIER, BUS):
    if p not in sys.path:
        sys.path.insert(0, p)

import ereignis                                               # noqa: E402
import lesen                                                  # noqa: E402

WACHEN = os.path.join(HIER, "wachen.json")
VERFOLGTE = os.path.join(HIER, "verfolgte.json")
ZUSTAND = os.path.join(HIER, "zustand.json")
JOURNAL = os.path.join(HIER, "handelsjournal.csv")

SPALTEN = ["zeit", "modus", "aktion", "kette", "wallet", "token", "symbol",
           "preis", "menge", "einsatz_usd", "wert_usd", "marktkap_usd",
           "slippage_pct", "gebuehr_pct", "grund"]

# Ob geschrieben wird. Die Vorschau stellt das ab (siehe journal()).
SCHREIBEN = True


# --- Sicherheitsnetz --------------------------------------------------------

class Papierfehler(RuntimeError):
    """Ein Kauf wurde aus der Papierspur heraus versucht. Das ist ein Fehler."""


def _kein_schreiben(*a, **kw):
    raise Papierfehler("Diese Spur ist papierfest: Schreibbefehle sind "
                       "stillgelegt.")


# Kein Orderpfad. Der Schreibschutz sitzt in lesen.py und wird hier
# gegengeprueft: Wer ihn dort entfernt, bekommt beim Start dieser Spur einen
# Fehler - lieber kein Buch als ein Buch, das heimlich tauschen koennte.
if not getattr(lesen, "SCHREIBBEFEHLE", None):
    raise RuntimeError("lesen.py hat keinen Schreibschutz mehr - die "
                       "Spiegel-Spur startet nicht.")


# --- Dateien ----------------------------------------------------------------

def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


def _zahl(wert):
    """Zahl aus einer Zeichenkette mit vielen Stellen - oder None."""
    try:
        return float(str(wert).replace(",", ""))
    except (TypeError, ValueError):
        return None


def lade(pfad, vorgabe):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return vorgabe


def schreibe(pfad, daten):
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)
        f.write("\n")


def journal(**felder):
    # In der Vorschau wird nichts geschrieben. Ohne diesen Schalter haette die
    # Vorschau Kopien im Journal geschlossen, die im Zustand offen bleiben -
    # zwei Wahrheiten, und die Vorschau waere keine Vorschau mehr.
    if not SCHREIBEN:
        return
    neu = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=SPALTEN, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in SPALTEN})


def lade_zustand():
    z = lade(ZUSTAND, None)
    if not z:
        z = {"positionen": [], "letzter_lauf": None, "modus": "papier"}
    z.setdefault("positionen", [])
    return z


def schreibe_zustand(z):
    # Wie das Journal: in der Vorschau wird nichts geschrieben. Sonst haette
    # ein Vorschau-Lauf den Herzschlag gesetzt und den Bestand veraendert.
    if not SCHREIBEN:
        return
    z["letzter_lauf"] = _jetzt()
    schreibe(ZUSTAND, z)


# --- Auswahl (verfolgte.json) ----------------------------------------------

def waehlen(w):
    """Baut die Verfolgungsliste aus dem Feed - und schreibt nur diese Datei.

    Die Auswahl ist **der Feed**, nicht die Rangliste: Wer nur die Gewinner
    einer Rangliste kopiert, betreibt Zuchtauswahl nach dem Ergebnis
    (Survivorship). Die gemessenen Zahlen der Rangliste werden daneben
    geschrieben, damit die Bilanz spaeter zeigen kann, ob sie die Kopierbarkeit
    vorhersagen - das ist eine offene Frage, keine Annahme.

    Verkaeufe werden gebraucht, um zu sehen, wann ein Vorbild aussteigt. Ob
    ein Kauf kopiert wird, entscheidet das Buch, nicht diese Liste.
    """
    wallet_liste = {}
    zahlen = {}
    for kette in w["ketten"]:
        try:
            for e in lesen.leaderboard(kette):
                zahlen[(kette, e.get("walletAddress"))] = e
        except lesen.Lesefehler as e:
            print("  Rangliste %s nicht abrufbar: %s" % (kette, e))
        for art in ("smart_money", "kol"):
            try:
                trades = lesen.tracker(kette, art)
            except lesefehler_arten() as e:
                print("  Feed %s/%s nicht abrufbar: %s" % (kette, art, e))
                continue
            for t in trades:
                adresse = t.get("walletAddress")
                if not adresse:
                    continue
                schluessel = (kette, adresse)
                eintrag = wallet_liste.setdefault(schluessel, {
                    "kette": kette, "wallet": adresse, "quellen": [],
                    "letzte_sichtung": None})
                eintrag["quellen"].append("tracker/%s" % art)
                zeit = t.get("tradeTime")
                if zeit and (not eintrag["letzte_sichtung"]
                             or int(zeit) > int(eintrag["letzte_sichtung"])):
                    eintrag["letzte_sichtung"] = int(zeit)

    for eintrag in wallet_liste.values():
        eintrag["quellen"] = sorted(set(eintrag["quellen"]))
        z = zahlen.get((eintrag["kette"], eintrag["wallet"]))
        if z:
            eintrag["gemessen"] = True
            for feld, name in (("winRatePercent", "trefferquote_pct"),
                               ("txs", "trades"), ("realizedPnlUsd", "pnl_usd"),
                               ("realizedPnlPercent", "roi_pct"),
                               ("avgBuyValueUsd", "einsatz_schnitt_usd"),
                               ("lastActiveTimestamp", "zuletzt_aktiv_ms")):
                eintrag[name] = z.get(feld)
        else:
            eintrag["gemessen"] = False

    daten = {
        "stand": _jetzt(),
        "regel": ("Alle Wallets, die im Feed (smart_money/kol) handeln. "
                  "Keine Vorauswahl nach Ergebnis; die Ranglistenzahlen "
                  "stehen daneben, entscheiden aber nicht."),
        "ketten": w["ketten"],
        "wallets": sorted(wallet_liste.values(),
                          key=lambda x: (x["kette"], x["wallet"])),
    }
    schreibe(VERFOLGTE, daten)
    gemessen = sum(1 for x in daten["wallets"] if x["gemessen"])
    print("verfolgte.json: %d Wallets (%d davon mit Ranglistenzahlen)"
          % (len(daten["wallets"]), gemessen))
    print("  %s" % ", ".join("%s: %d" % (k, sum(1 for x in daten["wallets"]
                                                if x["kette"] == k))
                             for k in w["ketten"]))
    return daten


def lesefehler_arten():
    """Ein Tupel, damit aeltere und neue Fehlerklassen gefangen werden."""
    return (lesen.Lesefehler, OSError, ValueError)


# --- Buch ------------------------------------------------------------------

def _gefolgt(w):
    d = lade(VERFOLGTE, {})
    return {(x["kette"], x["wallet"]): x for x in d.get("wallets", [])}


def _kaufpreis(preis, w):
    """Was ein Nachahmer wirklich zahlt: teurer als der Vorbildkurs."""
    return preis * (1 + w["slippage_pct"] / 100.0)


def _verkaeuflich(menge, kurs, w):
    """Was am Ende ankommt: billiger, und noch einmal Gebuehr."""
    return menge * kurs * (1 - w["slippage_pct"] / 100.0) * (
        1 - w["gebuehr_pct"] / 100.0)


def _kopie(sig, w, z):
    """Ein Kauf wird zur Buchzeile - oder es gibt einen Grund, warum nicht."""
    if sig["alter_s"] is not None and sig["alter_s"] > w["max_alter_signal_sekunden"]:
        return None, "Signal zu alt (%.0f s)" % sig["alter_s"]
    mk = sig["marktkap_usd"]
    unten, oben = w["marketcap_band_usd"]
    if mk is None:
        return None, "Marktkapitalisierung unbekannt"
    if not unten <= mk <= oben:
        return None, "Marktkapitalisierung %.0f ausserhalb %d-%d" % (mk, unten, oben)
    offen = [p for p in z["positionen"] if p["token"] == sig["token"]]
    if len(offen) >= w["max_kopien_je_token"]:
        return None, "schon %d Kopien auf diesem Token" % len(offen)
    if any(p["kette"] == sig["kette"] and p["token"] == sig["token"]
           and p["wallet"] == sig["wallet"] for p in z["positionen"]):
        return None, "diese Wallet steht hier schon auf diesem Token"

    if w["risiko_pflicht"]:
        try:
            r = lesen.risiko(sig["token"], sig["kette"])
        except lesen.Lesefehler as e:
            return None, "Risikopruefung nicht moeglich: %s" % e
        if r["stufe"] not in w["max_risiko_stufen"]:
            return None, "Risikostufe %s (%s)" % (r["stufe"],
                                                  ",".join(r["merkmale"][:3]))
    else:
        r = {"stufe": "ungeprueft", "merkmale": []}

    einsatz = w["max_einsatz_je_kopie_usd"]
    kauf = _kaufpreis(sig["preis"], w)
    gebuehr = einsatz * w["gebuehr_pct"] / 100.0
    menge = (einsatz - gebuehr) / kauf
    return {
        "kette": sig["kette"], "wallet": sig["wallet"], "token": sig["token"],
        "symbol": sig["symbol"], "quelle": sig["quelle"],
        "einsatz_usd": einsatz, "menge": menge, "preis_vorbild": sig["preis"],
        "preis_einstieg": kauf, "marktkap_usd": mk, "risiko": r["stufe"],
        "stop_preis": kauf * (1 - w["stop_pct"] / 100.0),
        "ziel_preis": kauf * (1 + w["ziel_pct"] / 100.0),
        "frist": _plus_stunden(w["haltedauer_stunden"]),
        "eroeffnet": _heute(), "eroeffnet_zeit": _jetzt(),
    }, None


def _plus_stunden(stunden):
    from datetime import timedelta
    return (datetime.now(timezone.utc)
            + timedelta(hours=stunden)).isoformat(timespec="seconds")


def _bis_zeit(wert):
    try:
        return datetime.fromisoformat(wert) if wert else None
    except (TypeError, ValueError):
        return None


def eroeffne(z, sig, w):
    p, grund = _kopie(sig, w, z)
    if not p:
        return grund
    z["positionen"].append(p)
    print("  AUF %-10s %-28s @ %.10g (Vorbild %.10g, %.1f%% Slippage) "
          "%.0f USD, %s"
          % (p["symbol"], p["token"], p["preis_einstieg"], p["preis_vorbild"],
             w["slippage_pct"], p["einsatz_usd"], p["risiko"]))
    print("      %-10s %-28s  Stop %.10g (%.0f%%)  Ziel %.10g (%.0f%%)  "
          "Frist %s"
          % (p["symbol"], p["token"], p["stop_preis"], w["stop_pct"],
             p["ziel_preis"], w["ziel_pct"], p["frist"][11:16]))
    journal(zeit=_jetzt(), modus="papier", aktion="eroeffnen", kette=p["kette"],
            wallet=p["wallet"], token=p["token"], symbol=p["symbol"],
            preis="%.10g" % p["preis_einstieg"], menge="%.6f" % p["menge"],
            einsatz_usd="%.2f" % p["einsatz_usd"],
            marktkap_usd="%.0f" % p["marktkap_usd"],
            slippage_pct=w["slippage_pct"], gebuehr_pct=w["gebuehr_pct"],
            grund="kopie")
    return None


def pruefe_ausstiege(z, w):
    """Stop, Ziel, Frist - und der Kill-Switch ueber das ganze Buch."""
    offen = z["positionen"]
    if not offen:
        return
    kurse = {}
    try:
        kurse = lesen.preise([(p["kette"], p["token"]) for p in offen])
    except lesen.Lesefehler as e:
        print("  Kurse nicht abrufbar (%s) - Bestand bleibt" % e)
        return

    behalten, jetzt = [], datetime.now(timezone.utc)
    for p in offen:
        kurs = kurse.get((p["kette"], p["token"]))
        grund = None
        if kurs is None:
            print("  %-10s %-28s kein Kurs - Kopie bleibt" % (p["symbol"],
                                                             p["token"]))
            behalten.append(p)
            continue
        if kurs <= p["stop_preis"]:
            grund = "stop"
        elif kurs >= p["ziel_preis"]:
            grund = "ziel"
        elif jetzt >= (_bis_zeit(p["frist"]) or jetzt):
            grund = "frist"
        if not grund:
            behalten.append(p)
            continue
        erloes = _verkaeuflich(p["menge"], kurs, w)
        print("  %s %-10s %-28s @ %.10g  (%s)  G/V %+.2f USD auf %.0f USD"
              % ("ZU " if SCHREIBEN else "WAERE ZU", p["symbol"], p["token"],
                 kurs, grund, erloes - p["einsatz_usd"], p["einsatz_usd"]))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                kette=p["kette"], wallet=p["wallet"], token=p["token"],
                symbol=p["symbol"], preis="%.10g" % kurs,
                menge="%.6f" % p["menge"], einsatz_usd="%.2f" % p["einsatz_usd"],
                wert_usd="%.2f" % erloes, grund=grund)
    z["positionen"] = behalten


def kill_switch(z, w):
    """Ruecklauf des Buches gegen die Grenze: dann alles flach."""
    if not z["positionen"]:
        return False
    try:
        kurse = lesen.preise([(p["kette"], p["token"])
                              for p in z["positionen"]])
    except lesen.Lesefehler:
        return False
    if not kurse:
        return False
    wert = sum(_verkaeuflich(p["menge"], kurse[(p["kette"], p["token"])], w)
               for p in z["positionen"]
               if (p["kette"], p["token"]) in kurse)
    einsatz = sum(p["einsatz_usd"] for p in z["positionen"]
                  if (p["kette"], p["token"]) in kurse)
    if wert - einsatz > -w["kill_switch_gesamt_usd"]:
        return False
    print("- Kill-Schwelle erreicht (%+.2f USD) -> alle Kopien zu -"
          % (wert - einsatz))
    return True


def flach_stellen(z, w, grund):
    for p in list(z["positionen"]):
        try:
            kurs = lesen.preise([(p["kette"], p["token"])]).get(
                (p["kette"], p["token"]))
        except lesen.Lesefehler:
            kurs = None
        erloes = _verkaeuflich(p["menge"], kurs, w) if kurs else 0.0
        print("  NOT-ZU %-10s %-28s  G/V %+.2f USD  (%s)"
              % (p["symbol"], p["token"], erloes - p["einsatz_usd"], grund))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                kette=p["kette"], wallet=p["wallet"], token=p["token"],
                symbol=p["symbol"], preis="" if not kurs else "%.10g" % kurs,
                menge="%.6f" % p["menge"], einsatz_usd="%.2f" % p["einsatz_usd"],
                wert_usd="%.2f" % erloes, grund=grund)
    z["positionen"] = []


# --- Bilanz ----------------------------------------------------------------

def bilanz(w):
    """Welche Wallets haben getragen - und welche gemessenen Zahlen luegen."""
    if not os.path.exists(JOURNAL):
        print("Noch keine Buchzeile - kein Journal.")
        return
    gefolgt = {k: v for k, v in _gefolgt(w).items()}
    je_wallet = {}
    offen = {}
    with open(JOURNAL, newline="", encoding="utf-8") as f:
        for zeile in csv.DictReader(f):
            schluessel = (zeile["kette"], zeile["wallet"])
            if zeile["aktion"] == "eroeffnen":
                offen[schluessel] = offen.get(schluessel, 0) + int(
                    float(zeile["einsatz_usd"] or 0) * 100)
                continue
            einsatz = int(float(zeile["einsatz_usd"] or 0) * 100)
            wert = int(float(zeile["wert_usd"] or 0) * 100)
            e = je_wallet.setdefault(schluessel, {"runden": 0, "gv": 0,
                                                  "symbole": set()})
            e["runden"] += 1
            e["gv"] += wert - einsatz
            e["symbole"].add(zeile["symbol"])
    if not je_wallet:
        print("Keine abgeschlossene Kopie im Journal.")
        return
    print("Bilanz aus %d abgeschlossenen Kopien (Zahlen in USD):" % sum(
        e["runden"] for e in je_wallet.values()))
    for (kette, wallet), e in sorted(je_wallet.items(),
                                     key=lambda x: -x[1]["gv"]):
        z = gefolgt.get((kette, wallet), {})
        zahlen = ("Trefferquote %s%%, %s Trades" % (z.get("trefferquote_pct"),
                                                    z.get("trades"))
                  if z.get("gemessen") else "nicht in der Rangliste")
        print("  %-9s %-44s %3d Runden  G/V %+8.2f  (%s)"
              % (kette, wallet, e["runden"], e["gv"] / 100.0, zahlen))


# --- Lauf ------------------------------------------------------------------

def zeige_wachen(w):
    print("Grenzen der Spiegel-Spur (Papier):")
    for name in ("ketten", "max_einsatz_je_kopie_usd", "max_offen",
                 "max_neu_je_zyklus", "max_kopien_je_token",
                 "kill_switch_gesamt_usd", "slippage_pct", "gebuehr_pct",
                 "stop_pct", "ziel_pct", "haltedauer_stunden",
                 "max_alter_signal_sekunden", "marketcap_band_usd",
                 "max_risiko_stufen", "herzschlag_max_minuten"):
        print("  %-30s %s" % (name, w.get(name)))
    print("  %-30s %s" % ("handel_erlaubt", w.get("handel_erlaubt")))


def signale_sammeln(w):
    aus, gesehen = [], set()
    for kette in w["ketten"]:
        for art in ("smart_money", "kol"):
            try:
                sig = lesen.signale(kette, art)
            except lesefehler_arten() as e:
                print("  Feed %s/%s nicht abrufbar: %s" % (kette, art, e))
                continue
            for s in sig:
                if not s["tx"] or s["tx"] in gesehen:
                    continue
                gesehen.add(s["tx"])
                aus.append(s)
    return aus


def lauf(modus):
    global SCHREIBEN
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Die Vorschau liest und rechnet, schreibt aber nichts - kein Journal,
    # kein Zustand. Alles andere schreibt (Papier ist ein Lauf, kein Entwurf).
    SCHREIBEN = modus != "vorschau"

    w = lade(WACHEN, None)
    if not w:
        print("wachen.json fehlt oder ist unlesbar - kein Lauf.")
        return 1

    if modus == "waehlen":
        waehlen(w)
        return 0
    if modus == "wachen":
        zeige_wachen(w)
        return 0
    if modus == "bilanz":
        bilanz(w)
        return 0
    if modus == "messen":
        return messen(w, lade_zustand())

    z = lade_zustand()

    if modus == "live":
        # Genau ein Grund, und das Wort Freigabefenster kommt darin nicht vor:
        # dauerlauf.nur_fenster_fehlt fragt nur, wenn der Grund dieses Wort
        # traegt. Es gibt hier keinen Live-Pfad, den eine Freigabe oeffnen
        # koennte.
        print("--live angefordert, aber gesperrt: kein Live-Pfad in dieser "
              "Spur (Papier)")
        print("-> es wird Papier gebucht.")

    if z["positionen"] and not _frisch(z, w):
        print("- Herzschlag alt (%s) -> alle Kopien zu, kein Neuerwerb dieser "
              "Lauf -" % z.get("letzter_lauf"))
        flach_stellen(z, w, "herzschlag_alt")
        schreibe_zustand(z)
        return 0

    pruefe_ausstiege(z, w)
    if kill_switch(z, w):
        flach_stellen(z, w, "kill_switch")
        schreibe_zustand(z)
        return 0

    gefolgt = _gefolgt(w)
    if not gefolgt:
        print("verfolgte.json ist leer - erst '--waehlen' laufen lassen.")
        return 1
    sig = signale_sammeln(w)
    neu = 0
    for s in sig:
        if len(z["positionen"]) >= w["max_offen"]:
            print("  Buch voll (%d Kopien) - Rest faellt aus"
                  % w["max_offen"])
            break
        if neu >= w["max_neu_je_zyklus"]:
            print("  Zyklusdeckel erreicht (%d neue Kopien)" % w["max_neu_je_zyklus"])
            break
        if (s["kette"], s["wallet"]) not in gefolgt:
            continue
        if modus == "vorschau":
            p, grund = _kopie(s, w, z)
            print("  %s %-10s %-28s %s"
                  % ("WAERE" if p else "NEIN ", s["symbol"][:10], s["token"],
                     "%d USD" % w["max_einsatz_je_kopie_usd"] if p else grund))
            if p:
                neu += 1
                z["positionen"].append(p)      # nur im Speicher, kein Schreiben
            continue
        grund = eroeffne(z, s, w)
        if grund is None:
            neu += 1

    print("=== Spiegel (PAPIER%s) | %d Signale, %d verfolgte Wallets | "
          "%d Kopien offen, %d neu ==="
          % ("" if modus != "vorschau" else ", Vorschau", len(sig), len(gefolgt),
             len(z["positionen"]), neu))
    if modus == "vorschau":
        print("Live waere gesperrt durch: kein Live-Pfad in dieser Spur (Papier)")
        return 0
    print("Live waere gesperrt durch: kein Live-Pfad in dieser Spur (Papier)")
    schreibe_zustand(z)
    return 0


def messen(w, z):
    """Die Kosten-Annahmen gegen echte Bucheindruecke halten.

    Zwei Messungen, weil zwei verschiedene Kosten zusammenkommen:

      1. **Tiefe.** Wie stark bewegt ein Einsatz von X USD den Preis im Pool?
         Naeherung fuer ein Constant-Product-Buch: 2 x Einsatz / Liquiditaet
         (in Prozent). Das ist eine *untere* Grenze - konzentrierte
         Liquiditaet, Spread und Prioritaetsgebuehren stecken nicht darin.
      2. **Nachlauf.** Wie weit ist der Kurs schon weg von dem Kurs, den das
         Vorbild bekommen hat? Das ist die eigentliche Strafe beim Nachahmen,
         und sie steht in keiner Pool-Tiefe. Gemessen an den frischesten
         Signalen: Kurs jetzt gegen Kurs im Signal.

    Gibt beide Verteilungen aus und schreibt sie nach daten/messung.json.
    Geschrieben wird nichts anderes - die Messung aendert kein Buch.
    """
    sig = signale_sammeln(w)
    frisch = [s for s in sig if s["alter_s"] is not None
              and s["alter_s"] <= w["max_alter_signal_sekunden"]]
    auswahl = []
    for s in frisch:
        if s["token"] not in [x["token"] for x in auswahl]:
            auswahl.append(s)
        if len(auswahl) >= 15:
            break
    lesen_je_kette = auswahl
    print("Tiefe und Nachlauf, %d frische Signale" % len(frisch))
    if not auswahl:
        print("  Keine frischen Signale - nichts zu messen.")
        return 1

    zeilen = []
    try:
        # Jede Kette fuer sich: die Stapelabfrage nimmt Kettenindex und Adresse.
        kurse = {}
        for kette in sorted({s["kette"] for s in auswahl}):
            kurse.update(lesen.preise([(kette, s["token"]) for s in auswahl
                                       if s["kette"] == kette]))
    except lesen.Lesefehler as e:
        print("  Kurse nicht abrufbar: %s" % e)
        kurse = {}

    for s in lesen_je_kette:
        t = s["token"]
        try:
            i = lesen.preise_info(t, s["kette"])
        except (lesen.Lesefehler, KeyError, TypeError) as e:
            print("  %s: keine Tiefe (%s)" % (t[:12], e))
            continue
        liq = _zahl(i.get("liquidity"))
        einsatz = w["max_einsatz_je_kopie_usd"]
        tiefe = (2 * einsatz / liq * 100) if liq else None
        kurs_jetzt = kurse.get((s["kette"], t))
        nachlauf = None
        if kurs_jetzt:
            nachlauf = (kurs_jetzt / s["preis"] - 1) * 100
        zeilen.append({"kette": s["kette"], "token": t, "symbol": s["symbol"],
                       "liquiditaet_usd": liq, "einsatz_usd": einsatz,
                       "tiefe_pct": tiefe, "nachlauf_pct": nachlauf,
                       "alter_s": s["alter_s"],
                       "marktkap_usd": _zahl(i.get("marketCap")),
                       "halter": i.get("holders")})
        print("  %-10s %-9s Liq %10s  Tiefe %7s  Nachlauf %8s  (Alter %ss, %s Halter)"
              % (s["symbol"][:10], s["kette"],
                 "?" if liq is None else "%.0f" % liq,
                 "?" if tiefe is None else "%.3f%%" % tiefe,
                 "?" if nachlauf is None else "%+.2f%%" % nachlauf,
                 "?" if s["alter_s"] is None else "%.0f" % s["alter_s"],
                 zeilen[-1]["halter"]))

    def schnitt(feld):
        werte = [z[feld] for z in zeilen if z[feld] is not None]
        if not werte:
            return None
        werte.sort()
        return (sum(werte) / len(werte), werte[len(werte) // 2], werte[-1])

    print()
    for name, feld in (("Tiefe (untere Grenze)", "tiefe_pct"),
                       ("Nachlauf", "nachlauf_pct")):
        m = schnitt(feld)
        print("  %-22s Schnitt %s, Median %s, groesster %s"
              % (name, "?" if not m else "%.2f%%" % m[0],
                 "?" if not m else "%.2f%%" % m[1],
                 "?" if not m else "%.2f%%" % m[2]))
    print("  Annahme in wachen.json: %.1f%% Slippage + %.1f%% Gebuehr"
          % (w["slippage_pct"], w["gebuehr_pct"]))

    ordner = os.path.join(HIER, "daten")
    if not os.path.isdir(ordner):
        os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, "messung.json"), "w", encoding="utf-8") as f:
        json.dump({"zeit": _jetzt(), "einsatz_usd": w["max_einsatz_je_kopie_usd"],
                   "annahme_slippage_pct": w["slippage_pct"],
                   "annahme_gebuehr_pct": w["gebuehr_pct"],
                   "werte": zeilen}, f, indent=2, ensure_ascii=False)
    print("  -> daten/messung.json geschrieben (nicht versioniert)")
    return 0


def _frisch(z, w):
    letzte = _bis_zeit(z.get("letzter_lauf"))
    if not letzte:
        return False
    grenze = w.get("herzschlag_max_minuten", 90)
    return (datetime.now(timezone.utc) - letzte).total_seconds() <= grenze * 60


def main():
    # Der Dauerlauf startet dieses Skript als eigenen Prozess (SPUREN
    # ["spiegel"], skript=spiegel.py) - Start und Ende melden sich deshalb
    # hier am Bus.
    # Muster: xperp/handeln.py. Ein toter Bus bricht den Lauf nicht ab.
    with ereignis.lauf("handel/spiegel"):
        return _main()


def _main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--waehlen", action="store_const", const="waehlen",
                   dest="modus", help="verfolgte.json aus dem Feed bauen")
    p.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    p.add_argument("--vorschau", action="store_const", const="vorschau",
                   dest="modus")
    p.add_argument("--papier", action="store_const", const="papier", dest="modus")
    p.add_argument("--bilanz", action="store_const", const="bilanz", dest="modus")
    p.add_argument("--messen", action="store_const", const="messen", dest="modus",
                   help="Tiefe und Nachlauf gegen die Kostenannahmen messen")
    p.add_argument("--live", action="store_const", const="live", dest="modus")
    p.set_defaults(modus="vorschau")
    a = p.parse_args()
    return lauf(a.modus)


if __name__ == "__main__":
    raise SystemExit(main())
