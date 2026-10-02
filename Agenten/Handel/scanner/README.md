# Marktscanner

Scannt taeglich eine Watchlist der grossen Krypto-Werte, bewertet jeden auf
**Chance gegen Risiko** und macht daraus konkrete, hart begrenzte
Handelsvorschlaege. Er kann diese Vorschlaege auch selbst ausfuehren -- im
Rahmen der Wachen in `wachen.json` und erst, wenn drei Sperren bewusst
geoeffnet sind.

Stand: 2026-08-31. **Live-Handel ist noch nie scharf gelaufen** -- es fehlen
gueltige OKX-Schluessel. Bis dahin: Papierhandel.

## Die Grundlinie kennen

Aus [[Handelsbots]] (`Wissen/Handelsbots.md`): Ueber lange Zeitraeume lag jede
getestete mechanische Krypto-Strategie **nahe null, leicht darunter** -- die
Gebuehren fressen den Vorteil. Ein Backtest ueber ein einzelnes gutes Fenster
misst vor allem dieses Fenster. Dieser Scanner sucht deshalb nicht den grossen
Wurf, sondern Lagen mit gutem Verhaeltnis von Aufwaertspotenzial zu Schwankung,
und siebt alles Zappelige hart aus. Er kann trotzdem Geld verlieren. Die
Kleinstbetraege (50 USD je Trade, 200 gesamt) sind Absicht.

## Dateien

| Datei | Zweck |
|---|---|
| `wachen.json` | **Eine Wahrheit fuer alle Grenzen** -- Watchlist, Betraege, Tore, Master-Schalter. Wird nur gelesen. |
| `okx.py` | OKX-Zugang. Oeffentliche Kerzen/Kurse ohne Schluessel; signierte Orders nur mit Schluessel + `--live`. |
| `bewertung.py` | Das Bewertungsmodell. Jede Kennzahl steht einzeln im Ergebnis. |
| `scan.py` | Taeglicher Scan -> `berichte/JJJJ-MM-TT.json` und `berichte/neuester.json`. Loest nichts aus. |
| `handeln.py` | Vorschlaege bauen und ausfuehren (Papier oder Live). Fuehrt `zustand.json` und `handelsjournal.csv`. |
| `.venv/` | Eigenes venv (Python 3.13.15, nur Standardbibliothek). Neu gebaut am 31.08.2026, nachdem der Python-Neustand kam -- siehe [[Python-Versionen]]. |

Nicht versioniert (Rauschen, aber gesichert): `zustand.json`, `handelsjournal.csv`, `berichte/`.

## Aufrufe

```powershell
cd Agenten\Handel\scanner

.venv\Scripts\python.exe scan.py              # Rangliste + Bericht schreiben
.venv\Scripts\python.exe scan.py --kurz       # nur Tabelle, nichts schreiben
.venv\Scripts\python.exe okx.py ETH-USDT      # Kerzen eines Werts pruefen

.venv\Scripts\python.exe handeln.py --vorschau  # zeigen, was er taete
.venv\Scripts\python.exe handeln.py --papier    # Papierhandel (Standard der Routine)
.venv\Scripts\python.exe handeln.py --live      # echte Orders -- nur wenn alle Sperren offen
```

## Das Bewertungsmodell

Eingabe: bis zu 300 Tageskerzen von OKX (`/api/v5/market/candles`, `bar=1D`).

**Chance (0--100)** -- gewichtete Summe aus:
- Trend: Schlusskurs ueber SMA20 / SMA50 / SMA100 (Gewicht 0,30)
- Momentum: 30-Tage-Rendite, skaliert -10 %..+40 % (0,28)
- Ruecksetzer: Abstand zum 60-Tage-Hoch -- ein Pullback ist gut, das Hoch selbst nicht (0,16)
- nicht ueberkauft: RSI(14) ueber 82 loescht die Chance (0,14)
- Volumenbestaetigung: juengstes Volumen gegen 30-Tage-Schnitt (0,12)

