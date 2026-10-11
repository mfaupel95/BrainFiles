---
name: handel-spuren
description: "Spuren in Agenten/Handel anbinden, pruefen, auswerten."
version: 0.1.0
author: Hermes
category: brainfiles
metadata:
  hermes:
    tags: [Trading, Paper-Trading, Journal, Optimierung]
---

# Handelsspuren

**Tore, Freigaben, Deckel und die Trennung von Monitor und Ausfuehrung:**
`references/gates-und-freigabekette.md` - wo eine Sperre gehoert, was ein
Deckel bindet, warum ein Ausfall nie wie eine Messung aussehen darf und
warum ein Warteschlangen-Eintrag pro Risikostufe eine eigene Datei braucht.

**Laufzeit-Audit aller Spuren und die Frage "was darf mit echtem Geld":**
`references/laufzeit-audit-und-live-berechtigung.md` - neun Schritte in fester
Reihenfolge, warum jeder Logbefund eine Gegenprobe am laufenden System
braucht, welche Auswertung welche Frage beantwortet, und warum in der
Verdict-Tabelle die Spalte der echten Live-Zeilen entscheidet. Dort auch die
Diagnose "war das ein Bug eines Waechters?": erst die Live-Flags
(`handel_erlaubt`, `freigabe.erfuellt`, `trailing_aktiv`) und die
Journalzeile (`modus=live` + `grund=stop`) pruefen, bevor man den
Waechter-Code verdaechtigt - ein Live-Stop-Ausstieg ist normale Schutzlogik.

**Offene Positionen nachtraeglich absichern (Spot wie Margin):**
`references/handgriff-offene-positionen.md` - Handgriff an Positionen, die
SCHON offen sind: Ort klaeren statt raten, Stop nie ueber dem Markt,
Margin-Stop verknuepft, Reihenfolge bei Kraken (reservierte Menge), und
warum ein wortgetreuer Auftrag buchstabengetreu falsch sein kann.

**Risiko-Werkzeuge, Basis-Deckel, Schattenarme, Stop im Gitter:**
`references/risiko-und-schattenarme.md` - `HANDEL` ist eine oder zwei Ebenen
(sonst meldet ein Werkzeug "keine Positionen" statt zu scheitern), eine
Position ohne Stop ist der ganze Einsatz, der Basis-Deckel ist eine TABELLE
und bindet nur neue Einstiege, Aliase muessen vorbereinheitlicht sein, sonst
umgeht man den Deckel mit einem anderen Namen.

**Depotbestand gegen Spuren-Bücher abgleichen (OKX + Kraken):**
`references/depotbestand-buch-abgleich.md` — drei Werkzeuge (Kraken abgleich, OKX positionen live, OKX waisen), die Reihenfolge, die Freigabe-Regel (Haken kommt NUR von Max), die Boerzen-Trennung (OKX EEA in USDC, Kraken in EUR/USDC) und die Sperrgruende.

**Botsenseitig lesen, wenn die Frage "was ist offen" lautet:**
`Agenten/Handel/okx_positionen_live.py` (rein lesend, ohne Bot-Blick) zeigt
Kontostand je Waehrung, offene Positionen mit Einstieg/Liquidation und die
Stops mit ihrer Menge. Die BOTS (Leiter, Munition) sind davon getrennt
(`okx-bots-bewachen`) - beide Fragen gleichzeitig beantwortet ein Aufruf
sonst nie.

## Die Verdrahtungsregel: eine Spur, die das Haus fuehrt, muss das Haus rechnen koennen

`dauerlauf.SPUREN` (47), `auswertung_alle.SPUREN` (44), `pruefe_ratschen.SPUREN`
(40), `lage.HOLER` (47), `befehle.FAMILIE` (51) sind fuenf **Hand-listen ohne
Maschine**. Eine Spur in nur einer davon sieht vollstaendig aus.

Gemessen 03.10.2026 (Auftrag "nicht erkannte Arbeit in Handel"):
`liq_wand`, `trendwende_btc` und `nautilus_emacross` liefen seit dem 21.09. im
Dauerlauf und fehlten in `auswertung_alle.SPUREN` - **liq_wand hatte 32
geschlossene Runden im Journal und 0 in jeder Auswertung**. Ebenso fuehren
fuenf Spuren (squeeze, wavetrend, macd_mtf, supertrend, nautilus_emacross)
eine Drawdown-Ratsche, die `pruefe_ratschen.py` nie nachfragte, und
`nautilus_emacross` uebergab den Bus-Namen als `"handel/" + NAME` - fuer
`test_anbindung_handel` (T-255) unsichtbar, der Test rot.

Faustregeln, wenn eine neue Spur entsteht:

1. **Das Journal entscheidet ueber den Rechenweg, nicht der Ordnername.**
   `kauf`/`verkauf` mit `einsatz_usd` = `runden_indikator`
   (INDIKATOR_ oder BOT_SPUREN). `eroeffnen`/`schliessen` mit Betrag =
   `runden_nautilus`. **In der Liste zu stehen garantiert NICHT, dass das
   Journalformat passt:** eine Spur in BOT_SPUREN, die `eroeffnen`/`schliessen`
   schreibt, bekommt still 0 Runden in JEDER Auswertung, weil
   `runden_indikator` nur `kauf`/`verkauf` paart (gemessen an omniquant:
   37 EINSTIEG/20 AUSSTIEG-Zeilen, 0 Runden). Vor einer Auswertungs-Aussage
   die AKTIONEN zaehlen, die die Spur wirklich schreibt
   (`Counter(r.get('aktion') for r in zeilen)`), und gegen den Rechenweg
   halten, dem sie zugeordnet ist - nicht nur pruefen, dass sie in der Liste
   steht. `inst`-Feld vorhanden = nautilus-Weg; `token`/`symbol`
   statt `inst` = **kein** Weg in auswertung_alle (belegt: `runden_nautilus`
   an kopier ergab 107 Runden mit falscher Paarung, Einsteig PATE /
   Ausstieg leeres Symbol). Dann gehoert eine eigene `auswertung.py` in den
   Ordner, und die Spur wandert NICHT in `auswertung_alle.SPUREN`.
2. **Jede gesetzte Ratsche wird geprueft.** `pruefe_ratschen.SPUREN`
   fragt `lage()` der Spur - die vier Indikator-Spuren haben keine eigene
   `lage()`, sie laufen ueber `("spur", "spur", "scanner", "wachen_pruefung")`.
3. **Der Bus-Name steht WOERTLICH in der Datei.** `"handel/" + NAME` ist fuer
   die Suite unsichtbar, egal wie korrekt die Konstante ist.
4. **Gegenprobe statt Annahme.** `tests/test_verdrahtung.py` (6 Tests) prueft
   die Regel mit zwei Gegenproben - nimmt man `liq_wand` aus der
   Auswertungsliste oder `squeeze` aus der Pruefliste, wird derselbe Test rot.

Audit in einem Lauf (etwa 30 Sekunden):

```python
import sys; sys.path.insert(0, 'Agenten/Handel')
import dauerlauf, auswertung_alle, pruefe_ratschen, befehle
ausw = set(auswertung_alle.SPUREN)
rats = set(x[0] for x in pruefe_ratschen.SPUREN) | set(pruefe_ratschen.RUHT)
print('ohne Auswertung:', sorted(set(dauerlauf.SPUREN) - ausw))
print('ohne Ratschenpruefung:', sorted(set(dauerlauf.SPUREN) - rats))
```

`lage.HOLER` ist ein **Tupel von Funktionen** (`spur_<name>`, `spur_kopier_familie`
fasst fuenf Spuren zusammen), `befehle.FAMILIE` ein `dict` Spur->Beschreibung -
beide naehern sich nicht so, wie man sie sich vorstellt. Ein Holer darf praeziser
heissen als die Spur (`spur_xperp_positionen` fuer xperp).

## Wann
Jede Änderung unter `Agenten/Handel/**`: Sperre ergänzen, Freigabe verdrahten,
Analysemodul bauen, Wachenwerte anfassen, Tests schreiben, Spur an fremden Feed
haengen (Kurs-, Signal-, Wallet-Daten).

Welche Spuren es gibt, steht in `dauerlauf.SPUREN` — von dort lesen, nicht aus
diesem Kopf: die Liste aendert sich (kraken war stillgelegt und laeuft wieder als
Papier, orbk kam dazu, omniquant ist eine Papierspur auf dem Prognose-Bericht).

Ausloeser → Referenz:
- Komplett-Neubau einer Spur (von der verifizierten, abgebrochenen Aufgabe bis
  zur laufenden GUI: Vorbilder lesen, bauen, verdrahten, beweisen,
  Dauerlauf-Start): `references/neue-spur-ende-zu-ende.md`
- Bus-Meldung „Ergebniscode 1“ deuten; „nimm die Spur auf Dauerbeobachtung“
  (heisst: sie steht in `dauerlauf.SPUREN` UND jede Positionsaenderung erreicht
  Telegram); Bestandscheck „was ist noch nicht angebunden?“:
  `references/anbindungs-audit.md` — zum Deutbaren gehoert
  `references/betriebsfehler-spuren.md` (Bus-Journal als Ursachenquelle,
  Zaehlung „Rueckgabe N“ je Spur, halber `except` in der Datenschicht).
  **Und die Anbindung selbst VERIFIZIEREN** („kann die Spur handeln?“, „lohnt
  die Börse?“, „warum ist das Konto leer?“) — `Handel/anbindung_pruefen.py`
  fragt die Börse (Schlüssel, Demo-Modus, Guthaben in der Quote der Spur,
  Kurs) und ordnet nichts; die Warnung dort: **die Vorgabe des Prüfers ist
  kein Befund**, und „anbindungsbereit“ sagt nichts über die Freigabe.
- **„Der Dauerlauf ist gestorben / alle drei Stufen stehen“** (Rueckgabe 143,
  Sperren-Churn, spurloser Tod, die Regel fuer Handstarts und die Wache):
  `references/dauerlauf-tode.md`
- **Bestehende Spur nachtraeglich in den Takt haengen** (sie hat `handeln.py` +
  `wachen.json`, laeuft aber nicht im Dauerlauf - auch mehrere auf einmal, mit
  allen fuenf Stellen, dem Vertrag des Tagesberichts, der Nachweis-Kette von der
  Warteschlangen-Probe bis zum ersten Zyklus und den Fallen dabei):
  `references/spur-nachtraeglich-anschliessen.md`
- Bilanz deuten, „das heisst, wir haetten X gewonnen?" — ein Papierbuch-Ergebnis
  hat fuenf Fragen, bevor es eine Antwort ist:
  `references/buchergebnis-pruefen.md`
- **„warum hat die Spur 0 Runden?"**, **„Spuren ohne Runden stillegen"** —
  „0 Runden" heisst NICHT „stirbt nie": die Auswertung zaehlt GESCHLOSSENE
  Runden, eine Spur mit heute eroeffneten Positionen steht dort bei null und
  arbeitet. fuenf Lagen, die gleich aussehen (wartet / arbeitet / nur
  Ausbuecher / **Buch voll** / Stall), plus die Stall-Falle „Instrument
  nicht mehr in der Wachenliste" **und die dritte Form: es gibt fuer einen
  gehaltenen Token gar KEINEN Kurs** (Onchain-Kette meldet nur Transaktionen) —
  „Buch voll bei vorhandenen Kandidaten" ist selbst eine Null-Lage.
  **Vor jeder Stilllege-Empfehlung erst der Befund-Lauf**
  (`scripts/null_runden_befund.py`, liest nur, nennt die Lage mit) und im
  Bericht die LAGE nennen statt der Rundenzahl: `references/null-runden.md`
- **„Code optimieren", „Suche nach Luecken", „mach das sichtbar" — Pruef- und
  Haertungsweg mit Verdachtsmuster-Checkliste, Fix-Disziplin, Nachweis-Kette:
  `references/spur-haerten.md`
- **„eine Spur macht nur Verlust", „Positionen werden geoeffnet und direkt
  wieder geschlossen"** — drei BUCHFUEHRUNGS-Ursachen in fester Reihenfolge
  pruefen (Phantom-Hoechststand des Kill/Ratsche, Geister-Ausbuchung von
  Live-Positionen, Buch-Stop gegen Boersen-Stop), bevor der Markt verdaechtigt
  wird: `references/verlust-spur-diagnose.md`
- **„welche Spur ist die beste?", „hat die Trefferquote einen Sinn?", „eine Spur
  sieht super aus und ist falsch"** — Werkzeug `Agenten/Handel/spur_audit.py`
  (liest nur, `--historie` laedt fehlende Kerzen nach), beantwortet fuer ALLE
  Spuren in EINEM Durchgang die Reihenfolge „Erst Echtheit, dann Edge“: drei
  Alarme aus dem Journal allein (Haltedauer im Aufrufertakt, ein Instrument traegt
  die Mehrheit, identische Einstiegspreise je (Instrument, Tag) = Preis
  UEBERNOMMEN statt geholt), dann die Excess-Rendite gegen BUY & HOLD statt der
  Trefferquote. **Die Trefferquote allein ist kein Edge** — 93 % koennen schlechter
  sein als 50 %, wenn die Verlierer laenger gehalten werden.
  `references/edge-und-statistik-audit.md` — dort auch die vier Fallen, die sich
  beim Bauen solcher Messungen zeigen: die Auswahl-Verzerrung (eine Kennzahl, die
  nur fuer eine TeilMENGE berechenbar ist, meldet den Teil als das Ganze — eine
  Runde von 15 Minuten hat keine volle Kerze im Fenster und damit keine Basislinie,
  und genau diese Runden sind die Scheinrunden), die stille Basislinien-Luecke
  (ein Mapping muss Basiswerte kennen, nicht Schreibweisen: dieselbe Position
  erscheint als Spot-, Kontrakt-, Swap- und Krakenname; ohne Reduktion auf den
  Basiswert faellt jede andere Spur durch), die leere Spalte als Befund aus dem
  Nichts (nicht jede Spur fuehrt das Instrument in `inst`) und die Regel, die
  auf einen Fall passt und die anderen zerschneidet (`[:-3]` macht aus `CASHCAT`
  -> `CASH`). **Ein Instrument ohne Historie bleibt eine LUECKE und bekommt kein
  Ersatzinstrument.**
