---
name: api-drosselung-bannen
description: Use when eine Fremd-API drosselt und Zyklen abbricht.
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Drosselung, Rate-Limit, Fremd-API, Hausbremse, Gegenbeweis, Belege]
    related_skills: [messwerkzeug-gegenprobe, stille-ausfaelle-eingrenzen, trugschluesse]
---

# API-Drosselung bannen — wenn ein Fremdanbieter das Haus ausbremst

Wenn ein Fremdanbieter (Boerse, Feed, Wetterdienst) das Haus drosselt, brechen
Zyklen ab, und die Fehlermeldung liegt in vielen Dateien verteilt. Dieser Skill
bringt die Ursache an **eine** Stelle und heilt die Fehlerart, die sich heilen
laesst. Er baut keine Drosselungs-Gewohnheit an (ein Gatter pro Aufrufer waere
wirkungslos) und behauptet nicht, die Fremd-API zu reparieren — er belegt,
dass das Haus sie verträgt.

Er ist nicht der Beweis eines Schalters (`messwerkzeug-gegenprobe`) und nicht
das Eingegrenzen eines stillen Ausfalls (`stille-ausfaelle-eingrenzen`).

## When to Use

- ein Fremdfehler beendet regelmaessig Zyklen: `HTTP 429`, `Too Many Requests`,
  `Rate Limit exceeded`, `50011`, HTTP 503 als Drosselung
- dieselbe Meldung steht bei mehreren Spuren/Wachen, obwohl jede fuer sich
  wenig tut
- ein Zyklus bricht ab, obwohl die Fehlerklasse eigentlich heilbar waere
- „parallel laeuft es schlimmer als nacheinander" ist eine Vermutung, die
  jemand pruefen will

**Don't use for:** ein einzelner gescheiterter Aufruf ohne Wiederholung
(`okx-orderweg-diagnose`), ein fremder Schluessel/Host (`okx-orderweg-diagnose`).

## Prerequisites

- **Vorher messen, nicht bauen.** Zugang zum Betriebs-Journal, in dem jede
  Zyklus-Ende mit `code` und `text` gelandet ist (im Haus
  `Agenten/Bus/journal/<JJJJ-MM-TT>.jsonl`). Ohne diese Zahlen ist „dauerhaft
  vorhanden" eine Behauptung.
- Ein Weg, die Fremd-API direkt anzusprechen (im Haus das jeweils zustaendige
  Zugangsmodul, z. B. `Agenten/Handel/scanner/okx.py`).
- Nur Standardbibliothek. Der Beitrag ist ein **gemeinsamer Takt**, keine neue
  Abhaengigkeit.

## How to Run

Der Burst-Gegenbeweis laeuft als Skript ueber das `terminal`-Werkzeug:
`scripts/burst-gegenbeweis.py`. Er misst dieselbe Last zweimal — einmal ohne,
einmal mit Bremse — und schreibt beide Zahlen in eine Datei. Beide Laeufe
gehoeren in **eine** Umgebung mit **laufendem Betrieb**, sonst prueft man das
Werkzeug statt seiner Stellung im Haus.

## Quick Reference

| Frage | Messung | Befund |
|---|---|---|
| Ist es Menge oder Gleichzeitigkeit? | N Abrufe nacheinander / N parallel | nur parallel -> Drosselung |
| Welche Spur trifft es? | Journal nach `wer` + Fehlercode zaehlen | 40 von 43 = eine Spur |
| Welche Fehlerart heilt? | Code-Klassen: 429 ja, 51008 nein | nach Warten erneut |
| Wirkt die Bremse im Betrieb? | Burst gegen das **echte** Fenster | 93 Fehler -> 0 |
| Haelt der Takt die Rate? | laengerer Lauf, Dauer / Abrufe | Sollrate ±10 % |
| Ist der Takt zu langsam? | gemessener Abstand gegen `FENSTER/ABRUFE` | zu langsam = selbst gebauter Fehler |

## Procedure

