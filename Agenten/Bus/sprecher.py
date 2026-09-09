"""Die einzige Stelle, die nach Telegram spricht.

Er ruft ausschliesslich melder.sende(). Niemals melder.hole() - sonst naehme
er dauerlauf.py die Nachrichten weg; davor warnt handel-dauerlauf.ps1 seit
jeher. Empfangen ist Teilprojekt 2.

Wie weit er gekommen ist, merkt er sich in stand.json. Nach einem Neustart
liest er das Journal ab dieser Marke weiter, damit nichts doppelt gemeldet
und nichts uebersprungen wird.
"""

import json
import os
import queue
import time
from datetime import datetime

import auffaellig
import journal

HIER = os.path.dirname(os.path.abspath(__file__))
STAND = os.path.join(HIER, "stand.json")


class Sprecher:
    def __init__(self, melder, regeln, wurzel=None, stand=None):
        self.melder = melder
        self.regeln = regeln
        self.wurzel = wurzel
        self.stand = stand or STAND
        self.gesehen = set(self._stand().get("ids", []))
        self.gesendet_seit = []          # Zeitstempel der letzten Meldungen
        self.deckel_gemeldet = False

    # --- Stand -----------------------------------------------------------
    def _stand(self):
        try:
            with open(self.stand, encoding="utf-8") as f:
                daten = json.load(f)
        except (OSError, ValueError):
            return {}
        # Nur der laufende Tag zaehlt - sonst waechst die Datei ewig.
        if daten.get("tag") != datetime.now().strftime("%Y-%m-%d"):
            return {}
        return daten

    def _stand_schreiben(self):
        try:
            with open(self.stand, "w", encoding="utf-8") as f:
                json.dump({"tag": datetime.now().strftime("%Y-%m-%d"),
                           "ids": sorted(self.gesehen)}, f)
        except OSError:
            pass

    # --- Melden ----------------------------------------------------------
    def _darf_senden(self):
        grenze = time.monotonic() - 3600
        self.gesendet_seit = [t for t in self.gesendet_seit if t > grenze]
        return len(self.gesendet_seit) < int(self.regeln["deckel_je_stunde"])

    def _sende(self, text):
        """True, wenn die Nachricht wirklich raus ist. Ein totes Telegram ist
        kein Fehler des Busses - das Journal steht."""
        try:
            self.melder.sende(text)
        except Exception:                                   # noqa: BLE001
            return False
        self.gesendet_seit.append(time.monotonic())
        return True

    def verarbeite(self, ereignis):
        eid = ereignis.get("id")
        if not eid or eid in self.gesehen:
            return False
        self.gesehen.add(eid)
        self._stand_schreiben()
        grund = auffaellig.bewerte(ereignis, self._historie(ereignis["wer"]),
                                   self.regeln)
        if not grund:
            return False
        if not self._darf_senden():
            if not self.deckel_gemeldet:
                self.deckel_gemeldet = True
                self._sende("Weitere Meldungen gedeckelt - zu viele in einer "
                            "Stunde. Der Rest steht im Journal.")
            return False
        return self._sende("%s: %s" % (ereignis["wer"], grund))

    def _historie(self, wer):
        return [e for e in journal.lesen(wurzel=self.wurzel)
                if e.get("wer") == wer and e.get("was") == "ende"]

    # --- Nachholen und Tagesmeldung --------------------------------------
    def nachholen(self):
        """Alles, was seit der Marke im Journal steht - etwa weil der Bus tot
        war und die Erzeuger selbst geschrieben haben."""
        for e in journal.lesen(wurzel=self.wurzel):
            self.verarbeite(e)

    def tagesmeldung(self):
        anzahl, dauer = {}, {}
        for e in journal.lesen(wurzel=self.wurzel):
            if e.get("was") != "ende":
                continue
            wer = e.get("wer", "?")
            anzahl[wer] = anzahl.get(wer, 0) + 1
            dauer[wer] = dauer.get(wer, 0) + (e.get("dauer_s") or 0)
        if not anzahl:
            return "Heute lief nichts."
        text = ["Tagesmeldung %s" % datetime.now().strftime("%d.%m.%Y")]
        for wer in sorted(anzahl):
            text.append("%s: %dx, zusammen %d s" % (wer, anzahl[wer], dauer[wer]))
        return "\n".join(text)

    def _letzte_laeufe(self):
        letzte = {}
        for e in journal.lesen(wurzel=self.wurzel):
            if e.get("was") != "ende":
                continue
            try:
                z = datetime.fromisoformat(e["zeit"]).replace(tzinfo=None)
            except (KeyError, ValueError):
                continue
            wer = e.get("wer")
            if wer and (wer not in letzte or z > letzte[wer]):
                letzte[wer] = z
        return letzte

    # --- Faden -----------------------------------------------------------
    def lauf(self, warteschlange):
        """Laeuft im Bus-Prozess. Holt aus der Warteschlange, holt einmal am
        Anfang das Journal nach, schickt abends die Sammelmeldung."""
        self.nachholen()
        letzter_tag = None
        while True:
            try:
                self.verarbeite(warteschlange.get(timeout=5))
            except queue.Empty:
                pass
            except Exception:                               # noqa: BLE001
                pass        # der Sprecher darf den Bus nie mitreissen
            jetzt = datetime.now()
            if jetzt.hour >= 20 and letzter_tag != jetzt.date():
                letzter_tag = jetzt.date()
                offen = auffaellig.ausbleibend(self._letzte_laeufe(),
                                               self.regeln, jetzt)
                text = self.tagesmeldung()
                if offen:
                    text += "\nAusgeblieben: " + ", ".join(offen)
                self._sende(text)
