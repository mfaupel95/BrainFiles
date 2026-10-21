---
name: brainfiles-auftrag
description: Aenderung in BrainFiles belegen, dokumentieren, committen.
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [BrainFiles, Arbeitsablauf, Nachweis, Verifikation]
---

# Auftrag in BrainFiles nachweisbar abschliessen

Dieses Muster zieht einen Aenderungsauftrag in Max' KI-Betriebssystem durch --
von der Diagnose ueber den belegten Lauf bis zum Commit. Es ist **kein Router**
auf die Fach-Skills, sondern die Disziplin DARZWISCHEN: nichts behaupten ohne
echten Lauf, nichts anfassen ohne Sicherung, nichts committen ohne Doku. Es
macht keine Fachentscheidungen (welcher Wert gut ist, welche Strategie
weiterlaeuft) -- die stehen in den Skills `handel-spuren`, `hermes-config-ops`,
`omniroute-betrieb`; dieses Muster sagt, WIE man sie sicher einsetzt.

## When to Use

- „Fuege X als Provider hinzu", „keys in die Umgebungsvariablen", „aendere die Hermes-Config"
- „optimiere die Spur", „sammle schneller Daten", „welche Zahl ist dafuer richtig?"
- Jeder Auftrag, der eine LAUFENDE Komponente aendert (Handel, Hermes, Router, Dauerlauf)
- Jede Antwort auf „funktioniert das?" -- Antworten sind Nachweise, keine Meinungen

## Prerequisites

- `HERMES_HOME=C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes` setzen, BEVOR ein
  `hermes.exe`-Aufruf startet; ohne sie liest/schreibt die CLI die AppData-Config
  (`%LOCALAPPDATA%\hermes`) statt der Projekt-Config, und „der Wert steht drin" ist falsch.
- `PYTHONHOME` und `PYTHONPATH` vor jedem `hermes.exe`-Aufruf entfernen (`unset PYTHONHOME PYTHONPATH`),
  sonst stirbt der Interpreter mit `init_import_site`-Fehlern.
- Schluessel liegen als Windows-Benutzervariablen in `HKCU\Environment`; Werte werden nie
  wiedergegeben, nur Laenge + SHA-256-Anfang.
- Git-Repo BrainFiles, aktiver Zweig `master` (seit 16.09.2026; `telegram-bus`
  wurde hinein gefuehrt und geloescht); mehrere Sitzungen arbeiten gleichzeitig
  am Baum.

## How to Run

Fuenf Phasen, jede mit eigenem Nachweis: **1** Skill laden + Ist-Stand lesen,
**2** sichern + aendern, **3** testen (Temp-Bereich), **4** echten Lauf belegen,
**5** dokumentieren + committen. Werkzeuge sind die Hermes-Standardwerkzeuge
(`read_file`, `search_files`, `patch`, `write_file`, `terminal`); Schluessel
gehen NUR durch Skripte, die sie per `winreg` aus der Registry lesen -- nie
ueber die Kommandozeile.

## Quick Reference

- Fach-Skill laden: `skill_view(name='handel-spuren' | 'hermes-config-ops' | 'omniroute-betrieb')`
- Benutzervariablen-NAMEN listen: PowerShell `(Get-Item HKCU:\Environment).GetValueNames()`
- Wert in der Sitzung: `[Environment]::GetEnvironmentVariable('NAME','User')`
- Identitaet zweier Kandidaten: sha256-Anfang vergleichen, den Wert nie zeigen
- Hermes-Config aendern: `./bin/hermes.exe config set <pfad> <wert>` (`patch` ist gesperrt)
- Provider-Livetest: `./bin/hermes.exe chat -q "<frage>" -Q --provider <p> -m <modell> -t memory`
- Spur-Testsuite: `<spur>/.venv/Scripts/python.exe -m unittest discover -s tests -t tests` (absoluter Interpreter!)
- Spur-Vorschau (schreibt nichts): `<interpreter> <spur>.py --vorschau`
- Kopie ausser Haus: `<Handel>/scanner/.venv/Scripts/python.exe spiegelstand.py` -> „9 von 9 byte-gleich"
- Sicherung je Datei: `<datei>.bak-JJJJMMTT` (Stufe 1, auch wachen.json/zustand.json)
- Commit: `git add <namentliche Pfade> && git commit --author="Hermes <hermes@local>" -m "<meldung>"`

## Procedure

1. **Skill laden.** Passt einer der Fach-Skills? `handel-spuren` (Agenten/Handel),
   `hermes-config-ops` (Hermes-Config/Secrets), `omniroute-betrieb` (Router).
   Sie enthalten die Pitfalls des Bereichs -- die sind Vorgabe, nicht Rat.
