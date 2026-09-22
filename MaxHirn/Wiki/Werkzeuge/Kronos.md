# Kronos (Foundation-Modell fuer Kerzen)

`shiyu-coder/Kronos` — erstes offenes Foundation-Modell fuer **K-Linien
(Kerzen)**, trainiert ueber 45 Boersen, **MIT**, angenommen bei der AAAI 2026.
Klon liegt in `Werkstatt/Repos/Kronos` (kein Fork, direkt vom Original),
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

## Erster Messbefund (22.09.2026, BTC 1H, Horizont 24 h)

Zwei Hold-outs, Kontext je 400 Kerzen, gegen die **Nullinie** (Vorhersage =
letzter Kurs) gestellt:

| Fenster | Prognose | wirklich | Horizont | Richtung je Kerze | mittlerer Fehler | besser als Nullinie |
|---|---|---|---|---|---|---|
| letzte 24 h | 77.200 | 79.240 | daneben | 16/24 = 67 % | 0,831 % (Nullinie 0,731 %) | NEIN |
| 7 Tage frueher | 63.664 | 64.115 | **Treffer** | 10/24 = 42 % | 0,489 % (Nullinie 0,509 %) | JA |

**Zwei Fenster sind ein Befund, keine Messung.** Weder Sieg noch Niederlage
belegt; der naechste Schritt ist dieselbe Rechnung ueber viele Fenster
(100+ Hold-outs), sonst ist es Rauschen. Sonde:
`Agenten/Hermes/cache/scratch/kronos_probe.py`.