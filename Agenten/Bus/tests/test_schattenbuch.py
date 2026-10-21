"""Test fuer schattenbuch.py (reine Rechnung, kein Netz). Direkt ausfuehrbar: python tests/test_schattenbuch.py"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import schattenbuch as sb   # noqa: E402


def test_flache_reihe_gibt_gewicht_null():
    assert max(sb.gewichte([100.0] * 600)) == 0.0


def test_steigende_reihe_gibt_positives_gewicht_unter_deckel():
    c = [100.0 * (1.0005 ** i) + math.sin(i) * 0.05 for i in range(2600)]
    w = sb.gewichte(c)
    assert 0.0 < w[-1] <= 1.0 and all(0.0 <= x <= 1.0 for x in w)


def test_verlauf_voll_investiert_ist_buy_and_hold_ohne_umschichtung():
    c = [100.0 + i for i in range(50)]
    w = [1.0] * 50
    eq, bh = sb.verlauf(c, w, 10)
    assert abs(eq - bh * (1 - sb.KOST)) < 1e-9   # nur der Einstieg kostet


def test_verlauf_flat_bleibt_eins():
    c = [100.0 + i for i in range(50)]
    eq, bh = sb.verlauf(c, [0.0] * 50, 10)
    assert eq == 1.0 and bh > 1.0


def test_umschichtung_kostet():
    c = [100.0] * 20
    w = [0.0] * 10 + [1.0] * 10
    eq, _ = sb.verlauf(c, w, 5)
    assert eq < 1.0


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            f()
    print("schattenbuch bestanden")
