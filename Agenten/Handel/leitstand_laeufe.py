"""Laeufe des Leitstands: ein Prozess zur Zeit, abbrechbar, abgelegt.

Jeder Backtest, jede Optimierung und jede Urteils-Vorschau laeuft hierueber:
  * hoechstens EIN Lauf gleichzeitig (Steuerung.starte wirft sonst),
  * niedrige Prioritaet (Windows: BELOW_NORMAL_PRIORITY_CLASS), Arbeitsordner
    ist Handel/, stdout und stderr zusammen, zeilenweise ueber eine Queue,
  * Abbrechen beendet den ganzen Prozessbaum (Windows: taskkill /T /F).
    backtest_urteile.py startet seine Motoren als Kindprozesse; terminate()
    allein liesse sie bis zu 15 min weiterrechnen.
  * Ablage backtest_laeufe/<JJJJMMTT-hhmmss>-<name>.json, Ausgabe auf 1 MB
    gekuerzt. Der Ordner ist nicht versioniert und wird von keinem
    Betriebsteil gelesen.
"""

import json
import os
import queue
import re
import signal
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
ABLAGE = HIER / "backtest_laeufe"
MAX_AUSGABE = 1_000_000           # Zeichen der Ausgabe in der Ablage
ABBRUCH_WARTEN_S = 5              # ausserhalb Windows: terminate, dann kill
BELOW_NORMAL = 0x00004000         # BELOW_NORMAL_PRIORITY_CLASS
OHNE_FENSTER = 0x08000000         # CREATE_NO_WINDOW fuer taskkill
VORSCHAU_ENDUNG = "-vorschau.json"

LISTE_SPALTEN = ("Datei", "Lauf", "Start", "Dauer", "Ergebnis")
KENNZAHL_SPALTEN = ("Kennzahl", "A", "B", "Differenz B−A")
_KOPF = ("spur", "runden", "offen", "gebuehr_pct", "fenster", "kerzenquelle",
         "gleich", "abweichungen", "runden_alt")


# --- Hilfen -----------------------------------------------------------------

def zeitstempel(jetzt=None):
    return (jetzt or datetime.now()).strftime("%Y%m%d-%H%M%S")


def sicherer_name(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(name)).strip("_") or "lauf"


def kuerze(text, grenze=MAX_AUSGABE):
    """Das ENDE behalten: dort stehen Kennzahlen und Urteil."""
    if len(text) <= grenze:
        return text
    return ("[… %d Zeichen am Anfang gekürzt]\n" % (len(text) - grenze)
            + text[-grenze:])


def json_aus_ausgabe(text):
    """Das letzte JSON-Objekt, das am Anfang einer Zeile beginnt, oder None.

    Davor koennen Hinweise stehen ("Zeitraum angehoben: ..."), danach
    Schlusszeilen ("Trockenlauf: nichts gerechnet ..."). Eingerueckte
    Klammern (verschachtelte Objekte) beginnen nie am Zeilenanfang.
    """
    dec = json.JSONDecoder()
    letztes = None
    for m in re.finditer(r"(?m)^\{", text):
        try:
            obj, _ende = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(obj, dict):
            letztes = obj
    return letztes


def _schreib_json(pfad, daten):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, pfad)


def _jetzt_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _posix_start():
    os.setsid()                   # eigene Prozessgruppe: killpg trifft den Baum
    os.nice(10)


# --- ein Lauf ---------------------------------------------------------------

class Lauf:
    def __init__(self, name, befehl, ablage=None, stempel=None, auswerten=None):
        self.name, self.befehl = name, [str(b) for b in befehl]
        self.ablage = Path(ablage or ABLAGE)
        self.stempel = stempel or zeitstempel()
        self.auswerten = auswerten
        self.pfad = self.ablage / ("%s-%s.json" % (self.stempel, sicherer_name(name)))
        self.zeilen, self.abgebrochen, self.exit_code = [], False, None
        self.start = _jetzt_iso()
        self._t0 = time.monotonic()
        self._q = queue.Queue()
        self._eof = False
        umgebung = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        kw = ({"creationflags": BELOW_NORMAL} if os.name == "nt"
              else {"preexec_fn": _posix_start})
        self.proc = subprocess.Popen(
            self.befehl, cwd=str(HIER), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1, env=umgebung, **kw)
        threading.Thread(target=self._lesen, daemon=True).start()

    def _lesen(self):
        try:
            for zeile in self.proc.stdout:
                self._q.put(zeile)
        finally:
            self._q.put(None)

    def neue_zeilen(self):
        neu = []
        while not self._eof:
            try:
                z = self._q.get_nowait()
            except queue.Empty:
                break
            if z is None:
                self._eof = True
            else:
                neu.append(z)
        self.zeilen.extend(neu)
        return neu

    def fertig(self):
        return self._eof and self.proc.poll() is not None

    def verstrichen_s(self):
        return time.monotonic() - self._t0

    def abbrechen(self):
        if self.proc.poll() is not None:
            return
        self.abgebrochen = True
        if os.name == "nt":
            r = subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=OHNE_FENSTER)
            if r.returncode != 0 and self.proc.poll() is None:
                self.proc.kill()
            return
        try:
            os.killpg(self.proc.pid, signal.SIGTERM)
        except OSError:
            return
        threading.Thread(target=self._nachfassen, daemon=True).start()

    def _nachfassen(self):
        try:
            self.proc.wait(ABBRUCH_WARTEN_S)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except OSError:
                pass

    def abschliessen(self):
        """Nach fertig(): Ablage schreiben. Gibt (Pfad, Daten) zurueck."""
        self.exit_code = self.proc.wait()
        self.neue_zeilen()
        try:
            self.proc.stdout.close()
        except OSError:
            pass
        ausgabe = "".join(self.zeilen)
        daten = {"name": self.name, "befehl": self.befehl, "start": self.start,
                 "ende": _jetzt_iso(), "dauer_s": round(self.verstrichen_s(), 1),
                 "exit_code": self.exit_code, "abgebrochen": self.abgebrochen,
                 "ausgabe": kuerze(ausgabe)}
        if self.auswerten:
            daten["ergebnis"] = self.auswerten(ausgabe)
        try:
            _schreib_json(self.pfad, daten)
        except OSError as e:
            daten["ablage_fehler"] = str(e)
        return self.pfad, daten


