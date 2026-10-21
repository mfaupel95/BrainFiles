"""Spiegelstand der Handelsspuren (Bedingung 4) - lesend, ohne Netz.

Ein `journal_zweitziel` in wachen.json ist eine Absicht: kopiert wird erst im
Zyklus. Dieses Modul vergleicht je Spur die Originale mit den Kopien
BYTE-GENAU (wie `cmp`) und liest daneben den Vermerk aus zustand.json
(`journal_zweitziel_ok` / `_info`) sowie das Alter des Herzschlags.

Zwei Verbraucher, eine Rechnung:

  * `tagesbericht.py` - eine Zeile im Abendbericht (Funktion `kurz()`).
  * Systempruefung, Block 11 - Aufruf als Skript, Tabelle + Rueckgabecode.

Aufruf (Systempruefung, von Hand):

    python spiegelstand.py [--handel ORDNER] [--stunden N]

Rueckgabecode 0 = jede Spur, die der Dauerlauf faehrt, hat ein Ziel und ist
byte-gleich; 1 = mindestens eine Abweichung. Spuren mit `wachen.json`, die
nicht in `dauerlauf.SPUREN` stehen (orb: Altbestand), werden mitgeprueft,
aber gekennzeichnet und nicht gezaehlt. kraken stand bis zum 14.09.2026 in
dieser Liste - seit es der Dauerlauf fuehrt, wird es wie jede andere Spur
gezaehlt.
Das Modul schreibt nichts.
"""

import argparse
import ast
import csv
import json
import os
import time
from datetime import datetime, timezone

import risikostufe  # gleicher Ordner: Faktor und Dateinamen der Stufen

HANDEL = os.path.dirname(os.path.abspath(__file__))
DATEIEN = ("handelsjournal.csv", "zustand.json")
# Zusatzdateien je Spur. Der Vergleich ist derselbe (byte-genau), aber eine
# Datei, die nur EINE Spur mitbringt, darf die anderen nicht abweichend
# machen. spiegel fuehrt das Ablehnungsprotokoll - warum Kandidaten NICHT
# gekauft wurden. Es gehoert wie das Journal ausser Haus: faellt die Platte
# aus, fehlt sonst genau die Begruendung, die man spaeter braucht.
ZUSATZ = {"spiegel": ("ablehnungen.csv",),
        "scanner": ("ablehnungen.csv",)}


