"""Was die Buecher hergeben - Spur fuer Spur, mit ihrer eigenen Kostenrechnung.

Warum es dieses Modul gibt: spiegel, omniquant und gitter haben eigene
Auswertungen, die drei Buecher mit den groessten Journalen (xperp, swap,
scanner, kraken) hatten keine. Die haeufigste Frage im Handel-Baum - traegt
das Buch nach Kosten? - stand damit fuer sie offen.

Die gemeinsame Mechanik (Bilanz, Trefferquote, Gruppen, Baender, die Regel
"unter MIN_AUSSTIEGE wird nichts behauptet") steht in buchauswertung.py. Hier
steht nur, was jede Spur anders macht: welches Feld der Einsatz ist, welches
der Erloes, und welcher Satz an Kosten in der Zahl schon steckt.

WICHTIG - die Kosten sind NICHT geschaetzt, sondern stehen in der Zeile:
  xperp/swap  Gebuehr auf den Nominalwert (beide Seiten) und Funding, beides
              als Spalte im Journal; gerechnet wird aus margin_usd und preis.
  scanner     GEBUEHR_PCT = 0.0005 je Seite, im Journal schon eingerechnet
              (kauf: usd*(1+g), verkauf: erloes).
  kraken      Gebuehr aus wachen.json (seit 14.09.2026 0 % dank Kraken-Pro),
              ebenfalls schon in der Zeile.
  orbk        gv_usd steht fertig in der Zeile.

Aufruf (aus dem Handel-Ordner):
    scanner/.venv/Scripts/python.exe auswertung_alle.py
    scanner/.venv/Scripts/python.exe auswertung_alle.py --spur xperp
"""

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

import stoerungen  # gleicher Ordner: trennt Zwangsschluesse von Handelsrunden

HIER = Path(__file__).resolve().parent

# Ab wie vielen geschlossenen Runden eine Spur ueberhaupt etwas aussagt.
# Dieselbe Schwelle wie buchauswertung.MIN_AUSSTIEGE - zwei Schwellen fuer
# dieselbe Frage laufen sonst auseinander.
MIN_RUNDEN = 8

SPUREN = ("xperp", "swap", "scanner", "kraken", "orbk", "gitter", "nautilus")


def kennzahlen_fuer(spur):
    """Die Kennzahlen EINER Spur - Zuordnung Spur -> Rechenweg an EINER Stelle.

    Der Weg stand bis zum 15.09.2026 nur in `main()`. Ein zweiter Aufrufer
    (die Telegram-Befehle in `befehle.py`) haette die Zuordnung abschreiben
    muessen - und beim naechsten neuen Feld nur an einer Stelle mitgezogen.
    `main()` und `befehle.py` rufen jetzt beide diese Funktion.

    Rueckgabe: das dict aus `kennzahlen()`, oder None wenn die Spur keine
    geschlossenen Runden hat (bzw. gar kein Journal).
    """
    z = zeilen(spur)
    if not z:
        return None
    gebuehr = 0.0
    wp = HIER / spur / "wachen.json"
    if wp.exists():
        try:
            gebuehr = (json.loads(wp.read_text("utf-8")).get("gebuehr_taker")
                       or 0.0)
        except (OSError, ValueError):
            gebuehr = 0.0
    if spur in ("xperp", "swap"):
        runden = runden_xperp(z)
    elif spur == "scanner":
        runden = runden_spot(z, 0.0005)
    elif spur == "kraken":
        runden = runden_spot(z, gebuehr, einsatz_feld="eur")
    elif spur == "orbk":
        runden = runden_orbk(z)
    elif spur == "gitter":
        runden = gitter_zyklen(z)
    else:
        runden = []
    return kennzahlen(runden, "USD")



def prozent(x, stellen=2):
    """Eine Zahl mit Vorzeichen, oder n/a. Kein Lambda: die Verkettung
    'Pattern bauen' + 'formatieren' hat hier still den Rohling ausgegeben."""
    if x is None:
        return "n/a"
    return ("%+." + str(stellen) + "f") % x


