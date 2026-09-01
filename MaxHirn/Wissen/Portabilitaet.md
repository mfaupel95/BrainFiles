---
id: 20260830-portabilitaet
title: 'Portabilität — Umzug auf externe SSD'
tags: [betrieb]
created: 2026-08-23
updated: 2026-08-23
related: []
summary: 'Was beim Umzug des gesamten Systems auf eine externe SSD zu beachten ist.'
---

# Portabilität — Umzug auf externe SSD

Das System ist so gebaut, dass es als ein Ordner umziehen kann. Diese Notiz hält
fest, was dabei zu beachten ist.

## Warum SSD und nicht USB-Stick

Nicht wegen der Kapazität, sondern wegen des Verhaltens bei vielen kleinen
Dateien — genau das erzeugen Archiv, SQLite-Index und Git. Sticks brechen dabei
auf wenige MB/s ein und verschleißen schnell. Eine externe SSD an USB 3.x ist
für diesen Zweck unproblematisch.

## Vorbereitung der SSD

1. **NTFS formatieren**, nicht exFAT. exFAT beherrscht keine Symlinks und keine
   Rechte, und SQLite wie Git sind darauf anfällig für Beschädigung, wenn das
   Laufwerk abrupt abgezogen wird.
2. **Festen Laufwerksbuchstaben vergeben** (Datenträgerverwaltung →
   Laufwerkbuchstaben ändern). Ohne das ändert Windows den Buchstaben je nach
   Reihenfolge der angesteckten Geräte, und absolute Pfade brechen.
3. Vor dem Abziehen immer „Hardware sicher entfernen" — offene SQLite-Schreibvorgänge
   überleben ein hartes Abziehen nicht zuverlässig.

## Umzug

1. Ordner `MaxHirn/` komplett auf die SSD kopieren.
2. **Kopie prüfen, bevor das Original gelöscht wird** — Dateizahl *und*
   Gesamtgröße abgleichen, nicht nur „hat funktioniert" glauben.
3. Vault in Obsidian neu öffnen (Vault wechseln → Ordner auf der SSD wählen).
4. `.venv` neu erzeugen (siehe unten).

## Das `.venv` muss neu erzeugt werden

`Archiv/ArchivSuche/.venv/pyvenv.cfg` enthält den alten absoluten Pfad fest
verdrahtet; ein kopiertes venv funktioniert nicht. Auf der SSD im Ordner
`Archiv/ArchivSuche/`:

```powershell
Remove-Item .venv -Recurse -Force
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Danach einmal neu indexieren:

```powershell
.venv\Scripts\python.exe index.py
```

## Skills außerhalb des Vaults

Nicht alle Skills liegen in `.claude/skills/` im Vault. **`sprache` liegt global**
unter `~/.claude/skills/sprache/` und zieht beim SSD-Umzug **nicht mit**.

Seit dem 20.08.2026 verweisen zwei Skills aufeinander:

- `sprache` (global) → schließt `auftrag` an
- `auftrag` (im Vault) → setzt `sprache` davor

Fehlt einer von beiden, bricht nichts ab — der jeweils andere arbeitet allein
weiter, nur ohne den zweiten Schritt. Nach einem Umzug oder auf einem neuen
Rechner also prüfen, ob `sprache` mitgekommen ist; sonst kopieren.

Sicherung des Vorzustands: `~/.claude/skills/sprache/SKILL.md.bak-20260820`.

## Zeilenenden

Der Vault verwendet durchgehend **LF**, nicht CRLF. Wer Dateien mit Python
schreibt, muss `newline=""` setzen — sonst stellt Windows still jede Zeile der
Datei um, und eine Änderung von drei Zeilen sieht in jedem Vergleich aus wie
eine komplette Neufassung. Am 20.08.2026 genau so passiert, an zehn Dateien.

## Was nicht mitzieht

- **Claude Code selbst** und die Anmeldedaten liegen in `C:\Users\faupe\.claude`
  und bleiben auf dem Rechner. Portabel wird der Inhalt, nicht das Programm.
- **Globale Einstellungen** (`~/.claude/CLAUDE.md`, Memory) ebenso. Wenn sie
  mitwandern sollen, gehören sie als Kopie in den Vault.
- **Der Hermes-Programmcode** unter `C:\Hermes` (1,6 GB) — genau wie das `.venv`
  pfadgebunden und auf einem neuen Rechner neu zu erzeugen:
  `iex (irm https://hermes-agent.nousresearch.com/install.ps1)` mit
  `-HermesHome` auf den Vault-Ordner. Die **Daten** unter `MaxHirn/Hermes/`
  (Konfiguration, Skills, Gedächtnis, Sitzungen) ziehen dagegen mit. Danach die
  Benutzervariable `HERMES_HOME` auf den neuen Pfad setzen. Details: [[Hermes]].
