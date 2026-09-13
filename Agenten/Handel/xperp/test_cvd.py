"""Tests fuer cvd.py (CVD-4h-Divergenz) und ihre Einbindung in lage().

Keine Pytest-Infrastruktur im Projekt, deshalb reine Asserts wie in
test_indikatoren.py. Kein Test darf das Netz erreichen: cvd_4h() bekommt seine
Quellen als Modulattribute von okxf untergeschoben, lage() seine CVD-Lage ueber
den Seam indikatoren.cvd_quelle.

Direkt ausfuehrbar: python test_cvd.py
"""

import cvd
import indikatoren
import okxf

TS0 = 1_700_000_000_000
BAR_MS = cvd.BAR_MS


def kerzen(schlusskurse, versatz=0.5):
    """Kerzenreihe aus einer Liste von Schlusskursen - hoch/tief als
    Versatz um den Schluss, Volumen konstant."""
    k = []
    for i, c in enumerate(schlusskurse):
        o = schlusskurse[i - 1] if i else c
        k.append([TS0 + i * BAR_MS, o, c + versatz, c - versatz, c, 1000.0])
    return k


def tape(deltas, neueste_zuerst=True):
    """Taker-Volumen-Reihe zu einer Liste von Deltas (kauf - verkauf).
    OKX liefert neueste zuerst, je Zeile [ts, verkauf, kauf]."""
    reihen = []
    for i, d in enumerate(deltas):
        # Delta = kauf - verkauf; Verkauf fest auf 100, Kauf = 100 + Delta
        verkauf = 100.0
        reihen.append([TS0 + i * BAR_MS, verkauf, verkauf + d])
    return list(reversed(reihen)) if neueste_zuerst else reihen


# --- reihen(): Ausrichtung und CVD -------------------------------------------------

def test_reihen_bildet_cvd_als_laufende_summe():
    k = kerzen([100.0 + i for i in range(12)])
    t = tape([10.0, -5.0] * 6)
    paare, cvd_werte = cvd.reihen(k, t, eimer=12)
    assert len(paare) == 12 and len(cvd_werte) == 12
    assert cvd_werte == [10.0, 5.0, 15.0, 10.0, 20.0, 15.0,
                         25.0, 20.0, 30.0, 25.0, 35.0, 30.0], cvd_werte


def test_reihen_braucht_ein_lueckenloses_fenster():
    k = kerzen([100.0] * 12)
    # ein Eimer fehlt in der Mitte -> keine zusammenhaengende Reihe
    t = [r for r in tape([1.0] * 12) if int(r[0]) != TS0 + 5 * BAR_MS]
    assert cvd.reihen(k, t, eimer=12) == (None, None)


def test_reihen_zu_wenig_eimer():
    k = kerzen([100.0] * 12)
    assert cvd.reihen(k, tape([1.0] * 5), eimer=12) == (None, None)


# --- divergenz(): die vier Faelle -------------------------------------------

def test_baerische_divergenz_preis_hoch_cvd_runter():
    # erste Haelfte flach bei 100, zweite steigt auf 110 (neues Hoch), Delta
    # dreht in der zweiten Haelfte ins Negative -> Verteilung am Hoch
    k = kerzen([100.0, 100.2, 100.4, 100.6, 100.8, 101.0,
                101.0, 102.8, 104.6, 106.4, 108.2, 110.0])
    t = tape([200.0] * 6 + [-100.0] * 6)
    paare, werte = cvd.reihen(k, t, eimer=12)
    z = cvd.divergenz(paare, werte)
    assert z["richtung"] == -1, z
    assert z["stark"] is True, z
    assert z["d_cvd"] < 0 < z["d_preis"], z


def test_bullische_divergenz_preis_runter_cvd_hoch():
    k = kerzen([110.0, 109.8, 109.6, 109.4, 109.2, 109.0,
                109.0, 107.2, 105.4, 103.6, 101.8, 100.0])
    t = tape([-200.0] * 6 + [100.0] * 6)
    paare, werte = cvd.reihen(k, t, eimer=12)
    z = cvd.divergenz(paare, werte)
    assert z["richtung"] == 1, z
    assert z["stark"] is True, z


def test_bestaetigter_aufwaertstrend_ist_keine_divergenz():
    # Preis steigt UND CVD steigt - kein Widerspruch, kein Signal
    k = kerzen([100.0 + i for i in range(12)])
    t = tape([50.0] * 12)
    paare, werte = cvd.reihen(k, t, eimer=12)
    z = cvd.divergenz(paare, werte)
    assert z["richtung"] == 0, z
    assert z["grund"] == "keine Divergenz", z


