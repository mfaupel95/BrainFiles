# MoA, Hilfsmodelle und Cache-Stufen richtig verdrahten

Drei Bloecke, die man beim \"Desktop optimal einrichten\" gemeinsam faehrt und
die drei verschiedene Fehlerklassen haben: `moa:`, `auxiliary:` und
`prompt_caching:`. Jeder laesst sich MIT KONFIG setzen und damit behaupten,
dass etwas laeuft - der Nachweis ist jeweils ein eigener.

## MoA: der Aggregator IST das handelnde Modell

Ein Preset ist kein Beratergremium neben dem Hauptmodell, sondern ein
**Austausch des Hauptmodells fuer eine Sitzung**:

- Die `reference_models` beraten einmal je User-Turn (bei
  `fanout: user_turn`) und liefern freien Text.
- Der `aggregator` **handelt**. Er laeuft in jedem Werkzeugschritt, fuehrt die
  Tools aus und traegt fast die gesamten Kosten des Laufs.

Daraus folgt die einzige Regel, die hier etwas kostet: **ein Aggregator auf
einem lokalen Modell ist fast immer ein Fehlbau.** Ein lokales Ollama-Geraet
haelt mehrere GB RAM, antwortet um Sekunden langsamer und verliert gegen den
Aggregator bei jedem Werkzeugschritt. Genau das stand in zwei Presets, und ein
weiteres Preset hatte einen lokalen Berater, dessen Dienst gar nicht laeuft.
Wenn ein Aggregator auf einem lokalen Modell steht, ist das der Befund - nicht
der Preset.

`fanout: per_iteration` vervielfacht die Beraterkosten mit der Tiefe der
Werkzeugschleife. Fuer lange Werkzeugketten `user_turn` (Vorgabe) lassen.

**Tote Schluessel im Preset.** Ein Schluessel, den weder `hermes moa list` noch
die Normalisierung (`hermes_cli/moa_config.py::_normalize_preset`) kennt, wird
niemals gelesen. `max_tokens: 64096` stand dort und tat nichts: gelesen wird
`reference_max_tokens`, und das nur als Aufrufargument. **Vor dem Uebernehmen
eines Preset-Feldes den Leser suchen** (`grep` nach dem Feld in `moa_config.py`
und `agent/moa_loop.py`) - ein Feld, das nur im Listing-Listing steht, ist
Text, keine Einstellung.

**Nachweis:** `hermes moa list` (zeigt die Normalisierung, also die Form, in der
die Presets gelesen werden) und EIN echter Lauf ueber den Aggregator-Pfad:
`hermes chat --oneshot -q "<marke>" --provider moa`. Die Referenzzeilen im
Ergebnis (`Reference 5/5 - <provider>:<modell>`) belegen die Berater, die
Endantwort den Aggregator.

## `auxiliary:` - `auto` erbt das HAUPTmodell

`provider: auto` heisst nicht \"billig\", sondern **\"das Modell dieser
Sitzung\"**. Auf einem GROSSEN Hauptmodell zahlt damit jeder Einzeiler-Aufruf
mit dem grossen Preis:

| Aufgabe | Art | Verschwendung, wenn `auto` |
|---|---|---|
| `approval` | Klassifizierer, ~1 Satz | hoch - laeuft bei jedem gesperrten Befehl |
| `title_generation` | Sitzungstitel | mittel - einmal pro Sitzung |
| `skills_hub` | Metadaten-Liste | mittel |
| `curator` | Skill-Review ueber lange Laeufe | hoch - nimmt Minuten |
| `mcp` | Werkzeugbeschreibung | mittel |
| `memory_query_rewrite` | Suchanfrage umschreiben | mittel |
| `compression` | lange Zusammenfassung | **darf nicht** billig sein |
| `vision` | Bildverstaendnis | **darf nicht** ein Textmodell sein |

Auf ein kleines, gemessenes Modell zu setzen lohnt bei allen bis auf
`compression` (braucht ein grosses Fenster - unter 64k bricht die Kompression
ab) und `vision` (ein Textmodell kann keine Bilder). Fuer Aufgaben, die
**strukturiertes JSON** liefern muessen (Kanban-Triage, Zerlegung in
Child-Tasks), ein schnell bestaetigtes Modell waehlen und **am echten Aufruf
pruefen, ob `content` gefuellt ist** - ein Denkmodell mit kleinem
`max_tokens` liefert leeren `content` und schiebt den Text nach `reasoning`.

