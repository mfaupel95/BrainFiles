# Pruefbericht: Routing-Plan (Eingang der Kette t_37ac8a78 -> t_cb2465ea)

Karte: `t_5cdfc16c` "Read and validate parent routing plan input"
Geprueft am 2026-10-04 · Pruefer: `MaxHirn/Archiv/routing_plan_pruefen.py`

## Ergebnis in einem Satz

Der Plan **existiert, ist nicht leer und hat in allen 119 Zeilen alle
geforderten Felder** - aber er deckt **nicht alle offenen Punkte** ab: 47
fehlen, und seine eigene Mengenangabe im Kopf ist falsch.

## Eingang

| | |
|---|---|
| Plan | `Agenten/Hermes/cache/scratch/ROUTING_PLAN_probe.md` (nur Laufzeitstand, nicht im Repo) |
| Quelle | `MaxHirn/Archiv/TASKS.md`, Abschnitt `## Offen` |
| Werkzeug | `routing_plan_bauen.py` (nennt sich im Plankopf selbst) |

**Leerzustand: NEIN.** Es gibt offene Punkte, die nachgehen muessen - das
Signal "nothing to execute" greift nicht.

## Feldpruefung (die eigentliche Aufgabe dieser Karte)

Erwartet: `items`, `criteria`, `order`, `flags` - im Haus als Tabellenspalten
`Titel | Quelle | Definition of Done | Blocker | Aufwand | Profil |
Begruendung` plus Wellenlisten.

| Feld | Ergebnis |
|---|---|
| Tabelle (Inventar) | 119 Zeilen, 119 eindeutige T-IDs, **keine Doppelnennung** |
| Spaltenzahl | 8 im Kopf, **0 Zeilen mit abweichender Zahl** |
| Leere Felder | **keine** - jede Zeile traegt Titel, Quelle, Definition of Done, Blocker, Aufwand, Profil, Begruendung |
| Wellenlisten | 119 IDs verteilt auf Welle 1/2/3/5/6, **jede genau einmal** |
| Zuordnung Profil | 6 Profile belegt (markt-recherche 68, hermes-wartung 19, default 15, basic-memory 9, lotse 5, nerd 2, agent-trade-kit 1) |

## Zwei Befunde

### 1. Der Plan verliert 47 offene Punkte (hart)

TASKS.md fuehrt 167 nicht abgearbeitete Eintraege, der Plan 119.

**46 der 47 fehlenden Punkte sind mit einem ASCII-Bindestrich geschrieben
(`**T-335 - Titel**`) statt mit dem Geviertstrich des Hausformats
(`**T-335 — Titel**`).** Ein Leser, der nur die Hausform kennt, uebersieht sie
- genau das ist bei `doppelte_nummern.py` (T-332) schon einmal passiert, dort
mit 26 Eintraegen und dem Meldeergebnis "gruen".

Der 47. ist **T-064** (Geviertstrich, trotzdem nicht im Plan) - dort ist der
Plan selbst nachzuziehen.

Betroffen: T-064, T-115, T-119, T-121, T-122, T-140, T-141, T-152, T-160,
T-166, T-167, T-168, T-169, T-170, T-171, T-176, T-178, T-202, T-203, T-230,
T-234, T-235, T-236, T-242, T-244, T-248, T-249, T-250, T-253, T-254, T-273,
T-274, T-275, T-277, T-278, T-280, T-282, T-284, T-285, T-287, T-305, T-306,
T-307, T-312, T-314, T-333, T-335.

### 2. Die Mengenangabe im Plankopf ist falsch

Der Kopf sagt: *"132 Eintraege im Abschnitt `Offen`, davon 13 mit `[x]`,
**119 offen**"*.

Tatsaechlich im Abschnitt `## Offen`:

| | Kopf sagt | Tatsache |
|---|---|---|
| Checkbox-Eintraege | 132 | **188** |
| davon `[x]` | 13 | **21** |
| nicht abgearbeitet | 119 | **166** (`' '` 159, `[?]` 6, `[!]` 1) |

Die Differenz ist dieselbe Ursache: die 46 Bindestrich-Punkte wurden nicht
mitgezaehlt. `- [?]` (wartet auf Max) und `- [!]` (blockiert) sind **offen** -
der Plan fuehrt sie mit, die Zahl im Kopf nicht.

## Was der Plan damit weitergehen kann

Nichts, in dieser Form. Wer die 119 Zeilen als vollstaendige Liste nimmt,
verliert 28 % des Backlogs - darunter T-064 (Nautilus-Kraken-Orderweg), T-115
(Kraken-USDC), T-202/T-203 (Backtest-Regeln), T-253 (Paperclip-CLI).

## Naechster Schritt

`routing_plan_bauen.py` so umstellen, dass es beide Kopfformen liest
(beide Regexe, wie im Pruefer), T-064 nachtraegt und die Kopfzahl aus der
gezaehlten Liste zieht statt sie zu behaupten. Danach:

```
python MaxHirn/Archiv/routing_plan_pruefen.py <plan.md>
```

muss mit Exit 0 enden. Der Plan gehoert zusaetzlich aus dem Scratch-Ordner
nach `MaxHirn/Archiv/ROUTING_PLAN_YYYY-MM-DD.md` - im Scratch-Ordner ist er
ein flüchtiger Sitzungsstand, und die Karte t_c2eab7bc verlangt genau diesen
dauerhaften Ablageort.