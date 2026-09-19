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
import risikostufe  # gleicher Ordner: Dateinamen der Risikostufen
import zeitfenster  # gleicher Ordner: Fenstergrenzen und Zeilenfilter

# Risikostufe dieser Auswertung: None = Basis. Setzt main() aus --risiko.
STUFE = None

HIER = Path(__file__).resolve().parent

# Ab wie vielen geschlossenen Runden eine Spur ueberhaupt etwas aussagt.
# Dieselbe Schwelle wie buchauswertung.MIN_AUSSTIEGE - zwei Schwellen fuer
# dieselbe Frage laufen sonst auseinander.
MIN_RUNDEN = 8

SPUREN = ("xperp", "swap", "scanner", "kraken", "orbk", "gitter", "nautilus")

# Die vier Indikator-Spuren journalisieren kauf/verkauf mit `einsatz_usd`
# (beim Kauf der Einsatz, beim Verkauf der Erloes). Sie stehen getrennt,
# weil IHR JOURNAL anders heisst, nicht weil anders gerechnet wird - der
# Rechenweg steht in runden_indikator() an einer Stelle.
INDIKATOR_SPUREN = ("squeeze", "wavetrend", "macd_mtf", "supertrend", "mosaic")

# Bot-Spuren (16.09.2026): Papierbuecher auf den Signalen geklonter Fremd-Bots
# (Werkstatt/Repos/moon-dev-ai-agents). Ihr Journal hat dieselbe Form wie das
# der Indikator-Spuren (kauf/verkauf mit einsatz_usd), deshalb derselbe
# Rechenweg - nur der NAME der Gruppe ist ein anderer.
BOT_SPUREN = ("moondev_funding", "moondev_listingarb", "moondev_topmovers",
              "moondev_marktlage", "iv_wand",
              # IV-WAELLE (18.09.2026): Deribit-IV-Waende, dieselbe
              # Journalform (kauf/verkauf mit einsatz_usd) - derselbe Weg.
              "iv_waelle",
              # Die drei Sprachmodell-Spuren (17.09.2026) fuehren dasselbe
              # Journal (kauf/verkauf mit einsatz_usd) - derselbe Rechenweg.
              "moondev_whale", "moondev_liquidation", "moondev_sentiment",
              # MOONDEV_SNIPER (19.09.2026): neue Solana-Launches, dasselbe
              # Journal - derselbe Weg.
              "moondev_sniper")
SPUREN = SPUREN + INDIKATOR_SPUREN + BOT_SPUREN


