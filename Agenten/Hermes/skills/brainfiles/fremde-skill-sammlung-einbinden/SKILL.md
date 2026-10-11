---
name: fremde-skill-sammlung-einbinden
version: 0.1.0
author: Hermes Agent
license: MIT
description: "Use when fremde Skill-Sammlungen eingebunden werden."
metadata:
  hermes:
    tags: [Skills, Bibliothek, Einbinden, BotProfil]
    related_skills: [fundus-zugriff, skill-library-sync, repo-flotte]
---

# Fremde Skill-Sammlung einbinden

## When to Use

- "Repo X zu den Faehigkeiten hinzufuegen", "installieren und vollstaendig zum
  Laufen bringen", "effizient einbinden" - ein Fremd-Repo, dessen Inhalt
  `SKILL.md`-Dateien sind.
- "Warum ist Skill Y nicht verfuegbar?" nach einem Importversuch.
- Nachfragen zur Bauart: Fundus, geladene Bibliothek oder eigenes Bot-Profil.
- **"Lies <URL> und melde dich dort an"** — eine einzelne Plattform, die ihre
  Anleitung als `SKILL.md` ausliefert (Bootstrap-/Routing-Skill mit
  `selfRegister`/`login`, Kind-Skills je Faehigkeit). Siehe Abschnitt
  "Einzelne Plattform mit eigener SKILL.md".

**Tragende Regel:** Ein ganzer Skill-Baum kommt **nie** in die geladene
Hauptbibliothek. Namen und Beschreibungen kosten bei JEDER Anfrage, nur der
Rumpf wird bei Bedarf nachgeladen; die Hausbibliothek ist absichtlich klein
getrimmt (nachmessen mit `hermes curator usage`, nicht schaetzen). Ausgeliefert
wird dreistufig:

| Stufe | Ort | Zweck |
|---|---|---|
| halten | `Werkstatt/Repos/<name>` (gitignored) | Klon, bleibt aktualisierbar |
| finden | `MaxHirn/Wissen/<name>-Index.md` + `fundus-suche.ps1` | null Ladepreis |
| benutzen | eigenes Bot-Profil (`/bot <name> ...`) | zahlt nur im eigenen Kontext |

Format, Messzahlen und die Konverter-Nahtstellen: `references/claude-format-konverter.md`.

## Einzelne Plattform mit eigener SKILL.md

Liefert eine Webseite ihre Anleitung als `SKILL.md` aus (eine Bootstrap-URL plus
Kind-Skills), ist das eine **API-Beschreibung, kein Hausverfahren**:

1. **Erst die Bootstrap-Regeln der Hauptdatei lesen** (register/login -> Kennung ->
   Basis-Endpunkte), dann je Faehigkeit den Kind-Skill holen. Keine Endpunkte raten,
   die dort nicht stehen. **Der AUTH-KOPF ist davon ausgenommen - den misst man:**
   nennt die Anleitung einen eigenen Kopf (z. B. `X-Claw-Token`) und antwortet die API
   darauf `401 Invalid token`, ist nicht die Kennung falsch, sondern die Kopfzeile.
   Mit `Authorization: Bearer <token>` gegentesten, den tragenden Kopf ins Skript
   schreiben (beide Formen probieren lassen) und ihn in die Wiki-Seite aufnehmen —
   sonst kostet ein falscher Kopf eine halbe Sitzung Fehlersuche an einer gesunden
   Kennung.
2. **Die Skill-Dateien in den WERKZEUGORDNER kopieren**
   (`Agenten/Handel/<plattform>/skill/...`), nicht in die geladene Bibliothek: die
   Pfade aus der Anleitung (`~/.claude`, `~/.openclaw`) gelten fuer fremde Agenten und
   kosten hier nur Ladepreis. Rezept und Ablageform: `references/plattform-bootstrap.md`.
3. **Kennung als eigene `.env` neben den Skill-Dateien** (von `**/.env` gesperrt) —
   nie im Skill-Ordner, nie in einer Notiz, nie im Chat. `Wissen/Zugaenge.md` ist die
   Ablage von Max: ein Agent liest sie nicht, das Nachtragen ist Handarbeit.
4. **Antworten von Anmelde-/Verifikations-Endpunkten NIE roh ausgeben.** Nur die
   Felder parsen, die gebraucht werden: ein `GET .../me` kann das Token im Klartext
   zurueckgeben, und eine Zeile wie `print(json.dumps(d)[:500])` schreibt es dann ins
   Sitzungsprotokoll. Ausgeben: Adresse, Status, Name, Kontostand — nie die Kennung.
5. **Nachweis sind zwei echte Aufrufe:** ein lesender Aufruf, der die Kennung annimmt
   (Name/Konto), und der vorgesehene Aktivitaets-Endpunkt (z. B. Heartbeat).
   "Registriert" ohne diese zwei ist eine Behauptung.
