---
id: 20260830-pdf-scans-lesen
title: 'Gescannte PDFs wirklich lesen'
tags: [archiv]
created: 2026-08-20
updated: 2026-08-20
related: []
summary: 'Wie gescannte PDFs ohne Textebene per OCR auswertbar gemacht werden.'
---

# Gescannte PDFs wirklich lesen

Viele Dokumente im Archiv sind **Scans ohne Textebene**. `pypdf` liefert dort
für jede Seite einen leeren String — das sieht aus wie ein defektes PDF, ist
aber nur ein Bild.

**Warum das zählt:** Bei Beträgen, Aktenzeichen und Fristdaten ist OCR nicht gut
genug. Ein verlesenes `3` statt `8` im Fristdatum kostet mehr als die paar
Minuten, das Bild selbst anzusehen. Der Volltextindex mit OCR ist zum **Finden**
da, nicht zum **Auswerten**.

## Der Weg, der funktioniert

`pdftoppm`/poppler ist auf diesem Rechner **nicht installiert**, das Lesewerkzeug
für PDFs scheitert daran. Stattdessen die eingebetteten Scan-Bilder direkt
herausholen — bei einem Scan ist jede Seite genau ein Bild:

```python
from pypdf import PdfReader
r = PdfReader(pfad)
for i, pg in enumerate(r.pages, 1):
    for im in pg.images:
        open(f"s{i:02d}_{im.name}", "wb").write(im.data)
```

Die Bilder sind meist **TIFF** (CCITT-Gruppe 4, bitonal) und müssen nach PNG
gewandelt werden. Dabei zwei Grenzen beachten:

- **Höchstens 2000 × 2000 px**, sonst wird das Bild abgewiesen.
- Eine ganze A4-Seite auf 2000 px Höhe gestaucht ist bei Fließtext **nicht mehr
  lesbar**. Deshalb: auf 1600 px Breite skalieren und in eine **obere und eine
  untere Hälfte mit Überlappung** schneiden (0–54 % und 46–100 %). Die
  Überlappung verhindert, dass eine Zeile genau am Schnitt verschwindet.

```python
from PIL import Image
im = Image.open(tiff).convert("L")
im = im.resize((1600, int(h * 1600 / w)), Image.LANCZOS)
w, h = im.size
im.crop((0, 0, w, int(h * .54))).save("seite01_1.png")
im.crop((0, int(h * .46), w, h)).save("seite01_2.png")
```

Gemessen am ESt-Bescheid vom 17.07.2026: 8 Seiten, je 2481 × 3506 px,
45–80 KB pro Seite als TIFF. 16 Hälften, alle gut lesbar.

## Leere Seiten billig prüfen

Rückseiten und Trennblätter müssen nicht angesehen werden — das lässt sich
messen statt schauen:

```python
h = Image.open(png).histogram()
dunkel = sum(h[:128])          # 0 = garantiert leer
```

So bleibt „**alle** Seiten geprüft" belegt, ohne jede Leerseite zu betrachten.

**Stand:** 2026-08-20 · gehört zu [[Fristen]] und dem Skill `frist`
