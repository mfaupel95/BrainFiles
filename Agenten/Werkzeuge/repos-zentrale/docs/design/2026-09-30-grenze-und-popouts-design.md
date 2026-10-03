# Grenze ziehen und Popouts abstellen — Design

Datum: 30.09.2026 · Status: **zur Pruefung** (noch kein Code) · Auftrag: Max
("code und struktur ueberall optimieren, wieder viele popouts"), Umfang A.

## 1. Der Befund, der das ausgeloest hat

**Popouts.** `repos_zentrale.py` startet Terminal-, Bot- und Befehls-Aktionen mit
`wt.exe` — und Windows Terminal oeffnet pro Aufruf ein **neues Fenster**. Vier
Stellen bauen diesen Aufruf:

| Stelle | Was |
|---|---|
| `aktionen.argv_terminal` (Z. 40) | "Terminal" im Projektordner |
| `aktionen.argv_befehl_im_terminal` (Z. 110) | Befehlszeile der Zeile, `cmd.exe /k` haelt sie offen |
| `aktionen.argv_bot_auftrag` (Z. 119) | Bot-Einzelauftrag |
| `fenster.bot_chat` (Z. 689) | Bot-Chat, baut den `wt`-Aufruf **inline** (nicht ueber aktionen) |

Gemessen am 30.09.2026: `WindowsTerminal.exe` (PID 17496) hielt **8 sichtbare
Fenster** ("hermes", "BRAINFILES", "npm prefix", 3x `…scanner\.venv\Scripts\
python.exe`, `…tools\python-3.14.7…`, "Claude"); in einem lief noch
`hermes -p fomo-radar chat`. Nichts davon ist kaputt — es sammelt sich nur an,
weil kein Aufruf je ein Fenster zurueckgibt und keiner ein vorhandenes benutzt.

**Struktur.** Die Grenze zwischen *unserem Code* und *Fremd-Material im eigenen
Baum* ist nirgends gezogen:

| Ort | Dateien | Zeilen |
|---|---|---|
| `Agenten/Handel` gesamt | 986 | 634.815 |
| davon `Agenten/Handel/OpenAlice` | 482 | **513.266** (81 %) |
| unser Handelscode (ohne OpenAlice) | 508 | 122.253 |
| `Agenten/MCP-Server` (fast nur Fremd-Klone) | 391 | 231.282 |
| `Agenten/Hermes/scripts` · `Werkzeuge` · `Routinen` · `Bus` | 90/41/64/25 | 14.836 / 8.956 / 6.977 / 4.572 |

Weitere Messungen: **147 byte-identische Dateigruppen** ab 2 kB, fast alle
OpenAlice-Run-Snapshots (38x `candidate.py`, 26x `factor_diagnostics.py`).
**TODO/FIXME/HACK: 7 Dateien, 5 davon fremd** — unser Code traegt keine
Merker-Schuld. 389 Testdateien / 128.470 Zeilen (14 %).

Die Folge ist nicht Aesthetik: **jede Bestandsfrage kostet eine Messung wie
diese.** Wer "wie gross ist unser Handelssystem" fragt, bekommt 634.815 Zeilen
und muss OpenAlice im Kopf abziehen. Werkzeuge, die zaehlen oder suchen
(`bestand`, `fundus-suche.ps1`, die Zentrale, `repos-updaten.py`), haben je
eigene, verstreute Vorstellungen davon, was dazugehoert.

**Gegenprobe, die fast schiefging.** Sieben Spuren `klassik_*` (bollinger,
donchian, donchian_trend, ema, macd, rsi, rsi2, sma) haben **keine** Tests und
lagen als `??` im Baum — ein Verdacht auf Fremd-Material. Nachgesehen: angelegt
am 30.09.2026 17:05, in `dauerlauf.SPUREN` eingetragen, aufgebaut auf
`Handel/klassik_regeln.py`. **Unser Code.** Genau diese Verwechslung soll die
Liste unmoeglich machen: die Grenze wird *nachgesehen*, nicht geraten.

## 2. Was "fremd" heisst (die Definition)

