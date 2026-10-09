"""Bus-Nachrichtentyp "signal": Fremd-Werkzeuge melden Signale ueber den Bus.

Regeln stehen im Hermes-Skill `fremdrepos-signal`, geprueft wird mit
`Agenten/Handel/signal_schema.py`. Dieses Modul handelt nicht und wirft nie
(Grundregel des Bus: ein toter Bus bricht keinen Lauf ab).

Zeilen im Journal (Felder wie journal.neu, `text` = JSON bzw. Verwerfgrund):
  was = "signal"            gueltig, Text = das Signal als JSON
  was = "signal_verworfen"  ungueltig, Text = Grund (kein Retry, kein Handy)
Beide Typen sind fuer auffaellig.py unbekannt und bleiben deshalb still.
Ausfuehren tut ein Signal erst das wachen.json-Gate in Handel/.
"""
import json
import os
import sys
import time

import ereignis
import journal

_HANDEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "Handel"))


def _schema():
    if _HANDEL not in sys.path:
        sys.path.insert(0, _HANDEL)
    import signal_schema
    return signal_schema


def melden_signal(wer, signal, jetzt=None, port=None, wurzel=None):
    """Prueft und meldet. Gibt (ok, grund) zurueck. Wirft nie."""
    try:
        jetzt = time.time() if jetzt is None else jetzt
        ok, grund = _schema().pruefe(signal, jetzt)
        if ok:
            zeile = journal.neu(wer, "signal",
                                text=json.dumps(signal, ensure_ascii=False))
        else:
            zeile = journal.neu(wer, "signal_verworfen", text=grund)
        ereignis.melden(zeile, port=port, wurzel=wurzel)
        return ok, grund
    except Exception as f:                                  # noqa: BLE001
        return False, "%s: %s" % (type(f).__name__, f)
