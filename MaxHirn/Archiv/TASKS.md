# Offene Punkte

Sitzungsübergreifende Aufgabenliste. Einzige Quelle für „was ist noch offen".
Angelegt am 2026-08-28, weil offene Punkte aus früheren Chats bis dahin
nirgends festgehalten wurden und mit dem Sitzungsende verloren gingen.

## Regeln

- **Am Sitzungsanfang lesen**, bevor gefragt wird, woran gearbeitet werden soll.
- **Sofort eintragen**, wenn ein Punkt entsteht — nicht am Sitzungsende sammeln.
  Wird die Sitzung vorher abgebrochen, ist der Punkt sonst weg.
- **Erledigtes nach `## Erledigt` verschieben**, mit Datum. Nicht löschen —
- [x] **T-044 - Gateway-Waechter registriert, Alt-Task deaktiviert, Bus ohne Konsolenfenster**
      **Erledigt 2026-09-16.** Max hat den UAC-Dialog bestaetigt; das Skript
      `Agenten\Routinen\vorsorge-gateway-admin.ps1` ist in einer Admin-PowerShell
      durchgelaufen. Von einer normalen Sitzung nachgemessen: `Hermes_Gateway` =
      **Disabled** (startet die Altanlage nicht mehr bei der Anmeldung),
      `MaxHirn-Gateway-Waechter` = **Ready** (registriert, alle 2 Minuten),
      `BrainFiles-Bus` = laeuft unter **pythonw.exe** (PID 59316, Port 8787 offen).
      **Zur dritten Zeile:** der Bus-Task lief bis heute als `python.exe` bei
      Interactive-Logon - bei jedem Start ploppte ein Konsolenfenster auf. Die
      Ursache war nicht die Aufgabenplanung (alle 18 MaxHirn-Tasks tragen
      `-WindowStyle Hidden`), sondern der Bus selbst. `bus.ps1` (die Registrierung)
      ist auf `pythonw` umgestellt, die Live-Aenderung steht als Schritt 3 im
      Admin-Skript; der Neustart aus der Aufgabenplanung brachte sofort pythonw
      (Commit 4fca63d).
      Betrifft: `Agenten/Routinen/vorsorge-gateway-admin.ps1`, `bus.ps1`,
      `Agenten/Routinen/gateway-waechter.ps1`, Aufgaben `Hermes_Gateway`,
      `MaxHirn-Gateway-Waechter`, `BrainFiles-Bus`
      Angelegt: 2026-09-16
  die Historie zeigt, was schon einmal versucht wurde.
- **Nichts erfinden.** Nur eintragen, was Max gesagt hat oder was aus einer
  abgebrochenen Arbeit tatsächlich offen blieb. Vermutete Folgeaufgaben
  gehören als Vorschlag in die Zeile „Kontext", nicht als eigener Punkt.
- **Stand aktuell halten.** Fällt beim Arbeiten auf, dass ein Eintrag hier
  überholt ist, sofort korrigieren und die Korrektur melden — auch wenn es
  nicht zur laufenden Aufgabe gehört.
- IDs fortlaufend `T-001`, `T-002`, … Einmal vergeben, nie wiederverwenden.

## Status-Kürzel

| Kürzel | Bedeutung |
|---|---|
| `[ ]` | offen, noch nicht angefangen |
| `[~]` | in Arbeit / teilweise erledigt |
| `[?]` | wartet auf Entscheidung oder Information von Max |
| `[!]` | blockiert, Ursache im Kontext benannt |
| `[x]` | erledigt → gehört nach unten |

## Eintragsformat

```

- [ ] **T-0NN — Kurztitel**
      Kontext: worum es geht, warum es offen ist
      Nächster Schritt: eine konkrete, ausführbare Handlung
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28
```
Optional zusätzlich: `Betrifft:` (Pfad, Projekt, Gerät), `Wartet auf:` (bei `[?]`/`[!]`).

## Offen

- [ ] **T-203 - Backtest-Zahlen, die auf der alten Kerzenschluss-Regel beruhen, neu lesen**
      Kontext: T-177 ist behoben (Ausstieg auf der beruehrten Marke). Die Wirkung ist
      gross: squeeze dreht von +61,93 auf -6,34 % (759 Runden), moondev_topmovers von
      +522,44 auf +260,00, moondev_funding von +156,50 auf +87,00. Jede Notiz und jedes
      Urteil, das auf einer Backtest-Zahl von vorher fusst, ist zu guenstig gerechnet -
      betroffen sind `Agenten/Handel/backtest_urteile.py`, die Zeilen von
      `auswertung_alle.py --backtest` und die Notizen unter MaxHirn/Wiki/Handel/.
      Naechster Schritt: die gespeicherten Backtest-Laeufe mit der Regel neu fahren
      (`replay.py --lauf <neu>`) und die Urteile nachziehen. Kennzahl der Regel ist
      `ausstiege_an_marke`/`ausstiege` - ein Lauf von vorher zeigt 0/N.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Handel/backtest_urteile.py, daten/backtest/**, MaxHirn/Wiki/Handel/

- [ ] **T-202 - Docht-Ausstieg im Replay abbilden (Beruehrung ohne Schluss jenseits der Marke)**
      Kontext: Mit der Beruehrungsregel (T-177, erledigt 30.09.2026) geschieht der
      Ausstieg am Kurs der Marke, wenn die Kerze sie beruehrt - der AUSLOESER bleibt
      aber der Kerzenschluss, wie live. Eine Kerze, die eine Marke nur mit dem Docht
      streift und darueber schliesst, loest weiterhin nichts aus.
      Naechster Schritt: zaehlen, wie oft das in den vorhandenen Historien vorkommt
      (Zaehler neben `auf_der_marke`), und erst dann entscheiden - ein Docht-Ausstieg
      macht die Zahlen strenger, nie besser, und weicht vom Live-Verhalten ab.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Handel/replay.py, MaxHirn/Wiki/Handel/Backtest-Fundament.md

- [ ] **T-197 — Freqtrade-Bots: die Frequenz-Bremse fehlt in der Uebertragung**
      Kontext: Der erste echte Backtest der drei Moon-Dev-Strategien (30.09.2026) ist in
      allen Fenstern negativ, und der Grund ist nicht die Richtung, sondern die ZAHL der
      Trades: `MoonDevTradingAgent` macht 3,23 Runden pro Tag, was bei 0,2 % je Runde
      ueber 240 % Kosten im Jahr ergibt. Im Backtest stehen 8.399 USDT Gebuehren gegen
      ein Ergebnis von -8.335 USDT - der Verlust IST die Gebuehr.
      Im Haus gibt es zwei Bremsen, die in der Uebertragung fehlen:
      `Agenten/Handel/risikovorfilter.py` (Verlust-/Gewinngrenze im 12-h-Fenster,
      Buchrisiko-Deckel) und `handeln.in_zielsperre` (Sperrfrist nach Ziel-Ausstieg,
      Spur scanner). Keine davon ist in `user_data/strategies/` angekommen.
      Naechster Schritt: `populate_entry_trend` um einen Mindestabstand zwischen zwei
      Einstiegen desselben Paares und um eine Sperrfrist nach Ziel-Ausstieg ergaenzen,
      dann DENSELBEN Backtest erneut fahren - die Kosten muessen fallen, sonst ist die
      Strategie unbrauchbar. Erst messen, dann bewerten.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/freqtrade/user_data/strategies/, Agenten/Handel/freqtrade/bots.json

- [ ] **T-198 — Freqtrade-Bots sind long-only: die Short-Regeln fehlen**
      Kontext: `bots.json` haelt es unter `_offen` selbst fest - alle drei Bots sind
      long-only, weil `can_short = True` im Spot-Modus nicht laedt
      (`strategy_resolver.py:167`). Die Short-Regeln der Agenten (marktlage: -2 % und
      Breite <= 40 %) kommen also gar nicht zum Einsatz; die Uebertragung ist die halbe
      Strategie.
      Wichtig fuer die Bewertung: die Short-Seite erklaert den Verlust NICHT. In H1 war
      der Markt +76,6 %, waehrend `MoonDevTradingAgent` -62,9 % machte - eine Long-Seite,
      die in einem steigenden Markt verliert, wird durch Shorts nicht gerettet, und die
      Gebuehrenlast (T-197) bliebe dieselbe.
      Naechster Schritt: `trading_mode: futures` plus Futures-Daten fuer die 24 Paare
      (`BTC/USDT:USDT`-Form) laden und denselben Backtest mit kurzer Seite fahren - als
      MESSUNG, nicht als Umbau. Wegen T-197 erst nach der Frequenz-Bremse sinnvoll.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/freqtrade/user_data/bots/, Agenten/Handel/freqtrade/bots.json

- [ ] **T-199 — bots.json: zwei Absagen sind durch den Feed-Backtest ueberholt**
      Kontext: Die Liste `nicht_portierbar` (11 Eintraege) begruendet je Agent, warum
      keine Uebertragung erfolgt. Zwei Absagen stuetzen sich auf "keine Historie
      vorhanden" (Funding sowie Open Interest/Liquidationen): ohne Reihe kein Backtest.
      Seit dem 29.09.2026 gibt es diese Reihe im Haus: `Agenten/Handel/moondev_historie.py`
      archiviert den Marktquerschnitt UND Funding (6 Instrumente); `replay.lauf_c` faehrt
      die Funding-Spur nach (23 Runden, 74 %, +5,99 % je Runde).
      Was bleibt, ist eine Freqtrade-Frage, keine Datenfrage: der Spot-Backtest von
      Freqtrade sieht keine Funding-Rate, sie steht in keiner Kerze. Wer das will,
      braucht `informative_pairs` plus eigene Datenquelle - oder nimmt die Haus-Spur,
      die es schon kann.
      Naechster Schritt: `bots.json` an dieser Stelle richtigstellen (Grund auf den
      Datenmodell-Punkt kuerzen statt auf die fehlende Historie) und pruefen, ob OI und
      Liquidationen genauso nachrechenbar sind - `moondev_historie.py` deckt bisher nur
      Preise und Funding.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/freqtrade/bots.json, Agenten/Handel/moondev_historie.py

- [ ] **T-200 — MCP_DOCKER-Abgleichkreis: die Wache nennt ihn, verhindert ihn nicht**
      Kontext: Am 30.09.2026 lief der Rechner eine Stunde mit 1,0 GB freiem Commit, weil
      der Docker-Daemon tot war und der Gateway-Abgleich trotzdem `MCP_DOCKER` starten
      wollte - bei JEDEM Versuch startete er daraufhin alle sechs MCP-Gruppen neu
      (146 Python-Prozesse, WSL-VM tot, Docker tot: ein geschlossener Kreis).
      Die Wache `mcp-zombie-wache.py` nennt die Ursache jetzt (Commit 19a79a5), aber ihre
      Kur bleibt Symptombehandlung: sie killt die Ueberzahl, und der Abgleich spawnt
      weiter, solange Docker tot und MCP_DOCKER eingetragen ist.
      Naechster Schritt: Entscheidung von Max - `MCP_DOCKER` aus
      `Agenten/Hermes/config.yaml` austragen (kostet die 17 Docker-MCP-Werkzeuge im
      Werkzeugkasten der Agenten) oder eintragen lassen und den Ausfallweg hinnehmen.
      Der Versuch `hermes mcp remove MCP_DOCKER` scheiterte am 30.09. an
      `pm: worker exited without a result` - damals aus Commit-Mangel; ein zweiter
      Versuch braucht Luft und vorher eine Sicherung der Config.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Hermes/config.yaml, Agenten/Hermes/scripts/mcp-zombie-wache.py

- [ ] **T-201 — Container `freqtrade` (Port 8080) hat keinen Zweck mehr**
      Kontext: Der Vorgaenger-Container faehrt `SampleStrategy` und laeuft seit dem Aufbau
      der drei Bot-Container weiter mit. Er belegt Port 8080, verbraucht Commit und ist
      im Ablauf eine Verwechslungsquelle - die drei echten Bots liegen auf
      8081/8082/8083.
      Naechster Schritt: pruefen, ob Max ihn von Hand nutzt (dann Kennzeichnung), sonst in
      `bots_starten.sh` als Altlast vermerken und den Container stoppen. NICHT ohne
      Rueckmeldung loeschen - es ist der einzige Container, dessen Zweck ich nicht kenne.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/freqtrade/bots_starten.sh

- [ ] **T-195 — Ein abgebrochener Wartungslauf laesst den naechsten Dashboard-Start alles neu bauen**
      Kontext: Beim Wartungslauf vom 29.09.2026 (`outcome: partial`) blieb der Zustand "finishing
      an interrupted source update" liegen. Am 30.09.2026 las der Dashboard-Start diesen Vermerk und
      baute VOR dem Bereitstellen alles neu - Node-Abhaengigkeiten, TUI, Web-UI, Desktop-App,
      gemessen 6 Minuten (Beleg: Log des Handstarts), waehrend Port 9119 zu blieb. Ein Neustart in
      dieser Zeit hilft nicht: die neue Instanz faengt denselben Bau an. Die neue Dashboard-Wache
      fasst deshalb nichts an, solange die CPU-Zeit der Prozesskette steigt.
      Naechster Schritt: pruefen, ob der Wartungslauf den Zustand selbst aufraeumen kann (bzw. ob
      der Starter einen abgebrochenen Bau sauber beenden soll), damit der naechste Start wieder
      Sekunden statt Minuten braucht.
      BELEG 30.09.2026 (2-Jahres-Laeufe, vollstaendige Paartabellen): Der Verlust
      sitzt in den KLEINEN Werten, nicht in den grossen. TopMovers 924 Trades,
      -46,02 %, maxDD 77,4 %, Treffer 37,4 %; je Paar LINK -14,94 %, AVAX -12,41 %,
      PEPE -8,46 %, NEAR -4,01 %, DOGE -2,05 %, ATOM +1,25 %. MarktRegime 210 Trades,
      -37,24 %, maxDD 48,5 %. Damit gibt es einen ZWEITEN Hebel neben der Frequenz:
      die Paarauswahl. Ein Lauf nur auf den grossen Paaren ist billig zu messen und
      gehoert VOR jeden Umbau der Strategie - sonst optimiert man an der Strategie,
      waehrend das Geld in einem Drittel der Paarliste verbrennt.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Hermes/gateway-service/Hermes_Dashboard.vbs, Agenten/Hermes/scripts/dashboard-wache.py


- [ ] **T-196 — Wer schreibt `logs/dashboard-restart.log`?**
      Kontext: Die Datei `Agenten/Hermes/logs/dashboard-restart.log` waechst, aber kein Skript in
      `Agenten/` nennt den Namen (Suche ueber py/ps1/vbs: 0 Treffer, auch `search_files` findet
      nichts). Die neue Dashboard-Wache nennt den Pfad als Hinweis in ihrer Meldung - wenn die Datei
      verwaist ist, schickt sie den Nutzer zu einem toten Protokoll.
      Naechster Schritt: Schreiber suchen (Aufgaben-Action, VBS, Hermes-Seite) - oder den Pfad in
      der Wache auf die Datei umstellen, die es wirklich gibt (z.B. `logs/agent.log`).
      Angelegt: 2026-09-30
      Betrifft: Agenten/Hermes/logs/, Agenten/Hermes/scripts/dashboard-wache.py


- [ ] **T-194 — Dateischwund-Wache auf weitere Ordner ausweiten?**
      Kontext: Die Wache vom 30.09.2026 (`Agenten/Hermes/scripts/dateischwund-wache.py`,
      Cron `dateischwund-wache`) bewacht NUR `Agenten/Hermes/scripts/` - dort sind die
      sechs verschwundenen Testdateien beobachtet worden. Dasselbe Muster kann jeden
      Ordner treffen, in dem kurzlebige Dateien entstehen: `Agenten/Handel/*`
      (Spur-Tests), `Agenten/Bus/`, `Agenten/Routinen/`.
      Naechster Schritt: Entscheidung von Max, welche Ordner dazukommen. Technisch ist
      es ein weiterer Eintrag in der Ordnerliste (je Ordner Git-Soll + eigene
      Merkliste); Kosten sind nur groessere Merkdateien, keine Laufzeit.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Hermes/scripts/dateischwund-wache.py

- [ ] **T-193 — Dauerlauf stirbt nach rund einem Zyklus an SIGTERM (Rueckgabe 143)**
      Kontext: Am 30.09.2026 waren zwischen 01:52 und 02:39 **alle drei Dauerlauf-Stufen
      tot** (Sperrdateien 52312/61436/42504, kein passender Prozess). Die Waechter-Aufgaben
      arbeiten korrekt - sie erkannten die verwaisten Sperren und starteten neu
      (`Routinen/logs/handel-dauerlauf-letzter-lauf*.log`: 02:05, 02:07, 02:08, 02:24) -
      aber jede neue Instanz starb nach etwa einem Zyklus wieder. Kein Rechnerneustart
      (letzter Start 29.09. 21:06:19), kein Traceback. Die Todesart steht im Log als
      **`<spur> Rueckgabe 143`** = SIGTERM (128+15): 29.09. 23:22:59 bei `xperp`,
      30.09. 02:36:55 bei `kraken`. Ein Handstart schaffte 16 Spuren und lief bis zum
      kraken-Zyklus; in jenem Lauf war mein eigener `timeout` nicht auszuschliessen,
      der Wert trat aber schon am 29.09. ohne Fremdeinwirkung auf.
      Verdacht: ein Kindprozess beendet den ganzen Baum mit, statt nur sich selbst -
      `moondev_dauerlauf.py:417 _stoppe` beendet mit `taskkill /T /F` den GANZEN Baum,
      und sein Prozessfilter kann die eigene Kommandozeile treffen (Falle vom 24.09.).
      Die Wrapper starten mit `-WindowStyle Hidden` OHNE Umleitung, deshalb ist der
      Sterbegrund bisher unsichtbar.
      Naechster Schritt: (1) die Wrapper leiten stdout/stderr nach
      `Routinen/logs/dauerlauf-<stufe>-kind.log` um - erst dann ist der Sterbegrund
      lesbar; (2) pruefen, ob `moondev_dauerlauf._stoppe` fremde Prozesse trifft;
      (3) Wache auf "kein Zyklus seit >10 min" statt nur "PID tot".
      URSACHE GEFUNDEN UND BEHOBEN (30.09.2026, Commit 41d2ffa): Nicht der
            Prozessbaum war schuld, sondern die Sperre selbst. `handel-dauerlauf.ps1`
            schreibt die PID, die `Start-Process` zurueckgibt - bei einem
            venv-Startprogramm ist das der ELTERNPROZESS des Interpreters, nicht der
            Lauf. `sperre.belegt()` verglich sie mit `os.getpid()`, sah ein lebendes
            fremdes Python und liess den Lauf mit "Es laeuft bereits ein Dauerlauf der
            Stufe niedrig" sofort enden. Die Rueckgabe 143 war eine Verwechslung: in
            meinem Handstart kam sie von MEINEM eigenen `timeout` (feuerte in derselben
            Sekunde), nicht vom Lauf. Fix: `belegt()` nimmt auch `os.getppid()` aus -
            der eigene Starter ist kein fremder Lauf. Gegenprobe ohne den Fix: 1 roter
            Test, mit Fix 17/17. Punkt (1) erledigt: der Wrapper leitet stdout/stderr
            nach `Routinen/logs/dauerlauf-<stufe>-kind[.err].log` um - ohne diese
            Umleitung war der Sterbegrund nicht auffindbar, sie hat ihn gefunden.
            Punkt (2) entfaellt, kein taskkill im Spiel. OFFEN bleibt (3): eine Wache
            auf "kein Zyklus seit >10 min" statt nur "PID tot" - sie haette den Ausfall
            um 01:52 in Minuten statt in 47 gemeldet. Alle drei Stufen laufen seit
            02:51/02:55 wieder vollstaendig (30 Spuren je Zyklus).
            Angelegt: 2026-09-30
            Betrifft: Agenten/Routinen/handel-dauerlauf.ps1, Agenten/Handel/moondev_dauerlauf.py

- [ ] **T-192 — Auswertung: drei Messluecken lassen tote Spuren lebendig aussehen**
      Kontext: Die Auswertung vom 30.09.2026 (`auswertung_alle.py` alle drei Stufen +
      `kosten_wendepunkt.py`) zeigt drei Luecken, die jede Zahl verzerren.
      (1) **Kein Gebuehrenfeld**: `orb`, `orbk`, `scanner`, `moondev_signalwelle` und
      `iv_wand` tragen in ihrer `wachen.json` ueberhaupt keinen Gebuehrenschluessel
      (`grep gebuehr` in orbk/*.py findet nichts). Der Kosten-Wendepunkt rechnet sie
      deshalb mit 0 % und nennt orb +0,07 %, orbk/mittel +0,01 %, orbk/hoch +0,03 %
      "tragfaehig, haengt an der Gebuehrfreiheit (unter 0,4 %)". orbk ist aber
      **ORB auf Kraken-Spot** und die gemessene Kraken-Gebuehr ist **0,600 % je Seite
      = 1,2 % je Runde** (Fuellung 22.09.2026) - orbk ist damit um rund das 40-fache
      tot, orb (OKX, ~0,1 %/Runde) in Basis ebenfalls.
      (2) **orbk-Journal ohne Einsatz**: `orbk/handelsjournal.csv` fuehrt
      `zeit,inst,richtung,einstieg,stop,ziel,ausgang,ausstieg,gv_punkte,gv_usd` -
      ohne Einsatzspalte sagt der Bericht "Ergebnis in Prozent: kein Einsatz im
      Journal", 16 Runden lassen sich nicht in Prozent ausdruecken.
      (3) **Papierzeilen ohne Gebuehr**: alle Papierbuecher melden "Kosten 0.00 %",
      die echten 0.05 % (scanner), 0.39-0.50 % (xperp/swap) und 0.60 % (kraken) -
      die Papiersummen sind BRUTTO und mit den Live-Zahlen nicht vergleichbar.
      Naechster Schritt: (1) Gebuehr in die wachen.json von orb/orbk/scanner/
      moondev_signalwelle/iv_wand eintragen (Kraken 0.006, OKX 0.0005), dann
      `kosten_wendepunkt.py` erneut - das Urteil der Spuren aendert sich damit;
      (2) orbk schreibt den Einsatz je Runde mit (Muster scanner);
      (3) `auswertung_alle.py` weist brutto UND netto aus und markiert Bruttozeilen.
      Fortschritt: (1) erledigt am 30.09.2026 (Commit 7c525cd) - `gebuehr_taker` steht
      jetzt in orb (0.0005), orbk (0.006), scanner (0.0005), moondev_signalwelle (0.0005)
      und iv_wand (0.0005), dazu ein Einheitenfehler im Werkzeug behoben: es druckte den
      Bruch als Prozentwert und verglich ihn direkt mit f_max. Neues Urteil: orbk
      "1.200 % je Runde (0.600 % je Seite) liegt darueber" - tot. Test
      `tests/test_kosten_wendepunkt.py` (9). Punkte (2) und (3) bleiben offen.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Handel/{orb,orbk,scanner,moondev_signalwelle,iv_wand}/wachen.json,
                Agenten/Handel/auswertung_alle.py, Agenten/Handel/kosten_wendepunkt.py

- [ ] **T-191 — Webhook und OmniRoute hoeren auf 0.0.0.0, nicht nur auf localhost**
      Kontext: Nachgemessen am 30.09.2026 01:52. Der Hermes-Dienstprozess 73852 haelt
      `0.0.0.0:8644` UND `[::]:8644` (Webhook-Plattform) - also aus dem lokalen Netz
      erreichbar, obwohl die Steuerwege auf `127.0.0.1` liegen. Derselbe Befund beim
      OmniRoute-Router (`node`, PID 15924, `0.0.0.0:20128`). Beides ist bewusst NICHT
      angefasst worden (laufende Dienste); ohne Firewall-Regel ist jeder Rechner im
      WLAN ein moeglicher Aufrufer.
      Naechster Schritt: entscheiden - Bindeadresse auf `127.0.0.1` ziehen (Webhook
      braucht dann einen Reverse-Proxy fuer Fremdzugriff) ODER eine eingehende
      Firewall-Regel auf die beiden Ports setzen. Vorher pruefen, ob ein Telefon/
      ein anderes Geraet den Webhook wirklich aufruft.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: Agenten/Hermes/gateway-service, `C:\Users\faupe\.omniroute\`, Windows-Firewall
- [ ] **T-190 — Hermes-Update: Orphan-Aliase und Checkout-Reste**
      Kontext: Nach dem Update vom 29./30.09.2026 meldet `hermes doctor` 14 Orphan-Aliase
      (`agent-reach.bat`, `coder.bat`, `nous.bat`, `projectatlas.bat`, `superpowers.bat` und neun weitere)
      fuer Profile, die es nicht mehr gibt — die `.bat` liegen als Leichen im Alias-Ordner.
      Ausserdem zeigt der Checkout einen lokalen `Dockerfile`-Unterschied.
      Naechster Schritt: Alias-Ordner auflisten, die 14 Leichen nach `.sicherung/` verschieben,
      `Dockerfile`-Diff ansehen (eigene Anpassung oder Rest) und dann committen oder verwerfen.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: Agenten/Hermes/alts/, Agenten/Hermes/hermes-agent/Dockerfile
- [ ] **T-189 — claude-red: vier SKILL.md hat Defender entfernt, der Klon zeigt sie als Loeschung**
      Kontext: Beim Flottenlauf am 30.09.2026 (46 Klone) ist `claude-red` aktuell,
      traegt aber vier `D`-Eintraege im Arbeitsbaum
      (`Skills/infrastructure/offensive-shellcode`, `Skills/web/offensive-file-upload`,
      `Skills/web/offensive-rce`, `Skills/web/offensive-sqli`). Ursache ist Windows
      Defender (Fundort `Get-MpThreatDetection`), nicht der Klon; der Fundus deckt
      deshalb 75 von 79 Skills. `git checkout` holt die Dateien zurueck, der
      LESEZUGRIFF bleibt aber gesperrt ("Datei enthaelt einen Virus").
      Naechster Schritt: entscheiden, ob eine Defender-Ordnerausnahme fuer
      `Werkstatt/Repos/claude-red/Skills/` gesetzt wird (dann alle 79 lesbar) oder
      ob die vier gesperrt bleiben — der Stand ist so oder so zu dokumentieren.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `Werkstatt/Repos/claude-red/Skills/`, Fundus-Index
- [ ] **T-188 — OpenTerminal und osiris: lokale Aenderungen sperren das Vorspulen**
      Kontext: Beim Flottenlauf am 30.09.2026 waren beide hinter ihrem Original,
      wurden aber nicht gespult, weil sie Aenderungen an VERFOLGTEN Dateien tragen:
      `OpenTerminal` `package.json` + `package-lock.json` (4 Commits Rueckstand),
      `osiris` `package-lock.json` (5). Ein `.env.template` (untracked) sperrt
      nicht — nur verfolgte Dateien. Verwerfen ist laut Hausregel verboten, also
      bleibt der Klon stehen und die Aenderung entscheidet Max.
      Naechster Schritt: sagen, ob die beiden Sperren bleiben sollen (dann bleibt
      der Klon dauerhaft alt) oder ob die lokalen Aenderungen weg duerfen; danach
      `repos-updaten.py --nur OpenTerminal osiris`.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `Werkstatt/Repos/OpenTerminal/package.json`, `Werkstatt/Repos/osiris/package-lock.json`, `Agenten/Werkzeuge/repos-updaten.py`
- [ ] **T-187 — Zwei Klone stehen auf eigenem Zweignamen (84 und 91 Commits Rueckstand)**
      Kontext: `jev-chat-jarvis` liegt lokal auf Zweig `JEV`, `tradememory-protocol`
      auf `Werkstatt` — beide zeigen auf denselben Commit wie ihr Remote-Zweig
      (`origin/main` bzw. `origin/master`), nur der Name weicht vom Quell-
      Standardzweig ab (`upstream/main` bzw. `upstream/master`). Das Werkzeug raet
      den Zweig nicht und schaltet nicht um, deshalb steht bei beiden
      "anderer Zweig" im Bericht. Nachgemessen am 30.09.2026: 84 bzw. 91 Commits
      Rueckstand, gemessen ohne Umschalten.
      Naechster Schritt: entscheiden, ob die Namen bleiben (dann werden die beiden
      nie vorgespult) oder ob ein sauberes Umschalten auf main/master erlaubt ist;
      `repos-updaten.py --ausser` deckt sie bis dahin ab.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `Werkstatt/Repos/jev-chat-jarvis`, `Werkstatt/Repos/tradememory-protocol`
- [ ] **T-185 — Klon-.env-Kopien veralten ohne Nachweis (Kopien liegen seit 30.09.2026 in .sicherung)**
      Kontext: Von 47 Klonen unter `Werkstatt/Repos` tragen 7 eine `.env`, keine
      davon war gesichert (beide Sicherungen klammern `Werkstatt` per `/XD` aus,
      und die Klartext-Pruefung in `sichern.ps1` sieht sie deshalb ebenfalls
      nicht). Sechs Kopien liegen jetzt byte-gleich in
      `Agenten/Hermes/.sicherung/` (`moondev-env.bak-20260930`,
      `moondev-src-env.bak-20260930`, `openmontage-env.bak-20260930`,
      `openterminalui-env.bak-20260930`, `omniroute-werkstatt-env.bak-20260930`,
      `omniroute-home-env.bak-20260930`), Bestandsaufnahme in
      `.sicherung/klon-envs-20260930.md`, Wiki-Abschnitt in
      `Wiki/Betrieb/Sicherung-und-Laufwerke.md`. Aendert Max eine dieser
      `.env`, veraltet die Kopie still - bisher merkt das niemand.
      Naechster Schritt: entscheiden, ob ein Schritt in `sichern.ps1` (Kopien
      beim Lauf mitziehen und Abweichung melden) oder eine eigene Wache gebaut
      wird; bis dahin ist die Kopie ein Stand vom 30.09.2026.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `Agenten/sichern.ps1`, `Agenten/Hermes/.sicherung/`, `Werkstatt/Repos/*/.env`
- [ ] **T-186 — `C:\Users\faupe\.omniroute\` liegt in keiner Sicherungsquelle (1,2 GB)**
      Kontext: Der OmniRoute-Dienst haelt seinen Zustand unter
      `C:\Users\faupe\.omniroute\`: `storage.sqlite` (101 MB, Anbieter-
      Verbindungen und Kosten), `db_backups/`, `logs/`, `plugins/` - und eine
      `.env` mit `STORAGE_ENCRYPTION_KEY`, `JWT_SECRET`, `API_KEY_SECRET`. Kein
      Sicherungsskript erfasst diesen Pfad (Quellen sind `MaxHirn/` und
      `Agenten/`), und der Schluessel entschluesselt die Verbindungen in der
      Datenbank: ohne ihn ist der Router nach einem Wiederaufbau leer, obwohl
      die Datei da ist. Die `.env` allein liegt seit 30.09.2026 als Kopie in
      `Agenten/Hermes/.sicherung/omniroute-home-env.bak-20260930`; die Datenbank
      (mit laufendem Router nur im WAL-Stand kopierbar) ist NICHT gesichert.
      Naechster Schritt: entscheiden, ob `storage.sqlite` in die taegliche
      Sicherung aufgenommen wird (Kopie im laufenden Betrieb, `db_backups/`
      existiert bereits) oder ob ein Router-Ausfall bewusst hingenommen wird.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `C:\Users\faupe\.omniroute\`, `Agenten/sichern.ps1`

- [ ] **T-183 — NODE_ENV=production in der Agenten-Shell bricht jeden vite-Dev-Lauf**
      Kontext: Beim ersten echten Lauf der Skill-Anleitung `inspecting-hermes-desktop-dom`
      starb der Renderer mit `ReferenceError: $RefreshSig$ is not defined`
      (`apps/desktop/src/i18n/context.tsx`), `#root` blieb leer. Ursache ist ein geerbtes
      `NODE_ENV=production` in der Shell des Agenten: `@vitejs/plugin-react` emittiert dann
      die Fast-Refresh-Aufrufe OHNE die Laufzeit. Gemessen am 2026-09-30:
      `cmd /c "set NODE_ENV"` = production; NICHT in `HKCU\Environment`, NICHT in
      `terminal.docker_forward_env` der config.yaml (dort Zeile 2295 nur im env-Block des
      MCP-Servers desktop-commander). Mit `env -u NODE_ENV` vor vite UND electron mountet die
      App normal: 351 Knoten, 79 `[data-slot]`, ~32 s bis gemountet, Port 9333 liefert DOM
      und Konsolenfehler. Die Skill-Pitfalls sind entsprechend ergaenzt (Commit b39288f).
      Naechster Schritt: Quelle des geerbten NODE_ENV finden (Startweg der Hermes-TUI,
      `hermes.exe --tui` aus `Agenten/Hermes/bin`) und entscheiden, ob sie dort bleiben muss —
      sie faerbt JEDEN Dev-Server, den ein Agent startet, nicht nur diesen einen.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: `Agenten/Hermes/config.yaml`, `Agenten/Hermes/skills/software-development/inspecting-hermes-desktop-dom`, `apps/desktop` (Fremd-Checkout)

- [ ] **T-179 — Handels-Dauerlauf fiel 20:59 aus (0xC0000142), Ursache offen**
      Kontext: Alle drei Stufen (Basis/mittel/hoch) starben am 29.09. ~20:59: die Kindprozesse kamen nicht hoch (Rueckgabe 3221225794 = 0xC0000142, DLL-/Speicher-Initialisierung). Die Waechter starteten neu (23:05/23:07/23:08/23:20), aber die Neustarts starben ebenfalls. Belegt: 87 verwaiste node-Prozesse aus Hermes	ools (abgebrochener Build, alle seit 21:13:59, Eltern = Gateway 73852 mit 70 Kindern) + Commit frei 0 GB. Behoben 29.09. 23:23-23:34: 87 node-Waisen beendet, alle drei Stufen manuell neu gestartet - laufen wieder stabil (Zyklen 23:35). Die eigentliche Ursache des Todes um 20:59 (vor dem node-Waisen-Start 21:13) ist NICHT geklaert.
      Naechster Schritt: Beobachten, ob der Dauerlauf stabil bleibt; wenn er wieder mit 0xC0000142 stirbt, Commit/Seitenfile zum Tatzeitpunkt messen und die Waisen-Quelle (Gateway-Build) identifizieren.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Handel/dauerlauf.py, Agenten/Routinen/handel-dauerlauf.ps1


- [ ] **T-181 — Bonsai-Einbau der parallelen Sitzung nutzt Port 8080 (freqtrade-Konflikt)**
      Kontext: Eine parallele Sitzung baut Bonsai ein (Agenten/Hermes/scripts/bonsai-provider-einbauen.py) mit Port 8080 - genau der Port, den der Freqtrade-Container belegt (127.0.0.1:8080->8080). Ich habe am 29.09. auf 8081 umgestellt (Starter + Config); das Skript der parallelen Sitzung wuerde 8080 wieder einschreiben.
      Naechster Schritt: Das Skript der parallelen Sitzung auf 8081 anpassen oder nach dessen Lauf den Port erneut pruefen.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/scripts/bonsai-provider-einbauen.py


- [ ] **T-176 - Kill-Schalter geht nie wieder auf (spur_buch)**
      Kontext: Am 29.09.2026 endete der Backtest-Lauf von moondev_funding nach
      SECHS TAGEN mit kill_ausgeloest=true, obwohl das Buch im Plus war.
      Ursache ist der Bauart nach ein Fehler: `spur_buch.zyklus` kehrt bei
      gesetztem `kill` sofort zurueck (Zeile 571, Positionen werden geleert).
      Der Kill rechnet aber auf der Kapitalkurve (Ruecklauf vom Hoechststand),
      und die erholt sich nur durch neue Trades - genau die sperrt der Kill.
      Betroffen ist JEDE Spur, die ihr Buch ueber spur_buch fuehrt (alle
      Feed-Spuren), nicht nur funding. Beim Menschen faellt das nicht auf, weil
      er den Deckel von Hand hebt (xperp 21.09.2026: 40 -> 100).
      Naechster Schritt: entscheiden, ob der Kill nach einer Frist (z. B. 7
      Tage) oder nach Erholung der Kurve von selbst wieder aufgeht, oder ob er
      bewusst eine Handarbeit bleibt. Ohne Entscheidung bleibt es so.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/spur_buch.py, alle Feed-Spuren


