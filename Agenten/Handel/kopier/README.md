# Kopier-Spur — Copy-Trading der Pump.fun-Rangliste (Papierbuch)

Eine zweite Spur nach dem Muster von `spiegel/`: Sie beantwortet die Frage,
**ob das Nachahmen der Top-Trader von Pump.fun nach Kosten trägt** — als
Papierbuch ohne Orderpfad.

## Was der Feed ist

| Zweck | Quelle | Endpunkt |
|---|---|---|
| Trader-Feld (taeglich, PnL) | frontend-api-v3.pump.fun | `/pnl-leaderboard?period=daily&sort=combined` |
| Positionen eines Traders | frontend-api-v3.pump.fun | `/user-portfolio/<wallet>` |
| Letzter Kauf (Signal-Zeit) | swap-api.pump.fun | `POST /v1/coins/<mint>/trades/batch` |
| Risiko (gebannt/nsfw) | frontend-api-v3.pump.fun | `/coins/<mint>` |
| Letzte Kurse (Bericht) | swap-api.pump.fun | `GET /v2/coins/<mint>/trades?limit=1` |

Alle Endpunkte sind oeffentlich, ohne Schluessel — und `lesen.py` ist der
einzige Zugang. Der Waechter dort (Schreibwortliste + Pfad-Whitelist) laesst
nur Lese-Pfade durch; `kopier.py` prueft beim Import, dass der Waechter noch
da ist, und startet sonst nicht.

## Was ein Signal ist

Eine Position, die **neu** im Portfolio eines verfolgten Traders auftaucht
und deren letzter Kauf des Vorbilds nicht aelter ist als
`max_alter_signal_sekunden` (30 Minuten). Ein gehaltener Altbestand ist kein
Signal — ihn nachzukaufen waere Zuchtauswahl nach dem Ergebnis.

Der gesehene Bestand steht in `zustand.json` unter `gesehen_portfolios` und
wird jeden Zyklus neu registriert:

- **Einlauf**: Beim ersten Kontakt mit einer Wallet wird deren Bestand still
  uebernommen (kein Kauf). Das verhindert, dass der erste Zyklus das ganze
  aktuelle Portfolio der Gewinner kopiert.
- **Endgueltig**: Jede Entscheidung (Band, zu alt, Risiko, gekauft) gilt fuer
  (Wallet, Token); nur Kapazitaetsfälle (Buch voll, Zyklusdeckel) duerfen im
  naechsten Zyklus wieder Kandidat sein.

Preise fuer offene Kopien kommen aus den Portfolio-Snapshots
(`tokenPriceUsd`) — der Zyklus liest die Portfolios ohnehin.

## Ausstiege

Stop (−15 % vom Einstand, realisiert max −20 % inklusive Kosten),
**Trailing-Stop** (ab +30 % hängt der Ausstieg 25 % unter dem höchsten
beobachteten Kurs) und Frist (168 h als Sicherheitsnetz) sind eigene
Mathematik — kein Auto-Exit nach dem Vorbild-Timing. Bis zum 15.09.2026 galt
ein festes Ziel (+60 %); die Umstellung auf Trailing soll theoretische
10x/100x laufen lassen. Zusätzlich schließt die Spur eine Kopie, wenn die
Position des Vorbilds aus dessen Portfolio verschwindet (`follow_ausstieg` in
wachen.json): das ist die beobachtbare Ausstiegs-Entscheidung des Modells,
geschlossen zum letzten beobachteten Kurs. Altbestand läuft unter den vor dem
15.09.2026 gebuchten Regeln aus. OKX-Vorbereitung: Stop = Stop-Market,
Trailing = OKX-Trailing-Stop (Trigger/Callback siehe wachen.json).

## Kosten

5 % Slippage + 1 % Gebuehr, zweimal gerechnet (Kauf teurer, Verkauf
billiger). Konservativer als spiegel (3 %), weil Pump.fun-Buecher duenner
sind. `--messen` haelt den Nachlauf (Kurs jetzt gegen Kurs des Vorbilds)
gegen die Annahme.

**Gemessen am 01.10.2026** (`--messen --bestand --stichprobe 25`, das Buch
wird dabei nicht angefasst, Rohwerte in `daten/messung.json`): 25 Kandidaten
im Marktkap-Band angefragt, 14 verwertet - 11 hatten in den letzten 50 Trades
KEINEN sichtbaren Kauf (die API liefert nur 50, bei einem Vorbild, das gerade
verkauft, stehen dort nur Verkaeufe; das wird gezaehlt, nicht still
uebersprungen). Nachlauf: Median **-35,64 %**, Schnitt **-31,48 %**, Spanne
**-87,15 % bis +76,05 %**.

Was das heisst: der Nachlauf auf gehaltenen Positionen ist gross und breit -
aber er ist **nicht** der eigene Abschlag. Diese Spur kauft zum
BEOBACHTETEN Kurs + 5 %; die 5 % Slippage und die 1 % Gebuehr bleiben
Annahmen, weil die Pump.fun-Schnittstelle **keine Pooltiefe** liefert (die
Untergrenze waere `2 x Einsatz / Liquiditaet`). Neu messen, wenn der Einsatz
sich aendert oder eine Live-Anbindung ansteht.

## Aufruf

    python kopier.py --waehlen     # verfolgte.json aus der Rangliste bauen
    python kopier.py --vorschau    # was waere dran, ohne zu schreiben
    python kopier.py --papier      # ein Papierzyklus mit Journal
    python kopier.py --bilanz      # welche Trader getragen haben
    python kopier.py --ablehnungen # warum Kandidaten NICHT gekauft wurden
    python kopier.py --messen      # Nachlauf gegen die Slippage-Annahme
    python kopier.py --messen --bestand --stichprobe 25   # ueber den Bestand
    python kopier.py --live        # verweigert (kein Live-Pfad)

Verdrahtet wie spiegel: `dauerlauf.SPUREN`, Bus `/status`, Tagesbericht,
`.gitignore`-Whitelist. Das Journal, der Zustand, die Verfolgungsliste und
das Ablehnungsprotokoll werden nach jedem Zyklus nach
`Q:\Handel_Journal\kopier` gespiegelt (Bedingung 4).