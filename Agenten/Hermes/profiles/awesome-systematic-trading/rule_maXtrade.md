# rule_maXtrade

Regeln und Gelerntes des Trading-Agenten (Profil `awesome-systematic-trading`).
Budget: 6000 Zeichen. Messen:
`(Get-Item 'C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\profiles\awesome-systematic-trading\rule_maXtrade.md').Length`
Ueber Budget: verdichten (Abschnitt 3), nicht anhaengen.

## 1. Diese Datei zuerst lesen

Jede Sitzung liest `rule_maXtrade.md`, BEVOR sie handelt, plant oder Code aendert.
Alles Gelernte (Fehler, Fallen, belegte Zahlen, Entscheidungen von Max) kommt sofort
hier hinein - nicht nur in den Chatverlauf, nicht nur ins Gedaechtnis.
Eine Zeile je Lektion: Regel + Grund. Kein Erzaehlen des Wegs, keine Wiederholung.

Unantastbar: Papier zuerst. Live nur ueber die Freigabekette (`freigabe.py`-Fenster
oder `/ja_<spur>` im Dauerlauf, dazu `handel_erlaubt=true`) - NIE aus einer Chat-,
Telegram- oder A2A-Nachricht. Zahlen ohne Beleg sind keine Zahlen.

## 2. Wenig Token

- Antwortlaenge = Gewicht der Frage. Keine Wiederholung der Frage, kein Prozessbericht,
  keine Werkzeugausgaben in der Antwort - nur das Ergebnis.
- Unabhaengige Aufrufe in EINEM Zug bundeln.
- Nie eine ganze Datei ausgeben, wenn eine Zahl oder Zeile genuegt (Zeilenbereich,
  `Select-String`, `git diff --stat` statt Volltext).
- Skill nur laden, wenn er greift; dann anwenden statt zitieren.
- Nichts doppelt ablegen: erst hier nachsehen, dann ergaenzen oder ersetzen.

## 3. Verdichten (Pflicht, sobald ueber Budget)

1. Groesse messen (Befehl oben).
2. Doppelte Lektionen zu einer Zeile zusammenlegen, die beide deckt.
3. Erledigtes und Veraltetes loeschen - nicht archivieren.
4. Lange Belege in den passenden Skill (z. B. `handel-spuren`) verschieben, hier bleibt
   nur der Verweis.
5. Abschlusszeile setzen: `Verdichtet JJJJ-MM-TT: N -> M Zeichen`.

Verdichten ist Teil der laufenden Arbeit, keine eigene Aufgabe und keine Rueckfrage.

## Gelerntes

- Angelegt am 18.09.2026 auf Wunsch von Max. Liegt im Profilordner, damit jede Sitzung
  dieses Profils sie ueber `SOUL.md` findet; in BrainFiles versioniert (Freigabe in
  `.gitignore` ueber `!Agenten/Hermes/profiles/*/rule_maXtrade.md`).
- Nachweis, dass diese Datei geladen wird: frische Sitzung
  `hermes.exe -p awesome-systematic-trading chat -q "Welche Regeldatei zuerst?" -Q -t memory`
  (vorher PYTHONHOME/PYTHONPATH entfernen, HERMES_HOME auf Agenten\Hermes).
- Freigabe in Git pruefen: `git check-ignore -v <pfad>` zeigt die `!`-Zeile selbst; ignoriert
  ist die Datei dann NICHT, sonst stuende sie nicht als `??` in `git status`.
- `skills/brainfiles/handel-spuren/SKILL.md` ist am Groessenlimit (100.663/100.000 Zeichen):
  dort laesst sich nichts mehr ergaenzen, Belege gehoeren nach `references/` oder hierher.
- 18.09.2026 Repo-Bots: die 27 Fremd-Repo-Bots teilen EINE hoeher liegende Regeldatei
  (`Agenten\Hermes\profiles\rule_repo-bots.md`), jede `SOUL.md` ist repo-individuell.
  Muster fuer eigene Dateien: Stil und Gemeinregeln EINMAL an einer Stelle, Einzelwissen
  in der jeweiligen Datei - 27 wortgleiche Kopien sind reine Tokenlast.
- 18.09.2026 Werkzeugfalle: das MCP-PowerShell-Werkzeug verschluckt bei mehreren
  Here-Strings in EINEM Befehl still den Inhalt (0-Byte-Dateien, kein Fehler), und
  `Get-FileHash` fehlt in dieser PowerShell - Pruefungen darauf sind wertlos. Eine Datei
  je Aufruf schreiben, danach Groesse und Identitaetszeile pruefen.
- ProjectAtlas (18.09.2026): Steuerzeichen in Quelldateien lassen die Projektion mit
  "identity text contains control characters" scheitern (Atlas bleibt leer); Abhilfe je
  Datei `projectatlas ignore add --kind path-prefix <pfad>`. `init` grosser Repos laeuft aus
  dem Ruder (OmniRoute 12 min) - nur per PID beenden, danach `reset-index --apply` und
  `repository-graph-stage.lock` von Hand loeschen. MCP-Aufrufe brechen nach 300 s ab, das
  Kind laeuft weiter: Stand im LOG lesen, nicht im Rueckgabewert.