def test_divergenz_in_der_mitte_des_bereichs_zaehlt_nicht():
    # Frueherer Ausreisser nach oben (112), danach Aufwaertspreis 101 -> 103:
    # CVD faellt, aber der Kurs steht in der Mitte des Fensters - das ist
    # "rally ohne CVD" ohne Naehe zum Hoch, also kein Signal.
    k = kerzen([96.0, 96.0, 96.0, 112.0, 100.0, 100.0,
                101.0, 101.4, 101.8, 102.2, 102.6, 103.0])
    t = tape([200.0] * 6 + [-100.0] * 6)
    paare, werte = cvd.reihen(k, t, eimer=12)
    z = cvd.divergenz(paare, werte, min_bewegung=0.0)
    assert z["richtung"] == 0, z
    assert z["lage_im_bereich"] < cvd.NAEHE_HOCH, z


def test_mindestbewegung_ist_ein_schalter_nicht_geschmack():
    k = kerzen([100.0, 100.2, 100.4, 100.6, 100.8, 101.0,
                101.0, 102.8, 104.6, 106.4, 108.2, 110.0])
    t = tape([200.0] * 6 + [-100.0] * 6)
    paare, werte = cvd.reihen(k, t, eimer=12)
    assert cvd.divergenz(paare, werte)["richtung"] == -1
    # dieselbe Lage, nur mit einer Schwelle ueber der tatsaechlichen Bewegung
    assert cvd.divergenz(paare, werte, min_bewegung=0.9)["richtung"] == 0


def test_zu_kurzes_fenster_ist_kein_signal():
    k = kerzen([100.0, 101.0, 102.0])
    assert cvd.divergenz(k, [0.0, 1.0, 2.0])["richtung"] == 0
    assert cvd.divergenz(k, None)["richtung"] == 0
    # Laengen muessen zusammenpassen - sonst waere die Zuordnung geraten
    assert cvd.divergenz(kerzen([100.0] * 6), [0.0, 1.0])["richtung"] == 0


def test_cvd_untergrenze_schneidet_das_rauschband():
    """Eine abgeklungene Kauflut (-5 je Eimer) gegen einen klaren Preisanstieg
    ist keine Verteilung: die Steigung liegt unter MIN_CVD_ANTEIL."""
    k = kerzen([100.0, 100.2, 100.4, 100.6, 100.8, 101.0,
                101.0, 102.8, 104.6, 106.4, 108.2, 110.0])
    t = tape([200.0] * 6 + [-5.0] * 6)
    paare, werte = cvd.reihen(k, t, eimer=12)
    z = cvd.divergenz(paare, werte)
    assert z["richtung"] == 0, z
    assert abs(z["cvd_anteil"]) < cvd.MIN_CVD_ANTEIL, z
    # ohne die Untergrenze waere es eine baerische Divergenz
    assert cvd.divergenz(paare, werte, min_cvd_anteil=0.0)["richtung"] == -1


# --- cvd_4h(): Quellen als Seam, Ausfall ist kein Absturz --------------------

class Quellen:
    """Schreibt okxf.taker_volumen/kerzen fuer die Dauer des with-Blocks um."""

    def __init__(self, tape_reihe, kerzen_reihe=None):
        self.tape = tape_reihe
        self.k = kerzen_reihe
        self.alt = (okxf.taker_volumen, okxf.kerzen)

    def __enter__(self):
        def tape_fn(inst, period="4H"):
            if isinstance(self.tape, Exception):
                raise self.tape
            return self.tape

        def kerzen_fn(inst, bar="1H", anzahl=300):
            return self.k

        okxf.taker_volumen = tape_fn
        okxf.kerzen = kerzen_fn
        return self

    def __exit__(self, *a):
        okxf.taker_volumen, okxf.kerzen = self.alt
        return False


K12 = kerzen([100.0, 100.2, 100.4, 100.6, 100.8, 101.0,
              101.0, 102.8, 104.6, 106.4, 108.2, 110.0])
T12 = tape([200.0] * 6 + [-100.0] * 6)


