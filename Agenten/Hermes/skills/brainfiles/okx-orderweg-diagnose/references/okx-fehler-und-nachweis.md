# OKX-Fehlercodes am Orderweg und der Beleg dazu

## Codes, die am Orderweg auftreten

| Code | Bedeutung | Typische Ursache im Haus |
|---|---|---|
| `51000` | Parameter ungueltig | Ein Wert ist leer/`None` (z. B. `ordId`, weil die Position keine Order-Kennung hat). `urlencode` schreibt `None` als Text „None". |
| `51603` | Order unbekannt | Kennung formal gueltig, aber die Order existiert nicht / liegt ausserhalb des Orderhistorie-Fensters. |
| `51008` | zu wenig Guthaben | Quote-Waehrung des Paares ist leer (0 USDT bei gefuelltem USDC). **Beim VERKAUF ist der Code meist die Folge einer Position, die es an der Boerse nie gab** (Buch-Geist: `modus: live` im Journal, keine Order in der Historie) — dann ist nicht die Kontolage, sondern der Geist zu pruefen (siehe Deutung unten). |
| `50119` | Key existiert nicht (in dieser Umgebung) | **Haeufigster Grund ist der falsche HOST**, nicht ein toter Schluessel: der Schluessel kam ueber den Registry-Rueckfall, der Host aber nicht (nur `os.environ`) — ein EEA-Schluessel gegen `www.okx.com` gibt genau diesen Code. Erst die Basis pruefen, dann den Schluessel. |
| `50101` | Key passt nicht zur Umgebung | Basis (www vs eea) oder Demo-Modus (`OKX_DEMO`/`OKX_SIMULATED`) — dieselbe Wurzel wie `50119`. |
| `50124` | keine Handelsberechtigung FUER DIESEN MARKT | Meist der falsche NAMENSRAUM desselben Marktes: die Spur schickt `XAU-USDT-SWAP` (`instType=SWAP`), handelbar ist nur der XPERP-Kontrakt (`instType=FUTURES`, `XAU-USD_UM_XPERP-…`). `perm`/`acctLv` sind dabei in Ordnung. |
| `51015` | `instId` passt nicht zu `instType` | Falscher `instType` beim Nachweis — der XPERP-Kontrakt ist `FUTURES`, nicht `SWAP`. |
| `1` | generisch „All operations failed" | **Meist KEIN freies Guthaben**: `availEq` der Margin-Waehrung ist 0, obwohl die Spur in ihrem eigenen Modell Platz sieht. Eine CROSS-Margin-Position frisst das GESAMTE Konto, nicht nur ihre eigene Margin — das eigene `max_margin_gesamt_usd` zaehlt nur das eigene Buch und sieht eine fremde Cross-Position nicht. |

Merksatz: `51000` ist ein FORMfehler (der Wert selbst), `51603` ein
EXISTENZfehler. Wer beides verwechselt, sucht am falschen Ende.

**`50119`/`50101` vor jeder Schluessel-Theorie gegen den Host pruefen.** Der Schluessel
wird mit Registry-Rueckfall gelesen, der Host muss es genauso. Probe ohne Netz:
`env -u OKX_BASE <venv>/python.exe -c "import okx; print(okx._live_basis())"` — kommt
die Kontakt-Basis, ist der Prozess in Ordnung; kommt die globale, hat der Aufrufer den
Schluessel nur ueber die Registry gefunden. Den Host im Fehlertext MITNENNEN (welcher
angesprochen wurde und welcher in der Registry steht), sonst sucht der Naechste wieder
beim Schluessel.

## Beleg-Rezept (signiert, rein lesend)

Aus dem Spur-Ordner, Haus-Modul `okx.py` (liest **Schluessel UND Host** aus
der Prozessumgebung, sonst aus `HKCU\Environment`):

```python
import sys
sys.path.insert(0, r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel\scanner")
import okx
print("Basis:", okx._live_basis())            # IMMER zuerst: sonst deutet man
print("Key da:", okx.schluessel_vorhanden())   # den Fehler der falschen Umgebung

# Handelsrecht des Schluessels (perm muss 'trade' enthalten) + IP-Sperre ('ip' leer)
d = okx._roh("/api/v5/account/config", "GET", signiert=True)
r = (d or [{}])[0]

# Kontostand EINER Waehrung: details == [] bedeutet Bestand 0
okx._roh("/api/v5/account/balance?ccy=NEAR", signiert=True)

# Orderhistorie EINES Instruments (Fenster ca. 7 Tage): [] = keine Order
okx._roh("/api/v5/trade/orders-history?instType=SPOT&instId=NEAR-USDT&limit=20",
         signiert=True)

# Steht fuer JEDE Live-Position ein Notausstieg? Ein fehlender ist ein Risiko.
okx._roh("/api/v5/trade/orders-algo-pending?ordType=conditional",
         "GET", signiert=True)
```

