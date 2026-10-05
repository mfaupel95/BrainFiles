---
id: 20261005-fremd-api-drosselung
title: 'Lektionen — Fremd-API-Drosselung (Parallelität, nicht Menge)'
tags: [lektion, werkzeuge, drosselung, rate-limit, okx, parallelitaet]
created: 2026-10-05
updated: 2026-10-05
related: ['[[Lektionen/Werkzeug-Fallen]]', '[[Betrieb/Wachen-und-Aufgaben]]', '[[Handel/Boersen-und-Schluessel]]', '[[Lektionen/Windows-Umgebung]]']
summary: 'Ein Fremdanbieter drosselt nicht, weil zu viel Arbeit anliegt, sondern weil zu viel gleichzeitig laeuft — belegt an OKX 50011; dazu die Hausbremse `okx_takt.py` und die Regel, welche OKX-Fehlerart man wartet und welche man sofort wirft.'
---

# Fremd-API-Drosselung

**Regel: Drosselung entsteht durch Nebenlaeufigkeit, nicht durch Menge.** Wer
eine Fremd-API „langsamer aufruft", belegt die falsche Ursache, wenn viele
Aufrufer gleichzeitig laufen — die Bremse muss dann zwischen den Aufrufern
stehen, nicht in jedem Aufrufer.

## Der Beleg

Gemessen am 05.10.2026 gegen die OKX-oeffentliche Schnittstelle:

| Last | Ergebnis |
|---|---|
| 120 Abrufe **nacheinander** | 0 Fehler |
| 6 Threads x 40 Abrufe | **93 Fehler** (`50011`, teils `429`) |

Derselbe Anbieter, dieselbe Menge, zwei Ergebnisformen. Ein Gatter pro Aufrufer
haette beide Lasten nur langsamer gemacht — die 6 Threads bleiben 6 Threads.

## Die Hausbremse: ein Fenster, nicht je Aufrufer ein Zaehler

`Agenten/Handel/okx_takt.py` haelt **einen** Fensterspiegel auf der Platte
(`Handel/cache/okx-takt/fenster.json`, 12 Abrufe je 2 s) und wird ueber den
**Pfad** geladen, damit er wirklich eine Instanz ist und nicht eine je Spur.
`reserviere()` wird **vor** dem Senden gerufen, nicht danach.

Gemessene Nebenwirkung einer Rechnung, die falsch herum stand: die erste Fassung
rechnete `TAKT_PRO_S / TAKT_ABRUFE` (= 0,5 s Abstand) statt
`TAKT_FENSTER_S / TAKT_ABRUFE` (= 0,167 s) — der Takt war doppelt so langsam wie
gedacht, ohne dass eine Meldung das verriet.

- **Zeilenende der Zahlen:** der Fensterspiegel schreibt **6** Nachkommastellen
  (Mikrosekunden). Mit 3 kostet jede gerundete Marke bis 0,5 ms, und ueber zehn
  aufeinanderfolgende Abrufe ergab das 0,166 statt 0,167 — der Test „zehn
  Abrufe" fand genau diese Abweichung.
- **Ein unlesbarer Spiegel gilt als LEER** (kein Takt), also im Zweifel
  zuschlagen: ein zu schneller Durchlass erzeugt genau die Drosselung, die die
  Bremse beseitigen soll.
- **Windows haelt die Datei zeitweise offen.** `os.replace` scheitert dann mit
  `WinError 32/5`, weil ein lesender Prozess die Zieldatei haelt — zweimal in
  70 s unter Last. Deshalb mehrfach versuchen (`SCHREIBVERSUCHE`) und die
  `.tmp`-Datei beim endgueltigen Scheitern wegraeumen. **Meldung:** eine solche
  Ausnahme ging als „OKX-Transportfehler" in die Betriebsprotokolle und sah wie
  ein Netzausfall aus.

## Welche OKX-Fehlerart man wartet und welche nicht

`429` ist die **einzige** heilbare Fehlerart: exponentielles Warten, hoechstens
vier Versuche, danach an den Aufrufer. Alles Fachliche (`50119` fremde
Umgebung, `50101` Schluessel, `51008` zu wenig Bestand, „Menge zu klein")
**wirft sofort** — beim Schreiben kann jeder weitere Versuch eine echte Order
sein. Wer 429 von 50119 nicht trennt, wiederholt beim Kauf.

## Nachweis

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && \
  python -m unittest tests.test_okx_takt -v          # 21 Tests
# Gegenbeweis der Kausalitaet, ohne Börse:
python Agenten/Hermes/skills/brainfiles/api-drosselung-bannen/scripts/burst-gegenbeweis.py
```

Der Verdrahtungstest in dieser Suite prueft **jeden** Aufrufer gegen den echten
Pfad und meldet Werkzeuge, deren Datei fehlt — der Fehler fiel dort zweimal
auf (ein Werkzeugpfad zeigte ins Leere). Der Gegenbeweis-Skript kann mit
Attrappen laufen; **nie** gegen eine echte Boerse im Parallelbetrieb.

## Siehe auch

- Skill `api-drosselung-bannen` — das Verfahren, mit dieser Seite verknuepft
- [[Betrieb/Wachen-und-Aufgaben]] — leere Ausgabe, doppelte Bedeutung
- [[Handel/Boersen-und-Schluessel]] — Fehlercode der Boerse ist eine Antwort
  ueber die **Adresse**, nicht ueber die Faehigkeit