class Steuerung:
    """Hoechstens ein Lauf. Der Reiter ruft takt() alle 200 ms."""

    def __init__(self, ablage=None):
        self.ablage = ablage
        self.lauf = None

    def laeuft(self):
        return self.lauf is not None

    def starte(self, name, befehl, auswerten=None, stempel=None):
        if self.lauf is not None:
            raise RuntimeError("es läuft schon: %s" % self.lauf.name)
        self.lauf = Lauf(name, befehl, self.ablage, stempel, auswerten)
        return self.lauf

    def abbrechen(self):
        if self.lauf is not None:
            self.lauf.abbrechen()

    def takt(self):
        """(neue Zeilen, (Pfad, Daten) oder None)."""
        if self.lauf is None:
            return [], None
        neu = self.lauf.neue_zeilen()
        if not self.lauf.fertig():
            return neu, None
        ende = self.lauf.abschliessen()
        self.lauf = None
        return neu, ende

    def status(self):
        if self.lauf is None:
            return ""
        s = int(self.lauf.verstrichen_s())
        return "Backtest: %s läuft seit %d:%02d" % (self.lauf.name, s // 60, s % 60)


# --- Laufliste und Vergleich ------------------------------------------------

def lade_lauf(pfad):
    try:
        d = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) and "befehl" in d else None


def laufliste(ablage=None):
    ordner = Path(ablage or ABLAGE)
    try:
        namen = sorted((p.name for p in ordner.glob("*.json")
                        if not p.name.endswith(VORSCHAU_ENDUNG)), reverse=True)
    except OSError:
        return []
    aus = []
    for n in namen:
        d = lade_lauf(ordner / n)
        aus.append(dict(d, datei=n) if d else {"datei": n, "name": "nicht lesbar"})
    return aus


def listen_zeilen(liste):
    zeilen = []
    for d in liste:
        if "befehl" not in d:
            zeilen.append((d["datei"], "nicht lesbar", "", "", ""))
            continue
        if d.get("abgebrochen"):
            erg = "abgebrochen"
        elif d.get("exit_code") == 0:
            erg = "ok"
        else:
            erg = "Exit %s" % d.get("exit_code")
        dauer = d.get("dauer_s")
        dauer_t = ("%d:%02d" % divmod(int(dauer), 60)
                   if isinstance(dauer, (int, float)) else "")
        zeilen.append((d["datei"], d.get("name", ""), d.get("start", ""), dauer_t, erg))
    return zeilen


def _zahl(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return ("%.4f" % v).rstrip("0").rstrip(".")
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)[:80]
    return str(v)


def kennzahlen_flach(daten):
    """Replay-Ergebnis als geordnete Liste (Name, Wert); None ohne Ergebnis."""
    e = (daten or {}).get("ergebnis")
    if not isinstance(e, dict):
        return None
    aus = [(k, e[k]) for k in _KOPF if k in e]
    k = e.get("kennzahlen")
    if isinstance(k, dict):
        aus += list(k.items())
    return aus


def ergebnis_zeilen(daten):
    k = kennzahlen_flach(daten)
    if k is None:
        return [("Ergebnis", "kein Replay-Ergebnis", "", "")]
    return [(n, _fmt(v), "", "") for n, v in k]


def vergleich(a, b):
    ka, kb = kennzahlen_flach(a), kennzahlen_flach(b)
    if ka is None or kb is None:
        raise ValueError("Vergleich nur zwischen zwei Replay-Läufen mit Ergebnis")
    da, db = dict(ka), dict(kb)
    namen = [n for n, _ in ka] + [n for n, _ in kb if n not in da]
    zeilen = []
    for n in namen:
        va, vb = da.get(n), db.get(n)
        diff = _fmt(vb - va) if _zahl(va) and _zahl(vb) else ""
        zeilen.append((n, _fmt(va), _fmt(vb), diff))
    return zeilen