Fremd ist Material, das **wir nicht pflegen**: ein Klon, ein Import, ein
Fremdprojekt im eigenen Baum. Kriterium ist nicht die Sprache, die Groesse oder
die Qualitaet, sondern die Frage: *aendern wir es, oder benutzen wir es?*

Drei Regeln, die daraus folgen:

1. **Fremdes wird nicht gezaehlt.** Bestand, Umfang, Testquote, Doppelungen
   laufen ohne es — mit einem Schalter, um es dazuzunehmen.
2. **Fremdes wird nicht aufgeraeumt.** Kein Umbenennen, kein Verschieben, kein
   Loeschen, kein "Verbessern" in fremden Baeumen (gilt schon fuer die Klone).
3. **Fremdes wird nicht verschwiegen.** Die Zentrale zeigt es als Zeile mit der
   Rolle `Fremdprojekt` und der Herkunft — man soll es finden, nur nicht
   mitzaehlen.

Nicht fremd sind: neue eigene Spuren, eigene Werkzeuge, generierte
Laufzeitstaende (die sind *unser* Betrieb, nur nicht versioniert), und
`Werkstatt/Repos` als Ganzes (das ist eine *Ablage* von Klonen, kein einzelner
Fremdbaum — sie steht schon in `repo-flotte`).

## 3. Die eine Quelle: `Agenten/FREMD-Liste.json`

JSON, weil beide Welten sie lesen koennen (Python und PowerShell) — dasselbe
Muster wie `Agenten/MCP-Manifest.json` + `mcp-sync-check.ps1`.

```json
{
  "fassung": 1,
  "stand": "2026-09-30",
  "eintraege": [
    {
      "pfad": "Agenten/Handel/OpenAlice",
      "art": "Fremdprojekt",
      "herkunft": "Klon eines fremden Quant-Frameworks (eigene workspaces/runs)",
      "regel": "nur lesen",
      "warum": "81 % der Zeilen in Agenten/Handel; eigene AGENTS.md sagt: nur lesen, wenn die Aufgabe ausdruecklich OpenAlice betrifft"
    }
  ]
}
```

Regeln fuer die Datei selbst:

- `pfad` ist **relativ zur BrainFiles-Wurzel**, mit `/`, ohne `..` — kein
  absoluter Pfad (Portabilitaet).
- Kein Eintrag darf einen anderen enthalten (kein Baum im Baum) — der Pruefer
  meldet es.
- Kein Eintrag darf einen Pfad nennen, den `quellen.py` als eigene Wurzel
  fuehrt — sonst waere "fremd" und "unser" gleichzeitig wahr.
- Der Eintrag ist **kein Manifest**: er beschreibt Herkunft und Regel, er
  ersetzt nicht die Zentrale.

## 4. Der Leser: `Agenten/Werkzeuge/fremd.py`

Nur Standardbibliothek, keine Abhaengigkeiten, wie die uebrigen Haus-Werkzeuge.

```python
# Die Wurzel wird aus __file__ bestimmt (Agenten/Werkzeuge/fremd.py -> drei
# Ebenen hoch) - keine absoluten Pfade, damit der Umzug auf eine SSD nichts
# bricht. Derselbe Weg wie in fenster_design.py.
def wurzel() -> Path: ...
def liste_pfad(wurzel: Path | None = None) -> Path: ...   # <wurzel>/Agenten/FREMD-Liste.json

@dataclass(frozen=True)
class Fremd:
    pfad: str          # "Agenten/Handel/OpenAlice"
    art: str
    herkunft: str
    regel: str
    warum: str

def laden(wurzel: Path | None = None) -> list[Fremd]
def ist_fremd(rel_pfad: str, eintraege=None) -> Fremd | None   # laengster Treffer gewinnt
def ohne_fremd(pfade, eintraege=None) -> list
def pruefen(wurzel: Path | None = None) -> list[str]           # Befunde, leer = gesund
```

