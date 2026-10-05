# Plan: FOMO / Copy-Trading auf Solana (Papier zuerst)

Stand 12.09.2026. Auftrag: Max, `/plan fomo krypto copy Trade bot`, zu einer
vorgelegten Anleitung (Telegram-Bots „Mofo Bot" / „Copy Fomo Bot", Wallet per
Bot, PIN, SOL einzahlen, Top-Trader spiegeln).

Dieser Plan ist ein Dokument. Es wird nichts gebaut, nichts gekauft, kein
Schluessel angelegt.

## Kurzurteil

**Den vorgelegten Weg nicht gehen.** Ein Bot, der die Wallet erzeugt, ist der
Verwahrer des Geldes: Wer die Adresse generiert, hat den Schluessel. Wer den
Schluessel hat, kann alles damit tun - und muss dafuer weder Vertrag noch
Haftung noch Rechenschaft vorlegen. Das widerspricht der Hausregel, nach der
Zugangswerte in `Wissen/Zugaenge.md` und in eigenen Haenden liegen, und es
widerspricht Punkt 3 der Handelsregeln: scharf geschaltet wird von Hand, an
einem Fenster, das die Grenzen aus `wachen.json` zeigt.

**Stattdessen: eine Papierspur „spiegel"**, die derselben Frage nachgeht
(welche Wallets lohnen sich, wenn man sie nachahmt?) mit Werkzeugen, die hier
schon installiert sind, eigenen Schluesseln, ohne Orderpfad - und mit demselben
Tor wie jede andere Spur: 6 Wochen, 50 Runden, netto positiv **nach** Gebuehren,
Slippage und Funding, bevor ueberhaupt Geld bewegt wird (Handelsregeln,
Bedingung 1).

## Was am vorgelegten Weg nicht traegt

