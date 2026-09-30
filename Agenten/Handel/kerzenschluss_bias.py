"""Wie weit liegen Backtest-Ausstiege neben ihrer Marke? (rein lesend)

HINTERGRUND. Der Replay stieg bis zum 30.09.2026 zum SCHLUSS der Kerze aus, in
der Stop oder Ziel beruehrt wurde - nicht zum Stop- oder Zielkurs. Ein Laeufer
ueberschiesst sein Ziel dadurch (gemessen: ADA stand mit Ziel +12 % im Buch und
wurde mit +48 % geschlossen). Seit dem Fix (T-177, `replay.beruehrte_marke`)
steht der Ausstieg auf der Marke. Dieses Werkzeug beziffert BEIDE Seiten: wie
viel zu gut die Gewinner und wie viel zu schlecht die Verlierer gerechnet waren,
je Journal und in der Summe.

WARUM ZEILENWEISE UND NICHT UEBER DIE PAARUNG. `kosten_wendepunkt.paarung()`
paart ohne `pos_id` ueber das INSTRUMENT, und diese Backtest-Journale haben
keine Kennung. Bei verschachtelten Positionen desselben Instruments greift die
Paarung daneben (bekannt als T-095) - ein falsch gepaarter Einstieg liefert
einen erfundenen Abstand und damit eine erfundene Ueberschreitung. Jede
Austrittszeile traegt ihre Marke aber SELBST (`stop` bzw. `ziel` in derselben
Zeile), also wird je Zeile gemessen:

    Abweichung = (preis - marke) / marke * 100     # Prozentpunkte der Marke

Das Vorzeichen wird auf "besser/schlechter" gedreht - bei einem LONG liegt das
Ziel oben und der Stop unten, bei einem SHORT umgekehrt:

    Ziel-Ausstieg:  besser     = Abweichung * (+1 long / -1 short)
    Stop-Ausstieg:  schlechter = Abweichung * (-1 long / +1 short)

`zuviel Gewinn` ist die Summe der Verbesserungen, `zuviel Verlust` die Summe der
Verschlechterungen. Nach dem Fix muessen beide gegen null gehen; die Spalte
`auf der Marke` zaehlt die Zeilen, die genau auf ihr sitzen.

Das Werkzeug schreibt nichts. Aufruf aus `Agenten/Handel`:

    python kerzenschluss_bias.py                   # alle Backtest-Journale
    python kerzenschluss_bias.py --spur wavetrend  # nur eine Spur
    python kerzenschluss_bias.py --json
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER / "daten" / "backtest"

# Toleranz fuer "sitzt auf der Marke": relativ, weil die Kurse bis sechs
# Stellen tragen. Darunter ist der Unterschied Gleitkomma-Rauschen und keine
# Messung (eine Runde GENAU am Ziel liegt rechnerisch bei 2e-15).
TOLERANZ = 1e-6
MARKEN = ("stop", "ziel")


def journale(spur: str | None = None) -> list[Path]:
    """Alle Backtest-Journale, je Ordner das groesste.

    Der Walk schreibt `<spur>/<lauf>/handelsjournal.csv` - ZWEI Ebenen unter
    `daten/backtest`; ein Muster mit nur einer Ebene findet nichts und meldet
    "keine Journale", obwohl welche da sind. Je Ordner gewinnt die groesste
    Datei (die Anzeige-Regel des Hauses fuer mehrere Fensterlaeufe).
    """
    muster = ("%s/*/*.csv" % spur if spur else "*/*/*.csv")
    je_ordner: dict[Path, Path] = {}
    for p in sorted(WURZEL.glob(muster)):
        if not p.is_file():
            continue
        alt = je_ordner.get(p.parent)
        if alt is None or p.stat().st_size > alt.stat().st_size:
            je_ordner[p.parent] = p
    return sorted(je_ordner.values())


def _zahl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def messen(pfad: Path) -> dict | None:
    """Die Abweichungen EINES Journals (rein lesend, ohne Paarung).

    Eine fehlende Datei ist kein Fehler - sie liefert None wie ein leeres
    Journal (die Wache gegen versehentliches Schreiben ruft den Weg mit einem
    absichtlich nicht vorhandenen Pfad auf).
    """
    if not Path(pfad).is_file():
        return None
    with open(pfad, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    ziel, stop, auf_marke, ohne_seite = [], [], 0, 0
    for r in rows:
        grund = str(r.get("grund") or "").strip().lower()
        if grund not in MARKEN:
            continue
        preis, marke = _zahl(r.get("preis")), _zahl(r.get(grund))
        if not preis or not marke:
            continue
        seite = str(r.get("seite") or "").strip().lower()
        if seite not in ("long", "short"):
            ohne_seite += 1
            continue
        lang = seite == "long"
        # Vorzeichen-RICHTIG: "besser_alt" ist die Wirkung des ALTEN
        # Ausstiegskurses auf das Ergebnis, gemessen an der Marke. Ein hoeherer
        # Ausstieg ist fuer einen Long immer besser - egal ob Stop oder Ziel -,
        # fuer einen Short immer schlechter. Deshalb EIN Vorzeichen je
        # Richtung und nicht je Marke.
        #
        # Die erste Fassung dieses Werkzeugs zaehlte nur die Ausstiege JENSEITS
        # der Marke und liess die auf der guten Seite weg; die Summe war damit
        # einseitig und ergab fuer wavetrend +493 statt der richtigen -48
        # (Gegenprobe: `kosten_wendepunkt.paarung` auf denselben zwei Journalen).
        besser_alt = (preis - marke) / marke * 100.0 * (1.0 if lang else -1.0)
        if abs(besser_alt) <= TOLERANZ * 100:
            auf_marke += 1
        (ziel if grund == "ziel" else stop).append(besser_alt)
    ausstiege = len(ziel) + len(stop) + ohne_seite
    if not ausstiege:
        return None
    alle = ziel + stop
    zuviel_gewinn = sum(a for a in alle if a > 0)      # der alte Kurs war besser
    zuviel_verlust = sum(-a for a in alle if a < 0)    # der alte Kurs war schlechter
    try:
        name = str(pfad.relative_to(WURZEL)).replace("\\", "/")
    except ValueError:          # von Hand mit relativem Pfad aufgerufen
        name = str(pfad).replace("\\", "/")
    return {
        "journal": name,
        "ausstiege": ausstiege,
        "ziel_ausstiege": len(ziel),
        "stop_ausstiege": len(stop),
        "auf_der_marke": auf_marke,
        "ohne_seite": ohne_seite,
        "zuviel_gewinn": zuviel_gewinn,
        "zuviel_verlust": zuviel_verlust,
        "netto": zuviel_gewinn - zuviel_verlust,
        "betroffen": len([a for a in alle if abs(a) > TOLERANZ * 100]),
    }


def tabelle(zeilen: list[dict]) -> str:
    kopf = ("%-44s %7s %9s %9s %11s %11s %9s %8s"
            % ("Journal", "Ausst.", "auf Marke", "betroffen", "zuviel Gew.",
               "zuviel Verl.", "netto", "Marke%"))
    aus = [kopf, "-" * len(kopf)]
    for z in zeilen:
        quote = (100.0 * z["auf_der_marke"] / z["ausstiege"]
                 if z["ausstiege"] else 0.0)
        aus.append("%-44s %7d %9d %9d %11.1f %11.1f %9.1f %7.0f %%"
                   % (z["journal"], z["ausstiege"], z["auf_der_marke"],
                      z["betroffen"], z["zuviel_gewinn"], z["zuviel_verlust"],
                      z["netto"], quote))
    return "\n".join(aus)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spur", help="nur diese Spur")
    ap.add_argument("--json", action="store_true", help="Maschinenlesbar")
    a = ap.parse_args(argv)

    if not WURZEL.is_dir():
        print("Kein Backtest-Ordner: %s" % WURZEL)
        return 1
    zeilen = [z for z in (messen(p) for p in journale(a.spur)) if z]
    if a.json:
        print(json.dumps(zeilen, indent=1, ensure_ascii=False))
        return 0
    if not zeilen:
        print("Keine Backtest-Journale mit Ausstiegen gefunden.")
        return 1
    print("Kerzenschluss-Abweichung im Backtest (rein lesend, in "
          "Prozentpunkten der Marke)")
    print()
    print(tabelle(zeilen))
    print()
    n = sum(z["ausstiege"] for z in zeilen)
    marke = sum(z["auf_der_marke"] for z in zeilen)
    print("%d Ausstiege in %d Journalen; %d (%.0f %%) sitzen auf ihrer Marke"
          % (n, len(zeilen), marke, (100.0 * marke / n) if n else 0.0))
    print("Summe zu gut gerechnet %+.1f | zu schlecht gerechnet %+.1f | "
          "netto %+.1f Prozentpunkte"
          % (sum(z["zuviel_gewinn"] for z in zeilen),
             sum(z["zuviel_verlust"] for z in zeilen),
             sum(z["netto"] for z in zeilen)))
    print()
    print("Eine Spalte 'Marke%' bei 100 % heisst: der Lauf stammt von NACH dem "
          "Fix (T-177) - dann ist hier nichts mehr zu korrigieren.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())