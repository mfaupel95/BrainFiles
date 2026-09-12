# Telegram-Bus — Umsetzungsplan (Teilprojekt 1: Bus und Anbindung)

> **Für agentische Arbeiter:** ERFORDERLICHE UNTER-SKILL:
> `superpowers:subagent-driven-development` (empfohlen) oder
> `superpowers:executing-plans`, um diesen Plan Aufgabe für Aufgabe
> umzusetzen. Die Schritte tragen Kästchen (`- [ ]`) zum Abhaken.

**Ziel:** Jeder Agent, jeder Bot und jede Routine meldet Start und Ende an
einen lokalen Dienst; der Dienst schreibt das ins Journal und schickt über
Telegram nur, was auffällig ist.

**Aufbau:** Ein Python-Dienst auf `127.0.0.1:8787` nimmt Ereignisse per
`POST /ereignis` entgegen, hängt sie an `Agenten/Bus/journal/JJJJ-MM-TT.jsonl`
an und flusht, bevor er sie weitergibt. Im selben Prozess läuft der Sprecher
als Faden: er liest das Journal ab einer Marke, bewertet, drosselt und ruft
`melder.py`. Erzeuger feuern mit 1 s Zeitlimit und fallen bei totem Bus auf
Direktschreiben ins Journal zurück.

**Technik:** Python 3.13, nur Standardbibliothek (`http.server`,
`urllib.request`, `json`, `threading`, `queue`). PowerShell für die Routinen.
Keine neuen Abhängigkeiten.

**Spec:** `Werkstatt/spec-telegram-bus-2026-09-09.md`

## Globale Vorgaben

Diese Punkte gelten für **jede** Aufgabe. Sie stammen wörtlich aus der Spec
und aus `CLAUDE.md`.

- `Agenten/Handel/melder.py` bleibt **unverändert**. Er wird nur aufgerufen.
- **Ein toter Bus darf niemals einen Lauf abbrechen.** Diese Regel steht über
  jeder Meldegenauigkeit. Erzeugercode wirft nie eine eigene Ausnahme.
- Der Bus führt nichts aus. Ein Ereignis annehmen ist Schreiben.
- Diese Stufe **nimmt nichts entgegen**: Der Sprecher ruft niemals
  `melder.hole()`, nur `melder.sende()`. Sonst nähme er `dauerlauf.py` die
  Telegram-Nachrichten weg — davor warnt `handel-dauerlauf.ps1` bereits.
- **Keine absoluten Pfade** in Code oder Konfiguration. Python rechnet ab
  `os.path.dirname(os.path.abspath(__file__))`, PowerShell ab `$PSScriptRoot`.
  Absolute Pfade existieren allein in der Registrierung der Aufgabenplanung.
- **Kein pytest im Projekt.** Tests sind Skripte mit reinen `assert`,
  ausführbar mit `python test_x.py`, so wie
  `Agenten/Handel/xperp/test_indikatoren.py`. Kein Netzzugriff im Test.
- Neue Dateien UTF-8, deutsche Kommentare im Ton der bestehenden Module:
  erklären *warum*, nicht *was*.
- Port: `8787`. Journalordner: `Agenten/Bus/journal/`.

## Dateien

| Datei | Verantwortung |
|---|---|
| `Agenten/Bus/journal.py` | Ereigniszeile bauen, anhängen, lesen. Sonst nichts. |
| `Agenten/Bus/bus.py` | HTTP-Annahme, PID-Sperre, Reihenfolge Schreiben→Weitergeben, startet den Sprecherfaden. |
| `Agenten/Bus/ereignis.py` | Erzeugerseite Python: `lauf()`-Kontextmanager, Rückfall. |
| `Agenten/Bus/Ereignis.ps1` | Erzeugerseite PowerShell: `Melde-Start` / `Melde-Ende`. |
| `Agenten/Bus/auffaellig.py` | Reine Bewertung: ist dieses Ereignis auffällig? |
| `Agenten/Bus/auffaellig.json` | Die Regelwerte. Kein Code. |
| `Agenten/Bus/bus.json` | `{"port": 8787}`. |
| `Agenten/Bus/sprecher.py` | Journal ab Marke lesen, entdoppeln, drosseln, `melder.sende()`, Tagesmeldung. |
| `Agenten/Bus/tests/test_*.py` | Je Modul ein Testskript. |
| `Agenten/Routinen/bus.ps1` | Registrierung der Aufgabe „bei Systemstart". |

---

### Aufgabe 1: Journal

**Dateien:**
- Anlegen: `Agenten/Bus/journal.py`
- Test: `Agenten/Bus/tests/test_journal.py`

**Schnittstellen:**
- Verbraucht: nichts.
- Liefert: `neu(wer, was, code=None, dauer_s=None, text="", log=None) -> dict`,
  `pfad(zeit=None, wurzel=None) -> str`,
  `anhaengen(ereignis, wurzel=None) -> str`,
  `lesen(tag=None, wurzel=None) -> list[dict]`.
  `wurzel` ist überall der Journalordner; `None` heißt `Agenten/Bus/journal`.
  Alle späteren Aufgaben schreiben ausschließlich über `anhaengen`.

- [ ] **Schritt 1: Den scheiternden Test schreiben**

`Agenten/Bus/tests/test_journal.py`:

```python
"""Test fuer journal.py - reine Datei-Arbeit, kein Netz.
Direkt ausfuehrbar: python tests/test_journal.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal  # noqa: E402

FELDER = {"id", "zeit", "wer", "was", "code", "dauer_s", "text", "log"}


def test_neu_hat_alle_felder():
    e = journal.neu("handel/xperp", "start")
    assert set(e) == FELDER, e
    assert e["code"] is None and e["dauer_s"] is None
    assert len(e["id"]) == 32
    # Zeitzone muss dranstehen, sonst ist die Zeile spaeter nicht sortierbar.
    assert "+" in e["zeit"] or e["zeit"].endswith("Z")


def test_ids_sind_verschieden():
    assert journal.neu("a", "start")["id"] != journal.neu("a", "start")["id"]


def test_anhaengen_und_lesen():
    with tempfile.TemporaryDirectory() as w:
        journal.anhaengen(journal.neu("routine/sicherung", "start"), wurzel=w)
        journal.anhaengen(journal.neu("routine/sicherung", "ende", code=0,
                                      dauer_s=12), wurzel=w)
        zeilen = journal.lesen(wurzel=w)
        assert len(zeilen) == 2, zeilen
        assert zeilen[1]["code"] == 0 and zeilen[1]["dauer_s"] == 12


def test_halbe_zeile_wird_uebersprungen():
    # Nach einem Stromausfall kann die letzte Zeile abgeschnitten sein.
    # Das darf das Lesen der guten Zeilen nicht verhindern.
    with tempfile.TemporaryDirectory() as w:
        journal.anhaengen(journal.neu("a", "start"), wurzel=w)
        with open(journal.pfad(wurzel=w), "a", encoding="utf-8") as f:
            f.write('{"id": "abc", "wer"\n')
        assert len(journal.lesen(wurzel=w)) == 1


def test_lesen_ohne_datei_ist_leer():
    with tempfile.TemporaryDirectory() as w:
        assert journal.lesen(wurzel=w) == []


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Journal-Tests bestanden")
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag prüfen**

```bash
cd Agenten/Bus && python tests/test_journal.py
```

Erwartet: `ModuleNotFoundError: No module named 'journal'`

- [ ] **Schritt 3: `journal.py` schreiben**

```python
"""Der einzige Ort der Wahrheit: Agenten/Bus/journal/JJJJ-MM-TT.jsonl.

Alles im Bus schreibt und liest ueber dieses Modul. Es kennt kein Netz und
keinen Melder - damit ein Erzeuger es auch dann benutzen kann, wenn der Bus
tot ist. Angehaengt wird mit fsync, weil die Spec verlangt, dass die Zeile auf
Platte steht, bevor irgendjemand sie weitergibt.
"""

import json
import os
import uuid
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HIER, "journal")


def neu(wer, was, code=None, dauer_s=None, text="", log=None):
    """Baut eine Ereigniszeile. Felder wie in der Spec, immer dieselben acht."""
    return {
        "id": uuid.uuid4().hex,
        "zeit": datetime.now().astimezone().isoformat(timespec="seconds"),
        "wer": wer,
        "was": was,
        "code": code,
        "dauer_s": dauer_s,
        "text": text,
        "log": log,
    }