`ist_fremd` vergleicht **auf Pfadgrenzen** (`Agenten/Handel/OpenAlice` trifft
`Agenten/Handel/OpenAlice/…`, aber nicht `Agenten/Handel/OpenAlice2`), nimmt bei
mehreren Treffern den **laengsten** (der genaueste gewinnt) und ist
gross-/kleinschreibungs-tolerant (Windows).

## 5. Wer sie benutzt

| Verbraucher | Was sich aendert |
|---|---|
| `repos-zentrale/quellen.py` | neue Funktion `fremde()`; Rolle und Herkunft eines Ordners kommen aus der Liste (statt aus `KURATIERT` gepflegt zu werden) |
| `repos-zentrale/fuellen.py` | `KURATIERT` verliert die Fremd-Eintraege, die aus der Liste kommen — eine Quelle, nicht zwei |
| `repos-zentrale/fenster.py` | Statuszeile nennt bei einem fremden Projekt "fremd — nur lesen"; Zaehlung im Kopf ohne Fremde |
| `Agenten/Werkzeuge/bestand.py` (neu, aus dem Pruefskript) | `--mit-fremd` zeigt beide Zahlen; Standard ohne |
| `Agenten/Werkzeuge/fundus-suche.ps1` | liest die Liste und meldet fremde Baeume getrennt (heute durchsucht es `Werkstatt/Repos` und `MaxHirn/skills` nach eigenem Wissen) |
| `Agenten/Hermes/scripts/systempruefung.ps1` | ein Block "Grenze": Liste lesbar, Eintraege vorhanden, keine Ueberschneidung |

`FREMD.md` daneben ist die **lesbare** Fassung fuer Max (Tabelle: Pfad, Was,
Herkunft, Regel) — geschrieben von Hand, geprueft gegen die JSON von
`fremd.pruefen()` plus einem Test, der beide auf dieselbe Pfadmenge prueft.
Damit gibt es keine zweite Wahrheit, sondern eine Quelle und eine Anzeige.

## 6. Die Popout-Reparatur

**Ein neues Fenster nur, wenn keins da ist.** `wt.exe` bekommt ueberall
`-w 0` vorangestellt: das oeffnet einen **Tab im vorhandenen** Fenster
(Windows-Terminal-Schalter `-w <nummer|name|new|last>`; `0` = das erste
Fenster). Ohne vorhandenes Fenster legt `wt` eines an — genau das gewuenschte
Verhalten.

| Stelle | vorher | nachher |
|---|---|---|
| `argv_terminal` | `wt -d <pfad>` | `wt -w 0 -d <pfad>` |
| `argv_befehl_im_terminal` | `wt -d <pfad> cmd /k <cmd>` | `wt -w 0 -d <pfad> cmd /k <cmd>` |
| `argv_bot_auftrag` | `wt -d <pfad> hermes …` | `wt -w 0 -d <pfad> hermes …` |
| `fenster.bot_chat` | inline `wt -d <cwd> hermes …` | ueber `aktionen.argv_bot_chat(bot, pfad)` — **kein vierter Bauplatz** |

`argv_bot_chat` ist neu und liegt neben `argv_bot` (das den nackten Befehl ohne
Terminal liefert). Der Name ist bewusst anders als `argv_bot_auftrag`: der eine
ist der Chat, der andere der Einzelauftrag mit `-q`.

`cmd.exe /k` **bleibt**: die Ausgabe eines Befehls soll lesbar bleiben, das war
der Grund fuer `/k`. Der Tab ist der Ort, der Preis ist der Verzicht auf ein
eigenes Fenster je Klick.

**Der Schalter ist gemessen** (30.09.2026, `wt_probe.ps1`): Fensterzahl 1, dann
`wt -w 0 -d <ordner> cmd /c exit`, danach Fensterzahl 1 — **kein neues Fenster**,
der Aufruf landet als Tab im vorhandenen. Damit ist `-w 0` kein Zitat aus der
Doku, sondern ein eigener Beleg. Ohne vorhandenes Fenster legt `wt` eines an;
auch das bleibt zu pruefen, wenn der Fall eintritt (dann ist ein Fenster
richtig, nicht falsch).