def lade(pfad):
    try:
        with open(pfad, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def gleich(a, b):
    """Byte-Vergleich - ein Zeilenende- oder Reihenfolgeunterschied zaehlt.

    Eine Datei, die auf BEIDEN Seiten fehlt, ist gleich: eine Spur erzeugt
    ihr Journal erst mit der ersten Buchung (kopier: bis zum ersten Kauf),
    ein Ablehnungsprotokoll erst mit dem ersten Zyklus. Fehlt sie nur auf
    EINER Seite, ist das eine Abweichung - die Kopie haengt hinterher.
    """
    try:
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read() == fb.read()
    except OSError:
        va, vb = os.path.exists(a), os.path.exists(b)
        return va == vb and not va


def zeilen(pfad):
    """Datenzeilen des Journals (ohne Kopfzeile); None, wenn nicht lesbar."""
    try:
        with open(pfad, newline="", encoding="utf-8") as f:
            return max(0, sum(1 for _ in csv.reader(f)) - 1)
    except OSError:
        return None


def alter_minuten(zeitstempel):
    if not zeitstempel:
        return None
    try:
        t = datetime.fromisoformat(str(zeitstempel).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() / 60


def frisches_alter(spurordner, benenne):
    """Alter des letzten Laufs - aus dem FRISCHESTEN der beiden Staende.

    `alter_minuten` allein auf zustand.json zu rechnen war ein Fehlalarm: eine
    Spur, die nur live laeuft, schreibt zustand.live.json, waehrend ihr
    Papierstand einfriert. Gemessen am 29.09.2026 lief `moondev_marktlage` im
    15-Minuten-Takt ("(live) ok" im dauerlauf.log), der Papierstand stand
    seit 03:39 - die Systempruefung machte daraus "Herzschlag 204 min alt
    (> 2 h) - laeuft die Spur ueberhaupt?" und meldete das jeden Tag.

    Dasselbe Muster wie `moondev_marktlage._papier_zustand()`: der Zustand des
    Zweigs, der schreibt, zaehlt; nur Papier sperrt eine Spur, die nie live
    lief. `benenne` biegt den Risikostufen-Suffix in BEIDE Namen.
    """
    werte = []
    for name in (benenne("zustand.json"), benenne("zustand.live.json")):
        werte.append(alter_minuten((lade(os.path.join(spurordner, name))
                                    or {}).get("letzter_lauf")))
    werte = [w for w in werte if w is not None]
    return min(werte) if werte else None


def spuren_im_lauf(handel=HANDEL):
    """Die Schluessel von `SPUREN` aus dauerlauf.py - per ast, nicht per import.

    Das Modul zu importieren zieht die halbe Handel-Umgebung; gelesen wird nur
    das Dict-Literal (die Werte enthalten os.path.join, deshalb nur die
    Schluessel). None, wenn die Datei fehlt oder nicht lesbar ist - dann gilt
    jede Spur mit wachen.json als relevant (kein stiller Freibrief).
    """
    try:
        with open(os.path.join(handel, "dauerlauf.py"), encoding="utf-8") as f:
            baum = ast.parse(f.read())
    except (OSError, SyntaxError):
        return None
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Assign) and any(
                isinstance(z, ast.Name) and z.id == "SPUREN"
                for z in knoten.targets):
            if not isinstance(knoten.value, ast.Dict):
                return None
            namen = {s.value for s in knoten.value.keys
                     if isinstance(s, ast.Constant) and isinstance(s.value, str)}
            return namen or None
    return None


def spuren_ordner(handel=HANDEL):
    """Spurname -> Unterordner aus dauerlauf.SPUREN (per ast).

    Seit den Spiegel-Schattenbuechern (18.09.2026) teilen sich mehrere Spuren
    einen Ordner (spiegel/spiegel_knapp/spiegel_weit -> alle "spiegel"). Der
    Spurname ist also nicht mehr der Ordnername. None, wenn nicht lesbar -
    dann faellt spur_zeile auf den Spurnamen als Ordnernamen zurueck.
    """
    try:
        with open(os.path.join(handel, "dauerlauf.py"), encoding="utf-8") as f:
            baum = ast.parse(f.read())
    except (OSError, SyntaxError):
        return None
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Assign) and any(
                isinstance(z, ast.Name) and z.id == "SPUREN"
                for z in knoten.targets):
            if not isinstance(knoten.value, ast.Dict):
                return None
            ordner = {}
            for schluessel, wert in zip(knoten.value.keys,
                                        knoten.value.values):
                if not isinstance(wert, ast.Dict):
                    continue
                for k2, v2 in zip(wert.keys, wert.values):
                    if (isinstance(k2, ast.Constant) and k2.value == "ordner"
                            and isinstance(v2, ast.Constant)
                            and isinstance(v2.value, str)):
                        ordner[schluessel.value] = v2.value
            return ordner or None
    return None


def laeufe_arme(handel, ordner):
    """Buecher eines Dauerlaufs, der unter <ordner>/laeufe/<arm>/ faehrt.

    llm_stunde (12.10.2026) startet sechs Straenge - drei Indikator-Kandidaten,
    jeder als Regel- (R) und LLM-Arm (L). Jeder Arm fuehrt ein eigenes Buch in
    laeufe/<variante>-<arm>/ mit eigener wachen.json (journal_zweitziel zeigt
    auf denselben Zielordner). Der Hauptordner llm_stunde/ selbst haelt nur
    die Basis-Wachen, KEINE Quelldateien - ihn als Spur zu pruefen meldet
    faelschlich ABWEICHUNG.

    Rueckgabe: die relativen Armbuecher (z. B. "llm_stunde/laeufe/ema1h-L").
    Leer, wenn kein laeufe-Unterordner mit eigenen Wachen existiert - dann
    prueft `stand` die Spur wie vorher.
    """
    laeufe = os.path.join(handel, ordner, "laeufe")
    if not os.path.isdir(laeufe):
        return []
    arme = sorted(
        d for d in os.listdir(laeufe)
        if os.path.isfile(os.path.join(laeufe, d, "wachen.json")))
    return [os.path.join(ordner, "laeufe", d) for d in arme]


def _arm_datei(name, suffix):
    """Dateiname eines Schattenbuchs: zustand.json -> zustand.knapp.json."""
    if not suffix:
        return name
    stamm, endung = os.path.splitext(name)
    return "%s.%s%s" % (stamm, suffix, endung)


