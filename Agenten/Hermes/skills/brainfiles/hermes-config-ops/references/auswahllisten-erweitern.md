# Eine kuratierte Auswahlliste erweitern (gemessen 01.10.2026)

Fall: Max meldete „model liste unvollstaendig. alle modelle von nous wieder
eintragen". Der Modellwaehler zeigte fuer den Anbieter `nous` 58 Eintraege, das
Portal liefert 428. Hier steht, wie das gemessen, wo es erweitert und wie es
belegt wurde — uebertragbar auf jede andere vom Code kuratierte Liste.

## Zwei Listen, zwei Wege

| Groesse | Woher | Zahl (01.10.2026) |
|---|---|---|
| Was der Waehler zeigt | kuratiertes Manifest `Agenten/Hermes/cache/model_catalog.json` (Fernabruf, TTL 20 min, Rueckfall = In-Repo-Schnappschuss) plus Portal-Empfehlungen | 50 + 8 = **58** |
| Was der Anbieter kann | Live-Katalog `Agenten/Hermes/provider_models_cache.json` (`/v1/models` mit dem eigenen Schluessel, 1 h TTL) | **428** roh, 423 nach Chat-Filter |

Beide Wege sind Wahrheit, aber fuer verschiedene Fragen: der Waehler fragt „was
soll ich anbieten", `provider_model_ids` fragt „was gibt es".

```bash
cd Agenten/Hermes && ./hermes-agent/venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'hermes-agent')
from hermes_cli.models import get_curated_nous_model_ids, provider_model_ids
print('kuratiert', len(get_curated_nous_model_ids()))
print('live     ', len(provider_model_ids('nous', force_refresh=True)))"
```

## Code-Stellen (nachgelesen, nicht geraten)

- `hermes_cli/model_switch_providers.py`:
  - `_nous_picker_model_ids()` — Docstring: *„Nous serves a huge live catalog; the
    picker shows ONLY the curated agentic list, augmented with the Portal's
    free/paid recommendations and narrowed by org policy."* Also Absicht, kein Bug.
  - `_lap_overlay_rows()` — hier wird der eigene `providers:`-Block gelesen:
    `configured = user_providers.get(hermes_slug)`, danach
    `model_ids = list(dict.fromkeys([*_declared_model_ids(configured.get("models")), *model_ids]))`
    und `b.add_builtin_row(..., "hermes")`. Der Block wird VORANGESTELLT, die Zeile
    bleibt `source: hermes`.
  - `_UNCAPPED_PICKER_PROVIDERS = frozenset({"opencode-zen", "opencode-go", "nous", "openrouter"})`
    — fuer `nous` greift kein `max_models`-Deckel, die volle Liste ist sichtbar.
- `hermes_cli/model_switch.py::_declared_model_ids` — nimmt `{"id": {...}}`, `["a"]`,
  `[{"id": ...}]` oder `"a"`; ein `models:`-DICT ist Metadaten, KEINE Allowlist.
- `gateway/slash_commands_model.py` (`self.user_provs = cfg.get("providers")`) und
  `tui_gateway/model_switch.py` (`user_provs = cfg.get("providers")`, `cfg = load_config()`
  bei JEDER `/model`-Eingabe) — deshalb wirkt der Block ohne Neustart: `load_config`
  ist an die Dateisignatur gebunden.
- `hermes_cli/model_catalog.py` — Fernabruf des Manifests (`enabled`, `url`,
  `ttl_minutes`, `providers.<name>.url` fuer eine eigene Kurationsliste,
  `excluded_providers` zum Ausblenden). Doku: `reference/model-catalog`.

## Werkzeug und Pruefung

- `Agenten/Hermes/scripts/nous-modellliste-richten.py` — holt die rohe Portal-Liste
  (`_load_provider_models_cache`, sonst `provider_model_ids(..., force_refresh=True)`),
  schreibt `providers: nous: models:` in die Config. Trockenlauf ist Standard;
  `--anwenden`, `--zuruecknehmen`, `--profile`, `--json`. Bytes lesen/schreiben,
  `yaml.safe_load` als Gegenprobe, Sicherung `config.yaml.bak-JJJJMMTT`.
- `Agenten/Hermes/scripts/test_nous_modellliste_richten.py` — 12 Pruefungen auf einer
  KOPIE der Config: eintragen, CRLF erhalten, YAML liest den Block, `model`-Block
  unberuehrt, Rest der Datei gleich, zweites Eintragen still, `--zuruecknehmen` stellt
  den Ausgangszustand byte-gleich her. **Nie auf der echten Config testen.**

## Zahlen des echten Laufs

- Config 835 -> 1265 Zeilen, Commit `fc395e3` (430 Einfuegungen, 1 Datei).
- Waehler-Zeile `nous`: 58 -> **428** Modelle, `source: hermes` unveraendert.
- `hermes config check` Exit 0; `doppelte_nummern.py` Exit 0.
- Commit des Werkzeugs: `1cb59f2` (Werkzeug, Test, Wiki, TASKS), Skill-Abschnitt `3fc9dd0`.

## Uebertragen auf andere Listen

1. **Erst fragen, was die Oberflaeche WIRKLICH liest.** Fuer den Waehler ist das
   `list_authenticated_providers(for_picker=True, user_providers=cfg["providers"])`;
   ohne den zweiten Parameter prueft man eine andere Liste als die gezeigte.
2. **Den Bauplatz lesen, nicht raten.** Ein `search_files` nach dem Listennamen im
   Checkout zeigt die Funktion; ihr Docstring trennt Absicht von Fehler.
3. **Die vorgesehene Erweiterung benutzen** statt den Checkout zu patchen. Fuer
   Anbieterlisten ist das `providers.<name>.models:`; fuer den Fernabruf
   `model_catalog.providers.<name>.url`; zum Ausblenden `excluded_providers`.
4. **Nachzaehlen mit demselben Aufruf wie vorher** und die Zahl nennen
   (58 -> 428). Eine Liste ohne Vorher/Nachher ist kein Nachweis.

## Fallen

- **Ein `models:`-DICT ist Metadaten, keine Allowlist** — es erweitert nur. Wer eine
  Liste VERKLEINERN will, braucht `discover_models: false` bzw. eine Liste/String-Form.
- **`model_catalog.enabled: false`** schaltet den Fernabruf ab und liefert den
  In-Repo-Schnappschuss — nicht die volle Liste; das ist kein Fix fuer „zu wenig".
- **Die App schreibt `config.yaml` aus eigenem Speicher zurueck.** Am 01.10.2026 um
  18:45 lag ein Diff von 19/26 Zeilen gegen HEAD im Arbeitsbaum, den keine Sitzung
  geschrieben hatte (`bonsai`-/`smart`-Block weg, `moa.enabled` false -> true,
  `personality`, telemetry, `desktop.repo_scan_roots`). Ein so zurueckgeschriebener
  Stand loescht frisch eingetragene Bloecke. Nach jeder Einstellungsaenderung in
  Desktop/TUI nachzaehlen: mit `search_files` den Mustertext `claude-opus-4.1:batch`
  in `Agenten/Hermes/config.yaml` suchen — genau 1 Treffer. Offen als T-297.
- **Die Profil-Configs sind eigene Waehler.** Sie tragen den Block nicht; ob sie ihn
  brauchen, ist eine Entscheidung (T-296) — die Bots lesen ihr Modell aus ihrer
  `config.yaml`, nicht aus dem Waehler.
