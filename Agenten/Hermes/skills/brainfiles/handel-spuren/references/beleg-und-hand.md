# Freigabe-Beleg und Hand: wer eine Order ausfuehrt

Die eine Bruecke zwischen Spur-Entscheidung und Boersen-Order. Gilt fuer jede
Spur, die einen Auftrag ABGEBEN statt selbst ausfuehren soll, und fuer jede
Anbindung, die Orders aus einer SITZUNG heraus ausloesen koennte (MCP-Werkzeug,
CLI, Bot, Chat).

## Warum es das gibt

Ein Tauschwerkzeug (MCP-Server, CLI, Bot) darf nicht selbst entscheiden: es ist
aus jeder Sitzung, jedem Bot und jeder A2A-Nachricht aufrufbar, kennt aber keine
Wachen, kein Buch, keinen Herzschlag und keinen Kill-Switch. Ein Verbot im Text
haelt das nicht (Text ist keine Sperre). Die Loesung ist eine **Erlaubnis als
Datei**: `Agenten/Handel/freigabebeleg.py`.

```
Spur (kennt Wachen, Buch, Kill-Switch) --stellt aus--> Beleg <--verlangt-- Hand (MCP/CLI/Skript)
```

- `schreibe(spur, seite, paar, menge, preis_max|preis_min, grund, gueltig_sekunden, zusatz)`
  **verweigert**, wenn kein Freigabefenster offen ist ODER `handel_erlaubt=false` -
  also unter genau den Bedingungen, unter denen die Spur ohnehin handeln darf.
- Inhalt: Spur, Seite, Paar, Hoechstmenge, Hoechstpreis, Frist (Standard 180 s)
  und `zusatz` fuer das, was nur die Spur weiss (Stop, Ziel). Die Hand soll den
  Auftrag vollstaendig kennen, sonst entscheidet sie doch.
- **Einmalig:** `pruefe(...)` vor dem Ausfuehren, `verbrauche(...)` danach.
- `preis_max` gilt nur bei `buy`, `preis_min` nur bei `sell` - vertauscht ist es
  eine Erlaubnis fuer den falschen Preis.
- `offene()`/`uebersicht()` sind lesend und nennen die offenen Belege.
- Der Beleg hat keinen Erzeuger-Zwang ausserhalb der Spur: stellt nur eine Spur
  aus, und nur sie kennt die Wachen.

## Der Spur-Zweig: abgeben oder selbst ausfuehren

Die Entscheidung steht als FELD in der `wachen.json` der Spur
(`order_ueber: "mcp"`), damit ein Schalter nicht im Code versteckt ist:

1. **Beleg ausstellen** - in beiden Varianten. Schlaegt das fehl, faellt der
   Einstieg aus: eine Spur ohne Freigabefenster darf auch auf ihrem EIGENEN Weg
   nicht kaufen. Wer den Beleg nur im Abgabe-Zweig ausstellt, umgeht das Tor.
2. **`order_ueber: "mcp"`** - die Spur ordert NICHT. Sie schreibt eine
   Journalzeile (`kauf_beleg`) und laesst den Beleg liegen; ausgefuehrt wird von
   der Hand.
3. **eigener Weg** (Feld fehlt oder `"spur"`) - die Spur **verbraucht den Beleg
   VOR der Order** und ordert dann selbst.

**Der Verbrauch VOR der Order ist der Kern der Einmaligkeit.** Bliebe der Beleg
nach einer eigenen Order liegen, koennte die Hand dieselbe Order innerhalb der
Frist ein zweites Mal ausfuehren - ein echter Doppelkauf, kein Schoenheitsfehler.
Umgekehrt gilt: nach einem Fehlschlag wird KEIN Beleg aufgehoben, der naechste
Zyklus entscheidet neu.

## Die Hand: zwei Wege, ein Tor

- **Aus einer Sitzung:** das MCP-Werkzeug `kraken_order_mit_beleg` prueft und
  verbraucht denselben Beleg. Das frueher offene Werkzeug `kraken_order_aufgeben`
  kann NICHT mehr echt ausfuehren (nur noch pruefen), und ein Sammelstorno
  (`kraken_order_stornieren('all')`) ist gesperrt, weil es den Schutz-Stop einer
  offenen Position mitnimmt. **Einzelstorno bleibt erlaubt** - es kuerzt nur
  Risiko. **Ausstiege haengen NIE am Beleg**, nur Einstiege; Stop und Notaus
  bleiben frei.
- **Im Betrieb:** `Agenten/Handel/beleg_hand.py` (Vorschau ist Standard) fuehrt
  genau das aus, was im Beleg steht (Paar, Menge, Hoechstpreis, Stop, Ziel) und
  bucht die Position in das ECHTE Buch der Spur (Journal, Zustand, Spiegelung -
  Bedingung 4). Gerufen von Cron `beleg-hand` (5 min, `no_agent`, leise wenn
  nichts offen).

**Ohne den zweiten Weg ist der Beleg-Weg im Dauerlauf ein Stillstand:** die Spur
gibt ab, und niemand nimmt. Ein Beleg, den nur eine Sitzung ausfuehren kann, ist
fuer einen Dauerprozess kein Weg.

## Fallen

- **Hochwertige Attrappen verdecken den Boersenkontakt im Test.** Die Attrappe
  muss an der UNTERSTEN Transportschicht sitzen (Stolperdraht), sonst kann ein
  Test mit `echt=True` wirklich kaufen - siehe `handelsspur-anlegen`, Abschnitt
  Tests.
- **Der Fenster-Name ist der SPURNAME, nicht der der Nachbarspur.** Ein zweiter
  Weg auf derselben Boerse, der das Fenster der Haus-Spur benutzt, schaltet sich
  mit ihr scharf.
- **`sitzung_da()` darf im Dauerlauf nie wahr werden:** der Dauerlauf setzt
  `MAXHIRN_ROUTINE=1` in BEIDEN Modi, ein Live-Lauf kann sich also nicht fuer
  eine Sitzung am Bildschirm halten und auf eine Freigabe warten, die niemand
  geben kann. Das Zeitfenster (`freigabefenster.py`) ist der zweite, ehrliche Weg.
- **Die `--vorschau` stellt keinen Beleg aus und schreibt nichts** (kein
  Zustand, kein Journal, keine Order) - sonst baut jeder Testlauf Erlaubnisse.
- **Eine Einheit fuer alle Schalter:** Ein Vorschau-Lauf, der die Sperrenliste
  ausgibt, muss GENAU EINEN Grund mit dem Wort "Freigabefenster" nennen, sonst
  kann der Dauerlauf nicht unterscheiden, ob nur das Fenster fehlt
  (`dauerlauf.nur_fenster_fehlt`).
- **Eine neue Spur auf dem MCP-Weg braucht BEIDE Enden:** den Aussteller im
  Spurcode UND die Hand im Betrieb. Nur eines von beiden zu bauen hinterlaesst
  eine Spur, die entweder nichts ausfuehrt oder nichts abgibt.
