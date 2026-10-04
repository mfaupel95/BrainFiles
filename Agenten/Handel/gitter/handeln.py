"""Die Gitter-Spur: ein Papier-Grid auf OKX-Stundenkerzen.

Angelegt am 13.09.2026 auf Max' Anweisung, nachdem die Grid-Strategie im
Nautilus-Backtest stand ("Soll das Grid als Papierspur in den Dauerlauf?").
Der Backtest (`nautilus/backtest_grid.py`) ist die Messung an der
Vergangenheit; diese Spur ist dasselbe Gitter im laufenden Betrieb - mit
echten Kursen, ohne echtes Geld.

WAS SIE IST
-----------
Ein statisches Gitter zwischen einer unteren und einer oberen Grenze. Die
Grenzen entstehen EINMAL aus dem ersten gesehenen Kurs (+/- spanne_prozent)
und werden danach nie verschoben - ein Gitter, das seiner Spanne nachzieht,
waere eine andere Strategie. Auf jeder Stufe ausser der obersten liegt eine
Kauforder; ist eine Stufe gefuellt, liegt eine Stufe hoeher der Verkauf fuer
genau diese Menge. Der Gewinn eines Zyklus ist der Stufenabstand minus beide
Kostensaetze.

WAS SIE NICHT IST
-----------------
Kein Orderpfad. Kein Broker-Aufruf, keine Position am Markt. `--live`
verweigert mit genau einem Grund, in dem das Wort Freigabefenster NICHT
vorkommt - so fragt der Dauerlauf keine Freigabe an, die nichts oeffnen kann
(Muster: spiegel, omniquant, nautilus - papierfest).

GLEICHE WAHRHEIT
----------------
Die Stufenformel wird nicht neu erfunden: sie kommt aus `Handel/grid.py`
(`stufen_bauen`) - eine Rechnung, zwei Aufrufer. Preise und Mengen werden auf
das Raster der Boerse gerundet (tickSz/lotSz aus dem Instrument), damit das
Papierbuch dieselben Zahlen benutzt, die eine echte Order haette.

DIE KERZEN-REGEL (wichtig fuer jede Zahl, die hier herauskommt)
---------------------------------------------------------------
Je abgeschlossener Kerze:

  1. Kaeufe zuerst: eine Stufe kauft, wenn das TIEF die Stufe beruehrt.
  2. Verkaeufe danach: ein Los verkauft, wenn das HOCH den Verkaufspreis
     beruehrt - aber nur, wenn das Los schon VOR dieser Kerze lag. Was in
     dieser Kerze gekauft wurde, verkauft fruehestens in der naechsten.
  3. Am Ende der Kerze wird neu armiert: freie Stufen unter dem Schlusskurs
     bekommen eine Kauforder.

Innerhalb einer Kerze ist der Kursweg unbekannt. Diese Regel ist die
vorsichtige: sie erfindet keinen Zyklus, der in derselben Stunde begonnen und
beendet worden waere. Der Backtest arbeitet genauso (Order aus Kerze N wirkt
ab Kerze N+1) - die Spur ist damit keine zweite Rechnung, sondern derselbe
Gedanke auf laufenden Daten.

Die laufende (noch nicht abgeschlossene) Kerze wird verworfen: ein Hoch, das
noch steigen kann, ist keine Ausfuehrung.

Aufruf:
    python handeln.py --vorschau    # Lage und Sperren, schreibt nichts
    python handeln.py --papier      # ein Zyklus mit Journal und Kopie
    python handeln.py --wachen      # Grenzen als Momentaufnahme
    python handeln.py --live        # verweigert, nennt den Grund
"""

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HIER, HANDEL, os.path.join(HANDEL, "scanner"),
          os.path.join(HANDEL, os.pardir, "Bus")):
    if p not in sys.path:
        sys.path.insert(0, p)

import ereignis                                            # noqa: E402
import okx                                                 # noqa: E402
import wachen_pruefung as wp                               # noqa: E402

