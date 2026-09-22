---
titel: Boersen und Schluessel
tags: [lektion, handel, kraken, schluessel]
aktualisiert: 2026-09-22
---

# Boersen und Schluessel

Zwei Lektionen vom 22.09.2026, beide aus einem einzigen Satz von Max
(„Grade wird auch kraken-cli integriert"). Beide haben dieselbe Wurzel: auf
der Boerse gilt FUER EINEN SCHLUESSEL, was das ZULETZT gesehene Werkzeug
getan hat - nicht, was das eigene Werkzeug tut.

## 1. Zwei Werkzeuge, ein Schluessel: die Nonce-Einheit muss die groesste sein

Kraken verlangt zu jeder signierten Abfrage einen **nonce** (eine Zahl, die
streng steigen muss) und merkt sich je Schluessel den **hoechsten** Wert. Die
Hausseite rechnete in **Mikrosekunden** (~1,77e12); die offizielle
`kraken-cli` signiert in **Nanosekunden** (~1,78e18) - rund eine Million Mal
groesser. Nach EINEM Aufruf der CLI war jede Hausabfrage kleiner als der
gemerkte Wert und endete mit `EAPI:Invalid nonce`.

**Wie es aufgefallen ist:** nicht am kraken-Skript, sondern an der
LIVE-SPERRE von mosaic - `--vorschau` meldete nicht mehr „Freigabefenster
nicht offen", sondern „Guthaben nicht abrufbar (EAPI:Invalid nonce)". Ein
Nebeneffekt auf einem anderen Weg ist oft das einzige Symptom.

**Regel:** benutzen zwei Werkzeuge denselben API-Schluessel, muss die
Nonce-Einheit die GROESSTE der beiden sein (hier: Nanosekunden, belegt durch
den Betrieb der offiziellen CLI). Wer eine zweite Anbindung einrichtet, misst
zuerst, womit sie signiert (`Agenten/Hermes/cache/kraken_nonce_sonde.py`).

**Gegenprobe, wenn es wieder passiert:** `kraken.guthaben('ZEUR')` ueber das
Hausmodul; kommt `EAPI:Invalid nonce`, hat ein anderes Werkzeug den Zaehler
hochgestellt. Heilen kann nur ein groesserer Wert, nicht ein Neustart.

## 2. Ein Programmpaar mit zwei Namen: der gueltige steht selten im Handbuch

In der Benutzerumgebung liegen **zwei** Kraken-Paare:

| Name | Zustand (gemessen 22.09.2026) |
|---|---|
| `KRAKEN_SPOT_API_KEY` / `KRAKEN_SPOT_API_SECRET` | **gueltig** - liest Haus-`kraken.py` und der Kraken-MCP |
| `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` | existiert, Kraken antwortet `EAPI:Invalid key` |

Ein Programm, das „Invalid key" meldet, waehrend ein anderes mit demselben
Konto arbeitet, liest den ANDEREN Variablennamen - nicht einen falschen
Schluessel. `Agenten/Werkzeuge/kraken.ps1` setzt fuer die CLI die generischen
Namen aus den SPOT-Werten; danach meldet die CLI dasselbe Guthaben wie die
Hausseite.

**Regel:** vor jeder „Schluessel kaputt"-Aussage pruefen, welchen NAMEN das
Programm liest (Quelltext oder Doku), und beide Namen gegen die API halten.
Kein Wert wird je ausgegeben oder committet - nur Ja/Nein und Laenge.