1. **Das Fehlerbild aus dem Betrieb zaehlen, nicht aus dem Gedaechtnis.**
   Journal lesen, je `wer` und Fehlercode summieren. Erst dieser Block lehnt
   Regeln ab, bevor man welche baut. (Gemessen 05.10.2026: 43 Abbrueche, davon
   40 beim scanner — eine Spur, nicht „das Haus".)
2. **Reproduzieren, BEVOR zu bauen — und die Hypothese im Test trennen.**
   Zwei Laeufe, die sich in genau einer Eigenschaft unterscheiden:
   *nacheinander* gegen *gleichzeitig*. Unterschied nur in der Menge ->
   Drosselung ist bei OKX nicht die Ursache. Unterschied nur in der
   Gleichzeitigkeit -> die ist es. Ohne diese Trennung baut man eine Bremse
   gegen die falsche Sache.
3. **Die Fehlerart klassifizieren: welche heilt durch Warten?** Das ist die
   halbe Arbeit. 429 heilt durch Warten; `50119` (Schluessel/Host), `51008`
   (Balance), „Menge zu klein" nicht. Vorher stand 429 unter der Regel
   „fachlich, nicht wiederholen" — und genau das tötete den Zyklus.
4. **Die gemeinsame Stelle suchen, nicht jede Datei reparieren.** Fehler in
   mehreren Modulen mit derselben Ursache gehoeren an EINEN Ort. Wirkt der
   Eingriff nur im eigenen Prozess, ist er im Haus wirkungslos — mehrere
   Stufen, Fenster und Wachen sind eigene Prozesse gegen dieselbe IP.
5. **Vor dem Senden begrenzen, nicht nach der Antwort.** `reserviere()` wird
   vor dem Netzaufruf gerufen. Sonst begrenzt man die Antworten, nicht die
   Versuche — und jeder Wiederholungsversuch ist bei einer Order eine echte
   Order.
6. **Die Regel testbar machen: kuenstliche Uhr statt echter Zeit.** Raten
   werden ueber einen Uhr-Parameter geprueft, nie ueber eine Stoppuhr. Ein
   Test, der eine Rate misst, prueft sonst nur, wie schnell der Rechner ist.
7. **Den GATEWEG pruefen, nicht das Stichwort.** Der Test liest den
   **Aufruf** (`reserviere()`) in jeder verdrahteten Datei. Eine Datei, die
   den Namen nur im Kommentar nennt, faellt durch.
8. **Der Gegenbeweis gehoert gegen das echte Fenster.** Nicht in ein selbst
   gewaehltes Temp-Verzeichnis: dort misst man die Bremse, nicht ihre Wirkung
   im Haus. Wenn der Nutzer an der Beweislage zweifelt, ist meist genau das die
   Luecke.
9. **Fehler, die erst im echten Betrieb auftauchen, sind Ergebnis.** Im
   Laborkoffer fehlen sie zwangslaeufig (hier: Windows blockiert `os.replace`,
   solange ein Leser die Datei offen haelt). Im Fehlerbild ist eine solche
   Meldung nicht mehr vom eigentlichen Fehler unterscheidbar — sie heilen.
10. **Was man NICHT mehr behauptet, ausschreiben.** Belegt ist meist „parallele
    Last fuehrt nicht mehr zum Abbruch". Ob der Anbieter selbst drosselt (bei
    geteilter IP, Fremdnutzung), ist unbelegt — dafuer fehlt ein Zaehler.
11. **Vorbestehende Fehler per Gegenprobe trennen.** Ein roter Test nach der
    Aenderung ist erst dann eigener Schaden, wenn er auf der HEAD-Fassung
    nicht auch rot ist.

## Pitfalls

- **Ein Gegenbeweis in einem selbst gewaehlten Verzeichnis prueft das
  Werkzeug, nicht seine Stellung im Betrieb.** Genau dieser Fehler stand in
  der ersten Fassung des Nachweises: `OKX_TAKT_ORDNER` war auf ein Temp-Verzeichnis
  gesetzt, also lief die Bremse allein — ohne die acht laufenden Prozesse, die
  im Haus in dieselbe Datei schreiben.
- **Ein Messskript misst den Mitbetrieb, wenn es das gemeinsame Fenster
  benutzt.** 4 Test-Threads ergaben 96 s statt 30 s — die Differenz waren
  nicht die Test-Threads, sondern der laufende Betrieb. Isolationsordner fuer
  die Ratenmessung, echtes Fenster fuer den Wirkungsnachweis.
- **„N Abrufe je M Sekunden" heisst M/N Sekunden Abstand.** Die erste Fassung
  rechnete `PRO_S/ABRUFE` statt `FENSTER/ABRUFE` und war **dreimal zu langsam**
  (2,2/s statt 6/s). Die Kontrolle ist nicht das Rechnen, sondern der Vergleich
  mit der Rate, die man selbst erwartet.
- **Ein Parametername, der zugleich Schleifenvariable ist, friert die Uhr
  ein.** `jetzt` war Parameter und wurde in der Schleife ueberschrieben — im
  zweiten Durchlauf eingefroren, negative Wartezeit, endlose Schleife (Timeout
  nach 45 s statt 1,1 s). Testparameter, die eine Uhr ersetzen, heissen darum
  ausdruecklich nicht wie die lokale Uhr.