# Eine Rechnung, zwei Aufrufer: die Stufen kommen aus dem Gitter-Simulator
# des Handelsordners (Kraken-Forschungswerkzeug), nicht aus einer zweiten
# Formel hier. `grid.py` laeuft absichtlich ohne Netz und ohne Orderpfad.
from grid import stufen_bauen                              # noqa: E402

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

WACHEN = os.path.join(HIER, "wachen.json")
ZUSTAND = risikostufe.datei(os.path.join(HIER, "zustand.json"))
JOURNAL = risikostufe.datei(os.path.join(HIER, "handelsjournal.csv"))

SPALTEN = ["zeit", "modus", "aktion", "inst", "stufe", "preis", "menge",
           "einsatz_usd", "wert_usd", "gw_usd", "kasse_usd", "buchwert_usd",
           "bestand_menge", "letzter_kurs", "grund"]

# Ob geschrieben wird. Die Vorschau stellt das ab (siehe journal()).
SCHREIBEN = True

# --- Test-Seams -------------------------------------------------------------
# None -> echte Quelle. Tests setzen Lambda/Liste und stellen in tearDown
# zurueck (Mechanik wie kerzen_quelle bei den anderen Spuren).
kerzen_quelle = None           # f(inst, takt, anzahl) -> [[ts,o,h,l,c,vol], ...]
letzter_kurs_quelle = None     # f(inst) -> float
instrument_quelle = None       # f(inst) -> dict(tickSz, lotSz, minSz)

TAKTE_MS = {"1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
            "30m": 1_800_000, "1H": 3_600_000, "2H": 7_200_000,
            "4H": 14_400_000, "6H": 21_600_000, "12H": 43_200_000,
            "1D": 86_400_000}


def _jetzt():
    return datetime.now(timezone.utc)


def _zeit():
    return _jetzt().isoformat(timespec="seconds")


def _heute():
    return _jetzt().date().isoformat()


def lade_wachen():
    with open(WACHEN, encoding="utf-8") as f:
        return risikostufe.skaliere(json.load(f))


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
    return atomar.lade_json(ZUSTAND, lambda: {})


def schreibe_zustand(z):
    z["letzter_lauf"] = _zeit()
    z["positionen"] = positionen_aus(z)      # abgeleitet, nie von Hand gefuellt
    z["buchwert_usd"] = round(buchwert(z), 2)
    atomar.schreibe_json(ZUSTAND, z)


def journal(**felder):
    if not SCHREIBEN:
        return
    neu = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=SPALTEN, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in SPALTEN})


def journal_anlegen():
    """Die Journaldatei mit Kopfzeile anlegen, auch ohne Buchung.

    Zwei Gruende: die Kopie ausser Haus vergleicht DATEIEN - eine fehlende
    Datei liest sich in der Pruefung wie ein Unterschied, obwohl beide Seiten
    nichts haben. Und der Auswerter (buchauswertung) liest eine Datei; ein
    leeres Journal mit Kopfzeile ist eine Aussage ("noch kein Zyklus"), eine
    fehlende nicht.
    """
    if not SCHREIBEN or os.path.exists(JOURNAL):
        return
    with open(JOURNAL, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=SPALTEN).writeheader()


# --- Raster und Rechnung ----------------------------------------------------

def takt_ms(takt):
    if takt not in TAKTE_MS:
        raise ValueError("unbekannter Kerzentakt %r - erlaubt: %s"
                         % (takt, ", ".join(TAKTE_MS)))
    return TAKTE_MS[takt]


def raster(wert, schritt, abrunden=False):
    """Auf das Raster der Boerse runden (tickSz/lotSz).

    Ueber Decimal: 78236.4 / 0.1 ist in Gleitkomma 782364.0000000001, und
    eine Stufe, die eine Zehntausendstel daneben liegt, ist keine Order mehr.
    """
    if schritt <= 0:
        raise ValueError("Rasterschritt muss groesser 0 sein")
    d = Decimal(str(wert)) / Decimal(str(schritt))
    d = d.to_integral_value(rounding=ROUND_DOWN if abrunden else ROUND_HALF_UP)
    return float(d * Decimal(str(schritt)))


