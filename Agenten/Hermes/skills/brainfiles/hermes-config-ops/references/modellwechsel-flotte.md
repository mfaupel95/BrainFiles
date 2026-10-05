# Modellwechsel ueber viele Profile: was die Werkzeuge NICHT sagen

- **`git commit -- <pfade>` committet den ARBEITSBAUM dieser Pfade, nicht den
  Index.** Ein zuvor per `update-index` deterministisch gebauter Index wird von
  so einem Aufruf ignoriert - fremde Hunks in derselben Datei landen mit im
  Commit. Fuer "nur meine Zeilen" ohne Pathspec committen (`git commit`), davor
  `git diff --cached --name-only` lesen und gegen die eigene Absicht zaehlen.
- **Staged Eintraege koennen verschwinden, wenn eine zweite Sitzung committet:**
  ein `git commit` OHNE Pfadangabe committet den ganzen Index - die eigene
  Aenderung landet dann im fremden Commit (richtig, aber falsch beschriftet),
  oder ein `git add -A` der anderen Sitzung zieht sie mit. Deshalb: eigenen
  Index bauen, `git diff --cached --name-only` gegen die Absicht zaehlen und
  in DERSELBEN Sitzung committen - kein Zeitfenster dazwischen.
- **Der Kommentar-Schluss geht auch bei PROFIL-Configs verloren**, wenn
  `hermes config set` die Datei neu schreibt (gemessen: 38 Zeilen). Ein
  Profil, das nur "laeuft schon" ist, wird von einem Umstellungs-Werkzeug
  uebersprungen - seinen Schaden heilt dann niemand. Nach jeder Umstellung
  `git diff --numstat` JE Datei lesen: 2/2 ist richtig, hunderte Zeilen heissen
  gekippte Zeilenenden oder weggefallener Doku-Block.
- **Zeilenenden sind bei Profil-Configs gemischt.** Ein `hermes config set`
  schreibt LF-only; aus einem CRLF-Profil kopierte Bloecke bringen CRLF mit.
  Vor dem Einfuegen die ROHEN Bytes ansehen und die Zeilen einzeln behandeln
  (an Zeilenumbruch trennen und ein abschliessendes CR vor der Zeile abstreifen),
  nicht auf ein einheitliches Zeilenende vertrauen. `subprocess(... text=True)`
  wandelt CRLF still nach LF und baut dann eine LF-Kopie der ganzen Datei.