**Risiko (0--100)** -- gewichtete Summe aus:
- Volatilitaet p.a.: Standardabweichung der Tagesrenditen x sqrt(365), 30 %..150 % (0,42)
- max. Drawdown der letzten 90 Tage (0,28)
- RSI-Extreme, oben wie unten (0,16)
- Absturz-Momentum: stark negative 30-Tage-Rendite (0,14)

**Score** = `chance x (1 - 0,7 x risiko/100)`, gekappt auf 0--100.
**Verhaeltnis** = `chance / risiko`.

### Die Tore (hart, nicht nur Gewichtung)

Ein Wert wird nur zum Vorschlag, wenn **alle drei** erfuellt sind
(`wachen.json`):

| Tor | Standard | warum |
|---|---|---|
| `mindest_score` | 60 | unter 60 ist das Bild nicht klar genug |
| `max_volatilitaet_pa` | 1,20 | "lower risk" als Filter, nicht als Abzug |
| `mindest_chance_risiko` | 1,5 | Chance muss das Risiko um die Haelfte uebersteigen |

## Vom Vorschlag zur Position

- **Einstieg**: letzter Schlusskurs.
- **Pflicht-Stop**: `3 % + 6 % x min(vola_pa, 1,5)`, gedeckelt auf
  `pflicht_stop_prozent_min..max` (4--12 %). Jede Position hat einen Stop -- das
  ist nicht abschaltbar.
- **Ziel**: Einstieg + 2 x (Einstieg - Stop). Chance/Risiko 2:1.
- **Groesse**: `max_pro_trade_usd` (50).

Der Ausfuehrer oeffnet neue Positionen nur, solange
`offene < max_offene_positionen` (4) **und**
`gebunden + 50 <= max_gesamt_usd` (200). Nach einem Stop-Out gilt fuer diesen
Wert `abklingzeit_tage` (3) Sperre. Bereits gehaltene Werte werden nicht
nachgekauft.

Ausstieg je Lauf: aktueller Kurs gegen Stop und Ziel. Beruehrt er einen, wird
glattgestellt und ins Journal geschrieben; ein Stop-Out setzt die Abklingzeit.

## Die drei Sperren vor echtem Handel

`handeln.py --live` handelt **nur** scharf, wenn **alle drei** offen sind --
sonst laeuft es auf Papier weiter und sagt, welche Sperre zu war:

1. `wachen.json` -> `"handel_erlaubt": true`
2. `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE` als
   Windows-Benutzervariablen (`HKCU\Environment`) -- **nicht** in den Vault,
   nicht neben den Code. `okx.py` liest sie ersatzweise direkt aus der Registry,
   genau wie der Kraken-MCP.
3. `--live` ausdruecklich auf der Kommandozeile.

Die tägliche Routine (`Agenten/Routinen/marktscanner.ps1`) ruft `handeln.py`
**ohne** `--live` auf. Aus einem Zeitplan heraus wird nie echtes Geld bewegt --
das ist die Regel aus `Wissen/Handelsregeln.md` und gilt weiter.

### Scharfschalten (wenn es soweit ist)

1. Auf OKX ein API-Schluesselpaar mit **Handelsrecht** (kein Auszahlungsrecht)
   erzeugen. IP-Freigabe setzen.
2. `setx OKX_API_KEY ...`, `setx OKX_API_SECRET ...`, `setx OKX_API_PASSPHRASE ...`
   -- neue Shell oeffnen, `okx.py` zeigt dann `Schluessel gesetzt: True`.
3. `okx.guthaben_usdt()` gegenpruefen (mind. 200 USDT auf dem Spot-Konto).
4. **Einen** Vorschlag von Hand scharf ausfuehren und in der OKX-Oberflaeche
   nachsehen, dass Order und Stop richtig ankamen -- der Live-Pfad ist bis dahin
   ungetestet.
5. `wachen.json` -> `handel_erlaubt: true`. Erst danach ergibt `--live` echte
   Orders.

## WebSocket-Trigger (Event-getriebener Ausfuehrungspfad)

