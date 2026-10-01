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

- Klon: `Werkstatt/RLTrader` (upstream `notadamking/RLTrader`, GPL-3.0,
  seicht geklont, eigener `.git`; in der Zentrale: Bereich WERKSTATT,
  STARTBAR). Fremd-Klon mit unserer Arbeit — siehe `Agenten/FREMD-Liste.json`.
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

## Kein Live-Pfad

Der Klon *könnte* live (lib/env/trade/LiveTradeStrategy.py, ccxt-Provider) —
bei uns läuft er ausschließlich statisch/papier; Börsenschlüssel sind dem
Container nie gegeben. Freigabekette und Handelsregeln bleiben, wie sie sind.