- [ ] **T-178 - Einstiegsgrund im Journal der Buch-Spuren ist ein Platzhalter**
      Kontext: Jede Einstiegszeile der Feed-Spuren traegt als `grund` den Satz
      "Der Grund, der im Journal steht." - der Platzhalter steht auch in den
      ECHTEN Journalen (z. B. moondev_topmovers 15.09.2026), kommt also aus
      `spur_buch` und nicht aus dem Backtest. Der Ausstiegsgrund (ziel/stop) ist
      echt; der Einstiegsgrund sagt nichts, und wer ein Buch liest, kann die
      Einstiegsursache nicht nachvollziehen.
      Naechster Schritt: in `spur_buch` den echten Grund setzen (z. B. das
      Signal, das den Einstieg ausgeloest hat) - wirkt auf alle Buecher, daher
      mit den Spuren-Tests zusammen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/spur_buch.py, Journale der Feed-Spuren

- [ ] **T-166 - Zehn neue Repos haben kein Bot-Profil**
      Kontext: Am 29.09.2026 sind neun Repos ins Manifest der Repos-Zentrale
      aufgenommen worden (osiris, jev-trader, deepseek-harness,
      tradememory-protocol, ziplime, foreman, awesome-dsh-plugin,
      awesome-deepseek-harness-plugins, fast-jev-compaction, jev-chat-jarvis, OpenTerminalUI).
      Ihre Eintraege tragen bewusst KEIN `bot`-Feld - sonst zeigt die Zeile
      sofort "Bot-Profil fehlt". Das Hausmuster ist ein Profil je Repo
      (26 Repo-Bots, Wiki/Werkzeuge/Repo-Bots.md).
      Naechster Schritt: entscheiden, ob fuer die sechs STARTBAREN (osiris,
      jev-trader, deepseek-harness, tradememory-protocol, ziplime, OpenTerminalUI) Profile
      angelegt werden - `hermes profile create <name>` OHNE --clone, dann
      providers-/model-Block, terminal.cwd auf den Klon, auth.json als Symlink
      (braucht Admin: Agenten/Hermes/scripts/auth-verknuepfen.ps1).
      Angelegt: 2026-09-29
      Betrifft: Agenten/Hermes/profiles/, Agenten/Werkzeuge/repos-zentrale/

- [ ] **T-167 - foreman einrichten (venv fehlt)**
      Kontext: `foreman` steht in der Repos-Zentrale unter EINRICHTEN, weil im
      Klon kein venv liegt. Ohne venv laesst sich der Startbefehl nicht
      belegen, und die Gegenprobe (test_manifest_gegenprobe) verlangt zu jedem
      `start` eine Logdatei.
      Naechster Schritt: `python -m venv .venv` im Klon,
      `.venv\Scripts\python.exe -m pip install -e ".[dev]"`, dann
      `foreman demo --repo .` als Beleglauf starten und den Eintrag auf
      STARTBAR ziehen.
      Angelegt: 2026-09-29
      Betrifft: Werkstatt/Repos/foreman/

- [ ] **T-168 - deepseek-harness: Klon ungebaut, UI laeuft nur ueber npx**
      Kontext: Die Web-UI startet ueber `npx -y @deepseek-ai/dsh web`
      (Port 3080, belegt am 29.09.2026) - das laedt das VEROEFFENTLICHTE Paket,
      nicht den eigenen Klon. Der Klon hat kein node_modules; der Weg
      `pnpm install && pnpm run build && pnpm dsh web` steht im Manifest, ist
      aber nie gelaufen.
      Naechster Schritt: nur falls der eigene Klon gebraucht wird (eigene
      Aenderungen am Harness), pnpm install + build einmal durchlaufen lassen
      und belegen. Sonst bleibt der npx-Weg der richtige.
      Angelegt: 2026-09-29
      Betrifft: Werkstatt/Repos/deepseek-harness/

- [ ] **T-169 - tradememory-protocol: Browser-Dashboard nicht gebaut**
      Kontext: `.venv\Scripts\tradememory-api.exe` liefert auf Port 8000 die
      REST-API (belegt am 29.09.2026), aber KEIN Dashboard - dafuer fehlt
      `dashboard/dist`. Die oeffentliche Demo laeuft auf
      tradememory-dashboard.onrender.com.
      Naechster Schritt: entscheiden, ob das Dashboard lokal gebaut wird (Node
      im dashboard/-Ordner, Vite) oder ob der Eintrag dauerhaft "API ohne
      Dashboard" heisst.
      Angelegt: 2026-09-29
      Betrifft: Werkstatt/Repos/tradememory-protocol/dashboard/

- [ ] **T-170 - ziplime: OPENROUTER_API_KEY fehlt fuer den Assistenten**
      Kontext: `python -m ai_assistant` startet und fragt dann nach dem
      OpenRouter-Schluessel (so im Beleglauf vom 29.09.2026). Ohne ihn laeuft
      nur die Backtest-CLI; das venv ist vollstaendig.
      Naechster Schritt: entscheiden, ob ein OpenRouter-Zugang hinterlegt wird
      (Wissen/Zugaenge.md ist die einzige Ablage) oder ob ziplime ohne
      Assistent bleibt.
      Angelegt: 2026-09-29
      Betrifft: Werkstatt/Repos/ziplime/

- [ ] **T-171 - O:\Werkstatt 2\ enthaelt nur noch eine zweite Kopie von deepseek-harness**
      Kontext: Bestandsaufnahme 29.09.2026 - der Ordner trug zunaechst sieben
      Repos, davon lagen sechs bereits in `Werkstatt/Repos/` (dorthin
      aufgenommen). Uebrig ist eine ZWEITE Kopie von `deepseek-harness`.
      Doppelte Klone kosten Platz und stiften Verwirrung beim Vorspulen.
      Naechster Schritt: entscheiden, ob die Kopie weggelegt oder geloescht
      wird. NICHTS geloescht, solange Max nicht zustimmt.
      Angelegt: 2026-09-29
      Betrifft: O:\Werkstatt 2\


- [ ] **T-160 - Acht Feed-Spuren: eine Position verliert ihren Kurs, wenn ihr Symbol aus dem Feed faellt**
      Kontext: Bei diesen Spuren kommt der Kurs aus dem AKTUELLEN Feed
      (`quelle()` baut `kurse` aus den heutigen Kandidaten). Faellt ein Symbol
      aus dem Feed (Top-Movers wechseln taeglich, Token verliert die Bewertung,
      Liste wird umgestellt), bekommt seine offene Position keinen Kurs mehr.
      `spur_buch.pruefe_ausstiege` behaelt sie dann (seit 29.09.2026 mit
      Meldung auf stderr) - sie wird nie geschlossen, belegt einen Platz und
      das Journal friert ein. Gemessen am 29.09.2026 durch Vergleich aller
      `quelle()`-Funktionen: betroffen sind moondev_liquidation,
      moondev_listingarb, moondev_marktlage, moondev_sentiment,
      moondev_signalwelle, moondev_topmovers, moondev_whale und
      robinhood_radar. KEIN Thema bei den Ein-Instrument-Spuren
      (trendwende_btc, liq_wand, iv_wand) - dort kann das Symbol nicht
      wechseln.
      VORLAGE im Haus: `moondev_sniper/handeln.py` Zeilen 156-165 holt nach dem
      Aufbau von `kurse` die Preise der gehaltenen Positionen nach
      (`pump_letzter_preis`, Fehler werden gemeldet, nicht geworfen).
      moondev_funding ist am 29.09.2026 behoben (Plan + Bestand ueber
      `wp.pruef_instrumente`).
      Naechster Schritt: je Spur die Preisquelle fuer ein EINZELNES Symbol
      bestimmen (CoinGecko `maerkte()`, OKX `okx.letzter_kurs`, Pump
      `pump_letzter_preis`, Robinhood-DB) und den Block aus moondev_sniper
      uebernehmen; je Spur ein Test 'Position ohne Feed-Symbol wird geschlossen'.
      Angelegt 2026-09-29. Betrifft Agenten/Handel/{moondev_*,robinhood_radar}/handeln.py.


- [x] **T-156 — Bonsai aus, aber zwei MoA-Presets haengen daran**
      Kontext: `hermes moa list` zeigt fuer die Presets "Max 2" und "Vision" den Aggregator `bonsai` - dort
      laeuft die ganze Werkzeugschleife, nicht nur eine Beratung. `delegation.fallback_providers` hat bonsai
      an Stelle 2 (vor ollama-launch gesetzt, s. u.). Der Dienst antwortet nicht: Port 8081 zu, gemessen mit
      `scripts/config-gegenprobe.py`. Config und Starter nennen inzwischen denselben Port (8081).
      **Erledigt 29.09.2026 - umgestellt, nicht Bonsai gestartet.** Aggregator der Presets `Max 2` und
      `Vision` ist jetzt `ollama-launch/gemma-e4b-8k:latest`; die drei toten `bonsai`-Referenzen (Preset
      `default`, Preset `Max 2`, Top-Level-Block) stehen auf `enabled: false`. Werkzeug
      `cache/scratch/moa-umstellen.py`: zaehlt die Vorkommen, prueft `yaml.safe_load` VOR dem Schreiben,
      Sicherung `config.yaml.bak-moa-20260929_234442`.
      Warum gemma: `/api/show` meldet 131072 Kontext bei 7,52 B Parametern (der Name traegt "8k", der
      Kontext ist es nicht) und ueber den OpenAI-Weg kommt sauberer `content` ohne Denkanteil - 19 s fuer
      einen echten Aggregationsauftrag.
      Nachweis: `hermes moa list` nennt fuer beide Presets `ollama-launch:gemma-e4b-8k:latest`,
      `hermes config check` exit 0, `git diff --numstat` 7/7 (CR == LF).
      Offen: `delegation.fallback_providers` fuehrt `bonsai` weiter an Stelle 2 - ein Eintrag, der
      durchfaellt und wieder greift, sobald der Dienst laeuft. Bonsai bleibt aus (entlaedt sonst die
      Ollama-Modelle aus dem VRAM, die die Sprachmodell-Spuren brauchen).
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/config.yaml, Agenten/Werkzeuge/bonsai-27b.ps1

- [ ] **T-157 — Hauptprofil hat keinen lokalen Rueckfall**
      Kontext: `hermes fallback list` im Hauptprofil = nous/deepseek-v4.1-flash, nous/upstage/solar-pro4:free.
      Alle 22 Profile haben seit 21.09.2026 `ollama-launch/gemma-e4b-8k:cpu` an erster Stelle; nur das
      Hauptprofil faehrt zwei Anbieter-Eintraege desselben Anbieters. Die lokalen Modelle tragen 131k-262k
      Kontext (`/api/show`), die 64k-Grenze ist also kein Hindernis.
      Naechster Schritt: dritten Eintrag `ollama-launch/gemma-e4b-8k:cpu` ergaenzen - bewusst als Entscheidung
      offen gelassen, weil eine Notiz vom 21.09.2026 den Zustand "absichtlich unveraendert" nennt.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/config.yaml

- [ ] **T-158 — moa:-Block traegt Schluessel, die Hermes nicht kennt**
      Kontext: `hermes config get moa.enabled` antwortet "'moa.enabled' is not a recognized config key", und
      `hermes moa list` meldet "Active in config: (off)". Damit sind die Top-Level-Schluessel `enabled`,
      `aggregator`, `reference_models`, `degraded_reference_policy`, `fanout`, `max_tokens` (~25 Zeilen)
      toter Text; gelesen werden `presets` und `default_preset`.
      Naechster Schritt: in `hermes_cli/config_defaults.py` nachsehen, welche Schluessel die laufende Version
      liest, dann die toten Zeilen entfernen - erst nach Ruecksprache, weil sie Max' Presets dokumentieren.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/config.yaml

- [ ] **T-159 — affinity-SSE-Adresse localhost:6767 antwortet nicht**
      Kontext: In 18 Configs steht `SSE_URL: http://localhost:6767/sse`; der Port ist zu (gemessen mit
      `scripts/config-gegenprobe.py`). Der Server selbst arbeitet - `hermes mcp test affinity` listet 13
      Werkzeuge - der Eintrag ist also ein Rest ohne Wirkung.
      Naechster Schritt: nur aufraeumen, wenn Affinity weiter genutzt wird; sonst den Server abschalten
      (jeder aktive MCP-Server kostet Werkzeugschemas in jeder Anfrage).
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/config.yaml und die Profile


- [ ] **T-155 — Bonsai-Dienst ist startbar, aber ungeprueft**
      Kontext: Port-Konflikt behoben (8080 gehoerte dem Freqtrade-Container, jetzt 8081 in Starter und Config). Ein echter Start wurde NICHT gefahren: der Dienst ist ein Schwergewicht und entlaedt die Ollama-Modelle aus dem VRAM, die die Sprachmodell-Spuren im Handel gerade brauchen.
      Naechster Schritt: Bonsai in einer ruhigen Minute starten (Werkzeuge/bonsai-27b.ps1 -Aktion start) und pruefen, ob er als Agent-Modell durchgeht (64k Kontext); danach entscheiden, ob delegation.provider auf bonsai zurueckgeht.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Werkzeuge/bonsai-27b.ps1, Agenten/Hermes/config.yaml
      Nachtrag 29.09.2026: Nicht nur ein Testfall - die MoA-Presets **Max 2** und **Vision** haben
      `bonsai` als AGGREGATOR (`hermes moa list`), dort laeuft die ganze Werkzeugschleife. Solange
      der Dienst aus ist, sind diese beiden Presets nicht benutzbar; siehe T-156.



- [ ] **T-152 - MCP-Spawn-Kette: Ursache des Zombie-Kreises dauerhaft beheben**
      Kontext: Die Wache mcp-zombie-wache (Cron 15 min) haelt die MCP-Gruppen bei 3 Prozessen,
      behebt aber nur das SYMPTOM. Die Ursache - etwas startet die MCP-Server im Kreis (mail/
      windows-mcp/kraken/archiv/tooluniverse/blender wuchsen seit dem Boot auf bis zu 44 Kopien)
      - ist noch nicht gefunden. Das MCP-Manifest selbst ist sauber (je Server ein Eintrag,
      keiner ruft den anderen); Fundort der Spawn-Kette ist der Startweg in
      claude_desktop_config.json bzw. Agenten/Hermes/config.yaml gegen die Server-venv-Autostarts.
      Max hat 29.09.2026 Option 4 gewaehlt: jetzt NICHT anfassen, Wache beobachten.
      Naechster Schritt (eigener abgestimmter Eingriff): die Start-Konfiguration beider Apps
      gegen die Server-Starts pruefen, Kreis schliessen, Wache auf dauerhaft 0 Meldungen stellen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/MCP-Manifest.json, claude_desktop_config.json, Agenten/Hermes/config.yaml


- [ ] **T-146 — Der Gateway-Waechter braucht eine Gegenprobe fuer beide Startformen**
      Kontext: Am 29.09.2026 startete `Routinen/gateway-waechter.ps1` den Gateway 148-mal neu,
      weil sein Suchmuster nur die Launcher-Kommandozeile traf, nicht die `runpy`-Form des
      Update-Wegs. Behoben (Identitaet aus `gateway_state.json` zuerst, Kommandozeile als
      Rueckfall mit beiden Formen) und belegt: 19:15:13 und 19:15:59 "Gateway laeuft ..., kein
      Start". Es gibt aber keinen Test, der den Rueckfall prueft.
      Naechster Schritt: kleine Pruefung (PowerShell oder Python-Test), die beide
      Kommandozeilenformen gegen die Waechter-Muster haelt, plus eine, die einen falschen
      Zustand als "Neustart" erwartet.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Routinen/gateway-waechter.ps1




