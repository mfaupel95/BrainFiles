# OKX-Fehler richtig lesen (und nicht dreimal senden)

Befund vom 20.09.2026, Spur `scanner`: Journal zeigte
`Verkauf AVAX-USDT fehlgeschlagen: HTTP Error 400: Bad Request`.
Daraus ist nicht ablesbar, was zu tun ist. Dahinter steckten ZWEI Fehler.

## 1. Orderfehler kommen mit HTTP 200

OKX lehnt eine Order fachlich ab, antwortet aber mit **HTTP 200** und
`code: "1"`. Die eigentliche Auskunft steht in `data[0].sMsg`/`sCode`:

```json
{"code":"1","msg":"All operations failed",
 "data":[{"sCode":"51020","sMsg":"Your order amount does not meet the minimum order amount."}]}
```

Wer nur das aeussere `msg` ausliest, schreibt "All operations failed" ins
Journal. Immer `data[0].sMsg` bevorzugen, `msg` nur als Rueckfall.

## 2. HTTP 4xx darf nicht als Transportfehler gelten

`_roh()` las die OKX-Auskunft nur bei 401/403 aus. Ein **400** fiel als
roher `HTTPError` durch und wurde von `_mit_wiederholung` fuer einen
Transportfehler gehalten - also **dreimal erneut gesendet**. Bei einer
Verkaufsorder ist jeder Versuch eine echte Order.

Regel: ALLE 4xx als fachlichen `OKXFehler` werfen (keine Wiederholung),
nur echte Transportfehler wiederholen.

## Gegenprobe (am echten Endpunkt, ohne Geld zu bewegen)

Eine Order mit zu kleiner Menge senden - OKX lehnt sie ab, es entsteht
keine Position:

```python
okx.markt_verkauf('AVAX-USDT', 0.001)
# vorher: HTTP Error 400: Bad Request
# jetzt:  OKX 51020: Your order amount does not meet the minimum order amount.
```

## 3. `50119`/`50101` heisst meist FALSCHER HOST, nicht toter Schluessel

Symptom: **jede** Order scheitert mit `OKX 50119: API key doesn't exist (HTTP
401)`, waehrend Leseaufrufe weiter funktionieren.

Mechanismus: ein Zugang besteht aus Schluessel **und** Host (`OKX_BASE`, EEA
`https://eea.okx.com` gegen global `www.okx.com`). Wird der Schluessel mit
Registry-Rueckfall gelesen (`_variable`), der Host aber nur aus der
Prozessumgebung (`_env`), dann findet ein Kindprozess ohne geerbte
Benutzervariablen den Schluessel - und signiert gegen den Vorgabe-Host. Der
Fehler sieht wie ein toter Schluessel aus, ist aber ein falscher Endpunkt.

**Regel: Schluessel und Host gehoeren zu EINEM Zugang - wer einen Teil mit
Rueckfall liest, liest jeden Teil so.** Und: ein `50119`/`50101`, das auf
JEDER Order steht, ist kein abgelaufener Schluessel.

Pruefen, **bevor** ein Schluessel getauscht wird:

```bash
env -u OKX_BASE python -c "import okx; print(okx._live_basis())"
# muss den EEA-Host nennen, sonst faellt der Kindprozess auf den globalen zurueck
```

Reihenfolge der Diagnose: erst Host, dann Kontoberechtigung, dann Schluessel.
Kontoberechtigung lesend: `/api/v5/account/config` signiert, Feld `perm`
(`read_only,trade`) und Feld `ip` (leer = keine IP-Sperre). **`okx._roh()` gibt
die DATA-LISTE zurueck, nicht das Antwort-Dict** - ein Probeaufruf mit `.get()`
faellt mit `AttributeError` um, obwohl der Abruf geklappt hat.

## Falle beim Nachstellen

OKX antwortet ohne `User-Agent` mit **HTTP 403 (Cloudflare 1010)**. Wer
ein Wegwerfskript baut und `okx.HEADERS` vergisst, misst seinen eigenen
Fehler und haelt ihn fuer einen Schluesselfehler.

