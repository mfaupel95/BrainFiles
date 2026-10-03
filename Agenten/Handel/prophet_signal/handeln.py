#!/usr/bin/env python3
"""Prophet-Signal: Saisonale Zerlegung + Trend als Handelsregel (CryptoPredictions Papier).

Basis: Facebook Prophet-Methode (aus CryptoPredictions-Papier 2023, Sharif University).
Regel: Long bei steigendem Trend-Forecast, Short bei fallendem.

Das Paper zeigt Prophet als bestes Modell für Crypto-Vorhersagen (MAE 83 vs 787-1140 bei
anderen Modellen). Diese Spur nutzt Prophets additive Saison-Zerlegung ohne echte Prophet-
Installation (NumPy-Kompatibilität) - stattdessen nachgebautes Modell mit exponentieller
Glättung + Saisonalität wie Prophet.

Aufruf: python handeln.py --vorschau | --papier | --wachen  (--live verweigert)
"""
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import prophet_regeln  # noqa: E402

if __name__ == "__main__":
    sys.exit(prophet_regeln.spur_main("prophet_signal", HIER,
                                      bus_name="handel/prophet_signal"))
