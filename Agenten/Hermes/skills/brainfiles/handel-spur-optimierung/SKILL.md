---
name: handel-spur-optimierung
description: "Use when eine Handel-Spur mathematisch optimiert wird."
category: brainfiles
platforms: [windows]
---

# Handel-Spur optimieren: messen, belegen, dann aendern

## Wann
Eine Spur soll „besser" werden — Eingangsfilter, Ausstiegsgeometrie, Auswahl der
Vorbilder, Sizing. Abgrenzung: Anbinden/Betrieb/Auswerten einer Spur steht in
`handel-spuren`, der Nautilus-Knoten in `nautilus-okx-handel`, der allgemeine
Nachweis-Ablauf (Sicherung, Diff, Commit, echter Lauf) in `brainfiles-auftrag`.
Dieser Skill ist die REIHENFOLGE und die Beweisregel fuer Parameteraenderungen
an Spuren.

## Reihenfolge — nicht abkuerzen

1. **Messen, nicht erinnern.** Vor jeder Aussage die vorhandene Auswertung
   fahren: `<spur>/auswertung.py`, sonst `auswertung_alle.py`. Immer getrennt
   ausweisen: nach Kosten UND vor Kosten, echte Handelsrunden getrennt von
   Stoerungen (ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung). Ein
   frueheres Lesebild darf kippen, wenn die Stichprobe waechst — die groessere
   Stichprobe gewinnt.
2. **Pruefbarkeit aus den Journalfeldern ableiten, nicht aus der Idee.**
   `handelsjournal.csv` traegt: zeit, modus, aktion, kette, wallet, token,
   symbol, preis, menge, einsatz_usd, wert_usd, marktkap_usd, slippage_pct,
   gebuehr_pct, grund. Rueckwirkend pruefbar sind damit Marktkapitalisierung,
   Kette, Wallet, Zeitpunkt. NICHT pruefbar: das Signalalter (steht nur in
   `ablehnungen.csv`, und dort nur fuer ABGELEHNTE Signale ohne Ergebnis) und
   jede Ausstiegsgeometrie (die Preispfade stehen nirgends). Ausstiegsfragen
   sind nur prospektiv zu beantworten (eigenes Buch, s. unten).
3. **Eine Buchhaltung, nie zwei.** Paarung und Kennzahlen kommen aus der Spur
   selbst: `<spur>/auswertung.py` per `importlib.util.spec_from_file_location`
   mit EINDEUTIGEM Modulnamen laden (alle Spuren besitzen ein Modul
   `auswertung`; ueber `sys.path` gewaenne die zuletzt eingefuegte), dann
   `lade_ausstiege()` und `buchauswertung.kennzahlen()` benutzen. Ein
   nachgebautes Paarungsverfahren liefert andere Zahlen und macht den Vergleich
   wertlos.
4. **Beleg vor Vorschlag.** Eine Regel gilt nur als Vorschlag, wenn ALLE vier
   Bedingungen halten: (a) Zeithalbierung — nach `zeit` sortieren, aeltere 60 %
   Suchhaelfte, juengere 40 % Gegenprobe; (b) Besetzung — mindestens 30
   Ausstiege je Gruppe in JEDER Haelfte; (c) Vorzeichen — in beiden Haelften
   positiv nach Kosten; (d) Vorsprung — in beiden Haelften besser als die
   Restgruppe.
5. **Gegenprobe fahren.** Dieselbe Messung mit der UMGEKEHRTEN Regel (Band
   verschieben statt oeffnen) muss die Gegenrichtung zeigen — sonst ist die
   Zahl ein Artefakt. Ein Test, der nur den Wunschfall prueft, ist kein Test.
6. **Verdikt-Wortschatz:** `traegt` / `nicht entschieden` / `verworfen`.
   „nicht entschieden" ist das ehrliche Ergebnis kleiner Buecher (unter 30
   Ausstiegen je Haelfte) — dort wird KEIN Verdikt erfunden. Junge Spuren
   liefern genau das; so stehen lassen.
7. **Kosten dominieren.** Bei 3–5 % Slippage je Seite liegt das Ergebnis VOR
   Kosten oft nahe Null und NACH Kosten deutlich negativ. Eine Regel, die nur
   vor Kosten traegt, ist kein Vorschlag, sondern eine Slippage-Korrektur — als
   solche benennen.
8. **Design-Gate.** Erst Design, dann Code (Skills `brainstorming`, danach
   `writing-plans`): Messung zeigen -> 2–3 Wege mit Abwaegung und EINER
   Empfehlung -> genau EINE Frage -> Spezifikation nach
   `Agenten/Handel/docs/design/JJJJ-MM-TT-<thema>-design.md` (Selbstpruefung:
   Platzhalter, Widerspruch, Umfang, Mehrdeutigkeit) -> Freigabe abwarten ->
   Plan nach `Agenten/Handel/docs/plans/` -> TDD-Umsetzung. Kein Code vor der
   Freigabe. Vorgemerkte Stufen bekommen einen eigenen Abschnitt in der
   Spezifikation, nicht einen Nebensatz.
