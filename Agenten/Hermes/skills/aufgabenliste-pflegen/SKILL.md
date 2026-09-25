---
name: aufgabenliste-pflegen
description: Use when TASKS.md-Eintraege geaendert werden.
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Aufgaben, TASKS.md, BrainFiles, Editieren]
---

# Aufgabenliste pflegen (`MaxHirn/Archiv/TASKS.md`)

## When to Use

- "als Task eintragen", "was ist offen", "fass die offenen Punkte zusammen"
- am Ende JEDER Aufgabe (stehende Regel, siehe unten)
- Sammelauftrag, Sitzungsabschluss, Betriebsrunde: Aufgaben nachziehen
- eine Aufgabe ist erledigt (`## Erledigt`), oder ihr Titel behauptet etwas, das
  eine Messung widerlegt hat

Die Datei ist die EINE offene-punkte-Liste des Hauses,
CRLF, und waechst zwischen zwei Sitzungen um Dutzende Eintraege. Sie wird oft per
Skript geaendert - genau dort verschwindet still ein Eintrag, wenn die Ersetzung
zu grob greift.

## Stehende Regel (Max)

Am Ende jeder Aufgabe gehoeren die **nicht angefassten** Punkte und jede offene
**Entscheidung von Max** als Task in die Liste - nicht nur der eigene Auftrag.
Dazu: was absichtlich liegen blieb (Fremdarbeit, laufende Prozesse, generierte
Dateien) und was noch eine Entscheidung braucht. Danach committen.

## Ablauf

1. **Frisch lesen, nie aus dem Kopf ergaenzen.** `grep -n "^## "` zeigt die
   Abschnitte, ein Zeilenfenster die ersten Eintraege. Die hoechste vergebene
   Nummer bestimmt die neue - **Nummern nie wiederverwenden**, auch nicht fuer
   geloeschte.
   **Und lesen und schreiben gehoeren in DENSELBEN Aufruf.** Zwischen einem
   Blick von vorhin und dem Schreiben liegen in diesem Baum Minuten, in denen
   eine parallele Sitzung Eintraege einfuegt: Zeilenindizes aus einem frueheren
   Aufruf zeigen dann auf einen anderen Block, und der wird beim Ersetzen
   zerschnitten (Text des Nachbarn weg, `Zuletzt:` mitten im Absatz). Der
   Schreibvorgang liest die Datei deshalb selbst ein, sucht den Block ueber SEIN
   eigenes Merkmal (`- [ ] **T-0NN — ` bzw. der Titel, nicht ein Zeilenindex),
   ersetzt und schreibt zurueck - und druckt den Block danach plus den Anfang des
   folgenden Eintrags zur Kontrolle.
2. **Byte-sicher schreiben** (CRLF erhalten):

```python
with open(PFAD, "rb") as f:
    text = f.read().decode("utf-8")
nl = "\r\n" if "\r\n" in text else "\n"
assert text.count(anker) == 1
neu = ...                                   # jeder Ersatz mit `nl` gebaut
text = text.replace(anker, neu, 1)
with open(PFAD, "wb") as f:
    f.write(text.encode("utf-8"))
```

3. **Anker = Blockgrenze, nicht Kastenstellung.** Der Block endet beim NAECHSTEN
   `- [ ]` ODER `- [x]`. Ein Ausblick nur auf `- [ ] **` schluckt den folgenden
   ERLEDIGTEN Block und loescht ihn mit.

```python
# richtig - beide Kastenstellungen
re.compile(r"- \[[ x]\] \*\*T-067.*?(?=\r?\n- \[[ x]\] \*\*|\Z)", re.S)
```

4. **Nach JEDEM Schreiben die Nummernmenge vergleichen.**

```python
ids = lambda t: set(re.findall(r"- \[[ x]\] \*\*(T-\d+)", t))
assert ids(neu) - ids(alt) == set(), sorted(ids(alt) - ids(neu))
```

   Fehlt etwas: wortgleich aus `git show HEAD:MaxHirn/Archiv/TASKS.md`
   zurueckholen, nicht neu formulieren.
5. **`git diff --numstat` muss plausibel sein.** Ein ersetzter eigener Block zeigt
   Insertions UND Deletions - mehr Deletions als der neue Block Zeilen hat heisst:
   es ist Fremdtext mitgegangen.
