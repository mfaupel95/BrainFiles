"""Ein Bild aller Spuren - fuer das Handy, einmal am Tag.

Angelegt am 03.09.2026 auf Max' Anweisung ("taegliche Meldung mit Updates auf
mein Handy"). Liest nur; loest nichts aus, aendert keine Datei.

Der Bericht beantwortet drei Fragen in dieser Reihenfolge, weil sie am
Handy-Display in dieser Reihenfolge zaehlen:

  1. Was ist offen, und wie steht es?   - Positionen gegen den aktuellen Kurs
  2. Was hindert Live gerade?           - die Sperren, im Klartext
  3. Was waere heute dran?              - die Spitze der Rangliste

Robust gegen Ausfaelle: Jede Spur wird einzeln eingesammelt. Faellt eine aus
(kein Netz, kaputte Datei), steht das im Bericht und die anderen kommen
trotzdem. Ein Melder, der bei der ersten Stoerung schweigt, meldet genau dann
nichts, wenn es darauf ankommt.

Aufruf:
    python tagesbericht.py            # Bericht auf die Konsole
    python tagesbericht.py --senden   # zusaetzlich per Telegram
    python tagesbericht.py --risiko mittel   # der Bericht der Stufe mittel
    python tagesbericht.py --risiko alle     # Basis, mittel und hoch untereinander
"""

import argparse
import csv
import datetime as dt
import json
import os
import sys
import traceback
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "scanner"))

import melder                                            # noqa: E402
import risikostufe                                       # noqa: E402
import spiegelstand                                     # noqa: E402
import lage                                              # noqa: E402
import schnappschuss                                     # noqa: E402
from lage import (                                       # noqa: E402
    HOLER, sperren, wachenlage,
    # Zusaetzlich re-exportiert: befehle.py, dauerlauf.py und die Tests
    # unter kopier1zu1/tests und spiegel/tests greifen bisher auf diese
    # Namen ueber tagesbericht.* zu. Der Umzug nach lage.py aendert nur den
    # Ort der Erhebung, nicht ihre bisherige Schnittstelle nach aussen.
    spur_xperp_positionen, spur_xperp, spur_spiegel,
    bilanz, _lies,
)


# --- Text -------------------------------------------------------------------

def _zahl(x):
    """Eine Zahl, wie ein Mensch sie liest - nie in Exponentialschreibweise.

    Befund 25.09.2026: Robinhood-Radar und Moon-Dev Sniper standen im Bericht
    als '0x48f413c32a7b... long 4.258775833450569e-05'. Die Zahl war richtig
    (Einstiegspreis eines Token mit acht Nachkommastellen), aber unlesbar.
    Die Stellenzahl richtet sich nach der Groessenordnung: bei Werten unter
    0,01 bleiben vier Ziffern sichtbar.
    """
    if x is None:
        return "-"
    x = float(x)
    ax = abs(x)
    if ax == 0:
        return "0"
    if ax >= 1000:
        stellen = 2
    elif ax >= 1:
        stellen = 4
    elif ax >= 0.01:
        stellen = 6
    else:
        import math
        stellen = min(12, max(6, int(-math.log10(ax)) + 4))
    s = ("%%.%df" % stellen) % x
    return s.rstrip("0").rstrip(".") if "." in s else s


def _kurz(name, breite=16):
    """Lange Positionsschluessel kuerzen - ein Token-Mint sprengt sonst die Zeile."""
    n = str(name or "?")
    return n if len(n) <= breite else n[:breite - 1] + "\u2026"


def zeile_position(p, waehrung):
    if p["kurs"] is None:
        return "  %-12s %s  (kein Kurs)" % (_kurz(p["name"]), _zahl(p["einstieg"]))
    pfeil = "+" if p["vh"] >= 0 else ""
    # Stop-Abstand richtungsbewusst: bei long liegt der Stop unter dem Kurs
    # (kurs/stop - 1 positiv = Luft), bei short ueber dem Kurs (kurs/stop - 1
    # negativ, obwohl der Stop NICHT gerissen ist). Ohne den Richtungsfaktor
    # zeigt der Bericht jede gesunde short-Position als "Stop gerissen" -
    # Befund 13.09.2026 an der ersten omniquant-short-Position.
    vz = 1 if (p.get("seite") or p.get("richtung") or "long") == "long" else -1
    abstand = (vz * (p["kurs"] / p["stop"] - 1) * 100) if p.get("stop") else None
    entfernung = None
    if not p.get("stop") and p.get("ziel"):
        # Eine Buch-Spur ohne Stop (Gitter: verkauft wird eine Stufe hoeher)
        # braucht trotzdem eine Marke am Kurs: ohne sie steht in der Zeile
        # nur die Bewegung und niemand sieht, wie weit der Verkauf entfernt
        # ist. Richtungsbewusst wie der Stop-Abstand.
        ziel = p["ziel"]
        if ziel and p["kurs"]:
            entfernung = vz * (ziel / p["kurs"] - 1) * 100
    text = "  %-12s %s%.1f%%  %.0f %s" % (
        p["name"], pfeil, p["vh"], p["wert"], waehrung)
    if p.get("hebel") and p["hebel"] > 1:
        text += " Margin @%.0fx" % p["hebel"]
    if entfernung is not None:
        text += "  Verkauf in %.1f %%" % abs(entfernung)
    if abstand is not None:
        if abstand < 0:
            # Der Kurs steht jenseits des Stops. Bei den Kontraktspuren
            # schliesst der naechste Lauf, aber solange gilt: nicht als
            # negativen Prozentsatz zeigen - das liest sich wie ein Fehler.
            text += "  Stop gerissen (%.1f%%)" % abs(abstand)
        else:
            # Bei Hebel ist der Stop-Abstand am Kurs gemessen, der Gewinn an
            # der Margin. Ohne den Hebel danebenzuschreiben liest sich
            # "+1,3 % bei 4,1 % Stop" wie viel Luft - tatsaechlich sind es
            # 0,8 % Kurs.
            text += "  Stop %.1f%% (Kurs)" % abs(abstand)
    if p.get("kurs_warnung"):
        text += "  DATENHINWEIS: %s" % p["kurs_warnung"]
    return text


