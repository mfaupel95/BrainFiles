"""Read-only cross-check of the Quant spot scan and running paper books.

This report adds context to the existing spot scan. It never places orders,
changes a watch, writes tracking events, or updates a report file. Paper-book
entries are evidence of a recent simulation event, not live approvals.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
HANDEL = HERE.parent


def _parse_time(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    value = str(value).strip()
    if len(value) == 10 and value[4] == "-" and value[7] == "-":
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    for parser in (lambda v: datetime.strptime(v, "%d.%m.%Y %H:%M:%S"),):
        try:
            parsed = parser(value)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _active_traces():
    """Read the runner's literal SPUREN map without importing its runtime."""
    tree = ast.parse((HANDEL / "dauerlauf.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "SPUREN"
                   for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            break
        traces = {}
        for key, value in zip(node.value.keys, node.value.values):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            folder = key.value
            if isinstance(value, ast.Dict):
                for subkey, subvalue in zip(value.keys, value.values):
                    if (isinstance(subkey, ast.Constant) and subkey.value == "ordner"
                            and isinstance(subvalue, ast.Constant)
                            and isinstance(subvalue.value, str)):
                        folder = subvalue.value
                        break
            traces[key.value] = folder
        return traces
    raise ValueError("SPUREN-Liste in dauerlauf.py nicht lesbar")


def _positionen(state):
    positions = state.get("positionen") or []
    if isinstance(positions, dict):
        return [(str(key), value) for key, value in positions.items()
                if isinstance(value, dict)]
    if isinstance(positions, list):
        return [("", value) for value in positions if isinstance(value, dict)]
    return []


def _market_code(position, fallback):
    return str(position.get("inst") or position.get("paar") or fallback or "")


def _recent_paper_entries(state_root: Path, hours: float):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    entries = {}
    stale = []
    skipped = 0
    traces = _active_traces()
    for trace, folder in traces.items():
        directory = state_root / folder
        watch_path = directory / "wachen.json"
        try:
            watch = json.loads(watch_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            watch = {}
        max_age = float(watch.get("herzschlag_max_minuten") or 180)
        for path in directory.glob("zustand*.json"):
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                skipped += 1
                continue
            ran = _parse_time(state.get("letzter_lauf"))
            age_minutes = ((now - ran).total_seconds() / 60) if ran else None
            if age_minutes is None or age_minutes > max_age:
                stale.append((trace, path.name, age_minutes))
                continue
            state_mode = str(state.get("modus") or "").lower()
            for fallback, position in _positionen(state):
                symbol = _market_code(position, fallback)
                side = str(position.get("seite") or position.get("side") or "").lower()
                opened = _parse_time(position.get("eroeffnet_zeit")
                                     or position.get("eroeffnet")
                                     or position.get("opened_at"))
                position_mode = str(position.get("modus") or state_mode).lower()
                if (not symbol or side not in {"long", "short"} or not opened
                        or position_mode != "papier"):
                    continue
                if opened >= cutoff:
                    key = (trace, symbol.upper(), side)
                    item = {"trace": trace, "book": path.name,
                            "symbol": symbol, "side": side,
                            "opened": opened, "run": ran}
                    if key not in entries or opened > entries[key]["opened"]:
                        entries[key] = item
    return list(entries.values()), stale, skipped, len(traces)


def _base(symbol):
    return symbol.split("-", 1)[0].split("_", 1)[0].upper()


def _scanner_gate(row, watch, quant_settings):
    vola = row.get("kennzahlen", {}).get("volatilitaet_pa")
    if vola is None:
        return False
    passed = (row.get("score", 0) >= watch.get("mindest_score", 60)
              and vola <= watch.get("max_volatilitaet_pa", 2.0)
              and row.get("verhaeltnis", 0)
              >= watch.get("mindest_chance_risiko", 1.5))
    quant = row.get("quant")
    if quant_settings.get("aktiv") and quant_settings.get("modus") == "tor":
        passed = (passed and quant is not None and not quant.get("zu_gedehnt")
                  and quant.get("quant_score", 0)
                  >= quant_settings.get("mindest_quant_score", 60))
    return passed


def build_report(state_root: Path, recent_hours: float = 6.0):
    if str(HANDEL / "scanner_quant") not in sys.path:
        sys.path.insert(0, str(HANDEL / "scanner_quant"))
    import scan  # noqa: PLC0415

    # Score only completed UTC daily bars. The shared OKX helper also returns
    # today's forming candle; that can swing the score during the day.
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    original_kerzen = scan.okx.kerzen

    def completed_kerzen(inst, bar="1D", anzahl=300):
        candles = original_kerzen(inst, bar, anzahl)
        if bar == "1D":
            candles = [c for c in candles if int(c[0]) + 86_400_000 <= now_ms]
        return candles

    scan.okx.kerzen = completed_kerzen
    try:
        # --kurz suppresses the scanner's tracking and file writes.
        with contextlib.redirect_stdout(io.StringIO()):
            market = scan.lauf(kurz=True)
    finally:
        scan.okx.kerzen = original_kerzen
    watch = scan.wachen()
    quant_settings = scan.quant_einstellung()
    entries, stale, skipped, trace_count = _recent_paper_entries(
        state_root, recent_hours)

    rows = []
    for row in sorted(market.get("werte", []),
                      key=lambda item: item.get("score", 0), reverse=True):
        symbol = str(row.get("inst") or "")
        base = _base(symbol)
        exact = [e for e in entries if e["symbol"].upper() == symbol.upper()]
        proxy = [e for e in entries if _base(e["symbol"]) == base
                 and e["symbol"].upper() != symbol.upper()]
        q = row.get("quant") or {}
        rows.append({"symbol": symbol, "score": row.get("score"),
                     "qscore": q.get("quant_score"),
                     "gate": _scanner_gate(row, watch, quant_settings),
                     "direct": exact, "proxy": proxy})

    freigabe = watch.get("freigabe") or {}
    return {"generated": now,
            "market_date": market.get("datum"),
            "closed_through": (now.date() - timedelta(days=1)).isoformat(),
            "market_rows": len(rows),
            "recent_hours": recent_hours,
            "active_trace_count": trace_count,
            "fresh_paper_entries": entries,
            "stale_state_files": stale,
            "skipped_state_files": skipped,
            "spot_live_gate": {"handel_erlaubt": watch.get("handel_erlaubt"),
                               "freigabe_erfuellt": freigabe.get("erfuellt"),
                               "budget_usd": watch.get("budget_usd"),
                               "quote_universe": (watch.get("universum") or {}).get("quotes")},
            "rows": rows}


def render(report):
    print("=== Querabgleich OKX-Spot / Papierbücher (nur Bericht) ===")
    print("Stand %s UTC | abgeschlossene Tageskerzen bis %s | "
          "%d aktive Laufspuren | %d Spotwerte mit ausreichender Historie | "
          "Papier-Einstiege letzte %.1f h: %d" % (
              report["generated"].strftime("%Y-%m-%d %H:%M"),
              report["closed_through"],
              report["active_trace_count"], report["market_rows"],
              report["recent_hours"],
              len(report["fresh_paper_entries"])))
    gate = report["spot_live_gate"]
    print("Live-Wache Spot: handel_erlaubt=%s, freigabe.erfuellt=%s, "
          "Budget=%s USD, Quotes=%s" % (
              gate["handel_erlaubt"], gate["freigabe_erfuellt"],
              gate["budget_usd"], gate["quote_universe"]))
    print("Hinweis: Papier-Einstiege sind Spurbelege, keine Live-Freigaben; "
          "Spuren sind nicht statistisch unabhängig.")
    print("Wert       Score  QScore  Markt-Tor  Frisch direkt (Long/Short)  "
          "Frisch gleicher Basiswert")
    for row in report["rows"][:12]:
        direct = row["direct"]
        proxy = row["proxy"]
        direct_text = ", ".join("%s %s" % (e["trace"], e["side"])
                                for e in direct) or "-"
        proxy_text = ", ".join("%s:%s" % (e["trace"], e["symbol"])
                               for e in proxy) or "-"
        qscore = "-" if row["qscore"] is None else "%.1f" % row["qscore"]
        print("%-10s %5.1f  %6s  %-9s  %-26s %s" % (
            row["symbol"], row["score"], qscore,
            "JA" if row["gate"] else "NEIN", direct_text, proxy_text))
    passed = [r["symbol"] for r in report["rows"] if r["gate"]]
    print("Markt-Tor bestanden: %s" % (", ".join(passed) if passed else "keine"))
    if report["stale_state_files"] or report["skipped_state_files"]:
        print("Zustände außerhalb Herzschlaggrenze: %d; unlesbare Zustände: %d" % (
            len(report["stale_state_files"]), report["skipped_state_files"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path, default=HANDEL,
                        help="Handelslaufzeit-Ordner mit zustand*.json")
    parser.add_argument("--fresh-hours", type=float, default=6.0,
                        help="Fenster für frische Papier-Einstiege (Standard: 6 h)")
    args = parser.parse_args()
    render(build_report(args.state_root, args.fresh_hours))


if __name__ == "__main__":
    main()