**`provider: auto` ist kein Fehler, sondern eine Entscheidung.** Es ist richtig,
wenn das Hauptmodell selbst das guenstige ist, und falsch, wenn es das teure
ist. Diese Frage beantwortet man pro Aufgabe, nicht pro Datei.

## `prompt_caching.cache_ttl`

Werte sind `5m`, `1h`, `auto` und aus. Die Tiers kosten unterschiedlich beim
**Schreiben** (1h etwa doppelt so viel wie 5m) - gegen den **Lesen** ist der
Unterschied der Punkt, den man kaufen will.

`auto` heisst: **1h fuer alles, was ein Mensch tippt** (cli, tui, desktop,
Messaging), **5m fuer maschinell getaktete Quellen** (`subagent`, `cron`,
`kanban`, `oneshot`, `webhook`, `api`). Das ist fast immer die richtige Wahl:
Subagenten rechnen am Stueck durch und brauchen keine lange Tier, eine
Desktop-Sitzung mit Pausen von mehreren Minuten schon.

Der Wert wird **einmal je Sitzung** aus der Quelle der Sitzung abgeleitet, nicht
je Turn - eine laufende Sitzung nimmt eine Aenderung erst mit der naechsten
Sitzung an. Und: unbekannte Werte bleiben still auf `5m`, es gibt keine Warnung.

**Nachweis, und der ist nichttrivial.** Ein `cache_read`-Anteil von 100 % ueber
viele Sekunden hinweg unterscheidet 5m **nicht** von 1h. Der Beleg braucht eine
Pause laenger als das kurze Tier und denselben Prefix danach:

1. Im Sitzungsprotokoll zwei Aufrufe suchen, zwischen denen **mehr als 5 Minuten**
   liegen, und die `cache_read`-Zahl des zweiten mit der `in`-Zahl des ersten
   vergleichen. **Gleich** heisst: der Prefix hat den Ablauf ueberlebt.
2. Gegenprobe: dieselbe Konstellation auf `cache_ttl: 5m` wiederholen. Ohne sie
   ist "100 % nach 7 Minuten" mit beiden Werten erklaerbar.

Faellt die Zeit zwischen zwei Aufrufen nie so gross aus (Durchsatz ohne
Pausen), ist der Nachweis **nicht** erbracht - dann ist die Verdrahtung ueber den
Code belegt (Aufloeser des Werts je Quelle aufrufen, nicht die Datei lesen) und
die Wirkung bleibt offen. Das ehrlich benennen; eine nicht gemessene Ersparnis
als Ersparnis zu melden ist die teuerste Form von "funktioniert".

## Was sich NICHT lohnt umzustellen

- `cache_ttl` auf maschinell getakteten Profilen (Bots): `auto` gaebe ihnen
  ohnehin 5m. Eine Aenderung ohne Wirkung ist eine zweite Wahrheit.
- `compression.threshold` auf Profilen mit kurzen Sitzungen: eine Schwelle nahe
  0.7 schaltet die Kompression praktisch ab, statt sie zu tunen.
- Alles, was das Profil-Hauptmodell bereits richtig bedient - ein Preset
  bekommt keinen MoA-Block, weil es eine MoA-Verdrahtung ist, keine
  Profilverdrahtung.

## Fallstricke beim Ersetzen

- **Ein Schluesselname kann im selben Block mehrfach vorkommen** (z. B. ein
  Aggregator-Slot im Preset UND dieselbe Angabe als flache Kompatibilitaets-
  Ausgabe auf der Ebene darueber). Eine Suche vom Dateianfang trifft die
  falsche Stelle - ab dem gesuchten Blocknamen suchen.
- **Ein Kommentar an der Blockgrenze gehoert zum Block, nicht zum Nachbarn.**
  Ein Kommentar mit Block-Einrueckung, gefolgt von einem Top-Level-Schluessel,
  verschiebt beim Ersetzen den Nachbarn in den Block hinein.

Beide Faelle und das byteweise Muster, mit dem ein Preset-Bloch sicher
geschrieben wird: `references/einstellung-umstellen.md`.