def spiegelzeile():
    """Eine Zeile zum Stand der Kopie ausser Haus (Bedingung 4).

    Gelesen wird die Kopie selbst (byte-genau) und der Vermerk im Zustand der
    Spur - beides lokal, kein Netz. Ein Fehler darf den Bericht nicht kippen:
    dann steht der Grund in der Zeile statt eines Tracebacks.
    """
    try:
        e = spiegelstand.stand(HIER)
    except Exception as fehler:                          # noqa: BLE001
        return "Journal ausser Haus: nicht geprueft (%s)" % str(fehler)[:80]
    text = spiegelstand.kurz(e)
    if e.get("fehler") or e["abweichend"]:
        return "<b>Journal ausser Haus: %s</b>" % text
    return "Journal ausser Haus: %s" % text


# Die Spuren dieses Berichts in Anzeige-Reihenfolge. EINE Liste fuer alle
# Aufrufer: `baue()` (Tagesbericht) und `befehle.py` (/lage) lesen dieselbe -
# eine zweite Aufzaehlung waere beim naechsten neuen Spurordner still veraltet.
# Die Risikostufen ueber der Basis (Handel/risikostufe.py). Der Bericht oben
# zeigt die Basis; hier geht es um die zweiten Laeufe, die mit groesseren
# Betraegen Daten sammeln - ohne diese Zeile waeren sie unsichtbar.
STUFEN = ("mittel", "hoch")
# Reihenfolge des Gesamtberichts (`--risiko alle`): Basis zuerst, dann die
# Stufen in ihrer Reihenfolge - nicht alphabetisch, sonst stuende "hoch" oben.
STUFEN_ALLE = (risikostufe.STANDARD,) + STUFEN


def _stufenbuecher(stufe):
    """Spuren mit einem Buch dieser Stufe, aus dem Ordnernamen gelesen.

    Kein Import von `dauerlauf.SPUREN`: dauerlauf importiert dieses Modul
    (Zyklus), und ein Rueckimport waere ein halb geladener Zyklus. Ein Buch
    heisst zustand.<stufe>.json - wer eines hat, laeuft in dieser Stufe.
    """
    aus = []
    try:
        namen = sorted(os.listdir(HIER))
    except OSError:
        return aus
    for name in namen:
        ordner = os.path.join(HIER, name)
        if not os.path.isdir(ordner):
            continue
        z = _lies(os.path.join(ordner, risikostufe.datei_fuer("zustand.json",
                                                             stufe)))
        if isinstance(z, dict):
            aus.append((name, z))
    return aus


def buchzeile():
    """Herkunft der Zahlen eines Stufenberichts: welche Dateien er gelesen hat.

    Ohne diese Zeile sieht ein Bericht mit vierfachen Betraegen genauso aus wie
    die Basis - die Stufe muss am Buch erkennbar sein, nicht nur am Kopf.
    """
    s = risikostufe.suffix()
    if not s:
        return ""
    return ("Buch: zustand%s.json / handelsjournal%s.csv (Faktor %.0f) - "
            "die Basis laeuft daneben unveraendert weiter."
            % (s, s, risikostufe.faktor()))


