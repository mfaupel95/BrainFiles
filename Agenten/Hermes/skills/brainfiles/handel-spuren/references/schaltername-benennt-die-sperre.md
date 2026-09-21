# Ein Schaltername beschreibt die SPERRE, nicht den Tag

## Der Anlass

Max las in `xperp/handeln.py`:

```python
we = s["wochenende"]
...
if we and kandidat["kategorie"] in ("aktie", "rohstoff"):
    continue
```

und fragte: *"Muesste die nicht wennnichtwochenende heissen?"*

Berechtigt - und die Antwort ist lehrreich: **die Logik war richtig, der Name
war falsch.**

## Warum der Name falsch war

`wochenende_sperrt()` liefert `True`, wenn **gesperrt** ist. Die Sperre beginnt
aber **Freitag 19:00 UTC** (`freitag_stopp_utc`) - da ist noch kein Wochenende.

`we` liest sich als Tatsachenbehauptung ("es ist Wochenende"), und diese
Behauptung ist am Freitagabend schlicht unwahr. Der Leser stolpert zu Recht.
Gemeint ist ein Zustand: **gesperrt**.

```python
wochenende_gesperrt = s["wochenende"]
if wochenende_gesperrt and kandidat["kategorie"] in ("aktie", "rohstoff"):
    continue
```

## Die Regel

**Ein boolescher Name benennt den ZUSTAND, den er schaltet - nicht den Anlass,
aus dem der Zustand entstand.**

| schlecht | gut | warum |
|---|---|---|
| `we` / `wochenende` | `wochenende_gesperrt` | die Sperre beginnt vor dem Wochenende |
| `nacht` | `ausserhalb_handelszeit` | "Nacht" ist je nach Boerse etwas anderes |
| `fehler` | `abbruch_noetig` | nicht jeder Fehler bricht ab |
| `wenn_nicht_wochenende` | — | doppelte Verneinung im Namen, dann ist `if not x` unlesbar |

Die Form `wenn_nicht_X` gehoert **nie** in einen Namen: sie verlagert die
Verneinung aus dem `if` in den Bezeichner, und die naechste Verneinung
(`if not wenn_nicht_wochenende`) ist nicht mehr lesbar.

## Vorgehen bei so einer Frage

Nicht sofort umbenennen und nicht sofort verteidigen - **erst nachrechnen**:

1. Was liefert die Funktion in den Grenzfaellen? (Fr 18:59, Fr 19:00, Sa, Mo)
2. Wie liest sich die Bedingung damit?
3. Erst dann entscheiden: Logikfehler oder Namensfehler.

Hier: Fr 18:59 offen, Fr 19:00 gesperrt, Sa/So gesperrt, Mo offen - Logik ok.

## Und dann der fehlende Test

Die Frage deckte auf, dass die Sperre **gar keinen Test hatte**. Eine Namens-
korrektur ohne Test waere Kosmetik. Dazu gehoeren beide Haelften:

- **die Zeiten** (Freitag-Grenze, Wochenende, Montag, fehlende und kaputte
  Stoppzeit - eine kaputte Zeitangabe darf nicht dauerhaft stilllegen)
- **die Bedingung im Einstiegspfad**: gesperrt + Aktie/Rohstoff = kein Anlauf,
  **Krypto laeuft durch**. Stuende dort kein Kategorie-Filter, waere die ganze
  Spur am Wochenende blind - obwohl Kryptomaerkte durchgehend handeln.

Siehe `xperp/tests/test_wochenendsperre.py` (9 Tests).
