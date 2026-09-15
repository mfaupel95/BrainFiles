"""Mosaic-Spur: Mehr-Zeitrahmen-Preisaktion (Top-Down).

Bias und Ausfuehrung werden getrennt gerechnet, damit jede Schicht einzeln
messbar bleibt und spaeter optimiert werden kann, ohne die anderen zu
verfaelschen.

Signalkette (alles lange Kerzen = Aufwaertstrend):
1. 4H: die letzte Kerze ist gruen (close > open)  -> Aufwaerts-Bias.
2. 30M: ein Pullback hat eine Nachfragezone beruehrt und sich dort
       umgedreht; die Zone sind die Swing-Tiefs der letzten 20 Kerzen.
3. 5M: die letzte Kerze schliesst ueber dem letzten relevanten Swing-High
       des 5M-Charts (Break of Structure, BOS) im Sinne des Bias.

Ein Einstieg verlangt ALLE drei. Ausstieg: ATR-Stop, Ziel 2R.

Papier-Handel: handel_erlaubt=false. Keine Orders.

Aufruf:
 python handeln.py --vorschau   waere dran, ohne schreiben
 python handeln.py --papier     Papierlauf mit Journal
 python handeln.py --wachen     Grenzen als Momentaufnahme
 python handeln.py --live       verweigert, nennt den Grund
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
# Reihenfolge zaehlt: sys.path.insert(0, ...) dreht die Liste um, deshalb
# rueckwaerts einfuegen. HIER muss ganz vorne stehen, sonst gewinnt
# scanner/handeln.py gegen das handeln.py dieser Spur.
for p in (os.path.join(HANDEL, os.pardir, "Bus"),
          os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import wachen_pruefung as wp  # noqa: E402
import ereignis  # noqa: E402

# ratschen.py ueber den PFAD laden, nicht ueber sys.path: die Datei liegt
# eine Ebene hoeher und heisst wie kein Paket. Ein Import ueber sys.path
# haenge davon ab, wer vorher eingefuegt hat.
from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402

_spec_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "ratschen.py")
_spec = spec_from_file_location("ratschen", _spec_path)
ratschen = module_from_spec(_spec)
_spec.loader.exec_module(ratschen)

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

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund"]

# Schreib-Flag: False in Tests, True im Betrieb.
SCHREIBEN = True

# --- Test-Seams -----------------------------------------------------------
# Kerzenquelle: None = echte Quelle (okx). Tests setzen eine Lambda.
kerzen_quelle = None
# Zeit-Quelle: None = utcnow. Tests koennen setzen.
zeit_quelle = None


# --- Zeit ------------------------------------------------------------------

def _jetzt():
    if zeit_quelle:
        return zeit_quelle()
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


# --- Dateien ---------------------------------------------------------------

def lade_wachen():
    with open(WACHEN, encoding="utf-8") as f:
        return risikostufe.skaliere(json.load(f))


def lade_zustand():
    try:
        with open(ZUSTAND, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"positionen": [], "modus": "papier", "letzter_lauf": None,
                "verluste_usd": 0.0}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    with open(ZUSTAND, "w", encoding="utf-8") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")


def journal(**felder):
    if not SCHREIBEN:
        return
    neu = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN)
        if neu:
            w.writeheader()
        w.writerow(felder)


def spiegeln(z, w):
    """Bedingung 4: Journal und Zustand ausser Haus.

    Erst schreiben, dann kopieren. Der Vermerk ist juenger als die Kopie:
    wechselt er, wird der Zustand einmal nachgezogen, damit auf derselbe
    Stand liegt. Ohne den Nachzug meldet spiegelstand.py JEDEM Zyklus eine
    Abweichung, dem sich der Spiegelstand aendert (Muster: swap/handeln.py).
    """
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand)
    if ok:
        wp.spiegele_journal([ZUSTAND], ziel)


# --- Kerzen ----------------------------------------------------------------

def lade_kerzen(inst, intervall, anzahl):
    """Kerzen laden: entweder Seam oder echte Quelle."""
    if kerzen_quelle:
        return kerzen_quelle(inst, intervall, anzahl)
    try:
        import okx
        return okx.kerzen(inst, intervall, anzahl)
    except Exception as e:
        print("Netzfehler: Kerzen fuer %s nicht abrufbar (%s)" % (inst, e),
              file=sys.stderr)
        return []


# --- Preisaktions-Bausteine -------------------------------------------------

def _schluss(k, idx):
    """Schlusskurs der Kerze idx (auch negativ = von hinten), oder None."""
    if idx < -len(k) or idx >= len(k):
        return None
    return k[idx][4]


def _kerze_gruen(k, idx):
    """True, wenn Kerze idx gruen ist (close > open). Auch negativ idx."""
    if idx < -len(k) or idx >= len(k):
        return False
    return k[idx][4] > k[idx][1]


def _swing_tiefs(k, fenster):
    """Swing-Tiefs (lokale Minima) der letzten Kerzen.

    Ein Index i ist ein Swing-Tief, wenn sein Low das Minimum in einem
    Fenster von `fenster` Kerzen LINKS (oder bis zum Rand) und RECHTS
    (oder bis zum Rand) ist. Der Fenster-Rand wird nicht ueberschritten -
    dadurch sind auch Tiefs nahe am Ende der Serie erlaubt, wo rechts
    weniger Kerzen liegen als `fenster` (fuer BOS-Referenzen wichtig).

    Monotone Reihen liefern so keine Tiefs (bewusst): ein Aufwaerts-Markt
    ohne Pullback hat keine Nachfragezone, an der ein Einstieg Sinn ergibt.
    """
    if len(k) < 3:
        return []
    ergebnis = []
    start = max(1, len(k) - 2 * fenster)
    for i in range(start, len(k) - 1):
        links_von = max(0, i - fenster + 1)
        links_bis = i + 1
        rechts_von = i
        rechts_bis = min(len(k), i + fenster)
        links = min(k[j][3] for j in range(links_von, links_bis))
        rechts = min(k[j][3] for j in range(rechts_von, rechts_bis))
        if k[i][3] <= links and k[i][3] <= rechts:
            ergebnis.append(i)
    return ergebnis


def _swing_hochs(k, fenster):
    """Swing-Hochs (lokale Maxima) der letzten Kerzen. Rand erlaubt."""
    if len(k) < 3:
        return []
    ergebnis = []
    start = max(1, len(k) - 2 * fenster)
    for i in range(start, len(k) - 1):
        links_von = max(0, i - fenster + 1)
        links_bis = i + 1
        rechts_von = i
        rechts_bis = min(len(k), i + fenster)
        links = max(k[j][2] for j in range(links_von, links_bis))
        rechts = max(k[j][2] for j in range(rechts_von, rechts_bis))
        if k[i][2] >= links and k[i][2] >= rechts:
            ergebnis.append(i)
    return ergebnis


def nachfrage_zone(k30, w):
    """Nachfragezone auf dem 30M-Chart.

    Zone = Preisspanne der Swing-Tiefs der letzten `zone_schwung_kerzen_30m`
    Kerzen. Damit ein Pullback-Zone-Setup Sinn macht, muss die Zone einen
    Puffer haben (untere < obere). Liefert (untere, obere) oder None, wenn
    die Kerzen fehlen.

    Der Fallback fuer Fehlanzeigen (keine echten Swing-Tiefs, z.B. weil der
    Pullback gerade erst unterwegs ist) nimmt die untere Haelfte der Spanne
    der letzten Fenster-Kerzen. So ist die Zone auch waehrend eines
    laufenden Pullbacks definiert, und `zone_beruehrt` entscheidet, ob der
    Kurs sie tatsaechlich erreicht hat.
    """
    fenster = int(w.get("zone_schwung_kerzen_30m", 20))
    if len(k30) < fenster:
        return None
    tiefs = _swing_tiefs(k30, fenster)
    if tiefs:
        werte = [k30[i][3] for i in tiefs]
        untere = min(werte)
        obere = max(werte)
        # Nur die untere Haelfte der Spanne ist echte Nachfrage. Degeneriert
        # die Spanne (ein einzelnes Tief, alle gleich), faellt der Code in
        # den Fenster-Fallback darunter - eine Zone ohne Puffer ist keine.
        if obere > untere:
            return (untere, untere + (obere - untere) * 0.5)
    # Fallback: die untere Haelfte der letzten Fenster-Kerzen-Lows
    werte = [k30[i][3] for i in range(max(0, len(k30) - fenster), len(k30))]
    if not werte:
        return None
    untere = min(werte)
    obere = max(werte)
    if obere <= untere:
        return None
    return (untere, untere + (obere - untere) * 0.5)


def zone_beruehrt(k30, w, zone):
    """True, wenn eine der letzten `zone_beruehrung_kerzen_30m` Kerzen die
    Zone beruehrt hat (Low <= obere Grenze und High >= untere)."""
    if not zone:
        return False
    fenster = int(w.get("zone_beruehrung_kerzen_30m", 30))
    untere, obere = zone
    for kerze in k30[-fenster:]:
        if kerze[3] <= obere and kerze[2] >= untere:
            return True
    return False


def letztes_relevantes_swing_hoch(k5, fenster):
    """Hoechstes Swing-Hoch der letzten `fenster` 5M-Kerzen (fuer BOS).

    Fallback, wenn die Serie keine echten Swing-Hochs hat (monoton, zu
    kurz): das hoechste High der letzten `fenster` Kerzen. Ein BOS ist
    dann der Schluss ueber dem hoechsten Punkt der jüngsten Vergangenheit
    - eine sinnvolle Referenz auch ohne lokale Maxima.
    """
    hochs = _swing_hochs(k5, fenster)
    if hochs:
        return max(k5[i][2] for i in hochs)
    if len(k5) <= fenster:
        return None
    return max(k5[j][2] for j in range(len(k5) - fenster, len(k5)))


def structure_shift(k5, w):
    """Structure Shift auf dem 5M-Chart (Break of Structure, BOS).

    True, wenn die letzte Kerze ueber dem hoechsten relevanten Swing-High
    der letzten `struktur_shift_kerzen_5m` Kerzen schliesst.
    """
    fenster = int(w.get("struktur_shift_kerzen_5m", 30))
    if len(k5) < fenster + 1:
        return False
    swing_hoch = letztes_relevantes_swing_hoch(k5[:-1], fenster)
    if swing_hoch is None:
        return False
    return k5[-1][4] > swing_hoch


def bias_4h(k4, w):
    """4H-Bias: letzte Kerze gruen -> long, rot -> short, sonst None."""
    if len(k4) < 1:
        return None
    if _kerze_gruen(k4, -1):
        mindest = int(w.get("trend_min_kerzen_4h", 0))
        if len(k4) < 1 + mindest:
            return None
        # Die letzten `mindest` 4H-Kerzen vor der letzten muessen gruen sein.
        for i in range(len(k4) - mindest - 1, len(k4) - 1):
            if not _kerze_gruen(k4, i):
                return None
        return "long"
    return "short"


def signal(k4, k30, k5, w):
    """Mosaic-Signal: 'long', 'short' oder None.

    Top-down: Bias (4H) -> Nachfragezone mit Beruehrung (30M) -> BOS (5M).
    Aktuell nur LONG verlangt: Bias long + Nachfragezone + BOS nach oben.
    SHORT ist absichtlich noch nicht verdrahtet, bis die Long-Seite belegt
    ist.
    """
    if bias_4h(k4, w) != "long":
        return None
    zone = nachfrage_zone(k30, w)
    if not zone or not zone_beruehrt(k30, w, zone):
        return None
    if not structure_shift(k5, w):
        return None
    return "long"


# --- Positionen ------------------------------------------------------------

def atr_abs(k, idx, n=14):
    """Einfacher ATR ueber die letzten Kerzen bis idx."""
    if idx < n:
        return None
    s = 0.0
    for j in range(idx - n + 1, idx + 1):
        s += k[j][2] - k[j][3]  # hoch - tief
    return s / n


def position_groesse(einstieg, stop_pct, w):
    """Risiko-normierte Groesse, gedeckelt und mit Drawdown-Ratsche."""
    stop_pct_eff = max(stop_pct, w.get("pflicht_stop_prozent_min", 5.0))
    stop_pct_eff = min(stop_pct_eff, w.get("pflicht_stop_prozent_max", 12.0))
    nominel = w["risiko_je_position_usd"] / (stop_pct_eff / 100.0)
    nominel = min(nominel, w["max_pro_trade_usd"])
    return nominel


def groessenfaktor(ruecklauf, w):
    """Drawdown-Ratsche aus ratschen.py - eine Umsetzung fuer alle Spuren."""
    return ratschen.groessenfaktor(ruecklauf, w)


def pruefe_einstieg(inst, k4, k30, k5, z, w, faktor):
    """Prueft, ob eine neue Position eroeffnet werden soll."""
    if not z.get("positionen"):
        z["positionen"] = []
    if len(z["positionen"]) >= w.get("max_offene_positionen", 4):
        return

    sig = signal(k4, k30, k5, w)
    if not sig:
        return

    einstieg = k5[-1][4]  # Schluss als Einstieg (Papier)
    atr = atr_abs(k5, len(k5) - 1, 14)
    if not atr or atr <= 0:
        return

    # Stop-Abstand aus dem ATR, in den Pflichtrahmen gezwungen.
    stop_pct = atr / einstieg * 100.0
    stop_pct = max(stop_pct, w.get("pflicht_stop_prozent_min", 5.0))
    stop_pct_eff = min(stop_pct, w.get("pflicht_stop_prozent_max", 12.0))

    vz = 1 if sig == "long" else -1
    abstand = einstieg * stop_pct_eff / 100.0
    ziel_r = w.get("ziel_r_vielfaches", 2.0)
    stop = einstieg - vz * abstand
    ziel = einstieg + vz * abstand * ziel_r

    nominel = w["risiko_je_position_usd"] / (stop_pct_eff / 100.0)
    nominel = min(nominel, w["max_pro_trade_usd"])
    nominel *= faktor
    if nominel <= 0:
        return

    z["positionen"].append({
        "inst": inst, "seite": sig, "einstieg": einstieg,
        "stop": stop, "ziel": ziel, "stop_pct": stop_pct_eff,
        "nominal": nominel, "eroeffnet_zeit": _jetzt(),
    })

    print("EINSTIEG %s %.6f Stop %.2f%% Ziel R=%.1f (%.6f) Nominal %.2f USD" % (
        sig.upper(), einstieg, stop_pct_eff, ziel_r, ziel, nominel))
    journal(zeit=_jetzt(), modus="papier", aktion="kauf", inst=inst, seite=sig,
            preis="%.6f" % einstieg, einsatz_usd="%.2f" % nominel,
            stop="%.6f" % stop, ziel="%.6f" % ziel,
            stop_pct="%.2f" % stop_pct_eff, grund="mosaic")


def pruefe_ausstiege(z, k5, w, nur=None):
    """Bestehende Positionen auf Stop/Ziel pruefen.

    `k5` sind die Kerzen EINES Instruments (5M); `nur` grenzt die Pruefung
    darauf ein. Ohne die Einschraenkung wuerde jede offene Position gegen
    diesen einen Kurs geprueft (Befund 15.09.2026).
    """
    behalten = []
    for p in z.get("positionen", []):
        if nur is not None and p.get("inst") != nur:
            behalten.append(p)
            continue

        kurs = k5[-1][4] if len(k5) else None
        if not kurs:
            behalten.append(p)
            continue

        grund = None
        vz = 1 if p["seite"] == "long" else -1
        if p["seite"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif kurs >= p["ziel"]:
                grund = "ziel"
        else:
            if kurs >= p["stop"]:
                grund = "stop"
            elif kurs <= p["ziel"]:
                grund = "ziel"

        if not grund:
            behalten.append(p)
            continue

        # G/V auf den NOMINALWERT: eine Kursbewegung von x Prozent bewegt
        # x Prozent des Nominalwerts (Befund 15.09.2026, siehe squeeze).
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
        erloes = p["nominal"] + gv
        print("AUSSTIEG (%s) %.6f G/V %+.2f USD" % (grund, kurs, gv))
        journal(zeit=_jetzt(), modus="papier", aktion="verkauf", inst=p["inst"],
                seite=p["seite"], preis="%.6f" % kurs,
                einsatz_usd="%.2f" % erloes, stop="%.6f" % p["stop"],
                ziel="%.6f" % p["ziel"], stop_pct="%.2f" % p["stop_pct"],
                grund=grund)

    z["positionen"] = behalten


# --- Laeufe -----------------------------------------------------------------

def lauf(modus):
    """Ein Zyklus der Mosaic-Spur."""
    w = lade_wachen()
    z = lade_zustand()
    z.setdefault("positionen", [])

    if modus == "wachen":
        print(json.dumps(wp.lage(w, JOURNAL, z), indent=2, ensure_ascii=False))
        return

    # Drawdown-Ratsche
    s = wp.lage(w, JOURNAL, z)
    ruecklauf = s.get("ruecklauf_usd", 0.0)
    faktor = groessenfaktor(ruecklauf, w)

    if s.get("kill"):
        print("- Kill-Schwelle erreicht (%.2f USD Ruecklauf). Alles flach." % ruecklauf)
        z["positionen"] = []
        schreibe_zustand(z)
        spiegeln(z, w)
        return

    if modus == "vorschau":
        print("Vorschau: keine Dateien geschrieben.")
        return

    # Kerzen fuer alle Instrumente laden (drei Zeitrahmen je Instrument).
    for inst in w.get("instrumente", []):
        k4 = lade_kerzen(inst, w.get("kerzen_takt_4h", "4H"),
                         w.get("mindest_kerzen", 300))
        k30 = lade_kerzen(inst, w.get("kerzen_takt_30m", "30m"),
                          w.get("mindest_kerzen", 300))
        k5 = lade_kerzen(inst, w.get("kerzen_takt_5m", "5m"),
                         w.get("mindest_kerzen", 300))
        if not k4 or not k30 or not k5:
            print("Uebersprungen (%s): keine Kerzen" % inst, file=sys.stderr)
            continue

        # Ausstiege zuerst
        bestehend = [p for p in z["positionen"] if p["inst"] == inst]
        if bestehend:
            z["positionen"] = [p for p in z["positionen"] if p["inst"] != inst]
            z["positionen"].extend(bestehend)
            pruefe_ausstiege(z, k5, w, nur=inst)

        # Neue Einstiege
        pruefe_einstieg(inst, k4, k30, k5, z, w, faktor)

    schreibe_zustand(z)
    spiegeln(z, w)


# --- Main -------------------------------------------------------------------

def main():
    # Meldet sich am Bus wie jede andere Spur im Dauerlauf (Muster
    # kraken/handeln.py). Ein toter Bus bricht den Lauf nicht ab.
    with ereignis.lauf("handel/mosaic"):
        return _main()


def _main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau",
                    dest="modus", help="was waere dran, ohne schreiben")
    ap.add_argument("--papier", action="store_const", const="papier", dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    ap.set_defaults(modus="vorschau")
    a = ap.parse_args()

    if a.modus == "live":
        print("--live verweigert: Papier-Spur, keine Orders moeglich.")
        return 1

    lauf(a.modus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())