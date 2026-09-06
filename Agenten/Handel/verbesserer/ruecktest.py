"""Walk-Forward-Backtest fuer den Marktscanner.

Teil 1: merkmals_matrix() rechnet die neun ungewichteten Bausteine je (Wert,
Tag) EINMAL vor. Danach kostet das Bewerten eines Kandidaten nur noch
Gewichtung und Tore - die Gewichtssuche wird fast kostenlos.
"""

import bewertung

MINDEST_KERZEN = 120


def merkmals_matrix(kerzen_je_inst):
    aus = {}
    for inst, kerzen in kerzen_je_inst.items():
        reihe = {}
        for t in range(MINDEST_KERZEN, len(kerzen)):
            reihe[t] = bewertung.roh_komponenten(kerzen[: t + 1])
        aus[inst] = reihe
    return aus
