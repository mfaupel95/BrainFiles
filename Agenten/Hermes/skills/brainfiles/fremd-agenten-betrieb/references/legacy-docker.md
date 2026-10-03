# Legacy-Fremd-Repos in Docker (TF-1.x-Aera)

Repos aus der TensorFlow-1.x-Zeit (README nennt `python=3.6`, conda-
Anleitungen, `stable_baselines` der ersten Serie, MPI-Nota) sind auf diesem
Host NIE installierbar: die Interpreters sind 3.9+, TF 1.15 hat keine Rader
ab 3.8, und `tensorflow.contrib` (das `stable_baselines` beim Import verlangt)
ist in TF 2 gestrichen. Ein Host-venv darauf ist eine Sackgasse, die erst beim
Import auffaellt. Die Klasse ist "betreibbar als Docker-Bild (CPU)" — nicht
reparierbar auf dem Host. Alte GPU-Frameworks verstehen Ampere-Karten nicht:
CPU ist der ehrliche Modus, nicht der Notbehelf — das in der Akte sagen.

## Erst: Anspruch messen, dann pinnen

- Die Bauanleitung des Repos lesen (Dockerfiles, requirements). Upstream-
  Basisbilder alter Distros (jessie/buster, auch `python:3.6.8-jessie`) haben
  tote apt-Quellen: seit LTS-Ende liegt die Distro nur noch auf
  `archive.debian.org` (NUR `main` — ein `bullseye-security`-Pfad existiert
  dort nicht, 404). Eigenes Dockerfile: Quelle umbiegen, eigene Pins,
  Basisbild naechste tragfaehige Stufe.
- Pines nicht raten, sondern an harten Zeugen festmachen:
  - Framework-Importfehler ist der Zeuge fuer die Aera (`tensorflow.contrib`
    fehlt -> TF 1.x; `typing.TypedDict` braucht erst Python 3.8, also die
    Vor-3.8-Rader der Nebenpfade).
  - Mitgebrachte Datenbanken im Repo nach SCHEMA-Version fragen (bei optuna-
    Aera: `alembic_version`/`version_info` in der db) — die Such-API des
    Codes (`trial.should_prune(step)`, `optuna.structs`) passt nur zur
    passenden Major. Ein falscher Pin macht die Analyse still leer statt laut
    rot.
  - Eine Bibliothek, die ihr eigenes Rad nicht bauen kann (invalides
    Extras-Muster in `setup.py`, z. B. `opencv-python>=3.`), durch die
    naechst-aeltere, BAUBARE Version ersetzen — nicht mit gcc nach pruegeln.
- Reine Import-Pruefung vor dem ersten echten Lauf: ein `python -c` im fertigen
  Bild, das ALLE Hauptimporte der Kette hat (auch die, die ein Paket-Import
  still mitbringt: cv2, mpi4py ueber `trpo_mpi`). Diese Probe findet die
  Nachzu-Pins in einer Minute statt pro Lauf in zehn. `stable_baselines` mit
  `--no-deps` setzen, sonst zieht es sein eigenes Extras-Grab.

## Docker Desktop: Filesharing ist die unsichtbare Wand

- Was mounted werden darf, steht in
  `%APPDATA%\Docker\settings-store.json` -> `FilesharingDirectories`. Ein Bind
  aus einem NICHT freigegebenen Ort (auf diesem Rechner: alles unter
  `O:\Werkstatt...`, auch ueber die `Werkstatt`-Junction, auch
  `%USERPROFILE%`-Orte) bringt den Container STILL in `Created` haengen — kein
  Fehler, keine Meldung, nur ein Timeout des Aufrufs. Vor jedem Mount-Design
  die Liste lesen, nicht die Docker-Doku.
- Die Regel daraus: **Code ins Bild (COPY), nicht mounten.** Der
  Build-Kontext laeuft ueber die CLI und darf jede Platte lesen (auch O:).
  `.dockerignore` muss die Altlasten des Klons ausschliessen (`venv`,
  `__pycache__`, grosse Medien), sonst tarnt sich ein 1-GB-Kontext.
