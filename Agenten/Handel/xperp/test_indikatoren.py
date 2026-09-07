"""Test fuer volumen_drift() in indikatoren.py - keine Pytest-Infrastruktur im
Projekt, deshalb reine Asserts wie hier ueblich (`reine Rechnung, keine
Netzzugriffe`). Direkt ausfuehrbar: python test_indikatoren.py
"""

from indikatoren import volumen_drift

TS0 = 1_700_000_000_000
BAR_MS = 14_400_000  # 4h, wie BAR im Bot


def kerzen(phasen):
    """Baut eine Kerzenreihe aus Phasen [(anzahl, drift, volumen), ...].
    volumen kann eine Zahl (konstant) oder (start, ende) fuer eine Rampe sein.
    """
    k = []
    preis = 100.0
    i = 0
    for anzahl, drift, volumen in phasen:
        for j in range(anzahl):
            o = preis
            preis += drift
            c = preis
            h, l = max(o, c) + 0.05, min(o, c) - 0.05
            if isinstance(volumen, tuple):
                v = volumen[0] + (volumen[1] - volumen[0]) * (j / max(1, anzahl - 1))
            else:
                v = volumen
            k.append([TS0 + i * BAR_MS, o, h, l, c, v])
            i += 1
    return k


def test_uptrend_mit_frischem_volumenschub_ist_long():
    # durchgehender Aufwaertstrend, aber Volumen erst in den letzten 15 Kerzen
    # deutlich ueber dem langjaehrigen Schnitt - kuerzer als n=20, damit das
    # Vergleichsfenster davor noch komplett in der alten Volumenlage liegt
    k = kerzen([(285, 0.3, 1000), (15, 0.3, 2200)])
    z = volumen_drift(k, n=20)
    assert z["richtung"] == 1, z
    assert z["stark"] is True, z


def test_downtrend_mit_frischem_volumenschub_ist_short():
    k = kerzen([(285, -0.3, 1000), (15, -0.3, 2200)])
    z = volumen_drift(k, n=20)
    assert z["richtung"] == -1, z
    assert z["stark"] is True, z


def test_drift_ohne_volumenanstieg_gibt_kein_signal():
    k = kerzen([(300, 0.3, 1000)])  # Trend da, aber Volumen konstant -> Filter greift
    z = volumen_drift(k, n=20)
    assert z["richtung"] == 0, z


def test_widerspruch_zwischen_zeitebenen_gibt_kein_signal():
    # lange, ausgepraegte Abwaertsphase, danach kurze, milde Aufwaertsphase mit
    # anziehendem Volumen: Basisebene (letzte 20 Kerzen) zeigt long, die 4x-
    # Ebene (letzte 80 Kerzen) wird noch vom Abwaertsteil dominiert -> Konflikt
    k = kerzen([
        (260, -1.2, 800),
        (40, 0.3, (800, 2200)),
    ])
    z = volumen_drift(k, n=20)
    assert z["richtung"] == 0, z


def test_zu_wenig_historie_ist_sicher_leer():
    k = kerzen([(10, 0.3, 1000)])
    z = volumen_drift(k, n=20)
    assert z["richtung"] == 0, z
    assert z["n"] == len(k)


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("OK", t.__name__)
    print("Alle Tests bestanden (%d)" % len(tests))
