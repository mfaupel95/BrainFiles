# Einen FREM DEN Lauf spiegeln (Weg B, omnitrade 30.09.2026)

Muster fuer: "nur noch <Fremdprogramm> darf auf <Boerse> handeln" - der
Fremdlauf bleibt der Entscheider, der Haus-Orderweg fuehrt aus. Gebaut als
`Agenten/Handel/omnitrade` (Spiegel der Rust-Laeufe in `Werkstatt/omnitrade`).

Gilt fuer jeden Fremdlauf, der einen ZUSTAND in einer Datei hinterlaesst:
Rust-CLI, Fremd-Bot, MCP-Server, On-Chain-Sammler.

## 0. Zuerst die Auftragsseite pruefen - Sperre ist kein Umzug

Belegt: Max ordnete "nur noch omnitrade auf kraken handel erlaubt" an. Umgesetzt
war nur die SPERRSEITE (vier Spuren auf `handel_erlaubt=false`, eine auf
`boersen: ["okx"]`, alle aus `dauerlauf.AUTO_FREIGABE`). Die Freigabeseite fehlte:
`omnitrade-exchange/src/` kennt nur `binance` und `okx`, `live.rs:33` weist jedes
andere `--exchange` ab. **Danach handelte NIEMAND auf der Boerse.**

- Vor dem Bauen pruefen, ob der Nachfolger die Boerse ueberhaupt kennt
  (Befehlsparser, Adapter-Ordner, `grep -r <boerse> <fremdrepo>/src`).
- Steht in der Antwort "umgestellt", obwohl nur gesperrt wurde, erwartet Max
  Orders, die nicht kommen. Das gehoert woertlich in den Bericht.

## 1. Weg waehlen: Adapter im Fremdcode oder Haus-Spur?

| | A: Adapter im Fremd-Repo | B: Haus-Spur spiegelt (gewaehlt) |
|---|---|---|
| Schluessel | zweiter Satz noetig | der vorhandene Haus-Weg |
| Nonce | eigener Zaehler, kollidiert mit dem Haus-Pool | Haus-Pool |
| Preisregeln/Stops/Beleg | in Fremdsprache neu bauen | schon da |
| Risiko | Fremdbaum wird veraendert | Fremdbaum bleibt unberuehrt |

Entscheidungsregel: **der Fremdlauf liefert die ENTSCHEIDUNG, das Haus die
ORDER.** Weg A nur, wenn der Fremdlauf zwingend selbst ordern muss (eigener
Prozess ohne Datei-Zustand).

## 2. Das fremde Statusdokument lesen, nicht erfinden

Erst die Quelle im Fremd-Code lesen (hier `omnitrade-cli/src/status.rs`), dann
bauen. Was dort steht, entscheidet den ganzen Aufbau:

* `state`: `starting` / `running` / `stopped` / `error`
* `net_quantity`: Netto-Menge (buy positiv, sell negativ) - **der Zustand**
* `recent_orders`: **Ringpuffer** (`MAX_ORDERS = 20`) mit
  `{time_ms, side, quantity, price, outcome, detail}`
* `last_close`, `recent_candles`, `orders_placed`, `orders_rejected`,
  `last_error`, `pid`, `updated_ms`, `symbol`, `script`

Drei Regeln, die daraus folgen:

1. **Den ZUSTAND spiegeln, nicht die Orderliste.** Ein Ringpuffer verliert bei
   einem Ausfall alles dazwischen; wer daraus Ereignisse nachzaehlt, verpasst
   sie still. `net_quantity > 0` sagt zu jedem Zeitpunkt, ob eine Position steht.
2. **`state: running` ist kein Beweis - zwei Zeugen, und der zweite braucht
   einen NAMEN.** Nach einem harten Ende bleibt die Datei auf `running` stehen.
   Einstieg nur bei frischer Datei UND lebender PID - aber **"die PID lebt"
   allein genuegt NICHT**: Windows vergibt PIDs neu. Gemessen: die Statusdatei
   trug `running` mit PID 2024, die inzwischen `csrss.exe` gehoerte; der Lauf war
   4,5 Stunden tot, und das Startwerkzeug meldete "laeuft schon", weil es nur
   die PID-Existenz prueefte. Die Prozessabfrage muss den PROGRAMMNAMEN
   mitverlangen (`pid_lebt(pid, name="<fremdprogramm>.exe")`, Name aus der
   `tasklist`-Ausgabe) - sonst haelt jede Wache eine Wiederverwendung fuer einen
   lebenden Lauf. Gegenprobe im Test: die eigene PID mit falschem Namen muss
   `False` ergeben.
3. **Den echten Orderpreis buchen, nicht den letzten Kerzenschluss.** Der
   Ausstieg des Fremdlaufs ist eine echte Order; ihr Preis steht in
   `recent_orders`. `last_close` als Verkaufskurs ins Journal zu schreiben,
   erfindet einen Kurs.

## 3. Bauen - vier Dateien

| Datei | Inhalt |
|---|---|
| `lesen.py` | Statusdateien lesen, Symbol zerlegen, zwei Zeugen. Rein lesend, wirft nie. |
| `handeln.py` | `quelle(w)`, `signal(d, w)`, `ausstieg_grund(p, w)`, `boerse_binden(w)`; ruft `spur_buch.zyklus`. |
| `wachen.json` | Grenzen inkl. `boerse`, `kraken_quote`, `guthaben_waehrung`, `mindest_guthaben`, `live_*` |
| `tests/test_<spur>.py` | Attrappen-Statusordner + Seams + Modulwaechter |

Die tragenden Entscheidungen:

