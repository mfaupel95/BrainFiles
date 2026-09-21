#!/usr/bin/env python3
"""Wache auf die ersten GESCHLOSSENEN Runden der Nautilus-Arme.

WARUM: Die drei Arme (nautilus, nautilus_kraken, nautilus_kraken_futures) haben
seit dem 15./19.09.2026 kein einziges Mal geschlossen - nur Einstiege und
Zyklus-Zeilen. Ihre Ausstiegsgeometrie (Trailing ab +30 %) erreicht BTC in einer
Woche nicht, deshalb ist die FRIST (168 h) der wirkliche Ausstieg. Der erste
faellige Ausstieg steht am 22.09.2026 gegen 00:05 UTC an.

Diese Wache meldet:
  1. jede NEUE geschlossene Runde (Symbol, Ausstiegspreis, G/V, Grund) - das ist
     die erste belastbare Zahl dieser Arme,
  2. eine UEBERFAELLIGE Position: Frist vorbei, aber seit ueber GRACE_MIN Minuten
     keine Ausstiegszeile. Dann laeuft der Arm nicht oder der Quotenpfad ist tot
     (genau der Fehler vom 21.09.2026, 08:41-10:16: "keine Quote angekommen").

LEERE AUSGABE = nichts senden. Zustand in
Agenten/Hermes/cache/nautilus-runden-wache.json.

Aufruf (Hermes-Cron, no_agent, alle 30 Minuten):
    python nautilus-runden-wache.py
    python nautilus-runden-wache.py --jetzt   # nur zeigen, nichts schreiben
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

HANDEL = Path(__file__).resolve().parents[2] / "Handel"
STAND = Path(__file__).resolve().parents[1] / "cache" / "nautilus-runden-wache.json"

AUSSTIEG = ("schliessen", "verkauf", "AUSSTIEG", "exit")
GRACE_MIN = 90               # so lange darf eine faellige Position noch offen sein

ARME = {
    "nautilus": {"journal": HANDEL / "nautilus" / "handelsjournal.csv",
                 "zustand": HANDEL / "nautilus" / "zustand.json", "waehrung": "USD"},
    "nautilus_kraken": {"journal": HANDEL / "nautilus_kraken" / "handelsjournal.csv",
                        "zustand": HANDEL / "nautilus_kraken" / "zustand.json",
                        "waehrung": "EUR"},
    "nautilus_kraken_futures": {"journal": HANDEL / "nautilus_kraken" / "handelsjournal.futures.csv",
                                "zustand": HANDEL / "nautilus_kraken" / "zustand.futures.json",
                                "waehrung": "USD"},
}


def _lies(pfad):
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return {}


def _zeit(wert):
    if not wert:
        return None
    try:
        d = dt.datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def _zahl(r, *namen):
    for n in namen:
        v = r.get(n)
        if v not in (None, ""):
            try:
                return float(v)
            except ValueError:
                continue
    return None


def zeilen(journal):
    p = Path(journal)
    if not p.is_file():
        return []
    with p.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def wache(schreiben: bool = True) -> int:
    stand = _lies(STAND)
    jetzt = dt.datetime.now(dt.timezone.utc)
    meldungen = []
    neu_stand = dict(stand)

    for name, cfg in ARME.items():
        rows = zeilen(cfg["journal"])
        raus = [r for r in rows if (r.get("aktion") or "").strip() in AUSSTIEG]
        vorher = int(stand.get(name, {}).get("ausstiege", 0))
        neu_stand.setdefault(name, {})["ausstiege"] = len(raus)
        if len(raus) > vorher:
            for r in raus[vorher:]:
                ein = _zahl(r, "einsatz_usd", "einsatz_eur")
                aus = _zahl(r, "wert_usd", "wert_eur")
                gv = ("%+.2f" % (aus - ein)) if (ein is not None and aus is not None) else "?"
                meldungen.append("%s: RUNDE ZU  %s  %s  G/V %s %s  (Grund %s)" % (
                    name, r.get("symbol") or r.get("inst") or "?",
                    (r.get("zeit") or "")[:16], gv, cfg["waehrung"], r.get("grund") or "?"))
        elif vorher == 0 and len(raus) == 0 and name not in stand:
            meldungen.append("%s: Beobachtung laeuft ab jetzt (noch kein Ausstieg; "
                             "Ausstieg ueber Stop, Trailing oder Frist)." % name)

        # ueberfaellige Position: Frist vorbei, keine Zeile
        z = _lies(cfg["zustand"])
        faellig = []
        for p in (z.get("positionen") or []):
            f = _zeit(p.get("frist"))
            if f and jetzt > f and (jetzt - f).total_seconds() > GRACE_MIN * 60:
                faellig.append((p.get("symbol") or "?", f))
        if faellig:
            letzte = max((_zeit(r.get("zeit")) or jetzt for r in raus), default=None)
            if letzte is None or (jetzt - letzte).total_seconds() > GRACE_MIN * 60:
                meldungen.append("%s: %d Position(en) ueber der Frist, aber keine "
                                 "Ausstiegszeile (aelteste Frist %s) - Quotenpfad pruefen."
                                 % (name, len(faellig),
                                    faellig[0][1].astimezone().strftime("%d.%m. %H:%M")))

    neu_stand["geprueft"] = jetzt.isoformat(timespec="seconds")
    if schreiben:
        STAND.parent.mkdir(parents=True, exist_ok=True)
        STAND.write_text(json.dumps(neu_stand, ensure_ascii=False, indent=1), encoding="utf-8")
    for m in meldungen:
        print(m)
    return 0


def main() -> int:
    jetzt = "--jetzt" in sys.argv
    return wache(schreiben=not jetzt)


if __name__ == "__main__":
    sys.exit(main())