def spur_zeile(handel, spur, risiko=None, ordner=None, _wachen_vorgabe=None):
    """Ein Pruefergebnis je Spur: Ziel, Kopiestand, Herzschlag, Journalzeilen.

    Verglichen werden die zwei Pflichtdateien plus die Zusatzdateien DIESER
    Spur (ZUSATZ). Eine fehlende Zusatzdatei liest sich wie ein Unterschied -
    das ist gewollt: sie wird im selben Zyklus mitgespiegelt, in dem sie
    entsteht, also muss sie auf beiden Seiten liegen.

    `risiko` prueft eine ANDERE Stufe als die dieses Prozesses: dann heissen
    die Dateien zustand.mittel.json und handelsjournal.mittel.csv (siehe
    risikostufe.datei_fuer). Ohne Angabe gilt die Stufe der Umgebung, also im
    Regelfall die Basis.

    `ordner` ist der Unterordner der Spur (aus dauerlauf.SPUREN). Seit den
    Spiegel-Schattenbuechern (18.09.2026) teilen sich mehrere Spuren einen
    Ordner; ohne Angabe faellt spur_zeile auf den Spurnamen zurueck.

    `_wachen_vorgabe` ist die Wachen-Datei je laeufe-Arm (llm_stunde,
    12.10.2026): von `stand` gesetzt, damit der Schatten-Suffix-Ersatz unten
    AUS bleibt. Ein Armename wie ema1h-L hat keinen Unterstrich zum Kuerzen;
    die Heuristik wuerde ueber die Spur-Struktur raten und faelschlich
    wachen.json erzeugen (dort liegt es ja wirklich). Das Trennzeichen ist
    der Unterstrich - deshalb kann `_wachen_vorgabe` einen leeren String nie
    mit einem "nicht gesetzt" verwechseln: aufgerufen wird es nur mit einem
    Dateinamen oder gar nicht.
    """
    def benenne(n):
        return n if risiko is None else risikostufe.datei_fuer(n, risiko)

    ordner = ordner or spur
    spurordner = os.path.join(handel, ordner)
    # Die Schattenarme tragen eigene Wachen-Dateien (wachen.knapp.json /
    # wachen.weit.json / wachen.futures.json / wachen.eth.json), deren
    # journal_zweitziel auf ihr eigenes Ziel zeigt. Die Haupt-Wachen
    # (wachen.json) gilt nur, wenn die Spur der Ordnername ist
    # (spiegel -> wachen.json).
    #
    # Das Suffix NICHT mit split("_", 1) raten: aus nautilus_kraken_futures
    # wird so "kraken_futures" und gesucht wird wachen.kraken_futures.json -
    # das gibt es nicht, dann still waere die HAUPT-Wachen des Ordners
    # (nautilus_kraken/wachen.json = der SPOT-Arm) gelesen worden und der
    # Futures-Arm waere mit dem fremden Ziel geprueft worden. 04.10.2026.
    # Korrekt ist: von rechts nach links kuerzen, bis die Datei da ist.
    wachen_name = _wachen_vorgabe or "wachen.json"
    if not _wachen_vorgabe and spur != ordner:
        teile = spur.split("_")
        for i in range(len(teile) - 1, 0, -1):
            kandidat = "wachen.%s.json" % "_".join(teile[i:])
            if os.path.isfile(os.path.join(spurordner, kandidat)):
                wachen_name = kandidat
                break
    w = lade(os.path.join(spurordner, wachen_name)) or {}
    z = lade(os.path.join(spurordner, benenne("zustand.json"))) or {}
    ziel = w.get("journal_zweitziel")
    ziel = ziel.replace("\\", os.sep) if isinstance(ziel, str) else None
    # Das Suffix gehoert an JEDE Buchdatei dieser Spur - auch an den Journal-
    # Zaehler und den Herzschlag. 04.10.2026: nautilus_kraken_futures las die
    # Zahl 1286 und das Ziel-Info des SPOT-Arms, weil anzahl/alter noch ohne
    # Suffix liefen (geprueft wurde trotzdem die richtige Datei - die Anzeige
    # war falsch, nicht der Vergleich). Es wird darum EINMAL oben bestimmt
    # und unten nur noch benutzt.
    suffix = wachen_name[len("wachen."):-len(".json")] \
        if wachen_name != "wachen.json" else ""
    dateinamen = (lambda n: benenne(_arm_datei(n, suffix) if suffix else n))
    alter = frisches_alter(spurordner, dateinamen)
    anzahl = zeilen(os.path.join(spurordner, dateinamen("handelsjournal.csv")))

    if not ziel:
        return {"spur": spur, "stand": "kein Ziel", "grund": "journal_zweitziel leer",
                "ziel": None, "alter": alter, "zeilen": anzahl}
    if not os.path.isdir(ziel):
        return {"spur": spur, "stand": "Ziel fehlt", "grund": "Ordner nicht erreichbar",
                "ziel": ziel, "alter": alter, "zeilen": anzahl}

    dateien = [dateinamen(n) for n in DATEIEN + ZUSATZ.get(spur, ())]
    # Die Schattenarme (18.09.2026) tragen ihre Dateien mit Suffix
    # (zustand.knapp.json, handelsjournal.knapp.csv). Der Vergleich muss
    # dieselben Namen nehmen, sonst meldet er eine Abweichung, wo die
    # Kopie byte-gleich ist.
    abweichungen = [n for n in dateien
                    if not gleich(os.path.join(spurordner, n), os.path.join(ziel, n))]
    return {"spur": spur,
            "stand": "gleich" if not abweichungen else "ABWEICHUNG",
            "grund": ", ".join(abweichungen) if abweichungen else
                     (z.get("journal_zweitziel_info") or ""),
            "ziel": ziel, "alter": alter, "zeilen": anzahl,
            "vermerk": z.get("journal_zweitziel_ok")}


