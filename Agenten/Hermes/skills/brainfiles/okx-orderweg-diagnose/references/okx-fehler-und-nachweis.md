# OKX-Fehlercodes am Orderweg und der Beleg dazu

## Codes, die am Orderweg auftreten

| Code | Bedeutung | Typische Ursache im Haus |
|---|---|---|
| `51000` | Parameter ungueltig | Ein Wert ist leer/`None` (z. B. `ordId`, weil die Position keine Order-Kennung hat). `urlencode` schreibt `None` als Text „None". |
| `51603` | Order unbekannt | Kennung formal gueltig, aber die Order existiert nicht / liegt ausserhalb des Orderhistorie-Fensters. |
| `51008` | zu wenig Guthaben | Quote-Waehrung des Paares ist leer (0 USDT bei gefuelltem USDC). |
| `50101` | Key passt nicht zur Umgebung | Basis (www vs eea) oder Demo-Modus (`OKX_DEMO`/`OKX_SIMULATED`). |

Merksatz: `51000` ist ein FORMfehler (der Wert selbst), `51603` ein
EXISTENZfehler. Wer beides verwechselt, sucht am falschen Ende.

## Beleg-Rezept (signiert, rein lesend)

Aus dem Spur-Ordner, Haus-Modul `okx.py` (liest Keys aus Prozessumgebung, sonst
aus `HKCU\Environment`):

```python
import sys
sys.path.insert(0, r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel\scanner")
import okx
print("Basis:", okx._live_basis())            # IMMER zuerst: sonst deutet man
print("Key da:", okx.schluessel_vorhanden())   # den Fehler der falschen Umgebung

# Kontostand EINER Waehrung: details == [] bedeutet Bestand 0
okx._roh("/api/v5/account/balance?ccy=NEAR", signiert=True)

# Orderhistorie EINES Instruments (Fenster ca. 7 Tage): [] = keine Order
okx._roh("/api/v5/trade/orders-history?instType=SPOT&instId=NEAR-USDT&limit=20",
         signiert=True)
```

Ausfuehren mit dem Spur-venv (`scanner/.venv/Scripts/python.exe`), Skript nach
`Agenten/Hermes/cache/` schreiben und danach loeschen. Die Modulpfade sind der
Weg ueber den PFAD, nicht ueber `sys.path`-Eintraege in den Spuren.

## Deutung der Ergebnisse

- `details: []` beim Kontostand UND `[]` in der Orderhistorie: die Position hat es
  am Handelsplatz nie gegeben — sie lebt nur im Journal. Der abgebrochene Verkauf
  war dann korrekt (nichts zu verkaufen), und es ist kein Geld verloren.
- `details` gefuellt, Orderhistorie leer: falsches Instrument oder falsches
  Fenster (Historie reicht nur wenige Tage zurueck).
- Quote pruefen: `ccy=USDT` gegen `ccy=USDC`. Die `availBal` der Quote-Waehrung ist
  die einzige Grundlage fuer „dieser Kauf haette klappen koennen".

## Was ein Leseaufruf NICHT ersetzt

die Fehlermeldung des Zyklus. Die Spur druckt Kinderstderr, der Dauerlauf haengt
Auffaelligkeiten an die Telegram-Nachricht des Zyklus — eine Zeile wie
`<spur>: Verkauf X fehlgeschlagen: <text>` bleibt der einzige Beleg fuer den
konkreten Text. Sie ist nicht im Journal; wer sie braucht, fragt Max nach der
vollstaendigen Zyklusnachricht.
