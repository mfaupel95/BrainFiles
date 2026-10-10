# Handelswissen — Knowledge Base

## Nutzung (für Agenten)
1. Diesen Index zuerst lesen. Notes nach Beschreibung auswählen; nur die relevanten öffnen.
2. Für eine Frage 1–3 spezifische Notes bevorzugen, nicht alles scannen.
3. Beim Zitieren die Note-`id` angeben.

## Pflege (für Agenten)
- Neue Idee → neue atomare Note. Gleiche Idee, neue Info → Note in-place bearbeiten und `updated` erhöhen.
- Jede Anlage / Umbenennung / Löschung muss Registry und `_topic.md` im selben Zug aktualisieren.
- Nur Tags aus der Controlled-Vocabulary verwenden; neue Tags hier eintragen, bevor sie genutzt werden.

## Controlled Tags
`handel`, `llm`, `architektur`, `strategie`, `verbesserer`, `kombination`, `implementierung`

## Registry

### selbstverbessernde-spuren
- `20261006-verbesserer-architektur` — **Verbesserer-Architektur** — `topics/selbstverbessernde-spuren/verbesserer-architektur.md` — Aufbau und Ablauf des Verbesserer-Moduls: wöchentliche Vorschlags-Schleife, Bewertung, Übernahme.
- `20261007-spur-bewertung` — **Spur-Bewertung** — `topics/selbstverbessernde-spuren/spur-bewertung.md` — Metriken und Schwellwerte, nach denen der Verbesserer entscheidet, ob eine Spur schlecht, ineffizient oder verbesserungswürdig ist.
- `20261007-verbesserer-ausloeser` — **Verbesserer-Auslöser** — `topics/selbstverbessernde-spuren/verbesserer-ausloeser.md` — Wann der Verbesserer aktiv wird — zeitgesteuert alle paar Tage oder ereignisgesteuert bei starkem Momentum.
- `20261007-papier-experiment-zyklus` — **Papier-Experiment-Zyklus** — `topics/selbstverbessernde-spuren/papier-experiment-zyklus.md` — Wie Verbesserungsvorschläge auf Papier getestet, im Journal festgehalten und bei Erfolg in die Live-Spur übernommen werden.
- `live-spur-aktuell` — **Spur-Aktueller-Stand** — `topics/selbstverbessernde-spuren/spur-aktuell.md` — Automatisch generierter Tagesstand aller Spuren mit Urteil (OK/BEOBACHTEN/VERBESSERN).

### llm-signalgeber
- `20261006-llm-als-signal` — **LLM als Signalgeber** — `topics/llm-signalgeber/llm-als-signal.md` — Konzept: wie ein LLM Kursdaten interpretiert und daraus Handelssignale erzeugt.
- `20261007-prompt-design-ohlcv` — **Prompt-Design für OHLCV-Input** — `topics/llm-signalgeber/prompt-design-ohlcv.md` — Wie OHLCV-Kerzen in einen LLM-Prompt überführt werden und welche Strukturen zuverlässige Signale liefern.

### strategien-implementierung
- `20261006-spur-typen` — **Spurtypen und Implementierung** — `topics/strategien-implementierung/spur-typen.md` — Überblick der aktiven Spuren (Spur 1 Kraken, Spur 2 OKX-Perpetuals) und ihrer Code-Strukturen.

### kombinationen
- `20261006-signal-kombinationen` — **Signalkombinationen** — `topics/kombinationen/signal-kombinationen.md` — Muster für die Verbindung mehrerer Signalquellen zu einem Handelsentscheid.
