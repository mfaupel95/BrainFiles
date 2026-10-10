"""Gleichheitsrahmen fuer Phase 2 (Ansatz B, Spec 10.10.2026).

Eine vektorisierte Strategie darf eine Spur erst dann in bots.json ersetzen,
wenn sie auf derselben Kerzenreihe JEDE Kerze gleich entscheidet wie der
Adapter (hausspur_regeln.signale). Der Adapter ist die Referenz, weil er die
Haus-Regel importiert statt sie nachzubauen.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hausspur_regeln as hr                                   # noqa: E402


def vergleiche(kerzen, name, b_einstieg, ab=0):
    """Abweichungen (index, A, B) ab Kerze `ab`; leer heisst gleich."""
    if len(b_einstieg) != len(kerzen):
        raise ValueError("B liefert %d Werte fuer %d Kerzen" % (len(b_einstieg), len(kerzen)))
    a = hr.signale(kerzen, name, ab=ab)
    return [(i, (a[i] or {}).get("einstieg"), b_einstieg[i])
            for i in range(ab, len(kerzen))
            if (a[i] or {}).get("einstieg") != b_einstieg[i]]
