"""Scharfschalten auf Zeit - die Handy-Fassung des Freigabefensters.

Angelegt am 03.09.2026 auf Max' Anweisung: 24/7-Betrieb mit Steuerung ueber
das Smartphone. Das kollidiert mit Punkt 3 der Handelsregeln, wonach scharf
nur am Bildschirm geschaltet wird - vor einem Fenster, das die Werte aus
wachen.json zeigt und nach 120 Sekunden von selbst ablehnt.

Diese Datei loest den Widerspruch, ohne die Regel aufzugeben. Sie ersetzt
das Bildschirmfenster durch ein *Zeitfenster*, das dieselben drei Dinge
leistet:

  Bildschirmfenster (freigabe.py)      Zeitfenster (hier)
  ---------------------------------    ---------------------------------
  zeigt die Werte aus wachen.json      dieselben Werte in der Anfrage
  Max bestaetigt oder lehnt ab         Max antwortet /ja oder /nein
  laeuft nach 120 s ab -> Ablehnung    laeuft nach dauer_minuten ab ->
                                       zurueck auf Papier

Der tragende Satz bleibt unberuehrt: **Der Automat entscheidet ueber
Positionen, nicht darueber, ob er selbst scharf ist.** Kein Skript schreibt
sich hier eine Freigabe. Was der Dauerlauf tun darf, wenn niemand antwortet,
ist Papierhandel - und sonst nichts.

WAS EINE FREIGABE NICHT KANN
----------------------------
Sie oeffnet ein Zeitfenster, mehr nicht. Sie kann keine Grenze anheben: nicht
den Einsatz, nicht den Hebel, nicht die Zahl der Positionen. Alle Werte
kommen weiter aus wachen.json. Wer mehr will, aendert die Datei - und das ist
Stufe 1 mit eigenem Commit und gerechneten Zahlen.

Damit ist auch der Telegram-Kanal begrenzt: Wer ihn uebernimmt, kann
hoechstens ein Fenster oeffnen, dessen Grenzen schon feststehen.

ABLAUF
------
    freigabe = lade()                     # was gerade gilt
    if freigabe.offen(): ...              # scharf, bis es ablaeuft

    anfragen(spur, dauer_minuten=1440)    # fragt per Telegram
    # Max antwortet /ja 12  -> 12 Stunden offen
    # Max antwortet /nein   -> abgelehnt
    # keine Antwort         -> nach antwort_frist_minuten verfallen

    neue_anfrage_erlaubt(spur)            # darf ueberhaupt neu gefragt werden?
    # nach einer Ablehnung 12 h lang nicht, nach einer unbeantworteten Anfrage
    # 2 h lang nicht - sonst fragt der Dauerlauf dieselbe Sache im Halbstundentakt

Die Freigabe steht in freigabe_fenster.json, nicht in wachen.json. Grund:
wachen.json wird von den Skripten gelesen und nie geschrieben (einzige
Ausnahme: sperre_zu von true auf false). Ein Zeitfenster ist Betriebszustand,
keine Grenze - es gehoert nicht in die Datei, die die Grenzen haelt.
"""

import contextlib
import datetime as dt
import json
import os
import re
import time

HIER = os.path.dirname(os.path.abspath(__file__))
DATEI = os.path.join(HIER, "freigabe_fenster.json")

# Laenger als das darf ein Fenster nie sein, egal was jemand schickt. Eine
# Freigabe, die man vergessen kann, ist keine Freigabe - sie ist ein
# Dauerzustand mit hoeflichem Namen.
MAX_STUNDEN = 24

# So lange wartet eine Anfrage auf Antwort. Danach verfaellt sie. Das ist das
# Gegenstueck zu den 120 Sekunden des Bildschirmfensters: Wer nicht antwortet,
# hat nicht freigegeben.
ANTWORT_FRIST_MINUTEN = 30

# Wiedervorlage - zwei Fristen, absichtlich ungleich. Eine *unbeantwortete*
# Anfrage darf der Dauerlauf wiederholen: Vielleicht war Max nicht am Handy.
# Eine *abgelehnte* nicht. Wer um 19:06 /nein sagt, bekommt um 19:20 nicht
# dieselbe Frage wortgleich erneut; solche Fragen werden weggewischt, und mit
# ihnen die naechste, auf die es ankommt - derselbe Grund, aus dem der
# Dauerlauf ueberhaupt erst fragt, wenn nur noch das Fenster fehlt.
WIEDERVORLAGE_MINUTEN = 120
WIEDERVORLAGE_NACH_ABLEHNUNG_STUNDEN = 12