- [ ] **T-148 — Der Web-Bau des Dashboards bricht an fehlendem `vitest` ab**
      Kontext: `npm run build` im `hermes-agent/web` scheitert mit `tsc -b`
      (`apps/shared/src/*.test.ts`: "Cannot find module 'vitest' or its corresponding type
      declarations", 27 Zeilen im Protokoll vom 19.09.2026); der Dienst startet dann mit
      "serving stale dist as fallback". Im `apps/shared` stehen Testdateien im Bauprogramm,
      `vitest` liegt aber nur im Wurzel-`node_modules`.
      Naechster Schritt: entscheiden - beobachten (upstream) oder lokal `vitest` in
      `apps/shared/devDependencies` aufnehmen (wirkt bis zum naechsten Update, das die Datei
      zuruecksetzt). Kein Handlungsdruck: der Dienst laeuft (HTTP 200).
      Angelegt: 2026-09-29
      Betrifft: Agenten/Hermes/hermes-agent/web, apps/shared/tsconfig



- [ ] **T-150 — 18 Commits Rueckstand im Hermes-Checkout, Update nicht wiederholt**
      Kontext: Der Lauf am 29.09.2026 18:46 endete `partial` (Gateway-Restart) und ist 3,5 h
      spaeter; `origin/main` ist inzwischen 18 Commits weiter (HEAD `ca705dbf7e`, 0.21.5).
      Arbeitsbaum sauber, leerer Autostash verworfen, `pm_sync_outcome: ok`.
      Naechster Schritt: `hermes update` erneut fahren, DETACHED (Start-Process ueber eine
      cmd-Datei, PYTHONHOME/PYTHONPATH darin leeren) - als Kind der Agenten-Shell stirbt der
      Lauf beim Gateway-Stopp. Danach Dashboard-Start und `hermes doctor` pruefen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Hermes/hermes-agent, Agenten/Hermes/logs/update_receipts/

- [ ] **T-142 — Der Grund im Journal der Feed-Spuren ist ein Platzhalter**
      Kontext: Bei jedem Einstieg steht "Der Grund, der im Journal steht." in
      der Spalte `grund`. Der Text kommt aus dem Dummy-Schluessel `_grund` der
      wachen (moondev_topmovers/-marktlage/-signalwelle, iv_wand, moondev_whale,
      -liquidation, -sentiment). Gemessen am 29.09.2026: auch das ECHTE Journal
      vom 15.09.2026 traegt ihn, es ist also kein Fehler der Rueckrechnung,
      sondern Bestand. Folge: jede Auswertung, die den Grund lesen will, liest
      Nichts - bei 55 Runden im Ruecklauf ist nicht zu sagen, welches Signal
      gegriffen hat.
      Naechster Schritt: `spur_buch` schreibt den echten Grund (Signal/Regel)
      statt `_grund`. Wirkt auf ALLE Spuren dieser Familie, daher eigene Aufgabe
      mit Gegenprobe. Entscheidung Max.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/spur_buch.py, wachen.json der Feed-Spuren


- [ ] **T-143 — Der Funding-Ruecklauf endet an der eigenen Ratsche**
      Kontext: moondev_funding 2021-2026 liefert 23 Runden, aber
      `kill_ausgeloest = true`: die Drawdown-Ratsche hat den Lauf beendet. Die
      23 Runden decken damit NICHT den Zeitraum - die Zahl ist ein Anfang, kein
      Ergebnis.
      Naechster Schritt: entscheiden, ob der Ruecklauf die Ratsche stilllegen
      soll (dann misst er die Strategie) oder ob der Abbruch das Ergebnis IST
      (dann braucht der Lauf eine eigene Kennzahl "Zeit bis Abbruch"). Nicht
      selbst entschieden: es aendert die Vergleichbarkeit aller Folgelaeufe.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/replay.py (lauf_c), moondev_historie.py


- [ ] **T-144 — Die Signalwelle rechnet im Ruecklauf auf kleinerem Universum**
      Kontext: 41 Symbole mit 1H-Kerzen gegen 250 Coins im Betrieb; der Lauf
      liefert 62 Runden. Die Zahl ist mit dem Betrieb nicht vergleichbar, weil
      das Tor (Aenderung 1h, Volumen 24h) auf einem kleineren Feld greift.
      Naechster Schritt: entweder das Universum aufziehen (1H-Kerzen fuer 250
      Symbole, ~1,5 GB) oder in jeder Aussage dazuschreiben. Entscheidung Max.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/daten/historie/feed, Wiki/Handel/Backtest-Fundament.md


- [ ] **T-145 — CoinGecko antwortet von diesem Rechner mit HTTP 403**
      Kontext: Der frische Gegenprobe-Abzug (`daten_probe_coingecko.py`) wird
      von Cloudflare abgewiesen. Die Gegenprobe laeuft deshalb gegen die Preise,
      die die Spuren sich selbst geholt haben (echte Journals): 40 Preise
      verglichen, groesste Abweichung 13,5 %.
      Naechster Schritt: den Abzug einmal aus einem Browser oder einem anderen
      Netz aufzeichnen und als `daten/historie/coingecko_probe.json` ablegen -
      der Test prueft ihn dann automatisch statt zu ueberspringen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/daten_probe_coingecko.py, tests/test_replay_feed.py


- [ ] **T-141 - Braucht ein Werkzeug TCP 9900? Der Gateway lauscht nur noch auf dem Control-Pipe**
      Kontext: Seit dem Hermes-Update vom 29.09.2026 lauscht der Gateway auf einem Named Pipe
      (`\\.\pipe\hermes-gateway-*`, belegt: 1 Pipe im Namensraum) und bedient Webhooks auf 8644;
      **TCP 9900 bleibt zu, waehrend der Dienst gesund laeuft** (`hermes gateway status` =
      "Gateway process running", `hermes doctor` = "gateway running", Telegram wurde bedient).
      Die zwei Haus-Wachen sind umgestellt (siehe T-139). Offen ist, ob ein a2a-Peer oder ein
      Fremdwerkzeug den Port erwartet - die Peer-Liste steht in der `a2a_agents`-Sektion der
      Hermes-`config.yaml`.
      Naechster Schritt: einen Peer-Aufruf aus einer Bot-Sitzung fahren (`a2a_list`/`a2a_call`);
      gelingt er ohne 9900, ist der Port endgueltig Altweg.
      KORREKTUR 2026-09-30: Die Annahme "TCP 9900 bleibt zu, waehrend er gesund laeuft"
      ist widerlegt. Gemessen am 30.09.2026 01:52 mit `Get-NetTCPConnection`: der
      Dienstprozess 73852 haelt **127.0.0.1:9900** (A2A) und **0.0.0.0:8644** (Webhook).
      Der Gateway laeuft als EINE Kette 73620 (Launcher-venv) -> 36840 (.hermes-runtime)
      -> 73852 (tools-Python, `runpy`-Form, schreibt `gateway_state.json`). Die
      Prozesssuche `*gateway run*` findet 73852 NICHT (die runpy-Form traegt den Text
      nicht) - deshalb lesen die Wachen zuerst `gateway_state.json`. Offen bleibt nur,
      ob ein Peer den Port BRAUCHT: er ist da, also ist die Frage nach dem Altweg erledigt.
      Angelegt 2026-09-29. Betrifft Agenten/Hermes (config.yaml), Agenten/Routinen/gateway-waechter.ps1.


- [ ] **T-140 - Gateway-Wache laeuft nur 08:15: ein abends gescheitertes Update faellt erst am Morgen auf**
      Kontext: Die Wache `gateway-identitaet-wache` (Cron, taeglich 08:15) prueft genau die
      Bedingung, an der `hermes update` am 26.09.2026 abbrach. Ein Update am Abend (typisch: die
      Halter-Aufgabe laeuft 21:00) wuerde einen erneuten Identitaetsverlust aber erst am
      naechsten Morgen melden.
      Naechster Schritt: Entscheidung von Max - zweiter Lauf am Abend (z.B. 21:45, nach dem
      Zwischenstand) oder bei 08:15 belassen. Vorher keine Aenderung.
      Angelegt 2026-09-29. Betrifft Agenten/Hermes/scripts/gateway-identitaet-wache.py, Cron.













- [ ] **T-122 - iv_waelle: der Wandweg bleibt ungemessen, nur der Spannenweg ist belegt**
      Kontext: Die Spur hatte seit dem 19.09.2026 kein Geschaeft, weil ihr Tor
      (Wand hoechstens 0,5 % neben dem Kurs, im Band Grenze..3 Sigma) an echten
      Deribit-Ketten nie aufgeht - gemessen 29.09.2026: Call-Wand 90.000 =
      3,13 Sigma, Put-Wand 60.000 = 13,9 Sigma (Basis 84.470, Sigma 1.765). Seit
      dem 29.09.2026 gibt es den zweiten, GEMESSENEN Weg (`signal_an_der_spanne`,
      k=1,0 / Stop 0,5 Sigma / halber Rueckweg = +0,276 % je Runde, 204/400 Tage)
      plus Ausstieg am Tagesende; das Journal liegt mit Kopfzeile bereit.
      Offen bleibt: (a) der Wandfilter ist weiter nicht messbar - es gibt bei
      Deribit keine Open-Interest-HISTORIE (nur den aktuellen Stand), deshalb
      kann niemand sagen, ob eine Wand damals ein Signal war; (b) nur BTC und nur
      das eine Regime der 400 Tage; (c) Perpetual-Funding fehlt in der Rechnung.
      Naechster Schritt: entscheiden, ob (a) als dauerhaft ungemessen im Code
      vermerkt bleibt (Vorschlag) und (b) mit einem zweiten Instrument
      (ETH-PERPETUAL) gegengeprueft wird.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/iv_waelle/.


- [ ] **T-121 - Dasselbe Loch wie bei den vier Indikatorspuren in weiteren Spuren suchen**
      Kontext: Eine Spur prueft ihre Ausstiege ueber ihre PLAN-Instrumente
      (`w["instrumente"]`). Wird der Plan umgestellt, sind offene Positionen
      darauf unsichtbar: sie werden nie geprueft, nie geschlossen, belegen die
      Plaetze, und das Journal friert ein (Befund 29.09.2026: macd_mtf, squeeze,
      wavetrend, supertrend, acht Tage ohne Zeile). Behoben fuer diese vier
      (`scanner/wachen_pruefung.pruef_instrumente` = Plan + Bestand; Einstieg
      bleibt auf den Plan begrenzt; Test
      `Agenten/Handel/tests/test_verwaiste_instrumente.py`). Andere Spuren mit
      Instrumentenliste im Plan sind NICHT geprueft.
      Naechster Schritt: alle Spuren mit `instrumente` in der wachen auflisten
      (`git grep -l '"instrumente"' Agenten/Handel/*/wachen*.json`), je Spur die
      Ausstiegsschleife ansehen und die Regel nachziehen, wo sie fehlt.
      TEILBEFUND 29.09.2026: es sind neun Wachen mit `instrumente`
      (iv_waelle, macd_mtf, moondev_funding, mosaic, orb, orbk, squeeze,
      supertrend, wavetrend). FIX sind die vier Indikatorspuren und seit
      dem 29.09.2026 auch mosaic (Papierzweig laeuft ueber `pruef_instrumente`,
      Einstieg bleibt auf den Plan begrenzt, Tests
      `mosaic/tests` 101 gruen). SICHER ohne Pruefung: iv_waelle (Schleife ueber
      die Marktdaten des Zyklus), orb/orbk (je eine Konfiguration je Instrument).
      OFFEN: moondev_funding sammelt seine Kurse ueber die Plan-Liste
      (handeln.py:356) - eine Position auf einem gestrichenen Symbol bekommt
      keinen Kurs mehr; spur_buch meldet das inzwischen, schliesst sie aber
      nicht. Ebenso ungeprueft: Spuren ohne `instrumente`-Liste, die intern
      ueber eine feste Symboltabelle laufen.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/*/handeln.py.


- [ ] **T-119 - MAE/MFE je Position vollstaendig fuehren (sonst kein Stop aus Daten)**
      Kontext: Der Stop-Vorschlag aus `stop_from_mae` (90-%-Quantil der MAE der
      Gewinner) braucht echte Werte. Gemessen am 29.09.2026: der scanner schreibt
      bei Ausstiegen mit Grund `ziel` durchweg `mae_pct = 0.0000`; echte Werte
      stehen nur bei stop (13), herzschlag_alt (18), buchbereinigung (2) und
      handverkauf_boerse (2). kraken und die uebrigen Spuren haben die Spalte
      gar nicht. `strategie_kennzahlen.py` schreibt deshalb 'MAE ungefuehrt',
      statt eine Null als Messwert auszugeben.
      Naechster Schritt: in den Spuren beim Schliessen/Trail den
      Zwischenverlust mitschreiben (Hoch/Tief seit Einstieg), Spalte in allen
      Journalen fuellen; danach den Stop-Vorschlag je Spur gegen den gefahrenen
      Stop stellen.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/<spur>/handeln.py, Journale.


- [ ] **T-115 - Kraken-USDC: Umstellung vorbereitet, es fehlt das USDC-Guthaben**
      Kontext: Auftrag Max 28.09.2026 ("Welche Spuren koennen live auf Kraken USDC
      geschaltet werden?"). Kraken listet 45 USDC-Paare, darunter XBTUSDC, ETHUSDC,
      SOLUSDC, XRPUSDC, LINKUSDC. Vorbereitet: `Agenten/Handel/kraken_paare.py` ist
      die EINE Paar-Tabelle (Quoten EUR und USDC); mosaic und moondev_marktlage
      lesen die Quote aus der wachen (`"kraken_quote"`, Vorgabe EUR = altes
      Verhalten), 17 Tests in `Agenten/Handel/tests/test_kraken_paare.py`.
      Gemessen: das Kraken-Konto traegt 0,0097 USDC gegen 45,90 EUR - ein
      USDC-Lauf waere am Guthaben-Tor zu.
      Naechster Schritt (Entscheidung Max): USDC auf dem Kraken-Konto bereitstellen
      (Tausch EUR->USDC oder Einzahlung), dann `"kraken_quote": "USDC"` in
      mosaic/wachen.json und moondev_marktlage/wachen.json setzen. Die kraken-Spur
      braucht keinen Code (watchlist + waehrung), nautilus_kraken nur `paar`.
      Achtung: USDC-Paare bringen auf einem EUR-Konto zusaetzlich EUR/USD-Risiko.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/kraken_paare.py, mosaic,
      moondev_marktlage, kraken, nautilus_kraken.


- [ ] **T-102 — Kraken kauft denselben Wert mehrfach: "Kauf ohne Fuellung" ist eine Fehlmeldung**
      Kontext: Der Tagesbericht 28.09.2026 22:05 fuehrte fuer Kraken vier Positionen,
      davon DOTEUR/ATOMEUR/FILEUR mit "1 EUR"/"2 EUR" statt ~50 EUR. An der Boerse
      nachgemessen: **FILEUR wurde am 28.09. VIER mal gekauft** (15:33 53,48 @0,935 ·
      15:44 53,42 @0,936 · 16:32 55,13 @0,911 · 16:44 55,43 @0,906) = rund 200 EUR
      fuer EIN Signal; das Buch fuehrt 55,43 Einheiten, also einen Kauf.
      Ursache: `Agenten/Handel/beleg_hand.py:99-100` fragt `kraken.gefuellte_menge(txid)`
      SOFORT nach dem Marktkauf ab. Die Boerse fuelte um 16:32 (53,42 Einheiten,
      50,00 EUR), das Journal schrieb 53 s spaeter "beleg_hand: Kauf ohne Fuellung"
      (14:32:53 UTC). Ohne erkannten Fill bucht die Spur keine Position und stellt im
      naechsten Zyklus (alle 15 min) einen neuen Beleg - der naechste Kauf folgt.
      Zweiter Befund: XLMEUR wurde am 28.09. 17:02 fuer 50,02 EUR gekauft und steht
      NICHT im Buch; die Buchpositionen tragen nur `paar`+`menge`, keinen Einstiegspreis,
      Einsatz oder Stop (daher die 1-2-EUR-Anzeige im Bericht).
      Naechster Schritt: (1) nach AddOrder die Fuellung abwarten (Poll auf gefuellte
      Menge/Orderstatus, ~10 s, wie die wartende-Auftraege-Logik in xperp) und erst
      danach "ohne Fuellung" melden; (2) vor dem Stellen eines Belegs pruefen, ob fuer
      dasselbe Instrument schon Beleg, offene Order oder Bestand existiert; (3) die
      Buchpositionen der Kraken-Spur mit preis/einsatz/stop fuellen.
      Nicht dringend: 45,90 EUR frei < 50 EUR Beleg, derzeit ist kein weiterer Kauf moeglich.
      Angelegt: 2026-09-28
      Betrifft: Agenten/Handel/beleg_hand.py, Agenten/Handel/kraken/handeln.py


- [ ] **T-132 — Nautilus-Arme erst nach belastbarer Statistik live**
      Kontext: 27.09.2026 auf Papier gesetzt (handel_erlaubt=false, freigabe.erfuellt=false) - nautilus, nautilus_kraken, nautilus_kraken_futures haben 0 geschlossene Runden, keine belastbare Messung. nautilus_kraken (Spot) war von einer parallelen Sitzung scharf gestellt (T-065, ~1-EUR-Round-Trip), Auftrag Max hat das ueberschrieben.
      Naechster Schritt: erst nach >=8 geschlossenen Runden je Arm und Freigabekette live.
      Angelegt 27.09.2026 · Zuletzt 27.09.2026 · Betrifft Agenten/Handel/nautilus*


- [ ] **T-130 — xperp kill_switch schliesst gewinnende Positionen (zu aggressiver Schutz)**
      Kontext: Auswertung 27.09.2026 - alle 5 kill_switch-Ausgaenge (21.09. BZ/CRCL/HBAR, 25.09. CRCL/MSTR) waren POSITIV (+0,4 bis +2,4 %). Der Kill feuert nicht wegen der aktuellen Position, sondern weil der kumulierte Ruecklauf vom Peak den Deckel erreicht - er schuetzt den realisierten Gewinn, schliesst dabei aber Positionen im Plus. Deckel jetzt 250 USD (21.09. von 40 erhoeht), max. je erreichter Ruecklauf 31 USD -> de facto entschaerft.
      Naechster Schritt: Entscheidung, ob der Kill auf echte Verluste umgestellt oder der Deckel als Gewinnschutz beibehalten wird.
      Angelegt 27.09.2026 · Zuletzt 27.09.2026 · Betrifft Agenten/Handel/xperp




- [ ] **T-131 — Kraken-EUR: 0,71 EUR frei blockieren `kraken` UND `nautilus_kraken` live**
      Kontext: Am 25.09.2026 waren in beiden Spuren die Papier-Positionen ausgebucht
      (siehe T-103 und Wiki/Handel/Lektionen.md) - damit ist das Buch frei, aber das
      Geld ist der naechste Grund: `kraken/verifiziere_guthaben.py` misst ZEUR = 0,7059,
      noetig sind 60,00 EUR (`mindest_guthaben_eur`); `nautilus_kraken` braucht fuer den
      ~1-EUR-Round-Trip 1,00 EUR (`live_einsatz_eur` 1.0, `mindest_guthaben_eur` 2).
      Das Kraken-EUR haengt in mosaics Live-Positionen (SOL + BTC, rund 96 EUR Nominal)
      und wird erst beim Ausstieg wieder frei. Kraken ist ausserdem `handel_erlaubt=false`
      und ordert ueber den Freigabe-Beleg (`order_ueber: mcp`), nautilus_kraken hat
      `handel_erlaubt=true` und den REST-Orderweg gebaut.
      Naechster Schritt: entscheiden - (a) auf mosaics Ausstieg warten (dann wird EUR frei
      und nautilus_kraken kann den 1-EUR-Test fahren), (b) EUR einlegen, oder (c)
      `mindest_guthaben_eur`/`live_einsatz_eur` senken. Nicht getan: nichts davon ohne
      Entscheidung, kein Geld umgeschichtet.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/kraken/wachen.json, nautilus_kraken/wachen.json, Kraken-Konto




- [ ] **T-128 — Marktbreite-Reihe auswerten und entscheiden, ob eine Spur sie als Tor nutzt**
      Kontext: `Agenten/Werkzeuge/breite.py` misst seit 25.09.2026 taeglich den
      Anteil der 30 Top-Paare ueber ihrer EMA200 und schreibt die Reihe
      (`Agenten/Werkzeuge/breite-reihe.jsonl`); Cron `breite-wache` (taeglich
      19:00, no_agent) meldet nur Aenderungen. Die erste Messung war 29 von 29 =
      100 % - aus EINEM Punkt folgt keine Richtung, "die Breite schrumpft" ist
      erst mit einer Reihe belegbar. Offen ist ausserdem, ob eine Handelsspur die
      EMA200-Breite als Tor nutzen soll: bisher rechnet nur
      `moondev_marktlage` eine Breite, und das ist eine ANDERE Groesse (Anteil
      mit positivem 24-h-Vorzeichen, aus CoinGecko).
      Naechster Schritt: in etwa zwei Wochen `python Agenten/Werkzeuge/breite.py
      --reihe` ansehen und entscheiden (a) Reihe behalten oder verwerfen,
      (b) ob eine Spur ein Breiten-Tor bekommt.
      NACHTRAG 25.09.2026: Die Reihe fuehrte zuerst eine Zeile je MESSUNG - sechs
      Laeufe am ersten Tag ergaben sechs Zeilen fuer DENSELBEN Kerzentag, also
      genau den einen Messpunkt, den sie aufloesen soll. Jetzt ersetzt eine
      Messung derselben Kerze ihre Zeile (Tageskerze wechselt 16:00 UTC), und
      `--reihe` rechnet den Verlauf in Punkten je Tag. Fuer die Auswertung
      zaehlen daher KERZENTAGE, nicht Zeilen; der erste echte zweite Punkt kommt
      aus dem Cron am 26.09.2026 um 19:00.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Werkzeuge/breite.py, Agenten/Hermes/scripts/breite-wache.py,
      Agenten/Handel/moondev_marktlage


- [ ] **T-127 — Kein freies Guthaben fuer neue Live-Einstiege (Kraken 0,71 EUR / OKX 0,15 USDC)**
      Kontext: `mosaic` und `swap` nennen ihre Sperre seit 25.09.2026 mit Boerse
      und Waehrung. Der Fakt dahinter: Kraken traegt **0,71 EUR** frei, waehrend
      ~196 EUR in drei offenen Live-Positionen liegen (BTC/ETH/SOL, alle mit
      Boersen-Stop); OKX traegt **0,15 USDC** frei, die uebrigen 757 USDC sind
      die Besicherung laufender XPERP-Positionen (FIL/MON/MSTR/CRCL + die
      manuelle FIL-Position). Kein Dateischalter loest das - es fehlt Geld, keine
      Bedingung.
      Naechster Schritt: Entscheidung von Max - Guthaben aufstocken, eine
      Position schliessen oder die Spuren im Papier lassen. Nichts davon
      automatisch tun.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/mosaic, Agenten/Handel/swap, Kraken- und OKX-Konto


- [ ] **T-126 — swap handelt jetzt den XPERP-Kontrakt; der Geld-Blocker bleibt**
      Kontext: Der Fehler `OKX 50124` (25.09.2026, jede Runde) kam vom falschen
      Markt-Namensraum: swap handelte `XAU-USDT-SWAP` (instType=SWAP), handelbar
      ist auf diesem Konto nur der XPERP-Zwilling (`XAU-USD_UM_XPERP-310502`,
      instType=FUTURES, belegt mit 93 gefuellten Kontrakten am 24.09.).
      Behoben: `kandidaten.handels_kontrakte()` bildet je Basiswert auf den
      Zwilling ab, `handeln.anlauf()` handelt ihn, und die Sperrliste nennt die
      freie Margin (`nur 0.15 USDC frei, noetig 50.00`), damit AUTO_FREIGABE
      kein Fenster fuer einen Lauf oeffnet, der nicht handeln kann.
      NACHGETRAGEN (25.09.2026, gleiche Spur): Der Umbau wirkte nur auf den
      ERSTEN Lauf. `handeln.rangliste()` lagerte die Kennzahlen OHNE den
      Zwilling zwischen - jeder Zyklus innerhalb der zwei Stunden Gueltigkeit
      fiel in `anlauf()` auf den gewoehnlichen Perpetual zurueck. Belegt: die
      gespeicherte Rangliste (05:37 UTC, nach dem Umbau) trug kein
      `handels_instId`, und `--vorschau` zeigte `XAU-USDT-SWAP` statt des
      XPERP-Kontrakts. Behoben: die Zeile traegt `handels_instId`/
      `handels_instr`, ein Stand aus altem Schema wird verworfen statt bis zum
      Ablauf zu gelten, ohne Zwilling entsteht kein Vorschlag mehr, und
      `anlauf()` loest nie auf den Reihennamen auf (frische Zwillingstabelle
      als Rueckfall). Die Vorschau nennt jetzt je Kandidat den GEHANDELTEN
      Kontrakt, und die Sperrzeile steht auch dann da, wenn nichts sperrt.
      Nachweis: 57 Tests gruen (11 neue; Gegenprobe ohne den Fix: 9 rot),
      Vorschau listet `META-USD_UM_XPERP-310613` und `XAU-USD_UM_XPERP-310502`.
      OFFEN: swap kann weiterhin NICHT live handeln - es fehlt die freie
      Margin, gemessen 0.00 USDC frei (siehe T-089). Und die Papierposition im
      Buch traegt noch die alte Kennung `XAU-USDT-SWAP`; neue Positionen laufen
      unter dem XPERP-Namen.
      Naechster Schritt: bei freier Margin zuerst `handeln.py --vorschau` lesen -
      dort muss je Kandidat der XPERP-Zwilling stehen.
      Angelegt: 2026-09-25
      Zuletzt: 2026-09-25
      Betrifft: Agenten/Handel/swap (handeln.py, kandidaten.py, tests/)


- [ ] **T-125 — Fremdarbeit im Arbeitsbaum liegen gelassen (parallele Sitzung)**
      Kontext: Beim Commit am 25.09.2026 lagen Aenderungen im Arbeitsbaum, die nicht
      aus dieser Sitzung stammen: geloescht `Agenten/Hermes/scripts/test_waisen_wache.py`,
      geaendert vier Skill-Dateien (arbeitsbaum-git-hygiene, dauerprozess-bewachen,
      fremdrepo-agent-start, laufwerk-platz-schaffen) sowie
      `handel-spuren/references/boersen-aufrufe.md` und `okx-fehlermeldungen.md`, neu
      `Agenten/Hermes/skills/brainfiles/sicherung-fahren/` und `kraken-cli/` im
      Wurzelordner. Bewusst NICHT mitgenommen (eigene Pfade stagen).
      Naechster Schritt: der naechste Lauf von `fremdarbeit-einziehen.ps1` (taeglich
      20:40) oder eine Sitzung committet sie mit Autor „Andere Sitzung“;
      `kraken-cli/` in der Wurzel gehoert nach Werkstatt/Repos.
      Angelegt: 2026-09-25


- [ ] **T-124 — Eine scharfe Spur, die dauerhaft sperrt, meldet sich nur einmal**
      Kontext: Der Ereignisfilter des Dauerlaufs meldet Sperrzeilen („--live
      angefordert, aber gesperrt: …“) jetzt mit Gedaechtnis je Spur — dieselbe
      Zeile kommt einmal statt in jedem Zyklus. Das ist gewollt (Rauschen), laesst
      aber den Dauerfall offen: eine scharfe Spur, die wochenlang an Guthaben oder
      einem anderen Tor haengt, faellt nur im Tagesbericht auf.
      Naechster Schritt: pruefen, ob `sperrgruende.py` oder `spuren_stand.py` von
      einer Wache taeglich aufgerufen werden soll (Muster stille-spuren-wache).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/dauerlauf.py, Agenten/Hermes/scripts/


- [ ] **T-123 — Zweiter Stufenlauf „hoch“ laeuft doppelt**
      Kontext: Beim Neustart des Basis-Dauerlaufs am 25.09.2026 standen ZWEI
      Prozesspaare mit `--risiko hoch` (60536/37924 und 60424/38452, beide am
      24.09. 18:49 gestartet) neben Basis und Mittel. Stufenlaeufe senden nicht und
      gehen nie live, ein Doppel kostet also nur Rechenzeit und Netz — es ist aber
      dieselbe Klasse wie die vier gleichzeitigen Laeufe vom 16.09.2026, die bei
      offenem Freigabefenster echtes Doppelorder-Risiko trugen. Nicht angefasst
      (Fremdstart einer anderen Sitzung).
      Naechster Schritt: pruefen, welcher Ausloeser den zweiten hoch-Lauf startet
      (Get-ScheduledTask der MaxHirn-Handel-Aufgaben), ein Paar geordnet beenden und
      IgnoreNew setzen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/dauerlauf.hoch.pid, Agenten/Routinen/handel-dauerlauf.ps1


- [ ] **T-106 — dmcsystem: Modellwahl-Diskussion aufnehmen**
      Kontext: Projekt existiert hier nicht. Selbes Muster.
      Naechster Schritt: Projekt aufnehmen → Diskussion fortsetzen.
      Angelegt: 2026-09-25 · Zuletzt: 2026-09-25
      Betrifft: dmcsystem (noch nicht vorhanden)
      Kontext: Der offizielle Santiment-MCP-Connector
      (`https://api.santiment.net/mcp`, Streamable HTTP, acht Werkzeuge) nennt
      seine Werkzeugliste anonym, verlangt fuer jeden `tools/call` aber OAuth 2.0
      mit PKCE (HTTP 401). Der Anmeldeschritt laeuft im Browser gegen ein
      kostenloses Santiment-Konto - nicht automatisierbar.
      **Kein Blocker mehr fuer Daten:** der GraphQL-Weg laeuft seit dem
      16.09.2026 ohne Schluessel (`Agenten/Handel/santiment_daten.py`, Probe
      5/5), mit den kleineren Fenstern der freien Stufe. Der MCP ist der
      breitere Weg auf dieselbe Kontostufe.
      Naechster Schritt (Max): `hermes mcp add santiment --url
      https://api.santiment.net/mcp --auth oauth`, danach
      `hermes mcp login santiment`. Danach im MCP-Manifest aus `disabled` in
      die Serverliste (Feld `agent: hermes`) und `mcp-sync-check.ps1` laufen
      lassen.
      Wartet auf: Max - Browser-Anmeldung bei Santiment
      Betrifft: `Agenten/MCP-Manifest.json` (Eintrag `disabled`),
      [[Buildix-Santiment-Handelswissen]]
      Angelegt: 2026-09-16


- [ ] **T-105 — huruf: Modellwahl-Diskussion aufnehmen**
      Kontext: Projekt existiert hier nicht. Selbes Muster wie T-104 — Diskussion pausiert, bis das Projekt vorliegt. Lokaler Platzhalter in `docs/tasks/offene-aufgaben-splits-huruf-dmc.md`.
      Naechster Schritt: Projekt aufnehmen → Diskussion fortsetzen.
      Angelegt: 2026-09-25 · Zuletzt: 2026-09-25
      Betrifft: huruf (noch nicht vorhanden)


- [ ] **T-104 — splits: Modellwahl-Diskussion aufnehmen**
      Kontext: Projekt existiert hier nicht — Voraussetzung ist, dass splits als Repo/Ordner hier vorliegt. Die Frage nach Splits lautete im Gespräch: „Als task abspeichern um weiter zu machen mit splits, huruf, dmcsystem … aufgabe weitermachen". Die Diskussion reicht bisher bis zur Empfehlung, nicht zu Max' Betrieb zu passen — `docs/tasks/offene-aufgaben-splits-huruf-dmc.md` (lokal) ist der Platzhalter bis maximale Aufnahme.
      Naechster Schritt: Projekt aufnehmen (Klon in Werkstatt/Repos/<name>, Bot-Profil, Doku), dann Modellwahl-Diskussion fortsetzen.
      Angelegt: 2026-09-25 · Zuletzt: 2026-09-25
      Betrifft: splits (noch nicht vorhanden)


- [ ] **T-101 — Regimefilter fuer die Prognose-Spuren pruefen (der Hebel liegt nicht am Parameter)**
      Kontext: Die erste Parametersuche ueber 24 Monate und vier Halbjahres-Fenster
      (2026-09-25) zeigt: KEIN Kandidat gewinnt alle vier Fenster, weil in jeder
      Spur ein Halbjahr fuer JEDEN Parameter negativ ist (supertrend F1/F3,
      squeeze F3). Die Stop-Breite wirkt monoton, aber nur auf die TIEFE des
      schlechten Fensters (Stop 3 % -> -1,13 %, 5 % -> -3,39 %, 7 % -> -5,04 %)
      und auf die Hoehe der guten - sie ist eine Risikoeinstellung, kein Hebel.
      Wenn es einen Hebel gibt, dann die Frage: laesst sich das schlechte Regime
      VORHER erkennen?
      Naechster Schritt: mit demselben Fundament (replay.py + optimieren.py) je
      Spur pruefen, ob ein Marktzustand das negative Fenster ankuendigt -
      Marktbreite (breite.py gibt es schon), Volatilitaet, Trendlage gegen den
      200er. Disziplin wie beim Gitter: Suchfenster -> ungesehenes Prueffenster,
      "kein Filter haelt" ist ein vollwertiges Ergebnis (der Gitter-Befund vom
      15.09.2026: KEIN Seitwaerts-Filter hielt out-of-sample).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/optimieren.py, Agenten/Handel/breite.py, Wiki/Handel/Backtest-Fundament.md


- [ ] **T-100 — Ungeklaerte Loeschung: sechs Testdateien verschwanden aus Agenten/Hermes/scripts/**
      Kontext: Am 25.09.2026 verschwand `test_breite_wache.py` zweimal aus dem
      Arbeitsbaum (`ad081ef` angelegt, `c49111f` nahm die Loeschung mit, `a257c62`
      holte sie zurueck). Am 30.09.2026 nachgezaehlt: es sind SECHS Dateien, nicht
      eine, alle `test_*.py` in `Agenten/Hermes/scripts/` - `test_breite_wache.py`
      (`455e0fe`), `test_waisen_wache.py` (`22e5f7d`), `test_spiegelfrist_wache.py`
      und `test_spur_wache.py` (`3ef372b`), `test_live_wache_stops.py` (`aae26a9`),
      `test_hermes_doctor.py` (`cc70977`). Jede lag danach nur noch als Bytecode in
      `__pycache__`.
      GEMESSEN und ausgeschlossen (30.09.2026): das Werkzeug-Backend ist kein
      Container mit eigener Sicht (Terminal nativ auf dem Host, `C: on /c type
      ntfs`), `write_file` schreibt host-sichtbar (Sonde: 294 B in beiden Sichten,
      `git status` zeigt `??`); kein Haus-Werkzeug loescht dort (`datensortierung.ps1`
      verschiebt nur `.bak` mit Schutzpruefung, `systempruefung.ps1` nur
      Ollama-Reststores, kaputte venvs und eigene Logs ueber 30 Tage,
      `skills-entdoppeln.py` nur Skill-Baeume), nirgends ein `/MIR`-Spiegel; kein
      Defender-Fund auf diesem Pfad; OneDrive nicht betroffen (UserFolder
      `C:\Users\faupe\OneDrive`); die PowerShell-History (1.761 Zeilen) kennt weder
      die Dateinamen noch `git clean`/`checkout`/`stash`.
      Der Taeter ist damit WEITER OFFEN. Der Schadensweg ist belegt:
      `Agenten/Routinen/fremdarbeit-einziehen.ps1` sieht eine fehlende Datei nach 30
      Minuten als 'ruhende Fremdarbeit' und committet die Loeschung - sie ist der
      SCHREIBER des Verlusts, nicht sein Urheber, und nennt als Urheber 'Andere
      Sitzung', was die Suche in die Irre fuehrt.
      Naechster Schritt: nicht mehr suchen, sondern fangen. Seit 30.09.2026 laeuft
      die Wache `Agenten/Hermes/scripts/dateischwund-wache.py` (Hermes-Cron
      `dateischwund-wache`, alle 15 Minuten, no_agent, Telegram, leere Ausgabe = kein
      Befund, 18 Tests in `test_dateischwund_wache.py`). Sie meldet (a) jede Datei,
      die in HEAD steht und im Arbeitsbaum fehlt - der T-100-Fall, sichtbar
      mindestens 30 Minuten BEVOR die Routine ihn festschreibt - und (b) jede Datei,
      die seit dem letzten Lauf verschwunden ist (auch nie committete) sowie eine auf
      0 Byte zusammengefallene. Sie aendert nichts. Meldet sie das naechste Mal: den
      Pfad sofort mit `git checkout HEAD -- <pfad>` zurueckholen und DANN die Uhrzeit
      mit den laufenden Sitzungen abgleichen (`Agenten/Hermes/logs/`,
      `Agenten/Hermes/cache/`), um den Loescher zu fassen.
      Angelegt: 2026-09-25 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Hermes/scripts/, Agenten/Routinen/fremdarbeit-einziehen.ps1

- [ ] **T-099 — Breite-Wache justieren: sind 10 Punkte Rueckgang richtig?**
      Kontext: Die Wache meldet seit 25.09.2026 einen Rueckgang erst ab **10
      Punkten** gegenueber der letzten Meldung - vorher war sie innerhalb der
      Stufe "ok" ganz **blind** (100 % auf 81 % haette keine Nachricht erzeugt).
      10 ist eine SETZUNG, keine Messung: zu klein = Tagesalarm, zu gross = ein
      echtes Schrumpfen bleibt still.
      Naechster Schritt: nach den ersten 2-3 echten Meldungen `breite.py --reihe`
      ansehen und entscheiden, ob 10 bleibt oder auf 5-8 sinkt. Die Zahl steht
      als `RUCKGANGS_PP` in `Agenten/Hermes/scripts/breite-wache.py`.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/scripts/breite-wache.py


- [ ] **T-098 — Breite-Reihe am 02.10.2026 erstmals auswerten**
      Kontext: Die Reihe laeuft seit 25.09.2026 (erste Messung 29 von 29 = 100 %).
      Aus EINEM Messpunkt folgt keine Richtung; erst mehrere Tage zeigen, ob
      100 % ein Plateau war oder der Gipfel. Erste Probe 02.10.2026 (dann sind
      sieben Messungen da).
      Naechster Schritt: `python Agenten/Werkzeuge/breite.py --reihe` laufen lassen
      und in einem Satz festhalten, was die Reihe zeigt (steigt/faellt/seitwaerts)
      - danach T-095 entscheiden.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Werkzeuge/breite-reihe.jsonl


- [ ] **T-097 — Indikatorschwellen der Prognose-Spuren liegen als Konstanten im Code**
      Kontext: Gemessen 2026-09-25 beim Bau des Optimierers. Die vier
      Indikator-Spuren (squeeze, wavetrend, macd_mtf, supertrend) lesen aus
      ihrer `wachen.json` NUR die Ausstiegs-Geometrie
      (`pflicht_stop_prozent_min`, `pflicht_stop_prozent_max`,
      `ziel_r_vielfaches`, `max_offene_positionen`). Ihre eigentlichen
      Indikatorschwellen stehen als Konstanten im Code - `squeeze.signal()` ist
      eine feste Regel ueber `ti.squeeze_momentum(k)`, und `supertrend` holt
      sich `supertrend_n`/`supertrend_faktor` NICHT aus den Wachen (im
      Gegensatz zu trendwende_btc, das beide liest). Das verstoesst gegen die
      Hausregel "Zahlen gehoeren in die wachen.json, nicht in den Code" und
      hat eine harte Folge: diese Parameter lassen sich nicht tunen, ohne Code
      zu aendern - der Optimierer kann sie nicht anfassen.
      Naechster Schritt: je Spur die Konstanten als Schluessel in die
      wachen.json aufnehmen (Wert = der heutige Code-Default, damit sich NICHTS
      verhaelt), die Spur lesend umstellen und mit einem Beleglauf zeigen, dass
      die Ergebnisse vorher/nachher gleich sind. Danach in `spur_opt.json`
      aufnehmen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/{squeeze,wavetrend,macd_mtf,supertrend}/handeln.py und wachen.json, spur_opt.json


- [x] **T-096 — Backtest ueber die volle Historie fuer die uebrigen Spuren**
      Kontext: Fuer 2021-2026 gerechnet und belegt sind bisher vier Spuren
      (squeeze, wavetrend, macd_mtf, supertrend) - je 750 bis 1130 auswertbare
      Runden. Der Kern (`replay.py`) kann Familie A und Familie B; es fehlen die
      per-Spore-Historienquellen fuer die Feed-Spuren (moondev_listingarb,
      -topmovers, -marktlage, -sniper, -signalwelle brauchen 24h-Aenderung und
      Volumen aus Kerzen, moondev_funding braucht Binance-Funding-Historie).
      Nicht nachrechenbar und mit Grund vermerkt: moondev_whale (OKX-OI),
      -liquidation, -sentiment, liq_wand, iv_wand, iv_waelle, robinhood_radar,
      kopier, nautilus-Arme.
      **Erledigt 2026-09-29:** Daten- und Adapterschicht stehen
      (`moondev_historie.py`, `daten/historie/feed/`: 300 Tagesreihen + 41
      Stundenreihen + 6 Funding-Reihen), die vier Laeufe sind gefahren
      (topmovers/marktlage/signalwelle/funding), die Lehren stehen im Wiki
      ([[Backtest-Fundament]]). Verweigerte Spuren nennen ihren Grund in
      `replay.NICHT_NACHRECHENBAR`. Offen geblieben sind T-142 bis T-145.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/replay.py, Agenten/Handel/docs/plans/2026-09-24-backtest-fundament.md


- [ ] **T-095 — `runden_aus_journal` paart je INSTRUMENT, nicht je Position**
      Kontext: Der Backtest ueber 5,7 Jahre deckt es auf. Bei squeeze standen
      1088 geschlossene Runden im Buch, `runden_aus_journal()` wertete aber nur
      759 aus (30 % Verlust); bei macd_mtf 1209 gegen 774, bei wavetrend 1506
      gegen 1128. Ursache: die Funktion legt offene Positionen in einem Dict
      `offen[inst]` ab - zwei gleichzeitige Positionen im selben Instrument
      ueberschreiben einander, die erste Ausstiegszeile paart dann mit dem
      falschen Einstieg oder faellt weg. Die Spuren erlauben mehrere Plaetze und
      besetzen denselben Wert mehrfach, das ist also der Normalfall.
      Auswirkung: Trefferquote und f_max werden auf einer Teilmenge gerechnet,
      und die uebersprungene Teilmenge ist nicht zufaellig (gleichzeitige
      Positionen im selben Instrument sind eher gleichgerichtet).
      Naechster Schritt: Positionskennung ins Journal (Spalte `pos_id` beim
      Einstieg, von der Ausstiegszeile mitgefuehrt) und `runden_aus_journal`
      darauf paaren - mit Rueckfall auf die Instrumentenpaarung fuer alte
      Journale. Betrifft ALLE Auswertungen, nicht nur den Backtest.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/kosten_wendepunkt.py, Agenten/Handel/auswertung_alle.py, spur_buch.py


- [ ] **T-094 — Entscheidung Max: kostenpflichtige Historien (Deribit-Strike-OI, Onchain)**
      Kontext: `iv_wand`, `iv_waelle` (Strike-OI-Historie), `moondev_whale`
      (OKX-OI), `moondev_liquidation`, `robinhood_radar` und `kopier` bleiben ohne
      Backtest, weil ihre Historie frei nicht abrufbar ist (gemessen 2026-09-24,
      OKX-OI antwortet `50030 Illegal time range`).
      Naechster Schritt: entscheiden, ob dafuer Geld in die Hand genommen wird
      (Deribit-Archiv, Onchain-Indexer) oder ob es beim Vermerk "nicht
      nachrechenbar" bleibt. Empfehlung: beim Vermerk bleiben - die frei
      nachrechenbaren Spuren liefern erst einmal genug Runden.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/{iv_wand,iv_waelle,moondev_whale,moondev_liquidation,robinhood_radar}


- [ ] **T-093 — Handelsregeln: Backtest-Runden zaehlen nicht fuer die Freigabe**
      Kontext: Die Backtest-Fundament-Spezifikation setzt das fest (Abschnitt
      "Trennung von Live"), aber `Wissen/Handelsregeln.md` sagt es noch nicht.
      Ohne den Satz koennten die historischen Runden als Freigabe-Runden gelesen
      werden - genau die Vermischung, die Max am 2026-09-24 ausgeschlossen hat.
      Naechster Schritt: Absatz in Bedingung 1 ergaenzen: "Runden aus dem
      Backtest (`Agenten/Handel/daten/backtest/`) zaehlen NICHT fuer die Runden-
      und die netto-positiv-Bedingung; sie sind Messung, keine Live-Erfahrung."
      Angelegt: 2026-09-25
      Betrifft: MaxHirn/Wissen/Handelsregeln.md


- [ ] **T-092 — xperps Tageszweig ist nachrechenbar, aber noch nicht angeschlossen**
      Kontext: `xperp/bot.py` traegt bereits die Naht `tages_kerzen_quelle`, und
      die Tageskerzen liegen als `Agenten/Handel/daten/*.csv` (yfinance, mehrere
      Jahre). Damit ist der Aktien-/Rohstoff-Zweig backtestbar, waehrend der
      Perp-Zweig es nicht ist (siehe T-091).
      Naechster Schritt: eigene Aufgabe nach dem Backtest-Plan - Kerzen aus
      `daten/*.csv` ueber dieselbe Naht, kein neuer Datenweg.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/xperp/bot.py, Agenten/Handel/daten/


- [ ] **T-091 — Vier Kern-Spuren ohne Kerzen-Naht sind nicht backtestbar**
      Kontext: `scanner`, `xperp` (Perp-Zweig), `swap` und `kraken` rufen den
      Kerzenweg DIREKT (kein `kerzen_quelle`) und lesen Kontostand und
      Ranglisten. Der Replay-Kern aus
      `Agenten/Handel/docs/plans/2026-09-24-backtest-fundament.md` kann sie
      deshalb nicht fahren - und genau dort laeuft das echte Geld.
      Naechster Schritt: eigener Design-Zyklus, Datenzugriff kapseln wie in den
      uebrigen 18 Spuren, Live-Pfad vollstaendig draussen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/{scanner,xperp,swap,kraken}/


- [ ] **T-090 — RBI-Schleife laeuft unbeaufsichtigt und wird nicht gewacht**
      Kontext: Seit 25.09.2026 laeuft die Research-Backtest-Implement-Schleife
      des moon-dev-Klons (rbi_agent) echt durch: Idee -> Strategie -> Backtest-
      Code -> Paket -> Final. Sie arbeitet 4482 Ideen ab, schreibt je Idee Dateien
      nach src/data/rbi/<datum>/ und braucht je Idee Minuten auf der CPU. Es gibt
      KEINE Wache dafuer (der Haus-Dauerlauf kennt sie nicht, der MoonDev-Treiber
      startet nur new_or_top und kraken_agent). Ein haengender Lauf faellt niemandem
      auf, ein wiederholter faellt nur an der Platte auf.
      Naechster Schritt: entscheiden, ob die Schleife ueberhaupt dauerhaft laufen
      soll. Wenn ja: no_agent-Cron (15 min) auf Prozesszahl + Alter + freien Commit,
      wie bei moondev-agenten-wache.
      Angelegt: 2026-09-25
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents/src/agents/rbi_agent.py


- [ ] **T-089 — xperp haengt am eigenen KILL-SWITCH, nicht an handel_erlaubt**
      Kontext: Auftrag Max 25.09.2026 ("SPUREN auto freigabe live"). kraken liess sich
      scharf stellen (haengt nur am Guthaben: 0,71 von 60 EUR), xperp NICHT: nach dem
      Setzen von handel_erlaubt=true stand es im naechsten Lauf wieder auf false, weil
      der Kill-Switch erreicht ist - Ruecklauf 137,16 USD gegen den Deckel
      `kill_switch_gesamt_usd` 100 (Hoechststand 497,42 USD), Meldung im Wachen-Bericht
      "KILL-SWITCH erreicht - der naechste Lauf stellt flach". Ein blosses
      handel_erlaubt=true reicht deshalb nicht: der naechste Zyklus wuerde flachstellen
      und die offene Position verkaufen (genau der Fall vom 21.09.2026, damals Deckel
      40 -> 100). Rollierender EV ist positiv (+10,005 USD).
      Naechster Schritt: entscheiden - Deckel erhoehen (mit datiertem Vermerk
      `_kill_switch_erhoeht` in xperp/wachen.json) ODER flachstellen lassen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/xperp/wachen.json


- [ ] **T-088 — Kraken: rund 0,98 SOL frei, die in keinem Buch stehen**
      Kontext: Am 25.09.2026 gemessen: Kraken traegt 1,4620084165 SOL frei,
      mosaics Buch kennt 0,48058439 SOL (Live-Position vom 23.09.). Die Differenz
      (rund 100 EUR) gehoert keiner Spur; die Buecher von `kraken` (Papier) und
      `moondev_marktlage` (XBT/USD) erklaeren sie nicht. Die Kraken-Ledger-Abfrage
      laeuft wegen des Derivate-Verkehrs (rollover/flexconversion, 45 Zeilen in
      4,5 h) nicht bis zum Kauf zurueck.
      Naechster Schritt: bei Max nachfragen, ob das eigener Bestand ist. Wenn
      nicht: `Ledgers` mit `start` vor dem 23.09.2026 und `asset=SOL` eingrenzen.
      Angelegt: 2026-09-25
      Betrifft: Kraken-Konto (Spot), Agenten/Handel/mosaic


- [ ] **T-087 — moondev_listingarb auf OKX: das Spot-Guthaben ist durch die Scanner-Stops gesperrt**
      Kontext: Auf Auftrag Max 25.09.2026 auf OKX/USDC umgestellt (vorher kraken/EUR,
      dort nur 0,71 EUR frei). Der Orderweg bindet jetzt `mosaic/okx_spot`
      (Gegenprobe: `venue_inst('LINK')` = `LINK-USDC`), und die Spur prueft vor dem
      Einstieg, ob es `<SYM>-USDC` auf OKX ueberhaupt gibt - von den drei Signalen
      des Tages (VVV, WBT, XMR) hatte nur VVV ein OKX-Paar, und das nur als -USDT.
      OFFEN ist Geld: gemessen 25.09. 08:1x ist das USDC des OKX-Kontos
      `eq 730,42` / `frozenBal 730,42` / `availEq = availBal = cashBal 0,0021` -
      die 730 USDC sind vollstaendig durch die Stop-Orders der fuenf offenen
      scanner-Positionen reserviert. Das Guthaben-Tor der Spur (mindest_guthaben 50)
      haelt sie deshalb zu, und weil der Grund nicht ALLEIN das Freigabefenster ist,
      oeffnet der Dauerlauf auch kein Fenster von selbst (gewollt).
      Frueher am Morgen standen dort noch 227,39 verfuegbar - die Sperre schwankt
      mit den Scanner-Positionen.
      Naechster Schritt: entscheiden - (a) auf einen Scanner-Ausstieg warten (dann
      wird USDC frei und die Spur handelt von allein), (b) USDC im OKX-Portal in die
      Spot-Brieftasche legen, oder (c) `mindest_guthaben` senken (dann handelt sie
      mit Kleinstbetraegen). Nicht getan: nichts davon ohne Entscheidung.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/moondev_listingarb/wachen.json, OKX-Konto, scanner/


- [ ] **T-086 — moon-dev-ai-agents: RBI-Schleife laeuft, aber die Kursdatei ist die des Autors**
      Kontext: Die vier RBI-Laeufer des GUI starten seit 25.09.2026 (UTF-8 +
      Wurzel-.env im Kind, conda durch den venv-Interpreter ersetzt, Prompt-
      Datenpfad lokalisiert). OFFEN: die Kursdatei src/data/rbi/BTC-USD-15m.csv
      ist der Datensatz des Autors (31.046 Kerzen 15m, Ende 2023) - fuer eine
      Aussage ueber HEUTE muesste sie durch eine frische Reihe (OKX/Binance,
      eigener Abruf) ersetzt werden. Ausserdem: kein Walk-Forward, keine
      Kostenmodellierung ausser der Strategie-eigenen Gebuehr.
      Naechster Schritt: entscheiden, ob die Schleife ueberhaupt weiterlaufen
      soll - die gemessenen Ergebnisse (95-97 % Verlust) sprechen dagegen, dass
      sie ohne Walk-Forward je etwas Tragfaehiges liefert.
      Angelegt: 2026-09-25
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents (geaenderter Klon: moongui.py,
      src/agents/rbi_agent*.py, backtest_runner.py, 19 *_BT.py)


- [ ] **T-085 — Repos-Zentrale: fuer die meisten Repos fehlen Anleitung und Befehle**
      Kontext: Das Fenster zeigt seit 25.09.2026 zu jedem Projekt einen Bereich
      "Was dieses Projekt kann" (Ablauf in Worten + anklickbare Befehle). Hinterlegt
      ist das fuer intelligent-trading-bot, moon-dev-ai-agents, openmontage,
      kraken-cli und fomo-robinhood-radar (Befehle) sowie Kronos, laya und
      robinhood-fomo-kronos-arena (nur Anleitung). Die uebrigen rund 27 Eintraege
      zeigen nur die allgemeinen Handgriffe (Terminal, Ordner, Doku, Bot).
      Es fehlt WISSEN ueber das Repo, nicht Code: ein Befehl darf erst ins
      Manifest, wenn er einmal wirklich gelaufen ist (Hausregel).
      Naechster Schritt: bei Bedarf ein Repo nach dem anderen - einmal den Weg
      gehen, dann "anleitung" und "befehle" in repos-zentrale.json ergaenzen
      (Rezept in Agenten/Werkzeuge/repos-zentrale/README.md).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json


- [ ] **T-083 — Bonsai 2 27B: Vision nicht angeschlossen**
      Kontext: Das Modell kann Bilder lesen; die Vision-Komponente (mmproj Q8_0,
      0,63 GB) ist absichtlich nicht geladen worden, weil der VRAM bei 8k Kontext
      schon randvoll ist (322 MiB frei). `BONSAI_MMPROJ_CPU=1` bzw.
      `--no-mmproj-offload` wuerde den Projektor in den RAM legen - ungemessen.
      Naechster Schritt: mmproj laden, mit `--no-mmproj-offload` starten, ein Bild
      (Screenshot) durchschicken und Geschwindigkeit notieren.
      Angelegt: 2026-09-25
      Betrifft: Modelle/GGUF/Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf (fehlt noch)


- [ ] **T-082 — Bonsai 2 27B: PQ2_0-Packung ist ungemessen**
      Kontext: Auf dem Rechner liegen 5,95 GB als PTQ1_0; erzeugt 32 t/s bei 8k
      Kontext (gemessen 25.09.2026). Die PrismML-Karte nennt fuer Ampere-Karten
      (diese 3060 Ti ist Ampere) PQ2_0 beim Dekodieren SCHNELLER als PTQ1_0 -
      die Packung ist aber 7,21 GB gross und passt nicht mehr vollstaendig in den
      VRAM, braucht also Teilauslagerung. Ob das unter dem Strich schneller ist,
      ist nicht gemessen.
      Naechster Schritt: PQ2_0 herunterladen (7,21 GB), mit `-ngl 99` und mit
      abgestufter Auslagerung (`-ngl 60/70`) messen, Zahlen in
      Wiki/Werkzeuge/Bonsai-2-27B.md stellen.
      Angelegt: 2026-09-25
      Betrifft: Modelle/GGUF/, Agenten/Werkzeuge/bonsai-27b.ps1


- [ ] **T-081 — Fremdarbeit im Arbeitsbaum liegen gelassen (parallele Sitzung)**
      Kontext: Beim Commit am 25.09.2026 lagen Aenderungen im Arbeitsbaum, die nicht
      aus dieser Sitzung stammen: geloescht `Agenten/Hermes/scripts/test_waisen_wache.py`,
      geaendert vier Skill-Dateien (arbeitsbaum-git-hygiene, dauerprozess-bewachen,
      fremdrepo-agent-start, laufwerk-platz-schaffen) sowie
      `handel-spuren/references/boersen-aufrufe.md` und `okx-fehlermeldungen.md`, neu
      `Agenten/Hermes/skills/brainfiles/sicherung-fahren/` und `kraken-cli/` im
      Wurzelordner. Bewusst NICHT mitgenommen (eigene Pfade stagen).
      Naechster Schritt: der naechste Lauf von `fremdarbeit-einziehen.ps1` (taeglich
      20:40) oder eine Sitzung committet sie mit Autor „Andere Sitzung“;
      `kraken-cli/` in der Wurzel gehoert nach Werkstatt/Repos.
      Stand 25.09.2026 03:20 weiterhin im Baum (nicht angefasst, eigene Pfade
      gestaged): `Agenten/Handel/swap/handeln.py`, `swap/kandidaten.py`, drei
      swap-Tests, `Agenten/Hermes/skills/brainfiles/arbeitsbaum-git-hygiene/SKILL.md`,
      `kraken-cli/`. Der eigene Commit 1fcea14 (Kraken-Abweisungs-Sonde) hat nur
      die acht eigenen Pfade mitgenommen.
      Angelegt: 2026-09-25


- [ ] **T-080 — Eine scharfe Spur, die dauerhaft sperrt, meldet sich nur einmal**
      Kontext: Der Ereignisfilter des Dauerlaufs meldet Sperrzeilen („--live
      angefordert, aber gesperrt: …“) jetzt mit Gedaechtnis je Spur — dieselbe
      Zeile kommt einmal statt in jedem Zyklus. Das ist gewollt (Rauschen), laesst
      aber den Dauerfall offen: eine scharfe Spur, die wochenlang an Guthaben oder
      einem anderen Tor haengt, faellt nur im Tagesbericht auf.
      Naechster Schritt: pruefen, ob `sperrgruende.py` oder `spuren_stand.py` von
      einer Wache taeglich aufgerufen werden soll (Muster stille-spuren-wache).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/dauerlauf.py, Agenten/Hermes/scripts/


- [ ] **T-079 — swap: der erste echte Live-Einstieg steht noch aus**
      Kontext: swap hat seit dem 25.09.2026 einen tragfaehigen Zweig-Trenner (`modus`
      an jeder Position, Ausstiege und Tore nur im eigenen Zweig, Bereinigung nur
      fuer Altbestand ohne Feld). Im Journal stehen bis 24.09. AUSSCHLIESSLICH
      Papierzeilen; der Live-Zweig hat noch nie geordert, obwohl sein Freigabefenster
      seit dem 24.09. 23:55 offen ist. Belegt ist damit nur, dass eine Papierposition
      jetzt stehen bleibt (kein `buchbereinigung` mehr im Kreis).
      Naechster Schritt: beim ersten Live-Kauf pruefen, dass die Zeile `modus=live`
      traegt und der naechste Papierzweig sie NICHT verkauft.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/swap/


- [ ] **T-078 — Zweiter Stufenlauf „hoch“ laeuft doppelt**
      Kontext: Beim Neustart des Basis-Dauerlaufs am 25.09.2026 standen ZWEI
      Prozesspaare mit `--risiko hoch` (60536/37924 und 60424/38452, beide am
      24.09. 18:49 gestartet) neben Basis und Mittel. Stufenlaeufe senden nicht und
      gehen nie live, ein Doppel kostet also nur Rechenzeit und Netz — es ist aber
      dieselbe Klasse wie die vier gleichzeitigen Laeufe vom 16.09.2026, die bei
      offenem Freigabefenster echtes Doppelorder-Risiko trugen. Nicht angefasst
      (Fremdstart einer anderen Sitzung).
      Naechster Schritt: pruefen, welcher Ausloeser den zweiten hoch-Lauf startet
      (Get-ScheduledTask der MaxHirn-Handel-Aufgaben), ein Paar geordnet beenden und
      IgnoreNew setzen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/dauerlauf.hoch.pid, Agenten/Routinen/handel-dauerlauf.ps1


- [ ] **T-077 — swap: der erste echte Live-Einstieg steht noch aus**
      Kontext: swap hat seit dem 25.09.2026 einen tragfaehigen Zweig-Trenner (`modus`
      an jeder Position, Ausstiege und Tore nur im eigenen Zweig, Bereinigung nur
      fuer Altbestand ohne Feld). Im Journal stehen bis 24.09. AUSSCHLIESSLICH
      Papierzeilen; der Live-Zweig hat noch nie geordert, obwohl sein Freigabefenster
      seit dem 24.09. 23:55 offen ist. Belegt ist damit nur, dass eine Papierposition
      jetzt stehen bleibt (kein `buchbereinigung` mehr im Kreis).
      Naechster Schritt: beim ersten Live-Kauf pruefen, dass die Zeile `modus=live`
      traegt und der naechste Papierzweig sie NICHT verkauft.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/swap/


- [ ] **T-076 — Der OKX-Bot-Waechter kennt die GESCHLOSSENEN Grids nicht**
      Kontext: `waechter.py`/`analyse.py` lesen nur laufende Bots
      (`dca/ongoing-list`, `grid/orders-algo-pending`). Die 62 geschlossenen Grids
      (`grid/orders-algo-history`, 08.08.-24.09.2026) sind damit unsichtbar -
      genau die Bots, deren Ergebnis man auswerten will. Die Auswertung vom
      25.09.2026 (Netzgewinn +305,64 gegen Richtungsgewinn -392,99 = -77,01 auf
      7.072,87 USDC Einsatz) entstand aus einer Wegwerfsonde in
      `Agenten/Hermes/cache/scratch/okx_grid_kursweg.py`.
      Naechster Schritt: die Sonde als `grid_historie.py` in `okx_bot_waechter`
      uebernehmen (je Grid: Seite, Laufzeit, Netzgewinn, Richtungsgewinn, Stop
      vorhanden ja/nein, Marktbewegung waehrend der Lebensdauer) und in den
      Bericht aufnehmen; rein lesend, wie der uebrige Bericht.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/okx_bot_waechter/, MaxHirn/Wiki/Werkzeuge/okx-bot-waechter.md


- [ ] **T-075 — kraken_rest.guthaben() scheitert sporadisch mit EGeneral:Permission denied**
      Kontext: `kraken_rest.py` laedt `../kraken/kraken.py` ueber
      spec_from_file_location. Derselbe Aufruf `guthaben("ZEUR")` liefert in EINEM
      Prozess ueber den normalen Import 0,7059 und ueber den spec-Weg
      'EGeneral:Permission denied'; in einer Serie von 12 Aufrufen fielen alle 12
      (beide Wege), Minuten spaeter gingen wieder alle. Nicht die Ursache: Key
      (unveraendert), Uhr (1,3 s), nonce_pool (beide Wege laden dieselbe Datei
      `kraken/.kraken_nonce`), venv, cwd, oeffentliche IP (Terminal und Host
      identisch).
      Naechster Schritt: den von kraken.py benutzten nonce bzw. die Antwort im
      Fehlerfall mitschreiben (Header/Statuscode) und gegen den erfolgreichen Fall
      stellen - dies ist der einzige verbleibende Unterschied.
      Werkzeug vorhanden (25.09.2026): `Agenten/Handel/kraken_abweisungs_sonde.py`
      haelt genau das fest (Status, content-type, Header, Rohkoerper) und laeuft als
      Cron `kraken-abweisung-wache` alle 30 min; sie deckt den signierten Spot-Weg
      ueber die Haus-kraken.py ab. Beim naechsten Auftreten zuerst dort nachsehen
      (cache/kraken-abweisungen.jsonl), statt eine neue Sonde zu bauen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/nautilus_kraken/kraken_rest.py,
      Agenten/Handel/kraken/kraken.py


- [ ] **T-074 — nautilus_kraken (Spot) hat noch nicht gekauft - drei gemessene Tore**
      Kontext: Der Arm ist scharf (handel_erlaubt=true, freigabe.erfuellt=true,
      live_einsatz_eur 1.0), kauft aber nur bei einem FRISCHEN Kauf der kopier-Spur.
      Gemessen am 25.09. 01:15: (1) Kraken-Spot-EUR frei = 0,7059 - unter
      `mindest_guthaben_eur` 2 (das Guthaben sitzt im FUTURES-Konto, T-073);
      (2) Freigabefenster zu: der Dauerlauf hat 22:40:42 eine Anfrage gestellt, sie
      lief 23:10:42 ab, ohne dass jemand `/ja` gegeben hat - nautilus_kraken steht
      NICHT in AUTO_FREIGABE; (3) kein neues kopier-Signal seit 24.09. 15:36.
      Zusaetzlich: `handeln.py --vorschau` meldet 'Guthaben nicht abrufbar (Kraken
      meldet: EGeneral:Permission denied)', waehrend derselbe Key ueber
      `kraken/kraken.py` und ueber mosaics Vorschau 0,7059 liefert - der Leseweg
      NUR von `kraken_rest.py` scheitert (T-075).
      Naechster Schritt: entscheiden, ob die 1-EUR-Endabnahme (T-065) auf das
      Spot-Konto soll - dann muessten Geld vom Futures- ins Spot-Konto und das
      Freigabefenster gestellt werden; sonst bleibt der Arm Papier.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/nautilus_kraken/wachen.json, freigabe_fenster.json


- [ ] **T-072 — repos-zentrale: Manifest nennt Bots, deren Profil geloescht ist**
      Kontext: `tests/test_manifest.EchtesManifestTest.test_jedes_bot_profil_des_manifests_existiert`
      ist rot (1 von 56 Tests): 17 Bot-Namen im Manifest haben kein Profil mehr -
      sie liegen seit 19.09.2026 unter `Agenten/Hermes/profiles/.deleted/`
      (projectatlas, skills, superpowers, tradingview-mcp, agent-reach, nous, codex,
      scrapling, santiment, claude-plugins-official, coder, easycliproxyapi,
      graphify, max, moon-dev-code, odysseus, winget-cli). Der Test ist richtig -
      das Manifest ist veraltet; unklar ist, ob die Profile zurueckkommen sollen.
      Naechster Schritt: entscheiden - Profile zurueckholen ODER die bot-Felder im
      Manifest entfernen bzw. kennzeichnen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json,
      Agenten/Hermes/profiles/.deleted/

- [x] **T-069 — moon-dev-ai-agents: die freien Datenquellen in den Fork pushen**
      Erledigt: 2026-09-24. `1b3c650` (api_frei.py + die drei umgestellten
      Agenten) liegt auf origin/main des Forks mfaupel95/moon-dev-ai-agents -
      geprueft mit `git branch -r --contains 1b3c650` (origin/main). Der Klon
      ist NICHT shallow, ein Push braucht kein `fetch --unshallow`.
      Kontext: `src/agents/api_frei.py` und die umgestellten Importe der drei
      Agenten (whale/funding/liquidation) liegen als Commit 1b3c650 NUR LOKAL im
      Klon Werkstatt/Repos/moon-dev-ai-agents. Der Fork mfaupel95/moon-dev-ai-agents
      hat den Stand nicht - ein Plattenausfall kostet die Arbeit. Ein Push in ein
      Fremd-Repo wird nicht ungefragt gemacht; der Klon traegt ausserdem fremde
      uncommittete Arbeit (T-062), die nicht mitgehen darf.
      Naechster Schritt: entscheiden, ob der Stand in den Fork gepusht wird -
      dann `git fetch --unshallow` pruefen, nur die vier eigenen Dateien stagen
      (api_frei.py + die drei Agenten) und pushen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents (Branch main, Commit 1b3c650)


- [ ] **T-071 — Bot-Profil fuer intelligent-trading-bot fehlt**
      Kontext: Der Klon ist seit 25.09.2026 im Startfenster angebunden (Eintrag in
      `Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json`, Startbefehl
      `itb_pruefstand.py`, Verknuepfung `Werkstatt/Repos/intelligent-trading-bot`).
      Als einziges Flotten-Repo hat er KEIN Hermes-Profil - `/bot` kennt ihn nicht.
      Anlegen kostet Arbeit: Profil erzeugen (ohne --clone), providers-/model-Block
      (nous/deepseek-v4-flash-0731), terminal.cwd auf den Klon, die drei
      Router-Schluesselnamen in die eigene .env, und die auth.json als Verknuepfung
      auf `Agenten/Hermes/auth.json` (braucht einen UAC-Klick).
      Naechster Schritt: entscheiden, ob ueberhaupt ein Bot gebraucht wird - eine
      Spur entsteht hier nicht (der Klon ist nur Pruefstand, Wiki Lektion 13).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/profiles/, Agenten/Werkzeuge/repos-zentrale


- [ ] **T-070 — echte Zugangsdaten in `Werkstatt/Repos/fomo-robinhood-radar/.env.example`**
      Kontext: Beim Sichern der Fremdarbeit am 24.09.2026 gefunden - in einer
      VERSIONIERTEN Vorlagendatei stehen zwei echte Kennungen im Klartext
      (ANTHROPIC_API_KEY und TELEGRAM_BOT_TOKEN, Werte hier absichtlich nicht
      wiederholt). Die Aenderung liegt nur im Arbeitsbaum (Status " M"), der
      Kopf des Klons ist unveraendert auf origin/main - es ist also noch NICHTS
      gepusht und nichts geleakt.
      RISIKO: Die Datei wird von jedem `git add -A` in diesem Klon erfasst; ein
      Push in den Fork mfaupel95/fomo-robinhood-radar legt beide Kennungen
      offen. Deshalb wurde sie beim Sichern bewusst NICHT committet.
      Naechster Schritt (Entscheidung Max): beide Werte in der Datei wieder auf
      Platzhalter setzen und die zwei Kennungen als kompromittiert behandeln -
      Anthropic-Key neu ausstellen, Telegram-Bot-Token bei BotFather neu holen.
      Vorher pruefen, in welcher .env die echten Werte noch stehen (die Datei
      selbst ist Stufe 0 und wird nicht geblaettert).
      STAND 26.09.2026: Die zwei Dateien sind bereinigt (jede auf ihren
      HEAD-Stand zurueckgesetzt, in dem die Werte LEER sind), die
      Arbeitsbaeume sind sauber. Beide waren nur im Arbeitsbaum veraendert -
      HEAD und Fork/Upstream trugen leere Werte, es ist also NICHTS geleakt.
      Der Fund war doppelt: neben fomo-robinhood-radar/.env.example trug auch
      Werkstatt/skillspector/.env.example einen echten OPENAI_API_KEY (Klon von
      nvidia/skillspector, Remote zeigt auf NVIDIA - ein Push dorthin waere gar
      nicht moeglich gewesen).
      Geprueft und unauffaellig: 41 .env-Dateien in Wurzel und Werkstatt/Repos -
      die zwei .env mit echten Werten (Agenten/Hermes/.env,
      moon-dev-ai-agents/.env) sind per .gitignore gesperrt und nie versioniert
      worden; die .env.template-Artefakte in mehreren Klonen sind die Vorlage
      von ToolUniverse ("fill in your actual API keys"), kein Wert.
      OFFEN (nur Max): die drei Kennungen (Anthropic, Telegram-Bot, OpenAI) als
      kompromittiert behandeln und neu ausstellen. Kein Leak nach aussen, aber
      die Werte lagen in Klon-Arbeitsbaeumen, die von Sicherungen und
      Sitzungsablagen nicht erfasst werden - Rotation ist die saubere Antwort.
      Werkzeug: Agenten/Hermes/cache/scratch/keys_bereinigen.py (liest und
      meldet nur Laengen/Hashes, gibt nie Werte aus).
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-26
      Betrifft: Werkstatt/Repos/fomo-robinhood-radar/.env.example,
      Werkstatt/skillspector/.env.example


- [ ] **T-067 — Kraken-Futures-Orderweg LIVE bewiesen, Spur auf PF_SOLUSD umgestellt (armt noch nicht)**
      Kontext: `nautilus_kraken/kraken_futures.py` spricht die Futures-REST an
      (eigener Dienst, eigene Signatur, Kopf APIKey/Nonce/Authent, Schluessel
      KRAKEN_FUTURE_API_KEY/SECRET). Der Live-Zweig ruft weiter `kraken_rest`;
      KRAKEN_PRODUKT=futures laedt dort das Futures-Modul.
      KORREKTUR 25.09.2026 (die frueher hier behauptete Regel war FALSCH):
      1 Kontrakt ist NICHT 1 USD Nennwert, sondern EINE Einheit der Basiswaehrung,
      und der Einschuss fuer ein EEA-Konto ist 10 % (`marginSchedules.europa`).
      Gemessen: 1 Kontrakt PF_NEARUSD bei 4,5517 USD belegte 0,4548 USD Marge
      (= 10 % von 4,5517). Damit gilt: PF_XBTUSD 1 Kontrakt = 1 BTC = rund
      84.500 USD, Einschuss rund 8.450 USD - mit 141,59 USD frei um den Faktor 60
      zu gross (Boerse: insufficientAvailableFunds, auch fuer size 1).
      PF_ETHUSD braucht ~269 USD, PF_SOLUSD ~11,75 USD, PF_NEARUSD ~0,46 USD.
      `kontrakte()` ist entsprechend korrigiert, `einschuss()` und `handelbar()`
      sind neu; Tests nautilus_kraken 30 gruen.
      Beleg 25.09.2026, ECHTER Round-Trip (futures_probe.py --anwenden): Kauf
      1 Kontrakt PF_NEARUSD @ 4,5517 (01:46:15, Fuellung gelesen), Verkauf
      reduceOnly @ 4,5508, Position danach geschlossen (Positionen [], Orders []).
      Kosten der Runde: 0,0029 USD auf 4,55 USD Nennwert, davon 0,0009 USD
      Kursunterschied (Spread) -> Gebuehr je Seite im Bereich 0,04-0,05 %.
      /fills und /accountlogcsv sind mit diesem Schluessel nicht lesbar (401) -
      die Equity vor/nach der Ausfuehrung war der Messpunkt.
      STAND 24.09.2026 abends: die Freigabekette ist fertig eingerichtet -
      herzschlag_max_minuten zurueck auf 180 (Hausregel 19.09.2026, T-004:
      eine 45er-Grenze stellt nach einem Rechner-Ausfall echte Positionen ohne
      Handelsentscheidung flach und war zugleich der einzige Wert, den
      systempruefung.ps1 Block 11b als Fehler meldet), Guthaben-Tor fuer Spot
      in sperren_zeile() (Muster kraken/mosaic), live_einsatz_eur 1.00 mit
      live_max_risiko_gesamt_eur 20 statt der Papier-Grenzen 50/200, Schutz-Stop
      direkt nach dem echten Kauf, Journalzeile bei gescheitertem Live-Auftrag
      und ein Waechter je Position: der Live-Lauf ordert Papier-Positionen des
      gemeinsamen Buchs NICHT (4 Papier-Positionen liegen dort, sie haetten beim
      ersten echten Zyklus einen Verkauf von BTC ausgeloest, das es an der
      Boerse nicht gibt - der Fehler von scanner/xperp am 21./23.09.).
      Probe: `handeln.py --vorschau` nennt genau EINEN Sperrgrund
      ("Freigabefenster zu") - damit stellt der Dauerlauf die Anfrage und die
      Auto-Freigabe greift nicht (sie verlangt genau einen Fenster-Grund UND
      das Wort Freigabefenster). Der Round-Trip selbst wartet auf das /ja von
      Max im Dauerlauf; freies Guthaben 4,10 EUR liegt ueber dem Einsatz 1,00.
      Tests: nautilus_kraken 38 gruen inkl. test_live_orderweg.py (5).
      ERLEDIGT 25.09.2026 (Auftrag Max: 'SOL'): Symbol und Paar der Spur stehen
      auf PF_SOLUSD, dazu live_einsatz_usd 118.00 (= EIN Kontrakt SOL, rund
      117,5 USD Nennwert) und live_max_risiko_gesamt_usd 25.00. Das BUCH wurde
      dabei sauber gezogen: die vier offenen Papier-Positionen (alle PF_XBTUSD,
      Einstiege 81.110-81.475) sind zum Kurs 84.263 mit grund=symbolwechsel
      geschlossen (Einsatz 200,00 -> Erloes 206,80 USD, +6,80), weil die
      Strategie JEDE Position mit dem Kurs des EINEN konfigurierten Symbols
      bewertet - ein offenes BTC-Buch waere beim ersten SOL-Kurs als 'stop'
      ausgestiegen. Spiegelung nach Q: bestaetigt, Buch jetzt leer.
      Die Sperrenkette nennt jetzt den ECHTEN Bedarf: `handelbar()` sagt
      '1 Kontrakt PF_SOLUSD braucht 11.75 USD Einschuss, frei sind ...', und
      ein Einsatz UNTER einem Kontrakt wird gesperrt ('Mindestgroesse der
      Boerse') statt still aufgerundet - das war der eigentliche Fallstrick:
      bei live_einsatz_eur 1.00 haette die Boerse 1 Kontrakt = 118 USD
      gefuellt. Tests nautilus_kraken 73 gruen (test_futures_grenzen 5 neu).
      ARMIERT 25.09.2026 (eine parallele Sitzung, Auftrag Max 'Strategie hoch
      fahren!'): handel_erlaubt und freigabe.erfuellt stehen true, das Fenster
      oeffnet die Auto-Freigabe selbst (Spur steht in dauerlauf.AUTO_FREIGABE).
      Stand 26.09. 02:42 lokal: Modus live seit rund 23:00 UTC, 74 live-Zeilen,
      NOCH KEIN Einstieg (0 Positionen) - es fehlt ein frischer Kopier-Kauf als
      Signal. BINDEND: der Futures-Schluessel wird abgewiesen, solange ein VPN
      laeuft (NordLynx -> authenticationError); ohne Tunnel sind 141,59 USD frei.
      Kleiner Nachtrag von mir: der Vermerk _herzschlag_regel behauptete noch
      'auf 45, sobald handel_erlaubt true wird' - richtig ist 180 (Hausregel
      19.09.2026, gilt fuer Papier UND Live); der Wert stand schon auf 180.
      OFFEN: der erste echte SOL-Kauf (1 Kontrakt, rund 122 USD Nennwert,
      Schutz-Stop 19,8 % darunter) - der Dauerlauf meldet ihn ueber den Bus.
      Vor dem Arming ist zu entscheiden, ob eine Mindestposition von 118 USD
      (Risiko am 19,8-%-Stop rund 23 USD) gewollt ist. Kleiner geht auf Kraken
      Futures nicht: die Boerse kennt keine Kontraktbruchteile.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-25
      Betrifft: Agenten/Handel/nautilus_kraken/kraken_futures.py, futures_probe.py,
      test_kraken_futures.py, wachen.futures.json (Symbol, offen)


- [x] **T-068 — nautilus_kraken (Spot) ist scharf gestellt: zwei Tests laufen deshalb rot**
      Kontext: `nautilus_kraken/wachen.json` traegt seit 24.09.2026
      handel_erlaubt=true und freigabe.erfuellt=true (Vermerk T-065, ~1-EUR-
      Round-Trip als Endabnahme des REST-Orderwegs; fremde Sitzung). Zwei
      Tests in `test_handeln.py` frieren den alten Zustand ein (sie erwarten
      "handel_erlaubt=false" im Vorschau-Text) und schlagen fehl, obwohl der
      Code stimmt. Freies Guthaben real: rund 4,10 EUR; die Futures-Seite
      hat 0,00 USD.
      Erledigt: 2026-09-24 (Auftrag Max "nautilus_kraken Freigabe einrichten").
      Die beiden Tests pruefen jetzt die REGEL statt den Zustand: sie lesen
      handel_erlaubt/freigabe.erfuellt aus der wachen.json und verlangen genau
      die Gruende, die dort stehen - kein erfundener Grund, kein fehlender.
      Ein dritter Test sichert die Lehre: eine Suite darf `--live` NIE fahren
      (bei offenem Freigabefenster wuerde der Testlauf echte Orders ausloesen).
      Beleg: nautilus_kraken 38 Tests gruen (test_handeln 12,
      test_sperrenkette 7, test_live_orderweg 5, test_trailing_stop 14).
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Handel/nautilus_kraken/test_handeln.py


- [ ] **T-066 — nautilus_kraken_futures: Futures-Gebuehr 0,05% verifizieren**
      Kontext: Die Futures-Variante (PF_XBTUSD, USD, Hebel) laeuft Papier. Die
      Gebuehr 0,05% ist eine Annahme, nicht gemessen. Vor dem Scharfschalten
      der Futures-Spur an einer echten Fuellung pruefen.
      Naechster Schritt: Futures-Gebuehr an einer echten (oder Demo-)Order
      messen, in wachen.futures.json eintragen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Handel/nautilus_kraken/wachen.futures.json

      BELEG 25.09.2026 (echte Fuellung, 1 Kontrakt PF_NEARUSD): Kosten der Runde
      0,0029 USD auf 4,55 USD Nennwert, davon 0,0009 USD Spread -> Gebuehr je
      Seite 0,04-0,05 % des Nennwerts. Die Annahme 0,05 % ist damit NICHT
      widerlegt, aber wegen der groben Aufloesung (0,0001 USD) auch nicht eng
      bestaetigt. Fuer eine belastbare Zahl eine groessere Fuellung fahren
      (PF_ETHUSD, ~2.688 USD Nennwert, Einschuss ~269 USD - braucht Guthaben
      und eine Entscheidung von Max). Messweg: Equity vor/nach der Ausfuehrung,
      weil /fills und /accountlogcsv mit diesem Schluessel 401 liefern.


- [ ] **T-065 — nautilus_kraken: echter ~1-EUR-Spot-Live-Test (Freigabekette)**
      Kontext: Der REST-Orderweg (kraken_rest.py) ist committed (de433da) und
      per Preflight verifiziert (Keys, Guthaben, markt_kauf echt=False). Der
      echte Orderweg (markt_kauf/markt_verkauf mit echt=True) wird nur aktiv,
      wenn die Spur ueber die Freigabekette scharf ist (handel_erlaubt=true +
      freigabe.erfuellt=true + offenes Freigabefenster). Ein winziger
      ~1-EUR-Round-Trip verifiziert den echten Spot-Pfad.
      Naechster Schritt: Freigabekette oeffnen (nur Max), dann einen
      ~1-EUR-Round-Trip ausfuehren und die Fuellung pruefen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Handel/nautilus_kraken


- [ ] **T-064 — Nautilus-Kraken-Orderweg: WebSocket-Token verweigert, REST traegt
      Kontext: `nautilus_kraken` und `nautilus_kraken_futures` laufen Papier
      (`handel_erlaubt=false`, `freigabe.erfuellt=false`). Der gemeldete Fehler "OKX
      51001" war ERZEUGT und steht in keiner Datei (Suche ueber den Handelsbaum: nur
      xperp und Skill-Doku). Der echte Blocker ist der Exec-Client des
      Nautilus-Kraken-Adapters: `Failed to get WebSocket token: API error:
      EGeneral:Permission denied` (gemessen 24.09. 18:49 UTC,
      `nautilus_kraken/logs/kraken-orders-20260924T184919894096Z.jsonl` ->
      `success: false, entered: false`). Ueber REST arbeitet derselbe Kraken-Schluessel
      einwandfrei (Kontostand und 14 offene Orders lesbar). Eine parallele Sitzung baut
      `nautilus_kraken/kraken_rest.py` + Live-Zweig in `handeln.py` (24.09. 20:33,
      Commit de433da) - Kraken direkt per REST am Nautilus-Adapter vorbei. Der
      REST-Weg ist verifiziert (Keys, Guthaben, markt_kauf echt=False Preflight
      ok, 28/28 Tests + 4/4 Sperrenkette). Offen: echter ~1-EUR-Round-Trip
      (T-065) und Futures-Gebuehr (T-066).
      ENTSCHEIDUNG Max 24.09.2026: REST bleibt. Der Nautilus-Exec-Client wird aufgegeben,
      der Kraken-Schluessel NICHT um WebSockets-Rechte erweitert.
      BELEG (24.09. 21:35, Trockenlauf validate=true, kein Geld bewegt): Marktkauf und
      Stop-Loss werden angenommen ('buy 0.00010 XBTEUR @ market' / 'sell 0.00010 XBTEUR
      @ stop loss 78000.0'), ein falsches Paar wird abgelehnt - der Weg ist befahrbar UND
      fehlerempfindlich. Dabei gefunden und behoben: wachen.json trug kein 'paar',
      handeln.py fiel auf das Nautilus-Symbol BTC/EUR zurueck, das Kraken mit
      'EQuery:Unknown asset pair' abweist -> "paar": "XXBTZEUR" ergaenzt, Test Orderpaar
      in test_handeln.py.
      OFFEN: Der Futures-Arm (PF_XBTUSD) hat GAR KEINEN REST-Zweig - kraken.py ist die
      SPOT-REST-API, Kraken Futures eine eigene Schnittstelle (anderer Host, eigene
      Signatur). Der REST-Weg traegt nur nautilus_kraken (Spot).
      GUTHABEN: 4,10 EUR frei (24.09. 21:35) - unter jedem sinnvollen Einsatz, der
      Live-Zweig bleibt also ohnehin zu, bis EUR frei ist.
      Naechster Schritt: pruefen, ob der Nautilus-Exec-Client aus dem Code verschwindet
      (kraken_order_test.py, Altlasten), damit niemand den toten Weg neu verdrahtet.

      Betrifft: Agenten/Handel/nautilus_kraken (+ `_futures`), Werkstatt/Repos/nautilus*
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24


- [ ] **T-063 — moon-dev-ai-agents: entscheiden, ob die Content-/Medienagenten ueberhaupt laufen sollen**
      Kontext: In der .env stehen acht Platzhalter, die nur ueber Fremdkonten zu
      fuellen sind und mit Handel nichts zu tun haben: ELEVENLABS_API_KEY,
      GROQ_API_KEY, YOUTUBE_API_KEY, RESTREAM_CLIENT_ID/-SECRET/-EMBED_TOKEN,
      TWITTER_USERNAME/-EMAIL/-PASSWORD, GOOGLE_APPLICATION_CREDENTIALS. Alles,
      was fuer den HANDEL zaehlt, laeuft schluessellos (lokales Modell ueber die
      Bruecke, oeffentliches CoinGecko statt Schluessel, RPC_ENDPOINT gesetzt).
      Solange diese Frage offen ist, bleiben die betroffenen Agenten dunkel -
      sie sind aber kein Betriebsfehler, sondern eine Entscheidung.
      Naechster Schritt: Max sagt je Gruppe ja/nein (Twitter, Yo
      uTube, Restream, ElevenLabs, Google) - bei nein die Platzhalter
      auskommentieren, damit der Zustand nicht als "unfertig" gelesen wird.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents/.env


- [x] **T-061 — moon-dev-ai-agents: welche Agenten ohne tote Datenquelle weiterlaufen sollen**
      Kontext: `api.moondev.com:8000` antwortet nicht (gemessen 24.09.2026, kein
      HTTP-Status). Damit sind `whale_agent`, `funding_agent`, `liquidation_agent`,
      `fundingarb_agent` und alles unter `src/agents/api.py` ohne Daten — ein
      Schlüssel hilft dort nicht, es fehlt die Quelle. Dagegen laufen
      `new_or_top`, `kraken_agent`, `sniper_agent` und `trading_agent` schon
      schluessellos (freie Quellen: CoinGecko public, Pump.fun, OKX/Kraken).
      Die Content-Agenten (Twitter, YouTube, Restream, ElevenLabs, Google)
      brauchen Fremdkonten und haben mit Handel nichts zu tun — bewusst nicht
      verdrahtet.
      Erledigt: 2026-09-24. Keiner der drei api.py-Agenten braucht den
      MoonDev-Schluessel: `src/agents/api_frei.py` stellt dieselbe Klasse mit
      derselben Schnittstelle bereit (gleiche Methoden, gleiche DataFrame-
      Spalten) und holt die Daten aus oeffentlichen Quellen - Funding 910
      Saetze je Aufruf von Binance /fapi/v1/premiumIndex, Open Interest von
      Binance /fapi/v1/openInterest + markPrice, Liquidationen von OKX
      /api/v5/public/liquidation-orders je uly (Binance allForceOrders
      antwortet 404, der Endpunkt ist weg). Die Klasse versucht ZUERST die
      echte API und schaltet nur um, wenn der Host nicht antwortet; Rueckweg
      ist der Import in den drei Agenten.
      KORREKTUR der Annahme im Eintrag: es sind DREI Agenten, nicht fuenf -
      `fundingarb_agent` nutzt api.py nicht (eigene Datenwege), und die
      Content-Agenten brauchen Fremdkonten statt einer Datenquelle.
      Bewusst NICHT ersetzt: `get_copybot_follow_list` und
      `get_recent_transactions` sind MoonDevs eigene Kopierhandels-Datenbank;
      beide geben None zurueck, damit die Agenten den Zyklus ueberspringen
      statt mit Nullwerten zu rechnen.
      Nachweis (je ein Lauf, echte Zahlen): whale_agent BTC-OI 8,09 Mrd USD /
      ETH 6,11 Mrd / Total 14,21 Mrd (Binance); liquidation_agent 300 OKX-
      Zeilen, 1-h-LONGS 28.249,61 USD (6 Ereignisse), 4-h-LONGS 314.626,55 USD
      (96 Ereignisse); funding_agent 910 Saetze.
      Fallen: die Agenten verlangen OPENAI_KEY UND ANTHROPIC_KEY schon im
      Konstruktor; ohne `python -u` bleibt bei einem abgebrochenen Lauf das
      Log LEER, obwohl der Agent arbeitet.
      Doku: MaxHirn/Wiki/Werkzeuge/MoonDev-Freie-Datenquellen.md
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents/src/agents/

- [x] **T-062 — moon-dev-ai-agents: fremde uncommittete Arbeit im Werkstatt-Klon**
      Erledigt: 2026-09-24. Der Arbeitsbaum ist gesichert und leer: die
      parallele Sitzung hat ihren Teil selbst committet (a344457), der Rest
      (moongui.py, backtest_runner.py, backtest_start.py, src/data/rbi/*,
      src/data/coingecko_results/*) ist als 7a894b3 mit der Kennung
      "Andere Sitzung <fremd@local>" nachgezogen und nach origin/main gepusht.
      `.env` blieb draussen (echte Schluessel; sie stand nicht im Status).
      Kontext: Im Klon liegen Änderungen, die nicht aus meiner Sitzung stammen:
      `rbi_agent.py` (36 Einfügungen / 78 Löschungen), `sniper_agent.py`,
      `src/models/ollama_model.py`, `src/nice_funcs.py`, `src/data/rbi/ideas.txt`,
      gelöschtes `src/.env_example`, dazu untracked `BUG_REPORT_DETAILED.md`,
      `FIXES_APPLIED.md`, `README_FIXES.md`, `SESSION_2_SUMMARY.md`, `START_GUI.bat`,
      `VALIDATE_ALL.bat`, `startup.py`, `src/utils/`, `src/data/coingecko_results/`.
      MEINE Änderung in `rbi_agent.py` (Aufrufort liest `DEEPSEEK_BASE_URL`) ist
      deshalb NICHT mitcommittet — sie liegt im Arbeitsbaum und wirkt, ist aber
      nur auf dieser Platte bzw. in der Arbeitsbaum-Kopie gesichert.
      Naechster Schritt: fremde Arbeit sichten und in einem eigenen Commit mit
      Autor „Andere Sitzung <fremd@local>“ sichern, danach die eine Zeile im
      rbi_agent nachziehen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents (Fork mfaupel95/moon-dev-ai-agents)


- [ ] **T-059 — Rest-Konsolenblitze: Agenten->onchainos, copilot, docker/npx**
      Kontext: Nach dem Fix der Haus-Prozesse bleiben ~6 kurze Konsolenfenster je
      Minute: (a) die moondev-Agenten (Fremd-Repo new_or_top/kraken) spawnen
      onchainos.exe weiter ohne CREATE_NO_WINDOW; (b) GitHub Copilot (copilot.EXE
      via npx) blitzt; (c) einmalige docker/npx/uvx-Build-Ketten. Kein
      kontinuierlicher Fokus-Raeuber wie der git-Poller, aber noch sichtbare
      Fenster.
      Naechster Schritt: (a) im Fremd-Repo die onchainos-Spawns auf
      CREATE_NO_WINDOW stellen; (b/c) beobachten, ob Copilot/docker-Builds im
      Alltag stoeren, dann gezielt.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents, GitHub Copilot, Docker

- [?] **T-049 — xperp-Key antwortet 50101, kein Orderweg**
      Kontext: Der OKX-EEA-Satz von xperp liefert 50101
      ("APIKey does not match current environment"), obwohl handel_erlaubt
      und freigabe.erfuellt true sind und das Fenster offen war. Kein
      Dateischalter loest das - es ist ein Konto-/Schluesselproblem: Host
      (EEA vs. global), IP-Whitelist oder fehlendes Trade-Recht.
      Naechster Schritt (Max, OKX-Portal): signierter Leseaufruf gegen den
      Registry-Host (guthaben/offene_orders), Schluesselrechte im Portal
      pruefen (read_only -> Trade), Host/Whitelist abgleichen.
      Wartet auf: Max - OKX-Key-Rechte/-Umgebung fuer xperp
      Betrifft: Agenten/Handel/xperp/okxf.py, OKX EEA (OKX_BASE)
      Angelegt: 2026-09-22 · Zuletzt: 2026-09-22

- [?] **T-050 — kraken bleibt Papier: Guthaben und Rueckrechnung**
      Kontext: Freies Guthaben reichte zuletzt nicht fuer mindest_guthaben_eur
      60 (33,15 EUR frei), und die eigene Rueckrechnung ist -0,57 % je Runde.
      handel_erlaubt=false, stillgelegt gesetzt. Die Auto-Freigabe oeffnet nur
      das Fenster, nicht das Guthaben.
      Naechster Schritt (Max): entscheiden, ob Kraken-Guthaben aufgestockt
      wird; bis dahin bleibt kraken bewusst nicht live.
      Wartet auf: Max - Aufstockung Kraken-EUR oder bewusst Papier lassen
      Betrifft: Agenten/Handel/kraken/wachen.json (mindest_guthaben_eur)
      Angelegt: 2026-09-22 · Zuletzt: 2026-09-22


- [x] **T-038 — 21,5 GB Modellgewichte liegen auf `C:`, nicht in `Modelle/`**
      **Erledigt 2026-09-19.** Auf `C:` liegt kein Modellgewicht mehr (C: frei
      3,2 GB → 66,1 GB). Die 21,1 GB `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` liegen
      unter `O:\Modelle\GGUF\`; das 0,84 GB große mmproj wurde nach
      `O:\Modelle\hermes\assets\` verschoben, und
      `%LOCALAPPDATA%\hermes\models` ist jetzt eine Junction auf
      `O:\Modelle\hermes`.
      **Antwort auf die Frage nach der Variable:** Es gibt **keine** eigene
      Variable für den Modellort — `bootstrap.models_dir()` liest
      `get_default_hermes_root() / "models"`, also `%LOCALAPPDATA%\hermes\models`
      (wenn `HERMES_HOME` ungesetzt) bzw. `HERMES_HOME\models`. Mit dem
      gesetzten `HERMES_HOME = ...\BrainFiles\Agenten\Hermes` wäre das
      `Agenten\Hermes\models` — dort ist bewusst **keine** Junction: `Agenten\`
      ist Sicherungsquelle, robocopy würde den Modellen in die Nachtsicherung
      folgen.
      **Offen bleibt:** `local_runtime.enabled` steht auf `false`, deshalb
      liest derzeit niemand diesen Ordner. Vor dem Einschalten muss entschieden
      werden, wohin die Gewichte gehören — sonst landen 20 GB wieder auf `C:`
      oder in der Sicherung.
      Zuletzt: 2026-09-19
      --- ursprünglicher Befund vom 08.09.2026 ---
      Kontext: Bei der Gesundheitsprüfung am 08.09.2026 gemessen.
      `%LOCALAPPDATA%\hermes\models` ist **21,5 GB** groß und damit der größte
      einzelne Posten auf der Systemplatte (`AppData\Local\hermes` gesamt
      22,7 GB). Das widerspricht der Regel aus der Wurzel-`CLAUDE.md`:
      Modellgewichte gehören nach `Modelle/` (Junction auf `O:\Modelle`), sind
      neu herunterladbar und bleiben deshalb aus der Sicherung draußen. Auf
      `C:` werden sie weder gesichert noch aus der Sicherung ausgenommen — sie
      belegen einfach die Platte, die am knappsten ist.
      Zum Vergleich auf derselben Platte: Claude 25,6 GB
      (`Packages\Claude_pzs8sxrjxfjjc` 13,8 + `Roaming\Claude` 11,8),
      `Cleanup_2026` 13,0, `Roaming\Pioneer` 11,7.
      Nächster Schritt: prüfen, ob Hermes den Ort über eine Variable lesen
      kann (wie Ollama über `OLLAMA_MODELS`); wenn ja, Store nach
      `O:\Modelle\hermes` verschieben und die Variable setzen. Wenn nein,
      entscheiden, welche Modelle dort überhaupt gebraucht werden.
      Betrifft: `%LOCALAPPDATA%\hermes\models`, [[Ordnerstruktur]]
      Angelegt: 2026-09-08 · Zuletzt: 2026-09-08


- [x] **T-011 — Wer schreibt `Modelle/.onchainos`?** — erledigt 2026-09-08
      Nach Suche im gesamten Vault: **kein Skript** referenziert diesen Pfad.
      Der Ordner ist ein Überbleibsel von „Stufe 0" (vor dem 30.08.2026),
      wahrscheinlich von OKX/OnchainOS-Werkzeugen angelegt. Inhalt:
      `wallets.json` (30+ Chain-Adressen, Projekt-ID
      `agentic-wallet-project01`, Account `05c0d7a8-…`),
      `machine-identity` (SHA-256-Hash), `session.json` (Session-Key,
      ablaufbar 2027-01-18), `keyring.enc` (verschlüsselt).
      **Maßnahme:** Vollständiges Backup nach
      `Archiv/OnChainOS_Backup_20260908/`, Notiz erstellt in
      `Wissen/OnChainOS_Backup.md`, Original gelöscht.
      Keine aktive Komponente nutzt den Ordner — kein Risiko bei Wegfall.
      Betrifft: `Modelle/.onchainos` → `Archiv/OnChainOS_Backup_20260908/`
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-08


- [x] **T-032 — In `Werkstatt/` liegt eigene Arbeit, die nirgends gesichert wird** — erledigt 2026-09-19
      **Erledigt 2026-09-19.** `Werkstatt/Protokolle/Codex` (78 Dateien) nach
      `O:\Archiv\Protokolle\Codex` verschoben — liegt jetzt in der über
      `sichern.ps1` geschützten Archivmenge. `Werkstatt/Sitzungen/m3u_cleaner`
      wurde **nicht** überschrieben: `O:\Archiv\Software\m3u_cleaner` existiert
      bereits (229 Dateien, neueste `.py` in beiden Kopien identisch), die
      m3u_cleaner-Arbeit ist damit schon im gesicherten Archiv. Die
      Werkstatt-Kopie (335 MB) bleibt als redundante Fassung stehen;
      Kollisionsschutz hatte den Umzug verhindert. Kein Eingriff in
      `sichern.ps1`. Hinweis: eine parallele Sitzung reorganisiert gerade
      `O:\Archiv\Software\m3u_cleaner`.
      Kontext: Beim Abräumen von `G:` am 03.09.2026 aufgefallen. `Werkstatt/`
      ist aus beiden Sicherungen ausgenommen — richtig für geklonte Fremd-Repos
      und Sitzungsreste, falsch für das, was tatsächlich dort liegt:
      `Werkstatt\Sitzungen\m3u_cleaner\` ist eigener Python-Code samt
      PyInstaller-Builds, `Werkstatt\Protokolle\Codex\` sind Auswertungen. Von
      beidem existiert nur noch die alte Kopie auf `G:` (Ordner `Codex\` und
      `Coworking-Space\`, zusammen 0,4 GB), und die stammt von vor dem
      30.08.2026.
      Nächster Schritt: entscheiden, ob `m3u_cleaner` in den Vault gehört
      (dann nach `Archiv/Software/` — liegt seit 07.09.2026 auf `O:\Archiv`,
      T-037 — oder als eigenes Projekt) oder ob `Werkstatt/` eine Ausnahme in
      `sichern.ps1` bekommt. Bis dahin die beiden
      Altordner auf `G:` stehen lassen.
      Betrifft: `Werkstatt/`, `Agenten/sichern.ps1`
      Angelegt: 2026-09-03 · Zuletzt: 2026-09-03


- [x] **T-033 — `OKX_API.env`: Schlüssel im Portal widerrufen** — erledigt 2026-09-19
      **Erledigt 2026-09-19.** Alter Key im Portal widerrufen; neue Schlüssel
      per `setx` in der **User-Umgebung** registriert und bestätigt
      (`OKX_API_KEY`/`OKX_API_SECRET`/`OKX_PASSPHRASE`, alle Werte **neu**, nicht
      der widerrufene). Die Klartext-Kopie in `_zu_loeschen` existiert nicht
      mehr (schon im Aufräumen entfernt). Hinweis: Ein 4-Zeichen-`OKX_SECRET_KEY`
      steht noch in der User-Umgebung — vermutlich der alte unbrauchbare Rest,
      bei Bedarf entfernen.
      Kontext: Beim Abräumen von `G:` am 03.09.2026 im Altzweig gefunden
      (`Claude\Worktrees\Investment\OKX_API.env`, 124 Bytes, Stand
      07.08.2026). Kein Duplikat, sondern der letzte Rest eines alten
      Arbeitszweigs.
      **Erledigt am 03.09.2026:** Inhalt geprüft, Datei nach SHA256-Verifikation
      von `G:` nach `Archiv/Posteingang/_zu_loeschen/` verschoben — damit ist der
      Klartext von der Platte weg, die regelmäßig abgezogen wird (T-015). Befund
      in [[Zugaenge]] festgehalten: Der Secret ist zu kurz (4 Zeichen gemessen,
      am 23.08. mit 6 notiert) und damit unbrauchbar; Key und Passphrase sehen
      echt aus und stehen sonst nirgends in `Zugaenge.md`. Der dortige Pfad-
      verweis auf `Claude/Worktrees/investment/` ist mitgezogen.
      **Nicht gelöscht** — Stufe 0, und die Datei ist bis zum Widerruf das
      Identifikationsmittel im Portal.
      Nächster Schritt: Max ruft `https://web3.okx.com` → API-Verwaltung auf und
      löscht den Schlüssel. **Ob er noch aktiv ist, lässt sich von hier nicht
      feststellen** — ohne gültigen Secret ist keine signierte Anfrage möglich.
      Bis dahin gilt er als möglicherweise aktiv. Danach darf die Datei weg.
      **Es gibt eine zweite Kopie:**
      `O:\MaxHirn-Zweitkopie\Claude\Worktrees\investment\OKX_API.env` (124 Bytes,
      07.08.2026) — der Altzweig, wie er beim letzten Zweitkopie-Lauf aussah.
      Bewusst nicht angefasst: In eine Sicherung greift man nicht nebenbei
      hinein. Nach dem Widerruf müssen **beide** weg, sonst war der Aufwand
      umsonst. Gesucht wurde in `C:\Users\faupe\Documents`, `G:`, `O:` und `J:`
      — **ganz `C:` ist nicht geprüft**, dort ist eine weitere Kopie nur
      unwahrscheinlich, nicht ausgeschlossen.
      Wartet auf: Max — Widerruf im OKX-Portal
      Betrifft: `Archiv/Posteingang/_zu_loeschen/OKX_API.env`,
      `O:\MaxHirn-Zweitkopie\...\OKX_API.env`, [[Zugaenge]]
      Angelegt: 2026-09-03 · Zuletzt: 2026-09-03 (23:34)


- [x] **T-013 — Drei Pfadverweise in `Zugaenge.md` von Hand nachziehen** — erledigt 2026-09-07
      Alle drei Verweise geändert:
      1. Zeile 108: `Claude/Software/…` → `Archiv/Software/…`
      2. Zeile 116: `Claude/Worktrees/investment/` → `Archiv/Worktrees/investment/`
      3. Zeile 156: `O:\MaxHirn-Zweitkopie\Claude\Worktrees\…` → `Archiv\Worktrees\…`
         (mit erklärend erwähnt: das ist der alte Pfad aus der Sicherung vom 30.08.2026)
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-07


- [x] **T-014 — 1,5 GB Ollama-Protokolle in 17 Dateien** — erledigt 2026-09-07
      Das Hauptvolumen (1,5 GB) war nicht in den 17 Protokolldateien, sondern im
      Ordner `updates_v2` (alte Ollama-Versionen). Gelöscht am 07.09.2026, 22:40.
      Danach regenerieren sich die `.log`-Dateien (trivial, <10 KB je). Die
      `.sqlite-wal` und `.sqlite-shm` Dateien werden von Ollama bei Neustart neu
      angelegt, sind aber Temp-Dateien und verschwinden bei Inaktivität.
      **Resultat:** 1,5 GB Speicherplatz auf C: freigegeben.
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-07


- [x] **T-016 — Ordner `MaxHirn/Claude/` → `MaxHirn/Archiv/` samt Verweisen** — erledigt
      2026-09-02. Der physische Rename lief am 01.09. bei der Absturz-Recovery
      durch; `MaxHirn/Claude/` existiert nicht mehr. Am 02.09. nachgezogen:
      `.gitignore`-Whitelist zeigt auf `MaxHirn/Archiv/`, `git check-ignore`
      bestaetigt, dass neue Dateien unter `Archiv/` **nicht** mehr ignoriert
      werden. `.venv` in `Archiv/ArchivSuche/` neu erzeugt (Python 3.13) und
      `requirements.txt` installiert — alle neun Abhaengigkeiten importierbar.
      Textebene: `Claude/` → `Archiv/` in ~25 versionierten Dateien (Notizen,
      Dashboard, Archiv-Doku, Skript-Kommentare); `Claude/Worktrees/` →
      `Werkstatt/Worktrees/`; `%APPDATA%\Claude\` (Claude-Desktop-Config) und
      historische „hiess Claude/"-Erwaehnungen verschont. Dabei drei kaputte
      Skriptpfade gefunden und behoben: `sichern-zweitkopie.ps1` (Medien-
      Ausschluss), `posteingang.ps1` und `mail/mailversand.py` (Wurzel loeste
      seit der Ordnertrennung auf `Agenten/` statt `BrainFiles/` auf).
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-02


- [x] **T-017 — Gehebelter Handel hat noch keine `wachen.json`** — erledigt
      2026-09-01. `Agenten/Handel/xperp/wachen.json` liegt (Höchsteinsatz je
      Anlauf 50 USD Margin, gesamt 200, Höchsthebel 5, Pflicht-Stop in ATR
      statt Prozent, Kill-Switch je Anlauf und gesamt). Der Modulkopf von
      `okxf.py` ist auf Spur 2 umgeschrieben und nennt den alten Wortlaut nur
      noch als Historie. Zusätzlich legt `bot.pruefpflicht()` die vier
      geforderten Zahlen vor; neu gerechnet ist Zahl 4 (nötige gegen
      beobachtete Trefferquote) samt Warnung, wenn die seltenere Seite unter
      zehn Ereignissen liegt. Siehe [[XPERP-Handel]].
      Kontext: [[Schutzregeln]] erlaubt seit dem 01.09.2026 gehebelte
      Positionen auf ausdrückliche Anweisung (Spur 2). Die Grenzen dieser Spur
      stehen bisher **nur in der Prosa der Notiz**, nicht in einer Datei — im
      Gegensatz zu Spur 1, wo `scanner/wachen.json` die einzige Wahrheit ist.
      Genau diese Bauform ist aber der Schutz: eine Sitzung kann eine Regel
      vergessen, eine Datei nicht.
      Zweitens trägt `Agenten/Handel/xperp/okxf.py` im Modulkopf noch den
      alten Wortlaut („gilt ausdruecklich nur fuer nur Spot, nur Long, kein
      Hebel … Dieses Modul faellt NICHT darunter"). Das stimmt seit heute
      nicht mehr und widerspricht der Regeldatei.
      Nächster Schritt: `xperp/wachen.json` anlegen (Höchsteinsatz je Position,
      Gesamtnominal, Höchsthebel, Pflicht-Stop, erlaubte Kontrakte) und den
      Modulkopf auf Spur 2 umschreiben.
      Betrifft: `Agenten/Handel/xperp/` — **dort arbeitete am 01.09. 17:34 eine
      andere Sitzung**, deshalb hier nur eingetragen und nicht angefasst.
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-01


- [x] **T-019 — Die Regel erlaubt jetzt mehr, als der XPERP-Bot kann**
      Erledigt 2026-09-03: Der Live-Pfad ist gebaut, nachdem Max XPERP zum
      Hauptweg gemacht hat. Neu sind `xperp/handeln.py` (Zyklus, Ausstiege,
      Einstiege, Journal, Zustand) und `xperp/wachen_xperp.py` (Bedingungen
      1–5, Rechnung importiert aus `scanner/wachen_pruefung.py`).
      Die vier Pflichtzahlen stehen je Position im Journal, nicht im Chat —
      Spalten `liq_abstand`, `funding_pct`, `gebuehr_pct`, `quote_noetig`,
      `quote_beob`. Und sie sind keine Zierde: Der erste Papierlauf hat
      XAG short (Quote 19,8 % gegen nötige 33,3 %) und XAU short (23,7 gegen
      35,5) abgewiesen und drei Anläufe eröffnet — MSTR, CL, BZ.
      Punkt 2 und 3 der alten Liste sind mit angeglichen: der Hinweis in
      `wachen.json` und die Stellen in `bot.py`, die „es gibt keinen
      Live-Pfad" sagten.
      Gegengeprüft: Notausstieg bei altem Herzschlag schließt alle drei
      Positionen (`herzschlag_alt`), die Rundenrechnung erkennt sie als drei
      abgeschlossene Runden samt Funding. Die Testdaten wurden danach
      zurückgenommen, damit die Freigabe-Statistik sauber bleibt.
      **Offen bleibt daraus:** siehe T-035 (Herzschlag und Dauerbetrieb, vormals fälschlich T-032).

      Angelegt: 2026-09-01 · Zuletzt: 2026-09-01


- [ ] **T-057 — Hermes-Desktop git-Poller (bundle-skew) feuert auf jeden Fokus**
      URSACHE GEKLAERT (25.09.2026, belegt): onFocus (src/store/updates.ts:1083) ruft
      refreshDesktopVersion() (1084) -> getVersion() -> IPC hermes:version
      (electron/main.ts:18193) -> detectRendererSkew() (18172) -> detectBundleSkew()
      (zwei runGit: merge-base + rev-list) - auf JEDEN Fokus, OHNE Rate-Limit.
      Kontrast: runPassiveChecks (der eigentliche Update-Poll) ist korrekt per
      passiveCheckDue auf 24h begrenzt (BACKGROUND_UPDATE_CHECK_MS), nur der
      Versions-Check im Fokus-Handler ist ungebremst. Rueckkopplung: der git-
      Prozess (Konsolen-Kind eines GUI-Elterns ohne Konsole) blitzt ein Fenster,
      das den Fokus stiehlt; der Focus-Wechsel feuert onFocus erneut -> 2-3s-
      Schleife (gemessen 24.09.: ~8 git-Blitze/40s). Nach dem Haus-Fix (moondev/
      handelszentrale fensterlos) ist der direkte Fokus-Raeuber weg, die Schleife
      stoppt; der Verstaerker bleibt latent (jeder echte Fokus-Wechsel laeuft
      wieder git).
      Fix (upstream Nous Research, das Repo ist KEIN Fork): detectRendererSkew()-
      Ergebnis cachen (1x je Lauf oder TTL), oder refreshDesktopVersion() in
      onFocus an passiveCheckDue binden. Ein lokaler Patch wird von `hermes update`
      ueberschrieben.
      Naechster Schritt: als Issue an NousResearch/hermes-agent melden, oder einen
      lokalen Cache-Patch anlegen und den Update-Verlust bewusst in Kauf nehmen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-25
      Betrifft: hermes-agent apps/desktop (updates.ts:1083, main.ts:18172)


- [ ] **T-056 — OKX-Quoten-Node (nautilus) liefert nichts**
      Kontext: `docker ps` antwortet nicht mehr, der Container nautilus-demo
      ist damit unerreichbar; der Nautilus-Arm bekommt keine Fills und fuellt
      kein Buch (Quote-Feed tot, feed_quelle=fallback_kopier, quotes=0).
      Naechster Schritt: Docker Desktop pruefen (Dienst + Container), danach
      einen Zyklus abwarten und die Quoten im Zustand zaehlen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: nautilus (eigenes Repo), Docker Desktop


- [ ] **T-055 — fomo-radar-Bot ohne auth.json-Verknuepfung**
      Kontext: Das Profil laeuft, aber `auth.json` ist noch eine eigene Datei
      statt eines Symlinks auf Agenten/Hermes/auth.json; das Anlegen braucht
      Adminrechte (UAC-Prompt blieb nachts unbestaetigt). Bis dahin traegt die
      Ollama-Rueckfallkette.
      Naechster Schritt: `Agenten/Hermes/scripts/auth-verknuepfen.ps1` erhoeht
      ausfuehren, UAC bestaetigen, danach `hermes -p fomo-radar chat -q "hallo"`
      und den Modellnamen pruefen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      BELEG 2026-09-30: Bestandsaufnahme aus der Kanban-Karte `t_5cf6dbfd` (Board `repos`,
      Status blocked/needs_input): 18 Profile haben inzwischen einen echten Symlink auf
      `Agenten/Hermes/auth.json`; **zwei fehlen noch: `fomo-radar` und `lokal-first`**.
      Ein Versuch aus der headless-Sitzung schlug fehl - `ln -s` bildet ohne das Privileg
      `SeCreateSymbolicLinkPrivilege` STILL eine Kopie (genau das Insel-Muster, das die
      Verknuepfung vermeiden soll); die zwei entstandenen Kopien wurden wieder entfernt.
      Unberuehrt bleiben `awesome-systematic-trading` und `basic-memory` (eigene befuellte
      Stores - ein Symlink wuerde deren Bot-Zugangsdaten aendern).
      Betrifft: Agenten/Hermes/profiles/fomo-radar/, Agenten/Hermes/profiles/lokal-first/


- [ ] **T-054 — Fremde SKILL.md-Aenderungen unter skills/brainfiles sichern**
      Kontext: Seit dem 24.09.2026 stehen mehrere SKILL.md geaendert im
      Arbeitsbaum, die nicht aus meiner Sitzung stammen (u.a.
      dauerprozess-bewachen/SKILL.md mit 169 Einfuegungen / 7 Loeschungen,
      dazu arbeitsbaum-git-hygiene, fremd-agenten-betrieb, fremdrepo-agent-start).
      Nach Hausregel gehoeren sie in einem EIGENEN Commit mit
      `Andere Sitzung <fremd@local>` gesichert.
      Naechster Schritt: Diff je Datei ansehen, dann namentlich stagen
      (kein `git add -A`) und als Fremdarbeit committen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      BELEG 2026-09-30: Die Aenderungen liegen unveraendert im Arbeitsbaum (7 SKILL.md,
      zuletzt angefasst 01:37-01:50, dazu der neue Skill `brainfiles/kanban-board/` und
      `dauerprozess-bewachen/references/geplante-aufgaben-anlegen.md`). Die schreibende
      Sitzung laeuft noch; solange gilt die 30-Minuten-Regel, dann zieht
      `fremdarbeit-einziehen.ps1` (20:40) sie mit Autor `Andere Sitzung <fremd@local>` nach.
      Betrifft: Agenten/Hermes/skills/brainfiles/, Agenten/Hermes/skills/aufgabenliste-pflegen/


- [ ] **T-053 — handel-spuren kuerzen (Auftrag vom 24.09., Limit war veraltet)**
      Kontext: Der Auftrag beruhte auf meiner Meldung, skill_manage verweigere
      jede Ergänzung (100.663 von 100.000 Zeichen). Nachgemessen: die Datei ist
      52.814 Bytes / 715 Zeilen, und der Einfuegevorgang wurde angenommen - die
      alte Meldung stimmte nicht mehr. Der Kontohandgriff ist deshalb direkt
      eingefuegt (neuer Abschnitt + references/boersen-aufrufe.md).
      Naechster Schritt: nur wenn Max die Struktur trotzdem teilen will - dann
      die fuenf grossen Bloecke (Wann 7,6 kB, Pitfalls 8,0 kB, Handelszentrale
      6,8 kB, Werkzeugfallen 7,5 kB, Prozedur 6,7 kB) nach references/ auslagern
      und im SKILL.md nur den Ausloeser lassen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Hermes/skills/brainfiles/handel-spuren/SKILL.md


- [ ] **T-052 — OKX-DCA-Parameter der laufenden Bots anpassen**
      Kontext: Der Weg ist bekannt (dca/amend-order-algo), aber `anpassen_erlaubt`
      steht auf false und es fehlt Guthaben: 0,03 USDC frei gegen ~428 USDC
      Margin (UNI 163,90 · ARB 145,19 · MON 102,09 · BCH 17,25). Die Leitern der
      fuenf DCA-Bots sind 4,2-8,4 % tief, die Instrumente laufen 8,6-13,2 % je
      TAG (ATR14) - Regel fuer neue Bots: Tiefe = max(3x ATR, Rueckgang 90/180/
      365 Tage, 10 %), Schritt 0,15-0,5x ATR, nie unter 2,5 %; der Engpass ist
      die STUFENZAHL (dca_max_steps 12 deckt bei 2,5 % nur 30 %).
      Naechster Schritt: Max nennt je Bot die gewuenschten Zahlen; danach
      `wachen.json` scharf schalten und mit --anwenden amendieren.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Handel/okx_bot_waechter/, OKX-Bots UNI/ARB/MON/BCH


- [ ] **T-036 — Codex über OmniRoute: Provider „codex" hat im Router keine aktiven Credentials**
      Kontext: Am 07.09.2026 war `MaxHirn/.codex/config.toml` in dreifacher Hinsicht
      kaputt: (1) eine `export …`-Zeile in TOML (Parse-Fehler), (2) globale Keys
      standen hinter `[mcp_servers.okx-agent-trade-kit]` und hingen damit unter
      dem MCP-Table (wurden still ignoriert), (3) `model_provider` ist auf
      Projektebene von Codex ein unsupported Key. Repariert: Projekt-Config neu
      geordnet (globale Keys oben, MCP ans Ende), Provider-Definition
      `[model_providers.omniroute]` in die User-Config `~/.codex/config.toml`
      gelegt (additiv, `.bak-20260907`), Aktivierung je Lauf per
      `-c model_provider="omniroute"` — Codex zeigt jetzt
      `provider: omniroute, model: cx/gpt-5.5`. Der Endpunkt selbst antwortet
      (401 ohne Key, Modellkatalog mit Key). **Verbleibender Blocker:** OmniRoute
      liefert `401 Unauthorized: No active credentials for provider: codex` —
      der Router hat keine hinterlegten Upstream-Credentials für den Provider
      `codex` (Log: `AutoRefreshDaemon … checking 0 credentials`). Das ist der
      seit 07.09. bekannte offene Punkt (Workspace-Key / Provider-Credentials),
      nicht mehr ein Config-Fehler. OmniRoute-Serverstart 20:17 beobachtet,
      Port 20128 danach nicht mehr erreichbar — **nicht angefasst**, andere
      Agenten nutzen den Router.
      Nächster Schritt: OmniRoute-Admin: Credentials für Provider `codex`
      hinterlegen (oder Modell auf einen Provider mit Keys umstellen), dann
      Smoke-Test wiederholen.
      Betrifft: `MaxHirn/.codex/config.toml`, `~/.codex/config.toml`, OmniRoute
      Wartet auf: Credentials für Provider `codex` in OmniRoute
      **Key-Verweis (13.09.2026):** Der Admin-Schlüssel für die OmniRoute-Config steckt
      nicht im Router-Prozess. Lesbar sind die Benutzervariablen
      `OMNIROUTE_ADMIN_API_KEY` (Admin-/Config-API `/api/*`) und `OMNIROUTE_API_KEY`
      (Modell-API `/v1/*`) direkt aus `HKCU\Environment` - der Prozess erbt frisch
      gesetzte Variablen nicht, also aus der Registry lesen statt env. Der Klartext
      selbst liegt nur in [[Zugaenge]] (Stufe 0): dorthin sehen, nie in Notizen
      kopieren.
      Angelegt: 2026-09-07 · Zuletzt: 2026-09-13 (Key-Verweis ergänzt)

- [?] **T-042 — orbk und kraken sind per Telegram nicht freizugeben**
      Kontext: Beim Pruefen von Max' Frage „Orbk ist noch nicht in freigabe.py
      angebunden?“ am 13.09.2026 aufgenommen. Es gibt zwei Freigabe-Wege mit
      zwei Spurenlisten:
      - Bildschirm (`freigabe.py`): spot (scanner), hebel (xperp), kraken;
        eine unbekannte Spur lehnt es mit klarer Meldung ab.
      - Telegram (`dauerlauf.befehl`): nur xperp und swap (`/ja_xperp`,
        `/ja_swap` samt nein/stop/freigabe) plus die generischen `/ja`,
        `/nein`, `/stop` fuer Spot.
      `kraken` hat einen Live-Pfad (`--live` vorhanden) und ist am Bildschirm
      angebunden, per Handy aber nicht - sie laesst sich nur am Rechner scharf
      schalten. `orbk` hat gar keinen Live-Pfad (kein Orderaufruf,
      handel_erlaubt=false, Sperre 4 offen: backtest_bestanden=false); dort ist
      nichts anzubinden, solange die Spur nicht live gehen soll. Beide stehen
      auf handel_erlaubt=false, die Luecke ist damit derzeit folgenlos.
      Naechster Schritt (erst bei Bedarf): vier Stellen nach dem Muster von
      swap - Live-Zweig und `freigabefenster.lade("<spur>")` in den
      Sperrgruenden der jeweiligen handeln.py, `WACHEN`/`BETRAGSFELD`/`TITEL`
      in freigabe.py, die `/ja_<spur>`-Familie in dauerlauf.befehl, und
      handel_erlaubt erst nach der jeweiligen Sperre.
      Betrifft: `Agenten/Handel/{orbk,kraken}`, `freigabe.py`, `dauerlauf.py`
      Angelegt: 2026-09-13

- [?] **T-045 — Facebook und Instagram: es fehlt nur die Browser-Extension**
      Kontext: Auf Max' Auftrag wurden am 16.09.2026 die Kanaele `facebook` und
      `instagram` in Agent Reach installiert. Beide laufen ueber OpenCLI
      (`@jackwener/opencli` 1.8.7, npm global) und benutzen den eigenen
      Chrome-Login - kein Cookie-Export, keine Zugangsdaten in Dateien. Der
      Daemon laeuft (Port 19825), der Kanalstatus ist `warn`: „opencli
      installiert, aber keine verbundene Browser-Extension“.
      Naechster Schritt (nur am Rechner, nicht aus der Sitzung):
      1. Extension installieren und aktiv lassen:
         https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk
      2. Im selben Browser bei facebook.com und instagram.com angemeldet sein,
         danach einen `opencli`-Befehl laufen lassen - der Doctor schaltet den
         Kanal erst danach auf verfuegbar.
      Zu bedenken: die Extension handelt im Namen des angemeldeten Kontos; die
      Doku von Agent Reach raet dafuer zu einem Zweitkonto. Gepostet wird nichts,
      die Kanaele lesen (Suche, Profil, Feed, Gruppen).
      Wartet auf: Max - Extension und Anmeldung
      Betrifft: [[Agent-Reach]], `Werkstatt/Repos/Agent-Reach`
      Angelegt: 2026-09-16

- [?] **T-046 — Benutzer-PATH enthaelt einen abgeschnittenen Eintrag `C:\Users\fa`**
      Kontext: Beim Nachsehen, wohin `yt-dlp` installiert werden muss
      (16.09.2026), fiel im Benutzer-PATH der Eintrag `C:\Users\fa` auf - ein
      abgeschnittener Pfad, der auf nichts zeigt. Er ist harmlos, kann aber
      Fehlermeldungen verwirren, und er zeigt, dass beim Bearbeiten des PATH
      einmal eine Zeile zu kurz geraten ist.
      Naechster Schritt: Den Eintrag in den Benutzervariablen entfernen - vorher
      die PATH-Zeile sichern, wie am 23.08.2026 praktiziert. Die uebrigen 18
      Eintraege bleiben unangetastet.
      Wartet auf: Freigabe von Max (Systemeinstellung)
      Betrifft: `HKCU\Environment` PATH
      Angelegt: 2026-09-16
- [?] **T-047 — Santiment-MCP braucht Max' Browser-Anmeldung (OAuth)**


- [ ] **T-023 — ASUS MG278 antwortet nicht auf DDC/CI, PowerDisplay lässt ihn aus**
      Kontext: Aus dem PowerToys-Report vom 02.09.2026. Von zwei Monitoren
      (beide direkt an DisplayPort) steuert PowerToys PowerDisplay nur den
      Acer XB281HK. Die **ASUS MG278** (`DISPLAY2`, EDID `ACI27A8`, in Windows
      als „Generic PnP Monitor") liefert keine DDC/CI-Daten; unabhängig von
      PowerToys mit `Agenten/Routinen/monitor-ddc-pruefen.ps1` nachgestellt:
      schon `GetCapabilitiesStringLength` scheitert mit Win32-Fehler
      `0xC0262582` (`ERROR_GRAPHICS_DDCCI_VCP_NOT_SUPPORTED`). Kein
      Software-Fehler — Reparatur nur am Monitor möglich.
      Nächster Schritt (Max, am Gerät): MG278-OSD → System Setup → DDC/CI → On;
      hilft das nicht, Monitor ~30 s stromlos, DP-Kabel/-Eingang prüfen. Danach
      `monitor-ddc-pruefen.ps1` erneut, bei Erfolg PowerDisplay „Monitore
      aktualisieren". Details: [[Hardware]], Abschnitt „Monitore und PowerToys
      PowerDisplay".
      Betrifft: Monitor ASUS MG278 · `Agenten/Routinen/monitor-ddc-pruefen.ps1`
      Angelegt: 2026-09-02 · Zuletzt: 2026-09-02

- [!] **T-004 — Zwölf Abschaltungen ohne Bluescreen seit 08.08., Ursache offen**
      Kontext: Alle zwölf Kernel-Power-41-Ereignisse haben `BugcheckCode = 0`
      und `PowerButtonTimestamp = 0` — kein Bluescreen, kein Speicherabbild,
      sondern harter Stromverlust. Keine WHEA-Fehler in 30 Tagen, keine
      Plattenfehler (nur ID 98, Information), kein Dump. In den drei Minuten
      vor dem letzten Abschalten steht **ein einziger** Protokolleintrag.
      **Die Beobachtung vom 28.08. ist entschieden — negativ.** Sie musste nicht
      auslaufen: seit dem Start am 28.08. um 16:00 ist der Rechner dreimal
      ausgegangen (29.08. 10:45, 29.08. 13:17, 30.08. 20:59, echte Zeitpunkte
      aus Ereignis 6008). Aus neun Vorfällen sind damit zwölf geworden, und die
      Abstände sind kürzer geworden: drei in zwei Tagen gegen sieben in den
      vierzehn Tagen davor.
      **Standby scheidet als Ursache aus.** Seit dem 28.08. 06:46 gab es keinen
      einzigen Standby-Zyklus mehr (kein Kernel-Power 42/107) — die drei neuen
      Abstürze fielen also in eine Phase ganz ohne Standby. Der Ablauf „3–10
      Minuten nach dem Aufwachen aus S3" war Begleiterscheinung, nicht Ursache.
      Das frühere Merkmal `SleepInProgress = 16` beruhte auf einer Verwechslung
      mit dem Feld `Checkpoint`; `SleepInProgress` ist bei allen zwölf `0`.
      Nächster Schritt: **Stromzufuhr ausserhalb des Netzteils prüfen** —
      Kaltgerätekabel, Steckdosenleiste, Wandsteckdose. Billig und nie geprüft,
      deshalb zuerst; danach erst der Gegentest mit einem bekannt guten Netzteil.
      Beides Handgriffe an der Hardware, also Max' Sache, und **einen nach dem
      anderen**, sonst ist unbekannt, welcher gewirkt hat. Bei zuletzt 2,5 bis
      32 Stunden Abstand zeigt sich das binnen zwei bis drei Tagen.
      Wartet auf: Max — Handgriff an Kabel und Steckdose.
      Messbefehl: Routinen/absturz-nachmessen.ps1 (nur lesend, ohne Adminrechte)
      Betrifft: [[Hardware]], Abschnitt „Nachmessung 30.08.2026, 22:20"
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-30 (22:20)


- [ ] **T-007 — 18 claude.ai-Connectors ohne einen einzigen Aufruf**
      Kontext: `claude mcp list` meldet 21 aktive claude.ai-Connectors. In
      53 gespeicherten Sitzungen wurden davon **drei** je einmal aufgerufen
      (Kalender, Gmail, Drive); die übrigen 18 kein einziges Mal — darunter
      Uber, Uber Eats, PayPal, HubSpot, monday.com, Morningstar, DataHub,
      Play Sheet Music, tldraw, Excalidraw, Sprouts, Windsor.ai, Superhuman
      Docs, ChangeThisFile, UseMyContext, Unstructured, Economic Index.
      Jeder belegt in **jeder** Sitzung Kontext, bevor ein Wort gesagt ist.
      Max hat das am 27.08. selbst als größten Hebel benannt; der Punkt ging
      danach verloren, weil er nirgends eingetragen war.
      Nächster Schritt: Max schaltet sie in den Connector-Einstellungen auf
      claude.ai ab — das geht nicht lokal und nicht aus einer Sitzung heraus.
      Messbefehl für den Vorher-Nachher-Vergleich:
      `sitzungen_auswerten.py --werkzeuge`
      Betrifft: claude.ai-Konto, nicht den Vault
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28


- [x] **T-008 — MCP-Server `mail` ist nicht eingerichtet** — erledigt 2026-09-19
      **Erledigt 2026-09-19.** Zugang ist hinterlegt und funktioniert:
      Adresse `faupel3107@googlemail.com` + App-Passwort im
      Windows-Anmeldeinformationsspeicher (`MaxMailVersand`), SMTP-Anmeldung
      getestet = `anmeldung: ok`. Kein Einrichten nötig; der Server war
      inzwischen konfiguriert.
      Kontext: `Archiv/CLAUDE.md` beschreibt den Versand über `mail_senden`
      als den vorgesehenen Weg für „schick mir das per Mail". Der Server
      antwortet aber mit „Keine Absenderadresse hinterlegt" — in 53 Sitzungen
      wurde er kein einziges Mal erfolgreich benutzt. Der dokumentierte Weg
      existiert also nur auf dem Papier. Die CLAUDE.md ist am 28.08.
      entsprechend korrigiert.
      Nächster Schritt: `MCP-Server/mail/.venv\Scripts\python.exe einrichten.py`
      — braucht Absenderadresse und App-Passwort, also Max' Zutun.
      Wartet auf: Zugangsdaten von Max
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28


- [x] **T-009 — `Zugaenge.md` als einzige Notiz ohne Frontmatter** — erledigt 2026-09-19
      **Erledigt 2026-09-19 (von Max freigegeben).** Acht Zeilen Frontmatter
      vorangestellt (`id: 20260830-zugaenge`, `tags: [sicherheit]`, Template wie
      die übrigen Notizen); der Body wurde byte-erhalten, kein Wert der Datei
      ausgelesen oder ausgegeben.
      Kontext: Am 30.08.2026 haben alle 21 übrigen Notizen in `Wissen/`
      YAML-Frontmatter mit stabiler `id` bekommen, dazu `Wissen/INDEX.md` als
      vollständige Registry. `Zugaenge.md` wurde bewusst ausgelassen, weil sie
      in [[Schutzregeln]] unter den geschützten Schlüsseldateien steht und dort
      kein Agent ohne ausdrückliche Anordnung schreibt. Sie ist in der Registry
      geführt, hat aber keine `id`. Fachlich spricht nichts dagegen — das
      Frontmatter berührt keine Zugangsdaten, sondern steht davor.
      Nächster Schritt: Max gibt frei (oder nicht); dann acht Zeilen Frontmatter
      voranstellen, `id: 20260830-zugaenge`, `tags: [sicherheit]`.
      Vorschlag zum selben Themenkreis, nicht eingetragen als eigener Punkt:
      Die Dateinamen in `Wissen/` sind gemischt geschrieben statt durchgehend
      kleingeschrieben. Eine Umbenennung würde alle `[[Wikilinks]]` brechen und
      ist den Gewinn vermutlich nicht wert.
      Betrifft: `Wissen/Zugaenge.md`, `Wissen/INDEX.md`
      Wartet auf: Freigabe von Max
      Angelegt: 2026-08-30 · Zuletzt: 2026-08-30


## Erledigt
- [x] **T-177 - Ausstiege zum Kerzenschluss rechnen die Gewinner zu gut**
      Kontext: Im Replay wird zum SCHLUSS der Kerze ausgestiegen, in der Stop
      oder Ziel beruehrt wurde - nicht zum Stop- oder Zielkurs. Ein Laeufer
      ueberschiesst sein Ziel dadurch deutlich: ADA stand mit Ziel +12 % im Buch
      und wurde mit +48 % geschlossen. Beide Familien (A und B) rechnen so,
      also sind ihre Zahlen untereinander vergleichbar - aber nicht als
      Ertragserwartung zu lesen.
      Naechster Schritt: intrabar-Ausstieg pruefen (Stop/Ziel-Kurs statt
      Kerzenschluss) und die Differenz an einem Lauf beziffern, bevor Zahlen
      aus dem Backtest in eine Entscheidung eingehen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/replay.py, backtest_prognose.py
      **Erledigt 2026-09-30.** Der Replay schliesst jetzt am Kurs der beruehrten Marke (Hoch/Tief) statt am Kerzenschluss - Ausloeser bleibt der Schluss wie live, nur der Preis ist berichtigt (replay.Beruehrungsjournal, beruehrte_marke/kurs_der_marke; Live-Pfad spur_buch.pruefe_ausstiege unangetastet). Vorher/Nachher ueber sechs Spuren: wavetrend +419,66 -> +385,88, macd_mtf +299,90 -> +285,02, squeeze +61,93 -> -6,34, topmovers +522,44 -> +260,00, funding +156,50 -> +87,00, supertrend -24,17 unveraendert; Rundenzahl und Trefferquote bei wavetrend/macd_mtf/squeeze/supertrend identisch (die Regel verschiebt den Kurs, nicht den Ausloeser). Markenquote je Lauf in auswertung_alle; Gegenprobe mit ausgeschaltetem Fix: 10 von 19 Tests rot. Offen als T-202 (Docht-Ausstieg) und T-203 (Backtest-Zahlen neu lesen).
- [x] **T-147 — Das Dashboard hat keine Wache**
      Kontext: `hermes update` beendete den Lauf am 29.09.2026 mit `outcome: partial` und
      `phase_error: "Could not restart every paused Windows gateway"`; der Gateway kam zurueck,
      das Dashboard nicht (Port 9119 bis zum manuellen `Start-ScheduledTask Hermes_Dashboard`
      tot). Der Gateway hat Wachen (Gateway-Waechter, gateway-identitaet-wache), das Dashboard
      keine - ein Ausfall bleibt bis zur naechsten Anmeldung unbemerkt.
      Naechster Schritt: Wache nach Hausmuster (`no_agent`, leere Ausgabe = nichts senden), die
      die ANTWORT prueft (`http://127.0.0.1:9119/` = 200) und nur dann startet, wenn 60 s nach
      dem Ausloesen kein Prozess da ist (der Dienst braucht ~45 s).
      Angelegt: 2026-09-29
      Betrifft: Agenten/Hermes/gateway-service/Hermes_Dashboard.vbs, Agenten/Hermes/scripts/
      Erledigt 30.09.2026: Agenten/Hermes/scripts/dashboard-wache.py + Hermes-Cron 'dashboard-wache' (bf375a2ac65f, alle 15 min, no_agent, Telegram, leere Ausgabe = nichts senden). Prueft die ANTWORT (HTTP, jeder Statuscode) statt nur den Port, unterscheidet einen laufenden Bau von einem Haenger ueber zwei CPU-Messungen der Prozesskette (12 s Abstand), heilt per Stop-Process + Start-ScheduledTask, Bremse 30 min. Belege: 18 Tests gruen (test_dashboard_wache.py, mit Attrappen), Gegenprobe mit entferntem Bau-Zweig = 2 Tests rot, Cron-Lauf 'silent (empty output)' bei HTTP 200, Alarmrichtung mit --nicht-heilen an echten Daten gezeigt. Wiki: Betrieb/Wachen-und-Aufgaben.md + Lektionen/Wahrheit-pruefen.md 13.
- [x] **T-133 — `Handel/historie.py` und `xperp/historie.py`: gleicher Modulname, Test rot**
      Kontext: `Agenten/Handel/tests/test_handelszentrale_bindung.py`
      (`NamensfalleTest`) verlangt, dass kein Modulname am Handel-Kopf auch in einem
      Spurenordner liegt - sonst faengt ein Import mit `Handel/` auf `sys.path` das
      falsche Modul (Befund 13.09.2026 mit `gui.py`). Gemessen am 25.09.2026 ist die
      Dopplung `historie` (Backtest-Fundament, Commit e9e28f3, aus einer parallelen
      Sitzung) gegen `xperp/historie.py` - die Handel-Suite ist dadurch rot
      (698 Tests, 1 Fehler). FREMDARBEIT: nicht von mir angefasst.
      Naechster Schritt: eines der beiden umbenennen (`Handel/backtest_historie.py`)
      und die Importe in `replay.py`/`optimieren.py`/Tests mitziehen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/historie.py, Agenten/Handel/xperp/historie.py, tests/
      **Erledigt 2026-09-30 (Stand abgeglichen, nicht neu gebaut).** Die Dopplung ist weg: `Agenten/Handel/historie.py` existiert nicht mehr, an seiner Stelle liegt `historie_binance.py` (Umbenennung aus dem Backtest-Fundament); `xperp/historie.py` bleibt Spur-eigen. Nachgemessen am 30.09.2026 02:05: `cd Agenten/Handel/tests && ../.venv/Scripts/python.exe -m unittest test_handelszentrale_bindung.NamensfalleTest -v` -> 1 Test, OK.
- [x] **T-151 - Geplanter Neustart des Rechners (Commit/Memory entlasten)**
      Kontext: Am 29.09.2026 war der PC sehr langsam durch Commit-Erschoepfung (~200 Zombie-
      MCP-Prozesse, 29,6 GB Commit); behoben per Kill + Wache mcp-zombie-wache (Cron 15 min,
      Telegram). Seit 100 h Uptime steht Memory Compression bei 7,5 GB. Max hat am 29.09.2026
      entschieden: Option 4 (nichts weiter bauen), aber Reboot einplanen. Design-Doc:
      MaxHirn/Wiki/Betrieb/Systemleistung-2026-09-29.md.
      Naechster Schritt: ruhiges Zeitfenster AUSSERHALB 20:00-22:30 (Nachtsicherungen) waehlen,
      offene Live-Positionen + freigabefenster pruefen, Restart-Computer -Force, danach Dauerlauf-
      Stufen, Gateway, Dashboard, mcp-zombie-wache und Commit-Lage pruefen. Zeitpunkt braucht
      Max' Freigabe.
      Angelegt: 2026-09-29
      Betrifft: Rechner/Host, alle Dauerlauf-Stufen, Gateway, Dashboard
      **Erledigt 2026-09-30.** Der Rechner wurde am 29.09.2026 um 21:06 neu gestartet (LastBootUpTime 29.09.2026 21:06:19), danach liefen die drei Dauerlauf-Stufen wieder an. Gemessen 30.09. 02:00: Commit frei 15,6 GB von 87,7 GB (vor dem Neustart 1,9 GB), 33 Python-Prozesse - die Commit-Erschoepfung ist weg. Der zweite Teil (Speicher entlasten) ist nur teilweise erreicht: Memory Compression steht bei 8,32 GB.
- [x] **T-048 — Ausser-Haus-Kopie verschluesseln (BitLocker To Go)**
      Kontext: Q:\MaxHirn-AusserHaus ist vollstaendig und geprueft, aber
      NICHT verschluesselt und enthaelt Klartext-Zugangsdaten
      (Wissen/Zugaenge.md, Wissen/OKX_API.env). Ohne angestecktes Q: stecken
      alle Kopien im selben Rechner; gegen den Netzteilschaden 2026 hilft nur
      die Kopie ausser Haus.
      Erledigt 2026-09-30: Entscheidung Max - bewusst OHNE BitLocker To Go.
      Die SSD bleibt unverschluesselt; die Vertraulichkeit haengt damit am
      Aufbewahrungsort (ausser Haus, kein Dritter). Dokumentiert in
      Wissen/Routinen.md, Abschnitt 'Die dritte Kopie: ausser Haus'.
      Betrifft: Q:\MaxHirn-AusserHaus, Wissen/Zugaenge.md (Stufe 0)
      Angelegt: 2026-09-22 · Zuletzt: 2026-09-30

- [x] **T-184 — Aufgabe 'MaxHirn-Ausserhaus-Kopie' ist nicht registriert (Doku sagt taeglich 21:30)**
      Kontext: Commit 12f3433 (30.09.2026, T-182) sagt, die Ausser-Haus-Kopie
      erneuere sich taeglich 21:30 ueber `Routinen/ausserhaus-kopie.ps1`. Der
      Aufgabenplaner kennt sie NICHT: `schtasks /query /tn "MaxHirn-Ausserhaus-Kopie"`
      endet mit „Das System kann die angegebene Datei nicht finden", und die
      vollstaendige Liste der MaxHirn-Aufgaben (25 Eintraege, 30.09.2026 01:30)
      enthaelt keinen Ausserhaus-Eintrag. Das Log
      `Agenten/Routinen/logs/ausserhaus-kopie-letzter-lauf.log` von 01:12 stammt
      daher von einem Handlauf. Der Registrierer dokumentiert selbst, dass
      `Register-ScheduledTask` "Ready" samt naechstem Lauf meldete, ohne dass die
      Aufgabe blieb - er legt darum per `schtasks /create` an und prueft per
      `schtasks /query`. Bis zur Klaerung ist die Doku-Aussage unbelegt.
      Naechster Schritt: `Agenten/Routinen/ausserhaus-kopie-aufgabe.ps1`
      ausfuehren (legt an und prueft selbst; wirft, wenn die Probe scheitert),
      danach unabhaengig per `schtasks /query` gegenpruefen.
      Angelegt 2026-09-30 · Zuletzt 2026-09-30
      Betrifft: Agenten/Routinen/ausserhaus-kopie.ps1, ausserhaus-kopie-aufgabe.ps1,
      Agenten/sichern-ausser-haus.ps1, Aufgabe MaxHirn-Ausserhaus-Kopie
      **Erledigt 2026-09-30.** Der Registrierer Agenten/Routinen/ausserhaus-kopie-aufgabe.ps1 wurde ausgefuehrt und hat die Aufgabe angelegt; unabhaengig gegengeprueft per schtasks /query: Aufgabenname \MaxHirn-Ausserhaus-Kopie, naechste Laufzeit 30.09.2026 21:30, Status Bereit, Aktiviert, Aktion powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ...ausserhaus-kopie.ps1. Die Kette ist am Handlauf 01:12 belegt (robocopy-Code 3 = erfolgreich, 65051 Dateien abgeglichen, 44,573 GB, 0 kopiert von 0 kopierten Bytes - alles schon vorhanden, Lauf 70 s). Q: war beim Nachpruefen angesteckt, deshalb bewusst KEIN zusaetzlicher Lauf ausgeloest. Offen bleibt nur der Blick auf den ersten PLANlauf (30.09. 21:30) im Log Agenten/Routinen/logs/ausserhaus-kopie-letzter-lauf.log; ohne angesteckte SSD endet er mit Exitcode 2 (uebersprungen, kein Fehlschlag).
- [x] **T-182 — Ausser-Haus-Kopie: Frist festschreiben und Fahrweise entscheiden**
      Kontext: Die Kopie unter Q:\MaxHirn-AusserHaus ist die einzige Sicherung
      ausserhalb dieses Rechners (G: und O: haengen am selben Netzteil). Sie
      laeuft von Hand - bewusst ohne geplante Aufgabe, weil das Ziel eine
      USB-Platte ist, die meist nicht angesteckt ist. Der neue Waechter
      (Hermes-Cron ausserhaus-frist-wache, 27a16c73cf03) meldet taeglich um
      08:00 erst, wenn die juengste Spur im Ziel aelter als 14 Tage ist
      (Merkdatei: hoechstens alle 72 h). Gemessen 29.09.2026: 5,1 Tage alt.
      Naechster Schritt: entscheiden - 14 Tage als blosse Erinnerung belassen,
      oder eine geplante Aufgabe, die bei angesteckter Platte selbst sichert.
      Angelegt · 2026-09-29
      Betrifft: Agenten/Hermes/scripts/ausserhaus-frist-wache.py, Agenten/sichern-ausser-haus.ps1
      **Erledigt 2026-09-30.** Aufgabe `MaxHirn-Ausserhaus-Kopie` (taeglich 21:30, versteckt, Zeitlimit 6 h) wird aus dem Gateway heraus angelegt (Hermes-Cron `ausserhaus-aufgabe-sichern`, 08:30) und faellt bei fehlender SSD mit Exitcode 2 still aus. Wrapper `Routinen/ausserhaus-kopie.ps1`; echter Lauf endet `ENDE ok` (robocopy-Code 3), nachdem `Agenten\Hermes\cache`, `cron\output`, `*.pid`, `*.db-shm`, `*.db-wal` ausgenommen wurden (Code 11 = Exit 1 vorher). Kopie war 5,1 Tage alt, jetzt frisch. Fristwache 14 Tage bleibt zweite Absicherung.
- [x] **T-180 — Zweitkopie bricht ab - Ziel J: ist die fehlerhafte Platte**
      Kontext: Die Zweitkopie (Ziel J:\MaxHirn-Zweitkopie) schlug am 28.09. (Code 1) und 29.09. (21:10, 0xC000013A abgebrochen) fehl. Direkt davor (21:06-21:07) 8x NTFS-Event 98 (Volume als schreibgeschuetzt eingebunden) auf J:. J: ist die WD My Book mit 479 unkorrigierten Lesefehlern (Memory) und so langsam, dass ein rekursives Auflisten 300 s ueberschreitet. Jetzt wieder schreibbar, aber die Platte ist der Schwachpunkt. Memory-Vorgabe war 'Zweitkopie auf O: (Disk 1)'.
      Naechster Schritt: Entscheiden, ob die Zweitkopie auf O: umzieht (gesunde Platte) oder J: ersetzt wird; dann sichern-zweitkopie.ps1 anpassen und einen Lauf pruefen.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/sichern-zweitkopie.ps1, Agenten/Routinen/zweitkopie.ps1
      **Erledigt 30.09.2026.** Ziel in sichern-zweitkopie.ps1 auf O:\MaxHirn-Zweitkopie umgestellt (Backup .bak-20260929), echter Lauf 30.09. 00:01-00:06 durchgelaufen: robocopy-Code 1, 200.113 Dateien / ~37 GB, Zielstruktur O:\MaxHirn-Zweitkopie\MaxHirn angelegt, O: frei 160,6 -> 121,1 GB. G: bewusst nicht gewaehlt: G:, H:, I: sind dieselbe Platte (Disk 2) wie die Hauptsicherung. J:-Altbestand bleibt liegen.
- [x] **T-129 — Fristwaechter fuer die Ausser-Haus-Kopie (sie wird still alt)**
      Kontext: `sichern-ausser-haus.ps1` hat ABSICHTLICH keine geplante Aufgabe -
      sie braucht die angesteckte Q:-SSD. Folge: am 25.09.2026 war die Kopie
      **13 Tage alt** (gemessen: 89.421 Dateien / 18,31 GB fehlten), ohne dass
      irgendwo eine Meldung entstand. Es gibt einen Nachweis (`spiegelstand.py`
      fuer Q:\\Handel_Journal) und den Tagesbericht, aber **keine Wache** auf das
      Alter der Ausser-Haus-Kopie selbst.
      Naechster Schritt: Wache nach dem Muster `spiegelfrist-wache.py` bauen -
      meldet nur, wenn die Kopie aelter als N Tage (Vorschlag 7) ist, leere
      Ausgabe sonst. Sie darf NICHT selbst kopieren.
      Angelegt: 2026-09-25
      Betrifft: Agenten/sichern-ausser-haus.ps1, Q:\\MaxHirn-AusserHaus
      **Erledigt 2026-09-29.** Agenten/Hermes/scripts/ausserhaus-frist-wache.py meldet nur, was eine Frist reisst (Kopie aelter als 14 Tage, Laufwerk nicht angeschlossen, Ziel fehlt/leer/nicht lesbar); Hermes-Cron 27a16c73cf03 taeglich 08:00, Probelauf 'succeeded'; 11 Tests gruen; gemessen: Kopie 5,1 Tage alt = gruen.
- [x] **T-138 — Docker-Engine aus: Container `nautilus-demo` fehlt, OKX-Arm ohne Quoten**
      Kontext: `docker ps -a` antwortet 29.09.2026 mit `failed to connect to the docker API at
      npipe:////./pipe/dockerDesktopLinuxEngine ... daemon is running`; die Systempruefung meldete
      dasselbe um 07:00 ("Docker-Engine antwortet nicht (Frist 20 s)"). Ohne den Container bekommt
      der Nautilus-Arm auf OKX keine Quotes - genau der Befund vom 25.09. (`feed_quelle
      fallback_kopier`, quotes=0); die uebrigen zwei Arme (Kraken Spot/Futures) laufen ohne Docker.
      Naechster Schritt: Docker Desktop starten, `docker start nautilus-demo`, Block 14 der
      Systempruefung nachziehen und pruefen, ob wieder Quotes ankommen.
      Angelegt 2026-09-29. Betrifft Agenten/Handel/nautilus, Docker-Host.
      **Erledigt 2026-09-29.** Docker Desktop laeuft (Max gestartet); `docker ps`: `nautilus-demo | Up`. Ob am OKX-Arm wieder Quoten ankommen, bleibt am Arm selbst zu beobachten.
- [x] **T-137 — Routine `fremdarbeit-einziehen`: Push scheitert mit 403, Commits bleiben liegen**
      Kontext: Der Lauf vom 28.09.2026 20:40 hat 5 ruhende Dateien uebernommen (Commit 5c80b19),
      aber nicht gepusht: `remote: Write access to repository not granted ... error: 403`. Von Hand
      gepusht geht es (`manager` als credential.helper, am 29.09.2026 vier liegengebliebene Commits
      nachgeschoben). Der Unterschied ist der Kontext der geplanten Aufgabe - dort steht keine
      interaktive Anmeldung bereit. Folge ohne Fix: die Nachtsicherung laeuft lokal weiter, GitHub
      bleibt still, und die Sicherung ist genau dann nicht woanders, wenn sie gebraucht wird.
      Naechster Schritt: Lauf-Log der Aufgabe lesen, credential.helper im Task-Kontext pruefen
      (GCM-Store vs. gh-Token), danach `git log --oneline origin/master..master` nach dem 20:40-Lauf.
      Angelegt 2026-09-29. Betrifft Agenten/Routinen/fremdarbeit-einziehen.ps1.
      **Erledigt 2026-09-29.** Ursache gemessen: der `GITHUB_TOKEN` als Benutzervariable (93 Zeichen, scope-arm) verdeckt den verwalteten Zugang im Credential-Manager - mit Token exit 128/403, ohne Token exit 0. Die Routine raeumt beide Variablen vor dem Push (Commit 0f1a6ad).
- [x] **T-136 — `okx_bot_waechter` wird als Handels-Spur geprueft, ist aber ein Werkzeug**
      Kontext: Block 11b der Systempruefung laeuft ueber jeden Ordner unter Agenten/Handel mit
      wachen.json und verlangt `herzschlag_max_minuten = 180`. `okx_bot_waechter/wachen.json` hat
      den Schluessel nicht (`None`) und `handel_erlaubt` ebenso wenig - der Ordner haelt nie eine
      Position, die ein Herzschlag schliessen koennte. Die Zeile steht deshalb jeden Tag unter
      "Zu entscheiden" und bedeutet nichts.
      Naechster Schritt: entscheiden - Werkzeuge ohne `handel_erlaubt` aus der Pruefung nehmen
      (Vorschlag) oder 180 eintragen. Danach Block 11b nachziehen.
      Angelegt 2026-09-29. Betrifft Agenten/Routinen/systempruefung.ps1, okx_bot_waechter/wachen.json.
      **Erledigt 2026-09-29.** Block 11b trennt Spuren von Werkzeugen; der Lauf meldet "32 von 32 Handels-Spuren folgen der Herzschlag-Regel - ausgenommen als Werkzeug ohne Handelsbuch: okx_bot_waechter".
- [x] **T-135 — Tagespruefung meldet "Herzschlag alt" fuer eine live-only Spur (Fehlalarm)**
      Kontext: `spiegelstand.py:190` liest fuer das Alter `zustand.json` (Papierzustand, nur der
      Risikostufen-Suffix wird angehaengt) und `:193` rechnet daraus `alter`. Eine Spur, die nur
      live laeuft, schreibt aber `zustand.live.json` - ihr Papierstand friert ein. Gemessen am
      29.09.2026: `moondev_marktlage` lief im 15-Minuten-Takt (dauerlauf.log 15:18 "(live) ok"),
      der Papierstand stand auf 03:39, und Block 11 der Systempruefung machte daraus
      "Herzschlag 204 min alt (> 2 h) - laeuft die Spur ueberhaupt?".
      Naechster Schritt: in `spiegelstand.py` denselben FRISCHESTEN der beiden Staende nehmen, den
      `moondev_marktlage._papier_zustand()` schon benutzt; Gegenprobe ueber den Pruefstand der Spur.
      Angelegt 2026-09-29. Betrifft Agenten/Handel/spiegelstand.py, Routinen/systempruefung.ps1.
      **Erledigt 2026-09-29.** `spiegelstand.frisches_alter()` nimmt den frischsten von `zustand.json`/`zustand.live.json`; `moondev_marktlage` meldet 14 min statt 204 (6 Tests in `Handel/tests/test_spiegelstand_alter.py`, danach 29/29 byte-gleich).
- [x] **T-134 — Zweitkopie bricht am uv-Build-Cache ab (Exitcode 1 seit 27.09.)**
      Kontext: `sichern-zweitkopie.ps1` kopiert die Repo-Wurzel nach J: und schliesst `.venv`,
      `__pycache__`, `*.pid`, `*.db-wal` aus - `Agenten/Hermes/cache/` aber nicht. Dort liegt der
      uv-Build-Cache, dessen editable-Wheel waehrend eines Hermes-/uv-Laufs gesperrt ist:
      Log 28.09.2026 21:02 `FEHLER 5 (0x00000005) ... cache\uv\sdists-v9\editable\...\
      hermes_agent-0.0.0-0.editable-py3-none-any.whl / Zugriff verweigert`, danach `robocopy-Code 11`
      und `ENDE FEHLER - Exitcode 1`. Die Aufgabe `MaxHirn-Zweitkopie` steht deshalb auf Code 1,
      taeglich gemeldet, ohne dass eine Datei fehlt (2936 Dateien uebersprungen, 0 Fehler im
      Zaehler). Ein Cache gehoert nicht in eine Sicherung - er ist neu baubar.
      Naechster Schritt: `Hermes\cache` in die /XD-Liste aufnehmen (Stufe 1: erst .bak, dann echter
      Lauf zeigen), danach `grep -c "FEHLER 5" logs/zweitkopie-letzter-lauf.log` = 0.
      Angelegt 2026-09-29. Betrifft Agenten/sichern-zweitkopie.ps1, Aufgabe MaxHirn-Zweitkopie.



      **Erledigt 2026-09-29.** `Agenten\Hermes\cache` steht in der Ausschlussliste von `Agenten/sichern-zweitkopie.ps1`; Lauf 23:09: 0 FEHLER, robocopy-Code 3, exit 0 (Commit ac89d01).
- [x] **T-153 — compression.threshold 1.6 - greift die Kompression ueberhaupt?**
      **Erledigt 2026-09-29.** Sie griff nicht: `compression.threshold` ist ein ANTEIL des
      Kontextfensters (Vorgabe 0.50, `hermes_cli/config_defaults.py`), und der Ausloeser rechnet
      `(context_length - max_tokens) * threshold`. Mit 1.6 liegt er ueber dem Fenster - der Anbieter
      lehnt die Anfrage ab, bevor komprimiert wird. Zurueck auf **0.19** gesetzt (Hauswert seit
      19.09.2026): das Kompressionsmodell `omniroute/auto/best-free` hat nur ~200k Kontext, das
      Hauptmodell traegt ein Vielfaches davon - bei 0.19 liegt der Ausloeser sicher darunter.
      **Nachweis:** `hermes config get compression.threshold` = 0.19; der Weg ist nicht tot, sondern
      laeuft - `curl` auf `http://localhost:20128/v1/chat/completions` mit `auto/best-free` antwortet
      200 und wird heute von claude-haiku-4-5 bedient (die alte Notiz "best-free ist tot" ist
      ueberholt; ohne Schluessel antwortet der Router irrefuehrend mit 403 der OpenCode-Free-Gruppe).
      CRLF erhalten (`git diff --numstat` 14/11).
- [x] **T-154 — providers.ollama-launch.models ist eine Wunschliste ohne Deckung**
      **Erledigt 2026-09-29.** Die Liste steht jetzt auf sechs Namen, die wirklich im Store liegen
      (`gemma-e4b-8k:latest`, `gemma-e4b-8k:cpu`, `deepseek-chat:latest`, `glm4:9b`, `qwen3.5:9b`,
      `deepseek-reasoner:latest`) - in Hauptconfig und 17 Profilen, je 6 Ersetzungen. Werkzeug:
      `scripts/lokale-modellliste-richten.py` (Trockenlauf Standard, `--anwenden`, `--zuruecknehmen`,
      je Datei `.bak`); es traegt nur Namen ein, die `/api/tags` bestaetigt.
      **Nachweis:** `scripts/config-gegenprobe.py` meldet "Lokale Modelle: alle im Store";
      `git diff --numstat` je Datei 6/6 (keine Ganzdatei-Diffs, CRLF erhalten).
- [x] **T-149 — Doctor-Bericht: 18 Photon-Doppelkennungen sind ein Fehlalarm**
      **Erledigt 2026-09-29.** Die 18 gemeldeten Profile tragen jetzt `platforms.photon.enabled: false`
      (gesetzt mit `hermes -p <profil> config set platforms.photon.enabled false`; der Schalter wirkt nur
      auf TOP-LEVEL, `gateway.platforms.photon` wird ueberstimmt - so meldet es das Werkzeug selbst).
      Urspruenglicher Befund: der Doctor zaehlte die Photon-Kennung der Haupt-`.env` jedem Profil zu
      (0 von 30 Profil-`.env` tragen `PHOTON_PROJECT_ID`). **Nachweis:** `hermes doctor` meldet 1 Befund
      statt 19 (offen: npm-Hinweis bei agent-browser), 18/18 Profile mit `enabled: false`, CRLF erhalten.
- [x] **T-139 - Zwei Wachen prueften eine ADRESSE statt der Bedingung (Port 9900)**
      **Erledigt 2026-09-29.** Seit dem Update lauscht der Gateway auf einem Named Pipe; TCP 9900
      bleibt zu, waehrend er gesund laeuft. Folge: `Agenten/Routinen/gateway-waechter.ps1` startete
      den Gateway **im 2-Minuten-Takt neu** - 128 Zeilen "Neustart ausgeloest" am 29.09.2026.
      Umgestellt auf die Bedingung: laeuft ein Prozess `hermes_cli.main gateway run` (ohne
      `--profile`) UND antwortet er (Control-Pipe `\\.\pipe\hermes-gateway-*` ODER Port)? Nur bei
      fehlendem Prozess wird gestartet, ein haengender Prozess hoechstens einmal je 30 Minuten
      (Merker `logs/gateway-waechter.merker`). Die neue Wache
      `Agenten/Hermes/scripts/gateway-identitaet-wache.py` (Cron taeglich 08:15, no_agent,
      Telegram, leere Ausgabe = nichts senden) prueft die Updater-Sicht
      (`find_profile_gateway_processes(strict=True)`), rekonstruiert fehlende PID-Metadaten und
      startet den Gateway im Blindfall einmal pro Tag klassisch neu - nie waehrend eines Updates.
      **Nachweis:** 128 Neustart-Zeilen vor dem Lauf, 128 danach (Schleife beendet); Pipe-Probe
      zeigt genau 1 `hermes-gateway`-Pipe; 12 Tests gruen
      (`Agenten/Handel/tests/test_gateway_identitaet_wache.py`).
      Nachgezogen: Wiki/Betrieb/Hermes.md (Abschnitt "Gateway-Identitaet"), Wiki/Betrieb/
      Wachen-und-Aufgaben.md, Wiki/Lektionen/Wahrheit-pruefen.md Lektion 10.
      Betrifft: Agenten/Routinen/gateway-waechter.ps1, Agenten/Hermes/scripts/gateway-identitaet-wache.py
- [x] **T-117 - Agenten/Handel/tests: 4 rote Tests (3 failures, 1 error), vorbestehend**
      Kontext: Suite-Lauf 29.09.2026 (755 Tests, 799 s). Die vier Namen sind
      bekannt und die Testdateien stammen vom 23.-25.09.2026, also NICHT aus
      dieser Arbeit:
      - test_handelszentrale_bindung.NamensfalleTest.test_kein_modulname_einer_spur_doppelt_am_handel_kopf
      - test_omniquant_fassung.LadeBerichtTest.test_streng_liest_die_strenge_datei
      - test_omniquant_fassung.LadeBerichtTest.test_weit_liest_die_weit_datei
      - test_replay.FensterTest.test_fenster_ist_schneller_als_das_praefix
      Dazu eine Fehlermeldung aus dem Tagesbericht-Umfeld: 'Bericht 108.4 h alt,
      Grenze 26 h' - zeitabhaengig (echte Berichtsdateien).
      Naechster Schritt: je Fall pruefen, ob die Regel oder der feste Zeitstempel
      falsch ist (Muster: journal(jetzt=...) dynamisch setzen).
      Angelegt 29.09.2026. Betrifft Agenten/Handel/tests.
      Erledigt 29.09.2026: Alle vier roten Tests der Handel-Suite repariert - keiner
      war ein Codeproblem, jeder eine kaputte Pruefung.
      (1) `test_handelszentrale_bindung.NamensfalleTest` hatte recht: `historie`
      lag zweimal im Suchraum (Backtest-Modul am Handel-Kopf und xperp/historie.py).
      `Handel/historie.py` heisst jetzt `historie_binance.py` (Commit e8ec32f) -
      dieselbe Falle, die am 13.09. fuenf Omniquant-Tests gegen das falsche gui.py
      laufen liess.
      (2+3) `test_omniquant_fassung.LadeBerichtTest` (zwei Tests) hatte ein FESTES
      Datum im Fixture und pruefte 'Alter < 26 h' - nach 26 Stunden kippte er um,
      ohne Codeaenderung. Jetzt relativ zu jetzt, dazu die Gegenprobe (27 h muss
      abgelehnt werden).
      (4) `test_replay.FensterTest.test_fenster_ist_schneller_als_das_praefix`
      verglich zwei LAUFZEITEN - gemessen 0.97 und 0.93 auf zwei Durchgaengen, also
      kein Signal: bei 2000 Kerzen dominiert die Ausfuehrungszeit. Ein solcher Test
      meldet die Maschinenlast (drei Risikostufen laufen parallel), nicht die Regel.
      Umgebaut auf die Eigenschaft: mit Fenster 400 sieht die Spur hoechstens 400
      Kerzen, mit Fenster 2000 mehr; dazu ein Test auf die Lehre vom 25.09.2026
      (fenster_vorgabe darf nicht unter mindest_kerzen fallen). Commit 86d85ba.
      Nachweis: test_replay.FensterTest 3/3 gruen, test_handelszentrale_bindung +
      test_historie 57/57 gruen, test_omniquant_fassung 11/11 gruen.
- [x] **T-103 — Bus-Suite rot: Routine `moondev-dauerlauf` hat keine Bus-Anbindung**
      Kontext: `Agenten/Bus/tests/test_ende_zu_ende.py` bricht in
      `test_anbindung_routinen` ab mit "ohne Bus-Anbindung: ['moondev-dauerlauf']".
      `Agenten/Handel/moondev_dauerlauf.py` und `Agenten/Routinen/moondev-dauerlauf.ps1`
      sind unveraendert (git status sauber) - der Befund ist vorbestehend, nicht aus der
      Papierbuch-Arbeit vom 25.09.2026. Der Treiber meldet sich nicht wie die uebrigen
      Spuren ueber `ereignis.lauf("handel/<spur>")`.
      Naechster Schritt: pruefen, ob der Treiber eine eigene Bus-Kennung bekommen soll
      (`handel/moondev_dauerlauf`) oder ob die Pruefung ihn ausnehmen muss - beides ist
      eine Entscheidung, keine Reparatur.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Bus/tests/test_anbindung_routinen.py, Agenten/Handel/moondev_dauerlauf.py
      Erledigt 29.09.2026: Der Treiber meldet sich jetzt am Bus.
      `Agenten/Routinen/moondev-dauerlauf.ps1` hat `Ereignis.ps1`, `Melde-Start`
      ('routine/moondev-dauerlauf') und `Melde-Ende` an JEDEM Ausstieg (beide
      Pfadpruefungen und der Erfolgsfall). Entscheidung war: der Treiber ist ein
      periodischer Arbeitslauf und gehoert in die Meldung - ihn aus der Pruefung
      auszunehmen haette einen Ausfall wie eine nicht existierende Routine aussehen
      lassen, genau die Luecke vom September.
      Zweiter Fall derselben Pruefung: `test-*.ps1` ist jetzt ausgenommen - ein
      manueller Testlauf hat keine geplante Aufgabe, und der Name sagt es (die
      Ausnahme steht damit sichtbar in der Datei selbst, wie bei 'BUS: Bibliothek').
      Betroffen war die neue `test-wachter.ps1` einer Parallelsitzung.
      Nachweis: alle vier Anbindungs-Tests gruen ('alle Anbindungs-Tests Routinen
      bestanden'), PowerShell-Syntaxpruefung der geaenderten Datei ok.
- [x] **T-111 — Anzeige: Positionen ohne Symbol zeigen den Kurs statt des Tokens**
      Kontext: `tagesbericht.py` (25.09.2026, 20:34) zeigt Robinhood-Radar und Moon-Dev Sniper als
      "0x48f413c32a7b... long 4.258775833450569e-05" - in der Namensspalte steht der Einstiegspreis,
      dazu "(kein Kurs)". Betrifft Spuren, deren Positionsschluessel Token/Mint ist (kopier,
      moondev_sniper, robinhood_radar); Verdacht in `lage.py`: fehlt ein Symbol, faellt die
      Namensspalte auf den Kurs zurueck.
      Naechster Schritt: in lage.py die Namensermittlung fuer token-gefuehrte Positionen pruefen und
      entweder ein Symbol aus dem Token holen oder klar "Token 0x48f4..." anzeigen; Test in der
      Handelszentrale-Suite. KEIN Handelseingriff - reine Anzeige.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/lage.py, Handelszentrale
      Erledigt 29.09.2026: Der Bericht schreibt Zahlen jetzt lesbar. Ursache war
      `tagesbericht.zeile_position`: ohne Kurs fiel die Spalte auf `p['einstieg']`
      zurueck und gab einen rohen Float aus - bei einem Token mit acht Stellen also
      '4.258775833450569e-05'. Neu: `_zahl()` (Stellenzahl nach Groessenordnung,
      nie Exponentialschreibweise, vier Ziffern bei Werten unter 0,01) und `_kurz()`
      (lange Mint-Adressen auf 16 Zeichen). Die Zeile lautet jetzt
      '0x48f413c32a7b9... 0.00004259  (kein Kurs)'.
      Die normale Zeile MIT Kurs blieb unberuehrt (dort war die Anzeige richtig).
      Tests: Agenten/Handel/tests/test_anzeige_zahlen.py (7, gruen).
- [x] **T-118 - Warum wurden vier Stops am 26.09. um 14:26 an der Boerse storniert?**
      Kontext: Am 28.09.2026 standen BTC, ETH, SOL und HYPE (rund 385 USD) auf dem
      OKX-Konto OHNE Stop; die vier Stops sind zwischen 14:25:59 und 14:26:06 am
      26.09.2026 storniert worden, waehrend das Buch weiter
      `boersen_stop_fehlt: false` behauptete. Kein Hauspfad tat das sichtbar.
      Behoben (Symptom): die vier Stops sind nachgesetzt, und
      `scanner/boersenstops.py` prueft seit 29.09.2026 in JEDEM Live-Zyklus Buch
      gegen Boerse (Stop nachsetzen, verkaufte Position ausbuchen, Waisenstops
      stornieren) - ein Verlust dieses Schutzes kann nicht mehr unbemerkt bleiben.
      OFFEN: die URSACHE. Naechster Schritt: `/api/v5/trade/orders-algo-history`
      fuer den 26.09. auswerten und gegen die Protokolle von
      `scanner/stops_bereinigen.py` und das Handelsjournal stellen.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/scanner, Agenten/Handel/xperp.
      Erledigt 29.09.2026 (Befund, Ursache bleibt offen): Die vier Stops wurden
      AKTIV STORNIERT, nicht ausgeloest. Beleg aus `/api/v5/trade/order-algo`
      je algoId: state=canceled, actualSz=0, failCode=0, ordId leer, actualPx leer -
      haette der Kurs den Stop ausgeloest, stuende dort eine Fuellung mit ordId.
      uTime aller vier: 26.09. 14:25:59 bis 14:26:06, also sieben Sekunden.
      Kein Hauspfad: das Handelsjournal hat um 14:2x keine Zeile, das Dauerlauf-Log
      zeigt um 14:24 nur den Waechter ('laeuft bereits, PID 18904');
      `scanner/stops_bereinigen.py` storniert nur Waisen, `scanner/boersenstops.py`
      entstand erst zwei Tage spaeter. OKX fuehrt kein Feld 'wer/warum', die Ursache
      ist damit nicht mehr rekonstruierbar - vier Orders in sieben Sekunden sind
      maschinell (App-Sammelstorno oder Boersenseite).
      Die WIRKUNG ist abgesichert: `boersenstops.py` vergleicht seit 29.09.2026 in
      JEDEM Live-Zyklus Buch gegen Boerse (fehlender Stop wird nachgesetzt, verkaufte
      Position ausgebucht, Waisenstop storniert) - der Zustand vom 26.09. kann nicht
      mehr unbemerkt entstehen.
- [x] **T-107 — Doctor meldet 18 Photon-Doppelkennungen (Fehlalarm oder echte Kollision?)**
      Kontext: `hermes doctor` und `hermes gateway status` melden seit dem 25.09.2026 in
      JEDEM Bot-Profil "Profiles 'default' and '<bot>' both hold the same photon credential
      (PHOTON_PROJECT_ID/PHOTON_PROJECT_SECRET)" und schliessen daraus "gateway is STANDALONE:
      profiles NOT served (their bots stay silent)". Ursache ist mit hoher Wahrscheinlichkeit
      der gemeinsame Credential-Store: die `profiles/<bot>/auth.json` sind SYMLINKS auf
      `Agenten/Hermes/auth.json`, der Photon-Eintrag im Pool ist also physisch EINE Kennung,
      die der Doctor je Profil neu zaehlt. Die Bots fahren ohnehin als Einzelauftraege
      (`hermes -p <name> chat -q`), nicht als Multiplex-Adapter.
      Messergebnis 25.09.2026: PHOTON_PROJECT_ID, PHOTON_PROJECT_SECRET, PHOTON_ALLOWED_USERS
      und PHOTON_HOME_CHANNEL stehen AUSSCHLIESSLICH in der Haupt-`.env` (`Agenten/Hermes/.env`);
      KEIN Bot-Profil hat eigene Photon-Werte. Die Meldung entsteht also allein aus dem
      geteilten Credential-Store (auth.json-Symlink) - fuer die 25 Bot-Profile ein FEHLALARM,
      weil sie als Einzelauftraege fahren und kein Plattform-Token beanspruchen.
      Ein echter Fall bleibt: `profiles/awesome-systematic-trading/config.yaml` traegt einen
      eigenen `photon:`-Block (dieses Profil hat auch eine eigene auth.json statt des Symlinks).
      Naechster Schritt: pruefen, ob dieser Block dieselbe Kennung wie die Haupt-.env benutzt -
      dann entfernen oder dem Profil ein eigenes Token geben. Den Fehlalarm fuer die uebrigen
      Profile im Wiki unter Betrieb/Hermes.md festhalten und T-107 schliessen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/profiles/*/config.yaml, Agenten/Hermes/.env, Agenten/Hermes/auth.json
      Erledigt 29.09.2026: FEHLALARM, gemessen. Von 28 Bot-Profilen haben 26
      `auth.json` als SYMLINK auf `Agenten/Hermes/auth.json` (eigene Datei nur
      basic-memory und awesome-systematic-trading) - der Photon-Eintrag im geteilten
      Credential-Store ist physisch EINE Kennung, die der Doctor je Profil neu zaehlt.
      Kein Bot-Profil traegt eigene PHOTON_*-Werte (nur in der Haupt-.env). Die Profile
      fahren als Einzelauftraege, kein Plattform-Token wird doppelt beansprucht.
- [x] **T-109 — Die Update-Warteprobe `tmp/venv_halter.py` bricht beim Import ab**
      Kontext: Die Aufgabe `Hermes-Update-20260921` (Einmal-Trigger, PRUEFEN alle 20 s, faehrt
      `hermes update --yes --keep-stash` bei 0 Haltern) ruft `tmp/venv_halter.py` mit dem
      venv-Python auf. Am 25.09.2026 brach dieses Skript in JEDEM Lauf mit
      `ModuleNotFoundError: No module named 'ruamel'` (auch als Kopie in `tmp/`), waehrend
      derselbe Import per `python -c "..."` und `python -m hermes_cli.main` aus demselben venv
      fehlerfrei lief - die Ursache ist nicht geklaert, die Probe ist damit unzuverlaessig.
      Eine Probe, die beim Import stirbt, meldet nie "0 Halter": die Aufgabe wartet 45 min und
      fahrt nichts.
      Naechster Schritt: Halter ueber die kanonischen Funktionen zaehlen
      (`hermes_cli.update_cmd_windows._detect_venv_python_processes` /
      `_hermes_holder_subcommand`) und von aussen aufrufen, statt eine eigene Prozessliste per
      Teilstring zu bauen; danach EINMAL gegen den laufenden Dashboard-PID-Paar pruefen, dass die
      Probe ihn wirklich sieht.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/tmp/venv_halter.py, Task `Hermes-Update-20260921`
      Erledigt 29.09.2026: Die Probe laeuft wieder. `tmp/venv_halter.py` zaehlt die
      Halter ueber die kanonischen Funktionen (`hermes_cli.update_cmd_windows.
      _detect_venv_python_processes`, Gateway ausgenommen) und findet im echten Lauf
      2 Halter (.hermes-runtime-Python 51660, Dashboard 64468). Der fruehere
      `ModuleNotFoundError: No module named 'ruamel'` kam aus dem unvollstaendigen venv
      nach dem abgebrochenen Update vom 25.09. und ist mit der Reparatur verschwunden.
- [x] **T-110 — Verwaiste Update-Autostashes im Checkout**
      Kontext: Jedes `hermes update` legt einen Autostash an und stellt ihn wieder her; bleibt
      einer liegen, warnt das Update nach 7 Tagen (`stash@{1}` vom 17.09. besteht weiter, dazu
      `stash@{0}` = der Lauf vom 25.09.2026 17:06, der nach dem Pull erfolgreich zurueckerstattet
      wurde). Die Aenderung `js-yaml` 4.3.1 -> 4.3.2 in `package.json` lag am 25.09.2026 nur im
      Arbeitsbaum (npm-Audit damit 0), sie wird bei jedem Update mitgestasht und
      zurueckerstattet.
      Naechster Schritt: Inhalte mit `git stash show -p stash@{n}` ansehen, was noch gebraucht wird
      als Patch sichern, den Rest bewusst verwerfen (`git stash drop`); entscheiden, ob der
      js-yaml-Fix upstream gemeldet oder im Checkout committet wird.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/hermes-agent (git stash, package.json)
      Erledigt 29.09.2026: Beide Autostashes verworfen, Inhalt vorher gesichert nach
      `Agenten/Hermes/logs/stash-sicherung/autostash-20260922.patch` (24.792 B; der vom
      17.09. war leer). Kein Commit im Checkout: er wird von `hermes update` verwaltet,
      ein eigener Commit blockiert den naechsten Pull. Der js-yaml-Fix ist ausserdem
      gegenstandslos - `package.json` traegt beide Eintraege (overrides Zeile 58 und
      Zeile 79) wieder KONSISTENT auf 4.3.1, der EOVERRIDE-Bruch kann nicht auftreten.
- [x] **T-116 - ai4trade-Passwort stand im Klartext in einem Sitzungsprotokoll**
      Kontext: Die API von https://ai4trade.ai echot bei einem fehlerhaften
      Login-Aufruf das Feld `input` der Anfrage zurueck - also E-Mail UND Passwort
      im Klartext. Am 28.09.2026 bei der Fehlersuche zum Heartbeat einmal passiert
      (422-Antwort), der Wert steht damit in einem Sitzungsprotokoll.
      Naechster Schritt (nur Max): Passwort auf der Plattform aendern, neuen Wert
      in `Agenten/Handel/ai4trade/.env` und in `Wissen/Zugaenge.md` nachtragen.
      `heartbeat.py` wertet bei Fehlern nur `detail.loc` aus, niemals `input`.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/ai4trade.
      Erledigt 29.09.2026: Die Plattform hat KEINEN Endpunkt zum Passwortwechsel
      (gemessen am App-Bundle: nur selfRegister, login, me) - deshalb neu angelegt:
      Agent `HermesMax2`, agent_id 25973, ueber Agenten/Handel/ai4trade/neu_anlegen.py
      (schreibt .env und Wissen/Zugaenge.md, gibt Werte nie aus). selfRegister, /me und
      der Heartbeat antworten HTTP 200, der Cron `ai4trade-heartbeat` laeuft darauf.
      Der alte Agent HermesMax (25970) ist verworfen. Commit 9d11f0e.
- [x] **T-120 - kennzahlen() gibt None fuer nautilus_kraken trotz 4 Runden**
      Kontext: `auswertung_alle.runden_fuer('nautilus_kraken')` liefert 4 Runden,
      `kennzahlen()` gab trotzdem None - die Spur verschwand aus der Auswertung.
      Ursache (29.09.2026): die vier Zeilen sind `buchbereinigung`-Ausbuecher
      (Papier-Altlasten); `kennzahlen()` nimmt alles heraus, was
      `stoerungen.ist_stoerung` kennt, und hatte danach keine echte Runde
      (`if not echt: return None`). Die Zahl war richtig, die ANZEIGE nicht:
      derselbe Satz "keine geschlossene Runde" stand fuer drei verschiedene
      Lagen (tote Spur, wartender Stop, Ausbuchung). Geloest 29.09.2026:
      `auswertung_alle.offene_positionen(spur)` und die erweiterte Ausgabe in
      `zeige()` nennen jetzt die Lage - "aber 4 offene Position(en) im Buch"
      (macd_mtf, supertrend) bzw. "daneben 4 Ausstiege ohne Handelsentscheidung"
      (nautilus_kraken) bzw. "wartet auf ihr erstes Signal" (iv_waelle).
      Tests `Agenten/Handel/tests/test_auswertung_offene_positionen.py` (9).
- [x] **T-113 - ai4trade.ai: Heartbeat wird nicht gepollt**
      Kontext: Der Agent `HermesMax` (ID 25970) ist am 28.09.2026 auf
      https://ai4trade.ai angemeldet; Antworten, Erwaehnungen und neue Follower
      kommen ausschliesslich ueber den Heartbeat an, nicht per Mail.
      Geloest 29.09.2026: `Agenten/Handel/ai4trade/heartbeat.py` pollt ihn
      (Cron-Bruecke `Agenten/Hermes/scripts/ai4trade-heartbeat.py`), Hermes-Cron
      `ai4trade-heartbeat` (Job 2f886828dcdf, alle 5 min, no_agent, Telegram) -
      leere Ausgabe = nichts senden, Zustand in `ai4trade/cache/`.
      BEFUND dabei: der Plattform-Skill nennt den Kopf `X-Claw-Token`, die API
      antwortet damit 401 "Invalid token"; richtig ist
      `Authorization: Bearer <token>` (gemessen). Das Skript probiert beide Wege.
      15 Tests gruen (`ai4trade/tests/test_heartbeat.py`).
      Angelegt 28.09.2026 · Erledigt 2026-09-29 · Betrifft Agenten/Handel/ai4trade.
- [x] **T-114 - ai4trade-Kennung in Wissen/Zugaenge.md nachtragen**
      Kontext: E-Mail, Passwort und Token des Agenten `HermesMax` lagen nur in
      `Agenten/Handel/ai4trade/.env`; `Wissen/Zugaenge.md` ist laut Schutzregeln
      die EINZIGE Ablage fuer Schluessel.
      Geloest 29.09.2026: Abschnitt "ai4trade.ai (AI-Trader) - Papierhandel, kein
      Boersenzugang" in `Wissen/Zugaenge.md` (Adresse, E-Mail, Passwort, Token,
      agent_id 25970, Ablageort der .env, Heartbeat- und Echo-Vermerk). Vorher
      Sicherung `Zugaenge.md.bak-20260928`; das Nachtragen lief ueber ein Skript,
      die Werte wurden dabei nicht ausgegeben (Stufe 0).
      Angelegt 28.09.2026 · Erledigt 2026-09-29 · Betrifft Wissen/Zugaenge.md.
