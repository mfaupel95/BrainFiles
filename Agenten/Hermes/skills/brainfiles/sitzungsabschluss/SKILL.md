---
name: sitzungsabschluss
description: "Use when eine Sitzungsaufgabe abgeschlossen wird."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Sitzung, Abschluss, Aufgabenliste, TASKS.md, Uebergabe]
    related_skills: [betriebsrunde, sammelauftrag, wiki-pflege, sichern, brainfiles-auftrag]
---

# Sitzungsabschluss — alles in die Aufgabe schreiben

Bringt EINE Sitzungsaufgabe zu Ende und schreibt **jeden** Punkt dorthin, wo er
wiederfindbar ist: erledigte Teilschritte, Messwerte, Entscheidungen mit Begruendung,
gefundene aber nicht behobene Maengel, absichtlich nicht angefasste Dinge und jeder
offene Punkt mit naechstem Schritt. Das ist kein Beleg-Lauf (dafuer `betriebsrunde`),
kein Sammeln fremder Sitzungen (`sammelauftrag`) und keine Lehrensammlung
(`wiki-pflege`) — es ist die Vollstaendigkeitspruefung am Ende, damit nichts im
Chatverlauf verschwindet.

Leitregel: **Ein Punkt, der nur im Chat steht, ist nach dem Sitzungsende weg.**
Deshalb gilt: nichts zusammenfassen, was einen eigenen Eintrag braucht; nichts
erfinden, was nicht belegt ist.

## When to Use

- "Sitzung abschliessen", "Aufgabe zu Ende bringen", "Task fertig", "/writung", "alles festhalten"
- "schreib alles in die Aufgabe, damit wir nichts vergessen"
- eine mehrteilige Aufgabe ist abgearbeitet und soll ihre Spur hinterlassen
- vor dem Beenden: offene Punkte, Entscheidungen und Nichtangefasstes sichern

**Don't use for:** Befunde einer Sitzung belegen und beheben (`betriebsrunde`),
Arbeit paralleler Sitzungen einsammeln (`sammelauftrag`), eine abgebrochene Sitzung
verstehen (`sitzungs-rekonstruktion`), nur committen (`sichern`).

## Prerequisites

- Arbeiten aus der Repo-Wurzel `BrainFiles/` (enthaelt `MaxHirn/`, `Agenten/`, `Werkstatt/`).
- Aufgabenliste: `MaxHirn/Archiv/TASKS.md` (CRLF, einzige Quelle fuer "was ist offen").
- Wiedervorlage: `MaxHirn/Wiki/Offen/Entscheidungen.md`.
- Vor jedem Schreibzugriff `MaxHirn/Wissen/Schutzregeln.md` lesen (Stufe 0/1/2).
- Kein Netz, kein Modell, keine neuen Abhaengigkeiten — stdlib und git.

## How to Run

1. `terminal` → Abschluss-Audit (nur lesend, Schritt 1):

```bash
python Agenten/Hermes/skills/brainfiles/sitzungsabschluss/scripts/abschluss_audit.py
```

2. `read_file`/`search_files` → je Befund die betroffene Stelle ansehen (Schritt 2–3).
3. `write_file`/`patch` → Aufgabenliste und Wiedervorlage fortschreiben (Schritt 4–5),
   Vorlage `templates/aufgaben-eintrag.md` (laden mit `skill_view`).
4. `terminal` → eigener Commit, nur eigene Pfade namentlich (Schritt 6).
5. Abschlussmeldung in vier Zeilen (Schritt 7) — keine Nacherzaehlung des Verlaufs.

## Quick Reference

| Was | Wo |
|---|---|
| offene Aufgaben, T-IDs | `MaxHirn/Archiv/TASKS.md`, Abschnitte `## Offen` / `## Erledigt` |
| wartet auf Max | `MaxHirn/Wiki/Offen/Entscheidungen.md` |
| Lehre mit Merksatz | `MaxHirn/Wiki/Lektionen/*` (+ `Wiki/INDEX.md` nachziehen) |
| Zahl/Befund zu Max | `MaxHirn/Wissen/` (+ `Wissen/INDEX.md`) |
| einmalige Uebergabe | `Werkstatt/Austausch/<JJJJ-MM-TT>/<thema>.md` |
| Verfahren | Skill unter `Agenten/Hermes/skills/` |
| meine Aenderungen | `git status --porcelain`, `git diff --numstat` |
| Abschluss-Audit | `scripts/abschluss_audit.py` (nur lesend) |
| Vorlage Eintrag | `templates/aufgaben-eintrag.md` |

