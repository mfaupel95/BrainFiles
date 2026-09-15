# VRAM-Faustregeln

Gemessen auf Max' Rechner: RTX 3060 Ti, **8,0 GiB** (nvidia-smi; WMI meldet
fälschlich 4 GB). 4K-Desktop. Reserve = Windows-Desktop + GPU-Kontext +
Rechenpuffer.

## Formeln

```
Gewichte GiB = (Parameter_2D * Bits + Parameter_1D * 16) / 8 / 2^30
KV GiB       = Bloecke * KV_Koepfe * (key_len + value_len) * Kontext * Bytes / 2^30
```

1-D-Tensoren (Normen, Biases) bleiben F16 — deshalb nie `Parameter * Bits / 8`
allein rechnen. Bytes je KV-Element: F16 2,0 · Q8_0 1,0625 · Q4_0 0,5625.

## Bitwerte je Stufe (nicht die runde Zahl)

BF16 16,0 · Q8_0 8,5 · Q6_K 6,5625 · Q5_K_M 5,65 · Q4_K_M 4,85 ·
Q3_K_M 3,95 · IQ3_XXS 3,0625 · Q2_K 2,75

## Was wirklich im VRAM landet

Grundlast (sauberer Desktop, 4K, viele GPU-beschleunigte Programme):
**2,5–3,4 GiB**. Rechenpuffer + CUDA-Kontext: gemessen **~0,83 GiB** bei einem
4-Mrd-Modell. Bei 8.192 Token bleiben damit rund **5,9 GiB für Gewichte + KV**.

Grenzwerte in Modellgröße bei diesem Budget:

| Stufe | bis |
|---|---|
| BF16 | 3,2 Mrd |
| Q8_0 | 6,0 Mrd |
| Q6_K | 7,7 Mrd |
| Q5_K_M | 9,0 Mrd |
| Q4_K_M | 10,4 Mrd |
| Q3_K_M | 12,8 Mrd |
| IQ3_XXS | 16,5 Mrd |
| Q2_K | 18,4 Mrd |

**„12–14B passen knapp“ ist falsch.** 14 Mrd sind bei Q4_K_M 7,9 GiB und
passen nicht; nur 3 Bit geht (Q3_K_M 6,4 / IQ3_XXS 5,0 GiB).

## Gemessene Fälle

**gemma-4-E4B** — 7,518 Mrd (kein 4-Mrd-Modell!), 42 Blöcke, 2 KV-Köpfe,
Kopf 512/512, Trainings-Kontext 131072. KV: 0,1641 MiB je Token — bei vollem
Kontext allein 21 GiB, also unerreichbar.

| Datei | VRAM gemessen | Kontext | Verteilung | Tempo |
|---|---|---|---|---|
| Q8_0, 8,03 GB | **5,02 GiB** | 8192 | 100 % GPU | 43 Token/s |
| BF16, 15,05 GB | — (rechnerisch zu groß) | — | — | — |

Die Q8_0-Datei ist größer als der gemessene Verbrauch: es landen nur ~5,1 GiB
im VRAM. Die Datenmenge bleibt real, die Verteilung ist offen (Treiber/mmap) —
als offenen Punkt berichten, nicht als Befund.

**qwen3.5-4B** — 4,326 Mrd, 33 Blöcke, 4 KV-Köpfe, Kopf 256/256,
Trainings-Kontext 262144 (2,79 GiB Gewichte):

| Kontext | VRAM gemessen | Verteilung | Tempo |
|---|---|---|---|
| 262144 (Vorgabe) | 5,63 GiB | 42 %/58 % CPU/GPU | 18,4 Token/s |
| 8192 | **3,19 GiB** | 100 % GPU | **76,2 Token/s** |

Der Kontext allein ist der Unterschied: 2,4 GiB weniger und 4× schneller.

## Was gemessen wenig bringt

- **KV-Cache auf Q8_0 statt F16:** bei 8.192 Token und diesem Kopf gemessen
  nur **93 MiB** (gerechnet waren 483 MiB) — kein Hebel bei kurzem Kontext.
- **Aktivierungsquantisierung (A4/A6):** greift nur den Rechenpuffer, also
  Größenordnung einige hundert MB. Für „passt es“ zählen Gewichtsstufe und KV.
- Eine Gewichtsstufe tiefer spart dagegen 0,7–1,7 GiB (7,5-Mrd-Modell).