def leiter_bauen(kurs, w, inst_daten):
    """Stufen, Mengen und Startzustand - die Grenzen entstehen EINMAL.

    Rueckgabe: dict mit unten/oben/preise/mengen/zustand und den Zahlen, die
    der Bericht braucht (Schrittweite, gebundenes Kapital, zu kleine Stufen).
    """
    spanne = float(w.get("spanne_prozent", 20.0)) / 100.0
    stufen = int(w.get("stufen", 12))
    einsatz = float(w.get("einsatz_usd", 1000.0))
    unten = raster(kurs * (1 - spanne), inst_daten["tickSz"])
    oben = raster(kurs * (1 + spanne), inst_daten["tickSz"])
    preise = [raster(p, inst_daten["tickSz"])
              for p in stufen_bauen(unten, oben, stufen,
                                    bool(w.get("geometrisch", True)))]
    # Zwei Stufen koennen nach dem Runden zusammenfallen (Abstand < tickSz).
    # Dann faellt die obere weg - eine Stufe ohne eigenen Preis ist keine.
    eindeutig = []
    for p in preise:
        if not eindeutig or p > eindeutig[-1]:
            eindeutig.append(p)
    if len(eindeutig) < 3:
        raise ValueError("Spanne zu eng fuer %d Stufen bei tickSz %g"
                         % (stufen, inst_daten["tickSz"]))
    preise = eindeutig

    nominal = einsatz / (len(preise) - 1)
    mengen = []
    for p in preise[:-1]:                       # oberste Stufe kauft nie
        menge = raster(nominal / p, inst_daten["lotSz"], abrunden=True)
        mengen.append(menge if menge >= inst_daten["minSz"] else 0.0)
    return {
        "unten": preise[0], "oben": preise[-1], "stufen": len(preise),
        "preise": preise, "mengen": mengen,
        "zustand": ["frei"] * (len(preise) - 1),
        "schritt_prozent": (preise[1] / preise[0] - 1) * 100,
        "einsatz_in_orders": sum(m * p for m, p in zip(mengen, preise[:-1])),
        "stufen_ohne_menge": sum(1 for m in mengen if m <= 0),
    }


def kostenfaktoren(w):
    """(kauf, verkauf) - beide Kostensaetze, beide Seiten.

    Gebuehr und Slippage getrennt und nacheinander: beim Kauf wird teurer
    gekauft und zusaetzlich Gebuehr faellig, beim Verkauf billiger verkauft
    und wieder Gebuehr. Ein Faktor fuer beide Seiten waere die halbe Rechnung.
    """
    g = float(w.get("gebuehr_pct", 0.0)) / 100.0
    s = float(w.get("slippage_pct", 0.0)) / 100.0
    return (1.0 + s) * (1.0 + g), (1.0 - s) * (1.0 - g)


def buchwert(z, kurs=None):
    """Kasse + Bestand zum letzten Kurs."""
    if not z:
        return 0.0
    k = kurs if kurs is not None else z.get("letzter_kurs")
    if k is None:
        k = z.get("anker_preis", 0.0)
    return float(z.get("kasse_usd", 0.0)) + sum(
        los["menge"] * float(k) for los in (z.get("lose") or {}).values())


def positionen_aus(z):
    """Die offenen Gitterstufen in der Form, die Bus und Fenster lesen.

    Nur eine Quelle der Wahrheit: die Lose. `positionen` ist die Ableitung -
    wird sie von Hand gefuellt, sagen Zustand und Anzeige Verschiedenes.
    Die Felder sind die Schnittstelle von handel_befehle/handelszentrale:
    inst, seite, einstieg, menge, nominal, ziel, eroeffnet.
    """
    leiter = z.get("leiter") or {}
    preise = leiter.get("preise") or []
    aus = []
    for schluessel, los in sorted((z.get("lose") or {}).items(),
                                  key=lambda kv: int(kv[0])):
        i = int(schluessel)
        ziel = preise[i + 1] if i + 1 < len(preise) else None
        aus.append({
            "inst": z.get("instrument"),
            "seite": "long",
            "stufe": i,
            "einstieg": los["einstieg"],
            "menge": los["menge"],
            "nominal": round(los["kosten"], 2),
            "ziel": ziel,
            "eroeffnet": los.get("eroeffnet"),
            # Kein hebel-Feld: ein Spot-Gitter hat keinen Hebel. Eine 1 dort
            # waere eine Aussage ueber Margin, die es nicht gibt.
        })
    return aus