def zahl(x):
    """Ein Feld als Zahl, oder None. Leere Zellen sind keine Null."""
    if x is None:
        return None
    s = str(x).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def zeilen(spur, datei="handelsjournal.csv"):
    p = HIER / spur / datei
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f)]


def tage(von, bis):
    """Haltedauer in Tagen aus zwei ISO-Zeitstempeln."""
    try:
        a = datetime.fromisoformat(von)
        b = datetime.fromisoformat(bis)
    except (TypeError, ValueError):
        return None
    return (b - a).total_seconds() / 86400.0


def kennzahlen(runden, einheit):
    """Die gemeinsame Ausgabe. runden = Liste von dicts mit ergebnis/einsatz.

    ZWANGSSCHLUESSE ZAEHLEN NICHT MIT. Ein Ausstieg mit herzschlag im Grund
    ist keine Handelsentscheidung, sondern die Folge eines Ausfalls (der
    Waechter stellt die Spur flach, wenn der Dauerlauf zu lange stand). Er
    steht trotzdem im Journal und wuerde sonst als Runde mitgezaehlt: die
    Rundenzahl waere zu hoch, die Trefferquote zu niedrig, weil die
    Zwangsschluesse meist im Verlust sitzen. Beides wird deshalb getrennt
    ausgewiesen - nicht versteckt, nur nicht vermischt.
    """
    echt = [r for r in runden if not stoerungen.ist_stoerung(r.get("grund"))]
    stoer = [r for r in runden if stoerungen.ist_stoerung(r.get("grund"))]
    if not echt:
        return None
    runden = echt
    ergebnisse = [r["ergebnis"] for r in runden]
    einsatz = sum(r["einsatz"] for r in runden)
    erloes = sum(r["ergebnis"] + r["einsatz"] for r in runden)
    pcts = [100.0 * r["ergebnis"] / r["einsatz"] for r in runden
            if r["einsatz"]]
    treffer = sum(1 for r in runden if r["ergebnis"] > 0)
    halten = [r["halten"] for r in runden if r.get("halten") is not None]
    return {
        "n": len(runden), "einheit": einheit, "einsatz": einsatz,
        "erloes": erloes, "ergebnis": erloes - einsatz,
        "pct": 100.0 * (erloes - einsatz) / einsatz if einsatz else 0.0,
        "median_pct": statistics.median(pcts) if pcts else None,
        "treffer": treffer,
        "treffer_pct": 100.0 * treffer / len(runden),
        "best": max(pcts) if pcts else None,
        "schlecht": min(pcts) if pcts else None,
        "halten_tage": statistics.median(halten) if halten else None,
        "gruende": _zaehle(r["grund"] for r in runden),
        "kosten_anteil": _kosten_anteil(runden),
        # Separat, nicht eingerechnet: die Fehleranalyse.
        "n_stoerung": len(stoer),
        "stoerung_ergebnis": sum(r["ergebnis"] for r in stoer) if stoer else 0.0,
        "runden_gesamt": len(echt) + len(stoer),
    }


def _zaehle(werte):
    aus = {}
    for w in werte:
        w = (w or "ohne").strip() or "ohne"
        aus[w] = aus.get(w, 0) + 1
    return dict(sorted(aus.items(), key=lambda kv: -kv[1]))


def _kosten_anteil(runden):
    """Kosten in Prozent des Einsatzes, soweit das Journal sie hergibt."""
    if any(r.get("kosten") is None for r in runden):
        return None
    einsatz = sum(r["einsatz"] for r in runden)
    if not einsatz:
        return None
    return 100.0 * sum(r["kosten"] for r in runden) / einsatz


