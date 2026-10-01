# Legacy-Python-Repos in Docker (wenn die Epoche nicht mehr auf den Host passt)

Klassenerkennung: Repos aus der TensorFlow-1.x-/gym-Aera (stable_baselines,
RLTrader, aehnliche) brauchen Python <= 3.7 - der Host hat 3.9+, kein conda.
Auch die GPU ist kein Grund zur Freude: neuere Architekturen (Ampere und
jienger) werden vom CUDA des alten Frameworks nicht unterstuetzt. CPU ist dann
der EHRliche Modus, nicht der Notbehelf - so in den Bericht.

## Was Docker Desktop mounten darf - vorher lesen, nicht probieren

Die Freigabeliste steht in `%APPDATA%\Docker\settings-store.json`, Schluessel
`FilesharingDirectories`. Alles ausserhalb faellt still oder laut: ein
`O:\...`-Bind wird zurueckgewiesen ("not shared from the host"), und weil
`BrainFiles\Werkstatt` eine JUNCTION auf `O:\Werkstatt` ist, loest Docker den
C:-Notations-Pfad auf dieselbe Zielplatte auf und weist ihn ebenfalls ab. Ein
Mount aus einem nicht freigegebenen Ort kann den Container zudem ohne
Fehlermeldung in `Created` haengen lassen - das ist kein Defekt, das ist die
Freigabegrenze. Regeln:
- Code INS Bild (`COPY . /code`): der Build-Kontext laeuft ueber die CLI und
darf von jedem Host-Pfad kommen - nur Mounts sind begrenzt. `.dockerignore`
um `.venv`, `.git`, `__pycache__`, Modell-/Radateien ergaenzen, sonst wandert
  der ganze Ballast ins Bild.
- Schreibende Daten: Volume nur aus dem freigegebenen Gebiet - im Haus
  `Agenten/Hermes/cache/<name>/daten` (echtes C:). Der Wrapper saat den
  Eingangsbestand dahin (input, params) und legt ALLE schreibenden
  Unterordner (agents/reports/tensorboard/log) VOR dem ersten Lauf an - ein
  fehlender Zielordner wirft `FileNotFoundError` erst NACH der ganzen
  Rechenzeit (Training 15 min gelaufen, Save fehlte, Ergebnis weg).
- Freigaben aendern (Settings + Docker-Neustart) trifft laufende Container
  (Handel, Bots) - nicht heimlich tun, nur auf ausdrueckischen Auftrag.

## apt auf EOL-Distros

Quellen archivierter Distros (jessie; bullseye nach LTS-Ende) liegen auf
`archive.debian.org`; die `deb.debian.org`-Pools geben 404. Umstellen mit
`echo 'deb http://archive.debian.org/debian <codename> main' > /etc/apt/sources.list`
- und NUR `main`: die `-security`-Suite existiert auf archive meist NICHT
(404 auf die Release-Datei, apt exit 100). build-essential und MPI lassen sich
aus main vollstaendig loesen.

## Era-Pines - jede mit Mechanismus, nie aus dem Kopf

| Baustein | Pin | Warum |
|---|---|---|
| TensorFlow | 1.15.0 | stable_baselines 2.10 importiert `tensorflow.contrib` (nur 1.x); die letzte 1.x mit cp37-Rad |
| gym | 0.17.3 | 0.21.0 zerstoert seinen eigenen sdist-Bau: eine Extras-Zeile `opencv-python>=3.` ist keine gueltige Spec, das `wheel`-Metadaten-Brichen bricht |
| optuna | nach SCHEMA des mitgebrachten params.db + API im Code | 0.x-DB (alembic `v0.9.0.a`) plus Aufrufe wie `trial.should_prune(step)`/`optuna.structs` = 0.19; neuere lesen den Altspeicher nicht oder verfehlen die Signatur |
| numpy | < 1.20 | TF 1.15 ABI/Namens-Epoche |
| yfinance + multitasking | rueckwaertz pinnen | transitiver Import von `typing.TypedDict` (erst Python >= 3.8) - die Kette sitzt oft hinter quantstats |
| cv2 | opencv-python-headless | `stable_baselines.common` importiert cv2 schon beim Paket-Import; headless ohne GUI-Bibliotheken |
| mpi4py | manylinux-Rad, sonst apt `libopenmpi-dev` + gcc | `trpo_mpi` laeuft beim stable_baselines-Paket-Import mit |

Kleine Zugaben (ein Einzelpaket) als EIGENE RUN-Schicht hinter der grossen:
requirements byte-gleich lassen = die schwere Schicht bleibt im Build-Cache.
Dockerfile OHNE Fortsetzungsbackslashes schreiben (eine Anweisung pro Zeile,
`echo` statt `printf` mit `\n`) - der Inhalt von Werkzeugaufrufen verliert eine
Escape-Ebene. Batch-Wrapper (`.cmd`) in Python aus `chr(92)`-Teilen bauen und
mit CRLF schreiben; Gegenprobe ist `cat -A` (Backslash einfach sichtbar, `^M$`
an jeder Zeile), vor dem ersten Ausfuehren.

## Lauf und Nachweis

- Foreground-Aufrufe werden bei ~420 s gekappt - Build und Training hoeren
  NICHT auf, wenn der Aufrufer kappt. Beides detached fahren
  (`Start-Process cmd /c ... > log 2>&1`), Log pollen. Ein gekillter
  docker-Client hinterlasst ein LEBENDES Gefaess: vor jedem neuen Lauf
  `docker ps --filter ancestor=<image>` pruefen und Waisen stoppen - zwei
  Gefaisse auf demselben Daten-Volume schreiben sich gegenseitig die Modelle
  ueber den Kopf.
- Globale argparse-Optionen VOR den Unterbefehl (`cli.py --n-envs 4 train
  --epochs 1`): subparsers erben Top-Level-Argumente nicht - die Reihenfolge
  ist die einzige still quittierende Falle am ersten Start.
- Prozessbremsen je Lauf setzen (`--memory 6g --cpus 4`, `OMP_NUM_THREADS`):
  die Vorgabe `os.cpu_count()` traeneriert sonst so viele Modell-Prozesse,
  wie der Rechner Threads hat - Commit-Erschoepfung ist Hausakte.
- Nachweis = Exit 0 IM Log UND Ergebnisdatei mit Groesse auf der Platte. Fuer
  die Zentrale-Zeile: `start`/`bauen` als argv auf den Wrapper, und
  `beleg_frist_s` oberhalb der 90-Sekunden-Belegfrist des `--belege`-Laufs
  (sonst killt das Belegwerkzeug genau den Lauf, der den Beleg liefern soll).
- Orderfaehige Repos (Live-Strategie oder ccxt-Zweig im Code) bleiben bei dem,
  was belegt wurde: statische Daten, Simulation, keine Schluessel im
  Container. Der Live-Zweig ist dann nicht verbaut, sondern nie verbunden -
  genau so in die FREMD-Regel und den Bericht.