# Was als Ablehnung zaehlt. schliessen() schreibt den Grund ins Feld
# schliess_grund; /nein und /stop sind beide eine Entscheidung gegen den
# Handel, "Dauerlauf beendet" ist keine.
ABLEHNUNGSGRUENDE = ("abgelehnt", "stop")

# Zwei Schreiber (Dauerlauf, Leitstand): jede Lesen-Aendern-Schreiben-Folge
# laeuft unter einer Dateisperre neben DATEI.
SPERRE_WARTEN_S = 5.0
SPERRE_VERWAIST_S = 30.0


@contextlib.contextmanager
def _gesperrt():
    """Exklusiv lesen-aendern-schreiben. Sperre = DATEI.lock (O_CREAT|O_EXCL).

    Wer sie nicht bekommt, wartet hoechstens SPERRE_WARTEN_S und bekommt dann
    TimeoutError - geschrieben wird dann nichts. Eine Sperre, die aelter als
    SPERRE_VERWAIST_S ist, stammt von einem abgestuerzten Prozess und wird
    entfernt.
    """
    sperre = DATEI + ".lock"
    frist = time.monotonic() + SPERRE_WARTEN_S
    while True:
        try:
            fd = os.open(sperre, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except (FileExistsError, PermissionError):
            # PermissionError: Windows, die Sperre wird gerade geloescht.
            try:
                if time.time() - os.path.getmtime(sperre) > SPERRE_VERWAIST_S:
                    os.remove(sperre)
                    continue
            except OSError:
                pass
            if time.monotonic() >= frist:
                raise TimeoutError("Sperre %s belegt" % sperre)
            time.sleep(0.02)
    try:
        try:
            os.write(fd, str(os.getpid()).encode("ascii"))
        finally:
            os.close(fd)
        yield
    finally:
        try:
            os.remove(sperre)
        except OSError:
            pass


def _jetzt():
    # Use naive local datetime, not UTC-aware.
    # _zeit() returns naive datetimes; mixed comparisons raise TypeError.
    return dt.datetime.now()


def _lies():
    try:
        with open(DATEI, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _schreib(d):
    """Atomar: erst DATEI.tmp, dann os.replace - kein Leser sieht eine halbe Datei."""
    tmp = DATEI + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")
    for versuch in range(20):
        try:
            os.replace(tmp, DATEI)
            return
        except PermissionError:
            # Windows: ein Leser haelt DATEI gerade offen.
            if versuch == 19:
                raise
            time.sleep(0.05)


class Fenster:
    """Der Freigabestand einer Spur."""

    def __init__(self, spur, d):
        self.spur = spur
        self.d = d or {}

    @property
    def bis(self):
        return _zeit(self.d.get("offen_bis"))

    def offen(self):
        """Ist gerade scharf freigegeben?"""
        b = self.bis
        return bool(b and _jetzt() < b)

    def rest_minuten(self):
        b = self.bis
        if not b:
            return 0
        return max(0, int((b - _jetzt()).total_seconds() // 60))

    def anfrage_offen(self):
        """Wartet gerade eine unbeantwortete Anfrage?"""
        b = _zeit(self.d.get("anfrage_bis"))
        return bool(b and _jetzt() < b)

    def text(self):
        if self.offen():
            r = self.rest_minuten()
            return "scharf, noch %d:%02d h" % (r // 60, r % 60)
        if self.anfrage_offen():
            return "Anfrage laeuft, unbeantwortet"
        return "Papier"


def lade(spur):
    return Fenster(spur, _lies().get(spur))


def alle():
    return {s: Fenster(s, d) for s, d in _lies().items()}


def _zeit(wert):
    """ISO-Zeit aus der Datei - oder None. Ein kaputter Wert darf nicht werfen.

    _jetzt() liefert naive lokale Zeit (Fix vom 17.09.2026 - vorher UTC-
    aware). Alte Eintraege in freigabe_fenster.json koennen noch ein
    "+00:00" tragen (mit der alten _jetzt() geschrieben) - ein aware Wert
    wird deshalb IMMER auf naive lokale Zeit gebracht, sonst crasht jeder
    Vergleich mit _jetzt() (TypeError: can't compare offset-naive and
    offset-aware).

    Gebracht heisst UMGERECHNET (astimezone), nicht abgeschnitten: das blosse
    Abschneiden las eine UTC-Zeit als Ortszeit - 1 bis 2 Stunden daneben, ein
    Freigabefenster lief entsprechend zu frueh oder zu spaet ab (30.09.2026).
    """
    if not wert:
        return None
    try:
        w = dt.datetime.fromisoformat(wert)
    except (TypeError, ValueError):
        return None
    return w.astimezone().replace(tzinfo=None) if w.tzinfo is not None else w


def neue_anfrage_erlaubt(spur):
    """Darf der Dauerlauf diese Spur jetzt erneut fragen?

    Es gilt die spaeteste der beiden Fristen: WIEDERVORLAGE_MINUTEN nach der
    letzten Anfrage, WIEDERVORLAGE_NACH_ABLEHNUNG_STUNDEN nach einer Ablehnung.
    Grundlage ist der eigene Zustand - anfrage_gestellt und
    zuletzt_geschlossen stehen ohnehin hier, eine zweite Merkdatei waere eine
    zweite Wahrheit.

    Was das nicht ist: eine Sperre. Kein Pfad wird geschlossen, kein Wert
    angehoben, keine Freigabe verweigert - es wird nur nicht mehr gefragt.
    Wer es sich anders ueberlegt, schaltet am Bildschirm scharf
    (freigabe.py) oder antwortet auf die naechste Anfrage.
    """
    d = _lies().get(spur) or {}
    fristen = []

    zu = _zeit(d.get("zuletzt_geschlossen"))
    grund = (d.get("schliess_grund") or "").lower()
    # Wortgrenzen-Match: "Befehl /stop" und "Telegram stop" muessen treffen
    # (echte Aufrufer in dauerlauf.py), aber "stoppage"/"stopped early" nicht
    # (der einzige Grund fuer den frueheren exact-match-Fix - der hat jedoch
    # die echten Aufrufer selbst zerschossen, 17.09.2026 per Test gefunden).
    if zu and any(re.search(r"\b%s\b" % re.escape(w), grund)
                  for w in ABLEHNUNGSGRUENDE):
        fristen.append(zu + dt.timedelta(
            hours=WIEDERVORLAGE_NACH_ABLEHNUNG_STUNDEN))

    gestellt = _zeit(d.get("anfrage_gestellt"))
    if gestellt:
        fristen.append(gestellt + dt.timedelta(minutes=WIEDERVORLAGE_MINUTEN))

    return not fristen or _jetzt() >= max(fristen)


def anfrage_stellen(spur, dauer_minuten):
    """Merkt eine wartende Anfrage vor. Oeffnet noch nichts."""
    with _gesperrt():
        d = _lies()
        e = d.setdefault(spur, {})
        e["anfrage_bis"] = (_jetzt() + dt.timedelta(
            minutes=ANTWORT_FRIST_MINUTEN)).isoformat()
        e["anfrage_dauer_minuten"] = min(dauer_minuten, MAX_STUNDEN * 60)
        e["anfrage_gestellt"] = _jetzt().isoformat()
        _schreib(d)
        return e["anfrage_dauer_minuten"]


def oeffnen(spur, stunden=None, wer="telegram"):
    """Gibt frei - nur, wenn eine Anfrage wartet.

    Ohne wartende Anfrage passiert nichts. Damit kann eine uebernommene
    Telegram-Sitzung nicht aus dem Nichts scharf schalten: Der Anstoss kommt
    immer vom Dauerlauf, der die Lage geprueft hat.
    """
    with _gesperrt():
        d = _lies()
        e = d.get(spur) or {}
        s = e.get("anfrage_bis")
        anfrage_endet = _zeit(s)  # Use _zeit() for safe parsing
        if not anfrage_endet or _jetzt() >= anfrage_endet:
            return None

        minuten = (stunden * 60 if stunden
                   else e.get("anfrage_dauer_minuten", 60))
        minuten = min(minuten, MAX_STUNDEN * 60)

        e["offen_bis"] = (_jetzt() + dt.timedelta(minutes=minuten)).isoformat()
        e["freigegeben_von"] = wer
        e["freigegeben_am"] = _jetzt().isoformat()
        e.pop("anfrage_bis", None)
        d[spur] = e
        _schreib(d)
        return minuten


def _schliesse_in(d, spur, grund):
    """Eine Spur in d auf Papier setzen. Ohne Sperre, ohne Schreiben."""
    e = d.get(spur)
    if not isinstance(e, dict):        # kaputter Eintrag: ersetzen, nicht werfen
        e = d[spur] = {}
    war = Fenster(spur, dict(e)).offen()
    e.pop("offen_bis", None)
    e.pop("anfrage_bis", None)
    e["zuletzt_geschlossen"] = _jetzt().isoformat()
    e["schliess_grund"] = grund
    return war


def schliessen(spur, grund="von Hand"):
    """Sofort zurueck auf Papier. Geht immer, ohne Anfrage, ohne Frist."""
    with _gesperrt():
        d = _lies()
        war = _schliesse_in(d, spur, grund)
        _schreib(d)
    return war


def alles_schliessen(grund="Notaus"):
    """Jede Spur zurueck auf Papier - eine Sperre, ein Schreiben."""
    with _gesperrt():
        d = _lies()
        if not d:
            return []
        offen = [s for s in list(d) if _schliesse_in(d, s, grund)]
        _schreib(d)
    return offen


def grenzwerte(w, waehrung="USD"):
    """Die Grenzen aus wachen.json als (Bezeichnung, Wert mit Einheit).

    anfrage_text() (Telegram) und der Freigabe-Dialog des Leitstands zeigen
    dieselbe Liste - eine zweite Fassung waere eine zweite Wahrheit.
    """
    def w_(*namen):
        for n in namen:
            if n in w:
                return w[n]
        return None

    paare = [
        ("je Anlauf", w_("max_pro_trade_eur", "max_pro_trade_usd",
                         "max_margin_je_anlauf_usd"), waehrung),
        ("gesamt", w_("max_gesamt_eur", "max_gesamt_usd",
                      "max_margin_gesamt_usd"), waehrung),
        ("Positionen", w_("max_offene_positionen", "max_offene_anlaeufe"), ""),
        ("Hebel bis", w_("max_hebel"), "x"),
        ("Risiko je Anlauf", w_("risiko_je_anlauf_usd"), waehrung),
        ("Kill-Switch", w_("kill_switch_gesamt_usd"), waehrung),
    ]
    zeilen = [(name, "%s %s" % (wert, einheit))
              for name, wert, einheit in paare if wert is not None]
    # Familien mit eigener Hebel-/Stopgrenze (Rohstoffe, Auftrag Max
    # 08.10.2026) muessen in der Anfrage stehen: sonst unterschriebe Max
    # "Hebel bis 5x" und der Automat risse bei Rohstoffen 10x.
    for fam_name, fam in sorted((w.get("familien") or {}).items()):
        if "max_hebel" in fam:
            text = "%s x" % fam["max_hebel"]
            if fam.get("stop_max_pct") is not None:
                text += ", Stop hoechstens %s %%" % fam["stop_max_pct"]
            zeilen.append(("Hebel bis (%s)" % fam_name, text))
    return zeilen


def anfrage_text(spur, w, dauer_minuten, waehrung="USD"):
    """Was in der Anfrage steht: dieselben Werte, die freigabe.py zeigt.

    Ohne diese Werte waere die Freigabe eine Blankounterschrift. Das
    Bildschirmfenster zeigt sie, also zeigt die Handy-Fassung sie auch.
    """
    z = ["<b>Freigabe %s?</b>" % spur,
         "Dauer: %d:%02d h" % (dauer_minuten // 60, dauer_minuten % 60),
         "", "Es gelten die Grenzen aus wachen.json:"]

    for name, wert in grenzwerte(w, waehrung):
        z.append("  %-18s %s" % (name, wert))

    z += ["",
          "/ja        freigeben fuer %d:%02d h" % (dauer_minuten // 60,
                                                   dauer_minuten % 60),
          "/ja 6      stattdessen 6 Stunden",
          "/nein      ablehnen",
          "",
          "Ohne Antwort verfaellt die Anfrage in %d Minuten."
          % ANTWORT_FRIST_MINUTEN]
    return "\n".join(z)


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stand", action="store_true", help="was gerade gilt")
    p.add_argument("--schliessen", metavar="SPUR",
                   help="eine Spur sofort auf Papier zuruecksetzen")
    p.add_argument("--alles-schliessen", action="store_true")
    a = p.parse_args()

    if a.schliessen:
        print("geschlossen" if schliessen(a.schliessen, "von Hand")
              else "war nicht offen")
        return 0
    if a.alles_schliessen:
        w = alles_schliessen("von Hand")
        print("geschlossen: %s" % (", ".join(w) if w else "nichts war offen"))
        return 0

    f = alle()
    if not f:
        print("Kein Fenster je geoeffnet - alle Spuren auf Papier.")
        return 0
    for spur, fenster in f.items():
        print("  %-10s %s" % (spur, fenster.text()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
