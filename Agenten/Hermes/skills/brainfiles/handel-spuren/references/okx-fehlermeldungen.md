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

## Falle beim Nachstellen

OKX antwortet ohne `User-Agent` mit **HTTP 403 (Cloudflare 1010)**. Wer
ein Wegwerfskript baut und `okx.HEADERS` vergisst, misst seinen eigenen
Fehler und haelt ihn fuer einen Schluesselfehler.
