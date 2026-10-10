"""Aus der Rangliste des Scans Vorschlaege bauen und - im Rahmen der Wachen -
ausfuehren.

Aufruf:
    python scanner\\handeln.py --vorschau          # nur zeigen, was er taete
    python scanner\\handeln.py --papier            # Papierhandel, Standard der Routine
    python scanner\\handeln.py --live              # echte Orders (siehe Sperren unten)

Diese Sperren muessen ALLE offen sein, sonst laeuft trotz --live nur Papier:
    1. wachen.json  handel_erlaubt == true
    2. OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE als Benutzervariablen
    3. --live ausdruecklich auf der Kommandozeile
    4. wachen.json  freigabe.erfuellt == true      (Handelsregeln, Bedingung 1)
    5. Herzschlag frisch                            (Bedingung 3)
    6. rollierender Erwartungswert nicht negativ    (Bedingung 5)
    7. eine Freigabe von Hand - am Bildschirm das Fenster (freigabe.py)
       oder im Dauerbetrieb das Zeitfenster (freigabefenster.py, /ja am
       Handy). Eine von beiden muss offen sein.
Fehlt eine, wird Papier gehandelt und es wird gesagt, welche Sperre zu war.

Punkt 3 der Handelsregeln laesst sich auf zwei Wegen erfuellen, und welcher
gilt, sagt die Lage:

  * **Sitzung am Bildschirm** - vor jedem Einstieg zeigt freigabe.py das
    Bestaetigungsfenster. Bedient es niemand, lehnt es nach
    FREIGABE_ZEITLIMIT_S von selbst ab. Zwei Bedingungen muessen dafuer
    zusammenpassen: eine geplante Aufgabe oder ein Dauerlauf darf dieses
    Fenster GAR NICHT erst erreichen (dauerlauf.py setzt MAXHIRN_ROUTINE=1,
    das schlaegt die isatty-Erkennung), und FREIGABE_ZEITLIMIT_S muss unter
    dem Abbruch-Zeitlimit des Aufrufers bleiben (dauerlauf.TIMEOUT_S) -
    sonst reisst der Abbruch den Lauf mit, und mit ihm die Spiegelung.
    Beides war am 21.09.2026 verletzt (Fenster 600 s, Abbruch 300 s).
  * **Kein Bildschirm, aber offenes Zeitfenster** - freigabefenster.py
    traegt die Freigabe: Max hat sie am Handy mit /ja erteilt, sie laeuft
    nach spaetestens 24 h ab und /stop schliesst sie sofort. Dann tritt
    das Zeitfenster an die Stelle des Fensters - sonst bliebe der
    Dauerbetrieb dauerhaft auf Papier (Befund 10.09.2026).

Kein Weg fuehrt am Bildschirm vorbei, ohne dass jemand geantwortet hat:
das Zeitfenster oeffnet sich nur auf eine Anfrage des Dauerlaufs hin, und
der fragt nur, wenn sonst nichts mehr fehlt. Ausstiege laufen nie durch
eine Freigabe: ein Stop muss auch dann greifen, wenn niemand davorsitzt.

Bedingungen 2-5 aus Wissen/Handelsregeln.md rechnet wachen_pruefung.py:
    2  Drawdown-Ratsche : Positionsgroesse x0.5 ab drawdown_halbierung_prozent,
       Notausstieg + Sperre ab kill_switch_gesamt_usd
    3  Herzschlag       : letzter_lauf zu alt -> alles zu, dann Papier
    4  Journal ausser Haus : nach jedem Zyklus nach journal_zweitziel kopiert
    5  Soll-Ist         : handeln.py --wachen (Wochenlauf) sperrt bei EV < 0

Jede Aktion landet in handelsjournal.csv. Der offene Bestand steht in
zustand.json. Beide werden nicht versioniert (Rauschen), aber gesichert.

Der Live-Pfad (okx.markt_kauf / markt_verkauf / stop_setzen) ist mangels
gueltiger Schluessel noch NICHT gegen echte Orders getestet. Vor dem ersten
scharfen Lauf mit einem einzigen Wert und Kleinstbetrag gegenpruefen.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, os.pardir, "Bus"))
import ereignis                                            # noqa: E402

import okx
import scan
# pos_kennung liegt im Handel-Ordner. Der eigene Spurenordner ist beim
# Start sys.path[0], darum wird der Ordner ANGEHAENGT (nicht vorne
# eingefuegt - ein Eintrag vorne koennte ein gleichnamiges Spurenmodul
# verdecken, siehe Handel/grid.py neben gitter/grid.py).
_handel_ordner = os.path.dirname(          # Handel/, nicht der Spurenordner
    os.path.dirname(os.path.abspath(__file__)))
if _handel_ordner not in sys.path:
    sys.path.append(_handel_ordner)
import pos_kennung
import tracking as _tracking
# signal_wechsel liegt ebenfalls im Handel-Ordner - darum NACH dem
# sys.path-Eintrag, nicht bei den uebrigen Standardimporten oben. Dort
# wuerde der Import mit ModuleNotFoundError abbrechen, weil der eigene
# Spurenordner beim Start sys.path[0] ist (dieselbe Falle wie pos_kennung).
from signal_wechsel import ERLAEUT, GESPERRT, zugelassen  # noqa: E402
import wachen_pruefung as wp
import boersenstops

HIER = Path(__file__).resolve().parent
# Risikostufe (HANDEL_RISIKO): Faktor auf die Betraege, Suffix auf Zustand
# und Journal. OHNE die Variable aendert sich nichts (Faktor 1.0, kein
# Suffix) - das ist die Bedingung, unter der diese Umstellung in laufenden
# Handelscode darf. Ueber den PFAD geladen wie ratschen.py: die Spur hat ihren
# eigenen Ordner als sys.path[0], ein 'import risikostufe' haenge an der
# Reihenfolge der Eintraege.
from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec
_rs_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "risikostufe.py")
_rs_spec_obj = _rs_spec("risikostufe", _rs_datei)
risikostufe = _rs_mod(_rs_spec_obj)
_rs_spec_obj.loader.exec_module(risikostufe)

# Freigabefenster ebenso ueber den PFAD laden: der eigene Ordner ist
# sys.path[0], der Handel-Ordner liegt dort NICHT (nur <spur>/../../Bus).
# Ein blankes 'import freigabefenster' scheiterte deshalb mit
# ModuleNotFoundError, zeitfenster_offen() fing das still ab und die Sperre
# meldete "kein Zeitfenster" - obwohl eines offen war (Befund 22.09.2026, der
# Scanner handelte Papier, waehrend der Dauerlauf --live anforderte).
_fw_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "freigabefenster.py")
_fw_spec_obj = _rs_spec("freigabefenster", _fw_datei)
freigabefenster = _rs_mod(_fw_spec_obj)
_fw_spec_obj.loader.exec_module(freigabefenster)

ZUSTAND = risikostufe.datei(HIER / "zustand.json")
JOURNAL = risikostufe.datei(HIER / "handelsjournal.csv")

# 0,05 % OKX Taker (Volumen < 10.000), gemessen 02.09.2026 - Handelsregeln.md
# nennt einen Papierlauf ohne Gebuehr einen Fehler. Identisch mit
# verbesserer/kosten.py (dort test_kosten_gleich.py). Bewusst nicht importiert:
# handeln.py bleibt ohne den Verbesserer lauffaehig.
GEBUEHR_PCT = 0.0005


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# Zustand atomar schreiben und laut lesen (atomar.py, 30.09.2026). Ueber den
# PFAD geladen wie risikostufe.py: die Spur hat ihren eigenen Ordner als
# sys.path[0]. Defekte Datei -> Sicherung .bak, sonst laute Ausnahme statt
# leerem Bestand.
from importlib.util import module_from_spec as _at_mod, \
    spec_from_file_location as _at_spec
_at_obj = _at_spec("atomar", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "atomar.py"))
atomar = _at_mod(_at_obj)
_at_obj.loader.exec_module(atomar)


def lade_zustand():
    z = atomar.lade_json(ZUSTAND, lambda: None)
    if z is not None:
        z.setdefault("letzte_ziele", {})   # Sperrfrist nach Ziel-Ausstieg
        return z
    return {"positionen": [], "letzte_stops": {}, "letzte_ziele": {},
            "letzter_lauf": None, "modus": None}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    atomar.schreibe_json(ZUSTAND, z)


def journal(*felder):
    neu = not JOURNAL.exists()
    # Der Kopf der DATEI entscheidet (T-095): ein Altjournal ohne `pos_id`
    # bekommt die Zeile ohne die neue Spalte - sonst wanderten alle Werte um
    # einen Platz nach links (siehe pos_kennung.zeile).
    kopf = None if neu else pos_kennung.kopf(JOURNAL)
    # felder enthaelt: zeit, modus, aktion, inst, preis, usd, stop, ziel,
    # grund, mfe_pct, mae_pct, haltetage, pos_id
    # wir fuegen herkunft als vorletzte Spalte ein (vor pos_id)
    felder_mit_herkunft = list(felder)
    if len(felder_mit_herkunft) >= 13:
        felder_mit_herkunft.insert(-1, HERKUNFT)
    else:
        felder_mit_herkunft.append(HERKUNFT)
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        if neu:
            s.writerow(["zeit", "modus", "aktion", "inst", "preis", "usd",
                        "stop", "ziel", "grund", "mfe_pct", "mae_pct",
                        "haltetage",
                        "herkunft",
                        # Die Kennung der Position (T-095) - letzte Spalte,
                        # damit die alten Zeilen lesbar bleiben.
                        "pos_id"])
        s.writerow(pos_kennung.zeile(felder_mit_herkunft, kopf))


# --- Vorschlaege ---------------------------------------------------------------

def stop_prozent(z, w):
    """Stop-Abstand: aus Volatilitaet und Drawdown, hart gedeckelt."""
    vola = z["kennzahlen"]["volatilitaet_pa"]
    roh = 3.0 + 6.0 * min(vola, 1.5)          # ~5 % ruhig, ~12 % wild
    return max(w["pflicht_stop_prozent_min"],
               min(w["pflicht_stop_prozent_max"], round(roh, 1)))


ABLEHNUNGEN = risikostufe.datei(HIER / "ablehnungen.csv")

# Diese Gruende zaehlen ZYKLEN, nicht Kandidaten - sie gehoeren nicht in die
# Kandidatensumme, sonst geht die Kontrollzeile nicht auf.
KAPAZITAET = ("Buch voll", "Gesamtdeckel erreicht", "nicht mehr erreicht",
              "bewertet", "kaufbar", "bewertete Maerkte")

# Eigene Datei, NIE ins Journal: dessen Leser (auswertung_alle.py,
# buchauswertung.py) zaehlen jede Zeile als Runde. Eine Ablehnung dort waere
# eine erfundene Runde und wuerde die Bilanz der einzigen Geld-Spur faelschen.
SPALTEN_ABLEHNUNG = ["zeit", "art", "grund", "anzahl", "inst", "score",
                     "vola", "cr"]

# Wird in der Vorschau abgeschaltet - eine Vorschau, die schreibt, ist keine
# Vorschau. Ein Schalter an EINER Stelle statt eines if je Aufrufer.
SCHREIBEN = True

# Herkunft der Buchung: "zyklus" (Standard, 15-Minuten-Dauerlauf) oder
# "trigger" (WebSocket-Trigger bei Kerzenschluss). Wird vom Trigger gesetzt.
HERKUNFT = "zyklus"


def journal_ablehnung(**felder):
    """Eine Zeile ins Ablehnungsprotokoll."""
    if not SCHREIBEN:
        return
    neu = not ABLEHNUNGEN.exists()
    with ABLEHNUNGEN.open("a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=SPALTEN_ABLEHNUNG,
                           extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in SPALTEN_ABLEHNUNG})


def protokolliere(grund, anzahl=1, **zahlen):
    """Die Lage EINES Zyklus als Zahl, ohne Kennung.

    Der Ort fuer die Massenfaelle: seit dem 14.09.2026 sieht der Scan den
    ganzen Spotmarkt, mehrere hundert Kandidaten je Lauf. Die einzeln mit
    Kennung zu protokollieren waere ein Protokoll, das niemand liest.

    `zahlen` nimmt Messwerte auf (`betrag=`, `noetig=`). Sie sind KEINE Spalten
    des Protokolls - sie wandern in den Grundtext, damit sie im CSV lesbar
    bleiben. Grund: ein Aufrufer, der sie als Keyword uebergibt, bekam
    `TypeError: protokolliere() got an unexpected keyword argument 'betrag'`
    und RISS DEN GANZEN ZYKLUS ab (17x am 02.10.2026 zwischen 02:23 und 06:26,
    gemessen im Ereignisprotokoll). Die Regel: eine Hilfsfunktion nimmt die
    Felder an, die ihre Aufrufer brauchen - oder der Aufrufer darf sie nicht
    uebergeben. Eine halbe Erweiterung (nur `anzahl`) ist die schlimmere
    Variante, weil sie erst zur Laufzeit auffaellt.
    """
    text = grund
    for k, v in zahlen.items():
        text += " %s=%s" % (k, v)
    if anzahl or zahlen:
        journal_ablehnung(zeit=_jetzt(), art="zyklus", grund=text,
                          anzahl=anzahl)


def _schon_protokolliert(inst, grund):
    """Sperre gegen Doppelzaehlung, je (Instrument, Grund) und TAG.

    Derselbe Markt steht Tag fuer Tag im Bericht und wird alle 15 Minuten
    erneut abgelehnt - ohne Sperre zaehlte ein einziger gehaltener Wert 96
    Ablehnungen am Tag und das Protokoll saehe aus wie ein Tor, das nie
    aufgeht. Der Tag ist die richtige Koernung, weil die Rangliste taeglich
    neu entsteht: eine Ablehnung am selben Tag ist dieselbe Lage, eine am
    naechsten eine neue.
    """
    if not ABLEHNUNGEN.exists():
        return False
    heute = _heute()
    with ABLEHNUNGEN.open(newline="", encoding="utf-8") as f:
        for zeile in csv.DictReader(f):
            if (zeile.get("art") == "kandidat"
                    and zeile.get("inst") == inst
                    and zeile.get("grund") == grund
                    and (zeile.get("zeit") or "")[:10] == heute):
                return True
    return False


def protokolliere_kandidat(inst, grund, **felder):
    """Ein einzelner Kandidat, der bis zur teuren Pruefung kam."""
    if not SCHREIBEN or _schon_protokolliert(inst, grund):
        return
    journal_ablehnung(zeit=_jetzt(), art="kandidat", grund=grund, anzahl=1,
                      inst=inst, **felder)


def lies_ablehnungen(pfad=None):
    """Der Leser: was hat die Tore nicht passiert, und warum.

    Die Kontrollzeile ist der Kern. kaufbar (= was die Bewertungstore
    passiert hat) muss sich vollstaendig aufteilen in "bewertet" (im
    Einstiegspfad angesehen) und "nicht mehr erreicht" (der Zyklus brach
    vorher ab, weil das Buch voll war). Geht sie nicht auf, ist die
    Zaehlung falsch - nicht die Kontrollzeile.

    Kapazitaets-Ereignisse stehen bewusst DARUNTER und nicht in der Summe:
    sie zaehlen Zyklen, nicht Kandidaten. Genau ihre Trennung ist der
    Zweck des Protokolls - "Tor zu" und "Buch voll" sehen im Journal
    identisch aus.
    """
    p = pfad or ABLEHNUNGEN
    zeilen = []
    if not os.path.exists(p):
        return ["Noch kein Ablehnungsprotokoll: %s" % p]
    with open(p, newline="", encoding="utf-8") as f:
        daten = list(csv.DictReader(f))
    if not daten:
        return ["Ablehnungsprotokoll ist leer."]

    def summe(art, grund=None):
        n = 0
        for d in daten:
            if d.get("art") != art:
                continue
            if grund is not None and d.get("grund") != grund:
                continue
            try:
                n += int(d.get("anzahl") or 0)
            except ValueError:
                pass
        return n

    gruende = {}
    for d in daten:
        if d.get("art") in ("zyklus", "kandidat"):
            g = d.get("grund") or "?"
            if g in KAPAZITAET:
                continue
            try:
                gruende[g] = gruende.get(g, 0) + int(d.get("anzahl") or 0)
            except ValueError:
                pass

    zeilen.append("=== Ablehnungen scanner ===")
    zeilen.append("%-34s %7s" % ("Grund", "Anzahl"))
    for g, n in sorted(gruende.items(), key=lambda x: -x[1]):
        zeilen.append("%-34s %7d" % (g, n))

    kaufbar = summe("zyklus", "kaufbar")
    bewertet = summe("zyklus", "bewertet")
    nicht_erreicht = summe("zyklus", "nicht mehr erreicht")
    zeilen.append("")
    zeilen.append("Kontrolle: kaufbar %d = bewertet %d + nicht mehr erreicht %d"
                  % (kaufbar, bewertet, nicht_erreicht))
    if kaufbar != bewertet + nicht_erreicht:
        zeilen.append("ACHTUNG: die Zaehlung geht nicht auf (Differenz %d). "
                      "Ein Kandidat steht in zwei Zaehlern oder in keinem."
                      % (kaufbar - bewertet - nicht_erreicht))

    zeilen.append("")
    zeilen.append("Kapazitaet (ZYKLEN, nicht Kandidaten - nicht in der Summe):")
    for g in KAPAZITAET:
        n = summe("zyklus", g)
        if n:
            zeilen.append("  %-32s %5d" % (g, n))
    return zeilen


def nominal_fuer(stop_pct, w):
    """Der Einsatz einer Position - aus dem RISIKO, nicht aus einer festen Zahl.

    Vorher band jede Position denselben Betrag (max_pro_trade_usd), waehrend
    ihr Stop zwischen 5 und 12 Prozent schwankte: gemessen am 15.09.2026
    riskierten die 18 Vorschlaege eines Zyklus zwischen 5,20 und 8,70 USD -
    Faktor 1,7 bei gleichem gebundenem Kapital. Wer mehr riskiert, sollte
    nicht denselben Platz belegen wie der, der weniger riskiert.

    Neu faellt das Nominal aus dem Stop-Abstand:
        nominal = risiko_je_position_usd / (stop_pct / 100)
    Bei 6 USD Risiko sind das 115 USD bei 5,2 Prozent Stop und 69 USD bei
    8,7 Prozent. Das Verlustpotenzial je Position ist damit gleich, das
    Kapital wandert dorthin, wo es weniger riskiert - und weil weite Stops
    weniger binden, passen mehr Positionen unter denselben Gesamtdeckel.

    max_pro_trade_usd bleibt die Obergrenze: das Sizing darf eine Position
    nicht groesser machen als die Hausregel erlaubt, auch wenn der Stop sehr
    eng ist. Ein Stop nahe null gaebe sonst eine unbegrenzte Position.

    ALTBESTAND-RUECKFALL: fehlt risiko_je_position_usd in wachen.json (oder
    steht auf null), bleibt es beim alten festen Nominal. So aendert sich fuer
    eine Spur, die den Wert nicht kennt, gar nichts.
    """
    deckel = w["max_pro_trade_usd"]
    risiko = w.get("risiko_je_position_usd")
    if not risiko or stop_pct <= 0:
        return deckel
    return round(min(deckel, risiko / (stop_pct / 100.0)), 2)


def marktkurs(inst):
    """Jetzt-Kurs fuer den Einstieg - die EINE Stelle, die das Netz ruft.

    Anlass (03.10.2026): vorschlaege() nahm den Einstieg aus dem
    Vortagesbericht. Der Bericht 2026-09-17 trug AVAX-USDT mit 7,531,
    der Markt am 19.09. lag bei 8,53-8,78 - der Einstieg 12 % unter
    Markt, das Ziel beim Kauf schon erfuellt, 82 Scheinrunden an einem
    Tag (+1866 %). Siehe vorschlaege().

    Zwei Regeln, beide aus dem Befund:

    1. KEIN Rueckfall auf einen aelteren Preis. Ein alter Preis als
       Einstieg IST der Fehler; ihn wieder zuzulassen haette ihn nur
       unsichtbar gemacht.
    2. Ein Fehler ist eine Ablehnung, keine Ausnahme. Ein Markt, der
       nicht antwortet, darf nicht den ganzen Zyklus abbrechen - die
       uebrigen Kandidaten bleiben kaufbar.

    Die Funktion ist der Testnaht: die Tests biegen sie um, statt das
    Netz zu fassen (so test_ablehnungen es mit jedem anderen Modulpfad
    auch tut).
    """
    try:
        k = okx.letzter_kurs(inst)
    except Exception as e:  # noqa: BLE001
        print("  Kurs %s nicht abrufbar: %s" % (inst, e), file=sys.stderr)
        return None
    if not k or k <= 0:
        return None
    return k


def vorschlaege(bericht, w):
    """Die Kandidaten, die alle Bewertungstore passiert haben.

    Die Zaehlung haengt an DIESER Pruefung, nicht an einer zweiten Fassung
    derselben Bedingung: zwei Fassungen einer Grenze waeren zwei Wahrheiten.
    Jeder Kandidat faellt in GENAU EINEN Zaehler - geprueft wird in fester
    Reihenfolge, der erste greifende Grund gewinnt.
    """
    aus = []
    lage = {}
    for z in bericht["werte"]:
        vola = z["kennzahlen"]["volatilitaet_pa"]
        grund = None
        if z["score"] < w["mindest_score"]:
            grund = "Score unter %g" % w["mindest_score"]
        elif vola > w["max_volatilitaet_pa"]:
            grund = "Vola ueber %g" % w["max_volatilitaet_pa"]
        elif z["verhaeltnis"] < w["mindest_chance_risiko"]:
            grund = "Chance/Risiko unter %g" % w["mindest_chance_risiko"]
        if grund:
            lage[grund] = lage.get(grund, 0) + 1
            continue
        # Einstieg ist der JETZT-KURS, nicht der Bewertungspreis des
        # Vortagesberichts. Gemessen 03.10.2026: der Bericht 2026-09-17
        # (Score 64,7) trug AVAX-USDT mit 7,531, der Markt am 19.09. lag
        # bei 8,53-8,78. Der Einstieg lag 12 % UNTER dem Markt, das Ziel
        # (Einstieg + 2x Stop) war damit schon beim Kauf erfuellt, und der
        # naechste Zyklus verkaufte mit 15 % Gewinn - 82mal am 19.09.,
        # Summe +1866 %. Das war keine Signalstaerke, sondern ein Rechen-
        # fehler: 97 von 105 Ziel-Ausstiegen kamen nach 0,25 h.
        # Kein Rueckfall auf den Berichtspreis: ein veralteter Preis als
        # Einstieg IST der Fehler. Ohne Kurs gibt es keine Position.
        einstieg = marktkurs(z["inst"])
        if einstieg is None:
            lage["Kurs nicht abrufbar"] = lage.get("Kurs nicht abrufbar", 0) + 1
            continue
        sp = stop_prozent(z, w)
        stop = round(einstieg * (1 - sp / 100.0), 6)
        ziel = round(einstieg + 2.0 * (einstieg - stop), 6)   # Chance/Risiko 2:1
        aus.append({"inst": z["inst"], "score": z["score"], "einstieg": einstieg,
                    "stop": stop, "stop_pct": sp, "ziel": ziel,
                    "usd": nominal_fuer(sp, w)})
    protokolliere("bewertete Maerkte", len(bericht["werte"]))
    for grund, n in sorted(lage.items()):
        protokolliere(grund, n)
    protokolliere("kaufbar", len(aus))
    return aus


# --- Ausstieg / Einstieg ---------------------------------------------------

def in_abklingzeit(inst, z, w):
    d = z["letzte_stops"].get(inst)
    if not d:
        return False
    tage = (date.fromisoformat(_heute()) - date.fromisoformat(d)).days
    return tage < w["abklingzeit_tage"]


def in_zielsperre(inst, z, w):
    """War dieses Instrument gerade erst im Ziel - laeuft die Sperrfrist noch?

    Anlass 23.09.2026 (Auftrag Max "Sperrfrist 2h"): ZEC wurde live im Ziel
    verkauft (1618.36) und acht Sekunden spaeter zum fast selben Kurs neu
    gekauft (1619.38). Die Runde kostet 1,2 % Gebuehren, ohne dass sich am Markt
    etwas geaendert haette - der Kandidat stand weiter auf der Rangliste, weil
    das Signal nicht verschwunden war, sondern gerade ERFUELLT wurde.

    Ein Ziel-Ausstieg heisst: der geplante Gewinn ist da. Sofort wieder
    einzusteigen ist kein neues Signal, sondern dieselbe Bewegung noch einmal
    bezahlt. Nach einem STOP gilt die laengere Abklingzeit (Tage) - ein
    gescheiterter Versuch ist ein anderer Grund als ein gelungener.

    Die Frist steht als Zahl in der wachen (sperrfrist_nach_ziel_stunden,
    Standard 0 = aus).
    """
    stunden = float(w.get("sperrfrist_nach_ziel_stunden", 0) or 0)
    if stunden <= 0:
        return False
    t = (z.get("letzte_ziele") or {}).get(inst)
    if not t:
        return False
    try:
        zu = datetime.fromisoformat(t)
    except (TypeError, ValueError):
        return False
    if zu.tzinfo is None:
        zu = zu.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - zu).total_seconds() < stunden * 3600


def _boersenstop_gefuellt(p):
    """Hat der Notausstieg beim Handelsplatz schon verkauft?

    Dann ist die Position am Markt weg, auch wenn sie hier noch im Buch steht.
    Der Stoppreis ist der Ausloeser, nicht die Fuellung - gerechnet wird
    trotzdem damit, weil es der einzige bekannte Preis ist.
    """
    if not p.get("stop_ord_id"):
        return False
    try:
        d = okx.stop_details(p["stop_ord_id"])
    except Exception as e:  # noqa: BLE001
        print("  Stop-Zustand %s nicht lesbar: %s" % (p["stop_ord_id"], e),
              file=sys.stderr)
        return False
    return float(d.get("accFillSz") or 0) > 0


def _live_verkauf(p, z):
    """Live verkaufen: erst den Notausstieg abbestellen, dann Market verkaufen.

    Gibt "ok", "boerse" (der Boersen-Stop war schneller) oder "fehler".
    Ein nicht stornierbarer Stop ist KEIN Grund, den Verkauf zu unterlassen -
    genau das liess Positionen im Buch stehen, die am Markt laengst verkauft
    waren. Bleibt er offen, wird er in zustand.json gemerkt und beim naechsten
    Live-Lauf erneut storniert.
    """
    if p.get("stop_ord_id"):
        try:
            okx.stop_stornieren(p["stop_ord_id"], p.get("inst"))
        except Exception as e:  # noqa: BLE001
            print("  Stop %s nicht stornierbar: %s" % (p["stop_ord_id"], e),
                  file=sys.stderr)
            if _boersenstop_gefuellt(p):
                print("  der Boersen-Stop hat ausgeloest - Position ist weg")
                return "boerse"
            _merke_offenen_stop(z, p.get("inst"), p["stop_ord_id"])
    kauf_id = p.get("kauf_ord_id")
    if not kauf_id:
        # Ohne Handelsplatz-Order gibt es dort nichts zu verkaufen. Ein
        # Market-Verkauf wuerde nicht "nichts" verkaufen, sondern den GESAMTEN
        # Bestand dieses Werts auf dem Konto - auch Coins, die diese Spur nie
        # gekauft hat. Am 21.09.2026 lief genau das in "OKX 51000: Parameter
        # ordId error": order_details fragte mit ordId=None an (urlencode macht
        # daraus den Text "None"), die Position kam aus dem Papierlauf und
        # hatte keine Order. Solche Altlasten bucht bueche_papier_altlasten_aus
        # aus; kommt eine trotzdem hier an, wird nicht verkauft.
        print("  %s steht ohne OKX-Order im Buch - kein Verkauf moeglich"
              % p["inst"], file=sys.stderr)
        return "fehler"
    try:
        d = okx.order_details(p["inst"], kauf_id)
        menge = float(d.get("accFillSz") or 0) or p["usd"] / p["einstieg"]
    except Exception as e:  # noqa: BLE001
        print("  Menge fuer %s nicht lesbar: %s" % (p["inst"], e),
              file=sys.stderr)
        _schutz_zurueck(p)
        return "fehler"
    try:
        okx.markt_verkauf(p["inst"], round(menge, 8))
    except Exception as e:  # noqa: BLE001
        print("  Verkauf %s fehlgeschlagen: %s" % (p["inst"], e),
              file=sys.stderr)
        _schutz_zurueck(p, menge)
        return "fehler"
    return "ok"


def _schutz_zurueck(p, menge=None):
    """Nach einem fehlgeschlagenen Verkauf den Notausstieg wieder anlegen.

    Der Verkauf bestellt ZUERST den Stop ab - sonst blockiert er den Bestand,
    und OKX lehnt den Verkauf ab. Scheitert der Verkauf DANACH, steht die
    Position ohne Notausstieg an der Boerse, bis der naechste Zyklus es erneut
    versucht. Genau das passierte am 22./23.09.2026: weil der Prozess ohne
    OKX_BASE lief und gegen www.okx.com signierte (OKX 50119), scheiterte JEDER
    Verkaufsversuch, und ZEC stand die Nacht ueber bei +19 % ohne Stop.

    Ein alter Stop, dessen Storno scheiterte, bleibt unberuehrt (er schuetzt
    schon). Ohne Stop-Preis wird nur gemeldet, nie geraten.
    """
    if p.get("stop_ord_id") or not p.get("stop"):
        return False
    if menge is None:
        try:
            d = okx.order_details(p["inst"], p.get("kauf_ord_id"))
            menge = float(d.get("accFillSz") or 0) or p["usd"] / p["einstieg"]
        except Exception as e:  # noqa: BLE001
            print("  Schutz fuer %s nicht wiederherstellbar (Menge unbekannt): %s"
                  % (p["inst"], e), file=sys.stderr)
            return False
    try:
        algo = okx.stop_setzen(p["inst"], round(menge, 8), p["stop"])
        p["stop_ord_id"] = algo
        print("  Schutz wieder angelegt: %s Stop %.6f (algoId %s)"
              % (p["inst"], p["stop"], algo), file=sys.stderr)
        return True
    except Exception as e:  # noqa: BLE001
        print("  Schutz liess sich NICHT wieder anlegen (%s): %s"
              % (p["inst"], e), file=sys.stderr)
        return False


def _merke_offenen_stop(z, inst, stop_ord_id):
    """Einen nicht stornierbaren Stop EINMAL merken.

    Ohne die Pruefung wuchs die Liste bei jedem weiteren Ausstiegsversuch: am
    23.09.2026 standen 23 Kopien DESSELBEN Stop in ``zustand.json``, weil der
    Storno an einem OKX-Fehler scheiterte und jeder Zyklus ihn erneut merkte.
    """
    offen = z.setdefault("offene_stops", [])
    for e in offen:
        if e.get("stop_ord_id") == stop_ord_id:
            return False                # steht schon drin - nicht doppelt
    offen.append({"inst": inst, "stop_ord_id": stop_ord_id, "seit": _heute()})
    return True


def raeume_offene_stops(z):
    """Stops abarbeiten, die beim Ausstieg nicht stornierbar waren.

    Sie stehen weiter beim Handelsplatz im Buch. Beim naechsten Live-Lauf wird
    es erneut versucht; erst wenn einer wirklich weg ist, faellt der Eintrag.
    Ohne das koennte ein alter Stop eine spaetere Position desselben
    Instruments zum alten Stoppreis verkaufen.

    Zwei Altlasten werden hier mit aufgeraeumt:
      * doppelte Eintraege (derselbe Stop mehrfach gemerkt), und
      * das fehlende ``inst`` alter Eintraege - OKX verlangt beim Storno die
        instId (50014 ``Parameter instId can not be empty``), deshalb wird sie
        lesend nachgeholt (``okx.stop_inst``).
    """
    offen = z.get("offene_stops") or []
    eindeutig, gesehen = [], set()
    for e in offen:
        sid = e.get("stop_ord_id")
        if sid and sid not in gesehen:
            gesehen.add(sid)
            eindeutig.append(e)
    rest = []
    for e in eindeutig:
        try:
            inst = e.get("inst") or okx.stop_inst(e["stop_ord_id"])
            weg = okx.stop_stornieren(e["stop_ord_id"], inst)
            if not e.get("inst") and inst:
                e["inst"] = inst
            print("  offener Stop %s %s"
                  % (e["stop_ord_id"],
                     "storniert" if weg else "war schon weg (gefuellt/abgelaufen)"))
        except Exception as ex:  # noqa: BLE001
            if not _boersenstop_gefuellt(e):
                rest.append(e)
                print("  offener Stop %s bleibt liegen: %s"
                      % (e["stop_ord_id"], ex), file=sys.stderr)
    if len(rest) != len(offen):
        z["offene_stops"] = rest


def _haltetage(p):
    """Kalendertage seit dem Einstieg (UTC-Datum, wie _heute()).

    Leerer String, wenn das Feld fehlt - Altbestand aus der Zeit vor dieser
    Spalte wird nicht geraten.
    """
    try:
        return (date.fromisoformat(_heute())
                - date.fromisoformat(p["eroeffnet"])).days
    except (KeyError, TypeError, ValueError):
        return ""


def _merke_extrem(p, kurs):
    """Buchgewinn/-verlust fortschreiben (MFE/MAE in Prozent des Einstiegs).

    Gemessen wird an den Zykluspunkten - die echten Extreme zwischen zwei
    Laeufen liegen weiter aussen, die Zahl ist also eine UNTERGRENZE. Sie ist
    trotzdem das einzige Mittel, um spaeter zu trennen, ob ein Stop zu eng war
    (die Position lief erst ins Plus und drehte dann) oder ob das Signal falsch
    war (sie lief sofort gegen den Einstieg).

    Die Spur ist long-only, deshalb kein Richtungsfaktor. Altbestand ohne die
    Felder faellt ueber .get() auf 0.0 zurueck und wird ab dem naechsten
    Zyklus mitgemessen - rueckwirkend rekonstruiert wird nichts.
    """
    bewegung = (kurs - p["einstieg"]) / p["einstieg"] * 100.0
    p["mfe_pct"] = max(p.get("mfe_pct", 0.0), bewegung)
    p["mae_pct"] = min(p.get("mae_pct", 0.0), bewegung)


def bueche_papier_altlasten_aus(z):
    """Positionen OHNE echte OKX-Order aus dem Live-Buch buchen.

    Anlass (21.09.2026, gemessen): Das Buch ist EINES fuer Papier und Live.
    Laeuft die Spur mit geschlossenem Freigabefenster im Papier, fuellt sie
    dasselbe Buch; wird das Fenster geoeffnet, stehen diese Positionen im
    Live-Buch. Ihnen fehlt die kauf_ord_id, am Handelsplatz gibt es also
    nichts zu verkaufen - sie blockieren nur Plaetze, und jeder
    Ausstiegsversuch laeuft in denselben Fehler. Am 20.09.2026 von Hand
    bereinigt (buchbereinigung.py), am 21.09. um 02:06 wieder vier Altlasten
    im Buch, weil der Papier-Zyklus um 23:48 dasselbe Buch gefuellt hatte.
    Darum jetzt bei JEDEM Live-Lauf: ausbuchen als Papier-Verkauf mit Grund
    "buchbereinigung", echte Order-Traeger bleiben liegen. Idempotent.
    """
    altlasten = [p for p in z["positionen"] if not p.get("kauf_ord_id")]
    if not altlasten:
        return 0
    behalten = []
    for p in z["positionen"]:
        if p.get("kauf_ord_id"):
            behalten.append(p)
            continue
        try:
            kurs = okx.letzter_kurs(p["inst"])
        except Exception as e:                                     # noqa: BLE001
            print("  Buchbereinigung %s: kein Kurs (%s) - bleibt liegen"
                  % (p["inst"], e))
            behalten.append(p)
            continue
        if not kurs:
            print("  Buchbereinigung %s: kein Kurs - bleibt liegen" % p["inst"])
            behalten.append(p)
            continue
        erloes = p["usd"] * (kurs / p["einstieg"])
        gv = erloes - p["usd"]
        print("  Buchbereinigung: %s (ohne Order) @ %.6f  G/V %+.2f USD"
              % (p["inst"], kurs, gv))
        journal(_jetzt(), "papier", "verkauf", p["inst"], "%.6f" % kurs,
                "%.2f" % erloes, "", "", "buchbereinigung",
                "%.4f" % p.get("mfe_pct", 0.0),
                "%.4f" % p.get("mae_pct", 0.0), _haltetage(p),
                p.get("pos_id", ""))
    z["positionen"] = behalten
    return len(altlasten)


def ist_live_position(p):
    """Eine ECHTE Position am Handelsplatz - erkennbar an der Kauf-Order.

    Das Buch ist EINES fuer Papier und Live. Ein Papierzyklus (Fenster zu) darf
    eine live gekaufte Position deshalb NICHT im Buch schliessen: an der Boerse
    bliebe sie offen, der Stop wuerde spaeter ohne Buchzeile ausloesen, und die
    Spur haette Margin belegt, ohne es zu wissen (genau so entstand am 21.09.2026
    die HBAR-Karteileiche in xperp; dasselbe Muster traf mosaic am 23.09.).
    """
    return bool(p.get("kauf_ord_id"))


def pruefe_ausstiege(z, live):
    if live:
        raeume_offene_stops(z)
    behalten = []
    for p in z["positionen"]:
        if not live and ist_live_position(p):
            # Der Papierlauf hat hier nichts zu schliessen - nur zu melden.
            print("  %s bleibt stehen: echte Position (kauf_ord_id), wird nur "
                  "vom Live-Lauf geschlossen" % p["inst"])
            behalten.append(p)
            continue
        kurs = okx.letzter_kurs(p["inst"])
        _merke_extrem(p, kurs)
        grund = None
        if kurs <= p["stop"]:
            grund = "stop"
        elif kurs >= p["ziel"]:
            grund = "ziel"
        if not grund:
            behalten.append(p)
            continue
        # Nur die journalisierte Zeile traegt die Gebuehr; p["usd"] bleibt
        # nominal fuer Deckel- und G/V-Rechnung.
        erloes = p["usd"] * kurs / p["einstieg"] * (1 - GEBUEHR_PCT)
        gv = erloes - p["usd"]
        if live:
            ergebnis = _live_verkauf(p, z)
            if ergebnis == "fehler":
                behalten.append(p)
                continue
            if ergebnis == "boerse":
                # Verkauft hat der Stop am Handelsplatz, nicht wir.
                grund = "stop (boerse)"
                kurs = p["stop"]
                erloes = p["usd"] * kurs / p["einstieg"] * (1 - GEBUEHR_PCT)
                gv = erloes - p["usd"]
        print("  AUSSTIEG (%s): %s @ %.6f  G/V %+.2f USD"
              % (grund, p["inst"], kurs, gv))
        journal(_jetzt(), "live" if live else "papier", "verkauf", p["inst"],
                "%.6f" % kurs, "%.2f" % erloes, "", "", grund,
                "%.4f" % p.get("mfe_pct", 0.0),
                "%.4f" % p.get("mae_pct", 0.0), _haltetage(p),
                p.get("pos_id", ""))
        _tracking.track_zyklus_abgeschlossen(
            spur_name="scanner",
            instrument=p["inst"],
            richtung="long",
            einstieg_kurs=p["einstieg"],
            ausstieg_kurs=kurs,
            ergebnis_pct=round((kurs - p["einstieg"]) / p["einstieg"] * 100, 4),
            ergebnis_eur=round(gv, 2),
            haltedauer_stunden=float(_haltetage(p) or 0) * 24,
            ausstiegsgrund=grund.split(" ")[0],
            is_paper=not live,
            risikostufe=risikostufe.stufe(),
        )
        if grund.startswith("stop"):
            z["letzte_stops"][p["inst"]] = _heute()
        elif grund == "ziel":
            # Sperrfrist nach Ziel-Ausstieg (Auftrag Max 23.09.2026): sonst
            # kauft der naechste Zyklus dasselbe Instrument sofort wieder.
            z.setdefault("letzte_ziele", {})[p["inst"]] = _jetzt()
    z["positionen"] = behalten


def flach_stellen(z, live, grund):
    """Alle offenen Positionen sofort schliessen - Notausstieg fuer Bedingung 2
    (Kill-Switch) und Bedingung 3 (Herzschlag alt). Im Papierlauf zum aktuellen
    Kurs verbucht, live per Market-Verkauf. Ein fehlgeschlagener Live-Verkauf
    laesst die Position stehen und wird gemeldet."""
    behalten = []
    for p in z["positionen"]:
        if not live and ist_live_position(p):
            print("  %s bleibt stehen: echte Position (kauf_ord_id) - ein "
                  "Papierlauf stellt sie nicht flach" % p["inst"])
            behalten.append(p)
            continue
        kurs = okx.letzter_kurs(p["inst"])
        _merke_extrem(p, kurs)
        # Wie in pruefe_ausstiege: Gebuehr nur in der journalisierten Zeile.
        erloes = p["usd"] * kurs / p["einstieg"] * (1 - GEBUEHR_PCT)
        if live:
            ergebnis = _live_verkauf(p, z)
            if ergebnis == "fehler":
                behalten.append(p)
                continue
        print("  AUSSTIEG (%s): %s @ %.6f  G/V %+.2f USD"
              % (grund, p["inst"], kurs, erloes - p["usd"]))
        journal(_jetzt(), "live" if live else "papier", "verkauf", p["inst"],
                "%.6f" % kurs, "%.2f" % erloes, "", "", grund,
                "%.4f" % p.get("mfe_pct", 0.0),
                "%.4f" % p.get("mae_pct", 0.0), _haltetage(p),
                p.get("pos_id", ""))
    z["positionen"] = behalten


def pruefe_einstiege(z, vs, w, live, faktor=1.0):
    gehalten = {p["inst"] for p in z["positionen"]}
    eingesetzt = sum(p["usd"] for p in z["positionen"])
    if faktor != 1.0:
        print("  (Drawdown-Ratsche aktiv: Positionsgroesse x %.2f)" % faktor)
    # Freies Kontoguthaben je Basiswaehrung - EINmal je Zyklus, nicht je
    # Kandidat. Ohne dieses Tor pruefte nur der Deckel: der am 02.10.2026 bei
    # 442 von 444 USDC gebundenen Konto (4 offene Positionen, Rest in Stops)
    # und 1,76 USDC frei sieht jeden Kandidaten als kaufbar, bis die Boerse
    # jeden einzelnen mit "insufficient balance" zurueckweist. Die Waehrung
    # kommt aus dem Instrument, nicht aus einer festen Konstante - sonst
    # entsteht genau der Fehler, den diese Zeile verhindert.
    frei = {}
    # Schwelle aus der Wachen, 0 = aus (alte Regel: nur der Deckel begrenzt).
    # VOR dem if, weil die Pruefung weiter unten auch im Papierlauf durchlaeuft:
    # ein NameError, den nur der Papierpfad sieht, waere dort unauffindbar.
    minq = float(w.get("min_guthaben_quote") or 0.0)
    if live:
        for inst in {v["inst"] for v in vs}:
            q = okx.quote(inst)
            if q and q not in frei:
                try:
                    frei[q] = okx.guthaben(q)
                except Exception as e:  # noqa: BLE001
                    print("  Guthaben %s nicht lesbar: %s" % (q, e),
                          file=sys.stderr)
                    frei[q] = 0.0
        for q in sorted(frei):
            print("  Guthaben %s: %.2f frei%s" % (
                q, frei[q], "" if minq <= 0 else " (Tor ab %.2f)" % minq))
    bewertet = 0
    deckel_gemeldet = False
    gemeldet_guthaben = set()
    for i, v in enumerate(vs):
        if len(z["positionen"]) >= w["max_offene_positionen"]:
            # KEIN Tor, sondern Kapazitaet: der Rest der Liste war kaufbar
            # und wurde nur nicht mehr angesehen. Beides getrennt zaehlen -
            # sonst liest sich ein volles Buch wie ein zu strenges Tor.
            protokolliere("Buch voll")
            protokolliere("nicht mehr erreicht", len(vs) - i)
            break
        # Signal-Wechsel-Gatter (03.10.2026, Auftrag Max "Erweitern"). Es
        # steht VOR `okx.markt_kauf` - ein Gatter hinter dem Kauf waere bei
        # Live genau einen Zyklus zu spaet, die Order waere schon draussen.
        if zugelassen(z, w, v["inst"], "long") is not ERLAEUT:
            protokolliere_kandidat(v["inst"], GESPERRT, score=v.get("score"))
            continue
        bewertet += 1
        usd = round(v["usd"] * faktor, 2)
        if eingesetzt + usd > w["max_gesamt_usd"]:
            # Kapazitaet, kein Tor - und EIN Ereignis je Zyklus, nicht eines
            # je Kandidat: bei vollem Deckel faellt jeder der 18 Vorschlaege
            # hier durch, und 18 Zeilen laesen sich wie 18 verschiedene
            # Ablehnungen statt wie ein einziger voller Einsatz.
            if not deckel_gemeldet:
                protokolliere("Gesamtdeckel erreicht")
                deckel_gemeldet = True
            continue
        if live and minq > 0:
            q = okx.quote(v["inst"])
            if frei.get(q, 0.0) < max(usd, minq):
                # Kapazitaet wie der Deckel, aber je WAEHRUNG: bei gemischten
                # Paaren ist das freie USDC kein Guthaben fuer einen EUR-Kauf.
                # Ein Ereignis je Waehrung und Zyklus, damit ein volles Konto
                # nicht 18 Zeilen in die Ablehnungen schreibt.
                if q not in gemeldet_guthaben:
                    protokolliere("zu wenig %s frei" % q,
                                  betrag=round(frei.get(q, 0.0), 2),
                                  noetig=usd)
                    gemeldet_guthaben.add(q)
                continue
        if v["inst"] in gehalten:
            protokolliere_kandidat(v["inst"], "schon im Buch",
                                   score=v.get("score"))
            continue
        if in_abklingzeit(v["inst"], z, w):
            protokolliere_kandidat(v["inst"], "Abklingzeit nach Stop",
                                   score=v.get("score"))
            continue
        if in_zielsperre(v["inst"], z, w):
            protokolliere_kandidat(v["inst"], "Sperrfrist nach Ziel-Ausstieg",
                                   score=v.get("score"))
            continue
        kauf_id = stop_id = None
        stop_fehlt = False
        if live:
            try:
                kauf_id = okx.markt_kauf(v["inst"], usd)
                d = okx.order_details(v["inst"], kauf_id)
                menge = float(d.get("accFillSz") or 0)
            except Exception as e:  # noqa: BLE001
                print("  Kauf %s fehlgeschlagen: %s" % (v["inst"], e),
                      file=sys.stderr)
                continue
            if menge <= 0:
                print("  Kauf %s ohne Fuellung - kein Eintrag" % v["inst"],
                      file=sys.stderr)
                continue
            try:
                stop_id = okx.stop_setzen(v["inst"], round(menge, 8), v["stop"])
            except Exception as e:  # noqa: BLE001
                # Der Kauf steht, der Notausstieg nicht. Dann lieber gar nicht
                # halten als unbewacht: zurueckverkaufen. Klappt auch das
                # nicht, wird die Position wenigstens gebucht und als
                # unbewacht gekennzeichnet - eine Position, die am Markt liegt
                # und im Buch fehlt, ist der schlimmere Zustand.
                print("  Stop fuer %s fehlgeschlagen: %s" % (v["inst"], e),
                      file=sys.stderr)
                try:
                    okx.markt_verkauf(v["inst"], round(menge, 8))
                    print("  zurueckverkauft - kein Eintrag")
                    continue
                except Exception as e2:  # noqa: BLE001
                    print("  Rueckverkauf ebenfalls fehlgeschlagen: %s" % e2,
                          file=sys.stderr)
                    stop_fehlt = True
        _pos = {
            "inst": v["inst"], "einstieg": v["einstieg"], "usd": usd,
            "stop": v["stop"], "ziel": v["ziel"], "eroeffnet": _heute(),
            "kauf_ord_id": kauf_id, "stop_ord_id": stop_id,
            "boersen_stop_fehlt": stop_fehlt,
            "mfe_pct": 0.0, "mae_pct": 0.0,
            # Die Kennung dieser Position (T-095): sie entsteht beim
            # Einstieg und steht in JEDER Zeile dieser Position.
            "pos_id": pos_kennung.neu(_jetzt()),
        }
        z["positionen"].append(_pos)
        eingesetzt += usd
        gehalten.add(v["inst"])
        print("  AUF %-10s @ %.6f  Stop %.6f (-%.1f%%)  Ziel %.6f  %.2f USD"
              % (v["inst"], v["einstieg"], v["stop"], v["stop_pct"],
                 v["ziel"], usd))
        journal(_jetzt(), "live" if live else "papier", "kauf", v["inst"],
                "%.6f" % v["einstieg"], "%.2f" % (usd * (1 + GEBUEHR_PCT)),
                "%.6f" % v["stop"], "%.6f" % v["ziel"],
                "score %.1f" % v["score"], "", "", "",
                _pos["pos_id"])
        _tracking.track_position_eroeffnet(
            spur_name="scanner",
            instrument=v["inst"],
            richtung="long",
            einstieg_kurs=v["einstieg"],
            stop_kurs=v["stop"],
            ziel_kurs=v["ziel"],
            nominal_eur=usd,
            is_paper=not live,
            risikostufe=risikostufe.stufe(),
        )
    protokolliere("bewertet", bewertet)


# --- Freigabe von Hand (Handelsregeln Punkt 3) -------------------------------

# Sekunden ohne Bedienung, nach denen das Freigabefenster von selbst ablehnt.
# Das ist der tragende Schutz fuer den Bildschirmweg - aber nur, solange der
# Aufrufer laenger wartet als dieses Limit: dauerlauf.TIMEOUT_S (700) > hier
# (600) > vorher 120. Die Umkehr dieses Verhaeltnisses hat am 21.09.2026
# jeden scanner-Zyklus abgebrochen.
FREIGABE_ZEITLIMIT_S = 600


def sitzung_da():
    """Sitzt jemand davor, der das Freigabefenster bedienen kann?

    Nur eine erste Huerde, keine Garantie: isatty() ist unter Windows nicht
    verlaesslich - in der Git-Bash meldet es auch dann ein Terminal, wenn
    stdin umgeleitet wurde (gemessen 02.09.2026). Verlassen wird sich
    deshalb auf FREIGABE_ZEITLIMIT_S, nicht auf diese Funktion.

    MAXHIRN_ROUTINE=1 setzt der Wrapper einer geplanten Aufgabe. Das ist die
    ausdrueckliche Ansage "hier sitzt niemand" und schlaegt alles andere."""
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


# Spur, unter der diese Datei im Dauerlauf und in freigabefenster.py steht.
SPUR = "scanner"


def zeitfenster_offen():
    """Hat Max am Handy freigegeben (freigabefenster.py)?

    Gelesen wird das Modul aus dem Handel-Ordner (oben ueber den PFAD geladen).
    Ein Lesefehler gilt als *nicht* freigegeben - im Zweifel keine Order. Er
    wird aber GEMELDET: dieselbe Zeile stand am 22.09.2026 fuer ein offenes
    Fenster im Chat, und die Ursache war nur im stderr zu sehen."""
    try:
        return bool(freigabefenster.lade(SPUR).offen())
    except Exception as e:                                   # noqa: BLE001
        print("  Zeitfenster nicht lesbar (%s: %s) - gilt als zu."
              % (type(e).__name__, e), file=sys.stderr)
        return False


def sperren_live(w, s):
    """Alles, was --live gerade verschliesst. Leere Liste = frei."""
    g = []
    if not risikostufe.live_erlaubt():
        # Eine Risikostufe geht NIE live (siehe risikostufe.live_erlaubt): ihre
        # groesseren Betraege sind zum Messen da, und ihr Buch ist getrennt -
        # live gehandeltes Geld stuende in keiner Auswertung. Der Grund traegt
        # bewusst NICHT das Wort Freigabefenster: sonst haelt der Dauerlauf ihn
        # fuer eine Fenster-Bitte und fragt nach einer Freigabe, die es in
        # einer Stufe gar nicht geben darf.
        g.append("Risikostufe %s: kein Live-Pfad in einer Stufe"
                   % risikostufe.stufe())
    if not w.get("handel_erlaubt"):
        g.append("wachen.json handel_erlaubt=false")
    if not okx.schluessel_vorhanden():
        g.append("OKX-Schluessel nicht gesetzt")
    if not s["freigabe_erfuellt"]:
        g.append("freigabe.erfuellt=false (Bedingung 1)")
    if not s["herzschlag_frisch"]:
        g.append("Herzschlag alt (Bedingung 3)")
    if s["ev_negativ"]:
        g.append("rollierender EV %.3f USD < 0 (Bedingung 5)"
                 % s["rollierender_ev"])
    # Punkt 3 der Handelsregeln, in zwei Fassungen: am Bildschirm das
    # Freigabefenster, im Dauerbetrieb das Zeitfenster. Eine muss offen
    # sein. Die Begruendung nennt immer das Freigabefenster, weil
    # dauerlauf.nur_fenster_fehlt genau darauf prueft, ob allein die
    # Freigabe noch fehlt - und nur dann fragt er am Handy nach.
    if not sitzung_da() and not zeitfenster_offen():
        g.append("Freigabefenster nicht offen - keine Sitzung am "
                 "Bildschirm und kein Zeitfenster (Handelsregeln Punkt 3)")
    return g


def freigabe_protokoll(vs, z, s):
    """Haelt fest, dass das Zeitfenster die Freigabe war.

    Der Bildschirmweg hat sein Protokoll in freigabe.py. Ohne diese Zeilen
    waere im Journal nicht zu sehen, welche Einstiege ohne Fenster
    freigegeben wurden. Best effort wie dort: ein Schreibfehler darf den
    Einstieg nicht verhindern."""
    try:
        sys.path.insert(0, str(HIER.parent))
        import freigabe
        for v in vs:
            freigabe.audit({
                "spur": SPUR, "ergebnis": "bestaetigt",
                "quelle": "zeitfenster", "modus": "live",
                "waehrung": "USD", "inst": v.get("inst"),
                "einstieg": v.get("einstieg"), "stop": v.get("stop"),
                "ziel": v.get("ziel"), "stop_pct": v.get("stop_pct"),
                "gebunden": v.get("usd"),
                "gebunden_gesamt": sum(p["usd"] for p in z["positionen"]),
                "offene_positionen": len(z["positionen"]),
                "ruecklauf_usd": s.get("ruecklauf_usd")})
    except Exception:                                   # noqa: BLE001
        pass


def hole_freigabe(vs, z, s):
    """Jeden Vorschlag im Fenster bestaetigen lassen. Gibt die bestaetigten
    zurueck - abgelehnt heisst leere Liste, und leer heisst kein Einstieg.

    Faellt das Fenster aus (Tk fehlt, Anzeige weg), wird nicht gehandelt.
    Ein Fehler beim Bestaetigen darf nie zu einem ungefragten Kauf werden."""
    sys.path.insert(0, str(HIER.parent))
    try:
        import freigabe
    except Exception as e:  # noqa: BLE001
        print("  Freigabefenster nicht verfuegbar (%s) - kein Einstieg." % e,
              file=sys.stderr)
        return []
    # Betraege in der Waehrung der Spur - hier USD, bei Spur 3 EUR. Die
    # Schluessel sind deshalb waehrungsneutral.
    bestand = {
        "gebunden": sum(p["usd"] for p in z["positionen"]),
        "offene_positionen": len(z["positionen"]),
        "verlust_gesamt": s["ruecklauf_usd"],
    }
    try:
        return freigabe.bestaetige(vs, "spot", bestand,
                                   zeitlimit=FREIGABE_ZEITLIMIT_S)
    except Exception as e:  # noqa: BLE001
        print("  Freigabe abgebrochen (%s) - kein Einstieg." % e,
              file=sys.stderr)
        return []


# --- Wachen-Status (Bedingungen 2-5) ----------------------------------------

def _spiegeln(w):
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND, ABLEHNUNGEN], ziel)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))


def zeige_wachen(w):
    """handeln.py --wachen: alle fuenf Bedingungen als Momentaufnahme, dazu die
    beiden Automatik-Reaktionen des Wochenlaufs - Bedingung 4 (spiegeln) und
    Bedingung 5 (bei negativem Erwartungswert die Sperre schliessen)."""
    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)
    print("=== Wachen-Status  %s ===" % _jetzt())
    # Die Rundenzahl fuer Bedingung 1 zaehlt Handelsrunden, nicht Buchungen:
    # ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung. Die Kurve
    # (Ruecklauf unten) bleibt ungefiltert - sie ist gebucht.
    print("  1 Freigabe erfuellt      %s   (Handelsrunden %d, davon Papier %d, "
          "dazu %d Betriebsstoerung(en), seit %s)"
          % (s["freigabe_erfuellt"], s["runden_echt"], s["runden_papier_echt"],
             s["runden_stoerung"], s["erste_runde"] or "-"))
    print("  2 Ruecklauf              %.2f USD von Hoechststand %.2f  -> Faktor %.2f%s"
          % (s["ruecklauf_usd"], s["hoechststand_usd"], s["groessenfaktor"],
             "   >>> KILL-SWITCH" if s["kill"] else ""))
    _schwelle = s.get("halbierungsschwelle_usd")
    print("    Halbierung ab          %s%s"
          % ("%.2f USD" % _schwelle if _schwelle is not None else "?",
             "" if s.get("halbierung_im_gewinn", True)
             else "   >>> greift erst nach Verlust ueber den Nullpunkt"))
    print("  3 Herzschlag frisch     %s   (%s min alt, Grenze %d)"
          % (s["herzschlag_frisch"],
             "?" if s["herzschlag_alter_min"] is None
             else "%.0f" % s["herzschlag_alter_min"],
             w.get("herzschlag_max_minuten", 30)))
    print("  4 Journal-Zweitziel     %s" % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  5 Rollierender EV       %s%s"
          % ("n/a (zu wenig Runden)" if s["rollierender_ev"] is None
             else "%+.3f USD/Runde" % s["rollierender_ev"],
             "   >>> NEGATIV" if s["ev_negativ"] else ""))
    print()
    _spiegeln(w)
    if s["kill"] and wp.sperre_zu("Bedingung 2 (Wochenlauf): Ruecklauf %.2f USD >= Kill-Switch"
                                  % s["ruecklauf_usd"]):
        print("  -> Bedingung 2: handel_erlaubt auf false gesetzt.")
    if s["ev_negativ"] and wp.sperre_zu("Bedingung 5 (Wochenlauf): rollierender EV %.3f USD < 0"
                                        % s["rollierender_ev"]):
        print("  -> Bedingung 5: handel_erlaubt auf false gesetzt.")


# --- Hauptlauf ---------------------------------------------------------------

def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Eine Vorschau, die schreibt, ist keine Vorschau. Der Schalter steht an
    # EINER Stelle statt als if je Aufrufer - vorschlaege() laeuft auch in
    # der Vorschau und wuerde sonst jeden Zyklus mitzaehlen.
    global SCHREIBEN
    SCHREIBEN = modus != "vorschau"

    w = scan.wachen()

    # Bedingung 4 an der ERSTEN Stelle des Zyklus: die Dateien dieses Ordners
    # auf den Stand des letzten Zyklus nach Q: bringen - VOR jedem return.
    # Vorher stand die Spiegelung nur am ENDE, deshalb fehlten die fruehen
    # Ausgaenge (--wachen, "Kein Bericht", und der abgebrochene Lauf, der die
    # Zeitgrenze reisst: gemessen am 21.09.2026 Q: 21:23 gegen lokal 21:40).
    # Ein Zyklus, der nie fertig wird, zieht jetzt trotzdem nach, was der
    # vorige geschrieben hat.
    if w.get("journal_zweitziel"):
        _spiegeln(w)

    if modus == "wachen":
        zeige_wachen(w)
        return

    bpfad = scan.BERICHTE / "neuester.json"
    if not bpfad.exists():
        print("Kein Bericht. Erst scan.py laufen lassen.")
        return
    bericht = json.loads(bpfad.read_text("utf-8"))

    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)

    # Live-Sperren pruefen - die sechs alten plus die Freigabe von Hand
    # (Punkt 3): am Bildschirm oder als Zeitfenster.
    live = False
    if modus == "live":
        gruende = sperren_live(w, s)
        if gruende:
            print("--live angefordert, aber gesperrt: " + "; ".join(gruende))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    vs = vorschlaege(bericht, w)
    print("=== Handeln (%s) | Bericht %s | %d Vorschlaege ==="
          % ("LIVE" if live else "Papier", bericht["datum"], len(vs)))

    z["modus"] = "live" if live else "papier"

    # Erst aufraeumen, dann handeln: ein Live-Lauf uebernimmt kein Papierbuch.
    if live and SCHREIBEN:
        n_alt = bueche_papier_altlasten_aus(z)
        if n_alt:
            print("  %d Papier-Altlast(en) aus dem Live-Buch gebucht" % n_alt)

    # Buch gegen BOERSE, vor jeder Handelsentscheidung: hat jede Live-Position
    # ihren Notausstieg noch - und ist sie ueberhaupt noch da? Am 26.09.2026
    # standen vier Live-Positionen ohne Stop (die Stops waren an der Boerse
    # storniert worden) und eine am 24.09. vom eigenen Stop verkaufte Position
    # stand als Geist im Buch. Das Buch kann das nicht wissen: es prueft nur
    # den eigenen Kurs gegen den eigenen Stop. Also fragt der Zyklus die
    # Boerse. Faellt die Abfrage aus, bleibt das Buch unangetastet.
    if live and SCHREIBEN:
        try:
            _bs = boersenstops.pruefe(z, okx, anwenden=True, journal=journal)
            if _bs["nachgesetzt"] or _bs["ausgebucht"] or _bs["waisen"]:
                print("  Boersen-Abgleich: %d Stop(s) nachgesetzt, %d Position(en) "
                      "nach Boersenstand ausgebucht, %d Waisenstop(s)"
                      % (_bs["nachgesetzt"], _bs["ausgebucht"], _bs["waisen"]))
            if _bs["unklar"] or _bs["fehlt_weiter"]:
                print("  Boersen-Abgleich: %d unklar, %d ohne wirksamen Stop - "
                      "bitte nachsehen" % (_bs["unklar"], _bs["fehlt_weiter"]))
        except Exception as e:                                 # noqa: BLE001
            print("  Boersen-Abgleich nicht moeglich (%s) - Buch unveraendert" % e)

    if modus == "vorschau":
        for v in vs:
            print("  %-10s Score %.1f  Einstieg %.6f  Stop %.6f (-%.1f%%)  Ziel %.6f"
                  % (v["inst"], v["score"], v["einstieg"], v["stop"],
                     v["stop_pct"], v["ziel"]))
        eing = sum(p["usd"] for p in z["positionen"])
        print("\nOffener Bestand: %d Positionen, %d USD gebunden"
              % (len(z["positionen"]), eing))
        # Auch hier die Sperren nennen, nicht nur unter --live:
        # dauerlauf.nur_fenster_fehlt liest genau diese Zeile, um zu
        # entscheiden, ob sich eine Freigabe-Anfrage ueberhaupt lohnt.
        # Ohne sie wurde nie gefragt - und ein /ja blieb folgenlos.
        # IMMER drucken, auch ohne Sperre - dann mit "nichts". Vorher stand
        # die Zeile nur unter `if g:`, und genau dann, wenn eine Spur start-
        # klar war, fehlte sie: dauerlauf.nur_fenster_fehlt las None und
        # fragte nie nach einem Fenster (T-313).
        g = sperren_live(w, s)
        print("Live waere gesperrt durch: " + ("; ".join(g) or "nichts"))
        # Bedingung 4 gilt AUCH hier: die Vorschau ist der haeufigste Aufruf
        # (der Dauerlauf fragt jede Spur damit ab), und wenn NUR sie laeuft,
        # weil der echte Zyklus in die Zeitgrenze laeuft, muss Q: trotzdem
        # nachgezogen werden.
        if w.get("journal_zweitziel"):
            _spiegeln(w)
        return

    # Bedingung 2 - Kill-Switch: alles zu, Sperre zu, Schluss.
    if s["kill"]:
        print("- KILL-SWITCH: Ruecklauf %.2f USD >= %g -> Notausstieg + Sperre -"
              % (s["ruecklauf_usd"], w["kill_switch_gesamt_usd"]))
        flach_stellen(z, live, "kill_switch")
        if wp.sperre_zu("kill_switch: Ruecklauf %.2f USD" % s["ruecklauf_usd"]):
            print("  wachen.json handel_erlaubt -> false")
        schreibe_zustand(z)
        # Bedingung 4 gilt auch hier: gerade der Notausstieg gehoert ausser
        # Haus (Muster: der Herzschlag-Zweig direkt darunter).
        if w.get("journal_zweitziel"):
            _spiegeln(w)
        return

    # Bedingung 3 - Herzschlag alt: alles zu, dieser Lauf handelt nicht mehr.
    # Der naechste Lauf mit frischem Herzschlag faengt normal wieder an.
    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel dieser Lauf -"
              % ("?" if s["herzschlag_alter_min"] is None
                 else "%.0f" % s["herzschlag_alter_min"],
                 w.get("herzschlag_max_minuten", 30)))
        flach_stellen(z, live, "herzschlag_alt")
        z["modus"] = "papier"
        schreibe_zustand(z)
        if w.get("journal_zweitziel"):
            _spiegeln(w)
        return

    # Ausstiege laufen nie durch das Fenster: ein Stop muss greifen, auch
    # wenn niemand davorsitzt.
    print("- Ausstiege -")
    pruefe_ausstiege(z, live)

    print("- Einstiege -")
    faktor = s["groessenfaktor"]
    if live and vs:
        # Punkt 3 der Handelsregeln: scharf geschaltet wird von Hand. Der
        # Faktor der Drawdown-Ratsche wird vorher eingerechnet, damit im
        # Fenster die Zahl steht, die auch gekauft wird.
        vs = [dict(v, usd=round(v["usd"] * faktor, 2), cr=2.0) for v in vs]
        faktor = 1.0
        if sitzung_da():
            # Am Bildschirm: das Fenster fragt je Einstieg einzeln.
            vs = hole_freigabe(vs, z, s)
            if not vs:
                print("  Freigabe abgelehnt - kein Einstieg in diesem Lauf.")
        else:
            # Kein Bildschirm, aber ein offenes Zeitfenster. Es wurde beim
            # Sperrenpruefen geprueft; hier noch einmal, weil dazwischen
            # Netzabfragen liegen und /stop in der Zeit greifen kann.
            if zeitfenster_offen():
                try:
                    stand = freigabefenster.lade(SPUR).text()
                except Exception:                       # noqa: BLE001
                    stand = "offen"
                print("  Freigabe ueber das Zeitfenster (%s) - %d Einstieg(e) "
                      "ohne Fenster am Bildschirm." % (stand, len(vs)))
                freigabe_protokoll(vs, z, s)
            else:
                print("  Zeitfenster ist inzwischen zu - kein Einstieg.")
                vs = []
    pruefe_einstiege(z, vs, w, live, faktor)

    eing = sum(p["usd"] for p in z["positionen"])
    print("\nStand: %d/%d Positionen, %d/%d USD gebunden"
          % (len(z["positionen"]), w["max_offene_positionen"],
             eing, w["max_gesamt_usd"]))
    schreibe_zustand(z)

    # Bedingung 4 - Journal nach jedem Zyklus ausser Haus.
    if w.get("journal_zweitziel"):
        _spiegeln(w)


def main():
    with ereignis.lauf("handel/scanner"):
        return _main()


def _main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau", help="nur zeigen")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier", help="Papierhandel (Standard)")
    g.add_argument("--live", action="store_const", dest="modus",
                   const="live", help="echte Orders, wenn alle Sperren offen")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen", help="Bedingungen 2-5 zeigen und durchsetzen "
                                        "(Wochenlauf)")
    p.add_argument("--ablehnungen", action="store_true",
                   help="das Ablehnungsprotokoll auswerten, nichts handeln")
    a = p.parse_args()
    if a.ablehnungen:
        for zeile in lies_ablehnungen():
            print(zeile)
        return
    lauf(a.modus or "papier")


if __name__ == "__main__":
    main()
