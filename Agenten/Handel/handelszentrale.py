"""Handelszentrale - eine Ansicht ueber alle Spuren in Handel/.

Das Gegenstueck zur omnitrade-Oberflaeche (omnitrade-ui): dort Chart,
Orderbuch, Positionen und Konsole in einem Fenster - hier dieselben vier
Dinge, aber ueber alle sieben Papierspuren statt ueber eine Engine.

Rein lesend
-----------
Gelesen werden je Spur `zustand.json`, `wachen.json` und
`handelsjournal.csv`, dazu `dauerlauf.log`, `dauerlauf.pid` und
`freigabe_fenster.json`. Kurse und Kerzen kommen aus `scanner/okx` (OKX),
`kraken/kraken.py` (Kraken) bzw. `spiegel/lesen.py` (Onchain-Feed) - alles in
Hintergrund-Threads, damit das Netz die Oberflaeche nie blockiert. Dazu liest
die Kopfzeile den echten Kraken-Kontostand (ZEUR, 60-s-Cache, rein lesend)
und warnt rot, sobald er unter das Mindestguthaben der Spur faellt.
Geschrieben wird NICHTS: der Dauerlauf bleibt der einzige Schreiber.
`tests/test_handelszentrale_rein_lesend.py` verbietet Schreibzugriffe per
AST-Pruefung.

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
import freqtrade_bridge                                     # noqa: E402
import omnitrade_bridge                                     # noqa: E402

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
    """Dateiname in der Stufe dieser Ansicht (Basis: unveraendert)."""
    if not RISIKO:
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
          "kopier": "feed", "kopier1zu1": "feed"}
QUELLE_VORGABE = "okx"

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
            p["kurs_schluessel"] = p.get("token")
        else:
            # `schluessel` ist die generische Lesart aus positionen_aus()
            # (inst ODER paar ODER token). Vorher stand hier roh["inst"] - die
            # Kraken-Spur fuehrt ihr Instrument als `paar`, der Kursweg blieb
            # deshalb None und ihr Chart lief ins Leere.
            p["kurs_schluessel"] = p["schluessel"]
    return aus


def kurs_fmt(wert):
    """Genauigkeit passend zur Preisgroesse: 0.05697 -> 5, 2471 -> 1."""
    w = _zahl(wert)
    if w is None:
        return "-"
    if w >= 1000:
        return "%.1f" % w
    if w >= 10:
        return "%.2f" % w
    if w >= 1:
        return "%.3f" % w
    return "%.5f" % w


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


def spur_zeile(stand):
    """Die Zellen der Spurtabelle, in Spaltenreihenfolge."""
    erlaubt = stand["handel_erlaubt"]
    return (
        stand["spur"],
        stand["modus"],
        stand["fenster"],
        stand["stand"],
        str(stand["positionen"]),
        stand["herzschlag"],
        ("ja" if erlaubt else "nein") if erlaubt is not None else "?",
    )


def spur_zeile(stand):
    """Die Zellen der Spurtabelle, in Spaltenreihenfolge."""
    erlaubt = stand["handel_erlaubt"]
    return (
        stand["spur"],
        stand["modus"],
        stand["fenster"],
        stand["stand"],
        str(stand["positionen"]),
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


def dauerlauf_stand(pfad, jetzt):
    """Letzter Eintrag im Dauerlauf-Log als (Text, Minuten seitdem).

    Der Zeitstempel im Log hat kein Jahr. Liegt die gelesene Zeit mehr als
    einen Tag in der Zukunft, gehoert sie zum Vorjahr - sonst liest sich ein
    Altbestand als Zukunft.
    """
    letzte = None
    try:
        with open(pfad, encoding="utf-8", errors="replace") as f:
            for zeile in f:
                if len(zeile) >= 15 and zeile[:2].isdigit():
                    letzte = zeile
    except Exception:                                        # noqa: BLE001
        return (None, None)
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


def freqtrade_kopf(lage):
    """(Text, Marke) der Kopfzeile im FreqTrade-Reiter aus `freqtrade_bridge.lage()`."""
    if not lage:
        return "FreqTrade: wird abgefragt …", "matt"
    if not lage.get("erreichbar"):
        return "⚠ FreqTrade nicht erreichbar — %s" % lage.get("fehler", "?"), "schlecht"
    modus = "Probebetrieb" if lage.get("dry_run") else "LIVE"
    text = ("FreqTrade %s · %s · %s · %s %s   Guthaben %.2f %s   offen %d   "
            "Trades %d   G/V geschlossen %+.2f   gesamt %+.2f"
            % (modus, lage.get("zustand"), lage.get("boerse"),
               lage.get("strategie"), lage.get("zeitrahmen"),
               _zahl(lage.get("guthaben")) or 0.0, lage.get("waehrung"),
               lage.get("offene_trades", 0), lage.get("trades_gesamt", 0),
               _zahl(lage.get("gewinn_geschlossen")) or 0.0,
               _zahl(lage.get("gewinn_gesamt")) or 0.0))
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


def _freqtrade_im_thread(ziel):
    """Lage, offene und letzte Trades - im Hintergrund, wirft nie."""
    lage = freqtrade_bridge.lage()
    offen, zu, tage = [], {}, {}
    if lage.get("erreichbar"):
        try:
            offen = freqtrade_bridge.offene_trades()
            zu = freqtrade_bridge.trades(100)
            tage = freqtrade_bridge.tagesbilanz(14)
        except Exception:                                    # noqa: BLE001
            pass      # Lage steht schon; Tabellen bleiben dann leer
    ziel.put((lage, offen, zu, tage))


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
        self._ft_laeuft = False
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
        self.reiter = ttk.Notebook(self.root)
        seite = tk.Frame(self.reiter, bg=FARBEN["bg"])
        self.reiter.add(seite, text="Spuren")
        self._baue_freqtrade()
        self._baue_omnitrade()

        # --- Spurtabelle
        t_spur_label = tk.Label(seite, text="Spuren", bg=FARBEN["bg"],
                                fg=FARBEN["akzent"], anchor="w")
        self._registriere_schrift(t_spur_label, 0, fett=True)
        t_spur_label.pack(fill="x", padx=10)
        r1 = tk.Frame(seite, bg=FARBEN["blatt"])
        r1.pack(fill="x", padx=10)
        sp_spur = ("spur", "modus", "fenster", "stand", "pos", "herzschlag",
                   "handel")
        kopf_s = {"spur": "Spur", "modus": "Modus", "fenster": "Fenster",
                  "stand": "Stand", "pos": "Pos", "herzschlag": "Herzschlag",
                  "handel": "handel_erlaubt"}
        breit_s = {"spur": 110, "modus": 80, "fenster": 190, "stand": 90,
                   "pos": 50, "herzschlag": 130, "handel": 120}
        self.t_spuren = ttk.Treeview(r1, columns=sp_spur, show="headings",
                                     height=len(SPUREN))
        for s in sp_spur:
            self.t_spuren.heading(s, text=kopf_s[s])
            self.t_spuren.column(s, width=breit_s[s],
                                 anchor="w" if s in ("spur", "modus", "fenster",
                                                     "herzschlag", "handel")
                                 else "e")
        self.t_spuren.pack(fill="x")
        self.t_spuren.tag_configure("schlecht", foreground=FARBEN["rot"])
        self.t_spuren.tag_configure("gut", foreground=FARBEN["gruen"])

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
                  "ziel": "Ziel", "abstand": "Abstand", "wert": "Wert USD",
                  "gv": "G/V %"}
        breit_p = {"spur": 90, "instrument": 210, "seite": 60, "einstieg": 90,
                   "kurs": 90, "stop": 90, "ziel": 90, "abstand": 80,
                   "wert": 90, "gv": 80}
        self.t_pos = ttk.Treeview(r2, columns=sp_pos, show="headings",
                                  height=7, selectmode="browse")
        for s in sp_pos:
            self.t_pos.heading(s, text=kopf_p[s])
            self.t_pos.column(s, width=breit_p[s],
                              stretch=s == "instrument",
                              anchor="w" if s in ("spur", "instrument", "seite")
                              else "e")
        sb = ttk.Scrollbar(r2, orient="vertical", command=self.t_pos.yview)
        self.t_pos.configure(yscrollcommand=sb.set)
        self.t_pos.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.t_pos.tag_configure("schlecht", foreground=FARBEN["rot"])
        self.t_pos.tag_configure("gut", foreground=FARBEN["gruen"])
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
        sb2 = ttk.Scrollbar(r3, orient="vertical", command=self.konsole.yview)
        self.konsole.configure(yscrollcommand=sb2.set, state="disabled")
        self.konsole.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")
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

    def _baue_freqtrade(self):
        """Reiter FreqTrade: Kopfzeile, offene Positionen, letzte Trades."""
        seite = tk.Frame(self.reiter, bg=FARBEN["bg"])
        self.reiter.add(seite, text="FreqTrade")
        self.l_ft = tk.Label(seite, bg=FARBEN["bg"], anchor="w",
                             text=freqtrade_kopf(None)[0], fg=FARBEN["matt"])
        self._registriere_schrift(self.l_ft, 0, fett=True)
        self.l_ft.pack(fill="x", padx=10, pady=(6, 2))
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
            baum = ttk.Treeview(rahmen, columns=spalten, show="headings",
                                height=hoehe)
            for sp in spalten:
                baum.heading(sp, text=kopf[sp])
                baum.column(sp, width=180 if sp == "grund" else 110,
                            anchor="w" if sp in ("paar", "seite", "seit", "auf",
                                                 "zu", "grund") else "e")
            leiste = ttk.Scrollbar(rahmen, orient="vertical", command=baum.yview)
            baum.configure(yscrollcommand=leiste.set)
            baum.pack(side="left", fill="both", expand=True)
            leiste.pack(side="right", fill="y")
            baum.tag_configure("schlecht", foreground=FARBEN["rot"])
            baum.tag_configure("gut", foreground=FARBEN["gruen"])
            setattr(self, attr, baum)
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
                            text="Quelle: FreqTrade-API %s (freqtrade_bridge, "
                                 "nur lesend) — Start: Agenten/Handel/freqtrade/start.sh"
                                 % freqtrade_bridge.URL)
        self._registriere_schrift(t_quelle, KLEIN)
        t_quelle.pack(fill="x", padx=10, pady=(4, 0))

    def _baue_omnitrade(self):
        """Reiter omnitrade: Kopfzeile und letzte Order-Ereignisse aus der Statusdatei."""
        seite = tk.Frame(self.reiter, bg=FARBEN["bg"])
        self.reiter.add(seite, text="omnitrade")
        self.l_omni = tk.Label(seite, bg=FARBEN["bg"], anchor="w", justify="left",
                               text=omnitrade_kopf(None)[0], fg=FARBEN["matt"])
        self._registriere_schrift(self.l_omni, 0, fett=True)
        self.l_omni.pack(fill="x", padx=10, pady=(6, 2))
        t = tk.Label(seite, text="Letzte Orders", bg=FARBEN["bg"],
                     fg=FARBEN["akzent"], anchor="w")
        self._registriere_schrift(t, 0, fett=True)
        t.pack(fill="x", padx=10, pady=(6, 0))
        rahmen = tk.Frame(seite, bg=FARBEN["blatt"])
        rahmen.pack(fill="both", expand=True, padx=10)
        spalten = ("zeit", "seite", "menge", "preis", "ergebnis", "meldung")
        kopf = {"zeit": "Zeit", "seite": "Seite", "menge": "Menge", "preis": "Preis",
                "ergebnis": "Ergebnis", "meldung": "Meldung"}
        self.t_omni = ttk.Treeview(rahmen, columns=spalten, show="headings", height=20)
        for sp in spalten:
            self.t_omni.heading(sp, text=kopf[sp])
            self.t_omni.column(sp, width=320 if sp == "meldung" else 110,
                               anchor="e" if sp in ("menge", "preis") else "w")
        leiste = ttk.Scrollbar(rahmen, orient="vertical", command=self.t_omni.yview)
        self.t_omni.configure(yscrollcommand=leiste.set)
        self.t_omni.pack(side="left", fill="both", expand=True)
        leiste.pack(side="right", fill="y")
        self.t_omni.tag_configure("schlecht", foreground=FARBEN["rot"])
        self.t_omni.tag_configure("gut", foreground=FARBEN["gruen"])
        t_quelle = tk.Label(seite, bg=FARBEN["bg"], fg=FARBEN["matt"], anchor="w",
                            text="Quelle: %s (omnitrade_bridge, nur lesend) — Start: "
                                 "omnitrade live --status-file … (Testnet)"
                                 % omnitrade_bridge.pfad())
        self._registriere_schrift(t_quelle, KLEIN)
        t_quelle.pack(fill="x", padx=10, pady=(4, 0))

    def _zeige_omnitrade(self, lage):
        text, marke = omnitrade_kopf(lage)
        self.l_omni.configure(text=text, fg=FARBEN[{"gut": "gruen", "schlecht": "rot"}.get(marke, marke)])
        for i in self.t_omni.get_children():
            self.t_omni.delete(i)
        for werte in omnitrade_order_zeilen(lage):
            marke = {"filled": "gut", "rejected": "schlecht"}.get(werte[4], "")
            self.t_omni.insert("", "end", values=werte, tags=(marke,))

    def _starte_freqtrade_worker(self):
        """Nur EIN Abruf gleichzeitig; ein haengender Bot stapelt keine Threads."""
        if self._ft_laeuft:
            return
        self._ft_laeuft = True
        threading.Thread(target=_freqtrade_im_thread, args=(self.q_freqtrade,),
                         daemon=True).start()

    def _zeige_freqtrade(self, lage, offen, zu, tage=None):
        self.ft_lage = lage
        self.ft_tage = freqtrade_tagesbalken(tage)
        self._zeichne_ft_tage()
        text, marke = freqtrade_kopf(lage)
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
            z = lade_json(os.path.join(ordner, "zustand.json"))
            w = lade_json(os.path.join(ordner, "wachen.json"))
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
        feed_punkte = sorted({(p["kette"], p["token"]) for p in positionen
                              if p["quelle"] == "feed" and p["token"]})
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
        self.q_kurse.put(neu)

    def _planer(self):
        try:
            while True:
                self.kurse.update(self.q_kurse.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                spur, schluessel, kerzen, grund = self.q_kerzen.get_nowait()
                self.kerzen[(spur, schluessel)] = (kerzen, grund)
                self._kerzen_wunsch = None
        except queue.Empty:
            pass
        try:
            while True:
                self._zeige_freqtrade(*self.q_freqtrade.get_nowait())
                self._ft_laeuft = False
        except queue.Empty:
            pass
        self._kurs_laeuft = False
        self.refresh()
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
                ("%.0f" % p["wert_usd"]) if p["wert_usd"] else "-",
                ("%+.1f" % gv) if gv is not None else "-",
            ))
            self._pos_id[iid] = p

        # Fuss: offene Positionen und ihr Nominal
        summe = sum(p["wert_usd"] or 0.0 for p in self.positionen)
        self.l_summe.config(text="%d offene Positionen   |   Nominal %.0f USD"
                                 % (len(self.positionen), summe))

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
        log = dauerlauf_dateien()[1]
        try:
            with open(log, encoding="utf-8", errors="replace") as f:
                zeilen = f.readlines()[-12:]
        except Exception:                                    # noqa: BLE001
            zeilen = []
        if not zeilen:
            k.insert("end", "  nicht lesbar\n", "matt")
        for z in zeilen:
            z = z.rstrip("\r\n")
            marke = "matt" if " ok" in z else "schlecht"
            k.insert("end", "  " + z + "\n", marke)

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
                          p["quelle"], p["kurs_schluessel"]))
        for e in journal_ereignisse(spur, os.path.join(
                ordner, stufenname("handelsjournal.csv")), 2):
            aus.append("      Journal: %s" % ereignis_zeile(e))
    return aus


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
        root.after(700, lambda: root.attributes("-topmost", False))
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
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.1)
    except Exception:                                        # noqa: BLE001
        pass
    Handelszentrale(root)
    nach_vorn(root)
    root.mainloop()


if __name__ == "__main__":
    main()
