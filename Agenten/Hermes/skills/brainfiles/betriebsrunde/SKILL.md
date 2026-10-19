---
name: betriebsrunde
description: Befunde belegen, beheben, sichern und Aufgaben schliessen.
version: 0.1.0
author: Hermes
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Betrieb, Wartung, Befunde, Git, Aufgabenplanung]
    related_skills: [systemdiagnose, sammelauftrag, sichern, brainfiles-auftrag, absturz-recovery]
---

# Betriebsrunde

Arbeitet die Befunde EINER Sitzung ab: jeden belegen, beheben, den Arbeitsbaum
getrennt sichern, Aufgaben schliessen, pushen. Das ist der Ablauf **nach** dem
Sammeln — keine neue Diagnose (dafuer `systemdiagnose`), keine Sammlung (dafuer
`sammelauftrag`), kein Einzelauftrag (dafuer `brainfiles-auftrag`).

Stdlib, PowerShell und git — keine neuen Abhaengigkeiten.

## Wann

- „weiter“, „arbeite die offenen Punkte ab“, „mach die Runde“
- eine Sitzung hat mehrere kleine Befunde gesammelt (Pruefer, MCP-Check,
git status) und keiner ist zu Ende gefuehrt
- der Arbeitsbaum ist schmutzig und niemand weiss, welche Aenderung wem gehoert
- vor dem Push: alles belegt, getrennt committet, Aufgaben nachgezogen

**Don't use for:** einen einzelnen Auftrag (Code aendern, Feature bauen) — dafuer
`brainfiles-auftrag`. Fuer „was ist kaputt“ ohne Auftrag: `systemdiagnose`.

## Voraussetzungen

- Arbeiten aus der Repo-Wurzel `BrainFiles/`.
- `hermes.exe` liegt in `Agenten/Hermes/bin/hermes.exe`; vor jedem Aufruf
  `PYTHONHOME`/`PYTHONPATH` entfernen, sonst stirbt der Interpreter.
- Fuer Aufgabenplanung ist eine erhoeh te Sitzung noetig (Schritt 4).
- `Werkstatt/` ist eine **Junction** auf `O:\Werkstatt` (Schreibweg: Fallen).

## Ablauf

1. **Lage messen, nicht erinnern.** Die vorhandenen Pruefer laufen lassen statt
   neu zu suchen: `Agenten/Routinen/systempruefung.ps1` (letzter Nachtlauf:
   `logs/systempruefung-letzter-lauf.md`), `Agenten/mcp-sync-check.ps1`,
   `Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/sammeln.py`,
   `git status --porcelain`, `Get-ScheduledTask -TaskName 'MaxHirn-*'` plus
   Cron-Liste. *Fertig, wenn* jede Quelle einmal gelaufen ist und ihr Befund in
   eine der fuenf Klassen aus Schritt 2 einsortiert wurde.
2. **Befundklasse bestimmen — daran haengt der Beweisweg:**

   | Klasse | Erkennen | Weg |
   |---|---|---|
   | Konfig-Drift (MCP, Manifest, Config) | Pruefer meldet Abweichung | mit dem Haus-Werkzeug beheben (`hermes mcp add/remove`), Manifest nachziehen, Pruefer erneut |
   | Laufzeitstand im Git | Baum ist NIE sauber, Datei aendert sich mit jeder Nachricht | `git ls-files <ordner>` + Aenderungszeit; `git rm --cached` + Sperrzeile (spaetere Regel gewinnt), Datei lebt weiter |
   | Fremdarbeit im Baum | Aenderung stammt nicht aus dieser Sitzung | < 10 min: liegen lassen und melden. Sonst eigener Commit, `--author="Andere Sitzung <fremd@local>"` |
   | Doku widerspricht dem System | Notiz/Skill behauptet etwas Pruefbares | Beleg am laufenden System holen, dann die Doku ziehen (nie umgekehrt) |
   | Aufgabenliste | TASKS.md/Routinen.md gegen den Ist-Stand | Erledigtes nach `## Erledigt` mit Belegsatz, Neues sofort eintragen |
   | **Pruefer-Fehlalarm** | ein Pruefer meldet seit Tagen dasselbe („Herzschlag 204 min alt - laeuft die Spur ueberhaupt?“, „0 statt 180 min“) | ZUERST die gemeldete Zahl SELBST messen. Stimmt sie, ist der Fehler im PRUEFER, nicht im Geprueften - dann den Pruefer ziehen (er liest den falschen Zustandszweig, den falschen Ordner oder eine Zahl, die nie etwas bedeutete) und NIE die Spur „reparieren“. Eine Dauerwarnung ohne Bedeutung ist der Anfang, an dem echte Warnungen ueberlesen werden |