Seit 2026-10-02 gibt es einen optionalen Trigger-Prozess, der die Wartezeit bis
zum naechsten 15-Minuten-Zyklus entfernt: beim Kerzenschluss (confirm=1) wird
`handeln.py` sofort ausgefuehrt, statt im naechsten Viertelstunden-Zyklus.

**Regeln (nicht verhandelbar):**
1. **Signal-Logik UNVERAENDERT** -- `handeln.py` wird nur frueher gerufen.
2. **Sperrenkette UNANGETASTET** -- alle Wachen bleiben wirksam.
3. **PAPER ZUERST** -- Buchungen laufen ueber denselben Papierweg.
4. **Zyklus bleibt Rueckfallebene** -- Trigger ist Zusatz, kein Ersatz.
5. **Fuellpreis-Vergleich** -- `herkunft=trigger` vs `herkunft=zyklus` im Journal.
6. **Tests ohne Netz** -- WebSocket-Rahmen als Attrappen.

### Datei

| Datei | Zweck |
|---|---|
| `ws_trigger.py` | WebSocket-Client fuer den OKX BUSINESS-Feed (`/ws/v5/business`, Kanal `candle15m`) - die Kerzenkanaele liegen NICHT auf `/public` (gemessen 02.10.2026). Ruft `handeln.pruefe_ausstiege` / `pruefe_einstiege` bei Kerzenschluss; Buchungen tragen `herkunft=trigger`. Benoetigt `websocket-client` im venv. |
| `tests/test_ws_trigger.py` | Tests mit JSON-Frame-Attrappen, kein echtes Netz. |

### Aufrufe

```powershell
cd Agenten\Handel\scanner

# Papier-Modus (Standard, keine echten Orders)
.venv\Scripts\python.exe ws_trigger.py --modus papier

# Live-Modus (nur wenn alle Sperren offen)
.venv\Scripts\python.exe ws_trigger.py --modus live

# Testmodus: eine JSON-Zeile von stdin als Kerze verarbeiten
echo '{"arg":{"channel":"candle15m","instId":"BTC-USDC"},"data":[["1727780400000","50000","50100","49900","50050","100","1"]]}' | .venv\Scripts\python.exe ws_trigger.py --modus papier --test
```

### Technische Details

- **WebSocket-Host** wird aus `OKX_BASE` abgeleitet (EEA -> `ws.eea.okx.com`, WWW -> `ws.okx.com`).
- **Kanal**: `candle15m` fuer alle Instrumente aus `wachen.json` (Watchlist oder ganzes Universum).
- **Nur `confirm=1`** (abgeschlossene Kerze) loest aus -- identisch zur heutigen Logik.
- **Reconnect** mit exponentiellem Backoff (2s, 4s, 8s... max 300s).
- **Ping/Pong** alle 30s (OKX verlangt Text `ping`).
- **PID-Datei** `ws_trigger.pid` verhindert doppelten Start.
- **Log** in `ws_trigger.log` mit Zeitstempeln.
- **Eigene Prozess-ID** -- laeuft parallel zum 15-Minuten-Dauerlauf.

### Journal-Erweiterung

Jede Trigger-Buchung traegt `herkunft=trigger` im Journal (Standard: `herkunft=zyklus`).
Nach zwei Wochen kann man Fuellpreise je Quelle vergleichen.

## Grenzen

- Nur Long, nur Spot. Kein Hebel, kein Leerverkauf.
- Tageskerzen loesen nicht auf, ob an einem Tag zuerst Hoch oder Tief kam -- ein
  Stop-Out am selben Tag wie ein Ziel wird als Stop gewertet (vorsichtig).
- OKX liefert ueber `/market/candles` nur ~300 Tage. Fuer laengere Historie
  muesste `history-candles` geblaettert werden (wie in `dca_auswertung.py`).
- Der Scanner rechnet keine Gebuehren/Funding in die Vorschlaege ein. Real
  liegen die Ergebnisse darunter -- siehe [[Handelsbots]].
- Vergangene Kursverlaeufe sagen nichts ueber kuenftige.
