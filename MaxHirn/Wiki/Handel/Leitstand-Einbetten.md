---
id: leitstand-einbetten
tags: [handel, gui, leitstand, nautilus, tkinter]
---

# Leitstand: fremde UIs als Reiter einbetten

Der Leitstand (`Agenten/Handel/leitstand.py`) ist ein `ttk.Notebook`. Jeder
Reiter ist ein `ttk.Frame` mit drei Methoden: `refresh()`, `titel_zusatz()`,
`status()`. Am 04.10.2026 sind zwei fremde Oberflächen dazugekommen.

## Die zwei Formen von GUI

| Form | Beispiel | Was beim Einbetten passiert |
|---|---|---|
| baut in ein übergebenes Widget | `OmniquantGui(root)`, `NautilusFrame(eltern)` | fast nichts: `ttk.Frame` ist ein Widget, `after()` geht darauf |
| **ist** selbst ein Fenster | `class X(tk.Tk)` | muss zerlegt werden: Inhalt in ein Frame, Fenster drumherum |

`NautilusGui(tk.Tk)` war die zweite Form. Der Umbau:

- `NautilusFrame(ttk.Frame)` — der ganze Inhalt, kein `title`/`geometry`/`minsize`/`protocol`
- `NautilusFenster(tk.Tk)` — dünner Wrapper: Titel, Größe, `WM_DELETE_WINDOW`, hostet ein Frame
- `NautilusGui` bleibt Alias auf das Fenster — sonst brechen alle Aufrufer von vor dem Umbau

**Merksatz: Fensterpflege gehört dem Fenster, nie dem Frame.** Der Fehler fällt
erst zur Laufzeit auf (Fenster im Fenster), deshalb prüft
`test_leitstand_nautilus.Trennung` das über den AST des Quelltexts statt über
einen Klick.

## Der Reiter darf den Rahmen nicht mitnehmen

`leitstand.py` importiert Nautilus **nicht**. Der Reiter lädt es zur Laufzeit
über `nautilus_gui_laden()` und fängt `ImportError`:

- Rad da → `NautilusFrame` einbetten
- Rad fehlt → eine erklärende Zeile mit der Installationsanweisung

Grund: `nautilus_trader` ist ein 326-MB-Paket. Fehlt es in einem frischen venv,
wäre ein direkter Import im Rahmen ein **toter Leitstand** — das Werkzeug nimmt
den ganzen Rahmen mit, weil eine Nebensache fehlt.

## Zwei venv, ein Rad

`nautilus_trader` lag nur in `nautilus/.venv`; der Leitstand läuft in
`Handel/.venv`. Umweg über einen Kindprozess wäre die teure Lösung gewesen
(326 MB umkopieren, Startup jedes Mal). Gemessen und gewaehlt: **das Rad auch ins
Handel-.venv installieren**. Import 1,8 s einmalig beim Leitstand-Start.

Zusaetzlich `psutil` ins `nautilus/.venv`, weil `handelszentrale` es braucht und
die Nautilus-Dateien die Zentrale nicht importieren sollen, sondern umgekehrt.

## Der `after`-Timer ist eine Leiche

Der Frame pollt seine Queue alle 120 ms mit `self.after(...)`. In einem Fenster
ist das unauffällig — beim Einbetten nicht: verschwindet der Reiter, während das
Fenster weiterlebt, feuert der Timer ins Leere und Tk meldet
`invalid command name 1776052318848_poll_queue` auf stderr.

Der Frame bindet deshalb `<Destroy>` und bricht ab:

```python
if event is not None and event.widget is not self:
    return          # nicht der eigene Abbau: Kinder sterben mit
self._abgebrochen = True
self.after_cancel(self._poll_id)
```

Dabei wird ein **laufender Node mitgestoppt**. Sonst bliebe er als Waise zurück
und hielte den Prozess.

## Merksatz: ein Reiter darf den Rahmen nicht sperren

`abbrechbar()` ist Teil der Reiter-Schnittstelle. Solange ein Node laeuft, gibt
der Nautilus-Reiter `False` zurueck — der Leitstand fragt das vor dem Schliessen
und verweigert es mit einer Meldung. Ein Werkzeug, das im Hintergrund einen
Börsen-Node hält, darf den Nutzer nicht durch ein X zerstoeren.

## Nachweis (04.10.2026)

- 14/14 neu: `test_leitstand_nautilus` (10) + `test_leitstand_nautilus_echt` (4)
- Leitstand-Suite 214/214
- **Echter Lauf aus dem Reiter:** `Quote BTC-USDT-SWAP.OKX bid=85397.40` nach 2,0 s
- Reitertitel zeigt `●`, Statusleiste `Nautilus: Node läuft (OKX DEMO)`, `abbrechbar()` = `False`

Vorbestehend rot (per Stash belegt, nicht von dieser Arbeit):
`nautilus/test_credentials.py`, 3 Fehler (`KeyError: 'OKX'`) — auch ohne die
Aenderung an `nautilus_gui.py`.

## Dateienden

`nautilus/` ist ein **eigenes Git-Repo** mit `core.autocrlf=true`, aber die
Dateien sind als **LF** versioniert. `git stash`/`git checkout` dort dreht die
Arbeitskopie auf CRLF — der Diff wird dann unlesbar groß. Nach jedem
`git`-Befehl in diesem Repo prüfen:

```bash
python -c "b=open('nautilus_gui.py','rb').read(); print(b.count(b'\r\n'), b.count(b'\n'))"
```

und bei CRLF mit `b.replace(b'\r\n', b'\n')` zurückdrehen, dann
`git diff --numstat` kontrollieren.
