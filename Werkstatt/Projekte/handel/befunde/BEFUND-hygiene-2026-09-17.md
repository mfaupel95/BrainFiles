# Befund: Hygiene und Struktur — 17.09.2026

**Dieser Befund ändert nichts.** Er benennt und belegt; jede Zeile mit
`Datei:Zeile` ist am 17.09.2026 nachgelesen worden. Was davon angefasst wird,
ist eine getrennte Entscheidung.

Untersucht wurde der Baum `Agenten/Handel` entlang von sechs Achsen: Leichen,
die drei Review-Dokumente im Wurzelverzeichnis, doppelte Wahrheiten, Lücken je
Spur, die Zeit-Konvention und die CI. Ausdrücklich **nicht** untersucht:
`OpenAlice/`, alle `.venv/`, `daten/`, `__pycache__/`, `kerzen_*.json` und
`README.md` (53 KB) — die Ausschlussliste aus `AGENTS.md`.

Ein Satz vorweg, weil er die Reihenfolge bestimmt: **die drei Review-Dokumente
im Wurzelverzeichnis sind in Teilen falsch** und der einzige Fund, der aktiv
Schaden anrichtet, solange er liegen bleibt — er verleitet dazu, einen
funktionierenden Notaus wieder kaputtzumachen.

---

## 1. Sofort entscheidbar

Fundstellen, bei denen Befund und Behandlung eindeutig sind. „0 Referenzen"
heißt: `grep -rn -F <name> .` über den Baum ohne die Ausschlussordner findet
außer der Datei selbst nichts.

| Fundstelle | Beleg | Befund | Empfehlung |
|---|---|---|---|
| Erledigtes Migrationsskript | `fehler-beheben-20260915.py` | 0 Referenzen; Docstring beschreibt einen am 15.09. behobenen Fehler in vier Indikatorspuren | entfernen |
| Fünf Backup-Kopien | `stoerungen.py.bak2-20260915`, `gitter/`, `kopier/`, `kopier1zu1/`, `omniquant/auswertung.py.bak2-20260915` | 0 Referenzen, alle vom 15.09., Originale existieren daneben | entfernen |
| Versteckter Backup-Ordner | `orb/.backup-okx-20260913/` (`handeln.py` 25 KB, `oanda.py`, `session.py`, `SPEC.md`, eigenes `wachen.json`, eigenes `tests/`) | vollständiger Schattenbaum einer Spur, vom 13.09. | entfernen — ein zweiter `wachen.json` neben einer aktiven Spur ist genau die doppelte Wahrheit, vor der `AGENTS.md` warnt |
| Getrackte `.bak`, auf Platte gelöscht | `verbesserer/konfig.json.bak-20260917`, Git-Status ` D` | ein `.bak` war überhaupt im Index; die Löschung steht seit heute unbestätigt im Arbeitsbaum | Löschung eintragen |
| `wachen.json` ohne Spur | `omnitrade_wachen.json` | 0 Referenzen; es gibt keine Spur `omnitrade` | entfernen |
| Logs ohne Rotation im Quellbaum | `dauerlauf.log` (398 KB), `dauerlauf.mittel.log` (121 KB), `check.log` (2 KB), `omniquant/gui-err.log` (0 Byte) | korrekt ignoriert, aber unbegrenzt wachsend | Rotation oder Ablage außerhalb des Quellbaums |

Nicht in diese Liste gehören, obwohl sie ähnlich aussehen:
`plan.json.v1` (wird von `Dockerfile:45` ins Image kopiert),
`backtest_urteile.json` (Laufzeitdatei, von `backtest_urteile.py:58` geschrieben),
die `.pid`-Dateien (aktiver Betrieb).

---

## 2. Die drei Review-Dokumente — was davon heute stimmt

`BUG_REPORT.md`, `CODE_REVIEW_SUMMARY.md` und `FIXES_APPLIED.md` sind
un-getrackt, englischsprachig, in `AGENTS.md` und `README.md` nirgends erwähnt
und verweisen nur aufeinander (`CODE_REVIEW_SUMMARY.md:158-159`). Sie behaupten
vier Fixes in `freigabefenster.py`.

| Behauptung der Dokumente | Heutiger Code |
|---|---|
| `_jetzt()` naiv statt UTC-aware | **stimmt** — `freigabefenster.py:87-90` |
| `oeffnen()` parst sicher über `_zeit()` | **stimmt** — `freigabefenster.py:226` |
| `alles_schliessen()` sammelt Keys vorab | **stimmt** — `freigabefenster.py:256-259` |
| Exact-Match `grund in ABLEHNUNGSGRUENDE` | **bewusst zurückgenommen** — siehe unten |

