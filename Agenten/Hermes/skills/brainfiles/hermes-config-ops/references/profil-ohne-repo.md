# Ein neues Profil OHNE Repo anlegen (Wartungsbot-Muster)

Ein Profil, dessen Arbeitsbereich ein Hausordner ist statt eines Fremd-Repos
(Beispiel: `hermes-wartung` mit `terminal.cwd = Agenten\Hermes`).

**Erst den WEG waehlen — `--clone-from` ist der kurze, die Schritte 1-8 sind der
Notfallweg.** Existiert in der Flotte schon ein eingerichtetes Profil mit demselben
Zuschnitt (Hausordner, `terminal.backend: local`, Flottenmodell), ist
`hermes profile create <name> --clone-from <quellprofil> --description "<Rolle>"`
der richtige Aufruf: er bringt `providers`-Block, `.env`-Vorlage, `SOUL.md`, die
getrimmte Skill-Bibliothek und die Beschreibung fuer `/bots` mit. Kanalzugangsdaten
bleiben dabei von selbst draussen (`--clone-channels` waere der ausdrueckliche
Zusatz), und eine `auth.json` kommt ebenfalls NICHT mit — die gehoert als Symlink
dazu (Abschnitt „Einem Profil eine Modell-Anmeldung geben", `references/modell-anmeldung.md`). Danach bleiben nur
drei Handgriffe: `terminal.cwd` setzen, **`SOUL.md` auf die NEUE Rolle umschreiben**
(der Klon traegt die Rolle des Quellprofils wortwoertlich weiter — wer das
uebersieht, hat einen Wartungsbot, der ploetzlich Marktdaten liefert), `profile.yaml`
pruefen. Die Schritte 1-8 gelten, wenn kein passendes Quellprofil existiert.

1. `hermes profile create <name> --no-alias` (ohne `--clone`, damit keine
   fremde Modellkennung und keine Kanalzeilen mitkommen).
2. **Ein frisches Profil ist NICHT fertig** - es hat eine 45-Zeilen-`config.yaml`
   ohne `providers`- und `terminal`-Block, `SOUL.md` ist die eingebaute
   Standard-Identitaet, und **`profile.yaml` fehlt ganz** (ohne sie kennt `/bots`
   das Profil nicht). Der `--clone`-Weg liefert dagegen eine 1700-Zeilen-Config.
3. `providers.omniroute` byte-genau aus einem bestehenden Bot-Profil einsetzen
   (nicht abtippen - die `auto/*`-Modellliste ist 1700 Zeilen), dazu
   `model.provider=omniroute`, `model.default=auto/best-coding` (per
   `hermes -p <name> config set`, danach Kommentar-Schluss zurueckholen).
4. `terminal:`-Block mit `backend: local` und dem gewuenschten `cwd` ergaenzen.
   Die Bloecke VOR dem Schreiben mit `yaml.safe_load` parsen und Assertions
   setzen (`rest == vorher` ausserhalb der beiden Bloecke).
5. Die Router-Schluesselnamen in die eigene `.env` (frisch = leere Vorlage).
   Ein Kommentar ohne `#` laesst `python-dotenv` beim JEDEN Start meckern
   ("could not parse statement starting at line N") - Zeilen pruefen.
6. Beschreibung per `hermes profile describe <name> --text "..."` - das erzeugt
   `profile.yaml` erst an.
7. Ein Bot ohne Repo liest dieselbe Stilquelle wie die Repo-Bots:
   `profiles/rule_repo-bots.md`. Dort seinen Geltungsbereich im Kopf nennen und in
   der eigenen `SOUL.md` darauf verweisen — die Datei hat ein Budget von 6000
   Zeichen, also nur den Geltungsbereich ergaenzen, nichts anhaengen.
8. **Skills nachziehen — ein frisches Profil hat KEINE Haus-Skills.** Ohne
   `--clone` enthaelt `profiles/<name>/skills/` nur die eingebauten Kategorien
   (apple, autonomous-ai-agents, devops, …). Verweist die eigene `SOUL.md` auf
   Haus-Skills (`brainfiles/hermes-config-ops`, `hermes-doctor`,
   `dauerprozess-bewachen`, `systemdiagnose`), laufen die ersten Zuege des Bots
   in fehlgeschlagene `skill_view`-Aufrufe („Skill '<name>' not found") — der
   Lauf kostet Zeit und wirkt kaputt, ohne es zu sein. Die genannten Skills aus
   `Agenten/Hermes/skills/` hinueberkopieren und mit
   `hermes -p <name> skills list` belegen (Zaehlzeile „N local" plus die Namen
   in der `source`-Spalte `local`) — vor dem ersten Bot-Lauf, nicht danach.
   Zwei Fallen beim Kopieren: **den Zielordner vorher anlegen**
   (`mkdir -p profiles/<name>/skills/<kategorie>`) — `cp -r <quelle> <zielkategorie>/`
   mit fehlendem Ziel legt die Kategorie als KOPIE der ersten Quelle an, und die
   zweite Quelle landet darin verschachtelt (`SKILL.md` direkt im Kategorieordner,
   daneben ein Ordner der zweiten Quelle). Und **Skillnamen im Baum nachsehen**
   (`ls Agenten/Hermes/skills/<kategorie>/`), nicht aus dem Gedaechtnis tippen:
   `handelsspur-studie` existiert nicht, `handel-spur-studie` schon — ein `cp` auf
   den geratenen Namen bricht ab, und ob der Skill im Profil liegt, zeigt erst
   `hermes -p <name> skills list`.

6. **Ein abgebrochenes `--clone` hinterlaesst eine Muellehalde.** Wird der Lauf
   gekappt (Zeitlimit, Abbruch), liegt danach
   `profiles/.<name>.staging-<pid>/` auf der Platte: eine VOLLE Kopie des
   Startprofils samt `.env` (Kanalzugangsdaten!) und Sessions, gemessen
   599 MB. Sie traegt eine `config.yaml` und stand deshalb als Phantom-Bot in
   `/bots` (`skillsbot.bot_namen()` ueberspringt seit 22.09.2026 Punkte-Ordner).
   Nach einem abgebrochenen Anlegen also `profiles/` nach `.`-Ordnern absuchen
   und den Staging-Rest loeschen. Fuer einen Bot mit Repo ist der stille Weg
   `hermes profile create <name> --no-alias` + Nacharbeiten ohnehin der bessere:
   `--clone` bringt die 1700-Zeilen-Config des Startprofils mit.
7. **`auth.json` verknuepfen: `pwsh` 7, nicht `powershell.exe`.** Ein SymbolicLink
   auf den Root-Store braucht in dieser Umgebung Erhoehung; `New-Item` unter
   `C:\Program Files\PowerShell\7\pwsh.exe` laeuft ohne UAC durch, unter
   `powershell.exe` 5.1 endet er mit "Administratorrechte erforderlich".

Beleg-Pflicht (nichts davon ist durch "Datei steht da" bewiesen):
`hermes -p <name> chat -q "Fuehre pwd aus und nenne Modell und Arbeitsverzeichnis." -Q -t terminal`
- `pwd` muss den Zielordner melden, das Modell den Routerpfad. Dazu
`hermes profile list` (0 Warnzeilen) und die Profilliste des SkillsBot
(`bot_namen()` in `Agenten/Bus/skillsbot.py`) gegen die Zahl der Profilordner.

Falle: Zeilenenden nicht raten. Ein Profil, das per `hermes config set`
angefasst wurde, kann LF-only sein, waehrend ein aus einem CRLF-Profil
kopierter Block CRLF mitbringt - die Datei ist danach gemischt. Vor dem
Schreiben `\r\n` in den ROHEN Bytes bestimmen und die GANZE Datei auf das
Hausformat (CRLF) normalisieren; der `yaml.safe_load`-Vergleich beweist, dass
nur die Enden normalisiert wurden, der Diff gegen die Sicherung zeigt genau
die neuen Zeilen.

#### Ein Rollen-Bot, der nur verteilen soll (Verteil-/Dispatcher-Bot)

Ein Profil, dessen Aufgabe „Auftrag verstehen, Ziel finden, delegieren" ist.
**Ein Verbot allein haelt nicht, eine Selbstpruefung haelt.** Gemessen an derselben
klaren Aufgabenstellung („pruefe, ob die Repos aktuell sind"): mit der SOUL-Regel
„bearbeite den Auftrag NICHT selbst" hat der Bot die Pruefung SELBST gefahren —
18 Werkzeugaufrufe mit einem kleinen Modell, 7 mit einem starken; es aenderte sich nur
die Zahl der Umwege. Erst die drei Zusaetze unten haben die Rolle gehalten (danach
2 Aufrufe und eine Rueckfrage statt Eigenlauf; bei „lass Bot X sein Repo pruefen" hat
er wirklich delegiert und das Ergebnis des Ziels samt dessen Empfehlung berichtet):

1. **Eine Frage, die der Bot sich vor JEDEM Schritt selbst stellt** — „Fuehre ich
   gerade den Auftrag aus, oder suche ich sein Ziel?" — mit den Merkmalen des
   Abweichens, an denen er sich ertappt: Verzeichnisse des Gegenstands lesen, ein
   Fachwerkzeug aufrufen, zaehlen, vergleichen, ein Fachergebnis formulieren. Und
   ausdruecklich: **auch ein Trockenlauf ist Ausfuehrung** — „ich schaue nur schnell
   nach" ist der Weg, auf dem die Rolle verloren geht. Dazu die Regel fuer den Fall
   ohne Ziel: **kein Bot passt → Werkzeug NENNEN und fragen, nicht starten.** Ein
   Rollen-Verbot braucht diese Pruefung, sonst bleibt es wirkungslos.
2. **Den Weg deterministisch machen, nicht die Absicht.** Ein Skript kapselt den
   mechanischen Teil (`Agenten/Werkzeuge/<rolle>-route.py`): `--liste` (Ziele samt
   Beschreibung aus `profiles/*/profile.yaml`, damit die Zielliste nicht abgetippt
   wird), `--suche <wort>` (welche Ziele passen), `--an <ziel> "<auftrag>"` (startet
   wirklich `hermes -p <ziel> chat -q`, entfernt `PYTHONHOME`/`PYTHONPATH`, setzt eine
   Frist). In der SOUL genau diese drei Aufrufe als ERSTEN Schritt nennen. Damit ist
   der Ausgang nachvollziehbar und wiederholbar, auch wenn das Modell umwege nimmt.
3. **Nicht mehr versprechen als gemessen ist.** „Der Bot verteilt" ist erst wahr,
   wenn ein Auftrag nachweislich bei einem anderen Profil ankam — je Rolle DREI
   Auftragsarten durchspielen (ein Sachauftrag ohne Bot, ein Fachauftrag mit Werkzeug,
   ein echter Delegationsauftrag) und die Werkzeugaufrufe zaehlen, nicht das Gefuehl
   befragen. Die harte Durchsetzung waere ein eingeschraenkter Werkzeugsatz — Hermes
   bietet dafuer heute keinen Config-Schluessel (`tools` regelt die Werkzeugsuche,
   `toolsets` die Plugin-Sets), also nicht als geloest darstellen. Das Rollenmodell
   selbst bleibt Geschmackssache: ein kleines Modell folgt der Charta genauso wenig
   wie ein grosses, nur mit mehr Umwegen — die Selbstpruefung ist der Hebel.

Dazu die Profil-Pflichten wie oben (frisches Profil = 45 Zeilen ohne `providers`/
`terminal`, `profile.yaml` fehlt), `hermes profile describe <name> --text "<Satz>"`
fuer `/bots` — und ein neues Werkzeugskript unter `Agenten/Werkzeuge/` in die
`.gitignore`-Freigabeliste aufnehmen (`!Agenten/Werkzeuge/<datei>.py`): ohne die Zeile
ist es beim naechsten `git status` unsichtbar (`git check-ignore -v <pfad>` zeigt `!!`)
und wird nie versioniert.
