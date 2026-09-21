---
id: 20260921-git-und-textdateien
title: 'Lektionen — Git und Textdateien'
tags: [lektion, git]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Lektionen/Tests]]', '[[Wissen/Schutzregeln]]']
summary: 'Zeilenenden, Whitelist-Falle, index.lock, Fremdarbeit im Arbeitsbaum — die vier Fallen, die am haeufigsten zugeschlagen haben.'
---

# Git und Textdateien

## 1. Zeilenenden: nie per Rewrite schreiben

**Regel.** Eine Textdatei aendern heisst: lesen als Bytes, Zeilenende aus dem ROHEN
Text ableiten, als Bytes zurueckschreiben.

```python
roh = open(pfad, "rb").read()
nl = b"\r\n" if b"\r\n" in roh else b"\n"
neu = roh.replace(alt, ersatz)
open(pfad, "wb").write(neu)
```

**Warum.** `open(pfad, encoding="utf-8")` wandelt CRLF still nach LF um; danach ist
`"\r\n" in text` immer `False` und eine Ein-Zeilen-Aenderung landet als Ganzdatei-Diff.
`Path.write_text()` dreht umgekehrt eine LF-Datei auf CRLF (`os.linesep`).
Zweimal passiert (Skill-Dateien), einmal bei `config.yaml`.

**Nachweis.** Nach JEDER Textaenderung `git diff --numstat` **je Datei**: eine gewollte
Zeile muss `1 1` zeigen. Steht dort die ganze Datei: nicht committen, zurueckholen
(`git checkout HEAD -- <datei>`), neu patchen. Ist es schon committet, in einem
Folge-Commit die Enden wiederherstellen — **nie** force-push.

**Zusatzfalle `git config set`/`hermes config set`:** schneidet den Kommentar-Schluss
der Datei ab und schreibt LF. Vorher kopieren, danach byte-genau zurueckholen,
`git diff --numstat` pruefen.

## 2. Whitelist-Falle: neu ist unsichtbar

**Regel.** BrainFiles arbeitet nach „erst alles ignorieren, dann einzeln freigeben".
Ein NEUER Ordner ist damit unsichtbar, bis er in `.gitignore` freigegeben ist.

**Nachweis.**
`git check-ignore -v <pfad>` — zeigt die Regel, die greift. Gegenprobe:
`git ls-files '<muster>'` muss die gewollten Dateien fuehren.
Global ignoriert wird per `*` (Zeile 20), Verzeichnisse werden per `!*/` freigegeben,
dann Dateimuster wie `!MaxHirn/Wiki/**/*.md`.

**Dritte Form (17.09.2026):** eine spaetere Sperre hebt eine fruehere Freigabe auf —
der LETZTE Treffer gewinnt. Beispiel: `Agenten/Handel/*/zustand.mittel.json` stand
hinter `!Agenten/Handel/moondev_funding/*.json` und machte die Freigabe wirkungslos.
Nach jeder Spur-Anlage beide Proben fahren.

## 3. `index.lock`: umbenennen, nie loeschen

**Regel.** Meldet Git „Unable to create `.git/index.lock`: File exists", erst Alter der
Datei und die echten Git-Prozesse pruefen, dann die Sperre **umbenennen**
(`.git/index.lock.verwaist-JJJJMMTT`).

**Warum.** Die Dutzenden `git fsmonitor--daemon run --detach`-Prozesse laufen dauerhaft
und beweisen nichts — zaehlen nur Prozesse OHNE `fsmonitor`. Bisher war die Sperre
immer 0 Byte und von einer abgebrochenen Fremdsitzung.

## 4. Fremdarbeit im Arbeitsbaum

**Regel.** Nur eigene Pfade namentlich stagen. **Nie** `git add -A`, `git add .`,
`git commit -a`. Fremde Aenderungen in einem EIGENEN Commit mit
`--author="Andere Sitzung <fremd@local>"` sichern, wenn der Urheber nicht feststeht.

**Warum.** Es laeuft zeitweise eine zweite Hermes-Sitzung auf demselben Baum (sie
aendert z. B. `Agenten/Handel/swap/`, `Agenten/Hermes/skills/`, `Bus/stand.json`).
`git add -A` nimmt sie mit und vermischt die Urheberschaft. Kein Verwerfen
(`reset --hard`, `checkout --`, `restore`, `stash`, `clean`) — das loescht die
uncommittete Arbeit der anderen Sitzung unwiederbringlich.

**Merksatz.** Was in den letzten 10 Minuten geschrieben wurde, liegt still und wird
nicht angefasst.

## 5. Zweige

`master` ist der einzige Arbeitszweig. `zwischenstand` ist die automatische
Nachtsicherung (nie dort committen). Ein eigener Zweig kostet Ueberblick ohne Gewinn.
Fruehwarnung, wenn die Nachtsicherung stillsteht:
`git log -1 --format=%ci zwischenstand`; Gegenprobe `git add -A --dry-run`
(Exitcode 128 = ein Fremd-Klon im Baum ohne ausgecheckten Commit blockiert das Staging).