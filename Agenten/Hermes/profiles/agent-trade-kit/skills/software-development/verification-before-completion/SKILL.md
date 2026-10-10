---
name: verification-before-completion
description: 'Use when Arbeit fertig melden: erst verifizieren.'
---

# Verifikation vor Fertigmeldung

Adaptiert aus obra/superpowers (Fork mfaupel95/superpowers), 16.09.2026.

## Kernprinzip

**Evidenz vor Behauptung, immer.** Wer den Buchstaben umgeht, verletzt den Geist.

**Eiserne Regel:** KEINE FERTIG-BEHAUPTUNG OHNE FRISCHE VERIFIKATIONS-EVIDENZ. Wer den Verifikationsbefehl nicht in dieser Nachricht ausgefuehrt hat, darf nicht behaupten, dass etwas gruen ist.

## Das Tor (vor jeder Behauptung)

```
1. BENENNEN: Welcher Befehl beweist diese Behauptung? (Test, Build, Linter)
2. AUSFUEHREN: Den VOLLSTAENDIGEN Befehl frisch laufen lassen (terminal).
3. LESEN: Ganze Ausgabe, Exit-Code, Fehleranzahl pruefen.
4. PRUEFEN: Bestaetigt die Ausgabe die Behauptung?
   - Nein: Ist-Zustand mit Beleg nennen.
   - Ja: Behauptung MIT Beleg nennen.
5. ERST DANN: Behaupten.
```
Jeder uebersprungene Schritt ist Luegen, nicht Verkuerzen.

## Haeufige Fehler (Behauptung -> noetiger Beleg)

| Behauptung | Erfordert | Nicht ausreichend |
|------------|-----------|-------------------|
| Tests gruen | Testlauf: 0 Fehler | Frueherer Lauf, "sollte passen" |
| Linter sauber | Linter-Ausgabe: 0 Fehler | Teilpruefung, Hochrechnung |
| Build ok | Build-Befehl: Exit 0 | Linter gruen, Logs sehen gut aus |
| Bug behoben | Ursprungssymptom laeuft gruen | Code geaendert, angenommen |
| Aufgabe erledigt | VCS-Diff zeigt die Aenderungen | Agent meldet "Erfolg" |
| Anforderungen erfuellt | Checkliste Punkt fuer Punkt | Tests gruen |

## Stopp-Fahnen

- Woerter wie "sollte", "wahrscheinlich", "scheint"
- Zufriedenheit vor Verifikation ("Super!", "Perfekt!", "Fertig!")
- Commit/Push/PR ohne Verifikation
- Agenten-Erfolgsmeldungen blind glauben: selbst den Diff pruefen (terminal/git)
- Teilpruefung als Beweis; "nur dieses eine Mal" als Denkmuster
- Muedigkeit, die Arbeit abschliessen zu wollen
- JEDE Formulierung, die Erfolg andeutet, ohne dass Verifikation gelaufen ist

## Rationalisierungen entlarven

| Ausrede | Realitaet |
|---------|-----------|
| "Sollte jetzt funktionieren" | Verifikation laufen lassen |
| "Ich bin sicher" | Sicherheit ist kein Beleg |
| "Nur diesmal" | Es gibt keine Ausnahmen |
| "Linter war gruen" | Linter ist kein Compiler |
| "Der Agent sagte Erfolg" | Selbst pruefen |
| "Ich bin muede" | Muedigkeit ist keine Ausrede |
| "Teilpruefung reicht" | Teil beweist nichts |
| "Andere Worte, Regel gilt nicht" | Geist ueber Buchstaben |

## Schluesselmuster

- **Tests:** [Testbefehl laufen lassen, "34/34 gruen" sehen] -> "Tests gruen". Nicht: "Sollte passen".
- **Regression (Red-Green):** Test schreiben -> gruen -> Fix zurueckbauen -> Test MUSS rot sein -> Fix wiederherstellen -> gruen. Ohne Rot-Phase beweist der Test nichts.
- **Build:** [Build laufen lassen, Exit 0 sehen] -> "Build gruen". "Linter gruen" prueft keine Kompilierung.
- **Anforderungen:** Plan lesen -> Checkliste -> jede einzeln verifizieren -> Luecken oder Abschluss melden.
- **Delegation:** Agent meldet Erfolg -> Diff pruefen -> Aenderungen verifizieren -> Ist-Zustand melden.

## Wann anwenden

IMMER vor: jeder Erfolgs- oder Abschlussmeldung, jeder Zufriedensaesserung, Commit/Push/PR, Uebergang zur naechsten Aufgabe, Delegation an Agenten.

Gilt fuer exakte Formulierungen, Synonyme, Paraphrasen und jede Andeutung von Erfolg oder Korrektheit.
