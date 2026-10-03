# Das Muster: eine JSON-Quelle, ein Leser, eine Anzeige, Verbraucher

Ausgearbeitet am 30.09.2026 an `Agenten/FREMD-Liste.json` (Grenze zwischen
eigenem Code und Fremd-Material). Die Namen sind austauschbar, die Formen nicht.

## 1. Warum JSON und nicht Python

Die Quelle wird von **zwei** Welten gelesen: Python (Werkzeuge, Tests) und
PowerShell (Routinen, Pruefskripte). Eine `.py`-Datei koennte nur die eine Seite
lesen, ein Markdown niemand maschinell. Muster im Haus:
`Agenten/MCP-Manifest.json` + `mcp-sync-check.ps1`.

## 2. Die Quelle

```json
{
  "fassung": 1,
  "stand": "2026-09-30",
  "_zweck": "Ein Satz, warum es diese Datei gibt.",
  "_regeln": ["pfad ist relativ zur Wurzel, mit '/'", "kein Eintrag enthaelt einen anderen"],
  "eintraege": [
    {"pfad": "Agenten/Handel/OpenAlice", "art": "Fremdprojekt",
     "herkunft": "Klon eines fremden Quant-Frameworks", "regel": "nur lesen",
     "warum": "482 Dateien, 513.266 Zeilen = 81 % von Agenten/Handel"}
  ]
}
```

Vier Felder sind Pflicht (`pfad`, `art`, `herkunft`, `regel`, `warum`), weil jede
Zeile im Fenster drei Fragen beantworten muss: *was ist das*, *woher*, *was tue
ich damit*. `warum` traegt die Zahl oder den Zeugen — ohne ihn ist der Eintrag
spaeter nicht mehr zu verteidigen.

Regeln, die der Leser durchsetzt: relative Pfade, `/` statt `\`, kein `..`,
kein Laufwerksbuchstabe, keine Doppelung, kein Eintrag im Eintrag, kein Eintrag,
der selbst eine Wurzel des eigenen Codes ist.

## 3. Der Leser (Standardbibliothek, per Pfad geladen)

```python
def wurzel() -> Path: ...          # aus __file__, nie aus dem Aufrufer
@dataclass(frozen=True)
class Eintrag: pfad, art, herkunft, regel, warum
def laden(wurzel=None) -> list[Eintrag]
def ist_<art>(rel_pfad, eintraege=None) -> Eintrag | None
def ohne_<art>(pfade, eintraege=None) -> list
def pruefen(wurzel=None, eigene_wurzeln=()) -> list[str]   # Befunde, leer = gesund
def als_text(wurzel=None) -> str                            # die Anzeige
```

Drei Entscheidungen, die sich bewaehrt haben:

- **Vergleich auf Pfadgrenzen**, nicht als Textanfang: `…/OpenAlice` trifft
  `…/OpenAlice/src`, aber nicht `…/OpenAlice2`. Sonst faengt jede Verlaengerung
  des Namens mit.
- **Der laengste (genaueste) Treffer gewinnt.** Bei mehreren Treffern gilt der
  spezifischste Eintrag.
- **Gross-/Kleinschreibung egal, `\` erlaubt** — Windows-Nutzer schreiben beides.

Laden ueber den PFAD (`importlib.util.spec_from_file_location`), nicht ueber
`sys.path`: ein Eintrag auf einem gemeinsamen Ordner kann gleichnamige Module
verdecken (im Haus: `Handel/` hat ein `grid.py` neben `gitter/grid.py`).

**Falle:** VOR `spec.loader.exec_module(modul)` ein
`sys.modules[<name>] = modul` setzen. Sonst bricht ein `@dataclass` im geladenen
Modul ab (`sys.modules[cls.__module__]` ist `None` →
`AttributeError: 'NoneType' object has no attribute '__dict__'`), und zwar erst
beim Laden.

## 4. Die acht Befunde von `pruefen`

Jeder Befund braucht einen Test, der ihn ausloest — ein Pruefer, der nur bei
gesunder Quelle gruen wird, prueft nichts.

| Befund | Ausgeloest durch |
|---|---|
| `Liste fehlt: <pfad>` | Datei nicht da |
| `kein gueltiges JSON` | Syntaxfehler |
| `Feld '<f>' fehlt oder ist leer` | Pflichtfeld leer |
| `Backslash im Pfad` | `a\b` |
| `'..' im Pfad` | Aufstieg |
| `absoluter Pfad` | `/x` oder `C:/x` |
| `doppelt in der Liste` | zwei gleiche `pfad` |
| `Ordner liegt nicht auf der Platte` | Leiche |
| `liegt in '<anderer>' - ein Eintrag genuegt` | Baum im Baum |
| `ist eine EIGENE Wurzel` | eigener Code als fremd markiert |

Die letzten zwei sind die wertvollen: sie verhindern, dass die Quelle sich selbst
widerspricht.

**Eigene Wurzeln werden hereingereicht**, nicht im Leser wiederholt:
`pruefen(eigene_wurzeln=quellen.WURZELN)`. So gibt es keine zweite Liste, und der
Aufrufer entscheidet, was fuer ihn "eigen" ist.

Ausnahme, ausdruecklich: `Werkstatt/Repos` ist eine eigene Wurzel der Zentrale
und trotzdem zu 100 % fremd (eine Klonsammlung). Solche Faelle gehoeren in den
Aufruf kommentiert, nicht in eine Sonderregel im Leser.

## 5. Die Anzeige

`als_text()` erzeugt die Markdown-Tabelle; die Datei (`Agenten/FREMD.md`) wird
daraus **erzeugt**, nicht daneben gepflegt. Ein Test liest die Tabelle mit einem
Muster (`^\|\s*` + Backtick-Pfad) und vergleicht die Pfadmenge mit `laden()`.
Ohne diesen Test entstehen zwei Wahrheiten, und die Anzeige luegt irgendwann.

## 6. Verbraucher anschliessen

Das Muster aus der Zentrale (`manifest._zeile`):

```python
rolle = e.rolle                      # eigene, genauere Rolle gewinnt
modul = quellen.fremd_modul()
treffer = modul.ist_fremd(quellen.pfad_in_wurzel(repo.wurzel, repo.pfad_rel))
if treffer is not None:
    rolle = rolle or treffer.art
    gruende.append(f"fremd: {treffer.regel} ({treffer.herkunft})")
