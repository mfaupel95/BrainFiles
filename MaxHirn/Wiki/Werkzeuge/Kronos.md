# Kronos (Foundation-Modell fuer Kerzen)

`shiyu-coder/Kronos` — erstes offenes Foundation-Modell fuer **K-Linien
(Kerzen)**, trainiert ueber 45 Boersen, **MIT**, angenommen bei der AAAI 2026.
Klon liegt in `Werkstatt/Kronos` (kein Fork, direkt vom Original),
eigenes `.venv`.

Groessen und Gewichte (HuggingFace `NeoQuasar`): Mini 4,1 M · Small 24,7 M ·
Base 102,3 M · Large 499,2 M Parameter, Kontext 512–2048. `Kronos-small` laeuft
auf CPU in Sekunden, auf der 3060 Ti ohnehin.

## Aufruf

```python
from model import Kronos, KronosTokenizer, KronosPredictor
tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
model = Kronos.from_pretrained("NeoQuasar/Kronos-small"); model.eval()
p = KronosPredictor(model, tok, max_context=512)          # device="cpu" moeglich
out = p.predict(df=df[["open","high","low","close"]],
                x_timestamp=x_ts, y_timestamp=y_ts, pred_len=24,
                T=1.0, top_p=0.9, sample_count=1, verbose=False)
```

`df` braucht `open/high/low/close`; `volume`/`amount` sind optional (werden mit
0 gefuellt). Volumen braucht es nicht — die vorhandene Kerzendatei
`Agenten/Handel/kerzen_BTC-USDT_1H_8760.json` (Format
`[ts_ms, open, high, low, close]`) reicht.

## FALLE: requirements.txt pinnt pandas==2.2.2 — die stuerzt ab

Erste Laeufe endeten mit **Segmentation Fault / Access Violation**
(`0xC0000005`), auch auf dem Host, auch mit einem Thread, auch mit torch 2.7.1
statt 2.14. `python -X faulthandler` zeigte die Stelle:

```
Windows fatal exception: access violation
  File ".../pandas/core/arrays/datetimes.py", line 439 in _generate_range
  File ".../pandas/core/indexes/datetimes.py", line 1008 in date_range
```

**`pd.date_range` selbst reisst den Prozess ab** — pandas 2.2.2 auf Python 3.13
/ Windows. Es war nie torch und nie Kronos. Fix: `pip install -U pandas numpy`
(auf 3.0.6 / 2.5.3) — danach laeuft alles.

Merksatz: Bei einem harten Absturz zuerst `-X faulthandler` laufen lassen. Die
Vermutung „das Modell ist zu neu fuer die Bibliothek" kostete hier zwei
Torch-Neuinstallationen, der Zeuge zeigte in eine ganz andere Ecke.

## Messbefund (22.09.2026, BTC 1H, Horizont 24 h, Kontext 400 Kerzen)

Zuerst zwei Hold-outs, gegen die **Nullinie** (Vorhersage = letzter Kurs)
gestellt — 1 Treffer, 1 besser. Dann die belastbare Rechnung ueber
**100 nicht ueberlappende Fenster** mit `Kronos-small`, einer Probe je Fenster
(`sample_count=1`), Sonde `_kronos_fenster.py`:

| Groesse | Wert |
|---|---|
| Horizont-Richtung richtig | **47/100 = 47,0 %** (Muenzwurf) |
| besser als die Nullinie | **20/100 = 20,0 %** |
| Richtung je Kerze | 1176/2400 = 49,0 % |
| mittlerer Fehler | **2,059 %** gegen Nullinie **0,875 %** |

**Ergebnis: Kronos-small schlaegt in dieser Form die Nullinie nicht — im
Gegenteil, es liegt 1,18 Prozentpunkte darueber.** Als Handelssignal ist das
wertlos.

Was das NICHT heisst: geprueft ist **ein** Modell (Small, 24,7 M), **eine** Reihe
(BTC 1H), **ohne** Nachtrainieren. Der faire Gegentest — Mittelung ueber
mehrere Proben, weil ein generatives Modell mit `sample_count=1` die
pessimistischste Einstellung ist — wurde gefahren (`_kronos_fenster2.py`,
30 Fenster, 5 Proben):

| Groesse | 1 Probe (100 Fenster) | 5 Proben (30 Fenster) |
|---|---|---|
| Horizont-Richtung richtig | 47,0 % | **50,0 %** |
| besser als die Nullinie | 20,0 % | **30,0 %** |
| mittlerer Fehler | 2,059 % | 1,767 % |
| Nullinie | 0,875 % | 0,663 % |
| Abstand zur Nullinie | +1,184 pp | **+1,104 pp** |

**Die Mittelung verbessert den Fehler (2,06 % → 1,77 %) und aendert das Urteil
nicht.** Beide Einstellungen bleiben rund **2,7-fach ueber** der Nullinie, die
Richtung bleibt ein Muenzwurf. Damit ist der Fall geschlossen: Kronos-small ist
**kein** fertiger Prognostiker fuer BTC 1H auf 24 h. Ein ernsthafter Versuch
braeuchte Nachtrainieren (die Skripte liegen im Repo) — das ist ein Projekt,
keine Zehn-Minuten-Messung, und der Nutzen stuende erst nach einer ebenso
strengen Gegenprobe fest.

Sonden: `Agenten/Hermes/cache/scratch/kronos_fenster.py` (100 Fenster),
`kronos_fenster2.py` (Proben-Mittelung, Modellgroesse per Argument waehlbar).