def stand(handel=HANDEL, stunden=30.0, risiko=None):
    """Alle Spuren pruefen. Schluessel: spuren, geprueft, abweichend, ausserhalb,
    alt (Herzschlag ueber der Grenze), spurenliste.

    `risiko` prueft die Dateien einer Stufe (siehe spur_zeile); ohne Angabe
    die der Umgebung.
    """
    alle = []
    if not os.path.isdir(handel):
        return {"spuren": [], "geprueft": 0, "abweichend": [], "ausserhalb": [],
                "alt": [], "handel": handel, "im_lauf_lesbar": False,
                "fehler": "Ordner nicht erreichbar"}
    alle = sorted(d for d in os.listdir(handel)
                  if os.path.isfile(os.path.join(handel, d, "wachen.json")))
    im_lauf = spuren_im_lauf(handel)
    ordner_zuordnung = spuren_ordner(handel)
    ergebnis = {"spuren": [], "geprueft": 0, "abweichend": [], "ausserhalb": [],
                "alt": [], "handel": handel, "risiko": risiko,
                "im_lauf_lesbar": im_lauf is not None}
    # Die Schattenarme teilen den Ordner ihres Hauptbuchs, tragen aber eigene
    # Wachen-Dateien (wachen.knapp.json / wachen.weit.json / wachen.futures.json
    # / wachen.eth.json) mit eigenem `journal_zweitziel`. Sie stehen in
    # dauerlauf.SPUREN, aber nicht in `alle` (das nur Verzeichnisse mit
    # wachen.json listet). 04.10.2026: die Liste der ARM-NAMEN stand hier fest
    # und traf nur spiegel. Deshalb werden die Namen aus dauerlauf.SPUREN
    # GESAMMELT und die Dateiendung aus der Wachen-Datei gelesen - eine neue
    # Arm-Buchstabe braucht dann keinen zweiten Ort mehr.
    arm_dateien = ("wachen.knapp.json", "wachen.weit.json",
                   "wachen.futures.json", "wachen.eth.json")
    if ordner_zuordnung:
        for spur, ordner in ordner_zuordnung.items():
            if spur in alle:
                continue
            treffer = [w for w in arm_dateien
                       if os.path.isfile(os.path.join(handel, ordner, w))]
            if treffer:
                alle.append(spur)
        alle = sorted(set(alle))
    # Die laeufe-Arme (llm_stunde, 12.10.2026): der Hauptordner haelt nur die
    # Basis-Wachen, die SECHS Straenge fahren eigene Buecher unter
    # laeufe/<variante>-<arm>/. Jeder Arm ersetzt die Haupt-Spur im Pruefplan
    # (die selbst keine Quelldateien hat und sonst faelschlich ABWEICHUNG
    # meldet); im Lauf-Status gilt er durch seinen Hauptnamen (llm_stunde
    # steht in SPUREN, die Straenge nicht).
    zeilen = []  # (anzeige, ordner, wachen_vorgabe, zugehoerige_spur)
    for spur in alle:
        ordner = (ordner_zuordnung or {}).get(spur, spur)
        arme = laeufe_arme(handel, ordner)
        if arme:
            for arm in arme:
                zeilen.append(("%s/%s" % (spur, os.path.basename(arm)),
                               arm, "wachen.json", spur))
        else:
            zeilen.append((spur, ordner, None, spur))
    for spur, ordner, wachen_vorgabe, zugehoerig in zeilen:
        e = spur_zeile(handel, spur, risiko, ordner=ordner,
                       _wachen_vorgabe=wachen_vorgabe)
        im_dienst = im_lauf is None or zugehoerig in im_lauf
        if not im_dienst:
            ergebnis["ausserhalb"].append(spur)
            note = "[nicht in dauerlauf.SPUREN]"
            e["grund"] = (e["grund"] + "  " + note) if e["grund"] else note
        else:
            ergebnis["geprueft"] += 1
            if e["stand"] != "gleich":
                ergebnis["abweichend"].append(spur)
            if e["alter"] is not None and e["alter"] > stunden * 60:
                ergebnis["alt"].append((spur, e["alter"]))
        ergebnis["spuren"].append(e)
    return ergebnis


