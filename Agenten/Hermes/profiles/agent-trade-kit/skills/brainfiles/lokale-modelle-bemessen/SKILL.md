---
name: lokale-modelle-bemessen
description: "Modelle gegen den VRAM bemessen und Ollama einstellen."
category: brainfiles
---

# Lokale Modelle gegen den VRAM bemessen

## Wann
„Passt Modell X auf die Karte“, „welche Quantisierung“, „wie viel Kontext geht“,
„das Modell ist langsam“, „läuft das noch auf der GPU“, `Out of memory`, oder
wenn ein Modell heruntergeladen oder umgewandelt werden soll. Auch immer dann,
wenn eine Größenangabe aus dem Gedächtnis kommt („12–14B passen knapp“) — sie
ist eine Vermutung und wird nachgerechnet.

## Prozedur
1. **Karte und freie Reserve messen**, nicht schätzen:
   `nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv`.
   Auf diesem Rechner lügt WMI (meldet 4 GB für eine 8-GB-Karte) — nvidia-smi
   ist die Wahrheit. Die Belegung **vor** dem Laden ist die Vergleichsbasis.
2. **Bestand aufnehmen:** alle `.gguf`-Dateien mit echter Größe auflisten.
   Nicht annehmen, dass ein Name die Parameterzahl nennt — „E4B“ war in
   Wahrheit ein 7,5-Mrd-Modell.
3. **Kopf lesen statt raten:** `scripts/gguf-kopf.py <datei.gguf>` liefert
   Parameter, Blockzahl, KV-Köpfe, Kopfdimensionen, Trainings-Kontext und die
   echten Bits je Parameter. Die Gegenprobe rechnet die Gewichte gegen die
   Dateigröße; weicht sie um mehr als ~1 % ab, stimmt das Bit-Modell nicht.
4. **Rechnen:** Gewichte und KV getrennt, dann erst addieren —
   Formeln, Bitwerte und Grenzwerte in `references/vram-faustregeln.md`.
5. **Messen statt glauben.** Modell mit dem gewünschten Kontext bauen und
   laden, VRAM-Delta gegen die Rechnung stellen, `ollama ps` auf die
   Prozessorverteilung ansehen. Die Rechnung ist die Vorhersage — die Messung
   entscheidet.
6. **Eine Empfehlung:** eine Quantisierungsstufe und ein Kontextwert, mit der
   Zahl, die sie trägt („5,0 GiB bei 100 % GPU“). Keine Optionsliste.

## Regeln (Standing)
- **Der Kontext gehört ins Modelfile, nicht in die Umgebung.**
  `PARAMETER num_ctx <n>` beim Anlegen:
  `ollama create <name> -f Modelfile`. Danach **immer** mit `ollama ps`
  prüfen, dass in der Spalte `CONTEXT` der gewünschte Wert steht — nur was
  dort steht, ist gesetzt. Eine Umgebungsvariable allein ist kein Beleg.
- **Der Trainings-Kontext aus dem Kopf ist kein Betriebswert.** Ohne eigene
  Angabe nimmt Ollama ihn (gemessen: 262144 statt 8192) und zahlt ihn aus dem
  KV-Cache — das ist der größte Einzelhebel, den es hier gibt.
- **Jede Zahl, die einen Kauf oder Download begründet, braucht eine Messung.**
  Eine Empfehlung ohne gemessenen Verbrauch ist eine Schätzung.

## Pitfalls
- **Dienstaufrufe mit Zeitgrenze fahren, nie blank.** `ollama list` bzw. `curl` gegen
einen nicht laufenden Dienst blockieren bis zum Werkzeug-Timeout (180 s) und verbrennen
den ganzen Schritt: `timeout 20 ollama list`, `curl -s -m 5 http://127.0.0.1:11434/api/tags`.
Und die Namen, Quantisierung und `capabilities` (`tools`/`thinking`) **am Dienst** abfragen,
nicht aus `config.yaml` oder dem Gedächtnis — ein Provider-Block darf veraltete
Modellnamen führen, ohne dass es auffällt.
- **Ladungsdeltas sind nur bei sauberer Grundlast vergleichbar.** Vor dem
  Messen entladen (`ollama stop <name>`), dann warten, bis der Speicher
  nachweislich zurück ist (`ollama ps` leer und nvidia-smi auf Grundlast) —
  sonst misst man das Vorgängermodell mit, und der zweite Wert ist zu klein.
  Bei verunreinigter Basis die Messung wiederholen, nicht interpretieren.
- **`ollama ps` entscheidet über „läuft auf der GPU“.** `100% GPU` ist das
  Ziel; eine Aufteilung wie `42%/58% CPU/GPU` erklärt Langsamkeit besser als
  jede Quantisierungsstufe, und der Kontext ist meist die Ursache.
- **Nicht aus der Dateigröße auf den VRAM-Bedarf schließen.** Gemessen kann
  deutlich weniger im VRAM landen als die Datei groß ist (Treiber/mmap) — eine
  Vorhersage „passt nicht“ ist erst widerlegt, wenn sie gemessen wurde. Die
  Datenmenge bleibt real, die Verteilung ist offen; das gehört als offener
  Punkt in den Bericht, nicht als Behauptung in die Empfehlung.
- **Die Aktivierungsseite (A4/A6) spart keine Gigabyte.** Sie greift nur den
  Rechenpuffer, Größenordnung einige hundert MB. Für „passt es“ zählen allein
  Gewichtsstufe und KV-Cache.
- **Kontext verdoppeln verdoppelt den KV.** Bei kleiner KV-Kopfzahl ist der
  KV der Deckel, nicht die Quantisierung — ein langer Trainings-Kontext ist
  dann unerreichbar, egal wie klein die Gewichte sind.
- **Der Import eines vorhandenen GGUF als Ollama-Modell ist billig** (Kopie im
  Store, kein Download) und der schnellste Weg zu einer belastbaren Messung.
  Aufräumen danach mit `ollama rm <name>`.
- **`localhost` und `127.0.0.1` sind auf diesem Rechner NICHT dieselbe
  Ollama-Instanz.** `localhost` löst auf `::1` (IPv6) auf, wo eine ZWEITE,
  modell-lose Instanz lauschen kann — ein Aufruf gegen
  `http://localhost:11434/api/generate` mit einem installierten Modell liefert
  dann `404 model not found`, obwohl `ollama list`/`curl 127.0.0.1:11434/api/tags`
  das Modell zeigt (die Abfrage traf zufällig die richtige Instanz, der Aufruf
  die falsche). Jeden Ollama-Client fest auf `127.0.0.1` eintragen, nie
  `localhost`. Bei einem 404 „model not found“ für ein nachweislich
  installiertes Modell zuerst `localhost` und `127.0.0.1` EINZELN gegen
  `/api/tags` UND `/api/generate` testen, bevor am Modellnamen gesucht wird.

## References
- `references/vram-faustregeln.md` — Formeln, Bitwerte je Stufe, gemessene
  Werte dieses Rechners und die Grenzwerte für 8 GB VRAM.
- `scripts/gguf-kopf.py` — liest den GGUF-Kopf und rechnet Gewichte je Stufe
  und KV je Kontext. Aufruf: `python scripts/gguf-kopf.py <datei> [--kontext N]`.
- `references/fremdrepo-auf-ollama.md` — ein fremdes Agenten-Repo (Werkstatt-Klon)
  ohne Schluessel auf das lokale Ollama ziehen: Modellpfad im Code finden,
  Standardmodell und Basis-URL aus der Umgebung, Rueckfall statt `None`, Nachweis
  mit einem echten Aufruf.