- **Beim Ersetzen von Text mit Backslashes (Windows-Pfade, `\r\n`, Regex) das
  Patch-Werkzeug nicht benutzen.** Es deutet Escapes: eine Zeichenfolge wie
  Backslash-r-Backslash-n landet als echter Zeilenumbruch MITTEN im Satz, und
  wer den Anker der Ersetzung nicht im Ersatztext wiederholt, loescht die
  Ueberschrift mit. Byte-genau per Skript schreiben (Bytes lesen, ersetzen,
  schreiben, `count == 1` asserten) und die geaenderte Stelle danach noch
  einmal lesen — ein gelungener Patch ist kein Beleg fuer sauberen Text.
  **Es kippt ausserdem die Zeilenenden der Region, die es anfasst:** in einer Datei
  mit GEMISCHTEN Enden (ein Teil LF, ein Teil CRLF — Normalfall bei einer Datei, die
  eine andere Sitzung per `config set` angefasst hat) schreibt es den beruehrten
  Abschnitt geschlossen auf CRLF, gemessen 64/61 an einer README, in der EINE Zeile
  gemeint war. Deshalb `git diff --numstat` NACH JEDER EINZELNEN Aenderung lesen,
  nicht erst am Ende eines Stapels: stimmt die Zahl nicht, `git show HEAD:<pfad> >
  <pfad>` (nur wenn die Datei ausschliesslich die eigene Aenderung traegt) und mit
  dem byte-genauen Skript neu setzen — danach muss die Zahl der Absicht entsprechen
  (drei eingefuegte Zeilen = `3 0`).
  **Der Skript-Weg selbst, damit keine Escape-Sequenz als echter Umbruch landet:**
  den Text erst auf LF normalisieren (`raw.replace(b"\r\n", b"\n")`), das
  Zeilenende der ANKERZEILE bestimmen (endet sie auf `\r\n`, dann dieses, sonst `\n`)
  und beim Schreiben die neuen Zeilen mit genau diesem Ende setzen.
  **Der Suchtext braucht dasselbe Zeilenende wie die DATEI** - ein mehrzeiliger
  Suchblock, im Skript mit `\n` geschrieben, trifft eine CRLF-Datei **null** mal;
  das Symptom ist `count == 0` bzw. der Abbruch "Anker trifft 0 mal", und der
  naechste Verdacht (falscher Wortlaut, Wert anders geschrieben) ist dann falsch.
  Vor dem Suchen einmal `nl` aus den Rohbytes ableiten und den Suchtext damit
  erzeugen (`alt = ALT.replace("\n", nl)`), statt den Treffer zu bedauern. Mehrere Zeilen
  hinter einer Ankerzeile einhaengen heisst: Index der Marke suchen, dann das naechste
  `\n` — den Anker NICHT mit einem Zeilenumbruch im Suchmuster schreiben (trifft sonst
  nicht, und in der Datei selbst kein `\n` in einem String-Literal bilden, das als
  Text gemeint ist.
  **Im eigenen Skript die Windows-Pfade als Raw-String schreiben** (`r"…"` oder
  verdoppelte Backslashes): ein einteiliger Pfad in einem normalen String-Literal
  frisst Escape-Sequenzen — aus `Handel\auswertung_alle.py` wird `Handel` + BEL +
  `uswertung_alle.py` (\a), waehrend \H, \W und \k einfach stehen bleiben; das
  faellt erst auf, wenn die geschriebene Datei gelesen wird (eine Zeile mitten im
  Text ist still kaputt). Nach jedem solchen Schreibvorgang die Steuerzeichen
  zaehlen: `[hex(ord(z)) for z in text if ord(z) < 32 and z not in "\r\n\t"]` muss
  leer sein.
- **Beim Ersetzen eines Modellnamens ueberall: den KATALOG-Eintrag ZUERST entfernen,
  sonst entsteht ein stilles Duplikat.** Ein Modell-Katalog (`providers.nous.models`)
  fuehrt jede Modell-ID als `name: {}`. Ersetzt man den alten Namen per blanket-replace,
  wird auch der Katalog-Eintrag umgeschrieben — und wenn das Zielmodell dort schon steht,
  hat die Datei danach ZWEI Eintraege mit demselben Key. YAML gewinnt still den LETZTEN
  Key, ein Duplikat faellt erst beim Lesen auf. Reihenfolge im Skript: Katalog-Eintrag
  entfernen, DANN blanket-replace, DANN `yaml.safe_load` + `set(cfg) == vorher` gegenpruefen.
- **Das Patch-Werkzeug kann eine Datei so zerschiessen, dass weiterpatchen sinnlos ist —
  dann loeschen und frisch schreiben.** Bei einem mehrzeiligen Block-Ersatz verschob es die
  Einrueckung (IndentationError) UND injizierte einen Tippfehler in den Ersatztext
  (`Zn_alt` statt `ZIEL`), und `write_file` verweigerte danach das Ueberschreiben wegen
  "partial view". Nach dem zweiten Fehlschlag nicht ein drittes Mal patchen: `rm` +
  `write_file` mit dem vollstaendigen, korrekten Inhalt ist der Weg. Der Fuzzy-Match des
  Patch-Werkzeugs wendet Tippfehler im old_string trotzdem an — bei Python-Code nach jedem
  Patch `py_compile` laufen lassen, nicht nur auf den Diff schauen.
- **`bot-modell-auf-nous.py --auch-lokale` greift auch lokale Provider.** Ohne den
  Schalter bleiben `llamacpp`/`docker`/`ollama` stehen (Grund: sie brauchen keine
  Anmeldung). Beim Umstellen MUSS das lokale `model.base_url` (z. B.
  `http://127.0.0.1:18434/v1`) mit weg, sonst zeigt der Nous-Aufruf weiter auf den
  lokalen Endpunkt — das Werkzeug entfernt es und prueft nach. Gemessen 21.09.2026:
  17 Profile, `openmontage` (llamacpp mit CLIP-mmproj, als Hauptmodell gar nicht
  ladbar) und `awesome-systematic-trading` (docker) waren die letzten zwei.
- **Die LF-Falle sitzt IN `kommentar_schluss_zurueckholen()` selbst.** Es las die
  Sicherung mit `read_text()` (ohne `newline=""`) und schrieb mit `newline=""`:
  der zurueckgeholte Block kam als LF in eine CRLF-Datei, der Diff zeigte die
  ganze Datei (5 von 17 Profilen). Der ganze Vorgang gehoert auf BYTES
  (`read_bytes`, Endung aus den Rohdaten ableiten, `write_bytes`) — so repariert,
  mit isoliertem Test gegen eine Fixture. Bestandsdateien heilt
  `scripts/zeilenenden-zuruecksetzen.py <pfad>`; wenn neue Zeilen keine
  HEAD-Vorlage haben, normalisiert `scripts/zeilenenden-auf-head-format.py` die
  GANZE Datei auf die Endung aus `git show HEAD:<pfad>`.
- **Die Einrueckungstiefe ist ein Dateieigenschaft, keine Hauskonvention.**
  Profil-Configs setzen Top-Level-Schluessel auf Spalte 0 und ihre Skalarfelder
  mit ZWEI Leerzeichen darunter (`delegation:` / `  provider: nous`), waehrend
  die Hauptkonfiguration Schluessel mit zwei und Felder mit vier Leerzeichen
  fuehrt. Ein Ersatzzblock aus dem einen Haus im anderen sieht richtig aus und
  parst nicht: YAML bricht mit `expected <block end>` ab, und weil die
  Gegenprobe erst NACH dem Schreiben greift, ist der Schaden schon auf der
  Platte - der Schluessel ist dann ein String statt eines Blocks, und alle
  nachfolgenden Felder werden verschluckt. Deshalb **zwei Regeln**:
  (a) die Tiefe vor dem Lauf an EINER Datei messen (`head -20`, Einrueckung der
  Kinder zaehlen), sie als Parameter durch den Block-Detektor geben und nicht
  als Konstante setzen; (b) den Ersatzzblock **allein stehend** parsen, bevor
  irgendeine Datei angefasst wird - `yaml.safe_load("\\n".join(block + zu_behalten))`
  und die erwarteten Felder asserten. Rollback ist byteweise aus den
  `.bak-JJJJMMTT` (alle zurueckspielen), und der Beleg dafuer ist
  `git status --porcelain -- <pfade>` **leer** - nicht die Tatsache, dass der
  Assertion-Fehler kam.
- **Ein Trockenlauf, der "keine Aenderung" meldet, obwohl Dutzende erwartet
  sind, ist ein Fehlbefund des Suchers, keine Auskunft ueber die Datei.** Die
  Ursache ist fast immer das abschliessende `\r`: `text.split("\\n")` laesst es
  an JEDER Zeile stehen, und `line.startswith("  delegation:")` trifft dann
  null mal, ohne Fehler zu werfen. Nach dem Split also jede Zeile auf ein
  abschliessendes `\\r` pruefen, oder von Anfang an ruest-schnell ueber
  `splitlines()` gehen. Ein leerer Trockenlauf bei erwartetem Befund ist das
  Signal, die Erkennung zu pruefen, nicht die Absicht, "nichts zu tun".
- **`HERMES_HOME` auf ein Profil zu setzen bricht die Profil-Werkzeuge.** Die
  Profil-Wurzel ist am **Hermes-Root** verankert (`hermes_cli/profiles.py::
  _get_profiles_root` -> `get_default_hermes_root()`, das aus `HERMES_HOME` den
  Root bildet), nicht am jeweils gesetzten Home. Mit `HERMES_HOME=<root>
  /profiles/<name>` meldet `hermes -p <name> ...` "Profile does not exist" und
  richtet vorher noch eine Dependency-Installation im Profil aus. Fuer
  profilbezogene Abfragen immer die Wurzel-Form `-p <name>` nehmen und
  `HERMES_HOME` unveraendert lassen.
- **Ein Bot auf `terminal.backend: docker` stirbt mit einer irrefuehrenden
  Meldung.** Ist der Docker-Daemon langsam, laeuft der 5-Sekunden-Probe
  (`docker version`) in `TimeoutExpired`, der Lauf bricht ab und der Client sagt
  nur "Switch to a different model with `/model`" — der Verdacht faellt auf das
  Modell, obwohl der TERMINAL-Backend das Problem ist. Vor dem Modellwechsel
  pruefen: `terminal.backend` muss bei Repo-Bots `local` sein (Hausstandard);
  `docker` gehoert nur zu einer bewussten Container-Spur.
