"""Tests fuer den SWAP-Block im Tagesbericht - ohne Netz, ohne Order, ohne Lauf.

Der Bericht liest den Zustand aus swap/zustand.json und - wenn Positionen da
sind - den Kurs ueber xperp/okxf.py. Beides wird hier ersetzt: die Dateien durch
einen Datenordner, okxf durch ein Stummelmodul in sys.modules. Damit laeuft die
echte Rechnung (Prozent auf die Margin, Hebel daneben) und trotzdem keine
einzige Anfrage.

Was hier belegt wird:
  1. Eine Papierposition der SWAP-Spur steht im Bericht, mit Hebel auf die
     Margin gerechnet - dieselbe Formel wie bei Spur 2.
  2. Sie wird als "SWAP (Papier)" ausgewiesen und "Live: GESPERRT" mit
     Klartext-Gruenden; der Bericht behauptet nirgends, hier sei Live nur
     "offen". SWAP setzt "papierfest" bewusst nicht (siehe lage.spur_swap:
     seit 12.09.2026 hat die Spur einen echten Live-Pfad) - die Sperre
     kommt hier aus den echten Bedingungen (handel_erlaubt, Freigabe,
     Herzschlag), nicht aus einem festen "kein Live-Zweig (Papierpfad)".
  3. Der Bericht schreibt nichts. Vorher/nachher werden Dateiliste und
     Aenderungszeiten des Datenordners verglichen.

Nachsehen statt glauben:
    python tests/test_tagesbericht_swap.py --zeigen   # rendert den Bericht mit
                                                      # Beispieldaten
"""

import io
import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import tagesbericht                                        # noqa: E402

BEISPIEL = {
    "inst": "CHIP-USDT-SWAP", "basis": "CHIP", "seite": "long",
    "familie": "krypto", "einstieg": 1.0, "stop": 0.9, "ziel": 1.3,
    "margin": 50.0, "hebel": 3, "liq": 0.7, "eroeffnet": "2026-09-12",
}

# Die echten Grenzen der Spur. Nicht erfunden: wachen_xperp.lage() liest
# Groessen wie max_margin_gesamt_usd und die Familienanteile heraus. Ein
# erfundener Rest liesse den Bericht "Wachen nicht lesbar" schreiben - und was
# gerendert wird, waere dann nicht das, was Max aufs Handy bekommt.
WACHEN_DATEI = os.path.join(HANDEL, "swap", "wachen.json")

ZUSTAND = {"modus": "papier", "letzter_lauf": "2026-09-12T17:00:00+00:00",
           "positionen": [BEISPIEL]}


def _schreibe(pfad, daten):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with io.open(pfad, "w", encoding="utf-8", newline="") as f:
        if isinstance(daten, str):
            f.write(daten)
        else:
            json.dump(daten, f, ensure_ascii=False)


def datenordner(positionen=None):
    """Ein Ordner, wie ihn der Bericht erwartet - nur der SWAP-Teil gefuellt."""
    t = tempfile.mkdtemp(prefix="bericht-")
    with io.open(WACHEN_DATEI, encoding="utf-8", newline="") as f:
        _schreibe(os.path.join(t, "swap", "wachen.json"), f.read())
    _schreibe(os.path.join(t, "swap", "zustand.json"),
              dict(ZUSTAND, positionen=positionen or []))
    return t


def stub_okxf(kurs):
    """okxf als Stummel - kein Netz, kein Schluessel, kein Order-Weg."""
    m = types.ModuleType("okxf")
    m.letzter_kurs = lambda inst: kurs
    return m


def bestand(ordner):
    """Dateiliste mit Groesse und Aenderungszeit - fuer den Schreib-Nachweis."""
    aus = {}
    for wurzel, _, dateien in os.walk(ordner):
        for name in sorted(dateien):
            p = os.path.join(wurzel, name)
            s = os.stat(p)
            aus[os.path.relpath(p, ordner)] = (s.st_size, s.st_mtime_ns)
    return aus


def bericht(positionen=None, kurs=1.1):
    t = datenordner(positionen)
    with patch.dict(sys.modules, {"okxf": stub_okxf(kurs)}), \
            patch.object(tagesbericht, "HIER", t):
        text = tagesbericht.baue(mit_xperp=False)
    return t, text