def _paare(zeilen_, einstieg_namen, ausstieg_namen, einsatz_feld, ergebnis_fn,
           einheit, grund_feld="grund"):
    """Einstiege und Ausstiege je Instrument in der Reihenfolge des Journals
    zusammenfuehren (wer zuerst kauft, verkauft zuerst), und daraus Runden
    bauen. Kein Nachrechnen von Kursen: Erloes und Einsatz stehen in den
    Zeilen - was nicht in den Zeilen steht, wird nicht erfunden.
    """
    offen = {}
    runden = []
    for r in zeilen_:
        art = (r.get("aktion") or "").strip().lower()
        schluessel = (r.get("inst") or r.get("paar") or "").strip()
        if not schluessel:
            continue
        if art in einstieg_namen:
            offen.setdefault(schluessel, []).append(r)
            continue
        if art not in ausstieg_namen:
            continue
        kette = offen.get(schluessel) or []
        if not kette:
            continue                      # Ausstieg ohne Einstieg: ignorieren
        ein = kette.pop(0)
        einsatz = zahl(ein.get(einsatz_feld))
        if not einsatz:
            continue
        ergebnis, kosten = ergebnis_fn(ein, r)
        if ergebnis is None:
            continue
        runden.append({
            "inst": schluessel, "einsatz": einsatz, "ergebnis": ergebnis,
            "kosten": kosten, "grund": (r.get(grund_feld) or "").strip() or None,
            "halten": tage(ein.get("zeit"), r.get("zeit")),
        })
    return runden


def runden_xperp(zeilen_):
    """Hebelspuren: Einsatz ist die Margin, Erloes die Margin beim Ausstieg."""
    def ergebnis(ein, aus):
        margin = zahl(ein.get("margin_usd"))
        erloes = zahl(aus.get("margin_usd"))
        if not (margin and erloes):
            return None, None
        nominal = zahl(ein.get("nominal_usd")) or 0.0
        gebuehr = (zahl(ein.get("gebuehr_pct")) or 0.0) + \
                  (zahl(aus.get("gebuehr_pct")) or 0.0)
        funding = zahl(aus.get("funding_pct")) or 0.0
        kosten = nominal * gebuehr + nominal * abs(funding)
        return erloes - margin, kosten

    return _paare(zeilen_, {"eroeffnen"}, {"schliessen"}, "margin_usd", ergebnis,
                  "USD")


def runden_spot(zeilen_, kosten_pct=0.0, einsatz_feld="usd"):
    """Spot (scanner, kraken): Einsatz und Erloes stehen als Betrag in der Zeile.
    Die Gebuehr ist bei scanner/kraken schon eingerechnet; kosten_pct ist nur
    fuer die Anzeige, wie viel davon Gebuehr war."""
    def ergebnis(ein, aus):
        einsatz = zahl(ein.get("usd") if ein.get("usd") is not None
                       else ein.get("eur"))
        erloes = zahl(aus.get("usd") if aus.get("usd") is not None
                      else aus.get("eur"))
        if not (einsatz and erloes is not None):
            return None, None
        return erloes - einsatz, einsatz * kosten_pct

    return _paare(zeilen_, {"kauf"}, {"verkauf"}, einsatz_feld, ergebnis,
                  "USD")


def runden_orbk(zeilen_):
    """orbk journalisiert die fertige Runde - hier wird nichts gepaart."""
    runden = []
    for r in zeilen_:
        gv = zahl(r.get("gv_usd"))
        if gv is None:
            continue
        runden.append({"inst": r.get("inst", ""), "einsatz": 0.0,
                       "ergebnis": gv, "kosten": 0.0,
                       "grund": (r.get("ausgang") or "").strip() or None,
                       "halten": None})
    return runden


def gitter_zyklen(zeilen_):
    """Ein Gitter-Zyklus ist ein Verkauf einer Stufe, die vorher gekauft wurde.
    Der Gewinn steht als gw_usd in der Verkaufszeile."""
    offen = {}
    zyklen = []
    for r in zeilen_:
        art = (r.get("aktion") or "").strip().upper()
        stufe = r.get("stufe")
        if art == "KAUF":
            offen.setdefault(stufe, []).append(r)
        elif art == "VERKAUF":
            kette = offen.get(stufe) or []
            if not kette:
                continue
            ein = kette.pop(0)
            gw = zahl(r.get("gw_usd"))
            einsatz = zahl(ein.get("einsatz_usd"))
            if gw is None or not einsatz:
                continue
            zyklen.append({"inst": r.get("inst", ""), "einsatz": einsatz,
                           "ergebnis": gw, "kosten": 0.0,
                           "grund": "Stufe %s" % stufe,
                           "halten": tage(ein.get("zeit"), r.get("zeit"))})
    return zyklen


