# Fremd-Material im eigenen Baum

Wie das Haus die Grenze zwischen **eigenem Code** und **Fremd-Material** zieht,
warum es sie ueberhaupt braucht und wo sie steht.

## Der Befund (30.09.2026)

Die Frage „wie gross ist unser Handelssystem" ergab **634.815 Zeilen** in
`Agenten/Handel`. Davon stammten **513.266 Zeilen (81 %)** aus einem fremden
Projekt: `Agenten/Handel/OpenAlice`, 482 Dateien, ein eigenes Quant-Framework mit
`workspaces/` und `runs/`. Ueber den ganzen Baum gerechnet: 11.489 Dateien und
**4,2 Mio. Zeilen** — davon ist der weitaus groesste Teil nicht unser Code
(`Werkstatt/Repos` 6.160 .py, `Werkstatt/Ausgemustert` 5.767, davon allein eine
mitgelieferte CPython-Standardbibliothek, `repos-verschoben-aus-skills` 2.173).

Jede Bestands-, Such- und Aufraeumfrage musste das im Kopf abziehen, und jedes
Werkzeug hatte eine eigene Vorstellung davon, was dazugehoert. **Der echte
Schaden war nicht die Groesse, sondern die Unklarheit.**

Mit der Grenze: **831 Dateien / 173.481 Zeilen eigener Code.**

## Die Definition

Fremd ist Material, das wir **nicht pflegen** — ein Klon, ein Import, ein
Fremdprojekt im eigenen Baum, eine stillgelegte Anlage. Kriterium ist nicht
Sprache, Groesse oder Qualitaet, sondern die Frage: *aendern wir es, oder
benutzen wir es?*

Drei Regeln:

1. **Fremdes wird nicht gezaehlt** — Bestand, Umfang, Doppelungen laufen ohne es.
2. **Fremdes wird nicht aufgeraeumt** — kein Umbenennen, Verschieben, Loeschen.
3. **Fremdes wird nicht verschwiegen** — es steht als Zeile da, mit Herkunft und
   Regel. Sichtbar, nur nicht mitgezaehlt.

Nicht fremd: eigene Spuren und Werkzeuge, Laufzeitstaende (unser Betrieb, nur
nicht versioniert), `Werkstatt` als Ganzes (das traegt eigene Projekte) und
`Werkstatt/Projekte` (Datenfelder).

Grenzfaelle, ausdruecklich so entschieden:

- `Werkstatt/omnitrade` und `Werkstatt/OmniRoute` sind **Klon fremden Codes, in
  dem wir arbeiten** (Portierung, Router-Produktion). Sie zaehlen nicht als
  Haus-Code — aber sie sind produktiv, also „nur lesen, nicht anfassen".
- `Werkstatt/handel-stack` ist **unser eigener Code, eingefroren** (Spiegel vom
  18.09.2026). Er zaehlt nicht als lebender Code; er bleibt, weil er die einzige
  Kopie des Handelsstacks ausser Haus ist (Entscheidung Max, 30.09.2026).

## Wo es steht

| Datei | Rolle |
|---|---|
| `Agenten/FREMD-Liste.json` | **die eine Quelle** (JSON, weil Python UND PowerShell sie lesen) |
| `Agenten/Werkzeuge/fremd.py` | der Leser: `laden`, `ist_fremd`, `ohne_fremd`, `pruefen`, `als_text` |
| `Agenten/FREMD.md` | die lesbare Anzeige (Tabelle); ein Test vergleicht die Pfadmengen |
| `Agenten/Werkzeuge/bestand.py` | Bestand messen, `--mit-fremd` zum Vergleich |

Der Leser vergleicht **auf Pfadgrenzen** und nimmt den **laengsten** Treffer:
`…/OpenAlice` trifft `…/OpenAlice/src`, aber nicht `…/OpenAlice2`. Das ist der
Fall, der zaehlt — ein Textvergleich haette beide getroffen.

Verbraucher: die Zentrale (Rolle + Hinweis + Kopfzeile „63 fremd"),
`bestand.py`. Offen: `fundus-suche.ps1` und ein Block in der Systempruefung.

## Pruefen

    python Agenten/Werkzeuge/fremd.py --pruefen      # gesund: 37 Eintraege
    python Agenten/Werkzeuge/bestand.py              # eigener Code
    python Agenten/Werkzeuge/bestand.py --mit-fremd  # zum Vergleich
    python -m unittest discover -s Agenten/Werkzeuge/tests

`pruefen()` meldet: fehlender Ordner, leeres Feld, absoluter Pfad, `..`,
Doppelung, Eintrag im Eintrag, eine **eigene Wurzel** als fremd. Jede dieser
Pruefungen hat einen Test, der sie ausloest — ein Pruefer, der nur bei gesunder
Liste gruen wird, prueft nichts.

## Fallen

- **Ein Eintrag ist eine Aussage ueber Herkunft und wird nie geraten.** Beim
  ersten Anlauf sah es so aus, als haetten die acht `klassik_*`-Spuren keine
  Tests und waeren fremd — nachgesehen: angelegt am selben Tag, in
  `dauerlauf.SPUREN`, aufgebaut auf `klassik_regeln.py`. **Unser Code.** Genau
  diese Verwechslung soll die Liste unmoeglich machen.
- **Ein per Pfad geladenes Modul mit `@dataclass` braucht einen
  `sys.modules`-Eintrag.** `importlib.util.module_from_spec` +
  `exec_module` allein laesst `sys.modules[cls.__module__]` leer, und dataclasses
  bricht mit `AttributeError: 'NoneType' object has no attribute '__dict__'` ab —
  erst beim Laden, nicht beim Schreiben. Deshalb steht in `quellen.fremd_modul()`
  ein `sys.modules["haus_fremd"] = modul` VOR dem `exec_module`.
- **Die Wurzel nicht verzaehlen.** `Path(__file__).resolve().parents[1]` ist von
  `Agenten/Werkzeuge/repos-zentrale` aus `Agenten`, nicht BrainFiles — ein Test
  mit dieser Wurzel findet null Dateien und wird still gruen, wenn er nur
  „keine Fremden" behauptet. Richtig sind `parents[2]` bzw. der Anker aus
  `fremd.wurzel()`.

## Verwandt

- `MaxHirn/Wiki/Werkzeuge/repos-zentrale.md` — das Startfenster, das die Grenze anzeigt
- `MaxHirn/Wiki/Betrieb/Arbeitsverzeichnis.md` — wo Sitzungen starten
- `Agenten/FREMD.md` — die Liste selbst