- **Schreibende Daten nur in ein Volume innerhalb des geteilten Gebiets** —
  im Haus: `Agenten/Hermes/cache/<repo>/...`. Vor dem ersten Lauf alle
  Unterordner anlegen, die der Code beim Speichern erwartet (agents/reports/
  tensorboard/log): fehlende Ordner werfen erst am ENDE des Laufes —
  FileNotFoundError beim Modell-Speichern nach zwoelf Minuten Training.
  Build-Cache pflegen: grosse Abhaengigkeitsschicht UNVERANDERT lassen
  (Requirements-Datei byte-gleich halten), Nachzu-Pins in eigene RUN-Schichten.

## Wrapper-Dateien: .cmd und Dockerfile

- `.cmd` braucht CRLF und einfache Backslashes. Ueber Tool-Heredocs/Inline-
  Python geschrieben droht doppeltes Ungluck: Escape-Schichten fressen
  Backslash-Folgen, und ein `'\r'` im Text wird zu einem echten CR (eine
  `cache\rltrader`-Zeile wird zu `cache<CR>ltrader`). Sicherer Bauplatz:
  Zeilenliste in Python, Ruckstrich ueber `chr(92)` bauen,
  `('\r\n'.join(zeilen)).encode('ascii')` schreiben, Gegenprobe `cat -A`.
- Dockerfiles ohne Zeilenfortsetzungen bauen (eine Anweisung pro Zeile) —
  Fortsetzungs-Backslashs sind genau das, was beim Hineinschreiben stirbt.
  Laengere Layer-Folge statt `&&`-Kette: jeder RUN cachebt fuer sich.
- CLI-Ecke: argparse-Unterbefehle erben keine Top-Level-Schalter — globale
  Optionen MUESSEN vor dem Unterbefehl stehen; im Wrapper und im
  Manifest-Start die belegte Reihenfolge ausprechen, nicht die schoene.
- Ein Handstart mit eigenem Zeitlimit toetet nur den Client: der
  `docker run`-Container laeuft auf dem Daemon weiter und schreibt ins echte
  Datenvolume. Nach jedem Abbruch `docker ps --filter ancestor=<image>` —
  Waisen per Container-ID stoppen, vor jeder "zwei Laeufe parallel"-Meldung
  Startzeiten lesen.

## Nachweis (in dieser Reihenfolge)

1. `docker build` bis Exit 0 (Bildgroesse nennen).
2. Import-Probe im Bild (siehe oben).
3. EINER echter End-to-End-Lauf mit dem exakten Start-argv, der spaeter im
   Manifest steht — mit Logdatei und Exit-Code. Streuung zweier Laeufe ist ein
   Befund, kein Fehler: zwei Ergebnisse (z. B. -48 und +0 Testbelohnung) als
   Zahlen in die Doku, keinen Mittelwert erfinden.
4. Rueckzug: totes Alt-venv des ersten Wirtsversuchs NICHT loeschen, sondern
   nach `Werkstatt/Ausgemustert/<anlass>-JJJJMMTT/` verschieben (Gegenprobe:
   Quelle weg, Ziel da).
5. Sicherung des Klons: vor dem Fernsichern `fetch --unshallow` (flacher Klon
   pushet nicht), Remotes drehen origin=Fork/upstream=Original — und
   `ls-remote` gegen `rev-parse` der ARBEITSASTE halten: in solchen Klonen
   liegt die Arbeit oft auf einem Zweig einer Altsitzung, waehrend der lokale
   `master` noch der reine Upstream-Stand ist (der Push "geht durch" und
   gesichert ist nichts). Master erst auf den Arbeitszweig ziehen (wenn
   Vorfahr), dann pushen, dann Fernstand gegen lokal verifizieren.

Je Repo die konkreten Zahlen (Groessen, Ergebnis, Pins) in die Wiki-Seite —
hier steht nur die Klasse.
