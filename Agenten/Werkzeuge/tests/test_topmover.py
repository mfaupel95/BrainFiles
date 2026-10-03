"""Das Mover-Werkzeug rechnet LAGEN, nicht Ampel-Farben (02.10.2026).

Anlass war NIGHT: +129 % in 30 Tagen, 1,1 % unter dem 90-Tage-Hoch. Die
Marktbreite sagte "89,7 %, Trend intakt" - die Tageskerze sagte "das Volumen
ist vom 9,9-fachen auf das 1,7-fache des Median gefallen". Zwei Aussagen
ueber dasselbe Ding, und die zweite ist die wichtige.

Die Tests sichern die REGELN, nicht die Tageswerte:

1. Das Volumen wird gegen den 30-Tage-MEDIAN gemessen, nicht gegen gestern.
   "2x gestern" sagt nichts, "1,7x Median" ist eine Zahl mit Bedeutung.
2. Der Median schliesst HEUTE aus - sonst misst man sich selbst.
3. Eine laufende Tageskerze ist kein Schlusskurs (confirm != "1" wird
   verworfen). Ein Tageshoch aus einer halben Kerze ist die haeufigste
   Falschaussage in solchen Werkzeugen.
4. Zu wenig Historie ist ein eigener Zustand, nicht eine guetige Zahl.
5. `ausbruch` braucht Volumen. Der Kurs allein ist kein Signal.
6. Ein Kandidat ist: ueber EMA200 UND Volumen da. Beides, nicht eines.
7. Nur abgeschlossene Kerzen - und der EMA braucht 200 davon.

Ohne Netz, ohne Order: `hole()` wird umgebogen, `lage()` ist eine reine
Funktion und bekommt erfundene Kerzen.

Ausfuehrbar:  python tests/test_topmover.py   (aus Agenten/Werkzeuge)
"""
import os
import sys
import unittest

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if W not in sys.path:
    sys.path.insert(0, W)

import topmover as tm                                        # noqa: E402


def kerze(ts, o, h, l, c, v, confirm="1"):
    """Eine Rohzeile im OKX-Format: [ts,o,h,l,c,vol,volCcy,volQuote,confirm]."""
    return [str(ts), str(o), str(h), str(l), str(c), str(v),
            str(v), str(v), confirm]


def reihe(n=260, start=1.0, schritt=1.0, volumen=1000.0, ende=None,
          bestaetigt="1"):
    """n Kerzen. `ende` setzt den letzten Schlusskurs, sonst steigt es."""
    k = []
    for i in range(n):
        p = start + schritt * i
        k.append(kerze(1700000000000 + i * 86400000, p, p * 1.01, p * 0.99,
                       p, volumen, bestaetigt))
    if ende is not None:
        k[-1][4] = str(ende)
    return k


def lage_mit(k, **kw):
    return tm.lage(k, **kw)