### Der vierte „Fix" war ein Schaden

Heute steht dort ein Wortgrenzen-Vergleich:

```python
# freigabefenster.py:192-193
if zu and any(re.search(r"\b%s\b" % re.escape(w), grund)
              for w in ABLEHNUNGSGRUENDE):
```

Der Kommentar darüber (`freigabefenster.py:188-191`) nennt den Grund: Der
Exact-Match, den die Dokumente als Verbesserung feiern, hätte die echten
Aufrufer nie getroffen. `dauerlauf.py:594` schreibt `"Telegram " + wort`,
`dauerlauf.py:683` schreibt `"Befehl /stop"` — beides ist nach `grund ==
"stop"` keine Ablehnung. Der „Fix" hätte die Ablehnungs-Wiedervorlage still
abgeschaltet. Gefunden wurde das am 17.09.2026 per Test; der heutige Stand ist
durch `tests/test_freigabefenster_zeitvergleich.py` abgesichert, das sowohl
`"Telegram stop"` als auch die Nicht-Treffer wie `"stoppage im Feed"` prüft.

### Gegenstandslos

Drei weitere „Bugs" der Dokumente entstanden daraus, dass die damalige Sitzung
die Datei nur abgeschnitten gelesen hat:

- „unvollständiges `main()`" (`BUG_REPORT.md` #3 und #10) — `main()` ist
  vollständig, `freigabefenster.py:304` bis `333`; die Datei hat 333 Zeilen.
- „fehlende Funktionen `oeffnen()`/`alles_schliessen()`" (#2, #7) — beide
  vorhanden, `freigabefenster.py:216` und `256`.
- „falsche Argumentfolge bei `anfrage_text()`" (#5) — `anfrage_stellen()` gibt
  Minuten zurück (`freigabefenster.py:213`), der Aufruf in `dauerlauf.py:461`
  ist korrekt.

**Empfehlung:** die drei Dateien entfernen und diesen Befund an ihre Stelle
setzen. Zu beachten: `tests/test_freigabefenster_zeitvergleich.py:80` verweist
im Docstring auf `FIXES_APPLIED.md` — diese Zeile muss mitgezogen werden, sonst
zeigt ein Test auf eine Datei, die es nicht mehr gibt.

---

## 3. Doppelte Wahrheiten

Maßstab ist die Faustregel aus `AGENTS.md`: *Zahlen gehören in `wachen.json`,
nicht in den Code.* Geordnet nach Schwere.

### Schwerster Fall: `xperp/auswahl.py`

Für jede dieser Konstanten existiert ein **gleichnamiger Schlüssel** in
`xperp/wachen.json`, der an der Verwendungsstelle nicht befragt wird:

| Code | wachen.json | benutzt in |
|---|---|---|
| `auswahl.py:38` `WARTUNGSMARGE = 0.005` | `wachen.json:9` `wartungsmarge` | `auswahl.py:203` (`hebel_deckel`) |
| `auswahl.py:39` `GEBUEHR_TAKER = 0.0005` | `wachen.json:23` `gebuehr_taker` | — |
| `auswahl.py:40` `GEBUEHR_MAKER = 0.0002` | `wachen.json:22` `gebuehr_maker` | `auswahl.py:381` (`zyklus = 2 * GEBUEHR_MAKER`) |
| `auswahl.py:101` `RUHE_ANTEIL = 0.25` | `wachen.json:57` `ruhe_anteil` | `auswahl.py:119` |

Die Werte stimmen heute überein — deshalb fällt es nicht auf. Wer künftig
`xperp/wachen.json` ändert, ändert nichts, und das ist die gefährliche Sorte
Fehler: lautlos.

Einen halben Schritt besser ist `auswahl.py:57` `VOLA_TOR = 1.20` — die
Konstante dient nur als Fallback (`z.get("vola_tor", VOLA_TOR)`, Zeilen 321 und
354), der Schlüssel `vola_tor_pa` steht in `wachen.json:26`.

`xperp/cvd.py:50,51,57,58,72` führt fünf weitere Schwellen (`MIN_BEWEGUNG 0.15`,
`STARK_BEWEGUNG 0.30`, `NAEHE_HOCH 0.60`, `NAEHE_TIEF 0.40`,
`MIN_CVD_ANTEIL 0.10`) ganz ohne Entsprechung in `wachen.json`.

