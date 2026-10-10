"""Wache: carry.py auf Spuren mit positivem Netto.

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst
nichts zu melden**, es wird nichts gesendet (Watchdog-Muster).
Nur eine Zeile mit positivem netto_bp nach Gebuehren wird gemeldet -
sonst waere jede Ausgabe des Scanners eine Nachricht, die niemand
liest.

WARUM ES DIESE WACHE GIBT
-----------------------------
Die Messung vom 04.10.2026 zeigt: auf den fuer uns erreichbaren
Maerkten (OKX Spot/Perp, Kraken Spot/Futures) bleibt nach Gebuehren
nichts uebrig - die groesste echte Luecke war 0,012 % gegen 0,60 %
Kraken-Spot-Gebuehr je Seite. carry.py stellt die Zahlen hin; diese
Wache meldet erst, wenn EIN Basiswert die Rechnung traegt.

WAS ES NICHT TUT
----------------
Es handelt nicht, es ordert nicht, es schreibt in keine Spur, es
schaltet nichts scharf. Es ruft carry.py auf und filtert die Ausgabe
auf positive Netto-Spalten. Ein leeres Ergebnis ist der Normalfall -
die Stille ist gewollt und kein Fehler.

Aufruf:
    python Agenten/Hermes/scripts/carry-wache.py
    python Agenten/Hermes/scripts/carry-wache.py --vorschau  # nur anzeigen
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # Agenten/Hermes/scripts/ -> BrainFiles
CARRY = WURZEL / "Agenten" / "Handel" / "carry.py"
MERKDATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "carry-wache.json"
# Ein Basiswert gilt als positiv nur wenn netto_bp darueber: jede Runde
# kostet Gebuehren - ein Netto von 1 bp ist Rauschen und kein Signal.
MIN_NETTO_BP = 2.0
# Taegliche Obergrenze fuer Meldungen, damit ein kleiner positiver
# Basiswert nicht taeglich als Feststellung wiederholt wird.
MAX_MELDUNGEN_PRO_TAG = 3


def lade_carry(argv: list[str]) -> tuple[list[dict], list[str], str]:
    """carry.py als Kindprozess aufrufen. Rueckgabe: (zeilen, fehler, stdout)."""
    if not CARRY.exists():
        return [], ["carry.py nicht gefunden: %s" % CARRY], ""
    env = os.environ.copy()
    # PYTHONHOME/PYTHONPATH entfernen, falls vom Venv-Umfeld uebernommen
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    r = subprocess.run(
            [sys.executable, str(CARRY), "--json", *argv],
            capture_output=True, text=True, timeout=120, env=env,
            cwd=str(WURZEL / "Agenten" / "Handel"),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if r.returncode != 0:
        return [], ["carry.py exit %d: %s" % (r.returncode, r.stderr.strip())], r.stdout
    try:
        daten = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        return [], ["JSON-Fehler: %s" % e], r.stdout
    return daten.get("zeilen", []), daten.get("_fehler", []), r.stdout


def filter_positiv(zeilen: list[dict]) -> list[dict]:
    """Nur Zeilen mit positivem Netto nach Gebuehren."""
    raus = []
    for z in zeilen:
        try:
            netto = float(z.get("netto_bp") or 0)
        except (ValueError, TypeError):
            continue
        if netto > MIN_NETTO_BP:
            z["_netto_bp"] = netto
            raus.append(z)
    return raus


def meldung(zeilen: list[dict], erstellt: str) -> list[str]:
    if not zeilen:
        return []
    zeilen = sorted(zeilen, key=lambda z: -float(z.get("_netto_bp") or 0))
    out = ["carry.py: %d Basiswert(e) nach Gebuehren positiv (netto_bp > %.1f):"
           % (len(zeilen), MIN_NETTO_BP)]
    for z in zeilen[:MAX_MELDUNGEN_PRO_TAG]:
        out.append(
            "  %(basis)-5s  Basis %(basis_okx)s vs %(basis_kf)s  "
            "netto %(netto).1f bp  %(urteil)s" % {
                "basis": z.get("basis", "-"),
                "basis_okx": z.get("okx_basis_bp", "-"),
                "basis_kf": z.get("kraken_basis_bp", "-"),
                "netto": z.get("_netto_bp", 0),
                "urteil": z.get("urteil", "-"),
            }
        )
    if len(zeilen) > MAX_MELDUNGEN_PRO_TAG:
        out.append("  ... und %d weitere" % (len(zeilen) - MAX_MELDUNGEN_PRO_TAG))
    out.append("erstellt %s" % erstellt)
    return out


def main(argv: list[str] | None = None) -> int:
    global MIN_NETTO_BP
    p = argparse.ArgumentParser(description="carry.py-Wache")
    p.add_argument("--vorschau", action="store_true",
                   help="Nur anzeigen, keine Meldung bei Positiv")
    p.add_argument("--min-netto", type=float, default=MIN_NETTO_BP,
                   help="Schwelle netto_bp (Standard %.1f)" % MIN_NETTO_BP)
    a = p.parse_args(argv)
    MIN_NETTO_BP = a.min_netto
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    zeilen, fehler, stdout = lade_carry([])
    if fehler:
        for f in fehler:
            print("FEHLER: %s" % f)
        return 0  # Wache meldet Fehler als Text, nicht als Ausnahme
    if not zeilen and not a.vorschau:
        return 0  # leere Ausgabe = nichts zu melden (Watchdog-Muster)

    # JSON-Zeitstempel zum Datumieren
    try:
        daten = json.loads(stdout)
        erstellt = daten.get("erstellt", "")[:10]
    except (json.JSONDecodeError, ValueError):
        erstellt = datetime.now(timezone.utc).date().isoformat()

    positiv = filter_positiv(zeilen)
    if a.vorschau:
        if not positiv:
            print("carry.py: keine Zeile mit netto_bp > %.1f (rein lesend)" % MIN_NETTO_BP)
        for z in positiv:
            print("%(basis)-5s netto %(netto).1f bp  %(urteil)s" % {
                "basis": z.get("basis", "-"),
                "netto": z["_netto_bp"],
                "urteil": z.get("urteil", "-"),
            })
        return 0

    text = "\n".join(meldung(positiv, erstellt))
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())