def test_cvd_4h_liest_tape_und_kerzen():
    with Quellen(T12, K12):
        z = cvd.cvd_4h("TEST-USDT-SWAP")
    assert z["richtung"] == -1 and z["eimer"] == 12, z
    assert z["grund"] == "", z
    assert cvd.marke(z).startswith("CVD-4h-Divergenz bearish"), cvd.marke(z)


def test_cvd_4h_ohne_tape_ist_neutral_mit_grund():
    with Quellen([], K12):
        z = cvd.cvd_4h("TEST-USDT-SWAP")
    assert z["richtung"] == 0 and z["n"] == 0, z
    # Der Grund muss den HOST nennen: auf my.okx.com/eea.okx.com kommt eine
    # leere Liste ohne Fehler - "leer" allein laesst sich nicht deuten.
    assert "Host" in z["grund"] and "okx.com" in z["grund"], z["grund"]
    assert cvd.marke(z) == "", z


def test_taker_volumen_fragt_den_rubik_host_und_den_vollen_instid():
    """Der Abruf darf nicht ueber OKX_BASE laufen (dort kommt eine leere
    Liste) und muss Instrument und Periode mitgeben."""
    gesehen = {}
    alt = okxf._roh

    def fake(pfad, *a, **kw):
        gesehen["pfad"] = pfad
        gesehen["basis"] = kw.get("basis")
        return [["1700000000000", "10", "20"]]

    okxf._roh = fake
    try:
        r = okxf.taker_volumen("TEST-USDT-SWAP", "4H")
    finally:
        okxf._roh = alt
    assert gesehen["pfad"].startswith("/api/v5/rubik/stat/taker-volume-contract?"), gesehen
    assert "instId=TEST-USDT-SWAP" in gesehen["pfad"], gesehen
    assert "period=4H" in gesehen["pfad"], gesehen
    assert gesehen["basis"] == okxf.rubik_basis(), gesehen
    assert gesehen["basis"].startswith("https://"), gesehen
    assert r == [[1700000000000, 10.0, 20.0]], r


def test_cvd_4h_zu_wenig_tiefe_ist_neutral_mit_grund():
    with Quellen(tape([5.0] * 6), K12):
        z = cvd.cvd_4h("TEST-USDT-SWAP")
    assert z["richtung"] == 0, z
    assert "lueckenloses" in z["grund"], z


def test_cvd_4h_ueberlebt_einen_ausfall_der_quelle():
    with Quellen(RuntimeError("kein Netz"), K12):
        z = cvd.cvd_4h("TEST-USDT-SWAP")
    assert z["richtung"] == 0, z
    assert "kein Netz" in z["grund"] and "Host" in z["grund"], z["grund"]


def test_cvd_4h_wiederholt_ein_429_einmal():
    """Too Many Requests heilt durch Warten - anders als ein falsches
    Instrument. Der zweite Anlauf muss greifen."""
    versuche = {"n": 0}
    original = okxf.taker_volumen

    def mal_429(inst, period="4H"):
        versuche["n"] += 1
        if versuche["n"] == 1:
            raise okxf.OKXFehler("OKX 50011: Too Many Requests")
        return T12

    with Quellen(T12, K12):
        okxf.taker_volumen = mal_429
        z = cvd.cvd_4h("TEST-USDT-SWAP")
        okxf.taker_volumen = original
    assert versuche["n"] == 2, versuche
    assert z["richtung"] == -1, z


# --- Einbindung in lage(): Rang, Ausfall und Rueckwaertskompatibilitaet -------

def lage_kerzen():
    """300 4h-Kerzen mit Aufwaertstrend und frischem Volumenschub - so, wie
    volumen_drift() es fuer ein LONG-Signal braucht."""
    kurse, preis = [], 100.0
    for i in range(300):
        preis += 0.3 if i < 285 else 0.3
        kurse.append(round(preis, 4))
    k = kerzen(kurse)
    for i, row in enumerate(k):
        row[5] = 2200.0 if i >= 285 else 1000.0
    return k


def lage_kerzen_ruhig(anzahl=300):
    """Dieselbe Reihe, aber ruhiger: vier Schritte auf, einer zurueck. Der
    Trend bleibt (volumen_drift long, empirisch nachgemessen: RSI 70,
    Score +0.18), RSI bleibt unter der Ueberkauft-Wache - die braucht es fuer
    den Bestaetigungsfall."""
    kurse, preis = [], 100.0
    for i in range(anzahl):
        preis += -0.5 if i % 5 == 4 else 0.35
        kurse.append(round(preis, 4))
    k = kerzen(kurse)
    for i, row in enumerate(k):
        row[5] = 2200.0 if i >= anzahl - 15 else 1000.0
    return k