- **Buch und Boerse passen nicht zusammen** („die Spur zeigt Positionen, live ist
  aber nur X da", „Order ging nicht durch", „Limit wartet", Position ohne
  boersenseitigen Stop, Kill-Switch entsperren, Q: laeuft hinterher):
  `references/live-order-und-buchpflege.md` — Order angenommen ist keine Fuellung,
  ein Limit hinter dem Markt ist WARTEND statt fehlerhaft, Geisterpruefung erst
  nach dem Orderzustand, ein Papierlauf schliesst keine echte Position, die
  Spiegelung gehoert an den Zyklusanfang; ein gemeinsames Buch fuer Papier und
  Live fuellt die LIVE-Plaetze (der Deckel greift, bevor ein Kaufversuch
  entsteht), Positionen ohne Orderkennung sind Papier-Altlasten; der Abgleich prueft die
  GROESSE, und eine Ausbuchung darf keinen Verlust erfinden.
  **Ergaenzend als vierte Stufe: die DECKUNG** - Geister, Groesse und
  „liegt ein Stop" fragen alle nur OB, nie WIEVIELE Kontrakte geschuetzt sind.
  Ein boolescher Existenztest gibt `True` zurueck, sobald ein einziger
  Schutzauftrag liegt, und wirft die Menge weg; gemessen standen so 19 von 145
  Kontrakten ohne Schutz, ohne dass ein Befund kam — ein boolescher
  Existenztest gibt `True` zurueck, sobald EIN Schutzauftrag liegt, und wirft
  die Menge weg. Zwei Preise verweigert ein Nachsetzen statt zu raten (long-Stop
  auf/ueber dem Kurs, Stop auf/unter `liqPx`). Werkzeug
  `xperp/stopdeckung.py` (Vorschau Standard, `--anwenden --stop <preis>` ohne
  Preisschalter stellt NICHTS), Referenz Abschnitt 5d derselben Datei.
  **Und die Deckung wird in JEDEM Live-Zyklus gemessen, nicht nur beim Kauf:**
  `live_perp.stopdeckung_pruefen()` fragt die Boerse ueber `/openorders` mit der
  Kontraktzahl, setzt einen fehlenden Stop mit der vollen Menge nach,
  kontrolliert den Nachsatz ein zweites Mal und fasst bei einem Abruf-Fehler
  nichts an. Eine gesetzte Order ist kein Beweis - ein Weg, den man falsch
  waehlt, liefert `requiredArgumentMissing` und wird als „nicht lesbar"
  gemeldet, obwohl der Stop an der Boerse liegt.
- **„weniger handeln", „Ein- und Ausstiege sollen indikatorindiziert und nicht
  zeitabhaengig laufen", „die Signale sollen ausloesen, nicht die Uhr",
  „die Spur handelt dieselbe Sache dutzende Male am Tag"**: ein Einstieg nur
  bei einem **Signalwechsel**, der Dauerlauf legt den Auftrag in eine Queue,
  ein asynchroner Executor fuehrt aus - und fuer Spuren mit EIGENEM
  `handeln.py` (xperp, scanner, mosaic, kraken) liegt die Regel einmalig in
  `Handel/signal_wechsel.py`, weil `spur_buch.trigger_modus` dort
  stiillschweigend ignoriert wird. Ausloeser ist fast immer der Befund
  **„Gebuehren-Excess nahe null"**: eine Spur mit 2,44 % Ergebnis und 0,01 %
  Excess hat keinen Vorteil, die Gebuehr hat ihn aufgefressen, und die Zahl der
  Runden ist die einzige Groesse, die sich sofort senken laesst:
  `references/signal-statt-takt.md` - dort auch die drei Fehler, die diese
  Regel gekostet haben: ein Gatter NACH dem Orderaufruf (bei Live ein Zyklus
  zu spaet), ein Schluessel auf dem Instrument statt auf der Basis (derselbe
  Markt als `XBT-USD` und `BTC-USD-um_XPERP` macht die Regel wirkungslos) und
  ein Gatter, das auf einem Weg `True` und auf dem anderen einen String
  zurueckgibt (sperrt dann jede Spur OHNE Flag und wirft nie einen Fehler).
  Und ein Weg ausserhalb des Dauerlaufs traegt **alle** Tore selbst,
  einschliesslich des Freigabefensters - ein Importfehler bedeutet: keine
  Order.
- **Tagesbericht auswerten**, ein Bericht liegt vor und die Zahlen sollen ein
  Urteil tragen (ein Posten mit unpassender Groesse, "Stop gerissen", ein
  negativer Zuwachs seit gestern, dieselbe Spur in zwei Stufen mit
  gegensaetzlichem Vorzeichen): `references/buch-und-boerse-abgleichen.md` -
  der Bericht ist ein Verdachtsgenerator, die Wahrheit kommt aus der
  Boersenabfrage; dort auch die Namensfalle beim Bestand (`ALGO` gegen `ZALGO`)
  und die Zuordnung "wer hat das gekauft". Dazu `references/beleg-und-hand.md`:
  die Fuellung wird ABGEWARTET, sonst stellt die Spur denselben Beleg neu und
  die Hand kauft denselben Wert erneut.
- **Ein Orderpreis wird abgelehnt** („price can only be specified up to N
  decimals“, `tickSz`, der Notausstieg kommt nicht zustande und die eben
  gekaufte Position wird zurueckverkauft): `references/zweite-boerse.md` —
 Preisregeln je Paar/Instrument aus der API, Rundungsrichtung, Probe mit
 `validate=true`. Dazu gehoeren die gemessenen Gebuehrensatze: siehe
 `references/tor-kalibrierung.md`, Regel 8; den Satz selbst BELEGEN (Kontotarif
 plus echte Fuellung, `gebuehr_taker` Bruch gegen `gebuehr_pct` Prozent,
 Werkzeug `Handel/gebuehren_setzen.py`): `references/gebuehren-belegen.md`.
 **Jeder Satz traegt seine QUELLE neben dem Wert** (`_gebuehr_quelle`; ein Wert
 ohne Notiz ist ein Fund, auch wenn er richtig aussieht), **und ein Widerspruch in
 der Datei wird BENANNT und mit dem TEUREREN der beiden Saetze gerechnet**
 (Beispiel: `boerse: kraken_futures` gegen Instrumente, die ueber OKX bewertet
 werden) - der guenstigere Satz waere geraten und freundlich, beides verboten.
- **Eine Zeile wie `OKX-Transportfehler 1/6: <urlopen error [WinError 10054]>`**
  ("ist die Boerse weg?", ein abgebrochener Kauf, dieselbe Meldung von Kraken):
  sie ist eine WARNUNG - der Wiederholer versucht es bis zu sechsmal mit
  wachsender Pause, erst der sechste Fehlschlag ist einer. Pruefen statt deuten
  (signierter Leseaufruf plus die Fehlerzeilen des DAUERLAUF-Logs, nicht der
  Rand-Logs), und die Meldung selbst so formulieren, dass sie die Wiederholung
  ausspricht ("- wird wiederholt, kein Ausfall"): `references/okx-fehlermeldungen.md`,
  Abschnitt 11.
