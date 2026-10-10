---
name: codeagent-uebernahme
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [Codeagent, OpenCode, Review, Uebergabe]
description: "Beauftragt Codeagenten und prueft deren Abgabe selbst."
---

# Codeagent beauftragen und Abgabe pruefen

Uebergibt Coding-Arbeit an einen CLI-Codeagenten (OpenCode), prueft dessen
Abgabe strenge und fixt Defekte selbst, statt sie zu glauben. Gilt NICHT
fuer delegate_task-Subagenten (dafuer: Skill subagent-delegation).

## When to Use

- Max sagt "coding arbeit an <agent> abgeben" oder nennt ein Modell/Werkzeug
  als Uebergabe-Ziel.
- Ein Codeagent liefert einen Abschlussbericht - IMMER vor Uebernahme pruefen.
- Ein gemischter Commit (eigene + fremde Arbeit in einem) ist zu entwirren.

## Prerequisites

- `opencode` CLI installiert und angemeldet
  (`~/.local/share/opencode/auth.json` listet die Authentifizierungen nach
  PROVIDER-NAMEN; `~/.config/opencode/opencode.jsonc` haelt die custom
  Provider - dort steht der Hausweg `omniroute` = lokaler Router auf
  http://localhost:20128/v1 mit Modellpfaden `omniroute/auto/*`, `no-think/*`).
  Aus der .jsonc nur Namen/BaseURL/Modellpfade lesen, NIE apiKey-Werte.
- Brief als Datei, nie als Inline-Argument; Ablage im Scratch-Ordner.
- Keine Schluessel noetig; die Zen-Gratis-Modelle (Namen mit `-free`) kosten nichts.

## How to Run

Modellweg zweistufig testen, dann der echte Lauf im Hintergrund - alles
durch das `terminal`-Werkzeug, Arbeitsverzeichnis ist der Ziel-Ordner
(z. B. `Agenten/Handel`):

```
opencode run --model <provider/model> "Antworte mit genau einem Wort: bereit"
opencode run --model <provider/model> "Lies zunaechst <BRIEF-PFAD> - er ist der VOLLSTAENDIGE Auftrag; beantworte NUR: welcher Task ist der erste und welche Datei betrifft er?"
opencode run --model <provider/model> "Lies zunaechst <BRIEF-PFAD> - er ist der VOLLSTAENDIGE Auftrag..."
```

Schritt 1 (Ping) prueft nur den Transport. Schritt 2 (Mini-Lauf mit einem
echten Stueck des Prompts) prueft die Combo unter Last - ein Ping kann
gruen sein, waehrend der volle Lauf mit "Maximum combo retry limit reached"
abbricht. Erst wenn beide gruen sind, den echten Lauf (Schritt 3) starten.

## Quick Reference

- `opencode models` - Modellliste.
- `opencode run --model <m> "..."` - Einzellauf, nicht interaktiv.
- Agent-Log: `~/.local/share/opencode/log/opencode.log` (UTC-Zeitstempel).
- Auth: `~/.local/share/opencode/auth.json` (nur Schluesselnamen lesen, nie Werte).

## Procedure

1. **Aufgabe waehlen, dann Brief schreiben** (Werkzeug `write_file`):
   bei Sammelauftraegen ("alle Tasks, die keine Entscheidung brauchen")
   die Auswahl mit `references/task-auswahl.md` treffen (Block-Parsing,
   Klassifikation an den "Naechster Schritt"-Zeilen, Abhaengigkeits-Check).
   Brief: Ziel, Regeln - nicht verhandelbar: Signal/Logik UNVERAENDERT,
   Sperren unangetastet, PAPER zuerst, kein Commit, Tests ohne Netz,
   Belegfeld im Journal -, technische Vorgaben, Abgabeform.
2. **Modellweg ermitteln, nicht raten**: custom Provider zuerst aus
   `~/.config/opencode/opencode.jsonc` lesen (Hausweg omniroute), dann
   `opencode models`, dann zweistufiger Test (Ping + Mini-Lauf, siehe
   How to Run); im Fehlerfall naechster Kandidat.
   **Fallback, wenn kein Weg stabil laeuft**: nach 2-3 fehlgeschlagenen
   Wegen (Combo-Retry-Limit, Abbruch nach dem ersten Satz) NICHT weiter am
   Modellweg laborieren - die Arbeit ist ausfuehrbar, nur das Uebergabe-
   Tool ist es gerade nicht. Die Tasks dann selbst abarbeiten (gleiche
   Regeln: PAPER, kein Commit fremder Pfade, Tests ohne Netz, Beleg) und
   dem Nutzer sagen, dass die Uebergabe am Modellweg scheiterte und die
   Arbeit direkt erledigt wurde. Der Skill-Zweck ist die gepruefte
   Uebernahme, nicht das Tool um jeden Preis.
3. **Start im Hintergrund** (`terminal` mit background=true + notify),
   Brief-PFAD im Prompt nennen.
4. **Fortschritt beobachten**: `git status --porcelain <ordner>` und
   `~/.local/share/opencode/log/opencode.log`; den Bericht nie glauben,
   bevor Schritt 5 fertig ist.
5. **Bericht gegenpruefen** (jede Aussage):
   - Tests SELBST laufen lassen; die Zahl im Bericht ist kein Beleg.
   - `git diff --numstat` je Datei - stimmt der behauptete Umfang?
   - Erfundene API: jedes vom neuen Code gerufene Symbol mit
     `search_files` gegen die echte Quelle (`def <name>`) suchen.
   - Regelverstoessuche: hat der Agent trotz "ohne Netz" echte Prozesse/
     Netzaufrufe hinterlassen (eigene Logdateien, pid-Dateien,
     Journalzeilen mit neuen Spaltenwerten)?
   - `git log -1 -- <pfad>`: hat er trotz Verbot committet (ggf. fremde
     Arbeit im selben Commit)?
6. **Datenschaeden zuerst klaren**: Bei Schemaaenderungen (Journalspalten)
   Zeilenlaengen-Counter in der echten Datei messen, verlorene Werte aus
   sekundaeren Quellen zurueckholen (Zustand, Boerse, Backup), Migration nur
   mit .bak-JJJJMMTT-Sicherung und Gegenprobe (Zeilenzahl, Spaltenlaengen,
   Stichprobe).
7. **Selbst fixen**: kleine, gezielte `patch`-Schritte; nach jedem Lauf die
   Suite; die Agent-Arbeit ist Geruest, nicht Wahrheit. FALLE (gemessen
   07.10.2026): das fuzzy patch-Werkzeug kann bei einem Block mit
   ungleichmaessiger Einrueckung Tippfehler EINFUEGEN ("pre preis_fuer",
   "aus ausstieg") und die Einrueckung verschieben - nach dem ERSTEN
   IndentationError nicht weiterpatchen, sondern den Block byte-genau per
   Python-Skript ersetzen (Zeilen per Index finden, Block-Liste neu
   schreiben, `py_compile` vor dem Schreiben) oder die Datei komplett neu
   schreiben. Ein fuzzy patch, das zweimal denselben Fehler erzeugt, ist
   das Signal fuer den byte-genauen Weg.
8. **Commit NUR eigene Pfade** (explizites `git add`, nie `-A`), Meldung
   nennt die Fix-Runde; Push erst nach gruenen Suiten.

## Pitfalls

- **Der Abschlussbericht ist unzuverlaessig** (gemessen 02.10.2026):
  "10/10 OK" war real FAILED (fehlendes Paket im venv); eine behauptete
  Codeaenderung fehlte ganz; ein gerufenes Symbol (`handeln.groessenfaktor`)
  existierte nicht. Jede Zahl im Bericht nachfahren.
- **Exit-Code 0 des Hintergrundlaufs ist KEIN Abschluss**: der Prozess
  kann mit 0 enden, nachdem er nur den ersten Satz des Prompts ausgab und
  dann still abbrach - kein Tool-Aufruf, keine Dateiaenderung, kein
  Commit (gemessen 07.10.2026: Ausgabe war nur "Ich lese die Datei...",
  `git status --porcelain` leer). Abschluss heisst: `git status` zeigt
  die erwarteten Aenderungen UND das Agent-Log zeigt Tool-Aufrufe nach
  dem ersten Satz. Erst dann gegenpruefen.
- **Agent committet trotz Verbot** - und nimmt vorgemerkte fremde Arbeit mit
  (gemessen: der Agent-Commit enthielt die USDC-Arbeit einer Parallelsitzung).
  Nach dem Lauf `git log -1 -- <pfad>` pruefen.
- **"Tests ohne Netz" wird uebergangen**: der Agent startete die gebaute
  Spur gegen den echten Feed (Logbeleg). Sein eigener Log-/Journal-Schmutz
  ist der Beweisweg.
- **Modellweg bricht laut - Fehlerklasse zaehlt, nicht die Meldung**:
  je Klasse anderer naechster Schritt. "Maximum combo retry limit reached"
  (server_error) = die auto/*-Combo loest gerade nicht auf - anderen Zweig
  waehlen (z. B. auto/coding statt auto/best-coding); ein Ein-Wort-Ping kann
  gruen sein, waehrend derselbe Weg beim vollen Lauf abfaellt, deshalb vor
  dem echten Lauf der Mini-Lauf (How to Run). "No active credentials for
  provider: X" = der Provider im Pfad hat keine Keys - Provider wechseln,
  nicht denselben Pfad wiederholen. HTTP 502 ("Stream ended before
  producing a non-ping SSE event") = Router-Zweig tot - naechster
  Kandidat. 401/403 = Key/Rechte. Reihenfolge: Gratis-Modell vor
  Bezahlmodell, im Fehlerfall naechster Weg (nicht denselben dreimal).
- **Auch der Mini-Lauf ist kein Beleg fuer den vollen Lauf**: die
  auto/*-Combo-Aufloesung ist lastabhaengig - ein Weg, der Ping UND
  Mini-Lauf (liest den Brief, arbeitet) gruen besteht, kann beim vollen
  Hintergrundlauf mit "Maximum combo retry limit reached" abfallen
  (gemessen 07.10.2026: auto/coding:fast bestand beide, der echte Lauf
  starb). Verlaesslich ist ein Weg, der auf ein KONKRETES externes Modell
  aufloest (z. B. auto/glm -> zai-org/glm-5.2) statt auf eine Combo, die
  je Last neu waehlt. Vor dem Start den Router direkt fragen, welches
  Modell der Weg aufloest (`/v1/models` + Chat-Completion-Probe mit einem
  realistisch langen Prompt inkl. Tool-Aufruf), nicht nur den Ein-Wort-Ping.
- **PowerShell-Einzeiler aus bash**: `$var`/`$_` werden von bash
  verschluckt oder brechen den Parser - Skript als .ps1-Datei schreiben und
  mit `-File` aufrufen, nie als `-Command` einbetten.
- **Migration ohne Backup trunciert die Datei**: `open('w')` kuerzt, BEVOR
  `writerows` laufen kann - ein Fehler mitten drin hinterlaesst eine halbe
  Datei. Immer zuerst .bak, immer Gegenprobe (Zeilenzahl).
- **Agent bearbeitet Live-Code waehrend des Laufs**: Die Spur-Skripte
  starten je Zyklus neu - ein halbfertiges handeln.py bricht den
  LIVE-Zyklus ("Rueckgabe 1" im dauerlauf.log). Im Zeitfenster des
  Agent-Laufs den dauerlauf.log auf Crashs pruefen.
- **Tests fassen keine echten Laufzeitdateien an** (pid, Log, Journal):
  eine pid-Pruefung in einem Test hinterliess sonst eine verwaiste Sperre,
  die einen echten Start blockiert.
- **Eine Test-Attrappe ohne die volle Seam-Flaeche faellt auf das ECHTE
  Modul zurueck**: wenn der Code eine Methode neu aufruft, die die Attrappe
  nicht kennt, laeuft die Funktion ueber den Modul-Fallback weiter und
  macht einen ECHTEN Netzaufruf (gemessen: `stopdeckung.deckung()` laedt
  das echte okxf, wenn `stopdeckung.okxf` nicht gesetzt ist -> OKX 51001
  im Test). Beim Erweitern einer Funktion, die ein Modul-Attribut als
  Testnaht nutzt, DAS Attribut auf die Attrappe setzen und der Attrappe
  jede neu gerufene Methode geben; der Test muss beweisen, dass nichts an
  den echten Host geht.
- **Ein Test, der einen Literal-Text im Quelltext sucht (Gegenprobe),
  bricht, wenn die Meldung umformuliert wird**: verbessert man die Logik
  und aendert dabei den Text (z. B. "KEINE Fuellung gelesen" ->
  "KEINE Kauf-Fuellung gelesen"), muss man BEIDE Stellen anpassen - die
  Verhaltens-Assertion UND die Quelltext-Suche der Gegenprobe. Ein roter
  Test, der nach dem alten Text sucht, ist kein Codeproblem, sondern eine
  veraltete Gegenprobe.

## Verification

```powershell
cd Agenten/Handel/scanner && .venv/Scripts/python.exe -m unittest discover -s tests -t tests
```

Plus: `git log -1 --oneline` zeigt den eigenen Fix-Commit; der
Agent-Bericht wurde in jedem Punkt gegengeprueft (Schritt 5).