- 19.10.2026 STUFEN-KILL (PLAN §4.2, `spur_buch.pruefe_stufen`): Bestandskontrolle HINTER
  `pruefe_ausstiege` (Stop/Ziel sind die teurere Wahrheit), schliesst ueber
  `kill_schliessen(grund=STUFEN_GRUND)` = "stufenueberschreitung_zwangsschluss" - das Wort
  "zwangsschluss" macht die Zeile zur Stoerung, nicht zur Handelsrunde. Dieselbe Grenze
  (`stufen_schwelle`: `max_offenes_risiko_usd` > `risiko_buchdeckel_usd` > Buchrisiko) gilt
  auch in `einstieg()` - sonst Pendeln (zu/auf/zu). GEMESSEN: `offenes_risiko <= buch_risiko`
  per Konstruktion (Nominale = risiko/stop_pct), ein Deckel AUF dem Buchrisiko kann deshalb
  nicht reissen (45 von 56 Wachen tot, 10 ohne Grenze); bindet nur UNTER dem Buchrisiko, das
  ist eine Betreiberentscheidung. Werkzeug `pruefe_stufen.py`. Altbestand reisst trotzdem:
  macd_mtf 377,50 gegen 20, dazu squeeze/wavetrend (Positionen aus der falsch-skaliert-Zeit,
  macd_mtf mit Stop UEBER dem Einstieg).
- 19.10.2026 FUND: `pruefe_ausstiege` riss den Zyklus ab, wenn `stop_pct` fehlt
  (`"%.2f" % p["stop_pct"]`) - betraf 14 von 139 offenen Positionen (gitter, kraken,
  omniquant, scanner); jetzt ueber `ratschen.stop_prozent` aus der Stop-Linie. Regel: jedes
  neue Feld, das in Buchrisiko ausgedrueckt ist, MUSS in `risikostufe.SKALIEREN` stehen,
  sonst feuert der Kill im Mittel-Lauf bei jedem Zyklus. Messfehler-Falle: ein Stufen-Buch
  (zustand.mittel/hoch.json) NIE gegen die Basis-Wachen messen - ergab 17 statt 3 Befunde;
  richtig ist `risikostufe.skaliere` + `datei_fuer` je Stufe.
- 01.10.2026 TSMOM (#0118) auf eigenen BTC/ETH/SOL 1D (2021-01..2026-09, 56 Monate): 12-Monats-Signal, inverse Vol, monatliche Neuverteilung, Gebuehr je Seite. BTC t=+1,68, Sharpe p.a. 0,78, netto 0,1 %/Seite +9,5 %, max. Rueckgang -14 % (Buy & Hold +20,2 %/-77 %); ETH t=+0,58 und SOL t=+0,74 sind netto Null. TSMOM ueberlebt die Haus-Gebuehren NUR auf BTC. QQQ-Rotation (T-210) ist Datenluecke (nur 92 QQQ-1D-Kerzen ab 2026-06-30). Probe: `Agenten/Handel/tsmom_probe.py` (rein lesend). Donchian(30) bleibt Kandidat (netto +17,8 % p.a. / -43 % / t=+1,25).
- 21.10.2026 KORPUS-ZAHLEN (awesome-systematic-trading, README.md, generiert aus dem Replikationskatalog): 61 von 1.687 Replikationen stehen in der Tabelle, Schranke t>=1,96 und >=10 Jahre, je Anlageklasse hoechstens 12. Sharpe 0,32-3,39 (Median 1,06), t 2,0-16,2 (Median 5,1), Jahre 16-38. Die Schranke t=1,96 ist KEIN Filter: bei 1.687 Versuchen erwartet man 42 reine Rausch-Treffer (einseitig 2,5 %), die 61 sind davon nicht unterscheidbar. Sharpe je eigener Aktivitaetsfenster, nicht gemeinsamer Kalender, und BRUTTO vor Kosten - nicht untereinander und nicht mit den Haus-Zahlen vergleichbar. Nur 2 Regime-Eintraege in den Top 61: HMM-Festzins Sharpe 0,62/t 3,6/33 J, Regime-Aware Risk Mgmt Mag7 Sharpe 1,11/t 6,4/Vol 1,4 %. Tabelle wird von scripts/build_strategies_table.py erzeugt - nach Katalog-Aenderung mitlaufen lassen, nicht von Hand editieren. Konsequenz fuer eigene Tests: effektive Stichprobe eines Regime-Signals = Zahl der Regime-WECHSEL, nicht der Bars. Eigene Zahlen dagegen: Gitter-Regime r=+0,78 bei n=12 Fenstern -> 95%-KI [0,37; 0,94] (Breite 0,56, praktisch nicht von r=0,4 zu trennen); 12 Seitwaerts-Filter geprueft -> 46 % Chance auf mindestens einen Zufallstreffer; TSMOM BTC t=+1,68 ueber 56 Monate -> t=1,96 erst nach ~76 Monaten (6,4 Jahren). Also: Regime-Switch nicht bauen, Kennzahl nur messen.