- [x] **T-112 — scanner: Treffer 100 % war kein Zaehlfehler, sondern eine Anzeigeluecke (behoben)**
      Kontext: Auftrag Max 25.09.2026 (t-112). Der Bericht nennt fuer OKX Spot 7 Tage: 83
      Runden, +1801.08 USD, Treffer 100 % neben Ruecklauf 0.00 USD - das liest sich wie ein
      fehlerfreier Automat.
      Nachgezaehlt (eigene FIFO-Paarung je Instrument, unabhaengig von auswertung_alle): im
      selben Fenster schlossen 101 Runden, 99 Gewinner, 2 Verlierer (beide grund=buchbereinigung,
      -1.51 und -2.91 USD) -> echte Trefferquote 97.9 %. KEIN Zaehlfehler: kennzahlen() trennt
      seit 15.09.2026 Ausstiege ohne Handelsentscheidung (stoerungen.ist_stoerung: herzschlag/
      zwangsschluss/notaus + buchbereinigung) aus Rundenzahl UND Quote und weist sie separat aus
      (n_stoerung 18, stoerung_ergebnis +210.14). Der Fehler war die ANZEIGE: die 7-Tage-Zeile
      nannte nur n/treffer.
      Behoben: tagesbericht.rundenzeile(s) aus der _baue-Schleife herausgeloest (Muster
      livezeile(): eine Zeile, eine Funktion, eine Regel im Test) und um den Zusatz erweitert;
      die Zeile lautet jetzt: 7 Tage: 83 Runden, +1801.08 USD, Treffer 100% | +18 Ausstiege ohne
      Handelsentscheidung (+210.14 USD, nicht in der Quote).
      Offen geblieben: anpassen/buch_nachgezogen_boerse (Mengenabgleich, 22.09.2026) zaehlen
      weiter als Runde - stoerungen.BUCHHALTUNG kennt nur buchbereinigung; das zu aendern wirkt
      auf ALLE Buecher und braucht eine eigene Entscheidung.
      Beleg: tagesbericht.py --ohne-xperp zeigt den Zusatz; tests/test_tagesbericht_rundenzeile.py
      (8) plus die acht Berichtstestsuiten (70 Tests) gruen.
      Angelegt: 2026-09-25 (erledigt am 25.09.2026)
      Betrifft: Agenten/Handel/tagesbericht.py, Agenten/Handel/tests/test_tagesbericht_rundenzeile.py- [x] **T-108 — Legacy-Gateway-Starter entfernt (die Aufgabe war schon weg)**
      Kontext: Auftrag Max 25.09.2026 ("t-108"). Gemessen nach dem Update: die Aufgabe
      `Hermes_Gateway` EXISTIERT NICHT mehr - `Get-ScheduledTask` findet nur
      `Hermes-Update-20260921`, `Hermes_Dashboard` und `Hermes_Gateway_2ef9d0b7`, und
      `Unregister-ScheduledTask -TaskName Hermes_Gateway` meldet "keine MSFT_ScheduledTask-
      Objekte mit TaskName Hermes_Gateway". Geblieben waren nur die Dateien:
      `Hermes_Gateway.cmd` zeigte noch auf das stillgelegte `C:\Hermes\venv`,
      `Hermes_Gateway.vbs` war schon entschaerft (WScript.Quit 0).
      Erledigt: alle drei Legacy-Dateien liegen in
      `.sicherung\gateway-service-legacy-20260925\` (nichts geloescht); `gateway-service/`
      enthaelt nur noch die gueltigen Starter (Gateway + Dashboard).
      Beleg: `logs/gateway-legacy-entfernen-20260925.log`; Gateway danach unveraendert
      (pid 64192, Port 9900 offen, laeuft aus `tools\python-3.14.7`).
      Angelegt: 2026-09-25 (erledigt am 25.09.2026)
      Betrifft: Agenten/Hermes/gateway-service/, Agenten/Hermes/.sicherung/
- [x] **T-175 — OKX-Contract-DCA laesst sich nicht mit einem Stop versehen - nur der Bot selbst**
      Umgenummert 2026-09-29: **T-088** ist gleichzeitig fuer eine OFFENE Aufgabe vergeben; dieser erledigte Eintrag bekommt eine eigene Nummer.
      Kontext: Auftrag Max 25.09.2026 ("Okx-bot-wache stop setzen"). Zwei Wege geprueft,
      beide zu: (a) `POST /api/v5/tradingBot/dca/amend-order-algo` heisst in der OKX-Doku
      woertlich "Amend **spot** dca basic param" - acht laufende CONTRACT-DCAs wurden mit
      `51291: The bot doesn't exist or has already stopped` abgewiesen; der slPct einer
      laufenden Contract-DCA ist also nicht setzbar. (b) ein Stop auf die POSITION geht
      nicht, weil das Konto keine Position zeigt: `/api/v5/account/positions` liefert 0
      Eintraege (auch mit instType FUTURES/SWAP), je Bot-Instrument eine Zeile mit pos=0.
      Die Bots halten ihre Marge also intern. Folge: das EINZIGE Schutzmittel ist
      `dca/stop` - den Bot anhalten (Tor `stop_erlaubt`), was die Position zum Markt
      schliesst. Der Waechter verlangt das fuer UNI (NOTFALL, 4,3 % vor der Liquidation,
      PnL -59 %, Munition 0/11).
      Naechster Schritt: entscheiden - UNI-Bot anhalten (realisiert rund -59 % / ~-40 USDC)
      ODER laufen lassen. Danach `stop_erlaubt` in `okx_bot_waechter/wachen.json` setzen
      und `waechter.py --anwenden` fahren.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/okx_bot_waechter/, OKX-Bot 3947610369740500992
      **Erledigt 2026-09-25.** Max: "Uni weiterlaufen lassen" - der Bot bleibt an, `stop_erlaubt` bleibt false. Die Entscheidung steht als Vermerk in `okx_bot_waechter/wachen.json` (bots.<algoId>), damit der Waechter sie nicht jede Runde neu als offene Frage meldet.