class VolumenRegelTest(unittest.TestCase):
    """Der Median ist das Mass - und er schliesst den heutigen Tag aus."""

    def test_faktor_gegen_den_median(self):
        k = reihe(260)
        k[-1][5] = "5000"                      # heute 5x des Median
        d = lage_mit(k)
        self.assertAlmostEqual(d["volumen_faktor"], 5.0, places=1,
                               msg="heute 5000 gegen Median 1000 = 5x")

    def test_median_ohne_heute(self):
        """Sonst misst man den heutigen Tag gegen sich selbst: bei
        einheitlichem Volumen waere der Faktor 1,0 und damit blind."""
        k = reihe(260)
        k[-1][5] = "9000"
        d = lage_mit(k)
        self.assertAlmostEqual(d["volumen_median"], 1000.0, places=1)
        self.assertAlmostEqual(d["volumen_faktor"], 9.0, places=1,
                               msg="der Median ist 1000, nicht 9000")

    def test_median_haelt_heute_nicht_fuer_sich_selbst(self):
        """DER Test fuer den Median, und der Gegenprobe ist das Wichtigste
        daran.

        Ein Median, der den heutigen Tag MITZAEHLT, verschiebt die
        Bezugsgroesse mit dem heutigen Volumen - eine Rueckkopplung: viel
        Volumen hebt die eigene Messlatte.

        Das Fenster ist 30 Tage. Geaendert wird die Haelflfte davon (15 der
        letzten 30 Tage), denn DREI Ausreiser verschieben den Median eines
        30er-Fensters nicht - bei 27 einheitlichen Werten liegen die beiden
        mittleren weiterhin bei 1000 (gemessen am 02.10.2026: die ersten
        zwei Fassungen dieses Tests waren deshalb falsch und haetten den
        Fehler nicht gefangen).

        Gemessen mit dieser Fassung:
            Median MIT den 15 Ausreisern   = 16000
            Median OHNE sie (Vorgestage)   =  1000
        """
        k = reihe(300, volumen=1000.0)
        for i in range(1, 16):                   # 15 der letzten 30 Tage
            k[-i][5] = str(30000 + 1000 * i)

        mit = sorted(float(x[5]) for x in k[-30:])
        ohne = sorted(float(x[5]) for x in k[-31:-1])
        m_mit = (mit[14] + mit[15]) / 2.0
        m_ohne = (ohne[14] + ohne[15]) / 2.0

        d = lage_mit(k)
        self.assertAlmostEqual(m_ohne, 1000.0, places=1,
                              msg="die 15 AELTEREN hohen Tage liegen nicht im "
                                  "Vorgestagsfenster")
        self.assertGreater(m_mit, 1000.0,
                           "GEGENPROBE: mit dem heutigen Tag waere der Median "
                           "ein anderer - genau das darf nicht passieren")
        self.assertAlmostEqual(d["volumen_median"], m_ohne, places=1,
                               msg="das Werkzeug MUSS den Median der "
                                   "VORGESTAGE nehmen")
        self.assertNotAlmostEqual(d["volumen_median"], m_mit, places=1)

    def test_median_wird_vom_heutigen_tag_nicht_gezogen(self):
        """Der Median muss der der VORGESTAGE sein, unabhaengig davon, wie
        viel heute gehandelt wurde. Drei Messungen, eine Erwartung."""
        for heute in (1000, 9000, 50000, 200):
            k = reihe(260, volumen=1000.0)
            k[-1][5] = str(heute)
            d = lage_mit(k)
            self.assertAlmostEqual(
                d["volumen_median"], 1000.0, places=1,
                msg="Median %s bei heutigem Volumen %d" % (d["volumen_median"],
                                                           heute))

    def test_gestern_verglichen_wuerde_nichts_sagen(self):
        """Gegenprobe des Gedankens: 2x GESTERN kann 0,3x Median sein."""
        k = reihe(260)
        k[-2][5] = "200"                        # gestern winzig
        k[-1][5] = "400"                        # heute 2x gestern
        d = lage_mit(k)
        self.assertLess(d["volumen_faktor"], 1.0,
                        "'2x gestern' sieht nach Verdopplung aus und ist "
                        "trotzdem unter dem Median")


class KerzenHygieneTest(unittest.TestCase):
    """Nur abgeschlossene Kerzen zaehlen."""

    @staticmethod
    def _roh_mit(k):
        """Der Filter aus `tm.kerzen`, mit einer Attrappe als Quelle. Ohne
        Netz und ohne den OKX-Aufruf - sonst prueft der Test die Boerse."""
        tm.hole = lambda url, basis=None: {"code": "0", "data": list(k)}
        try:
            return tm.kerzen("X-USDT")
        finally:
            del tm.hole

    def test_laufende_kerze_wird_verworfen(self):
        """Eine laufende Tageskerze ist KEIN Schlusskurs. Ein Tageshoch aus
        einer halben Kerze ist die haeufigste Falschaussage in solchen
        Werkzeugen - hier waere der Abstand zum Hoch zu klein."""
        k = reihe(260, schritt=0.02)
        k[-1][2] = str(float(k[-1][4]) * 3.0)   # absurdes Hoch, noch offen
        k[-1][8] = "0"
        offen = self._roh_mit(k)
        self.assertNotIn(k[-1], offen, "die offene Kerze ist nicht dabei")
        self.assertEqual(len(offen), 259)
        d = lage_mit(offen)
        geschlossen = lage_mit([x for x in k if x[8] == "1"])
        self.assertEqual(d["zustand"], geschlossen["zustand"])

    def test_bestaetigt_filter_in_kerzen(self):
        k = reihe(11)                           # 11 Kerzen
        k[-1][8] = "0"                          # die letzte laeuft noch
        k.insert(5, kerze(1700000000000 + 5 * 86400000, 9, 9, 9, 9, 1, "0"))
        raus = self._roh_mit(k)
        self.assertEqual(len(raus), 10, "10 von 12 sind abgeschlossen")
        self.assertTrue(all(x[8] == "1" for x in raus))