# --- Der Lauf ueber die Kerzen ----------------------------------------------

def abgeschlossene(kerzen, takt, jetzt=None):
    """Nur fertige Kerzen. Die laufende Stunde hat kein Ergebnis.

    OKX liefert die noch laufende Kerze als neueste mit; ein Hoch, das noch
    steigen kann, ist keine Ausfuehrung und ein Schlusskurs gibt es noch nicht.
    """
    jetzt_ms = int((jetzt or _jetzt()).timestamp() * 1000)
    dauer = takt_ms(takt)
    return [k for k in kerzen if int(k[0]) + dauer <= jetzt_ms]


def arme(z, kurs):
    """Freie Kaufstufen unter dem Kurs mit einer Order belegen.

    Kauforders ueber dem Markt waeren getarnte Marketorders und wuerden den
    Einsatz in einer Kerze verbrauchen - dieselbe Wache wie im Backtest
    (`nur_unter_kurs`).
    """
    leiter = z["leiter"]
    for i, preis in enumerate(leiter["preise"][:-1]):
        if leiter["zustand"][i] != "frei" or leiter["mengen"][i] <= 0:
            continue
        if preis < kurs:
            leiter["zustand"][i] = "armiert"


def _kauf(z, i, preis, w, fkauf, zeilen, zahlen):
    menge = z["leiter"]["mengen"][i]
    brutto = menge * preis
    kosten = brutto * fkauf
    if kosten > z["kasse_usd"] + 1e-9:
        zeilen.append("  Stufe %d (%.2f) nicht gekauft: Kasse %.2f < %.2f"
                      % (i, preis, z["kasse_usd"], kosten))
        return False
    z["kasse_usd"] -= kosten
    z["bestand"] = z.get("bestand", 0.0) + menge
    z["lose"][str(i)] = {"menge": menge, "einstieg": preis, "brutto": brutto,
                         "kosten": kosten, "eroeffnet": _heute()}
    # NOTAUS UNTER DER GITTERUNTERKANTE (04.10.2026, Auftrag Max "Gitter stop").
    #
    # Dieser Notaus wird beim KAUF gesetzt und nicht von Hand in zustand.json
    # geschrieben: gitter schreibt den Zustand bei jedem Zyklus neu, ein
    # eingetragener Stop ist beim naechsten Schreiben weg. Genau das ist am
    # 04.10. passiert - der Stop stand um 01:00 im Zustand, um 01:11 schrieb
    # der Dauerlauf darueber, und die Position stand ab da wieder schutzlos.
    #
    # WARUM SO TIEF: das Gitter kauft bei der Stufe ueber dieser nach. Ein Stop
    # ueber der naechsten Kaufstufe wuerde feuern, BEVOR das Gitter kaufen
    # kann - das waere kein Schutz, sondern eine Behauptung. Der Notaus liegt
    # deshalb EINE Stufe unter der untersten Leiterstufe: dort ist die Leiter
    # zu Ende und die Voraussetzung des Gitters stirbt. Er ersetzt keinen
    # Ziel-Ausstieg und wird nie durch ihn ausgeloest.
    if w.get("notaus_unter_gitterunterkante") and not z.get("_notaus"):
        unterste = min((s for s in z["leiter"].get("preise") or [None] if s),
                       default=None)
        schritt = (z["leiter"].get("schritt_prozent") or 0.0) / 100.0
        if unterste and schritt:
            z["_notaus"] = round(unterste * (1.0 - schritt), 6)
            zeilen.append("  NOTAUS gesetzt: %.2f (eine Stufe unter der "
                          "Gitterunterkante %.2f)" % (z["_notaus"], unterste))
    z["leiter"]["zustand"][i] = "gekauft"
    z["kaeufe"] += 1
    zahlen["kaeufe"] += 1
    zahlen["neu_gekauft"].add(i)
    zeilen.append("  KAUF Stufe %d @ %.4f, %g %s = %.2f %s"
                  % (i, preis, menge, str(z.get("instrument", "")).split("-")[0],
                     brutto, w.get("waehrung", "USDT")))
    journal(zeit=_zeit(), modus=z.get("modus"), aktion="KAUF",
            inst=z.get("instrument"), stufe=i, preis=preis, menge=menge,
            einsatz_usd=round(brutto, 4), kasse_usd=round(z["kasse_usd"], 4),
            bestand_menge=z["bestand"], letzter_kurs=z.get("letzter_kurs"),
            grund="Stufe %d" % i)
    return True


