#!/usr/bin/env python3
"""LLM-Stunde: drei Indikator-Kandidaten auf 1H, je Regelarm (R) und LLM-Arm (L). Papier.

Jede Variante (ema1h, st1h, rsi1h) laeuft als eigener Strang mit eigenem Ordner
unter laeufe/<variante>-<arm>/, weil spur_buch je Ordner genau ein Buch fuehrt.

Aufruf: python handeln.py --vorschau | --papier | --wachen  (--live verweigert)
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(HIER))

import klassik_regeln as kr  # noqa: E402
import llm  # noqa: E402
import regeln  # noqa: E402


def entscheide(arm, kandidat, llm_erg, w):
    """Einstieg-Entscheid je Arm. R: Regel allein. L: Regel UND LLM ueber der Schwelle."""
    if kandidat != "long":
        return {"entscheid": "kein_einstieg", "grund": "kein Kandidat"}
    if arm == "R":
        return {"entscheid": "einstieg", "grund": "Regel"}
    if llm_erg is None:
        return {"entscheid": "kein_einstieg", "grund": "LLM nicht gefragt"}
    if llm.darf_einsteigen(llm_erg, w):
        return {"entscheid": "einstieg",
                "grund": f"LLM {llm_erg['urteil']} {llm_erg['konfidenz']}%"}
    return {"entscheid": "kein_einstieg",
            "grund": f"LLM {llm_erg['urteil']} {llm_erg['konfidenz']}%"}


def _quelle(w):
    """Kerzen je Instrument, nur abgeschlossene (klassik_regeln._kerzen)."""
    bar = w["kerzen_zeitrahmen"]
    anzahl = int(w["kerzen_anzahl"])
    daten, kurse, fehler = {}, {}, []
    for inst in w["instrumente"]:
        try:
            k = kr._kerzen(inst, bar, anzahl)
        except Exception as e:  # noqa: BLE001
            fehler.append(f"{inst}: Kerzen nicht abrufbar ({str(e)[:100]})")
            continue
        if not k:
            fehler.append(f"{inst}: keine Kerzen")
            continue
        daten[inst] = {"kerzen": k, "bar": bar, "inst": inst}
        kurse[inst] = float(k[-1][4])
    return daten, kurse, fehler


def _protokolliere(ordner, variante, arm, inst, kerze_ts, llm_erg, e):
    """Eine Zeile je LLM-Frage: Urteil, Konfidenz, Prompt-Hash, Rohgrund."""
    zeile = {
        "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kerze_ts": kerze_ts, "inst": inst, "variante": variante, "arm": arm,
        "urteil": llm_erg["urteil"], "konfidenz": llm_erg["konfidenz"],
        "prompt_hash": llm_erg["prompt_hash"], "grund": llm_erg["grund"],
        "entscheid": e["entscheid"],
    }
    with open(ordner / "llm_entscheide.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")


def _signal_fabrik(variante, arm, ordner, schreibe):
    def signal(d, w):
        k = d.get("kerzen") or []
        if len(k) < int(w.get("mindest_kerzen", 240)):
            return None
        kand = regeln.kandidat(variante, k, w)
        if kand is None:
            return None
        llm_erg = None
        if arm == "L":
            snap = llm.momentaufnahme(k, variante, kand, w["stop_prozent"])
            llm_erg = llm.frage(snap, w)
        e = entscheide(arm, kand, llm_erg, w)
        if arm == "L" and schreibe:
            _protokolliere(ordner, variante, arm, d.get("inst"), int(k[-1][0]), llm_erg, e)
        return kand if e["entscheid"] == "einstieg" else None
    return signal


def _ausstieg_fabrik(variante):
    def zusatz(p, w):
        if p.get("seite") != "long":
            return None
        try:
            k = kr._kerzen(p["inst"], w["kerzen_zeitrahmen"], int(w["kerzen_anzahl"]))
        except Exception:  # noqa: BLE001
            return None
        if not k:
            return None
        return "regel_" + variante if regeln.ausstieg(variante, k, w) else None
    return zusatz


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group()
    for opt, c, h in (("--vorschau", "vorschau", "nur rechnen, nichts schreiben"),
                      ("--papier", "papier", "Papierbuch (Standard)"),
                      ("--live", "live", "verweigert: kein Live-Zweig"),
                      ("--wachen", "wachen", "nur den Wachenstand zeigen")):
        g.add_argument(opt, action="store_const", dest="modus", const=c, help=h)
    modus = p.parse_args(argv).modus or "papier"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if modus == "live":
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier, Kursregel ohne Orderweg).")
        return 2

    w0 = json.loads((HIER / "wachen.json").read_text(encoding="utf-8"))
    # Jeder Arm spiegelt in EINEN eigenen Unterordner des Ziels, sonst
    # ueberschrieben sich die sechs Journale gegenseitig (T-413,
    # 19.10.2026). Das Haupt-Ziel bleibt als Basis bestehen.
    ziel_basis = w0.get("journal_zweitziel") or "Q:/Handel_Journal/llm_stunde"
    buch = kr._lade(HANDEL / "spur_buch.py", "spur_buch_llm_stunde")
    rc = 0
    for variante in w0["varianten"]:
        for arm in ("R", "L"):
            ordner = HIER / "laeufe" / f"{variante}-{arm}"
            ordner.mkdir(parents=True, exist_ok=True)
            w = dict(w0, _variante=variante, _arm=arm)
            w["journal_zweitziel"] = str(
                Path(ziel_basis) / f"{variante}-{arm}")
            (ordner / "wachen.json").write_text(
                json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
            rc = max(rc, buch.zyklus(
                str(ordner), _quelle,
                _signal_fabrik(variante, arm, ordner, schreibe=modus != "vorschau"),
                modus,
                ereignis_name=f"handel/llm_stunde/{variante}-{arm}",
                zusatz_ausstieg=_ausstieg_fabrik(variante)) or 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
