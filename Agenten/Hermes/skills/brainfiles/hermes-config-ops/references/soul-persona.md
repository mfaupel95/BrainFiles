# Persona und Ausgabestil dauerhaft wirksam machen (`SOUL.md`)

Ein Wunsch wie „antworte kuenftig immer so" gehoert **nicht** in einen Skill:
Skills sind Nachladeware — im Prompt steht dauerhaft nur ihre `description`, der
Text kommt erst mit `skill_view` — und Hermes hat fuer Skills **keinen**
Immer-an-Schalter. Der Traeger fuer Dauerverhalten ist `SOUL.md`: sie steht in
Slot 1 des Systemprompts, wird aber **nur aus `HERMES_HOME`** geladen, nie aus
dem Arbeitsverzeichnis.

1. **Nachsehen, was drinsteht.** Nach der Installation ist `SOUL.md` die
eingebaute Standard-Identitaet (hier 667 B, derselbe Text wie der Fallback). Sie
**anhaengen**, nicht ersetzen — eine geloeschte Datei laesst Hermes auf die
eingebaute Identitaet zurueckfallen.
2. **Alle Ablagen derselben Persona mitziehen**, sonst antwortet jede Oberflaeche
anders:
   - `$HERMES_HOME\SOUL.md` (hier `Agenten/Hermes/SOUL.md`) — CLI und
     Messaging-Sitzungen dieses Homes,
   - `%LOCALAPPDATA%\hermes\SOUL.md` — Laeufe **ohne** `HERMES_HOME` (Desktop-App,
     Gateway; siehe Falle „Welche Config der laufende Gateway liest" in `references/fallen.md`),
   - `profiles/<bot>/SOUL.md` — je Profil eine eigene Datei; erst `ls profiles/`
     zeigt, wie viele (hier 14).
3. **Stufe 1: vor jeder Datei `.bak-JJJJMMTT`.** Die Sicherung ist die Ruecknahme —
   den Skill zu entfernen nimmt einen Ausgabestil **nicht** zurueck.
4. **Belegen, dass sie geladen wird — nicht, dass sie dasteht.** Eine frische
   Sitzung die eigene Identitaet nacherzaehlen lassen:

       Remove-Item Env:PYTHONHOME, Env:PYTHONPATH   # Falle unten, danach:
       hermes.exe chat -q "Nenne in hoechstens zwei Saetzen die Ausgabestil-Regeln aus deiner SOUL.md." -Q -t memory

   Kommen die Regeln sinngemaess zurueck, ist `SOUL.md` im Prompt. `-t memory`
   haelt den Lauf kurz und billig, `-Q` schaltet Banner ab (ohne `-t` laeuft eine
   ganze Werkzeugschleife los). Zweiter Beleg fuer die Wirkung: eine offene Frage
   stellen und die Form pruefen (erste Zeile = Handlung, nummeriert, keine
   Schlussfloskel) — ein Stiltest mit einer Frage, die zu einem Vorspann verleitet.
5. **Notiz und Commit.** `Wissen/Hermes.md` (Stufe 1) um Quelle, Wirkung,
   Abschaltbefehl und Sicherungspfad ergaenzen, dann die getrackten Dateien
   namentlich committen. `SOUL.md` des Hauptprofils ist **nicht** versioniert,
   `profiles/*/SOUL.md` sind ueber die Whitelist `!Agenten/Hermes/profiles/*/SOUL.md`
   freigegeben: `git ls-files | grep SOUL.md` zeigt, was mitgeht,
   `git check-ignore -v <pfad>` zeigt, was nicht.

Fallen:

- **Eine laufende Sitzung behaelt ihren Systemprompt** (Prompt-Cache-Invariante,
  siehe „Regeln (immer)" 3) — die Aenderung greift erst in einer **neuen**
  Sitzung. Der letzte Schritt gehoert dem Nutzer: `/reset` bzw. `/new`. Nie
  „sofort wirksam" behaupten. Kein Widerspruch zu Regel 3: hier wird kein Prozess
  neu gestartet, nur eine Sitzung begonnen.
- **Der Anlass gehoert in die Notiz.** Steht der Ausgabestil nur in `SOUL.md`,
  haelt ihn die naechste Sitzung fuer Ballast und „raeumt auf". Ein Absatz in
  `Wissen/Hermes.md` macht ihn zu einer Entscheidung des Nutzers.