def pfad(zeit=None, wurzel=None):
    z = zeit or datetime.now()
    return os.path.join(wurzel or JOURNAL, z.strftime("%Y-%m-%d") + ".jsonl")


def anhaengen(ereignis, wurzel=None):
    """Haengt eine Zeile an und erzwingt sie auf Platte. Gibt den Pfad zurueck."""
    p = pfad(wurzel=wurzel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(ereignis, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return p


def lesen(tag=None, wurzel=None):
    """Liest einen Tag. Kaputte Zeilen werden uebersprungen, nicht gemeldet -
    eine halbe Zeile nach einem Absturz darf die guten nicht mitreissen."""
    p = pfad(zeit=tag, wurzel=wurzel)
    if not os.path.exists(p):
        return []
    zeilen = []
    with open(p, encoding="utf-8") as f:
        for z in f:
            z = z.strip()
            if not z:
                continue
            try:
                zeilen.append(json.loads(z))
            except json.JSONDecodeError:
                continue
    return zeilen
```

- [ ] **Schritt 4: Test laufen lassen, Erfolg prüfen**

```bash
cd Agenten/Bus && python tests/test_journal.py
```

Erwartet: `alle Journal-Tests bestanden`

- [ ] **Schritt 5: Committen**

```bash
git add Agenten/Bus/journal.py Agenten/Bus/tests/test_journal.py && git commit -m "Bus: Journal als einziger Ort der Wahrheit"
```

---

### Aufgabe 2: Der Dienst

**Dateien:**
- Anlegen: `Agenten/Bus/bus.py`, `Agenten/Bus/bus.json`
- Test: `Agenten/Bus/tests/test_bus.py`

**Schnittstellen:**
- Verbraucht: `journal.neu`, `journal.anhaengen`, `journal.lesen` aus Aufgabe 1.
- Liefert: `port_aus_datei() -> int` (liest `bus.json`),
  `starte(port=None, wurzel=None, warteschlange=None) -> ThreadingHTTPServer`
  — bindet an `127.0.0.1`, serviert erst, wenn der Aufrufer `serve_forever()`
  ruft; `PID_DATEI`, `pid_sperren() -> bool`.
  Aufgabe 6 hängt den Sprecher an dieselbe `warteschlange` (`queue.Queue`).

  **Namensregel:** Die Funktion heißt `port_aus_datei()`, damit der Parameter
  `port` heißen darf. Nicht umbenennen — Aufgaben 3 und 9 rufen beide Namen so.

- [ ] **Schritt 1: Den scheiternden Test schreiben**

`Agenten/Bus/tests/test_bus.py`:

```python
"""Test fuer bus.py - startet den Dienst auf einem freien Port im eigenen
Prozess und redet ueber localhost mit ihm. Kein Telegram, kein Melder.
Direkt ausfuehrbar: python tests/test_bus.py
"""
import json
import os
import queue
import sys
import tempfile
import threading
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bus       # noqa: E402
import journal   # noqa: E402


def _dienst(wurzel, q):
    srv = bus.starte(port=0, wurzel=wurzel, warteschlange=q)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _post(port, nutzlast):
    req = urllib.request.Request(
        "http://127.0.0.1:%d/ereignis" % port,
        data=json.dumps(nutzlast).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as a:
        return a.status


def test_nimmt_an_und_schreibt_vor_dem_verteilen():
    with tempfile.TemporaryDirectory() as w:
        q = queue.Queue()
        srv, port = _dienst(w, q)
        try:
            e = journal.neu("handel/xperp", "ende", code=0, dauer_s=3)
            assert _post(port, e) == 200
            # Die Zeile muss auf Platte stehen, sobald die Antwort da ist -
            # das ist die Gegenmassnahme gegen einen Absturz danach.
            zeilen = journal.lesen(wurzel=w)
            assert len(zeilen) == 1 and zeilen[0]["id"] == e["id"]
            assert q.get(timeout=2)["id"] == e["id"]
        finally:
            srv.shutdown()


def test_kein_get_und_kein_fremder_pfad():
    with tempfile.TemporaryDirectory() as w:
        srv, port = _dienst(w, queue.Queue())
        try:
            for auf in ("/ereignis", "/beliebig"):
                try:
                    urllib.request.urlopen(
                        "http://127.0.0.1:%d%s" % (port, auf), timeout=3)
                    raise AssertionError("GET haette scheitern muessen")
                except urllib.error.HTTPError as f:
                    assert f.code in (404, 405), f.code
        finally:
            srv.shutdown()


def test_muell_wird_abgewiesen_ohne_absturz():
    with tempfile.TemporaryDirectory() as w:
        srv, port = _dienst(w, queue.Queue())
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:%d/ereignis" % port, data=b"kein json",
                headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=3)
                raise AssertionError("haette 400 geben muessen")
            except urllib.error.HTTPError as f:
                assert f.code == 400
            assert journal.lesen(wurzel=w) == []
            # Danach muss der Dienst weiterhin arbeiten.
            assert _post(port, journal.neu("a", "start")) == 200
        finally:
            srv.shutdown()


def test_bindet_nur_an_localhost():
    with tempfile.TemporaryDirectory() as w:
        srv, _ = _dienst(w, queue.Queue())
        try:
            assert srv.server_address[0] == "127.0.0.1"
        finally:
            srv.shutdown()


def test_port_kommt_aus_bus_json():
    assert bus.port_aus_datei() == 8787


def test_pid_sperre_laesst_keinen_zweiten_bus_zu():
    # Zwei Sprecher am selben Telegram-Token naehmen sich gegenseitig die
    # Nachrichten weg - davor warnt handel-dauerlauf.ps1 seit jeher.
    with tempfile.TemporaryDirectory() as w:
        echt, bus.PID_DATEI = bus.PID_DATEI, os.path.join(w, "bus.pid")
        try:
            assert bus.pid_sperren() is True        # wir selbst laufen
            assert bus.pid_sperren() is False       # derselbe Prozess: besetzt
            with open(bus.PID_DATEI, "w", encoding="utf-8") as f:
                f.write("999999")                   # tote PID
            assert bus.pid_sperren() is True        # Leiche blockiert nicht
        finally:
            bus.PID_DATEI = echt


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Bus-Tests bestanden")
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag prüfen**

```bash
cd Agenten/Bus && python tests/test_bus.py
```

Erwartet: `ModuleNotFoundError: No module named 'bus'`

- [ ] **Schritt 3: `bus.json` und `bus.py` schreiben**

`Agenten/Bus/bus.json`:

```json
{"port": 8787}
```

`Agenten/Bus/bus.py`:

```python
"""Der Dienst. Nimmt Ereignisse entgegen, schreibt sie fort, gibt sie weiter.

Er fuehrt nichts aus. Ein Ereignis annehmen ist Schreiben, kein Ausloesen -
deshalb braucht er auch keinen Schluessel: das Schlimmste, was ein fremder
lokaler Prozess anrichten kann, ist eine erfundene Journalzeile.

Die Reihenfolge in do_POST ist bindend und der Grund, warum dieser Dienst
ueberhaupt vertretbar ist: erst anhaengen und flushen, dann verteilen. Faellt
er dazwischen aus, steht die Zeile trotzdem auf Platte.
"""

import json
import os
import queue
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import journal

HIER = os.path.dirname(os.path.abspath(__file__))
PID_DATEI = os.path.join(HIER, "bus.pid")
GRENZE = 64 * 1024      # eine Ereigniszeile ist nie groesser


def port_aus_datei():
    with open(os.path.join(HIER, "bus.json"), encoding="utf-8") as f:
        return int(json.load(f)["port"])


def _laeuft(pid):
    try:
        a = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                           capture_output=True, text=True, timeout=10)
        return str(pid) in a.stdout
    except Exception:                                       # noqa: BLE001
        return False


def pid_sperren():
    """True, wenn wir der einzige Bus sind. Zwei Sprecher am selben Telegram-
    Token naehmen sich gegenseitig die Nachrichten weg."""
    if os.path.exists(PID_DATEI):
        try:
            with open(PID_DATEI, encoding="utf-8") as f:
                alt = int(f.read().strip())
        except (OSError, ValueError):
            alt = None
        if alt and _laeuft(alt):
            return False
    with open(PID_DATEI, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    return True


def _bauen(wurzel, warteschlange):
    class Griff(BaseHTTPRequestHandler):
        def do_POST(self):                                  # noqa: N802
            if self.path != "/ereignis":
                return self._kurz(404)
            try:
                n = int(self.headers.get("Content-Length", 0))
                if n <= 0 or n > GRENZE:
                    return self._kurz(400)
                e = json.loads(self.rfile.read(n).decode("utf-8"))
                if not isinstance(e, dict) or "id" not in e or "wer" not in e:
                    return self._kurz(400)
            except (ValueError, UnicodeDecodeError):
                return self._kurz(400)
            try:
                journal.anhaengen(e, wurzel=wurzel)          # 1. auf Platte
            except OSError:
                return self._kurz(500)
            warteschlange.put(e)                             # 2. erst dann
            self._kurz(200)

        def do_GET(self):                                   # noqa: N802
            self._kurz(405)

        def _kurz(self, code):
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_):
            pass    # kein Zugriffsprotokoll - das Journal ist das Protokoll

    return Griff


def starte(port=None, wurzel=None, warteschlange=None):
    """Bindet an 127.0.0.1. Serviert erst, wenn der Aufrufer serve_forever()
    ruft - so kann der Test den Port abfragen, bevor etwas laeuft."""
    q = warteschlange if warteschlange is not None else queue.Queue()
    p = port if port is not None else port_aus_datei()
    return ThreadingHTTPServer(("127.0.0.1", p), _bauen(wurzel, q))


def main():
    if not pid_sperren():
        print("Ein Bus laeuft bereits - dieser beendet sich.")
        return 1
    try:
        q = queue.Queue()
        srv = starte(warteschlange=q)
        _sprecher_starten(q)
        print("Bus lauscht auf 127.0.0.1:%d" % srv.server_address[1])
        srv.serve_forever()
    finally:
        try:
            os.remove(PID_DATEI)
        except OSError:
            pass
    return 0


def _sprecher_starten(q):
    """Wird in Aufgabe 6 gefuellt. Bis dahin absichtlich leer, damit der
    Dienst schon vorher von Hand pruefbar ist."""
    del q


if __name__ == "__main__":
    sys.exit(main())
```

`threading` ist erst ab Aufgabe 6 in Gebrauch — lass den Import weg, bis er
gebraucht wird, wenn dein Linter ungenutzte Importe anmerkt.

- [ ] **Schritt 4: Test laufen lassen, Erfolg prüfen**

```bash
cd Agenten/Bus && python tests/test_bus.py
```

Erwartet: `alle Bus-Tests bestanden`

- [ ] **Schritt 5: Committen**

```bash
git add Agenten/Bus/bus.py Agenten/Bus/bus.json Agenten/Bus/tests/test_bus.py && git commit -m "Bus: Dienst auf 127.0.0.1, erst schreiben dann verteilen"
```

---

### Aufgabe 3: Erzeugerseite Python

**Dateien:**
- Anlegen: `Agenten/Bus/ereignis.py`
- Test: `Agenten/Bus/tests/test_ereignis.py`

**Schnittstellen:**
- Verbraucht: `journal.neu`, `journal.anhaengen`, `bus.port_aus_datei`.
- Liefert: `melden(ereignis, port=None, wurzel=None) -> str`
  (`"bus"` / `"journal"` / `"nichts"`),
  `lauf(wer, log=None, port=None, wurzel=None)` als Kontextmanager,
  `hinweis(wer, text, port=None, wurzel=None)`.
  Aufgabe 7 benutzt ausschließlich `lauf` und `hinweis`, immer ohne `port`
  und `wurzel` — die beiden gibt es nur für den Test.

- [ ] **Schritt 1: Den scheiternden Test schreiben**

`Agenten/Bus/tests/test_ereignis.py`:

```python
"""Test fuer ereignis.py - der Bus ist hier absichtlich tot.
Die wichtigste Zusicherung der ganzen Stufe wird hier geprueft:
ein toter Bus bricht niemals einen Lauf ab.
Direkt ausfuehrbar: python tests/test_ereignis.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ereignis  # noqa: E402
import journal   # noqa: E402

TOT = 1          # dort lauscht nichts


def test_toter_bus_schreibt_selbst_und_wirft_nicht():
    with tempfile.TemporaryDirectory() as w:
        weg = ereignis.melden(journal.neu("handel/xperp", "start"),
                              port=TOT, wurzel=w)
        assert weg == "journal", weg
        assert len(journal.lesen(wurzel=w)) == 1


def test_lauf_meldet_start_und_ende():
    with tempfile.TemporaryDirectory() as w:
        with ereignis.lauf("routine/sicherung", port=TOT, wurzel=w):
            pass
        z = journal.lesen(wurzel=w)
        assert [e["was"] for e in z] == ["start", "ende"], z
        assert z[1]["code"] == 0
        assert z[1]["dauer_s"] is not None


def test_lauf_reicht_die_ausnahme_durch_und_meldet_fehler():
    with tempfile.TemporaryDirectory() as w:
        gefangen = None
        try:
            with ereignis.lauf("handel/orb", port=TOT, wurzel=w):
                raise ValueError("kaputt")
        except ValueError as f:
            gefangen = f
        # Der Aufrufer muss den Fehler weiterhin sehen - wir verschlucken nichts.
        assert isinstance(gefangen, ValueError)
        z = journal.lesen(wurzel=w)
        assert z[1]["was"] == "ende" and z[1]["code"] == 1
        assert "kaputt" in z[1]["text"]


def test_auch_unschreibbares_journal_bricht_nicht_ab():
    # Weder Bus noch Journal erreichbar: der Lauf muss trotzdem durchlaufen.
    gelaufen = False
    with ereignis.lauf("a", port=TOT, wurzel="Z:\\gibt-es-nicht\\journal"):
        gelaufen = True
    assert gelaufen


def test_hinweis_traegt_text():
    with tempfile.TemporaryDirectory() as w:
        ereignis.hinweis("handel/xperp", "SNDK ueber SuperTrend",
                         port=TOT, wurzel=w)
        z = journal.lesen(wurzel=w)
        assert z[0]["was"] == "hinweis" and z[0]["code"] is None
        assert "SNDK" in z[0]["text"]


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Ereignis-Tests bestanden")
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag prüfen**

```bash
cd Agenten/Bus && python tests/test_ereignis.py
```

Erwartet: `ModuleNotFoundError: No module named 'ereignis'`

- [ ] **Schritt 3: `ereignis.py` schreiben**

```python
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
```

- [ ] **Schritt 4: Test laufen lassen, Erfolg prüfen**

```bash
cd Agenten/Bus && python tests/test_ereignis.py
```

Erwartet: `alle Ereignis-Tests bestanden`

- [ ] **Schritt 5: Committen**

```bash
git add Agenten/Bus/ereignis.py Agenten/Bus/tests/test_ereignis.py && git commit -m "Bus: Erzeugerseite Python mit Rueckfall aufs Journal"
```

---

### Aufgabe 4: Erzeugerseite PowerShell

**Dateien:**
- Anlegen: `Agenten/Bus/Ereignis.ps1`
- Test: `Agenten/Bus/tests/test_ereignis_ps1.py`

**Schnittstellen:**
- Verbraucht: `bus.json` (Port), das Journalformat aus Aufgabe 1.
- Liefert: `Melde-Start -Wer <string> [-Log <string>]` → Objekt mit `Wer`,
  `Start` (DateTime), `Log`;
  `Melde-Ende -Marke <object> [-Code <int>] [-Text <string>]`;
  `Melde-Hinweis -Wer <string> -Text <string>`.
  Aufgabe 8 benutzt genau diese Aufrufe.

- [ ] **Schritt 1: Den scheiternden Test schreiben**

`Agenten/Bus/tests/test_ereignis_ps1.py`:

```python
"""Test fuer Ereignis.ps1 - ruft PowerShell wirklich auf, mit totem Bus,
und prueft, was danach im Journal steht.
Direkt ausfuehrbar: python tests/test_ereignis_ps1.py
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal  # noqa: E402

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS1 = os.path.join(BUS, "Ereignis.ps1")


def _ps(skript, wurzel):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
         "$env:BUS_JOURNAL='%s'; $env:BUS_PORT='1'; . '%s'; %s"
         % (wurzel.replace("'", "''"), PS1.replace("'", "''"), skript)],
        capture_output=True, text=True, timeout=60)


def test_start_und_ende_landen_im_journal():
    with tempfile.TemporaryDirectory() as w:
        a = _ps("$m = Melde-Start -Wer 'routine/sicherung'; "
                "Melde-Ende -Marke $m -Code 0", w)
        assert a.returncode == 0, a.stderr
        z = journal.lesen(wurzel=w)
        assert [e["was"] for e in z] == ["start", "ende"], z
        assert z[1]["code"] == 0 and z[1]["wer"] == "routine/sicherung"


def test_fehlercode_kommt_durch():
    with tempfile.TemporaryDirectory() as w:
        _ps("$m = Melde-Start -Wer 'routine/zweitkopie'; "
            "Melde-Ende -Marke $m -Code 11 -Text 'robocopy 11'", w)
        z = journal.lesen(wurzel=w)
        assert z[1]["code"] == 11 and "robocopy" in z[1]["text"]


def test_toter_bus_bricht_das_skript_nicht_ab():
    # Genau der Fall aus der Spec: der Lauf muss weiterlaufen.
    with tempfile.TemporaryDirectory() as w:
        a = _ps("$ErrorActionPreference='Stop'; "
                "$m = Melde-Start -Wer 'a'; Write-Output 'weiter'", w)
        assert a.returncode == 0, a.stderr
        assert "weiter" in a.stdout


def test_log_pfad_wird_uebernommen():
    with tempfile.TemporaryDirectory() as w:
        _ps("$m = Melde-Start -Wer 'routine/sicherung' "
            "-Log 'Agenten/Routinen/logs/sicherung-letzter-lauf.log'; "
            "Melde-Ende -Marke $m -Code 0", w)
        z = journal.lesen(wurzel=w)
        assert z[1]["log"].endswith("sicherung-letzter-lauf.log"), z[1]


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Ereignis.ps1-Tests bestanden")
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag prüfen**

```bash
cd Agenten/Bus && python tests/test_ereignis_ps1.py
```

Erwartet: Fehlschlag, weil `Ereignis.ps1` nicht existiert (das Punkt-Einbinden
scheitert, `Melde-Start` ist unbekannt)

- [ ] **Schritt 3: `Ereignis.ps1` schreiben**

```powershell
# Erzeugerseite fuer die Routinen. Wird mit Punkt eingebunden:
#
#   . (Join-Path $wurzel 'Bus\Ereignis.ps1')
#   $marke = Melde-Start -Wer 'routine/sicherung' -Log $relativerLogPfad
#   ... eigentliche Arbeit ...
#   Melde-Ende -Marke $marke -Code $code
#
# Die Regel ueber allen anderen: ein toter Bus darf niemals einen Lauf
# abbrechen. Deshalb steht in jeder Funktion ein try/catch um alles, und
# $ErrorActionPreference wird waehrenddessen auf 'Continue' gesetzt - sonst
# reisst ein 'Stop' aus dem aufrufenden Skript den Melder mit hinein.
#
# Pfade sind relativ zu diesem Skript. BUS_JOURNAL und BUS_PORT gibt es nur
# fuer den Test.

$BusWurzel = $PSScriptRoot

function Get-BusPort {
  if ($env:BUS_PORT) { return [int]$env:BUS_PORT }
  try {
    return [int]((Get-Content (Join-Path $BusWurzel 'bus.json') -Raw |
                  ConvertFrom-Json).port)
  } catch { return 0 }
}

function Get-BusJournal {
  if ($env:BUS_JOURNAL) { return $env:BUS_JOURNAL }
  return (Join-Path $BusWurzel 'journal')
}

function Send-BusEreignis {
  param([hashtable]$Ereignis)
  $alt = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $roh  = $Ereignis | ConvertTo-Json -Compress -Depth 4
    $port = Get-BusPort
    if ($port -gt 0) {
      try {
        Invoke-RestMethod -Uri "http://127.0.0.1:$port/ereignis" -Method Post `
          -Body $roh -ContentType 'application/json' -TimeoutSec 1 | Out-Null
        return
      } catch { }
    }
    try {
      $ordner = Get-BusJournal
      if (-not (Test-Path $ordner)) {
        New-Item -ItemType Directory -Path $ordner -Force | Out-Null
      }
      $datei = Join-Path $ordner ((Get-Date).ToString('yyyy-MM-dd') + '.jsonl')
      Add-Content -Path $datei -Value $roh -Encoding UTF8
    } catch { }
  } catch { } finally { $ErrorActionPreference = $alt }
}

function New-BusEreignis {
  param([string]$Wer, [string]$Was, $Code, $Dauer, [string]$Text, $Log)
  return @{
    id      = [guid]::NewGuid().ToString('N')
    zeit    = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
    wer     = $Wer
    was     = $Was
    code    = $Code
    dauer_s = $Dauer
    text    = $Text
    log     = $Log
  }
}

function Melde-Start {
  param([Parameter(Mandatory)][string]$Wer, [string]$Log)
  Send-BusEreignis (New-BusEreignis -Wer $Wer -Was 'start' -Code $null `
                    -Dauer $null -Text '' -Log $Log)
  return [pscustomobject]@{ Wer = $Wer; Start = Get-Date; Log = $Log }
}

function Melde-Ende {
  param([Parameter(Mandatory)]$Marke, [int]$Code = 0, [string]$Text = '')
  $s = [int]((Get-Date) - $Marke.Start).TotalSeconds
  Send-BusEreignis (New-BusEreignis -Wer $Marke.Wer -Was 'ende' -Code $Code `
                    -Dauer $s -Text $Text -Log $Marke.Log)
}

function Melde-Hinweis {
  param([Parameter(Mandatory)][string]$Wer,
        [Parameter(Mandatory)][string]$Text)
  Send-BusEreignis (New-BusEreignis -Wer $Wer -Was 'hinweis' -Code $null `
                    -Dauer $null -Text $Text -Log $null)
}
```

Zwei Fallstricke, die beim Schreiben auffallen werden:

- `ConvertTo-Json` macht aus `$null` in einem Hashtable tatsächlich `null` —
  gut so, das Journalformat verlangt es. Prüfe es im Test mit
  `z[0]["code"] is None`.
- `Add-Content -Encoding UTF8` schreibt unter Windows PowerShell 5.1 eine
  BOM. `journal.lesen` öffnet mit `encoding="utf-8"` und stolpert darüber.
  Wenn der Test das zeigt: in `journal.lesen` auf `encoding="utf-8-sig"`
  wechseln (liest beides) und die Änderung mit dem Journal-Test absichern.

- [ ] **Schritt 4: Test laufen lassen, Erfolg prüfen**

```bash
cd Agenten/Bus && python tests/test_ereignis_ps1.py && python tests/test_journal.py
```

Erwartet: beide Testskripte melden „bestanden"

- [ ] **Schritt 5: Committen**

```bash
git add Agenten/Bus/Ereignis.ps1 Agenten/Bus/journal.py Agenten/Bus/tests/test_ereignis_ps1.py && git commit -m "Bus: Erzeugerseite PowerShell (Melde-Start/Melde-Ende)"
```

---

### Aufgabe 5: Auffälligkeit

**Dateien:**
- Anlegen: `Agenten/Bus/auffaellig.py`, `Agenten/Bus/auffaellig.json`
- Test: `Agenten/Bus/tests/test_auffaellig.py`

**Schnittstellen:**
- Verbraucht: nichts außer der eigenen Regeldatei.
- Liefert: `regeln(pfad=None) -> dict`,
  `bewerte(ereignis, historie, regeln_) -> str | None` — Grund im Klartext
  oder `None`;
  `ausbleibend(letzte_laeufe, regeln_, jetzt) -> list[str]`.
  `historie` ist die Liste der `ende`-Ereignisse **derselben** Komponente,
  älteste zuerst. `letzte_laeufe` ist `{wer: datetime}` ohne Zeitzone.

- [ ] **Schritt 1: Den scheiternden Test schreiben**

`Agenten/Bus/tests/test_auffaellig.py`:

```python
"""Test fuer auffaellig.py - reine Rechnung, kein Netz.
Direkt ausfuehrbar: python tests/test_auffaellig.py
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auffaellig  # noqa: E402

R = {"deckel_je_stunde": 20, "dauer_faktor": 2.0, "dauer_mindestlaeufe": 5,
     "erwartet": {"routine/sicherung": 30}}


def e(was, code=None, dauer=None, text=""):
    return {"id": "x", "zeit": "", "wer": "routine/sicherung", "was": was,
            "code": code, "dauer_s": dauer, "text": text, "log": None}


def hist(*dauern):
    return [e("ende", code=0, dauer=d) for d in dauern]


FAELLE = [
    # (Name, Ereignis, Historie, auffaellig?)
    ("Fehlercode meldet immer",     e("ende", code=1, dauer=3), hist(3, 3, 3, 3, 3), True),
    ("Erfolg in normaler Zeit",     e("ende", code=0, dauer=3), hist(3, 3, 3, 3, 3), False),
    ("doppelte Dauer meldet",       e("ende", code=0, dauer=7), hist(3, 3, 3, 3, 3), True),
    ("knapp darunter schweigt",     e("ende", code=0, dauer=6), hist(3, 3, 3, 3, 3), False),
    ("zu wenig Historie schweigt",  e("ende", code=0, dauer=99), hist(3, 3), False),
    ("Start ist nie auffaellig",    e("start"), hist(3, 3, 3, 3, 3), False),
    ("Hinweis ist immer auffaellig", e("hinweis", text="ATR steigt"), [], True),
]


def test_tabelle():
    for name, ereignis, historie, erwartet in FAELLE:
        grund = auffaellig.bewerte(ereignis, historie, R)
        assert bool(grund) == erwartet, "%s -> %r" % (name, grund)
        if erwartet:
            assert isinstance(grund, str) and grund, name


def test_median_nicht_mittelwert():
    # Ein einzelner Ausreisser darf die Schwelle nicht hochziehen.
    assert auffaellig.bewerte(e("ende", code=0, dauer=10),
                              hist(3, 3, 3, 3, 300), R)


def test_ausbleibender_lauf():
    jetzt = datetime(2026, 9, 9, 12, 0)
    spaet = {"routine/sicherung": jetzt - timedelta(hours=40)}
    puenktlich = {"routine/sicherung": jetzt - timedelta(hours=2)}
    assert auffaellig.ausbleibend(spaet, R, jetzt) == ["routine/sicherung"]
    assert auffaellig.ausbleibend(puenktlich, R, jetzt) == []
    # Nie gelaufen ist auch ausgeblieben.
    assert auffaellig.ausbleibend({}, R, jetzt) == ["routine/sicherung"]


def test_regeln_datei_ist_lesbar():
    r = auffaellig.regeln()
    for schluessel in ("deckel_je_stunde", "dauer_faktor",
                       "dauer_mindestlaeufe", "erwartet"):
        assert schluessel in r, r


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Auffaelligkeits-Tests bestanden")
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag prüfen**

```bash
cd Agenten/Bus && python tests/test_auffaellig.py
```

Erwartet: `ModuleNotFoundError: No module named 'auffaellig'`

- [ ] **Schritt 3: `auffaellig.json` und `auffaellig.py` schreiben**

`Agenten/Bus/auffaellig.json` — die Werte stehen bewusst hier und nicht im
Code, damit sie ohne Codeänderung nachgezogen werden können. `erwartet` ist
`wer` → höchstens so viele Stunden ohne Lauf.

```json
{
  "deckel_je_stunde": 20,
  "dauer_faktor": 2.0,
  "dauer_mindestlaeufe": 5,
  "erwartet": {
    "routine/sicherung": 30,
    "routine/zweitkopie": 30,
    "routine/systempruefung": 30
  }
}
```

`Agenten/Bus/auffaellig.py`:

```python
"""Entscheidet, was das Handy erreicht. Reine Rechnung, damit die Regel
pruefbar bleibt - die Werte selbst stehen in auffaellig.json.

Der Median statt des Mittelwerts ist Absicht: ein einzelner langer Lauf soll
die Schwelle nicht so weit hochziehen, dass danach nichts mehr auffaellt.
"""

import json
import os
import statistics

HIER = os.path.dirname(os.path.abspath(__file__))


def regeln(pfad=None):
    with open(pfad or os.path.join(HIER, "auffaellig.json"),
              encoding="utf-8") as f:
        return json.load(f)


def bewerte(ereignis, historie, regeln_):
    """Gibt den Grund im Klartext zurueck - oder None fuer 'still sammeln'."""
    was = ereignis.get("was")
    if was == "hinweis":
        return "Hinweis: %s" % (ereignis.get("text") or "ohne Text")
    if was != "ende":
        return None
    if ereignis.get("code"):
        return "Ergebniscode %s" % ereignis["code"]
    dauer = ereignis.get("dauer_s")
    frueher = [e["dauer_s"] for e in historie
               if e.get("was") == "ende" and isinstance(e.get("dauer_s"), int)]
    if dauer is None or len(frueher) < int(regeln_["dauer_mindestlaeufe"]):
        return None
    mitte = statistics.median(frueher[-10:])
    if mitte > 0 and dauer > mitte * float(regeln_["dauer_faktor"]):
        return "Dauer %s s statt sonst rund %s s" % (dauer, int(mitte))
    return None


def ausbleibend(letzte_laeufe, regeln_, jetzt):
    """Wer laenger nicht gelaufen ist, als er duerfte."""
    offen = []
    for wer, stunden in sorted(regeln_.get("erwartet", {}).items()):
        letzter = letzte_laeufe.get(wer)
        if letzter is None or (jetzt - letzter).total_seconds() > stunden * 3600:
            offen.append(wer)
    return offen
```

- [ ] **Schritt 4: Test laufen lassen, Erfolg prüfen**

```bash
cd Agenten/Bus && python tests/test_auffaellig.py
```

Erwartet: `alle Auffaelligkeits-Tests bestanden`

- [ ] **Schritt 5: Committen**

```bash
git add Agenten/Bus/auffaellig.py Agenten/Bus/auffaellig.json Agenten/Bus/tests/test_auffaellig.py && git commit -m "Bus: Auffaelligkeitsregeln als pruefbare Rechnung"
```

---

### Aufgabe 6: Der Sprecher

**Dateien:**
- Anlegen: `Agenten/Bus/sprecher.py`
- Ändern: `Agenten/Bus/bus.py` (`_sprecher_starten` füllen)
- Test: `Agenten/Bus/tests/test_sprecher.py`

**Schnittstellen:**
- Verbraucht: `journal.lesen`, `auffaellig.bewerte`, `auffaellig.regeln`,
  `auffaellig.ausbleibend`; `melder.sende(text, stumm=False)` aus
  `Agenten/Handel/melder.py` — **unverändert**, nur gerufen.
- Liefert: `Sprecher(melder, regeln, wurzel=None, stand=None)` mit
  `verarbeite(ereignis) -> bool` (True = gesendet), `nachholen()`,
  `tagesmeldung() -> str`, `lauf(warteschlange)`.
  `melder` ist absichtlich ein Parameter: der Test übergibt einen
  Doppelgänger, der protokolliert statt zu senden.

- [ ] **Schritt 1: Den scheiternden Test schreiben**

`Agenten/Bus/tests/test_sprecher.py`:

```python
"""Test fuer sprecher.py - gegen einen Melder-Doppelgaenger, der statt zu
senden protokolliert. Kein Telegram, kein Token.
Direkt ausfuehrbar: python tests/test_sprecher.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal   # noqa: E402
import sprecher  # noqa: E402

R = {"deckel_je_stunde": 3, "dauer_faktor": 2.0, "dauer_mindestlaeufe": 5,
     "erwartet": {}}


class Doppelgaenger:
    """Sieht aus wie melder.py, sendet aber nichts."""

    def __init__(self):
        self.gesendet = []

    def sende(self, text, stumm=False):
        self.gesendet.append(text)
        return True


def _sprecher(d, w):
    return sprecher.Sprecher(d, R, wurzel=w, stand=os.path.join(w, "stand.json"))


def test_fehler_wird_gemeldet_erfolg_nicht():
    with tempfile.TemporaryDirectory() as w:
        d = Doppelgaenger()
        s = _sprecher(d, w)
        assert s.verarbeite(journal.neu("a", "ende", code=0, dauer_s=1)) is False
        assert s.verarbeite(journal.neu("a", "ende", code=7, dauer_s=1)) is True
        assert len(d.gesendet) == 1
        assert "7" in d.gesendet[0] and "a" in d.gesendet[0]


def test_entdopplung_ueber_id():
    with tempfile.TemporaryDirectory() as w:
        d = Doppelgaenger()
        s = _sprecher(d, w)
        e = journal.neu("a", "ende", code=7, dauer_s=1)
        assert s.verarbeite(e) is True
        assert s.verarbeite(e) is False      # dieselbe id kommt nicht zweimal
        assert len(d.gesendet) == 1


def test_deckel_greift():
    with tempfile.TemporaryDirectory() as w:
        d = Doppelgaenger()
        s = _sprecher(d, w)
        for _ in range(10):
            s.verarbeite(journal.neu("a", "ende", code=7, dauer_s=1))
        # Drei Meldungen plus genau eine Notiz, dass jetzt gedeckelt wird.
        assert len(d.gesendet) == 4, d.gesendet
        assert "gedeckelt" in d.gesendet[-1].lower()


def test_nachholen_ab_der_marke():
    with tempfile.TemporaryDirectory() as w:
        stand = os.path.join(w, "stand.json")
        for code in (0, 5):
            journal.anhaengen(journal.neu("a", "ende", code=code, dauer_s=1),
                              wurzel=w)
        d1 = Doppelgaenger()
        sprecher.Sprecher(d1, R, wurzel=w, stand=stand).nachholen()
        assert len(d1.gesendet) == 1
        # Neustart: dieselbe Zeile darf nicht noch einmal kommen.
        d2 = Doppelgaenger()
        sprecher.Sprecher(d2, R, wurzel=w, stand=stand).nachholen()
        assert d2.gesendet == []


def test_tagesmeldung_listet_alle_laeufe():
    with tempfile.TemporaryDirectory() as w:
        for wer in ("routine/sicherung", "handel/xperp"):
            journal.anhaengen(journal.neu(wer, "ende", code=0, dauer_s=4),
                              wurzel=w)
        t = _sprecher(Doppelgaenger(), w).tagesmeldung()
        assert "routine/sicherung" in t and "handel/xperp" in t


def test_totes_telegram_bricht_nichts_ab():
    class Stumm(Doppelgaenger):
        def sende(self, text, stumm=False):
            raise RuntimeError("Telegram tot")

    with tempfile.TemporaryDirectory() as w:
        s = _sprecher(Stumm(), w)
        # Darf nicht werfen - das Journal ist geschrieben, das genuegt.
        assert s.verarbeite(journal.neu("a", "ende", code=7, dauer_s=1)) is False


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Sprecher-Tests bestanden")
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag prüfen**

```bash
cd Agenten/Bus && python tests/test_sprecher.py
```

Erwartet: `ModuleNotFoundError: No module named 'sprecher'`

- [ ] **Schritt 3: `sprecher.py` schreiben**

```python
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
```

- [ ] **Schritt 4: Test laufen lassen, Erfolg prüfen**

```bash
cd Agenten/Bus && python tests/test_sprecher.py
```

Erwartet: `alle Sprecher-Tests bestanden`

- [ ] **Schritt 5: Den Sprecher im Dienst starten**

In `Agenten/Bus/bus.py` `_sprecher_starten` ersetzen und `threading` sowie
die drei Module importieren:

```python
def _sprecher_starten(q):
    """Der Sprecher laeuft als Faden im selben Prozess wie der Bus. Ein
    eigener Prozess braechte einen zweiten Telegram-Sprecher in Reichweite -
    und zwei am selben Token nehmen sich gegenseitig die Nachrichten weg."""
    import auffaellig
    import sprecher
    sys.path.insert(0, os.path.join(HIER, os.pardir, "Handel"))
    import melder                                           # noqa: E402
    s = sprecher.Sprecher(melder, auffaellig.regeln())
    threading.Thread(target=s.lauf, args=(q,), daemon=True).start()
```

`melder` wird als Modul übergeben — es hat `sende(text, stumm=False,
ziel=None)`, genau die Form, die der Doppelgänger nachbildet. Die Importe
stehen absichtlich in der Funktion: so bleiben die Modultests aus Aufgabe 2
frei von `melder.py` und brauchen keinen Telegram-Token.

- [ ] **Schritt 6: Von Hand prüfen**

```bash
cd Agenten/Bus && python bus.py
```

In einer zweiten Shell:

```bash
cd Agenten/Bus && python -c "import ereignis; ereignis.hinweis('handel/xperp','Probe vom Bus')"
```

Erwartet: Die Nachricht kommt auf dem Handy an, und die Zeile steht in
`Agenten/Bus/journal/<heute>.jsonl`. Danach den Bus mit Strg+C beenden.

- [ ] **Schritt 7: Committen**

```bash
git add Agenten/Bus/sprecher.py Agenten/Bus/bus.py Agenten/Bus/tests/test_sprecher.py && git commit -m "Bus: Sprecher meldet Auffaelliges und die Tagesmeldung"
```

---

### Aufgabe 7: Handelsspuren anbinden

**Dateien:**
- Ändern: `Agenten/Handel/dauerlauf.py`, `dca.py`, `grid.py`,
  `xperp/bot.py`, `verbesserer/auswerter.py`, das Einstiegsskript in
  `orb/` und das in `scanner/`
- Test: `Agenten/Bus/tests/test_anbindung_handel.py`

**Schnittstellen:**
- Verbraucht: `ereignis.lauf` aus Aufgabe 3.
- Liefert: nichts Neues. Die Namen in `wer` sind festgelegt:
  `handel/dauerlauf`, `handel/dca`, `handel/grid`, `handel/xperp`,
  `handel/orb`, `handel/scanner`, `handel/verbesserer`.

- [ ] **Schritt 1: Die Einstiegsskripte von orb und scanner finden**

```bash
grep -rl "__main__" Agenten/Handel/orb Agenten/Handel/scanner
```

Trag die gefundenen Dateien unten im Test-Wörterbuch `SPUREN` nach, bevor du
weitermachst. Ohne sie ist die Anbindung unvollständig und „alle Komponenten
melden" aus der Spec nicht erfüllt.

- [ ] **Schritt 2: Den scheiternden Test schreiben**

`Agenten/Bus/tests/test_anbindung_handel.py`:

```python
"""Prueft, dass jede Handelsspur den Bus wirklich ruft. Startet keinen Bot -
nur die Anbindung wird geprueft. Direkt ausfuehrbar.
"""
import os

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.join(os.path.dirname(BUS), "Handel")

# orb und scanner in Schritt 1 nachtragen.
SPUREN = {
    "dauerlauf.py": "handel/dauerlauf",
    "dca.py": "handel/dca",
    "grid.py": "handel/grid",
    os.path.join("xperp", "bot.py"): "handel/xperp",
    os.path.join("verbesserer", "auswerter.py"): "handel/verbesserer",
}


def test_jede_spur_ruft_den_bus():
    fehlt = []
    for datei, wer in SPUREN.items():
        with open(os.path.join(HANDEL, datei), encoding="utf-8") as f:
            inhalt = f.read()
        if "ereignis.lauf" not in inhalt or wer not in inhalt:
            fehlt.append(datei)
    assert not fehlt, "ohne Bus-Anbindung: %s" % fehlt


def test_orb_und_scanner_sind_nachgetragen():
    # Die Spec verlangt alle sieben Spuren. Dieser Test faellt absichtlich,
    # solange Schritt 1 nicht erledigt ist.
    assert len(SPUREN) == 7, "orb und scanner fehlen noch in SPUREN"


def test_melder_bleibt_unveraendert():
    # Die Spec verlangt das ausdruecklich. Faellt diese Zusicherung, ist die
    # Grenze verschoben worden, die melder.py selbst beschreibt.
    import subprocess
    wurzel = os.path.dirname(os.path.dirname(HANDEL))
    a = subprocess.run(["git", "log", "--oneline", "-1", "--",
                        "Agenten/Handel/melder.py"],
                       capture_output=True, text=True, cwd=wurzel)
    b = subprocess.run(["git", "status", "--porcelain", "--",
                        "Agenten/Handel/melder.py"],
                       capture_output=True, text=True, cwd=wurzel)
    assert b.stdout.strip() == "", "melder.py wurde angefasst:\n%s" % b.stdout
    del a


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Anbindungs-Tests Handel bestanden")
```

- [ ] **Schritt 3: Test laufen lassen, Fehlschlag prüfen**

```bash
cd Agenten/Bus && python tests/test_anbindung_handel.py
```

Erwartet: `AssertionError: ohne Bus-Anbindung: [...]` mit allen Dateien

- [ ] **Schritt 4: Die Anbindung einbauen**

In **jeder** der Dateien, bei den Importen. Für eine Datei direkt in
`Agenten/Handel/` (`dauerlauf.py`, `dca.py`, `grid.py`):

```python
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, "Bus"))
import ereignis                                            # noqa: E402
```

Für eine Datei eine Ebene tiefer (`xperp/bot.py`, `verbesserer/auswerter.py`,
`orb/…`, `scanner/…`) dasselbe mit `os.pardir, os.pardir, "Bus"`.
`dauerlauf.py` legt diesen `sys.path`-Griff bereits für `melder` an — halte
dich an das dortige Muster statt ein zweites zu erfinden.

Dann in `main()` den bisherigen Rumpf umschließen — Beispiel `xperp/bot.py`:

```python
def main():
    with ereignis.lauf("handel/xperp"):
        return _main()          # bisheriger Rumpf, umbenannt
