"""Verdrahtungsregel: was das Haus fuehrt, muss das Haus auch rechnen.

Die Regel, nicht die Zahl: eine feste Spurenlaenge geht bei jeder neuen
Spur kaputt. Geprueft wird die EIGENTLICHE Bedingung - eine Spur mit einem
Ratschenbetrag in ihrer Wache wird auch geprueft, und eine Spur mit
Journal wird auch ausgewertet.

Befund 03.10.2026: liq_wand hatte 32 geschlossene Runden im Journal und
0 in jeder Auswertung - kein Tagesbericht, keine Strategiekennzahl, kein
Kosten-Wendepunkt. trendwende_btc und nautilus_emacross waren genauso
unerkannt. pruefe_ratschen pruefte die fuenf Spuren nicht, deren Ratsche
nie nachgefragt wurde (squeeze, wavetrend, macd_mtf, supertrend,
nautilus_emacross).

Ausfuehren aus dem Ordner Handel/tests:
    ..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_verdrahtung -v
"""
import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import auswertung_alle      # noqa: E402
import dauerlauf            # noqa: E402
import pruefe_ratschen      # noqa: E402

# Spuren mit eigener Auswertung (auswertung.py im Ordner): ihr Journal traegt
# eine eigene Form, ein Weg in auswertung_alle waere eine ZWEITE Wahrheit.
# Bei kopier/kopier1zu1 belegt: runden_nautilus lieferte 107 Runden mit
# falscher Paarung (Einsteig PATE, Ausstieg leeres Symbol).
EIGENE_AUSWERTUNG = ("spiegel", "spiegel_knapp", "spiegel_weit", "kopier",
                     "omniquant", "omniquant_weit", "gitter",
                     "jev_trader", "llm_stunde")

RUHT = tuple(pruefe_ratschen.RUHT)


def wachen_pfad(spur):
    cfg = dauerlauf.SPUREN.get(spur, {})
    ordner = cfg.get("ordner", spur)
    for kandidat in (os.path.join(HANDEL, ordner, "wachen.json"),
                     os.path.join(HANDEL, ordner, ordner, "wachen.json")):
        if os.path.exists(kandidat):
            return kandidat
    return None


def wache(spur):
    p = wachen_pfad(spur)
    if not p:
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def fuehrt_ratsche(spur):
    """Traegt die Wache einen Drawdown-Betrag? Dann muss er geprueft werden."""
    return wache(spur).get("drawdown_halbierung_usd") is not None


def fuehrt_journal(spur):
    cfg = dauerlauf.SPUREN.get(spur, {})
    ordner = cfg.get("ordner", spur)
    for kandidat in (os.path.join(HANDEL, ordner, "handelsjournal.csv"),
                     os.path.join(HANDEL, ordner, ordner,
                                  "handelsjournal.csv")):
        if os.path.exists(kandidat):
            with open(kandidat, "rb") as f:
                zeilen = sum(1 for _ in f)
            return zeilen > 1
    return False


class RechenwegTest(unittest.TestCase):
    def test_jede_spur_mit_journal_hat_einen_rechenweg(self):
        auswertet = set(auswertung_alle.SPUREN) | set(EIGENE_AUSWERTUNG)
        fehlen = {s for s in dauerlauf.SPUREN
                  if fuehrt_journal(s) and s not in auswertet}
        self.assertEqual(
            fehlen, set(),
            "Journal vorhanden, aber kein Rechenweg in keiner Auswertung: %s"
            % sorted(fehlen))

    def test_alle_spuren_sind_erfasst(self):
        """Ohne Journal zaehlt die Spur trotzdem - sie ist eine geplante Spur."""
        auswertet = set(auswertung_alle.SPUREN) | set(EIGENE_AUSWERTUNG)
        fehlen = {s for s in dauerlauf.SPUREN if s not in auswertet}
        self.assertEqual(
            fehlen, set(),
            "im Dauerlauf, aber in keiner Auswertung gelistet: %s"
            % sorted(fehlen))

    def test_jede_ratsche_wird_geprueft(self):
        geprueft = set(x[0] for x in pruefe_ratschen.SPUREN) | set(RUHT)
        fehlen = {s for s in dauerlauf.SPUREN
                  if fuehrt_ratsche(s) and s not in geprueft}
        self.assertEqual(
            fehlen, set(),
            "Ratschenbetrag gesetzt, aber nie geprueft: %s" % sorted(fehlen))

    def test_geprueftes_buchrisiko_trifft_den_betrag(self):
        """Jeder nachgetragene Eintrag muss den Betrag = 1.0 x Buchrisiko treffen.

        Ein Eintrag ohne diesen Nachweis waere nur eine Zeile in einer Liste.
        """
        R = pruefe_ratschen.RATSCHEN
        offen = []
        for spur, _ordner in sorted(x[0:2] for x in pruefe_ratschen.SPUREN):
            w = wache(spur)
            if not w:
                continue
            betrag = R.halbierungsschwelle(w)
            risiko = R.buch_risiko(w)
            if betrag is None or risiko is None:
                offen.append(spur)
            elif abs(betrag - risiko) > 0.005:
                offen.append(spur)
        # Erlaubt ist genau die eine Ausnahme, die als Luecke benannt ist:
        # nautilus_emacross setzt 100.0 ohne Risiko-Feld in der Wache.
        # moondev_funding (15.00 gegen 20.00) und orb (1.00 gegen 3.00) sind
        # VORBESTHENDE Abweichungen, die pruefe_ratschen.py selbst als "!"
        # meldet - sie stehen hier nicht, dieser Test prueft die Nachtraege.
        erlaubt = {"nautilus_emacross", "moondev_funding", "orb"}
        self.assertEqual(set(offen) - erlaubt, set(),
                         "Betrag weicht von 1.0 x Buchrisiko ab: %s"
                         % sorted(set(offen) - erlaubt))