### Weitere

- `dauerlauf.py:290` `TAKT_MAX_MINUTEN = 15` — jede `wachen.json` führt
  daneben ein eigenes `herzschlag_max_minuten`.
- `nautilus/backtest.py:47-48` (`SCHNELL = 10`, `LANGSAM = 30`) und
  `nautilus/seitwaerts_probe.py:17` (`RUHIG = 0.10`) — `nautilus/wachen.json`
  existiert und wird an diesen Stellen nicht befragt.
- Betriebspolitik im Code: `freigabefenster.py:65` `MAX_STUNDEN = 24`,
  `:70` `ANTWORT_FRIST_MINUTEN = 30`, `:78` `WIEDERVORLAGE_MINUTEN = 120`,
  `:79` `WIEDERVORLAGE_NACH_ABLEHNUNG_STUNDEN = 12`. Das sind Entscheidungen,
  keine Mathematik — sie sind ausführlich kommentiert, stehen aber im Code.
- Dreifache Gebührenkonstante: `scanner/handeln.py:92`, `verbesserer/kosten.py:7`,
  `dca_auswertung.py:45` je `0.0005`. Immerhin durch `test_kosten_gleich.py`
  aneinander gebunden — aber `scanner/wachen.json` kennt gar keinen
  Gebührenschlüssel.

### Ausdrücklich unkritisch

Damit ein späterer Durchgang sie nicht fälschlich aufgreift: `iv_waelle/iv_waelle.py:24-27`
(`K_68`, `K_90`, `K_95`, `K_99` sind z-Werte der Normalverteilung) und
`TAGE_JE_JAHR = 365.0` sind Mathematik, keine Politik. Sie gehören in den Code.

---

## 4. Spuren ohne Netz

`AGENTS.md` erwartet je Spur ein eigenes `README.md` und Tests. Die Lücken:

| Spur | fehlt |
|---|---|
| **`nautilus/`** | README **und** Tests |
| **`xperp/`** | Tests |
| `gitter/`, `iv_waelle/`, `mosaic/`, `orb/`, `orbk/`, `swap/` | README |

`xperp/` ist die Spur mit Hebel- und Margin-Logik — dieselbe Spur, die oben die
vier doppelten Wahrheiten trägt. Eine Spur, die aus einer Wartungsmarge einen
Hebeldeckel rechnet (`auswahl.py:203`), ohne Test, ist der auffälligste Punkt
dieses Abschnitts.

---

## 5. Zeit: zwei Konventionen im selben Baum

**Die Freigabe-Kette ist konsistent naiv-lokal.** `freigabefenster.py:90`,
`dauerlauf.py:294`, `befehle.py:157,206,471,510,586` — alle `dt.datetime.now()`
ohne Zone. Das ist seit dem 17.09.2026 so und richtig.

**Die Spuren arbeiten UTC-aware.** `kraken/`, `kopier/`, `kopier1zu1/`,
`mosaic/`, `macd_mtf/`, `gitter/handeln.py:124`, `iv_wand/handeln.py:196`,
`kursdaten.py:28`, `backtest_urteile.py:63`. Zwei Konventionen im selben Baum —
heute ohne Berührung, weil sie getrennte Zustandsdateien führen.

### Die eine benannte Zeitbombe

`_zeit()` (`freigabefenster.py:151-166`) **kappt** eine vorhandene Zeitzone,
statt zu konvertieren:

```python
return w.replace(tzinfo=None) if w.tzinfo is not None else w
```

Das verhindert den Absturz — und verschiebt den Wert. In
`freigabe_fenster.json` liegt noch ein Altwert aus der UTC-Zeit:
`"freigegeben_am": "2026-09-11T09:47:21.786998+00:00"`. Gekappt statt
konvertiert wird er in CEST als 09:47 Ortszeit gelesen, also zwei Stunden zu
früh.

**Heute harmlos:** `freigegeben_am` ist rein informativ, es wird nirgends
verglichen. **Träfe dasselbe `offen_bis`**, wäre ein Freigabefenster zwei
Stunden zu lang oder zu kurz — bei einem Fenster, dessen ganzer Zweck die
Begrenzung ist. Die saubere Form wäre `w.astimezone().replace(tzinfo=None)`.

### Latent