2. **Ist-Stand lesen, nicht erinnern.** Dateien per `read_file`/`search_files`, Config per
   `hermes config get`, Registry per PowerShell, Router-DB read-only
   (`sqlite3.connect('file:...storage.sqlite?mode=ro', uri=True)`). Vor jeder
   „fehlt"-Aussage noch einmal lesen: eine zweite Sitzung kann zwischen zwei
   Aufrufen schreiben. Variable NAMEN aus der Registry listen, keine Kandidatenliste raten.
3. **Schluessel gegen den echten Dienst pruefen, BEVOR verdrahtet wird.** Modellliste
   (`GET /v1/models` bzw. `https://api.anthropic.com/v1/models`) 200 = Anmeldung ok;
   ein 400 „credit balance is too low" = kein Guthaben, KEIN toter Key; 401 = Key falsch;
   403 = Limit. Fehlerklassen lesen, dann erst verdrahten.
4. **Sichern (Stufe 1).** `.bak-JJJJMMTT` je angefasster Datei; Vault-Notiz zusaetzlich
   `updated:` auf heute; Router-DB per SQLite-Backup-API nach `~/.omniroute/db_backups/`.
5. **Aendern.** Normale Dateien per `patch`/`write_file` (eine Zeile aendern, danach diff
   gegen die Sicherung: darf nur die gewollte Zeile sein). Hermes-Config NUR per
   `hermes config set` (auch Listen: der Wert wird YAML/JSON-geparst). JSON/Wachen per
   Applier, der im Speicher `json.loads` VOR dem Schreiben prueft und den diff zeigt.
6. **Testen.** Suiten in Temp-Ordnern: echte Zielpfade (`Q:\Handel_Journal\<spur>`,
   `journal_zweitziel`) im Test auf Temp umbiegen, Netz-Seams stuben, Grenzen aus
   DERSELBEN Funktion lesen, die der Lauf benutzt -- nicht aus der Rohdatei.
