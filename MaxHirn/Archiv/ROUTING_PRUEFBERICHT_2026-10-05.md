# Pruefbericht Routing-Worklist (170 Punkte)

Erstellt am 2026-10-05 · Pruefer: t_0dece3ea · Quellen: `MaxHirn/Archiv/ROUTING_WORKLIST.md`,
`.worktrees/t_5609d126/cache/scratch/wl/statusliste.md`, Handoff-Metadaten von t_df4b5161.

## Kurzfassung

| Status | Anzahl |
|---|---|
| done | 29 |
| blocked (echter Blocker) | 114 |
| offen (unbearbeitet, kein Blocker) | 20 |
| FEHLT (kein Status geliefert) | 7 |
| **Summe** | **170** |

Kein einziger Punkt wurde als `split` gemeldet - die drei neuen Befunde aus
t_df4b5161 (T-349, T-350, T-351) sind neue TASKS.md-Punkte, keine Aufteilungen.

Die Abnahmekriterien dieser Karte verlangen fuer **jeden** Punkt einen Status aus
done / blocked / split. Das ist nicht erfuellt - siehe die Defekte unten.

## Defekte (Punkte ohne gueltigen Status)

| Punkt | Nr | Bucket | Was fehlt |
|---|---|---|---|
| **T-336** | 10 | ORDERED | Ursache mit T-347 behoben; Zahlen neu rechnen ist ein mehrstuendiger Lauf - KEIN done/blocked/split |
| **T-324** | 22 | ORDERED | kein Status im Handoff t_df4b5161 |
| **T-323** | 23 | ORDERED | kein Status im Handoff t_df4b5161 |
| **T-312** | 30 | ORDERED | kein Status im Handoff t_df4b5161 |
| **T-300** | 36 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-297** | 37 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-295** | 38 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-294** | 39 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-292** | 42 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-287** | 45 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-258** | 55 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-256** | 58 | PARALLEL | keine Statuszeile - Punkt aus der PARALLEL-Liste gefallen |
| **T-234** | 64 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-224** | 74 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-183** | 85 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-181** | 86 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-159** | 98 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-122** | 110 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-102** | 114 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-128** | 118 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-104** | 123 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-101** | 124 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-092** | 130 | ORDERED | kein Status im Handoff t_df4b5161 |
| **T-091** | 131 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| **T-067** | 149 | ORDERED | kein Status im Handoff t_df4b5161 |
| **T-064** | 152 | ORDERED | kein Status im Handoff t_df4b5161 |
| **T-053** | 161 | PARALLEL | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |

### B1 - 6 ORDERED-Punkte ohne jeden Status

Der Handoff von t_df4b5161 fuehrt 22 ORDERED-Punkte auf, gibt aber nur 16 einen
Status. Diese 6 kommen im Kommentar und in den Metadaten **nicht** vor - sie sind
weder done, blocked noch split. Das ist genau das 'silently dropped', das diese
Karte verhindern soll.

### B2 - T-336 traegt keinen Abschlussstatus

T-336 steht unter 'noch offen mit Code-Anteil': die Ursache ist mit T-347 behoben,
die Zahlen selbst nicht neu gerechnet. Das ist weder done noch blocked noch split.

### B3 - T-256 fehlt in der PARALLEL-Statusliste, T-065 steht doppelt

