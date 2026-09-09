"""Die Erzeugerseite. Zwei Zeilen pro Komponente, mehr soll es nicht sein.

Hier gilt die Regel, die ueber allen anderen steht: ein toter Bus darf
niemals einen Lauf abbrechen. Deshalb faengt jede Funktion in diesem Modul
alles ab, wirft nie von sich aus und wartet nie laenger als eine Sekunde.
Kommt der Bus nicht ans Telefon, schreibt der Erzeuger die Zeile selbst -
der Sprecher findet sie beim naechsten Durchgang.
"""

import contextlib
import json
import time
import urllib.request

import bus
import journal

ZEITLIMIT = 1.0

# Auf diesem Windows-Rechner wird ein Verbindungsversuch auf einen lokalen
# Port ohne Lauscher nicht sofort abgelehnt, sondern laeuft in das volle
# ZEITLIMIT. Ohne Gegenmassnahme zahlt jeder einzelne Aufruf von melden()
# diesen Aufschlag erneut - ein lauf() mit zwei Ereignissen also doppelt,
# und ein Dauerprozess bei jedem Takt. Deshalb merkt sich dieses Modul (ganz
# bewusst als schlichter globaler Zustand, keine Klasse - es gibt ohnehin
# nur einen Prozess je Erzeuger) den Zeitpunkt des letzten Fehlschlags: Ist
# der Bus einmal nicht ans Telefon gekommen, wird fuer die Dauer von
# MERKZEIT nicht erneut angeklopft, sondern sofort ins Journal geschrieben.
# Nach Ablauf der Frist versucht der naechste Aufruf es wieder - startet der
# Dienst spaeter, findet ihn dieser Versuch. _merkzustand_zuruecksetzen()
# existiert nur fuer Tests, die unabhaengig von der Wanduhr pruefen wollen.
MERKZEIT = 60.0

_zuletzt_toter_versuch = None


def _merkzustand_zuruecksetzen():
    """Nur fuer Tests: vergisst einen gemerkten Fehlschlag."""
    global _zuletzt_toter_versuch
    _zuletzt_toter_versuch = None


def melden(ereignis, port=None, wurzel=None):
    """Erst an den Bus, sonst selbst ins Journal. Wirft nie."""
    global _zuletzt_toter_versuch
    jetzt = time.monotonic()
    innerhalb_merkzeit = (_zuletzt_toter_versuch is not None
                           and jetzt - _zuletzt_toter_versuch < MERKZEIT)
    if not innerhalb_merkzeit:
        try:
            p = port if port is not None else bus.port_aus_datei()
        except Exception:                                   # noqa: BLE001
            p = None
        if p:
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:%d/ereignis" % p,
                    data=json.dumps(ereignis, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=ZEITLIMIT):
                    _zuletzt_toter_versuch = None
                    return "bus"
            except Exception:                               # noqa: BLE001
                _zuletzt_toter_versuch = jetzt
    try:
        journal.anhaengen(ereignis, wurzel=wurzel)
        return "journal"
    except Exception:                                       # noqa: BLE001
        return "nichts"      # stille Aufgabe - der Lauf ist wichtiger


def hinweis(wer, text, port=None, wurzel=None):
    """Ein Agent sagt von sich aus etwas. Immer auffaellig (siehe Aufgabe 5)."""
    return melden(journal.neu(wer, "hinweis", text=text), port=port,
                  wurzel=wurzel)


@contextlib.contextmanager
def lauf(wer, log=None, port=None, wurzel=None):
    """Meldet Start, Ende, Dauer und einen Fehler von selbst.

        with ereignis.lauf("handel/xperp"):
            ...
    """
    begonnen = time.monotonic()
    melden(journal.neu(wer, "start", log=log), port=port, wurzel=wurzel)
    code, text = 0, ""
    try:
        yield
    except SystemExit as f:
        # sys.exit(0) bzw. sys.exit() ist ein sauberer Lauf, kein Fehler -
        # sonst meldet der Sprecher spaeter faelschlich "code: 1" fuers Handy.
        # Ein anderer Code wird uebernommen; KeyboardInterrupt faellt nicht
        # hierunter und bleibt unten ein Fehler.
        if f.code is None or f.code == 0:
            code = 0
            text = ""
        else:
            code = f.code
            text = "%s: %s" % (type(f).__name__, f)
        raise                       # der Aufrufer muss den Fehler sehen
    except BaseException as f:                              # noqa: BLE001
        code = 1
        text = "%s: %s" % (type(f).__name__, f)
        raise                       # der Aufrufer muss den Fehler sehen
    finally:
        dauer = int(time.monotonic() - begonnen)
        melden(journal.neu(wer, "ende", code=code, dauer_s=dauer, text=text,
                           log=log), port=port, wurzel=wurzel)