9. **Aendern (Stufe 1).** Sicherung `<datei>.bak-JJJJMMTT` -> byte-genauer
   Ersatz (Rohbytes lesen, Zeilenende erhalten, `wb` schreiben) -> Beleg:
   `git diff --numstat` zeigt `1 1` bzw. `2 2`; zeigt es die ganze Datei,
   zuruecknehmen und neu patchen. Den Grund der Aenderung in den Erklaertext der
   Wache schreiben (jeder Wachen-Wert traegt seinen Grund) -> committen und
   pushen -> den naechsten Dauerlauf-Zyklus als Live-Beleg lesen.
10. **Grenzen der Aenderung nennen.** Ein Eingangsfilter wirkt nur auf NEUE
    Positionen; offene laufen unter ihren gebuchten Stops und Fristen aus. Die
    naechste Auswertung ist deshalb GEMISCHT und taugt nicht als Beweis der
    Wirkung — dafuer braucht es Tage neuer Positionen. Das sagen, statt eine
    Zahl zu deuten.

## Zweites Buch (Ausstiegsgeometrie, nur prospektiv)
Vorlage ist der Risikostufen-Lauf: derselbe Code, eigene Dateien je Ausfertigung
(`*.mittel.json`, eigenes Journal, eigene PID/Log), Eintrag in `SPUREN` UND in
`NUR_BASIS` (sonst laeuft die Spur doppelt). Fuer eine Ausstiegsvariante:
Startskript, das eine Kennung setzt; die Spur erweitert nur die Dateinamen; das
Hauptbuch bleibt UNVERAENDERT (es ist die Vergleichsgrundlage). Ein Arm je
Runde — zwei Arme gleichzeitig kosten den dreifachen Feed-Abruf je Zyklus und
verwaessern das Bild. Messzeitraum bis 30 Ausstiege je Arm. Billige Naeherung
fuer spaeter: `tiefster_kurs` je Position im Zustand mitschreiben (analog
`hoechster_kurs`) — grob, weil die Reihenfolge von Hoch und Tief nicht
rekonstruierbar ist.

## Pitfalls
- **In-Sample-Falle.** Alle Regeln stammen aus derselben Stichprobe; die
  Zeithalbierung mildert das, hebt es nicht auf. Ergebnis als Vorschlag
  ausweisen, nie als Beweis.
- **Auswahl nach Ergebnis ist die verfuehrerischste Regel** (nur Vorbilder mit
  belegter Bilanz kopieren). Ohne Zeithalbierung und Mindestzahl Runden je
  Wallet ist das Nachschau-Auswahl — im selben Datensatz kippt sie nach hinten.
- **Ein Auswertungswerkzeug schreibt nie in einen Spurenordner.** Test auf
  Tempjournalen mit bekanntem Ausgang, dazu ein Modulwaechter (`setUpModule`
  merkt Dateiliste und Groessen der Spurenordner, `tearDownModule` vergleicht)
  — sonst schreibt ein Testlauf ins echte Buch.
- **Der Dauerlauf ist der einzige Schreiber.** Nie einen Papierzyklus von Hand
  fahren; fuer eine Vorschau `--vorschau` benutzen (schreibt keinen Zustand).
- **Wegwerfskripte in den Arbeitsbaum legen** (`Agenten/Hermes/cache/`), nicht
  nach `%LOCALAPPDATA%\Temp`: ausserhalb `HERMES_WRITE_SAFE_ROOT` wird der
  Schreibvorgang verweigert.
- **Neue Ordner bleiben unversioniert, bis JEDE Whitelist-Ebene freigegeben ist**
  (`!Agenten/Handel/docs/` + `!.../docs/design/` + `!.../design/*.md`); Nachweis:
  `git status --porcelain` zeigt `??` statt `!!`.
- **Die Zeilenenden der .gitignore aus den Rohbytes ableiten** und mit demselben
  Terminator anhaengen; danach `git diff --numstat` pruefen (eine gewollte Zeile
  = `1 1`).

## Nachweis
Ein Optimierungsauftrag ist fertig, wenn (a) die Messung mit Stichprobenzahlen
vorliegt, (b) jede vorgeschlagene Regel beide Haelften und die Gegenprobe
ueberlebt hat oder ausdruecklich „nicht entschieden" lautet, (c) die
Spezifikation freigegeben und committet ist, (d) die Aenderung eine Sicherung
und einen sauberen Diff hat (`git diff --numstat`, gepusht), und (e) der
naechste echte Dauerlauf-Zyklus die Wirkung zeigt.

Regelkatalog, Werkzeugaufruf und Paritaetsprobe: `references/filter-studie.md`.