def zeige(spur, k):
    if k is None:
        print("\n=== %s ===" % spur.upper())
        print("  keine geschlossenen Runden im Journal")
        return
    p = prozent
    print("\n=== %s ===" % spur.upper())
    print("  %-28s %d" % ("geschlossene Runden", k["n"]))
    if k.get("n_stoerung"):
        print("  %-28s %d   (nicht mitgezaehlt: Ergebnis %+.2f %s)"
              % ("davon Zwangsschluesse", k["n_stoerung"],
                 k["stoerung_ergebnis"], k["einheit"]))
        print("  %-28s %d" % ("Runden mit Stoerungen", k["runden_gesamt"]))
    print("  %-28s %s" % ("Ergebnis", "%+.2f %s (%+.2f %%)"
                          % (k["ergebnis"], k["einheit"], k["pct"])))
    print("  %-28s %.0f %%  (%d von %d)"
          % ("Treffer (Gewinn > 0)", k["treffer_pct"], k["treffer"], k["n"]))
    if k["einsatz"]:
        print("  %-28s %s %%   Median %s %%"
              % ("Ergebnis auf den Einsatz (gesamt)",
                 p(100.0 * k["ergebnis"] / k["einsatz"]),
                 p(k["median_pct"])))
    else:
        print("  %-28s kein Einsatz im Journal" % "Ergebnis in Prozent")
    print("  %-28s %s %% / %s %%"
          % ("beste / schlechteste Runde", p(k["best"]), p(k["schlecht"])))
    if k["kosten_anteil"] is not None:
        print("  %-28s %.2f %% vom Einsatz"
              % ("Kosten (aus den Zeilen)", k["kosten_anteil"]))
    if k["halten_tage"] is not None:
        print("  %-28s %.1f Tage" % ("Haltedauer (Median)", k["halten_tage"]))
    print("  Ausstiegsgruende: %s"
          % ", ".join("%s %d" % (g, n) for g, n in k["gruende"].items()))
    if k["n"] < MIN_RUNDEN:
        print("  -> nur %d Runden: das ist ein Befund, keine Messung. "
              "Belastbar wird es ab %d." % (k["n"], MIN_RUNDEN))


def main():
    global MIN_RUNDEN
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(
        description="Auswertung der Spuren, die keine eigene haben")
    p.add_argument("--spur", action="append", choices=list(SPUREN),
                   help="nur diese Spur(en)")
    p.add_argument("--min", type=int, default=MIN_RUNDEN,
                   help="Schwelle fuer 'belastbar' (Standard %d)" % MIN_RUNDEN)
    a = p.parse_args()
    MIN_RUNDEN = a.min

    spuren = a.spur or list(SPUREN)
    zahlen = {}
    for spur in spuren:
        # Ein Weg fuer beide Aufrufer: hier stand die Zuordnung Spur ->
        # Rechenweg bis 15.09.2026 ein zweites Mal (siehe kennzahlen_fuer).
        k = kennzahlen_fuer(spur)
        zahlen[spur] = k
        zeige(spur, k)

    print("\n=== Uebersicht ===")
    print("  %-10s %6s %8s %10s %8s" % ("Spur", "Runden", "Treffer",
                                        "Ergebnis", "Treffer %"))
    for spur, k in zahlen.items():
        if k is None:
            print("  %-10s %6s" % (spur, "-"))
            continue
        print("  %-10s %6d %8d %10.2f %7.0f %%"
              % (spur, k["n"], k["treffer"], k["ergebnis"], k["treffer_pct"]))
    print("\n  spiegel, omniquant und gitter haben eigene Auswertungen "
          "(auswertung.py im jeweiligen Ordner).")


if __name__ == "__main__":
    main()
