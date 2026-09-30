"""Dritte Spur: Kraken, Spot, nur Long, kein Hebel - in der Quotewaehrung des Paares.

Aufruf (aus diesem Ordner):
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --vorschau
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --papier    # Standard der Routine
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --live      # echte Orders
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --wachen    # Wochenlauf

Seit dem 14.09.2026 fuehrt der Dauerlauf (dauerlauf.py) diese Spur: sie steht
wieder in dauerlauf.SPUREN und wird alle 15 Minuten geprueft - Stop und Ziel
greifen damit durchgehend statt einmal am Tag. Den Scan (die Rangliste)
rechnet weiterhin einmal taeglich die Aufgabe MaxHirn-Kraken-Spur3; gehandelt
wird dort nicht mehr. Den Einstandskurs nimmt der Lauf vom lebenden Kurs,
nicht aus dem Bericht (der Bericht waehlt aus, er nennt keinen Preis mehr).

Diese Sperren muessen ALLE offen sein, sonst laeuft trotz --live nur Papier:
    1. wachen.json  handel_erlaubt == true
    2. KRAKEN_SPOT_API_KEY / KRAKEN_SPOT_API_SECRET gesetzt
    3. --live ausdruecklich auf der Kommandozeile
    4. wachen.json  freigabe.erfuellt == true      (Handelsregeln, Bedingung 1)
    5. Herzschlag frisch                            (Bedingung 3)
    6. rollierender Erwartungswert nicht negativ    (Bedingung 5)
    7. journal_zweitziel gesetzt und erreichbar     (Bedingung 4)
    8. mindestens mindest_guthaben_je_quote frei in der WAEHRUNG DES PAARES
    9. eine Sitzung am Bildschirm, die das Freigabefenster bedienen kann
Fehlt eine, wird Papier gehandelt und es wird gesagt, welche Sperre zu war.

Sperre 7 und 8 hat diese Spur zusaetzlich zu Spur 1. Sperre 8, weil am
02.09.2026 nur 0,0094 EUR frei auf dem Konto lagen: ein Kauf-Automat ohne
Fiat kauft nichts, er scheitert nur - und zwar in jedem Lauf, mit einer
Fehlermeldung, die nach einem Schluesselproblem aussieht.

QUOTEWAEHRUNG (seit 30.09.2026, Auftrag Max 'kraken auch mit eurc/usdc
handel'): Die Spur war auf EUR festgelegt - Watchlist in EUR, Tor gegen
"ZEUR". Auf demselben Konto liegt Kapital auch in EURC und USDC. quote.py
holt die Quote JE PAAR aus der Kraken-API (Feld `quote`, sonst `wsname`);
daraus entstehen drei Dinge:
  - das Guthaben-Tor prueft in der Waehrung des Paares, nicht in EUR,
  - ein Buch fuehrt EINE Waehrung (Einsatz, Erloes, Ruecklauf und Ratsche
    summieren Betraege - eine Summe aus EUR und USDC waere keine Zahl),
  - die Basis-Kennung (`wsname`) verhindert, dass dasselbe Instrument
    zweimal im Buch steht, nur weil es in zwei Waehrungen notiert ist.
Der Feldname `eur` im Buch und im Journal bleibt trotzdem: auswertung_alle.py
liest ihn. Eine Position in einer anderen Waehrung traegt zusaetzlich
`waehrung`, und im Journal steht die Waehrung hinter dem Grund.
Die Erweiterung allein schaltet NICHTS scharf: das Tor vergleicht weiter
gegen mindest_guthaben_je_quote, und das Konto liegt in jeder Waehrung darunter.

Der Unterschied zum Kraken-MCP-Server ist der ganze Punkt dieser Spur: Dort
liegt dieselbe API, aber ohne wachen.json, ohne Journal, ohne Herzschlag -
deshalb bleiben seine schreibenden Werkzeuge verboten (Wissen/Handelsregeln.md,
Abschnitt "Kraken"). Hier gelten die Wachen, deshalb darf hier gehandelt
werden.

Gebuehren stehen im Papierlauf mit drin: 0,40 % je Ausfuehrung, also 0,80 %
je Runde. Ein Papierlauf, der sie weglaesst, empfiehlt eine Strategie, die
live verliert - genau der Fehler aus Wissen/Handelsbots.md.

Der Live-Pfad ist mangels Freigabe und Guthaben noch NIE scharf gelaufen. Vor
dem ersten scharfen Lauf mit einem einzigen Paar und Kleinstbetrag gegenpruefen.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

HIER = Path(__file__).resolve().parent
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

# Freigabefenster ebenso ueber den PFAD laden - Handel/ liegt im Spurlauf
# NICHT auf sys.path (nur <spur>/../../Bus). Ein blankes 'import freigabefenster'
# scheitert mit ModuleNotFoundError; zeitfenster_offen() wuerde das still
# schluecken und die Spur koennte im Dauerlauf nie live gehen (Befund
# scanner 22.09.2026 - dieselbe Falle).
_fw_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "freigabefenster.py")
_fw_spec_obj = _rs_spec("freigabefenster", _fw_datei)
freigabefenster = _rs_mod(_fw_spec_obj)
_fw_spec_obj.loader.exec_module(freigabefenster)

# Freigabe-Beleg (Agenten/Handel/freigabebeleg.py). Dieselbe Erlaubnis, die
# auch das Kraken-MCP-Werkzeug `kraken_order_mit_beleg` verlangt - damit ist
# die Erlaubnis EINE Datei: die Spur entscheidet unter ihren Wachen, der MCP
# (oder das Hand-Skript) ist nur die ausfuehrende Hand. Ebenfalls ueber den
# PFAD geladen, aus demselben Grund wie das Fenster.
_fb_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "freigabebeleg.py")
_fb_spec_obj = _rs_spec("freigabebeleg", _fb_datei)
freigabebeleg = _rs_mod(_fb_spec_obj)
_fb_spec_obj.loader.exec_module(freigabebeleg)

ZUSTAND = risikostufe.datei(HIER / "zustand.json")
JOURNAL = risikostufe.datei(HIER / "handelsjournal.csv")

# Der Bus liegt zwei Ebenen hoeher (Agenten/Bus). Ohne diesen Eintrag meldet
# sich der Lauf nicht am Journal - und ein Zyklus ohne Bus-Eintrag ist von
# einem ausgefallenen nicht zu unterscheiden. Dieselbe Zeile wie in
# xperp/handeln.py und swap/handeln.py.
sys.path.insert(0, str(HIER.parent.parent / "Bus"))
import ereignis                                          # noqa: E402
import kraken                                            # noqa: E402
import quote                                             # noqa: E402
import scan                                              # noqa: E402
import wachen_kraken as wp                               # noqa: E402

# Sekunden ohne Bedienung, nach denen das Freigabefenster von selbst ablehnt.
# MUSS unter dauerlauf.TIMEOUT_S bleiben (700): ein Abbruch des Aufrufers
# toetet den Lauf mitten in der Wartezeit und reisst die Spiegelung mit
# (21.09.2026, scanner: Fenster 600 s > Abbruch 300 s).
FREIGABE_ZEITLIMIT_S = 600


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def lade_zustand():
    if ZUSTAND.exists():
        return json.loads(ZUSTAND.read_text("utf-8"))
    return {"positionen": [], "letzte_stops": {}, "letzter_lauf": None,
            "modus": None}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    ZUSTAND.write_text(json.dumps(z, ensure_ascii=False, indent=2), "utf-8")


def journal(*felder):
    neu = not JOURNAL.exists()
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        if neu:
            s.writerow(["zeit", "modus", "aktion", "paar", "preis", "eur",
                        "menge", "stop", "ziel", "grund"])
        s.writerow(felder)


# --- Vorschlaege ---------------------------------------------------------------

def stop_prozent(z, w):
    """Stop-Abstand aus der Volatilitaet, hart auf den Wachen-Rahmen gedeckelt.
    Die Untergrenze liegt hier bei 5 % statt 4 %: bei 0,80 % Gebuehr je Runde
    ist ein engerer Stop zu einem Sechstel Kosten."""
    vola = z["kennzahlen"]["volatilitaet_pa"]
    roh = 3.0 + 6.0 * min(vola, 1.5)
    return max(w["pflicht_stop_prozent_min"],
               min(w["pflicht_stop_prozent_max"], round(roh, 1)))


def _kurs_jetzt(inst, rueckfall):
    """Einstandskurs fuer einen Vorschlag: der lebende Kurs, nicht der Preis
    aus dem Bericht.

    Bis zum 14.09.2026 lief diese Spur einmal am Tag, der Scan unmittelbar
    davor - der Berichtspreis war Sekunden alt und damit richtig. Im
    Viertelstundentakt waere er bis zu einen Tag alt: Einstand, Stop und Ziel
    haengen dann an einem Kurs von gestern, und die Runde misst eine
    Gelegenheit, die es so nicht gab. Der Bericht waehlt weiter aus (Score,
    Volatilitaet, Chance/Risiko); den Preis holt der Lauf selbst. Faellt der
    Kurs aus, gilt der Berichtspreis - ein Kursausfall darf den Zyklus nicht
    anhalten.
    """
    try:
        kurs = float(kraken.letzter_kurs(inst))
        return kurs if kurs > 0 else rueckfall
    except Exception:                                    # noqa: BLE001
        return rueckfall


def vorschlaege(bericht, w):
    aus = []
    for z in bericht["werte"]:
        vola = z["kennzahlen"]["volatilitaet_pa"]
        if not (z["score"] >= w["mindest_score"]
                and vola <= w["max_volatilitaet_pa"]
                and z["verhaeltnis"] >= w["mindest_chance_risiko"]):
            continue
        try:
            waehrung = quote.quote_von_paar(z["inst"])
            basis = quote.basis_von_paar(z["inst"])
        except quote.QuoteUnbekannt as e:
            # Ohne Quote gibt es keine Waehrung fuer das Buch und kein
            # Guthaben-Tor - der Kandidat faellt raus, statt in einen
            # geratenen Markt zu laufen.
            print("  -- %-10s uebersprungen: %s" % (z["inst"], e))
            continue
        einstieg = _kurs_jetzt(z["inst"], z["preis"])
        sp = stop_prozent(z, w)
        stop = round(einstieg * (1 - sp / 100.0), 8)
        ziel = round(einstieg + 2.0 * (einstieg - stop), 8)   # Chance/Risiko 2:1
        aus.append({"inst": z["inst"], "basis": basis, "waehrung": waehrung,
                    "score": z["score"], "einstieg": einstieg,
                    "stop": stop, "stop_pct": sp, "ziel": ziel,
                    "eur": w["max_pro_trade_eur"]})
    return aus


# --- Mengen ----------------------------------------------------------------

def menge_fuer(paar, eur, kurs):
    """Wieviel Basiswaehrung kauft dieser Betrag? Abgerundet auf die
    Stellenzahl des Paares - aufrunden wuerde den Rahmen ueberschreiten.

    Gibt (menge, fehler) zurueck. Ein Fehler heisst: diese Order wuerde
    Kraken ablehnen, und zwar bevor sie Geld kostet."""
    try:
        info = kraken.paar_info(paar)
    except Exception as e:  # noqa: BLE001
        return 0.0, "Paar-Info nicht abrufbar (%s)" % e
    stellen = info["mengen_stellen"]
    roh = eur / kurs if kurs > 0 else 0.0
    menge = int(roh * 10 ** stellen) / 10 ** stellen
    if menge < info["mindestmenge"]:
        return 0.0, ("Menge %.8f unter Mindestmenge %.8f"
                     % (menge, info["mindestmenge"]))
    if menge * kurs < info["mindestwert"]:
        return 0.0, ("Wert %.2f EUR unter Mindestwert %.2f"
                     % (menge * kurs, info["mindestwert"]))
    return menge, None


# --- Quotewaehrung ---------------------------------------------------------
#
# Bis 30.09.2026 war die Spur auf EUR festgelegt: Watchlist in EUR, Tor gegen
# "ZEUR", Journalspalte "eur". Auf demselben Kraken-Konto liegt Kapital auch
# in anderen Quotewaehrungen (EUR, EURC, USDC). quote.py holt die Quote JE
# PAAR aus der API - hier wird daraus die Waehrung des BUCHS und die des
# Guthaben-Tors.

def _basis_oder_paar(paar):
    """Basis-Kennung des Paares, sonst der Paarname selbst.

    Der Rueckfall auf den Namen ist fuer Altbestaende: steht das Paar nicht
    mehr in der API, ist sein eigener Name die einzige Kennung, die bleibt."""
    try:
        return quote.basis_von_paar(paar)
    except quote.QuoteUnbekannt:
        return str(paar or "").strip().upper()


def _noetig_je_quote(w):
    """({lesbare Waehrung: Mindestguthaben}, Vorgabewert).

    Fehlt die Karte mindest_guthaben_je_quote, gilt der alte EUR-Wert
    mindest_guthaben_eur fuer JEDE Waehrung - eine wachen.json von vor dem
    30.09.2026 bleibt damit benutzbar, ohne dass das Tor still aufgeht."""
    try:
        vorgabe = float(w.get("mindest_guthaben_eur", 0) or 0)
    except (TypeError, ValueError):
        vorgabe = 0.0
    aus = {}
    for k, v in (w.get("mindest_guthaben_je_quote") or {}).items():
        try:
            aus[quote.lesbar(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return aus, vorgabe


def guthaben_lage(w):
    """{lesbare Waehrung: (frei, noetig)} fuer jede Quote der Watchlist.

    EIN Kontostaende-Abruf fuer alle Waehrungen, nicht einer je Waehrung.
    Nur Waehrungen, die in der Watchlist wirklich vorkommen - eine Waehrung
    ohne Paar braucht kein Guthaben."""
    quoten = quote.quoten_der_watchlist(w.get("watchlist") or [])
    if not quoten:
        return {}
    staende = kraken.kontostaende()
    karte, vorgabe = _noetig_je_quote(w)
    aus = {}
    for q in quoten:
        name = quote.lesbar(q)
        aus[name] = (quote.frei(staende, q), karte.get(name, vorgabe))
    return aus


def lage_text(lage):
    if not lage:
        return "keine Quotewaehrung in der Watchlist"
    return ", ".join("%s %.2f/%.2f" % (name, frei, noetig)
                     for name, (frei, noetig) in sorted(lage.items()))


def bevorzugte_waehrung(w, lage):
    """In welcher Waehrung ein LEERES Buch anfangen darf.

    quote_vorrang aus wachen.json entscheidet - Zahlen in der Datei, nicht im
    Code. Waehrungen ohne Deckung fallen raus. None heisst: keine Waehrung
    ueber dem Tor, dann wird nicht eingestiegen."""
    vorrang = [quote.lesbar(x) for x in (w.get("quote_vorrang") or [])]
    if not vorrang:
        vorrang = sorted(lage)
    for name in vorrang:
        frei, noetig = lage.get(name, (0.0, 0.0))
        if frei > 0 and frei >= noetig:
            return name
    return None


def ziel_waehrung(z, w, lage, live):
    """In welcher Waehrung dieses Buch gefuehrt wird.

    1. Steht das Buch schon, gilt seine Waehrung - sonst waeren Einsatz,
       Erloes, Ruecklauf und Ratsche eine Summe aus zwei Waehrungen.
    2. Live: die erste GEDECKTE Waehrung aus quote_vorrang. Das Guthaben-Tor
       hat das schon geprueft; hier wird es nur angewandt.
    3. Sonst (Papier, oder das Guthaben war nicht lesbar): die erste Waehrung
       aus quote_vorrang. Ein PAPIERLAUF darf nie davon abhaengen, ob das
       Konto lesbar ist - ein Netzausfall oder ein fehlender Schluessel
       wuerde ihn sonst stillstellen, und niemand saehe den Unterschied."""
    eigene = buch_waehrung(z)
    if eigene:
        return eigene
    if live:
        bevorzugt = bevorzugte_waehrung(w, lage)
        if bevorzugt:
            return bevorzugt
    vorrang = [quote.lesbar(x) for x in (w.get("quote_vorrang") or [])]
    if vorrang:
        return vorrang[0]
    return quote.lesbar(w.get("waehrung") or "EUR")


def buch_waehrung(z):
    """Die Waehrung, in der das Buch steht - None, wenn es leer ist.

    Ein Buch fuehrt EINE Waehrung: Einsatz, Erloes, Ruecklauf und die
    Drawdown-Ratsche summieren Betraege, und eine Summe aus EUR und USDC ist
    keine Zahl. Wer mischen will, braucht zuerst einen Umrechnungskurs je
    Position - das ist ein eigener Bau, kein Nebeneffekt."""
    for p in z.get("positionen") or []:
        name = quote.lesbar(p.get("waehrung") or "")
        if name:
            return name
    return None


# --- Ausstieg / Einstieg ---------------------------------------------------

def in_abklingzeit(paar, z, w):
    """Abklingzeit nach einem Stop - ueber die BASIS, nicht ueber den Paarnamen.

    Ein Stop in SOLEUR und ein neuer Kauf in SOLUSDC sind dasselbe Instrument;
    die Sperre muss beide treffen, seit die Spur mehrere Quotewaehrungen
    fuehrt. Alte Eintraege stehen als Paarname in letzte_stops und werden
    genauso aufgeloest. Ein unlesbares Datum sperrt NICHT dauerhaft."""
    eintraege = z.get("letzte_stops") or {}
    if not eintraege:
        return False
    basis = _basis_oder_paar(paar)
    letzter = None
    for k, d in eintraege.items():
        if _basis_oder_paar(k) != basis:
            continue
        try:
            tag = date.fromisoformat(str(d))
        except (TypeError, ValueError):
            continue
        if letzter is None or tag > letzter:
            letzter = tag
    if letzter is None:
        return False
    return (date.fromisoformat(_heute()) - letzter).days < w["abklingzeit_tage"]


def _erloes(p, kurs, w):
    """Verkaufserloes nach Gebuehr. Die Gebuehr steht im Papierlauf genauso
    drin wie live - sonst misst Bedingung 1 eine Strategie, die es nicht gibt."""
    return p["menge"] * kurs * (1.0 - w["gebuehr_taker"])


def raeume_offene_stops(z):
    """Stops abarbeiten, die beim Ausstieg nicht stornierbar waren.

    Sie stehen weiter beim Handelsplatz im Buch. Beim naechsten Live-Lauf wird
    es erneut versucht; erst wenn einer wirklich weg ist, faellt der Eintrag.
    """
    offen = z.get("offene_stops") or []
    rest = []
    for e in offen:
        try:
            kraken.order_stornieren(e["stop_txid"])
            print("  offener Stop %s storniert" % e["stop_txid"])
        except Exception as ex:  # noqa: BLE001
            if not kraken.stop_gefuellt(e.get("stop_txid")):
                rest.append(e)
                print("  offener Stop %s bleibt liegen: %s"
                      % (e["stop_txid"], ex), file=sys.stderr)
    if len(rest) != len(offen):
        z["offene_stops"] = rest


def _schliesse(p, kurs, w, live, grund, z):
    """Eine Position schliessen. Gibt True zurueck, wenn sie weg ist."""
    if live:
        if p.get("stop_txid"):
            try:
                kraken.order_stornieren(p["stop_txid"])   # Stop zuerst weg
            except Exception as e:  # noqa: BLE001
                # Schon ausgeloest oder schon storniert - trotzdem verkaufen.
                # Genau hier blieben Positionen im Buch stehen, die am Markt
                # laengst verkauft waren.
                print("  Stop %s nicht stornierbar: %s" % (p["stop_txid"], e),
                      file=sys.stderr)
                if kraken.stop_gefuellt(p["stop_txid"]):
                    print("  der Boersen-Stop hat ausgeloest - Position ist weg")
                    kurs = p["stop"]
                    grund = "stop (boerse)"
                    erloes = _erloes(p, kurs, w)
                    print("  AUSSTIEG (%s): %s @ %-12.6g  G/V %+.2f EUR"
                          % (grund, p["paar"], kurs, erloes - p["eur"]))
                    journal(_jetzt(), "live", "verkauf", p["paar"],
                            "%.8g" % kurs, "%.2f" % erloes,
                            "%.8f" % p["menge"], "", "", grund)
                    z["letzte_stops"][p["paar"]] = _heute()
                    return True
                z.setdefault("offene_stops", []).append(
                    {"paar": p["paar"], "stop_txid": p["stop_txid"],
                     "seit": _heute()})
        try:
            kraken.markt_verkauf(p["paar"], p["menge"], echt=True)
        except Exception as e:  # noqa: BLE001
            print("  Verkauf %s fehlgeschlagen: %s" % (p["paar"], e),
                  file=sys.stderr)
            return False
    erloes = _erloes(p, kurs, w)
    print("  AUSSTIEG (%s): %s @ %-12.6g  G/V %+.2f EUR"
          % (grund, p["paar"], kurs, erloes - p["eur"]))
    journal(_jetzt(), "live" if live else "papier", "verkauf", p["paar"],
            "%.8g" % kurs, "%.2f" % erloes, "%.8f" % p["menge"], "", "", grund)
    if grund == "stop":
        z["letzte_stops"][p["paar"]] = _heute()
    return True


def ist_live_position(p):
    """Eine ECHTE Position bei Kraken - erkennbar an der Transaktionskennung.

    Das Buch ist EINES fuer Papier und Live. Ein Papierzyklus (Fenster zu,
    Guthaben zu) darf eine live gekaufte Position deshalb NICHT im Buch
    schliessen: bei Kraken bliebe sie offen, der Schutz-Stop wuerde spaeter
    ohne Buchzeile ausloesen, und die Spur belegt Kapital, ohne es zu wissen.
    Dasselbe Muster traf scanner und xperp (HBAR) am 21.09.2026.
    """
    return bool(p.get("kauf_txid") or p.get("beleg"))


def pruefe_ausstiege(z, w, live):
    if live:
        raeume_offene_stops(z)
    behalten = []
    for p in z["positionen"]:
        if not live and ist_live_position(p):
            print("  %s bleibt stehen: echte Position (kauf_txid), wird nur "
                  "vom Live-Lauf geschlossen" % p.get("inst", p.get("paar")))
            behalten.append(p)
            continue
        kurs = kraken.letzter_kurs(p["paar"])
        grund = None
        if kurs <= p["stop"]:
            grund = "stop"
        elif kurs >= p["ziel"]:
            grund = "ziel"
        if not grund or not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def flach_stellen(z, w, live, grund):
    """Alle offenen Positionen sofort schliessen - Notausstieg fuer Bedingung 2
    (Kill-Switch) und Bedingung 3 (Herzschlag alt)."""
    behalten = []
    for p in z["positionen"]:
        if not live and ist_live_position(p):
            print("  %s bleibt stehen: echte Position (kauf_txid) - ein "
                  "Papierlauf stellt sie nicht flach" % p.get("inst", p.get("paar")))
            behalten.append(p)
            continue
        kurs = kraken.letzter_kurs(p["paar"])
        if not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def bueche_papier_altlasten_aus(z):
    """Positionen OHNE echte Kraken-Order aus dem Live-Buch buchen.

    Anlass (21.09.2026, gemessen): kraken ist seit 08:43 live - das
    Freigabefenster der Auto-Freigabe war offen und das EUR-Guthaben reichte.
    Sein Buch trug aber die vier Positionen der Papierphase, alle ohne
    `kauf_txid`. Folgen, dieselbe Klasse wie bei scanner am selben Tag:
      1. alle vier Plaetze belegt -> live wird nichts Neues gekauft,
      2. im Live-Modus versucht der Ausstieg, Coins zu verkaufen, die am Konto
         gar nicht liegen (die Buchung kam nie von einer Order).
    Deshalb zu Beginn JEDES Live-Laufs ausbuchen - als PAPIER-Verkauf mit
    Grund "buchbereinigung"; Positionen MIT txid bleiben liegen. Idempotent.
    """
    altlasten = [p for p in z["positionen"] if not p.get("kauf_txid")]
    if not altlasten:
        return 0
    behalten = []
    for p in z["positionen"]:
        if p.get("kauf_txid"):
            behalten.append(p)
            continue
        try:
            kurs = kraken.letzter_kurs(p["paar"])
        except Exception as e:                                     # noqa: BLE001
            print("  Buchbereinigung %s: kein Kurs (%s) - bleibt liegen"
                  % (p["paar"], e), file=sys.stderr)
            behalten.append(p)
            continue
        if not kurs:
            print("  Buchbereinigung %s: kein Kurs - bleibt liegen" % p["paar"],
                  file=sys.stderr)
            behalten.append(p)
            continue
        erloes = p["eur"] * (kurs / p["einstieg"])
        gv = erloes - p["eur"]
        print("  Buchbereinigung: %s (ohne Order) @ %.6g  G/V %+.2f EUR"
              % (p["paar"], kurs, gv))
        journal(_jetzt(), "papier", "verkauf", p["paar"], "%.8g" % kurs,
                "%.2f" % erloes, "%.8f" % p.get("menge", 0.0), "", "",
                "buchbereinigung")
    z["positionen"] = behalten
    return len(altlasten)


def _beleg_zur_order(inst, menge, kurs, stop, ziel):
    """Freigabe-Beleg fuer einen Live-Kauf ausstellen. None = kein Kauf.

    Der Beleg entsteht nur, wenn das Freigabefenster offen ist UND
    `handel_erlaubt=true` - also unter genau den Bedingungen, unter denen
    diese Spur ohnehin kaufen darf. Er macht sie pruefbar und gibt der Hand
    (MCP-Werkzeug `kraken_order_mit_beleg`, Skript beleg_hand.py) dieselbe
    Erlaubnis, ohne die Entscheidung dorthin zu verlagern.
    """
    beleg = freigabebeleg.schreibe(SPUR, "buy", inst, menge,
                                   preis_max=float(kurs) * 1.05,
                                   grund="Einstieg %s" % inst,
                                   zusatz={"inst": inst, "stop": stop, "ziel": ziel})
    if not beleg.get("kennung"):
        print("  kein Beleg fuer %s: %s" % (inst, beleg.get("grund")),
              file=sys.stderr)
        return None
    return beleg


def pruefe_einstiege(z, vs, w, live, faktor=1.0, lage=None):
    # Das Guthaben wird NUR im Live-Zweig abgerufen: ein Papierlauf darf nicht
    # davon abhaengen, ob das Konto lesbar ist.
    if lage is None and live:
        try:
            lage = guthaben_lage(w)
        except Exception as e:                                # noqa: BLE001
            print("  Guthaben-Lage nicht abrufbar (%s) - kein Einstieg" % e)
            lage = {}
    if lage is None:
        lage = {}
    # Ein Buch, eine Waehrung (siehe ziel_waehrung).
    waehrung = ziel_waehrung(z, w, lage, live)
    basen = {_basis_oder_paar(p["paar"]) for p in z["positionen"]}
    gehalten = {p["paar"] for p in z["positionen"]}
    eingesetzt = sum(p["eur"] for p in z["positionen"])
    if faktor != 1.0:
        print("  (Drawdown-Ratsche aktiv: Positionsgroesse x %.2f)" % faktor)
    for v in vs:
        if len(z["positionen"]) >= w["max_offene_positionen"]:
            break
        v_waehrung = quote.lesbar(v.get("waehrung") or "")
        # Nur eine BEKANNTE Abweichung ist eine Abweichung: ein Vorschlag
        # ohne Waehrung (Altbestand, Handaufruf) wird nicht gefiltert.
        if v_waehrung and v_waehrung != waehrung:
            print("  -- %-10s uebersprungen: Buch wird in %s gefuehrt, Paar "
                  "notiert in %s" % (v["inst"], waehrung, v_waehrung))
            continue
        eur = round(v["eur"] * faktor, 2)
        # Das Guthaben bindet nur, wenn es wirklich gelesen werden konnte -
        # im Papierlauf ist lage leer, und dort ist Geld nicht die Grenze.
        if waehrung in lage and lage[waehrung][0] < eur:
            print("  -- %-10s uebersprungen: %.2f %s frei, %.2f noetig"
                  % (v["inst"], lage[waehrung][0], waehrung, eur))
            continue
        if eingesetzt + eur > w["max_gesamt_eur"]:
            continue
        if v["inst"] in gehalten or v.get("basis") in basen \
                or in_abklingzeit(v["inst"], z, w):
            continue

        menge, fehler = menge_fuer(v["inst"], eur, v["einstieg"])
        if fehler:
            print("  -- %-10s uebersprungen: %s" % (v["inst"], fehler))
            continue

        kauf_txid = stop_txid = None
        stop_fehlt = False
        if live:
            beleg = _beleg_zur_order(v["inst"], menge, v["einstieg"],
                                     v["stop"], v["ziel"])
            if beleg is None:
                continue
            if str(w.get("order_ueber", "spur")).lower() == "mcp":
                # Die Order fuehrt die HAND aus: das MCP-Werkzeug
                # `kraken_order_mit_beleg` oder Agenten/Handel/beleg_hand.py -
                # beide pruefen denselben Beleg. Er bleibt liegen (180 s);
                # laeuft er ab, ist der Einstieg verfallen, und der naechste
                # Zyklus entscheidet neu.
                print("  Beleg %s ausgestellt - Order geht an die Hand"
                      % beleg["kennung"])
                journal(_jetzt(), "live", "kauf_beleg", v["inst"],
                        "%.8g" % v["einstieg"], "%.2f" % eur, "%.8f" % menge,
                        "%.8g" % v["stop"], "%.8g" % v["ziel"],
                        "beleg %s | %s" % (beleg["kennung"], waehrung))
                continue
            # Eigener Weg: den Beleg SOFORT einloesen. Einmalig heisst einmalig
            # - bliebe er liegen, koennte die Hand dieselbe Order ein zweites
            # Mal ausfuehren, und das waere ein echter Doppelkauf.
            ok, warum = freigabebeleg.pruefe(beleg["kennung"], SPUR, "buy",
                                             v["inst"], menge, v["einstieg"])
            if not ok:
                print("  Beleg nicht einloesbar: %s" % warum, file=sys.stderr)
                continue
            freigabebeleg.verbrauche(SPUR, beleg["kennung"], ergebnis="spur")
            try:
                kauf_txid = kraken.markt_kauf(v["inst"], menge, echt=True)
                gefuellt = kraken.gefuellte_menge(kauf_txid) if kauf_txid else 0.0
            except Exception as e:  # noqa: BLE001
                print("  Kauf %s fehlgeschlagen: %s" % (v["inst"], e),
                      file=sys.stderr)
                continue
            if gefuellt <= 0:
                print("  Kauf %s ohne Fuellung - kein Eintrag" % v["inst"],
                      file=sys.stderr)
                continue
            menge = gefuellt
            try:
                stop_txid = kraken.stop_setzen(v["inst"], menge, v["stop"],
                                               echt=True)
            except Exception as e:  # noqa: BLE001
                # Der Kauf steht, der Notausstieg nicht: zurueckverkaufen.
                # Klappt auch das nicht, wird die Position gebucht und als
                # unbewacht gekennzeichnet - besser als eine Position, die am
                # Markt liegt und im Buch fehlt.
                print("  Stop fuer %s fehlgeschlagen: %s" % (v["inst"], e),
                      file=sys.stderr)
                try:
                    kraken.markt_verkauf(v["inst"], menge, echt=True)
                    print("  zurueckverkauft - kein Eintrag")
                    continue
                except Exception as e2:  # noqa: BLE001
                    print("  Rueckverkauf ebenfalls fehlgeschlagen: %s" % e2,
                          file=sys.stderr)
                    stop_fehlt = True

        kosten = eur * w["gebuehr_taker"]
        z["positionen"].append({
            "paar": v["inst"], "einstieg": v["einstieg"], "eur": eur,
            "waehrung": waehrung, "basis": v.get("basis"),
            "menge": menge, "stop": v["stop"], "ziel": v["ziel"],
            "eroeffnet": _heute(), "kauf_txid": kauf_txid,
            "stop_txid": stop_txid, "boersen_stop_fehlt": stop_fehlt,
        })
        eingesetzt += eur
        gehalten.add(v["inst"])
        basen.add(v.get("basis") or _basis_oder_paar(v["inst"]))
        print("  AUF %-10s @ %-12.6g Stop %-12.6g (-%.1f%%) Ziel %-12.6g "
              "%.2f %s"
              % (v["inst"], v["einstieg"], v["stop"], v["stop_pct"],
                 v["ziel"], eur, waehrung))
        journal(_jetzt(), "live" if live else "papier", "kauf", v["inst"],
                "%.8g" % v["einstieg"], "%.2f" % (eur + kosten), "%.8f" % menge,
                "%.8g" % v["stop"], "%.8g" % v["ziel"],
                "score %.1f | %s" % (v["score"], waehrung))


# --- Freigabe von Hand (Handelsregeln Punkt 3) -------------------------------

SPUR = "kraken"


def zeitfenster_offen():
    """Hat Max am Handy freigegeben (freigabefenster.py)?

    Gelesen wird das Modul aus dem Handel-Ordner (oben ueber den PFAD geladen).
    Ein Lesefehler gilt als *nicht* freigegeben - im Zweifel keine Order. Er
    wird aber GEMELDET statt still verschluckt zu werden (Befund 22.09.2026)."""
    try:
        return bool(freigabefenster.lade(SPUR).offen())
    except Exception as e:                                   # noqa: BLE001
        print("  Zeitfenster nicht lesbar (%s: %s) - gilt als zu."
              % (type(e).__name__, e), file=sys.stderr)
        return False


def sitzung_da():
    """Sitzt jemand davor, der das Freigabefenster bedienen kann?

    Nur eine erste Huerde: isatty() meldet in der Git-Bash unter Windows auch
    bei umgeleitetem stdin ein Terminal (gemessen 02.09.2026). Der tragende
    Schutz ist FREIGABE_ZEITLIMIT_S. MAXHIRN_ROUTINE=1 setzt der Wrapper einer
    geplanten Aufgabe - die ausdrueckliche Ansage "hier sitzt niemand"."""
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


def hole_freigabe(vs, z, s):
    """Jeden Vorschlag im Fenster bestaetigen lassen. Leere Liste heisst
    abgelehnt - und abgelehnt heisst kein Einstieg. Faellt das Fenster aus,
    wird nicht gehandelt: ein Fehler darf nie zu einem ungefragten Kauf werden."""
    sys.path.insert(0, str(HIER.parent))
    try:
        import freigabe
    except Exception as e:  # noqa: BLE001
        print("  Freigabefenster nicht verfuegbar (%s) - kein Einstieg." % e,
              file=sys.stderr)
        return []
    bestand = {
        "gebunden": sum(p["eur"] for p in z["positionen"]),
        "offene_positionen": len(z["positionen"]),
        "verlust_gesamt": s["ruecklauf_eur"],
    }
    try:
        return freigabe.bestaetige(vs, "kraken", bestand,
                                   zeitlimit=FREIGABE_ZEITLIMIT_S)
    except Exception as e:  # noqa: BLE001
        print("  Freigabe abgebrochen (%s) - kein Einstieg." % e,
              file=sys.stderr)
        return []


# --- Wachen-Status (Bedingungen 2-5) ----------------------------------------

def _spiegeln(w, z=None):
    """Bedingung 4: Journal und Zustand ausser Haus - nach dem Herzschlag.

    Mit uebergebenem Zustand wird das Ergebnis dort vermerkt
    (journal_zweitziel_ok/_info) - nur beim Wechsel, und die Kopie wird danach
    einmal nachgezogen. Ohne den Vermerk ist eine ausgefallene Kopie
    unsichtbar: der Dauerlauf protokolliert bei Rueckgabe 0 nur "ok", und die
    Spurausgabe zeigt er nicht. Dieselbe Rechnung wie in swap/handeln.py.
    """
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if z is not None and wp.vermerke_spiegelung(z, ziel, ok, info,
                                                schreibe_zustand) and ok:
        # Der Vermerk ist juenger als die Kopie: einmal nachziehen, damit auf
        # Q: derselbe Stand liegt.
        wp.spiegele_journal([ZUSTAND], ziel)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))
    return ok


def zeige_wachen(w):
    """handeln.py --wachen: alle fuenf Bedingungen als Momentaufnahme, dazu die
    beiden Automatik-Reaktionen des Wochenlaufs - Bedingung 4 (spiegeln) und
    Bedingung 5 (bei negativem Erwartungswert die Sperre schliessen)."""
    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)
    print("=== Wachen-Status Kraken  %s ===" % _jetzt())
    # Die Rundenzahl fuer Bedingung 1 zaehlt Handelsrunden, nicht Buchungen:
    # ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung. Die Kurve
    # (Ruecklauf unten) bleibt ungefiltert - sie ist gebucht.
    print("  1 Freigabe erfuellt      %s   (Handelsrunden %d, davon Papier %d, "
          "dazu %d Betriebsstoerung(en), seit %s)"
          % (s["freigabe_erfuellt"], s["runden_echt"], s["runden_papier_echt"],
             s["runden_stoerung"], s["erste_runde"] or "-"))
    print("  2 Ruecklauf              %.2f EUR von Hoechststand %.2f  -> Faktor %.2f%s"
          % (s["ruecklauf_eur"], s["hoechststand_eur"], s["groessenfaktor"],
             "   >>> KILL-SWITCH" if s["kill"] else ""))
    print("  3 Herzschlag frisch      %s   (%s min alt, Grenze %d)"
          % (s["herzschlag_frisch"],
             "?" if s["herzschlag_alter_min"] is None
             else "%.0f" % s["herzschlag_alter_min"],
             w.get("herzschlag_max_minuten", 2880)))
    print("  4 Journal-Zweitziel      %s"
          % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  5 Rollierender EV        %s%s"
          % ("n/a (zu wenig Runden)" if s["rollierender_ev"] is None
             else "%+.3f EUR/Runde" % s["rollierender_ev"],
             "   >>> NEGATIV" if s["ev_negativ"] else ""))
    print("  + Guthaben               %s"
          % _guthaben_text(w))
    print()
    _spiegeln(w, z)
    if s["kill"] and wp.sperre_zu("Bedingung 2 (Wochenlauf): Ruecklauf %.2f EUR >= Kill-Switch"
                                  % s["ruecklauf_eur"]):
        print("  -> Bedingung 2: handel_erlaubt auf false gesetzt.")
    if s["ev_negativ"] and wp.sperre_zu("Bedingung 5 (Wochenlauf): rollierender EV %.3f EUR < 0"
                                        % s["rollierender_ev"]):
        print("  -> Bedingung 5: handel_erlaubt auf false gesetzt.")


def _guthaben_text(w):
    """Jede Quotewaehrung der Watchlist mit freiem Stand und Tor - EIN Abruf."""
    if not kraken.schluessel_vorhanden():
        return "unbekannt (kein Schluessel)"
    try:
        lage = guthaben_lage(w)
    except Exception as e:  # noqa: BLE001
        return "nicht abrufbar (%s)" % e
    return lage_text(lage)


# --- Hauptlauf ---------------------------------------------------------------

def live_sperren(w, s):
    """Alle Gruende, die diesen Lauf auf Papier zurueckwerfen. Leere Liste
    heisst: scharf, aber weiterhin nur mit Freigabefenster je Einstieg."""
    gruende = []
    if not risikostufe.live_erlaubt():
        # Eine Risikostufe geht NIE live (siehe risikostufe.live_erlaubt): ihre
        # groesseren Betraege sind zum Messen da, und ihr Buch ist getrennt -
        # live gehandeltes Geld stuende in keiner Auswertung. Der Grund traegt
        # bewusst NICHT das Wort Freigabefenster: sonst haelt der Dauerlauf ihn
        # fuer eine Fenster-Bitte und fragt nach einer Freigabe, die es in
        # einer Stufe gar nicht geben darf.
        gruende.append("Risikostufe %s: kein Live-Pfad in einer Stufe"
                   % risikostufe.stufe())
    if not w.get("handel_erlaubt"):
        gruende.append("wachen.json handel_erlaubt=false")
    if not kraken.schluessel_vorhanden():
        gruende.append("KRAKEN_API_KEY/SECRET nicht gesetzt")
    if not s["freigabe_erfuellt"]:
        gruende.append("freigabe.erfuellt=false (Bedingung 1)")
    if not s["herzschlag_frisch"]:
        gruende.append("Herzschlag alt (Bedingung 3)")
    if s["ev_negativ"]:
        gruende.append("rollierender EV %.3f EUR < 0 (Bedingung 5)"
                       % s["rollierender_ev"])
    if not w.get("journal_zweitziel"):
        gruende.append("journal_zweitziel nicht gesetzt (Bedingung 4)")
    if not sitzung_da() and not zeitfenster_offen():
        gruende.append("Freigabefenster nicht offen - keine Sitzung am "
                       "Bildschirm und kein Zeitfenster (Handelsregeln Punkt 3)")
    if kraken.schluessel_vorhanden():
        try:
            lage = guthaben_lage(w)
        except Exception as e:  # noqa: BLE001
            gruende.append("Guthaben nicht abrufbar (%s)" % e)
        else:
            if not bevorzugte_waehrung(w, lage):
                # EIN Grund, auch wenn mehrere Waehrungen zu duenn sind: der
                # Dauerlauf oeffnet sein Auto-Freigabefenster nur, wenn GENAU
                # EIN Grund fehlt (dauerlauf.nur_fenster_fehlt).
                gruende.append("Guthaben-Tor zu in jeder Quotewaehrung (%s)"
                               % lage_text(lage))
    return gruende


def _bericht_alter(bericht):
    """Alter der Rangliste in Tagen. 999 = Datum fehlt oder unlesbar.

    Ein unlesbares Datum gilt als zu alt: dann wird nicht eingestiegen. Die
    Alternative - weiter einsteigen, weil man das Alter nicht kennt - hiesse,
    auf eine Rangliste zu bauen, deren Alter niemand kennt. Stop und Ziel
    werden von dieser Sperre nicht beruehrt, sie laufen immer.
    """
    try:
        return (date.fromisoformat(_heute())
                - date.fromisoformat(bericht["datum"])).days
    except (KeyError, TypeError, ValueError):
        return 999


def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = scan.wachen()

    # Der Schalter kommt aus wachen.json (stillgelegt, seit 14.09.2026
    # false). Er steht hier, vor allem anderen: ein Vermerk in der Datei haelt
    # nichts auf, solange das Skript ihn nicht liest. --wachen und --vorschau
    # bleiben auch bei true erlaubt - nachsehen duerfen ist der Sinn einer
    # aufbewahrten Spur; gehandelt wird dann nicht, auch nicht auf Papier.
    if w.get("stillgelegt") and modus in ("papier", "live"):
        print("Spur 3 (Kraken) ist stillgelegt - kein %s-Lauf." % modus)
        print()
        print(w.get("_stillgelegt", "").split(" Zum Wiederanschalten")[0].strip())
        print()
        print("Grund und Zahlen: Feld _stillgelegt_grund in wachen.json.")
        print("Nachsehen geht weiter: --wachen und --vorschau.")
        return

    if modus == "wachen":
        zeige_wachen(w)
        return

    bpfad = scan.BERICHTE / "neuester.json"
    if not bpfad.exists():
        print("Kein Bericht. Erst scan.py laufen lassen.")
        return
    bericht = json.loads(bpfad.read_text("utf-8"))

    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)

    live = False
    if modus == "live":
        gruende = live_sperren(w, s)
        if gruende:
            print("--live angefordert, aber gesperrt: " + "; ".join(gruende))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    tage = _bericht_alter(bericht)
    grenze = w.get("bericht_max_alter_tage", 3)
    if tage > grenze:
        print("- Bericht vom %s ist %s Tage alt (Grenze %d) -> keine Einstiege, "
              "Ausstiege laufen weiter -"
              % (bericht.get("datum"), tage if tage < 999 else "?", grenze))
        vs = []
    else:
        vs = vorschlaege(bericht, w)
    print("=== Kraken handeln (%s) | Bericht %s | %d Vorschlaege ==="
          % ("LIVE" if live else "Papier", bericht.get("datum"), len(vs)))

    z["modus"] = "live" if live else "papier"

    # Erst aufraeumen, dann handeln: ein Live-Lauf uebernimmt kein Papierbuch.
    if live:
        n_alt = bueche_papier_altlasten_aus(z)
        if n_alt:
            print("  %d Papier-Altlast(en) aus dem Live-Buch gebucht" % n_alt)

    if modus == "vorschau":
        for v in vs:
            print("  %-10s Score %.1f  %-4s  Einstieg %-12.6g Stop %-12.6g "
                  "(-%.1f%%)  Ziel %.6g"
                  % (v["inst"], v["score"], quote.lesbar(v.get("waehrung") or "?"),
                     v["einstieg"], v["stop"], v["stop_pct"], v["ziel"]))
        eing = sum(p["eur"] for p in z["positionen"])
        print("\nOffener Bestand: %d Positionen, %.2f %s gebunden"
              % (len(z["positionen"]), eing,
                 buch_waehrung(z) or ziel_waehrung(z, w, {}, False)))
        print("Guthaben: %s" % _guthaben_text(w))
        print("Live waere gesperrt durch: %s"
              % ("; ".join(live_sperren(w, s)) or "nichts"))
        return

    # Bedingung 2 - Kill-Switch: alles zu, Sperre zu, Schluss.
    if s["kill"]:
        print("- KILL-SWITCH: Ruecklauf %.2f EUR >= %g -> Notausstieg + Sperre -"
              % (s["ruecklauf_eur"], w["kill_switch_gesamt_eur"]))
        flach_stellen(z, w, live, "kill_switch")
        if wp.sperre_zu("kill_switch: Ruecklauf %.2f EUR" % s["ruecklauf_eur"]):
            print("  wachen.json handel_erlaubt -> false")
        schreibe_zustand(z)
        return

    # Bedingung 3 - Herzschlag alt: alles zu, dieser Lauf handelt nicht mehr.
    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel dieser Lauf -"
              % ("?" if s["herzschlag_alter_min"] is None
                 else "%.0f" % s["herzschlag_alter_min"],
                 w.get("herzschlag_max_minuten", 2880)))
        flach_stellen(z, w, live, "herzschlag_alt")
        z["modus"] = "papier"
        schreibe_zustand(z)
        if w.get("journal_zweitziel"):
            _spiegeln(w, z)
        return

    # Ausstiege laufen nie durch das Fenster: ein Stop muss greifen, auch
    # wenn niemand davorsitzt.
    print("- Ausstiege -")
    pruefe_ausstiege(z, w, live)

    print("- Einstiege -")
    faktor = s["groessenfaktor"]
    if live and vs:
        vs = [dict(v, eur=round(v["eur"] * faktor, 2), cr=2.0) for v in vs]
        faktor = 1.0
        # order_ueber=mcp: der Beleg-Weg prueft das Freigabefenster selbst
        # (freigabebeleg.schreibe verweigert ohne offenes Fenster). Die
        # Bildschirm-Freigabe hier wuerde die Kandidatenliste leeren, weil im
        # Dauerlauf niemand am Bildschirm sitzt (MAXHIRN_ROUTINE=1) - damit
        # waere der Beleg-Weg unerreichbar (Befund 27.09.2026).
        if str(w.get("order_ueber", "spur")).lower() != "mcp":
            vs = hole_freigabe(vs, z, s)
            if not vs:
                print("  Freigabe abgelehnt - kein Einstieg in diesem Lauf.")
    pruefe_einstiege(z, vs, w, live, faktor)

    eing = sum(p["eur"] for p in z["positionen"])
    print("\nStand: %d/%d Positionen, %.2f/%d %s gebunden"
          % (len(z["positionen"]), w["max_offene_positionen"],
             eing, w["max_gesamt_eur"],
             buch_waehrung(z) or ziel_waehrung(z, w, {}, False)))
    schreibe_zustand(z)

    # Bedingung 4 - Journal nach jedem Zyklus ausser Haus.
    if w.get("journal_zweitziel"):
        _spiegeln(w, z)


def main():
    # Meldet den Zyklus am Bus - wie xperp/orbk/gitter/spiegel. Ohne diese
    # Zeile ist ein Dauerlauf-Zyklus dieser Spur im Journal nicht zu sehen;
    # der Wrapper der Tagesroutine meldet nur routine/kraken-scanner (den
    # Scan). Ein bot.py wie in xperp gibt es hier nicht, eine Doppelmeldung
    # aus demselben Prozess ist also nicht moeglich.
    with ereignis.lauf("handel/kraken"):
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
                   const="wachen", help="Bedingungen 2-5 zeigen und durchsetzen "
                                        "(Wochenlauf)")
    a = p.parse_args()
    lauf(a.modus or "papier")


if __name__ == "__main__":
    main()