Status-Kuerzel der Aufgabenliste: `[ ]` offen · `[~]` in Arbeit · `[?]` wartet auf
Entscheidung · `[!]` blockiert · `[x]` erledigt (gehoert nach `## Erledigt`).

## Procedure

### 1. Audit fahren (lesend, 1 Minute)

```bash
python Agenten/Hermes/skills/brainfiles/sitzungsabschluss/scripts/abschluss_audit.py --seit 360
```

Es meldet: uncommittete Pfade, in den letzten `--seit` Minuten angefasste Dateien,
letzte Commits, nicht gepushte Commits, Befunde in `TASKS.md` (doppelte/fehlende IDs,
Eintraege im falschen Abschnitt, fehlende Pflichtfelder, `[x]` unter `## Offen`),
Zustand von `Wiki/Offen/Entscheidungen.md`, `ENDE FEHLER` in `Routinen/logs/` und
Aufgaben ohne Fortschritt > 14 Tage. Es schreibt nichts und kopiert nichts.

### 2. Session-Inventar bilden

Jeden Schritt der Sitzung durchgehen und in eine der fuenf Zeilen einsortieren:

| Was entstanden ist | Eintrag als |
|---|---|
| Teilschritt erledigt (Datei, Test, Commit) | Erledigt-Vermerk mit Datum + Beleg (Befehl/Datei) |
| Messwert, Zustand, Zahl | `Wissen/`-Notiz oder Kontextzeile im Aufgabeneintrag |
| Entscheidung mit Begruendung | Kontext im Aufgabeneintrag, Begruendung woertlich |
| Mangel gefunden, nicht behoben | eigener Punkt mit Status `[ ]` oder `[!]` |
| absichtlich NICHT angefasst | Kontextzeile "Nicht angefasst: … weil …" |

Vollstaendigkeitsprobe (die vier Fragen, die Punkte aufdecken):
**Was habe ich geaendert und wo? Was habe ich gemessen? Was habe ich absichtlich
liegen gelassen? Worauf wartet jemand anderes?**

### 3. Vor dem Schreiben gegenpruefen

- War der Punkt schon eingetragen? `search_files` ueber `MaxHirn/Archiv/TASKS.md` nach
  Stichwort **und** nach der Datei/Spur — ein vorhandener Eintrag wird fortgeschrieben
  (Status, `Zuletzt:`), nicht doppelt angelegt.
- Ist der Punkt wirklich offen? Was die Sitzung erledigt hat, wandert nach `## Erledigt`.
- Ist der Punkt wirklich einer von Max? Nur dann in `Wiki/Offen/Entscheidungen.md`.

### 4. Aufgabenliste fortschreiben

Format aus `TASKS.md` woertlich uebernehmen (Abschnitt `## Eintragsformat`),
ID fortlaufend und **nie wiederverwendet**:

```
- [ ] **T-049 — Kurztitel**
      Kontext: worum es geht, warum es offen ist; Messwerte mit Datum
      Naechster Schritt: eine konkrete, ausfuehrbare Handlung
      Angelegt: 2026-09-22 · Zuletzt: 2026-09-22
```

Optional `Betrifft:` (Pfad/Projekt/Geraet) und `Wartet auf:` (Pflicht bei `[?]`/`[!]`).
Erledigtes: Kuerzel `[x]`, **Erledigt-Datum in Fettschrift** an den Anfang des Kontexts,
und den ganzen Block nach `## Erledigt` verschieben — mit Datum, nie loeschen.

Schreibweg: die Datei ist **CRLF**. Byte-sicher aendern (`open(pfad,'rb')`, Zeilenende
aus dem ROHEN Text ableiten, `open(pfad,'wb')`) oder gezielt mit `patch`; danach
`git diff --numstat MaxHirn/Archiv/TASKS.md` — eine gewollte Einfuegung zeigt
wenige Zeilen, ein Zeilenende-Fehler zeigt die ganze Datei.

### 5. Wiedervorlage und Ablagen nachziehen

- `MaxHirn/Wiki/Offen/Entscheidungen.md`: nur Punkte, die auf Max warten; je Punkt
  Messung + naechster Schritt; Erledigtes **loeschen** (Historie liegt in Git) und
  `updated:` im Kopf ziehen.