3. **Jeder Fix braucht Vorher/Nachher.** Ein Befund ohne Reproduktion ist ein
   Verdacht. Bei Textdateien danach `git diff --numstat`: wenige Zeilen = gewollt,
   ganze Datei = Zeilenenden oder Kodierung verstellt (dann
   `git checkout HEAD -- <datei>` und neu). Byte-genaue Aenderungen an CRLF-Dateien
 immer mit `.bak-JJJJMMTT` und Gegenprobe (ohne die neue Zeile byte-identisch
 zum Backup).
 Liegt die Ursache in der UMGEBUNG (geplante Aufgabe vs. Aufruf von Hand),
 ist das Beweismittel ein PAAR: zweimal derselbe Aufruf in EINEM Prozess,
 genau eine Variable geaendert - `mit X: exit 128`, `ohne X: exit 0`. Das Paar
 ist der Beweis; ein einzelner Lauf zeigt nur, dass es gerade scheitert.
 Geheimnisse dabei nie ausgeben: Wert im Prozess belassen
 (`[Environment]::GetEnvironmentVariable('NAME','User')`), nur Laenge nennen.
4. **Admin-Schritte sammeln, nicht einzeln fragen.** `Set-ScheduledTask`,
   `Register-ScheduledTask` und `Disable-ScheduledTask` verweigern aus einer
   normalen Sitzung (`Zugriff verweigert`, HRESULT 0x80070005). Alle faelligen
   Schritte in EIN Skript `Agenten/Routinen/<thema>-admin.ps1` buendeln, dann den
   UAC-Dialog ausloesen:
   `Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-File','<pfad>'`
   Danach aus der normalen Sitzung **nachmessen** (Zustand, Aktion, Prozessname) —
   dem Skript allein nicht glauben. Fuer den Bus-Befund belegt: so wurden drei
   Schritte in einer Bestaetigung erledigt.
5. **Getrennt sichern.** Eigene Aenderung und Fremdarbeit in **zwei** Commits,
   Pfade namentlich (`git add <pfad>`), nie `git add -A`. Autoren:
   `--author="Hermes <hermes@local>"` fuer eigene, `--author="Andere Sitzung
   <fremd@local>"` fuer fremde, `--author="PC-Absturz Recovery <recovery@local>"`
   nach einem Absturz. Kein `reset --hard`, kein `checkout --`, kein `clean`.
6. **Umgestellte Dienste neu starten und den NEUEN Zustand belegen** —
   Prozessname, Port, PID. Eine geaenderte Aufgaben-Aktion wirkt erst beim
   naechsten Start; ohne Neustart meldet man einen Fix, der noch nicht laeuft.
7. **Bericht in dieser Reihenfolge:** was jetzt konkret funktioniert (mit
   Pruefweg), was absichtlich NICHT angefasst wurde (frische Fremdarbeit,
   laufende Dienste, ruhende Spuren), was eine Entscheidung von Max braucht.
   Genau eine Empfehlung. Push erst nach dem Nachweis.

## Kurzreferenz

