"""Handelszentrale - eine Ansicht ueber alle Spuren in Handel/.

Das Gegenstueck zur omnitrade-Oberflaeche (omnitrade-ui): dort Chart,
Orderbuch, Positionen und Konsole in einem Fenster - hier dieselben vier
Dinge, aber ueber ALLE Spuren des Dauerlaufs (42 am 01.10.2026) statt ueber
eine Engine. Dazu zwei Reiter fuer die Systeme ausserhalb der Spuren:
FreqTrade (die Bot-Container) und omnitrade (die Rust-Laeufe samt Haus-Spur).

Rein lesend
-----------
Gelesen werden je Spur `zustand.json`, `wachen.json` und
`handelsjournal.csv`, dazu `dauerlauf.log`, `dauerlauf.pid` und
`freigabe_fenster.json`. Kurse und Kerzen kommen aus `scanner/okx` (OKX),
`kraken/kraken.py` (Kraken) bzw. `spiegel/lesen.py` (Onchain-Feed) - alles in
Hintergrund-Threads, damit das Netz die Oberflaeche nie blockiert. Dazu liest
die Kopfzeile den echten Kraken-Kontostand (alle Waehrungen des Buchs,
60-s-Cache, rein lesend) und warnt rot, sobald keine Waehrung ueber das
Mindestguthaben der Spur kommt.
Der FreqTrade-Reiter fragt die Bot-APIs ab (Liste aus
`freqtrade/bots.json`, Adressen und Grenzen in `freqtrade_bridge.py`), der
omnitrade-Reiter liest die Statusdateien der Rust-Laeufe.
Geschrieben wird NICHTS: der Dauerlauf bleibt der einzige Schreiber.
`tests/test_handelszentrale_rein_lesend.py` verbietet Schreibzugriffe per
AST-Pruefung.

Scrollen
--------
Die Spuren-Seite ist eine Scrollflaeche und jede Tabelle hat eine Leiste
(`tabelle_mit_leiste`, `scrollbare_seite`): die Spurtabelle forderte bis
30.09.2026 so viele Zeilen an, wie es Spuren hat, und war damit hoeher als
jedes Fenster - der untere Teil der Seite war nicht zu erreichen.

Warum nicht `gui.py`
--------------------
`omniquant/gui.py` heisst schon so. Ein zweites `gui.py` in Handel/ faengt
dessen `import gui` ab, sobald Handel/ auf `sys.path` steht - die
Omniquant-Tests liefen danach gegen dieses Fenster und brachen mit
`module 'gui' has no attribute 'fuss_texte'` (Befund 13.09.2026). Gleiche
Module in zwei Spuren sind eine Falle; der eigene Name ist der Fix.

Welche Spuren gezeigt werden, steht NICHT in dieser Datei: die Liste kommt aus
`dauerlauf.SPUREN`. Eine zweite Liste waere eine zweite Wahrheit, die beim
naechsten neuen Spurordner still auseinanderlaeuft.

Start (Vorgabe-Interpreter der Spuren, aus dem Handel-Ordner):
    scanner/.venv/Scripts/python.exe handelszentrale.py
Ohne Fenster, als Nachweis der Bindungen:
    scanner/.venv/Scripts/python.exe handelszentrale.py --pruefen
"""

import argparse
import csv
import ctypes
import importlib.util
import json
import os
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime, timedelta, timezone
from tkinter import ttk

