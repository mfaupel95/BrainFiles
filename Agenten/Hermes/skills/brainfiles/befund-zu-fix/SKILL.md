---
name: befund-zu-fix
description: "Aus einem Symptom einen belegten, geprueften Fix machen."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Befund, Diagnose, Fix, Gegenprobe, Betrieb, BrainFiles]
    related_skills: [trugschluesse, code-audit, betriebsrunde, handel-spuren, messwerkzeug-gegenprobe]
---

# Befund zu Fix — ein Symptom wird zu einem geschlossenen Vorgang

Nimmt einen **kurzen, ungenauen Befund** („X nicht lesbar, behebe das") und
fuehrt ihn zu Ende: finden, was der Satz wirklich behauptet, die falsche
Haelfte aktiv zuruecknehmen, die echte Luecke schliessen, jeden Schritt
belegen, getrennt sichern, den Aufgabeneintrag ziehen. Er ist **kein Audit**
(`code-audit`), **kein Beleg-Werkzeug** (`trugschluesse`) und **kein
Sammellauf** (`betriebsrunde`) — er ist der Weg von einem Satz zu einem
geschlossenen Vorgang.

Zwei Dinge, die diesen Weg von einer normalen Fehlersuche unterscheiden:
erstens ist der Satz selbst **meistens halb falsch**, und zweitens ist eine
Pruefung, die **niemand aufruft**, bereits der Befund — nicht der Fix, den
man braucht.

Der Fall, aus dem das hier destilliert ist, steht als ganze Sitzung in
`references/fall-0510.md` (laden mit
`skill_view(name='befund-zu-fix', file_path='references/fall-0510.md')`).

## When to Use

- ein einzeiliger Befund ohne Ort, ohne Datei, ohne Zahl: „nicht lesbar", „geht
  nicht", „passt nicht", „mach das weg"
- eine Meldung, die **im Haus** steht (Log, Zustand, Bericht, Wache) und deren
  Ursache unbekannt ist
- „das ist behoben" steht im Raum und niemand weiss, ob es stimmt
- eine Pruefung oder ein Werkzeug wird nur von Hand gefahren
- eine Fehlermeldung nennt ein **Werkzeug oder einen Ort** — dort weiterarbeiten,
  nicht neu suchen

**Don't use for:** eine breite Bug-Suche (`code-audit`), eine Zustandsaussage
belegen (`trugschluesse`), eine Handelsspur anbinden (`handel-spuren`).

## Prerequisites

- Aus der Repo-Wurzel `C:\Users\faupe\Documents\BrainFiles` arbeiten; das
  `terminal`-Werkzeug laeuft in bash/MSYS. Host-Fragen ueber
  `mcp__windows_mcp__PowerShell`.
- Fuer den Handelsteil: der Spurordner traegt seinen **eigenen** Python
  (`../scanner/.venv/Scripts/python.exe` aus dem Spurordner aufrufbar).
- **Keine** Geheimnisse ausgeben. Existenz messen
  (`[Environment]::GetEnvironmentVariable('NAME','User')`), Laenge nennen.

## How to Run

Der Ablauf ist eine Kette, und jeder Schritt kann stoppen:

1. Den Satz **als Behauptung** behandeln und ihre Fundstelle suchen
2. Messen, was dort wirklich gemeldet wird
3. In **falschen Teil** und **echte Luecke** teilen
4. Die echte Luecke schliessen — mit dem kleinsten Weg, der im Betrieb laeuft
5. Gegenproben, echter Betrieb, getrennter Commit, Aufgabeneintrag

## Quick Reference

| Der Satz klingt wie | Der Befund ist meistens | Erstbeleg |
|---|---|---|
| „X nicht lesbar" | ein **falscher Endpunkt**, nicht ein fehlender Weg | den Endpunkt der zuständigen **Dienststelle** nachschlagen, nicht raten |
| „X wird nicht geprüft" | eine Pruefung, die **niemand aufruft** | `search_files` nach dem Aufrufer der Funktion |
| „der Fix wirkt" | der **erste** Teilschritt | die **letzte** Stufe der Kette messen (`trugschluesse`) |
| eine rote Suite | eine **kaputte Pruefung** oder ein echter Fehler | auf `HEAD` zuruecknehmen, Suite erneut fahren |
| „nichts passiert" | ein **veralteter Hintergrundlauf** | Zeitstempel der Ausgabedatei gegen die Reparatur |

## Procedure

### 1. Der Satz ist eine Behauptung, kein Befund

„Schutz-Stop nicht lesbar" nennt **weder Datei noch Ort**. Der Satz kann
alles heissen: ein falscher Endpunkt, ein toter Werkzeugpfad, eine falsche
Quelle, ein veralteter Lauf. Die Reihenfolge ist fest, weil jede fruehere
Fehlermeldung an dieser Stelle eine Fehldeutung erzeugt hat:

```bash
cd /c/Users/faupe/Documents/BrainFiles && git --no-pager grep -n -i "nicht lesbar" -- '*.py'
```

Dann die **Autoren** der Treffer (welche Datei, welcher Aufrufer) und
schliesslich **Ausgabe-Dateien und Logs**, in denen der Satz real gelandet
ist. Der Satz, den man beheben soll, ist meist der in einem **Werkzeug**, nicht
der im Betrieb — zweimal war er im Betrieb schon behoben und im Werkzeug
weiterhin im Text.

### 2. Was wird dort wirklich gemeldet

Den **Code lesen, der die Meldung erzeugt**, und die Frage stellen, die er
gerade beantwortet. Ein Werkzeug, das „nicht lesbar" sagt, koennte zwei
verschiedene Dinge meinen: die Abfrage ging nicht, oder **die Abfrage ging an
die falsche Stelle**. Beides sieht in der Ausgabe gleich aus.

Gemessen 05.10.2026: `requiredArgumentMissing` von Kraken Futures wurde als
„fehlende Funktion" gelesen. Es war der **Spot**-Endpunkt, der auf einem
Futures-Weg aufgerufen wurde; der Futures-Dienst kannte den richtigen Weg die
ganze Zeit (`offene_orders()`, Zeile 306). **Ein Fehlercode der Boerse ist
eine Antwort ueber die Adresse, nicht ueber die Faehigkeit.**

Gegenprobe: denselben Aufruf mit **drei** Varianten wiederholen (ohne
Parameter, mit Filter, als GET mit Query und als POST mit Koerper) und die
Antworten vergleichen. Bleiben sie identisch, ist es kein Parameterproblem.

### 3. In falschen Teil und echte Luecke teilen

Das ist der Schritt, der in diesem Haus die meiste Zeit fehlte. Ein Symptom
hat oft **zwei Ursachen**: eine, die man selbst erfunden hat (der falsche
Endpunkt), und eine, die real ist (der Weg fehlt im Betrieb). Beide gehoeren
in den Abschluss, aber nur eine wird repariert.

Formen der Antwort — und keine davon darf fehlen:

- **Falsche Behauptung, aktiv zuruecknehmen.** Nicht stillschweigend ersetzen,
  nicht als „kleinere Korrektur" verstecken. Im Commit und im Bericht: was ich
  behauptet hatte, was gemessen ist, warum das eine und nicht das andere.
- **Echte Luecke, mit ihrer Zahl benennen.** „145 Kontrakte an der Boerse,
  126 geschuetzt — 19 bis zur Liquidation." Eine Luecke ohne Zahl ist eine
  Behauptung.

### 4. Die Luecke schliessen: im Betrieb, nicht auf Abruf

Die entscheidende Frage lautet: **wer ruft das auf?** Eine Pruefung, die nur
startet, wenn ein Mensch sie eintippt, meldet eine Luecke nur dann, wenn sie
zufaellig aufgefaellt wird. Gemessen: `handeln.py` schrieb bei einer
uebernommenen Position „fehlt — Order setzt nur der Live-Lauf (Werkzeug
stopdeckung.py)", und `stopdeckung.py` wurde nur gefahren, wenn jemand daran
dachte.

Also: die Rechnung an den Ort haengen, der ohnehin jeden Zyklus laeuft
(`buche_abgleich()`, `pruefe_ausstiege()`, der Live-Zweig), nicht an einen
neuen Aufruf. Kosten je Zyklus: **eine Boersenabfrage**.

Zwei Grenzen, die dabei gelten:

- **Nichts stellen, dessen Preis niemand genannt hat.** Ein Notausstieg ist
  eine Order. Ein geratener Schutzpreis ist eine Order, die jemand nicht
  bestellt hat. Die Zyklus-Stufe liest und meldet; das Nachsetzen bleibt ein
  Werkzeug mit einem Pflicht-Schalter (`--stop`), das ohne Schalter **nichts**
  tut. Merksatz: *ein geratener Notausstieg ist teurer als eine gemeldete
  Luecke.*
- **„Unbekannt" ist ein dritter Zustand.** Ein Abruf-Fehler ist nicht „kein
  Stop". Die Funktion gibt deshalb `(befunde, abfrage_ok)` zurueck, und der
  Aufrufer darf aus `abfrage_ok=False` **keinen** Befund ableiten.

Und: **ein gesetzter Auftrag ist kein Beweis.** Nach dem Nachsetzen ein zweites
Mal mit der Menge messen — sonst meldet der Nachsatz Erfolg, obwohl die
Boerse nur die Haelfte nimmt.

### 5. Beim Einfuegen zwei eigene Fehler erwarten

Eine bestehende Funktion in einen laufenden Pfad einzuhängen erzeugt fast
immer etwas Neues. Diese drei kamen vor:

- **Import-Zirkel.** A importiert B, und A soll jetzt `B.f()` aufrufen. Der
  Weg ist ein **verzoegerter Lader** (`_lade()`), nicht ein `import` im
  Rumpf. Zirkel laeuft nicht als Fehler, sondern als halbfertige Instanz.
- **`sys.path`-Reihenfolge.** Zwei gleichnamige Module in zwei Spuroerdern
  (`scanner/handeln.py` und `xperp/handeln.py`): `if p not in sys.path`
  laesst den Pfad-Insert aus, und der falsche gewinnt. Das Pflicht-Insert
  machen und **einen Guard mit `assert os.path.dirname(modul.__file__)`**
  direkt daneben — er zeigt den Fehler statt ihn zu verstecken.
- **Die Testnaht verschwindet.** Wenn 21 Tests `modul.okxf = attrappe`
  setzen, den Import aber spaeter kommt, faellt alles mit
  `AttributeError`. `__getattr__` (PEP 562) haelt den Namen lesbar, ohne den
  Import zu erzwingen — das ist die kleinste Aenderung an der Testsuite.

Ein vierter, teurer: **ein Skript mit `open(p,'w')` schneidet die Datei beim
Oeffnen ab**, bevor die erste Assertion fallen kann. Deshalb immer `open(p,'rb')`
und am Ende `open(p,'wb')`; und **nicht** `git checkout HEAD -- <datei>`, wenn
eine andere Sitzung darin arbeitet — aus einer Sicherung oder byteweise
zurueckholen.

### 6. Gegenproben: der Fix muss fallen koennen

Zwei Arten, beide billig, beide Pflicht:

```bash
# (a) Code zuruecknehmen - der neue Test muss rot werden
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel/xperp && \
  ../scanner/.venv/Scripts/python.exe -m unittest tests.test_deckung_zyklus

# (b) am ECHTEN Konto eine kuenstliche Luecke erzeugen (nur im Speicher)
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel/xperp && \
  MAXHIRN_ROUTINE=1 ../scanner/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'.')
import handeln as h
z = h.lade_zustand()
for p in z['positionen']:
    if p.get('inst','').startswith('MON'): p['kontrakte'] = 2100.0
b, ok = h.bueche_stopdeckung(z, {}, live=False, still=False)
print('Befunde:', len(b), '| lesbar:', ok)"
```

Erwartet: `UNGESCHUETZT 104.0` und **keine** Order. Ein Fix ohne fallende
Gegenprobe prueft nichts. Ein Test, der auch ohne den Fix gruen ist, ist kein
Test.

Nach dem Lauf: `git diff --numstat` je Datei (eine Zeile geplant = wenige
Zahlen, ganze Datei = Zeilenende oder Kodierung verstellt) und
`spiegelstand.py`, wenn ein Buchpfad beruehrt wurde.

### 7. Getrennt sichern und den Aufgabeneintrag ziehen

Der Arbeitsbaum gehoert allen Sitzungen. Im `terminal` den echten Index **lesen**
(`git diff --cached --numstat`) und bei fremden Pfaden mit einem eigenen Index
committen:

```bash
cd /c/Users/faupe/Documents/BrainFiles && export \
  GIT_INDEX_FILE="C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/cache/scratch/idx_<thema>" && \
  git read-tree HEAD && git add <nur eigene pfade> && \
  git diff --cached --numstat && \
  git commit -F "C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/cache/scratch/commitmsg_<thema>.txt"
# Pflicht danach:
unset GIT_INDEX_FILE && git add <eigene pfade>
```

Beim `git add -A` oder `git commit` ohne Pfadangabe nimmt der Commit die
vorgemerkten Aenderungen einer **parallelen Sitzung** mit. Beim
`git commit -- <pfad>` committet Git den **Arbeitsbaum**-Inhalt statt des
Index — dann wandert laufende Arbeit einer anderen Sitzung mit.

Den Aufgabeneintrag **im selben Auftragsumfang** ziehen, mit dem
Aufgaben-Skill (`aufgabenliste-pflegen`) und nur wenn `TASKS.md` nicht juenger
als 10 Minuten ist (sonst gehoert sie einer anderen Sitzung). Hoechste Nummer
frisch aus der Datei lesen, nie aus dem Gedaechtnis — parallele Sitzungen
vergeben sonst dieselbe Nummer zweimal.

**Beleg mit Backticks geht nicht als Kommandozeilenargument**: die Bash loest
sie als Kommandoersetzung auf, der Text kommt zerhackt an, und das Werkzeug
meldet trotzdem „ok". Beleg in eine Datei schreiben und den Aufruf als
**Kindprozess ohne Shell** starten (`subprocess.run([python, script, beleg])`).

### 8. Bericht in dieser Reihenfolge

1. **Was jetzt konkret funktioniert** — mit Beleg (Zeile aus dem Lauf, Zahl vom
   echten Konto)
2. **Was absichtlich NICHT angefasst wurde** — Fremdarbeit (namentlich),
   laufende Zyklen, fremde Spuren, keine Freigabe geaendert
3. **Welche Entscheidung offen bleibt** — genau eine, mit Begruendung
4. **Ein naechster Schritt unter zwei Minuten**

## Pitfalls

- **Ein veralteter Hintergrundlauf sieht aus wie ein Befund.** Ein
  `FAILED`, der Minuten spaeter eintrifft, gehoert zu einem Lauf von **vor**
  der Reparatur. Immer den aktuellen Lauf wiederholen, bevor man auf eine
  Meldung reagiert — und nie in der Antwort auf einen toten Lauf reagieren.
- **Die Zahl 0 ist ein Befund, wenn sie genau passt.** „0 Befunde" bei
  zwei Positionen kann richtig sein und kann eine kaputte Abfrage sein.
  Gegenprobe: eine kuenstliche Luecke erzeugen (Schritt 6b) und die Zahl
  springen sehen.
- **Ein Werkzeug, das den Nutzer bedienen soll, wird zum neuen Werkzeug.**
  Wenn der alte Aufrufweg im Code bleibt, produziert er dieselbe falsche
  Meldung weiter — auch wenn die Kernfunktion repariert ist. Beide Stellen
  pruefen (`search_files` nach dem Endpunkt-Namen, nicht nur nach der
  Funktion).
- **Ein Test gegen ein festes Dikt bricht bei jeder Erweiterung** und trainiert
  den Reflex, rote Tests wegzuklicken. Auf die **Eigenschaft** pruefen: keine
  Zaehlung ungleich 0, Buch unveraendert, `abfrage_ok` False. Sonst wird die
  korrekte Erweiterung als Fehler gemeldet und die Suite wird „repariert",
  indem man die Pruefung abschwaecht.
- **Der Bericht nennt die groesste Zahl nicht.** „0 Befunde" bei einer
  Position mit 1996 Kontrakten ist eine Zahl ohne Aussage; die Aussage ist
  „67/67 und 1996/1996 gedeckt".
- **Eine Stufe hinter einem fruehen `continue` ist toter Code.** Die neue
  Deckungspruefung stand zuerst hinter `if wirksam: continue` — also genau in
  dem Zweig nicht, den der Betrieb nimmt. Der Test wurde rot und hat es
  benannt. Eine Regel gehoert an **jeden** Weg, der dieselbe Sache entscheidet.
- **Eine Null, die plausibel ist, ist gefaehrlicher als ein falscher Wert.**
  Kraken nennt dasselbe Paar als `XXBTZEUR` (Register) und `XBTEUR`
  (OpenOrders); der Lookup liefert `base=None` und damit null Treffer. Der
  Bericht las sich wie „kein Stop an der Boerse". Wenn eine Abfrage **alles**
  leer liefert, ist die **Abfrage** der Befund — nicht der Bestand
  (`code-audit`, vierter Filter).
- **Fremde Auftraege zaehlen zur Deckung und werden nie angefasst.** Fuenf
  Stops auf demselben Instrument, vier von einer Nachbarspur: die Position
  ist gedeckt, die vier bleiben unberuehrt. Ein Abgleich, der fremde Stops
  anfasst, ist ein Aufraeumer mit Boersenzugriff.
- **Die Aufloesung gehoert an EINE Stelle.** Beide Paar-Schreibweisen kann
  `spot_stops.muenze_aus_paar()`; eine eigene Regel im Abgleich waere die
  dritte Fassung derselben Wahrheit. Und sie ist nicht vollstaendig: `_PRAEFIX`
  fuehrt `XXBT, XBT, XETH, XXLM, XXRP, XZEC, XDG` — `XADA` bleibt `XADA`.
  Wer die falsche Form als die richtige haelt, bekommt bei jeder zweiten
  Muenze einen leeren Befund.
- **Die Toleranz steckt im Ergebnis, nicht im Vergleich.** Eine Rechnung, die
  `1e-9` von der Differenz abzieht, damit eine Lot-Rundung nicht als Luecke
  meldet, liefert `2,859e-06` statt `2,860e-06`. Ein Test, der auf die
  gerundete Zahl prüft und „fast gleich" findet, hat beide Zahlen im Kopf
  und keine in der Datei.
- **Ein Testfehler ist auch ein Befund.** Zwei meiner Tests behaupteten Dinge,
  die das Haus nicht tut (`XADA -> ADA`, gerundete Luecke). Sie wurden auf die
  **gemessene** Regel umgebaut statt weicher gestellt — ein Test, der eine
  Falschaussage festschreibt, ist eine zweite falsche Wahrheit.
- **Ein Werkzeug, das eine Shell braucht, um eine Datei zu lesen, prueft sein
  eigenes Argument nicht.** Der Trockenlauf meldete „ok" mit zerhacktem Beleg.
- **Zwei Spuren mit gleichem Modulnamen** sind die Standardfalle beim Einfuegen
  in eine fremde Spur — der `assert`-Guard daneben ist Pflicht, nicht Kosmetik.
- **Eine datierte Notiz, die konkrete Zeilen oder Werte nennt, ist eine
  Hypothese, kein Beleg.** Eine Gedaechtnis-Notiz sagte „drei
  verkauf_von_hand-Zeilen = Phantom-Peak", gemessen hatte NUR eine davon
  nominal==margin, die anderen beiden Phantome lagen woanders. Bevor eine
  Zahl aus einer Notiz korrigiert oder berichtet wird: die Zeilen frisch aus
  der Datei ableiten (Fingerabdruck: `nominal_usd == margin_usd` bei
  schliessen). Wer der Notiz glaubt, korrigiert die falsche Zeile und laesst
  die echte stehen.
- **Ein `.bak` im beschriebenen Ordner ist kein Beweis.** Der Dauerlauf
  schreibt das Journal weiter, waehrend man es korrigiert; ein lokaler
  `.bak` kann verschwinden und ein Byte-Vergleich gegen ihn prueft dann
  nichts. Der dauerhafte Zeuge einer Buchkorrektur ist die
  Bedingung-4-Kopie: nach dem Schreiben sofort die Spiegelung nachziehen
  (`wx.spiegele_journal([...], w['journal_zweitziel'])`) und gegen DIESE
  verifizieren - nicht gegen den lokalen `.bak`.
- **Ein Aufgabeneintrag gehoert nicht in eine Datei, die einer anderen Sitzung
  gehoert.** Die Grenze ist 10 min seit der letzten Aenderung. „Ich schreibe
  es spaeter" ist dann keine Ausrede, sondern eine offene Luecke im Vorgang —
  und die gehoert in den Bericht.

## Verification

Ein Vorgang gilt als geschlossen, wenn **alle vier** im selben Lauf sichtbar
sind:

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel/xperp && \
  ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_*.py' | tail -3
cd /c/Users/faupe/Documents/BrainFiles && git --no-pager log --oneline -2 && \
  git status --porcelain -- <eigene pfade>; echo "(leer = sauber)"
```

Erwartet: eine Zeile `OK` ueber allen Tests, **zwei** eigene Commits (Fix, dann
Doku/Aufgabe), und unter den eigenen Pfaden keine Ausgabe. Kommt eine Zahl ohne
diesen Lauf in die Antwort, gehoert sie nicht in die Antwort. Fehlt der zweite
Commit, ist der Aufgabeneintrag nicht gezogen — der Vorgang ist halb
geschlossen, und das gehört in den Bericht.