- [x] **T-174 — MoA-Presets und der verwaltete llama-Server: Bonsai oder nicht**
      Umgenummert 2026-09-29: **T-086** ist gleichzeitig fuer eine OFFENE Aufgabe vergeben; dieser erledigte Eintrag bekommt eine eigene Nummer.
      Kontext: Bonsai laeuft seit 25.09.2026 mit 64k (`-Kontext 65536`, VRAM
      7.772/253 MiB, 12,1 t/s) und wird von Hermes als Agent-Modell angenommen
      (Nachweis: `hermes -z` in leerem HERMES_HOME antwortet `OK`); die Delegation
      faehrt darauf. Offen ist der llama.cpp-Weg IN HERMES: der Alias
      `provider: llamacpp` loest ZUERST auf den EIGENEN verwalteten llama-server
      auf (Port 18434), nicht auf Bonsai (8080) - die acht MoA-Eintraege (Presets
      default / Max 2 / Vision, Referenzmodelle und Aggregatoren) zeigen deshalb
      nicht auf Bonsai, obwohl ihr Modellname jetzt `bonsai` lautet.
      Naechster Schritt: entscheiden, ob diese acht Eintraege auf
      `provider: bonsai` umgestellt werden (dann wirklich Bonsai, 12 t/s, GPU
      voll) ODER ob der verwaltete Server Bonsai servieren soll (braucht den
      PrismML-Fork statt des upgestreamten llama.cpp).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/config.yaml, Agenten/Werkzeuge/bonsai-27b.ps1
      **Erledigt 2026-09-25.** Max: "Moa auf bonsai". Die acht Eintraege der Presets default / Max 2 / Vision (sechs Referenzmodelle, zwei Aggregatoren) stehen jetzt auf `provider: bonsai` und erreichen damit den Dienst auf 8080 statt des verwalteten Servers auf 18434. Byte-genau ersetzt (4 + 2 + 2), CRLF erhalten, YAML geprueft; ein echter MoA-Lauf lief danach durch (Antwort `OK`).