| Punkt der Anleitung | Befund |
|---|---|
| „Der Bot generiert eine Solana-Wallet fuer dich" | Der Bot haelt den Schluessel. Kein Selbstverwahrungs-Weg, kein Ausweg, wenn er verschwindet. |
| „PIN im Bot einrichten" | Eine PIN im Telegram-Chat schuetzt gegen fremde Mitleser, nicht gegen den Betreiber. |
| „SOL an die Adresse ueberweisen" | Auszahlung ist Vertrauenssache - und bei Betreiber-Wechsel unumkehrbar. |
| „Top-Trader aus dem Leaderboard" | Eine Rangliste belohnt Vergangenheit. Der Edge der Spitze ist meist *fruh* in einem Launch zu sein; wer nachkauft, ist die Gegenpartei. |
| `[1, 2, 3]`-Belege im vorgelegten Text | Nicht aufloesbar: keine Quelle, kein Datum, kein Autor. Der Text ist nicht zitierfaehig. |
| „Mofo Bot" / „Copy Fomo Bot" | Auffindbar nur ueber Werbevideos (u. a. ein YouTube-Titel „How To Copytrade FOMO like a millionaire (MoFo Bot)"). Kein geprueftes Produkt, keine Audit-Spur. |

Zur Plattform selbst, damit nichts verwechselt wird: **fomo.family existiert**
(„social-first trading app", memecoins, Leaderboard, Feed, Alerts, Copy Trading,
gasless, Apple-Pay-Aufladung, Eigenangabe 500.000 Trader). Copy Trading ist dort
**in der App** eingebaut - dafuer braucht es keinen Telegram-Bot. Die 20
deutschen „Antworten"-Seiten der Seite sind SEO-Text, keine Belege.

## Was hier schon steht

- **`okx-dex-market`** (installiert, nur lesend): Top-Trader-Rangliste,
  Smart-Money-/KOL-Feed, eigene und fremde **Wallet-PnL**, Token-Risiko
  (Rug-Anteil, Halter-Klumpen), Bundle-/Sniper-Erkennung, pump.fun-Neulaunch-Scan
  und ein WebSocket-Monitor fuer Echtzeit-Signale.
- **`okx-agentic-wallet`** (`onchainos`): Bestand, Senden, Tauschen, Signieren -
  mit der bestehenden Politik aus `Wissen/Verbindungen.md` (50 USD je
  Transaktion, kein Auszahlungsrecht).
- **Regelwerk**: `Wissen/Handelsregeln.md` (fuenf Bedingungen, Punkt 3),
  `Wissen/Schutzregeln.md` (Stufen), Spuren-Muster `Agenten/Handel/handel-spuren`
  (Skill) und die eben fertiggestellte Spur `Agenten/Handel/swap/` als Vorlage.

Der Vault enthaelt zu FOMO, Copy Trading oder Solana-Memecoins bis jetzt
**nichts** (nur Solana-Adressen im OnChainOS-Backup und die USDG-Ausnahme).

## Ziel des Plans

Eine Spur, die auf dieselbe Frage eine pruefbare Antwort gibt - ohne dass je
ein fremder Schluessel ins Spiel kommt:

> Wenn ich die Signale der besten Solana-Wallets mit 50 USD je Position und
> meinen eigenen Grenzen nachgeahmt haette: Was haette das nach Gebuehren,
> Slippage und Fehlschlaegen gekostet oder eingebracht?

## Bauplan

Neue Spur `Agenten/Handel/spiegel/`, Muster: `swap/` (papierfest, eigene Wachen,
eigene Tests, eigenes Journal).

1. **Leseprobe (kein Code, nur Nachsehen).** `onchainos` Preflight
   (`okx-agentic-wallet/_shared/preflight.md`), dann Top-Trader-Rangliste und
   Smart-Money-Feed abfragen: 20 Wallets mit PnL, Trefferquote, Alter,
   Handelszahl, Kette. Ergebnis als Liste mit Stand und Quelle.
   **Abbruchpunkt:** Deckt der Feed Solana nicht ab, ist die Spur hier zu Ende -
   dann bleibt nur die App selbst, und die hat keine Schnittstelle.
2. **`spiegel/verfolgte.json`** - die 20 Wallets mit Kriterien, Datum und
   Begruendung. Von Hand gepflegt; nur diese Datei entscheidet, wer verfolgt
   wird.
3. **`spiegel/wachen.json`** - eigene Grenzen, kein Kopieren von xperp-Werten:
   `max_einsatz_je_kopie_usd`, `max_offen`, `kill_switch_gesamt_usd`,
   `slippage_annahme_pct` (je Liquiditaet), `gebuehr_pct`, `abklingzeit_stunden`,
   `max_alter_signal_sekunden` (hinterherlaufen ist kein Nachahmen),
   `handel_erlaubt: false`.
4. **`spiegel/lesen.py`** - normalisiert Signale (Wallet, Token, Richtung,
   Zeit, Preis, Liquiditaet) aus der OKX-CLI. Nur lesend, kein Schluessel.
5. **`spiegel/spiegel.py`** - das Papierbuch: je Signal ein hypothetischer Kauf
   mit Slippage-Aufschlag, Ausstieg nach eigenen Regeln (Stop/Ziel/Haltedauer),
   Journal mit denselben Spalten wie die anderen Spuren. Kein Orderaufruf im
   Modul; `onchainos`-Schreibbefehle werden beim Import stillgelegt (Muster
   `swap/handeln.py`, `Papierfehler`).
6. **`spiegel/tests/`** - Signal wird zur Buchzeile, Slippage und Gebuehr
   fliessen ein, zu alte Signale werden verworfen, Sperren greifen, und der
   Modulquelltext nennt keine Schreibfunktion. Ein Test darf nie eine Order
   erreichen.
7. **Anbinden** (Stufe 1, `.bak-JJJJMMTT`): `tagesbericht.py`
   (`spur_spiegel()`), `Bus/handel_befehle.SPUREN`, `dauerlauf.py` SPUREN.
   Sperrtext-Regel beachten: `dauerlauf.nur_fenster_fehlt` liest die Zeile
   „… gesperrt durch: …".
8. **Versionieren:** eigene `!`-Zeilen in `.gitignore`, Gegenprobe
   `git check-ignore -v`, `git status` muss die neuen Dateien zeigen.

## Tor vor jedem echten Geld

Alles aus `Wissen/Handelsregeln.md`, Bedingung 1, unveraendert: **mindestens
6 Wochen Papierlauf, ≥ 50 abgeschlossene Runden, netto positiv nach Gebuehren
und Slippage, groesster Ruecklauf unter dem Kill-Switch.** Erst dann darf
`handel_erlaubt` von Hand auf true - und selbst dann oeffnet nur Max am
Bildschirm (Punkt 3).

Vorab-Bedingung dieser Spur, weil Memecoin-Buecher duenn sind: **die
Papier-Annahme fuer Slippage muss gegen echte Bucheindruecke geprueft werden**
(Liquiditaet, Tiefe). Ein Papierlauf mit 0,1 Prozent Slippage auf einer 30.000-USD-
Liquiditaet ist keine Probe, sondern eine Wunschrechnung.

## Nicht-Ziele

- kein Telegram-Bot, keine Bot-Wallet, keine PIN-Weitergabe, kein Schluessel
  an Dritte
- kein pump.fun-Schreibpfad, kein Sniping, kein Hebel
- kein Auto-Exit nach fremder Mathematik: die Ausstiege bleiben die eigenen
- keine Steuer-Aussage - Memecoin-Trades koennen bei Gewerbe und
  Kleinunternehmerschaft steuerlich relevant sein; das ist ein eigener Vorgang,
  kein Nebensatz im Handelsplan

## Risiken und offene Fragen

1. **Schnittstelle:** fomo.family hat keine dokumentierte API. Der Umweg ist,
   die **Wallet-Adressen** der Trader zu verfolgen (das kann der OKX-Feed) -
   nicht die App. Ob das die App-Trader vollstaendig abbildet, ist offen.
2. **Spiegel-Verzerrung:** Der Ranglisten-Fuehrende ist oft frueh dran. Ein
   Nachahmer kauft spaeter, zu schlechterem Preis, mit weniger Tiefe.
3. **Fehlerkosten:** Rug Pulls, Honeypots, Freeze-Authorities - deshalb steht
   der Token-Risiko-Check aus `okx-dex-market` vor jedem Kauf, nicht danach.
4. **Kein Konto-Abgleich** (bekannt aus der SWAP-Arbeit): Das Papierbuch glaubt
   sich selbst.
5. **Ressourcen:** Ein Echtzeit-Monitor (WebSocket) laeuft dauerhaft; der
   Rechner geht aus heiklen Gruenden ohne Vorwarnung aus
   (`Wissen/Hardware.md`). Die Spur muss einen kalten Start ueberleben.

## Was ich brauche, bevor gebaut wird

1. **Ja zum Papierweg** (oder ausdruecklich: nur die App selbst, von Hand).
2. **Kette und Umfang:** Solana allein, oder auch EVM? Nur Signale der
   Top-20, oder alle ab einer Grenze?
3. Bestaetigung, dass `onchainos` mit dem vorhandenen Projekt laeuft
   (Preflight in Schritt 1 klaert das ohne Aenderung).