- **Zwei Regeln, die sich auf dieselbe Zahl deckeln, sind eine Regel mit
  Wartezeit.** Fenstergrenze = Ratengrenze hiess: wer das Fenster mit genau
  der Sollrate fuellt, wartet auf die Ablage der aeltesten Marke (bis 2 s),
  obwohl die naechste Stelle nach 0,17 s frei waere. Die Zahlen muessen
  entkoppelt sein, und der Test muss die Wartezeit je Aufruf messen.
- **Genauigkeit im gespeicherten Zustand ist Teil der Regel.** Drei
  Nachkommastellen kosten bei 0,167 s Abstand bis 0,5 ms je Marke; ueber zehn
  Abrufe ergab das 0,166 statt 0,167. Wer an der Speichergenauigkeit spart,
  verlangsamt still den Takt.
- **Unter Windows blockiert ein offenes Handle das Ersetzen einer Datei**
  (`WinError 32`/`5`). Wer ohne Sperre liest und dann atomar ersetzt, erzeugt
  Fehlermeldungen, die als Netzausfall im Protokoll landen und vom eigentlichen
  Fehler nicht unterscheidbar sind. Schreiben mehrfach versuchen,
  `.tmp`-Dateien aufraeumen, Lesefenster kurz halten.
- **Der Pfad zu einer Hausdatei wird GESUCHT, nicht gezaehlt.** Ebenenzaehler
  zeigten bei drei von vier Werkzeugen ins Leere (drei Ebenen hoch statt
  zwei). Der Unterschied fiel erst auf, als die Dateien echt gestartet wurden.
- **Ein Takt, der wartet, darf das Warten nicht in einen Fehler verwandeln.**
  Die erste Fassung meldete „kein Platz frei", weil die Wartegrenze genau der
  Sollzeit entsprach — sie tat genau das Richtige und wurde trotzdem zum
  Abbruch. Wartegrenze deutlich ueber der Sollzeit, Fehler nur fuer den Fall,
  dass ein fremder Prozess die Sperre haelt.
- **Bei gesperrter Sperre nicht aufgeben, sondern ohne Sperre weiter
  messen.** „Durchlassen" hiesse, den Takt genau dann aufzuheben, wenn
  mehrere Prozesse zugreifen — das erzeugt die Drosselung, die beseitigt
  werden soll.
- **Ein Mock, der die echte Funktion aufruft, die er ersetzt, ruft sich
  endlos selbst.** Die Wahrheit VOR dem Mocken festhalten.

## Verification

Der Nachweis besteht aus drei Teilen; alle drei gehoeren in eine Antwort:

1. **Ursache getrennt** — zwei Laeufe, nacheinander vs. parallel. Nur die
   Parallelvariante erzeugt den Fehler.
2. **Gegenbeweis gegen das echte Fenster**, mit laufendem Betrieb und ohne
   gesetzten Takt-Ordner: gleicher oder haerterer Burst, Fehlerzahl 0.
3. **Tests auf der Regel, nicht auf heutige Zahlen** — kuenstliche Uhr,
   kuenstliche Fehler, Verdrahtung geprueft am Aufruf in jeder Datei.

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && \
python ../Hermes/skills/brainfiles/api-drosselung-bannen/scripts/burst-gegenbeweis.py \
  --zugang scanner/okx.py --takt-modul okx_takt.py \
  --paare BTC-USDC ETH-USDC SOL-USDC --threads 8 --je-thread 40 \
  --ablage "$TMPDIR/burst-ergebnis.txt"
```

Erwartet: eine Zeile `ohne Bremse: N Fehler` mit N > 0, eine Zeile
`mit Bremse: 0 Fehler` bei gleicher Last, und eine **Ratenzeile** — sie zeigt,
dass die Bremse wirklich ansetzt. Ohne sie heisst `0 Fehler` auch „gar nicht
ausprobiert" (das tat die erste Fassung: beide Laeufe teilten sich die
neutralisierte Modulinstanz). Haelt die Bremse nicht, ist der Takt zu langsam
(Schritt 6) — nicht der Anbieter.

Der Hausfall mit allen Zahlen, Fehlerbildern und Belegen steht in
`references/okx-50011.md`; mit `skill_view(name="api-drosselung-bannen",
file_path="references/okx-50011.md")` laedbar, wenn es konkret wird.