- Eine Lehre, die in einem Monat noch gilt: Wiki-Seite nach `wiki-pflege`.
- Ein Verfahren, das wiederkehrt: Skill (dieser Abschluss kann der Ausloeser sein).
- Neue Ordner brauchen die `.gitignore`-Freigabe — Gegenprobe
  `git check-ignore -v <pfad>` (sonst ist der Eintrag unsichtbar).

### 6. Sichern, getrennt

```bash
git status --porcelain                     # erst ansehen, dann stagen
git add <eigene Pfade>                     # namentlich, NIE git add -A
git diff --cached --stat
git commit -m "<typ>(<bereich>): <was>"
```

Fremde Aenderungen im Baum: eigener Commit mit
`--author="Andere Sitzung <fremd@local>"`, nie vermischt. Dateien, die in den letzten
10 Minuten geschrieben wurden, liegen lassen.

### 7. Abschlussmeldung (vier Zeilen, keine Nacherzaehlung)

1. **Was jetzt funktioniert** — konkret und nachpruefbar (Befehl/Datei).
2. **Was absichtlich nicht angefasst wurde** — und warum.
3. **Was noch eine Entscheidung von Max braucht** — mit den Zahlen.
4. **Genau eine naechste Aktion** unter zwei Minuten.

Dazu die Gegenprobe nennen: `scripts/abschluss_audit.py` ... Befunde, und ein
Pu/Commit-Hash.

## Pitfalls

- **Der Chatverlauf ist kein Beleg.** Jeder Eintrag braucht Datei, Befehl oder Lauf;
  sonst verwerfen und unter "nicht aufgenommen" nennen.
- **Nichts erfinden.** Nur was Max gesagt hat oder tatsaechlich offen blieb;
  vermutete Folgeaufgaben gehoeren als Vorschlag in die `Kontext:`-Zeile.
- **Doppelte ID / wiederverwendete ID** ist ein Datenfehler — Audit meldet es; neue ID
  ist immer `hoechste + 1`.
- **`[x]` unter `## Offen`** heisst: Block wurde nicht verschoben. Kein Schoenheitsfehler,
  die Statuszeile ist dann falsch lesbar.
- **Nicht in `Wiki/Offen/` ablegen**, was ein Agent selbst entscheiden kann — die Seite
  ist eine Wiedervorlage fuer Max, kein Auftragszettel.
- **`Werkstatt/` ist eine Junction** (auf `O:\Werkstatt`): `write_file` lehnt den Pfad ab
  ("outside HERMES_WRITE_SAFE_ROOT") — ueber das `terminal`-Werkzeug schreiben.
- **Zugangsdaten nirgends** — auch nicht gekuerzt; es gibt genau eine Ablage
  (`MaxHirn/Wissen/Zugaenge.md`, Stufe 0).
- **Nach dem Abschluss nicht in Verifikations-/Memory-Schleifen laufen.** Eine belegte
  Messung + ein Commit reichen. Wiederholte identische Pruefungen (`carry.py`-Laeufe,
  Wache, `memory add` mit demselben Text) liefern keine neue Information, `memory`
  meldet dann "Entry already exists (no duplicate added)" und der Lauf endet im
  Tool-Loop-Hard-Stop. Abschlussmeldung einmal schreiben, dann aufhoeren.
- **Kein Push ohne Auftrag**, kein `git reset --hard`/`checkout -- <datei>`/`stash`:
  das loescht fremde Arbeit unwiederbringlich.
- Bekannter Bestand in `TASKS.md`: der Abschnitt `## Regeln` enthaelt einen
  Aufgabeneintrag (T-044) und die Formatvorlage enthaelt das Beispiel `T-001`.
  Das Audit ueberspringt Code-Bloecke, meldet aber Eintraege ausserhalb von
  `## Offen`/`## Erledigt` — Befund melden, Format nicht nebenbei umbauen.

## Verification

```bash
python Agenten/Hermes/skills/brainfiles/sitzungsabschluss/scripts/abschluss_audit.py | tail -5
git status --porcelain
```

Bestanden, wenn die Zusammenfassung des Audits `0 Befunde` meldet (oder jeder
verbleibende Befund in der Abschlussmeldung benannt ist), die eigene Arbeit
committet ist und `git diff --numstat` bei den Textaenderungen nur die beabsichtigten
Zeilen zeigt.
