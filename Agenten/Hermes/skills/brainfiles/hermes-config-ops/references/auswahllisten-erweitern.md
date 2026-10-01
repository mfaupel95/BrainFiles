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

---

## Vollstaendiger Abschnitt aus dem SKILL.md-Rumpf

# Eine unvollstaendige Auswahlliste erweitern (Modellwaehler und Verwandte)


**Wann:** „die Modellliste ist unvollstaendig", ein Waehler zeigt weniger
Eintraege als erwartet, oder ein Anbieter fehlt in der Auswahl. Das Muster gilt
fuer jede vom Code kuratierte Liste — erst MESSEN, was die Oberflaeche zeigt,
dann die Stelle suchen, die Hermes zum Erweitern vorsieht, statt am Code zu
patchen (der Checkout wird aktualisiert, der Patch waere beim naechsten Update
weg).

**1. Messen, was die Oberflaeche zeigt — mit DERSELBEN Funktion, die sie ruft.**
Der Waehler zeigt fuer einen Anbieter mit kuratierter Liste NICHT den vollen
Katalog. Gemessen am 01.10.2026 fuer `nous`: **58 Eintraege sichtbar** (50 aus dem
Manifest `cache/model_catalog.json` plus die Empfehlungen des Portals), waehrend
`provider_model_ids("nous")` **428** Modelle kennt. Hermes sagt es selbst:
`model_switch_providers._nous_picker_model_ids` — „the picker shows ONLY the
curated agentic list". Der volle Katalog liegt im Disk-Cache
`provider_models_cache.json`.

```bash
cd Agenten/Hermes && ./hermes-agent/venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'hermes-agent')
from hermes_cli.config import load_config
from hermes_cli.model_switch_providers import list_authenticated_providers
cfg=load_config()
for r in list_authenticated_providers(for_picker=True, user_providers=cfg.get('providers')):
    print(r['slug'], len(r['models']), r['source'])"
```

**Der Parameter ist der halbe Nachweis.** `user_providers=cfg["providers"]` ist
Pflicht — die Zeilenbauer lesen die eigenen `providers:`-Bloecke nur daraus.
Ohne ihn zeigt derselbe Aufruf die kuratierte Liste: ein Ergebnis, das wie ein
Fehlschlag aussieht, aber der falsche Aufruf ist (`user_provs = cfg.get("providers")`
steht in `gateway/slash_commands_model.py` und `tui_gateway/model_switch.py`).

Die von Hermes vorgesehene Stelle zum Erweitern ist der Config-Block

```yaml
providers:
  nous:
    models:
      "<modell>": {}
```

