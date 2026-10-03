---
titel: RLTrader in Docker (der Weg, der funktioniert)
aktualisiert: 2026-10-01
tags: [werkzeug, handel, docker, ml]
---

# RLTrader in Docker — Betrieb, Pines, Messergebnis

> **Falle zuerst:** RLTrader ist Code aus 2019 (TensorTrade-Vorgänger, upstream
> seitdem ruhend). Er braucht TensorFlow 1.x und Python 3.7 — **kein Host-Python
> ≥ 3.9 kann das**, und die RTX 3060 Ti (Ampere) wird von TF 1.15 nicht
> unterstützt: CPU ist der ehrliche Modus, nicht der Notbehelf. Ein alter
> Versuch mit Host-venv (Python 3.9) endet beim Import von
> `stable_baselines` in `ModuleNotFoundError: tensorflow.contrib`.

## Was wo liegt

- Klon: `Werkstatt/RLTrader` (eigener `.git`; in der Zentrale: Bereich
  WERKSTATT, STARTBAR). Fremd-Klon mit unserer Arbeit — siehe
  `Agenten/FREMD-Liste.json`. Vollhistorie seit 01.10.2026 (`fetch
  --unshallow`), `upstream` = `notadamking/RLTrader` (GPL-3.0, ruhig),
  `origin` = **privates Repo `mfaupel95/rltrader`** — unser Docker-Commit
  `25d9ff0` ist dorthin gepusht und per API nachgeprüft (`master =
  25d9ff0`, `private: true`).
- Unser Bauplatz im Klon (Commit `25d9ff0`): `requirements.local.txt`,
  `docker/Dockerfile.local`, `rltrader.cmd`, `--n-envs`-Schalter,
  `warnings`-Patches in `cli.py`/`optimize.py`, `.dockerignore` (hält `.venv`
  und Ballast aus dem Build-Kontext).
- Datengrab (Volume): `Agenten/Hermes/cache/rltrader/daten` — Modelle,
  Reports, Tensorboard, `params.db`.

## Start

```bat
cd Werkstatt\RLTrader
rltrader.cmd build
rltrader.cmd --n-envs 4 train --epochs 1 --no-report
```

**Globale Schalter vor dem Befehl** (`--n-envs 4 train ...`, nicht
`train ... --n-envs 4`) — argparse-Unterbefehle erben die Top-Level-Argumente
hier nicht. Ohne `--n-envs` greift `os.cpu_count()`: auf diesem Rechner **28
TensorFlow-Prozesse** je Lauf — Commit-Erschöpfung ist Hausakte (30.09.).

## Die Pines und warum (jede gemessen, nicht geraten)

| Pin | Grund |
|---|---|
| `python:3.7.17-slim-bullseye` | letzte 3.7; apt-Quellen seit LTS-Ende nur auf `archive.debian.org` (`bullseye main`); ein `bullseye-security` gibt es dort nicht |
| `tensorflow==1.15.0` | `stable_baselines` 2.10 importiert `tensorflow.contrib` (nur 1.x) |
| `gym==0.17.3` | 0.21.0 zerlegt sein eigenes Rad: die Extras-Zeile `opencv-python>=3.` ist ungültig, `wheel`-Metadatenbau bricht |
| `optuna==0.19` | gebündeltes `data/params.db` trägt das 0.x-Schema (alembic `v0.9.0.a`, `version_info` 0.10.0), und der Code ruft die 0.x-API (`trial.should_prune(step)`, `optuna.structs`) |
| `yfinance==0.1.87`, `multitasking==0.0.9` | quantstats importiert yfinance → multitasking; jüngere multitasking brauchen `typing.TypedDict` (erst Python ≥ 3.8) |
| `opencv-python-headless` | `stable_baselines.common` importiert `cv2` schon beim Paket-Import |
| `mpi4py==3.1.4` | `trpo_mpi` beim Paket-Import;apt `libopenmpi-dev` + gcc |
| `SQLAlchemy==1.3.24` | optuna 0.19 + neuer SQLAlchemy = Konflikt |

Der Code wird **ins Bild gepackt**: Docker Desktop darf `O:\Werkstatt` nicht
mounten (Filesharing nennt nur `BrainFiles`, `GitHub`, `O:\Modelle`) — Bind
von `O:` oder gar `%USERPROFILE%`-Ortshälften hängt den Container in `Created`
fest. Build-Kontext über die CLI funktioniert von `O:` trotzdem. Schreibende
Daten hängen als Volume über `/code/data`; der Wrapper legt `input/`,
`agents/`, `reports/`, `tensorboard/` an — ohne `agents/` scheitert der
Modell-Speichern mit `FileNotFoundError` (passiert im ersten Lauf).

## Messergebnis (10.01.2026, CPU, 4 Env, 1 Epoche)

- 14066 Trainings-Schritte auf `data/input/coinbase-1h-btc-usd.csv`
  (2019-Bestand), Hyper-Parameter aus dem mitgebrachten Optuna-Bestand
  (29 vollständige Suchläufe, Study `PPO2__MlpLnLstmPolicy__IncrementalProfit`).
