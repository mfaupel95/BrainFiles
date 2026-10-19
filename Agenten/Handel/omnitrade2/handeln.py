"""Handelsspur `omnitrade2` - der Rust-Lauf entscheidet, diese Spur spiegelt.

WOHER DIE SPUR KOMMT
--------------------
`Werkstatt/omnitrade2` (Rust, Phase 5 egui UI) ist ein Fork von `Womnitrade`.
Sein CLI kennt aktuell nur `backtest` und `validate` - es schreibt KEINE
Statusdatei. Diese Spur ist trotzdem verdrahtet: sie liest den definierten
Statuspfad und meldet sauber "keine Statusdatei", solange der Rust-Klon
keinen Live-Modus bekommt.

Die Spur ist ein Muster der bestehenden omnitrade-Spur (Agenten/Handel/omnitrade/):
- wachen.json: Tore und Zahlen
- lesen.py: liest Statusdateien ueber omnitrade_bridge.py und omnitrade_lauf.py
- handeln.py: Handelslogik mit spur_buch

WAS GESPIEGELT WIRD
-------------------
Nicht die Orderliste (ein Ringpuffer mit 20 Eintraegen), sondern der ZUSTAND:
Haelt der Lauf eine Position (`net_quantity > 0`), haelt die Spur sie auch;
meldet der Lauf keine Position mehr, steigt die Spur aus (`omnitrade2 flat`).

Ein Lauf zaehlt nur, wenn er WIRKLICH laeuft: Statusdatei frisch UND PID lebt
(`lesen.lauf`). Eine Leiche mit `state: running` darf keine Position eroeffnen.

Papier zuerst: `handel_erlaubt=false`. Der Live-Zweig ist gebaut und laeuft
ueber den gemeinsamen Kern (`spur_buch.sperren_live` + `orderweg`), aber er
braucht die Freigabekette (Handelsregeln Punkt 1-5) und Max' Endabnahme.

Aufruf:
  python handeln.py --vorschau | --papier | --live | --wachen
"""

import argparse
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HANDEL, os.path.join(HANDEL, "scanner"), HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

# spur_buch ZUERST: es legt Agenten/Bus auf sys.path.
import spur_buch as buch  # noqa: E402
import lesen  # noqa: E402
# Test-Seam: None -> echte Statusdateien. Tests setzen ein Lambda.
lage_override = None


def lage_holen():
    """Alle Laeufe ueber die Naht. Tests setzen `lage_override`."""
    if lage_override is not None:
        return lage_override()
    return lesen.lage()


def quelle(w):
    """Ein Instrument je omnitrade2-Lauf, mit Kurs und Positionsstand.

    Aufgenommen wird JEDER lesbare Lauf - auch ein gestoppter. Sein Zustand
    wird gebraucht: er sagt, dass die Position zu ist, und genau daraus faellt
    der Ausstieg (`ausstieg_grund`). Ein Einstieg kommt fuer ihn nicht in
    Frage, das entscheidet `signal()` ueber `laeuft`.

    Der Kurs ist der Ausstiegskurs, wenn der Lauf gerade verkauft hat: die
    Statusdatei traegt den echten Orderpreis, `last_close` waere ein Kurs, den
    es nie gab. Sonst gilt `last_close` (Bewertung der offenen Position).
    """
    laeufe, fehler = lage_holen()
    aus, kurse = {}, {}
    for e in laeufe:
        if not e.get("ok"):
            continue
        inst = e.get("inst")
        if not inst:
            fehler.append("%s: kein Instrument" % os.path.basename(e.get("datei") or "?"))
            continue
        kurs = e.get("kurs")
        if e.get("verkauf") and not e.get("offen"):
            kurs = e["verkauf"]
        if kurs is None:
            fehler.append("%s: kein Kurs (last_close fehlt)" % inst)
            continue
        aus[inst] = {
            "laeuft": bool(e.get("laeuft")),
            "offen": bool(e.get("offen")),
            "netto": e.get("netto"),
            "state": e.get("state"),
            "signal": e.get("signal"),
            "script": e.get("script"),
            "lauf": os.path.basename(e.get("datei") or ""),
            "alter_s": e.get("alter_s"),
            "fehler": e.get("fehler") or "",
        }
        kurse[inst] = kurs
    return aus, kurse, fehler


def signal(d, w):
    """Long, solange der omnitrade2-Lauf WIRKLICH laeuft und eine Position haelt.

    Kein short: omnitrade2 handelt nur long (ein Kauf setzt das Kapital ein, ein
    Verkauf schliesst die Position). Eine Short-Seite zu erfinden waere eine
    zweite Strategie neben der, die Max bestellt hat.

    `laeuft` gehoert in die Bedingung: eine stehengebliebene `net_quantity`
    eines toten Laufs darf keinen Einstieg ausloesen - es waere eine Position,
    die niemand mehr bewacht.
    """
    if not d.get("laeuft") or not d.get("offen"):
        return None
    return "long"


def ausstieg_grund(p, w):
    """Der Ausstieg, die die Rust-Strategie genommen hat.

    Gemeldet wird `omnitrade2 flat`, sobald fuer das Instrument eine Statusdatei
    steht, deren Lauf beendet ist ODER deren Nettomenge 0 ist. Der Zustand
    `stopped` zaehlt mit: die CLI verkauft beim Beenden, die Position ist dann
    bei ihr zu. `starting`/`error` zaehlen NICHT - da ist nicht entschieden,
    und ein Abbruch ist kein Handelssignal. Ohne Statusdatei bleibt die
    Position stehen (der Stop schuetzt sie weiter).
    """
    inst = p.get("inst")
    if not inst:
        return None
    laeufe, _fehler = lage_holen()
    for e in laeufe:
        if e.get("inst") != inst:
            continue
        if e.get("state") in ("running", "stopped") and not e.get("offen"):
            return "omnitrade2 flat"
    return None


def boerse_binden(w):
    """Den Orderweg an die Boerse der wachen binden (Quote setzen).

    `mosaic/kraken_spot` fuehrt die Quotewaehrung als Modulzustand (Vorgabe
    EUR). Mit EUR findet die Paar-Tabelle ein USDC-Paar NICHT - sie faellt
    ausdruecklich nicht auf eine andere Waehrung zurueck, damit keine Order im
    falschen Markt landet. Deshalb wird die Quote VOR dem ersten Sperrtext
    gesetzt. Ohne Boersenangabe bleibt alles wie es ist.
    """
    weg = buch.orderweg(w)
    quote = w.get("kraken_quote")
    if weg is not None and quote and hasattr(weg, "setze_quote"):
        return weg.setze_quote(quote)
    return None


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau", dest="modus")
    ap.add_argument("--papier", action="store_const", const="papier", dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    ap.set_defaults(modus="papier")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = buch.lade_wachen(buch.pfade(HIER)[0])
    boerse_binden(w)

    return buch.zyklus(HIER, quelle, signal, a.modus, "handel/omnitrade2",
                       zusatz_ausstieg=ausstieg_grund)


if __name__ == "__main__":
    raise SystemExit(main())
