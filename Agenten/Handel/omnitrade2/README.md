# omnitrade2 — Haus-Spur auf den Rust-Laeufen des Forks

**Was sie tut:** liest die Statusdateien der Rust-Laeufe in
`Werkstatt/omnitrade2/status/` und spiegelt deren **Position** in ein eigenes
Buch. Der Rust-Lauf entscheidet (das `.omni`-Skript), diese Spur fuehrt aus —
im Live-Zweig ueber den Haus-Orderweg auf Kraken.

Angelegt am 14.10.2026 (Auftrag Interpool, delegiert vom MAX-AUFTRAG).
Muster: die bestehende omnitrade-Spur (Agenten/Handel/omnitrade/).

## WICHTIG: omnitrade2 schreibt noch KEINE Statusdatei

Der Rust-Klon `Werkstatt/omnitrade2` (Phase 5 egui UI) hat aktuell nur
`backtest` und `validate` im CLI. Es gibt keinen `live`-Befehl und keinen
status-Ordner. Die Spur ist trotzdem verdrahtet:

- **Statuspfad definiert:** `Werkstatt/omnitrade2/status/live.json`
- **Umgebungsvariable:** `OMNITRADE2_STATUS_ORDNER` verschiebt den Ordner
- **Verhalten ohne Statusdatei:** Die Spur meldet `ok: False` mit dem Grund
  "keine Statusdatei (omnitrade2 live laeuft nicht)" und tut nichts. Sie
  erfindet keine Position.

Sobald der Rust-Klon einen Live-Modus bekommt und Statusdateien schreibt,
funktioniert die Spur ohne weitere Aenderungen.

## Aufruf

```
cd Agenten/Handel/omnitrade2
../scanner/.venv/Scripts/python.exe handeln.py --vorschau
```

`--vorschau` rechnet und schreibt nichts, `--papier` bucht, `--live` laeuft
ueber die Sperrenkette des gemeinsamen Kerns (`spur_buch.sperren_live`),
`--wachen` zeigt die Grenzen.

## Die Regel

| Was | Woher | Wann |
|---|---|---|
| Einstieg long | `net_quantity > 0` **und** Lauf laeuft wirklich | Statusdatei frisch **und** PID lebt |
| Ausstieg `omnitrade2 flat` | Lauf meldet keine Position mehr | `net_quantity 0` bei `running`/`stopped` |
| Notausstieg | `stop_prozent` 8 % | immer (Boersen-Stop im Live-Zweig) |

- **Gespiegelt wird der Zustand, nicht der Orderliste.** `recent_orders` ist ein
  Ringpuffer mit hoechstens 20 Eintraegen; wer daraus Ereignisse nachzaehlt,
  verliert bei einem Ausfall alles dazwischen.
- **`state: running` ist kein Beweis.** Nach einem harten Ende bleibt die Datei
  mit einer toten PID auf `running` stehen. Ein Einstieg verlangt Statusdatei
  frisch UND PID lebt (`lesen.lauf` -> `omnitrade_lauf.pid_lebt`).

## Bruecke und Laufpruefung

Die Spur teilt sich die Bruecke mit dem bestehenden omnitrade-Fork:

- `Agenten/Handel/omnitrade_bridge.py` — liest die Statusdatei (Schema 1)
- `Agenten/Handel/omnitrade_lauf.py` — prueft PID + Status (zwei Zeugen)

Beide liegen auf Handel-Ebene und werden von beiden Spuren geteilt.

## Tests

```
cd Agenten/Handel/omnitrade2
../scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Die Tests laufen ohne Netz und ohne laufenden Rust-Prozess. Sie setzen
`lesen.lebt_override` (Prozessabfrage) und `handeln.lage_override`
(Statusdateien) und schreiben nie in ein echtes Ziel.

## Spiegelung

Journal und Zustand werden nach `Q:\Handel_Journal\omnitrade2` gespiegelt
(Bedingung 4). `spiegelstand.py` vergleicht byte-genau.