* **Ausstieg ueber `zusatz_ausstieg`.** `spur_buch.zyklus(..., zusatz_ausstieg=fn)`
  fragt `fn(position, wachen)` NACH Stop und Ziel; der Fremdlauf ist die
  fuehrende Ausstiegslinie (`omnitrade flat`), der Stop ist der NOTAUS (weit,
  hier 8 %) und das Ziel absichtlich unerreichbar (10R) - sonst bucht die Spur
  Runden, die der Fremdlauf nie genommen haette.
* **Ausstieg auch bei `stopped`** (die CLI verkauft beim Beenden), **nie bei
  `starting`/`error`** - ein Abbruch ist kein Handelssignal.
* **Ein Test-Seam je Aussenwelt:** `lebt_override` (Prozessabfrage) und
  `lage_override` (Statusdateien). Ohne sie haengt jeder Test an einer echten PID.

## 4. Verdrahten - sechs Listen, alle sechs

Jede Liste, die eine Spur nennt, altert still. Alle sechs nachziehen und danach
gegenproben:

1. `dauerlauf.SPUREN` (Ordner + `skript`)
2. `lage.spur_<name>()` **und** der Eintrag in `lage.HOLER`
   (`live_faehig=True`, wenn ein Live-Zweig existiert - sonst meldet der Bericht
   "kein Live-Zweig (Papierpfad)")
3. `auswertung_alle.BOT_SPUREN` (bzw. die passende Familie)
4. `pruefe_ratschen.py` - `(spur, ordner, "scanner", "wachen_pruefung")`
5. `befehle.FAMILIE` - sonst faellt `test_befehle` rot
6. `.gitignore`-Whitelist: `!<spur>/*.py`, `!*.md`, `!wachen.json`,
   `!tests/*.py` plus Sperren fuer `zustand.json`/`handelsjournal.csv`

Gegenproben: `git check-ignore -v <pfad>` (nennt die greifende Regel) UND
`git add --dry-run <ordner>` (zeigt, was wirklich in den Commit kaeme).

## 5. Beweisen

```
cd Agenten/Handel/<spur> && MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe handeln.py --vorschau
cd Agenten/Handel && ./scanner/.venv/Scripts/python.exe spiegelstand.py
cd Agenten/Handel && ./scanner/.venv/Scripts/python.exe pruefe_ratschen.py
```

* Vorschau nennt GENAU die Sperrgruende (handel_erlaubt, freigabe, Fenster,
  Guthaben) - nur so kann `dauerlauf.nur_fenster_fehlt` sie lesen.
* Ein echter Papierzyklus schreibt `zustand.json` und spiegelt nach
  `Q:\Handel_Journal\<spur>`; `spiegelstand.py` muss byte-gleich melden.
* Der Dauerlauf liest `SPUREN` beim START: **die neue Spur erscheint erst nach
  einem Neustart des Dauerlaufs** - alle Stufen (Basis/mittel/hoch) einzeln.
  Beleg: `<spur> (papier) ok` im `dauerlauf.log` JEDER Stufe.

## 6. Fallen (alle in dieser Reihenfolge erlebt)

* **`spur_buch.zyklus` steigt bei LEEREN Daten VOR `pruefe_ausstiege` aus.**
  Liefert `quelle()` nur laufende Laeufe, kann ein beendeter Lauf die Position
  nie schliessen. Deshalb kommen ALLE lesbaren Laeufe ins `daten`-Dict und
  `signal()` prueft `laeuft` UND `offen`.
* **Eine unendliche Altersgrenze schaltet den einen Zeugen ab.** Ein Start-/Wach-
  Werkzeug, das `beurteile(lage, veraltet_s=float("inf"))` aufruft, prueft nur
  noch Zustand und PID - eine tagealte Statusdatei gilt dann als laufend und der
  tote Lauf wird nie neu gestartet. Die Altersgrenze gehoert aus dem
  Kerzenabstand der Datei (`bruecke.altersgrenze_s`) gerechnet, nicht auf `inf`
  gesetzt; wer sie aufheben will, muss den Grund im Code nennen.
* **Die Quotewaehrung vor der ersten Sperrenpruefung setzen**
  (`boerse_binden(w)` -> `weg.setze_quote(w["kraken_quote"])`): mit der Vorgabe
  EUR findet die Paar-Tabelle ein USDC-Paar nicht, und sie faellt ausdruecklich
  nicht auf eine andere Waehrung zurueck - sonst landet die Order im falschen Markt.
* **Normalisiertes Dict gegen rohes Dict.** `positionen_der_spur()` liefert
  `instrument`/`wert_usd`; `inst`/`nominal` gibt es nur im ROHEN Positions-Dict.
  Wer `instrument_name(p)` auf das normalisierte anwendet, zeigt eine Spalte
  voller Fragezeichen.
* **Naive und aware Zeitstempel mischen sich nicht.** Die Spur schreibt
  `letzter_lauf` als UTC-ISO (`+00:00`); `alter_minuten()` rechnet damit. Ein
  naives `datetime.now()` laeuft in `TypeError: can't subtract offset-naive and
  offset-aware datetimes`.
* **Doppelte JSON-Schluessel beim Einfuegen:** der LETZTE gewinnt. Nach jedem
  Einfuegen `json.loads` laufen lassen, nicht den eingefuegten Text ansehen.
* **Fuzzy-Patch-Treffer pruefen:** ein Tippfehler im Ersatztext (Pfad
  `Handel\Journal` statt `Handel_Journal`) wird angenommen und landet in der
  Datei. Nach jedem JSON-Patch den Wert per `read_file` nachsehen.
* **Erst messen, dann zaehlen:** die Spurenzahl nicht aus einer Notiz
  uebernehmen ("39 + 1 = 40" war falsch). `python -c "import dauerlauf;
  print(len(dauerlauf.SPUREN))"` - oder den Fenstertitel lesen, der sie nennt.
