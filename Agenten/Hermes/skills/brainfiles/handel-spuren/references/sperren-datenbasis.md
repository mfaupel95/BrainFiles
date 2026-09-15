# Sperren: welche Datenbasis, und wie man es belegt

Gehört zu `handel-spuren`. Anlass einer Änderung: eine Bedingung soll auf einer
anderen Datenmenge rechnen (z. B. Erwartungswert ohne Betriebsstörungen).
Alles hier ist am echten Bestand erprobt, nicht abgeleitet.

## 1. Die vier Wachenfassungen

Jede Spur mit eigener Wache hält ihre eigene `lage()`; die gemeinsame Rechnung
liegt in `scanner/wachen_pruefung.py` und wird von den anderen per
`importlib`-Pfad geladen (`basis.rollierender_ev` usw.).

| Fassung | Datei |
|---|---|
| Basis + scanner | `scanner/wachen_pruefung.py` |
| xperp | `xperp/wachen_xperp.py` |
| kraken | `kraken/wachen_kraken.py` |
| orbk | `orbk/wachen_orb.py` |

`orb/wachen_orb.py` ruht und bleibt unangetastet, solange orb nicht läuft.
`nautilus/` ist ein eigenes Git-Repository — dort einzeln committen.

Der Ist-Stand je Fassung lässt sich vor jeder Änderung mit einem Griff sehen:

```bash
cd Agenten/Handel && grep -n "rollierender_ev\|ev_negativ" xperp/wachen_xperp.py \
  kraken/wachen_kraken.py orbk/wachen_orb.py scanner/wachen_pruefung.py
```

Alle vier tragen dasselbe Muster (`ev = rollierender_ev(runden)`,
`"rollierender_ev": ev, "ev_negativ": ev is not None and ev < 0`). Weicht eine ab,
ist sie beim letzten Mal vergessen worden.

## 2. Wer das Feld liest, bevor man es umbenennt

Die Sperre selbst sitzt in `handeln.py` der Spur, die Anzeige daneben:

```bash
cd Agenten/Handel && grep -rn "sperre_zu(" --include="handeln.py" . | grep -v "\.venv\|OpenAlice\|\.backup"
```

Felder umbenennen heißt: **Sperrtext, Anzeige und Tests mitziehen.** Vorher
durchsuchen:

```bash
cd Agenten/Handel && grep -rn "rollierender_ev\|ev_negativ" --include="*.py" . | grep -v "\.venv\|OpenAlice"
```

Treffer in `tests/` sind der häufigste Übersehene — ein Test, der ein Dict-Literal
als Zustand baut, bricht beim nächsten Lauf.

## 3. Testgerüst für ein synthetisches Journal

`tests/test_stoerungen.py` ist das Vorbild und lädt Wachenmodule über den Pfad
(nie über den Modulnamen — im Handel-Baum liegen mehrere `wachen_pruefung.py`):

```python
spec = importlib.util.spec_from_file_location(name, pfad)
modul = importlib.util.module_from_spec(spec); sys.modules[name] = modul
spec.loader.exec_module(modul)
```

Regeln, die den Test tragfähig machen:

- **Echte Spaltenform je Spur**, nicht eine erfundene (Kopfzeilen stehen als
  `KOEPFE` im Test). Zwei Zeilen je Runde: Einstieg und Ausstieg, gleicher
  Instrumentname, die zweite trägt den `grund`.
- **Instrumentnamen je Runde eindeutig halten** — werden zwei Aufrufe eines
  Bauers kombiniert, kollidieren sonst die Namen und die Paarung Einstieg/Ausstieg
  wird falsch.
- **Wachen als Kopie mit ausdrücklich gesetzten Werten** (`wachen_kopie`), und
  `journal_zweitziel` immer in den Temp-Ordner biegen — niemals auf das echte
  Ziel (Q:). Ein Test, der in einen echten Zielpfad schreibt, verletzt Bedingung 4
  still.
- **Zwei Betragsklassen bauen**: mehrere echte Runden mit Gewinn, dazu Störungen
  (`herzschlag_alt`) mit Verlust, so dass Gesamtrechnung und Handelsrunden
  verschiedene Vorzeichen haben.

Muster (Ausschnitt, konkret anwendbar):

```python
for i in range(5):        # echte Runden
    z.append("%s,papier,kauf,ECH-%d,1,100,,,,,," % (ZEIT, i))
    z.append("%s,papier,verkauf,ECH-%d,1,110,,,ziel,,," % (ZEIT, i))
for i in range(3):        # Zwangsschlüsse
    z.append("%s,papier,kauf,STO-%d,1,100,,,,,," % (ZEIT, i))
    z.append("%s,papier,verkauf,STO-%d,1,50,,,herzschlag_alt,,," % (ZEIT, i))
```

Dann die Zusicherungen, die die Umstellung beweisen: Rundenzahlen je Klasse,
das Sperrfeld positiv, das Diagnosefeld negativ, `ev_negativ is False`.

Unter der Messgrenze (`mindest=5`) ist das Feld `None` — der Test soll das
explizit festhalten, sonst sieht „nichts gesperrt“ später wie ein Fehler aus.

## 4. Abnahme am lebenden System

```bash
cd Agenten/Handel/xperp && ../scanner/.venv/Scripts/python.exe handeln.py --wachen
```

Für jede betroffene Spur fahren (xperp, kraken, scanner, orbk) und im Bericht die
Zeile der Bedingung zitieren — Zahl **und** Rundenzahlen („Handelsrunden 11, dazu
12 Betriebsstoerung(en)“). Erwartete Lesarten:

- positiv → keine Sperre,
- `n/a (zu wenig Runden)` → nichts gemessen, nichts gesperrt.

Zusätzlich die Wurzel-Suite: `python -m unittest discover -s tests -t tests`
aus `Agenten/Handel`. Jede `.bak`-Sicherung der Wachen vorher anlegen — die
Dateien sind Stufe 1.

## 5. Was ausdrücklich NICHT mitgefiltert wird

Drawdown, Höchststand, Ratsche und Kill-Switch bleiben auf allen Buchungen. Wer
sie filtert, schönt genau das Risiko, gegen das die Sicherung gebaut ist. Die
Doku dazu steht in `MaxHirn/Wissen/Handelsregeln.md` (Bedingung 5) und ist bei
einer Änderung mitzuziehen.