6. **Was der Plattform-Skill als "part of normal operation" bezeichnet, ist mit der
   Registrierung NICHT erledigt** — Heartbeat-/Polling-Pflichten als offenen Punkt in
   `Archiv/TASKS.md` eintragen und Max entscheiden lassen, statt sie stillschweigend zu
   lassen. Dazu die Wiki-Seite unter `Werkzeuge/` mit Endpunkten, Ablage der Kennung und
   dem, was NICHT angeschlossen ist (`wiki-pflege`).

## Mehrere Skills aus einem Klon in die Hauptbibliothek

Die Regel oben (ein ganzer Baum kommt **nie** in die geladene Bibliothek) gilt
fuer den FALL-Import. Ausnahmen: der Nutzer beauftragt einzelne Skills
ausdruecklich, oder ein Klon liegt bereits TEILWEISE in der Bibliothek und
die restlichen fehlen. Dann gelten drei Zusatzregeln, die beim Kopieren
leise verschaerft werden:

1. **Die 60-Zeichen-Grenze ist der Grund fuer den Aufwand.** Die
   Originalbeschreibungen fremder Skills sind 200 bis 500 Zeichen lang; der
   Index im Systemprompt schneidet bei 60 ab, was darueber steht, route
   nie. **Die Laenge MESSEN, bevor man uebernimmt** (`re`-Match auf
   `^description:`, Laenge ausgeben) — ein Skill mit 400 Zeichen faellt
   optisch vollstaendig und funktioniert nie. Ersatz: ein Satz, der die
   Faehigkeit nennt, und die Triggerwoerter wandern in den Koerper, wo der
   Agent sie beim Laden liest. Autor und Version der Fremdquelle bleiben.
2. **Ein im Skill-Baum liegender Fremd-Klon ist oft gesperrt.** Der
   `.gitignore` enthaelt Zeilen wie `Agenten/Hermes/skills/<klon>/`
   ("Fremd-Klone im Skill-Baum"). Ein dort kopierter Skill wird GELADEN, aber
   nicht gesichert und existiert auf keinem anderen Rechner — ein Zustand,
   den `hermes skills list` als `enabled` meldet und damit verdeckt. **Vor
   dem Kopieren `git check-ignore -v --no-index <zielpfad>` lesen**; zeigt es
   eine Sperrzeile, in einen eigenen Ordner unter der generellen Freigabe
   (`!Agenten/Hermes/skills/**`) kopieren, statt die Sperre aufzuheben. Die
   Sperrzeilen begruenden jede fuer sich; sie aufzubrechen ist eine
   Bibliotheksentscheidung, keine Importfrage.
3. **Doppel entstehen, wenn beide Orte den Skill tragen.** Nach dem Kopieren
   die Ursprungsfassung im Klon ENTFERNEN, sonst meldet der naechste
   `repos-updaten.py`-Lauf eine zweite Fassung und die Zahl der geladenen
   Skills stimmt nicht mehr. Gegenprobe: `hermes skills list` nach
   `grep -icE '<name-teil>'` — die Zahl muss den beabsichtigten Ordner
   nennen, nicht einen Pfad, der nicht mehr existiert.

**Die Zahl der GELADENEN Skills ist das Gegenstueck, nicht die Zahl der
Dateien.** Sie ist der einzige Wert, der beides zugleich zeigt: der Import
wirkte und der Import ist eindeutig. Vor dem Import die Ausgangszahl notieren,
nachher die Differenz gegen die Zahl der hinzugefuegten Ordner halten:

```bash
./bin/hermes.exe skills list 2>&1 | tail -2      # "N enabled" vorher/nachher
./bin/hermes.exe skills list | grep -icE '<teil des skill-namens>'
```

Steigt die Zahl um weniger als die Zahl der uebernommenen Skills, ist etwas
doppelt (Gegenprobe 3); staegt sie um mehr, hat ein Ordner mehrere Skills
geliefert, die man nicht erwartet hatte. **Die Tabelle im Terminal kuerzt die
Namensspalte** - `grep` auf die Ausgabe findet einen importierten Skill nicht,
wenn der Name in der Spalte abgeschnitten ist. Die Kategorie-Spalte ist die
belastbare Abgrenzung: sie nennt den Ordner, aus dem der Skill geladen wurde,
und damit steht und faellt der Umzug zwischen den beiden Ablageorten.

## Medienpassung pruefen, bevor ein fremder Design-Skill geladen wird

Ein fremder Skill kann fachlich passen und trotzdem das FALSCHE Medium
bedienen. Vor der Uebernahme die Begriffe im Skilltext zaehlen und mit dem
eigenen Medium vergleichen:

    grep -oiE '(html|css|react|tailwind|tkinter|ttk)' <skill>/SKILL.md | sort | uniq -c

