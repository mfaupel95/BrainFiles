# Fremd-Repo mit HuggingFace-Modell lokal betreiben

Gilt fuer Repos, die keine App sind, sondern eine Bibliothek um ein
transformers-Checkpoint (laya, jev-artige Entscheidungsmodelle,
Klassifikatoren, Speech-Modelle). Ziel: Modell laeuft lokal, Beweis mit
eigenen Zahlen, Gewichte liegen nicht auf C:.

## Einrichten (5 Schritte)

1. Klon wie ueblich nach `Werkstatt/<name>` (origin = Fork, upstream =
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
- **Bei einer Prognose gehoert die NULLINIE daneben.** Ein Zeitreihen-Modell,
  das den letzten Kurs fortschreibt ("aendert sich nicht"), ist der
  Vergleichsmassstab: mittlerer Fehler und Richtungstreffer des Modells GEGEN
  dieselben Groessen der Nullinie stellen. Bericht ohne diese Zeile ist keine
  Messung. Und: ein, zwei Hold-out-Fenster sind ein Befund, keine Messung —
  dieselbe Rechnung ueber viele Fenster, bevor eine Zahl als Eigenschaft
  weitergegeben wird. Beides gilt fuer jedes Fremdmodell, das in eine
  Handelsspur soll.

## Pitfalls

- **Repos ohne `pyproject.toml`** (z.B. Kronos: nur `model/` + Beispiel-
  Skripte) werden nicht installiert, sondern benutzt:
  `pip install -r requirements.txt` im venv, Aufruf AUS dem Repo-Ordner, damit
  `from model import ...` greift (sonst `sys.path.insert(0, <repo>)` in der
  Sonde). Ein Modul namens `model` ist kein Paket auf PyPI — nie dort suchen.
- **Gepinnte Abhaengigkeiten sind die haeufigste Absturzursache, nicht das
  Modell.** Beim ersten Lauf auf diesem Rechner (Python 3.13 / Windows)
  starb die Vorhersage mit einer Access Violation, obwohl das Modell sauber
  lud (24,7 M Parameter). `python -X faulthandler` zeigte die Stelle:
  `pandas/core/indexes/datetimes.py`, `date_range` — das von der
  `requirements.txt` gepinnte `pandas==2.2.2` reisst den Prozess ab.
  `pip install -U pandas numpy` (3.0.6 / 2.5.3) war der Fix. Vor jedem
  "Modell unbrauchbar"-Urteil also: faulthandler, dann Pin hochziehen, dann
  erneut messen — kein Grund, die Gewichte zu verurteilen.
- **Das Modell laedt und rechnet — beides getrennt pruefen.** Ein Skript, das
  nur die Vorhersage faehrt, sagt bei einem Absturz nicht, WELCHER Schritt
  gestorben ist. Stufenweise Sonde: (1) Tokenizer laden, (2) Modell laden und
  die Parameterzahl ausgeben (`sum(p.numel() for p in m.parameters())`),
  (3) Predictor bauen, (4) eine winzige Vorhersage auf ZUFALLSDATEN. Erst
  danach die echte Reihe — so ist "Absturz" sofort einer Stufe zuzuordnen.
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