6. **Committen** mit namentlichem Pfad (`git add -- MaxHirn/Archiv/TASKS.md`),
   zusammen mit der Aenderung, zu der die Aufgabe gehoert.

## Eintragsform

```
- [ ] **T-0NN — Kurztitel**
      Kontext: was gemessen/gebaut wurde, MIT Belegen (Zahlen, Pfade, Kommandos)
      Naechster Schritt: die EINE naechste Handlung, oder die offene Entscheidung
      Angelegt: JJJJ-MM-TT · Zuletzt: JJJJ-MM-TT
      Betrifft: <Pfade>
```

- **Eigene Aufgaben auf den gemessenen Stand ziehen** (Titel darf sich aendern),
  mit einer datierten `KORREKTUR`-Zeile, die sagt, was vorher behauptet wurde und
  warum es falsch war - der Irrtum ist die nuetzliche Information, nicht die
  Korrektur allein.
- **Fremde Aufgaben nur ergaenzen:** alten Text stehen lassen, einen datierten
  `BELEG <datum>`-Absatz anhaengen. Sonst gehen fremde Begruendung und fremder
  Kontext verloren, und der Autor sieht seine Aufgabe umgeschrieben.
- **Erledigtes** wandert nach `## Erledigt` und behaelt den Belegsatz (was es
  gezeigt hat, nicht "fertig"). Dort steht `- [x]`, in `## Offen` `- [ ]` -
  **die Kastenstellung entscheidet nicht, der ABSCHNITT tut es.** Wer nach der
  Klammer filtert, haelt den ganzen Erledigt-Block fuer offene Arbeit; nach dem
  Abschnitt filtern (oder beide Klammerformen im Ausblick zulassen, siehe
  Anker-Regel) und beim Einsortieren die Kastenstellung des Zielabschnitts
  setzen. Der erledigte Eintrag nennt das GEMESSENE Ergebnis - auch wenn die
  Aufgabe selbst gegenstandslos war ("nichts zu tun, weil X schon nicht mehr
  existiert") gehoert genau das mit Beleg hinein, nicht der urspruengliche Auftrag
text.
- Ein Titel verspricht ein ERGEBNIS, kein Vorgehen: "PF_XBTUSD ist mit 141 USD
  nicht handelbar" ist eine Aufgabe, "Kontraktgroesse pruefen" ist eine Notiz.

## Fallen

- **Die Liste waechst zwischen zwei Blicken.** Vor dem Eintragen erneut lesen -
  eine parallele Sitzung haengt zwanzig Eintraege an, und die gewaehlte Nummer ist
  dann doppelt vergeben.
- **`write_file` verweigert die Datei** (kein vollstaendiger Lesevorgang dieser
  Sitzung) - ueber den Byte-Weg schreiben, nicht die Datei komplett neu setzen.
- **Ein Sichtfenster (`sed -n '1,40p'`) zeigt nur den Kopf.** Die eigene Aufgabe
  steht weiter unten: erst `grep -n "T-0NN"` suchen, dann Vorgaenger- und
  Nachfolgerblock lesen, bevor ersetzt wird.
- **Zeilenenden sind CRLF.** `open(..., "w")` dreht die Datei auf LF und erzeugt
  einen Ganzdatei-Diff; Gegenprobe `git diff --numstat`.
- **Doppelte Nummern sind ein Befund, kein Aufraeumauftrag.** Eine parallele
  Sitzung vergibt dieselbe Nummer fuer einen anderen Punkt (zwei `T-087` mit
  verschiedenen Titeln sind schon vorgekommen). Den fremden Eintrag NICHT
  umnummerieren - er ist gerade in Arbeit - sondern im Abschlussbericht melden
  und beim naechsten eigenen Eintrag die Nummer danach nehmen.
- **Ein Block, der beim Schreiben zerschnitten wurde, wird aus `HEAD`
  wiederhergestellt** und dann neu ergaenzt - nicht aus dem Gedaechtnis neu
  formuliert, und nicht einfach der eigene Text vor den Rest gesetzt.

## Nachweis

- Nummernmenge vor/nach dem Schreiben gleich (plus die neuen).
- `git diff --numstat` zeigt nur die gewollten Zeilen der eigenen Bloecke.
- Nach dem Push: `git show origin/master:MaxHirn/Archiv/TASKS.md | grep -c "T-0NN"`.