class IndikatorSchwellenTest(unittest.TestCase):
    """T-097: Indikatorschwellen stehen in der wachen.json, nicht im Code.

    Die vier Indikator-Spuren (squeeze, wavetrend, macd_mtf, supertrend)
    lasen bis 05.10.2026 ihre Indikator-Parameter als Konstanten aus dem
    Quelltext - optimieren.py konnte sie deshalb nicht variieren. Nach der
    Hebung MUSS jede dieser Spuren ihre Schluessel in der ECHTEN wachen.json
    tragen, sonst ist der Umbau stumm. Geprueft wird die Regel (Schluessel
    vorhanden), nicht ein Zahlenwert: ein Test gegen den Wert geht bei jeder
    bewussten Aenderung kaputt, ohne dass die Hebung weg ist.
    """

    # Indikator-Schluessel je Spur, deren Code-Stand vor T-097 fest war.
    SCHLUESSEL = {
        "squeeze": ("squeeze_laenge", "squeeze_bb_mult", "squeeze_kc_mult",
                    "atr_n"),
        "wavetrend": ("wt_n1", "wt_n2", "wt_ueberverkauft", "atr_n"),
        "macd_mtf": ("mtf_faktoren", "mtf_schnell", "mtf_langsam",
                     "mtf_signal", "atr_n"),
        "supertrend": ("supertrend_n", "supertrend_faktor", "atr_n"),
    }

    def test_jede_indikator_spur_traegt_ihre_schluessel(self):
        fehlend = {}
        for spur, schluessel in self.SCHLUESSEL.items():
            w = wache(spur)
            fehlen = [k for k in schluessel if k not in w]
            if fehlen:
                fehlend[spur] = fehlen
        self.assertEqual(fehlend, {},
                         "Indikatorschluessel fehlen in der wachen.json: %s"
                         % fehlend)

    def test_gegenprobe_ohne_schluessel_greift_die_regel(self):
        """Ein entfernter Schluessel muss von diesem Test gefunden werden.

        Geprueft wird gegen eine KOPIE im Temp-Ordner, nicht gegen die echte
        Datei: drei Dauerlauf-Stufen lesen wavetrend/wachen.json gerade live,
        ein Schreibfenster in die echte Datei koennte einen Zyklus treffen
        (halb geschriebenes JSON). Die Regel ist dieselbe - ein fehlender
        Schluessel muss den Test rot machen.
        """
        import shutil
        import tempfile as _tmp

        global wache
        quelle = wachen_pfad("wavetrend")
        tmp = _tmp.mkdtemp(prefix="t097-schwelle-")
        try:
            ziel = os.path.join(tmp, "wachen.json")
            shutil.copy2(quelle, ziel)
            with open(ziel, encoding="utf-8") as f:
                w = json.load(f)
            w.pop("wt_ueberverkauft")
            with open(ziel, "w", encoding="utf-8") as f:
                json.dump(w, f, ensure_ascii=False)

            echte_wache = wache

            def wache_aus_kopie(spur):
                if spur == "wavetrend":
                    with open(ziel, encoding="utf-8") as f:
                        return json.load(f)
                return echte_wache(spur)

            wache = wache_aus_kopie
            try:
                with self.assertRaises(AssertionError):
                    self.test_jede_indikator_spur_traegt_ihre_schluessel()
            finally:
                wache = echte_wache
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class RueckwaertsTest(unittest.TestCase):
    """Gegenprobe: ohne die Nachtraege melden dieselben Tests mehr."""

    def test_gegenprobe_rechenweg_ohne_eintrag(self):
        gespeichert = auswertung_alle.SPUREN
        try:
            auswertung_alle.SPUREN = tuple(
                s for s in gespeichert if s != "liq_wand")
            auswertet = set(auswertung_alle.SPUREN) | set(EIGENE_AUSWERTUNG)
            fehlen = {s for s in dauerlauf.SPUREN if s not in auswertet}
            self.assertIn("liq_wand", fehlen,
                          "ohne den Eintrag muss die Regel greifen")
        finally:
            auswertung_alle.SPUREN = gespeichert

    def test_gegenprobe_ratsche_ohne_eintrag(self):
        """Nimmt man scanner aus der Pruefliste, muss die Regel greifen."""
        gespeichert = pruefe_ratschen.SPUREN
        try:
            pruefe_ratschen.SPUREN = [x for x in gespeichert
                                      if x[0] != "scanner"]
            geprueft = set(x[0] for x in pruefe_ratschen.SPUREN) | set(RUHT)
            fehlen = {s for s in dauerlauf.SPUREN
                      if fuehrt_ratsche(s) and s not in geprueft}
            self.assertIn("scanner", fehlen,
                          "ohne den Eintrag muss die Regel greifen")
        finally:
            pruefe_ratschen.SPUREN = gespeichert


if __name__ == "__main__":
    unittest.main()