Zusaetzlich in `fenster.py`: eine **Zeile in der Statusleiste** zeigt, wie viele
Terminal-Fenster offen sind (Zahl aus `Get-Process WindowsTerminal`), damit
"wieder viele popouts" messbar ist statt gefuehlt. Kein Aufraeum-Knopf: Fenster
schliessen ist Handarbeit (in einem laeuft womoeglich ein Bot-Auftrag).

## 7. Tests (Regeln, nicht Staende)

`tests/test_fremd.py`
1. `ist_fremd` trifft auf Pfadgrenzen — `…/OpenAlice` ja, `…/OpenAlice2` nein.
2. Bei zwei Treffern gewinnt der laengste Eintrag.
3. `pruefen()` meldet: fehlender Ordner, Eintrag im Eintrag, Eintrag in eigener
   Wurzel, absoluter Pfad, `..` im Pfad.
4. **Gegenprobe:** die acht `klassik_*`-Spuren sind NICHT fremd (der Fall, der
   fast falsch gelaufen waere).
5. `FREMD.md` und `FREMD-Liste.json` nennen dieselbe Pfadmenge.

`tests/test_aktionen.py` (besteht, wird erweitert)
6. Jeder gebaute `wt`-Aufruf traegt `-w` — kein Bauplatz ohne Fensterwahl.
7. `argv_bot_im_terminal` ist die **einzige** Stelle, die einen Bot im Terminal
   baut (Quelltextpruefung, damit kein vierter Bauplatz entsteht).

`Agenten/Werkzeuge/tests/test_bestand.py`
8. Standard zaehlt ohne Fremde, `--mit-fremd` mit — an einem Attrappen-Baum.

## 8. Belege (wie das Ergebnis gezeigt wird)

- **Popouts:** Fensterzahl vor/nach einem echten Klick auf "Terminal"
  (`fenster_wer.ps1`, zaehlt sichtbare Fenster) — vorher +1, nachher +0.
- **Grenze:** `bestand.py` nennt beide Zahlen ("ohne Fremde: 508 Dateien /
  122.253 Zeilen · mit: 986 / 634.815") — dieselbe Messung wie in Abschnitt 1.
- **Liste:** `fremd.py --pruefen` (gesund) und der Systempruefungs-Block.
- **Tests:** `unittest discover` in Zentrale, Werkzeuge und die Bus-Suite
  (unveraendert gruen).

## 9. Nicht im Umfang (YAGNI)

- **Kein Umzug** von OpenAlice oder den Fremd-Klonen (Ansatz B, abgelehnt).
- **Kein Refactoring** der 30 `handeln.py` (xperp 1487 Zeilen ist die dickste).
- **Keine Tests fuer die acht `klassik_*`-Spuren** — eigener Auftrag; sie sind
  ungetrackt im Baum (`??`), das gehoert zuerst gesichert.
- **Kein Aufraeum-Knopf** fuer Terminal-Fenster, kein Prozess-Abschuss.
- Die Liste wird **nicht** automatisch gefuellt: ein Fremd-Eintrag ist eine
  Aussage ueber Herkunft, die ein Mensch trifft.

## 10. Risiken und Rueckweg

| Risiko | Antwort |
|---|---|
| `wt -w 0` verhaelt sich anders als dokumentiert | vor dem Umbau **einmal gemessen** (Fensterzahl vor/nach einem Tab-Aufruf); Verhalten ist der Beleg, nicht die Doku |
| Ein Verbraucher liest die Liste falsch und zaehlt ploetzlich nichts | `bestand.py` zeigt beide Zahlen; die Testgegenprobe (4) prueft den Hauscode |
| Zweite Wahrheit zwischen `FREMD.md` und JSON | Test 5 vergleicht die Pfadmengen |
| Popout-Fix macht die Ausgabe unlesbar | `/k` bleibt, nur der Ort wechselt vom Fenster zum Tab |

Rueckweg: die Aenderung ist additiv (neue Dateien) bis auf `aktionen.py`,
`fenster.py` und die drei Verbraucher — je Datei ein `git checkout` genuegt.