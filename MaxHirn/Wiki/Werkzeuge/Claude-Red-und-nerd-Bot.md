---
id: 20260922-claude-red-nerd-bot
title: 'Werkzeuge — claude-red und der nerd-Bot'
tags: [werkzeuge, bots, skills, sicherheit]
created: 2026-09-22
updated: 2026-09-23
related: ['[[Werkzeuge/Fundus-Skills-Bots]]', '[[Werkzeuge/SkillSpector]]', '[[Wissen/Repo-Bots]]', '[[Lektionen/Wahrheit-pruefen]]']
summary: 'Offensive-Security-Skill-Sammlung claude-red als Fundus-Faehigkeit und der Bot nerd dafuer; dazu der Befund, dass Windows Defender Teile des Repos sperrt.'
---

# claude-red und der nerd-Bot

`Werkstatt\Repos\claude-red` = Fork `mfaupel95/claude-red` von
`SnailSploit/Claude-Red` (MIT), vollstaendiger Klon, 7,3 MB, 44 Commits.
Kuratierte Sammlung von **Offensive-Security-Skills**: **79 `SKILL.md` in 23
Kategorien** (web, active-directory, cloud, wireless, mobile, iot, exploit-dev,
privesc, post-exploitation, forensik, fuzzing, recon, social-engineering,
supply-chain, crypto, container, api, cicd, network, ai, auth, utility,
infrastructure). Kein Programm, das startet — Text, `tools/` (Konverter) und
`claude-skills.json` (Manifest).

## Faehigkeit: im Fundus, nicht in der Bibliothek

- Der Klon liegt in `Werkstatt/Repos/` und wird damit von
  `Agenten/Werkzeuge/fundus-suche.ps1` **mitdurchsucht** — Aufruf
  `-Begriff "<wort>"`, Uebersichten per `-Index`.
- Nach dem Index-Lauf vom 22.09.2026: **24 Repos / 581 eindeutige Skills** im
  Werkstatt-Index, davon **claude-red 75** (die vier gesperrten Dateien fehlen,
  siehe unten). Datei: `Wissen/Fundus-Index-Werkstatt.md`.
- **Nichts davon in `Agenten/Hermes/skills/` importiert.** 79 fremde
  Beschreibungen kosten bei jeder Anfrage Kontext; der Hausweg ist Lesen auf
  Anforderung (`fundus-zugriff`).

## Der Bot `nerd`

`Agenten/Hermes/profiles/nerd` — Arbeitsverzeichnis `Werkstatt\Repos\claude-red`,
also liegt sein Nachschlagewerk direkt im Zugriff (`Skills/<kategorie>/<skill>/SKILL.md`).

Angelegt am 22.09.2026 mit `hermes profile create nerd --no-alias` (ohne
`--clone`, damit keine fremde Modellkennung und keine Kanalzeilen mitkommen),
danach nachgezogen:

1. `terminal.backend local` + `terminal.cwd` auf das Repo.
2. `providers.ollama-launch` + `fallback_providers` (lokales `qwen35-8k:cpu`
   zuerst, dann Router) — das frische Profil hat beides nicht.
3. `profile.yaml` per `hermes profile describe nerd --text "..."`.
4. Eigene `SOUL.md`: Faehigkeitsliste, Fundweg, Grenzen (nur autorisierte Ziele,
   beratend statt ausfuehrend), Defender-Befund.
5. `auth.json` als **Symlink** auf den Root-Store (`pwsh` 7 legt ihn ohne
   Erhoehung an, `powershell.exe` 5.1 verweigert mit
   „Administratorrechte erforderlich").
6. Haus-Skills aus `Agenten/Hermes/skills/` kopiert (166 `SKILL.md`; die
   `okx-*`-Junctions mit `cp -rL` dereferenziert).

**Beleg** (`hermes -p nerd chat -q "..." -Q -t terminal`): meldet Arbeitsverzeichnis
`Werkstatt\Repos\claude-red`, kennt die Kategorien- und Dateizahl und den
Defender-Befund. `hermes profile list` zeigt ihn ohne Warnzeile.

## Befund: Windows Defender sperrt vier Skill-Dateien

Beim Klonen am 22.09.2026, 23:39-23:41 hat Defender vier `SKILL.md` als Schadcode
eingeordnet und **zweimal geloescht** (Arbeitsbaum stand auf `D`), danach beim
Zurueckholen nur noch **den Lesezugriff gesperrt**:

| Datei | Erkennung |
|---|---|
| `Skills/web/offensive-sqli/SKILL.md` | `Backdoor:PHP/Perhetshell.A!dha` |
| `Skills/web/offensive-rce/SKILL.md` | `Backdoor:PHP/Perhetshell.A!dha` |
| `Skills/web/offensive-file-upload/SKILL.md` | `Trojan:Script/Wacatac.H!ml` |
| `Skills/infrastructure/offensive-shellcode/SKILL.md` | (Lesezugriff gesperrt) |

Es sind **Signaturtreffer auf Dokumentationstext** — die SQLi-/RCE-Skills zeigen
Webshell-Beispiele, das ist ihr Thema. Gemessen: von 79 Dateien sind **75 lesbar
(343.750 Zeichen)**, vier blockiert; `[IO.File]::ReadAllText` endet mit
„die Datei enthaelt einen Virus oder moeglicherweise unerwuenschte Software".

**Lehre:** `ls` zeigt die Datei, gelesen werden kann sie trotzdem nicht. Wer aus
einer Dateiliste auf „Faehigkeit vorhanden" schliesst, meldet Falsches — die
Probe ist ein echter Lesevorgang, und der Fundort ist
`Get-MpThreatDetection` (Ressourcenpfad + ThreatName), nicht der Arbeitsbaum.
`git checkout -- .` holt geloeschte Dateien zurueck, hebt aber die Sperre nicht auf.

**Offen (Entscheidung Max):** Defender-Ausnahme fuer den Ordner
(`Add-MpPreference -ExclusionPath 'O:\Werkstatt\Repos\claude-red'`, danach
`git checkout` und die vier Dateien sind lesbar). Der Ordner enthaelt keine
Programme, nur Text — die Ausnahme ist eng, aber es ist eine Aenderung am
Virenschutz und wird deshalb nicht ohne Zuruf gesetzt.

## Zwei Fallen beim Anlegen

- **`--clone` ist der falsche Weg und kann Muell hinterlassen.** Der erste Versuch
  (`hermes profile create nerd --clone`) lief in den Abbruch und liess
  `profiles/.nerd.staging-38880` stehen — eine **volle Kopie des Startprofils**
  mit dessen `.env` (Kanalzugangsdaten) und Sessions, 599 MB. Sie traegt eine
  `config.yaml` und stand als Phantom-Bot in `/bots`; `skillsbot.bot_namen()`
  ueberspringt seit dem 23.09.2026 Punkte-Ordner. Fuer einen Bot mit Repo ist
  `hermes profile create <name> --no-alias` + Nacharbeiten der bessere Weg.
- **Symlink nur mit `pwsh` 7.** `powershell.exe` 5.1 verweigert den `auth.json`-Link
  („Administratorrechte erforderlich"), `pwsh` 7 legt ihn ohne UAC an.

## Betrieb

- `origin` = Fork, `upstream` = `SnailSploit/Claude-Red`; der Klon ist **nicht**
  shallow, `git pull`/`fetch` also unproblematisch. Nie nach upstream pushen.
- Der Bot ist beratend: Auftraege gegen fremde Ziele werden benannt und
  abgelehnt, nicht abgeschwaecht ausgefuehrt (steht in seiner `SOUL.md`).
