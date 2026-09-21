# Eine ruhende oder neue Spur anschliessen

Ausloeser: „die Spur X ist gebaut, laeuft aber nirgends", „X aktivieren", ein
neuer Ordner unter `Agenten/Handel/<spur>/`. Die Spur-weite Aenderung an
BESTEHENDEN Spuren steht in `references/spur-weite-aenderung.md` — hier geht es
um die Frage, was fehlt, damit ueberhaupt ein Zyklus laeuft.

Zuerst inventarisieren, nicht annehmen: `dauerlauf.SPUREN` sagt, was laeuft;
fehlt der Name dort, laeuft die Spur nicht, egal wie vollstaendig der Ordner
aussieht. Ein Ordner mit `SPEC.md`, `backtest.py`, `session.py`, `wachen.json`
und `tests/` ist ein Entwurf — es fehlt das Zyklusskript.

## Checkliste (in dieser Reihenfolge)

1. **Zyklusskript schreiben, nicht erfinden.** Die naechstliegende laufende Spur
   als Vorlage nehmen (bei einer ORB-Variante z. B. `orbk/handeln.py`) und nur
   Datenquelle, Session und Waehrung tauschen. Ein Entwurfsskript aus einer
   frueheren Epoche (andere Boerse, entfernter Broker) ist keine Vorlage —
   pruefen, was es importiert, bevor es restauriert wird.
2. **Papier heisst: kein Live-Zweig.** `--live` muss einen gueltigen Aufruf ohne
   Absturz beantworten und GENAU EINEN Grund nennen; dieser Grund darf das Wort
   „Freigabefenster" NICHT enthalten, sonst stellt
   `dauerlauf.nur_fenster_fehlt` eine Freigabe-Anfrage fuer eine Spur, die gar
   nicht handeln kann.
3. **`wachen.json` vollstaendig machen.** Auch eine gesperrte Spur braucht ein
   `instrument_aktiv` (ohne Instrument laeuft kein Papierzyklus), ein
   `journal_zweitziel` (Bedingung 4, eigener Ordner unter `Q:\Handel_Journal\<spur>`)
   und die Ratsche als AUSDRUECKLICHEN Betrag `drawdown_halbierung_usd`
   (`drawdown_halbierung_prozent` liest `ratschen.py` nicht mehr).
4. **Journal-Schema und Leser zusammen umstellen.** Uebernimmt die neue Spur das
   Zyklusskript einer Vorlage, schreibt sie auch deren Journal-Schema — der
   eigene Wachenleser muss DIESES Schema lesen (`ausgang`/`gv_usd`), nicht das
   einer alten Fassung (`eur`): sonst stirbt der Bericht mit `KeyError`, waehrend
   der Zyklus gruen aussieht. Wachenmodul der laufenden Schwester-Spur kopieren
   ist der sichere Weg.
5. **`dauerlauf.SPUREN`** um den Eintrag erweitern (`ordner`, `waehrung`,
   `skript`; eigenes venv nur ueber `python`). Wirkt ohne Neustart des
   Dauerlaufs — der naechste Zyklus startet den neuen Unterprozess.
6. **Anbindung nachziehen, sonst faellt es im Test:** `befehl`-Familie
   (`befehl.FAMILIE`) und ein Leser in `lage.HOLER` (`spur_<name>()`, Muster der
   Schwester-Spur); `tests/test_befehle.py` verlangt fuer JEDEN `SPUREN`-Eintrag
   Familie UND Leser, `tests/test_lage.py` zaehlt `len(lage.HOLER)` — die Zahl
   mitziehen.
7. **`pruefe_ratschen.py`:** Eintrag in `SPUREN` (Ordner, Modulordner,
   Modulname) und aus `RUHT` entfernen — sonst meldet das Werkzeug die laufende
   Spur weiter als „ruhend, nicht geprueft".
8. **`.gitignore` je Ebene freigeben** (`*.py`, `*.md`, `*.json`, `tests/*.py`,
   `tests/fixtures/*.json`). Ohne das ist der neue Ordner unsichtbar und die
   Spur wird nie versioniert; Beleg `git check-ignore -v <pfad>`.
9. **Bus:** im Zyklusskript `ereignis.lauf("handel/<spur>")` mit dem Spurnamen
   WORTWOERTLICH, danach `Agenten/Bus/tests/test_anbindung_handel.py` laufen
   lassen — der Test prueft je Spur das zugehoerige Skriptfeld, nicht alle
   Skriptnamen gegen alle Spuren.
10. **Tests schreiben** (Range, Breakout, Einstieg, Ausstieg, Tages-Sperre,
    plus die Eigenheit der neuen Spur wie `ziel_modus` oder „kein Live-Pfad")
    und als Sammlung laufen lassen: `cd <spur> && <venv-python> -m unittest
    discover -s tests -t . -p "test_*.py"`. Journal im Test in einen
    Temp-Ordner biegen — ein Testlauf darf nie ins echte Buch oder an das
    Spiegelziel schreiben.
11. **Echter Papierlauf + Spiegelstand:** ein Zyklus muss Zustand schreiben und
    nach Q: spiegeln („Journal ausser Haus: ok"), danach `spiegelstand.py` —
    die Zahl der Spuren waechst mit. Eine Spur ohne Journaldatei zaehlt als
    „beidseitig fehlend = gleich", deshalb vorher einmal echt laufen lassen.

## Fallen

- **Ein Buch fuer Papier UND Live ist die eigentliche Falle.** Solange das
  Freigabefenster zu ist, fuellt der Papierzyklus dasselbe Buch, das der
  Live-Zyklus danach liest. Positionen aus der Papierphase haben keine echte
  Order (`kauf_ord_id` leer) — sie belegen Plaetze, blockieren den Neukauf und
  lassen jeden Ausstieg scheitern, weil am Handelsplatz nichts zu verkaufen ist.
  Richtig ist: der Live-Lauf raeumt SELBST auf, zu Beginn JEDES Live-Zyklus,
  und bucht solche Positionen als Papier-Verkauf mit eigenem Grund aus
  (`buchbereinigung`), echte Order-Traeger bleiben liegen; ohne Kurs bleibt die
  Position stehen. Eine einmalige Handbereinigung waechst nach — als Test
  festhalten (idempotent, keine Order an die Boerse) und am laufenden Live-Zyklus
  belegen (Buchgroesse vorher/nachher, Journalzeilen).
- **„Warum geht die Spur nicht live?" sind zwei Fragen.** `--vorschau` jeder
  Spur druckt die Sperrgruende; die Auto-Freigabe greift nur, wenn GENAU EIN
  Grund fehlt (das Fenster). Der zweite Grund ist meist das GUTHABEN in der
  Waehrung der Spur („nur X EUR frei, noetig Y") — das blockiert dauerhaft und
  lautlos, weil kein Schalter es zeigt. Also erst diese Zeile lesen, dann
  Guthaben und Fenster getrennt benennen.
- **Ein negatives eigenes Backtest-Urteil ist kein Grund, die Spur nicht
  anzuschliessen** — es ist der Grund, sie NUR im Papier laufen zu lassen: ein
  Instrument waehlen (das weniger schlechte) und begruenden, `handel_erlaubt`
  und `freigabe.erfuellt`/`backtest_bestanden` false lassen und das Urteil im
  Wachenbuch stehen lassen. Ein Test, der „gesperrt" prueft (`instrument_aktiv`
  ist `None`), wird dabei auf die neue Sperrlage umgeschrieben — nicht geloescht:
  die Absicherung bleibt, die Behauptung aendert sich.