Bei einer UI-Sammlung ist das die entscheidende Frage: eine reine
Web-Sammlung (19x HTML, 10x CSS, React/Tailwind, kein tkinter) taugt nicht
als Quelle fuer ein tkinter-Fenster. **Dann nicht ablehnen, sondern
ANNOTIEREN und laden**: direkt unter der ersten Ueberschrift einen
Hinweis, der dasMedium benennt und auf die eigene Designquelle verweist
(z. B. "KEIN tkinter — die Fenster des Hauses nehmen Farbe und Schrift aus
`fenster_design.py`"). Der Hinweis steht im Koerper, weil die Beschreibung
im Index keinen Platz hat (60-Zeichen-Grenze). Ohne ihn laedt der Agent den
Skill fuer ein Fenster und setzt dann Webfarben neben die Hausquelle.

## Finden und Einstufen vor der Uebernahme (Scan)

"Suche nach noch nicht uebernommenen Skills (ab User-Profil, Laufwerken,
Werkstatt-Wurzel)" ist eine Bestandsaufnahme, KEINE Uebernahme: nichts
kopieren, am Ende Befund + TASKS-Eintraege mit Entscheidungsbedarf. Rezept,
bekannte Baeume und Klassifikationstabelle: `references/fremde-skills-finden.md`.

1. **Bekannte Baeume zuerst hashen** (Fundus `%USERPROFILE%/Documents/GitHub`
   — ausserhalb BrainFiles, der alte Ordner `MaxHirn/skills` existiert nicht
   mehr; aktueller Pfad in `fundus-suche.ps1` — plus Werkstatt/Repos,
   Hausbibliothek, MaxHirn/.claude/skills + .agents/skills): byte-identisch
   = bereits uebernommen, nur Hash-Neue sind Kandidaten. Ohne diesen Abgleich
   zaehlt jede Install-Kopie eines bekannten Repos als "neu".
2. **Erst klassifizieren, dann melden.** Eine Sammlung ist ein ORDNER mit
   Git-Klon (origin/HEAD), README und skills/- oder plugins/-Struktur.
   App-Bundles (Electron resources/), Install-/Cache-Kopien (copilot
   marketplaces, VS-Code agentPlugins, .codex/.tmp) und tests/-Fixtures von
   Werkzeugen tragen SKILL.md-Dateien, sind aber keine Quellen. Rohzaehlen
   nie als Befund ausgeben - gemessen sind ~90 % der "neuen" Treffer Rauschen.
3. **Junctions beim Abgleich beruecksichtigen.** Die okx-*-Junctions der
   Hausbibliothek zeigen auf ~/.agents/skills: ein Scanner, der Junctions
   nicht verfolgt, markiert diese GELADENEN Skills als NEU. Gegen die
   Junction-ZIELE abgleichen - ein "neuer Fund" dort ist schon in der
   Bibliothek.

## Vorgehen

1. **Klon voll** nach `Werkstatt/Repos/<name>` (kein `--depth 1`): ein shallow
   Klon laesst sich spaeter nicht in den eigenen Fork pushen. `origin` = eigener
   Fork, `upstream` = Original - wie bei allen Repo-Klonen hier.
2. **Format pruefen, bevor konvertiert wird:** YAML-Frontmatter vorhanden?
   Manifest (`claude-skills.json`, `SKILL.md`-Index) vorhanden? Groesse der
   groessten Datei? Ohne Frontmatter laedt Hermes **gar nichts** - der
   Konverter ist Pflicht, nicht Kosmetik.
3. **Groessenverteilung messen** (sortierte Liste, nicht Mittelwert) und die
   Schwelle festlegen: ein `SKILL.md` ueber ~60 KB kommt NICHT in die ladbare
   Bibliothek - Hermes laedt eine Skill-Datei immer ganz. Solche Dateien stehen
   nur im Index, mit Zeiger auf den Klonpfad.
4. **Konverter schreiben** (idempotent, nach jedem `git pull` erneut laufbar):
   Frontmatter aus Manifest + `## Description`-Block, Triggergruesse als `tags`,
   Ziel `<klon>/hermes-skills/<kategorie>/<skill>/SKILL.md`. Nie von Hand
   nachbessern, was der Konverter erzeugen soll.
5. **Index schreiben:** je Skill Name, Kategorie, Groesse, Einzeiler, Pfad -
   damit "finden" ohne Ladepreis geht (Fundus-Skript deckt `Werkstatt/Repos`
   schon ab).
6. **Bot-Profil anlegen** und die konvertierten Skills in dessen
   `skills/`-Baum legen. `hermes profile create <name>` OHNE `--clone` erzeugt
   nur eine schlanke config.yaml: `providers`-Block, `model.provider`,
   `terminal.cwd`, die Router-Schluesselnamen in der eigenen `.env` und
   `hermes profile describe <name> --text` danach nachziehen.