# Der Importpfad der Spuren, nicht ein eigener: okx liegt im scanner-venv-
# Ordner, kraken daneben, der Feed-Leser in spiegel.
HIER = os.path.dirname(os.path.abspath(__file__))
for _p in (HIER, os.path.join(HIER, "scanner"), os.path.join(HIER, "kraken"),
           os.path.join(HIER, "spiegel")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dauerlauf                                            # noqa: E402
import freigabefenster                                      # noqa: E402
import risikostufe                                          # noqa: E402
import auswertung_alle                                      # noqa: E402
import freqtrade_bridge                                     # noqa: E402
import omnitrade_bridge                                     # noqa: E402
import omnitrade_auswertung                                 # noqa: E402

# Die Spurliste - eine Wahrheit, aus dem laufenden Code gelesen.
SPUREN = list(dauerlauf.SPUREN)

# Risikostufe dieser Ansicht: None = Basis (Vorgabe). Ein zweiter Dauerlauf
# fuehrt dieselben Spuren mit groesseren Betraegen in EIGENEN Dateien
# (zustand.mittel.json, handelsjournal.mittel.csv, dauerlauf.mittel.log) - siehe
# Handel/risikostufe.py. Die Zentrale zeigt beide Buecher, umschaltbar in der
# Kopfzeile; sie schreibt in keiner Stufe etwas.
RISIKO = None
BASIS_NAME = "Basis"
STUFEN_AUSWAHL = (BASIS_NAME, "mittel", "hoch")


def stufenname(name):
    """Dateiname in der Stufe dieser Ansicht (Basis: unveraendert).

    NUR fuer Zustand und Journal. Die Wachen werden beim Laden skaliert, nicht
    umbenannt (`risikostufe.py`) - `wachen.mittel.json` gibt es nicht, und eine
    so gelesene Wache waere leer: jede Sperre der Spur_fiele weg, still. Die
    Zentrale hat diesen Fall schon einmal falsch gemacht (25.09.2026 im
    Tagesbericht), also sitzt die Regel hier und nicht nur bei den Aufrufern.
    """
    if not RISIKO or name.startswith("wachen"):
        return name
    return risikostufe.datei_fuer(name, RISIKO)


def dauerlauf_dateien():
    """(PID-Datei, Logdatei) der Ansicht - je Stufe eigene Namen."""
    return (os.path.join(HIER, stufenname("dauerlauf.pid")),
            os.path.join(HIER, stufenname("dauerlauf.log")))

UTC = timezone.utc
REFRESH_MS = 15_000
KERZEN_OKX = 90
KERZEN_KRAKEN = 200

# Woher eine Spur ihre Kurse holt. Die Zuordnung haengt an der SPUR, nicht am
# Instrument: derselbe Basiswert notiert an zwei Boersen verschieden.
QUELLE = {"kraken": "kraken", "orbk": "kraken", "spiegel": "feed",
          # Die beiden Kopier-Spuren lesen denselben Onchain-Feed wie
          # spiegel: ihr Instrument ist ein Token (kette+token), kein
          # OKX-Paar. Ohne den Eintrag stand dort "Quelle okx" mit der
          # Token-Adresse als Instrument - der Chart lief ins Leere.
          "kopier": "feed",
          # moondev_sniper fuehrt seine Solana-Mints als `inst` (ohne
          # kette/token-Feld) - dieselbe Klasse: "Quelle okx" mit einer
          # Contract-Adresse, kein Kurs, seit dem 19.09. Gemessen am 01.10.2026
          # preisert der Feed den Token ueber die Kette solana (3,104e-06).
          "moondev_sniper": "feed",
          # robinhood_radar notiert auf der Robinhood-Kette (4663). Die ist im
          # Feed-Leser nicht gefuehrt (KETTEN: base, bnb, ethereum, solana,
          # xlayer) und hat auf OKX natuerlich kein Paar. "keine" sagt das,
          # statt weiter "okx" zu behaupten und ins Leere zu laufen.
          "robinhood_radar": "keine"}
QUELLE_VORGABE = "okx"

# Kette, die eine Feed-Spur in ihren Dateien NICHT mitschreibt. Nur ein
# Nachschlagen fur den Fall, dass die Spur selbst sie nicht fuehrt - Positionen
# mit eigenem `kette`-Feld brauchen das nicht.
FEED_KETTE = {"moondev_sniper": "solana"}

# Farben, Schrift, ttk-Stile: EINE Quelle fuer alle Fenster,
# Werkzeuge/fenster_design.py (Beschreibung: Werkstatt/design-system-fenster-*).
# Per Dateipfad geladen, nicht ueber sys.path: Werkzeuge/ enthaelt Module
# (z. B. marktdaten), die sonst Handel/ verdecken koennten.
_spec = importlib.util.spec_from_file_location(
    "fenster_design", os.path.join(HIER, "..", "Werkzeuge", "fenster_design.py"))
design = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(design)

FARBEN = design.FARBEN

# Schrift: EIN Basiswert, alles andere relativ dazu - so skalieren Titel,
# Tabellen, Chart und Konsole gemeinsam, wenn der Nutzer die Groesse wechselt.
# Wird nur im Speicher gehalten (die Zentrale schreibt nichts).
SCHRIFT_ART = design.SCHRIFT_ART
SCHRIFT_GROESSE = design.SCHRIFT_GROESSE
SCHRIFT_AUSWAHL = design.SCHRIFT_AUSWAHL
KLEIN = design.KLEIN            # Konsole, Fusszeile
TINY = design.TINY              # Chart-Beschriftung
TITEL = design.TITEL            # Fensterkopf


def schrift(rel=0, fett=False):
    """Schriftart dieser Ansicht: (veraenderliche) Basis + relative Groesse."""
    return design.schrift(SCHRIFT_GROESSE, rel, fett)


# --------------------------------------------------------------------------
# Reine Funktionen: hier steht die ganze Deutung, damit sie ohne Fenster
# pruefbar ist. Alles, was eine Zeile behauptet, wird hier gerechnet.
# --------------------------------------------------------------------------

def quelle_fuer(spur):
    return QUELLE.get(spur, QUELLE_VORGABE)


def _zahl(wert):
    try:
        if wert is None or wert == "":
            return None
        return float(wert)
    except (TypeError, ValueError):
        return None


def lade_json(pfad):
    """Lesen, nie anlegen. Eine fehlende Datei ist ein leerer Zustand."""
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:                                        # noqa: BLE001
        return {}


def instrument_name(p):
    """Der Anzeigename einer Position.

    Die Spuren benennen ihre Positionen verschieden: die Kontraktspuren
    `inst`, die Kraken-Spur `paar`, die Spiegel-Spur ein Token je Kette.
    Ohne diesen Griff stuende dort nur ein Fragezeichen.
    """
    name = p.get("inst") or p.get("paar")
    if name:
        return str(name)
    symbol = p.get("symbol") or p.get("token") or "?"
    kette = p.get("kette")
    return "%s (%s)" % (symbol, kette) if kette else str(symbol)


def positionen_aus(zustand):
    """Alle offenen Positionen einer Spur in EINER Form.

    Die Feldnamen sind nicht erfunden, sondern die Schnittstelle der
    Schreiberseiten: `positionen` (Liste) ODER `position` (Einzelwert, ORB),
    `seite` ODER `richtung`, `einstieg` ODER `preis_einstieg`,
    `stop`/`ziel` ODER `stop_preis`/`ziel_preis`,
    Einsatz als `nominal`, `usd`, `einsatz_usd` oder `eur`. Genau so liest
    auch `Bus/handel_befehle.status()`.
    """
    roh = zustand.get("positionen")
    if roh is None:
        einzel = zustand.get("position")
        roh = [einzel] if einzel else []
    if not isinstance(roh, list):
        return []
    aus = []
    for p in roh:
        if not isinstance(p, dict):
            continue
        seite = str(p.get("seite") or p.get("richtung") or "long").lower()
        einstieg = _zahl(p.get("einstieg", p.get("preis_einstieg")))
        stop = _zahl(p.get("stop", p.get("stop_preis")))
        ziel = _zahl(p.get("ziel", p.get("ziel_preis")))
        wert = None
        for name in ("nominal", "usd", "einsatz_usd", "eur"):
            wert = _zahl(p.get(name))
            if wert is not None:
                break
        if wert is None:
            menge = _zahl(p.get("menge"))
            if einstieg and menge:
                wert = einstieg * menge
        aus.append({
            "spur": None,            # fuellt der Aufrufer
            "schluessel": str(p.get("inst") or p.get("paar")
                              or p.get("token") or ""),
            "token": p.get("token"),
            "kette": p.get("kette"),
            "instrument": instrument_name(p),
            "seite": seite,
            "einstieg": einstieg,
            "stop": stop,
            "ziel": ziel,
            "wert_usd": wert,
            "hebel": _zahl(p.get("hebel")),
            "liq": _zahl(p.get("liq")),
            "eroeffnet": str(p.get("eroeffnet") or p.get("eroeffnet_zeit") or ""),
            "frist": str(p.get("frist") or ""),
            "roh": p,
        })
    return aus


def positionen_der_spur(spur, zustand, wachen):
    """Positionen einer Spur samt Kursweg.

    `kurs_schluessel` ist das, was die Kursquelle versteht: bei OKX der
    instId, bei Kraken der Kraken-Paarname aus dem Instrumentenblock (die
    ORB-Spur fuehrt als `inst` nur den Schluessel ETH_USD), bei der
    Spiegel-Spur das Token.
    """
    aus = positionen_aus(zustand)
    q = quelle_fuer(spur)
    for p in aus:
        p["spur"] = spur
        p["quelle"] = q
        if q == "kraken":
            block = (wachen.get("instrumente") or {}).get(p["roh"].get("inst"))
            p["kurs_schluessel"] = (block or {}).get("kraken") or p["schluessel"]
        elif q == "feed":
            # Token aus dem eigenen Feld, sonst aus dem generischen Schluessel
            # (moondev_sniper fuehrt die Contract-Adresse als `inst`). Kette:
            # was die Spur schreibt, sonst die nachgeschlagene Feed-Kette.
            p["kurs_schluessel"] = p.get("token") or p["schluessel"] or None
            p["kette"] = p.get("kette") or FEED_KETTE.get(spur)
        elif q == "keine":
            # Kein Kursweg, und das ist die Aussage - nicht ein leerer okx-Weg.
            p["kurs_schluessel"] = None
        else:
            # `schluessel` ist die generische Lesart aus positionen_aus()
            # (inst ODER paar ODER token). Vorher stand hier roh["inst"] - die
            # Kraken-Spur fuehrt ihr Instrument als `paar`, der Kursweg blieb
            # deshalb None und ihr Chart lief ins Leere.
            p["kurs_schluessel"] = p["schluessel"]
    return aus


def kurs_fmt(wert):
    """Genauigkeit passend zur Preisgroesse: 0.05697 -> 5, 2471 -> 1.

    Unter 0,0001 reicht keine Nachkommastell-Zahl mehr: die Memecoin- und
    Token-Kurse der Spuren liegen bei 1e-6 bis 1e-8. Bis 30.09.2026 endete die
    Skala bei "%.5f" - ein Einstieg von 3,14e-06 stand als "0.00000" in der
    Tabelle, Einstieg/Stop/Ziel einer Position also als drei Nullen. Unterhalb
    der Schwelle gilt die exponentielle Form mit drei gueltigen Ziffern.
    """
    w = _zahl(wert)
    if w is None:
        return "-"
    if w >= 1000:
        return "%.1f" % w
    if w >= 10:
        return "%.2f" % w
    if w >= 1:
        return "%.3f" % w
    if w >= 0.0001:
        return "%.5f" % w
    return "%.3g" % w


def vorzeichen(seite):
    """Die Richtung als Faktor - die Rechnung braucht sie, nicht die Anzeige."""
    return -1.0 if str(seite).lower() in ("short", "verkauf", "sell") else 1.0


def gv_prozent(seite, kurs, einstieg):
    """Gewinn/Verlust in Prozent, richtungsbewusst."""
    k, e = _zahl(kurs), _zahl(einstieg)
    if not k or not e:
        return None
    return vorzeichen(seite) * (k / e - 1.0) * 100.0


def abstand_prozent(seite, kurs, stop):
    """Abstand zum Stop IN Positionsrichtung.

    Bei short liegt der Stop ueber dem Kurs: ohne Richtungsfaktor waere das
    Produkt immer negativ und jede gesunde short-Position saehe aus wie ein
    gerissener Stop. Negativ heisst: der Kurs hat den Stop durchlaufen.
    """
    k, s = _zahl(kurs), _zahl(stop)
    if not k or not s:
        return None
    return vorzeichen(seite) * (k / s - 1.0) * 100.0


def waehrung_fuer(spur, zustand):
    """Die Waehrung, in der die Betraege DIESER Spur stehen.

    Die Regel liegt in `auswertung_alle.einheit_fuer()` und damit schon im
    Tagesbericht - die Zentrale fuehrt sie nicht ein zweites Mal. Der
    interne Schluessel einer Position heisst aus Altgruenden `wert_usd` und
    sagt nichts ueber die Waehrung: das Kraken-Buch steht in EUR (seit
    30.09.2026 moeglich auch USDC/EURC), die Kontraktspuren in USD. Eine
    EUR-Zahl in einer Spalte "Wert USD" ist dieselbe Klasse Anzeigefehler wie
    der Kraken-BTC-Kurs aus der OKX-Tabelle am 23.09.2026.
    """
    try:
        return auswertung_alle.einheit_fuer(spur, zustand)
    except Exception:                                        # noqa: BLE001
        return "USD"          # Berichtsweg nicht lesbar: Zahlen zeigen, nicht scheitern


def nominal_gruppen(positionen, zustaende):
    """[(Waehrung, Summe, Anzahl)] der offenen Positionen, groesster Betrag zuerst.

    Nach Waehrung GRUPPIERT, weil eine Summe ueber EUR und USD kein Betrag ist,
    den jemand ausgeben koennte.
    """
    gruppen = {}
    for p in positionen:
        w = waehrung_fuer(p.get("spur"), (zustaende or {}).get(p.get("spur")))
        summe, anzahl = gruppen.get(w, (0.0, 0))
        gruppen[w] = (summe + (p.get("wert_usd") or 0.0), anzahl + 1)
    return [(w, summe, anzahl) for w, (summe, anzahl) in
            sorted(gruppen.items(), key=lambda kv: (-kv[1][0], kv[0]))]


def wert_anzeige(wert, waehrung):
    """Der Einsatz mit seiner Waehrung: '150 EUR', nicht '150' in einer USD-Spalte."""
    if not wert:
        return "-"
    return "%.0f %s" % (wert, waehrung)


def alter_minuten(wert, jetzt):
    """Minuten seit einem ISO-Zeitstempel; None, wenn unlesbar."""
    if not wert:
        return None
    try:
        t = datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return (jetzt - t).total_seconds() / 60.0


def mit_live_herzschlag(zustand, ordner):
    """Herzschlag aus dem Live-Buch, wenn es juenger ist als das Papierbuch.

    Scharfe Spuren mit eigenem Live-Stamm (moondev_marktlage/live_kraken.py,
    moondev_signalwelle) schreiben im Live-Zyklus nur `zustand.live.json`;
    `zustand.json` bleibt stehen. Gelesen wurde nur das Papierbuch - die Spur
    stand im Leitstand auf "ueberfaellig", obwohl sie alle 15 min lief
    (gefunden 11.10.2026). Nur `letzter_lauf` wird uebernommen, die
    Positionen bleiben die des Papierbuchs.
    """
    live = lade_json(os.path.join(ordner, stufenname("zustand.live.json")))
    t_live = live.get("letzter_lauf") if isinstance(live, dict) else None
    if not t_live:
        return zustand
    jetzt = datetime.now(UTC)
    a_live = alter_minuten(t_live, jetzt)
    a_pap = alter_minuten((zustand or {}).get("letzter_lauf"), jetzt)
    if a_live is not None and (a_pap is None or a_live < a_pap):
        zustand = dict(zustand or {}, letzter_lauf=t_live)
    return zustand


def herzschlag_lage(spur, zustand, wachen, jetzt):
    """Traegt die Spur ihren eigenen Herzschlag noch?

    Grenze aus `wachen.json` (herzschlag_max_minuten), Messwert aus
    `zustand.json` (letzter_lauf) - beides gelesen, nichts behauptet.
    """
    grenze = _zahl(wachen.get("herzschlag_max_minuten"))
    alt = alter_minuten(zustand.get("letzter_lauf"), jetzt)
    if alt is None:
        return ("unbekannt", None, grenze)
    if grenze is None:
        return ("ohne Grenze", alt, grenze)
    return ("ok" if alt <= grenze else "ueberfaellig", alt, grenze)


def spur_stand(spur, zustand, wachen, fenster, jetzt):
    """Eine Zeile der Spurtabelle - gerechnet, nicht formatiert geraten."""
    lage, alt, grenze = herzschlag_lage(spur, zustand, wachen, jetzt)
    pos = positionen_der_spur(spur, zustand, wachen)
    handel_erlaubt = wachen.get("handel_erlaubt")
    return {
        "spur": spur,
        "modus": str(zustand.get("modus") or "-"),
        "fenster": fenster.text() if fenster is not None else "-",
        "positionen": len(pos),
        "stand": ("%.0f min" % alt) if alt is not None else "-",
        "herzschlag": lage,
        "herzschlag_minuten": alt,
        "herzschlag_grenze": grenze,
        "handel_erlaubt": (bool(handel_erlaubt) if handel_erlaubt is not None
                           else None),
        "stand_alter_min": alt,
    }


def spalten_der_spurtabelle():
    """Die Spaltenschluessel der Spurtabelle - aus dem Aufbau, nicht geraten.

    `spur_zeile` und die Tabelle muessen dieselbe Liste benutzen. Stand diese
    Liste zweimal in der Datei, war eine Aenderung an der einen wirkungslos,
    ohne Fehlermeldung (bei `spur_zeile` stand genau das bis 30.09.2026 zweimal
    da). Deshalb kommt die Liste aus EINER Funktion, und der Test liest sie
    von dort.
    """
    return tuple(SPUREN_SPALTEN)


# Die Reihenfolge ist Vertrag: `spur_zeile` liefert die Zellen in genau dieser
# Reihenfolge. Zwischen "pos" und "herzschlag" stehen seit 05.10.2026 die drei
# Bilanzspalten (Runden, Treffer %, Ergebnis) - Auftrag Max: "die PnL% etc als
# Auswahl in den Listen zum Filtern".
SPUREN_SPALTEN = ("spur", "modus", "fenster", "stand", "pos", "runden",
                  "treffer", "pnl", "herzschlag", "handel")
SPUREN_KOPF = {"spur": "Spur", "modus": "Modus", "fenster": "Fenster",
               "stand": "Stand", "pos": "Pos", "runden": "Runden",
               "treffer": "Treffer %", "pnl": "Ergebnis",
               "herzschlag": "Herzschlag", "handel": "handel_erlaubt"}
# Wunschbreiten in RANGfolge, nicht je Spalte: der Name zuerst, dann die
# Freigabe-Uhr als Hauptspalte.
SPUREN_WUNSCH = (200, 90, 150, 90, 60, 70, 80, 110, 110, 130)


def bilanz_zellen(spur, fenster=None):
    """Runden, Treffer %, Ergebnis als drei Zellen fuer die Spurtabelle.

    Ein VORHANDENER Aufruf: die Handelszentrale zeigte nie eine Bilanz, und
    wer eine Spur beurteilen will, muesste ein zweites Fenster aufmachen.
    Quelle ist `auswertung_alle.kennzahlen_fuer` - dieselbe wie im
    Tagesbericht, damit beide dieselbe Zahl zeigen.

    Fehlt eine Zahl (kein Journal, kaputte Datei), steht ein "?" dort. Eine
    falsche Zahl waere schlimmer als eine fehlende.

    `fenster` schneidet auf Tage zurueck (7 = die letzte Woche); ohne Angabe
    zaehlt alles, wie im Tagesbericht.
    """
    if fenster is None:
        z = {}
        try:
            z = auswertung_alle.kennzahlen_fuer(spur) or {}
        except Exception:                        # noqa: BLE001
            z = {}
    else:
        z = {}
        try:
            import datetime as _dt
            bis = _dt.datetime.now(_dt.timezone.utc)
            z = auswertung_alle.kennzahlen_fuer(
                spur, bis - _dt.timedelta(days=int(fenster)), bis) or {}
        except Exception:                        # noqa: BLE001
            z = {}
    n = z.get("n")
    runden = str(n) if isinstance(n, int) and n > 0 else "?"
    t_pct = z.get("treffer_pct")
    treffer = "%d %%" % round(t_pct) if isinstance(t_pct, (int, float)) and n else "?"
    erg = z.get("ergebnis")
    if isinstance(erg, (int, float)) and n:
        vorzeichen = "+" if erg > 0 else ""
        pnl = "%s%.2f %s" % (vorzeichen, erg, z.get("einheit") or "USD")
    else:
        pnl = "?"
    return runden, treffer, pnl


def spur_zeile(stand):
    """Die Zellen der Spurtabelle, in Spaltenreihenfolge.

    Bis 30.09.2026 stand diese Funktion ZWEIMAL in der Datei, wortgleich.
    Python laesst die LETZTE Definition gewinnen: die erste Fassung war tot.
    Kein Verhalten war deshalb falsch, aber eine Aenderung nur an der ersten
    haette gewirkt wie keine. Eine Fassung, ein Ort.
    """
    erlaubt = stand["handel_erlaubt"]
    runden, treffer, pnl = bilanz_zellen(stand["spur"], stand.get("fenster_tage"))
    return (
        stand["spur"],
        stand["modus"],
        stand["fenster"],
        stand["stand"],
        str(stand["positionen"]),
        runden,
        treffer,
        pnl,
        stand["herzschlag"],
        ("ja" if erlaubt else "nein") if erlaubt is not None else "?",
    )


def _log_zeit(text, basis):
    """'13.09. 18:25:44' -> Zeitstempel mit dem Jahr aus `basis`.

    Bewusst OHNE datetime.strptime('%d.%m. ...'): ein Format ohne Jahr warnt
    seit Python 3.13 (DeprecationWarning) und soll in 3.15 verbindlich
    scheitern. Ausserdem traegt das Log LOKALE Zeit - der Vergleich muss in
    derselben Zone stattfinden, sonst liest sich ein frischer Eintrag als
    Zukunft (negatives Alter).
    """
    try:
        t = datetime(basis.year, int(text[3:5]), int(text[0:2]),
                     int(text[7:9]), int(text[10:12]), int(text[13:15]),
                     tzinfo=basis.tzinfo)
    except (ValueError, IndexError):
        return None
    return t


LOG_SCHWANZ_BYTES = 65536


# ---------------------------------------------------------------- Spaltenbreite
# Die Tabellen bekommen ihre Breiten aus `spaltenbreiten` statt aus festen
# Pixelzahlen. Grund ist gemessen, nicht vermutet (04.10.2026, `messprobe.py`,
# Aufruf OHNE --dpi, weil die Zentrale selbst ohne dpi_bewusst() startet):
#   57 Texte passten nicht in ihre Spalte, die Positionstabelle war 36 px
#   breiter als ihr Baum.
# Ursache war nicht die Schrift, sondern dass feste Pixelzahlen nur fuer die
# Skalierung gelten, bei der sie gesetzt wurden. Die Zentrale startet mit
# `tk scaling 1.1`; kommt dpi_bewusst() dazu (Faktor 1.25), ist ein Zeichen
# 10 px breit statt 8 (gemessen mit zeichenbreite_dpi.py: 23 Zeichen gehen
# von 184 px auf 230 px).
SPALTEN_RAND = 8          # Luft in der Zelle, damit der Text nicht ansteht
SPALTEN_MINIMUM = 60      # darunter ist eine Spalte unlesbar
ROLLENDE = 40             # zwei Rollbalken (2 x 16) + Innenrand
ZEICHEN_BREITE_TK = 8     # ohne dpi_bewusst(), tk scaling 1.1 (gemessen)
ZEICHEN_BREITE_DPI = 10   # mit dpi_bewusst(), Faktor 1.25 (gemessen)
SPALTEN_VORGABE = 120     # Wunschbreite ohne Rangfolge (Text entscheidet)
BREITEN_MAX_DURCHGAENGE = 5   # danach gehoeren die Breiten dem Nutzer


def spaltenbreiten(spalten, kopf, wunsch, texte=None, zeichen_breite=None,
                   verfuegbar=0, rand=SPALTEN_RAND, minimum=SPALTEN_MINIMUM):
    """Breite je Spalte: was der Text braucht, gedeckelt durch den Platz.

    Reihenfolge der Entscheidung - und das ist eine Entscheidung, keine
    Reihenfolge des Zufalls:

      1. Jede Spalte braucht mindestens so viel, wie ihre UEBERSCHRIFT und
         ihre Texte brauchen. Das ist eine Untergrenze, keine Wunschzahl:
         ein Text, der nicht passt, wird still abgeschnitten.
      2. Wo Wunsch und Text sich widersprechen, gewinnt der Text bis zum
         Wunsch; darueber gewinnt der Wunsch - sonst wuerde ein langer
         Ausreisser das ganze Fenster verschieben.
      3. Passt die Summe nicht in den Baum, wird gekuerzt: von der letzten
         Spalte zuerst (sie ist meist der Restplatz), dann von hinten nach
         vorn. Keine Spalte faellt unter ihre Untergrenze aus Schritt 1.

    Reicht der Platz auch dafuer nicht, kommt eine waagerechte Leiste - die
    hat jede Tabelle (`tabelle_mit_leiste`). Ein sichtbares Scrollen ist
    besser als ein stiller Verlust.

    `zeichen_breite` kommt aus `zeichen_breite()` und nicht aus einer
    Konstante: dieselbe Schrift misst ohne dpi_bewusst() 8 px je Zeichen
    und mit 11 px, und die Rechnung gilt nur fuer den Fall, in dem sie
    laeuft.

    Rueckgabe: Liste (spalte, breite) in der Reihenfolge von `spalten`.
    """
    n = len(spalten)
    if not n:
        return []
    texte = texte or {}
    zb = zeichen_breite or ZEICHEN_BREITE_TK
    # Eine leere Wunschliste ist ein Aufruf ohne Rangfolge, kein Fehler: dann
    # gilt fuer jede Spalte ders Vorgabewunsch. Vorher lief hier ein
    # IndexError, das `refresh()` fing und in die Konsole schrieb - die
    # Nachrechnung fand also nie statt und die Breiten blieben die vom Bauen.
    if not wunsch:
        wunsch = [SPALTEN_VORGABE]

    def braucht(text):
        if text is None or text == "":
            return 0
        return len(str(text)) * zb + rand

    # 1. Untergrenze: Ueberschrift und Texte. Sie ist der groessere der
    #    beiden Werte - der Textbedarf gewinnt gegen SPALTEN_MINIMUM. Ein
    #    Fehler hier war beim Bauen messbar: die Spalte 'kurs' stand auf
    #    60 px, obwohl ihre Ueberschrift und ihr Text 80 px brauchen.
    #    'minimum' ist die Lesebarkeitsgrenze fuer eine Spalte OHNE Text,
    #    nicht ein Deckel fuer eine Spalte MIT Text.
    unten = []
    for sp in spalten:
        b = braucht(kopf.get(sp, sp))
        for zeile in texte.get(sp, ()):
            b = max(b, braucht(zeile))
        unten.append(max(minimum, b) if b else minimum)
    # 2. Wunsch, aber nie unter der Untergrenze.
    oben = [max(u, int(wunsch[min(i, len(wunsch) - 1)]))
            for i, u in enumerate(unten)]
    # 3. Kuerzen bis in den Platz. Zwei Fehler waren hier beim Bauen
    #    messbar und sind jetzt festgehalten:
    #   * Ein einziger Durchlauf rueckwaerts reichte nicht: kam am Ende
    #     noch Ueberhang, war er an den vorderen Spalten abgeschnitten und
    #     unter ihre Untergrenze gekommen (gemessen: Spalte 'kurs' 60 px
    #     bei 98 px Bedarf).
    #   * Die Hauptspalte wurde vor der letzten gekuerzt, weil die
    #     Rueckwaertsliste bei jedem Durchlauf neu anhaengt. Der Spurname
    #     stand dadurch auf 100 statt 220 px, waehrend die Kurspalte noch
    #     Luft hatte.
    # Also: Runden, bis nichts mehr geht, und in jeder Runde die hinteren
    # Spalten zuerst. Die Reihenfolge "letzte zuerst" ist eine Entscheidung:
    # die letzte Spalte traegt bei mehreren Tabellen den Grund.
    if verfuegbar <= 0:
        return list(zip(spalten, oben))
    platz = verfuegbar - ROLLENDE
    for _ in range(n):                      # hoechstens n Runden noetig
        ueber = sum(oben) - platz
        if ueber <= 0:
            break
        bewegt = False
        for i in list(range(n))[::-1]:
            if ueber <= 0:
                break
            nimm = min(oben[i] - unten[i], ueber)
            if nimm <= 0:
                continue                    # steht schon auf ihrem Minimum
            oben[i] -= nimm
            ueber -= nimm
            bewegt = True
        if not bewegt:
            break                           # nichts mehr zu geben: Leiste
    return list(zip(spalten, oben))


def zeichen_breite(root=None):
    """Wie breit ist ein Zeichen in der FENSTERSchrift: gemessen, nicht
    geraten. Ohne Fenster die gemessene Grundzahl des Nicht-DPI-Falls.

    Consolas ist festbreit, also genuegt die Zeichenlange - aber nur, wenn
    Schriftgroesse und DPI-Fall zum Fenster passen. Beides kommt aus dem
    Fenster, das wirklich laeuft.
    """
    try:
        import tkinter.font as tkfont
        if root is not None:
            f = tkfont.Font(root=root, family=SCHRIFT_ART, size=SCHRIFT_GROESSE)
            return int(f.measure("M" * 20) / 20 + 0.999)
    except Exception:                                        # noqa: BLE001
        pass
    return ZEICHEN_BREITE_TK


def log_ende(pfad, zeilen=12, grenze=LOG_SCHWANZ_BYTES):
    """Die letzten Zeilen einer Logdatei, ohne sie ganz zu lesen.

    Bis 30.09.2026 las die Zentrale bei JEDEM Refresh (alle 15 s) das ganze
    Dauerlauf-Protokoll zweimal: `dauerlauf_stand` Zeile fuer Zeile bis zum Ende
    und `_schreibe_konsole` per `readlines()[-12:]` - gemessen 85 KB im laufenden
    `dauerlauf.log`, 1,0 MB in der rotierten `dauerlauf.log.1`. Der Schwanz
    reicht fuer alles, was angezeigt wird, und wachst nicht mit dem Log.
    Eine unlesbare oder fehlende Datei ist kein Fehler: leere Liste.
    """
    try:
        with open(pfad, "rb") as f:
            f.seek(0, os.SEEK_END)
            groesse = f.tell()
            f.seek(max(0, groesse - grenze))
            anfang = f.tell()
            roh = f.read()
    except OSError:
        return []
    teile = roh.decode("utf-8", "replace").splitlines()
    if anfang and teile:
        teile = teile[1:]          # der angeschnittene Rest der ersten Zeile
    return teile[-zeilen:] if zeilen else teile


# Was in einem Dauerlauf-Protokoll einen Fehler anzeigt. Bewusst Woerter, keine
# Regel: "Auto-Freigabe scanner" ist eine normale Betriebsmeldung.
FEHLER_WOERTER = ("fehler", "fehler:", "fehler(", "traceback", "exception",
                  "timeout", "time-out", "abgestürzt", "abgestuerzt", "absturz",
                  "nicht erreichbar", "nicht lesbar", "abbruch", "crash",
                  "exit code", "exitcode", "zurückgewiesen", "zurueckgewiesen")


def log_marke(zeile):
    """Die Farbe einer Protokollzeile in der Konsole: "", "matt" oder "schlecht".

    Die Regel bis 30.09.2026 war: rot, wenn die Zeile NICHT " ok" enthaelt.
    Damit stand jede Betriebsmeldung in Alarmfarbe - belegt am 01.10.2026 mit
    der Zeile '01.10. 11:56:06  Auto-Freigabe scanner ...', die rot war, ohne
    dass etwas fehlschlug. Rot gibt es nur noch fuer ein echtes Fehlermerkmal;
    " ok" bleibt matt, alles andere bekommt keine Marke (Default-Farbe).
    """
    text = str(zeile).lower()
    if any(w in text for w in FEHLER_WOERTER):
        return "schlecht"
    return "matt" if " ok" in text else ""


def dauerlauf_stand(pfad, jetzt):
    """Letzter Eintrag im Dauerlauf-Log als (Text, Minuten seitdem).

    Der Zeitstempel im Log hat kein Jahr. Liegt die gelesene Zeit mehr als
    einen Tag in der Zukunft, gehoert sie zum Vorjahr - sonst liest sich ein
    Altbestand als Zukunft.
    """
    letzte = None
    for zeile in reversed(log_ende(pfad, 400)):
        if len(zeile) >= 15 and zeile[:2].isdigit():
            letzte = zeile
            break
    if not letzte:
        return (None, None)
    text = letzte[:15]
    basis = jetzt.astimezone()
    t = _log_zeit(text, basis)
    if t is None:
        return (text, None)
    if t - basis > timedelta(days=1):
        t = _log_zeit(text, basis.replace(year=basis.year - 1))
    return (text, (basis - t).total_seconds() / 60.0)


def prozess_lebt(pid):
    """Laeuft dieser Prozess? Reines Nachfragen - KEIN os.kill.

    Auf Windows wuerde `os.kill(pid, 0)` den Prozess terminieren; OpenProcess
    mit PROCESS_QUERY_LIMITED_INFORMATION fragt nur. None heisst: nicht
    beantwortbar (kein Windows, kein Recht auf Abfrage).
    """
    if not pid:
        return None
    try:
        k = ctypes.windll.kernel32                       # type: ignore[attr-defined]
    except Exception:                                        # noqa: BLE001
        return None
    griff = k.OpenProcess(0x1000, False, int(pid))
    if not griff:
        return False
    k.CloseHandle(griff)
    return True


def journal_ereignisse(spur, pfad, grenze=3):
    """Die juengsten Buchungen eines Journals in einer Form.

    Die Journalkoepfe sind je Spur verschieden (inst/paar/symbol,
    aktion/ausgang, preis/ausstieg, einsatz_usd/usd/eur) - jede Spalte wird
    ueber ihre Varianten gelesen, keine wird erfunden.
    """
    try:
        with open(pfad, encoding="utf-8", newline="") as f:
            zeilen = list(csv.DictReader(f))
    except Exception:                                        # noqa: BLE001
        return []
    aus = []
    for z in zeilen:
        symbol = z.get("symbol")
        kette = z.get("kette")
        instrument = (z.get("inst") or z.get("paar")
                      or ("%s (%s)" % (symbol, kette) if symbol and kette
                          else symbol or "?"))
        aus.append({
            "spur": spur,
            "zeit": z.get("zeit") or "",
            "instrument": instrument,
            "seite": str(z.get("seite") or z.get("richtung") or "").lower(),
            "aktion": str(z.get("aktion") or z.get("ausgang") or "").upper(),
            "preis": _zahl(z.get("preis") or z.get("ausstieg")),
            "einsatz": _zahl(z.get("einsatz_usd") or z.get("usd") or z.get("eur")),
            "wert": _zahl(z.get("wert_usd")),
            "gv": _zahl(z.get("gv_usd")),
            "grund": z.get("grund") or "",
        })
    aus.sort(key=lambda e: e["zeit"], reverse=True)
    return aus[:grenze]


def ereignis_gv(e):
    """G/V eines Journaleintrags in Prozent, oder None.

    Bevorzugt das mitgeschriebene `gv_usd`-Feld (ORB), sonst aus Wert/Einsatz
    gerechnet - das Journal der anderen Spuren hat kein G/V-Feld.
    """
    if e.get("gv") is not None and e.get("einsatz"):
        return e["gv"] / e["einsatz"] * 100.0
    if e.get("wert") is not None and e.get("einsatz"):
        return (e["wert"] / e["einsatz"] - 1.0) * 100.0
    return None


def zeit_kurz(wert):
    """Zeit fuer die Konsole.

    Die Journale sind hier nicht einig: die meisten schreiben einen
    ISO-Zeitstempel, die ORB-Spur nur das Datum ("2026-09-13"). Ein starres
    `wert[11:16]` liest dort eine leere Spalte - "--:--" fuer eine Buchung,
    die sehr wohl einen Tag hat.
    """
    w = str(wert or "")
    if len(w) >= 16 and w[10] in ("T", " "):
        return w[11:16]
    if len(w) >= 10 and w[4] == "-":
        return "%s.%s." % (w[8:10], w[5:7])
    return "--:--"


def ereignis_zeile(e):
    """Eine Konsolenzeile je Buchung - Instrument und Seite immer dabei."""
    teile = ["%s" % zeit_kurz(e["zeit"]), "%-8s" % e["spur"],
             "%-9s" % e["aktion"], "%-22s" % e["instrument"]]
    if e["seite"]:
        teile.append("%-5s" % e["seite"])
    if e["preis"] is not None:
        teile.append("@ %s" % kurs_fmt(e["preis"]))
    gv = ereignis_gv(e)
    if gv is not None:
        teile.append("%+.1f %%" % gv)
    if e["grund"]:
        teile.append("(%s)" % e["grund"])
    return "  ".join(teile)


def chart_bereich(kerzen, linien):
    """Der Preisbereich des Charts, damit Stop und Ziel nie aus dem Bild
    fallen. Leere Kerzen -> (0.0, 0.0)."""
    werte = []
    for k in kerzen or []:
        werte.extend([_zahl(k[2]), _zahl(k[3])])
    for l in linien or []:
        werte.append(_zahl(l))
    werte = [w for w in werte if w is not None]
    if not werte:
        return (0.0, 0.0)
    tief, hoch = min(werte), max(werte)
    if hoch <= tief:
        hoch = tief + (abs(tief) * 0.01 or 1.0)
    rand = (hoch - tief) * 0.06
    return (tief - rand, hoch + rand)


# --------------------------------------------------------------------------
# Die Oberflaeche
# --------------------------------------------------------------------------

_konto_cache = {"text": "Kraken-Konto: …", "warnung": False, "alter": None,
                "laufend": False}


def _konto_im_thread():
    """Echter Kraken-Kontostand, rein lesend. Schluessel kommen aus Umgebung
    oder HKCU\\Environment (kraken._variable); fehlt der Zugang oder der Abruf
    laeuft in eine Wand, bleibt die letzte Zeile stehen - die GUI darf am
    Konto nie scheitern und wartet nie darauf."""
    try:
        import kraken                                            # noqa: PLC0415
        staende = kraken.kontostaende()
        frei = {c: float(staende.get(c, 0.0) or 0.0)
                for c in ("ZEUR", "USDC", "EURC")}
        _konto_cache["text"] = ("Kraken-Konto: "
                                + ", ".join("%s %.2f" % (c, v)
                                            for c, v in frei.items())
                                + " frei")
        # mindest_guthaben_je_quote der Kraken-Spur. Die Spur ordert in der
        # Waehrung des PAARES - EINE gedeckte Waehrung genuegt also. Vorher
        # stand hier nur ZEUR: das Fenster meldete "unter 60", waehrend die
        # Spur in USDC haette handeln koennen.
        gedeckt = [c for c, v in frei.items() if v >= 60.0]
        _konto_cache["warnung"] = not gedeckt
        if not gedeckt:
            _konto_cache["text"] += "   (keine Waehrung ueber 60)"
    except Exception:                                            # noqa: BLE001
        _konto_cache["text"] = "Kraken-Konto: nicht erreichbar"
        _konto_cache["warnung"] = True
    finally:
        _konto_cache["laufend"] = False


def kraken_konto_lage():
    """(Text, Warnung) mit 60-s-Cache; der erste Aufruf startet den Abruf im
    Hintergrund, damit kein Netzwart auf dem GUI-Thread lastet."""
    jetzt = datetime.now()
    alt = _konto_cache["alter"]
    if alt and (jetzt - alt).total_seconds() < 60 and not _konto_cache["laufend"]:
        return _konto_cache["text"], _konto_cache["warnung"]
    if not _konto_cache["laufend"]:
        _konto_cache["alter"] = jetzt
        _konto_cache["laufend"] = True
        threading.Thread(target=_konto_im_thread, daemon=True).start()
    return _konto_cache["text"], _konto_cache["warnung"]


# ---------- FreqTrade (Reiter) ----------
def _ft_zeit(wert):
    """'2026-09-29 16:45:00' -> '29.09. 16:45'; FreqTrade-Trades laufen ueber Tage."""
    w = str(wert or "")
    if len(w) >= 16 and w[4] == "-" and w[10] in ("T", " "):
        return "%s.%s. %s" % (w[8:10], w[5:7], w[11:16])
    return zeit_kurz(w)


def freqtrade_kopf(lage, name=None):
    """(Text, Marke) der Kopfzeile im FreqTrade-Reiter aus `freqtrade_bridge.lage()`.

    `name` ist der Bot, dessen Lage hier steht - der Reiter zeigt jetzt alle
    Bots, ohne die Angabe waere nicht beantwortbar, WELCHEN Bot die Zeile
    beschreibt.
    """
    if not lage:
        return "FreqTrade: wird abgefragt …", "matt"
    if not lage.get("erreichbar"):
        return "⚠ FreqTrade%s nicht erreichbar — %s" % (
            " %s" % name if name else "", lage.get("fehler", "?")), "schlecht"
    modus = "Probebetrieb" if lage.get("dry_run") else "LIVE"
    text = ("FreqTrade %s · %s · %s · %s %s   Guthaben %.2f %s   offen %d   "
            "Trades %d   G/V geschlossen %+.2f   gesamt %+.2f"
            % (modus, lage.get("zustand"), lage.get("boerse"),
               lage.get("strategie"), lage.get("zeitrahmen"),
               _zahl(lage.get("guthaben")) or 0.0, lage.get("waehrung"),
               lage.get("offene_trades", 0), lage.get("trades_gesamt", 0),
               _zahl(lage.get("gewinn_geschlossen")) or 0.0,
               _zahl(lage.get("gewinn_gesamt")) or 0.0))
    if name:
        text = "%s  —  %s" % (name, text)
    # Ein Bot, der nicht im Probebetrieb laeuft, ist hier nie der Normalfall.
    return text, "gut" if lage.get("dry_run") else "schlecht"


def freqtrade_offen_zeile(t):
    """Werte einer offenen FreqTrade-Position fuer die Tabelle."""
    return (t.get("pair", "?"), "short" if t.get("is_short") else "long",
            _ft_zeit(t.get("open_date")), kurs_fmt(_zahl(t.get("open_rate"))),
            kurs_fmt(_zahl(t.get("current_rate"))),
            "%.2f" % (_zahl(t.get("stake_amount")) or 0.0),
            "%+.2f" % (_zahl(t.get("profit_pct")) or 0.0))


def freqtrade_zu_zeilen(antwort, anzahl=20):
    """Die letzten geschlossenen Trades aus `/trades`, neueste zuerst."""
    liste = antwort.get("trades", []) if isinstance(antwort, dict) else []
    zu = [t for t in liste if not t.get("is_open")]
    zu.sort(key=lambda t: t.get("close_date") or "", reverse=True)
    return [(t.get("pair", "?"), _ft_zeit(t.get("open_date")),
             _ft_zeit(t.get("close_date")),
             "%+.2f" % (_zahl(t.get("profit_pct")) or 0.0),
             "%+.2f" % (_zahl(t.get("profit_abs")) or 0.0),
             t.get("exit_reason") or "")
            for t in zu[:anzahl]]


def freqtrade_tagesbalken(antwort):
    """[(TT.MM., G/V absolut, Trades)] aus `/daily`, aeltester Tag zuerst."""
    liste = (antwort.get("data") if isinstance(antwort, dict) else None) or []
    tage = sorted((t for t in liste
                   if isinstance(t, dict) and len(str(t.get("date", ""))) >= 10),
                  key=lambda t: str(t["date"]))
    return [("%s.%s." % (str(t["date"])[8:10], str(t["date"])[5:7]),
             _zahl(t.get("abs_profit")) or 0.0,
             int(_zahl(t.get("trade_count")) or 0)) for t in tage]


def _gv_marke(text):
    """Tabellen-Tag aus '+1.23' / '-0.50'."""
    zahl = _zahl(text)
    return "gut" if zahl and zahl > 0 else "schlecht" if zahl and zahl < 0 else ""


def bot_waehlen(liste, name):
    """Der Bot mit diesem Namen, sonst der erste; None, wenn die Liste leer ist.

    Die Liste kommt aus `freqtrade_bridge.bots()` (freqtrade/bots.json). Ein
    name, den die Liste nicht kennt, faellt auf den ersten Bot zurueck - die
    Zentrale startet nichts und erfindet nichts, sie zeigt nur.
    """
    for b in liste or []:
        if b.get("name") == name:
            return b
    return (liste or [None])[0]


def freqtrade_uebersicht_zeilen(zeilen):
    """[(Werte, Marke)] je Bot - die Uebersicht Zeile fuer Zeile.

    Ein nicht erreichbarer Bot bekommt eine Zeile mit seinem Grund statt zu
    fehlen: "der Bot laeuft nicht" ist eine Aussage, die die Zentrale zeigen
    muss, nicht eine, die sie verschluckt (derselbe Fall wie die toten
    Spur-Ordner im Leitstand).
    """
    aus = []
    for z in zeilen or []:
        if not isinstance(z, dict):
            continue
        erreichbar = bool(z.get("erreichbar"))
        modus = ("Probebetrieb" if z.get("dry_run") else "LIVE") if erreichbar else "-"
        werte = (z.get("name") or "?", str(z.get("port") or "?"),
                 z.get("strategie") or "?", z.get("zeitrahmen") or "?",
                 modus, z.get("zustand") or "?",
                 "%s / %s" % (z.get("offen"), z.get("max")) if erreichbar else "-",
                 str(z.get("trades")) if erreichbar and z.get("trades") is not None else "-",
                 ("%+.2f" % (_zahl(z.get("gewinn")) or 0.0)) if erreichbar else "-",
                 "" if erreichbar else (z.get("fehler") or "nicht erreichbar"))
        if not erreichbar:
            marke = "schlecht"
        elif not z.get("dry_run"):
            marke = "schlecht"        # LIVE ist hier nie der Normalfall
        else:
            marke = "gut"
        aus.append((werte, marke))
    return aus


def _freqtrade_im_thread(ziel, name=None):
    """Uebersicht ALLER Bots plus die Details des gewaehlten - wirft nie.

    Ein Worker fuer beides: zwei Threads haetten zwei Antworten in beliebiger
    Reihenfolge, und die Uebersicht war manchmal juenger als die Tabelle
    darunter.
    Die Details stammen vom GEWAEHLTEN Bot (Port), die Anmeldung immer aus der
    Basis-config - `freqtrade_bridge.zugang_fuer` erklaert, warum.

    Die Antwort geht auf JEDEM Weg raus, auch bei einer Ueberraschungs-
    exception: die Zentrale haelt die Sperre `_ft_laeuft`, bis ein Stueck im
    Korb liegt. Bliebe sie unten, holte das Fenster nie wieder FreqTrade-Daten.
    """
    paket = ([], {"erreichbar": False, "fehler": "Abruf fehlgeschlagen"},
             [], {}, {})
    try:
        listen = freqtrade_bridge.bots()
        uebersicht = freqtrade_bridge.uebersicht(bot_liste=listen)
        bot = bot_waehlen(listen, name)
        if bot is None:
            # bots.json fehlt oder ist kaputt: nur die Basis-Instanz ist dann
            # beantwortbar - ihre Lage nennt den Grund, die Uebersicht bleibt leer.
            paket = (uebersicht, freqtrade_bridge.lage(), [], {}, {})
        else:
            zd = freqtrade_bridge.zugang_fuer(bot["port"])
            lage = freqtrade_bridge.lage_fuer(bot)
            offen, zu, tage = [], {}, {}
            if lage.get("erreichbar"):
                try:
                    offen = freqtrade_bridge.offene_trades(zd)
                    zu = freqtrade_bridge.trades(100, zd)
                    tage = freqtrade_bridge.tagesbilanz(14, zd)
                except Exception:                            # noqa: BLE001
                    pass        # Lage steht; Tabellen bleiben dann leer
            paket = (uebersicht, lage, offen, zu, tage)
    except Exception as e:                                   # noqa: BLE001
        paket = (paket[0], {"erreichbar": False,
                            "fehler": "%s: %s" % (type(e).__name__, str(e)[:60])},
                 [], {}, {})
    ziel.put(paket)


# ---------- omnitrade (Reiter) ----------
def _ms_zeit(ms):
    """Epoch-Millisekunden -> 'TT.MM. HH:MM:SS' Ortszeit, '' wenn unbrauchbar."""
    try:
        return datetime.fromtimestamp(float(ms) / 1000).strftime("%d.%m. %H:%M:%S")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def omnitrade_kopf(lage):
    """(Text, Marke) der Kopfzeile im omnitrade-Reiter aus `omnitrade_bridge.lage()`."""
    if not lage:
        return "omnitrade: wird gelesen …", "matt"
    if not lage.get("ok"):
        return "⚠ omnitrade — %s" % (lage.get("fehler") or "?"), "schlecht"
    netz = str(lage.get("network") or "?")
    text = ("omnitrade %s · %s %s · %s · %s   Kerzen %d   Kurs %s   Signal %s   "
            "netto %+.6g   Orders %d / abgelehnt %d   (vor %ds)"
            % (lage.get("state"), lage.get("exchange") or "binance", netz,
               lage.get("symbol"), lage.get("script"),
               int(_zahl(lage.get("candles_seen")) or 0),
               kurs_fmt(_zahl(lage.get("last_close"))), lage.get("last_signal"),
               _zahl(lage.get("net_quantity")) or 0.0,
               int(_zahl(lage.get("orders_placed")) or 0),
               int(_zahl(lage.get("orders_rejected")) or 0),
               int(lage.get("alter_s") or 0)))
    if lage.get("last_error"):
        text += "   letzter Fehler: %s" % lage["last_error"]
    # Echtgeld ist hier nie der Normalfall; ein Fehlerzustand auch nicht.
    gut = netz.lower() != "mainnet" and lage.get("state") != "error"
    return text, "gut" if gut else "schlecht"


def omnitrade_order_zeilen(lage):
    """Letzte Order-Ereignisse, neueste zuerst: (Zeit, Seite, Menge, Preis, Ergebnis, Meldung)."""
    liste = lage.get("recent_orders") if isinstance(lage, dict) else None
    zeilen = []
    for o in reversed(liste if isinstance(liste, list) else []):
        if not isinstance(o, dict):
            continue
        zeilen.append((_ms_zeit(o.get("time_ms")), o.get("side", "?"),
                       "%.6g" % (_zahl(o.get("quantity")) or 0.0),
                       kurs_fmt(_zahl(o.get("price"))), o.get("outcome", "?"),
                       o.get("detail") or ""))
    return zeilen


def omnitrade_laeufe_zeilen(bilanzen):
    """Zeilen der Laeufe-Tabelle aus `omnitrade_auswertung.alle()`: (Werte, Marke)."""
    def pct(x):
        return "-" if x is None else "%+.2f%%" % x
    zeilen = []
    for b in bilanzen or []:
        if "strategie" not in b:
            zeilen.append(((b.get("datei", "?"), "", "", "", "", "", "", "",
                            b.get("fehler", "")), "schlecht"))
            continue
        zustand = b["state"] if b["ok"] else (b["fehler"] or "?")
        werte = (b["strategie"], b["symbol"], "%.1f h" % b["laufzeit_h"], b["kerzen"],
                 "%d / %d" % (b["orders"], b["abgelehnt"]),
                 "%d / %d" % (b["kaeufe"], b["verkaeufe"]),
                 "%+.2f (%s)" % (b["gewinn"], pct(b["gewinn_pct"])),
                 pct(b["buyhold_pct"]), zustand)
        zeilen.append((werte, "gut" if b["ok"] else "schlecht"))
    return zeilen


# --- Haus-Buch der omnitrade-SPUR (derselbe Reiter) -------------------------
#
# Der Reiter trug bis zum 30.09.2026 NUR den Rust-Lauf (Statusdatei). An
# demselben Tag kam die Haus-Spur dazu, die dessen Position spiegelt - und sie
# heisst genauso. Ohne diesen Abschnitt liest man im Reiter "omnitrade" eine
# Zahl und weiss nicht, welche der beiden gemeint ist. Deshalb stehen sie
# getrennt: oben "Laeufe" (Rust, Testnet), hier "Haus-Buch" (Spur, Papier/Live).

def omnitrade_spur_kopf(zustand, wachen, jetzt=None):
    """(Text, Marke) der Kopfzeile des Haus-Buchs im omnitrade-Reiter.

    Zeigt dieselben Groessen, die der Sperrtext der Spur nennt: Modus, Plaetze,
    Alter des letzten Zyklus und den Live-Stand aus der wachen. `jetzt` ist fuer
    Tests da.
    """
    jetzt = jetzt or datetime.now(UTC)
    z = zustand or {}
    w = wachen or {}
    pos = z.get("positionen") or []
    plaetze = w.get("max_offene_positionen")
    alter = alter_minuten(z.get("letzter_lauf"), jetzt)
    teile = ["Haus-Buch (Spiegel-Spur omnitrade)",
             "%s" % (z.get("modus") or "?"),
             "%d%s Plaetze belegt" % (len(pos), (" von %d" % plaetze) if plaetze else "")]
    if alter is None:
        teile.append("noch kein Zyklus")
    else:
        teile.append("letzter Zyklus vor %d min" % int(alter))
    boerse = w.get("boerse")
    if boerse:
        teile.append("Boerse %s%s" % (boerse, ("/" + str(w["kraken_quote"]))
                                      if w.get("kraken_quote") else ""))
    if w.get("handel_erlaubt") and (w.get("freigabe") or {}).get("erfuellt"):
        teile.append("LIVE scharf")
        marke = "gut"
    else:
        teile.append("Papier (handel_erlaubt=%s, freigabe=%s)"
                     % (bool(w.get("handel_erlaubt")),
                        bool((w.get("freigabe") or {}).get("erfuellt"))))
        marke = "matt"
    # Ein alter Herzschlag heisst: die Spur lief nicht - das ist der einzige
    # Zustand, der hier eine Warnung verdient.
    if alter is not None and alter > (w.get("herzschlag_max_minuten") or 180):
        return "⚠ " + " · ".join(teile), "schlecht"
    return " · ".join(teile), marke


def omnitrade_spur_positionen(spur, zustand, wachen):
    """(Instrument, Seite, Einstieg, Stop, Ziel, Nominal) je offener Position.

    Gelesen wird die NORMALISIERTE Form aus `positionen_der_spur()` - dort
    heisst das Instrument `instrument` und der Einsatz `wert_usd`, nicht `inst`
    und `nominal`. Wer hier `instrument_name(p)` auf das normalisierte Dict
    anwendet, bekommt ein Fragezeichen: `inst` gibt es nur im ROHEN Dict.
    """
    aus = []
    for p in positionen_der_spur(spur, zustand, wachen):
        aus.append((p.get("instrument") or "?", (p.get("seite") or "").upper(),
                    kurs_fmt(p.get("einstieg")), kurs_fmt(p.get("stop")),
                    kurs_fmt(p.get("ziel")), kurs_fmt(p.get("wert_usd"))))
    return aus


def omnitrade_spur_journal(pfad, grenze=6):
    """(Zeit, Modus, Aktion, Instrument, Preis, Grund) - neueste zuerst.

    Eigenes Lesen statt `journal_ereignisse()`: dessen Form traegt kein `modus`
    - und genau das ist hier die interessante Spalte (papier oder live).
    """
    try:
        with open(pfad, encoding="utf-8", newline="") as f:
            zeilen = list(csv.DictReader(f))
    except Exception:                                        # noqa: BLE001
        return []
    aus = []
    for z in zeilen:
        aus.append((str(z.get("zeit") or "").replace("T", " ")[:19],
                    str(z.get("modus") or ""),
                    str(z.get("aktion") or z.get("ausgang") or "").upper(),
                    z.get("inst") or z.get("paar") or "?",
                    kurs_fmt(_zahl(z.get("preis") or z.get("ausstieg"))),
                    z.get("grund") or ""))
    aus.sort(key=lambda r: r[0], reverse=True)
    return aus[:grenze]


# --------------------------------------------------------------------------
# Scrollen: Tabellen mit Leiste, Seiten, die hoeher sind als das Fenster
# --------------------------------------------------------------------------

def _rad_schritte(event, zeilen=1):
    """Zeilen aus dem Mausrad-Ereignis: Windows meldet delta, X11 Buttons 4/5."""
    knopf = getattr(event, "num", None)
    if knopf == 4:
        return -zeilen
    if knopf == 5:
        return zeilen
    schub = int(getattr(event, "delta", 0) or 0)
    if not schub:
        return 0
    stufe = schub // 120 or (1 if schub > 0 else -1)
    return -stufe * zeilen


def rad_selbst(widget, zeilen=1):
    """Das Mausrad direkt an ein scrollbares Widget haengen.

    Das Widget gibt "break" zurueck, damit ein seitengebundener Rad-Handler
    (siehe seite_mausrad) dieselbe Bewegung nicht ein zweites Mal ausfuehrt.
    """
    def dreh(event):
        schritte = _rad_schritte(event, zeilen)
        if schritte:
            try:
                widget.yview_scroll(schritte, "units")
            except Exception:                                # noqa: BLE001
                pass          # Widget gerade weg: unwesentlich
        return "break"
    widget.bind("<MouseWheel>", dreh, add="+")
    widget.bind("<Button-4>", dreh, add="+")
    widget.bind("<Button-5>", dreh, add="+")
    return widget


def _nachkommen(widget):
    for kind in widget.winfo_children():
        yield kind
        for tiefer in _nachkommen(kind):
            yield tiefer


def seite_region_neu(c, innen):
    """Die Scrollregion einer Scrollseite neu setzen; leerer Inhalt bleibt ohne.

    Eigenen Namen, damit der Pfad ohne Fensterereignis pruefbar ist. Zwei
    Fallen, beide am 01.10.2026 nachgemessen:
      * `c.bbox("all")` ist None, solange der Canvas gar kein Item hat -
        `scrollregion=None` wirft einen Tcl-Fehler, der als Hintergrund-Fehler
        unter dem Fenster verschwindet und die Seite unscrollbar laesst.
      * Ist der Inhalt noch nicht gemessen, liefert bbox den ARTIFAKT-Rahmen
        (0, 0, 1, 1) - eine Region von einem Pixel. Die Seite tut dann nichts,
        obwohl eine Region gesetzt ist; also gilt: erst ab echter Hoehe setzen.
    """
    messung = c.bbox("all")
    if not messung or messung[3] <= 1:
        return None
    c.configure(scrollregion=messung)
    return messung


def scrollbare_seite(eltern):
    """(wrapper, innen, seiten_canvas) - eine Seite, die vertikal scrollt.

    Warum das noetig ist: die Spuren-Seite war am 30.09.2026 hoeher als jedes
    Fenster. Spurtabelle mit `height=len(SPUREN)` (42 Zeilen), dazu
    Positionstabelle, Chart und Konsole - der untere Teil war nicht erreichbar,
    weder durch Vergroessern noch durch Ziehen. Eine scrollbare Flaeche ist die
    Antwort, nicht ein kleineres Fenster.

    Die Breite folgt dem Canvas (sonst zerfliesst der Inhalt in die
    Scrollregion), die Scrollregion dem Inhalt.
    """
    wrapper = tk.Frame(eltern, bg=FARBEN["bg"])
    c = tk.Canvas(wrapper, bg=FARBEN["bg"], highlightthickness=0)
    leiste = ttk.Scrollbar(wrapper, orient="vertical", command=c.yview)
    innen = tk.Frame(c, bg=FARBEN["bg"])
    fenster_id = c.create_window((0, 0), window=innen, anchor="nw")
    c.configure(yscrollcommand=leiste.set)
    leiste.pack(side="right", fill="y")
    c.pack(side="left", fill="both", expand=True)
    innen.bind("<Configure>", lambda _e: seite_region_neu(c, innen))
    c.bind("<Configure>", lambda e: c.itemconfigure(fenster_id, width=e.width))
    return wrapper, innen, c


def seite_mausrad(c, innen):
    """Das Mausrad auf der ganzen Scrollseite wirksam machen.

    Ein Radereignis landet auf dem Widget unter dem Zeiger, nicht auf dem
    Canvas dahinter. Also wird der Handler auf den Canvas UND auf jeden
    Nachfahren gelegt - mit `add="+"`, damit nichts verloren geht. Widgets, die
    ihr Rad schon selbst fuehren (`rad_selbst`: Tabellen, Textfelder) werden
    uebersprungen, sonst verschwaede dieselbe Bewegung Seite UND Tabelle.
    """
    def dreh(event):
        schritte = _rad_schritte(event, 3)
        if schritte:
            try:
                c.yview_scroll(schritte, "units")
            except Exception:                                # noqa: BLE001
                pass
        return "break"

    for widget in [c, innen] + list(_nachkommen(innen)):
        try:
            if widget.bind("<MouseWheel>") or widget.bind("<Button-4>"):
                continue          # hat bereits einen eigenen Rad-Handler
            widget.bind("<MouseWheel>", dreh, add="+")
            widget.bind("<Button-4>", dreh, add="+")
            widget.bind("<Button-5>", dreh, add="+")
        except Exception:                                    # noqa: BLE001
            pass          # Widget nimmt keine Bindungen ( selten, z. B. im Aufbau)


def _as_liste_wunsch(baum):
    """Die Wunschbreiten einer gebauten Tabelle, aus ihrer aktuellen Breite.

    Die Tabellen ohne eigene Rangfolge (FreqTrade, omnitrade) bekommen ihre
    Soll-Breite beim Bauen aus ihrem Wunsch-Dict. Ohne diese Liste hier
    wuerde die Nachrechnung auf SPALTEN_VORGabe zurueckfallen und die
    haertzuschuechende Spalte verlieren, die der Nutzer mit einem Dict
    bekommen hat. Also: das Dict beim Bauen merken, nicht erraten.
    """
    return list(getattr(baum, "_wunsch", None) or [])


def kopf_von(baum):
    """Die Ueberschriften eines Treeviews als Dict - die Rechnung
    `spaltenbreiten` braucht sie, und sie stehen nur im Widget."""
    return {sp: (baum.heading(sp, "text") or sp) for sp in baum["columns"]}


def _als_liste(spalten, wunsch):
    """Wunschbreiten als Liste in Spaltenreihenfolge.

    Zwei Formen sind zulaessig, weil beide im Baum vorkommen:
      * eine Liste, der Reihenfolge von `spalten` folgend - die neue Form,
        sie nennt die RANGfolge ausdruecklich;
      * ein Dict je Spalte - die alte Form, die noch in sechs Aufrufen
        steht. Beide werden ueber `spaltenbreiten` gefuehrt, aber die
        Ausgabe ist immer dieselbe Liste; ein Aufrufer kann also nicht
        versehentlich wieder eine feste Pixelzahl setzen.

    Fehlt ein Eintrag, gilt der Wunsch der vorigen Spalte.
    """
    if isinstance(wunsch, dict):
        # Ein fehlender Eintrag erbt NICHT den Eintrag davor. In den
        # Aufrufen stehen Dicts wie {"zeit": 260} - dort ist "zeit" die
        # breite Spalte und alle anderen sind normale. Der alte Code
        # erbte rueckwaerts und machte aus {"zeit": 260} sechs Spalten zu
        # je 260 px (gemessen: 1560 px in einem Baum von 1241 px, +359 px).
        # Der Vorgabewunsch ist hier SPALTEN_VORGABE, nicht der Nachbar.
        return [int(wunsch.get(sp, SPALTEN_VORGABE)) for sp in spalten]
    if wunsch is None:
        return []
    return [int(w) for w in wunsch]


def tabelle_mit_leiste(rahmen, spalten, kopf, wunsch=None, hoehe=8,
                       anker_w=(), dehnen="", wahl=None, texte=None):
    """Eine Treeview MIT senkrechter und waagerechter Leiste und Mausrad.

    Vorher gab es die Leiste nur bei zwei der sieben Tabellen der Zentrale;
    eine Tabelle ohne Leiste ist bei mehr Zeilen als Platz ein Abschnitt, den
    man nicht lesen kann. Die Hoehe ist bewusst eine Vorgabe (keine Formel aus
    der Zeilenzahl): die Seite scrollt, die Tabelle bleibt ein Feld.
    `wahl` ist die Treeview-Auswahlform ("browse" fuer anklickbare Tabellen).

    Die Breiten kommen aus `spaltenbreiten`, nicht aus festen Pixelzahlen
    (Begründung und Messung dort). `wunsch` ist eine Liste von Breiten bei
    Skalierung 1, nach RANGfolge aufgebaut; fehlt sie, wird nach Textbedarf
    gerechnet. `texte` ist optional - ohne die Zeilen, die gerade drin
    stehen, rechnet die Funktion nur mit Ueberschriften und spaeter nach.

    `dehnen` bleibt erhalten, verliert aber seine Wirkung: Tk verteilt bei
    `stretch=True` die Restbreite selbst und verfaelscht damit jede hier
    gerechnete Breite (gemessen 191 statt 125 px, Skill desktop-fenster).
    Alle Spalten stehen auf stretch=False; wer mehr Platz hat, bekommt ihn
    ueber die waagerechte Leiste.
    """
    baum = ttk.Treeview(rahmen, columns=spalten, show="headings", height=hoehe,
                        **({"selectmode": wahl} if wahl else {}))
    zb = zeichen_breite(rahmen.winfo_toplevel())
    platz = rahmen.winfo_width() if rahmen.winfo_width() > 2 else 0
    breiten = dict(spaltenbreiten(spalten, kopf, _als_liste(spalten, wunsch),
                                  texte, zeichen_breite=zb,
                                  verfuegbar=platz))
    # Die Wunschliste am Baum merken: `_breiten_nachrechnen` rechnet ohne
    # Fenster und braucht dieselbe Rangfolge, sonst faellt sie auf
    # SPALTEN_VORGABE zurueck und verliert die Absicht des Aufrufers.
    baum._wunsch = list(_als_liste(spalten, wunsch))
    for sp in spalten:
        baum.heading(sp, text=kopf.get(sp, sp))
        baum.column(sp, width=breiten.get(sp, 110),
                    stretch=False,
                    anchor="w" if sp in anker_w else "e")
    laenger = ttk.Scrollbar(rahmen, orient="vertical", command=baum.yview)
    breiter = ttk.Scrollbar(rahmen, orient="horizontal", command=baum.xview)
    baum.configure(yscrollcommand=laenger.set, xscrollcommand=breiter.set)
    breiter.pack(side="bottom", fill="x")
    laenger.pack(side="right", fill="y")
    baum.pack(side="left", fill="both", expand=True)
    baum.tag_configure("schlecht", foreground=FARBEN["rot"])
    baum.tag_configure("gut", foreground=FARBEN["gruen"])
    rad_selbst(baum)
    return baum


class Handelszentrale:
    """Tk-Fenster ueber alle Spuren. Liest nur, schreibt nichts."""

    def __init__(self, root):
        self.root = root
        self.q_kurse = queue.Queue()
        self.q_kerzen = queue.Queue()
        self.kurse = {}            # (spur, kurs_schluessel) -> Kurs
        self.positionen = []       # zuletzt gelesene, normalisierte Positionen
        self.zustaende = {}
        self.wachen = {}
        self.fenster = {}
        self.kerzen = {}
        self.chart_wahl = None     # (spur, schluessel, position)
        self._pos_id = {}          # Tabellenzeile -> Position
        self._kurs_laeuft = False
        self._kerzen_wunsch = None
        self._schrift_widgets = [] # (widget, rel, fett) fuer die Schrift-Option
        self.q_freqtrade = queue.Queue()
        self.ft_lage = None        # letzte freqtrade_bridge.lage(), None = noch nie
        self.ft_bot = None         # Name des Bots, dessen Details gezeigt werden
        self._ft_laeuft = False
        # Breiten werden nach dem ERSTEN Befuellen nachgerechnet - beim Bauen
        # steht in den Tabellen noch nichts (siehe _breiten_nachrechnen).
        self._breiten_gesetzt = False
        self._breiten_durchgang = 0     # wie oft nachgerechnet wurde
        self._breiten_stand_alt = ()    # Zeilenzahl des vorigen Durchgangs
        self._breiten_platz_gewusst = False  # hatte der Baum schon eine Breite?
        self._wunsch_spuren = []        # von _baue gesetzt
        self._wunsch_pos = []
        if isinstance(root, tk.Tk):
            # Allein gestartet gehoert das Fenster der Zentrale; als Reiter
            # im Leitstand gehoeren Titel, Groesse und Lage dem Leitstand.
            root.title("Handelszentrale — %d Spuren (Papier, nur lesend)"
                       % len(SPUREN))
            root.configure(bg=FARBEN["bg"])
            root.geometry("1280x860")
            root.minsize(1000, 640)
        self._baue()
        if isinstance(root, tk.Tk):
            self._buero_im_bild()
        self.refresh()
        root.after(REFRESH_MS, self._planer)

    def _buero_im_bild(self):
        """Einmalig: Fenster zurueckholen, wenn es ausserhalb liegt.

        Nach dem Abziehen eines Monitors startet Tk das Fenster mit der alten
        (negativen) Position und es ist unsichtbar, obwohl es laeuft. Der
        Bildschirm des Python-Prozesses ist dann der einzige Beleg - die
        Fenstersystem-Abfrage beantwortet die Position erst nach einem
        Update-Zyklus, deshalb hier `update_idletasks`.
        """
        try:
            self.root.update_idletasks()
            x, y = self.root.winfo_x(), self.root.winfo_y()
            breite = self.root.winfo_screenwidth()
            hoehe = self.root.winfo_screenheight()
            # Rand von 60 Pixeln: ein Fenster, das nur einen Strich zeigt,
            # ist genauso unbenutzbar wie eines ganz draussen.
            if (x + self.root.winfo_width() < 60 or y + self.root.winfo_height() < 60
                    or x > breite - 60 or y > hoehe - 60):
                self.root.geometry("+80+60")
        except Exception:                                    # noqa: BLE001
            pass          # kein Fensterdienst: Position nicht beantwortbar

    def _stufe_gewaehlt(self, _event=None):
        """Umschalter: RISIKO umsetzen und die Ansicht neu lesen."""
        global RISIKO
        wahl = self.w_stufe.get()
        RISIKO = None if wahl == BASIS_NAME else wahl
        self.refresh()

    def _schrift_gewaehlt(self, _event=None):
        """Schrift-Option: Basisgroesse umsetzen und neu anwenden."""
        global SCHRIFT_GROESSE
        wahl = self.w_schrift.get()
        try:
            SCHRIFT_GROESSE = int(wahl)
        except (TypeError, ValueError):
            return
        self._wende_schrift_an()

    def _registriere_schrift(self, widget, rel=0, fett=False):
        """Ein Widget fuer die Schrift-Option merken und sofort setzen."""
        widget.configure(font=schrift(rel, fett))
        self._schrift_widgets.append((widget, rel, fett))

    def _wende_schrift_an(self):
        """Neue Schriftgroesse an allen gemerkten Widgets anwenden."""
        design.stil_anwenden(ttk.Style(), SCHRIFT_GROESSE)
        for widget, rel, fett in self._schrift_widgets:
            try:
                widget.configure(font=schrift(rel, fett))
            except Exception:                                # noqa: BLE001
                pass
        self._zeichne_chart()
        self._schreibe_konsole(datetime.now(UTC))

    # ---------- Aufbau ----------
    def _baue(self):
        design.stil_anwenden(ttk.Style(), SCHRIFT_GROESSE)

        kopf = tk.Frame(self.root, bg=FARBEN["bg"])
        kopf.pack(fill="x", padx=10, pady=(8, 2))
        t_kopf = tk.Label(kopf, text="HANDELSZENTRALE", bg=FARBEN["bg"],
                          fg=FARBEN["akzent"])
        self._registriere_schrift(t_kopf, TITEL, fett=True)
        t_kopf.pack(side="left")
        self.l_dauerlauf = tk.Label(kopf, bg=FARBEN["bg"])
        self._registriere_schrift(self.l_dauerlauf, 0, fett=True)
        self.l_dauerlauf.pack(side="left", padx=(16, 0))
        self.l_takt = tk.Label(kopf, bg=FARBEN["bg"], fg=FARBEN["matt"])
        self._registriere_schrift(self.l_takt)
        self.l_takt.pack(side="right")
        # Umschalter Basis/mittel/hoch: eine Ansicht, zwei Buecher. Ohne ihn
        # waere der zweite Lauf in dieser GUI unsichtbar, obwohl er laeuft.
        self.w_stufe = ttk.Combobox(kopf, values=STUFEN_AUSWAHL, width=8,
                                    state="readonly")
        self.w_stufe.set(RISIKO or BASIS_NAME)
        self.w_stufe.pack(side="left", padx=(16, 0))
        self.w_stufe.bind("<<ComboboxSelected>>", self._stufe_gewaehlt)
        # Schrift-Option: 8-16 pt, sofort wirksam. Reine Anzeige-Einstellung,
        # wird bewusst NICHT gespeichert (die Zentrale schreibt nichts).
        t_schrift = tk.Label(kopf, text="Schrift:", bg=FARBEN["bg"],
                             fg=FARBEN["matt"])
        self._registriere_schrift(t_schrift, KLEIN)
        t_schrift.pack(side="left", padx=(16, 0))
        self.w_schrift = ttk.Combobox(kopf, values=SCHRIFT_AUSWAHL, width=3,
                                      state="readonly")
        self.w_schrift.set(str(SCHRIFT_GROESSE))
        self.w_schrift.pack(side="left", padx=(4, 0))
        self.w_schrift.bind("<<ComboboxSelected>>", self._schrift_gewaehlt)
        self.l_konto = tk.Label(kopf, bg=FARBEN["bg"], fg=FARBEN["matt"],
                                text="Kraken-Konto: …")
        self._registriere_schrift(self.l_konto)
        self.l_konto.pack(side="left", padx=(16, 0))

        # --- Reiter: "Spuren" traegt die bisherige Ansicht, "FreqTrade" den
        # lokalen Bot (freqtrade_bridge, nur lesend). Fusszeile bleibt am
        # Fenster, damit sie in beiden Reitern steht.
        #
        # Die Spuren-Seite ist eine SCROLLFLAECHE: Spurtabelle, Positionstabelle,
        # Chart und Konsole zusammen sind hoeher als jedes Fenster (die Tabelle
        # allein hatte 42 Zeilen), und ohne Leiste war der untere Teil des
        # Fensters nicht zu erreichen.
        self.reiter = ttk.Notebook(self.root)
        self.seite_wrapper, seite, self.seite_canvas = scrollbare_seite(self.reiter)
        self.reiter.add(self.seite_wrapper, text="Spuren")
        self._baue_freqtrade()
        self._baue_omnitrade()

        # --- Spurtabelle
        t_spur_label = tk.Label(seite, text="Spuren", bg=FARBEN["bg"],
                                fg=FARBEN["akzent"], anchor="w")
        self._registriere_schrift(t_spur_label, 0, fett=True)
        t_spur_label.pack(fill="x", padx=10)
        r1 = tk.Frame(seite, bg=FARBEN["blatt"])
        r1.pack(fill="x", padx=10)
        # Die Spalten kommen aus EINER Quelle (05.10.2026): stand die Liste
        # zweimal in der Datei, waere eine Erweiterung an der einen Stelle
        # wirkungslos - ohne Fehlermeldung, weil ttk.Treeview ein Tuple zu
        # kurz einfach abschneidet.
        sp_spur = spalten_der_spurtabelle()
        kopf_s = SPUREN_KOPF
        wunsch_s = list(SPUREN_WUNSCH)
        # Zeilenweise Vorgabe statt `height=len(SPUREN)`: die Tabelle hatte
        # 42 Zeilen und damit eine angeforderte Hoehe ueber jedem Fenster -
        # die letzten Spuren waren unerreichbar. Zwolf Zeilen plus Leiste:
        # alles bleibt lesbar, die Seite scrolliert.
        self.t_spuren = tabelle_mit_leiste(r1, sp_spur, kopf_s, wunsch_s,
                                           hoehe=min(len(SPUREN), 12),
                                           anker_w=("spur", "modus", "fenster",
                                                    "herzschlag", "handel"))

        # --- Positionstabelle
        t_pos_label = tk.Label(seite,
                               text="Offene Positionen (Zeile anklicken = Chart)",
                               bg=FARBEN["bg"], fg=FARBEN["akzent"], anchor="w")
        self._registriere_schrift(t_pos_label, 0, fett=True)
        t_pos_label.pack(fill="x", padx=10, pady=(6, 0))
        r2 = tk.Frame(seite, bg=FARBEN["blatt"])
        r2.pack(fill="x", padx=10)
        sp_pos = ("spur", "instrument", "seite", "einstieg", "kurs", "stop",
                  "ziel", "abstand", "wert", "gv")
        kopf_p = {"spur": "Spur", "instrument": "Instrument", "seite": "Seite",
                  "einstieg": "Einstieg", "kurs": "Kurs", "stop": "Stop",
                  "ziel": "Ziel", "abstand": "Abstand", "wert": "Wert",
                  "gv": "G/V %"}
        # Reihenfolge nach Wichtigkeit: Instrument, dann die Zahlenspalten.
        wunsch_p = [90, 210, 60, 90, 90, 90, 90, 80, 110, 80]
        self.t_pos = tabelle_mit_leiste(r2, sp_pos, kopf_p, wunsch_p, hoehe=7,
                                        anker_w=("spur", "instrument", "seite"),
                                        wahl="browse")
        self.t_pos.bind("<<TreeviewSelect>>", self._gewaehlt)

        # --- Chart
        self.l_chart = tk.Label(seite, bg=FARBEN["bg"], fg=FARBEN["akzent"],
                                anchor="w", text="Chart")
        self._registriere_schrift(self.l_chart, 0, fett=True)
        self.l_chart.pack(fill="x", padx=10, pady=(6, 0))
        self.canvas = tk.Canvas(seite, bg=FARBEN["blatt"], height=260,
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10)
        self.canvas.bind("<Configure>", lambda _e: self._zeichne_chart())

        # --- Konsole
        t_konsole_label = tk.Label(seite,
                                   text="Konsole — letzte Buchungen und Dauerlauf",
                                   bg=FARBEN["bg"], fg=FARBEN["akzent"], anchor="w")
        self._registriere_schrift(t_konsole_label, 0, fett=True)
        t_konsole_label.pack(fill="x", padx=10, pady=(6, 0))
        r3 = tk.Frame(seite, bg=FARBEN["blatt"])
        r3.pack(fill="x", padx=10)
        self.konsole = tk.Text(r3, height=9, bg=FARBEN["blatt"],
                               fg=FARBEN["text"], font=schrift(KLEIN),
                               relief="flat", wrap="none")
        # Die Buchungszeilen sind lang (Spur, Instrument, Preis, Grund) und
        # `wrap="none"` schneidet sie ab - ohne horizontale Leiste war der
        # Rest der Zeile nicht zu lesen.
        sbq = ttk.Scrollbar(r3, orient="horizontal", command=self.konsole.xview)
        sb2 = ttk.Scrollbar(r3, orient="vertical", command=self.konsole.yview)
        self.konsole.configure(yscrollcommand=sb2.set, xscrollcommand=sbq.set,
                               state="disabled")
        sbq.pack(side="bottom", fill="x")
        self.konsole.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")
        rad_selbst(self.konsole, zeilen=2)
        self.konsole.tag_configure("matt", foreground=FARBEN["matt"])
        self.konsole.tag_configure("gut", foreground=FARBEN["gruen"])
        self.konsole.tag_configure("schlecht", foreground=FARBEN["rot"])
        self.konsole.tag_configure("kopf", foreground=FARBEN["akzent"])

        fuss = tk.Frame(self.root, bg=FARBEN["bg"])
        fuss.pack(side="bottom", fill="x", padx=10, pady=(4, 6))
        self.l_summe = tk.Label(fuss, bg=FARBEN["bg"])
        self._registriere_schrift(self.l_summe, 0, fett=True)
        self.l_summe.pack(side="left")
        t_fuss = tk.Label(fuss,
                          text="nur lesend — der Dauerlauf bleibt der einzige Schreiber",
                          bg=FARBEN["bg"], fg=FARBEN["matt"])
        self._registriere_schrift(t_fuss, KLEIN)
        t_fuss.pack(side="right")
        self.reiter.pack(fill="both", expand=True)
        # Das Mausrad fuer die Spuren-Seite - erst JETZT angelegt, wenn jeder
        # Rahmen unter ihr existiert; vorher haette der Rahmen unter dem Zeiger
        # keine Bindung und das Rad bliebe wirkungslos.
        self.seite = seite
        seite_mausrad(self.seite_canvas, seite)
        # Jede scrollende Seite braucht ihre Rad-Bindung: ein Radereignis
        # landet auf dem Widget unter dem Zeiger, nicht auf dem Canvas
        # dahinter. Ohne sie scrollen die beiden neuen Seiten nicht
        # (siehe die Erklaerung am Aufruf von scrollbare_seite).
        seite_mausrad(self._canvas_freqtrade, seite)
        # Scrollregion einmal SOFORT: kommt kein Configure-Ereignis (minimiert
        # gestartet, als Reiter im Leitstand gebaut), waere die Seite trotz
        # Inhalt nicht scrollbar. after_idle laesst den Aufbau erst fertig werden.
        self.root.after_idle(lambda: seite_region_neu(self.seite_canvas, seite))

    def _baue_freqtrade(self):
        """Reiter FreqTrade: alle Bots, dazu die Details des gewaehlten.

        Der Reiter zeigte bis 30.09.2026 EINEN Bot an der festen Adresse
        127.0.0.1:8080. Die drei FreqTrade-Bots laufen aber auf 8081-8083 und
        8080 antwortete nicht (gemessen) - der Reiter war taub, waehrend drei
        Bots liefen. Die Bot-Liste kommt aus `freqtrade/bots.json`, derselben
        Tabelle, die `bots.py` zum Starten benutzt.
        """
        # Auch diese Seite scrollt: `scrollbare_seite` war nur am
        # Spuren-Reiter gebaut, die beiden anderen Seiten waren blanke
        # tk.Frame. Gemessen bei 1280x860: FreqTrade zeigte 121 px von
        # 336 px Inhalt, omnitrade 141 von 468 - Journal und Quellen-
        # angabe waren unerreichbar, ohne dass etwas darauf hinwies.
        self._wrapper_freqtrade, seite, self._canvas_freqtrade = scrollbare_seite(self.reiter)
        self.reiter.add(self._wrapper_freqtrade, text="FreqTrade")
        self.l_ft = tk.Label(seite, bg=FARBEN["bg"], anchor="w", justify="left",
                             text=freqtrade_kopf(None)[0], fg=FARBEN["matt"])
        self._registriere_schrift(self.l_ft, 0, fett=True)
        self.l_ft.pack(fill="x", padx=10, pady=(6, 2))

        # --- Uebersicht: jeder Bot eine Zeile, auch der tote ---
        t_ueber = tk.Label(seite, text="Alle Bots (Liste aus freqtrade/bots.json)",
                           bg=FARBEN["bg"], fg=FARBEN["akzent"], anchor="w")
        self._registriere_schrift(t_ueber, 0, fett=True)
        t_ueber.pack(fill="x", padx=10, pady=(6, 0))
        bs = ("name", "port", "strategie", "rahmen", "modus", "zustand",
              "offen", "trades", "gv", "meldung")
        bk = {"name": "Bot", "port": "Port", "strategie": "Strategie",
              "rahmen": "Rahmen", "modus": "Modus", "zustand": "Zustand",
              "offen": "offen/max", "trades": "Trades",
              "gv": "G/V geschlossen", "meldung": "Meldung"}
        r_ueber = tk.Frame(seite, bg=FARBEN["blatt"])
        r_ueber.pack(fill="x", padx=10)
        self.t_ft_bots = tabelle_mit_leiste(
            r_ueber, bs, bk,
            {**dict.fromkeys(bs, 95), "strategie": 170, "meldung": 260},
            hoehe=max(len(freqtrade_bridge.bots()), 3),
            anker_w=("name", "strategie", "modus", "zustand", "meldung"),
            wahl="browse")
        self.t_ft_bots.bind("<<TreeviewSelect>>", self._ft_bot_auswahl)

        # --- Umschalter, falls die Tabelle doch nicht angewählt wurde ---
        zeile = tk.Frame(seite, bg=FARBEN["bg"])
        zeile.pack(fill="x", padx=10, pady=(6, 0))
        t_bot = tk.Label(zeile, text="Details von:", bg=FARBEN["bg"],
                         fg=FARBEN["matt"], anchor="w")
        self._registriere_schrift(t_bot, KLEIN)
        t_bot.pack(side="left")
        self.w_ft_bot = ttk.Combobox(zeile, values=[], width=22, state="readonly")
        self.w_ft_bot.pack(side="left", padx=(6, 0))
        self.w_ft_bot.bind("<<ComboboxSelected>>", self._ft_bot_auswahl)

        tabellen = (
            ("t_ft_offen", "Offene Positionen",
             ("paar", "seite", "seit", "einstieg", "kurs", "einsatz", "gv"),
             {"paar": "Paar", "seite": "Seite", "seit": "Seit",
              "einstieg": "Einstieg", "kurs": "Kurs", "einsatz": "Einsatz",
              "gv": "G/V %"}, 8),
            ("t_ft_zu", "Letzte geschlossene Trades",
             ("paar", "auf", "zu", "gv", "gv_abs", "grund"),
             {"paar": "Paar", "auf": "Eröffnet", "zu": "Geschlossen",
              "gv": "G/V %", "gv_abs": "G/V", "grund": "Ausstieg"}, 14),
        )
        for attr, titel, spalten, kopf, hoehe in tabellen:
            t = tk.Label(seite, text=titel, bg=FARBEN["bg"],
                         fg=FARBEN["akzent"], anchor="w")
            self._registriere_schrift(t, 0, fett=True)
            t.pack(fill="x", padx=10, pady=(6, 0))
            rahmen = tk.Frame(seite, bg=FARBEN["blatt"])
            rahmen.pack(fill="both", expand=attr == "t_ft_zu", padx=10)
            setattr(self, attr, tabelle_mit_leiste(
                rahmen, spalten, kopf,
                {**dict.fromkeys(spalten, 110), "grund": 180}, hoehe=hoehe,
                anker_w=("paar", "seite", "seit", "auf", "zu", "grund"),
                dehnen="grund"))
            if attr == "t_ft_offen":
                t = tk.Label(seite, text="G/V je Tag (14 Tage)", bg=FARBEN["bg"],
                             fg=FARBEN["akzent"], anchor="w")
                self._registriere_schrift(t, 0, fett=True)
                t.pack(fill="x", padx=10, pady=(6, 0))
                self.c_ft = tk.Canvas(seite, bg=FARBEN["blatt"], height=140,
                                      highlightthickness=0)
                self.c_ft.pack(fill="x", padx=10)
                self.c_ft.bind("<Configure>", lambda _e: self._zeichne_ft_tage())
        self.ft_tage = []
        t_quelle = tk.Label(seite, bg=FARBEN["bg"], fg=FARBEN["matt"], anchor="w",
                            text="Quelle: FreqTrade-API je Bot aus %s "
                                 "(freqtrade_bridge, nur lesend; Anmeldung aus der "
                                 "Basis-config) — Start: Agenten/Handel/freqtrade/"
                                 "bots_starten.sh"
                                 % freqtrade_bridge.BOTS_KONFIG)
        self._registriere_schrift(t_quelle, KLEIN)
        t_quelle.pack(fill="x", padx=10, pady=(4, 0))

    def _baue_omnitrade(self):
        """Reiter omnitrade: Kopfzeile und letzte Order-Ereignisse aus der Statusdatei."""
        # Auch diese Seite scrollt: `scrollbare_seite` war nur am
        # Spuren-Reiter gebaut, die beiden anderen Seiten waren blanke
        # tk.Frame. Gemessen bei 1280x860: FreqTrade zeigte 121 px von
        # 336 px Inhalt, omnitrade 141 von 468 - Journal und Quellen-
        # angabe waren unerreichbar, ohne dass etwas darauf hinwies.
        self._wrapper_omnitrade, seite, self._canvas_omnitrade = scrollbare_seite(self.reiter)
        self.reiter.add(self._wrapper_omnitrade, text="omnitrade")
        self.l_omni = tk.Label(seite, bg=FARBEN["bg"], anchor="w", justify="left",
                               text=omnitrade_kopf(None)[0], fg=FARBEN["matt"])
        self._registriere_schrift(self.l_omni, 0, fett=True)
        self.l_omni.pack(fill="x", padx=10, pady=(6, 2))
        tl = tk.Label(seite, text="Laeufe (alle Statusdateien)", bg=FARBEN["bg"],
                      fg=FARBEN["akzent"], anchor="w")
        self._registriere_schrift(tl, 0, fett=True)
        tl.pack(fill="x", padx=10, pady=(6, 0))
        lspalten = ("strategie", "symbol", "laufzeit", "kerzen", "orders", "kv",
                    "gewinn", "buyhold", "zustand")
        lkopf = {"strategie": "Strategie", "symbol": "Symbol", "laufzeit": "Laufzeit",
                 "kerzen": "Kerzen", "orders": "Orders", "kv": "Kauf/Verk.",
                 "gewinn": "Gewinn", "buyhold": "Buy&Hold", "zustand": "Zustand"}
        r_laeufe = tk.Frame(seite, bg=FARBEN["blatt"])
        r_laeufe.pack(fill="x", padx=10)
        self.t_laeufe = tabelle_mit_leiste(
            r_laeufe, lspalten, lkopf,
            {**dict.fromkeys(lspalten, 100), "zustand": 150}, hoehe=6,
            anker_w=("strategie", "symbol", "zustand"))
        # --- Haus-Buch der SPUR (30.09.2026) --------------------------------
        # Getrennt von den Rust-Laeufen: sie spiegelt deren Position in ein
        # eigenes Buch, heisst aber genauso. Wer nur eine der beiden sieht,
        # haelt die Zahlen der anderen fuer seine.
        tb = tk.Label(seite, text="Haus-Buch der Spur (Spiegel, Papier/Live)",
                      bg=FARBEN["bg"], fg=FARBEN["akzent"], anchor="w")
        self._registriere_schrift(tb, 0, fett=True)
        tb.pack(fill="x", padx=10, pady=(8, 0))
        self.l_omni_spur = tk.Label(seite, bg=FARBEN["bg"], anchor="w",
                                    justify="left", text=omnitrade_spur_kopf(None, None)[0],
                                    fg=FARBEN["matt"])
        self._registriere_schrift(self.l_omni_spur, 0)
        self.l_omni_spur.pack(fill="x", padx=10)
        pspalten = ("instrument", "seite", "einstieg", "stop", "ziel", "nominal")
        pkopf = {"instrument": "Instrument", "seite": "Seite", "einstieg": "Einstieg",
                 "stop": "Stop", "ziel": "Ziel", "nominal": "Nominal"}
        r_pos = tk.Frame(seite, bg=FARBEN["blatt"])
        r_pos.pack(fill="x", padx=10)
        self.t_omni_pos = tabelle_mit_leiste(
            r_pos, pspalten, pkopf,
            dict.fromkeys(pspalten, 140), hoehe=4,
            anker_w=("instrument", "seite"), dehnen="instrument")
        jspalten = ("zeit", "modus", "aktion", "instrument", "preis", "grund")
        jkopf = {"zeit": "Zeit", "modus": "Modus", "aktion": "Aktion",
                 "instrument": "Instrument", "preis": "Preis", "grund": "Grund"}
        r_journal = tk.Frame(seite, bg=FARBEN["blatt"])
        r_journal.pack(fill="x", padx=10, pady=(2, 0))
        self.t_omni_journal = tabelle_mit_leiste(
            r_journal, jspalten, jkopf,
            {"zeit": 260}, hoehe=6,
            anker_w=("modus", "aktion", "instrument", "grund"))
        t = tk.Label(seite, text="Letzte Orders", bg=FARBEN["bg"],
                     fg=FARBEN["akzent"], anchor="w")
        self._registriere_schrift(t, 0, fett=True)
        t.pack(fill="x", padx=10, pady=(6, 0))
        rahmen = tk.Frame(seite, bg=FARBEN["blatt"])
        rahmen.pack(fill="both", expand=True, padx=10)
        spalten = ("zeit", "seite", "menge", "preis", "ergebnis", "meldung")
        kopf = {"zeit": "Zeit", "seite": "Seite", "menge": "Menge", "preis": "Preis",
                "ergebnis": "Ergebnis", "meldung": "Meldung"}
        seite_mausrad(self._canvas_omnitrade, seite)
        self.t_omni = tabelle_mit_leiste(
            rahmen, spalten, kopf,
            {"meldung": 320}, hoehe=20,
            anker_w=("zeit", "seite", "ergebnis", "meldung"), dehnen="meldung")
        t_quelle = tk.Label(seite, bg=FARBEN["bg"], fg=FARBEN["matt"], anchor="w",
                            text="Quelle: %s (omnitrade_bridge, nur lesend) — Start: "
                                 "omnitrade live --status-file … (Testnet)"
                                 % omnitrade_bridge.pfad())
        self._registriere_schrift(t_quelle, KLEIN)
        t_quelle.pack(fill="x", padx=10, pady=(4, 0))

    def _zeige_omnitrade(self, lage):
        text, marke = omnitrade_kopf(lage)
        self.l_omni.configure(text=text, fg=FARBEN[{"gut": "gruen", "schlecht": "rot"}.get(marke, marke)])
        # Haus-Buch der SPUR (30.09.2026): eigene Dateien, eigener Stand - die
        # Spur schreibt zustand.json und handelsjournal.csv, der Rust-Lauf die
        # Statusdatei. Beides steht in diesem Reiter, getrennt beschriftet.
        wachen = lade_json(os.path.join(HIER, "omnitrade", "wachen.json"))
        zustand = lade_json(os.path.join(HIER, "omnitrade", stufenname("zustand.json")))
        stext, smarke = omnitrade_spur_kopf(zustand, wachen)
        self.l_omni_spur.configure(
            text=stext, fg=FARBEN[{"gut": "gruen", "schlecht": "rot"}.get(smarke, smarke)])
        for i in self.t_omni_pos.get_children():
            self.t_omni_pos.delete(i)
        for werte in omnitrade_spur_positionen("omnitrade", zustand, wachen):
            self.t_omni_pos.insert("", "end", values=werte)
        for i in self.t_omni_journal.get_children():
            self.t_omni_journal.delete(i)
        for werte in omnitrade_spur_journal(
                os.path.join(HIER, "omnitrade", stufenname("handelsjournal.csv"))):
            marke_j = "gut" if werte[1] == "live" else ""
            self.t_omni_journal.insert("", "end", values=werte, tags=(marke_j,))
        for i in self.t_omni.get_children():
            self.t_omni.delete(i)
        for werte in omnitrade_order_zeilen(lage):
            marke = {"filled": "gut", "rejected": "schlecht"}.get(werte[4], "")
            self.t_omni.insert("", "end", values=werte, tags=(marke,))
        for i in self.t_laeufe.get_children():
            self.t_laeufe.delete(i)
        for werte, marke in omnitrade_laeufe_zeilen(omnitrade_auswertung.alle()):
            self.t_laeufe.insert("", "end", values=werte, tags=(marke,))

    def _starte_freqtrade_worker(self):
        """Nur EIN Abruf gleichzeitig; ein haengender Bot stapelt keine Threads.

        Der gewaehlte Botname wird mitgegeben - der worker antwortet immer
        (auch bei einer exception), damit die Sperre nicht fuer immer bleibt.
        """
        if self._ft_laeuft:
            return
        self._ft_laeuft = True
        threading.Thread(target=_freqtrade_im_thread,
                         args=(self.q_freqtrade, self.ft_bot),
                         daemon=True).start()

    def _ft_bot_auswahl(self, _event=None):
        """Zeile in der Bots-Tabelle oder Umschalter: Details DIESES Bots holen."""
        name = None
        try:
            sel = self.t_ft_bots.selection()
            if sel:
                name = str(self.t_ft_bots.item(sel[0], "values")[0])
            elif self.w_ft_bot.get():
                name = str(self.w_ft_bot.get())
        except Exception:                                    # noqa: BLE001
            return          # noch nichts gewaehlt: Ansicht bleibt stehen
        if not name or name == self.ft_bot:
            return
        self.ft_bot = name
        try:
            self.w_ft_bot.set(name)     # set() loest bewusst KEIN Signal aus
        except Exception:                # noqa: BLE001
            pass
        self._starte_freqtrade_worker()

    def _zeige_freqtrade(self, uebersicht, lage, offen, zu, tage=None):
        self.ft_lage = lage
        self.ft_tage = freqtrade_tagesbalken(tage)
        self._zeichne_ft_tage()
        # Uebersicht zuerst: sie ist die Wahrheit ueber ALLE Bots, die Kopf-
        # zeile beschreibt nur den gewaehlten.
        for i in self.t_ft_bots.get_children():
            self.t_ft_bots.delete(i)
        namen = []
        for werte, marke in freqtrade_uebersicht_zeilen(uebersicht):
            self.t_ft_bots.insert("", "end", values=werte, tags=(marke,))
            namen.append(werte[0])
        if namen:
            self.w_ft_bot.configure(values=namen)
            if self.ft_bot not in namen:
                self.ft_bot = namen[0]     # bots.json geaendert: neu anlehnen
            self.w_ft_bot.set(self.ft_bot)
        text, marke = freqtrade_kopf(lage, self.ft_bot)
        self.l_ft.configure(text=text, fg=FARBEN[{"gut": "gruen", "schlecht": "rot"}.get(marke, marke)])
        for baum in (self.t_ft_offen, self.t_ft_zu):
            for i in baum.get_children():
                baum.delete(i)
        for t in offen if isinstance(offen, list) else []:
            werte = freqtrade_offen_zeile(t)
            self.t_ft_offen.insert("", "end", values=werte,
                                   tags=(_gv_marke(werte[-1]),))
        for werte in freqtrade_zu_zeilen(zu):
            self.t_ft_zu.insert("", "end", values=werte,
                                tags=(_gv_marke(werte[3]),))

    def _zeichne_ft_tage(self):
        """Balken je Tag um die Nulllinie; gruen Gewinn, rot Verlust."""
        c = self.c_ft
        c.delete("all")
        breite, hoehe = max(c.winfo_width(), 420), max(c.winfo_height(), 120)
        rand_l, rand_r, rand_o, rand_u = 60, 20, 10, 18
        if not self.ft_tage:
            c.create_text(breite // 2, hoehe // 2, text="keine Tagesdaten",
                          fill=FARBEN["matt"], font=schrift())
            return
        groesste = max(abs(w) for _, w, _ in self.ft_tage) or 1.0
        mitte = rand_o + (hoehe - rand_o - rand_u) / 2
        halb = (hoehe - rand_o - rand_u) / 2
        c.create_line(rand_l, mitte, breite - rand_r, mitte, fill=FARBEN["gitter"])
        for ys, wert in ((rand_o, groesste), (mitte, 0.0), (hoehe - rand_u, -groesste)):
            c.create_text(rand_l - 4, ys, anchor="e", fill=FARBEN["matt"],
                          font=schrift(TINY), text="%+.2f" % wert)
        feld = (breite - rand_l - rand_r) / len(self.ft_tage)
        for i, (tag, wert, _) in enumerate(self.ft_tage):
            x0 = rand_l + feld * i + feld * 0.2
            x1 = rand_l + feld * (i + 1) - feld * 0.2
            yw = mitte - halb * wert / groesste
            farbe = FARBEN["gruen"] if wert >= 0 else FARBEN["rot"]
            c.create_rectangle(x0, min(mitte, yw), x1, max(mitte, yw) + (wert == 0),
                               fill=farbe, outline=farbe)
            c.create_text((x0 + x1) / 2, hoehe - rand_u + 2, anchor="n",
                          fill=FARBEN["matt"], font=schrift(TINY), text=tag)

    # ---------- Daten ----------
    def refresh(self):
        jetzt = datetime.now(UTC)
        self.positionen = []
        for spur in SPUREN:
            ordner = os.path.join(HIER, dauerlauf.SPUREN[spur].get("ordner", spur))
            # Das Zustandbuch DIESER Stufe, nicht still die Basis: die drei
            # Dauerlaeufe fahren dieselben Spuren in eigenen Dateien
            # (zustand.mittel.json, zustand.hoch.json). Bis 30.09.2026 las
            # refresh() hart "zustand.json" - die Spurtabelle, die
            # Positionstabelle und die Fuss-Summe zeigten in der Ansicht
            # "mittel"/"hoch" die Basis-Buecher, waehrend Konsole und
            # omnitrade-Haus-Buch ueber _pfad()/stufenname() laengst die
            # richtigen Dateien lasen. Zwei Lesarten, ein Fenster.
            z = lade_json(os.path.join(ordner, stufenname("zustand.json")))
            w = lade_json(os.path.join(ordner, "wachen.json"))
            z = mit_live_herzschlag(z, ordner)
            self.zustaende[spur] = z
            self.wachen[spur] = w
            try:
                self.fenster[spur] = freigabefenster.lade(spur)
            except Exception:                                # noqa: BLE001
                self.fenster[spur] = None
            self.positionen.extend(positionen_der_spur(spur, z, w))
        self._zeige(jetzt)
        self._starte_kurs_worker()
        self._starte_freqtrade_worker()
        self._zeige_omnitrade(omnitrade_bridge.lage())   # kleine lokale Datei, kein Thread noetig
        # Nachrechnen erst HIER: `_zeige_omnitrade` befuellt die Lauf-Tabelle
        # und liefert ihre Zeilen erst nach `_zeige`. Vorher gerechnet
        # enthaelt diese Tabelle nur ihre Ueberschriften - gemessen blieben
        # danach 6 Texte zu schmal (Gewinn-Spalte, "+506.83 (+101.37 %)").
        try:
            self._breiten_nachrechnen()
        except Exception as e:                       # noqa: BLE001
            # Breite ist Kosmetik, kein Grund den Takt zu stoppen - aber der
            # Fehler gehoert in die Konsole, sonst ist ein stiller Ausfall
            # nicht von einem Fenster zu unterscheiden, das nichts anzeigt.
            try:
                self.konsole.insert("end", "Breiten-Nachrechnung: %s\n" % e)
            except Exception:                        # noqa: BLE001
                pass

    def _pfad(self, spur, name):
        return os.path.join(HIER, dauerlauf.SPUREN[spur].get("ordner", spur),
                            stufenname(name))

    def _starte_kurs_worker(self):
        """Nur EIN Kurslauf gleichzeitig.

        Die Feed-Abfrage (Spiegel) laeuft ueber ein CLI und darf Sekunden
        brauchen. Ohne diese Sperre stapeln sich die Threads im
        Viertelminutentakt und das Fenster lebt von Altantworten.
        """
        if self._kurs_laeuft:
            return
        self._kurs_laeuft = True
        threading.Thread(target=self._kurs_worker,
                         args=(list(self.positionen),), daemon=True).start()

    def _kurs_worker(self, positionen):
        neu = {}
        okx_insts = sorted({p["kurs_schluessel"] for p in positionen
                            if p["quelle"] == "okx" and p["kurs_schluessel"]})
        kraken_paare = sorted({p["kurs_schluessel"] for p in positionen
                               if p["quelle"] == "kraken"
                               and p["kurs_schluessel"]})
        feed_punkte = sorted({(p["kette"], p["kurs_schluessel"])
                              for p in positionen
                              if p["quelle"] == "feed" and p["kette"]
                              and p["kurs_schluessel"]})
        if okx_insts:
            try:
                import okx
                for inst in okx_insts:
                    try:
                        neu[("okx", inst)] = okx.letzter_kurs(inst)
                    except Exception:                        # noqa: BLE001
                        pass
            except Exception:                                # noqa: BLE001
                pass
        if kraken_paare:
            try:
                import kraken
                for paar in kraken_paare:
                    try:
                        neu[("kraken", paar)] = kraken.letzter_kurs(paar)
                    except Exception:                        # noqa: BLE001
                        pass
            except Exception:                                # noqa: BLE001
                pass
        if feed_punkte:
            try:
                import lesen
                preise = lesen.preise(feed_punkte)
                for kette, token in feed_punkte:
                    kurs = preise.get((kette, token))
                    if kurs:
                        neu[("feed", token)] = kurs
            except Exception:                                # noqa: BLE001
                pass       # Feed nicht erreichbar -> alte Anzeige behalten
        # Der Schwung geht IMMER raus - auch wenn oben etwas geworfen haette.
        # Sonst bleibt die Sperre unten, weil kein Antwortstueck ankommt, und
        # die Zentrale holt nie wieder Kurse (derselbe Fall wie der
        # freqtrade-Worker, nur stiller).
        self.q_kurse.put(neu)

    def _planer(self):
        """Der 15-Sekunden-Takt: Antworten einsammeln, neu lesen, weiterplanen.

        Zwei Fallen, beide am 30.09.2026 gemessen bzw. behoben:
          * Die Kurs-Sperre wurde bisher BEDINGUNGSLOS zurueckgenommen. Ein
            Worker, der laenger als ein Takt braucht (Feed-CLI, Netzwaende),
            war damit beim naechsten Tick "fertig" - es startete ein zweiter,
            waehrend der erste noch lief. Genau das Stapeln von Threads, das
            `_starte_kurs_worker` laut seiner eigenen Doku verbietet, war
            also nie abgeschaltet. Jetzt gilt: die Sperre faellt erst mit der
            Antwort.
          * Ein Werfen im Einsammeln (ein kaputtes Antwortstueck, ein
            Ueberraschungsfehler im Anzeigeaufbau) brachte den Takt zum
            Schweigen - das Fenster lief weiter, aktualisierte aber nie
            wieder, ohne eine Spur davon zu hinterlassen. Der Neustart des
            Timers steht deshalb im `finally`.
        """
        try:
            antworten = False
            while True:
                self.kurse.update(self.q_kurse.get_nowait())
                antworten = True
        except queue.Empty:
            pass
        finally:
            if antworten:
                self._kurs_laeuft = False
        try:
            while True:
                spur, schluessel, kerzen, grund = self.q_kerzen.get_nowait()
                self.kerzen[(spur, schluessel)] = (kerzen, grund)
                self._kerzen_wunsch = None
        except queue.Empty:
            pass
        except Exception:                                    # noqa: BLE001
            self._kerzen_wunsch = None      # kaputtes Stueck: Wunsch freigeben
        try:
            while True:
                self._zeige_freqtrade(*self.q_freqtrade.get_nowait())
                self._ft_laeuft = False
        except queue.Empty:
            pass
        try:
            self.refresh()
        except Exception:                                    # noqa: BLE001
            pass          # ein Lesefehler darf den Takt nicht entlassen
        finally:
            self.root.after(REFRESH_MS, self._planer)

    # ---------- Chart ----------
    def _gewaehlt(self, _event=None):
        sel = self.t_pos.selection()
        if not sel:
            return
        p = self._pos_id.get(sel[0])
        if not p:
            return
        self.chart_wahl = (p["spur"], p["kurs_schluessel"], p)
        self._starte_kerzen_worker(p)

    def _starte_kerzen_worker(self, p):
        spur, schluessel = p["spur"], p["kurs_schluessel"]
        wunsch = (spur, schluessel)
        if not schluessel:
            self.kerzen[wunsch] = ([], "kein Kursweg fuer dieses Instrument")
            self._zeichne_chart()
            return
        if self._kerzen_wunsch == wunsch:
            return              # laeuft gerade
        self._kerzen_wunsch = wunsch
        self.l_chart.config(text="%s  —  lade Kerzen …" % p["instrument"])
        threading.Thread(target=self._kerzen_worker, args=(p,), daemon=True).start()

    def _kerzen_worker(self, p):
        spur, schluessel = p["spur"], p["kurs_schluessel"]
        kerzen, grund = [], None
        try:
            if p["quelle"] == "okx":
                import okx
                kerzen = [[int(r[0])] + [float(x) for x in r[1:6]]
                          for r in okx.kerzen(schluessel, bar="1D",
                                              anzahl=KERZEN_OKX)]
            elif p["quelle"] == "kraken":
                import kraken
                kerzen = kraken.kerzen(schluessel, intervall=15,
                                       anzahl=KERZEN_KRAKEN)
            else:
                grund = ("Feed-Instrument — fuer Token der Kette gibt es "
                         "keine OKX-/Kraken-Kerzen")
        except Exception as e:                               # noqa: BLE001
            grund = "Kurse nicht erreichbar (%s)" % str(e)[:60]
        self.q_kerzen.put((spur, schluessel, kerzen or [], grund))

    def _zeichne_chart(self):
        c = self.canvas
        c.delete("all")
        breite = max(c.winfo_width(), 420)
        hoehe = max(c.winfo_height(), 200)
        rand_l, rand_r, rand_o, rand_u = 60, 60, 10, 18

        if not self.chart_wahl:
            c.create_text(breite // 2, hoehe // 2,
                          text="Zeile in der Positionstabelle anklicken",
                          fill=FARBEN["matt"], font=schrift())
            return
        spur, schluessel, p = self.chart_wahl
        kerzen, grund = self.kerzen.get((spur, schluessel), ([], None))
        titel = "%s  %s  %s" % (spur, p["instrument"], p["seite"])
        if not kerzen:
            c.create_text(breite // 2, hoehe // 2,
                          text=grund or "keine Kerzen verfuegbar",
                          fill=FARBEN["matt"], font=schrift())
            self.l_chart.config(text=titel)
            return

        tief, hoch = chart_bereich(kerzen, [p["einstieg"], p["stop"], p["ziel"]])
        spanne = (hoch - tief) or 1.0

        def x(i):
            return rand_l + (breite - rand_l - rand_r) * (i + 0.5) / len(kerzen)

        def y(w):
            return rand_o + (hoehe - rand_o - rand_u) * (1 - (w - tief) / spanne)

        for s in range(5):
            ys = rand_o + (hoehe - rand_o - rand_u) * s / 4
            c.create_line(rand_l, ys, breite - rand_r, ys, fill=FARBEN["gitter"])
            c.create_text(rand_l - 4, ys, anchor="e", fill=FARBEN["matt"],
                          font=schrift(TINY),
                          text=kurs_fmt(hoch - spanne * s / 4))

        kbreite = max(1.5, (breite - rand_l - rand_r) / len(kerzen) * 0.6)
        for i, k in enumerate(kerzen):
            o, h, l, cl = k[1], k[2], k[3], k[4]
            farbe = FARBEN["zellgruen"] if cl >= o else FARBEN["zellrot"]
            c.create_line(x(i), y(l), x(i), y(h), fill=farbe)
            yo, yc = y(o), y(cl)
            if abs(yo - yc) < 1:
                yo = yc - 1
            c.create_rectangle(x(i) - kbreite, yo, x(i) + kbreite, yc,
                               fill=farbe, outline=farbe)

        for name, wert, farbe in (("Einstieg", p["einstieg"], FARBEN["akzent"]),
                                  ("Stop", p["stop"], FARBEN["rot"]),
                                  ("Ziel", p["ziel"], FARBEN["gruen"])):
            if not wert or not (tief <= wert <= hoch):
                continue
            ys = y(wert)
            c.create_line(rand_l, ys, breite - rand_r, ys, fill=farbe,
                          dash=(4, 3))
            c.create_text(breite - rand_r + 2, ys, anchor="w", fill=farbe,
                          font=schrift(TINY, fett=True), text=name)

        def tag_str(ms):
            try:
                return datetime.fromtimestamp(ms / 1000, UTC).astimezone(
                    ).strftime("%d.%m.")
            except Exception:                                # noqa: BLE001
                return "?"

        c.create_text(rand_l, hoehe - 4, anchor="w", fill=FARBEN["matt"],
                      font=schrift(TINY), text=tag_str(kerzen[0][0]))
        c.create_text(breite - rand_r, hoehe - 4, anchor="e", fill=FARBEN["matt"],
                      font=schrift(TINY), text=tag_str(kerzen[-1][0]))

        kurs = self.kurse.get((p["quelle"], schluessel))
        gv = gv_prozent(p["seite"], kurs, p["einstieg"])
        self.l_chart.config(text="%s   —   %d Kerzen, Einstieg %s, Stop %s, "
                                 "Ziel %s%s" % (
            titel, len(kerzen), kurs_fmt(p["einstieg"]), kurs_fmt(p["stop"]),
            kurs_fmt(p["ziel"]),
            "   G/V %+.1f %%" % gv if gv is not None else ""))

    # ---------- Anzeige ----------
    def _breiten_nachrechnen(self):
        """Nach dem Befuellen: Breiten gegen die ECHTEN Texte rechnen.

        Beim Bauen ist die Tabelle leer, es stehen nur die Ueberschriften
        drin - eine Breite, die nur danach rechnet, ist die alte feste
        Breite mit neuem Namen. Nach dem ersten `insert` sind die Texte
        da, und erst dann laesst sich die vraechtig lange Spalte finden.

        Nachrechnen erst, wenn die Tabellen GEFUELLT sind - und dann
        einmal mehr, wenn der Kurs-Takt neue Zeilen bringt. Ein einmaliges
        Rechnen nach dem ersten `insert` reicht nicht: gemessen bei Schrift
        13 waren danach noch 96 Texte zu schmal, weil zu diesem Zeitpunkt
        erst 8 von 96 Positionen und 3 von 47 Spuren gelesen waren.

        Die Regel: nachrechnen, solange die Zeilenzahl sich noch aendert -
        hoechstens FUENF Mal. Danach gehoeren die Breiten dem Nutzer (er kann
        eine Spalte mit der Maus ziehen); eine Aenderung an der Schrift
        setzt die Grenze ohnehin zurueck (`setze_schrift`).
        """
        # ALLE Tabellen, nicht nur drei: die FreqTrade-Uebersicht stand bei
        # Schrift 13 mit 113 px gegen 128 px Bedarf ("G/V geschlossen"),
        # weil sie nicht nachgerechnet wurde.
        nachrechnen = tuple(b for b in
                            (self.t_spuren, self.t_pos, self.t_laeufe,
                             self.t_ft_bots, self.t_ft_offen, self.t_ft_zu,
                             self.t_omni_pos, self.t_omni_journal, self.t_omni)
                            if b is not None)
        zaehler = tuple(len(b.get_children()) for b in nachrechnen)
        self._breiten_platz_gewusst = True
        if self._breiten_gesetzt:
            return
        # Der Zaehler wird VOR dem Rechnen geprueft, nicht danach: sonst
        # greift die Grenze im selben Takt, in dem der Nutzer gerade
        # gezogen hat, und seine Breite geht doch verloren (gemessen: der
        # 5. Durchgang setzte 600 px auf 200 px zurueck).
        if self._breiten_durchgang >= BREITEN_MAX_DURCHGAENGE:
            self._breiten_gesetzt = True
            return
        self._breiten_durchgang += 1
        wuensche = {id(self.t_spuren): self._wunsch_spuren,
                    id(self.t_pos): self._wunsch_pos}
        for baum in nachrechnen:
            wunsch = wuensche.get(id(baum)) or _as_liste_wunsch(baum)
            # Eine LEERE Tabelle wird trotzdem gerechnet - nach den
            # Ueberschriften. Vorher wurden leere Tabellen uebersprungen und
            # behielten ihre Bau-Breite; bei Schrift 16 blieben so drei
            # Ueberschriften abgeschnitten ("G/V geschlossen" 158 px gegen
            # 158 px Bedarf, "offen/max", "Geschlossen"). Eine Tabelle ohne
            # Zeilen zeigt genau die Ueberschriften, und die muessen passen.
            texte = {}
            for iid in baum.get_children():
                for sp, wert in zip(baum["columns"], baum.item(iid, "values")):
                    texte.setdefault(sp, []).append(wert)
            # Der Platz fuer die Kuerzung kommt aus dem Baum. Tk vermisst
            # ein neu gebautes oder noch verborgenes Widget erst nach einem
            # `update_idletasks` und meldet vorher 1 px - dann unterbleibt
            # die Kuerzung grundsaetzlich (gemessen: die Positionstabelle
            # blieb bei Schrift 13 um 114 px breiter als ihr Baum). Fuenf
            # Versuche mit einem `update_idletasks` dazwischen, weil der
            # ersten Durchlauf sonst genau diesen 1-px-Fall trifft.
            platz = 0
            for _ in range(5):
                platz = baum.winfo_width()
                if platz >= 100:
                    break
                try:
                    baum.update_idletasks()
                except Exception:                        # noqa: BLE001
                    break
                platz = baum.winfo_width()
            if platz < 100:
                self._breiten_platz_gewusst = False
                platz = baum.master.winfo_width()
                if platz < 100:
                    platz = 0
            breiten = dict(spaltenbreiten(
                list(baum["columns"]), kopf_von(baum), wunsch, texte,
                zeichen_breite=zeichen_breite(baum.winfo_toplevel()),
                verfuegbar=platz))
            for sp, b in breiten.items():
                baum.column(sp, width=b)
        # Fertig nach dem zweiten Durchgang, in dem sich die Zeilenzahlen
        # nicht mehr geaendert haben. Eine Tabelle darf leer bleiben (ein Bot
        # ohne Trades, eine Positionstabelle ohne Positionen) - mit der
        # Bedingung "alle Tabellen gefuellt" blieb die Nachrechnung bei
        # Schrift 13 nach EINEM Durchgang stehen und sechs Tabellen blieben
        # auf ihrer Bau-Breite (gemessen: "G/V geschlossen" 113 px statt
        # 128 px Bedarf).
        # Fertig erst, wenn die Breiten auch GERECHNET wurden - nicht nur
        # zweimal dieselbe Zeilenzahl gesehen. `platz == 0` heisst: der Baum
        # hatte noch keine Breite, es wurde nicht gekuerzt, und der Durchgang
        # zaehlt nicht als fertig.
        # Fertig, wenn die Zeilenzahl zweimal gleich war UND der Platz
        # bekannt war - ODER nach fuenf Durchgaengen. Die Grenze ist Pflicht,
        # nicht Kosmetik: `BREITEN_MAX_DURCHGAENGE` stand vorher als
        # Konstante im Baum und wurde nirgends gelesen, damit lief die
        # Nachrechnung bei jeder Aenderung der Zeilenzahl weiter. Gemessen:
        # nach 5+ Durchgaengen war `_breiten_gesetzt` noch False, und eine
        # von Hand auf 600 px gezogene Spalte stand nach EINEM `refresh()`
        # wieder auf 200 px. Ein Fenster, dessen Spaltenbreiten man nicht
        # einrichten kann, ist ein Monitor statt einer Arbeitsflaeche.
        if (self._breiten_durchgang >= BREITEN_MAX_DURCHGAENGE
                or (self._breiten_durchgang >= 2
                    and self._breiten_stand_alt == zaehler
                    and self._breiten_platz_gewusst)):
            self._breiten_gesetzt = True
        self._breiten_stand_alt = zaehler

    def _zeige(self, jetzt):
        # Spurtabelle
        for i in self.t_spuren.get_children():
            self.t_spuren.delete(i)
        for spur in SPUREN:
            stand = spur_stand(spur, self.zustaende[spur], self.wachen[spur],
                               self.fenster[spur], jetzt)
            marke = ()
            if stand["herzschlag"] == "ueberfaellig":
                marke = ("schlecht",)
            elif stand["herzschlag"] == "ok":
                marke = ("gut",)
            self.t_spuren.insert("", "end", values=spur_zeile(stand),
                                 tags=marke)

        # Positionstabelle
        for i in self.t_pos.get_children():
            self.t_pos.delete(i)
        self._pos_id = {}
        # Waehrung je Spur EINMAL holen (der Berichtsweg liest mit), nicht je
        # Position - bei 42 Spuren und mehreren hundert Zeilen ist das der
        # Unterschied zwischen einem Lesevorgang und vielen.
        waehrungen = {spur: waehrung_fuer(spur, self.zustaende.get(spur))
                      for spur in self.zustaende}
        for p in sorted(self.positionen,
                        key=lambda x: (x["spur"], x["instrument"], x["seite"])):
            kurs = self.kurse.get((p["quelle"], p["kurs_schluessel"]))
            abstand = abstand_prozent(p["seite"], kurs, p["stop"])
            gv = gv_prozent(p["seite"], kurs, p["einstieg"])
            marke = ()
            if abstand is not None and abstand < 0:
                marke = ("schlecht",)
            elif gv is not None and gv > 0:
                marke = ("gut",)
            # Die Zeilen-ID wird gemerkt: zwei Kopien desselben Tokens sind
            # zwei Positionen mit gleichem Namen - ueber den Namen waere nur
            # die erste anklickbar.
            iid = self.t_pos.insert("", "end", tags=marke, values=(
                p["spur"], p["instrument"], p["seite"],
                kurs_fmt(p["einstieg"]),
                kurs_fmt(kurs) if kurs else "-",
                kurs_fmt(p["stop"]), kurs_fmt(p["ziel"]),
                ("%+.1f %%" % abstand) if abstand is not None else "-",
                wert_anzeige(p["wert_usd"], waehrungen.get(p["spur"], "USD")),
                ("%+.1f" % gv) if gv is not None else "-",
            ))
            self._pos_id[iid] = p

        # Fuss: offene Positionen und ihr Nominal - nach Waehrung getrennt,
        # denn EUR und USD in einer Summe ist kein Betrag, den jemand ausgeben
        # koennte (und "Nominal 562 USD" fuer ein 150-EUR-Buch war falsch).
        gruppen = nominal_gruppen(self.positionen, self.zustaende)
        self.l_summe.config(text="%d offene Positionen   |   Nominal %s"
                                 % (len(self.positionen),
                                    "   ".join("%s %.0f (%d)" % (w, s, n)
                                               for w, s, n in gruppen)
                                    or "0"))

        # Kopf: Dauerlauf DIESER Stufe
        pid_pfad, log_pfad = dauerlauf_dateien()
        pid = None
        try:
            with open(pid_pfad, encoding="ascii") as f:
                pid = int((f.read() or "0").strip() or 0)
        except Exception:                                    # noqa: BLE001
            pid = None
        lebt = prozess_lebt(pid)
        text, alt = dauerlauf_stand(log_pfad, jetzt)
        stufe = ("Stufe %s" % RISIKO) if RISIKO else BASIS_NAME
        lage = "%s   |   " % stufe
        lage += ("PID %s %s" % (pid, "laeuft" if lebt else "lebt nicht")
                 if pid else "keine PID-Datei")
        if alt is not None:
            lage += "   |   letzter Zyklus vor %.0f min" % alt
        elif text:
            lage += "   |   letzter Eintrag %s" % text
        farbe = FARBEN["gruen"] if (lebt and alt is not None and alt <= 30) \
            else FARBEN["rot"]
        self.l_dauerlauf.config(text=lage, fg=farbe)
        self.l_takt.config(text="Refresh alle %ds   |   %s"
                                % (REFRESH_MS // 1000,
                                   jetzt.astimezone().strftime("%d.%m. %H:%M:%S")))
        konto_text, konto_warn = kraken_konto_lage()
        self.l_konto.config(text=konto_text,
                            fg=FARBEN["rot"] if konto_warn else FARBEN["matt"])

        # Konsole
        self._schreibe_konsole(jetzt)
        self._zeichne_chart()

    def _schreibe_konsole(self, jetzt):
        k = self.konsole
        k.configure(state="normal")
        k.delete("1.0", "end")

        ereignisse = []
        for spur in SPUREN:
            ereignisse.extend(journal_ereignisse(
                spur, self._pfad(spur, "handelsjournal.csv"), 3))
        ereignisse.sort(key=lambda e: e["zeit"], reverse=True)
        k.insert("end", "letzte Buchungen (alle Spuren)\n", "kopf")
        if not ereignisse:
            k.insert("end", "  keine Buchungen vorhanden\n", "matt")
        for e in ereignisse[:len(SPUREN) * 2]:
            gv = ereignis_gv(e)
            marke = "matt" if gv is None else ("gut" if gv >= 0 else "schlecht")
            k.insert("end", "  " + ereignis_zeile(e) + "\n", marke)

        k.insert("end", "\n%s\n" % os.path.basename(dauerlauf_dateien()[1]),
                 "kopf")
        # Der Schwanz, nicht die ganze Datei (siehe log_ende).
        zeilen = log_ende(dauerlauf_dateien()[1], 12)
        if not zeilen:
            k.insert("end", "  nicht lesbar\n", "matt")
        for z in zeilen:
            z = z.rstrip("\r\n")
            marke = log_marke(z)
            if marke:
                k.insert("end", "  " + z + "\n", marke)
            else:
                k.insert("end", "  " + z + "\n")

        k.configure(state="disabled")


# --------------------------------------------------------------------------
# Ohne Fenster: die Bindungen gegen die echten Dateien pruefen
# --------------------------------------------------------------------------

def pruefe(jetzt=None):
    """Gibt zurueck, was das Fenster zeigen wuerde - zum Nachlesen im Log."""
    jetzt = jetzt or datetime.now(UTC)
    aus = ["Spuren aus dauerlauf.SPUREN: %s" % ", ".join(SPUREN)]
    text, alt = dauerlauf_stand(dauerlauf_dateien()[1], jetzt)
    pid = None
    try:
        with open(dauerlauf_dateien()[0], encoding="ascii") as f:
            pid = int((f.read() or "0").strip() or 0)
    except Exception:                                        # noqa: BLE001
        pid = None
    aus.append("Ansicht: %s (Dateien %s)"
               % (RISIKO or BASIS_NAME, stufenname("zustand.json")))
    aus.append("Dauerlauf: PID %s, lebt %s, letzter Log-Eintrag %s (%.0f min)"
               % (pid, prozess_lebt(pid), text, alt if alt is not None else -1))
    for spur in SPUREN:
        ordner = os.path.join(HIER, dauerlauf.SPUREN[spur].get("ordner", spur))
        z = lade_json(os.path.join(ordner, stufenname("zustand.json")))
        w = lade_json(os.path.join(ordner, "wachen.json"))
        try:
            f = freigabefenster.lade(spur)
        except Exception:                                    # noqa: BLE001
            f = None
        stand = spur_stand(spur, z, w, f, jetzt)
        aus.append("  %-9s %s" % (spur, "  ".join(spur_zeile(stand))))
        for p in positionen_der_spur(spur, z, w):
            aus.append("      %-24s %-5s Einstieg %-12s Stop %-12s Ziel %-12s"
                       " Quelle %s (%s)"
                       % (p["instrument"], p["seite"], kurs_fmt(p["einstieg"]),
                          kurs_fmt(p["stop"]), kurs_fmt(p["ziel"]),
                          p["quelle"], p["kurs_schluessel"] or "kein Kursweg"))
        for e in journal_ereignisse(spur, os.path.join(
                ordner, stufenname("handelsjournal.csv")), 2):
            aus.append("      Journal: %s" % ereignis_zeile(e))

    # FreqTrade: der Reiter zeigt die Bots aus bots.json - ohne diese Zeilen
    # waere die Bindung nur im Fenster nachsehbar. Kurze Zeitgrenze, denn ein
    # stehender Container antwortet sofort (Verbindung abgelehnt), nur ein
    # schwarzes Loch wuerde die volle Zeit brauchen.
    bots_liste = freqtrade_bridge.bots()
    aus.append("FreqTrade-Bots aus %s: %d"
               % (freqtrade_bridge.BOTS_KONFIG, len(bots_liste)))
    for werte, _marke in freqtrade_uebersicht_zeilen(
            freqtrade_bridge.uebersicht(zeitgrenze=2, bot_liste=bots_liste)):
        aus.append("  %-18s Port %-6s %-22s %-4s %-13s Zustand %-8s "
                   "offen %-8s Trades %-4s G/V %-10s %s"
                   % tuple(list(werte[:9]) + [werte[9] or ""]))
    return aus


def _topmost_weg(root):
    """Topmost-Status sicher zuruecknehmen.

    Das Fenster kann schon geschlossen sein, wenn der Timer auslaeuft - dann
    ist der Tcl-Interpreter weg und jede Attribute-Abfrage wuerde mit
    `TclError` scheitern. Der Callback bleibt deshalb rein defensiv.
    """
    try:
        if getattr(root, "winfo_exists", lambda: False)():
            root.attributes("-topmost", False)
    except Exception:                                        # noqa: BLE001
        pass


def nach_vorn(root):
    """Das Fenster einmal nach vorn holen.

    Wird die Ansicht nicht von Hand gestartet, sondern von einem Skript oder
    der Anmelde-Routine, entsteht ein Fenster ohne Vordergrundrecht: es ist
    offen (`IsWindowVisible` true), steht aber hinter allem anderen - und sieht
    damit aus, als waere es gar nicht da. Ein kurzer Topmost-Impuls plus
    `focus_force` holt es sichtbar heraus; danach faellt topmost wieder weg,
    sonst waere es ein Fenster, das sich nicht wegklicken laesst.
    """
    try:
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(700, _topmost_weg, root)
        root.focus_force()
    except Exception:                                        # noqa: BLE001
        pass          # kein Fenstermanager-Recht: unschaedlich


def main():
    global RISIKO, SCHRIFT_GROESSE
    ap = argparse.ArgumentParser(description="Handelszentrale (nur lesend)")
    ap.add_argument("--pruefen", action="store_true",
                    help="nur ausgeben, was das Fenster zeigen wuerde")
    ap.add_argument("--risiko", choices=sorted(risikostufe.FAKTOREN),
                    default=risikostufe.STANDARD,
                    help="Buecher dieser Risikostufe zeigen (Vorgabe %s = "
                         "Basis). Die Stufe laeuft als eigener Dauerlauf mit "
                         "eigenen Dateien - siehe risikostufe.py."
                         % risikostufe.STANDARD)
    ap.add_argument("--schrift", type=int, default=SCHRIFT_GROESSE,
                    choices=range(8, 17),
                    help="Schriftgroesse in pt (Vorgabe %d)" % SCHRIFT_GROESSE)
    args = ap.parse_args()
    RISIKO = (None if args.risiko == risikostufe.STANDARD
              else args.risiko)
    SCHRIFT_GROESSE = args.schrift
    if args.pruefen:
        for zeile in pruefe():
            print(zeile)
        return
    # `dpi_bewusst()` statt `tk scaling 1.1` (Auftrag Max, 05.10.2026).
    # Gemessen: der Monitor ist 120 dpi, ein dpi-unawares Fenster sieht
    # 3072x1728 statt 3840x2160 - 36 % weniger Bildschirm, und Windows
    # stretcht das fertige Bitmap, wodurch jede Schrift weich wird.
    #
    # Wichtig: der Aufruf muss VOR dem ersten `Tk()` laufen, und `tk
    # scaling` entfaellt. Beides zusammen ergibt 1.666 statt 1.25
    # (gemessen) - der alte Aufruf war ein Ersatz fuer genau das, was der
    # Windows-Aufruf jetzt macht.
    design.dpi_bewusst()
    root = tk.Tk()
    Handelszentrale(root)
    nach_vorn(root)
    root.mainloop()


if __name__ == "__main__":
    main()