def stufenzeile():
    """Eine Zeile je Risikostufe: laeuft sie, und was hat sie gemessen.

    Gelesen wird nur. Die Zahlen kommen aus DERSELBEN Rechnung wie die
    Auswertung (`auswertung_alle.kennzahlen_fuer`) - eine zweite Formel hier
    wuerde beim naechsten Umbau still auseinanderlaufen. `HIER` wird dabei
    mitgegeben, damit der Bericht auch in einem Testordner dieselbe Wahrheit
    liest wie seine uebrigen Zeilen.
    """
    zeilen = []
    for stufe in STUFEN:
        buecher = _stufenbuecher(stufe)
        if not buecher:
            continue
        alter = [spiegelstand.alter_minuten(z.get("letzter_lauf"))
                 for _, z in buecher]
        alter = [a for a in alter if a is not None]
        frisch = min(alter) if alter else None
        stueck = "Risikostufe %s: %d Spuren mit Buch" % (stufe, len(buecher))
        if frisch is not None:
            stueck += ", juengster Zyklus vor %.0f min" % frisch
        runden, ergebnis = _stufenzahlen(stufe)
        if runden:
            stueck += ", %d Runden, Summe %+.2f" % (runden, ergebnis)
        elif frisch is not None:
            stueck += ", noch keine geschlossene Runde"
        if frisch is None or frisch > 90:
            # Ein Buch, das nicht mehr waechst, ist kein laufender Lauf.
            zeilen.append("<b>%s - laeuft sie noch? "
                          "(dauerlauf.%s.log)</b>" % (stueck, stufe))
        else:
            zeilen.append(stueck)
    if not zeilen:
        return ""
    return "\n".join(zeilen) + ("\n  Details: auswertung_alle.py --risiko %s"
                                % STUFEN[0])


def _stufenzahlen(stufe):
    """(geschlossene Runden, Ergebnis) ueber alle auswertbaren Spuren."""
    runden, ergebnis = 0, 0.0
    try:
        import auswertung_alle                                # noqa: PLC0415
    except Exception:                                         # noqa: BLE001
        return 0, 0.0
    alt = auswertung_alle.HIER
    alt_stufe = auswertung_alle.STUFE
    auswertung_alle.HIER = Path(HIER)
    auswertung_alle.STUFE = stufe
    try:
        for spur in auswertung_alle.SPUREN:
            k = auswertung_alle.kennzahlen_fuer(spur)
            if k and k.get("n"):
                runden += k["n"]
                ergebnis += k["ergebnis"]
    except Exception:                                         # noqa: BLE001
        return runden, ergebnis
    finally:
        auswertung_alle.HIER = alt
        auswertung_alle.STUFE = alt_stufe
    return runden, ergebnis


def rang(e, diff):
    """Welchen Platz eine Spur im Bericht bekommt: 1, 2 oder 3.

    Die Rangfolge ordnet nach Dringlichkeit, nicht nach Interesse. Ein
    Bericht mit 24 gleichlangen Bloecken hat keinen Vorrang - man liest ihn
    einmal ganz und danach nie wieder.
    """
    w = e.get("wachen") or {}
    if (e.get("fehler") or e.get("stillgelegt")
            or diff.get("sperre_neu")
            or ("fehler" not in w
                and (w.get("herzschlag_frisch") is False or w.get("kill")))):
        return 1
    if (e.get("positionen") or diff.get("runden_mehr")
            or diff.get("position_neu") or diff.get("position_weg")):
        return 2
    return 3


def sammelzeile(stille):
    """Der stille Rest als eine Zeile: gezaehlt und benannt.

    Der Name einer Spur ist ihr `schluessel` - AUSSER er ist nicht eindeutig
    (die beiden Kraken-Nautilus-Arme teilen sich `nautilus_kraken`, sie
    erschienen deshalb zweimal als "nautilus_kraken" in einer Zeile, Befund
    21.09.2026). Dann steht der sprechende Name da.

    UND DIE BEDEUTUNG STEHT DAZUS (Befund Max, 22.09.2026: "Warum still und
    nicht papier?"). "Still" beschreibt den UNTERSCHIED zum letzten Bericht -
    kein Fehler, keine neue Runde, keine neue oder weggefallene Position -,
    NICHT den Modus: eine stille Spur laeuft weiter, im Papier wie eingestellt.
    Wer die Zeile ohne den Zusatz liest, haelt sie fuer abgeschaltet; genau das
    ist passiert.
    """
    if not stille:
        return ""
    schluessel = [e.get("schluessel") for e in stille if e.get("schluessel")]
    doppelt = {k for k in schluessel if schluessel.count(k) > 1}
    namen = []
    for e in stille:
        k = e.get("schluessel")
        namen.append(e["name"] if (not k or k in doppelt) else k)
    return ("%d Spuren still: %s  (still = kein Fehler und nichts Neues seit "
            "dem letzten Bericht - die Spuren laufen weiter)"
            % (len(stille), ", ".join(sorted(namen))))


NL = chr(10)          # Zeilenumbruch ohne Escape-Ketten im Quelltext

# Was im Journal ein HANDEL ist. Alles andere (zyklus, quotes, funding,
# rollover) ist Betriebsnotiz und darf das Alter einer stillen Spur nicht
# frisch aussehen lassen.
BUCHUNGEN = ("kauf", "verkauf", "eroeffnen", "schliessen", "einstieg",
             "ausstieg")
NOTIZEN = ("zyklus", "quotes", "funding", "rollover")