def lauf_mit_cvd(richtung, basis_kerzen=None, inst="TEST-USDT-SWAP"):
    """lage() mit einer CVD-Lage aus den echten reinen Funktionen."""
    z = cvd.leer("kein Instrument im Aufruf")
    if richtung:
        kerzen_reihe = K12 if richtung == -1 else kerzen(
            [110.0, 109.8, 109.6, 109.4, 109.2, 109.0,
             109.0, 107.2, 105.4, 103.6, 101.8, 100.0])
        deltas = [200.0] * 6 + [-100.0] * 6 if richtung == -1 \
            else [-200.0] * 6 + [100.0] * 6
        paare, werte = cvd.reihen(kerzen_reihe, tape(deltas), eimer=12)
        z = cvd.divergenz(paare, werte)
    alt = indikatoren.cvd_quelle
    indikatoren.cvd_quelle = lambda i: z
    try:
        return indikatoren.lage(basis_kerzen if basis_kerzen is not None
                                else lage_kerzen(), inst=inst)
    finally:
        indikatoren.cvd_quelle = alt


def test_lage_ohne_instrument_bleibt_nutzbar():
    k = lage_kerzen()
    z = indikatoren.lage(k)
    assert z["cvd"]["richtung"] == 0, z["cvd"]
    assert z["cvd"]["grund"] == "kein Instrument im Aufruf", z["cvd"]
    # die uebrigen Komponenten rechnen unveraendert weiter
    assert z["signal"] in ("long", "short", "kein"), z


def test_cvd_ueberstimmt_das_bestehende_signal_als_letzte_komponente():
    basis = lauf_mit_cvd(None)
    assert basis["vol_drift"]["richtung"] == 1, basis["vol_drift"]
    z = lauf_mit_cvd(-1)
    assert z["signal"] == "short", z
    assert "CVD-4h-Divergenz bearish" in z["grund"], z["grund"]
    assert "ueberstimmt" in z["grund"], z["grund"]


def test_cvd_bestaetigt_ein_gleichlautendes_signal():
    k = lage_kerzen_ruhig()
    grundlauf = indikatoren.lage(k)
    assert grundlauf["vol_drift"]["richtung"] == 1, grundlauf["vol_drift"]
    assert grundlauf["rsi"] < 78, grundlauf["rsi"]
    assert grundlauf["signal"] == "long", grundlauf["signal"]
    z = lauf_mit_cvd(1, basis_kerzen=k)
    assert z["signal"] == "long", z
    assert "CVD-4h-Divergenz bullish" in z["grund"], z["grund"]
    assert "bestaetigt" in z["grund"], z["grund"]


def test_rsi_wache_bleibt_hinter_der_cvd_komponente():
    """Nachweis der Reihenfolge: die CVD-Komponente laeuft VOR der RSI-Wache.
    Liefe sie danach, stuende hier 'long' - denn das CVD-Signal ist bullish.
    (Die RSI-Wache ueberschreibt den Grundtext, das ist ihr vorhandenes
    Verhalten und bleibt so.)"""
    z = lauf_mit_cvd(1)
    assert z["cvd"]["richtung"] == 1, z["cvd"]
    assert z["signal"] == "kein", z
    assert "RSI" in z["grund"], z["grund"]


def test_abgeschaltete_quelle_ist_neutral_und_bricht_nichts():
    alt = indikatoren.cvd_quelle

    def kaputt(inst):
        raise RuntimeError("Quelle weg")

    indikatoren.cvd_quelle = kaputt
    try:
        z = indikatoren.lage(lage_kerzen_ruhig(), inst="TEST-USDT-SWAP")
    finally:
        indikatoren.cvd_quelle = alt
    assert z["signal"] == "long", z
    assert "CVD-Lage nicht lesbar" in z["cvd"]["grund"], z["cvd"]


def test_fertige_cvd_lage_schlaegt_die_quelle():
    """Der Testweg (cvd_lage=) geht vor, auch ohne Instrument."""
    z = indikatoren.lage(lage_kerzen(), cvd_lage=cvd.leer("mitgegeben"))
    assert z["cvd"]["grund"] == "mitgegeben", z["cvd"]


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("OK", t.__name__)
    print("Alle Tests bestanden (%d)" % len(tests))