`_lap_overlay_rows` haengt ihn der Waehler-Zeile VORAN („A
providers.<overlay>.models block extends the row"); die Zeile bleibt
`source: hermes` und behaelt ihre Anmeldung. Derselbe Mechanismus traegt die
`models:`-Liste von `ollama-launch` und `omniroute` — er gilt fuer JEDEN Anbieter.

Werkzeug: `Agenten/Hermes/scripts/nous-modellliste-richten.py` (Trockenlauf ist
Standard, `--anwenden`, `--zuruecknehmen`, `--profile`, `--json`); Pruefungen
`Agenten/Hermes/scripts/test_nous_modellliste_richten.py` (12, auf einer KOPIE
der Config — nie auf der echten).

Nachweis: `list_authenticated_providers(for_picker=True, user_providers=cfg["providers"])`
zaehlt die Modelle der Zeile. **Ohne** `user_providers` zeigt derselbe Aufruf die
kuratierte Liste — ein Aufruf ohne diesen Parameter sieht wie ein Fehlschlag aus,
ist aber der falsche Aufruf.

Falle: die Desktop-/Gateway-App schreibt `config.yaml` aus ihrem eigenen Speicher
zurueck (01.10.2026 um 18:45: Diff 19/26 gegen HEAD, den keine Sitzung geschrieben
hatte). Ein frisch eingetragener Block kann so wieder verschwinden — nach jeder
Einstellungsaenderung in der App nachzaehlen (`grep -c "<modell>" Agenten/Hermes/config.yaml`).

**Der Block ist eine ANZEIGELISTE, keine Freigabe.** Er aendert weder das aktive
Modell noch die Anmeldung des Anbieters; er bestimmt nur, was im Waehler zur Wahl
steht. Wer ihn eintraegt, hat nichts „scharf geschaltet" — das im Bericht auch so
sagen, sonst liest die naechste Sitzung eine Modellauswahl als Konfigurationswechsel.

**Beim Entfernen eines eingerueckten Blocks trifft ein `split` auf die Einrueckung
zu FRUEH.** Ein Blockende zu finden, indem man den Text an `"\r\n  "` teilt, geht
schief: das ist ein PRAEFIX von `"\r\n      "` (sechs Leerzeichen), die Trennung
landet also schon auf der ersten Inhaltszeile — die restlichen Zeilen bleiben mit
ihrer Einrueckung ohne Elternteil stehen und die Datei ist danach ungueltiges YAML.
Richtig ist ein Muster, das GENAU zwei Leerzeichen verlangt:
`re.search(rb"\r\n  (?=[^ ])", rest)` — der Treffer ist die erste Folgezeile der
naechsten Ebene. Und die Gegenprobe gehoert VOR das Schreiben: den neuen Text mit
`yaml.safe_load` parsen und asserten, dass der entfernte Block weg und der Rest
unveraendert ist; das Schreiben selbst erst in der letzten Zeile
(`open(pfad, "wb").write(neu)`). Gilt fuer jeden Block-Schnitt an YAML/JSON,
nicht nur fuer die Modellliste.

**2. Den Bauplatz im Code finden, bevor etwas geschrieben wird.** Der Checkout
liegt unter `Agenten/Hermes/hermes-agent` — mit `search_files` nach dem Anbieter-
oder Listennamen suchen und die Funktion lesen, die die Zeile BAU:

```
search_files pattern="_nous_picker_model_ids|_lap_overlay_rows" path="Agenten/Hermes/hermes-agent/hermes_cli"
```

Der Docstring sagt meist selbst, was Absicht ist („shows ONLY the curated list")
— das ist die Antwort auf „ist das ein Fehler?": nein, eine Design-Entscheidung,
und gesucht ist ihre vorgesehene Erweiterung. Ein Patch im Checkout ist der
falsche Weg: `hermes update` holt den Baum neu.

**3. Eintragen, gegenpruefen, belegen** — Trockenlauf zuerst, dann schreiben, dann
mit demselben Aufruf wie in Schritt 1 nachzaehlen (58 -> 428) und
`hermes config check` (Exit 0) fahren. Ein `yaml.safe_load` der neuen Fassung
gehoert VOR das Schreiben.

**4. Abschluss wie im Haus ueblich:** Wiki-Seite (`Wiki/Betrieb/Hermes.md`,
config.yaml-Fallen) + offener Punkt in `MaxHirn/Archiv/TASKS.md` (stehende Regel)
+ eigener Commit. Fremde Aenderungen in derselben Datei NIE mitnehmen — Verfahren
im Skill `arbeitsbaum-git-hygiene` (`GIT_INDEX_FILE` + `read-tree HEAD`).

Zahlen, Code-Stellen und die Verallgemeinerung auf andere kuratierte Listen:
`siehe oben in dieser Datei` — laden, wenn eine ANDERE Liste klemmt.

#### Die Gegenrichtung: Profil-Listen kuerzen (Auftrag Max 01.10.2026)

„Die botprofile brauchen noch weniger" — die 19 Profile, die je ~1.739 Eintraege aus der
omniroute-`auto/*`-Liste mitkopiert hatten, sind auf das gekuerzt, was das Profil SELBST
nennt (`model.default`, `providers.<p>.model`/`default_model`, `fallback_providers`,
`delegation.model`, `moa`): **33.064 -> 125 Eintraege**, caveman 2248 -> 514 Zeilen.
Der `models:`-Block ist eine ANZEIGELISTE — die Wahl bleibt vollstaendig, weil
`discover_models: true` bleibt und der Waehler mit gesetztem Schluessel die echte Liste live
holt. Werkzeug: `Agenten/Hermes/scripts/profil-modelllisten-kuerzen.py` (Trockenlauf
Standard, `--anwenden`, `--zuruecknehmen`), Pruefungen
`Agenten/Hermes/scripts/test_profil_modelllisten_kuerzen.py` (17, auf Kopien).
**Nie auf den echten Profilen testen**, und nach dem Lauf pruefen, dass der Diff je Datei
NUR Loeschungen zeigt (0 Insertions) — eine Insertion heisst, ein fremder Block ist
mitgewandert. Die Hauptconfig bleibt unangetastet (eigene Entscheidung, T-302).

**Falle in Werkzeugen, die YAML-Bloecke schneiden:** Ein `models:`-Eintrag in Dict-Form kann
selbst Doppelpunkte tragen (`auto/coding:free: {}`) — der Name ist der Teil vor dem LETZTEN
Doppelpunkt (`rpartition`), nicht vor dem ersten. Und in Listenform duerfen die Eintraege
AUF der Hoehe des Schluessels stehen (`models:` / `- x`): ein Blockende-Kriterium
„Einzug <= Schluesseleinzug" bricht dort sofort ab und liest null Eintraege.
