# Werkstatt — die Spielregeln

Dieser Ordner gehört allen Modellen gemeinsam: Claude, Codex, Hermes und was
noch dazukommt. Er ist der einzige Ort, an dem sie ohne Absprache schreiben
dürfen. Angelegt am 30.08.2026 beim Umbau von `BrainFiles/` in vier Ordner.

Die Datei liegt zweimal — als `AGENTS.md` und als `CLAUDE.md`. Gleicher Inhalt,
zwei Namen, weil die Agenten verschiedene Dateien lesen. Wer eine ändert,
ändert beide.

## Wo was hingehört

| Fach | Wofür |
|---|---|
| `Austausch/` | Übergaben von einem Agenten an den nächsten. Eine Datei je Auftrag, Dateiname beginnt mit dem Datum. |
| `Projekte/` | Laufende Arbeit, die länger als eine Sitzung dauert. |
| `Ausgabe/` | Fertiges, das ein Mensch abholt — Berichte, Auswertungen, Exporte. |
| `Worktrees/` | Git-Arbeitsbäume für parallele Zweige. |
| `Repos/` | Geklonte Fremd-Repositories. Aus Git reproduzierbar, nicht gesichert. |
| `Sitzungen/` | Ablagen einzelner Sitzungen. Durchgangsware. |
| `Protokolle/` | Ausgaben einzelner Läufe, die als Beleg aufgehoben werden. |

## Vier Regeln

1. **Hier liegt nie ein Original.** Was nur hier existiert, existiert nicht.
   Persönliche Unterlagen gehören nach `MaxHirn/Archiv/`, dauerhaftes Wissen
   nach `MaxHirn/Wissen/`. Die Werkstatt darf jederzeit leergeräumt werden —
   und wird es auch, sobald sie voll läuft.

2. **Fremdes nicht verwerfen.** Es schreiben mehrere Agenten gleichzeitig
   hierher. Eine Datei, deren Änderungszeit weniger als **10 Minuten**
   zurückliegt, kann mitten in einem fremden Arbeitsschritt stehen — liegen
   lassen und melden, nicht anfassen. Die Schwelle ist bewusst eine Zahl und
   kein Ermessen; sonst entscheidet jede Sitzung anders. Geprüft wird mit
   `(Get-Item <pfad>).LastWriteTime`. Vollständig in
   [Schutzregeln](../MaxHirn/Wissen/Schutzregeln.md).

3. **Eine Übergabe trägt ihren Auftrag bei sich.** Wer in `Austausch/` etwas
   ablegt, schreibt in dieselbe Datei, was damit geschehen soll, woher die
   Zahlen stammen und woran man sieht, dass es erledigt ist. Ein Agent, der die
   Datei in einer Woche findet, hat keinen Gesprächsverlauf mehr.

4. **Versioniert ist hier nur diese Datei.** Alles andere in `Werkstatt/` steht
   in der `.gitignore` und ist damit auch aus der Sicherung nach `G:`
   ausgenommen. Wer etwas aufheben will, legt es in den Vault.

## Was nicht hierher gehört

Zugangsdaten jeder Art. Schlüssel und Tokens haben genau eine Ablage:
`MaxHirn/Wissen/Zugaenge.md`. Ein Schlüssel in einer Übergabedatei landet über
`Sitzungen/` und `Protokolle/` an drei weiteren Stellen und wird nie wieder
vollständig entfernt.
