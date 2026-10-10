"""Verifiziere, dass die 22 pos_id-Positionen aus dem missing_modus_report
an der OKX Boerse NICHT als aktiv existieren.

Nur Lesezugriff (GET /account/positions, GET /trade/orders-pending).
Schreibt ein JSON-Ergebnis und einen Markdown-Bericht.
"""
import json
import os
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
if str(HANDEL) not in sys.path:
    sys.path.insert(0, str(HANDEL))

from scanner import okx  # noqa: E402

POS_IDS = [
    # omniquant (5)
    "20261002T151238-91e138",
    "20261003T101206-ef79ef",
    "20261003T171958-525bba",
    "20261005T050531-8765c7",
    "20261005T171420-8a9dfe",
    # scanner (5)
    "20261003T091012-79f418",
    "20261003T091012-04dbd7",
    "20261003T091012-b8c6c9",
    "20261001T080416-ebaeac",
    "20261002T044143-dfdcd2",
    # squeeze (5)
    "20261004T070603-0cc0f6",
    "20261004T070210-5f6879",
    "20261004T070609-dd6285",
    "20261003T131233-bd872d",
    "20261004T070209-803585",
    # supertrend (4)
    "20261002T081005-0730f7",
    "20261002T082524-9b1ba3",
    "20261002T084034-73481d",
    "20261002T085548-6bba4f",
    # wavetrend (3)
    "20261001T214828-c73b3a",
    "20261002T011141-62d810",
    "20261002T012649-172641",
]


def main():
    ergebnis = {
        "zeit": None,
        "okx_basis": okx._live_basis(),
        "schluessel_vorhanden": okx.schluessel_vorhanden(),
        "positionen_aktiv": [],
        "orders_pending": [],
        "nicht_gefunden": [],
        "fehler": None,
    }

    if not ergebnis["schluessel_vorhanden"]:
        ergebnis["fehler"] = "OKX-LIVE-Schluessel fehlen - Abfrage nicht moeglich"
        _schreiben(ergebnis)
        return 1

    try:
        # Alle aktiven Positionen (FUTURES + SWAP + MARGIN)
        for inst_type in ("FUTURES", "SWAP", "MARGIN"):
            try:
                roh = okx._roh(
                    "/api/v5/account/positions",
                    body={"instType": inst_type},
                    signiert=True,
                )
                daten = roh.get("data") or []
                for p in daten:
                    ergebnis["positionen_aktiv"].append({
                        "instType": inst_type,
                        "instId": p.get("instId"),
                        "posId": p.get("posId"),
                        "pos": p.get("pos"),
                        "posCcy": p.get("posCcy"),
                        "avgPx": p.get("avgPx"),
                        "upl": p.get("upl"),
                    })
            except Exception as e:
                ergebnis["fehler"] = f"positions {inst_type}: {e}"

        # Alle offenen Orders
        try:
            roh = okx._roh(
                "/api/v5/trade/orders-pending",
                signiert=True,
            )
            daten = roh.get("data") or []
            for o in daten:
                ergebnis["orders_pending"].append({
                    "instId": o.get("instId"),
                    "ordId": o.get("ordId"),
                    "posId": o.get("posId"),
                    "side": o.get("side"),
                    "ordType": o.get("ordType"),
                    "sz": o.get("sz"),
                    "px": o.get("px"),
                })
        except Exception as e:
            ergebnis["fehler"] = f"orders-pending: {e}"

    except Exception as e:
        ergebnis["fehler"] = str(e)

    # pos_ids suchen
    alle_ids = set()
    for p in ergebnis["positionen_aktiv"]:
        if p.get("posId"):
            alle_ids.add(str(p["posId"]))
    for o in ergebnis["orders_pending"]:
        if o.get("posId"):
            alle_ids.add(str(o["posId"]))

    for pid in POS_IDS:
        if pid not in alle_ids:
            ergebnis["nicht_gefunden"].append(pid)

    _schreiben(ergebnis)
    return 0


def _schreiben(ergebnis):
    ziel = HIER / "cache" / "okx_pos_verifikation.json"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, indent=2, ensure_ascii=False)

    # Markdown-Bericht
    md = [
        "# OKX Positions-Verifikation",
        "",
        f"Zeit: {ergebnis['zeit']}",
        f"OKX-Basis: {ergebnis['okx_basis']}",
        f"Schluessel vorhanden: {ergebnis['schluessel_vorhanden']}",
        "",
        "## Aktive Positionen an der Boerse",
        "",
    ]
    if ergebnis["positionen_aktiv"]:
        md.append("| instType | instId | posId | pos | avgPx | upl |")
        md.append("|----------|--------|-------|-----|-------|-----|")
        for p in ergebnis["positionen_aktiv"]:
            md.append(
                f"| {p['instType']} | {p['instId']} | {p['posId']} | "
                f"{p['pos']} | {p['avgPx']} | {p['upl']} |"
            )
    else:
        md.append("(keine)")

    md.extend(["", "## Offene Orders", ""])
    if ergebnis["orders_pending"]:
        md.append("| instId | ordId | posId | side | ordType | sz | px |")
        md.append("|--------|-------|-------|------|---------|----|----|")
        for o in ergebnis["orders_pending"]:
            md.append(
                f"| {o['instId']} | {o['ordId']} | {o['posId']} | "
                f"{o['side']} | {o['ordType']} | {o['sz']} | {o['px']} |"
            )
    else:
        md.append("(keine)")

    md.extend([
        "",
        "## Verifikation der 22 pos_id-Positionen",
        "",
        f"Nicht an der Boerse gefunden: {len(ergebnis['nicht_gefunden'])} / {len(POS_IDS)}",
        "",
    ])
    for pid in POS_IDS:
        status = "NICHT GEFUNDEN" if pid in ergebnis["nicht_gefunden"] else "GEFUNDEN"
        md.append(f"- {pid}: **{status}**")

    if ergebnis["fehler"]:
        md.extend(["", f"Fehler: {ergebnis['fehler']}"])

    md.append("")
    md.append("## Schlussfolgerung")
    md.append("")
    if len(ergebnis["nicht_gefunden"]) == len(POS_IDS):
        md.append(
            "Alle 22 pos_id-Positionen aus dem missing_modus_report sind an der "
            "OKX Boerse NICHT als aktiv vorhanden. Sie sind reine Buchhaltungs-"
            "Eintraege ohne boerenseitige Existenz."
        )
    else:
        gefunden = len(POS_IDS) - len(ergebnis["nicht_gefunden"])
        md.append(
            f"{gefunden} der 22 pos_id-Positionen sind an der OKX Boerse aktiv! "
            "Diese muessen geprueft werden."
        )

    ziel_md = HIER / "cache" / "okx_pos_verifikation.md"
    with open(ziel_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"JSON: {ziel}")
    print(f"Markdown: {ziel_md}")
    print(f"Nicht gefunden: {len(ergebnis['nicht_gefunden'])} / {len(POS_IDS)}")


if __name__ == "__main__":
    sys.exit(main())
