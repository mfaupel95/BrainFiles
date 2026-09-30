"""Automatik-Kopplung: Engine (t_9f7db046) und Reaktionsschicht (t_f682e5c1).

Das Paket haelt selbst keinen Zustand. Es liest das Lauf-Log der Engine, legt
jede neue Zeile der Reaktionsschicht vor und traegt deren Bitten (Nachlauf,
Sperre) zurueck in die Engine. Gestartet wird ausschliesslich ueber die
Engine-Steuerung - siehe automatik/kopplung.py, Modulkopf.

    python -m automatik durchgang [--probe]
    python -m automatik stand
    python -m automatik nachholen [--probe]
"""
from __future__ import annotations

__all__ = ["kopplung", "pfade"]
