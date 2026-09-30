"""Belege- und Eingaben-Ermittlung fuer das Skill-Inventar (Kanban t_3d28119b)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risiko_marker import MARKER, QUELLEN, RANG  # noqa: E402


def belege(text):
    """(hoechste Klasse, Belegliste). Je Klasse wird ein Beleg festgehalten."""
    gefunden = []
    klasse = "none"
    zeilen = text.splitlines()
    for kl, marker in MARKER.items():
        treffer = None
        for nr, zeile in enumerate(zeilen, 1):
            klein = zeile.lower()
            for m in marker:
                if m in klein:
                    treffer = {"klasse": kl, "zeile": nr, "fund": m}
                    break
            if treffer:
                break
        if treffer:
            gefunden.append(treffer)
            if RANG[kl] > RANG[klasse]:
                klasse = kl
    return klasse, gefunden


def eingaben(kopf, text):
    """Welche Kontextquellen ein Skill anfasst (terminal, dateien, netz, ...)."""
    klein = text.lower()
    quellen = []
    if kopf.get("allowed-tools"):
        quellen.append("allowed-tools: " + kopf["allowed-tools"][:60])
    for name, marker in QUELLEN.items():
        if any(m in klein for m in marker):
            quellen.append(name)
    return quellen
