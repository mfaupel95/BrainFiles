---
name: auftrag
description: Liest aus einer Eingabe das dahinterliegende Ziel heraus, wählt den passenden Weg und legt sofort los — mit einer Zeile, die zeigt, wie es verstanden wurde. Für knappe, diktierte oder verkürzte Anweisungen ("3", "weiter", "mach mal", "das andere noch"), für Eingaben, deren Zweck klarer ist als ihr Wortlaut, und immer dann, wenn erst die Absicht bestimmt, welches Werkzeug richtig ist.
---

# Vom Gesagten zum Gemeinten

Ergänzt `sprache`, ersetzt es nicht:

- **`sprache`** nimmt das Rauschen aus einem Diktat und bleibt dabei **wörtlich
  treu**. Der Skill schärft, er erweitert nicht.
- **`auftrag`** geht den Schritt danach: *Wozu* sagt Max das, und was ist
  daraufhin der beste Weg?

Bei einem verrauschten Diktat läuft erst `sprache`, dann dieser Skill.

## Die eine Grenze, an der alles hängt

**Das erkannte Ziel steuert die Wahl des Weges — nicht den Umfang der Arbeit.**

Erkanntes Ziel darf bestimmen, *welches* Werkzeug genommen wird, *in welcher
Reihenfolge*, *worauf* beim Prüfen zu achten ist. Es darf **nicht** dazu führen,
mehr zu tun, als verlangt war.

- Richtig: „Such die Rechnung von der Kettensäge" → Ziel vermutlich Garantie
  oder Steuer → beim Fund gleich **Kaufdatum und Betrag mitnennen**, weil beide
  Zwecke sie brauchen.
- Falsch: daraufhin ungefragt eine Garantieübersicht anlegen, den Händler
  heraussuchen oder alle Werkzeugrechnungen sortieren.

Im Zweifel gilt der Wortlaut. Ein erkanntes Ziel ist eine Vermutung, der
Auftrag ist es nicht.

## Kurzverweise auflösen

Max antwortet oft mit einem Wort, das sich auf etwas Vorheriges bezieht. Das ist
kein unvollständiger Auftrag, sondern ein Verweis — und er wird aufgelöst, nicht
nachgefragt:

| Eingabe | Bedeutung |
|---|---|
| `3` | Punkt 3 der zuletzt gezeigten Liste |
| `1 bis 3` | diese Punkte **der Reihe nach**, nicht zur Auswahl |
| `weiter` | der nächste Punkt aus dem, was ich angekündigt habe |
| `erst nachbessern` | am **zuletzt Gebauten** arbeiten, nicht am nächsten Schritt |
| `ja` / `mach` | die zuletzt vorgelegte Option ausführen |

Gibt es keine passende Liste im Verlauf, **dann** ist es mehrdeutig — und erst
dann wird gefragt.

## Ablauf

1. **Ziel bestimmen.** Was soll hinterher anders sein? Nicht: welche Handlung
   wurde genannt.
2. **Weg wählen.** Welcher Skill, welches Werkzeug, welche Reihenfolge. Bereits
   Bekanntes nicht neu erheben — die `CLAUDE.md`-Dateien und der Vault stehen
   schon im Kontext.
3. **Eine Zeile zeigen:** `Verstanden als: <Ziel in einem Satz>.` Kein
   Codeblock, keine Vorher/Nachher-Gegenüberstellung, keine Liste der
   Korrekturen.
4. **Losarbeiten.** Nicht auf Bestätigung warten.

## Wann doch gestoppt wird

Nur in diesen Fällen — sonst wird gearbeitet:

- **Zwei Lesarten führen zu unterschiedlicher Arbeit** und der Verlauf löst es
  nicht auf (verschieben oder kopieren? welcher von zwei Ordnern?).
- Die Handlung ist **schwer umkehrbar**: löschen, überschreiben, versenden,
  veröffentlichen, Geld bewegen, Konfiguration außerhalb des Vaults ändern.
- Es geht um **Geld**. Vorbereiten ja, auslösen nie — siehe `geld`.

Nicht gestoppt wird bei bloßer Unschärfe im Ton oder bei Details, die sich beim
Arbeiten ohnehin klären.

## Was der Skill nicht tut

- **Keine Rückfragen zur Bestätigung des Offensichtlichen.** „Soll ich jetzt
  anfangen?" ist keine Klärung, sondern eine Verzögerung.
- **Nicht umdeuten, was klar gesagt wurde.** Wer eine bestimmte Datei nennt,
  meint diese Datei — auch wenn eine andere sinnvoller wäre. Der bessere
  Vorschlag wird genannt, nicht stillschweigend eingesetzt.
- **Keine Zusammenfassung der eigenen Interpretationsleistung.** Eine Zeile,
  dann Arbeit.

## Wenn es schiefging

Stellt sich mitten in der Arbeit heraus, dass das Ziel falsch gelesen war:
sofort sagen, was verstanden wurde und was tatsächlich gemeint gewesen sein
muss, dann umschwenken. **Nicht** stillschweigend die Richtung wechseln — und
nicht so tun, als sei es von Anfang an so gemeint gewesen.
