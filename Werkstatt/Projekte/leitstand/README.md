# leitstand

Rein lesende Zentrale fuer den Handel (Omnitrade) und die Fremd-Repos.

## Bausteine

- `/leitstand:status`: Handelsauswertung (`omnitrade_auswertung.py`, ohne `--schreibe`)
- `/leitstand:repos`: Git-Status aller Klone unter `Werkstatt/Repos/`
- Skill `leitstand-handel`: Karte fuer Handel, Repos und Hermes-Profile, mit Regeln
- Hook `SessionStart`: Hinweis beim Start

## Grenzen

Das Plugin handelt nicht und schreibt nichts. Orders laufen ausschliesslich
ueber die bestehenden Skripte, nach frischem Preislauf.

## Ausprobieren

```bash
claude --plugin-dir Werkstatt/Projekte/leitstand
```