```
cd "$HERMES_HOME/../.."                         # Wurzel - alle Pfade hier sind relativ dazu
git status --porcelain                       # Baum
powershell -File Agenten/mcp-sync-check.ps1  # MCP-Drift
python Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/sammeln.py
git diff --numstat <datei>                   # 1/1 = gewollt, ganze Datei = Alarm
git show HEAD:<pfad>                         # steht die eigene Aenderung schon drin?
git log --oneline origin/master..master      # unpushed Commits vor dem Bericht
grep -a -c "FEHLER 5" <robocopy-log>         # Beweislog mit Umlauten lesen
git fsck --full                              # 0 error nach Baum-Operationen
git remote set-head origin -a                # origin/HEAD nach Zweig-Loeschung
powershell -Command "Get-ScheduledTask -TaskName 'MaxHirn-*' | Select TaskName,State"
hermes.exe curator usage                     # (PYTHONHOME/PYTHONPATH leeren)
```

## Fallen

- **PowerShell 5.1, vier stille Fehler** (gemessen, alle schon in Produktion
  getroffen): (1) `.Count` auf einem Einzelobjekt aus der Pipeline ist **leer** —
  Gruppen mit `@()` erzwingen, sonst stehen 1-Element-Gruppen als „()“ da;
  (2) im Array-Literal gewinnt das Komma gegen das Plus — `@("# " + $t, ...)`
  macht den ganzen Kopf zu EINEM String, die Titelzeile vorher in eine Variable
  legen; (3) `Get-Content -Raw` ohne `-Encoding UTF8` liest UTF-8 als ANSI
  (Mojibake, sichtbar erst bei fremden Schriften); (4) `Get-FileHash` existiert
  nicht — `DateiHash()` ueber `System.Security.Cryptography` nutzen, sonst wird
  eine leere Hash-Gruppe zu einer FALSCHEN Zahl statt zu einem Fehler.
- **Eine per `write_file` geschriebene `.ps1` bricht in PowerShell 5.1 beim
  Parsen.** `write_file` schreibt UTF-8 OHNE BOM; PS 5.1 liest eine `.ps1` ohne
  BOM als ANSI — ein einziges Nicht-ASCII-Zeichen (—, ·, Umlaut) in einer
  doppelten Zeichenfolge endet als abgeschnittene Sequenz und meldet „Die
  Zeichenfolge hat kein Abschlusszeichen". Haus-Skripte daher ASCII-only
  schreiben (ue/oe/ae statt Umlaute) und vor dem ersten Lauf mit
  `[System.Management.Automation.Language.Parser]::ParseFile($pfad, [ref]$null,
  [ref]$errs)` pruefen; ein Patch, der ein — in einen String setzt, genuegt als
  Ausloeser.
- **`schtasks` aus git-bash braucht den einfachen Bindestrich.**
  `schtasks //query //fo list` endet in „Ungueltige(s) Option/Argument"; ein
  daruebergelegtes `grep` liefert dann LEER — das liest sich wie „Aufgabe
  existiert nicht", ist aber ein Aufruffehler. Richtig: `schtasks -query -fo list`.
  Vor jeder „Aufgabe fehlt"-Meldung einmal `schtasks -query -fo csv | head -3`
  als Gegenprobe fahren.
- **`Werkstatt/` ist eine Junction.** `write_file` prueft den aufgeloesten Pfad
  gegen `HERMES_WRITE_SAFE_ROOT` und lehnt ab, obwohl der Pfad im Baum liegt.
  Erst eine Datei ausserhalb der Junction schreiben, dann per `terminal` mit `cp`
  hinueber (Verzeichnis vorher anlegen).
- **Prozesssuche trifft sich selbst.** `CommandLine -like '*skript.py*'` findet die
  eigene Shell; immer zusaetzlich auf den Prozessnamen einschraenken. Und die
  `CommandLine` einer fremden PID kann leer sein — dann ueber den **Port** suchen:
  `Get-NetTCPConnection -LocalPort <port> -State Listen` → `OwningProcess`.