- Test auf den gehaltenen 20 %: **−48,32 USD** im ersten Durchlauf, **+$0,30**
  im Beleg-Lauf derselben Kommandozeile — die Streuung zwischen zwei Läufen ist
  größer als jedes Signal. Das Bild deckt sich mit dem Hausbefund zu den
  Indikatorsperren: gegen die Nulllinie gewinnt hier nichts, und mehr als
  Referenz ist dem RL-Zweig nicht zu geben.
- Belege: `Agenten/Hermes/cache/rltrader-train1.log` (Sparfehler, oben
  beschrieben), `-train2.log` (durchlaufend), Modell
  `rltrader/daten/agents/PPO2__MlpLnLstmPolicy__IncrementalProfit__0.pkl`.

## Optimize- und Report-Pfad (01.10.2026, beide jetzt gefahren — T-272)

Bis dahin war nur `train`/`test` belegt; die Suchschleife und der Report waren
„passend gepinnt, aber nie gefahren“. Jetzt sind beide gemessen.

**optimize** (21:35:35 → 21:57:16, 21 min 40 s CPU, 4 Env, 1 Prozess):

```bash
docker run --name rltrader-optimize1 --memory 6g --cpus 4 -e OMP_NUM_THREADS=4 \
  -v "<daten>:/code/data" rltrader-cpu \
  python /code/cli.py --n-envs 4 --parallel-jobs 1 optimize \
    --trials 1 --prune-evals 1 --eval-tests 1
```

- Die 0.19-API trägt: `trial.should_prune(step)` und `optuna.structs` laufen
  ohne Bruch, das Altschema der `params.db` wird gelesen (`Using an existing
  study …`), Trial 553 wurde angelegt.
- **Ergebnis: PRUNED**, Wert `1.971` — der Lauf hat trainiert
  (`n_steps_per_eval` ≈ 11 253 Schritte), validiert und dann über
  `should_prune(0)` verworfen. Bestes Trial bleibt `-57.91` aus dem
  mitgebrachten Bestand. `n_prune_evals_per_trial=1` heißt: genau EINE
  Auswertung, danach fällt die Entscheidung.
- Beleg: `Agenten/Hermes/cache/rltrader-optimize1.log`. Der Prozess endet mit
  `EXIT=125` — das ist **nicht** der Lauf, sondern die Docker-Engine, die
  unmittelbar danach wegbrach (siehe unten).

**report** (`test --save-report`):

```bash
docker run --name rltrader-report2 ... rltrader-cpu \
  python /code/cli.py --n-envs 4 test --model-epoch 0 --no-render --no-report --save-report
```

- **Falle, gemessen:** der Code von 2019 ruft
  `qs.reports.html(returns.Balance, file=reports_path)`; quantstats **0.0.40**
  kennt nur `output=`. Erster Lauf endete mit
  `TypeError: html() got an unexpected keyword argument 'file'` (Beleg:
  `rltrader-report1.log`). Behoben in `lib/RLTrader.py` (Commit `17ffa38` im
  Klon, `output=` + Titel).
- **Der Code liegt IM Bild** — eine Änderung im Klon wirkt erst nach
  `rltrader.cmd build` (bzw. `docker build -t rltrader-cpu -f
  docker/Dockerfile.local .`). Der zweite Report-Lauf gegen das alte Bild
  scheiterte mit demselben TypeError.
- Ergebnis: `daten/reports/PPO2__MlpLnLstmPolicy__IncrementalProfit__0.html`,
  917 KB, Titel = prüfbares Schluesselwort
  (`RLTrader PPO2__MlpLnLstmPolicy__IncrementalProfit Epoche 0`).
  Testzeile: `Finished testing model … : $7886.06` (Summe der Schritt-Belohnungen
  über den Testlauf, **nicht** der Kontostand — die frühere Zahl −48,32 USD war
  die Bilanz des gehaltenen Fünftels).
- `--no-render` ist im Container Pflicht (`test_env.render(mode='human')`
  braucht ein Fenster), `--no-report` überspringt `qs.plots.snapshot`
  (matplotlib ohne Anzeige).

## Docker-Engine: der Hausgriff reicht nicht immer (01.10.2026)

Die `docker-wache` heilt mit `wsl --shutdown` + Docker Desktop starten. Das
half hier **nicht**: die WSL-Distribution `docker-desktop` stand auf `Stopped`,
Docker Desktop lief aber seit 23 Stunden — ein zweiter Start holt nur das
Fenster nach vorn, die Engine startet ihre VM nicht neu. Wirkung: `docker info`
läuft in jeden Zeitablauf, alle Container sind mit der VM tot, und die Wache
meldet trotzdem nichts (ihr `_prozesse_json()` läuft unter Commit-Druck leer
und steigt still aus).

Was half (23:32): die Docker-Desktop-Prozesse **beenden** (`Stop-Process -Force`
über `Docker Desktop`, `com.docker.backend`, `com.docker.build`) und die App
frisch starten — Engine nach 23 s zurück, alle Container mit
`--restart`-Policy von selbst wieder da (freqtrade-Bots, openterminalui,
nautilus-demo). Werkzeug dieser Sitzung:
`Agenten/Hermes/cache/scratch/docker_neustart.py`.

## Kein Live-Pfad

Der Klon *könnte* live (lib/env/trade/LiveTradeStrategy.py, ccxt-Provider) —
bei uns läuft er ausschließlich statisch/papier; Börsenschlüssel sind dem
Container nie gegeben. Freigabekette und Handelsregeln bleiben, wie sie sind.
