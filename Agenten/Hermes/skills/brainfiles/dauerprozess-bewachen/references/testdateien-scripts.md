# Testdateien unter Agenten/Hermes/scripts

## Der Ordner `scripts/tests/` ist gitignoriert

`Agenten/Hermes/scripts/tests/` ist per .gitignore ausgenommen — die
Wachen-Tests dort (test_carry_wache.py, test_n8n_wache.py, ...) sind
**unversionierter Arbeitsstand**, kein Repo-Artefakt. `git add` auf diesen
Ordner wird mit „The following paths are ignored“ abgewiesen. Ein versionierter
Test gehoert ausserhalb von `scripts/tests/`.

## dateischwund (T-100)

Frisch per write_file geschriebene Dateien in diesem Baum koennen innerhalb von
Minuten verschwinden (nur `__pycache__` bleibt). Belegt mehrfach, auch in
`scripts/tests/`. Regeln:

- Den Test **direkt nach dem Schreiben ausfuehren** und das Ergebnis festhalten
  — nie auf die Datei als dauerhaftes Artefakt bauen.
- Nach jedem write_file in `Agenten/Hermes/scripts` sofort `git add`/committen,
  wenn die Datei versioniert werden soll (der Schwund faellt sonst erst als
  „pathspec did not match any files“ beim Commit auf).
- Ein Test, der ein Skript mit Bindestrich im Namen importieren will, laedt es
  per `importlib.util.spec_from_file_location` (ein `import n8n_wache` findet
  `n8n-wache.py` nicht).
