# Repo-Bot in Minuten: Geschwisterprofil kopieren (schnellster Weg)

Fuer einen Bot auf einem FREMD-REPO ist das Kopieren eines bestehenden Bot-Profils
kuerzer als `--clone-from` (das die Skill-Bibliothek mitbringt, hier aber oft die
falsche ist) und viel kuerrzer als der Notfallweg Schritt 1-8:

1. `hermes profile create <name> --no-alias` — legt Config, `SOUL.md` und `.env` an.
2. Aus einem bestehenden Bot-Profil `config.yaml` uebernehmen und **nur den Repo-Pfad
   umschreiben** (`Repos\<vorbild>` -> `Repos\<neu>`); `terminal.cwd` ist in der
   Flotte ABSOLUT (`C:\...\Werkstatt\Repos\<name>`) — den Hausstil uebernehmen, nicht
   einen relativen Pfad erfinden. Die Vorlagen-Config als `.bak-vorlage` daneben legen.
3. `profile.yaml` mitkopieren und **die Beschreibung sofort setzen**
   (`hermes profile describe <name> --text "..."`): die Kopie traegt den Text des
   Vorbilds wortwoertlich, und `/bots` zeigt dann den falschen Zweck — bei diesem
   Nutzer die einzige Stelle, an der er die Rolle eines Bots nachliest.
4. `.env` des Vorbilds uebernehmen (nur Namen und Laengen pruefen, Werte nie ausgeben).
5. Modell/Provider der Kopie gegenpruefen (`grep -n "^  provider:\|^  default:"`
   `<profil>/config.yaml`), Fallback-Kette lesen
   (`hermes -p <name> fallback list`), dann `auth.json` verknuepfen (Abschnitt „Einem Profil eine Modell-Anmeldung geben", `references/modell-anmeldung.md`).
6. **Beleg ist ein echter Auftrag, nicht die Dateiliste:**
   `hermes -p <name> chat -q "Nenne Startordner, Repo und die Datei, in der die Rohdaten liegen." -Q`.
   Ein Bot, der ohne `auth.json` nur ueber den Ollama-Rueckfall antwortet, ist
   einsatzbereit — aber das im Bericht sagen, statt die Anmeldung als erledigt
   darzustellen.
