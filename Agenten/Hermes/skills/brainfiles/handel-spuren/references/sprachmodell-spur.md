# Eine Spur, deren Richtung ein Sprachmodell gibt

Beweis: die drei Papierspuren `moondev_whale`, `moondev_liquidation`,
`moondev_sentiment` vom 17.09.2026 (Vorbilder: `whale_agent`,
`liquidation_agent`, `sentiment_agent` aus `Werkstatt/moon-dev-ai-agents`).

Hinweis: `SKILL.md` ist gross, aber NICHT am Zeichenlimit (gemessen ~53 kB
gegen 100.000) - ein Eintrag dieser Datei in die Ausloeser-Liste oben ist
moeglich und nur noch nicht gemacht. Vor jeder Aussage "das Skill ist voll"
die Datei messen, nicht der alten Notiz glauben.

## Wann
Max sagt „die restlichen Moon-Dev-Agenten mit LLM auch einbinden" o.ae.: die
Fremd-Agenten lassen ihr URTEIL in einem Modell fallen (Anthropic/DeepSeek/OpenAI,
Schluessel noetig). Der Haus-Weg ist dann NICHT der Fremd-Code, sondern seine
Arbeitsteilung:

    Daten oeffentlich  ->  GATE deterministisch  ->  Urteil lokal  ->  Buch

## 1. Ein Zugang fuer alle: `Handel/llm_lokal.py`
- Ollama auf `127.0.0.1:11434`, nur `urllib` (das gemeinsame venv hat kein
  ollama-Paket). Kein Schluessel, keine Kosten, keine fremde Rechnung.
- **Nie `localhost` als Ollama-URL, immer die IP `127.0.0.1`.** `localhost`
  loest auf diesem Rechner auf `::1` (IPv6) auf, wo eine ANDERE, modell-lose
  Ollama-Instanz antwortet. Symptom: `/api/generate` liefert HTTP 404 `model
  '<name>' not found`, obwohl `ollama list` bzw. `/api/tags` ueber `127.0.0.1`
  das Modell klar zeigt - der Name ist richtig, nur der Host trifft die
  falsche Instanz. Jede NEUE Ollama-Anbindung (nicht nur `llm_lokal.py`,
  jeder Fremd-Code mit eigenem HTTP-Aufruf, z. B. `verbesserer/digest.py`)
  einmal gegen `http://localhost:11434/api/tags` UND `http://127.0.0.1:11434/api/tags`
  pruefen - liefert `localhost` eine leere Modell-Liste, ist das der Fehler,
  nicht das Modell oder der Modellname.
- **`think: false` ist Pflicht.** Mit Denken verbraucht das Modell das
  Token-Kontingent im Denken: `content` kam LEER zurueck (num_predict 80).
  Symptom: die Spur handelt nie, ohne Fehlermeldung.
- **Ollamas EIGENER `/v1`-Adapter ist eine Falle**: gegen dasselbe Modell
  liefert er IMMER leeren `content` (die Antwort steht im `reasoning`-Feld),
  auch mit `think: false` oben im Koerper. Nur die native `/api/chat` mit
  `think: false` und `stream: false` antwortet zuverlaessig. Wer einen
  Fremd-Agenten ueber das openai-SDK anbindet, muss den Aufruf auf `/api/chat`
  umschreiben (urllib reicht), sonst laeuft der Agent und faellt still auf den
  DO-NOTHING-Default zurueck - Symptom einer stummen Modellstrecke ist eine
  lange Folge identischer DO-NOTHING-Urteile ohne Fehlermeldung. **Die Regel
  gilt fuer OLLAMA, nicht fuer `/v1` an sich** - siehe den zweiten Dienst unten.
- **Ein ZWEITER Dienst laeuft NUR unter `/v1`** (llama.cpp/Prism-Fork, z. B.
  Bonsai 2 27B auf `127.0.0.1:8080`, Starter
  `Agenten/Werkzeuge/bonsai-27b.ps1`): `/api/chat` gibt es dort nicht (HTTP 404).
  `llm_lokal.py` kennt deshalb zwei Wege; gewaehlt wird der Weg je Spur in der
  `wachen.json` (`llm_weg: "bonsai"` / `"ollama"`), ohne das Feld entscheidet
  der Modellname (`bonsai...` oder ein `.gguf`-Pfad = zweiter Dienst). **Kein
  stiller Rueckfall:** schweigt der Dienst, faellt das Urteil aus und die Spur
  handelt nicht, statt heimlich auf ein kleineres Modell zu wechseln.
