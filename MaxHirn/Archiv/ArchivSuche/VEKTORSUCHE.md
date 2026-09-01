# Semantische Suche (Vektorindex)

Zusatz zum Volltextindex: findet nach **Bedeutung** statt nach Stichwort.
Läuft vollständig lokal — es verlässt kein Byte den Rechner.

**Angelegt:** 2026-08-19

## Aufruf

```powershell
cd C:\Users\faupe\Documents\BrainFiles\MaxHirn\Archiv\ArchivSuche
.\.venv\Scripts\python.exe vektor_index.py          # indexieren, wiederaufnehmbar
.\.venv\Scripts\python.exe vektor_suche.py "frage"  # suchen
.\.venv\Scripts\python.exe vektor_suche.py "frage" --hybrid --limit 10
```

`--kategorie Dokumente|Bilder|Videos|Musik` schränkt ein, `--hybrid` mischt
zusätzlich exakte Volltexttreffer dazu (gut für Namen, Nummern, Aktenzeichen —
dort ist Bedeutungsähnlichkeit systematisch schwach).

## Aufbau

| Teil | Wo |
|---|---|
| Einbettungsmodell | Ollama, `bge-m3` (1024 Dimensionen, mehrsprachig, gutes Deutsch) |
| Vektoren | `vektor_index.db` — **eigene** Datei neben `archiv_index.db` |
| Suche | NumPy-Skalarprodukt über alle Abschnitte |

**Warum eine zweite Datenbank:** Ein abgebrochener oder beschädigter Vektorlauf
darf die funktionierende Volltextsuche nicht gefährden. `vektor_index.db`
löschen setzt nur den Vektorteil zurück. `archiv_index.db` wird ausschließlich
lesend geöffnet (`mode=ro`).

**Warum keine Vektordatenbank als eigenes Bauteil:** Bei rund 4.000–5.000
Abschnitten à 1024 Werten sind das ~20 MB. Ein NumPy-Skalarprodukt darüber
dauert Millisekunden. sqlite-vec, FAISS oder Chroma wären zusätzliche native
Abhängigkeiten ohne messbaren Gewinn — und jede native Abhängigkeit ist ein
weiterer Grund, warum nach dem SSD-Umzug etwas nicht mehr startet.

**Warum Ollama statt sentence-transformers:** Kein PyTorch im venv (~2,5 GB),
keine CUDA-Abhängigkeit, und dieselbe Laufzeit trägt später ein lokales
Sprachmodell.

## Nur Dateien mit echtem Text

Eingebettet wird nur, was **mindestens 200 Zeichen** extrahierten Text hat.
Gemessen am 19.08.2026: von 7.631 Archivdateien erfüllen das **1.036** — fast
ausschließlich Dokumente sowie 28 Bilder mit OCR-Treffern. Musik und Videos
haben gar keinen Text.

Der erste Testlauf ohne diese Schwelle lieferte auf die Frage
„Rechnung für ein Gerät" auf den Plätzen 1 bis 5 ausschließlich Bilddateien mit
Namen wie `(m=eidYGCjadqg)(mh=kK9HQ…)200x200.jpg`. Der Grund: Ein Vektor aus
einer bedeutungslosen Zeichenkette ist zu allem mäßig ähnlich und verdrängt
echte Treffer. Dateien ohne Text findet weiterhin die Volltextsuche über Namen
und Pfad — dafür braucht es keine Bedeutungsähnlichkeit.

`vektor_index.py` räumt bei jedem Lauf Einträge weg, die die Schwelle nicht
mehr erfüllen.

## Stromausfall-Festigkeit

Der Rechner schaltet sich unangekündigt ab (siehe [[Hardware]]). Deshalb:

- **Eine Transaktion je Datei.** Bricht der Lauf ab, ist jede bis dahin
  geschriebene Datei vollständig; der nächste Aufruf macht dort weiter.
- **WAL-Modus**, damit ein hartes Aus die Datenbank auf dem letzten
  abgeschlossenen Stand zurücklässt statt beschädigt.
- Ein Neustart nach Abbruch kostet nichts — er überspringt alles Fertige.

## Geschwindigkeit hängt am freien VRAM

Gemessen 19.08.2026: **2,3 Abschnitte/s**, unabhängig von der Stapelgröße.
`ollama ps` zeigte dabei `94%/6% CPU/GPU` — das Modell lief fast vollständig auf
der CPU.

Ursache: **`Star Wars Outlaws` belegte 7,5 GB der 8 GB VRAM.** Ollama lädt ein
Modell nur dann auf die GPU, wenn es vollständig hineinpasst; bge-m3 braucht
rund 1,3 GB und fiel deshalb auf die CPU zurück.

**Vor einem Indexlauf GPU-Anwendungen schließen.** Prüfen mit:

```powershell
nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv
ollama ps    # muss "100% GPU" zeigen, nicht "94%/6% CPU/GPU"
```

Der Lauf funktioniert auch auf der CPU, dauert dann aber ein Vielfaches
(~40 min statt weniger Minuten für den Erstlauf).

## Nach dem SSD-Umzug

`vektor_index.db` kann mitkopiert werden — sie enthält keine absoluten Pfade
außer den Archivpfaden, die sich mit dem Vault ohnehin mitbewegen. Nach dem
Neuaufbau des `.venv` (siehe [[Portabilitaet]]) zusätzlich `numpy` installieren:

```powershell
.venv\Scripts\python.exe -m pip install numpy
```

Ollama selbst zieht nicht mit — es ist unter `%LOCALAPPDATA%\Programs\Ollama`
installiert und muss auf dem Zielrechner vorhanden sein, ebenso das Modell
(`ollama pull bge-m3`).