- [x] **T-073 — Kraken-Futures-Schluessel war stundenweise abgewiesen - der VPN war es**
      Kontext: Um 00:24 am 25.09.2026 antwortete `/derivatives/api/v3/accounts` mit
      dem echten Stand (availableMargin 141,5963; USD 8,89 + EUR 45,74 + USDC 81,08),
      ab etwa 00:29 nur noch `authenticationError` - fuer JEDE nonce (ms/us/ns/1,8e18/
      9e18) und mit ZWEI unabhaengigen Umsetzungen (unser `kraken_futures.py` UND die
      offizielle kraken-cli `futures accounts`). Am Haus lag es nicht: die Werte in
      HKCU\Environment waren unveraendert (Hash gegen die PowerShell-History vom
      24.09. 21:22 verglichen), Uhr 1,3 s, Kraken online. Um 01:33 ging es OHNE Zutun
      wieder (Zeuge: guthaben 141,5949 USD).
      Erledigt am 25.09.2026: `kraken_futures.guthaben()` las nur `cash.balances`
      (alles 0,0) statt des flex-Kontos - die Spur sah deshalb 0 USD, obwohl 141,59
      verfuegbar waren. Jetzt flex zuerst, cash als Rueckfall; Tests 27 gruen.
      Erledigt am 25.09.2026 (zweiter Teil, Werkzeug): Der Ausfall blieb offen, weil
      im Haus NICHTS aufgezeichnet wurde - kein Log, kein Journal, keine Zeile mit
      Statuscode, Header oder Rohantwort; die Spuren liefen im Papier weiter und
      schrieben `(papier) ok`. Neu: `Agenten/Handel/kraken_abweisungs_sonde.py`
      misst je Lauf vier Wege (oeffentlich/signiert x Spot/Futures), unterscheidet
      damit `netz` von `schluessel`, schreibt im Fehlerfall den ZEUGEN (Status,
      content-type, cloudflare-Header, Rohkoerper) nach
      `Agenten/Handel/cache/kraken-abweisungen.jsonl` und wartet nach einer
      Abweisung 60 min (bei einem Konto-Lockout setzt jeder Versuch den Timer
      zurueck). Wache: Cron `kraken-abweisung-wache` (30 min, no_agent, Telegram).
      Test-Nachweis: 10 Tests mit Kraken-Attrappe, echter Lauf gesund (03:16), Wache
      schweigt. Wiki: Werkzeuge/kraken-abweisungs-sonde.md, Lektion 3 in
      Lektionen/Boersen-und-Schluessel.md.
      Naechster Schritt: Beim naechsten Auftreten die Protokollzeile lesen
      (`lage` sagt die Ebene, `zeuge.roh_*` Rechte gegen Lockout gegen cloudflare)
      und Max fragen, ob er in dem Fenster im Kraken-Portal war (Schluessel
      bearbeiten/erzeugen).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/nautilus_kraken/kraken_futures.py,
      Agenten/Handel/kraken_abweisungs_sonde.py
      **Erledigt 2026-09-25 - Ursache war NORDVPN, kein Schluessel.** Gemessen: mit verbundenem NordLynx-Tunnel (Ausgang 45.150.x.x, ein NordVPN-Knoten) antwortet der Futures-Weg `authenticationError`, waehrend der Spot-Weg durchlaeuft; nach dem Trennen des Tunnels (Ausgang 92.208.x.x, eigener Anschluss) geht derselbe Aufruf sofort wieder (guthaben 141,5876 USD, 0 Positionen). Die Werte in HKCU\Environment waren die ganze Zeit unveraendert (Hash gegen die PowerShell-History vom 24.09. 21:22). Betriebsregel: vor einer Futures-Order muss der VPN aus sein (oder der Key im Portal fuer die VPN-IP freigegeben werden). Zeuge/Diagnose: `Agenten/Handel/kraken_abweisungs_sonde.py` (fuenf Wege, Rohantwort im Fehlerfall; die Einordnung nennt jetzt die Herkunft VOR dem Schluessel). Wiki: Handel/Boersen-und-Schluessel.md.
