---
id: 20260902-skill-bibliothek
title: 'Skill-Bibliothek'
tags: [betrieb]
created: 2026-09-02
updated: 2026-09-06
related: [20260830-verbindungen, 20260830-ordnerstruktur, 20260830-schutzregeln, 20260830-wiederholbare-aufgaben]
summary: 'Selbstgeschriebene Skills liegen serverseitig im Anthropic-Konto; der Ordner unter AppData ist nur ein Sync-Cache — nicht in Git, nicht in der Sicherung.'
---

# Skill-Bibliothek

## Wo eigene Skills wirklich liegen

Selbstgeschriebene Skills (Beispiel: `local-ai-config-doctor`) sind **serverseitig
im Anthropic-Konto** gespeichert, nicht auf der Platte. Erkennbar am Manifest:

```
AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\<org>\<install>\manifest.json
  { "skillId": "skill_018DtAH4KgRZX9yq3a241ZQQ",
    "name": "local-ai-config-doctor",
    "creatorType": "user",
    "updatedAt": "2026-09-02T21:09:04Z" }
```

`creatorType: user` trennt eigene Skills von den mitgelieferten von Anthropic.
Der Ordner daneben (`skills/<name>/`) ist **nur ein Sync-Cache** und wird bei
jeder Aktualisierung überschrieben — am 01.09.2026 traf das alle mitgelieferten
Skills auf einen Schlag.

## Warum das ein Loch ist

Dieser Ordner liegt in `AppData`, also:

- **nicht in Git** — die Repo-Wurzel ist `BrainFiles/`
- **nicht in der Sicherung** — `Agenten/sichern.ps1` kopiert nur `BrainFiles\` nach `G:\MaxHirn-Sicherung`
- **nicht in `.claude/file-history`** — dort landen nur Claude-Code-Edits

Wer eine ältere Fassung hochlädt, überschreibt die neuere **auch serverseitig**;
lokal ist danach nichts mehr wiederherstellbar. Am 02.09.2026 um 23:09 genau so
passiert. Einzige verbleibende Quelle ist dann die Versionshistorie der
Skill-Verwaltung im Konto.

## Regel

Ein Skill, an dem gearbeitet wird, bekommt eine **Arbeitskopie unter
`MaxHirn/.claude/skills/`**. Von dort wird hochgeladen, nicht umgekehrt. Damit
liegt er in Git und in der Sicherung, und ein Fehlgriff kostet einen
`git checkout` statt der Arbeit von drei Tagen.

Für `local-ai-config-doctor` am 02.09.2026 so eingerichtet. **Nebenwirkung:**
Claude Code lädt den Skill dadurch zweimal — einmal als Projektskill aus dem
Vault, einmal als `anthropic-skills:` aus dem Konto. Das ist hier gewollt: der
Skill hat sonst keinen bleibenden Ort auf der Platte.

Für Skills, die **global** unter `~/.claude/skills/` installiert sind, gilt das
nicht — dort wäre die zweite Fassung nur Rauschen. Deren Sicherungskopie liegt
deshalb in `MaxHirn/.claude/skills-sicherung/`: in Git (eigene Freigabezeile in
`.gitignore`) und in der Sicherung, aber **nicht** von Claude Code geladen, weil
nur `skills/` gelesen wird. Gültig bleibt die globale Fassung; die Kopie ist
Rückfallebene, keine zweite Quelle.

## Nachweis, welche Fassung wann galt

Die Frontmatter-`description` jedes Skills steht in **jedem** Claude-Code-Transkript
unter `.claude/projects/<projekt>/*.jsonl` (Abschnitt der verfügbaren Skills). Ein
Vergleich über die Zeitstempel der Transkripte zeigt, ob und wann sie sich geändert
hat — im Fall oben war sie zeichengleich, der Verlust betraf also nur den Rumpf.

## Verwandt

[[Wiederholbare-Aufgaben]] — woraus die Skills entstehen.