def kurz(e):
    """Eine Zeile fuer den Tagesbericht - nie eine Behauptung ohne Deckung."""
    if e.get("fehler"):
        return "nicht geprueft: %s" % e["fehler"]
    if not e["spuren"]:
        return "keine Spur mit wachen.json gefunden"
    if e["geprueft"] == 0 and e["ausserhalb"]:
        return "keine Spur im Dauerlauf gefunden (%s ausserhalb)" % ", ".join(e["ausserhalb"])
    if e["abweichend"]:
        return ("%d von %d Spuren ABWEICHEND (%s) - Q: pruefen"
                % (len(e["abweichend"]), e["geprueft"], ", ".join(e["abweichend"])))
    if not e["im_lauf_lesbar"]:
        return ("%d Spuren geprueft, alle byte-gleich (SPUREN nicht lesbar - "
                "auch Spuren ausserhalb des Dauerlaufs gezaehlt)" % e["geprueft"])
    return "%d von %d Spuren byte-gleich (Q:)" % (e["geprueft"], e["geprueft"])


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--handel", default=HANDEL,
                   help="Handel-Verzeichnis (Vorgabe: dieses Verzeichnis)")
    p.add_argument("--stunden", type=float, default=30.0,
                   help="ab wann der Herzschlag als alt gemeldet wird")
    p.add_argument("--risiko", choices=sorted(risikostufe.FAKTOREN),
                   default=risikostufe.STANDARD,
                   help="Risikostufe pruefen (Vorgabe %s = Basis). Eine Stufe "
                        "schreibt zustand.mittel.json und "
                        "handelsjournal.mittel.csv - dieselbe Rechnung, "
                        "andere Dateinamen."
                        % risikostufe.STANDARD)
    a = p.parse_args()

    e = stand(a.handel, a.stunden,
              None if a.risiko == risikostufe.STANDARD else a.risiko)
    if e.get("fehler"):
        print("Spiegelstand nicht pruefbar: %s (%s)" % (e["fehler"], a.handel))
        return 1
    if not e["spuren"]:
        print("keine Spur mit wachen.json unter %s" % a.handel)
        return 1

    if not e["im_lauf_lesbar"]:
        print("Hinweis: SPUREN aus dauerlauf.py nicht lesbar - alle Spuren mit "
              "wachen.json werden geprueft.")
    print("Spiegelstand Bedingung 4 - %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Handel: %s" % a.handel)
    print("Risikostufe: %s" % a.risiko)
    print()
    print("%-20s %-12s %7s %7s  %s" % ("Spur", "Stand", "Zeilen", "Alter",
                                      "Ziel / Grund"))
    for x in e["spuren"]:
        alter = "--" if x["alter"] is None else "%.0f min" % x["alter"]
        anzahl = "--" if x["zeilen"] is None else str(x["zeilen"])
        print("%-20s %-12s %7s %7s  %s%s" % (
            x["spur"], x["stand"], anzahl, alter, x["ziel"] or "--",
            "   [%s]" % x["grund"] if x["grund"] else ""))
        if x["alter"] is not None and x["spur"] not in e["ausserhalb"] \
                and x["alter"] > a.stunden * 60:
            print("%-20s   Hinweis: Herzschlag %.0f min alt (> %.0f h) - laeuft die "
                  "Spur ueberhaupt?" % ("", x["alter"], a.stunden))
    print()
    print("Ergebnis: %s" % kurz(e))
    if e["ausserhalb"]:
        print("ausserhalb des Dauerlaufs mitgeprueft: %s" % ", ".join(e["ausserhalb"]))
    return 0 if not e["abweichend"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
