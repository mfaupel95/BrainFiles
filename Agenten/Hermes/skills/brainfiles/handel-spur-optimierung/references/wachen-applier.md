# wachen.json aendern, ohne dass fremde Arbeit mitgeht

Eine Wachen-Datei ist formatiert, traegt Erklaertexte und wird von parallelen
Sitzungen angefasst. Der Applier unten umgeht die drei Fallen; er gehoert zu
Schritt 9 des Skills (Aendern / Stufe 1) und ist zugleich der Weg fuer jede
JSON-Aenderung im Haus.

## Warum nicht `json.dumps` schreiben

`json.loads` + `json.dumps(..., indent=2)` normalisiert Einrueckung,
Schluesselreihenfolge und Escaping. Drei geaenderte Felder werden so zu einem
Diff ueber hunderte Zeilen, und im Streitfall nicht mehr unterscheidbar von der
Arbeit einer anderen Sitzung. **Die Datei bleibt TEXT mit gezieltem Feldersatz;
`json.loads` ist die PRUEFUNG, nicht der Schreibweg.**

## Der Applier

```python
import json

p = r"C:\...\wachen.json"
with open(p, "rb") as fh:
    b = fh.read()
nl = "\r\n" if b.count(b"\r\n") else "\n"
t = b.decode("utf-8")

# 1. Feldersatz als Text, mit vollstaendigem Zeilenanker
alt = '"handel_erlaubt": true,'
assert t.count(alt) == 1, t.count(alt)
t = t.replace(alt, '"handel_erlaubt": false,', 1)

# 2. Erklaertext MITZIEHEN (siehe "Jeden abgeleiteten Wert mitziehen")
alt_v = '"_handel_erlaubt_vermerk": "true auf Auftrag Max ..."'
assert t.count(alt_v) == 1
t = t.replace(alt_v, '"_handel_erlaubt_vermerk": "false auf Auftrag Max <datum>. Grund ist eine Messung: ..."', 1)

# 3. PRUEFEN vor dem Schreiben: Reihenfolge UND Werte, nicht nur Syntax
d = json.loads(t)
assert d["handel_erlaubt"] is False            # bool, nicht truthy
assert d["freigabe"]["erfuellt"] is False      # zweiter Schalter im selben Block

neu = t.encode("utf-8")
assert neu != b
with open(p, "wb") as fh:
    fh.write(neu)
```

Danach: `git diff --numstat <pfad>` (drei Felder ergaben belegt `3 3`), die
geschriebene Datei noch einmal `json.loads`, und der echte Lauf
(`<spur>/handeln.py --vorschau`), der die Sperrzeile im Klartext nennt.

## Die drei Fallen

1. **Der gleiche Schalter an zwei Stellen.** Ein Schalter steht als Wert UND im
   Erklaertext unter `_<feld>_vermerk`; ein zweiter kann im selben Block liegen
   (`freigabe.erfuellt` neben `handel_erlaubt`). Ein globaler Ersetzen trifft
   beide und damit auch fremde Stellen - **jeder Feldersatz mit seinem EIGENEN
   Zeilenanker und `count == 1`**, nie einen Schalter ueber die ganze Datei.
2. **Das Komma gehoert an die Vorzeile.** Faellt es beim Ersetzen eines kompletten
   Schluessel-Wert-Paares weg, ist die Datei kein gueltiges JSON mehr - und
   scheitert danach das Schreiben, steht die kaputte Datei da. Deshalb
   `json.loads(t)` unmittelbar VOR dem Schreiben.
3. **Ein Ganzdatei-Diff heisst immer Zeilenenden oder Einrueckung**, nicht "viele
   Felder geaendert". Drei Felder + Vermerk ergaben `3 3` und `2 2`.

## Die Datei vor dem Anfassen sichern und den Zustand pruefen

`.bak-JJJJMMTT` anlegen, und die Zeilenenden VOR dem ersten Ersetzen messen: ist
die Datei gemischt, traegt der neue Block das dominante Ende und alle
bestehenden Zeilen bleiben unangetastet. Ein Skript, das bei Mischung abbricht,
verhindert genau den haeufigsten Fall (eine parallele Sitzung hat LF hinter
lassen). Der Beweis ist `git diff --numstat` mit reinen Insertions, nicht die
Vorpruefung.