def kennzahlen_fuer(spur, von=None, bis=None):
    """Die Kennzahlen EINER Spur - Zuordnung Spur -> Rechenweg an EINER Stelle.

    Der Weg stand bis zum 15.09.2026 nur in `main()`. Ein zweiter Aufrufer
    (die Telegram-Befehle in `befehle.py`) haette die Zuordnung abschreiben
    muessen - und beim naechsten neuen Feld nur an einer Stelle mitgezogen.
    `main()` und `befehle.py` rufen jetzt beide diese Funktion.

    von/bis mit Vorgabe None: ohne Angabe bleibt alles wie vorher.

    DAS FENSTER SCHNEIDET RUNDEN, NICHT ZEILEN. Eine Runde gehoert in das
    Fenster ihres AUSSTIEGS - dort faellt ihr Ergebnis an. Der Schnitt
    passiert deshalb NACH der Paarung. Ein Schnitt davor (bis 18.09.2026)
    verwarf jede Runde, die vor dem Fenster einstieg und darin ausstieg:
    _paare() sah einen Ausstieg ohne Einstieg und liess ihn fallen. Die
    Zahl war zu klein, und niemand erfuhr davon. Dieselbe Lesart hat
    buchauswertung.lade_zeilen(), das ohnehin nur Ausstiegszeilen liest -
    erst damit beantworten beide Wege in gesamtbilanz.summe() dieselbe
    Frage.

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
    elif spur in INDIKATOR_SPUREN or spur in BOT_SPUREN:
        runden = runden_indikator(z)
    elif spur == "gitter":
        runden = gitter_zyklen(z)
    else:
        runden = []
    runden = [r for r in runden if zeitfenster.im_fenster(r, von, bis)]
    return kennzahlen(runden, "USD")


def belastbar(k, min_runden=None):
    """Sagt die Spur im gewaehlten Fenster ueberhaupt etwas?

    Die Schwelle gilt JE FENSTER. Ein Monat mit drei Runden ist keine
    Aussage, auch wenn die Spur insgesamt fuenfzig hat - sonst erzeugt die
    Zeitachse genau die Scheingenauigkeit, die MIN_RUNDEN verhindern soll.
    """
    if not k:
        return False
    return k.get("n", 0) >= (MIN_RUNDEN if min_runden is None else min_runden)


def hat_buch(spur, datei="handelsjournal.csv"):
    """Fuehrt die Spur ueberhaupt ein Journal?

    Getrennt von "hat Runden": eine Spur ohne Datei und eine Spur mit leerer
    Datei sind verschiedene Befunde, und nur der erste ist ein
    Betriebsfehler.
    """
    if STUFE:
        datei = risikostufe.datei_fuer(datei, STUFE)
    return (HIER / spur / datei).exists()


def buch_seit(spur):
    """Seit wann die Spur laeuft, soweit der Baum es hergibt.

    Quelle ist die Aenderungszeit von `zustand.json` - ohne Journal gibt es
    keine andere. Das ist ein Anhaltspunkt, keine Anmeldung: die Datei wird
    bei jedem Lauf angefasst. Sie beantwortet trotzdem die Frage, auf die es
    ankommt - laeuft die Spur, obwohl sie nichts schreibt?
    """
    p = HIER / spur / "zustand.json"
    if not p.exists():
        return None
    return datetime.fromtimestamp(p.stat().st_mtime).date()


def lage_der_spur(spur, k):
    """Eine von drei Kategorien - nie ein blosser Strich."""
    if not hat_buch(spur):
        return "kein Buch"
    if not belastbar(k):
        return "zu wenige Runden"
    return "belastbar"


def anzeige_fuer(spur, k):
    """Der Text der Lage-Spalte in der Uebersicht - eine von vier
    Kategorien, an genau dieser Stelle entschieden.

    lage_der_spur() kennt nur drei: sie geht von einem Journal aus. Die
    vierte - ein vorhandenes Buch ganz ohne geschlossene Runde (`k is
    None`) - liegt zwischen "kein Buch" und "zu wenige Runden" und braucht
    einen eigenen Text, sonst sieht sie wie "kein Buch" aus.
    """
    if not hat_buch(spur):
        return "kein Buch"
    if k is None:
        return "keine geschlossene Runde"
    return lage_der_spur(spur, k)


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
    """Die Journalzeilen einer Spur - alle, ungeschnitten.

    Kein Zeitfenster. Wer in Runden zaehlt, braucht ALLE Zeilen: die
    Paarung in _paare() findet den Einstieg sonst nicht, wenn er vor dem
    Fenster liegt, und verwirft die Runde stillschweigend. Geschnitten wird
    nach der Paarung, an der Ausstiegszeit - siehe kennzahlen_fuer().
    """
    if STUFE:
        # Risikostufe: dieselbe Auswertung auf den Dateien der Stufe
        # (handelsjournal.mittel.csv). Der Rechenweg bleibt derselbe - die
        # Betraege sind groesser, die Regeln nicht anders.
        datei = risikostufe.datei_fuer(datei, STUFE)
    p = HIER / spur / datei
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


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
            # Die Zeit der Runde ist die ihres AUSSTIEGS - dort faellt das
            # Ergebnis an. Der Name `zeit` ist der der Journalspalte, damit
            # zeitfenster.im_fenster() die Runde ohne Sonderfall liest.
            "zeit": r.get("zeit") or "",
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


def runden_indikator(zeilen_):
    """Indikatorspuren: kauf/verkauf, Betrag in `einsatz_usd`.

    Derselbe Feldname traegt beim Kauf den Einsatz und beim Verkauf den Erloes.
    Eine Gebuehr fuehren diese Spuren nicht (kein `gebuehr_taker` in ihrer
    wachen.json), also wird auch keine behauptet - kosten = 0. Sobald eine
    Gebuehr im Journal steht, gehoert sie hier gelesen, nicht geschaetzt.

    ACHTUNG: Bis zum 15.09.2026 schrieb die Spur den Erloes als
    `nominal + (kurs - einstieg)` - die rohe Kursdifferenz, bei BTC ein Faktor
    von rund 70.000. Zeilen aus jener Zeit liegen als
    `handelsjournal.falsch-skaliert-20260915.csv` daneben und zaehlen nicht.
    """
    def ergebnis(ein, aus):
        einsatz = zahl(ein.get("einsatz_usd"))
        erloes = zahl(aus.get("einsatz_usd"))
        if not einsatz or erloes is None:
            return None, None
        return erloes - einsatz, 0.0

    return _paare(zeilen_, {"kauf"}, {"verkauf"}, "einsatz_usd", ergebnis, "USD")


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
                       "halten": None, "zeit": r.get("zeit") or ""})
    return runden


# Die Aktionsnamen, mit denen gitter/handeln.py eine Stufe schliesst.
# `AUSSTIEG` ist der, den es wirklich schreibt (gitter/handeln.py:377);
# `VERKAUF` stand hier allein und traf damit keine einzige Zeile - der
# Rundenweg meldete fuer gitter immer null Zyklen, waehrend die eigene
# Auswertung der Spur dieselben Zeilen zaehlte.
GITTER_AUSSTIEG = ("AUSSTIEG", "VERKAUF")


def gitter_zyklen(zeilen_):
    """Ein Gitter-Zyklus ist der Ausstieg aus einer vorher gekauften Stufe.
    Der Gewinn steht als gw_usd in der Ausstiegszeile."""
    offen = {}
    zyklen = []
    for r in zeilen_:
        art = (r.get("aktion") or "").strip().upper()
        stufe = r.get("stufe")
        if art == "KAUF":
            offen.setdefault(stufe, []).append(r)
        elif art in GITTER_AUSSTIEG:
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
                           "halten": tage(ein.get("zeit"), r.get("zeit")),
                           "zeit": r.get("zeit") or ""})
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
    if not belastbar(k):
        print("  -> nur %d Runden: das ist ein Befund, keine Messung. "
              "Belastbar wird es ab %d." % (k["n"], MIN_RUNDEN))


def main():
    global MIN_RUNDEN, STUFE
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(
        description="Auswertung der Spuren, die keine eigene haben")
    p.add_argument("--spur", action="append", choices=list(SPUREN),
                   help="nur diese Spur(en)")
    p.add_argument("--min", type=int, default=MIN_RUNDEN,
                   help="Schwelle fuer 'belastbar' (Standard %d)" % MIN_RUNDEN)
    p.add_argument("--risiko", choices=sorted(risikostufe.FAKTOREN),
                   default=risikostufe.STANDARD,
                   help="Risikostufe auswerten (Vorgabe %s = Basis). Liest "
                        "dieselben Spalten aus handelsjournal.mittel.csv - "
                        "die Runden sind andere, die Rechnung nicht."
                        % risikostufe.STANDARD)
    p.add_argument("--tage", type=int,
                   help="nur die letzten N Tage auswerten")
    p.add_argument("--seit", help="Fensteranfang, JJJJ-MM-TT")
    p.add_argument("--bis", help="Fensterende, JJJJ-MM-TT (einschliesslich)")
    a = p.parse_args()
    try:
        von, bis = zeitfenster.fenster(tage=a.tage, seit=a.seit, bis=a.bis)
    except ValueError as e:
        p.error(str(e))
    if von or bis:
        print("Fenster: %s bis %s\n"
              % (von.date() if von else "Anfang",
                 bis.date() if bis else "heute"))
    MIN_RUNDEN = a.min
    STUFE = None if a.risiko == risikostufe.STANDARD else a.risiko
    if STUFE:
        print("Risikostufe %s: eigene Journale je Spur "
              "(handelsjournal.%s.csv)\n" % (STUFE, STUFE))

    spuren = a.spur or list(SPUREN)
    zahlen = {}
    for spur in spuren:
        # Ein Weg fuer beide Aufrufer: hier stand die Zuordnung Spur ->
        # Rechenweg bis 15.09.2026 ein zweites Mal (siehe kennzahlen_fuer).
        k = kennzahlen_fuer(spur, von=von, bis=bis)
        zahlen[spur] = k
        zeige(spur, k)

    print("\n=== Uebersicht ===")
    print("  %-10s %6s %8s %10s %8s  %s"
          % ("Spur", "Runden", "Treffer", "Ergebnis", "Treffer %", "Lage"))
    ohne_buch = []
    for spur, k in zahlen.items():
        # Der Text kommt immer aus anzeige_fuer(); hier wird nur die
        # Zeilenform gewaehlt. Ein Vergleich auf den Text waere eine
        # zweite Heimat der Entscheidung - ein Umbenennen wuerde still
        # den Ablauf verbiegen.
        anzeige = anzeige_fuer(spur, k)
        if not hat_buch(spur):
            ohne_buch.append(spur)
            print("  %-10s %6s %8s %10s %8s  %s"
                  % (spur, "-", "-", "-", "-", anzeige))
            continue
        if k is None:
            print("  %-10s %6d %8s %10s %8s  %s"
                  % (spur, 0, "-", "-", "-", anzeige))
            continue
        print("  %-10s %6d %8d %10.2f %7.0f %%  %s"
              % (spur, k["n"], k["treffer"], k["ergebnis"],
                 k["treffer_pct"], anzeige))
    if ohne_buch:
        print("\n  KEIN BUCH - diese Spuren schreiben kein Journal:")
        for spur in ohne_buch:
            seit = buch_seit(spur)
            print("    %-10s Zustand zuletzt %s"
                  % (spur, seit.isoformat() if seit else "nie"))
        print("  Eine laufende Spur ohne Journal ist ein Betriebsfehler, "
              "keine Formatfrage.")
    print("\n  spiegel, omniquant und gitter haben eigene Auswertungen "
          "(auswertung.py im jeweiligen Ordner).")
    if STUFE:
        print("  Gezaehlt wurde die Risikostufe %s - der Basislauf laeuft "
              "daneben unveraendert weiter." % STUFE)


if __name__ == "__main__":
    main()