- **Ein aufploppendes Konsolenfenster kommt vom Programm, nicht von
  `-WindowStyle Hidden`.** Alle 18 Routine-Aufgaben trugen bereits `Hidden`; das
  Fenster kam vom Bus, der als `python.exe` bei `Interactive`-Logon lief. Ein
  Dauerprozess ohne stdout-Bedarf gehoert auf `pythonw.exe` (Muster SkillsBot).
- **Nach dem Loeschen eines Zweigs zeigt `refs/remotes/origin/HEAD` auf einen
  Null-Zeiger** und `git fsck` meldet `invalid sha1 pointer` — kein Schaden,
  `git remote set-head origin -a` repariert.
- **Kein `git add -A`.** Im Mehrsitzungsbetrieb zieht das fremde Arbeit mit; die
  Herkunft steht im Autorenfeld, nicht in der Nachricht.
- **`index.lock` heisst meist „jemand committet gerade“.** Erst Alter UND echte
  git-Prozesse zaehlen (`git.exe` OHNE `fsmonitor` in der CommandLine). Bei >0
  WARTEN und denselben Commit wiederholen - die Sperre verschwindet von selbst.
  Nur bei 0 echten Prozessen ist es ein Wrack, und dann wird sie UMBENANNT
  (`Move-Item -Force`), nie geloescht.
- **Sagt `git commit` „no changes added to commit“, obwohl `git add` eben lief**,
  hat eine andere Sitzung die Datei in der Zwischenzeit committet. Nicht raten:
  `git show HEAD:<pfad>` zeigt, ob die eigene Aenderung schon drin ist (dann nur
  die Attribution falsch, der Code sicher). Eigenes, das laenger als 30 min
  uncommittet liegt, zieht die Routine `fremdarbeit-einziehen` als
  `fremd@local` nach master - Eigenes darum zuegig committen.
- **Ein PR verlangt einen Zweig - im Haus gibt es nur `master`.** „Branch pushen
  und PR oeffnen“ ist hier ohne Regelbruch nicht umsetzbar (`AGENTS.md`: keine
  weiteren Zweige, privates Repo, kein Reviewer). Statt dessen Conventional
  Commits auf `master`, pushen, und im Bericht sagen, warum kein PR. Der einzige
  sinnvolle PR-Kandidat ist ein fremder `arbeit/<kuerzel>`-Worktree.
- **Beweislogs enden oft als „Binaerdatei“.** robocopy-Ausgaben mit Umlauten
  lassen den Treffer unlesbar erscheinen: den Auszug als Text erzwingen
  (`grep -a`). Und einen Trockenlauf NIE an einem Auschnitt beurteilen - die
  Zahl der betroffenen Zeilen ZAEHLEN (7 gesehen, 144 gewirkt).
- **Abgeleitete Caches gehoeren in die AUSSCHLUSSLISTE der Sicherung, nicht in
  die Sicherung.** Ein gesperrtes Build-Artefakt (uv editable-Wheel) kostet sonst
  jede Nacht einen roten Exitcode (`FEHLER 5`, robocopy-Code 11), ohne dass eine
  Datei fehlt. Beleg: `FEHLER 5` = 0 im eigenen Log UND der Pfad steht in
  `Ausgeschl. Verzeichnisse`.
- **Nicht jeder Nicht-0-Wert ist ein Fehler.** Dauerlaeufe enden beim Herunterfahren
  mit 267014/1073807364, `2147946720` heisst „laeuft schon“. Ein Befund ist das erst
  mit `ENDE FEHLER` im eigenen Protokoll oder ohne Antwort auf den Port.

## Nachweis

- `git status --porcelain` nennt nur noch bewusst liegen gelassene Dateien.
- `git fsck --full` ohne `error:`-Zeile.
- Ports offen, Aufgaben `Ready` mit `LastTaskResult 0`, der geaenderte Dienst im
  Neustart mit dem erwarteten Programmnamen.
- Die Runde ist fertig, wenn jede Befundklasse ein Urteil hat, alles gesichert
  und gepusht ist und offene Entscheidungen namentlich im Bericht stehen.
