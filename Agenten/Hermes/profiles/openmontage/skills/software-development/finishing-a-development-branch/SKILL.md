---
name: finishing-a-development-branch
description: 'Use when Integration ansteht: Optionen bieten.'
---

# Entwicklungszweig abschliessen

Adaptiert aus obra/superpowers (Fork mfaupel95/superpowers), 16.09.2026.

## Ablauf

Tests verifizieren -> Umgebung erkennen -> Basis-Zweig bestimmen -> Optionen anbieten -> Auswahl ausfuehren -> aufraeumen.

## Schritt 1: Tests verifizieren

Die VOLLSTAENDIGE Test-Suite des Projekts laufen lassen (terminal; je nach Stack pytest, npm test, cargo test, go test ...).

**Tests fehlgeschlagen:** Fehler mit Anzahl melden, nicht abschliessen. Das Menue kommt erst bei gruener Suite.
**Tests gruen:** weiter zu Schritt 2.

## Schritt 2: Umgebung erkennen

Vor jeder Verzeichnis-Aenderung merken: Normal-Repo oder Git-Worktree (`git rev-parse --git-dir` vs. `--git-common-dir`), Arbeitsbaum-Pfad (`git rev-parse --show-toplevel`), HEAD-Zustand.

| Zustand | Menue | Aufraeumen |
|---------|-------|------------|
| Normal-Repo (git-dir == common-dir) | 3 Optionen | nichts zu raeumen |
| Arbeitsbaum mit benanntem Zweig | 3 Optionen | nach Herkunft (Schritt 6) |
| Detached HEAD (extern verwaltet) | 2 Optionen (kein Merge) | liegen lassen |

## Schritt 3: Basis-Zweig bestimmen

Basis = Zweig, von dem die Arbeit abging (Plan, Gespraech oder Upstream des Zweigs). Nicht bekannt: fragen. Vor dem Mergen bestaetigen -- falsche Basis ist teuer rueckgaengig zu machen.

## Schritt 4: Optionen anbieten

**Normal-Repo oder benannter Arbeitsbaum -- exakt diese 3 Optionen:**
```
Implementierung abgeschlossen. Was soll ich tun?

1. Lokal in <basis-zweig> mergen
2. Pushen und Pull-/Merge-Request erstellen
3. Zweig lassen wie er ist (spaeter erledigen)

Welche Option?
```

**Detached HEAD -- exakt diese 2 Optionen:**
```
Implementierung abgeschlossen. Du bist auf detached HEAD (extern verwalteter Arbeitsbereich).

1. Als neuen Zweig pushen und Pull-/Merge-Request erstellen
2. Lassen wie er ist (spaeter erledigen)

Welche Option?
```

Menue wortgetreu, knapp, jede Option aus der Liste. Verwerfen passiert NUR auf ausdrueckliche Bitte. Auf die Antwort warten: Die Integrations-Entscheidung liegt beim Auftraggeber.

## Schritt 5: Auswahl ausfuehren

**Option 1 -- Lokal mergen:** In den Basis-Zweig wechseln (checkout), pullen, Feature-Zweig mergen, DANN auf dem gemergten Stand die Test-Suite laufen lassen.
- Gruen: Arbeitsbaum raeumen (Schritt 6), Zweig loeschen (`git branch -d <zweig>`).
- ROT auf dem Merge-Ergebnis: anhalten, Arbeitsbaum und Zweig in Ruhe lassen, untersuchen. Nichts ist gepusht -- der Merge ist lokal und rueckholbar.

**Option 2 -- Pushen + PR:** `git push -u origin <zweig>` (bei detached HEAD: `git push origin HEAD:refs/heads/<neuer-zweig>`). Dann Pull-/Merge-Request gegen den Basis-Zweig ueber das Werkzeug der Forge (CLI oder die beim Push gezeigte Erstell-URL), Template und Konventionen des Repos beachten, URL melden.
Arbeitsbaum BEHALTEN -- PR-Feedback wird dort bearbeitet.

**Option 3 -- Lassen:** Melden: "Zweig <name> bleibt. Arbeitsbaum erhalten unter <pfad>."

**Verwerfen (nur auf ausdrueckliche Bitte):** Konsequenzen bestaetigen lassen -- was geloescht wird: Zweig <name>, alle Commits <liste>, Arbeitsbaum <pfad>. Exakte Bestaetigung (z. B. "discard") abwarten, dann Arbeitsbaum raeumen (Schritt 6) und `git branch -D <zweig>`.

## Schritt 6: Aufraeumen

Laeuft fuer Option 1 und bestaetigtes Verwerfen. Optionen 2 und 3 erhalten den Arbeitsbaum immer. Raeumen vom Haupt-Repo-Root aus, nicht aus dem Arbeitsbaum.

- Normal-Repo: nichts zu raeumen, fertig.
- Arbeitsbaum unter `.worktrees/` oder `worktrees/`: `git worktree remove <pfad>` und `git worktree prune` (raeumt veraltete Eintraege).
- Sonstiger Pfad: gehoert der Host-Umgebung -- liegen lassen.

## Kurzreferenz

| Option | Merge | Push | Arbeitsbaum bleibt | Zweig weg |
|--------|-------|------|--------------------|-----------|
| 1. Lokal mergen | ja | - | ja (sanft) |
| 2. PR erstellen | - | ja | ja | - |
| 3. Lassen | - | - | ja | - |
| Verwerfen (nur ausdruecklich) | - | - | - | ja (force) |

## Rationalisierungen

| Ausrede | Realitaet |
|---------|-----------|
| "Tests waren vorhin gruen" | Auf genau dem Baum laufen lassen, der integriert wird |
| "Sie wollen es offensichtlich gemergt" | Integration entscheidet der Auftraggeber: Menue zeigen, warten |
| "'Ja, weg damit' zaehlt als Bestaetigung" | Nur die exakte Bestaetigung erlaubt Loeschen |
| "PR ist oben, der Arbeitsbaum ist Ballast" | PR-Feedback wird dort gefixt; er bleibt bis zur Uebernahme |
| "Dieser andere Arbeitsbaum wirkt veraltet" | Nur unter .worktrees/ oder worktrees/ raeumen; alles andere gehoert dem Host |
| "Merge-Fehler ist sicher flaky" | Rotes Merge-Ergebnis stoppt alles |
| "Basis ist offensichtlich main" | Abzweig-Punkt bestaetigen; falsche Basis ist teuer |
| "Push abgelehnt -- force-pushen" | Abgelehnter Push heisst: Remote hat sich bewegt. Untersuchen; force-push nur auf ausdrueckliche Bitte |