- **Denken ausschalten, aber in der Sprache DIESES Dienstes.** `think: false`
  ist ein Ollama-Feld und wird unter `/v1` ignoriert; bei einem Denk-Modell
  gehoert `reasoning_effort: "none"` in den Koerper - und `max_tokens`
  grosszuegig (512), weil das Denken gegen das Kontingent zaehlt (mit 250 kam
  eine LEERE Antwort zurueck, `finish_reason: length`). Am selben Prompt
  gemessen: mit `none` 1,5 s / 25 Token, ohne die Angabe 8,7 s / 236 Token.
  Ein Denk-Modell, das den Vertrag haelt, ist damit bezahlbar - der Vertrag
  selbst bleibt unveraendert streng gelesen.
- **Ollama hat auf dieser Maschine keinen Windows-Dienst.** Der Daemon
  stirbt mit der Sitzung, die `ollama serve` gestartet hat; dann antwortet
  Port 11434 nicht mehr und ALLE LLM-Urteile kippen still auf den
 DO-NOTHING-Default. Vor dem „Modell ist schlecht"-Urteil immer
  `Test-NetConnection 127.0.0.1 -Port 11434` pruefen und notfalls neu
  starten (Wrapper: `Agenten/Routinen/ollama-start.ps1`).
- `temperature: 0` + fester `seed`: dasselbe Marktbild -> dasselbe Urteil.
- **Vertrag wortgleich zum Bot** (`llm_lokal.VERTRAG`): genau 3 Zeilen,
  Zeile 1 `BUY`/`SELL`/`NOTHING`, Zeile 3 `Confidence: X%`. Streng lesen
  (`urteil()`): unbekannte erste Zeile = KEIN Signal, nie eine Richtung raten.
- **Nachfassen statt raten**: unlesbare Antwort einmal mit `NACHFASSEN`
  wiederholen (`llm_nachfassen: false` schaltet es ab). Danach: kein Handel.
- **Confidence ist ein GATE** (`llm_mindest_confidence`, Vorgabe 60 %).
- Zwischenspeicher (300 s) je Prompt: Vorschau-Frage und Papierlauf eines
  Zyklus sehen DASSELBE Urteil, der zweite Aufruf kostet nichts.
- Rueckgabe immer `(seite|None, info)`. Fehler = `None`. Kein Urteil ist kein
  Handel.

## 2. Modellwahl messen, nicht annehmen: `Handel/llm_probe.py`

**Die Sonde muss den Weg des BETRIEBS nehmen.** Sie rief frueher
`llm._echte_anfrage` direkt und damit immer Ollama; ein Modell auf dem zweiten
Weg wurde als "(leer) 0/6, 0,0 s" gemeldet, obwohl es antwortete - und die
Sonde empfahl daraufhin das falsche Modell. Richtig ist die gemeinsame
Aufloesung (`llm.weg_aus(modell)`), und der Denk-Schalter wird je Weg
uebersetzt (Ollama `num_predict`, zweiter Dienst `reasoning_effort`). Merksatz:
wer eine Modellwahl messen will, misst den Pfad, den die Spur wirklich geht -
sonst misst er die Sonde.

`--wiederholungen 2` fragt jedes Modell mit denselben drei Marktbildern
und zaehlt Vertragstreue erste Antwort / nach Nachfassen, Richtung, Dauer.
Gemessen 17.09.2026 (je 6 Aufrufe):

- qwen35-8k: 6/6 im Vertrag, kalt 7,4 s, warm 1,5 s
- qwen36-35b-a3b: 6/6, kalt 38,6 s, warm 7,5 s
- gemma-e4b-8k: 2/6 (nach Nachfassen 4/6 - antwortete "BS" statt SELL)
- bonsai (27B, ueber `/v1`, `reasoning_effort: none`): 6/6 im Vertrag (drei
  Marktbilder, je zweimal gefragt), kalt 1,3 s, im Mittel 1,3 s - und damit
  das einzige Modell hier, das den Vertrag genauso sicher haelt wie qwen35-8k,
  dabei aber 27B statt 4,3B beurteilt

