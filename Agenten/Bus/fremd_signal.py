"""Bus-Nachrichtentyp "signal": Fremd-Werkzeuge melden Signale ueber den Bus.

Regeln stehen im Hermes-Skill `fremdrepos-signal`. Jedes Signal geht durch das
Tor `Agenten/Handel/fremd_tor.py` (erst Schema, dann Wache
`fremd_signale/wachen.json`). Ist die Wache zu, unlesbar oder unvollstaendig,
wird verworfen. Dieses Modul handelt nicht und wirft nie (Grundregel des Bus:
ein toter Bus bricht keinen Lauf ab).

Zeilen im Journal (Felder wie journal.neu, `text` = JSON bzw. Verwerfgrund):
  was = "signal"            durchs Tor gelassen, Text = das Signal als JSON
  was = "signal_verworfen"  Schema- oder Tor-Verstoss, Text = Grund (kein Retry, kein Handy)
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


def _tor():
    if _HANDEL not in sys.path:
        sys.path.insert(0, _HANDEL)
    import fremd_tor
    return fremd_tor


def melden_signal(wer, signal, jetzt=None, port=None, wurzel=None, wache=None):
    """Schickt das Signal durchs Tor und meldet das Ergebnis. (ok, grund). Wirft nie.

    `wache`: geladene Wache; ohne Angabe wird fremd_signale/wachen.json gelesen
    (kaputt oder zu = Tor zu).
    """
    try:
        jetzt = time.time() if jetzt is None else jetzt
        tor = _tor()
        w = wache if wache is not None else tor.lade()
        ok, grund = tor.entscheide(signal, w, jetzt)
        if ok:
            zeile = journal.neu(wer, "signal",
                                text=json.dumps(signal, ensure_ascii=False))
        else:
            zeile = journal.neu(wer, "signal_verworfen", text=grund)
        ereignis.melden(zeile, port=port, wurzel=wurzel)
        return ok, grund
    except Exception as f:                                  # noqa: BLE001
        return False, "%s: %s" % (type(f).__name__, f)