def _verkauf(z, i, preis, w, fverkauf, zeilen, zahlen):
    los = z["lose"][str(i)]
    menge = los["menge"]
    brutto = menge * preis
    erloes = brutto * fverkauf
    z["kasse_usd"] += erloes
    z["bestand"] = z.get("bestand", 0.0) - menge
    gw = erloes - los["kosten"]
    z["gw_usd"] = z.get("gw_usd", 0.0) + gw
    if gw < 0:
        z["verluste_usd"] = z.get("verluste_usd", 0.0) + (-gw)
    z["lose"].pop(str(i), None)
    z["leiter"]["zustand"][i] = "frei"
    z["verkaeufe"] += 1
    z["zyklen"] += 1
    zahlen["verkaeufe"] += 1
    zahlen["zyklen"] += 1
    zahlen["gw_usd"] += gw
    # Diese Zeile geht zeilenweise nach Telegram: Instrument, Stufe und
    # Ergebnis stehen drin, damit sie ohne die Zeilen davor lesbar ist.
    zeilen.append("  AUSSTIEG (verkauf) gitter %s Stufe %d -> %d @ %.4f, "
                  "Zyklus %+.2f %s"
                  % (z.get("instrument"), i, i + 1, preis, gw,
                     w.get("waehrung", "USDT")))
    journal(zeit=_zeit(), modus=z.get("modus"), aktion="AUSSTIEG",
            inst=z.get("instrument"), stufe=i, preis=preis, menge=menge,
            einsatz_usd=round(los["brutto"], 4), wert_usd=round(erloes, 4),
            gw_usd=round(gw, 4), kasse_usd=round(z["kasse_usd"], 4),
            bestand_menge=z["bestand"], letzter_kurs=z.get("letzter_kurs"),
            grund="Stufe %d -> %d" % (i, i + 1))
    return True


def walk(z, kerzen, w, takt):
    """Die Kerzen seit dem letzten Lauf nachziehen.

    Rueckgabe: (zeilen, zahlen). Die Zeilen sind der Bericht, die Zahlen die
    Kennzahlen des Zyklus - Tests pruefen beides, ohne dass gedruckt wird.
    """
    leiter = z["leiter"]
    fkauf, fverkauf = kostenfaktoren(w)
    kill = z.get("verluste_usd", 0.0) >= float(w.get("max_verlust_usd", 1e18))
    zeilen, zahlen = [], {"kaeufe": 0, "verkaeufe": 0, "zyklen": 0,
                          "gw_usd": 0.0, "kerzen": 0, "neu_gekauft": set()}
    grenze = z.get("letzte_kerze_ts") or 0

    for k in kerzen:
        ts, _, hoch, tief, schluss = (int(k[0]), float(k[1]), float(k[2]),
                                      float(k[3]), float(k[4]))
        if ts <= grenze:
            continue
        zahlen["kerzen"] += 1
        vorher = set(z["lose"])           # was schon lag, darf verkaufen

        # 1. Kaeufe zuerst (Tief beruehrt die Stufe)
        if not kill:
            for i, preis in enumerate(leiter["preise"][:-1]):
                if leiter["zustand"][i] != "armiert":
                    continue
                if tief <= preis:
                    _kauf(z, i, preis, w, fkauf, zeilen, zahlen)
        # 2. Verkaeufe danach (Hoch beruehrt den Verkaufspreis) - nur fuer
        #    Lose, die VOR dieser Kerze lagen.
        for i in sorted(int(s) for s in vorher):
            if str(i) not in z["lose"]:
                continue
            ziel = leiter["preise"][i + 1]
            if hoch >= ziel:
                _verkauf(z, i, ziel, w, fverkauf, zeilen, zahlen)

        # 3. Neu armieren am Schlusskurs dieser Kerze
        z["letzte_kerze_ts"] = ts
        z["letzter_kurs"] = schluss
        arme(z, schluss)

    z["bestand"] = sum(los["menge"] for los in z["lose"].values())
    return zeilen, zahlen