def _ist_buchung(zeile):
    """Ist diese Journalzeile ein Handel - oder nur Betriebsnotiz?

    Zwei Journal-Schemata im Haus: die meisten Spuren schreiben eine
    `aktion`-Spalte (kauf/verkauf/...). orbk und orb schreiben stattdessen
    `einstieg`/`ausgang` OHNE aktion-Spalte - dort war jede Zeile "keine
    Buchung", und die Spur sah aus, als haette sie nie gehandelt (8 echte
    Zeilen im orbk-Journal, Befund beim Einbau 21.09.2026). Quote-Sammler
    (`zyklus`, `quotes`, `funding`, `rollover`) bleiben in beiden Schemata
    NOTIZ und zaehlen nicht.
    """
    a = (zeile.get("aktion") or "").strip().lower()
    if a in BUCHUNGEN:
        return True
    if a:
        return False                      # bekannte Spalte, unbekannte Aktion
    if (zeile.get("grund") or "").strip().lower() in NOTIZEN:
        return False
    return any((zeile.get(f) or "").strip()
               for f in ("einstieg", "ausgang", "preis", "einsatz_usd",
                         "einsatz_eur", "menge"))


def letzte_buchung(journal):
    """Was das Journal einer Spur hergibt: (Tage seit letzter BUCHUNG,
    Buchungen, Tage seit der letzten Zeile, Zeilen).

    Unterschieden wird zwischen Buchung und Zeile, weil nicht jede Zeile ein
    Handel ist: die Nautilus-Arme schreiben im Takt `zyklus`-Zeilen mit
    Bid/Ask (Quote-Sammlung). Wer nur die letzte Zeile liest, haelt diese Spur
    fuer frisch beschaftigt, obwohl sie seit Wochen nicht handelt (Befund
    21.09.2026 beim Einbau der stillen Spuren).
    """
    p = Path(journal) if journal else None
    if not p or not p.is_file():
        return None, 0, None, 0
    letzte_b, n_b, letzte_z, n_z = None, 0, None, 0
    try:
        with p.open("r", newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                n_z += 1
                z = (r.get("zeit") or "").strip()
                if z and (letzte_z is None or z > letzte_z):
                    letzte_z = z
                if not _ist_buchung(r):
                    continue
                n_b += 1
                if z and (letzte_b is None or z > letzte_b):
                    letzte_b = z
    except OSError:
        return None, 0, None, 0
    return _alter_tage(letzte_b), n_b, _alter_tage(letzte_z), n_z


def _alter_tage(zeitstempel):
    if not zeitstempel:
        return None
    try:
        d = dt.datetime.fromisoformat(zeitstempel.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return max((dt.datetime.now(dt.timezone.utc) - d).days, 0)


def stillblock(stille):
    """Jede stille Spur einzeln: wie lange keine Buchung, und ob sie duerfte.

    Auftrag Max 21.09.2026: die stillen Spuren (Omniquant, iv_waelle, iv_wand,
    nautilus, nautilus_kraken, orbk, supertrend ...) gehoeren in den Bericht -
    eine Zeile mit acht Namen sagt nicht, welche davon seit einer Stunde und
    welche seit drei Wochen nichts tun.
    """
    if not stille:
        return ""
    ergebnis = []
    for e in sorted(stille, key=lambda x: x["name"].lower()):
        tage_b, n_b, _, n_z = letzte_buchung((e.get("roh") or {}).get("journal"))
        if tage_b is not None:
            alter = "letzte Buchung vor %d Tag(en)" % tage_b
        elif n_z == 0:
            alter = "kein Journal"
        elif n_b == 0:
            alter = "noch kein Handel (Journal traegt nur Kurse)"
        else:
            alter = "%d Buchung(en) ohne lesbares Datum" % n_b
        w = e.get("wachen") or (e.get("roh") or {}).get("w") or {}
        erlaubt = w.get("handel_erlaubt")
        name = e["name"]
        if len(name) > 29:
            name = name[:28].rstrip() + "…"
        ergebnis.append("  %-30s %s%s"
                        % (name, alter,
                           "" if erlaubt is None
                           else "  handel_erlaubt=%s" % str(erlaubt).lower()))
    return NL.join(ergebnis)



def _block(s, d):
    """Ein voller Block einer Spur. Text, sonst nichts.

    Parametername `s` (Spur-Lagebild aus lage.zu_lage()) und die lokale
    `lage_` (die Wachenlage darin) bleiben absichtlich wie im Vorgaenger:
    tests/test_stoerungen.py liest die Handelsrunden-Zeile per AST direkt aus
    dieser Datei und fuehrt sie mit genau diesen Namen aus.
    """
    if s["fehler"]:
        return "\n<b>%s</b>\n  AUSFALL: %s" % (s["name"], s["fehler"])

    if s.get("familie") is not None:
        # Die Kopie-Familie: ein Block, je Buch eine schlanke Zeile. Die
        # Positionen selbst bleiben (Snapshots, Summe), werden hier aber
        # nicht aufgezogen - wer Einzelpositionen will, schaut ins Buch.
        zeilen = ["\n<b>%s</b>" % s["name"]]
        for g in s.get("familie"):
            zeilen.append("  %-24s %3d offen | %s"
                          % (g["name"][:24], g["offen"], g["bilanz"]))
        if s.get("bilanz"):
            zeilen.append("  " + s["bilanz"])
        return "\n".join(zeilen)

    t = ["\n<b>%s</b>%s" % (s["name"],
                            "  — STILLGELEGT" if s["stillgelegt"] else "")]
    if s["positionen"]:
        summe = sum(p["wert"] for p in s["positionen"])
        mit = [p for p in s["positionen"] if p["vh"] is not None]
        schnitt = sum(p["vh"] for p in mit) / len(mit) if mit else None
        for p in s["positionen"]:
            t.append(zeile_position(p, s["waehrung"]))
        if schnitt is not None:
            t.append("  = %d Positionen, %.0f %s gebunden, im Schnitt %+.1f%%"
                     % (len(s["positionen"]), summe, s["waehrung"], schnitt))
    else:
        t.append("  keine offene Position")

    # Ein Buch ohne Bilanz ist eine halbe Auskunft. Spuren ohne
    # Auswertung tragen das Feld nicht - sie bleiben unveraendert.
    if s["bilanz"]:
        t.append("  " + s["bilanz"])

    lage_ = s["wachen"]
    if lage_ and "fehler" in lage_:
        t.append("  Wachen nicht lesbar: %s" % lage_["fehler"][:100])
    elif lage_:
        # Der Ruecklauf traegt die Waehrung im Namen - _usd bei Spur 1,
        # _eur bei Spur 3. Das ist Absicht (kraken/wachen.json: "Wer hier
        # USD liest, liest falsch") und darf hier nicht geraten werden.
        rueck = lage_.get("ruecklauf_%s" % s["waehrung"].lower())
        # Handelsrunden statt Buchungen: Zwangsschluesse sind keine
        # Handelsentscheidung. get() mit Rueckfall, weil ein Wachenmodul
        # ohne die Trennung dieselbe Zeile weiter bedienen soll.
        t.append("  Handelsrunden %d (Papier %d, %d Betriebsstoerung), "
                 "Ruecklauf %.2f %s, Faktor %.2f"
                 % (lage_.get("runden_echt", lage_["runden_gesamt"]),
                    lage_.get("runden_papier_echt", lage_["runden_papier"]),
                    lage_.get("runden_stoerung", 0),
                    rueck if rueck is not None else 0.0, s["waehrung"],
                    lage_["groessenfaktor"]))

    if s["stillgelegt"]:
        # Die Positionen stehen noch da - sie sind Papier und wurden nicht
        # fiktiv verkauft, das haette falsche Zahlen ins Journal geschrieben.
        # Sie bleiben sichtbar, damit klar ist, womit die Spur aufgehoert hat.
        t.append("  Kein Lauf mehr, weder Papier noch Live.")
    else:
        # sperren() lief schon in lage.erhebe() - inklusive des Papierpfad-
        # Zusatzes ganz vorn. Eine zweite Berechnung hier waere eine zweite
        # Wahrheit fuer dieselbe Frage.
        auf = s["sperren"]
        t.append("  Live: %s" % ("GESPERRT - " + "; ".join(auf) if auf
                                 else "offen"))

    z = rundenzeile(s)
    if z:
        t.append(z)

    teile = []
    if d.get("position_neu"):
        teile.append("neu: " + ", ".join(d["position_neu"]))
    if d.get("position_weg"):
        teile.append("geschlossen: " + ", ".join(d["position_weg"]))
    if d.get("sperre_neu"):
        teile.append("Sperre zu: " + "; ".join(d["sperre_neu"]))
    if d.get("sperre_weg"):
        teile.append("Sperre auf: " + "; ".join(d["sperre_weg"]))
    if d.get("runden_mehr"):
        teile.append("%+d Runden" % d["runden_mehr"])
    if teile:
        t.append("  seit gestern: " + " | ".join(teile))
    return "\n".join(t)


def rundenzeile(s):
    """Die Zeile '7 Tage: ...' einer Spur.

    Ein Zwangsschluss (Waechter) und eine Buchhaltungs-Korrektur sind KEINE
    Handelsentscheidung: `stoerungen.ist_stoerung` nimmt sie aus Rundenzahl
    und Quote. Sie werden hier ausdruecklich NEBEN die Quote gestellt - ohne
    den Zusatz liest sich "Treffer 100 %" wie ein fehlerfreier Automat,
    waehrend daneben weitere Ausstiege stehen (scanner 25.09.2026: 83 in der
    Quote, 18 daneben, zwei davon im Minus).
    """
    if s.get("buchlage") == "belastbar":
        k = s["kennzahlen"]
        z = ("  7 Tage: %d Runden, %+.2f %s, Treffer %d%%"
             % (k["n"], k["ergebnis"], s["waehrung"],
                round(100.0 * k["treffer"] / k["n"])))
        # BRUTTO ODER NETTO (T-192, 01.10.2026): Die Papierbuecher schreiben
        # ihre Zeilen OHNE Gebuehr - dann ist die Zahl kein Nettoergebnis und
        # darf nicht so gelesen werden. Steht die Gebuehr in der wachen.json,
        # wird die Nettosumme daneben gestellt (nicht stillschweigend
        # abgezogen: die Zeile soll zeigen, was der Satz ausmacht).
        if k.get("brutto"):
            einheit = k.get("einheit") or s["waehrung"]
            if k.get("gebuehr") and k.get("einsatz"):
                z += (" (brutto, netto nach %.2f %% je Seite %+.2f %s)"
                      % (100.0 * k["gebuehr"], k["netto"], einheit))
            elif k.get("einsatz"):
                z += " (brutto, Gebuehr unbekannt)"
        if k.get("n_stoerung"):
            z += (" | +%d Ausstiege ohne Handelsentscheidung (%+.2f %s,"
                  " nicht in der Quote)"
                  % (k["n_stoerung"], k["stoerung_ergebnis"], s["waehrung"]))
        return z
    if s.get("buchlage") == "zu_wenige_runden":
        return ("  7 Tage: zu wenige Runden (%d)"
                % ((s.get("kennzahlen") or {}).get("n", 0)))
    if s.get("schluessel"):
        seit = s.get("buch_seit")
        return "  kein Buch%s" % (" (seit %s)" % seit if seit else "")
    return None


def livezeile():
    """Eine Zeile: welche Spur kann ueberhaupt echtes Geld bewegen.

    WARUM: seit dem Auftrag vom 21.09.2026 steht `handel_erlaubt=true` in JEDER
    wachen.json - auch bei Spuren ohne einen einzigen Orderaufruf im Code. Der
    Bericht zeigte damit 29x "erlaubt" und verschwieg, dass nur eine Handvoll
    Spuren eine Boersenanbindung hat. Die Erkennung kommt aus DERSELBEN Quelle
    wie /live und spuren_stand.py (spuren_stand.sammle) - keine zweite Liste.

    haus = eigene Orderanbindung der Spur (echter Geldpfad).
    fremd = eine Fremd-Laufzeit ordert (Nautilus-Node, DEMO-Konto).
    Ein (F) hinter dem Namen heisst: Freigabefenster steht gerade offen.
    """
    try:
        import spuren_stand as ss  # noqa: PLC0415
        daten = ss.sammle()
    except Exception as fehler:  # noqa: BLE001
        return "Live-Anbindung: nicht geprueft (%s)" % str(fehler)[:80]
    haus, fremd = [], []
    for e in daten:
        if not e.get("order"):
            continue
        name = e["spur"]
        if str(e.get("fenster", "")).startswith("offen"):
            name += " (F)"
        (haus if e.get("art") == "haus" else fremd).append(name)
    if not haus and not fremd:
        return "Live-Anbindung: keine Spur hat einen Orderweg im Code."
    teile = []
    if haus:
        teile.append("haus: " + ", ".join(haus))
    if fremd:
        teile.append("fremd: " + ", ".join(fremd))
    ohne = len(daten) - len(haus) - len(fremd)
    return ("Live-Anbindung (%d von %d Spuren): %s; %d ohne Orderweg "
            "(handel_erlaubt dort wirkungslos)"
            % (len(haus) + len(fremd), len(daten), " | ".join(teile), ohne))


def guthaben_zeile():
    """scanner-Guthaben fuer den Bericht: Budget + verfuegbares Guthaben.

    Budget kommt aus `scanner/wachen.json` (`budget_usd`, Max 19.09.2026:
    80 USD total). Die WAEHRUNGEN kommen ebenfalls aus der Wachen
    (`universum.quotes`), nicht aus einer Liste im Skript: das Konto hatte
    438 USDC und 0,00 USDT, und die fest verdrahtete Liste
    ('USDT', 'USDC') meldete deshalb bis zur Umstellung am 02.10.2026
    "USDT 838.81" - ein aus `totalEq` geratener Gesamtkontostand, der wie ein
    Guthaben in einer Waehrung las, die es gar nicht gibt (T-311).

    Zwei Regeln dazu, beide gemessen:
    * KEIN Rueckfall auf `totalEq`. `totalEq` ist die Summe ueber ALLE
      Waehrungen in USD - als Ersatz fuer eine fehlende Waehrung nennt es
      eine Zahl, die es nicht gibt. Liefert die Boerse fuer eine abgefragte
      Waehrung kein `details`, ist das eine Waehrung OHNE Bestand: 0.00.
    * Jede Waehrung einzeln nennen, mit dem Hinweis, wenn sie ganz fehlt -
      dann ist "USDT fehlt" eine Aussage der Boerse und nicht ein
      Rundungsfehler im Bericht.

    Ein Guthaben-Ausfall darf den Bericht nie fallen lassen: 'nicht lesbar'.
    """
    budget = None
    quotes = []
    try:
        import json                                            # noqa: PLC0415
        with open(os.path.join(HIER, "scanner", "wachen.json"),
                  "r", encoding="utf-8") as f:
            wachen = json.load(f)
        budget = wachen.get("budget_usd")
        quotes = list((wachen.get("universum") or {}).get("quotes") or [])
    except Exception:                                          # noqa: BLE001
        budget = None
    if not quotes:
        quotes = ["USDC"]
    try:
        import okx                                             # noqa: PLC0415
        teile = []
        for ccy in quotes:
            try:
                d = okx._mit_wiederholung(
                    "/api/v5/account/balance?ccy=" + ccy, signiert=True)
            except Exception as e:                             # noqa: BLE001
                teile.append("%s n/A (%s)" % (ccy, str(e)[:40]))
                continue
            details = ((d or [{}])[0] or {}).get("details") or []
            verfuegbar = 0.0
            for e in details:
                try:
                    verfuegbar += float(e.get("availBal") or 0.0)
                except (TypeError, ValueError):
                    pass
            if not details:
                # Die Boerse fuehrt diese Waehrung nicht: 0.00, KEIN totalEq.
                teile.append("%s 0.00 (kein Bestand)" % ccy)
            else:
                teile.append("%s %.2f" % (ccy, verfuegbar))
    except Exception as e:                                      # noqa: BLE001
        return "Guthaben (scanner): nicht lesbar: %s" % str(e)[:80]
    budget_text = ("Budget $%s" % budget) if budget is not None else "Budget n/A"
    return "Guthaben (scanner): %s | verfuegbar %s" % (
        budget_text, "  ".join(teile))


def baue(mit_xperp=True, stufe_=None, xperp_daten=None):
    """Der ganze Bericht als Text. Kein Netz noetig fuer den Rahmen.

    Die Erhebung wohnt in lage.py und liest ihre Ordner ueber `lage.HIER`.
    Wer `tagesbericht.HIER` auf einen Datenordner umbiegt - die Tests tun
    genau das -, meint auch die Erhebung. Dieselbe Bindung wie bei
    `auswertung_alle.HIER` in `_stufenzahlen()`.

    `stufe_` waehlt die Risikostufe; None nimmt die dieses Prozesses. Gesetzt
    wird sie ueber `HANDEL_RISIKO` - derselbe Weg, den der Dauerlauf fuer seine
    Kindprozesse nimmt - und danach wieder zurueckgestellt: ein Bericht darf
    den aufrufenden Prozess nicht umstellen.
    """
    alt = lage.HIER
    lage.HIER = HIER
    alt_env = os.environ.get("HANDEL_RISIKO")
    if stufe_ is not None:
        os.environ["HANDEL_RISIKO"] = stufe_
    ist_basis = stufe_ in (None, risikostufe.STANDARD)
    try:
        return _baue(mit_xperp, stufen_titel=(None if ist_basis else stufe_),
                     mit_stufenzeile=ist_basis, xperp_daten=xperp_daten)
    finally:
        lage.HIER = alt
        if alt_env is None:
            os.environ.pop("HANDEL_RISIKO", None)
        else:
            os.environ["HANDEL_RISIKO"] = alt_env


def _baue(mit_xperp=True, stufen_titel=None, mit_stufenzeile=True,
          xperp_daten=None):
    heute = dt.datetime.now()
    kopf = "<b>Handel  %s</b>" % heute.strftime("%d.%m.%Y %H:%M")
    if stufen_titel:
        # Ein Bericht einer Stufe muss am Kopf sagen, welche - sonst liest man
        # die vierfachen Betraege fuer die Basis. FAKTOREN liefert den Faktor.
        kopf = "<b>Handel  %s · Risikostufe %s (Faktor %.0f)</b>" % (
            heute.strftime("%d.%m.%Y %H:%M"), stufen_titel,
            risikostufe.FAKTOREN.get(stufen_titel, 1.0))
    t = [kopf]

    # Der Schnappschuss entsteht hier nur im Speicher, fuer den Vergleich mit
    # gestern - geschrieben wird er an genau einer Stelle, im Dauerlauf nach
    # dem Bericht (Aufgabe 6). Ein zweiter Schreibort waere ein zweiter Ort
    # zum Scheitern.
    erhebung = lage.erhebe(mit_xperp=mit_xperp)
    stand = schnappschuss.baue(erhebung, heute=heute.date())
    gestern = schnappschuss.lade(heute.date() - dt.timedelta(days=1))
    diffs = schnappschuss.unterschiede(stand, gestern)
    if gestern is None:
        t.append("Kein Stand von gestern - der Vergleich faellt heute aus.")

    stille = []
    gesamt_offen = 0
    for e in erhebung:
        gesamt_offen += len(e["positionen"])
        d = diffs.get(e["schluessel"] or e["name"], {})
        if rang(e, d) == 3:
            stille.append(e)
            continue
        t.append(_block(e, d))

    zeile = sammelzeile(stille)
    if zeile:
        t.append("\n" + zeile)
        # Und dann JEDE stille Spur einzeln mit dem Alter ihrer letzten
        # Buchung (Auftrag Max 21.09.2026). Die Namenszeile allein laesst
        # nicht erkennen, welche Spur seit einer Stunde und welche seit drei
        # Wochen nichts tut - genau das ist der Unterschied zwischen "ruhig"
        # und "kaputt".
        detail = stillblock(stille)
        if detail:
            t.append(detail)

    if mit_xperp:
        try:
            # Die Rangliste ist eine MARKTgroesse - sie ist in jeder Stufe
            # dieselbe. Bei `--risiko alle` wird sie deshalb EINMAL geholt und
            # weitergereicht: dreimal scannen kostet das Dreifache an Zeit fuer
            # dieselbe Zeile.
            x = xperp_daten if xperp_daten is not None else spur_xperp()
            t.append("\n<b>%s</b>  (legt vor, handelt nicht)" % x["name"])
            if "fehler" in x["spitzen"]:
                t.append("  Rangliste nicht erreichbar: %s"
                         % x["spitzen"]["fehler"][:120])
            else:
                for zweck, titel in (("long", "Long"), ("short", "Short"),
                                     ("grid", "Grid")):
                    beste = x["spitzen"].get(zweck, [])
                    if not beste:
                        continue
                    teile = []
                    for b in beste:
                        kz = {"krypto": "K", "aktie": "A",
                              "rohstoff": "R"}[b["kategorie"]]
                        warn = "!" if (b["vola"] > b["tor"]
                                       or b["deckel"] < 5) else ""
                        teile.append("%s·%s %.0f%s" % (b["basis"], kz,
                                                       b["punkte"], warn))
                    t.append("  %-6s %s" % (titel, "  ".join(teile)))
                t.append("  K/A/R = Krypto/Aktie/Rohstoff, ! = Tor zu")
        except Exception as e:                           # noqa: BLE001
            t.append("\n<b>Rangliste XPERP</b>\n  AUSFALL: %s" % e)

    t.append("")
    t.append(spiegelzeile())
    t.append(livezeile())
    # In einem Stufenbericht ist die Stufenuebersicht doppelt - dort steht
    # stattdessen, aus welcher Datei die Zahlen kommen.
    stufe = stufenzeile() if mit_stufenzeile else buchzeile()
    if stufe:
        t.append(stufe)
    try:
        t.append(guthaben_zeile())
    except Exception:                                  # noqa: BLE001
        pass
    t.append("\n%d offene Position(en) insgesamt." % gesamt_offen)
    if not melder.bereit():
        t.append("Melder nicht eingerichtet: %s fehlt." % melder.fehlt())
    return "\n".join(t)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--senden", action="store_true",
                   help="zusaetzlich per Telegram schicken")
    p.add_argument("--ohne-xperp", action="store_true",
                   help="die Rangliste weglassen (schneller, kein Vollscan)")
    p.add_argument("--risiko", choices=list(STUFEN_ALLE) + ["alle"],
                   default=risikostufe.STANDARD,
                   help="Risikostufe des Berichts (%s) oder 'alle' fuer alle "
                        "drei untereinander; Vorgabe %s"
                        % (", ".join(STUFEN_ALLE), risikostufe.STANDARD))
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    stufen = STUFEN_ALLE if a.risiko == "alle" else (a.risiko,)
    # Die Rangliste EINMAL holen, wenn mehrere Stufen anstehen (sie ist eine
    # Marktgroesse, in jeder Stufe dieselbe). Ohne das kostet `--risiko alle`
    # drei volle Marktscans fuer dieselbe Zeile.
    vorrat = None
    if not a.ohne_xperp and len(stufen) > 1:
        try:
            vorrat = spur_xperp()
        except Exception:                                # noqa: BLE001
            vorrat = None        # _baue meldet den Fehler dann selbst je Stufe
    texte, fehler = [], 0
    for s in stufen:
        try:
            texte.append(baue(mit_xperp=not a.ohne_xperp, stufe_=s,
                              xperp_daten=vorrat))
        except Exception:                                # noqa: BLE001
            # Auch ein kaputter Bericht wird gemeldet. Stille ist die
            # schlechteste Meldung. Eine ausgefallene STUFE nimmt die uebrigen
            # nicht mit - bei 'alle' kommen die anderen trotzdem.
            fehler += 1
            texte.append(
                "<b>Handel - Risikostufe %s</b>\nDer Tagesbericht ist "
                "gescheitert:\n<pre>%s</pre>" % (s, traceback.format_exc()[-800:]))

    # Fuer die Konsole die HTML-Marken wieder heraus.
    print("\n\n".join(t.replace("<b>", "").replace("</b>", "")
                      for t in texte))

    if a.senden:
        # Je Stufe eine eigene Nachricht: drei Berichte zusammen sprengen die
        # Telegram-Grenze, und der Melder teilt dann mitten im Bericht.
        gesendet = sum(1 for t in texte if melder.sende(t))
        if gesendet == len(texte):
            print("\n-> per Telegram gesendet (%d Nachricht(en))" % gesendet)
        elif gesendet:
            print("\n-> nur %d von %d Nachrichten gesendet"
                  % (gesendet, len(texte)))
            return 1
        else:
            print("\n-> nicht gesendet: %s fehlt" % melder.fehlt())
            return 1
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