- **Eine Boerse wieder ENTZIEHEN** ("nur noch <Programm> darf auf <Boerse>
  handeln", "Kraken abschalten"): drei Schalter mit verschiedenen Wirkzeiten,
  die Vorbedingung (offene Positionen und ihre Boersen-Stops), warum eine Sperre
  kein Umzug ist und die Handwerkzeuge scharf bleiben -
  `references/zweite-boerse.md`, Abschnitt "Eine Boerse wieder ENTZIEHEN".
  **Eine Spur von EINER Quotewaehrung auf MEHRERE generalisieren** (EUR ->
  EUR/EURC/USDC: Quotewaehrung je Paar aus der API, Guthaben-Tor in der
  Paarwaehrung, Buch bleibt in der Spurwaehrung) und **der Rust-Laeufer
  omnitrade hat SELBST keinen Orderweg** (rein lesender Lauf; die Haus-Spur
  `Agenten/Handel/omnitrade/` spiegelt seine Position und ordert ueber den
  Haus-Spot-Weg - Hebel laesst sich dort nicht nachruesten), **omniquant hat
  keinen Orderweg** — "bauen" heisst dort Live-Orderweg anbinden: `references/zweite-boerse.md`, Abschnitte
  "Eine Spur von EINER Quotewaehrung..." und "omnitrade ist KEINE Spur".
 - **Derselbe Anbieter, ein ANDERES Produkt** (Spot gegen Futures/Terminkontrakt:
 eigener Host, eigene Kopfzeilen, eigene Schluesselnamen, `Authentication error`
 oder `404 NOT_FOUND` trotz gueltigem Schluessel, Groesse in Kontrakten statt
 Muenzen, Ausstieg braucht `reduceOnly`, Besicherung aus dem Cash-Konto des
 Dienstes): `references/zweite-boerse.md`, Abschnitt "Ein zweiter Dienst sieht aus
 wie eine zweite Boerse". **Und die Kontraktgroesse wird GEMESSEN, nicht aus dem
 Record gelesen** (`contractSize` ist dort immer 1 und sagt nichts): 1 Kontrakt =
 1 Einheit der Basiswaehrung, Einschuss 10 % fuer ein EEA-Konto - Abschnitt "Wie
 gross ist ein Kontrakt WIRKLICH" derselben Datei, mit der Tabelle, welcher Markt
 sich mit welchem Guthaben ueberhaupt handeln laesst. Weil es hier keinen
 `validate`-Schalter gibt, ist der Mini-Round-Trip der Beleg
 (`nautilus_kraken/futures_probe.py`, Vorschau Standard, Notausstieg per Stop) —
 **immer auf einem billigen Markt** (`--symbol PF_STRKUSD --kontrakte 1`), denn
 die Vorgabe des Werkzeugs war ein Markt, dessen 1 Kontrakt rund 84.600 USD
 kostet, und die Sonde rechnete sie als 1 USD: nach der Korrektur bricht sie im
 Tor ab, vorher haette sie gekauft. Und **der Einschuss kommt aus dem
 Margenplan des Marktes, nicht aus einer Pauschale** — gemessen lagen 10 %
 (EIA-retail) und 12,5 % (BTC) nebeneinander, ein „Hebel x10" ist also je Markt
 eine Behauptung.
- **Max aendert Positionen von HAND** (in der Boersen-App schliessen,
  verkleinern, aufstocken) - das Buch folgt der Boerse, die handgeschlossene
  Position bekommt ihr ECHTES Ergebnis, Stop/Ziel bleiben der Spur, und der
  Nachzieher samt Routine fuer alte kaputte Journalzeilen:
  `references/handgriffe-von-hand.md`
- **"in meinem OKX sehe ich keine Order"**, Zweifel an einem echten Kauf — Order am
  Handelsplatz LESEND nachpruefen (`avgPx` gegen Bucheinstieg), Unterkonto-Falle,
  und die verbraucher-/erzeuger-Falle (gehandelt auf einer Datei, die niemand mehr
  schreibt): `references/live-order-nachpruefen.md` + `scripts/okx_live_order_probe.py`
- **Zustandsbericht** („Bericht", „wie laeuft die Spur") — lesend, mit den
  Quellen, den Lese-Fallen (BOM im Bus-Journal, UTC vs. lokal, Vorschau-Lauf je
  Zyklus, kurze Abstaende vs. Luecken) und der Form, die Max erwartet:
  `references/spur-bericht.md`
- **Stille Spur / falsch gelesenes Etikett** („warum still und nicht papier?",
  eine Spur bucht nichts, eine Uebersicht zeigt 0 Ausstiege) **sowie Stilllegen**
  („<spur> stillegen bis eine Messung da ist"):
  `references/stille-spuren-deuten.md` — „still" heisst nichts Neues, nicht
  abgeschaltet; Werkzeug `stille_spuren.py`, bei Eigenspuren `--papier` statt
  `--vorschau`, Entscheidungsbaum zum Einschalten, und zum Ausschalten die ZWEI
  Schalter (ein einzelner laesst den Papierlauf den Bereinigungskreis fuellen).
- Änderung, die **alle Spuren** trifft („das gilt für alle", Bedingung 4, neuer
  Kosten-/Ausstiegsgrund, Befund an mehreren Spuren) — Ausrollweg von Inventar
  bis Commit, inklusive Testaufruf-Falle und versehentlich überschriebener Kopie
  außer Haus: `references/spur-weite-aenderung.md`
- „werte die Daten aus", „optimiere die Strategien", **ein mitgeschicktes
  Kennzahlen-Formelblatt** (Sharpe/Sortino/Calmar/VaR, Expectancy, MAE/MFE) oder
  eine Freigabe (Bedingung 1: 50 Runden netto positiv) — Weg von den Journalen
  zur EINEN belegten Aenderung, mit den Zahlen, die eine Aenderung tragen, und
  dem, was eine duenne Stichprobe NICHT hergibt:
  `references/auswertung-und-optimierung.md`. **Und Schritt 2b dort: eine Auswahl-
  regel wird GEGEN DIE BASISLINIE gemessen, nicht gegen null** (Differenz zu allen
  vom Scanner gesehenen Maerkten plus t-Test; |t| < 2 = kein Edge) — und „die beste
  Spur" heisst zwei Fragen, nicht eine: sagt ihr Signal etwas voraus, und kann
  sie ueberhaupt handeln. Eine Spur ohne Orderpfad kann die bessere Strategie sein
  und trotzdem nie sichtbar werden. Dort auch, wie man die Auswertung
  SELBST liest, bevor man ihr glaubt: der Anteil der groessten Spur an der
  Summe, Brutto gegen Netto (Papierzeilen tragen keine Gebuehr), ein FEHLENDES
  Gebuehrenfeld in der `wachen.json`, das eine tote Spur tragfaehig aussehen
  laesst (Satz gegen die Boerse der Spur halten, nicht gegen ihren Namen), und
  der harte Todesbeweis `f_max < 0`, und ein Buch OHNE Einsatz (Punktebuch), das weder Prozent noch USD behaupten darf - dafuer Ergebnis in R. Drei Regeln, die dabei gelten: (a) Die VORGABE eines Aggregators ist BRUTTO - eine Funktion, die nie etwas von ihrem Ergebnis abzieht, darf es nicht als netto ausgeben; wer die Gebuehr schon im Journal traegt, wird ueber eine NAMENSliste ausgenommen (`GEBUEHR_SCHON_DRIN`), sonst wird zweimal abgezogen, was genauso falsch ist wie gar nicht. (b) Ein Punktebuch bekommt KEIN erfundenes Nominal (es kaeme aus `risiko_pro_trade / stop_abstand`, und der Stop ist dort die Range-Hoehe - das waere ein Nominal von einigen tausend USD); es bekommt das Ergebnis in R und die Einheit `Punkte` statt `USD`. (c) **Die Auskunft gehoert in JEDEN Weg, den Max liest.** Eine Aenderung, die nur das CLI-Werkzeug trifft, erreicht ihn nicht: dieselbe Aussage muss in den Telegram-Befehl (`/strategien`) UND in die "7 Tage"-Zeile des Tagesberichts, ueber EINE gemeinsame Funktion, damit die Wege nicht auseinanderlaufen. Beim Formelblatt gilt: nur
  uebernehmen, was die eigene Datenlage traegt — Sharpe/Sortino/VaR/CAGR brauchen
  Tagesrenditen, die das Haus nicht fuehrt (Runden NICHT umrechnen, die Luecke
  benennen); die t-Statistik der Expectancy ist die Zahl hinter „unter 8 Runden
  ist es ein Befund"; und eine Kennzahl, die aus einer Journal-Spalte abgeleitet
  wird, erst gegen deren Fuellquote pruefen (ein Platzhalter wie `mae_pct 0.0000`
  macht einen Stop-Vorschlag zu 0 % - dann „nicht gefuehrt" ausgeben statt eine
  Null als Messwert). Und die EINHEIT des Gebuehrensatzes wird geprueft, nicht
  geraten: `gebuehr_taker` ist ein Bruch JE SEITE, `f_max` Prozent JE RUNDE -
  dazwischen liegt der Faktor 2 x 100, und ohne ihn erklaert jede Spur sich
  selbst fuer tragfaehig. **Und der Satz selbst wird GEMESSEN** (Kontotarif plus
  echte Fuellung am eigenen Konto, je Markt): `references/gebuehren-belegen.md`.
- **Ein Replay-/Backtest-Lauf verweigert** ("keine Historie fuer <spur>", der
  Backtest-Reiter bricht mit einem Traceback ab, "0 Runden" ohne einen einzigen
  gerechneten Schritt, ein angebotener Reiter-Knopf, der nur scheitern kann):
  `references/pitfalls.md`, Punkt 95 - die Pruefung gehoert VOR das Schneiden,
  der Bedarf ist `mindest_kerzen + 20` je Reihe, und ein angebotener Weg wird
  einmal ECHT gefahren, bevor er angeboten wird. **Drei Regeln dazu:**
  (a) **Die Vorgabe kommt aus der SPUR, nicht von der Kommandozeile** - ein fest
  eingetragener Gebuehrensatz ist fuer die eine Spur richtig und fuer die naechste
  geraten (`replay.gebuehr_aufloesen()` liest `gebuehr_taker` x 100 aus der
  wachen.json und schreibt seine Herkunft ins Ergebnis; ein ausdruecklicher Wert
  schlaegt sie, auch `0`).
  (b) **Die angebotene Liste wird gemessen, nicht gepflegt** - `orb`/`orbk` (kein
  `lade_wachen`), `mosaic` (braucht drei Kerzenreihen 4H/30M/5M) und `gitter`
  (kein `pruefe_ausstiege`, die Rechnung liegt in `grid.py`) fielen je mit einem
  ECHTEN Lauf heraus; der Reiter bietet seither VIER Spuren an (squeeze,
  wavetrend, macd_mtf, supertrend), die uebrigen stehen mit Grund in
  `replay.NICHT_NACHRECHENBAR`.
  (c) **Ein Backtest-Ergebnis traegt nur mit seiner Ausstiegsregel** - nach jeder
  Aenderung an der Ausstiegsregel sind die alten Zahlen ungueltig und werden NEU
  gemessen, nicht weiterzitiert (die Kerzenschluss-Regel senkte die Trefferquoten
  der vier Indikator-Spuren von 51-54 % auf 33-36 %; danach lag `macd_mtf` mit
  `f_max` 0,1997 % genau auf den Rundekosten von 0,200 %, `wavetrend` negativ).
  Eine Trefferquote ohne die Ausstiegsregel daneben ist keine Kennzahl.
- **„nach diesem Vorbild weitere Indikatoren zur Marktprognose entwickeln"**
  (ein mitgeschicktes Tor-Tabellen-Vorbild wie `prognose_berichte/Stanni.csv`,
  „zieh die neuen Strategien aus <Fremdquelle>", eine Luecke im
  Indikatorbestand): `references/strategie-aus-fremdquelle.md`, Abschnitte 7 und
  8 — den Ideenbestand ZAEHLEN statt lesen (die Zahlen der Fremdsammlung sind
  Prosa, uebernommen werden nur Namen und Rechenregeln), die Luecke per Suche
  belegen, und ein Merkmal als TOR bauen (Filter auf bestehenden Runden,
  Zeit-Halbierung beide Haelften positiv), nicht als neue Spur; den Wert aus
  einem Raster holen, die Tabelle traegt Wert UND Herkunft.
- Eine andere Sitzung laesst Arbeit im Baum liegen („wenn die Session fertig ist,
  mitnehmen", eine geaenderte Datei, die man selbst nicht angefasst hat) —
  Fertig-Erkennung, Waechter-Cron, getrennter Commit und die Frage, was eine
  Entscheidung von Max braucht: `references/fremdarbeit-mitnehmen.md`
- **Ein MCP-Werkzeug soll handeln dürfen** („was ist mit dem Boersen-MCP?",
  „Werkzeug bauen", Order aus einer Fremdsitzung), ein zweites Programm auf
  demselben Boersenschluessel streikt mit `Invalid key`, **oder ein Live-Tor
  meldet nach Wochen plotzlich `Permission denied` / `authenticationError`
  und der Kontostand ist nicht mehr abrufbar**:
  `references/mcp-tor-freigabebeleg.md` + `references/kraken-nonce-und-lockout.md`
  + `references/boersen-schluessel-diagnose.md`
  — Entscheidung bleibt bei der Spur, Einmal-Beleg als Tor, die alten Wege
  werden geschlossen, Ausstiege bleiben frei; die Zuordnung „unser Code,
  der Schluessel oder die Boerse" laeuft in der Reihenfolge der Diagnose-Datei.
  **Und eine zeitweise Abweisung** (heute da, in einer Stunde ohne Zutun weg)
  bekommt einen ZEUGEN samt Wache statt einer neuen Sonde: Abschnitt 8 der
  Diagnose-Datei - vier Wege (offen/signiert x Spot/Futures) trennen Netz von
  Schluessel, im Fehlerfall Status + Header + Rohantwort festhalten, nach einer
  Abweisung 60 min Kuehlzeit halten (jeder Versuch setzt den Lockout-Timer
  zurueck), und die Sonde nimmt ihre Adresse aus dem HAUSMODUL - sonst schickt
  der Test Aufrufe mit Attrappen-Schluessel an den echten Host.
- **"hab eingezahlt" und das Guthaben ist nicht da** („wo ist das Geld hin",
  „die Spur kann nicht handeln, weil 0 EUR frei sind", eine Einzahlung steht auf
  `Success` und trotzdem ist der Saldo 0): `references/einzahlung-und-guthaben.md`
  — eine Einzahlung wird ueber die BUCHUNGSKETTE nachgewiesen (Eingang ->
  Gegenbuchung mit `refid` -> Zielkonto -> alle Wallets), nicht ueber einen Saldo;
  die Boerse kennt Wallets, die ihre Handels-API nicht zeigt; kein Geld selbst
  bewegen.
  Ein Zugang, der eine Stunde lang abgewiesen wird und danach OHNE Zutun wieder
  geht, ist kein Schluesselproblem: Zeitpunkte notieren, Werte per Hash gegen die
  `setx`-Zeile der PowerShell-History halten, Uhr stellen, nach Minuten erneut
  messen. Und nach dem Freischalten nicht das Guthaben verwechseln - bei einem
  multiCollateral-Konto traegt `flex` das Geld und `cash.balances` steht auf 0,0
  (`references/einzahlung-und-guthaben.md`).
- **Risikostufen** („mit groesseren Positionen fahren", „zweiter Lauf mit mehr
  Einsatz", „mehr Daten in kuerzerer Zeit", `HANDEL_RISIKO`, `--risiko`,
  `risikostufe.py`, „Strategie Hoch hat noch kein PID", „alle drei Stufen
  gegeneinander"): derselbe Handel mit Faktor 1/2/4 auf getrennten Dateien —
  was skaliert wird und was nie, warum eine Stufe nie live geht, kein Telegram
  bekommt und warum der Spiegel aussen vor bleibt, wie eine Stufe einen eigenen
  Waechter-Task bekommt und warum drei Stufen keine Skalierung derselben
  Geschaefte sind: `references/risikostufen.md`
  **Eine VARIANTE anzuzeigen ist kein Beleg, sie zu LESEN.** Die Regel gilt fuer
  Risikostufen, Arme (`HANDEL_BUCH`) und Fassungen gleichermassen und braucht
  ZWEI Pruefungen: jede Buchdatei muss ueber die Variante gebildet werden
  (Suffix ZULETZT, `wachen.json` NIE - die Wachen werden skaliert, nicht
  umbenannt), UND die MODULVARIABLEN der Leser-Werkzeuge muessen gestellt werden
  (`auswertung_alle.STUFE` ist eine Modulvariable; ohne sie stehen in einer Zeile
  die Positionen der Variante und die Zahlen der Basis). Im `finally`
  zurueckstellen - ein Bericht darf den aufrufenden Prozess nicht umstellen.
- **„welche Spur handelt real", „nur die live und handel erlaubt Staende",
  `/live`: Orderfaehigkeit am CODE pruefen statt am Schalter (Haus-Funktionsnamen!),
  Buch je `modus` trennen, neuen Lese-Befehl in beide Bots verdrahten:
  `references/live-status-und-buch-trennung.md` — dort auch der Fall "eine
  Papier-Position belegt den LIVE-Platz": Aufraeumschritt am ANFANG des
  Live-Laufs, VOR der Platzzählung, und das Einmal-Werkzeug
  `Handel/papierbuch_schliessen.py` (Vorschau Standard, `--anwenden`,
  `--spur <name>`; ruft die Funktion DER Spur, fasst keine Zustandsdatei
  juenger als 300 s an).
- **„Gebuehren-tor“, „ab wann darf eine Spur live?“, „welche Spur hat ueberhaupt
  Edge?“, „Auswertung und Freigabe“** — ein Tor, das RECHNET statt den
  Freigabe-Haken zu setzen (`Handel/freigabe_tor.py`, Zahlen aus EINEM
  `spur_audit.py --json`-Lauf): vier Bedingungen — mindestens 8 Runden,
  mindestens 8 davon MIT Basislinie, Excess minus der Gebuehr der eigenen
  Boerse positiv, und **kein Befund im Audit**. Die vierte ist die
  wichtigste: der scanner haette die anderen drei mit +8,52 % klar
  bestanden und trotzdem nicht bestanden, weil sein Audit ihn beanstandet.
  **Eine schoene Zahl mit einem Befund daneben ist keine Freigabe.**
  Eine Spur ohne Auditrundlage ist *unbewiesen*, nicht abgelehnt — das Tor
  sperrt sie nicht. Fail-closed: Import- oder Lesefehler bedeutet keine
  Order. `references/gebuehren-tor.md`
- **„<spur> scharf schalten“, „handel erlaubt auf <Boerse>“, „gefechtsbereit
  machen"**: erst die fuenf Bedingungen LESEN, dann die zwei Schalter schreiben —
  eine reissende quantitative Bedingung nimmt `handel_erlaubt` innerhalb von
  Sekunden selbst zurueck (`sperre_zu`, Merker `_sperre_zu_ausgeloest`), und das
  Aussetzen einer Bedingung bleibt Max' Entscheidung - sie wird dann ABGESCHALTET
  statt geloescht (`<bedingung>_aktiv: false` in der `wachen.json`, Vorgabe gilt),
  und der Schalter muss an BEIDEN Stellen gelesen werden: Sperrgrund UND
  Sperr-Schliessung. Dazu das Zeitfenster, der Nachweis und die Nebenwirkung auf
  die `wachen.json` (Zeilenende): `references/spur-scharf-schalten.md`
- **Eine live geschaltete Spur kommt nicht ins Handeln** (sie ist scharf, es
  passiert aber nichts; „Herzschlag alt" obwohl sie laeuft; die Auto-Freigabe
  oeffnet Fenster ohne Ergebnis; **die Vorschau nennt gar keinen Sperrstand, dann
  findet `nur_fenster_fehlt` nichts und die Auto-Freigabe ist fuer ALLE Spuren
  eines gemeinsamen Kerns tot** — drei getrennte Ursachen, alle gemessen: die
   Zeile steht unter `if g:` (fehlt genau dann, wenn die Spur STARTKLAR ist); der
   Vorschau-Zweig kehrt zurueck, BEVOR irgendwo Sperren genannt werden; oder das
   Werkzeug startet die Spur mit dem FALSCHEN Interpreter, sie stuerzt ab, und ein
   abgestuerzter Lauf liefert keine Zeile (dann je Spur den eigenen venv waehlen);
   die Sperre nennt ein Guthaben ohne BOERSE und
  Waehrung, oder es ist schlicht kein Geld frei) oder **eine Grenze soll erhoeht werden**
  („X auf 100"): `references/live-tor-und-einsatzgroesse.md` — ein Tor muss den
  Zustand des Zweigs lesen, der SCHREIBT (sonst sperrt sich die Spur selbst),
  der Einsatz wird auf das freie Guthaben gedeckelt BEVOR das Freigabefenster
  ihn zeigt, und nach jeder Erhoehung wird nachgerechnet, welches Limit dann
  bindet. **Und „ist dort Geld, das eingesetzt werden kann?" wird GEMESSEN,
  nicht aus dem Kontostand geschlossen**: je Boerse total / gebunden / frei,
  `BalanceEx` traegt kein `available`, `availBal ≈ 0` heisst in Margin
  gebunden, `alle_paare()` liefert Tupel - Abschnitt 9 der Referenz. **Und
  „umschichten" ist ein eigener Ablauf**: Kandidaten gegen die Spurenbuecher
  halten (der Kontostand ist kein freies Kapital), je Paar `ordermin`/`costmin`
  und die gestakte Form pruefen, `validate` vor dem echten Verkauf, danach
  Kontostand und `ClosedOrders` als Zeugen statt der Rueckgabe, dazu die
  Compliance-Sperre (`OKX 51155`, nur am Orderweg erkennbar, der
  Instrumentenabruf listet sie als handelbar) - und danach die WIRKUNG am KONTO
  nachmessen: **ein freigemachtes Guthaben ist keine Zuweisung, ein anderes
  scharfes Instrument mit offenem Fenster liest es im selben Zyklus** -
  Abschnitt 10.
  Ein Live-Einsatz-Limit traegt den WAeHRUNGSNAMEN der Spur
  (`live_einsatz_eur`/`_usd`) - wer nur einen liest, rechnet still mit dem
  Papier-Einsatz weiter, und ein Einsatz unter der Mindestmenge des Instruments
  wird gesperrt statt aufgerundet. **Und ein Instrumentenwechsel mit offenem Buch
  ist ein Buchvorgang**, kein Konfigurationswert: erst das alte Buch zum alten
  Kurs schliessen und spiegeln, dann das Symbol tauschen
  (`references/zweite-boerse.md`, Abschnitt "Instrumentenwechsel mit offenem Buch").
  **Und die Quote ist eine Waehrung, kein Marktplatz**: laeuft eine Spur in
  mehreren Quotewaehrungen (EUR/USDC/EURC), gehoert die Frage „lohnt ein Umtausch
  fuer das Guthaben-Tor?" GEMESSEN, nicht geschaetzt — `kraken/quoten_vergleich.py`
  rechnet die zwei Groessen, die die Entscheidung tragen: DECKUNG (erschliesst die
  andere Waehrung ein Instrument, das es sonst gar nicht gibt?) und SPREAD (Median
  mehrerer Abrufe, je Instrument EIN Paar pro Waehrung) gegen die Umtauschkosten.
  Ein Umtausch lohnt nur, wenn er ein Instrument erschliesst ODER der Markt dort
  enger ist; das Guthaben-Tor in der Paarwaehrung bleibt trotzdem richtig, weil es
  eine Versicherung ist und kein Ertrag. Abschnitt 7 der Referenz.
- **Ein Fremdprogramm soll oefter / mit Hebel / mit Trailing-Stop handeln**
  („kann das nicht oefter?“, „in kurzen Zeitintervallen“, „hoehere
  Trefferchance“): drei Faehigkeiten am CODE feststellen (Takt-Schalter,
  Boersen-Stop gegen Software-Stop, ist das Leverage-Modul ueberhaupt
  aufgerufen), dann die Gebuehr aufs NOMINAL gegen die Margin rechnen (Hebel
  vervielfacht die Gebuehr, nicht die Trefferchance), dann mit dem EIGENEN
  Backtester des Fremdlaeufers messen statt zu argumentieren.
  **Und der Hebel gehoert auf die Boerse, die ihn hat** (Futures, XPERP) — als
  EIGENE Spur mit demselben Signal, nicht als zweite Boerse in der Spot-Spur:
  der neue Boersenname in `spur_buch.orderweg` + der Kontraktnamen-Zweig in
  `venue_inst` (VOR dem Bindestrich-Rueckfall), ganze Kontrakte, Hebel als
  wachen-Feld per Adapter-Setter, `stop_nachziehen` per /editorder als
  Baustein fuer den Trailing an der Boerse:
  `references/fremdprogramm-frequenz-und-hebel.md`, Abschnitt 8
- Uebergeordnete Ansicht ueber ALLE Spuren („GUI fuer meine Handelsspuren"):
  Abschnitt „Ein Fenster ueber alle Spuren".

- **Externe Kennzahlen, die unsere Kerzen nicht hergeben** („Santiment“, aktive
  Adressen, MVRV, Exchange-Zu-/Abfluesse, Social Volume, Dev-Aktivitaet):
  `references/santiment.md` — SanAPI ohne Schluessel, jede Metrik mit eigenem
  Zeitfenster.
- **Schattenbuch-Spur** (dieselbe Signalquelle mit ANDEREN Parametern parallel
  laufen lassen, Hauptbuch bleibt Vergleichsgrundlage — spiegel_knapp/weit):
  `references/schattenbuch-spur.md` — Suffix-Mechanik durch die
  Datei-Konstanten, Launcher je Arm, Verdrahtung inkl. spiegelstand- und
  Bus-Anbindungs-Falle.

- **Ein Prozessfilter, der die EIGENE Kommandozeile trifft, beendet die eigene
  Shell.** `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like
  '*dauerlauf*' } | Stop-Process` matcht sich selbst: Rueckgabe 4294967295,
  kein Prozessoutput, und die eigentliche Arbeit faellt mit um. Das sieht wie
  ein Werkzeugfehler aus und ist es nicht. **Das Muster aus Teilen bauen**
  (`$m = 'dauer'+'lauf'`) und `$_.ProcessId -ne $PID` als zweite Bedingung.
  Danach IMMER die Prozesszahl NACHZAEHLEN, statt auf die Ausgabe zu
  vertrauen - ein gestoppter Lauf, der weiterlaeuft, kostet mehr als die
  Pruefung.
- **`printf` ersetzt nur den ERSTEN `%s`.** `for f in a b; do printf '...%s...%s'
  "$f" > f_$f; done` erzeugt zwei Dateien mit identischem Inhalt, in denen die
  zweite Variable fehlt (leerer Modus, leerer Pfad). Bei mehr als einer
  Stellenhalter-Variable den Wert **so oft** uebergeben, wie Platzhalter daselbe
  sind. Aus demselben Grund: ein Skript, das per printf geschrieben wird, ist
  erst fertig, wenn man es gelesen hat - ein leeres Argument sieht in der
  Ausgabe nach einem Werkzeugfehler aus.
- **Ein Modulname mit Bindestrich ist nicht importierbar.** `tasks-wache.py`
  laesst sich mit `import tasks_wache` nie laden, egal was in `sys.path`
  steht. Der Weg ist der Pfad-Import:
  `spec = importlib.util.spec_from_file_location("x", <pfad>)`,
  `module_from_spec`, `exec_module` - und bei einem Modul mit `@dataclass`
  zusaetzlich `sys.modules[spec.name] = mod` **vor** dem `exec_module`.
- **Ein Skript unter `Agenten/Hermes/scripts` liegt eine Ebene tiefer als sein
  Merk-Ordner.** `MERK = os.path.join(HIER, "cache", ...)` legt einen ZWEITEN
  Cache-Ordner neben den 59 anderen an, verteilt den Stand des Hauses auf zwei
  Orte und wird beim Aufraeumen mitgenommen. Richtig: `os.path.dirname(HIER)`.
  Aus demselben Grund zeigt ein Skript direkt in `Agenten/Handel/` mit
  `HANDEL = os.path.dirname(HIER)` eine Ebene ZU HOCH - die Umkehrung ist
  dieselbe Falle und beide Richtungen kommen im Baum vor.

## Landkarte (nur was zum Arbeiten noetig ist)
- `Agenten/Handel/<spur>/` — je Spur `handeln.py`, `wachen.json` (die Grenzen;
  nur gelesen, einzige Ausnahme `sperre_zu` true→false), `zustand.json`,
  `handelsjournal.csv`.
- `Agenten/Handel/dauerlauf.py` — 24/7-Treiber. Startet je Spur
  `handeln.py --live/--papier` als Unterprozess und **liest dessen Ausgabe**.
- `Agenten/Handel/freigabe.py` — Bestätigungsfenster am Bildschirm, je
  Vorschlag einzeln.
- `Agenten/Handel/freigabefenster.py` — Zeitfenster fürs Handy (`/ja`, `/nein`,
  `/stop`), eigener Zustand in `freigabe_fenster.json`, nie in wachen.json.
- `Agenten/Handel/prognose.py` — Beobachter über den ganzen Markt in **beiden
  Richtungen** (LONG/SHORT), stellt keine Order, kennt keine Spur, Tore je
  Richtung in `prognose.json`.
- `Agenten/Handel/spiegel/` — Papierbuch auf fremdem Feed (OnchainOS):
  `lesen.py` liest nur, `spiegel.py` bucht nach, kein Orderpfad. Muster fuer jede
  weitere Feed-Anbindung: `references/fremdfeed-papierbuch.md`. Zweite Anbindung
  nach demselben Muster: `kopier/` (Pump.fun-REST, Positions-Spiegel statt
  Transaktions-Stream, mit Einlauf-Regel).
- `Agenten/Handel/CryptoPredictions_Wissen.md` — Wissensdatei des
  Handelsverzeichnisses: Datenquellen fuer historische Krypto-Marktdaten,
  Erklaerungen zu CryptoPredictions. Handelswissen gehoert hierher (anhaengen,
  `.bak-JJJJMMTT` vorher), nicht in neue Dateien.
- Interpreter je Spur: Vorgabe `scanner/.venv\Scripts\python.exe` im
  Handel-Ordner, Aufruf aus dem jeweiligen Spurordner. Spur mit EIGENEM venv
  (z. B. nautilus: nautilus_trader liegt nicht im scanner-venv) traegt im
  SPUREN-Eintrag `"python": os.path.join(HIER, "<spur>", ".venv", "Scripts",
  "python.exe")` — `zyklus_spur` UND `nur_fenster_fehlt` muessen
  `d.get("python", PYTHON)` respektieren (beide Stellen: die Vorschau-Frage laeuft
  ueber den zweiten Aufruf). **Ein spurenuebergreifendes Werkzeug, das
  `handeln.py` MEHRERER Spuren importiert, muss den Interpreter je Spur benutzen**
  oder je Spur getrennt aufgerufen werden: ein nautilus-Arm laedt im scanner-venv
  nicht (`ModuleNotFoundError: nautilus_trader`), und der Fehler faellt erst beim
  zweiten Import - nachdem die erste Spur schon gebucht hat. Also je Spur ein
  eigener Aufruf (`--spur <name>`) statt einer Sammelschleife in einem Prozess.

## Prozedur
1. **Lage lesen, nicht erinnern.** `handeln.py --vorschau` mit
   `MAXHIRN_ROUTINE=1` laeuft ohne Fenster und nennt jede geschlossenen Sperre.
   Sperrliste im Code lesen (`sperren_live`), nicht aus dem Gedächtnis.
   **Das gilt auch fuer eine weitergereichte Analyse: ihr Satz ueber das Haus
   („da fehlt uns ein Werkzeug", „dafuer haben wir nichts", „das kann die
   Spur nicht") ist eine BEHAUPTUNG und wird an der Hausquelle gegengemessen,
   bevor darauf hin gebaut, eingeschaltet oder abgeschaltet wird.** Der
   Gegencheck ist billig und hat eine begleitende Marktanalyse an einem
   Handelstag widerlegt: das Instrument war an beiden Hausboersen gelistet,
   die Kursbewegung lag im Fenster der bestehenden Kandidatenspur, und es
   fehlte nur die Beobachtung an einem Tag. Wer die Behauptung uebernimmt,
   baut ein Werkzeug fuer etwas, das es schon gibt — oder laesst eine
   vorhandene Faehigkeit ungenutzt liegen.
   **Ein genanntes Flag, das das Werkzeug gar nicht kennt** („`tagesbericht.py
   --alle`"), ist eine ABSICHT und kein Fehler: erst die echten Argumente des
   Werkzeugs lesen (`--help`, `grep add_argument`), dann die gemeinte Wirkung
   bauen oder liefern. Nicht mit einer Fehlermeldung antworten und die Absicht
   nicht als „unklare Anfrage" zurueckgeben - Max tippt kurz, oft halb.
   **Und der Kontext eines TASK-Eintrags ist eine Momentaufnahme.** Wer eine Aufgabe
   aus `MaxHirn/Archiv/TASKS.md` abarbeitet, messt ZUERST nach, was davon noch offen
   ist: ein Teil kann seit dem Vortag erledigt sein (dann behauptet der alte Text
   einen Mangel, den es nicht gibt), und der vorgeschlagene Weg kann FALSCH sein -
   belegt: ein Eintrag verlangte, ein Gebuehrenfeld in fuenf `wachen.json`
   einzutragen (war seit dem Vortag erledigt), und wollte im zweiten Teil einen
   „Einsatz" ins Journal schreiben, den ein Punktebuch bauartbedingt nicht hat
   (haette eine Positionsgroesse erfunden). Abweichen ist erlaubt und gehoert
   BENANNT: was schon erledigt war, was anders geloest wird und warum, mit Test.
2. **Sichern** (Stufe 1): `.bak-JJJJMMTT` für jede Datei, die angefasst wird —
   auch `wachen.json` und `zustand.json`, wenn ein Testlauf sie berühren kann.
3. **Ändern:** Sperren gehören in `sperren_live()` bzw. die gleichnamige Funktion
   der Spur, nicht verstreut in den Rumpf von `lauf()`.
4. **Ohne Broker testen - mit dem Aufruf, der im TESTKOPF der Spur steht.**
   Hausregel: aus `<spur>/tests` heraus `python -m unittest discover -s . -t .`.
   Ein Aufruf aus dem SPURORDNER (`cd <spur> && … discover -s tests -t tests`)
   setzt das Arbeitsverzeichnis in `sys.path`; die Testkoepfe ziehen ihre eigene
   Spur aber mit `if p not in sys.path: sys.path.insert(0, p)` nach, und weil
   die Spur schon drinsteht, bleibt `scanner/` vorn: `import handeln` holt
   `scanner/handeln.py`. Symptom: `AssertionError: falsches handeln: …\scanner\
   handeln.py`, `module 'handeln' has no attribute <X>` und ein halbes Dutzend
   roter Tests an Code, den niemand angefasst hat. Deshalb in Testkoepfen die
   eigene Spur IMMER vorne einsetzen - Pfad vorher entfernen
   (`while p in sys.path: sys.path.remove(p)`, dann `insert(0, p)`), sonst wirkt
   das `if p not in sys.path` als Bremse gegen die eigene Reihenfolge.
   Interpreter **absolut** angeben (z. B.
   `C:/…/Handel/scanner/.venv/Scripts/python.exe`): ein relativer Pfad bricht nach
   dem `cd`, und die leere Ausgabe sieht wie „keine Tests“ aus statt wie ein
   Fuer den Live-Pfad `pruefe_einstiege`/`pruefe_ausstiege` per Lambda
      stilllegen, Fenster regulaer oeffnen, Lauf starten, Zustandsdateien
      vorher/nachher per Hash vergleichen. Ein Test darf `markt_kauf` nie erreichen.

      **JEDER Test, der eine Spurenfunktion mit Journalaufruf ruft, schreibt
      zuerst `journal` im geladenen Modul um.** Das ist die teuerste Falle der
      ganzen Hausregelkette und sie ist zweimal eingetreten, weil sie als
      „Papierlauf braucht kein SCHREIBEN=False" im Kopf lag: getestet wird
      `pruefe_einstieg`/`pruefe_ausstiege`, und DAS journalisiert in die echte
      Datei der Spur - nicht in eine Tempdatei. Gemessener Schaden: 192 Zeilen
      in vier echten Journalen, alle am synthetischen Kurs erkennbar (zwei
      Spuren 57 und 45 Zeilen auf 239,65, eine auf 344,65), weil der Test
      dieselbe Spurenfunktion fuer vier Spuren in einer Schleife aufrief.
      Das Muster, das gilt:

      ```python
      mod = lade(spur)                      # handeln.py als Modul, nicht importieren
      geschrieben = []
      mod.journal = lambda **kw: geschrieben.append(kw)   # VOR dem ersten Aufruf
      mod.pruefe_einstieg("BTC-USDT", kerzen, z, w, 1.0)
      ```

      Zwei Dinge gehoeren dazu, sonst ist der Test gruen aus Faulheit:
      **Dateigroesse des echten Journals vorher/nachher vergleichen** (bricht die
      Regel, ist das der Fehler), und **beleegen, dass ueberhaupt protokolliert
      wurde** (`assertTrue(geschrieben)`) - ohne diesen zweiten Teil prueft der
      Test nichts und meldet Erfolg. Beim Aufraeumen gilt: die Zeilen sind am
      synthetischen Kurs erkennbar (Zeitstempel UND Preis), das Zustandsfile
      bleibt unberuehrt, Sicherung je Spur, danach `spiegelstand.py` (die
      Bedingung-4-Pruefung zeigt die Abweichung sonst als Befund).
   Eine geänderte Ausgabezeile **rendern statt lesen**: die `print`-Anweisung per
   `ast.get_source_segment` holen, mit `ast.parse`/`compile` übersetzen, mit
   Beispieldaten ausführen. Eine Formatprüfung im Kopf ist kein Nachweis, und
   `ast.parse` prüft nur Syntax.
   **Rote Tests vor der Deutung gegenproben.** Den EIGENEN Anteil stashen
   (`git stash push <eigene Pfade>`), dieselben Tests erneut laufen lassen, dann
   zurueckholen (`git stash pop`). Fallen sie ohne die eigene Aenderung genauso,
   ist der Befund vorbestehend — im Bericht als solcher benennen, nicht
   mitreparieren. Danach im Arbeitsbaum per `grep` pruefen, dass die eigenen
   Aenderungen wieder da sind: die Stash-Liste ist kein Beleg (mehrere
   Push-Aufrufe koennen in EINEM Eintrag landen, der zweite `pop` meldet dann
   "No stash entries found", obwohl alles zurueck ist).
   **Bleibt die Gegenprobe GRUEN, ist der eigene Code nicht auf dem Weg — er ist
   toter Code.** Nach jeder Aenderung an einem Rechenweg die Regel stilllegen und
   denselben Test erneut fahren: faellt er nicht, hat die Baustelle nie etwas
   getan. Gemessen an einer Verdichtung in einer Auswertung: der Test blieb gruen,
   weil die Paarung die Mehrfachzeile ohnehin richtig aufloest — der Code wurde
   entfernt, weil toter Code in einem Rechenweg eine Last ist und kein Beleg. Und
   **eine Regel, die man selbst gebaut hat, belegt man nicht durch das gruene
   Ergebnis ihrer eigenen Tests**, sondern durch die stillegelegte Fassung.
   - **Ein Test, der die Nicht-Existenz einer Spuren-Datei behauptet
   (`assertFalse(pfad.exists())`), faellt, sobald die Spur einmal echt gelaufen
   ist** — er friert den Zustand vor dem ersten Zyklus ein. Statt der Abwesenheit
   pruefen, dass der Live-/Vorschau-Pfad NICHTS schreibt: Dateigroessen vor und
   nach dem Aufruf vergleichen.
5. **Versionieren.** `.gitignore` ist eine **Whitelist**. Jede neue
   `.py`/`.json`/Testdatei braucht eine eigene `!`-Zeile, sonst landet sie still
   nicht im Verlauf — es sei denn, eine Glob-Zeile deckt sie schon
   (`!Agenten/Handel/*.py`, `!Agenten/Handel/tests/*.py`).
   `git add --dry-run <ordner>` zeigt, was wirklich in den Commit kaeme.
   - **Ein neuer Spurordner ist zunaechst komplett unsichtbar.** `git status
     --porcelain --ignored <ordner>` zeigt ihn als `!!`; `git status` allein
     schweigt, das `git add` tut nichts und meldet nichts. Vier Eintraege je
     Spur sind das Muster (`!…/<spur>/*.py`, `*.md`, `*.json`, `tests/*.py`) —
     damit war der Ordner freigegeben, ohne eigene Ordnerzeile. Wirkt eine
     Dateizeile trotzdem nicht (git steigt in einen ignorierten Ordner nicht
     hinab), erst `!<ordner>/` setzen, danach greifen die Dateizeilen.
     `zustand.json`, `handelsjournal.csv` und `.bak-JJJJMMTT` bleiben draussen:
     die Sperrliste weiter unten gewinnt als spaetere Regel, und `.bak-JJJJMMTT`
     endet nicht auf `.json`. Gegenprobe: `git diff --cached --name-only` darf
     keine dieser drei enthalten.
   - Eine solche Zeile ohne `!` ist eine **Sperre** — sieht wie eine Freigabe aus,
     bewirkt das Gegenteil; mehrfach eingefuegte gleiche Bloecke sind dasselbe
     Symptom. Gegenprobe zweimal: `git check-ignore -v <pfad>` nennt die
     entscheidende Regel, `git status --porcelain <ordner>` muss die neuen Dateien
     als `??` zeigen.
   - Versionierte Textdateien nie komplett neu schreiben: Fassung aus `HEAD` holen
     (Verlauf LF, Arbeitsbaum gern CRLF), nur die gewollten Stellen ersetzen;
     `git diff --stat` muss die geaenderte Zeilenzahl zeigen, nicht die ganze Datei.
     **Flippt ein Schreibwerkzeug die Endungen** (ein Patch-Weg gibt die Datei ueber
     seinen eigenen Editor zurueck: LF rein, CRLF raus), zeigt der Diff plotzlich die
     GANZE Datei - dann die Endungen aus der Vorversion wiederherstellen
     (`b.replace(b"\r\n", b"\n")`) und in einem FOLGE-Commit sichern (nie force-push);
     der Netto-Diff gegen `HEAD~1` muss genau die gewollten Zeilen zeigen.
   - In einem Baum mit mehreren Sitzungen gehoert in den Commit eine **explizite
     Pfadliste**, nie `git add -A <ordner>`: im Handel-Baum lag uncommittete
     Fremdarbeit (`spiegel/spiegel.py`, Ablehnungs-Protokollierung), die so unter
     die eigene Commit-Nachricht rutschte. Nach dem Commit `git show --stat` gegen
     die Absicht halten. Ist es passiert: `git reset --soft HEAD~1`,
     `git restore --staged <fremddatei>`, erneut committen, die Fremdaenderung
     unangetastet lassen und im Abschlussbericht nennen (braucht eine Entscheidung
     von Max, keine stille Mitnahme).
   - **Fremdes im SELBEN Dokument** (geteilte Dateien wie `MaxHirn/Archiv/TASKS.md`)
     trennt pfadgenaues Stagen nicht mehr. Dann ist Mitnehmen erlaubt, aber BENANNT:
     die fremden Eintraege in der Commit-Nachricht nennen. Stilles Mitnehmen ist der
 Fehler, nicht das Mitnehmen. **Und vor dem Patchen `git diff --numstat
 <datei>` lesen:** traegt die Datei schon FREMDE uncommittete Aenderungen,
 die groesser sind als die eigene (gemessen: 28 fremde Zeilen gegen 3
 eigene), gehoert die eigene Zeile NICHT hinein - sie wandert an einen Ort,
 der der eigenen Arbeit gehoert (die passende `references/`-Datei, ein
 eigener Abschnitt), und der Grund steht im Bericht. So wird weder fremde
 Arbeit mitgenommen noch die eigene verloren.
   - **Traegt der GETEILTE Index fremde Vormerkungen, mit eigenem Index committen**
     (`git diff --cached --numstat` zeigt sie): `GIT_INDEX_FILE=<cache>/idx_<thema>`
     setzen, `git read-tree HEAD`, nur eigene Pfade `git add`, `git commit -F <datei>`
     (die Meldungsdatei als NATIVEN `C:/…`-Pfad angeben - `git commit -F` findet
     einen MSYS-Pfad unter `/tmp` nicht und der Commit unterbleibt still). Danach
     PFLICHT: `unset GIT_INDEX_FILE` und dieselben Pfade im ECHTEN Index nachziehen -
     sonst steht die Datei als `MM` (Index alt, HEAD neu) und ein fremdes
     `git commit` ohne Pfadangabe setzt den ALTEN Stand wieder ein. Eine Datei, die
     die andere Sitzung nach dem eigenen Commit WEITERbearbeitet hat, nicht
     nachziehen (`git reset -q HEAD -- <pfad>`).
   - **Der Push scheitert, weil eine ANDERE Sitzung den Baum offen haelt** — und
     die fremden Dateien fasst man nicht an. `git pull` und `git pull --rebase`
     verweigern beide mit "You have unstaged changes". Der Weg, der die fremde
     Arbeit unveraendert laesst: `git pull --rebase --autostash origin master`.
     Git legt die fremden Aenderungen vor dem Rebase in einen Autostash und
     legt sie danach unveraendert zurueck ("Applied autostash"). Gegenprobe
     danach Pflicht: `git status --porcelain` muss dieselbe Zeilenzahl und
     dieselben Pfade zeigen wie vorher — so wird belegt, dass nichts von der
     fremden Sitzung mitgenommen oder zurueckgesetzt wurde. Wer stattdessen
     selbst committet, nimmt deren Arbeit in die eigene Meldung.
   - **Eine 0-Byte-`.git/index.lock` ist ein Wrack, kein laufender Commit:** Alter
     messen und echte `git`-Prozesse zaehlen (`Get-CimInstance Win32_Process`;
     `fsmonitor`-Daemons laufen immer und beweisen nichts), dann UMBENENNEN
     (`mv .git/index.lock .git/index.lock.verwaist-JJJJMMTT`), nie loeschen. Eine
     FRISCHE Sperre heisst warten und denselben Aufruf wiederholen; scheitert das
     `git add` daran, sind die eigenen Dateien danach `MM` - siehe voriger Punkt.
   **Und beim Ersetzen eines Blocks in einer Liste
     (TASKS-Eintrag, Klassenblock) nie per Lookahead auf ein Merkmal des Nachbarn
     arbeiten** - ein Muster `- [ ] **T-…` endet am naechsten UNERLEDIGTEN Eintrag,
     ein erledigter (`- [x]`) faellt mit in den Treffer und ist danach weg. Stattdessen
     ueber ZEILENINDIZES ersetzen und die Menge der IDs VORHER/NACHHER vergleichen
     (`set(re.findall(...))`, Differenz = genau die eigene Aenderung); im Zweifel den
     Block aus `HEAD` zurueckholen.
   - Der gelesene Stand ist eine MOMENTAUFNAHME: vor dem Aendern
     `diff <eigene .bak> <datei>` — nur diese Differenz zeigt, was seit dem Lesen
     dazukam; eine Meldung "Datei wurde von einer anderen Sitzung geaendert" ist
     kein Beleg, weder fuer eine Aenderung noch fuer deren Fehlen.
   - Wird im selben Zug eine Vault-Notiz geaendert (`MaxHirn/Wissen/*.md`), gehoert
     ihr `updated:`-Feld auf den heutigen Tag: Block 10c der Systempruefung meldet
     jede uncommittete Notiz mit altem `updated:` als offenen Punkt.
6. **Abschliessen, nicht nachfragen.** Ein „Ja" oder „Luecken schliessen" auf eine
   Empfehlung heisst: im vollen Umfang umsetzen (Code, Tests, Doku, Commit,
   Aufraeumen) — nicht nachbestaetigen lassen.
   **Mehrere Spuren, knappes Kapital: die Reihenfolge ist eine Entscheidung von
   Max, nicht eine technische.** Sagt er "<Spur A> zuerst, andere niedriger
   priorisieren aber bauen", heisst das: A vollstaendig bauen und scharf machen
   (sie nutzt das vorhandene Kapital), die uebrigen trotzdem bauen — nur in
   niedrigerer Reihenfolge, nicht weglassen. Vor dem Bauen den KAPITAL-Bezug je
   Spur pruefen (welche Waehrung liegt frei, welche Spur kann sie nutzen) und
   die Prioritaet daran festmachen; eine Spur, deren Quotewaehrung auf dem Konto
   fehlt, bleibt strukturell gesperrt, bis das Guthaben da ist — das ist kein
   Grund, sie nicht zu bauen, nur ein Grund, sie spaeter scharf zu schalten.
   Abschlussbericht in zwei Teilen:
   **was jetzt nachweisbar anders ist** (mit dem Befehl, der es zeigt —
   Systempruefung, `spiegelstand.py`, Testlauf, Logzeile) und **was absichtlich
   NICHT angefasst wurde** — fremde Spuren, laufende Prozesse, Altbestaende ohne
   Ziel, dazu jeder Wert, der eine Entscheidung von Max braucht (`gebuehr_taker`,
   Herzschlag-Grenzen, stillgelegte Pfade). Offene Entscheidungen aussprechen,
   nicht stillschweigend mitentscheiden. Entscheidet Max einen solchen Wert,
   gehoert die Entscheidung mit Datum und Ruecknahme-Bedingung an beide Orte
   (Erklaerfeld in `wachen.json`, z. B. `_gebuehren_abo`, UND die Wissensnotiz) —
   eine Kostensenkung ohne Ruecknahme-Regel zaehlt spaeter Runden fuer die
   Freigabe, die live nicht gelten. Und vorher lesen, welcher Satz ueberhaupt
   gelesen wird (`gebuehr_maker` liest `handeln.py` nicht): ein geaenderter Wert,
   den niemand liest, ist keine Aenderung. Und ein Wert, der nur im ERSTLAUF
   gelesen wird, wirkt nicht auf den laufenden Zustand: die Gitter-Leiter entsteht
   nur bei `neu = not z.get("leiter")` und wird danach nie verschoben — ein
   geaendertes `stufen` gilt erst auf eine frische Leiter. Vor jeder
   Parameter-Aenderung nachsehen, WANN der Wert gelesen wird, und die Wirkung im
   Bericht auf diesen Zeitpunkt datieren.
## Pitfalls
Die Landkarte der 103 Punkte steht in
`references/pitfalls-landkarte.md` (ein Satz je Punkt), die vollstaendigen
Lektionen mit Begruendung und Messwerten in `references/pitfalls.md` -
gleiche Nummer. Vor jeder Aenderung an einer Spur den Punkt lesen, der
greift; die Kurzfassung ersetzt die Begruendung nicht. Beide Dateien
liegen getrennt, weil die Landkarte (22.889 Zeichen) in dieser Datei nur
912 Zeichen Luft liess und damit jeden weiteren Patch blockierte.

## Welche Daten eine Sperre liest

Jede Bedingung, die eine Spur sperrt oder entsperrt, legt ausdrücklich fest,
auf welcher Datenmenge sie rechnet — das ist eine Entscheidung, keine
Nebenbedingung. Geltende Regel: eine **Betriebsstoerung** (Herzschlag-
Zwangsschluss, Notaus) ist keine Handelsentscheidung und darf eine
Erwartungswert-Sperre nicht auslösen. Die **Kapitalkurve** (Drawdown, Ratsche,
Halbierung, Kill-Switch) rechnet weiter auf ALLEN Buchungen — eine Stoerung ist
eingetragen und hat Geld bewegt.

- **Genau EIN Feld trägt die Zahl, auf der die Sperre beruht.** Heißt es
  `rollierender_ev`, dann ist das die Zahl der Bedingung; die Zahl über alle
  Buchungen bekommt einen eigenen Namen (`rollierender_ev_alle`). Ein Feld mit
  zwei Bedeutungen ist der Fehler: Anzeige und Sperrtext lesen dasselbe Feld,
  und hinterher kann niemand sagen, worauf gesperrt wurde.
- **Die Umstellung gehört in ALLE Wachenfassungen** (scanner, xperp, kraken,
  orbk) — jede hat ihre eigene `lage()`. Eine vergessene Fassung sieht nicht
  wie ein Fehler aus, sondern wie eine Spur mit anderen Zahlen.
- **Ein Test ohne Gegenprobe bleibt stillschweigend grün.** Der Test muss so
  gebaut sein, dass er mit der ALTEN Rechnung fehlschlägt: mehrere echte
  Runden mit Gewinn gegen eine Handvoll Zwangsschlüsse mit Verlust, so dass
  die alte Zahl negativ und die neue positiv ist — plus eine Zusicherung auf
  den alten Wert (`assertLess(s["rollierender_ev_alle"], 0)`).
- **Am lebenden System nachweisen, nicht nur im Test:** je Spur
  `handeln.py --wachen` fahren und die Zeile der Bedingung aus dem echten
  Journal zeigen (Spur, Zahl, ob gesperrt). Erst das belegt, dass die
  Umstellung wirkt — und deckt auf, wo eine Spur unter der Messgrenze liegt
  (`n/a`, zu wenig Handelsrunden).

Rezept mit Testgerüst, Journal-Formen je Spur und Prüfkommandos:
`references/sperren-datenbasis.md`

## Einzelne Spuren im Detail

Die datierten Kapitel je Spur (SWAP anbinden, Omniquant, Kraken wieder im
Dauerlauf, Gitter, Nautilus, ORB-Grundregel) stehen in
`references/spuren-einzeln.md` - Nachschlagewerk, nicht Prozedur. Nur laden,
wenn genau diese Spur ansteht.

## Boersendaten und Orderflow

Detaillierte API-Fallen fuer OKX/Kraken-Kerzen und Orderflow (Rubik/CVD) stehen in `references/boersen-datenzugriff.md`. Kernregeln: `okxf.kerzen()` unbekannte Instrumente leere Liste (len pruefen); Kraken-OHLC max 720 Kerzen ohne Rueckwaerts-Pagination (M15 7,5 Tage); 4h-CVD nur ueber `/rubik/` (nicht aus dem Tape); der Host gehoert zu EINEM
Zugang — `OKX_BASE` muss die API sein (`https://www.okx.com` beim globalen,
`https://eea.okx.com` beim EEA-Konto), nie `my.okx.com`; Rubik-429 wird nicht
wiederholt; Kaufkraft ist `availEq` je Waehrung (nicht `eq`), boersenseitige
Stops stehen nur in `trade/orders-algo-pending`. **Schluessel UND Host aus
derselben Quelle lesen** — ein `OKX_BASE` aus der Prozessumgebung neben einem
Schluessel aus der Registry signiert gegen die falsche Boerse und liefert
`50119`/`50101`. **Vor dem Anbinden einer Spur die Warmlauf-Laenge ihres Indikators gegen die Abrufgrenze rechnen** — ein Indikator, der mehr Historie braucht als der Abruf liefert, ist nicht ungenau, sondern still tot (Details und die OKX-Grenzen: `references/boersen-datenzugriff.md`).

## Ein Fenster ueber alle Spuren (Handelszentrale, 13.09.2026)
Die Regeln liegen in `references/handelszentrale-fenster.md` - dort auch die
Faelle, die sich beim Bau einer zweiten Liste, beim doppelten Modulnamen und
beim Start von Hand gezeigt haben. Diese Zeile ist der Anlass, die Datei zu
lesen; die Datei ist nicht bei jeder Spur-Runde Pflicht.
## ORB-Grundregel: ein Trade je UTC-Tag, und das Merkzeichen muss den Ausstieg ueberleben
- **Ein Tagesschutz, der nur die offene Position anschaut, ist keiner.** `_schon_gehandelt_heute` prueft nur `z["position"]["tag"]`; der Ausstieg entfernt die Position, damit war die Sperre im selben Zyklus wieder offen, und derselbe Breakout (gleiche Kerzen, gleiche Range) stieg sofort erneut ein: Endloskreis Ausstieg→Wiedereinstieg. Symptom-Kette (Befund 13.09.2026, orbk): Journal fuellt sich mit byte-identischen Ausstiegszeilen (51 an einem Tag), die Position "haengt" in zustand.json (wird ja nie wirklich geschlossen), und weil der Dauerlauf-Filter `ausstieg` case-insensitiv faengt, geht jede Viertelstunde eine AUSSTIEG-Meldung nach Telegram. Fix: Merkzeichen `zuletzt_gehandelt_tag` im Zustand, beim EINstieg gesetzt (nicht beim Ausstieg: eine gestern eroeffnete, heute geschlossene Position darf heute neu einsteigen), geprueft in `_schon_gehandelt_heute` nach dem Pop. Regressionstest laesst den echten `lauf()`-Zyklus Ende-zu-Ende laufen (Temp-Zustandsdateien, `_jetzt`/`_letzter_kurs`/`_wachen`/`kerzen_quelle` gepatcht) plus Gegenprobe ohne Merkzeichen, die den Fehler reproduziert — ein Test, der den Fix nur mitlaufen laesst, beweist nichts.

## Werkzeugfallen am Host
- **`vision_analyze`/`video_analyze` erreichen lokale Dateien NUR aus dem Media-Cache unter HERMES_HOME** (`video_cache/`, `temp_vision_images/`, `image_cache/` — Pfade anderswo heissen "media file not found"). Selbst aus dem Cache schlaegt der Anbieter mit 404 ("Couldn't find that, sorry.") fehl, wenn der OmniRoute-Router Bildinhalte nicht weiterreicht — der lokale Vision-Weg ist dann tot. Fallback fuer Video: ffmpeg-Frames ziehen (`ffmpeg -i v.mp4 -vf fps=1 frame_%02d.jpg`) und per Windows-OCR auslesen (`Windows.Media.Ocr.OcrEngine` via PowerShell, offline, kein Key) — fuer Trading-Dashboards reicht das (Zahlen + UI-Labels). Skripte: `Agenten/Hermes/cache/ocr_frame.ps1`.
- **Scratch- und Probe-Dateien nicht nach `Werkstatt/` legen.** `Werkstatt` ist
  eine Junction auf `O:`; `write_file` loest den Pfad auf sein echtes Ziel auf und
  verweigert ihn (`outside HERMES_WRITE_SAFE_ROOT`). Ablage fuer Wegwerf-Skripte:
  `Agenten/Hermes/cache/` (innerhalb BrainFiles, nicht versioniert). Zwei Vorlagen
  dort: eine **Filterprobe**, die nachbildet, was `dauerlauf.zyklus()` aus der
  Spur-Ausgabe nach Telegram schickt (`verkauf`, `stop`, `KILL`, `gesperrt`,
  `ausstieg`) — zeigt vor dem Commit, ob eine neue Ausgabezeile Spam erzeugt; und
  eine **Verbraucherprobe**, die `dauerlauf.Lauf.nur_fenster_fehlt(spur, d)`
  direkt aufruft und `None` erwartet, wenn die Spur keinen Live-Pfad hat. Beides
  gegen eine Spur laufen lassen, nicht gegen die Vermutung.
- **Backslashes in Windows-Pfaden nicht am Tool-Ergebnis zaehlen.** Die Ausgabe
  kommt JSON-kodiert zurueck, jeder Backslash erscheint doppelt: eine Datei mit
  `'Handel\spiegelstand.py'` zeigt in der Antwort `Handel\\spiegelstand.py`. Wer
  daraus zwei Backslashes schliesst und mit vier ersetzt, trifft nichts (Assertion
  `count == 1` schlaegt fehl — oder schlimmer, sie trifft und schreibt Unsinn).
  Gegenmittel: Zielzeile mit `repr()` ausgeben und **Zeile fuer Zeile** ersetzen
  (`split("\n")`, Praefix suchen, Zeile tauschen), statt im ganzen Text.
- **Terminal-Ausgabe nicht als Beweis fuer exakte Zeichen nehmen (Diffs, JSON mit
  Sonderzeichen, ein Commit-Hash, ein Textmuster-Treffer) — bei Zweifel in eine
  Datei schreiben und mit `read_file` zurueckholen.** Die gerenderte
  Tool-Antwort kann einzelne Zeichen unterdruecken oder verschieben, ohne dass
  die zugrundeliegenden Daten falsch sind. Ein kleines Diagnoseskript, das sein
  Ergebnis als JSON in eine Datei schreibt statt es zu drucken, und per
  `read_file` gelesen wird, zeigt den echten Stand zuverlaessig — dieselbe
  Disziplin wie bei den doppelten Backslashes, nur fuer den allgemeinen Fall.
  Vor jeder Aussage "das Muster existiert nicht" oder "dieser Commit/Wert ist
  da" erst so gegenpruefen, statt der gedruckten Ausgabe zu glauben.
- **Ein Leser kann am FALSCHEN Dienst derselben Sorte haengen — Adresse pruefen,
  bevor der Code verdaechtigt wird.** Laeuft derselbe Dienst mehrfach (Altlast-
  Container neben dem neuen, Spot neben Futures, Demo neben Live), traegt jede
  Instanz ihre eigenen Zugangsdaten im SPEICHER: dieselben Zugangsdaten gegen
  beide Adressen probieren, dann ist die Sache entschieden. Fingerabdruck eines
  solchen Falls: auf EINEM Port antwortet der oeffentliche Endpunkt (200), der
  geschuetzte mit 401 — der Dienst lebt also, aber es ist ein anderer. Eine
  Einschraenkung des Live-Tests (`skipUnless` auf diesen Dienst) verschiebt das
  Problem nur: sie laeuft ueber dieselbe Adresse und meldet 'laeuft nicht',
  solange die Altlast antwortet.
- **Laufzeit ist Teil der Funktion einer Wache.** Eine Wache, die teurer ist als
  ihr Nutzen, wird abgeschaltet - und ist damit blind, ohne dass irgendwo ein
  Fehler steht. Deshalb nach jeder Wache die Laufzeit messen, nicht nur die
  Ausgabe: eine Datei-Waechter ueber den ganzen Handel-Baum brauchte 4 min 40
  pro Lauf, weil der gaengige Aufrufer `rglob('*')` nimmt und JEDE Datei liest -
  bei 15-Minuten-Takt ist das 18 % der Maschinenzeit fuer eine Kontrolle. Ein
  Endungsfilter im Aufrufer half nicht, gefressen hat das die venv-Bestaende.
  Der Weg ist ein eigener, schmaler Aufrufer (`os.walk` ueber die Orte, an
  denen der Schaden tatsaechlich entsteht, mit Ablageordnern in der
  Ausnahmeliste), der den gleichen Bestand in 0,8 s erfasst. Und **eine
  Ausnahme in der Ablaufliste kann nur die Sicht verengen, nie eine Datei
  ausblenden, die vorher gemeldet wurde** - das ist das Argument, wenn eine
  Liste gewachsen ist. Erschreckend, wenn eine teure Wache als ERFOLG
  gelesen wird, weil sie fehlerfrei schweigt.
- **Das Host-PowerShell-Werkzeug hat eine harte Zeitgrenze (~300 s).** Eine
  rekursive Größenmessung über einen großen Baum reißt sie. Stattdessen
  vorher/nachher `Win32_LogicalDisk.FreeSpace` messen oder je Ordner einzeln — der
  Zuwachs ist die belastbare Zahl.
- **Nicht rekursiv ueber die Repo-Wurzel suchen.** Ein `grep -r`/`find` ab
  `BrainFiles/` laeuft ueber die Junctions nach `O:` (Modelle, Werkstatt), in
  jedes `.venv` und durch Millionen Fremdzeilen — der Aufruf reisst die
  Zeitgrenze, ohne ein Ergebnis zu liefern. Stattdessen: die Zieldatei nennen
  oder `search_files`/`read_file` auf ein ENGES Verzeichnis zeigen lassen. Beide
  brauchen ABSOLUTE Pfade: die Sitzung startet in `Agenten/Hermes`, ein relatives
  `Agenten/Handel` endet in "Path not found" — das liest sich wie ein leeres
  Ergebnis. Groessen- und Namenszaehlungen ueber einen Baum per `execute_code`
  rechnen, nicht per Shell.
- **Ein Befehl, den MAX ausfuehren soll, muss in SEINER Shell laufen (PowerShell).**
  `grep`, `ls`, `cat` und bash-`for`-Schleifen gibt es dort nicht — der Aufruf
  scheitert mit „Der Begriff "grep" wird nicht als Name eines Cmdlets … erkannt",
  obwohl die geprueften Dateien laengst stimmen; er muss nachfragen, statt das
  Ergebnis zu sehen. Deshalb: einzeilige Nachweise SELBST fahren und nur das
  Ergebnis zeigen, und wenn er selbst laufen soll, `Select-String` /
  `Get-ChildItem` / `Get-Content` nehmen — den Befehl vorher einmal echt in
  PowerShell ausprobieren. Die Probe aufs Exempel gehoert in die Antwort
  (`Select-String -Path <datei> -Pattern <wort>`), nicht in bash-Schreibweise.
- **`Get-FileHash` gibt es in dieser PowerShell nicht** (5.1.26100.9444:
  `Get-Command Get-FileHash` liefert nichts, der Aufruf bricht mit "Die Benennung
  ... wurde nicht als Name eines Cmdlet ... erkannt" ab). Ein Pruefblock, der
  daran scheitert, liest sich im Bericht wie "nichts gefunden" — der
  Regelwerk-Block der Systempruefung lief so wochenlang nie. Hashing ueber .NET:
  `[System.Security.Cryptography.SHA256]::Create()` +
  `[System.IO.File]::ReadAllBytes($pfad)`. Bei jedem neuen Pruefblock pruefen, ob
  alle benutzten Cmdlets existieren.
- Windows begrenzt die Kommandozeile (~32k Zeichen): ein großer
  PowerShell-Here-String scheitert mit `WinError 206`. Lange Dateien in Teilen
  schreiben (`Set-Content`, dann `Add-Content`) oder einen kleinen Applier die
  Nutzlast aus einer Datei holen lassen. Dasselbe fuer mehrzeilige Shell-Einzeiler
  (Schleife mit mehreren Befehlen): sie werden als „inline command payload“
  abgewiesen, BEVOR sie laufen — ein Retry mit demselben Text scheitert identisch.
  Schritte getrennt aufrufen oder das gespeicherte Skript mit `bash <pfad>`
  ausfuehren.
- **Ein zu grosser Schreibvorgang bricht mitten im Stream ab, nicht mit einem
  Fehler.** Ein `write_file` mit sehr viel Nutzlast (grob ueber 8K Token
  Argumente) laeuft in einen Stream-Timeout, und die Aktion wurde dann NICHT
  ausgefuehrt — ein Retry mit demselben Text scheitert identisch. Grosse Dateien
  in mehreren kleineren Aufrufen schreiben oder den Kern schreiben und den Rest
  per `patch` anhaengen. Dieselbe Grenze gilt fuer lange Tool-Einzeiler.
- **Ein Suchanker mit escapten Anfuehrungszeichen trifft nicht.** Beim Aendern
  eines JSON-Kommentarfelds (`"_feld": "... \"wort\" ..."`) bricht der Patch
  mit „Escape-drift detected" ab, weil der Anker ein `\"` enthaelt. Anker ohne
  escapte Zeichen waehlen — einen Teilstring ohne Anfuehrungszeichen (die
  Satzhaelfte, einen Zahlenwert) — und den Rest in einem zweiten Aufruf
  ersetzen. Gilt auch fuer Anker mit Backslash-Pfaden: erst `repr()` der
  Rohzeile zeigen, dann das Muster bauen. **Und fuer den ERSATZtext:** ein
  escaptes Anfuehrungszeichen im `new_string` (`\"Freigabefenster\"`) landet
  WOERTLICH als `\"` in der Datei — kein Syntaxfehler, nur falscher Text an
  einer Stelle, die niemand mehr ansieht. Nach jedem Patch, dessen Ersatz
  Anfuehrungszeichen enthaelt, die betroffene Zeile per `read_file` lesen und
  den Diff ansehen; Korrektur ist ein zweiter Patch mit dem Zeichen ohne
  Backslash.
- **Der fuzzy Patch wendet Tippfehler im old/new-String trotzdem an.** Ein
  vertippter JSON-Key (`kill_switch_gesamtmt_usd` statt `gesamt_usd`) oder
  Wert (`papier_faktor 6.0` statt `4.0`) wird vom Matcher als "aehnlich"
  akzeptiert und landet in der Datei - der Fehler ist erst nach dem Schreiben
  sichtbar. Nach JEDEM JSON-Patch den Schluessel/Wert per `read_file`
  verifizieren (nicht der Diff-Ausgabe glauben) und `json.loads` laufen
  lassen. Bei wiederholtem Vertippen: den Block einmal komplett mit exaktem
  old/new neu schreiben statt weiter zu flicken.
- **Ein Patch in einem EINGERUECKTEN Block kann die Einrueckung verschieben.**
  Beim Ersetzen eines mehrzeiligen Blocks innerhalb einer Funktion hat der
  Matcher den Ersatz um vier Leerzeichen nach rechts gestellt (die alten Zeilen
  waren ungleichmaessig eingerueckt) - Ergebnis `IndentationError` in einer
  Datei, die vorher lief, und zwei Reparaturversuche per Patch scheiterten
  erneut, weil der Anker danach nicht mehr eindeutig war. **Ab dem ersten
  `IndentationError` nicht weiterpatchen:** die Datei KOMPLETT lesen und den
  Block byte-genau per Python ersetzen (`text.index(anfang)` bis
  `text.index(ende)`, Ersatz davor einsetzen, `ast.parse` zur Kontrolle) oder
  die Datei mit `write_file` neu schreiben. Bei mehrzeiligen Ersetzungen in
  eingeruecktem Code vorher `repr()` der Zielzeilen ansehen, damit der Anker
  die echte Einrueckung trifft.
  **Dieselbe Drift trifft LISTENBLOECKE, und dort verliert sie still eine
  Zeile:** ein Patch am Kopf eines Eintrags hat die Einrueckung verschoben UND
  die Anschlusszeile entfernt - ohne Fehlermeldung, sichtbar erst beim Lesen des
  Blocks. Ein zwe
- **Ein Block-Ersetzungsskript kann EINFUEGEN statt ERSETZEN.** Wenn der
  Schnittmarker am Anfang des neuen Blocks sitzt statt am Anfang des alten,
  stehen am Ende **zwei Definitionen** derselben Funktion in der Datei, und in
  Python gewinnt die **SPAETERE**. Der neue Code laeuft nie, ohne dass irgendwo
  ein Fehler steht - der Lauf zeigt den alten Weg, und man pflegt am Code zu
  arbeiten, der gar nicht benutzt wird. Dagegen zwei billige Pruefungen: vor dem
  Schreiben `text.count("def <name>(") == 1` im **Speicher** erzwingen, und
  `ast.parse(neu)` VOR dem Schreiben laufen lassen. Beides hat hier mehrfach
  eine bereits kaputte Datei verhindert.
- **Eine Kontrollzeile, die zwei Nullen vergleichen kann, ist keine Kontrolle.**
  `abs(summe - kontrollwert) < 0.01` ist gruen, wenn beide Null sind - und
  beide waren Null, weil der Parser die falsche Ebene las. Ein echter
  Kontrollwert kann nicht Null sein (die Kontostand-Zahl selbst, die
  Zeilenzahl, der nichtleere Text). Sonst **bestaetigt** die Kontrolle den
  Fehler, statt ihn zu finden, und genau so wurde ein Konto mit ueber 900
  Waehrung als "0.00, stimmt" gemeldet.
- **Eine Bedingung ohne Wirkung liest sich wie eine Entscheidung.**
  `if bedingung: pass / elif ...` im Block, der eigentlich greifen sollte,
  sieht beim Review aus wie eine gepruefte Verzweigung und laesst danach die
  nächste Rechnung auf `None` laufen. Nach jeder Blockumschreibung lesen, was
  der Zweig jetzt tut, und die Leervariable pruefen: greift der neue Pfad,
  oder ist die Bedingung unerreichbar?
- **Skript fuer den Geraetezustand zuerst lesen, dann anrufen.** Wenn ein
  Helfer anders aufgebaut ist als angenommen (liefert ein Float statt eines
  Dict, nimmt keine SPOT-Instanz, verdoppelt ein Prozentfeld), faellt das im
  eigenen Lauf als leeres Ergebnis auf und wird leicht als "das Konto ist
  leer" gelesen. Ein Aufruf, der die ROHANTWORT zeigt, trennt "der Weg liefert
  nichts" von "mein Adapter liest falsch" in einer Minute.iter Patch am selben Block verschlimmert es, weil der Anker
  danach nicht mehr existiert. Gegenmittel: nach JEDEM Patch an einer Liste den
  BLOCK lesen (nicht den Diff) und die Zeilen gegen den eigenen Entwurf halten;
  beim ersten Anzeichen den Block ueber ZEILENINDIZES per Python ersetzen und
  danach `git diff --numstat` pruefen - dort muessen nur die eigenen Zeilen
  stehen.
- Geschriebene `.py`/`.json` pruefen — den NEUEN Text im Speicher VOR dem
  Schreiben, nicht erst die Platte danach: `ast.parse` bzw. `json.loads` (ein
  eingefuegtes Feld ohne abschliessendes Komma faellt sonst erst auf, wenn die
  Datei unlesbar liegt und jeder Leser der Spur — Systempruefung,
  `spiegelstand.py` — darueber stolpert; Suchmuster ohne Delimiter bauen, ein
  mitkopiertes Anfuehrungszeichen trifft nichts), dazu kein BOM und kein `\r`.
  **Ein Feld per Zeilentext einzufuegen heisst, das KOMMA zu verwalten:** traegt die
  Vorzeile schon eines, darf keines dazu (sonst `,,` und `json.loads` bricht erst
  beim naechsten Leser auf); ein Werkzeug, das ein Feld anlegt, prueft beide Faelle
  - ist das Feld schon da (dann nur den WERT tauschen, nicht die Zeile doppeln) und
  endet die Zeile auf ein Komma. Und die BELEGZEILE neben dem Wert wird mitgeaendert:
  ein alter Quelltext ueber einem neuen Wert ist ein Widerspruch in der Datei selbst,
  den jeder spaetere Leser glaubt (Muster: `_gebuehr_quelle` neben `gebuehr_taker`).
  Ueber einen PowerShell-Here-String mit `utf-8-sig` einlesen, `\r` entfernen,
  mit `newline=""` schreiben.
- `search_files`-Regex-Pattern werden intern gewrappt: escaped Klammern (`\(`) in
  einer Alternation brechen mit „unclosed group“ ohne klaren Grund. Nach dem
  nackten Symbol suchen (ohne `(`), wenn eine Mustersuche mit Klammern zweimal
  scheitert.
- Viele chirurgische Ersetzungen: je (alt, neu)-Paar `count == 1` asserten, danach
  `ast.parse` — Mehrfachtreffer und verrutschte Fundstellen fallen sofort auf.
  Zeilenenden VORHER erkennen und die Ersatztexte MIT ihnen bauen
  (`alt.replace(chr(10), nl)`), sonst findet der Anker in einer CRLF-Datei nichts;
  in einem per Heredoc erzeugten `.py` `chr(10)` statt `"\n"` schreiben, sonst
  steht ein echter Zeilenumbruch im String (unterminated string literal).
  **Ein Anker, der in N Schablonen-Spuren sitzt, beweist nicht, dass die
  ERSETZUNG dort gueltig ist** — dieselbe Zeile, verschiedene Bezeichner. Ein
  Regel-Block in vier Spuren eingefuegt und drei liessen sich mit
  `NameError` laufen, weil eine Spur die Seite `seite` nannte und die anderen
  `sig`; der Anker (`z["positionen"].append(_p)`) war in allen vier identisch.
  Nach dem Einsetzen **je Datei den EINSATZ-BEZUG pruefen, nicht den Anker**:
     die Bezeichner, die der neue Block benutzt, in jeder Zieldatei greppen und bei
     Abweichung den Block mit dem lokalen Namen wiederholen. Ein Test faellt nur
     dort, wo die Suite laeuft — die Spur-Suite wird oft einzeln gefahren, also
     jeden der N Kopien einzeln fahren, nicht die Gesamtsuite am Ende.

  - **Den Vertrag einer Funktion MESSEN, bevor man auf ihn testet.** Drei
    angenommene Vertraege ergaben drei gruene Tests ueber falsche Behauptungen:
    eine Richtungsfunktion liefert `1`/`-1` und nicht `"long"`/`"short"`; eine
    Glaettungsfunktion liefert eine REIHE mit `None` am Anfang und keine Zahl -
    und auf einer linearen Reihe laeuft die EMA in die SMA, die Praemisse „EMA
    steht ueber der SMA" war mathematisch falsch, der Test pruefte eine Behauptung
    ueber den Code und nicht den Code; und eine Signalfunktion wird von der einen
    Spur entpackt (`seite, _linie = sig`), von der anderen als Text verglichen.
    Dazu eine Zahl aus der Konfiguration statt eines festen Werts: die
    `mindest_kerzen` unterscheiden sich je Spur stark, eine feste Kerzenzahl im
    Test prueft bei der einen Spur gar nichts (statt dessen kommt die Zahl aus der
    `wachen.json`). Der billige Weg ist ein Aufruf in einer interaktiven Zeile und
    das Ergebnis ansehen - `repr()` der Rueckgabe, nicht der Name.

  - **Wer eine Buchposition schreibt, vergibt ihre Identitaet - auch auf dem Weg,
    der nicht der Einstieg ist.** `pos_id` ist kein Feld des Einstiegs, sondern
    eine Bedingung fuer JEDEN Pfad, der eine Position in `z["positionen"]`
    anlegt. Der Einstieg pflegte sie, der Uebernahmepfad fuer von Hand eroeffnete
    Positionen nicht - und genau dort lagen danach zwei echte LIVE-Positionen ohne
    Kennung. Ohne sie kann die Paarung den Ausstieg nicht eindeutig zuordnen,
    sobald zwei Positionen auf demselben Markt liegen. Beim Lesen auffaellig:
    **nach der Position den ZUSTAND pruefen, nicht den Einstiegscode** - die
    gefehlt hat, sah am Einstieg vollstaendig aus. Und Altbestand ohne Kennung
    wird NICHT nachtraeglich erfunden (die Journalzeilen tragen sie ebenfalls
    nicht, eine erfundene paart nichts) - der Weg aus Altbestand ist, die
    Positionen zu schliessen.

## Offene Positionen nachtraeglich absichern (Spot wie Margin)

Handgriff an Positionen, die SCHON offen sind - nicht der Stop beim
Einstieg. Reihenfolge, Fallgriffe und Werkzeuge:
`references/handgriff-offene-positionen.md`.

## References
- `references/okx-futures-positionen.md` — offene **OKX-Futures**-Positionen
  lesen und absichern (XPERP, Hebel, `isolated`/`cross`, OCO): welche Abfrage
  welche Frage beantwortet (`SPOT` nimmt `/positions` nicht), die
  Kontostand-Falle (Zahlen stehen je Waehrung in `details`, nicht auf
  Kontoebene), die Liquidationsluft mit Vorzeichen, „geschuetzt“ als **Summe**
  der Stueckzahlen (Luecke/Ueberdeckung/Nullmenge), der OCO-Koerper samt
  `tdMode`/`side` und warum `okx.stop_setzen` dort nicht passt, und die Regel
  vor dem Aufstocken: vorhandene Preise gegen den **aktuellen Kurs** rechnen,
  nicht gegen den Einstand. Ausloeser: „Positionen analysieren", „Stop
  setzen", „aufstocken", „intelligenter Take-Profit", „Luft bis Liquidation".
- `references/boersen-aufrufe.md` — Stops an BESTEHENDE Positionen: die exakten
  Kraken-Aufrufe (`AddOrder` mit `close[...]`, `OpenPositions`-Felder,
  `QueryOrders`-Antwort, Paarregeln), OKX-Stops und die Fehlermeldungen
  (`EOrder:Insufficient funds`, `EAPI:Invalid nonce/key`, `50014`, `51400`).
  Ausloeser: "absichern", "Stop nachziehen", "Sui/ZEC/NEAR"
- `references/sprachmodell-spur.md` — eine Spur, deren Richtung ein LOKALES
  Sprachmodell liefert: Vertrag (BUY/SELL/NOTHING + Confidence), Gate bleibt
  deterministisch und nachrechenbar, Messung der Modellwahl, Cache, Nachfassen,
  `think:false` und was ohne Gate passiert. Ausloeser: "LLM-Spur",
  "Modell entscheidet", "Confidence"
- `references/ausstieg-und-auswertung.md` — Ausstieg rechnen und Journal deuten
  (G/V auf den Nominalwert, Ausstiegspruefung je Instrument, Journalformate der
  Familien, Spur auswertbar machen, Testaufruf) **plus die Wiedereinstiegs-Regel:
  ein Ziel-Ausstieg hat das Signal verbraucht** (Sperrfrist in Stunden nach
  `ziel`, laengere Abklingzeit in Tagen nach `stop`, Zeitstempel statt Datum,
  Test mit Gegenprobe). Ausloeser: „kauft sofort wieder", „Sperrfrist",
  „Gebuehren fuer dieselbe Bewegung". **Dort auch MFE/MAE** — die Spalte, ohne
  die kein Stop begruendbar ist: ueber die LEBENSDAUER messen (beim Ausstieg
  gemessen ist die Zahl der Ausstiegskurs selbst), Richtungsfaktor sobald die
  Spur auch short handelt (die long-only Formel ist bei short spiegelverkehrt),
  und die Falle, dass eine NEUE Journal-Spalte auf einer bestehenden Spur erst
  nach einer Kopfzeilen-Migration ankommt — der Schreiber nimmt die Spalten aus
  der Datei und verwirft die neue sonst kommentarlos.
- `references/santiment.md` — Santiment SanAPI (GraphQL, anonym in der freien
  Stufe nutzbar): wo das Repo liegt, welche Metriken live geprueft sind, dass
  JEDE Metrik ihr eigenes Zeitfenster hat und `erlaubtes_fenster()` die Grenze
  aus der Fehlermeldung liest, warum eine leere Reihe kein Fehler ist und wie
  der MCP-Weg (OAuth) daneben aussieht.
- `references/schattenbuch-spur.md` — Varianten einer bestehenden Spur mit
  getrennten Dateien (Suffix durch die Datei-Konstanten, Launcher je Arm):
  Mechanik, Verdrahtung inkl. spiegelstand- und Bus-Anbindungs-Falle,
  Auswertung erst ab genug Ausstiegen je Arm.
- `references/browser-edge-sperre.md` — Hermes-Edge / browser-profile: eine
  laufende Headless-Edge-Instanz hält Cookies/Sessions gesperrt und bricht
  die Sicherungsläufe mit FEHLER 32 / Exit 20/21. `/XD browser-profile` in
  sichern.ps1 und sichern-zweitkopie.ps1; `0xC000013A` = Rechner-Neustart
  (Event 1074), kein Skript-Fix.
- `references/okx-fehlermeldungen.md` — OKX meldet Orderfehler mit HTTP 200
  und `code="1"` (Auskunft in `data[0].sMsg`, nicht im aeusseren `msg`); ein
  echter HTTP 4xx muss als fachlicher Fehler gelten statt als Transportfehler
  wiederholt zu werden (sonst geht eine abgelehnte Order dreimal raus); das
  STORNO einer Algo-Order braucht `instId` (`50014` ohne sie) und `51400`
  heisst erledigt, nicht Fehler.
- `references/kraken-nonce-und-lockout.md` — `Invalid nonce` und `Temporary
  lockout` erst unterscheiden, bevor man den nonce-Code jagt: eine Sperre
  lehnt JEDEN nonce ab, auch einen korrekten; weitere Sonden verlaengern sie.
- `references/boersen-schluessel-diagnose.md` — wenn ein Zugang von einer Minute
  auf die andere streikt: in welcher REIHENFOLGE man entscheidet, ob unsere
  Signatur, der Schluessel oder die Boerse die Ursache ist. Kernregeln: einen
  privaten Aufruf NIE von Hand signieren (die Hausmodule teilen den nonce-Pool
  `kraken/.kraken_nonce`; ein eigener Zeitstempel liegt unter dem Peak und Kraken
  antwortet mit `Permission denied`/`authenticationError` statt mit einem
  nonce-Fehler), eine UNABHAENGIGE Umsetzung als Schiedsrichter fahren (kraken-cli
  `futures accounts`; sie liest `KRAKEN_FUTURES_API_KEY`/`_SECRET`), die
  nonce-Verdacht ueber Groessenordnungen (ms/us/ns/1,8e18) ausschliessen und den
  Zugang ohne Klartext pruefen (Hash/Laenge gegen die `setx`-Zeile der
  PowerShell-History; `reg query` gibt die Werte aus).
- `references/einzahlung-und-guthaben.md` — Geld verfolgen: die Nachweis-Kette
  vom `DepositStatus` ueber die Gegenbuchung (`Ledgers`, PLURAL) bis zum
  Zielkonto, die Fallen (aufsteigende `/transfers`-Liste, Konten nicht nach
  `usd` filtern, Epoch umrechnen, Einzahl- vs. Mehrzahl-Schluesselnamen) und die
  Regel, dass ein Transfer zwischen Konten eine Kontohandlung ist. Ausloeser:
  "hab eingezahlt", "Guthaben fehlt", "wo ist das Geld hin".
- `references/gebuehren-tor.md` — wann eine Spur live darf: die vier
  Bedingungen, warum ein BEFUND im Audit die Freigabe sperrt (der scanner
  haette die drei anderen mit +8,52 % bestanden), warum eine Spur ohne
  Auditrundlage *unbewiesen* statt *abgelehnt* ist, und das Fail-closed
  am Weg, der ausserhalb des Dauerlaufs ordert.
- `references/pitfalls-landkarte.md` — die Landkarte aller 103 Punkte, ein Satz je Punkt (aus SKILL.md ausgelagert).
- `references/pitfalls.md` — ALLE Pitfalls im Volltext, gleiche Nummer:
  Meldungen und Schnittstellen, Sperren und Schwellen, Testfallen,
  Doppellauf und Neustart, Buch und Ablehnungen, Naht und Signatur,
  Auswertung und Backtest. **Vor jeder Spuraenderung lesen.**
- `references/spur-weite-aenderung.md` — Änderung über ALLE Spuren ausrollen:
  Inventar, Stufe-1-Sicherung, byte-genaue Ersetzungen in `wachen.json`/Code, alle
  Zyklenpfade inkl. Notausstieg, Testaufruf (`discover -s tests -t tests`), echter
  Lauf + byte-genauer Vergleich, Automatik-Nachweis über das Bus-Journal, Doku an
  drei Orten, getrennte Commits je Regel und Repo — plus die Falle „Testzyklen
  spiegeln ihre Temp-Zustandsdatei an das echte Ziel".
- `references/schwellen-haerten.md` — Verfahren, mit dem die Schutzwerte einer
  Spur vertrauenswuerdig werden: Buchrisiko feststellen, fehlende Eingabe aus
  dem Code ablesen statt raten, Betrag herleiten und ausdruecklich hinschreiben,
  warnen statt ausloesen, `halbierung_im_gewinn` pruefen statt "erreichbar" zu
  behaupten, Stand aller fuenf Spuren, die Spalten des Pruefskripts.
- `references/sicherungen-pruefen.md` — Sicherungen (Ratsche, Kill-Switch,
  Deckel, Groessenfaktor) und die Werkzeuge, mit denen man prueft, dass sie
  greifen koennen: absoluter Betrag statt Quote von fremder Groesse, warum
  "greift erst im Minus" nicht "abgeschaltet" heisst, der Vorrang des
  ausdruecklichen Werts, **warum eine Prozentangabe („Stop 60“) in einer
  Spur mit absolutem `stop_usd` nicht treu umsetzbar ist (Einsatz schwankt) —
  Prozentfeld mit Vorrang, groesster und kleinster Einsatz gegenrechnen**, und
  "keine Negativ-Aussage aus einer abgeschnittenen Suche" (Import-Kette!).
- `references/anbindungs-audit.md` — Bestandsaufnahme „was laeuft, was ist
  angebunden, was ist Altlast“: Verdrahtungsstellen gegeneinander halten,
  Aufrufer greppen, Befund richtig deuten.
- `references/spur-nachtraeglich-anschliessen.md` — eine BESTEHENDE Spur (oder
  mehrere) nachtraeglich in den Takt haengen: die fuenf Stellen, der Vertrag des
  Tagesberichts, der geteilte Journal-Leser, die Nachweis-Kette bis zum ersten
  Zyklus, und die Fallen (Zustand schlaegt wachen.json, fehlender
  Duplikat-Schutz, CRLF im Test-grep).
- Live schalten oder „gefechtsbereit machen" — Freigabekette, Plane-Zuerst-\
  Disziplin fuer den ERSTEN echten Geldpfad, Instrument-Verfuegbarkeit an der
  Zielboerse vor dem Umbau pruefen, abgetrennter Live-Zweig statt gemeinschaft
  Kern: `references/live-schalten.md`
- `references/spur-scharf-schalten.md` — eine Spur scharf schalten: die zwei
  Schalter samt datiertem Vermerk, das Zeitfenster und die Auto-Freigabe, der
  Nachweis am echten Zyklus — und die Regel, dass eine quantitative Bedingung
  den Schalter selbst zuruecknimmt, wenn sie reisst.
- `references/mcp-tor-freigabebeleg.md` — einem Boersen-MCP genau EIN Tor zum
  Ausfuehren geben (Einmal-Beleg der Spur, Felder und Fail-closed-Regeln, die
  alten Wege schliessen, Cache-Schluessel nach Pfad, Nachweis ueber
  `tools/list`), damit eine Fremdsitzung nicht am Skript vorbei ordert.
- `references/freigabe-kette.md` — Punkt 3 der Handelsregeln in beiden Fassungen:
  Bildschirm- und Zeitfenster, wer wann öffnet, was eine Freigabe nicht kann.
- `references/grenzen-und-deckelung.md` — Grenzen und Kappungen: welcher von
  Betrag/Gesamt/Plaetzen/Guthaben bindet, den Einsatz auf das freie Guthaben
  deckeln, und **ein wiederholtes Signal: die Position vergroessern statt zu
  verdoppeln** (gewichteter Einstieg, Stop/Ziel neu aus dem gemittelten Einstieg,
  kumulative Journalzeile statt Inkrement). Ausloeser: „Stackel", „vier Positionen
  auf einem Instrument", „nicht doppeln".
- `references/tor-kalibrierung.md` — Schwellen und Kostenannahmen kalibrieren,
  ohne dass sie entweder nichts filtern, nie aufgehen oder eine Wunschrechnung
  sind (Tore, Filter, Slippage/Gebühr).
- `references/ziel-und-hebel-geometrie.md` — wenn das Ziel KEIN Vielfaches des
  Stops ist (Marktpunkt, Zone, Wand, Niveaus): Zielabstands-Boden gegen die
  Gebuehr (eine hohe Trefferquote bei kleinem Zielabstand ist kein Vorteil),
  Marktpunkt als Preisstreifen statt Linie, und die Hebelrechnung — bei
  risikonormierter Groesse aendert der Hebel weder Gewinn noch Verlust, er
  senkt nur die Kapitalbindung auf 1/h, und bei 4 % Stop ist bei Hebel 25 die
  Liquidationsdistanz aufgebraucht. Die Frage „geht das mit Hebel?" ist bei
  einer Ein-Platz-Spur mit der Rechnung zu beantworten, nicht mit einem Arm.
- `references/fremdlauf-spiegeln.md` — einen FREM DEN Lauf spiegeln (Weg B):
  Sperrseite gegen Freigabeseite pruefen, Zustand statt Orderliste, zwei Zeugen
  statt `state: running`, echter Orderpreis, die sechs Verdrahtungslisten und
  die Fallen (leere Daten, Quotewaehrung, normalisiertes Dict, aware Zeitstempel).
- `references/spur-in-die-gui.md` — eine Spur in Handelszentrale und
  Werkzeug-Zentrale bringen: Reiter-Sektion mit reinen Funktionen und echtem
  Fensteraufbau-Test, Startbefehl plus Beleglauf, die still alternden Listen
  (Reiter-Zuordnung, `QUELLE`, `SPUREN_START`).
- `references/fremdfeed-papierbuch.md` — Spur an fremden Signal-Feed haengen
  (Copy-Trading, Spiegelung, Signalstudie): Leser mit Schreibschutz, Auswahlregel
  gegen Zuchtauswahl, Kosten zweimal gerechnet, Tore vor jeder Buchzeile.
- `references/freqtrade-dryrun.md` — eine FREMDARTIGE Engine als Papierflotte
  (Freqtrade-Container, nicht `spur_buch`): erst die Form bestimmen (OHLCV plus im
  Futures-Modus Funding/Markpreis — alles andere nicht portierbar, die Absagen mit
  Grund in dieselbe Datei), dann der Todesbeweis `avg_profit_pro_trade` gegen
  `2 * gebuehr_je_seite` — darunter ist der Verlust die Gebuehr und keine
  Parameteroptimierung hilft; Zugang, die `can_short`-Falle im Spot-Modus,
  `minimal_roi`/`stoploss` als Klassenattribute.
- `references/buchergebnis-pruefen.md` — Buch-Ergebnis deuten, bevor es als Gewinn
  gelesen wird: Papier vs. Geld, Saldo vs. Umsatz, Abhaengigkeit von den
  Top-Positionen, Mittelwert UND Median, was nicht in der Zahl steckt. Ausloeser:
  „das heisst, wir haetten X gewonnen?". Eine gemeldete Kennzahl („Treffer
  100 %") wird mit einer EIGENEN FIFO-Paarung nachgezaehlt, nicht durch einen
  zweiten Aufruf desselben Werkzeugs - Abschnitt 7 derselben Datei.
- `references/spur-haerten.md` — bestehende Spur pruefen, haerten, messbar machen:
  elf Verdachtsmuster (toter Code mit Docstring-Behauptung, erfundene Feldnamen,
  zu enge Ausnahmen, fehlende Deckel, ein Routing-Feld das eine Zwischenlagerung
  nicht ueberlebt, eine Anzeige die den leeren Fall verschweigt),
  Fix-Disziplin, Nachweis-Kette. Ausloeser:
  „Code optimieren", „Luecken suchen", „die Spur laeuft wieder in den alten
  Fehler".
- `references/spur-bericht.md` — Zustandsbericht ueber eine laufende Spur:
  Quellen in Reihenfolge, Lese-Fallen (Bus-Journal mit BOM, UTC vs. lokale
  Bus-Zeit, 1-s-Vorschau-Lauf je Zyklus als Absicht, kurze Abstaende vs. echte
  Taktluecken), was ein Bericht sagen muss und was nicht. Ausloeser: „Bericht",
  „wie laeuft <Spur>".
- `references/neue-spur-ende-zu-ende.md` — Spur von Null bis GUI aufbauen:
  abgebrochene Aufgabe verifizieren (nichts annehmen), Vorbilder lesen, drei
  Kerndateien bauen, **an jede Liste verdrahten** (Tabelle: Stelle -> Eintrag ->
  der Test, der ihn einfordert), Nachweis-Kette, Dauerlauf-Neustart (alle
  Stufen), GUI-Start und -Verifikation.
- `references/auswertung-und-optimierung.md` — Journale in eine belegte Aenderung
  uebersetzen: Runden zaehlen (Testlaeufe aussortieren), Kosten aus der Zeile,
  Geometrie-Gegenprobe, Ausstiegsgruende, Gruppen mit Stichproben-Disziplin, die
  eine Aenderung samt drei Ablageorten, und was eine duenne Stichprobe NICHT
  hergibt. Ausloeser: „werte die Daten aus", „optimiere die Strategien".
  **Dort auch Schritt 2b — die ZWEI Fragen, die vor jedem „nimm die beste Spur":
  Hat die Auswahlregel Edge (gemessen GEGEN die Basislinie aller gesehenen
  Maerkte, nicht gegen null) und kann die Spur ueberhaupt handeln?** Vordergrund
  steht eine Spur fast immer, weil sie die einzige mit echtem Orderpfad ist — das
  ist Handvormacht, keine Vorhersagequalitaet, und die beiden werden erst zusammen
  bewertet.
- `references/fremdarbeit-mitnehmen.md` — uncommittete Arbeit einer anderen
  Sitzung erkennen, liegen lassen, mitnehmen wenn fertig:
  Wachstums-/mtime-Kriterium, `reset --soft` zum Nachtrennen, Waechter als
  `no_agent`-Cron mit Ruhezeit und Merker, Commit nur der Quelldateien mit
  ehrlicher Nachricht. Skript: `scripts/fremdarbeit_waechter.py`.
- `references/xperp-rollover-2026-09-14.md` — XPERP-Kontrakt-Rollover (51001),
  Tests schreiben nie ins echte Journal, hartdatierte Tests, seite im
  Positions-Dict.
- `references/spuren-einzeln.md` — die datierten Kapitel je Spur (SWAP
  anbinden, Omniquant, Kraken wieder im Dauerlauf, Gitter, Nautilus,
  ORB-Grundregel). Ausgelagert, weil SKILL.md sonst ueber das
  100.000-Zeichen-Limit laeuft und gar nicht mehr patchbar ist. Nur laden,
  wenn genau diese Spur ansteht.
- `references/wartende-auftraege-belegen-platz.md` — ein Limit hinter dem Markt
  ist noch keine Position, belegt aber einen Platz; sonst legt jeder Zyklus
  nach (13 Dubletten an einem Abend). Plus: `_roh` serialisiert selbst,
  "mehrfach gebucht" zuerst an `orders-pending` pruefen.
- `references/test-friert-stand-ein.md` — ein Test gegen einen Commit-Hash oder
  eine feste Anzahl meldet Aenderung, nicht Fehler. Auf die Eigenschaft pruefen,
  die gelten soll; Zeit als Parameter hereingeben.
- `references/spur-tests-und-auswertung.md` — Tests richtig aufrufen (Testkopf-Form
  gegen `-t tests`, falsches `handeln`-Modul), vorbestehende Fehlschlaege deuten,
  **Fehlschlaege der vollen Suite zuordnen** (Datei allein fahren, Betreff gegen
  die eigene Aenderung halten, Alter des gelesenen Erzeugnisses),
  Ausstiegsrechnung auf den Nominalwert, Anschluss an `auswertung_alle`,
  Gebuehren-Grenze `f_max`.
- `references/schaltername-benennt-die-sperre.md` — ein boolescher Name benennt
  den Zustand, den er schaltet, nicht den Anlass (`wochenende_gesperrt`, nicht
  `we`); `wenn_nicht_X` gehoert nie in einen Namen.
- `references/live-tor-und-einsatzgroesse.md` — eine scharfe Spur, die nicht
  handelt: ein Tor muss den Zustand des Zweigs lesen, der SCHREIBT (Herzschlag aus
  dem frischesten Papier-/Livestand, sonst Selbstsperre und nutzlose
  Auto-Freigabe-Fenster); der Einsatz wird auf das freie Guthaben gedeckelt, bevor
  das Freigabefenster ihn zeigt (`gedeckelt = frei * (1 - gebuehr_taker - 0,2 %)`,
  Rueckfall-Regeln als Tabelle); nach jeder Grenz-Erhoehung nachrechnen, welche
  Grenze in der Kette je Trade → Plaetze → Gesamtdeckel → Guthaben bindet, und
  `mindest_guthaben*` mit dem KLEINSTEN Einsatz begruenden, nicht mit einem alten
  Beispielbetrag.
- `references/fremdprogramm-frequenz-und-hebel.md` — Frequenz-, Hebel- und
  Stop-Fragen an einen laufenden FREMDlaeufer: Faehigkeiten am Code pruefen
  (totes Leverage-Modul, Software-Stop gegen Boersen-Stop, Trailing auf
  Kerzenschluss gegen Kerzenhoch), Gebuehr aufs Nominal gegen die Margin
  rechnen, Messraster mit dem eigenen Backtester des Programms (`OMNI_LONG_ONLY`
  fuer den Spot-Fall, `historie_binance.TAKTE` fuer 5m/15m erweitern), neue
  Skriptfassungen ins Haus legen statt in den Klon. Ausloeser: „oefter handeln",
  „mit Hebel", „Trailing-Stop", „kurze Intervalle", „hoehere Trefferchance".
- `references/meldungen-des-dauerlaufs.md` — was in den Chat gehoert: eine Zeile
  muss ein GESCHEHEN aussprechen UND ihr Subjekt nennen (`EREIGNIS_ANFANG` /
  `EREIGNIS_WORTE`, `ereigniszeilen()` / `neue_ereignisse()`); Ueberschriften,
  Fortsetzungs- und Hinweiszeilen sind kein Ereignis (Zyklus 21 der Basis,
  25.09.2026: fuenf Zeilen, null Geschehen). Eine je Instrument gedruckte Zeile
  wird zum Zaehler plus EINER Meldung im Aufrufer. Wirkt erst nach einem
  Neustart des BASIS-Laufs.