`handelszentrale.py` mischt intern: `datetime.now()` in Z. 546 gegen
`datetime.now(UTC)` in Z. 723 und 1061 (`UTC = timezone.utc`, Z. 87). Die
UTC-Werte fließen als `jetzt` in
`spur_stand()` (`handelszentrale.py:304`), das vom Fenster ausschließlich
`fenster.text()` nimmt (Z. 312) — es kommt zu keinem naiv/aware-Vergleich.
Kein Fund, aber eine Stelle, an der ein künftiger Vergleich sofort abstürzt.

`freigabe.py:86` schreibt `datetime.now().astimezone().isoformat()`, also lokal
**mit** Offset, nach `freigabe_journal.jsonl`. Drittes Format im Baum; wird nie
zurückgelesen.

---

## 6. Die CI kann nicht fehlschlagen

`.github/workflows/ci.yml` — kein Schritt kann den Lauf rot machen:

| Zeile | Inhalt |
|---|---|
| `:37` | `ruff check . --exit-zero \|\| true` |
| `:38` | `ruff format --check . --exit-zero \|\| true` |
| `:43` | `mypy . --ignore-missing-imports \|\| true` |
| `:47` | `python -m pytest tests/ … 2>/dev/null \|\| python -m unittest discover -s tests …` |
| `:48` | `continue-on-error: true` |

Zwei Befunde übereinander:

**Der pytest-Zweig scheitert jedes Mal.** `pytest` steht nicht in
`requirements.txt` (24 Pakete, keines davon pytest), und das Projekt benutzt
`unittest` (`tests/test_backtest_urteile.py:19,57,223`). Der Aufruf fällt still
über `|| ` auf `unittest discover` zurück — `2>/dev/null` verschluckt die
Fehlermeldung.

**Nur ein Fünftel der Tests läuft.** Der Baum enthält **107** `test_*.py`,
davon **21** unter `tests/`. `unittest discover -s tests` findet genau diese 21.
Die rund 86 Tests in den Spur-Ordnern — darunter `orbk/` (8), `scanner/` (6),
`orb/` (6), `verbesserer/` (17) — sind in der CI noch nie gelaufen.

Zusammen heißt das: Ein grüner Lauf sagt derzeit nichts aus.

---

## 7. Gitignore

`Handel/` hat kein eigenes `.gitignore`. Alles hängt an `BrainFiles/.gitignore`
(28 KB), das nach Deny-all mit Allowlist arbeitet: Zeile 20 ist `*`, danach
folgen Ausnahmen — `!Agenten/Handel/*.md` in Zeile 66 ist der Grund, warum
dieses Dokument getrackt wird.

Zwei Zeilen sind redundant, weil `*` sie längst erfasst:
`.gitignore:249` `Agenten/Handel/plan.json.v1` und `:250` `Agenten/Handel/check.log`.

Praktische Folge des Prinzips: **jede neue Datei ist standardmäßig unsichtbar.**
Das erklärt, warum die drei Review-Dokumente monatelang un-getrackt liegen
konnten, ohne dass ein `git status` daran erinnert hätte.

---

## Was ich empfehle, zuerst anzufassen

Vorschlag, keine Umsetzung — in dieser Reihenfolge:

1. **Die drei Review-Dokumente entfernen** (mitsamt der Referenz in
   `tests/test_freigabefenster_zeitvergleich.py:80`). Sie sind der einzige Fund,
   der aktiv in die Irre führt: Wer ihnen folgt, baut den Exact-Match wieder ein
   und legt die Ablehnungs-Wiedervorlage still.
2. **Die CI scharf machen** — `continue-on-error` und die `|| true` entfernen,
   `pytest` in `requirements.txt` aufnehmen oder den pytest-Zweig streichen, und
   die Spur-Tests einsammeln. Solange das nicht steht, ist jede weitere
   Absicherung nur behauptet.
3. **`xperp/auswahl.py` an `wachen.json` binden** — vier Konstanten, die heute
   zufällig richtig sind. Das ist der klarste Verstoß gegen die Regel aus
   `AGENTS.md`, und die Spur trägt Hebel.
4. **Die Leichen aus Abschnitt 1 entfernen** — mechanisch, risikolos, und es
   macht den nächsten Durchgang billiger.
5. **`_zeit()` konvertieren statt kappen** (`freigabefenster.py:166`). Heute
   harmlos; die Stelle ist aber die Art Fehler, die erst auffällt, wenn ein
   Freigabefenster zwei Stunden zu lang offen stand.