```

Zwei Dinge, die dabei nicht passieren dürfen:

- Die Ausgabe der Bots ändert sich nicht. Der Bus hängt sich außen an.
- Wo ein Bot heute schon `melder.sende()` für eine echte Lagemeldung ruft
  (`dauerlauf.py`, `beobachte_live.py`, `tagesbericht.py`,
  `verbesserer/auswerter.py`), bleibt dieser Aufruf **stehen**. Der Bus
  ersetzt ihn nicht, er ergänzt ihn um Start und Ende.

- [ ] **Schritt 5: Test laufen lassen, Erfolg prüfen**

```bash
cd Agenten/Bus && python tests/test_anbindung_handel.py
```

Erwartet: `alle Anbindungs-Tests Handel bestanden`

- [ ] **Schritt 6: Einen Bot wirklich laufen lassen**

```bash
python Agenten/Handel/xperp/bot.py lage --wert SNDK
```

Erwartet: dieselbe Ausgabe wie vor der Änderung, und danach `start` und
`ende` für `handel/xperp` im heutigen Journal.

- [ ] **Schritt 7: Committen**

```bash
git add Agenten/Handel Agenten/Bus/tests/test_anbindung_handel.py && git commit -m "Handel: alle Spuren melden Start und Ende an den Bus"
```

---

### Aufgabe 8: Routinen und Sicherungen anbinden

**Dateien:**
- Ändern: alle `Agenten/Routinen/*.ps1` **außer** `einmalig-*` (erledigte
  Einzelläufe), `*-hook.ps1` (laufen im Sekundentakt) und `bus.ps1`
- Test: `Agenten/Bus/tests/test_anbindung_routinen.py`

**Schnittstellen:**
- Verbraucht: `Melde-Start` / `Melde-Ende` aus Aufgabe 4.
- Liefert: `wer` ist immer `routine/<Dateiname ohne .ps1>`.

- [ ] **Schritt 1: Den scheiternden Test schreiben**

`Agenten/Bus/tests/test_anbindung_routinen.py`:

```python
"""Prueft, dass jede geplante Routine den Bus ruft - und zwar an allen
Ausstiegen, nicht nur im Erfolgsfall. Direkt ausfuehrbar.
"""
import glob
import os

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTINEN = os.path.join(os.path.dirname(BUS), "Routinen")


def geplante():
    for p in sorted(glob.glob(os.path.join(ROUTINEN, "*.ps1"))):
        name = os.path.basename(p)
        if (name.startswith("einmalig-") or name.endswith("-hook.ps1")
                or name == "bus.ps1"):
            continue
        yield p, name[:-4]


def test_es_gibt_ueberhaupt_routinen():
    assert len(list(geplante())) >= 15, "Ordner falsch gefunden?"


def test_jede_routine_meldet():
    fehlt = []
    for p, name in geplante():
        with open(p, encoding="utf-8") as f:
            inhalt = f.read()
        if ("Ereignis.ps1" not in inhalt or "Melde-Start" not in inhalt
                or "Melde-Ende" not in inhalt
                or ("routine/" + name) not in inhalt):
            fehlt.append(name)
    assert not fehlt, "ohne Bus-Anbindung: %s" % fehlt


def test_melde_ende_steht_an_jedem_ausstieg():
    # Eine Routine, die im Fehlerfall 'exit' ruft, ohne vorher zu melden,
    # sieht im Journal wie ein ausgebliebener Lauf aus. Das ist schlimmer als
    # gar keine Anbindung, weil es einen falschen Alarm erzeugt.
    schief = []
    for p, name in geplante():
        with open(p, encoding="utf-8") as f:
            zeilen = f.readlines()
        for i, z in enumerate(zeilen):
            if z.strip().startswith("exit "):
                if "Melde-Ende" not in "".join(zeilen[max(0, i - 4):i]):
                    schief.append("%s:%d" % (name, i + 1))
    assert not schief, "exit ohne vorheriges Melde-Ende: %s" % schief


def test_keine_absoluten_pfade_dazugekommen():
    treffer = []
    for p, name in geplante():
        with open(p, encoding="utf-8") as f:
            for i, z in enumerate(f):
                if "Ereignis.ps1" in z and ":\\" in z:
                    treffer.append("%s:%d" % (name, i + 1))
    assert not treffer, "absoluter Pfad zum Bus: %s" % treffer


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Anbindungs-Tests Routinen bestanden")
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag prüfen**

```bash
cd Agenten/Bus && python tests/test_anbindung_routinen.py
```

Erwartet: `AssertionError: ohne Bus-Anbindung: [...]` mit rund zwanzig Namen

- [ ] **Schritt 3: Die Anbindung einbauen**

Muster an `Agenten/Routinen/sicherung.ps1` — so sieht die Datei danach aus.
Nur die vier markierten Zeilen sind neu, alles andere bleibt Wort für Wort
stehen:

```powershell
$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')                              # neu

$log = Join-Path $logs 'sicherung-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/sicherung' `
           -Log 'Agenten/Routinen/logs/sicherung-letzter-lauf.log'    # neu

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
try {
  & powershell -ExecutionPolicy Bypass -File (Join-Path $wurzel 'sichern.ps1') *>&1 |
    Add-Content $log -Encoding UTF8
  $code = $LASTEXITCODE
  $s = [int]((Get-Date) - $start).TotalSeconds
  if ($code -ne 0) {
    "ENDE FEHLER - Exitcode $code nach $s s" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code $code -Text "Exitcode $code"       # neu
    exit $code
  }
  "ENDE ok nach $s s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0                                    # neu
} catch {
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                         # neu
  exit 1
}
```

Vier Regeln für die übrigen Routinen:

1. Das Punkt-Einbinden steht **nach** `$wurzel = Split-Path $PSScriptRoot
   -Parent`, weil es diese Variable braucht. Nie ein absoluter Pfad.
2. `Melde-Ende` steht **vor jedem** `exit` und in **jedem** `catch`. Eine
   Routine, die still endet, sieht im Journal wie ein ausgebliebener Lauf aus
   und löst einen falschen Alarm aus.
3. Hat die Routine kein `try/catch`, bekommt sie eines — mit
   `Melde-Ende -Marke $marke -Code 1 -Text "$_"` im `catch` und `throw`
   dahinter, damit die Aufgabenplanung den Fehlschlag weiterhin sieht.
4. Der `-Log`-Pfad ist **relativ zur Vault-Wurzel** (`Agenten/Routinen/logs/…`),
   nicht die `$log`-Variable — die ist absolut. Teilprojekt 2 liest dieses
   Feld, um `/log` zu beantworten.

Die drei Sicherungsskripte `sichern.ps1`, `sichern-zweitkopie.ps1`,
`sichern-ausser-haus.ps1` werden über ihre Wrapper (`sicherung.ps1`,
`zweitkopie.ps1`) angebunden und bleiben selbst unangetastet — den
Ergebniscode reicht der Wrapper bereits durch. Das ist Absicht: die
Sicherungsskripte laufen auch von Hand, dann ohne Bus.

- [ ] **Schritt 4: Test laufen lassen, Erfolg prüfen**

```bash
cd Agenten/Bus && python tests/test_anbindung_routinen.py
```

Erwartet: `alle Anbindungs-Tests Routinen bestanden`

- [ ] **Schritt 5: Eine Routine wirklich laufen lassen**

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/systempruefung.ps1
```

Erwartet: läuft durch wie bisher; danach stehen `start` und `ende` für
`routine/systempruefung` im heutigen Journal.

- [ ] **Schritt 6: Committen**

```bash
git add Agenten/Routinen Agenten/Bus/tests/test_anbindung_routinen.py && git commit -m "Routinen: alle geplanten Laeufe melden an den Bus"
```

---

### Aufgabe 9: Betrieb und Abnahme

**Dateien:**
- Anlegen: `Agenten/Routinen/bus.ps1`, `Agenten/Bus/README.md`
- Ändern: `MaxHirn/Wissen/Routinen.md`
- Test: `Agenten/Bus/tests/test_ende_zu_ende.py`

**Schnittstellen:**
- Verbraucht: alles aus den Aufgaben 1–8.
- Liefert: die Aufgabenplanungs-Aufgabe `BrainFiles-Bus`.

- [ ] **Schritt 1: Den Ende-zu-Ende-Test schreiben**

`Agenten/Bus/tests/test_ende_zu_ende.py`:

```python
"""Nimmt die vier 'Fertig, wenn'-Punkte der Spec ab. Startet einen echten
Bus mit einem Melder-Doppelgaenger auf einem freien Port.
Direkt ausfuehrbar: python tests/test_ende_zu_ende.py
"""
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auffaellig  # noqa: E402
import bus         # noqa: E402
import ereignis    # noqa: E402
import journal     # noqa: E402
import sprecher    # noqa: E402

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Doppelgaenger:
    def __init__(self):
        self.gesendet = []

    def sende(self, text, stumm=False):
        self.gesendet.append(text)
        return True


def test_fehler_erreicht_das_handy_binnen_einer_minute():
    with tempfile.TemporaryDirectory() as w:
        q, d = queue.Queue(), Doppelgaenger()
        srv = bus.starte(port=0, wurzel=w, warteschlange=q)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        s = sprecher.Sprecher(d, auffaellig.regeln(), wurzel=w,
                              stand=os.path.join(w, "stand.json"))
        threading.Thread(target=s.lauf, args=(q,), daemon=True).start()
        try:
            ereignis.melden(journal.neu("routine/probe", "ende", code=9,
                                        dauer_s=1),
                            port=srv.server_address[1], wurzel=w)
            for _ in range(60):
                if d.gesendet:
                    break
                time.sleep(1)
            assert d.gesendet, "nichts gemeldet"
            assert "9" in d.gesendet[0]
        finally:
            srv.shutdown()


def test_toter_bus_laesst_die_routine_durchlaufen():
    with tempfile.TemporaryDirectory() as w:
        a = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command",
             "$env:BUS_JOURNAL='%s'; $env:BUS_PORT='1'; . '%s'; "
             "$m = Melde-Start -Wer 'routine/sicherung'; "
             "Start-Sleep -Milliseconds 100; "
             "Melde-Ende -Marke $m -Code 0; Write-Output 'fertig'"
             % (w.replace("'", "''"),
                os.path.join(BUS, "Ereignis.ps1").replace("'", "''"))],
            capture_output=True, text=True, timeout=60)
        assert a.returncode == 0 and "fertig" in a.stdout, a.stderr
        # Die Zeilen stehen trotzdem im Journal - das ist der ganze Punkt.
        assert len(journal.lesen(wurzel=w)) == 2


def test_alle_modultests_laufen():
    for name in ("test_journal", "test_bus", "test_ereignis",
                 "test_ereignis_ps1", "test_auffaellig", "test_sprecher",
                 "test_anbindung_handel", "test_anbindung_routinen"):
        a = subprocess.run([sys.executable,
                            os.path.join(BUS, "tests", name + ".py")],
                           capture_output=True, text=True, cwd=BUS, timeout=300)
        assert a.returncode == 0, "%s:\n%s\n%s" % (name, a.stdout, a.stderr)


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("Ende-zu-Ende bestanden")
```

- [ ] **Schritt 2: Test laufen lassen**

```bash
cd Agenten/Bus && python tests/test_ende_zu_ende.py
```

Erwartet: `Ende-zu-Ende bestanden`. Fällt etwas, ist das der Befund — nicht
den Test abschwächen, sondern die Ursache beheben.

- [ ] **Schritt 3: `Agenten/Routinen/bus.ps1` schreiben**

```powershell
# Registriert den Bus als Aufgabe 'bei Systemstart'.
#
# Register-ScheduledTask statt schtasks, weil schtasks kein 'Starten, sobald
# moeglich' setzt - siehe Wissen/Routinen.md. Einmal von Hand als
# Administrator ausfuehren; danach startet der Bus mit dem Rechner.
#
# Dies ist die einzige Stelle im ganzen Modul, die einen absoluten Pfad
# erzeugt - und sie erzeugt ihn zur Laufzeit aus $PSScriptRoot. Nach einem
# Umzug des Vaults muss dieses Skript einmal neu laufen.

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$busPy  = Join-Path $wurzel 'Bus\bus.py'
$python = (Get-Command python).Source

$aktion  = New-ScheduledTaskAction -Execute $python -Argument "`"$busPy`"" `
             -WorkingDirectory (Split-Path $busPy -Parent)
$ausloes = New-ScheduledTaskTrigger -AtStartup
$einst   = New-ScheduledTaskSettingsSet -StartWhenAvailable `
             -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) `
             -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName 'BrainFiles-Bus' -Action $aktion `
  -Trigger $ausloes -Settings $einst -RunLevel Highest -Force

Write-Output "Aufgabe 'BrainFiles-Bus' registriert: $busPy"
```

- [ ] **Schritt 4: `Agenten/Bus/README.md` schreiben**

Knapp: wozu der Bus da ist (ein Absatz), die Dateien mit je einer Zeile, wie
man ihn von Hand startet (`python bus.py`), wie man ihn registriert
(`Routinen/bus.ps1` als Administrator), wo das Journal liegt, wie man die
Tests laufen lässt (`python tests/test_ende_zu_ende.py`), und der Satz aus
der Spec: *ein toter Bus darf niemals einen Lauf abbrechen*. Ausdrücklich
dazu: **Abruf und Steuerung sind Teilprojekt 2, Deutung ist Teilprojekt 3** —
damit niemand hier danach sucht.

- [ ] **Schritt 5: `MaxHirn/Wissen/Routinen.md` ergänzen**

Eine Zeile in der Aufgabenliste: `BrainFiles-Bus` — bei Systemstart, startet
`Agenten/Bus/bus.py`, registriert über `Agenten/Routinen/bus.ps1`, Neustart
bei Fehler. Die Datei mit `Edit` ändern, **nicht** per Python-Rewrite: das
stellte die CRLF-Zeilenenden im Vault auf LF um.

- [ ] **Schritt 6: Registrieren und die vier Abnahmepunkte prüfen**

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/bus.ps1
```

Dann `Start-ScheduledTask -TaskName 'BrainFiles-Bus'` und einzeln abhaken:

1. **Alle Komponenten melden Start und Ende** — nach einem vollen Tag: das
   heutige Journal enthält jede Komponente aus dem Umfang.
2. **Ein erzwungener Fehler erscheint binnen einer Minute auf dem Handy** —
   `python -c "import sys; sys.path.insert(0,'Agenten/Bus'); import ereignis, journal; ereignis.melden(journal.neu('routine/probe','ende',code=9,dauer_s=1))"`
3. **Ein gestoppter Bus lässt einen Sicherungslauf durchlaufen** —
   `Stop-ScheduledTask -TaskName 'BrainFiles-Bus'`, dann `sicherung.ps1`
   starten: er muss durchlaufen, und die Zeile muss danach im Journal stehen.
   Bus wieder starten.
4. **Die Tagesmeldung listet alle Läufe des Tages** — abends abwarten, oder
   `Sprecher.tagesmeldung()` von Hand aufrufen und mit dem Journal vergleichen.

- [ ] **Schritt 7: Committen**

```bash
git add Agenten/Routinen/bus.ps1 Agenten/Bus/README.md MaxHirn/Wissen/Routinen.md Agenten/Bus/tests/test_ende_zu_ende.py && git commit -m "Bus: Betrieb ueber die Aufgabenplanung, Ende-zu-Ende-Abnahme"
```

---

## Was dieser Plan nicht tut

Kein `/lage`, kein `/log`, kein `/bericht`, kein Freigabefenster, keine Datei
statt Text, keine Prognosen und keine Empfehlungen. Das ist Teilprojekt 2 und
3 und bekommt je eine eigene Spec. Wer beim Umsetzen merkt, dass er dafür
„nur schnell" etwas einbaut, hat die Grenze überschritten.