7. **Echten Lauf belegen.** Ausfuehren und den Nachweis am Handle festmachen: Logzeile
   mit Message-ID (`id=msg_...`), DB-Zeile (billing_provider/model), Journal-Eintrag oder
   Byte-Vergleich. Bei Dauerlauf-Spuren auf den naechsten Zyklus (Takt ~15 min) warten
   und Journal/Ablehnungslog/zustand lesen -- NIEMALS einen Papierzyklus von Hand fahren
   („je Spur ein Schreiber": der Dauerlauf ist der einzige Schreiber).
8. **Dokumentieren.** Vault-Notiz (`Wissen/`) mit Aenderung, Nachweisweg, Sicherungspfad
   und Ruecknahme-Bedingung; README der Komponente; der zustaendige Skill bekommt die
   Lektion als `patch`, damit die naechste Sitzung sie laedt.
9. **Committen.** `git status --porcelain` und `git diff --cached` auf fremde Arbeit
   pruefen (mehrere Sitzungen!), dann NUR benannte Pfade mit
   `--author="Hermes <hermes@local>"`; nach dem Commit `git show --stat` gegen die Absicht halten.
10. **Bericht.** Ergebnis zuerst, genau EINE begruendete Empfehlung, keine Optionsliste;
    nennen, was absichtlich NICHT angefasst wurde und was eine Entscheidung von Max
    braucht (mit Ruecknahme-Bedingung); eine konkrete naechste Aktion unter zwei Minuten.

## Pitfalls

- **`patch` verweigert Hermes-Config** („Refusing to write to Hermes config file") und
  Pfade ausserhalb `HERMES_WRITE_SAFE_ROOT` (Junctions werden auf ihr echtes Ziel
  aufgeloest). Der Umweg ist `hermes config set` -- auch fuer Listenwerte.
- **`hermes config set` schneidet den Kommentar-Schluss der Datei ab** (38 Zeilen Doku
  verloren, belegt 14.09.2026). Nach JEDEM Set diff gegen die `.sicherung/`-Sicherung und
  den Block zurueckholen, sonst waechst eine unsichtbare Differenz.
- **Variablennamen koennen Tippfehler tragen.** Es existierte `#ANTHROPIC_API_KEY`
  (Rautenzeichen im Namen!), der kanonische `ANTHROPIC_API_KEY` fehlte. NAMEN listen,
  je Kandidat Laenge + sha8 vergleichen -- gleicher Hash = derselbe Wert, „FEHLT" ist
  erst nach dem Auflisten bewiesen.
- **400 ist kein 401.** „credit balance is too low" = Anmeldung ok, Konto leer. Einen
  Key nicht „tot" nennen, nur weil die Antwort 400 ist; /v1/models antwortet trotzdem 200.
- **Kein Geheimnis in eine Kommandozeile.** Skripte lesen Werte per `winreg` aus
  `HKCU\Environment`, in Prozessvariablen laden (`export` ist ein Shell-Builtin, kein
  argv-Eintrag), ausgeben nur Laenge/sha8/Praefix. `setx` nie (PSReadLine-Verlauf!).
- **Der laufende Gateway sieht neue Umgebungsvariablen nicht** -- aber
  Provider-Anmeldedaten kommen aus dem Credential-Pool (`auth.json`) und der `.env`,
  DAFUER ist KEIN Neustart noetig (belegt: Subagent lief sofort mit
  `provider=anthropic model=claude-opus-5`, Logzeile `platform=subagent`).
  Neustart braucht nur, wer `dauerlauf.py` selbst (SPUREN/Filter) aendert.
- **Testlaeufe koennen die Kopie ausser Haus ueberschreiben.** Jede Suite, die
  `lauf()` ruft, muss `journal_zweitziel` auf einen Temp-Ordner umbiegen; Nachweis:
  danach `spiegelstand.py` muss byte-gleich melden.
- **Eine neue je-Zyklus-Zeile mit einem Dauerlauf-Filterwort** (`verkauf`, `stop`,
  `kill`, `gesperrt`, `ausstieg`) wird Telegram-Spam. In Druck-Texten heisst der
  Kill-Switch „Notbremse".
- **Tests, die eine Grenze aus der Rohdatei lesen, messen nach einer
  Umfangs-Aenderung an der falschen Stelle** (Buch auf 60 gefuellt nach Dateiwert 20:
  gruen, aber blind). Grenze aus derselben Funktion holen, die der Lauf benutzt
  (Muster: `sp._umfang(self.w, "papier")["max_offen"]`).
- **Max will Zahlen, keine Optionen.** Bei „welche Zahl ist richtig?" Kapazitaet gegen
  Risiko rechnen (z.B. Runden/Tag = Plaetze x Umschlag je Platz; Notbremse im selben
  Anteil mitziehen) und die EINE gesetzte Zahl mit Ruecknahme-Bedingung nennen
  (live-Schalter = Ruecknahme).
- **`patch` schreibt die GANZE Datei neu und kann Zeilenenden umstellen.** Eine
  versionierte Datei mit gemischten Endungen (Beispiel: `Agenten/Bus/README.md`,
  86 CRLF + 52 LF) kam danach komplett als CRLF zurueck - 86 geaenderte Zeilen
  fuer eine gewollte. Erkennen: `git diff --numstat` zeigt ploetzlich die ganze
  Datei. Reparatur: die HEAD-Bytes holen (`git show HEAD:<pfad>`), den Zieltext
  BYTE-GENAU ersetzen und mit `newline=''`/`wb` schreiben; danach muss
  `git diff --ignore-cr-at-eol --stat` die eine Zeile zeigen.
- **Das fuzzy `patch`-Werkzeug kann Python-Einrueckung zerschiessen, und
  `write_file` verweigert nach einem offset/limit-Lesen dauerhaft.** Ein `patch`
  mit ungenauem Match (context_aware) verschiebt Blockgrenzen und erzeugt
  IndentationError/Syntaxfehler - ab dem ERSTEN IndentationError nicht weiter-
  patchen, sondern die Datei KOMPLETT lesen und neu schreiben. `write_file`
  blockiert das Ueberschreiben einer Datei, die je mit offset/limit gelesen
  wurde - auch nach einem vollstaendigen Neulesen (der partial-view-Guard hebt
  sich nicht). Beides umgeht man gleich: Inhalt an einen FRISCHEN Pfad unter
  `Agenten/Hermes/cache/scratch/` schreiben (write_file akzeptiert neue Pfade),
  `py_compile`/Lint pruefen, dann per `cp` ueber das Ziel legen.

## Verification

Ein Auftrag ist abgeschlossen, wenn beides steht: **(a)** `git log --oneline -1` nennt
nur die benannten Pfade der eigenen Aenderung, und **(b)** der ECHTE Lauf zeigt die
Wirkung mit Handle -- beim Provider die Logzeile `model=<ziel> provider=<p> ...
id=msg_...` einer realen Anfrage, bei einer Handelsspur der Eintrag des naechsten
Dauerlauf-Zyklus in Journal/Ablehnungslog plus `spiegelstand.py` „9 von 9 byte-gleich".

## Befehle fuer Max sind PowerShell (01.10.2026)

Max arbeitet in PowerShell, nicht in bash. Ein mitgegebener Befehl mit `grep`, `ls`,
`cat` oder einer bash-`for`-Schleife scheitert bei ihm mit "Der Begriff \"grep\" wird
nicht als Name eines Cmdlets ... erkannt" - und er muss nachfragen, obwohl die Sache
laengst laeuft. Zwei Regeln daraus:

- Nachweise, die EINE Zeile sind, SELBST fahren und nur das Ergebnis zeigen. Ein Befehl
  fuer ihn ist nur dann richtig, wenn er ihn wirklich ausfuehren soll.
- Muss er selbst laufen: PowerShell-Schreibweise (`Select-String`, `Get-ChildItem`,
  `Get-Content`) und den Befehl VORHER einmal echt in PowerShell ausprobiert - eine
  ungepruefte Zeile kostet ihn einen Fehlversuch.
