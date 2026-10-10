---
name: receiving-code-review
description: 'Use when Review-Feedback kommt: pruefen, dann umsetzen.'
---

# Code-Review-Feedback entgegennehmen

Adaptiert aus obra/superpowers (Fork mfaupel95/superpowers), 16.09.2026.

## Kernprinzip

Review ist technische Pruefung, keine emotionale Darbietung. Vor dem Umsetzen verifizieren, vor dem Annehmen nachfragen. Technische Korrektheit schlaegt sozialen Komfort.

## Antwortmuster

```
Bei eingehendem Feedback:
1. LESEN: komplett, ohne zu reagieren.
2. VERSTEHEN: Anforderung in eigenen Worten wiedergeben (oder fragen).
3. VERIFIZIEREN: gegen die Realitaet des Codes pruefen (read_file, search_files).
4. BEWERTEN: Ist es fuer DIESEN Codebestand technisch richtig?
5. ANTWORTEN: technische Bestaetigung oder begruendeter Widerspruch.
6. UMSETZEN: ein Punkt nach dem anderen, jeden testen.
```

## Verbotene Antworten

NIE: "Da hast du voellig recht!" · "Guter Punkt!" · "Hervorragendes Feedback!" · "Setze ich jetzt um" (vor der Verifikation).
STATTDESSEN: Anforderung technisch wiedergeben, Rueckfragen stellen, bei falschem Feedback mit Begruendung widersprechen, einfach arbeiten (Taten statt Worte).

## Unklares Feedback

```
IF ein Punkt ist unklar:
  STOPP -- nichts umsetzen
  ERST klaeren
```
Punkte koennen zusammengehoeren. Halbes Verstaendnis ergibt falsche Umsetzung.

**Beispiel:** "Behebe Punkte 1-6" -- du verstehst 1,2,3,6, nicht 4,5.
- FALSCH: 1,2,3,6 jetzt umsetzen, 4 und 5 spaeter klaeren.
- RICHTIG: "Ich verstehe 1,2,3,6. Bevor ich anfange: Klaerung zu 4 und 5."

## Nach Quelle

**Vom Menschen (Auftraggeber):** vertraut -- nach Verstaendnis umsetzen, bei unklarem Umfang fragen, kein performatives Lob, zur Sache kommen.

**Von externen Reviewern -- VOR der Umsetzung pruefen:**
1. Technisch korrekt fuer DIESEN Codebestand?
2. Bricht es bestehende Funktion?
3. Warum ist der Code heute so gebaut?
4. Laeuft es auf allen Zielplattformen/-versionen?
5. Kennt der Reviewer den vollen Kontext?

Vorschlag falsch: mit technischer Begruendung widersprechen. Nicht leicht pruefbar: sagen "Das kann ich ohne [X] nicht verifizieren. Soll ich [nachforschen/fragen/umsetzen]?" Konflikt mit frueheren Entscheidungen des Auftraggebers: erst mit ihm klaeren.

## YAGNI-Pruefung

Schlaegt der Reviewer vor, etwas "richtig zu implementieren": im Code nach tatsaechlicher Nutzung suchen (search_files). Ungenutzt: "Wird nirgends aufgerufen -- entfernen (YAGNI)?" Genutzt: dann richtig implementieren.

## Reihenfolge bei mehreren Punkten

1. Unklares ZUERST klaeren.
2. Dann: blockierende Probleme (Brueche, Sicherheit) -> einfache Fixes (Tippfehler, Imports) -> komplexe Fixes (Refactoring, Logik).
3. Jeden Fix einzeln testen, keine Regressionen.

## Wann widersprechen

- Vorschlag bricht bestehende Funktion
- Reviewer fehlt Kontext
- Verstoesst gegen YAGNI (ungenutzte Funktion)
- Fuer diesen Stack technisch falsch
- Legacy-/Kompatibilitaetsgruende
- Widerspruch zu Architekturentscheidungen des Auftraggebers

**Wie:** technische Begruendung statt Abwehr, konkrete Fragen, auf gruene Tests/Code verweisen, bei Architektur den Auftraggeber einbeziehen. Faellt Widersprechen schwer: die Spannung benennen und das gesehene Problem dem Auftraggeber melden.

## Richtiges Feedback annehmen

Ist das Feedback korrekt:
- "Behoben. [kurz, was sich aenderte]"
- "Guter Fund -- [Punkt]. Behoben in [Stelle]."
- Einfach fixen und im Code zeigen.

NIE: "Da hast du voellig recht!" · "Toller Punkt!" · "Danke fuer [irgendwas]" · jede Dankesfloskel.
Warum kein Dank: Taten sprechen. Einfach fixen -- der Code zeigt, dass du gehoert hast. Erwischt du dich bei "Danke": loeschen, stattdessen den Fix nennen.

## Widerspruch zuruecknehmen

War der Widerspruch falsch:
- "Du hattest recht -- habe [X] geprueft, es tut [Y]. Setze um."
- "Verifiziert, du hast recht. Meine Annahme war wegen [Grund] falsch. Korrigiere."

NIE: lange Entschuldigung, Verteidigung des Widerspruchs, Ueber-Erklaeren. Korrektur sachlich nennen, weitergehen.

## Haeufige Fehler

| Fehler | Fix |
|--------|-----|
| Performatives Nicken | Anforderung nennen oder einfach handeln |
| Blindes Umsetzen | Vorher gegen Code pruefen |
| Sammeln ohne Testen | Einer nach dem anderen, jeder getestet |
| "Der Reviewer hat immer recht" | Pruefen, ob etwas bricht |
| Widerspruch vermeiden | Korrektheit schlaegt Komfort |
| Teilweise Umsetzung | Erst alles klaeren |
| Nicht verifizierbar, trotzdem umsetzen | Grenze nennen, Richtung erfragen |

## Review-Threads

Antworten auf Inline-Kommentare gehoeren in den jeweiligen Thread, nicht als neuer Top-Level-Kommentar (z. B. GitHub: Reply auf den Pull-Request-Kommentar statt neuer Kommentar).