**`okx._roh` gibt die DATA-LISTE zurueck, nicht das Antwort-Dict** (`code`/`msg`
hängen intern). Wer `.get("code")` darauf aufruft, bekommt einen `AttributeError`,
obwohl der Abruf geklappt hat — nicht als Fehler deuten, sondern die Liste lesen.
Ein Fehlschlag kommt als `OKXFehler` mit Code und Text.

Ausfuehren mit dem Spur-venv (`scanner/.venv/Scripts/python.exe`), Skript nach
`Agenten/Hermes/cache/` schreiben und danach loeschen. Die Modulpfade sind der
Weg ueber den PFAD, nicht ueber `sys.path`-Eintraege in den Spuren.

## Deutung der Ergebnisse

- `details: []` beim Kontostand UND `[]` in der Orderhistorie: die Position hat es
  am Handelsplatz nie gegeben — sie lebt nur im Journal. Der abgebrochene Verkauf
  war dann korrekt (nichts zu verkaufen), und es ist kein Geld verloren. Diese
  Geist-Diagnose ist bei einem `51008 insufficient`-Verkauf der ERSTE Schritt,
  nicht der letzte: **erst die Orderhistorie bewusst pruefen, dann ein Urteil**
  (`orders-history` UND `orders-history-archive` UND `orders-pending` — die
  Standard-Historie kann fuer den Zeitraum leer sein, waehrend das Archiv die
  Wahrheit traegt; alle drei Endpunkte fragen, nicht nur den ersten). Und beim
  Kontostand `spotBal` gegen `frozenBal` lesen: `frozenBal > 0` heisst
  eingefrorener Bestand (offene Position), `frozenBal == 0` bei gefuelltem
  `spotBal` heisst frei verfuegbare Menge ohne Position. Merksatz: `modus: live`
  im Journal ist ein BUCHVERMERK, kein Orderbeleg — der Beleg ist die Order in
  der Boersen-Historie.
- `details` gefuellt, Orderhistorie leer: falsches Instrument oder falsches
  Fenster (Historie reicht nur wenige Tage zurueck).
- Quote pruefen: `ccy=USDT` gegen `ccy=USDC`. Die `availBal` der Quote-Waehrung ist
  die einzige Grundlage fuer „dieser Kauf haette klappen koennen".
- Bei `50124` zuerst den Namensraum belegen, dann die Rechte: Orderhistorie des
  Zwillings (`/trade/orders-history-archive?instType=FUTURES&instId=…`, wenn das
  kurze Fenster leer ist) und `/account/positions?instType=SWAP` gegen
  `?instType=FUTURES`. Sind die SWAP-Positionen leer und die FUTURES-Positionen
  gefuellt, handelt die Spur den falschen Namen desselben Marktes.
- Bei generischem `1 All operations failed` zuerst die MARGIN pruefen, nicht den
  Schluessel: `/account/balance?ccy=<margin-waehrung>` — `availEq` 0 bei gefuelltem
  `eq`/`frozenBal` heisst: das Konto ist voll belegt, jede neue Order scheitert.
  Dann `/account/positions?instType=FUTURES` auf `mgnMode` ansehen: eine
  `cross`-Position (oft eine uebernommene Fremdposition, `fremdposition_uebernommen`
  im Journal) bindet das GESAMTE Konto, waehrend die Spur `isolated` eroeffnet und
  in ihrem eigenen `max_margin_gesamt_usd` Platz sieht. Die Spur muss vor dem
  Eroeffnen das freie `availEq` der Boerse lesen und bei 0 ueberspringen statt
  blind eine Order zu schicken, die gar nicht fuellen kann.

## Was ein Leseaufruf NICHT ersetzt

die Fehlermeldung des Zyklus. Die Spur druckt Kinderstderr, der Dauerlauf haengt
Auffaelligkeiten an die Telegram-Nachricht des Zyklus — eine Zeile wie
`<spur>: Verkauf X fehlgeschlagen: <text>` bleibt der einzige Beleg fuer den
konkreten Text. Sie ist nicht im Journal; wer sie braucht, fragt Max nach der
vollstaendigen Zyklusnachricht.