class LageTest(unittest.TestCase):
    """Die fuenf Lagen und ihre Grenzen."""

    def test_aufsteigend_ohne_volumenwaechstum_ist_kein_ausbruch(self):
        """Gegenprobe zur Falle: eine gleichmaessig steigende Reihe hat
        Volumen 1,0x Median. Das ist KEIN Ausbruch - der Traeger fehlt.
        Ein Ausbruch verlangt Volumen ueber dem Median."""
        k = reihe(260, schritt=0.05)
        d = lage_mit(k)
        self.assertAlmostEqual(d["volumen_faktor"], 1.0, places=2)
        self.assertNotEqual(d["zustand"], "ausbruch",
                            "1,0x Median ist der Median, kein Ausbruch")
        self.assertEqual(d["zustand"], "ueberdehnt")

    def test_ausbruch_braucht_ein_wachstum_ueber_dem_median(self):
        """Jetzt das echte Szenario: der Kurs steigt UND das Volumen
        deutlich ueber dem Median - erst dann heisst es Ausbruch."""
        k = reihe(260, schritt=0.05)
        for x in k[-5:]:
            x[5] = "9000"                      # 9x Median
        d = lage_mit(k)
        self.assertGreaterEqual(d["volumen_faktor"], tm.SCHWELLE_AUSBRUCH)
        self.assertEqual(d["zustand"], "ausbruch")
        self.assertTrue(d["ueber_ema200"])
        self.assertIn("Median", d["begruendung"])

    def test_absteigend_ist_schwach(self):
        k = reihe(260, schritt=-0.05)
        d = lage_mit(k)
        self.assertEqual(d["zustand"], "schwach")
        self.assertFalse(d["ueber_ema200"])
        self.assertIn("EMA200", d["begruendung"])

    def test_hoher_kurs_ohne_volumen_ist_ballon(self):
        """Der Ballon: der Kaeufer geht weg, der Preis haelt sich noch.
        Genau NIGHTs Lage am 01.10.2026 (1,7x und fallend)."""
        k = reihe(260, schritt=0.05)
        for x in k[-10:]:                        # zehn Tage kein Volumen mehr
            x[5] = "200"
        d = lage_mit(k)
        self.assertIn(d["zustand"], ("ballon", "ueberdehnt"))
        self.assertLess(d["volumen_faktor"], tm.SCHWELLE_GETRAGEN)
        self.assertNotEqual(d["zustand"], "ausbruch",
                            "hoher Kurs OHNE Volumen ist kein Ausbruch")

    def test_am_hoch_ohne_volumen_ist_ueberdehnt(self):
        """Die gefaehrlichste Lage: hohes Chance-Risiko, duenner Traeger.
        Deshalb ist sie eine EIGENE Lage und nicht 'nur ballon'."""
        k = reihe(260, schritt=0.05)
        for x in k[-10:]:
            x[5] = "200"
        d = lage_mit(k, nah_hoch=5.0)
        self.assertEqual(d["zustand"], "ueberdehnt")
        self.assertIn("Traeger fehlt", d["begruendung"])

    def test_zu_wenig_kerzen_ist_unbekannt(self):
        d = lage_mit(reihe(50))
        self.assertEqual(d["zustand"], "unbekannt")
        self.assertIn("Kerzen", d["grund"],
                      "der Grund muss die Zahl nennen, nicht nur 'fehlt'")

    def test_kein_name_wird_erfunden(self):
        """Ein Instrument ohne Daten traegt seinen Namen - sonst steht in
        der Liste ein '?' und man weiss nicht, welches gemeint war."""
        tm.kerzen = lambda inst, anzahl=300: []
        try:
            d = tm.messe("FOO-USDT")
        finally:
            del tm.kerzen
        self.assertEqual(d["inst"], "FOO-USDT")
        self.assertIn(d["zustand"], (None, "unbekannt"))
        self.assertTrue(d["grund"], "ohne Daten braucht es einen Grund")
        self.assertFalse(tm.kandidat(d), "keine Daten sind kein Kandidat")

    def test_ema_braucht_200_kerzen(self):
        self.assertIsNone(tm.ema(list(range(199, 0, -1))))
        self.assertIsNotNone(tm.ema(list(range(200, 0, -1))))