Die Zeit steckt im LADEN, nicht im Urteilen. Vorgabe ist das schnellste Modell,
das den Vertrag vollstaendig haelt. `llm_modell` steht je Spur in der
`wachen.json` - wer ein zweites Urteil will, wechselt dort, nicht im Code.

## 3. GATE und Urteil trennen
Das Gate ist Haus-Code und nachrechenbar, nur die RICHTUNG kommt vom Modell.
Ausserdem spart es den Aufruf, und im Journal ist nachvollziehbar, wann
ueberhaupt geurteilt wurde:
- Wale: `|OI-Aenderung| >= max(mindest_aenderung_pct, 1.31 x mittlere absolute
  OI-Aenderung)` (1.31 = `WHALE_THRESHOLD_MULTIPLIER` des Bots).
- Liquidationen: die Spanne des Abrufs messen und die Summe darauf beziehen
  (USD/h) - OKX gibt nur die neuesten 100 Saetze heraus, ein festes Fenster
  waere leer oder unvollstaendig. Gate: Spanne frisch + Rate hoch +
  Ungleichgewicht deutlich.
- Schlagzeilen: Mindestmenge Text (Uebertragung der Bot-Schwelle 0.4).

## 4. Datenwege (oeffentlich, ohne Schluessel) - `Handel/moondev_daten.py`
- `okx_offenes_interesse`, `okx_oi_historie` (5-Min-Punkte, 48 h, neuester
  zuerst), `okx_kerzen` (liefert RUECKWAERTS - wird aufsteigend gedreht),
  `okx_liquidationen`.
- **`sz` bei Liquidationen ist in KONTRAKTEN**, nicht in Coins: USD erst ueber
  `ctVal` (BTC-USDT-SWAP = 0.01 BTC). Ohne diese Zahl sind alle Summen um
  Faktor 100 falsch.
- RSS: ueber `item` lesen. `//title` liefert den Kanalnamen als erste
  "Schlagzeile".

## 5. Tests (ohne Netz, ohne Modell)
- Seams: `quelle_override` (Daten), `urteil_override` (Urteil),
  `llm_lokal.ANFRAGE` (Rohtext), `llm.leere_cache()` in setUp/tearDown.
- Buchlauf gegen Temp-Ordner (`journal_zweitziel` in den Temp-Ordner!) +
  `setUpModule/tearDownModule`-Waechter ueber die Dateiliste des echten
  Spurenordners.
- Aufruf NUR aus `<spur>/tests`: `python -m unittest test_<spur>`.

## 6. Verdrahten - dieselben Stellen wie jede Spur
`dauerlauf.SPUREN`, `auswertung_alle.BOT_SPUREN`, `pruefe_ratschen.SPUREN`,
`tagesbericht` (Leser + HOLER), `befehle.FAMILIE` (eigene Familie
"Bot-Signal (LLM)", damit im Bericht sichtbar bleibt, wo ein Modell urteilte),
`.gitignore` (je Spur NUR `wachen.json` frei).

## Fallen (alle einmal getreten)
- **`.gitignore`: `!Agenten/Handel/<spur>/*.json` hebt die allgemeine Sperre
  `Agenten/Handel/*/zustand.mittel.json` auf** (letzter Treffer gewinnt) -
  die Laufzeitdatei liegt als `??` im Baum und waere beim naechsten
  `git add -A` im Commit. Immer nur `wachen.json` freigeben und mit
  `git check-ignore -v <spur>/zustand.mittel.json` gegenpruefen.
- **Bus-Test verlangt den Spurnamen WORTWOERTLICH in der gestarteten Datei.**
  Spuren ueber `spur_buch` banden den Bus korrekt, standen aber als "ohne
  Bus-Anbindung" (4 bestehende + 3 neue). Fix: `"handel/<spur>"` literal
  uebergeben statt `"handel/%s" % basename`, und die Pruefung zaehlt eine
  Kern-Bindung, wenn der Kern `ereignis.lauf` traegt.
- **Journal-Grund**: `spur_buch` schrieb fest "moondev_bot". Jetzt
  `w.get("_grund") or w.get("grund")`; eine LLM-Spur setzt `w["_grund"]` in
  `signal()` auf "<spur> llm BUY 72 %".
- **Textdateien byte-genau aendern** (LF): `git diff --stat` muss kleine
  Zahlen zeigen, sonst ist die ganze Datei neu geschrieben.