# --- Grenzen und Sperren ----------------------------------------------------

def sperren_live(w, z):
    """Gruende, warum --live nicht scharf schalten kann. Kein Freigabefenster.

    Das Wort "Freigabefenster" darf hier NICHT vorkommen: dauerlauf.
    nur_fenster_fehlt liest die Zeile und stellt nur dann eine Freigabe-
    Anfrage, wenn dort genau EIN Grund steht und dieser "Freigabefenster"
    enthaelt. Diese Spur hat keinen Live-Zweig - also keinen Grund, je zu
    fragen (Muster: spiegel, omniquant, nautilus).
    """
    g = []
    if not w.get("handel_erlaubt"):
        g.append("kein Live-Zweig: Gitter fuehrt ein Papierbuch auf "
                 "OKX-Kerzen (handel_erlaubt=false)")
    if z.get("verluste_usd", 0.0) >= float(w.get("max_verlust_usd", 1e18)):
        g.append("Kill-Switch: Verluste %.2f >= %g"
                 % (z.get("verluste_usd", 0.0), w.get("max_verlust_usd")))
    return g


def zeige_wachen(w):
    print("=== GITTER Wachen ===")
    for k in ("handel_erlaubt", "instrument", "waehrung", "spanne_prozent",
              "stufen", "geometrisch", "einsatz_usd", "gebuehr_pct",
              "slippage_pct", "max_verlust_usd", "kerzen_takt",
              "kerzen_anzahl", "herzschlag_max_minuten"):
        print("  %-26s %s" % (k, w.get(k)))
    f = w.get("freigabe") or {}
    print("  %-26s %s" % ("freigabe.erfuellt", f.get("erfuellt")))
    print("  %-26s %s (%s)" % ("  backtest_bestanden", f.get("backtest_bestanden"),
                               f.get("backtest_geprueft_am") or "-- keine Pruefung"))
    fk, fv = kostenfaktoren(w)
    print("  %-26s %.4f / %.4f (%.3f %% je Runde)"
          % ("Kostenfaktoren", fk, fv, (1 - fv / fk) * 100))
    z = lade_zustand()
    leiter = z.get("leiter") or {}
    if leiter:
        print("  %-26s %.4f .. %.4f, %d Stufen, Schritt %.3f %%"
              % ("Leiter (gesetzt)", leiter.get("unten", 0),
                 leiter.get("oben", 0), leiter.get("stufen", 0),
                 leiter.get("schritt_prozent", 0)))
    print("  %-26s %s" % ("journal_zweitziel",
                          w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  %-26s %s (%s)" % ("  letzte Kopie", z.get("journal_zweitziel_ok"),
                               z.get("journal_zweitziel_info")))


# --- Lauf -------------------------------------------------------------------

def lade_kerzen(w):
    inst = w.get("instrument", "BTC-USDT")
    takt = w.get("kerzen_takt", "1H")
    anzahl = int(w.get("kerzen_anzahl", 300))
    quelle = kerzen_quelle or okx.kerzen
    kerzen = quelle(inst, takt, anzahl)
    if not kerzen:
        # Eine leere Kerzenliste ist bei OKX kein Fehler, sondern eine
        # Antwort - ein Tippfehler im Instrument liest sich sonst als
        # "keine Daten".
        raise ValueError("keine Kerzen fuer %s %s (Instrument pruefen)" % (inst, takt))
    return abgeschlossene(kerzen, takt)


