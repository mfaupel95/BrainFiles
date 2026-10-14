---
id: 20260921-fundus-skills-bots
title: 'Werkzeuge — Fundus, Skills, Bots'
tags: [werkzeuge]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Betrieb/Hermes]]', '[[Wissen/Fundus-Index]]', '[[Wissen/Repo-Bots]]']
summary: 'Wo Skills liegen, wie der Fundus durchsucht wird, welche Bots existieren und was beim Aufraeumen schiefgeht.'
---

# Fundus, Skills, Bots

## Drei Orte, nicht verwechseln

| Ort | Was | Regel |
|---|---|---|
| `Agenten/Hermes/skills/` | **geladene** Bibliothek (jede Anfrage zahlt mit) | entdoppelt: 331 SKILL.md → **90 aktiv** (`hermes skills list` 88 enabled) |
| `Agenten/Hermes/skills/.archive/` | weggelegte Skills (werden NICHT geladen) | zurueck per `hermes curator restore <name>` |
| `MaxHirn/skills/` + `Werkstatt/*` | **Fremd-Fundus** (660 MB / 238 SKILL.md bzw. 356/293 in 18 Repos) | bewusst NICHT importiert (frueher ~14.700 Tokens je Anfrage) |

**Nichts aus fremden Baeumen importieren** (Skill `skill-library-sync`). Fremde SKILL.md sind
Material zum Nachlesen, keine Faehigkeiten dieses Hauses.

## Fundus durchsuchen

`Agenten/Werkzeuge/fundus-suche.ps1` (Suchbegriff; `-Index` schreibt die Uebersichten
`Wissen/Fundus-Index.md` und `Fundus-Index-Werkstatt.md`; `-MitKopien`). Der Skill heisst
`fundus-zugriff`.

**Falle, die eine FALSCHE AUSSAGE erzeugte (16.09.2026):** Das Skript benutzte `Get-FileHash`,
das es in **PowerShell 5.1 nicht gibt** (nur pwsh 7). Folge war keine Fehlermeldung, sondern:
leerer Hash → alle Skills in EINER Gruppe → „0 Treffer von 0 eindeutigen Skills" bei 182
Skills. Repariert mit `DateiHash()` ueber `System.Security.Cryptography.MD5` plus
Pfad-Gruppierung als Rueckfall. **So etwas nie ungeprueft glauben** — beide Wirte muessen
dasselbe liefern (`powershell.exe` und `pwsh`). Dieselbe Falle hatte `systempruefung.ps1`
Block 10 (`Get-FileHash`) — das Regelwerk war seit seiner Einfuehrung tot.

## Aufraeumen der Bibliothek

Werkzeug: `Agenten/Hermes/scripts/skills-entdoppeln.py` (Trockenlauf Standard, `--anwenden`
verschiebt; vorher `hermes curator backup`). Grundlage sind Messwerte, nicht Gefuehl:
`hermes curator usage`.

Gemessene Regel: Baum ohne jede Nutzung ganz weg (financial-services 118 Skills,
claude-plugins-official 31, cli 12 …), Baum mit wenigen genutzten behaelt genau diese
(OmniRoute 47 → 3), eigene Arbeit unantastbar. Ergebnis: Dauerlast je Anfrage
~83.800 → ~12.200 Zeichen (~21.000 → ~3.050 Token).

**Zwei Fallen dabei:**

1. Die `okx-*`-Baeume in `skills/` sind Windows-**Junctions** auf `~/.agents/skills`. Python
   meldet sie NICHT als symlink (`is_symlink`/`islink` = False) — nur `os.path.isjunction`
   erkennt sie. Ein Verschieben haette die Quelle fuer andere Agenten mitgerissen.
2. Ein Test, der an einem festen Skillnamen haengt (`test_skillkatalog` prueft `apple-notes`),
   geht bei jedem Aufraeumen kaputt. Auf die **Regel** pruefen, nicht auf den Namen.

**Offener Aufraeumkandidat:** `Agenten/Hermes/skills/` ist 2,4 GB, davon ~1,8 GB
unversionierte Fremd-Repo-Klone ohne SKILL.md (OmniRoute, unsloth, nautilus_trader,
claude-code, EasyCLIProxyAPI, onchainos-skills, chromaprint, public-apis, …). Alle neu
klonbar — bewusst noch nicht angefasst.

## Skills schreiben

Format: `platforms:` in der Frontmatter filtert. Hermes laesst fremde Systeme weg — 9 von 67
SKILL.md sind mit `platforms: [macos]` bzw. `[linux, macos]` markiert und erscheinen deshalb
NICHT in `/skills` (apple-notes/-reminders/-findmy/-imessage, research-paper-writing,
python-debugpy, serving-llms-vllm, evaluating-llms-harness, xurl).

**Groessenlimit:** `skills/brainfiles/handel-spuren/SKILL.md` ist am Limit (100.663 von 100.000
Zeichen) — `skill_manage` verweigert jede Ergaenzung und rollt den ganzen Stapel zurueck, auch
mitgeschriebene Referenzdateien. Wer dort ergaenzen will, muss zuerst Inhalt nach
`references/` auslagern.

## Bots

- **26 Repo-Bots** = Hermes-Profile unter `Agenten/Hermes/profiles/<name>/` mit
  `terminal.cwd = Werkstatt/<name>`; `copilot-worktrees` ist KEINE Repo (Worktree-Sammlung).
  Dazu Sonderprofile ohne Repo (`nous`, `hermes-wartung`, `lotse`).
- Aufruf im Chat: `/bots` (Liste), `/bot NAME NACHRICHT` = frischer Einzelauftrag
  (`hermes -p NAME chat -q`, Kaltstart 30-60 s).
- **Kanalzugangsdaten nur im Profil `default`** (18.09.2026 bereinigt, 119 Zeilen gestrichen).
  Ein zweites Gateway auf demselben Token nimmt dem Hauptgateway Nachrichten weg.
- **Modelle:** die Bots fahren `nous` / `deepseek/deepseek-v4-flash-0731`. Der lokale Router
  (`omniroute`, Port 20128) ist historisch ausgefallen, sobald seine Combo `auto/best-coding`
  ins Leere zeigte — dann standen ALLE Bots still.
- **Profile sind Inseln:** sie lesen nur ihr eigenes `auth.json`; geloest per Symlink auf den
  Root-Store (siehe [[Betrieb/Hermes]]).
- Der Verteiler-Bot `lotse` braucht eine **Selbstpruefung** („Fuehre ich den Auftrag aus, oder
  suche ich sein Ziel?"), sonst faehrt er die Aufgabe selbst: gemessen 7 → 2 Werkzeugaufrufe
  mit Rueckfrage. Auch ein Trockenlauf ist Ausfuehrung.

## Der SkillsBot

Liest `Agenten/Bus/skillkatalog.py`. Aenderungen wirken erst nach Neustart des Tasks
`BrainFiles-SkillsBot` (Modul im Prozess gecacht). Der Bot sendet **Klartext** (kein
parse_mode) — HTML-Marken waeren sichtbar. Befehle: `/skills`, `/skills SUCHWORT`, `/bots`,
`/model`, `/bots`, `/spuren`, `/lage`, `/bericht`, `/ja`, `/stop`.