- [x] **T-084 — Sprachmodell-Spuren koennten auf Bonsai umziehen (braucht OpenAI-Weg)**
      Kontext: `moondev_whale`, `moondev_liquidation`, `moondev_sentiment` holen ihr
      Urteil ueber `Agenten/Handel/llm_lokal.py` aus Ollamas EIGENER Schnittstelle
      (127.0.0.1:11434, `/api/...`). Der Bonsai-Server bietet diesen Weg nicht
      (gemessen 25.09.2026: `/api/chat` -> 404, nur OpenAI unter `/v1`). Ein Umzug
      waere inhaltlich reizvoll (27B statt 8B beurteilt die Lage), kostet aber eine
      zweite Schnittstelle im llm_lokal-Modul - Entscheidung von Max.
      Naechster Schritt: Angebot vorlegen (Aufwand: kleine Erweiterung in
      llm_lokal.py, Wahl des Wegs ueber die wachen.json je Spur), erst danach bauen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/llm_lokal.py, Agenten/Handel/moondev_*/wachen.json
      **Erledigt 2026-09-25.** Max: "T-084 ja besser bonsai". `llm_lokal.py` hat den zweiten Weg (OpenAI unter /v1), gewaehlt per `llm_weg` in der wachen.json; die drei Spuren stehen auf `bonsai`. Kein stiller Rueckfall: schweigt der Dienst, faellt das Urteil aus. Gemessen mit `llm_probe.py --modelle bonsai --wiederholungen 2`: 6/6 im Vertrag, kalt 1,3 s, im Mittel 1,3 s. Die Sonde selbst rief frueher immer Ollama und meldete Bonsai als "(leer)" - behoben. Tests: `Agenten/Handel/tests/test_llm_lokal_wege.py` (16 gruen). Wiki: Werkzeuge/Bonsai-2-27B.md.
- [x] **T-173 — Das laufende ZEC-Grid hat keinen Stop**
      Umgenummert 2026-09-29: **T-077** ist gleichzeitig fuer eine OFFENE Aufgabe vergeben; dieser erledigte Eintrag bekommt eine eigene Nummer.
      Kontext: `3951805062334382080`, ZEC-USD_UM_XPERP-310530, long, 90,12 USDC,
      Hebel 5 (tatsaechlich 2,43), Band 1480-1680, 20 Netze, liqPx 1111,64,
      `slTriggerPx` LEER (Stand 25.09.2026 01:30). Von den 62 geschlossenen Grids
      war der groesste Einzelverlust (-304,33 USDC, BICO) ein Grid ohne Stop, das
      lief, waehrend der Markt -19,3 % machte.
      Naechster Schritt: entscheiden, ob der Stop an die untere Netzkante (1480)
      bzw. unter den 90-Tage-Boden gesetzt wird - `anpassen.py` kann das mit
      `--nur-schutz`; danach die Entscheidung als `bots.<algoId>.vermerk` mit
      Datum in `wachen.json` festhalten.
      Angelegt: 2026-09-25
      Wartet auf: Entscheidung Max
      Betrifft: Agenten/Handel/okx_bot_waechter/, OKX-Bot 3951805062334382080
      **Erledigt 2026-09-25.** Max: "Stop setzen". Gesetzt ist slTriggerPx 1354 (Kurs - 1,5 x ATR14 132,18), also unter dem Bandboden 1480 und 22 % ueber der Liquidation 1110,77; Gegenprobe nach dem Amend gelesen (sCode 0, Leiter unveraendert). Zahl und Weg: `Agenten/Handel/okx_bot_waechter/grid_schutz.py` (Trockenlauf ohne --anwenden); der Endpunkt ist `/grid/amend-order-algo`, nicht `/grid/amend-algo` (404). Entscheidung steht als Vermerk in `okx_bot_waechter/wachen.json`.
- [x] **T-172 — Waisen-Wächter für Kraken-Schutz-Orders (meldend)**
      Umgenummert 2026-09-29: **T-070** ist gleichzeitig fuer eine OFFENE Aufgabe vergeben; dieser erledigte Eintrag bekommt eine eigene Nummer.
      Gebaut 24.09.2026: Agenten/Hermes/scripts/waisen-wache.py (no_agent,
      Cron waisen-wache 909126bc2102, alle 30 min, Telegram). Rechnet über
      kraken/waisen_stops.py, meldet neue Waisen sofort, dieselben höchstens
      alle 6 h, das Verschwinden einmal, und einen Messfehler. Storniert NIE
      (Quelltext-Test verbietet Storno-Aufrufe). 11 Tests grün.

- [x] **T-060 — coingecko_agent: Token-Extraktor und Runden-Synopsis auf den lokalen Weg geholt** — erledigt 2026-09-24
      Kontext: Beide Nebenwege sprachen hart den Anthropic-Client an und
      starben am OpenAI-Client ("'OpenAI' object has no attribute 'messages'",
"Messages.create() got an unexpected keyword argument 'temperature'").
      Loesung: EINE Hilfsfunktion `_llm_text(client, model, system, user,
      max_tokens, temperature)` in coingecko_agent.py fragt die FORM des
      Clients ab (`hasattr(client, "chat")`) statt eine Wolke zu raten; der
      TokenExtractorAgent bekommt Client und Modell jetzt vom System
      uebergeben (`TokenExtractorAgent(self.agent_one.client,
      self.agent_one.model)`) statt sich einen eigenen Anthropic-Client zu
      bauen. Nachweis: kompletter Lauf ueber die Bruecke ohne eine einzige
      Fehlerzeile - Extraktor nennt 6 Tokens (NEAR, ONDO, ASTRO, BP, LTC, ETH),
      Synopsis liefert echten Text. 23 Tests in
      Agenten/Werkzeuge/tests/test_ollama_openai_bruecke.py gruen.
      Angelegt: 2026-09-24 · Erledigt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents/src/agents/coingecko_agent.py