Die Statusliste hat 148 Zeilen, deckt aber nicht die 148 PARALLEL-Punkte der
Worklist: **T-256** (#58) fehlt ganz, **T-065** (#151, laut Worklist ORDERED) steht
stattdessen dort. Die Zeilenzahl stimmt also, die Punktmenge nicht - eine
Zaehlpruefung allein haette den Fehler durchgelassen.

### B4 - 19 PARALLEL-Punkte sind als 'blocked' gefuehrt, aber unbearbeitet

Begruetzung woertlich: 'nicht gemessen (kein Werkzeugzugriff in dieser Sitzung)'.
Das ist kein Blocker, sondern ein Nichtbegonnen. Im Bericht als blocked zu
fuehren, verwechselt 'kann nicht' mit 'habe nicht'. Betroffen:

`T-300`, `T-297`, `T-295`, `T-294`, `T-292`, `T-287`, `T-258`, `T-234`, `T-224`, `T-183`, `T-181`, `T-159`, `T-122`, `T-102`, `T-128`, `T-104`, `T-101`, `T-091`, `T-053`

### B5 - 33 der 114 'blocked' tragen einen unkonkreten Grund

Nach Abzug der 19 'nicht gemessen' (B4) bleiben 114 blocked. Davon sind rund 81
mit benanntem Grund (27x 'wartet auf Max' mit konkretem Fehler, Entscheidungen von
Max, gemessene Boersengatter). Die uebrigen **33** benennen weder einen Fehler noch
eine fehlende Berechtigung - Formulierungen wie 'grosser Block - eigene Karte',
'Grossteil, lange Laeufe', 'betrifft fremde Bereiche, eigene Karte', 'Status:
wartet auf Max' ohne den konkreten Gatter. Als Blocker sind sie unbrauchbar und
muessen als offen zurueck.

## Eigenmaessig nachgefuehrte Pruefungen

| Pruefung | Ergebnis |
|---|---|
| `tests/test_mae_im_journal.py` (T-119) | **9 Tests, OK** - bestaetigt |
| `wavetrend/tests/test_wavetrend.py` (T-097) | **24 Tests, OK** - bestaetigt |
| `scripts/test_docker_wache.py` (T-306) | **11 Tests, OK** - bestaetigt |
| `tests/test_gateway_identitaet_wache.py` (T-146) | **12 Tests, OK** - bestaetigt (Datei liegt in `Agenten/Handel/tests/`, nicht `scripts/`) |
| `tests/test_gebuehr_boerse_abgleich.py` (T-330) | **16 Tests, OK** im Hauptbaum - bestaetigt |
| `tests/test_signal_gatter_papier.py` (T-347) | **12 Tests, OK** - bestaetigt |
| T-093: Satz in `Handelsregeln.md` Bedingung 1 | vorhanden, Diff = 1 Zeile - bestaetigt |
| T-097: `wt_einstiegsschwelle: 40.0` in `wavetrend/wachen.json` | vorhanden, Wert = alter Literalwert - bestaetigt |
| T-346: `sys.path`-Eintrag VOR dem spur_buch-Import, mit `__file__`-Pruefung | vorhanden (signal-executor.py Z. 154-162) - bestaetigt |
| T-229: `state.db` mit `mode=ro` | vorhanden (sitzungen_auswerten.py Z. 249) - bestaetigt |
| T-230: Vorzeichen im Paarer | `kosten_wendepunkt.py` Z. 129-133 - bestaetigt |
| T-152: `mcp-zombie-wache.py` | vorhanden, 13.712 B - bestaetigt |
| T-100/T-194: beide Dateischwund-Wachen | vorhanden - bestaetigt |
| Merge wt/t_5609d126 -> master | **NICHT gemergt** (3894778a fehlt in master) |
| Merge wt/t_df4b5161 -> master | gemergt (550346ec ist Vorfahre von master) |

**Keine der 13 nachgefuehrten Pruefungen ergab eine Abweichung.** Die
belegbaren Fertigstellungen halten. Die Defekte liegen ausschliesslich in der
Vollstaendigkeit der Statusfuehrung.

## Je Punkt

| Punkt | Nr | Bucket | Titel | Status | Beleg / Pruefung |
|---|---|---|---|---|---|
| T-346 | 1 | PARALLEL | signal-executor laeuft seit 12 Laeufen rot: ModuleNotFoundError spur_buch | done | signal-executor.py: sys.path-Eintrag VOR dem spur_buch-Import, mit __file__-Pruefung gegen Agenten/Handel. Beleg: echter Lauf aus Agenten/Hermes/scripts ohne Absturz; spur_buch laedt aus Agenten/Handel/spur_buch.py (H... |
| T-347 | 2 | ORDERED | omnitrade_futures: echte Papierrunden abwarten, dann Live-Freigabe neu bewerten | done | spur_buch.signal_gatter_gilt(w, live); 12 Tests gruen, Gegenprobe 4 rot; echter Lauf EINSTIEG LONG BTC-USDC @ 86012 |
| T-348 | 3 | ORDERED | Vier Tests rot, alle vier von fremder Hand (04.10.2026) | done | tests/test_replay.py, tests/test_spur_wache.py, scripts/spur-wache.py; 38 Tests gruen; Befund: 3 Spuren mit Queue ohne Wache (T-348/t_5c32be6e) |
| T-343 | 4 | PARALLEL | Nautilus-Orderweg: der DEMO-Haken ist je Lauf wieder weg | blocked | echter Blocker: DEMO-Haken im Nautilus-Reiter beschriften oder entfernen - vorher messen. |
| T-344 | 5 | PARALLEL | `nautilus_trader` steht jetzt in zwei venv, ohne dass es jemanden stoert | blocked | echter Blocker: nautilus_trader in zwei venv - README + Versionspruefung beim Start des Reiters. |
| T-345 | 6 | PARALLEL | Leitstand-Reiter ohne Takt: F5 wirkt, die Statusleiste altert nicht | blocked | echter Blocker: Leitstand-Reiter ohne Takt - TAKT_SICHTBAR, vorher Timer messen. |
| T-341 | 7 | PARALLEL | omnitrade_futures: kein Rust-Lauf laeuft, also null Signale | blocked | echter Blocker: Rust-Lauf fuer omnitrade_futures starten - grosser Block (cargo build --release + Lauf), eigene Karte. |
| T-342 | 8 | ORDERED | Backtest-Fensterlaenge: adx_macd 28 Tage positiv, Nachbarfenster 382 USD anders | done | omnitrade/intervalle_messen.py; 14/28/42 Tage = -24,99 / +9,61 / -0,23 USD je Runde; Befund als T-349 ausgelagert |
| T-338 | 9 | PARALLEL | QQQ-Tageskerzen nachladen, dann die QQQ/BTC-Rotation messen | blocked | echter Blocker: QQQ-Tageskerzen nachladen - Yahoo als Quelle, eigene Messung noetig. |
| T-336 | 10 | ORDERED | `trigger_modus: signal` liess JEDE Feed-Backtest-Zahl zu 0 werden | offen | Ursache mit T-347 behoben; Zahlen neu rechnen ist ein mehrstuendiger Lauf - KEIN done/blocked/split |
| T-337 | 11 | PARALLEL | `moondev_historie.basis_von` las einen Cache, der Tests lahmlegte | done | moondev_historie: Kommentar in basis_von (Zeile 141) beschreibt genau den Fehler und die Korrektur ('if not _basis' las den Cache nur, solange er leer ist); _basis wird jetzt geleert. |
| T-335 | 12 | PARALLEL | Bereichs-Besitz steht, die Werkzeuge rufen ihn noch nicht auf | blocked | echter Blocker: Bereichs-Besitz in die ersten drei Schreibwerkzeuge einbauen - betrifft fremde Bereiche, eigene Karte. |
| T-333 | 13 | PARALLEL | Zweigbestand aufgeraeumt, ein Grenzfall braucht eine Entscheidung | blocked | echter Blocker: Grenzfall 5bff1231: Max entscheidet (Zweig einziehen oder behalten). |
| T-331 | 14 | PARALLEL | `satz_pct_fuer` las den Börsensatz aus den Notizfeldern | done | gebuehren_setzen.py satz_pct_fuer() liest den Marktyp aus instrumente/markttyp/produkt statt aus json.dumps(w) - der Kommentar nennt genau den T-331-Befund (04.10.2026). |
| T-332 | 15 | ORDERED | `doppelte_nummern.py` uebersah 26 Eintraege und meldete gruen | done | aufgabenliste-pflegen/scripts/erledigen.py + test_doppelte_nummern.py; 15 Tests gruen; Gegenprobe zeigt 29 verlorene Bloecke |
| T-327 | 16 | PARALLEL | `anbindung_pruefen.py` las die Wachen aus Agenten/ statt Agenten/Handel/ | done | anbindung_pruefen.py hat HANDEL = HIER (Zeile 35) mit dem Vermerk vom 03.10.2026; Fix-Commit e8b831c4 'drei Verdrahtungsfehler und fuenf Pruefer-Fehler gefunden und behoben'. |
| T-328 | 17 | PARALLEL | Zwei Schattenarme liefen, ohne dass das Haus ihre Q:-Kopie je pruefte | done | spiegelstand.py liest die Arm-Dateinamen aus dauerlauf.SPUREN (nicht mehr fest); echter Lauf im HAUPTBAUM: 47 von 47 Spuren byte-gleich, darunter squeeze_eth und nautilus_kraken_futures. |
| T-329 | 18 | ORDERED | mosaics Gebuehr stand auf dem Kraken-Satz, obwohl die Spur auf OKX handelt | done | bereits behoben, Commit e6f2715c + gebuehren_setzen.py --anwenden; Sicherung mosaic/wachen.json.bak-20261004 |
| T-330 | 19 | ORDERED | Kein Werkzeug prueft, ob die Gebuehr zur aktiven Boerse passt | done | gebuehr_boerse_abgleich.py; 16 Tests gruen, 2 Gegenproben je 3 rot; Lauf: 5 echte Abweichungen (8 Fehlalarme entfernt) |
| T-326 | 20 | PARALLEL | Offene squeeze-Positionen tragen die alte Geometrie noch | blocked | echter Blocker: offene squeeze-Positionen tragen die alte Geometrie - zieht automatisch bei der naechsten Skalierung mit; ein Test fehlt noch. |
| T-325 | 21 | PARALLEL | Drei Spuren liefen, ohne dass das Haus ihre Zahlen kannte | done | alle drei Spuren in auswertung_alle.SPUREN, pruefe_ratschen.SPUREN, lage und dauerlauf - gemessen am Hauptbaum, alle vier Listen nennen liq_wand, trendwende_btc und nautilus_emacross. |
| T-324 | 22 | ORDERED | Spur-Audit: Edge und Echtheit fuer ALLE Spuren in einem Durchgang messen | FEHLT | kein Status im Handoff t_df4b5161 |
| T-323 | 23 | ORDERED | Welche Spur hat ueberhaupt Edge: Feed-Spuren gegen die Scanner-Basislinie messen | FEHLT | kein Status im Handoff t_df4b5161 |
| T-322 | 24 | PARALLEL | Scanner-Einstieg kam aus dem Vortagesbericht - die 124 Runden waren ein Rechenfehler | blocked | echter Blocker: Scanner-Freigabe neu bewerten - Entscheidung Max (Freigabekette). |
| T-320 | 25 | PARALLEL | Der gesperrte Update-Waisen laesst sich nicht entfernen | blocked | echter Blocker: gesperrter Update-Waisen - nach dem naechsten Neustart pruefen, sonst Admin; geloescht wird hier nichts. |
| T-321 | 26 | PARALLEL | kopier1zu1 brach am 02.10. mit Errno 22 ab, Ursache offen | blocked | echter Blocker: kopier1zu1 Errno 22 nicht reproduzierbar - laut eigenem Abnahmekriterium KEIN Umbau ohne Reproduktion. |
| T-316 | 27 | PARALLEL | iv_wand braucht Runden, bevor das Schiebetor bewertbar ist | blocked | echter Blocker: iv_wand Schiebetor bewerten - ab 30 Runden, ein zweiter Arm noetig. |
| T-317 | 28 | PARALLEL | Hebel bei einer Ein-Platz-Spur: die Frage kommt wieder | blocked | echter Blocker: Hebel bei einer Ein-Platz-Spur - ist rechnerisch beantwortet (Vermerk), die Umsetzung waere eine Ein-Platz-Sperre. |
| T-314 | 29 | PARALLEL | Long/Short auf den drei Freqtrade-Bots: gemessen schlechter, nicht gebaut | blocked | echter Blocker: Freqtrade auf Futures umbauen und messen - Grossteil, lange Laeufe. |
| T-312 | 30 | ORDERED | futures_probe laesst eine Position OHNE Stop offen, wenn /fills ablehnt | FEHLT | kein Status im Handoff t_df4b5161 |
| T-311 | 31 | PARALLEL | Scanner-USDC-Umstellung: USDT-Buch im Journal, Guthaben-Abgleich liest USDT | done | guthaben_abgleich.py: WAEHRUNG[scanner]='USD' (feste Liste) -> handelswaehrung() liest universum.quotes. Beleg: handelswaehrung('scanner') = USDC, kraken EUR, xperp USD; unbekannte Spur -> KeyError. tests/test_guthabe... |
| T-306 | 32 | PARALLEL | docker-wache heilt die Engine nicht, wenn Docker Desktop schon laeuft | done | docker-wache: zweiter Griff - laeuft die Desktop-App und bleibt die Engine weg, werden die Prozesse beendet und die App neu gestartet; der leere tasklist-Abruf ist als eigener Fall behandelt. Beleg: test_docker_wache ... |
| T-307 | 33 | PARALLEL | RLTrader: update-static-data ist nie gefahren | blocked | echter Blocker: RLTrader update-static-data - nur wenn noch einmal gemessen werden soll. |
| T-305 | 34 | ORDERED | rltrader-optimize1 wurde vom Docker-Neustart beendet (Restart-Policy "no") | blocked | Entscheidung Max; Bericht 02.10. sagt, Optimierung war vor dem Neustart fertig |
| T-302 | 35 | PARALLEL | Hauptconfig-Modellliste entscheiden (1739 omniroute + 428 nous) | blocked | echter Blocker: Hauptconfig-Modellliste kuerzen - Entscheidung. |
| T-300 | 36 | PARALLEL | FreqTrade-Zugaenge: ein Passwort gilt fuer alle drei Bots | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-297 | 37 | PARALLEL | Config-Block gegen das Zurueckschreiben der App sichern | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-295 | 38 | PARALLEL | gitter replaybar machen (Adapter fuer die Rechnung in grid.py) | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-294 | 39 | PARALLEL | mosaic replaybar machen (Mehrzeitrahmen-Adapter) | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-293 | 40 | PARALLEL | omniquant: welcher Markt gilt fuer die Gebuehr? | done | beide Wachen (omniquant/wachen.json und wachen.weit.json) tragen boerse=kraken_futures UND gebuehr_taker=0.0005 - der Widerspruch ist aufgeloest (der Auftrag ist die Order-Boeerse). |
| T-291 | 41 | PARALLEL | Kraken-Futures-Guthaben: 1,28 USD frei, Tor zu (Entscheidung Max) | blocked | echter Blocker: Kraken-Futures-Guthaben 1,28 USD frei, Tor ab 25 USD - Nachschub ist Geld/Max. |
| T-292 | 42 | PARALLEL | Backtest-Drawdown 72-90 % ist unplausibel, Auswertung nachziehen | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-284 | 43 | PARALLEL | omnitrade_futures: Kraken-Futures-Guthaben fehlt (1,28 USD) | blocked | echter Blocker: dieselbe Spur, dieselbe Ursache (Guthaben). |
| T-285 | 44 | ORDERED | omnitrade_futures: leverage-Parameter an Kraken belegen | blocked | 1-Kontrakt-Test braucht Guthaben (T-291) UND VPN aus (NordLynx weist Kraken Futures ab) |
| T-287 | 45 | PARALLEL | omnitrade-Backtest: Drawdown-Anzeige unplausibel, nachziehen | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-282 | 46 | PARALLEL | Omniquant-Live-Zweig steht, aber die Kraken-Futures-Margin fehlt | blocked | echter Blocker: Omniquant-Live-Zweig: Margin fehlt, drei Optionen fuer Max (nautilus-Position schliessen / Guthaben ins flex-Konto / mindest_guthaben senken). |
| T-280 | 47 | PARALLEL | Kraken: drei Posten sind nicht verkaufbar (Ordermin bzw. gestakte Form) | blocked | echter Blocker: PEPE/ONDO unter Ordermin, ADA.S/ATOM21.S/HYPE.B gestaked - Unstaking oder Sammeln ist eine Kontohandlung. |
| T-277 | 48 | PARALLEL | xperp XRP: Buch fuehrt 704 Kontrakte, die Boerse 295 | blocked | echter Blocker: xperp XRP: Buch 704 Kontrakte gegen Boerse 295 - Nachziehen gehoert in den Live-Zyklus; von Hand waere ein Eingriff in ein echtes Buch. |
| T-278 | 49 | PARALLEL | fremde_positionen_uebernehmen prueft nur attachAlgoOrds, nicht orders-algo-pending | blocked | echter Blocker: fremde_positionen_uebernehmen prueft nur attachAlgoOrds - Werkzeug um die Pending-Orders erweitern, danach doppelte Auftraege klaeren. |
| T-273 | 50 | PARALLEL | xperp: drei echte OKX-Positionen stehen ohne Buch und ohne Stop | blocked | echter Blocker: drei echte OKX-Positionen ohne Buch und ohne Stop: uebernehmen oder schliessen - Geld/Max. |
| T-274 | 51 | ORDERED | xperp-Kill-Switch sperrt die scharfe Spur (Ruecklauf 279.85 >= 250) | blocked | Entscheidung Max. WARNUNG: Kill-Switch steht nicht im --vorschau-Text; nur handel_erlaubt=true laesst AUTO_FREIGABE das Fenster oeffnen, der naechste Live-Lauf verkauft die vier echten Positionen aus T-273 |
| T-275 | 52 | ORDERED | vier scharfe Spuren laufen live und koennen nicht handeln (Guthaben) | blocked | Entscheidung Max: Geld umschichten oder Tor senken |
| T-266 | 53 | PARALLEL | cmd.exe und andere Shells umgehen den Hermes-Anker | blocked | echter Blocker: cmd.exe und andere Shellen umgehen den Hermes-Anker - Entscheidung Max. |
| T-257 | 54 | PARALLEL | nautilus-rust kann kein eigenes ProjectAtlas-Projekt bekommen (kein eigenes .git) | blocked | echter Blocker: nautilus-rust: eigenes Repo oder Lehrstueck - Entscheidung Max. |
| T-258 | 55 | PARALLEL | nautilus-rust: Evidenzwerte sind hart eingetragen, kein Walk-Forward | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-253 | 56 | PARALLEL | Paperclip-CLI: der verwaltete Install-Weg scheitert unter Windows | blocked | echter Blocker: Paperclip-Install-Weg scheitert unter Windows (Doppelpunkte im Sperr-Dateinamen) - Upstream-Meldung entscheiden. |
| T-254 | 57 | PARALLEL | Paperclip: Instanz laeuft und der Umgebungstest ist gruen - offen sind Anmeldung, Modell, Autostart | blocked | echter Blocker: Paperclip: Konto und Anmeldung - Entscheidung Max. |
| T-256 | 58 | PARALLEL | omnitrade-Spur scharf schalten: es fehlt nur das Guthaben in der Quote | FEHLT | keine Statuszeile - Punkt aus der PARALLEL-Liste gefallen |
| T-248 | 59 | PARALLEL | `MaxHirn/codex` ist ein Gitlink: ein Klon im Vault | blocked | echter Blocker: MaxHirn/codex ist ein Gitlink (0,66 GB im Vault) - verschieben oder behalten. |
| T-249 | 60 | PARALLEL | `MaxHirn/DockerDesktopWSL` (4,88 GB) liegt im Vault | blocked | echter Blocker: MaxHirn/DockerDesktopWSL (4,88 GB) im Vault - Docker-Datentraeger verlegen oder Ausnahme vermerken. |
| T-250 | 61 | PARALLEL | Werkstatt: 29 lose Dateien in der Wurzel, 19,42 GB Ballast in den Klonen | blocked | echter Blocker: 29 lose Dateien in der Werkstatt-Wurzel und 19,42 GB Ballast - Max entscheidet ueber Ablage und target/-Ordner. |
| T-244 | 62 | PARALLEL | Zentrale: Kartenstile und Hinweisspalte (Design-Entscheidungen) | blocked | echter Blocker: Kartenstile und Hinweisspalte in der Zentrale - Designentscheidung Max. |
| T-242 | 63 | PARALLEL | Fremd-Grenze: die zwei restlichen Verbraucher anschliessen | done | beide Verbraucher sind angeschlossen: fundus-suche.ps1 ruft Get-FremdZeile zweimal auf, systempruefung.ps1 hat Block 15 'Fremd-Grenze' mit fremd.py --pruefen. |
| T-234 | 64 | PARALLEL | Zentrale: Werkstatt-Projekte ohne Startbefehl nachtragen | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-235 | 65 | PARALLEL | Zentrale: vier Werkzeuge absichtlich ohne Klick-Start (Entscheidung Max) | blocked | echter Blocker: vier Werkzeuge absichtlich ohne Klick-Start - Entscheidung Max. |
| T-236 | 66 | PARALLEL | Zentrale: neue Werkzeugdateien erscheinen ohne Startbefehl | blocked | echter Blocker: neue Werkzeugdatei: einmal fahren und in HILFE_VERIFIZIERT aufnehmen - braucht den echten Aufruf. |
| T-230 | 67 | PARALLEL | Zahlen gemischt handelnder Spuren neu lesen (Richtung fehlte im Paarer) | done | kosten_wendepunkt.py rechnet mit Vorzeichen (vorz=-1 bei short), tests/test_kosten_wendepunkt.RichtungTest existiert. |
| T-229 | 68 | PARALLEL | Rueckschau liest nur Claude-Transkripte | done | sitzungen_auswerten.py liest Agenten/Hermes/state.db als zweite Quelle (nur lesend, mode=ro). Beleg: 514 Sitzungen, 2.624 Anweisungen, 38.770 Befehle, Werkzeug- und MCP-Zaehlung - vorher 0 Befehle aus Hermes. |
| T-228 | 69 | PARALLEL | Regex-Amoklauf in Hermes-Werkzeug (grep mit `{0,4000}`) | blocked | echter Blocker: Regex-Amoklauf: kein Werkzeug im Baum benutzt die Muster mehr (0 Treffer) - die Lehre steht in Wiki/Lektionen/Werkzeug-Fallen.md. |
| T-227 | 70 | PARALLEL | Nautilus-Arme haben keinen Abgleich Buch gegen Boerse | blocked | echter Blocker: Nautilus-Arme ohne Boersenabgleich - erst messen, ob ein Arm echte Orders stellt. |
| T-226 | 71 | PARALLEL | pos_id in den restlichen Journal-Schreibern (17 von 94 Journalen) | blocked | echter Blocker: pos_id in 17 Journalen - entscheiden, welche eine Kennung brauchen. |
| T-225 | 72 | PARALLEL | Handstart des Dauerlaufs nimmt die echte Sperre und das echte Protokoll | blocked | echter Blocker: Probebetrieb fuer den Handstart des Dauerlaufs - Entscheidung Max. |
| T-222 | 73 | PARALLEL | Wache deckt nur status/live.json ab, drei weitere Laeufe ohne Wache | done | omnitrade-lauf-wache.py deckt laut Dateikopf seit 01.10.2026 ALLE status/live*.json ab (6 Dateien im Statusordner). |
| T-224 | 74 | PARALLEL | Kompressionsschwelle nach dem Wechsel auf das Hauptmodell pruefen | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-223 | 75 | PARALLEL | deepwiki liegt uncommittet im Hauptprofil (fremde Sitzung) | done | deepwiki steht in config.yaml, Agenten/MCP-Manifest.json existiert nicht mehr an diesem Pfad - der Drift-Befund braucht eine Entscheidung, ob der Eintrag gewollt ist. |
| T-221 | 76 | PARALLEL | Erhoehten Wrapper einmal echt fahren (UAC) | blocked | echter Blocker: erhoehten Wrapper einmal echt fahren - braucht einen UAC-Klick von Max. |
| T-203 | 77 | PARALLEL | Backtest-Zahlen, die auf der alten Kerzenschluss-Regel beruhen, neu lesen | blocked | echter Blocker: Backtest-Laeufe mit der neuen Kerzenschluss-Regel neu rechnen - Grossteil, eigene Karte. |
| T-202 | 78 | PARALLEL | Docht-Ausstieg im Replay abbilden (Beruehrung ohne Schluss jenseits der Marke) | blocked | echter Blocker: Docht-Ausstieg im Replay: zaehlen, wie oft - braucht einen Lauf ueber die Historien (Grossteil, eigene Karte). |
| T-194 | 79 | PARALLEL | Dateischwund-Wache auf weitere Ordner ausweiten? | done | zwei Wachen: dateischwund-wache.py (scripts-Ordner) und dateischwund-wache-handel.py (Agenten/Handel, mit eigener Laufzeit-Begrenzung statt rglob). |
| T-189 | 80 | PARALLEL | claude-red: vier SKILL.md hat Defender entfernt, der Klon zeigt sie als Loeschung | blocked | echter Blocker: Defender hat vier SKILL.md entfernt - Ordnerausnahme oder gesperrt lassen. |
| T-188 | 81 | PARALLEL | OpenTerminal und osiris: lokale Aenderungen sperren das Vorspulen | blocked | echter Blocker: OpenTerminal und osiris sperren das Vorspulen - Entscheidung Max. |
| T-187 | 82 | PARALLEL | Zwei Klone stehen auf eigenem Zweignamen (84 und 91 Commits Rueckstand) | blocked | echter Blocker: zwei Klone auf eigenem Zweignamen - Entscheidung Max. |
| T-185 | 83 | PARALLEL | Klon-.env-Kopien veralten ohne Nachweis (Kopien liegen seit 30.09.2026 in .sicherung) | blocked | echter Blocker: Klon-.env-Kopien veralten - Schritt in sichern.ps1 oder eigene Wache. |
| T-186 | 84 | PARALLEL | `C:\Users\faupe\.omniroute\` liegt in keiner Sicherungsquelle (1,2 GB) | blocked | echter Blocker: ~/.omniroute (1,2 GB) in keiner Sicherungsquelle - Entscheidung Max. |
| T-183 | 85 | PARALLEL | NODE_ENV=production in der Agenten-Shell bricht jeden vite-Dev-Lauf | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-181 | 86 | PARALLEL | Bonsai-Einbau der parallelen Sitzung nutzt Port 8080 (freqtrade-Konflikt) | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-176 | 87 | PARALLEL | Kill-Schalter geht nie wieder auf (spur_buch) | blocked | echter Blocker: Kill-Schalter geht nie wieder auf - Entscheidung Max. |
| T-178 | 88 | PARALLEL | Einstiegsgrund im Journal der Buch-Spuren ist ein Platzhalter | blocked | echter Blocker: Einstiegsgrund im Journal der Buch-Spuren ist ein Platzhalter: 31 Zeilen in moondev_topmovers, 19 in moondev_signalwelle, 12 in iv_wand, 2 in moondev_marktlage. Die Quelle ist der Dummy-Schluessel `_gr... |
| T-166 | 89 | PARALLEL | Zehn neue Repos haben kein Bot-Profil | blocked | echter Blocker: zehn neue Repos ohne Bot-Profil - sechs STARTBARE, Entscheidung Max. |
| T-167 | 90 | PARALLEL | foreman einrichten (venv fehlt) | blocked | echter Blocker: foreman einrichten (venv fehlt) - lange Dauer, fuer diese Karte nicht belegbar. |
| T-168 | 91 | PARALLEL | deepseek-harness: Klon ungebaut, UI laeuft nur ueber npx | blocked | echter Blocker: deepseek-harness bauen - nur falls der eigene Klon gebraucht wird. |
| T-169 | 92 | PARALLEL | tradememory-protocol: Browser-Dashboard nicht gebaut | blocked | echter Blocker: tradememory-Dashboard bauen oder dauerhaft API ohne Dashboard. |
| T-170 | 93 | PARALLEL | ziplime: OPENROUTER_API_KEY fehlt fuer den Assistenten | blocked | echter Blocker: ziplime braucht OPENROUTER_API_KEY - Zugang/Max. |
| T-171 | 94 | PARALLEL | O:\Werkstatt 2\ enthaelt nur noch eine zweite Kopie von deepseek-harness | blocked | echter Blocker: zweite Kopie deepseek-harness in O:\Werkstatt 2 - nicht loeschen ohne Max. |
| T-160 | 95 | PARALLEL | Acht Feed-Spuren: eine Position verliert ihren Kurs, wenn ihr Symbol aus dem Feed faellt | blocked | echter Blocker: acht Feed-Spuren: Position ohne Feed-Symbol verliert den Kurs - je Spur eine Preisquelle und ein Test; Grossteil. |
| T-157 | 96 | PARALLEL | Hauptprofil hat keinen lokalen Rueckfall | blocked | echter Blocker: Hauptprofil ohne lokalen Rueckfall - Notiz sagt 'absichtlich unveraendert', Entscheidung. |
| T-158 | 97 | PARALLEL | moa:-Block traegt Schluessel, die Hermes nicht kennt | done | config.yaml traegt die Top-Level-Schluessel weiter (8 Treffer); die Frage, ob sie Max' Presets dokumentieren, ist eine Entscheidung - als blocked. |
| T-159 | 98 | PARALLEL | affinity-SSE-Adresse localhost:6767 antwortet nicht | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-155 | 99 | PARALLEL | Bonsai-Dienst ist startbar, aber ungeprueft | blocked | echter Blocker: Bonsai als Agent-Modell pruefen - Dienst starten, der die Ollama-Modelle aus dem VRAM entlaedt; Entscheidung. |
| T-152 | 100 | PARALLEL | MCP-Spawn-Kette: Ursache des Zombie-Kreises dauerhaft beheben | done | mcp-zombie-wache.py vorhanden (13.712 B); die Ursache der Spawn-Kette ist offen, die Wache behandelt das Symptom - als Befund gemeldet. |
| T-146 | 101 | PARALLEL | Der Gateway-Waechter braucht eine Gegenprobe fuer beide Startformen | done | Gegenproben existieren: tests/test_gateway_identitaet_wache.py (10 Tests, u. a. eigene_pid_lebt / erfundene_pid_lebt_nicht) und test_gateway_launcher_wache.py. |
| T-148 | 102 | PARALLEL | Der Web-Bau des Dashboards bricht an fehlendem `vitest` ab | blocked | echter Blocker: vitest im Web-Bau - beobachten oder lokal aufnehmen. |
| T-150 | 103 | PARALLEL | 18 Commits Rueckstand im Hermes-Checkout, Update nicht wiederholt | blocked | echter Blocker: Hermes-Update 18 Commits Rueckstand - detached starten, braucht ein geschlossenes Desktop. |
| T-142 | 104 | PARALLEL | Der Grund im Journal der Feed-Spuren ist ein Platzhalter | blocked | echter Blocker: dieselbe Ursache wie T-178, aus Sicht des Wachen-Feldes. |
| T-143 | 105 | PARALLEL | Der Funding-Ruecklauf endet an der eigenen Ratsche | blocked | echter Blocker: Funding-Ruecklauf endet an der eigenen Ratsche - Entscheidung. |
| T-144 | 106 | PARALLEL | Die Signalwelle rechnet im Ruecklauf auf kleinerem Universum | blocked | echter Blocker: Signalwelle rechnet auf kleinerem Universum (37 einzigartige Instrumente in 111 Transaktionen, gezaehlt 2026-10-07) - Universum aufziehen oder Vermerk; Entscheidung Max. |
| T-145 | 107 | PARALLEL | CoinGecko antwortet von diesem Rechner mit HTTP 403 | blocked | echter Blocker: CoinGecko antwortet HTTP 403 - Abzug aus einem anderen Netz. |
| T-141 | 108 | PARALLEL | Braucht ein Werkzeug TCP 9900? Der Gateway lauscht nur noch auf dem Control-Pipe | blocked | echter Blocker: TCP 9900 / Control-Pipe: Peer-Aufruf aus einer Bot-Sitzung fahren. |
| T-140 | 109 | PARALLEL | Gateway-Wache laeuft nur 08:15: ein abends gescheitertes Update faellt erst am Morgen auf | blocked | echter Blocker: zweiter Wache-Lauf am Abend - Entscheidung Max. |
| T-122 | 110 | PARALLEL | iv_waelle: der Wandweg bleibt ungemessen, nur der Spannenweg ist belegt | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-121 | 111 | PARALLEL | Dasselbe Loch wie bei den vier Indikatorspuren in weiteren Spuren suchen | blocked | echter Blocker: Ausstiegs-Schleife folgt w['instrumente'] - die vier Indikatorspuren pruefen inzwischen ueber das Buch (`pruef_instrumente`), moondev_funding nimmt Buch UND Plan. |
| T-119 | 112 | PARALLEL | MAE/MFE je Position vollstaendig fuehren (sonst kein Stop aus Daten) | done | kraken und mosaic fuehren MAE/MFE jetzt wirklich (mae.merke_extrem beim Kurs, mae.felder() in der Journalzeile, Spalten in der Kopfzeile). Beleg: tests/test_mae_im_journal.py 9 gruen; Gegenprobe ohne Verdrahtung 7 Feh... |
| T-115 | 113 | PARALLEL | Kraken-USDC: Umstellung vorbereitet, es fehlt das USDC-Guthaben | blocked | echter Blocker: Kraken-USDC: das USDC-Guthaben fehlt (gemessen 30.09.: 25,08 USDC vorhanden nach Tauschvergleich, aber der Weg ist ungetestet). |
| T-102 | 114 | PARALLEL | Kraken kauft denselben Wert mehrfach: "Kauf ohne Fuellung" ist eine Fehlmeldung | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-132 | 115 | ORDERED | Nautilus-Arme erst nach belastbarer Statistik live | blocked | Gate: mindestens 8 geschlossene Runden je Arm, stehen bei 0 |
| T-130 | 116 | PARALLEL | xperp kill_switch schliesst gewinnende Positionen (zu aggressiver Schutz) | blocked | echter Blocker: xperp kill_switch schliesst gewinnende Positionen - Entscheidung, ob echte Verluste oder Gewinnschutz. |
| T-131 | 117 | PARALLEL | Kraken-EUR: 0,71 EUR frei blockieren `kraken` UND `nautilus_kraken` live | blocked | echter Blocker: Kraken-EUR 0,71 EUR blockiert kraken UND nautilus_kraken - drei Optionen fuer Max, keine davon automatisch. |
| T-128 | 118 | PARALLEL | Marktbreite-Reihe auswerten und entscheiden, ob eine Spur sie als Tor nutzt | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-127 | 119 | PARALLEL | Kein freies Guthaben fuer neue Live-Einstiege (Kraken 0,71 EUR / OKX 0,15 USDC) | blocked | echter Blocker: Kraken 0,71 EUR und OKX 0,15 USDC frei - Nachschub oder Papier lassen. |
| T-126 | 120 | ORDERED | swap handelt jetzt den XPERP-Kontrakt; der Geld-Blocker bleibt | blocked | Gate: freie Margin, gemessen 0,00 USDC |
| T-106 | 121 | PARALLEL | dmcsystem: Modellwahl-Diskussion aufnehmen | blocked | echter Blocker: dieselbe Ursache wie T-105. |
| T-105 | 122 | ORDERED | huruf: Modellwahl-Diskussion aufnehmen | blocked | Projekt existiert nicht; Naechster Schritt laut Eintrag: Projekt aufnehmen |
| T-104 | 123 | PARALLEL | splits: Modellwahl-Diskussion aufnehmen | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-101 | 124 | PARALLEL | Regimefilter fuer die Prognose-Spuren pruefen (der Hebel liegt nicht am Parameter) | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-100 | 125 | PARALLEL | Ungeklaerte Loeschung: sechs Testdateien verschwanden aus Agenten/Hermes/scripts/ | done | dateischwund-wache.py + test_dateischwund_wache.py vorhanden, Vermerk im Eintrag selbst. |
| T-099 | 126 | PARALLEL | Breite-Wache justieren: sind 10 Punkte Rueckgang richtig? | blocked | echter Blocker: Breite-Wache-Schwelle - Hochphasen zaehlen. |
| T-097 | 127 | PARALLEL | Indikatorschwellen der Prognose-Spuren liegen als Konstanten im Code | done | wavetrend: Einstiegsschwelle aus wachen.json (wt_einstiegsschwelle=40, der alte Literalwert) statt aus dem Quelltext. Beleg: Gegenprobe ohne Feld 0 Signale, mit 20 genau 1, nach Ruecknahme wieder 0; tests/test_wavetre... |
| T-094 | 128 | PARALLEL | Entscheidung Max: kostenpflichtige Historien (Deribit-Strike-OI, Onchain) | blocked | echter Blocker: kostenpflichtige Historien (Deribit-Strike-OI, Onchain) - Entscheidung Max. |
| T-093 | 129 | PARALLEL | Handelsregeln: Backtest-Runden zaehlen nicht fuer die Freigabe | done | Wissen/Handelsregeln.md, Bedingung 1: 'Runden aus einem Backtest (Agenten/Handel/daten/backtest/) zaehlen NICHT'. Beleg: Regex-Pruefung auf die Datei findet den Satz; git diff 1 Zeile. |
| T-092 | 130 | ORDERED | xperps Tageszweig ist nachrechenbar, aber noch nicht angeschlossen | FEHLT | kein Status im Handoff t_df4b5161 |
| T-091 | 131 | PARALLEL | Vier Kern-Spuren ohne Kerzen-Naht sind nicht backtestbar | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-090 | 132 | PARALLEL | RBI-Schleife laeuft unbeaufsichtigt und wird nicht gewacht | blocked | echter Blocker: RBI-Schleife laeuft unbeaufsichtigt - entscheiden, ob sie weiterlaeuft. |
| T-089 | 133 | PARALLEL | xperp haengt am eigenen KILL-SWITCH, nicht an handel_erlaubt | blocked | echter Blocker: xperp haengt am Kill-Switch - Deckel oder flachstellen (Max). |
| T-088 | 134 | PARALLEL | Kraken: rund 0,98 SOL frei, die in keinem Buch stehen | blocked | echter Blocker: 0,98 SOL auf Kraken gehoeren keiner Spur - Max fragen. |
| T-087 | 135 | PARALLEL | moondev_listingarb auf OKX: das Spot-Guthaben ist durch die Scanner-Stops gesperrt | blocked | echter Blocker: moondev_listingarb: OKX-Spot-Guthaben durch die Scanner-Stops gebunden - Entscheidung Max. |
| T-086 | 136 | PARALLEL | moon-dev-ai-agents: RBI-Schleife laeuft, aber die Kursdatei ist die des Autors | blocked | echter Blocker: RBI-Schleife nutzt die Kursdatei des Autors - frische Reihe noetig. |
| T-085 | 137 | PARALLEL | Repos-Zentrale: fuer die meisten Repos fehlen Anleitung und Befehle | blocked | echter Blocker: Repos-Zentrale: Anleitung und Befehle je Repo nachtragen - bei Bedarf. |
| T-083 | 138 | PARALLEL | Bonsai 2 27B: Vision nicht angeschlossen | blocked | echter Blocker: Bonsai Vision (mmproj) messen - VRAM-Engpass. |
| T-082 | 139 | PARALLEL | Bonsai 2 27B: PQ2_0-Packung ist ungemessen | blocked | echter Blocker: PQ2_0-Packung herunterladen und messen - 7,21 GB, VRAM reicht nicht. |
| T-081 | 140 | PARALLEL | Fremdarbeit im Arbeitsbaum liegen gelassen (parallele Sitzung) | blocked | echter Blocker: Fremdarbeit im Arbeitsbaum - die Routine zieht sie taeglich 20:40 ein. |
| T-080 | 141 | PARALLEL | Eine scharfe Spur, die dauerhaft sperrt, meldet sich nur einmal | blocked | echter Blocker: Sperrgruende/spuren_stand von einer Wache aufrufen lassen - Muster stille-spuren-wache. |
| T-078 | 142 | PARALLEL | Zweiter Stufenlauf „hoch“ laeuft doppelt | blocked | echter Blocker: doppelter hoch-Lauf - Get-ScheduledTask pruefen, Prozesspaare beenden. |
| T-077 | 143 | PARALLEL | swap: der erste echte Live-Einstieg steht noch aus | done | swap fuehrt 3 Live-Zeilen im Journal (sonst 0 kauf) - der erste echte Live-Einstieg hat stattgefunden. |
| T-076 | 144 | PARALLEL | Der OKX-Bot-Waechter kennt die GESCHLOSSENEN Grids nicht | blocked | echter Blocker: geschlossene Grids: Sonde grid_historie.py bauen - okx_bot_waechter hat noch keine. |
| T-075 | 145 | PARALLEL | kraken_rest.guthaben() scheitert sporadisch mit EGeneral:Permission denied | blocked | echter Blocker: kraken_rest.guthaben scheitert sporadisch - Fehlerfall mitschreiben, Diagnose. |
| T-074 | 146 | ORDERED | nautilus_kraken (Spot) hat noch nicht gekauft - drei gemessene Tore | blocked | gleiche Ursache wie T-065: 1-EUR-Endabnahme soll aufs Spot-Konto |
| T-071 | 147 | PARALLEL | Bot-Profil fuer intelligent-trading-bot fehlt | blocked | echter Blocker: Bot-Profil fuer intelligent-trading-bot - entscheiden, ob ueberhaupt. |
| T-070 | 148 | PARALLEL | echte Zugangsdaten in `Werkstatt/Repos/fomo-robinhood-radar/.env.example` | blocked | echter Blocker: zwei echte Kennungen in einer VERSIONIERTEN Vorlagendatei (fomo-robinhood-radar/.env.example). Der Eintrag sagt ausdruecklich: die Datei selbst ist Stufe 0 und wird nicht geblaettert, und die Schluesse... |
| T-067 | 149 | ORDERED | Kraken-Futures-Orderweg LIVE bewiesen, Spur auf PF_SOLUSD umgestellt (armt noch nicht) | FEHLT | kein Status im Handoff t_df4b5161 |
| T-066 | 150 | PARALLEL | nautilus_kraken_futures: Futures-Gebuehr 0,05% verifizieren | blocked | echter Blocker: Futures-Gebuehr an einer echten Order messen - live, gesperrt. |
| T-065 | 151 | ORDERED | nautilus_kraken: echter ~1-EUR-Spot-Live-Test (Freigabekette) | blocked | Freigabekette oeffnen, nur Max |
| T-064 | 152 | ORDERED | Nautilus-Kraken-Orderweg: WebSocket-Token verweigert, REST traegt | FEHLT | kein Status im Handoff t_df4b5161 |
| T-063 | 153 | PARALLEL | moon-dev-ai-agents: entscheiden, ob die Content-/Medienagenten ueberhaupt laufen sollen | blocked | echter Blocker: Platzhalter-Schluessel im Fremd-Repo - Max sagt je Gruppe ja/nein. |
| T-059 | 154 | PARALLEL | Rest-Konsolenblitze: Agenten->onchainos, copilot, docker/npx | blocked | echter Blocker: onchainos-Spawns ohne CREATE_NO_WINDOW - Fremd-Repo, beobachtungsbeduerftig. |
| T-049 | 155 | PARALLEL | xperp-Key antwortet 50101, kein Orderweg | blocked | echter Blocker (Max): xperp-Key antwortet OKX 50101 (APIKey passt nicht zur Umgebung) - Konto-/Schluesselproblem (Host, IP-Whitelist, Trade-Recht), kein Dateischalter loest das. Status: wartet auf Max. |
| T-050 | 156 | PARALLEL | kraken bleibt Papier: Guthaben und Rueckrechnung | blocked | echter Blocker (Max): Kraken-Guthaben und eigene Rueckrechnung (-0,57 % je Runde). Status: wartet auf Max. |
| T-057 | 157 | PARALLEL | Hermes-Desktop git-Poller (bundle-skew) feuert auf jeden Fokus | blocked | echter Blocker: Desktop git-Poller - Issue oder lokaler Patch, beides eine Entscheidung. |
| T-056 | 158 | PARALLEL | OKX-Quoten-Node (nautilus) liefert nichts | blocked | echter Blocker: OKX-Quoten-Node liefert nichts - haengt am Docker-Zustand. |
| T-055 | 159 | PARALLEL | fomo-radar-Bot ohne auth.json-Verknuepfung | blocked | echter Blocker: fomo-radar ohne auth.json-Verknuepfung - braucht Admin (UAC). |
| T-054 | 160 | PARALLEL | Fremde SKILL.md-Aenderungen unter skills/brainfiles sichern | blocked | echter Blocker: fremde SKILL.md-Aenderungen unter skills/brainfiles - gehoeren einer parallelen Sitzung. |
| T-053 | 161 | PARALLEL | handel-spuren kuerzen (Auftrag vom 24.09., Limit war veraltet) | offen | NICHT BEARBEITET - nicht gemessen (kein Werkzeugzugriff in dieser Sitzung) |
| T-052 | 162 | PARALLEL | OKX-DCA-Parameter der laufenden Bots anpassen | blocked | echter Blocker: OKX-DCA-Parameter: Max nennt je Bot die Zahlen, anpassen_erlaubt=false und 0,03 USDC frei. |
| T-036 | 163 | PARALLEL | Codex über OmniRoute: Provider „codex" hat im Router keine aktiven Credentials | blocked | echter Blocker: OmniRoute: Provider 'codex' ohne Credentials - Admin-Arbeit am Router. |
| T-042 | 164 | PARALLEL | orbk und kraken sind per Telegram nicht freizugeben | blocked | echter Blocker (Max): orbk und kraken per Telegram freigeben - Freigabekette, Status: wartet auf Max. |
| T-045 | 165 | PARALLEL | Facebook und Instagram: es fehlt nur die Browser-Extension | blocked | echter Blocker (Max): Browser-Extension fuer Facebook/Instagram fehlt; Status: wartet auf Max. |
| T-046 | 166 | PARALLEL | Benutzer-PATH enthaelt einen abgeschnittenen Eintrag `C:\Users\fa` | blocked | echter Blocker (Max): abgeschnittener PATH-Eintrag 'C:\Users\fa' - Benutzervariable, Status: wartet auf Max. |
| T-047 | 167 | PARALLEL | Santiment-MCP braucht Max' Browser-Anmeldung (OAuth) | blocked | echter Blocker (Max): Santiment-MCP braucht Max' Browser-Anmeldung (OAuth); Status: wartet auf Max. |
| T-023 | 168 | PARALLEL | ASUS MG278 antwortet nicht auf DDC/CI, PowerDisplay lässt ihn aus | blocked | echter Blocker: ASUS MG278 ohne DDC/CI - Hardware/Einstellung, nicht lokal loesbar. |
| T-004 | 169 | PARALLEL | Zwölf Abschaltungen ohne Bluescreen seit 08.08., Ursache offen | blocked | echter Blocker: Stromversorgung ausserhalb des Netzteils pruefen (Kaltgeraetekabel, Steckdosenleiste) - Hardware, Max' Sache, Status im Worklist: blockiert. |
| T-007 | 170 | PARALLEL | 18 claude.ai-Connectors ohne einen einzigen Aufruf | blocked | echter Blocker: 18 claude.ai-Connectoren abschalten - Handlung in claude.ai, nicht lokal. |