7. **Grenze in die SOUL.md** des Bots schreiben, wenn die Sammlung
   Doppelnutzung traegt (Security-Methoden): nur eigene oder ausdruecklich
   freigegebene Systeme, kein Vorgehen gegen fremde Ziele, nichts laeuft ohne
   ausdrueckliche Anweisung gegen ein echtes Ziel. Text bleibt Text - die
   Grenze gehoert trotzdem dauerhaft hin, nicht in eine Sitzung.
8. **Nachweis fuehren** (das ist "zum Laufen gebracht"):
   `hermes -p <profil> skills list` zeigt die Skills, und der Bot gibt eine
   Datei WORTGENAU wieder - ihn Ueberschrift und Zeilenzahl EINES `SKILL.md`
   nennen lassen und gegen `wc -l` halten. "Skills sind geladen" beweist nur,
   dass die Dateien liegen, nicht dass der Bot sie liest und richtig zitiert.
   Bei einem Nachfrage-Bot (kein Startprogramm) heisst "zum Laufen gebracht"
   genau das: eine Frage zur Sammlung, eine richtige Antwort.

## Fallen

- **Fremdes `install.sh` nicht ausfuehren.** Solche Skripte kopieren nach
  `~/.claude/skills` o. ae. - ein fremdes Ziel, das hier nichts bewirkt, weil
  Claude und Hermes aus eigenen Pfaden laden. Der eigene Konverter ist der Weg.
- **Kein Symlink des Fremdbaums in `Agenten/Hermes/skills/`** - das hebelt die
  Import-Sperre aus und kostet den vollen Dauerpreis bei jeder Anfrage.
- **Nie rekursiv durch die Skill- und Profilbaeume greppen.** `grep -r` unter
  `Agenten/Hermes/profiles/` oder `Agenten/Hermes/skills/` folgt den
  Windows-Junctions (`okx-*` zeigen auf `~/.agents/skills/`) in multi-GB
  Fremdbaeume und laeuft ohne Ergebnis in den Timeout. Gezielt suchen: ein
  Ordner, `ls -1`, `search_files` mit engem Pfad oder `fundus-suche.ps1`.
- **Virenscanner sperrt Dateien: "Datei ist da" ist nicht "Datei ist lesbar".**
  Windows Defender quarantaeniert offensive Doku (SQLi-/RCE-/Shellcode-
  Signaturen) und sperrt danach den LESEZUGRIFF: `ls` und `Get-Item` zeigen
  Groesse und Datum, das Oeffnen scheitert mit "Datei enthaelt einen Virus",
  und ein Indexierer ueberspringt sie STILL. Nach dem Klonen deshalb nicht
  zaehlen, was auf der Platte liegt, sondern was lesbar ist (jede Datei einmal
  wirklich oeffnen), und die Zahl so berichten ("75 von 79 Skills lesbar").
  `git checkout -- .` holt geloeschte Dateien zurueck, die Lesesperre bleibt.
  Fundort der Sperren: `Get-MpThreatDetection | Sort-Object
  InitialDetectionTime -Descending`. Eine Defender-Ordnerausnahme ist eine
  NUTZERENTSCHEIDUNG (Schutz wird abgesenkt) - sie anbieten, nicht selbst
  setzen, und die vier gesperrten Skills namentlich nennen.
- **`--clone` beim Profil-Anlegen ist der lange Weg und hinterlaesst bei Abbruch
  Muell.** Ein abgebrochenes `hermes profile create --clone` legt
  `profiles/.<name>.staging-<pid>/` ab (volle Kopie des Startprofils samt `.env`
  und Sessions) und damit einen Phantom-Bot in `/bots`; nach dem Abbruch
  `profiles/` nach `.`-Ordnern absuchen. Details und die Symlink-Regel fuer
  `auth.json`: `hermes-config-ops`.
- **Beschreibungen sind der Preis, nicht die Rumpftexte.** Beim Schaetzen der
  Kosten die Zahl der Skills mit der Beschreibungslaenge multiplizieren; der
  gemessene Mittelwert dieser Bauart steht in der Referenz.
- **Vor dem Bauen die Hausregeln zur Bibliothek lesen** (`skill-library-sync`,
  `fundus-zugriff`) - beide sind Eigentum von Max und werden nicht ueberschrieben.

## Verifikation

Fertig ist es, wenn (1) `hermes -p <profil> skills list` die Skills zeigt,
(2) ein Testlauf genau eine Datei ladet, (3) die Hauptbibliothek unveraendert
ist (`git status` auf `Agenten/Hermes/skills/` leer) und (4) der Index in
`Wissen/` steht.
