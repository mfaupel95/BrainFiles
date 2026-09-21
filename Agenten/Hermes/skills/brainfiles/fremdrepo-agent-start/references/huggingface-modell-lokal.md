# Fremd-Repo mit HuggingFace-Modell lokal betreiben

Gilt fuer Repos, die keine App sind, sondern eine Bibliothek um ein
transformers-Checkpoint (laya, jev-artige Entscheidungsmodelle,
Klassifikatoren, Speech-Modelle). Ziel: Modell laeuft lokal, Beweis mit
eigenen Zahlen, Gewichte liegen nicht auf C:.

## Einrichten (5 Schritte)

1. Klon wie ueblich nach `Werkstatt/Repos/<name>` (origin = Fork, upstream =
   Original). 54 Commits sind klein genug fuer einen VOLLEN Klon — shallow
   nur bei grossen Baeumen, und dann `git fetch --unshallow upstream` vor
   jedem Push.
2. Eigenes venv aus python.org, NICHT aus uv (uv setzt PYTHONHOME in die
   Prozessumgebung und vergiftet Kinder):
   `C:\Users\faupe\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv`
   Die Ausgabe "Actual location may have moved due to redirects, links or
   junctions" ist harmlos (Werkstatt ist eine Junction auf O:).
3. `./.venv/Scripts/python.exe -m pip install -e .` im Klon (editierbar, so
   laeuft der eigene Fork-Code, nicht das PyPI-Paket). `torch` allein sind
   ~280 MB als CPU-Wheel, das ganze venv ~0,9 GB.
4. Gewichte in den HF-Cache auf O: zwingen: `HF_HOME=O:\Modelle` beim Aufruf
   mitgeben. HF_HOME ist auf diesem Rechner NICHT als Benutzer-/Maschinen-
   variable gesetzt; ohne den Wert landen die Gewichte in
   `C:\Users\faupe\.cache\huggingface` (C: ist fast voll, O: hat ~240 GB
   frei). Der bestehende Cache `Modelle/hub` beweist, dass O:\Modelle der
   Hauspfad ist.
5. Sonde schreiben und EINMAL echt laufen lassen, bevor irgendetwas verdrahtet
   wird — Wegwerfskript nach `Agenten/Hermes/cache/<name>_probe.py`, Aufruf
   mit dem Repo-venv und absoluten Pfaden:
   `HF_HOME='O:\Modelle' USE_TF=0 ./.venv/Scripts/python.exe 'C:\...\cache\probe.py'`

## Sonde: was sie zeigen muss

- **Ladezeit** (erster Lauf baut das Modell + laedt Gewichte: 60 s sind
  normal), **Latenz je Aufruf und je Frage**, **device** — alles als Zahl,
  nicht als Gefuehl.
- **Ein Gegenbeispiel**, dessen Antwort man selbst kennt: zwei Texte, in
  denen offensichtlich eine Kuendigung/eine Frist steht, und dann pruefen, ob
  die noul-/score-Felder das treffen. Genau hier faellt auf, ob ein Modell
  brauchbar ist oder nur selbstbewusst.
- Ergebnis in den Bericht als "gemessen auf dieser Maschine" — nie die
  Herstellerangaben (T4-Latenzen, Benchmark-Genauigkeit) als eigene Zahl
  weitergeben.

## Pitfalls

- **`du` auf den Modellordner luegt:** `Modelle/hub/models--<org>--<name>/`
  enthaelt nur Symlinks (KB-Groesse). Die echten Gewichte liegen in
  `Modelle/hub/blobs/<erste 2 Zeichen>/<sha>` — dort messen
  (`ls -lh hub/blobs/*/*`), sonst meldet man faelschlich "Modell nicht
  geladen", obwohl es da ist.
- **`pip install torch` auf Windows zieht hier das CPU-Wheel.** Ein
  `device="cuda"` faellt dann still auf CPU zurueck (Warnung
  "CUDA requested but not available. Falling back to CPU.") — kein Fehler,
  nur ein anderer Rechenweg. GPU geraeteseitig pruefen (`nvidia-smi`) und
  entweder das CUDA-Wheel nachinstallieren oder CPU-Zahlen berichten, statt
  GPU-Latenzen zu versprechen.
- **`USE_TF=0` setzen:** transformers probiert beim Import TensorFlow; ist TF
  installiert, kann dessen abseil-Laufzeit die Modellkonstruktion blockieren
  (Haenger ohne Fehlermeldung).
- **Ein Entscheidungsmodell ist kein Entscheider.** Ein Checkpoint, der
  typisierte Antworten mit Wahrscheinlichkeit liefert, sieht fertig aus und
  ist es nicht: unkalibriert und ueberconfident heisst, dass hohe
  Konfidenz keine Warnung bei falscher Antwort gibt. Vor jeder Empfehlung
  eine eigene Sonde mit Gegenbeispielen; Feintuning auf eigene Daten ist der
  eigentliche Weg, Zero-Shot nur fuer grobe, klar abgegrenzte Kategorien.
- **Der Einsatzort wird am Vertrag entschieden, nicht am Modell.** Passt das
  Modell in eine vorhandene Schnittstelle (gleiche Rueckgabe wie eine
  bestehende Funktion), laesst sich "zweite Stimme, erst messen" bauen, ohne
  eine Schwelle zu uebernehmen — das ist der risikoarme erste Schritt.