```

Drei Regeln dazu:

1. **Nur ergaenzen.** Die Gruppe (`startbar`/`einrichten`) bleibt unveraendert —
   fremd heisst nicht kaputt. Eine Papierspur bleibt STARTBAR.
2. **Pfade zusammensetzen, nicht raten.** Das Manifest nennt den Pfad INNERHALB
   seiner Wurzel (`kraken/abgleich.py`), die Quelle den Pfad AB der Wurzel — eine
   Hilfsfunktion fuehrt beides zusammen (`pfad_in_wurzel(kennung, pfad)`).
3. **Zaehlen und nennen.** Die Kopfzeile traegt die Zahl (`… · 63 fremd`), sonst
   sieht die Gesamtzahl groesser aus als die eigene Arbeit.

## 7. Testformen

```python
# 1) Die Regel fuer JEDES Objekt, nicht ein Beispiel
def test_jede_fremde_zeile_hat_rolle_und_hinweis(self):
    for z in fenster.fremde_zeilen(self.zeilen): ...

# 2) Gegenprobe: der eigene Code darf NICHT treffen
def test_unser_code_ist_nicht_fremd(self):
    for p in ("Agenten/Handel/klassik_ema/handeln.py", "Agenten/Bus/bus.py"):
        self.assertIsNone(fremd.ist_fremd(p))

# 3) Die Pruefung kann rot werden (Attrappe in einem Temp-Ordner)
def test_fehlender_ordner(self):
    w = attrappe([eintrag("a/b")], ordner=())
    self.assertTrue(any("liegt nicht auf der Platte" in b for b in fremd.pruefen(w)))

# 4) "mindestens einer" mitpruefen - sonst ist eine falsche Wurzel still gruen
def test_openalice_ist_benannt(self):
    self.assertEqual(len([z for z in self.zeilen if z.ordner == "OpenAlice"]), 1)
```

## 8. Was es gebracht hat

| | Dateien | Zeilen |
|---|---|---|
| eigener Code (Vorgabe) | 831 | 173.481 |
| mit Fremd-Material | 11.489 | 4,2 Mio. |

Die erste Zahl war vorher nicht nennbar. Genau darin liegt der Nutzen: eine
Zahl, die man weitergeben kann, und eine Grenze, die nicht mehr im Kopf jedes
Auswerters liegt.
