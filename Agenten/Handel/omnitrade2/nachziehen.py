"""Schutz-Stop fuer den omnitrade2-XPERP-Live-Lauf AN DER BOERSE nachziehen.

Warum nicht im Loop: der Rust-Client kennt keinen Algo-Weg
(``omnitrade-exchange/src/okx/`` hat kein ``order-algo`` und kein
``reduceOnly``), und ein Stop im Prozess stirbt mit dem Prozess. Der Hausweg
``okxf.schutz_stop_setzen`` ist an echten XPERP-Positionen erprobt und
ueberlebt einen toten Loop.

Regeln (jede Regel ist unten eine Pruefung):
1. Die Position wird an der BOERSE gelesen, nie aus dem Loop-Status.
2. Gedeckt ist nur, was ein Schutz-Stop mit Preis abdeckt - ueber ALLE
   ordTypes (``okxf.ist_schutz_stop``). Ein nackter ``trigger`` zaehlt nicht.
3. Fehlt Deckung, wird nur die LUECKE gestellt (Menge minus gedeckte Menge):
   nach dem Hochziehen von 1 auf 19 Kontrakte steht ein Stop fuer 1 da, der
   Rest wird nachgezogen. Zwei Stops derselben Groesse waeren ein doppelter
   Ausstieg (T-278: der engere feuert zuerst).
4. Der Stop liegt 2 % vom Einstieg (gemessen: SOL ATR14 1H = 1,07 %), Seite
   ist die Gegenrichtung, Ausloesung als Market (``slOrdPx = -1``).
5. Mikro-Beleg: 1 Kontrakt gefuellt UND Stop gedeckt -> Lauf wird EINMAL auf
   19 Kontrakte hochgezogen (``lauf.json``), danach nie wieder.

Vorschau ist die Vorgabe; ``--anwenden`` schreibt an die Boerse bzw. zieht
hoch. ``--json`` gibt die Lage maschinenlesbar aus (fuer die Wache).

Aufruf aus dem Handel-Ordner oder absolut:
    python Agenten/Handel/omnitrade2/nachziehen.py --vorschau
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
WURZEL = HANDEL.parents[1]
OKXF_PFAD = HANDEL / "xperp" / "okxf.py"
LAUF_DATEI = HIER / "lauf.json"
ZUSTAND = HIER / "zustand.json"
STATUS = WURZEL / "Agenten" / "Hermes" / "cache" / "omnitrade2" / "sol-xperp-status.json"
START_PS1 = HIER / "start.ps1"

STOP_PROZENT = 2.0
MIN_LUECKE = 0.5          # Kontrakte; darunter gilt die Position als gedeckt
HOCHZIEHEN_NACH_SEK = 0   # sofort, sobald der Beleg steht


def okxf_laden():
    """okxf ueber den PFAD laden (Spur-Modul, kein sys.path-Eintrag)."""
    spec = importlib.util.spec_from_file_location("okxf_nachziehen", OKXF_PFAD)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


def lies_json(pfad: Path, vorgabe: dict) -> dict:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(vorgabe)


def schreibe_json(pfad: Path, daten: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(pfad)


def position(okxf, inst: str):
    """Die offene Position dieses Instruments an der Boerse, oder None."""
    for p in okxf.positionen(inst) or []:
        if p.get("instId") != inst:
            continue
        menge = float(p.get("pos") or 0.0)
        if abs(menge) < 1e-12:
            continue
        return {
            "menge": menge,
            "einstieg": float(p.get("avgPx") or 0.0),
            "seite": "long" if menge > 0 else "short",
            "upl": p.get("upl"),
        }
    return None


def deckt_position(auftrag: dict, seite: str) -> bool:
    """Schuetzt dieser Auftrag eine Position der genannten Seite?

    Als Schutz zaehlt nur ein Auftrag, der ``reduceOnly`` traegt UND dessen
    Seite GEGEN die Position steht (Short-Position -> Kauf-Stop, Long-Position
    -> Verkaufs-Stop). Entscheidung Max 21.10.2026.
    """
    gegen = "buy" if seite == "short" else "sell"
    if str(auftrag.get("side") or "").strip().lower() != gegen:
        return False
    return str(auftrag.get("reduceOnly") or "").strip().lower() in ("true", "1")


def deckung(okxf, inst: str, seite: str | None = None):
    """(gedeckte Kontrakte, Anzahl, fremde Auftraege).

    ``seite`` bindet die Deckung an die RICHTUNG der Position. Ohne diese
    Bedingung zaehlt der Stop der VORIGEN Richtung als Deckung der neuen
    Position: nach einem Wechsel stuende sie nackt da, weil
    ``okxf.ist_schutz_stop`` nur prueft, OB ein Triggerpreis vorhanden ist -
    nicht, wen er schuetzt. ``None`` zaehlt alles (nur fuer Altaufrufer).
    """
    stops = [s for s in (okxf.schutz_stops(inst) or []) if okxf.ist_schutz_stop(s)]
    summe = 0.0
    anzahl = 0
    fremde = []
    for s in stops:
        if seite is not None and not deckt_position(s, seite):
            fremde.append(s)
            continue
        try:
            summe += abs(float(s.get("sz") or 0.0))
        except (TypeError, ValueError):
            continue
        anzahl += 1
    return summe, anzahl, fremde


def stop_preis(pos: dict) -> float:
    if pos["seite"] == "long":
        return round(pos["einstieg"] * (1.0 - STOP_PROZENT / 100.0), 5)
    return round(pos["einstieg"] * (1.0 + STOP_PROZENT / 100.0), 5)


def loop_pid() -> int | None:
    st = lies_json(STATUS, {})
    try:
        pid = int(st.get("pid") or 0)
    except (TypeError, ValueError):
        return None
    return pid or None


def pid_lebt(pid: int) -> bool:
    """PID zaehlt nur mit dem richtigen Programmnamen (Windows vergibt neu)."""
    try:
        aus = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return "omnitrade-cli.exe" in aus


def loop_beenden(pid: int) -> bool:
    """Ueber PowerShell, nicht taskkill: taskkill /F tat im Haus schon nichts."""
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % pid],
                   capture_output=True, text=True, timeout=60)
    for _ in range(10):
        if not pid_lebt(pid):
            return True
        time.sleep(1)
    return not pid_lebt(pid)


def lauf_starten() -> str:
    aus = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                          "-File", str(START_PS1)],
                         capture_output=True, text=True, timeout=180)
    return (aus.stdout or "").strip() or (aus.stderr or "").strip()


def hochziehen(okxf, lauf: dict, zustand: dict, anwenden: bool) -> list[str]:
    """Von 1 auf 19 Kontrakte: lauf.json umstellen, Loop neu starten. Einmalig."""
    meldungen = []
    if zustand.get("hochgezogen_am"):
        return ["Hochziehen bereits erledigt am %s - nichts zu tun." % zustand["hochgezogen_am"]]
    neu = dict(lauf)
    neu["quantity"] = lauf.get("quantity_voll", 0.19)
    neu["phase"] = "voll"
    meldungen.append("Hochziehen: %s -> %s Kontrakte" % (lauf.get("quantity"), neu["quantity"]))
    if not anwenden:
        meldungen.append("Vorschau: lauf.json bliebe unveraendert, Loop liefe weiter.")
        return meldungen
    pid = loop_pid()
    if pid and pid_lebt(pid):
        if not loop_beenden(pid):
            meldungen.append("Loop PID %d liess sich nicht beenden - Hochziehen abgebrochen." % pid)
            return meldungen
        meldungen.append("Loop PID %d beendet." % pid)
    schreibe_json(LAUF_DATEI, neu)
    antwort = lauf_starten()
    meldungen.append("Start: %s" % (antwort.splitlines()[-1] if antwort else "keine Ausgabe"))
    zustand["hochgezogen_am"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    zustand["hochgezogen_von"] = float(lauf.get("quantity") or 0)
    schreibe_json(ZUSTAND, zustand)
    return meldungen


def lauf(anwenden: bool = False) -> dict:
    laufdaten = lies_json(LAUF_DATEI, {"inst": "", "quantity": 0.0, "phase": "unbekannt"})
    inst = laufdaten.get("inst") or ""
    zustand = lies_json(ZUSTAND, {})
    ergebnis = {"zeit": time.strftime("%Y-%m-%dT%H:%M:%S"), "inst": inst,
                "phase": laufdaten.get("phase"), "menge": 0.0, "gedeckt": 0.0,
                "stops": 0, "handlung": [], "fehler": None}
    if not inst:
        ergebnis["fehler"] = "lauf.json nennt kein Instrument"
        return ergebnis

    okxf = okxf_laden()
    pos = position(okxf, inst)
    if pos is None:
        ergebnis["handlung"].append("keine Position an der Boerse - nichts zu schuetzen")
        return ergebnis
    ergebnis.update({"menge": pos["menge"], "einstieg": pos["einstieg"], "seite": pos["seite"]})

    gedeckt, anzahl, fremde = deckung(okxf, inst, pos["seite"])
    ergebnis.update({"gedeckt": gedeckt, "stops": anzahl, "fremde_stops": len(fremde)})
    if fremde:
        # Ein Stop der GEGENRICHTUNG schuetzt diese Position nicht und wuerde
        # nach einem Wechsel sogar falsch ausloesen - er wird storniert.
        kennungen = [str(s.get("algoId") or "") for s in fremde]
        ergebnis["handlung"].append(
            "FREMDE Stops (%d) decken die %s-Position nicht: %s"
            % (len(fremde), pos["seite"], ", ".join(k for k in kennungen if k) or "ohne algoId"))
        if anwenden:
            for kennung in [k for k in kennungen if k]:
                try:
                    okxf.algo_stornieren(inst, kennung)
                    ergebnis["handlung"].append("Storniert: %s" % kennung)
                except Exception as e:  # noqa: BLE001 - jeder Fehlschlag ist ein Befund
                    ergebnis["fehler"] = "Storno %s scheiterte: %s" % (kennung, e)
    luecke = abs(pos["menge"]) - gedeckt
    if luecke < MIN_LUECKE:
        ergebnis["handlung"].append("Deckung vollstaendig (%.2f von %.2f Kontrakten)"
                                    % (gedeckt, abs(pos["menge"])))
    else:
        preis = stop_preis(pos)
        ergebnis["stop_preis"] = preis
        ergebnis["luecke"] = luecke
        ergebnis["handlung"].append(
            "Luecke %.2f Kontrakte: Stop %s bei %s" % (luecke, pos["seite"], preis))
        if anwenden:
            antwort = okxf.schutz_stop_setzen(inst, pos["seite"], luecke, preis)
            ergebnis["stop_antwort"] = antwort
            gedeckt2, anzahl2, _fremd2 = deckung(okxf, inst, pos["seite"])
            ergebnis.update({"gedeckt": gedeckt2, "stops": anzahl2})
            if gedeckt2 + MIN_LUECKE >= abs(pos["menge"]):
                ergebnis["handlung"].append("NACHKONTROLLE: gedeckt %.2f (Auftraege %d)"
                                            % (gedeckt2, anzahl2))
                # Beleg steht: jetzt hochziehen (nur in der Mikro-Phase).
                if laufdaten.get("phase") == "mikro":
                    ergebnis["handlung"] += hochziehen(okxf, laufdaten, zustand, anwenden)
            else:
                ergebnis["fehler"] = ("NACHKONTROLLE: nur %.2f von %.2f gedeckt"
                                      % (gedeckt2, abs(pos["menge"])))

    if anwenden and ergebnis["handlung"]:
        zustand["letzter_lauf"] = ergebnis["zeit"]
        zustand["letzte_handlung"] = ergebnis["handlung"][-1]
        schreibe_json(ZUSTAND, zustand)
    return ergebnis


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Schutz-Stop des omnitrade2-XPERP-Laufs nachziehen")
    ap.add_argument("--anwenden", action="store_true", help="wirklich an die Boerse schreiben")
    ap.add_argument("--json", action="store_true", help="Lage als JSON ausgeben")
    args = ap.parse_args(argv)
    ergebnis = lauf(anwenden=args.anwenden)
    if args.json:
        print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    else:
        print("omnitrade2-Nachzieher %s (%s, phase %s)"
              % (ergebnis["zeit"], ergebnis["inst"], ergebnis["phase"]))
        print("  Position: %s %s Kontrakte @ %s" % (ergebnis.get("seite"), ergebnis["menge"],
                                                    ergebnis.get("einstieg")))
        print("  Deckung: %.2f Kontrakte in %d Auftrag/Auftraegen"
              % (ergebnis["gedeckt"], ergebnis["stops"]))
        for zeile in ergebnis["handlung"]:
            print("  - " + zeile)
        if ergebnis["fehler"]:
            print("  FEHLER: " + ergebnis["fehler"])
        if not args.anwenden:
            print("  (Vorschau - nichts geschrieben)")
    return 0 if not ergebnis["fehler"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
