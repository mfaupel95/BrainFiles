---
name: sprache
description: Wandelt diktierten, per Spracheingabe entstandenen Text in einen sauberen, präzisen Prompt um und führt ihn anschließend aus. Nutze diesen Skill, wenn der Nutzer `/sprache` aufruft ODER wenn eine Nachricht erkennbar diktiert wurde (fehlende Satzzeichen, Füllwörter wie "äh"/"also"/"halt", Selbstkorrekturen wie "nee doch", Wortwiederholungen, verstümmelte Fachbegriffe, durchgehender Kleinschreibungs- oder Fließtextblock ohne Struktur).
---

# Sprache → Prompt

Diktierter Text ist inhaltlich meist vollständig, aber formal verrauscht. Dieser Skill
entfernt das Rauschen und macht die eigentliche Absicht explizit — **ohne den Auftrag zu
verändern**.

**Danach `auftrag` anschließen.** Dieser Skill bleibt am Wortlaut; `auftrag` bestimmt
das dahinterliegende Ziel und wählt daraufhin den Weg. Die Reihenfolge ist bindend:
erst bereinigen, dann deuten — sonst wird Rauschen als Absicht gelesen.

## Ablauf

1. **Rohtext bestimmen.** Das Argument hinter `/sprache` ist der Rohtext. Ohne Argument:
   die letzte Nutzernachricht verwenden.
2. **Bereinigen** (siehe unten).
3. **Als Prompt strukturieren** (siehe unten).
4. **Kurz zeigen** — der bereinigte Prompt in einem Codeblock, maximal ein Satz Kommentar
   dazu. Keine Vorher/Nachher-Tabelle, keine Auflistung der Korrekturen.
5. **Direkt ausführen.** Nicht auf Bestätigung warten. Ausnahme: siehe „Nachfragen".

## 1. Bereinigen

Entfernen:
- Füllwörter und Verzögerungslaute: `äh`, `ähm`, `also`, `halt`, `sozusagen`, `ne?`,
  `weißt du`, `irgendwie`, `quasi`, `so`, `mal gucken` — nur wenn sie leer sind. `mal` in
  „schau mal nach" ist Ton, kein Rauschen: darf bleiben, wenn es die Bitte weicher macht.
- Doppelungen aus dem Stocken: „ich will ich will das" → „ich will das".
- Metakommentare über das Diktieren selbst: „warte", „nochmal von vorn", „Punkt",
  „Komma", „neue Zeile" (als gesprochene Satzzeichen).

Auflösen:
- **Selbstkorrekturen** — nur die letzte Fassung zählt. „Nimm den Ordner Bilder, nee,
  Dokumente" → Dokumente. Das Verworfene taucht im Prompt nicht mehr auf.
- **Satzgrenzen und Groß-/Kleinschreibung** rekonstruieren; ein Diktat kommt oft als ein
  einziger Block.
- **Zahlen und Einheiten** in Ziffern, wo es die Lesbarkeit erhöht: „dreitausend Dateien"
  → „3000 Dateien".
- **Verstümmelte Fachbegriffe** korrigieren, wenn der Kontext sie eindeutig macht — siehe
  [references/stt-fehler.md](references/stt-fehler.md).

## 2. Strukturieren

Der bereinigte Prompt braucht diese Teile, sofern der Rohtext sie hergibt:

- **Auftrag** — was konkret getan werden soll, als Imperativ, im ersten Satz.
- **Ziel/Objekt** — welche Dateien, welcher Ordner, welches Skript.
- **Randbedingungen** — was ausgeschlossen ist, was erhalten bleiben muss, Format der
  Ausgabe.
- **Erfolgskriterium** — woran erkennbar ist, dass es fertig ist. Nur wenn im Rohtext
  angelegt.

Mehrere Aufträge in einem Diktat werden zu einer nummerierten Liste in der Reihenfolge,
in der sie gesprochen wurden.

Nicht erfinden. Fehlt eine Randbedingung, fehlt sie auch im bereinigten Prompt — sie wird
nicht ergänzt, weil sie „sinnvoll wäre". Der Skill schärft, er erweitert nicht.

## 2b. Kurzverweise nicht bereinigen

Eine Eingabe wie `3`, `weiter` oder `ja mach` ist **kein verrauschtes Diktat**, sondern
ein Verweis auf etwas Vorheriges. Hier gibt es nichts zu säubern. Solche Eingaben gehen
direkt an `auftrag`, der sie gegen den Gesprächsverlauf auflöst.

## 3. Nachfragen

Nur in einem Fall stoppen statt auszuführen: wenn eine **Mehrdeutigkeit die Ausführung
verändert** und nicht aus dem Kontext auflösbar ist — z. B. unklar, ob eine Datei
verschoben oder kopiert werden soll, oder welcher von zwei genannten Ordnern gemeint ist.
Dann `clarify` mit der bereinigten Fassung und den konkreten Alternativen.

Nicht nachfragen bei bloßer Unschärfe im Ton oder bei fehlenden Details, die sich beim
Arbeiten ohnehin klären.

## 4. Wenn der Auftrag riskant ist

Löschen, Überschreiben, Verschieben großer Mengen: die bereinigte Fassung zeigen und
bestätigen lassen, bevor ausgeführt wird. Ein Diktierfehler in einem Löschbefehl ist
nicht rückholbar.

## Beispiel

Roh:
> also äh ich hab da im posteingang so ein paar pdfs die sind glaub ich von der
> versicherung ähm kannst du die mal einsortieren also nicht die bilder nur die pdfs und
> danach halt nochmal indexieren nee warte erst gucken ob das überhaupt versicherung ist

Bereinigt:
```
1. Prüfe die PDFs im Posteingang darauf, ob sie inhaltlich zur Versicherung gehören.
2. Sortiere die PDFs entsprechend ein — nur PDFs, keine Bilder.
3. Lass danach index.py laufen.
```

Die Selbstkorrektur am Ende („nee warte erst gucken") hat die Reihenfolge geändert: Prüfen
kommt vor dem Einsortieren. Genau das muss der bereinigte Prompt abbilden.