- [x] **T-058 — MoonDev-Aufgabe auf fensterlosen Wrapper umgestellt** — erledigt 2026-09-24
- [x] **T-043 — OmniRoute lag 5,5 Stunden still, und die Aufgabe sah harmlos aus**
- [x] **T-051 — Stops fuer die uebrigen Kraken-Spotbestaende**
      Kontext: Am 24.09.2026 wurden die mosaic-Bestaende (BTC/ETH/SOL) und die
      Margin-Positionen SUI/NEAR/ZEC abgesichert. Das uebrige Guthaben traegt
      KEINEN Stop: ALGO, KAS, PEPE, JTO, ONDO, STG, SYN, ADA, DIMO und weitere
      Kleinstbestaende - ein Kursrutsch dort laeuft ungebremst.
      Naechster Schritt: Max nennt die Liste (oder "alle ab X EUR"), dann laufen
      sie durch dasselbe Muster (Skill handel-spuren, Abschnitt "Bestehende
      Positionen nachtraeglich absichern" + references/boersen-aufrufe.md).
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Handel/kraken/, Agenten/Handel/mosaic/kraken_stops_7_5.py
      **Erledigt 2026-09-24.** Max: "alle ab 50 €". Zwei Bestaende trugen
      keinen Stop und bekamen einen: **ALGO** 513,98026315 @ **0,09033**
      (`O6DA3U-7D5IU-Z2FKJR`) und **SOL** 0,98120906 @ **94,48**
      (`OB5P52-TSYY4-QTIJUN`) - der Rest der 1,4618 SOL war schon durch den
      mosaic-Stop (0,48058439 @ 96,24) belegt. Werkzeug:
      `Agenten/Handel/kraken/spot_stops.py` (Vorschau Standard, `--anwenden`,
      `--ab-eur`, `--prozent`); es ordert nur den FREIEN Teil (Betrag minus
      `hold_trade`), ist damit idempotent und der zweite Lauf meldet
      "0 Bestaende ohne Stop". 76 kraken-Tests gruen, an der Boerse geprueft:
      13 offene Stops, jeder unter dem Markt (5,3-11,6 %).
      Unter der 50er-Schwelle blieben liegen: KAS 43,3 · SYN 27,0 · STG 24,8 ·
      JTO 22,6 · ONDO 20,2 · DUAL 12,2 · HYPE 2,0 · PEPE 1,6 EUR/USD, dazu die
      gestakten ATOM21.S/ADA.S und XPEV.EQ (kein Paar).
      Betrifft: Agenten/Handel/kraken/spot_stops.py,
      Agenten/Handel/kraken/tests/test_spot_stops.py
      **Erledigt 2026-09-16.** Der Router war von 10:39 bis 16:04 nicht
      erreichbar. Ursache war der eigene Startweg: `omniroute-start.ps1` rief
      das Startskript mit einer Pipe auf, das Startskript startet aber einen
      Dauerprozess, der diese Pipe offen haelt. Der Aufrufer kehrte nie
      zurueck - die Aufgabe blieb „Running“, das eigene Protokoll war von
      aussen gesperrt (`Get-Content`: „Device or resource busy“), und als die
      Aufgabe beendet wurde (`^C` im Startprotokoll), starb der Router mit.
      Genau das ist am 16.09. um 10:35/10:39 passiert; der Teilcode 267014 sah
      wie „von aussen beendet“ aus, die Systempruefung meldete ihn nur als
      „zu entscheiden“.
      **Behoben:** der Wrapper startet das Startskript jetzt losgeloest
      (`Start-Process -WindowStyle Hidden`, eigener Prozessbaum) und wartet
      selbst auf den Port (bis 600 s). Nachweis: Router gestoppt, Wrapper von
      Hand - Exit 0 nach 18 s, Protokoll lesbar („ENDE ok nach 18 s“),
      `/v1/models` antwortet 401.
      **Neue Wache:** Hermes-Cron `omniroute-waechter` (alle 15 Minuten,
      `no_agent`, `Agenten/Hermes/scripts/omniroute-waechter.py`) - leere
      Ausgabe heisst „Router laeuft“, sonst Telegram mit Zustand, Startversuch
      und Nachmessung. Der Scheduler laeuft am Router vorbei; eine Wache darf
      nicht den Weg benutzen, den sie ueberwacht. Nachweis: Port freigegeben,
      Wache laufen lassen - „Nachgemessen: Port 20128 ist offen - geheilt“
      nach 25 s.
      Betrifft: `Agenten/Routinen/omniroute-start.ps1`,
      `Agenten/Hermes/scripts/omniroute-waechter.py`
      Angelegt: 2026-09-16

- [x] **T-018 — Saisonalitaet rechnete nur auf 50 Tagen, nicht auf der tiefen Reihe**
      **Erledigt 2026-09-16.** `indikatoren.lage(k_stat=...)` rechnet die
      Saisonalitaet jetzt auf der tiefen Reihe, wenn `bot.py` mit `--historie`
      laeuft; der Signal-Merge steht dafuer in `indikatoren.signal_bauen()` an
      einer Stelle. Uebernommen wird die Reihe nur, wenn sie laenger ist UND
      gleichzeitig endet (`_gleichzeitig`) - `saisonalitaet()` liest Wochentag
      und Tagesphase der naechsten Kerze aus dem Ende der Reihe.
      Gemessen an `LINK-USD_UM_XPERP-310829` (20 Tage alt): n=16 aus dem
      Kontrakt gegen n=172 aus `LINK-USDT-SWAP` (1200 Kerzen). Die Ausgabe
      nennt die Basis („Basis: tiefe Reihe, 1200 Kerzen“), die Warnung „n ist
      duenn“ entfaellt dann. Das Kurs-Signal bleibt am Kontrakt.
      Nachweis: 6 neue Tests (`xperp/test_saisonalitaet_tief.py`) und 18
      bestehende gruen, echter Lauf `bot.py trend --wert LINK --historie auto`,
      Gegenprobe ohne `--historie` (n=16), `handeln.py --vorschau` Exit 0.
      Betrifft: `Agenten/Handel/xperp/{indikatoren,bot}.py`, [[Saisonalitaet-Signal]]
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-16

- [x] **T-035 — Spur 2 ist nur im Dauerbetrieb nutzbar (Herzschlag 30 min)**
      **Erledigt 2026-09-16 — die 30 Minuten sind ueberholt.** Seit dem
      14.09.2026 gilt die Herzschlag-Regel: 180 Minuten fuer Papier-Spuren,
      45 Minuten fuer Spuren mit Handelserlaubnis (`_herzschlag_regel` in jeder
      `wachen.json`); der Dauerlauf-Waechter startet eine tote Spur alle 30
      Minuten neu. `xperp/wachen.json` steht auf 180 (Papier). Die
      Systempruefung misst es in Block 11b nach: 26 von 26 Handels-Spuren
      folgen der Regel. Der zweite Weg ist damit der eine Weg - der Dauerlauf
      laeuft.
      **Nachtrag 19.09.2026 (T-035 ueberdacht, von Max angeordnet):** Die
      45-Live-Grenze ist aufgehoben - seit 19.09.2026 gilt 180 fuer ALLE
      Spuren (Papier UND Live). Grund: ungeklaerte Abschaltungen (T-004)
      lassen die Herzschlag-Luecke bei einem PC-Ausfall ueber 45 min wachsen;
      ein Fehlschluss der Live-Position (scanner) waere ein Verlust in echtem
      Geld. Die Position loest die Spur ueber Stop-/Risiko-Logik auf, nicht
      der Herzschlag. Umgesetzt: `scanner/wachen.json`
      `herzschlag_max_minuten` 45 -> 180 (+ `_herzschlag_regel` konsistent),
      `systempruefung.ps1` Block 11b `$soll = 180` (war 45 live / 180 papier).
      Nachweis: 11b-Formel gegen scanner = konform true.
      Betrifft: `Agenten/Handel/xperp/wachen.json`, `dauerlauf.py`

- [x] **T-015 — Seagate Portable (`G:`) war ab, Hauptsicherung ohne Ziel**
      **Erledigt 2026-09-16.** `G:` ist angeschlossen (`G:\MaxHirn-Sicherung`
      vorhanden, 119 GB frei) und die Laeufe sind gruen: `MaxHirn-Sicherung`
      15.09. 20:00 Code 0, `MaxHirn-Zweitkopie` 21:00 Code 0,
      `MaxHirn-Posteingang` 22:00 Code 0 (gemessen 16.09.2026). Der Befund vom
      31.08. war das abgezogene Laufwerk, kein Defekt. Die Ausser-Haus-Kopie
      zielt inzwischen auf `Q:` statt `E:` (siehe [[Routinen]]).
      Betrifft: `Agenten/sichern.ps1`, `Agenten/sichern-ausser-haus.ps1`,
      Aufgabe `MaxHirn-Sicherung`

- [x] **T-041 — Drei Spuren startet der Dauerlauf, ohne dass sie den Bus melden**
      **Erledigt 2026-09-13.** `swap/handeln.py`, `spiegel/spiegel.py` und
      `orbk/handeln.py` tragen jetzt je `with ereignis.lauf("handel/<spur>")`
      (main() als Wrapper, _main() der bisherige Body; Muster
      `xperp/handeln.py`). Nachweis: drei `--vorschau`-Laeufe, im Journal stehen
      start/ende (code 0) fuer alle drei; der laufende Dauerlauf hatte sie im
      11:52-Zyklus schon gemeldet. Spurtests gruen (swap 30, spiegel 33, orbk 46),
      Bus-Suite meldet „Ende-zu-Ende bestanden“ (Commit 1b0140d).

      **Zwei Vorbestands-Fehler kamen dabei mit heraus**, beide erst sichtbar,
      nachdem die Pruefung darueber wieder griff:
      1. `test_anbindung_handel.py` zeigte in der statischen Liste auf
         `orb/handeln.py` - die Datei gibt es nicht mehr, die Spur laeuft als
         `orbk`. Nachgezogen, mit Begruendung im Kommentar.
      2. `safe-file-ops.ps1` ist eine **Bibliothek**, die `posteingang.ps1` und
         `datensortierung.ps1` dot-sourcen (eigener `$MyInvocation`-Einsprung).
         Eine eigene Start/Ende-Meldung von dort waere falsch - sie erzeugte bei
         jedem Aufruf des Einbinders einen zweiten Zyklus im Journal.
         `test_anbindung_routinen.py` ueberspringt jetzt Dateien, die sich im
         Kopf mit `BUS: Bibliothek` kennzeichnen; der Marker steht in der Datei,
         die Begruendung im Test.
      Betrifft: `Agenten/Handel/{swap,spiegel,orbk}`, `Agenten/Bus/tests/`,
      `Agenten/Routinen/safe-file-ops.ps1`
- [x] **T-037 — Echter Umzug: Archiv ganz aus dem Vault, konfigbasiert** — erledigt
      2026-09-07. Folgeauftrag zum Junction-Umzug vom 06.09. (Commit ad469fb).
      Die sechs NTFS-Junctions unter `MaxHirn/Archiv/` sind entfernt; die
      Archivdaten (44 GB, 64.745 Dateien) liegen nur noch auf `O:\Archiv`. Alle
      Werkzeuge finden sie über die neue User-Umgebungsvariable
      `ARCHIV_ROOT = O:\Archiv` (Rückfall im Code auf die Vault-Lage).
      `ArchivSuche/` (git-versionierter Code) und der Index `archiv_index.db`
      (neu baubar) bleiben auf `C:`.
      Geändert: `index.py`, `server.py` (`ROOT` aus `ARCHIV_ROOT`);
      `archiv_mcp.py`, `mailversand.py` (Datenwurzel von Indexwurzel getrennt);
      `sichern.ps1` / `sichern-zweitkopie.ps1` (Junction-Sonderfall raus, zweiter
      robocopy-Lauf `O:\Archiv` → `G:`/`J:` bleibt). `vektor_index.py`,
      `vektor_suche.py`, `search_cli.py` unverändert (nur DB).
      Gegenprobe: `index.py` inkrementell → 9712 Einträge, 0 verändert, 0
      entfernt; `search_cli.py`-Testsuche unverändert; `archiv`- und `mail`-MCP
      funktional gegen `O:` geprüft; `90-pruefen.ps1` — MCP-Pfade und Suchindex
      grün. Doku: `Ordnerstruktur.md`, `Schutzregeln.md`, `MaxHirn/CLAUDE.md` +
      `AGENTS.md`, `Archiv/CLAUDE.md` + `AGENTS.md`, `Archiv/README.md`.
      Offen: laufende Prozesse (Claude Desktop, Hermes) sehen `ARCHIV_ROOT` erst
      nach Neustart.
      Betrifft: `MaxHirn/Archiv/ArchivSuche/`, `Agenten/MCP-Server/{archiv,mail}/`,
      `Agenten/sichern*.ps1`
      Angelegt: 2026-09-07 · Zuletzt: 2026-09-07

- [x] **T-034 — Hauptsicherung fehlschlug am 04.09. weil Hermes live läuft** — erledigt
      2026-09-04. Um 20:00 meldete `sichern.ps1` robocopy-Code 11 (FEHLER), obwohl
      47,5 GB kopiert worden waren. Ursache: **Hermes läuft seit dem Umbau
      innerhalb der Sicherungsquelle** (`BrainFiles/Agenten/Hermes`) und hält
      beim 20-Uhr-Lauf seine drei lebenden Laufzeitordner offen:
      `pending_messages/`, `cache/terminal-output/`, `telemetry/shared_metrics/`.
      robocopy scheiterte daran mit Zugriff verweigert, verbrauchte die
      Wiederholungen und brach als Fehler ab (dieselbe Klasse wie der
      `logs`-Ausschluss vom 23.08.).
      **Fix:** diese drei Namen in `/XD` aller drei Sicherungsskripte
      (`sichern.ps1`, `sichern-zweitkopie.ps1`, `sichern-ausser-haus.ps1`)
      aufgenommen — gleiche Behandlung wie `logs` und Claude. Stufe 1:
      `.bak-20260904` angelegt, echter Lauf bestätigte **robocopy-Code 3,
      0 Fehler** (Hermes lief dabei). Commit `8a23529` (Autor Hermes).
      Die drei Ordner sind reine Durchlauf-Caches, damit kein Verlust.
      `MaxHirn-Sicherung` (Aufgabe) war Ready und lief fehlerfrei.
      Angelegt: 2026-09-04 · Zuletzt: 2026-09-04
      Betrifft: `Agenten/sichern*.ps1`, `Agenten/Hermes/{pending_messages,cache/terminal-output,telemetry/shared_metrics}`

- [x] **T-025 — Hauptsicherung nach `G:` hat zwei Tage übersprungen**
      Erledigt 2026-09-02. Die Ursache stand bereits in T-022: Die Aufgabe war
      deaktiviert und wurde heute wieder aktiviert — der Eintrag hier war
      insoweit doppelt und ist korrigiert worden. Bestätigt ist der Lauf jetzt
      auch: `G:` und `O:` tragen um 22:35 den Stand von heute, einschließlich
      der Regeländerungen dieser Sitzung. Beide Kopien sind damit wieder
      aktuell.
      Beobachtung am Rand: Ein zweiter Lauf um 22:40 brach mit `0xC000013A`
      (abgebrochen) ab — zeitgleich mit `MaxHirn-Posteingang`, was nach einem
      Sammelstart von Hand aussieht, fünf Minuten nach dem regulären. Die
      Hausregel „`sichern.ps1` nie doppelt starten" gilt genau dafür; Schaden
      ist keiner entstanden, die Kopie von 22:35 steht.
      Die Erkennungslücke ist geschlossen: Abschnitt 9 der Systemprüfung meldet
      seit heute nicht nur fehlerhafte Läufe, sondern auch ausgebliebene — jede
      `MaxHirn-*`-Aufgabe, die länger als 48 h nicht gestartet ist. Genau das
      hatte zwei Tage lang niemand gesehen.

- [x] **T-012 — Alte Zweige auf `G:` abräumen**
      Kontext: Die Sicherung läuft ohne `/MIR` und räumt deshalb nichts weg,
      was in der Quelle verschwindet. Auf `G:\MaxHirn-Sicherung` liegen nach
      dem Umbau vom 30.08.2026 noch die 51 GB `Modelle\` (ab jetzt aus der
      Sicherung ausgenommen) und der alte Zweig unter dem früheren Namen „Claude“ (er heißt jetzt
      `Archiv`, wird also ein zweites Mal kopiert).
      **Gemessen 03.09.2026**, nach einem vollständigen Lauf der neuen
      Sicherung (robocopy-Code 3, 54:38 Dauer, 29,1 GB übertragen): Auf `G:`
      liegen 190 GB, frei sind 68,5 GB von 2,75 TB.

      | Ordner | GB | Was |
      |---|---|---|
      | `Claude` | 93,8 | alter Archivname, heute `MaxHirn\Archiv` — doppelt gehalten. Allein `Claude\Posteingang\Maximilianbackup0924` sind 48,8 GB |
      | `MaxHirn` | 70,4 | aktuell (Quelle 45 GB; die Differenz sind Altstände, die ohne `/MIR` liegenbleiben) |
      | `Modelle` | 21,1 | seit 30.08.2026 aus der Sicherung ausgenommen |
      | `MCP-Server`, `Hermes`, `Handel`, `Wissen`, `Routinen`, `GitHub`, … | ~5 | Struktur **vor** der Ordnertrennung, heute alles unter `Agenten/` |

      **Abgeräumt am 03.09.2026 auf Max' Freigabe.** Entfernt wurden
      `Modelle\`, `MCP-Server\`, `Hermes\`, `GitHub\`, `Handel\`, `Routinen\`,
      `Wissen\`, `Referenz\`, `.obsidian\`, `.claude\`, `.agents\`, `.codex\`,
      elf lose Altdateien der obersten Ebene und zuletzt `Claude\`.

      Jeder Ordner wurde vorher gegengeprüft, keiner blind gelöscht. Zwei
      Fälle, in denen die Prüfung etwas gefunden hat:

      - **`Codex\` und `Coworking-Space\` (0,4 GB) stehen bewusst noch da.**
        Ihr heutiger Ort ist `Werkstatt\`, und Werkstatt ist aus der Sicherung
        ausgenommen — die Kopie auf `G:` ist die einzige, unter anderem vom
        eigenen `m3u_cleaner`. Siehe T-032.
      - **`Claude\` war nur zu 44,5 von 93,8 GB eine Dublette.** Drei
        Prüfrunden: Pfadvergleich (45 von 64.829 Dateien ohne Entsprechung),
        Namensvergleich über Archiv und Werkstatt (18 davon lagen umsortiert
        woanders), Größenvergleich der restlichen 27. Dabei kam heraus, dass
        die 24 ELSTER-Belege beim Einsortieren **umbenannt** worden waren
        (`1-Lohnsteuerbescheinigung_2022_…` → `2022_Belegabruf_…_2026-08-19`)
        und byteweise identisch vorliegen. Echte Unikate blieben drei:
        `Maximilianbackup0924` (52,4 GB), `EFIbackup0924` (524 MB) und
        `OKX_API.env` (124 B). Sie liegen jetzt in
        `G:\Unikate-aus-Altzweig-20260903\` mit einer `LIESMICH.md`, die den
        Weg dorthin beschreibt.

      **Die Lehre für das nächste Mal:** Ein Pfadvergleich allein hätte 50 GB
      gelöscht oder 41 GB verschont — beides falsch. Erst Pfad, dann Name,
      dann Größe.

      **Ergebnis:** frei auf `G:` von 68,5 GB (vor dem Lauf) auf **109,5 GB**.
      Im Sicherungsordner stehen nur noch `MaxHirn\`, `Agenten\`, die aktuellen
      Wurzeldateien und die beiden zurückgestellten Ordner aus T-032.
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-03

- [x] **T-030 — Drei Handels-Routinen in die Aufgabenplanung eintragen** —
      erledigt 2026-09-02 auf Max' Anweisung. Angelegt mit
      `Register-ScheduledTask` (nicht `schtasks` — das setzt kein „Starten,
      sobald möglich", und ohne das fällt ein Termin nach einer
      Hardware-Abschaltung ersatzlos aus): `MaxHirn-Marktscanner` täglich
      07:30, `MaxHirn-Kraken-Spur3` täglich 07:45, `MaxHirn-Handel-Wachen`
      sonntags 08:00. Alle drei einmal aus der Aufgabenplanung heraus gestartet
      und geprüft — Ergebniscode 0, Protokolle vollständig, keine
      Doppelkäufe. Damit sind es neun geplante Aufgaben. Beide Tagesläufe
      handeln nur auf Papier (`MAXHIRN_ROUTINE=1`, kein `--live`).

- [x] **T-029 — Dritte Spur: Kraken wirklich bauen** — erledigt 2026-09-02
      Auf Max' Anweisung („ich will ihn") das nachgeliefert, was T-027 als Weg
      beschrieben hatte. Neu unter `Agenten/Handel/kraken/`: `wachen.json`
      (EUR, eigener Rahmen), `kraken.py` (REST, nur Standardbibliothek, kein
      Auszahlungsweg), `scan.py`, `handeln.py`, `wachen_kraken.py`, README.
      Die währungsneutrale Rechnung der Bedingungen 2–5 wird aus
      `scanner/wachen_pruefung.py` **importiert**, nicht abgeschrieben.
      `freigabe.py` kennt jetzt drei Spuren und zeigt die Währung der Spur an;
      seine Bestandsschlüssel heißen dafür `gebunden`/`verlust_gesamt` statt
      `…_usd` (`scanner/handeln.py` nachgezogen, beide Spuren nachgeprüft).
      Gemessen dabei: Kraken nimmt 0,40 % Taker statt 0,05 % bei OKX — eine
      Runde kostet 0,80 %. Deshalb Stop mindestens 5 %, C/R mindestens 2,0,
      Score mindestens 65, und die Gebühr steht auch im Papierlauf in den
      Beträgen. Zweiter Befund: Auf dem Konto liegen 0,0094 EUR frei, der Rest
      steckt in Coins — daher die zusätzliche Sperre `mindest_guthaben_eur`.
      Erster Papierlauf gelaufen: 4 Positionen, 200 EUR gebunden; die sechs
      Wochen aus Bedingung 1 laufen ab heute. `handel_erlaubt` bleibt `false`.
      Die schreibenden MCP-Werkzeuge bleiben gesperrt — die Grenze verläuft
      jetzt nicht mehr zwischen Börsen, sondern zwischen Wegen.

- [x] **T-028 — Bestätigungsdialog zum Scharfschalten** — erledigt 2026-09-02
      `Agenten/Handel/freigabe.py` gebaut und an `scanner/handeln.py --live`
      angebunden. Beide Spuren, prüft gegen `wachen.json`, führt selbst nichts
      aus. Die Obergrenze jedes Reglers ist der Wachen-Wert, der Hebeldeckel
      ist senkbar, nie hebbar. Ausstiege laufen nie durch das Fenster.
      Beim Bauen gemessen: `sys.stdin.isatty()` meldet in der Git-Bash unter
      Windows auch bei umgeleitetem stdin ein Terminal — als Sperre gegen den
      Zeitplan taugt es nicht. Deshalb lehnt das Fenster nach 120 s ohne
      Bedienung von selbst ab; das ist der tragende Schutz. Zusätzlich setzen
      `Routinen/marktscanner.ps1` und `handel-wachen.ps1` jetzt
      `MAXHIRN_ROUTINE=1`.
      Offen als eigener Punkt: `xperp/bot.py` ist nicht angebunden — er legt
      Befehle ohnehin nur vor.

- [x] **T-027 — Handelsregeln decken Kraken nicht ab**
      Erledigt 2026-09-02: Neuer Abschnitt *Kraken ist keine dritte Spur* in
      `Wissen/Schutzregeln.md`. Kraken bleibt lesend — die neun lesenden
      Werkzeuge sind ausdrücklich erlaubt, `kraken_order_aufgeben` und
      `kraken_order_stornieren` ausdrücklich nicht, auch nicht mit Bestätigung
      im Chat. Begründung ist der eigene Maßstab des Abschnitts: ohne
      `wachen.json`, Journal und Herzschlag fehlen alle drei Eigenschaften, die
      die Handelserlaubnis tragen. Der Weg zu einer echten dritten Spur ist
      beschrieben. Nicht auf eine Entscheidung gewartet, weil die sichere
      Richtung aus der bestehenden Regel folgt — die Öffnung bleibt möglich.

- [x] **T-026 — `absturz-recovery.md` liegt lose im Skill-Ordner und wird nie geladen**
      Erledigt 2026-09-02: nach `skills/absturz-recovery/SKILL.md` gehoben
      (`git mv`, Inhalt unverändert), die `.bak-20260902` daneben entfernt. Der
      Skill erscheint seither in der Skill-Liste einer Sitzung. Abschnitt 10b
      der Systemprüfung meldet ab jetzt jede lose `.md` im Skill-Ordner und
      jeden Skill-Ordner ohne `SKILL.md`.

- [x] **T-024 — `CLAUDE.md` und `AGENTS.md` sind auseinandergelaufen**
      Erledigt 2026-09-02: Beide Paare zusammengeführt, jedes ist jetzt Zeichen
      für Zeichen gleich — wie in `Werkstatt/` schon erprobt. Übernommen wurde
      jeweils die Vereinigung: die Vektorsuche (`vektor_suche.py`, `--hybrid`,
      Abdeckung, Indexstand 19.08.2026) aus `Archiv/AGENTS.md`, die Mail-Sperre,
      der Netzteil-Kontext, die Umlaut-Suchfalle und die
      `sort_inbox.py`-Sicherungen aus `Archiv/CLAUDE.md`, dazu die schärfere
      Notizen-Regel aus `MaxHirn/AGENTS.md`. Der gemeinsame Kopf nennt jetzt die
      maschinelle Prüfung, die das hält (Abschnitt 10a in `systempruefung.ps1`).

- [x] **T-022 — `MaxHirn-Sicherung` deaktiviert, `MaxHirn-Posteingang` scheiterte**
      Erledigt 2026-09-02: `MaxHirn-Sicherung` auf Anweisung von Max wieder
      aktiviert (`Enable-ScheduledTask`), Auslöser unverändert täglich 20:00,
      „Starten sobald möglich". Warum sie aus war, ist nicht abschließend
      geklärt — vermutlich im Zuge von T-015 (Seagate `G:` war zeitweise ab).
      Der `MaxHirn-Posteingang`-Fehler vom 01.09. 22:00 war der Pfad
      `Agenten\Claude\ArchivSuche` — doppelt veraltet (`Agenten\` statt
      `MaxHirn\`, `Claude\` statt `Archiv\`). Der Wrapper `posteingang.ps1`
      zeigt inzwischen korrekt auf `MaxHirn\Archiv\ArchivSuche` (T-016), der
      nächste Lauf heute 22:00 sollte grün sein.

- [x] **T-021 — Fremd-MCP-Server apify und okx-Lokalklon entfernt**
      Erledigt 2026-09-02: Auf Anweisung von Max beide gelöscht.
      `Agenten/MCP-Server/ant.dir.gh.apify.apify-mcp-server/` (node_modules nur
      noch tote pnpm-Junctions auf den alten `…\MaxHirn\MCP-Server\`-Pfad) und
      `Agenten/MCP-Server/okx/` (eigenes `.venv`, `okx_mcp.py` mit doppelt
      kaputtem Pfad `…\MaxHirn\Claude\Worktrees\…`). Beide in keiner `.mcp.json`;
      der aktive okx-Zugang läuft über den HTTP-Server `okx-agent-trade-kit`.

- [x] **T-010 — Kimi-K2.7-Code entfernt**
      Erledigt 2026-09-02: Auf Anweisung von Max gelöscht. War ein
      HuggingFace-Repo-Klon (`.git` mit LFS, ~31 GB, keine Gewichtsdatei je
      ausgecheckt) unter `O:\Modelle\Kimi-K2.7-Code`. Reproduzierbar per
      `git clone`, falls je gebraucht.

- [x] **T-020 — Fremd-Repo `MaxHirn/OmniRoute` lag am falschen Ort**
      Erledigt 2026-09-02: Klon von `github.com/diegosouzapw/OmniRoute`,
      Branch `release/v3.8.51`. Beide Klone geprüft — weder unter `MaxHirn/`
      noch unter `Werkstatt/` gab es eigene Commits, Stashes oder Branches
      (Werkstatt-Reflog: nur `clone`; die geänderten `package*.json` dort waren
      reine `npm install`-Nebenwirkung). Der alte `Werkstatt/OmniRoute`
      (älterer HEAD, 4,3 GB mit `node_modules`/`dist`) wurde gelöscht, der
      neuere saubere Klon aus `MaxHirn/` (715 MB, Arbeitsbaum sauber) an seine
      Stelle verschoben. Die Übergangsregel `MaxHirn/OmniRoute/` in `.gitignore`
      ist wieder raus — `Werkstatt/*/` deckt den neuen Ort ab. Wer dort
      arbeiten will: `npm install` neu.

- [x] **T-001 — Sicherungslaufwerk G: fehlt, Hauptsicherung hat kein Ziel**
      Erledigt 2026-08-28: Kein Defekt. Max hatte die USB-Platten für einen
      CMOS-Reset abgezogen. Seagate Portable ist wieder angeschlossen,
      `G:\MaxHirn-Sicherung` erreichbar (2751,1 GB, 128,8 GB frei, `Healthy`).
      Der 20-Uhr-Lauf kann wieder arbeiten. Der Fehlstand bestand nur, solange
      die Platte ab war.

- [x] **T-002 — Auslagerungsdatei liegt auf einer USB-Platte**
      Erledigt 2026-08-28: Max hat den Eintrag mit erhöhten Rechten entfernt.
      Nachgemessen um 17:15: `PagingFiles` enthält nur noch
      `c:\pagefile.sys 0 0` und `o:\pagefile.sys 4096 16384`, auf `G:` liegt
      keine `pagefile.sys`. Ob damit auch T-004 verschwindet, ist offen —
      die Hypothese ist nicht bewiesen, nur die Fehlkonfiguration beseitigt.
      Sicherung des Schlüssels: `Routinen/sicherungen/MemoryManagement-20260828.reg`.

- [x] **T-003 — Windows Search stürzt seit 24.08. in Endlosschleife ab**
      Erledigt 2026-08-28: Der Starttyp wurde um **16:00:04** auf „Deaktiviert"
      gesetzt (Ereignis 7040). Letzter Absturz **15:59:41**, seither **null** in
      77 Minuten. Vorher waren es 16.926 in sieben Tagen, allein 984 zwischen
      dem Start um 15:19:36 und 15:59:41 — rund 24 pro Minute.
      Der Suchindex wurde nicht neu gebaut; die Suche im Startmenü bleibt tot.
      Max' eigene Archivsuche ist davon nicht betroffen (SQLite).
      Gewinn: Das Systemprotokoll reicht wieder bis zum **05.08.2026** zurück
      statt vier Tage — die Absturzspuren für T-004 überleben jetzt lange genug.

- [x] **T-005 — J: (WD My Book) nicht angeschlossen, iCloud-Junction ins Leere**
      Erledigt 2026-08-28: Die Platte ist wieder da. `Extern_BackUp`, 1.953 GB
      gesamt, 246 GB frei, `Healthy`; NTFS meldete um 15:47:51 „Volume J: ist
      fehlerfrei". Die Junction `C:\Users\faupe\iCloudPhotos` löst wieder auf.
      Unverändert gilt: 479 unkorrigierte Lesefehler (Messung 14.08.), die
      30.635 Mediendateien liegen weiter auf dem schwächsten Laufwerk.

- [x] **T-006 — Echtzeituhr ging 68 Minuten nach**
      Erledigt 2026-08-28: harmlos. Die Korrektur um 15:20:12 kam 36 Sekunden
      nach dem Kaltstart um 15:19:36 — der CMOS-Reset hatte die Uhr geleert,
      der Zeitdienst zog sie einmal gerade. **Seither kein weiterer Sprung**,
      Abweichung 0,12 s gegen `time.windows.com` (gemessen 17:17).
      Eine schwache CMOS-Batterie würde erneut driften; ein zweiter Messpunkt
      in einigen Tagen bestätigt es endgültig. Bis dahin kein Handlungsbedarf.

- [x] **T-031 — Telegram-Bot fuer Meldung und Steuerung einrichten** — erledigt 08.09.2026
      Die fünf Module (`Handel/melder.py`, `tagesbericht.py`, `freigabefenster.py`,
      `dauerlauf.py`, `Routinen/handel-dauerlauf.ps1`) waren seit 07.09. fertig,
      aber stumm — es fehlten nur die Token.

      Eingerichtet 08.09.2026: Bot **@CodeClaudebitbitbot**. `TELEGRAM_TOKEN`
      und `TELEGRAM_CHAT_ID` (`7648512088`) stehen als **Benutzervariablen** in
      `HKCU\Environment`. `melder.py` liest sie live aus der Registry
      (`_aus_registry`), ein laufender Dauerlauf braucht dafür **keinen
      Neustart**. Probe bestätigt, der Bot beantwortet Befehle.

      Fallen fürs nächste Mal:
      - Der Bot muss zuerst **vom Nutzer angeschrieben** werden, sonst gibt
        `sendMessage` HTTP 400 ("chat not found").
      - `melder.py --chat-id-suchen` liefert nichts, solange der Dauerlauf
        läuft: Telegram gibt jede Nachricht per `getUpdates` nur einmal aus,
        der Dauerlauf holt sie zuerst. Chat-ID dann aus `dauerlauf.log`
        (Zeilen „Befehl: …") lesen oder den Dauerlauf kurz stoppen.
      - Gültige Befehle: `/ja [h]`, `/nein`, `/hilfe`.

      Geplante Aufgaben stehen alle (State Ready): `MaxHirn-Handel-Dauerlauf`
      (+ `-Waechter`), `MaxHirn-Handel-Wachen`, `MaxHirn-Verbesserer`.

- [x] **T-039 — Hebel-Deckel-Tabelle in [[XPERP-Handel]] ist überholt** — erledigt 2026-09-19
      **Erledigt 2026-09-19.** Tabelle auf 3,6× (SOL), 4,1× (HYPE), 1,7×
      (ZEC) ersetzt, die Aussage „alle Tore bestanden" für die drei
      zurückgenommen, und der Messfehler als Falle danebengeschrieben
      (Deckel auf **Tageskerzen** rechnen — das 300-Kerzen-Fenster des
      gehandelten Kontrakts sind nur 50 Tage).
      Aufgefallen 09.09.2026. Die Tabelle in `Wissen/XPERP-Handel.md`
      (Abschnitt „Hebel-Deckel ≥ 5", Zeilen 165–171) stammt aus einer
      **fehlerhaften Messung**: `auswahl.py` leitete den Deckel aus 300
      4H-Kerzen ab, das sind nur 50 Tage. SOLs Rücklauf vom 31.05.2026 lag
      außerhalb dieses Fensters.
      Behoben ist der Code — `mae_tage()` rechnet jetzt auf 300 **Tages**kerzen,
      committet. Die Notiz nicht.

      | Wert | steht dort | gemessen (200 Tage) |
      |---|---|---|
      | SOL | 10,0× | **3,6×** |
      | HYPE | 6,4× | **4,1×** |
      | ZEC | 5,8× | **1,7×** |

      Damit trägt die Überschrift „Hebel-Deckel ≥ 5" für keinen der drei
      Werte mehr. Zu tun: Tabelle ersetzen, den Messfehler als Falle
      danebenschreiben (sonst wiederholt ihn die nächste Sitzung), und die
      Aussage „alle Tore bestanden" für die drei zurücknehmen.
      Betrifft: `MaxHirn/Wissen/XPERP-Handel.md`
      **Nachtrag 13.09.2026 (Max' Auftrag „README-Tabelle richtigstellen“):**
      Die Tabelle in `xperp/README.md` (Abschnitt „Gemessen am 01.09.2026“)
      trug noch die alten Deckel 10,0×/6,4×/5,8× — ersetzt auf 3,6×/4,1×/1,7×,
      „alle Tore bestanden“ zurückgenommen, Messfehler als Falle daneben
      (konsistent zu dieser Notiz). Dazu `bot.hebel_deckel()` auf Tageskerzen
      gezogen (`auswahl.mae_tage`): die Aufrufe in `pruefpflicht()` (neuer
      Parameter `stat_id`) und `zeige_lage()` holen jetzt die 1D-Reihe der
      Statistik-Quelle (bei `--historie` die des SWAP), ebenso der
      `historie.py`-Vergleich; Test `xperp/test_deckel.py` (3 Tests, Seam
      `bot.tages_kerzen_quelle`), alle 12 xperp-Tests grün. Frische
      CHIP-Messung auf Tagesbasis: jung 4,3× / 48 % vs. SWAP 2,2× / 29 %
      gegen 34 % nötig.

- [?] **T-040 — SOL long, 106 USD: Hebel 5× liegt über dem Deckel**
      Anweisung von Max am 09.09.2026: „SOL long 5x hebel 106 usd und stop
      schlage vor oder setz automatisch klug". Der Stop ist **gemessen**
      (`xperp/stopwahl.py`), der Hebel ist der Konflikt.

      Gemessene Geometrie: **Stop 3,00 ATR / Ziel 4,00 ATR**, E = +0,321 %
      je Runde über alles, +0,894 % in der jüngeren Hälfte, 469 Ziel- gegen
      557 Stop-Ereignisse, 24 von 42 Kombinationen in beiden Hälften positiv.
      Bei 1,92 % ATR sind das **5,75 % Stop / 7,66 % Ziel**.

      Der Deckel für SOL long ist **3,5–3,6×** (größter 7-Tage-Rücklauf
      27,9 %). Gerechnet bei Kurs 100,68:

      | | Nominal | Kontrakte | Verlust am Stop | Liq entfernt |
      |---|---|---|---|---|
      | 5× | 529,58 USD | 526 | 30,46 USD (28,8 % der Margin) | 19,5 % |
      | 3× | 317,14 USD | 315 | 18,24 USD (17,3 % der Margin) | 32,8 % |

      3× passt außerdem zu „lieber mehrere Anläufe": rund 6 statt 3 aus
      106 USD. `Wissen/Schutzregeln.md` führt „Hebel höchstens `hebel_deckel`"
      als auch mit Anweisung feste Grenze.
      **Wartet auf Max.** Bestätigt er 5×, wird 5× ausgeführt — vollständig,
      nicht stillschweigend kleiner.
      Vor dem Auftrag `bot.py` **frisch** laufen lassen, die Zahlen oben sind
      vom 09.09.2026.

