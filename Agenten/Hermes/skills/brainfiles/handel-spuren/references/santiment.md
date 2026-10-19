# Santiment SanAPI: On-Chain-, Social- und Dev-Metriken

Ausloeser: „Santiment" - oder eine Kennzahl, die unsere Kerzen nicht hergeben
(aktive Adressen, MVRV, Exchange-Zu-/Abfluesse, Social Volume, Dev-Aktivitaet).

## Woran man arbeitet

- `Werkstatt/santiment` - Fork `mfaupel95/santiment` von
  `api-evangelist/santiment`. **Keine Software**: Dokumentation plus das
  vollstaendige GraphQL-Schema (`graphql/santiment-schema.graphql`, 83 KB,
  179 Query-Felder) und eine MCP-Beschreibung (`mcp/santiment-mcp.yml`).
  Feldnamen **nie raten** - im Schema nachsehen.
- `Agenten/Handel/santiment_daten.py` - der Zugang (nur Standardbibliothek,
  nur lesend): `graphql()`, `projekte()`, `projekt()`, `metrik()`,
  `trendende_woerter()`, `erlaubtes_fenster()`, `probe()` und die Schalter
  `--probe`, `--fenster`, `--metrik`, `--woerter`, `--projekte`.
- Tests: `Agenten/Handel/tests/test_santiment_daten.py` (10, ohne Netz - der
  Fenster-Parser wird gegen die echte Fehlermeldung der API geprueft).

## Die drei Fallen

1. **Anonym laeuft - aber jede Metrik hat ihr EIGENES Zeitfenster.**
   Gemessen am 16.09.2026 (Stufe `SANAPI FREE`): Schema, `allProjects`,
   `getTrendingWords` und `getMetric`/`daily_active_addresses` kommen ohne
   Schluessel mit echten Werten; `social_volume_total` dagegen nur von
   2025-09-16 bis **2026-08-17** (rund einen Monat Rueckstand). Die API nennt
   die Grenze im Fehlertext (`Allowed time restrictions:`), und
   `erlaubtes_fenster()` liest sie dort heraus. **Nie ein Fenster annehmen,**
   ohne es fuer DIESE Metrik geprueft zu haben.
2. **Eine leere Reihe ist kein Fehler.** Ausserhalb des Fensters antwortet die
   API mit `timeseriesData: null` bei HTTP 200 - `metrik()` gibt dann `[]`
   zurueck. Wer `[]` als "null Aktive Adressen" liest, erfindet einen Absturz
   im Markt, wo nur die Stufe zu klein ist.
3. **Zwei Fehlermeldungen sehen aehnlich aus.** `from == to` ergibt „must be
   after the `from` datetime" - das ist KEINE Fenstergrenze. Der Fenster-Parser
   bricht in dem Fall bewusst ab, statt eine Zahl zu erfinden (dafuer fragt
   `erlaubtes_fenster()` mit zwei verschiedenen Zeitpunkten).

## Schluessel und Grenzen

- **Ein Schluessel ist optional.** Ohne `SANTIMENT_API_KEY` (Benutzervariable,
  aus `HKCU\Environment` gelesen wie in `melder.py`) laeuft alles anonym
  mit kleineren Fenstern; mit Schluessel (kostenloses Konto) sind sie weiter.
  Der Wert gehoert nach [[Zugaenge]] und **nicht** in eine `.env` im Fremd-Repo.
- **Der MCP-Weg ist der zweite, breitere Zugang**: `https://api.santiment.net/mcp`
  nennt acht Werkzeuge, `initialize` und `tools/list` antworten anonym, jeder
  `tools/call` kommt als HTTP 401 (OAuth 2.0 mit PKCE). Einrichten:
  `hermes mcp add santiment --url https://api.santiment.net/mcp --auth oauth`,
  danach `hermes mcp login santiment` - der Browser-Schritt ist Max' Teil.
- **Lesend.** Von den 179 Query-Feldern wird hier nur gelesen; die 136
  Mutations (Watchlists, Alerts, Dashboards) kommen nicht in Frage.

Verwandt: [[Buildix-Santiment-Handelswissen]], `references/boersen-datenzugriff.md`
