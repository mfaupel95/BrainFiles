# Wissen über CryptoPredictions Toolkit

## Überblick
CryptoPredictions ist ein Open-Source-Toolkit zur Vorhersage in Python. Implementiert von Amirhossein Alimohammadi und Ahmad Nosratbakhsh, ermöglicht es Benutzern, Vorhersagen basierend auf historischen Daten zu treffen und dabei verschiedene Modellierungsansätze zu verwenden.

## Hauptbestandteile des Toolkits

### Hydra Configurations
- **configs**: Hauptverzeichnis für Konfigurationsdateien, die verschiedene Aspekte des Toolkits steuern.
- **modularer Aufbau**, der eine klare Struktur in Bezug auf Datensätze, Modelle, Optimierer, Scheduler und Visualisierungen aufweist.

### Wichtige Dateien
- **main.yaml**: Hauptkonfigurationsdatei für das Datenmodul.
- **modelfiles**: Beinhaltet spezifische Modellparameter für verschiedene Algorithmen, wie z.B. LSTM, GRU.
- **optimizers**: Bezieht sich auf die Konfiguration von Optimierungsalgorithmen (z.B. Adam, SGD).
- **dataset_loader**: Konfigurationsdateien für das Laden verschiedener Datensätze (z.B. Bitmex, CoinMarket).

### Module und Funktionalitäten
- **vorschlag.py**: Erzeugt Vorschläge basierend auf historischen Daten und Marktanalysen.
- **lauf.py**: Orchestriert die verschiedenen Teile des Toolkits und führt die Hauptlogik aus.
- **digest.py**: Führt wöchentliche Analysen durch und generiert Berichte.

### Nutzung
Das Toolkit erfordert eine Konfiguration über YAML-Dateien und ist darauf ausgelegt, mit verschiedenen Datensätzen und Modellen zu arbeiten, während es beständig aktualisiert und optimiert wird.

## Vermerk im Handelsverzeichnis
Wissen über die Funktionsweise und Implementierung von CryptoPredictions sollte im Handelsverzeichnis vermerkt werden, um den Informationsaustausch und das Lernen zu erleichtern.
