"""Geister-Zeilen im Journal auf den echten Wert ziehen.

DAS PROBLEM (xperp, 21.09.2026)
-------------------------------
`bueche_geister_aus` schrieb die Verkaufszeile einer von Hand geschlossenen
Position mit `margin_usd = 0.00`. Die Wachen lesen die schliessen-Zeile als
ERLOES - die Runde zaehlte damit als Totalverlust in Hoehe des Einsatzes.
HBAR kostete das -16.84 USD in genau der Drawdown-Kurve, aus der der
Kill-Switch liest.

Der Code schreibt seit dem 22.09.2026 den echten Wert (Boersenergebnis, sonst
neutral). ALTE Zeilen tragen die 0.00 aber weiter - und eine Wache, die nur
den Code prueft, sieht sie nie.

WAS ES TUT
----------
Liest das Journal mit DERSELBEN FIFO-Regel wie `wachen_xperp.runden_aus_journal`
(eroeffnen-Zeile = Einsatz, schliessen-Zeile = Erloes, je Instrument in
Reihenfolge) und ersetzt bei einer kaputten Zeile
(`grund = buchbereinigung_geist` und Erloes genau 0.00) die 0.00 durch den
Einsatz, mit dem die Zeile verrechnet wird. Ergebnis: die Runde steht neutral
(Einsatz zurueck) statt als Vollverlust. Es wird NICHTS anderes angefasst -
keine Zeile geloescht, keine Zahl sonst veraendert.

WARUM NEUTRAL UND NICHT "DAS ECHTE ERGEBNIS": Bei diesen Zeilen stand die
Position in Wahrheit noch (HBAR wurde am selben Abend zurueckgebucht). Ein
Boersenergebnis gibt es dazu nicht - der ehrliche Wert ist der Einsatz.

VOR DEM SCHREIBEN: eine Kopie `handelsjournal.bak-JJJJMMTT.csv` daneben.

DER ZWEITE FALL (T-276, 01.10.2026): Geister-Zeilen mit NICHT-NULL-Erloes.
`bueche_geister_aus` schrieb am 24.09./29.09. zweimal falsche Erloese (XAU 80.07
statt 160.22, BZ 30.46 statt 134.14) - die Runden zaehlten -79.70/-107.59, die
Boerse hatte +0.45/-3.91. Rund 184 USD fiktiver Verlust standen in genau der
Kapitalkurve, aus der der Kill-Switch liest. Mit `--gegen-boerse` prueft das
Werkzeug JEDE Geister-Zeile gegen `/account/positions-history` (instId UND
Kontraktzahl muessen eindeutig passen, Zeitabstand hoechstens 12 h) und zieht
den Erloes auf `einsatz + funding + realizedPnl`. Ohne eindeutigen Boersen-
zeugen wird die Zeile NICHT angefasst - nach Hausregel: ohne Zeugen bleibt
stehen, was nicht bewiesen ist. Ohne die Flag bleibt das Werkzeug bei Fall 1
und braucht kein Netz (so ruft die Hermes-Wache es auf).

AUFRUF
    python geister_nachziehen.py --vorschau     (Standard, schreibt nichts)
    python geister_nachziehen.py --anwenden
    python geister_nachziehen.py --anwenden --spur xperp
    python geister_nachziehen.py --gegen-boerse --spur xperp    (Fall 1 + 2)
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)

KAPUTT_GRUND = "buchbereinigung_geist"
SPALTEN_MIN = ("zeit", "modus", "aktion", "inst", "kontrakte", "margin_usd",
               "grund")
# Fall 2 (T-276): Toleranz der Buch-Nettorechnung gegen den Boersenwert.
# Unter einem Dollar ist keine Geisterbuchung "falsch" - sie ist Rundung.
ZEUG_TOLERANZ_USD = 1.00
ZEUG_MAX_STUNDEN = 12


def _zeit_ms(text):
    """ISO-Zeitstempel des Journals in Millisekunden (Boerse rechnet in ms)."""
    from datetime import datetime
    try:
        return int(datetime.fromisoformat(str(text)).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def boese_zeug(history, inst, kontrakte, zeit):
    """Der eindeutige Boersen-Zeuge fuer eine geschlossene Position.

    Treffer nur, wenn instId UND Kontraktzahl (closedPos) passen und der
    Zeitabstand hoechstens ZEUG_MAX_STUNDen betraegt. Zwei verschiedene
    Treffer auf demselben Schlussel sind MEHRDEUTIG - dann lieber gar kein
    Zeug als das falsche (Hausregel: ohne Zeugen wird nichts angefasst).
    Gibt (eintrag, grund) zurueck; eintrag=None mit Grund als Text.
    """
    try:
        k = float(kontrakte)
    except (TypeError, ValueError):
        return None, "keine Kontraktzahl"
    ms = _zeit_ms(zeit)
    treffer = []
    for e in history or []:
        if str(e.get("instId") or "") != str(inst):
            continue
        try:
            if abs(float(e.get("closeTotalPos") or 0.0) - k) > 1e-6:
                continue
            t = int(e.get("uTime") or 0)
        except (TypeError, ValueError):
            continue
        if ms is not None and abs(t - ms) > ZEUG_MAX_STUNDEN * 3600 * 1000:
            continue
        treffer.append((abs((t - ms) if ms is not None else 0), e))
    if not treffer:
        return None, "kein Zeuge (inst/Kontrakt/Zeit)"
    treffer.sort(key=lambda x: x[0])
    if len(treffer) > 1 and treffer[0][1] is not treffer[1][1] \
            and abs(treffer[0][0] - treffer[1][0]) < 60_000:
        return None, "mehrdeutig (%d Treffer in einer Minute)" % len(treffer)
    return treffer[0][1], None


def _journale(spur=None):
    """Alle Journale, die nach dem eroeffnen/schliessen-Schema laufen."""
    ordner = [os.path.join(HANDEL, spur)] if spur else \
        [os.path.join(HANDEL, d) for d in sorted(os.listdir(HANDEL))]
    treffer = []
    for o in ordner:
        if not os.path.isdir(o):
            continue
        for name in sorted(os.listdir(o)):
            if not (name.startswith("handelsjournal") and name.endswith(".csv")):
                continue
            if ".bak-" in name or "falsch-skaliert" in name:
                continue
            p = os.path.join(o, name)
            try:
                with open(p, "r", newline="", encoding="utf-8") as f:
                    f.readline()          # Kopfzeile: nur Lesbarkeit pruefen
            except OSError:
                continue
            treffer.append(p)
    return treffer


def _kaputte_zeilen(pfad, zeuge=None):
    """[(zeilenindex, inst, alter_wert, richtiger_wert)] mit FIFO wie die Wachen.

    Gibt zusaetzlich die Kopfzeile und alle Zeilen zurueck, damit der Aufrufer
    nicht zweimal liest.

    Fall 1 (wie 21.09.): grund=buchbereinigung_geist UND Erloes 0.00 -> neutral
    auf den Einsatz ziehen.
    Fall 2 (T-276, nur wenn `zeuge` gegeben): grund=buchbereinigung_geist,
    Erloes ungleich 0, aber das Buch-GV weicht vom Boersenwert ab (Toleranz
    ZEUG_TOLERANZ_USD) -> Erloes auf einsatz + funding + realizedPnl ziehen.
    `zeuge(inst, kontrakte, zeit)` gibt (eintrag, grund) zurueck - aufrufbar
    mit `boese_zeug` ueber eine geholte positions-history; None = kein
    eindeutiger Beweis, Zeile bleibt stehen.
    """
    with open(pfad, "r", newline="", encoding="utf-8") as f:
        kopf = f.readline()
        zeilen = list(csv.reader(f))
    namen = next(csv.reader([kopf]))
    fehlend = [s for s in SPALTEN_MIN if s not in namen]
    if fehlend:
        # Ein Journal ohne diese Spalten ist nicht reparierbar - und das ist
        # KEIN Fehler des Werkzeugs, sondern ein fremdes/altes Schema. Vorher
        # lief die Pruefung hier durch und `namen.index("kontrakte")` fiel
        # darunter mit ValueError um (gefunden am 01.10.2026 beim Aufraeumen
        # des xperp-Buchs). Beide Gruende nennen dasselbe Wort, damit ein
        # Aufrufer nur EINE Form kennen muss.
        return kopf, zeilen, namen, [], \
            "kein eroeffnen/schliessen-Schema (Spalten fehlen: %s)" \
            % ", ".join(fehlend)
    i_zeit, i_akt = namen.index("zeit"), namen.index("aktion")
    i_inst, i_ktr = namen.index("inst"), namen.index("kontrakte")
    i_margin, i_grund = namen.index("margin_usd"), namen.index("grund")
    offen, funding = {}, {}          # inst -> Liste der Einsaetze/Funding je Runde
    kaputt = []
    gesehen_eroeffnen = False
    for n, z in enumerate(zeilen):
        if len(z) <= max(i_grund, i_ktr, i_margin):
            continue
        akt, inst = z[i_akt], z[i_inst]
        try:
            betrag = float(z[i_margin])
        except (TypeError, ValueError):
            betrag = None
        if akt == "eroeffnen":
            gesehen_eroeffnen = True
            if betrag is not None:
                offen.setdefault(inst, []).append(betrag)
                funding.setdefault(inst, []).append(0.0)
        elif akt == "funding" and funding.get(inst):
            if betrag is not None:
                funding[inst][0] += betrag      # wie die Wache: auf die aelteste offene
        elif akt == "schliessen":
            einsatz = offen[inst].pop(0) if offen.get(inst) else None
            fd = funding[inst].pop(0) if funding.get(inst) else 0.0
            if z[i_grund] != KAPUTT_GRUND:
                continue
            if einsatz is None:
                continue
            if betrag == 0.0:
                kaputt.append((n, inst, z[i_margin], "%.2f" % einsatz))
            elif zeuge is not None:
                eintrag, grund = zeuge(inst, z[i_ktr], z[i_zeit])
                if eintrag is not None:
                    try:
                        pnl = float(eintrag.get("realizedPnl") or 0.0)
                    except (TypeError, ValueError):
                        pnl = None
                    if pnl is not None and abs((betrag - einsatz - fd) - pnl) > ZEUG_TOLERANZ_USD:
                        neu = "%.2f" % (einsatz + fd + pnl)
                        kaputt.append((n, inst, z[i_margin], neu))
    if not gesehen_eroeffnen:
        return kopf, zeilen, namen, [], "kein eroeffnen/schliessen-Schema"
    return kopf, zeilen, namen, kaputt, None


def korrigiere_datei(pfad, anwenden=True, still=False, zeuge=None):
    """EINE Journaldatei. Rueckgabe: (kaputte_zeilen, geschrieben).

    Getrennt von `nachziehen`, damit ein Aufrufer mit einem bekannten Pfad
    (die Hermes-Wache) genau diese Datei behandeln kann - und damit ein Test
    auf einem Temp-Journal laufen kann, ohne die echten Buecher zu suchen.
    `zeuge=None` haelt das Werkzeug bei Fall 1 (kein Netz, wie die Wache es
    ruft); ein rufbarer Zeuge (boese_zeug ueber eine positions-history)
    zusaetzlich die Geister-Zeilen mit Nicht-Null-Erloes gegen die Boerse
    pruefen (Fall 2, T-276).
    """
    kopf, zeilen, namen, kaputt, fehler = _kaputte_zeilen(pfad, zeuge=zeuge)
    if fehler or not kaputt:
        return [], False
    if not still:
        print("%s: %d kaputte Geister-Zeile(n)" % (pfad, len(kaputt)))
    for n, inst, alt, neu in kaputt:
        if not still:
            print("  Zeile %d  %-28s  Erloes %s -> %s" % (n + 1, inst, alt, neu))
        zeilen[n][namen.index("margin_usd")] = neu
    if not anwenden:
        return kaputt, False
    sicherung = pfad.replace(".csv", ".bak-%s.csv"
                             % datetime.now(timezone.utc).strftime("%Y%m%d"))
    if not os.path.exists(sicherung):
        shutil.copy2(pfad, sicherung)
        if not still:
            print("  Sicherung: %s" % os.path.basename(sicherung))
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        f.write(kopf)
        csv.writer(f).writerows(zeilen)
    return kaputt, True


def hol_boersengeschichte(limit=100):
    """Die zuletzt geschlossenen Positionen bei OKX (xperp-Ebene, nur lesend).

    Over die okxf-Module derselben Spur - Schluessel und Host liegen schon in
    den Windows-Benutzervariablen, und die Antwort ist die einzige Stelle, an
    der OKX ein realisiertes Ergebnis je Position fuehrt.
    """
    if HIER not in sys.path:
        sys.path.insert(0, HIER)
    import okxf
    return okxf.geschlossene_positionen(limit=limit)


def nachziehen(spur=None, anwenden=False, gegen_boerse=False):
    zeuge = None
    if gegen_boerse:
        if spur not in (None, "xperp"):
            print("Die Boersengegenprobe (Fall 2) kennt nur die xperp-Spur - "
                  "okxf ist ihre Boerse. Mit --spur %s laeuft nur Fall 1." % spur)
        try:
            history = hol_boersengeschichte()
            import functools
            zeuge = functools.partial(boese_zeug, history)
            print("Boersenhistorie geholt: %d geschlossene Positionen als Zeugen."
                  % len(history or []))
        except Exception as e:                                       # noqa: BLE001
            print("BOERSENZEUGEN NICHT HOLBAR (%s: %s) - Fall 2 faellt aus, "
                  "Fall 1 laeuft wie bisher." % (type(e).__name__, e))
    gesamt = 0
    for p in _journale(spur):
        zeuge_p = zeuge if (zeuge is not None and
                             "/xperp/" in p.replace("\\", "/")) else None
        kaputt, geschrieben = korrigiere_datei(p, anwenden=anwenden, zeuge=zeuge_p)
        if kaputt:
            gesamt += len(kaputt)
    if not gesamt:
        print("Keine kaputten Geister-Zeilen gefunden.")
        return 0
    if not anwenden:
        print("\nVORSCHAU - nichts geschrieben. Mit --anwenden ausfuehren.")
        return 1
    print("\nFertig: %d Zeile(n) auf den echten Wert gezogen." % gesamt)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spur", default=None)
    ap.add_argument("--anwenden", action="store_true")
    ap.add_argument("--vorschau", action="store_true",
                    help="nur zeigen (Standard, wenn --anwenden fehlt)")
    ap.add_argument("--gegen-boerse", action="store_true",
                    help="Fall 2 (T-276): Geister-Zeilen mit Nicht-Null-Erloes "
                         "gegen /account/positions-history pruefen (nur xperp, "
                         "nur lesend, kein Orderweg)")
    a = ap.parse_args(argv)
    return nachziehen(spur=a.spur, anwenden=a.anwenden, gegen_boerse=a.gegen_boerse)


if __name__ == "__main__":
    sys.exit(main())