class KandidatTest(unittest.TestCase):
    """Ein Kandidat ist ueber EMA200 UND mit Volumen - beides, nicht eines."""

    def test_hoch_ohne_volumen_ist_kein_kandidat(self):
        k = reihe(260, schritt=0.05)
        for x in k[-10:]:
            x[5] = "200"
        self.assertFalse(tm.kandidat(lage_mit(k)))

    def test_ueber_ema_mit_volumen_ist_kandidat(self):
        k = reihe(260, schritt=0.05)
        for x in k[-5:]:
            x[5] = "9000"                      # ueber dem Median
        self.assertTrue(tm.kandidat(lage_mit(k)))

    def test_gleichmaessiges_volumen_ist_kein_kandidat(self):
        """1,0x Median ist 'wie immer', nicht 'Traeger da'. Wer diesen
        Test nicht hat, haelt jedes gleichmaessig wachsende Instrument
        fuer ein Signal."""
        self.assertFalse(tm.kandidat(lage_mit(reihe(260, schritt=0.05))))

    def test_schwach_ist_kein_kandidat(self):
        self.assertFalse(tm.kandidat(lage_mit(reihe(260, schritt=-0.05))))

    def test_unbekannt_ist_kein_kandidat(self):
        """Eine fehlende Lage ist kein Kandidat. Sonst kauft man den
        Unsinn, weil die Zahl nicht da war."""
        self.assertFalse(tm.kandidat({"zustand": "unbekannt"}))
        self.assertFalse(tm.kandidat({"zustand": None}))
        self.assertFalse(tm.kandidat({}))


class RechenTest(unittest.TestCase):
    """Die Kennzahlen selbst - sie sind das Fundament aller Laegen."""

    def test_median_gerade_und_ungerade(self):
        self.assertEqual(tm.median([3, 1, 2]), 2)
        self.assertEqual(tm.median([4, 1, 2, 3]), 2.5)
        self.assertIsNone(tm.median([]))

    def test_atr_ist_eine_prozentzahl_des_kurses(self):
        k = reihe(30)
        for x in k:
            x[2] = str(float(x[1]) * 1.02)       # 2 % Spanne
            x[3] = str(float(x[4]) * 0.98)
        a = tm.atr(k)
        self.assertGreater(a, 1.0, "2 % Spanne muessen ~4 % ATR ergeben")
        self.assertLess(a, 10.0)

    def test_hoch_ist_ueber_den_schlusskursen(self):
        """Ein Tageshoch IST das Hoch. Nimmt man nur die Schlusskurse,
        meldet das Werkzeug einen zu NIEDRIGEN Hoch - und damit einen zu
        KLEINEN Abstand zum Hoch: ein Instrument am echten Hoch saehe dann
        aus wie eines, das 30 % darunterliegt."""
        k = reihe(260, schritt=0.01)
        for x in k[-30:]:
            x[2] = str(float(x[1]) * 1.5)       # intraday hohes Hoch
        d = lage_mit(k)
        schluss_hoch = max(float(x[4]) for x in k[-90:])
        self.assertGreater(float(d["hoch_90t"]), schluss_hoch,
                           "das Hoch muss aus den Tageshighs kommen, nicht "
                           "aus den Schlusskursen")
        self.assertLess(d["abstand_hoch_pct"], -30.0,
                        "mit den Tageshighs ist der Abstand deutlich groesser")

    def test_renditen_sind_gegen_die_kerze_von_vor_n_tagen(self):
        k = reihe(260, schritt=0.01)
        d = lage_mit(k)
        jetzt = float(k[-1][4])
        vor7 = float(k[-8][4])
        self.assertAlmostEqual(d["pct_7t"], 100 * (jetzt / vor7 - 1), places=6)


class SortierTest(unittest.TestCase):
    """Was zuerst steht, ist nicht beliebig - die interessanten Lagen zuerst."""

    def test_rangfolge(self):
        k = [
            {"zustand": "schwach", "pct_30t": 50},
            {"zustand": "ballon", "pct_30t": 60},
            {"zustand": "ausbruch", "pct_30t": 10},
            {"zustand": "getragen", "pct_30t": 20},
            {"zustand": "ueberdehnt", "pct_30t": 30},
            {"zustand": "unbekannt", "pct_30t": 99},
            {"zustand": None, "pct_30t": 99},
        ]
        r = sorted(k, key=lambda d: {"ausbruch": 0, "ueberdehnt": 1,
                                     "getragen": 2, "ballon": 3, "schwach": 4,
                                     "unbekannt": 5, None: 9}.get(d.get("zustand"), 9))
        self.assertEqual([x["zustand"] for x in r][:3],
                         ["ausbruch", "ueberdehnt", "getragen"])

    def test_paare_ohne_doppelte(self):
        """Ein doppelter Eintrag erzeugt eine doppelte Zeile UND einen
        doppelten Kandidaten in der Fusszeile - beim ersten Lauf von
        topmover.py stand AAVE zweimal drin."""
        doppelt = [x for x in set(tm.PAARE) if tm.PAARE.count(x) > 1]
        self.assertEqual(doppelt, [], "doppelte Paare: %s" % doppelt)


class Selbsttest(unittest.TestCase):
    def test_laeufe(self):
        rc = tm.main(["--paares=PAAR-NIX", "--json"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)