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


def melden(ereignis, port=None, wurzel=None):
    """Erst an den Bus, sonst selbst ins Journal. Wirft nie."""
    try:
        p = port if port is not None else bus.port_aus_datei()
    except Exception:                                       # noqa: BLE001
        p = None
    if p:
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:%d/ereignis" % p,
                data=json.dumps(ereignis, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=ZEITLIMIT):
                return "bus"
        except Exception:                                   # noqa: BLE001
            pass
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
    except BaseException as f:                              # noqa: BLE001
        code = 1
        text = "%s: %s" % (type(f).__name__, f)
        raise                       # der Aufrufer muss den Fehler sehen
    finally:
        dauer = int(time.monotonic() - begonnen)
        melden(journal.neu(wer, "ende", code=code, dauer_s=dauer, text=text,
                           log=log), port=port, wurzel=wurzel)