class SwapImBericht(unittest.TestCase):

    def test_papierposition_wird_gerechnet_und_als_papier_benannt(self):
        _, text = bericht([BEISPIEL])
        self.assertIn("SWAP (Papier)", text)
        self.assertIn("CHIP long", text)
        # 10 % Kursbewegung bei 3x Hebel = 30 % auf die Margin.
        self.assertIn("+30.0%", text)
        self.assertIn("50 USD", text)
        # SWAP ist nicht "papierfest" (echter Live-Pfad seit 12.09.2026) -
        # die Sperre wird mit den echten Gruenden ausgewiesen, nicht mit
        # einem festen "kein Live-Zweig".
        self.assertIn("Live: GESPERRT -", text)

    def test_leere_spur_ist_kein_offenes_live(self):
        _, text = bericht([])
        self.assertIn("SWAP (Papier)", text)
        self.assertIn("keine offene Position", text)
        # Die Sperre wird ausgeschrieben, nicht weggelassen: Ohne Grund liest
        # sich "GESPERRT" wie eine Spur, die nur auf ein /ja wartet. SWAP ist
        # nicht "papierfest" (echter Live-Pfad seit 12.09.2026), deshalb die
        # echten Gruende statt eines festen "kein Live-Zweig".
        self.assertIn("Live: GESPERRT -", text)
        self.assertNotIn("Live: offen", text)

    def test_bericht_schreibt_nichts(self):
        t = datenordner([BEISPIEL])
        vorher = bestand(t)
        with patch.dict(sys.modules, {"okxf": stub_okxf(1.1)}), \
                patch.object(tagesbericht, "HIER", t):
            tagesbericht.baue(mit_xperp=False)
        self.assertEqual(vorher, bestand(t),
                         "Der Bericht darf keine Datei anfassen")

    def test_stummelfehler_des_kurses_kippt_die_position_nicht(self):
        # Kein Kurs: Die Position bleibt sichtbar, mit "(kein Kurs)".
        def platzt(inst):
            raise OSError("kein Netz im Test")
        t = datenordner([BEISPIEL])
        stumm = stub_okxf(None)
        stumm.letzter_kurs = platzt
        with patch.dict(sys.modules, {"okxf": stumm}), \
                patch.object(tagesbericht, "HIER", t):
            text = tagesbericht.baue(mit_xperp=False)
        self.assertIn("CHIP long", text)
        self.assertIn("(kein Kurs)", text)


class StopAbstandRichtung(unittest.TestCase):
    """zeile_position rechnet den Stop-Abstand richtungsbewusst.

    Befund 13.09.2026: Die erste omniquant-short-Position (WLFI-USDT) wurde
    im Tagesbericht als "Stop gerissen (8.0%)" gezeigt, obwohl der Stop 8,7 %
    UEBER dem Einstieg lag und nichts gerissen war - die Formel rechnete
    kurs/stop - 1 ohne Richtung, und bei short liegt der Stop immer ueber dem
    Kurs. Der Abstand ist Luft, kein Fehler.
    """

    def test_short_mit_luft_zum_stop_ist_nicht_gerissen(self):
        # short: Stop ueber dem Einstieg, Kurs noch beim Einstieg -> Luft.
        p = {"name": "WLFI short", "einstieg": 0.057, "kurs": 0.057,
             "stop": 0.062, "wert": 50.0, "vh": 0.0, "seite": "short"}
        text = tagesbericht.zeile_position(p, "USD")
        self.assertIn("Stop 8.1% (Kurs)", text)
        self.assertNotIn("gerissen", text)

    def test_short_mit_kurs_hinter_dem_stop_ist_gerissen(self):
        # Kurs ist UEBER den Stop gelaufen (nach oben) -> gerissen.
        p = {"name": "WLFI short", "einstieg": 0.057, "kurs": 0.065,
             "stop": 0.062, "wert": 50.0, "vh": -14.0, "seite": "short"}
        text = tagesbericht.zeile_position(p, "USD")
        self.assertIn("Stop gerissen", text)

    def test_long_mit_luft_zum_stop_ist_nicht_gerissen(self):
        p = {"name": "SOL long", "einstieg": 99.5, "kurs": 100.0,
             "stop": 94.5, "wert": 50.0, "vh": 0.5, "seite": "long"}
        text = tagesbericht.zeile_position(p, "USD")
        self.assertIn("Stop 5.8% (Kurs)", text)
        self.assertNotIn("gerissen", text)

    def test_long_mit_kurs_hinter_dem_stop_ist_gerissen(self):
        p = {"name": "SOL long", "einstieg": 99.5, "kurs": 94.0,
             "stop": 94.5, "wert": 50.0, "vh": -5.5, "seite": "long"}
        text = tagesbericht.zeile_position(p, "USD")
        self.assertIn("Stop gerissen", text)

    def test_ohne_seite_gilt_long(self):
        # Positionen ohne seite-Feld (aelleres Format) bleiben long - der
        # bisherige Default, unveraendert.
        p = {"name": "X long", "einstieg": 100.0, "kurs": 101.0,
             "stop": 95.0, "wert": 50.0, "vh": 1.0}
        text = tagesbericht.zeile_position(p, "USD")
        self.assertIn("Stop 6.3% (Kurs)", text)
        self.assertNotIn("gerissen", text)


def zeige():
    """Rendert den Bericht mit Beispieldaten - die Ausgabe ist der Nachweis."""
    _, text = bericht([BEISPIEL, dict(BEISPIEL, inst="XAU-USD-SWAP",
                                      basis="XAU", seite="short", hebel=5)])
    print(text.replace("<b>", "").replace("</b>", ""))


if __name__ == "__main__":
    if "--zeigen" in sys.argv:
        zeige()
    else:
        unittest.main()