def lade_instrument(w):
    inst = w.get("instrument", "BTC-USDT")
    if instrument_quelle is not None:
        return instrument_quelle(inst)
    d = okx._mit_wiederholung(
        "/api/v5/public/instruments?instType=SPOT&instId=" + inst)
    if not d:
        raise ValueError("Instrument %s nicht gefunden" % inst)
    x = d[0]
    return {"instId": x["instId"], "tickSz": float(x["tickSz"]),
            "lotSz": float(x["lotSz"]), "minSz": float(x["minSz"])}


def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = lade_wachen()
    if modus == "wachen":
        zeige_wachen(w)
        return

    z = lade_zustand()
    live = False
    if modus == "live":
        g = sperren_live(w, z)
        if g:
            print("--live angefordert, aber gesperrt: " + "; ".join(g))
            print("-> es wird Papier gebucht.")
        else:                                             # pragma: no cover
            live = True

    takt = w.get("kerzen_takt", "1H")
    inst = w.get("instrument", "BTC-USDT")
    z.setdefault("instrument", inst)
    z.setdefault("kasse_usd", float(w.get("einsatz_usd", 1000.0)))
    z.setdefault("startwert_usd", float(w.get("einsatz_usd", 1000.0)))
    z.setdefault("lose", {})
    z.setdefault("kaeufe", 0)
    z.setdefault("verkaeufe", 0)
    z.setdefault("zyklen", 0)
    z.setdefault("gw_usd", 0.0)
    z.setdefault("verluste_usd", 0.0)
    z.setdefault("bestand", 0.0)

    try:
        kerzen = lade_kerzen(w)
    except Exception as e:                                 # noqa: BLE001
        # Ein Datenabruf darf den Zyklus nicht umbringen: der Dauerlauf
        # zaehlt nur den Rueckgabecode, und ein Ausfall der Boerse ist kein
        # Fehler dieser Spur. Der Herzschlag wird trotzdem geschrieben.
        print("=== GITTER %s | Kursdaten nicht abrufbar: %s ===" % (inst, e))
        print("  Kein Kerzendurchlauf, Zustand unveraendert.")
        if modus != "vorschau":
            z["modus"] = "papier"
            journal_anlegen()
            schreibe_zustand(z)
            _spiegele(z, w)
        return

    neu = not z.get("leiter")
    zahlen = {"kaeufe": 0, "verkaeufe": 0, "zyklen": 0, "gw_usd": 0.0,
              "kerzen": 0, "neu_gekauft": set()}
    zeilen = []

    if neu:
        # Erstlauf: die Grenzen entstehen aus dem aktuellen Kurs und werden
        # danach nie mehr verschoben.
        try:
            kurs = float((letzter_kurs_quelle or okx.letzter_kurs)(inst))
        except Exception:                                  # noqa: BLE001
            kurs = float(kerzen[-1][4])
        daten = lade_instrument(w)
        z["leiter"] = leiter_bauen(kurs, w, daten)
        z["anker_preis"] = kurs
        z["anker_zeit"] = _zeit()
        z["letzte_kerze_ts"] = int(kerzen[-1][0])
        z["letzter_kurs"] = kurs
        z["tick_sz"], z["lot_sz"], z["min_sz"] = (daten["tickSz"],
                                                  daten["lotSz"],
                                                  daten["minSz"])
        arme(z, kurs)
        z["modus"] = "papier"
        print("=== GITTER anlegen | %s | Kurs %.4f | %d Stufen %.4f..%.4f "
              "(Schritt %.3f %%) | Einsatz %.2f %s ==="
              % (inst, kurs, z["leiter"]["stufen"], z["leiter"]["unten"],
                 z["leiter"]["oben"], z["leiter"]["schritt_prozent"],
                 w.get("einsatz_usd", 0), w.get("waehrung", "USDT")))
        print("  Leiter steht: %d Kaufstufen armiert, %.2f %s in Orders "
              "gebunden, %d Stufen zu klein fuer die Mindestmenge."
              % (sum(1 for s in z["leiter"]["zustand"] if s == "armiert"),
                 z["leiter"]["einsatz_in_orders"], w.get("waehrung", "USDT"),
                 z["leiter"]["stufen_ohne_menge"]))
    else:
        zeilen, zahlen = walk(z, kerzen, w, takt)
        z["modus"] = "papier" if not live else "live"
        print("=== GITTER handeln (%s) | %s | Kurs %.4f | %d Kerzen nachgezogen | "
              "Kasse %.2f | Bestand %g ==="
              % ("LIVE" if live else "Papier", inst,
                 z.get("letzter_kurs") or 0.0, zahlen["kerzen"],
                 z["kasse_usd"], z["bestand"]))

    for zeile in zeilen:
        print(zeile)

    if not neu:
        print("  Zyklen: %d neu, %d gesamt | Ergebnis dieses Zyklus %+.2f %s | "
              "Leiter %d armiert, %d belegt"
              % (zahlen["zyklen"], z["zyklen"], zahlen["gw_usd"],
                 w.get("waehrung", "USDT"),
                 sum(1 for s in z["leiter"]["zustand"] if s == "armiert"),
                 sum(1 for s in z["leiter"]["zustand"] if s == "gekauft")))
    print("  Buchwert: %.2f %s (Start %.2f) | Verluste %.2f von %g | %s"
          % (buchwert(z), w.get("waehrung", "USDT"), z.get("startwert_usd", 0),
             z.get("verluste_usd", 0.0), w.get("max_verlust_usd", "?"),
             _bindung(z, w)))
    kill_text = _kill(z, w)
    if kill_text:
        print(kill_text)

    if modus == "vorschau":
        g = sperren_live(w, z)
        if g:
            print("Live waere gesperrt durch: " + "; ".join(g))
        return  # bewusst kein schreibe_zustand: eine Vorschau schreibt nicht

    journal_anlegen()
    schreibe_zustand(z)
    _spiegele(z, w)


