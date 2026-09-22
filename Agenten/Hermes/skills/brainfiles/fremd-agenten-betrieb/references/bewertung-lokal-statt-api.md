# Ein Fremd-Repo bewertet mit einem bezahlten Modell — Urteil lokal faellen

Ausloeser: „<Repo> auf lokales Ollama", „die Bewertung laeuft nicht, der Schluessel
hat kein Guthaben", „das Urteil soll lokal fallen".

## 1. Zuerst die NAHT suchen, nicht den Anbieter tauschen

Viele Fremd-Repos mit LLM-Urteil bringen schon einen schluessellosen Weg mit.
Suchen, BEVOR Code umgebaut wird:

- CLI-Flags: `grep -rn "\-\-export\|\-\-import\|manual" <paket>/cli.py`
- ein `SCORER`/`PROVIDER`-Schalter in `config.py` mit den Werten `api|manual|auto`
- ein eigener Satz Regeln als Konstante (`SYSTEM = """..."""`) und ein
  Ergebnis-Schema (`models.<X>Result`) — beides sind die Schnittstellen, die die
  Naht ohnehin benutzt.

Faellt so ein Weg, ist der Umbau des Fremd-Repos verboten: es ist dessen Naht,
sie bleibt bei einem `git pull` des Upstreams heil, und das Urteil sieht aus wie
das der API. Das Haus-Werkzeug liegt NEBEN dem Repo (`Agenten/Werkzeuge/`) und
liest Prompt, Schema und Regeltext per Import AUS dem Repo (eine Quelle, keine
Kopie) — sonst driften Regeln und Format still auseinander.

Nur wenn es KEINE Naht gibt, wird der Anbieter im Repo ersetzt — und dann nach
`references/lokale-bildkette.md` / den Regeln dieses Skills (toter Schluessel in
der `.env` zuerst entfernen, sonst gewinnt der tote Weg).

## 2. Der Aufruf des Repos gehoert uns, nicht dem Fremdcode

Das Werkzeug ruft das Repo-CLI als Unterprozess mit der Umgebung des Repos:

- Interpreter ist IMMER der Repo-venv (`<repo>/.venv/Scripts/python`), weil das
  Werkzeug das Repo-Paket importiert (Schema/Klassen) — der Haus-Python kennt es
  nicht.
- `PYTHONIOENCODING=utf-8` setzen (Windows, cp1251-Mojibake bei Token-Namen).
- Den manuellen Modus ERZWINGEN (`SCORER=manual` o. a.), sonst nimmt das Repo bei
  vorhandenem Schluessel den toten API-Weg.
- Parameter, die das Werkzeug braucht, die das Repo aber nicht ausgibt: das
  Repo schreibt seine Zwischendatei selbst — Pfade als Argument mitgeben und
  sie AUSSERHALB des Fremd-Klons ablegen (`Agenten/Hermes/cache/<thema>/`),
  damit `git status` im Klon sauber bleibt (untracked Dateien im Fremd-Repo
  fallen sonst bei jedem `git add` auf).

## 3. Lokales Urteil: Schema zuerst, dann bitten, dann fallen lassen

- `format` = das JSON-Schema des Repos direkt an `/api/chat` mitgeben; der
  kleine Ollama-Server haelt es erstaunlich gut (gemessen: 16/16).
- `think: false`, `temperature: 0`, fester `seed`, `num_predict` gross genug
  (ein 2-3-Satz-`summary` plus JSON braucht ~250 Token; 200 als Vorgabe des
  Haus-Moduls `llm_lokal.py` ist zu knapp — hier 700).
- **Drei Stufen statt Raten**: Schema → `format="json"` → freier Text mit
  `{...}`-Ausschnitt; danach faellt der Datensatz AUS und wird gezaehlt
  (`unlesbar`). Ein geratenes Urteil ist schlimmer als keines.
- Nach jeder Stufe gegen die PYDANTIC-Klasse des Repos validieren, nicht gegen
  eine eigene Regel — Enums und Grenzen (`0..100`) liegen dort.
- Nie die Adresse/ID mit ins Modell schicken und zurueckkopieren: das Modell
  liefert nur das Urteil, den Schluessel setzt der Aufrufer wieder ein.

## 4. Nachweis, der traegt

- Erst `--trocken` (rechnen, nichts schreiben), dann echt importieren.
- Zwei Laeufe muessen DIESELBEN Punktzahlen liefern (temperaturfrei) — sonst ist
  das Urteil nicht nachrechenbar.
- Rueckgabe-Zaehler des Imports lesen: `{'imported': N, 'invalid': 0,
  'unknown_address': 0}`, danach in der Datenbank GEGENZAEHLEN
  (`select ai_model, count(*) ...`) und einen fertigen Bericht des Repos zeigen,
  in dem die Urteile auftauchen.
- Zeit mitliefern (Sekunden je Datensatz), damit klar ist, ob das Verfahren fuer
  den Takt einer Routine taugt. Gemessenes Muster: 4,3B-Modell ≈ 1,5-2 s warm je
  Wallet, 5-7 s kalt; lange Einzelwerte (≈10 s) kommen von Nachladen, nicht von
  groesserer Arbeit.

## 5. Tests ohne Netz

Zwei Nahten am Werkzeug, beide im Modul als `None` vorbelegt:

- `ANFRAGE(prompt, modell, format, zeitgrenze)` → Text (Ollama),
- `LAUF(args, trocken=...)` → `{rc, ausgabe}` (Repo-CLI).

Damit sind pruefbar: die Stufenfolge der Formate, ein Schemaverstoss (faellt aus,
zaehlt `unlesbar`), toter Ollama (`ollama_tot`), der Trockenlauf (kein Import),
Adress-Filter, leere Warteschlange (Exit 0) und „unbekannte Adresse → SystemExit".
Zusaetzlich per Quelltext-Pruefung festnageln, dass die Umgebung des Repo-Aufrufs
`SCORER=manual` und `PYTHONIOENCODING=utf-8` setzt — das ist die Zeile, die sonst
still auf den toten API-Weg zurueckfaellt.
