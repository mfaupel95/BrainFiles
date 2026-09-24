# Claude-Format -> Hermes-Frontmatter

Tiefe zu Schritt 2-4 in SKILL.md. Gilt fuer jede Sammlung, die aus dem
Claude-Skill-System kommt.

## Formaterkennung

Kein YAML-Frontmatter, stattdessen Markdown-Ueberschriften:

```
# SKILL: Fast Testing Checklist
## Metadata   - **Skill Name**: ... - **Folder**: ... - **Source**: ...
## Description  <ein Absatz>
## Trigger Phrases  Use this skill when the conversation involves any of: `<liste>`
```

Hermes braucht `name:` und `description:`. Konverter-Regel:
- `name` = Ordnername (das Manifest nennt dieselben Namen)
- `description` = erster Satz/ganzer Absatz aus `## Description`
- `tags` = die `## Trigger Phrases`

Zusaetzlich fast immer dabei: ein Manifest (`claude-skills.json`: `name`,
`version`, `categories` mit den Skillnamen) und ein `install.sh`, das nach
`~/.claude/skills/<name>` kopiert. Das Manifest ist die Liste der Wahrheit -
den Konverter daraus speisen, nicht aus einem Verzeichnisdurchlauf.

## Gemessene Groessenverteilung (Beispiel offensive-Security-Sammlung, 79 Skills)

| Kennzahl | Wert |
|---|---|
| Skills / Kategorien | 79 / 23 |
| Gesamttext | 3,4 MB |
| Median je Datei | 20 KB |
| groesste Datei | 567 KB |
| ueber 100 KB / ueber 50 KB | 4 / 10 |

Merksatz: der Median verschweigt den Ausreisser. 20 KB je Datei sind
unbedenklich (~5.000 Tokens), ein Ausreisser verbraucht ~145.000 Tokens.
Daraus die zwei Toepfe: **ladbar** (unter der Schwelle) und **index-only**
(mit Pfadzeiger).

## Token-Rechnung

Eine geladene Bibliothek kostet Namen + Beschreibungen bei jeder Anfrage.
Beschreibung 40-150 Zeichen, also je Skill grob 50-200 Tokens: 79 Skills sind
2.000-3.000 Tokens Dauerpreis - die Groessenordnung einer ganzen getrimmten
Hausbibliothek. Deshalb der eigene Bot statt der Hauptbibliothek; bei
Auswahl-Import nur die Kategorien nehmen, die Max wirklich braucht.

## Dual-Use-Rahmen

Methodensammlungen (Offensive Security o. ae.) sind Text, keine ausfuehrbaren
Werkzeuge. Der Rahmen steht in der `SOUL.md` des tragenden Bots und lautet in
der Sache: eigene oder ausdruecklich freigegebene Systeme, kein Vorgehen gegen
fremde Ziele, nichts ohne ausdrueckliche Anweisung gegen ein echtes Ziel. Die
Faehigkeit wird gebaut, die Hausordnung bleibt stehen.