def _bindung(z, w):
    """Ein Satz zur Kapitalbindung - die Zahl, die ein Gitter ausmacht."""
    wert = buchwert(z)
    start = z.get("startwert_usd") or 1.0
    return "Kapital %+.2f %% gegenueber Start" % ((wert / start - 1) * 100)


def _kill(z, w):
    if z.get("verluste_usd", 0.0) >= float(w.get("max_verlust_usd", 1e18)):
        return ("KILL-SWITCH gitter: Verluste %.2f >= %g - keine neuen "
                "Kauforders, belegte Stufen verkaufen weiter"
                % (z.get("verluste_usd", 0.0), w.get("max_verlust_usd")))
    return None


def _spiegele(z, w):
    """Bedingung 4: Journal und Zustand ausser Haus.

    Erst schreiben, dann kopieren - ein haengendes Zweitlaufwerk darf den
    Zyklus verzoegern, aber nicht den Herzschlag verschlucken. Ein fehlendes
    Ziel ist kein Fehler des Laufs; der Stand steht im Zustand.
    """
    ziel = w.get("journal_zweitziel")
    if not ziel:
        print("  Journal ausser Haus:  -- (kein Ziel gesetzt)")
        return
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        wp.spiegele_journal([ZUSTAND], ziel)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))


def main():
    # gitter/handeln.py ist der automatische Einstieg (der Dauerlauf startet
    # dieses Skript als eigenen Prozess) - es meldet sich damit am Bus.
    with ereignis.lauf("handel/gitter"):
        return _main()


def _main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier")
    # Der Dauerlauf ruft "--papier" als FLAG; ein argparse-choices-Eintrag
    # allein reicht nicht (argparse liest "--papier" als Option). Deshalb
    # beides: das Flag oben und hier das Positional fuer Handaufrufe.
    g.add_argument("--live", action="store_const", dest="modus", const="live")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen")
    p.add_argument("papier", nargs="?", choices=["papier"],
                   help="Positional: handeln.py papier")
    a = p.parse_args()
    lauf(a.modus or "papier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
