# Bash-Sperre für den Disponenten (vorbereitet, NICHT aktiv)

`bash_wache_disponent.py` erlaubt dem `handels-disponent` nur zwei Befehle:
`python xperp/bot.py` (frischer Kurs) und `python xperp/handeln.py --vorschau`.
Alles andere (`--live`, `--papier`, `--wachen`, Verkettung, Pipes, Umleitungen) liefert Exitcode 2.

## Verdrahten (erst nach Freigabe)

Im Kopf von `~/.claude/agents/handels-disponent.md` ergänzen. Der Hook gilt dann nur,
solange dieser Agent läuft:

```yaml
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: python "<Wurzel>/Agenten/Handel/agenten/bash_wache_disponent.py"
```

`<Wurzel>` durch den lokalen Pfad der BrainFiles-Wurzel ersetzen (nicht ins Repo schreiben).

## Prüfen

Siehe Beispiele im Kopf des Skripts; Gegenprobe:
`echo {"tool_input":{"command":"python xperp/handeln.py --live"}} | python bash_wache_disponent.py` → Exitcode 2.

## Grenzen

- Sperrt nur `Bash` des Disponenten. Ein anderes Werkzeug mit Schreibrecht auf `wachen.json`
  (`Write`, `Edit`) hat er nicht in seiner `tools:`-Zeile.
- Eine Erlaubnisliste kennt nur das, was drinsteht: neue Hilfsskripte müssen dort eingetragen werden.
