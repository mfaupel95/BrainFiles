# Fehlende Inhalte belegbar finden und zurueckholen

Fuer Auftraege der Art „suche, was fehlt": Gedaechtnis-Eintraege, Notizen,
Konfigurationsstaende. Ergebnis ist eine belegte Liste plus der Volltext des Verlorenen -
nie eine Vermutung darueber, was gefehlt haben koennte.

## Die drei Quellen

| Quelle | Was drin steht | Wann sie hilft |
|---|---|---|
| `state.db`, Tabelle `messages`, `tool_name` des Schreibwerkzeugs | Das ERGEBNIS-JSON jedes Aufrufs, inklusive der ersetzten/entfernten Eintraege im Volltext (`replaced_entries`, `removed_entries`) | Immer zuerst: sie belegt WER was ueberschrieben hat, mit Zeit und Sitzung |
| `sessions/request_dump_*.json` → `request.body.system` | Systemprompt samt eingefuegtem Gedaechtnis = Schnappschuss je Zeitpunkt | Wenn ein Eintrag still verschwunden ist (kein Aufruf belegt ihn) |
| `backups/*.zip` → `.../memories/MEMORY.md` | Gedaechtnis je Sicherungslauf, auch je Profil | Wenn die DB fehlt oder rotiert wurde |

Zum DB-Lesen (read-only, auch bei laufendem System):

```python
con = sqlite3.connect("file:Agenten/Hermes/state.db?mode=ro", uri=True)
con.execute("select timestamp, session_id, content from messages "
            "where tool_name='memory' and content like '%_entries%' order by timestamp")
```

- `timestamp` ist Unix-Zeit (REAL) → `datetime.datetime.fromtimestamp(...)`.
- Der Ergebnis-Text ist JSON, aber nicht immer sauber: vor dem Parsen auf `{` pruefen.
- Beim Entpacken der Zips den INNEREN Pfad mitnehmen (`.zip`-Eintrag kann
  `profiles/<bot>/memories/MEMORY.md` heissen) - sonst ueberschreiben sich die Treffer
  unter einem Namen und man misst nur den letzten.

## Verlust von Umformulierung trennen

Drei Proben, in dieser Reihenfolge - besteht eine, ist es KEIN Verlust:

1. woertlich (Leerraum normiert),
2. erste ~70 Zeichen (umgeschriebene Fassung),
3. Kopf-Signatur: erste drei Wortzeichen des Eintrags, klein geschrieben, Satzzeichen
   zu Leerzeichen (`re.sub(r"[^\w./-]+", " ", text.lower())`).

Probe 3 traegt zwei Faelle: einen mit Vermerk zurueckgeholten Eintrag
(`HERMES-CONFIG … (Stand; … WIEDERHERGESTELLT …)`) und alte Fassungen, die denselben
Titel tragen. Ohne sie meldet das Werkzeug wiederhergestellte Eintraege endlos als
verloren; mit einem reinen Zeichenvergleich meldet es jede Umformulierung als Verlust.

## Rezept

1. Verluste messen: `python Agenten/Hermes/scripts/memory-verlust.py`
   (Liste, `--alles` Volltexte, `--retten <datei>` als Markdown, `--json <datei>`).
2. Je Fund entscheiden: absichtlich entfernt (`removed_entries`) → nur berichten;
   umgeschrieben → nichts tun; verloren → zurueckholen.
3. Zurueckholen heisst NEU SCHREIBEN, nicht wiederherstellen: `add` mit dem Volltext,
   plus ein kurzer Vermerk, woher er kommt. Nicht `replace` - der Anker kann denselben
   Fehler ein zweites Mal ausloesen.
4. Jede Zahl im zurueckgeholten Text am lebenden System nachmessen (Datei, Kommando),
   bevor sie wieder im Gedaechtnis steht. Der DB-Text belegt den Inhalt, nicht die
   Gegenwart.
5. Tests: `python -m unittest test_memory_verlust` aus `Agenten/Hermes/scripts`
   (aus dem Oberordner `python -m unittest scripts.test_memory_verlust`).

## Fallen der Messung

- **Ein `success: true` ist kein Beleg fuer den Inhalt.** Es sagt, dass geschrieben
  wurde. Die Kontrolle ist `replaced_entries`/`removed_entries` im selben Ergebnis.
- **Ein kurzer `old_text`, der als Teilstring in einem fremden Eintrag liegt, loescht
  diesen ganzen Eintrag.** Anker deshalb der eigene Anfang des Eintrags; eine
  Schlusszeile ist der gefaehrlichste Anker, den es gibt.
- **`/memory approve all` auf tagealte Vorschlaege schreibt die Datei neu und wendet
  nichts an** - die Anker treffen nicht mehr. mtime der Datei pruefen, nicht die
  Erfolgsmeldung des Befehls.
- **Ein neu geschriebener Eintrag und ein spaeterer Schreibvorgang derselben Sitzung
  koennen sich gegenseitig verdraengen** (falscher Anker). Nach jeder Sitzung mit
  mehreren Gedaechtnis-Schreibvorgaegen einmal messen, ob der erste noch da ist.
- **Werkzeuge in `Agenten/Hermes/scripts/` verschwinden gelegentlich innerhalb von
  Minuten** (nur `__pycache__` bleibt). Nach jedem `write_file` sofort `ls` und stagen -
  sonst faellt der Verlust erst beim Commit als „pathspec did not match" auf.
