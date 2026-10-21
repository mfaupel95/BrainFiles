# Skill Bundles

Skill bundles group several skills under one slash command. `/<bundle-name> <text>` loads every referenced skill at once, with the text after the command as the user instruction.

## Location and schema

Bundles are YAML files in `$HERMES_HOME/skill-bundles/<slug>.yaml` (BrainFiles: `Agenten/Hermes/skill-bundles/`):

```yaml
name: spur            # optional, defaults to the filename stem; normalized to a hyphen slug
skills:               # required, non-empty: skill names or paths relative to the skills dir
  - handel-spuren
  - handel-risikosteuerung
description: ...      # optional, shown in `hermes bundles list` / `/bundles`
instruction: |        # optional glue line prepended to the loaded skill content
  ...
```

## CLI

- `hermes bundles create <slug> --skill a --skill b -d "..." -i "..."` — omit `--skill` to enter skills interactively; `--force` overwrites an existing bundle.
- `hermes bundles list` / `show <slug>` / `delete <slug>` / `reload` (re-scan the directory, reports added/removed).
- In-session: `/bundles` lists them; invoke a bundle with `/<slug> <text>`.

## Behavior (authoring rules)

- **A bundle takes precedence over a single skill on slug collision** — a bundle named `research` shadows the `research` skill. Name deliberately.
- Missing skills are skipped with a note, not fatal — verify every referenced slug resolves before declaring success (below).
- Bundles work on every surface including gateway platforms (Telegram), because dispatch is shared with skill commands.
- Invocation injects a **fresh user message**: it does NOT invalidate the prompt cache, but the loaded skill text stays in the conversation for its whole life. **Size discipline** — never stack the ~100k-char skills (handel-spuren, arbeitsbaum-git-hygiene, dauerprozess-bewachen ≈ 25k tokens each) into one bundle, and keep bundles to ~3 skills.
- A bundle is an alias, not an installer — the skills must already be present.

## House state (BrainFiles)

Existing bundles — extend these instead of recreating:

- `sitzung` — sitzungsabschluss, betriebsrunde, aufgabenliste-pflegen
- `systemcheck` — systemdiagnose, systempruefung-abarbeiten, sicherung-fahren
- `spur` — handel-spuren, handel-spur-optimierung, handel-risikosteuerung
- `handel-betrieb` — okx-orderweg-diagnose, dauerprozess-bewachen, stille-ausfaelle-eingrenzen
- `wissen` — wiki-pflege, notiz, dokumente-zu-wissen

Descriptions and instructions for new bundles in German, one glue line each.

## Pitfalls (BrainFiles)

- **New bundles are invisible to git.** `.gitignore` ignores `Agenten/Hermes/**` wholesale; a new `skill-bundles/` file needs whitelist entries — directory first (`!Agenten/Hermes/skill-bundles/`), then files (`!Agenten/Hermes/skill-bundles/*.yaml`) — a file is not freed while its parent dir is locked. Verify with `git add --dry-run <file>` (prints `add ...` when not ignored), then commit the bundle together with the whitelist.
- Verify referenced slugs on disk before shipping: `for s in <slugs>; do find skills -maxdepth 3 -type d -name "$s" | wc -l; done` — at least one hit per slug (a subcategorized skill may hit twice, e.g. `notiz` under claude-code-imports).
- Success is `hermes bundles list` showing the row plus `git add --dry-run` succeeding — the `create` success line is cosmetic and its long Windows path wraps mid-word in the output.
