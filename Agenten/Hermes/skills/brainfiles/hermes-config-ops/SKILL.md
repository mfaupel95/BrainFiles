---
name: hermes-config-ops
description: "Use when Config, .env oder Profile zu aendern sind."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, config, secrets, soul, persona, brainfiles, verifikation]
    related_skills: [skill-library-sync]
---

# Hermes' eigene Konfiguration ändern

Änderungen an `Agenten/Hermes/config.yaml` und `.env` so ausführen, dass kein
Geheimnis im Klartext in der Konfiguration steht, laufende Agenten unberührt
weiterlaufen und die Änderung mit einem echten Lauf belegt ist.

## When to Use

- "da steht ein Schlüssel im Klartext", "der Token gehört da nicht rein",
  "fix das, ohne die Agenten zu stören"
- eine Einstellung in `config.yaml` soll anders sein (Arbeitsverzeichnis,
  Backend, Timeout)
- nach einem Update oder Setup, das Werte materialisiert hat
- der Agent soll dauerhaft anders antworten (Stil, Ton, Form) — das ist kein
  Skill, sondern `SOUL.md` (references/soul-persona.md)
- "wo trage ich diesen Schlüssel ein / mit welchem Befehl setze ich die
  Umgebungsvariable" — erst die Ablage nach dem Verbraucher entscheiden, dann
  setzen und am laufenden Dienst belegen (nicht nur "steht drin")
- "funktioniert jetzt alles wie gewollt?" / "prüf die Config aus der letzten
  Sitzung" — die Commit-Meldung ist eine Absichtserklärung, nicht der Beleg: je
  Zeile messen und die Maskierung durch die Rückfallkette suchen
  (references/config-gegenprobe.md, Abschnitt *Abnahme*)
- "richtige das optimal ein mit den besten Modellen" / Desktop, CLI oder TUI
  sollen schneller, guenstiger oder traeger sein — dann ist JEDER Kandidat vorher
  wirklich zu rufen (references/modellkette-messen.md); eine Tabelle aus
  Modellnamen ist kein Beleg, und ein `provider: auto` in einem
  `auxiliary`-Block erbt still das Hauptmodell
- "das Terminal geht nicht mehr" / "Terminal environment unavailable" / jedes Kommando scheitert mit Exit 125 - dann den Windows-Host-Pfad in `terminal.cwd` und `docker_mount_cwd_to_workspace` pruefen (references/docker-sandbox.md)
- nach einem Backend-Fix "welche Ordner sehe ich jetzt ueberhaupt noch" / `git` im Terminal findet kein Repository / ein Pfad ausserhalb `Agenten/Hermes` ist plotzlich weg - dann den SICHTBEREICH des Containers messen, nicht nur den Fehler (references/docker-sandbox.md, Abschnitt *Was der Fix kostet*)
- "mach einen Bot / ein Profil fuer Telegram" / "der Bot antwortet nicht" /
  "passiert nichts" — dann zuerst die drei Tore messen, nicht die Config
  umbauen (references/profil-kanalzugangsdaten.md, Abschnitte *Ein NEUES
  Kanal-Profil* und *Ein von Hand eingetragener Token*)

**Don't use for:** MCP-Server-Einträge zwischen Claude und Hermes (`mcp-sync`),
Skill-Kopien (`skill-library-sync`), Update/venv/SQLite (`hermes-maintenance`).

## Regeln (immer)

1. **Drei Ablagen, nach Verbraucher getrennt.** Mensch → `Wissen/Zugaenge.md`
   (nie lesen, nie ausgeben, nie protokollieren). Hermes →
   `Agenten/Hermes/.env` (je Profil eine Kopie). Verbraucher außerhalb von
   Hermes (MCP, Claude, Skript, curl) → Windows-Benutzervariable
   `HKCU\Environment`. Einen Wert, den eine Ablage schon hält, nie ein zweites
   Mal ablegen. `config.yaml` enthält nur `${NAME}`-Verweise.
2. **Kein Geheimnis in eine Kommandozeile.** Werte in der Datei lesen; ausgeben
   nur Länge und SHA-256-Anfang. Vergleichen über Hashes, nie über Werte. Auch
   eine Vorschau ist eine Ausgabe — `.env` nur NAMEN und Längen zeigen.
3. **Nie einen laufenden Agenten neu starten.** Beleg: `hermes gateway status`
   vor und nach der Änderung.
4. **Stufe 1:** vor jeder Änderung an `Agenten/Hermes/**`
   `Agenten/Hermes/.sicherung/<datei>.bak-JJJJMMTT`.
5. **Genau eine Zeile, wo eine Zeile gemeint ist.** Belegen mit `Compare-Object`
   Sicherung gegen Datei — genau ein Zeilenpaar.
6. **Kodierung erhalten - und bei GEMISCHTEN Dateien nach der MEHRHEIT gehen.** BOM und LF/CRLF vorher bestimmen, danach gegenprüfen. Die Regel „wenn CRLF vorkommt, nimm CRLF“ ist bei einer gemischten Datei FALSCH: `Wissen/Hermes.md` führt 375 CRLF gegen 773 nackte LF, ein in CRLF gehaltener Anhang ergab dort einen Zuwachs von 0 statt 29 nackten LF. Richtig ist `nl = "\r\n" if crlf > bare else "\n"`. Gegenprobe danach über den ZUWACHS, nicht über den Bestand: `(neu.count(b"\n") - neu.count(b"\r\n")) - (alt.count(b"\n") - alt.count(b"\r\n"))` muss der Zahl der Zeilen im Anhang entsprechen.
7. **Vault-Notiz nachziehen** (`Wissen/Hermes.md`, Stufe 1 → vorher
   `.bak-JJJJMMTT`), dann `git -C <BrainFiles> commit --author="Hermes
   <hermes@local>" -- <pfad>` — nur benannte Pfade, nie `-A`. Vor dem Schreiben
   `git status --porcelain <pfad>` und `git diff --cached <pfad>` lesen; fremd
   Gestagetes nie mitcommitten. Liegt fremde Arbeit im Baum, den Rebase erst
   freiräumen: `git stash push -- <nur diese fremden Pfade>` (NIE `-a`, das
   nimmt die eigene uncommittete Arbeit mit), `git pull --rebase`, `git stash
   pop`.
8. **Zwei Nachweisstufen getrennt melden.** „Der Wert ist richtig verdrahtet"
   (der Leser im Code nimmt ihn, geprüft durch Aufruf der Auflösungsfunktion)
   und „der Wert wirkt" (ein Lauf zeigt die Wirkung) sind verschiedene Aussagen.
   Nie die zweite behaupten, wenn nur die erste gemessen ist — und im Bericht
   sagen, welcher Lauf die zweite noch braucht (references/modellkette-messen.md,
   Abschnitt Nachweisstufen).
9. **Ein geänderter Pfad gilt erst als belegt, wenn er einen Turn selbst
   vollendet hat.** Eine Rückfallkette kann eine tote Konfiguration vollständig
   verdecken: der Aufruf scheitert, der Nutzer bekommt trotzdem eine gute Antwort
   und sieht keinen Fehler. Immer die Fehlschlagspur im Log mitlesen, nicht die
   Antwort (references/config-gegenprobe.md, Abschnitt *Abnahme*).
10. **Ein Ersatzzblock wird ALLEIN stehend geparst, bevor eine Datei angefasst
   wird.** `yaml.safe_load("\\n".join(block + zu_erhalten))`, dann die
   erwarteten Felder asserten. Grund: die Einrückungstiefe ist eine
   Eigenschaft der Zieldatei, nicht des Hauses — Profil-Configs führen
   Skalarfelder mit zwei Leerzeichen unter einem Top-Level-Schlüssel, die
   Hauptkonfiguration mit vier. Ein Block aus dem einen Haus parst im anderen
   nicht (`expected <block end>`); wird erst NACH dem Schreiben gegengeprüft,
   ist der Schlüssel bereits ein String und alle folgenden Felder sind
   verschluckt. Rollback dann byteweise aus `.bak-JJJJMMTT`, Beleg ist
   `git status --porcelain -- <pfade>` **leer** (references/modellwechsel-flotte.md).
   **Den Block mit einem Interpreter parsen, der PyYAML traegt** — das venv des
   Hermes-Checkouts (`hermes-agent/venv/Scripts/python.exe`) fuehrt die
   Projektabhaengigkeiten, ein Spuren-venv wie `scanner/.venv` oft nicht
   (`ModuleNotFoundError: No module named 'yaml'`). Ein beliebiger Interpreter
   aus dem Baum ist keine Zusage, dass er parsen kann; im Zweifel vorher
   `-c "import yaml"` messen.
11. **Ein Trockenlauf ohne Treffer bei erwartetem Befund ist ein Fehler des
   Suchers.** `text.split("\n")` lässt das abschließende `\r` an jeder Zeile
   stehen, wodurch jedes Präfix still null Treffer hat. Nach dem Split jede
   Zeile auf `\r` prüfen, dann neu messen — „nichts zu tun" ist nie die
   Erklärung für einen leeren Lauf.
12. **Ein NEUES Kanal-Profil ist erst fertig, wenn drei Dinge gemessen sind:**
    `platforms.<plattform>.enabled`, ein EIGENER Bot-Token in der `.env` (ein
    Token haengt an maximal einem Profil), und `auxiliary.compression` gesetzt.
    `hermes profile list` fuehrt ein angelegtes, gestartet-werdendes Profil als
    `running`, auch wenn kein Prozess davon existiert — die Liste liest die
    Served-Liste des Gateways (references/profil-kanalzugangsdaten.md, Abschnitt
    *Ein NEUES Kanal-Profil*).
13. **`gateway.multiplex_profiles: false` ist KEIN Blocker — das Flag ist als
    Opt-out abgeschafft.** `hermes_cli/gateway_multiplex_mode.py::resolve_multiplex_mode`
    loest ein explizites `false` wie ein unset auf, warnt und multiplexed trotzdem
    (der Rueckfallpfad ist nicht optimistisch: ein echter Blocker wie ein s6-
    Container, ein sekundaeres eigenes Gateway oder eine doppelte Bot-Kennung
    laesst den Host solo starten und sagt warum). Wer `false` in einer
    Profil-Config als Kanal-Blocker liest, jagt einen Fehler, den es nicht gibt.
    Der echte Kanal-Blocker ist die fehlende Credential im Profilscope.
14. **Ein Kommentar ist ein Kommentar — nie als YAML-Schluessel schreiben.**
    `delegation_fallback_note: >` mit einem Text darunter erzeugt eine
    erfundene Einstellung: sie taucht in jeder Config-Ansicht, jedem
    `config get` und jedem Dashboard als Schalter auf, den es nicht gibt, und
    sieht beim naechsten Lesen wie Absicht aus. Erklaerungen gehoeren an die
    Zeile, die sie erklaeren. Nach jedem Einfuegen von Bloecken die
    Schluesselmenge gegenpruefen, nicht nur die Werte (`set(cfg) == vorher`).
15. **Ein von Hand eingetragener Kanalwert braucht drei getrennte Messungen:**
    richtiger Bot (`getMe` beider Token vergleichen — der Nutzer schreibt dem
    vertrauten Bot), ueberhaupt je eine Nachricht empfangen (`getUpdates` leer
    heisst "noch nie geschrieben", nicht "kaputt"), und die Form der
    Nutzerkennung (Zeichenart je Position, Laenge, Vergleich ueber
    Normalisierung — ohne den Wert auszugeben). `getChat` ist als Probe
    unbrauchbar: Telegram meldet fuer einen privaten Chat ohne bestehende
    Nachricht `400 chat not found`. Einen vermutlich falschen `.env`-Wert nicht
    ueberschreiben, sondern den Nutzer korrigieren lassen
    (references/profil-kanalzugangsdaten.md, Abschnitt *Ein von Hand
    eingetragener Token*).
16. **Nach einem Fix nicht nur messen, ob der Fehler weg ist, sondern was jetzt
    da ist.** Ein Backend-Schalter kann einen Zustand reparieren und dabei einen
    anderen veraendern: `docker_mount_cwd_to_workspace: true` behebt Exit 125 und
    bindet zugleich NUR noch den `terminal.cwd` — die uebrigen Ordner der Wurzel
    sind danach unsichtbar. Wer nur den Exitcode prueft, meldet Erfolg und laesst
    die halbierte Sicht als Ueberraschung fuer die naechste Sitzung stehen. Also
    nach dem Beleg der Wirkung den neuen Zustand selbst abfragen (was liegt in
    `/workspace`, was in `/workspace/..`, funktioniert `git`) und das Ergebnis in
    den Bericht — als Faehigkeit oder als Grenze, nicht als Nebensatz
    (references/docker-sandbox.md, Abschnitt *Was der Fix kostet*).
17. **Den Terminal-Backend nach der ARBEITSLAST waehlen, nicht nach der
    Verfuegbarkeit.** Der Docker-Backend ist Linux: die Spur-venvs sind
    Windows-EXEs (`PE32+`), `Routinen/*.ps1` sind PowerShell — im Container
    laeuft davon nichts. Ein Baum, dessen Arbeit in diesen Programmen steckt,
    gehoert auf `local`; `docker` ist die Wahl fuer reine Python/Node-Laeufe, die
    isoliert laufen sollen. Die Kosten von `local` sind nicht „der Agent loescht
    alles", sondern derselbe Benutzer ohne Rueckfrage bei destruktiven Kommandos
    — das faengt die Sicherung ab, nicht der Container. Kommt „Docker faellt
    staendig aus" als Argument, erst die Rate messen (Event-Log je Tag plus
    `cron/output/<job-id>/`, wo `**Status:** silent` = gesund): Wahrnehmung und
    Rate gehen weit auseinander (references/docker-sandbox.md, Abschnitt
    *Backend waehlen*).

17. **Ein Eintrag in einer Auswahlliste ist kein Beleg, dass das Modell existiert.**

## Index — references laden, wenn ...

- references/soul-persona.md — laden, wenn der Agent dauerhaft anders antworten soll (SOUL.md statt Skill)
- references/klartext-verweis.md — laden, wenn ein Klartext-Geheimnis in config.yaml auf einen ${NAME}-Verweis umgestellt wird
- references/benutzervariablen.md — laden, wenn ein Zugangswert fuer einen Verbraucher ausserhalb von Hermes (MCP, Claude, Skript, curl) gesetzt oder geprueft wird
- references/docker-sandbox.md — laden, wenn Tools im Docker-Backend Variablen nicht sehen (${env:NAME} leer) ODER JEDES Terminal-Kommando mit "Terminal environment unavailable" scheitert (Exit 125, Windows-cwd im Docker-Backend)
- references/mcp-server-anbinden.md — laden, wenn ein fremder MCP-Server (HTTP/OAuth) angebunden werden soll
- references/config-gegenprobe.md — laden, wenn "optimier meine Config" / "warum greift die Einstellung nicht" / nach Update
- references/einstellung-umstellen.md — laden, wenn eine einzelne Einstellung umgestellt wird (Wert setzen mit Beleg); darin auch der .env-Sonderfall (wirkt erst nach dem Neustart, zweiseitiger Gegentest, Schutzschalter-Kosten)
- references/fallback-kette.md — laden, wenn die Fallback-Kette aufgebaut, geprueft oder repariert wird
- references/hauptmodell-provider.md — laden, wenn das Hauptmodell auf einen anderen Provider umgestellt wird
- references/config-zusammenfuehren.md — laden, wenn config.yaml fremde Aenderungen traegt und zusammengefuehrt werden muss
- references/profil-kanalzugangsdaten.md — laden, wenn ein Bot-Token/Photon-Zugang einem Profil zugeordnet oder entfernt wird
- references/profilflotte-audit.md — laden, wenn mehrere Profile auf einmal geprueft/repariert werden ("ein Bot antwortet nicht")
- references/repo-bot.md — laden, wenn ein Bot fuer ein Fremd-Repo angelegt wird (Geschwisterprofil kopieren)
- references/profil-ohne-repo.md — laden, wenn ein Profil OHNE Repo (Hausordner/Wartungsbot) angelegt wird; Vorlage `templates/profil-config-lean.yaml` (schlanke Config statt des vollen nous-Modellblocks)
- references/modell-anmeldung.md — laden, wenn ein Profil keine Modell-Anmeldung hat ("/bot NAME antwortet nicht")
- references/modellwechsel-flotte.md — laden, wenn ein Modellwechsel ueber viele Profile laeuft
- references/desktop-multiplex.md — laden, wenn die Desktop-App nur das default-Profil zeigt oder multiplex-Probleme hat
- references/fallen.md — laden, wenn eine Aenderung an config.yaml/.env unerwartete Nebenwirkungen zeigt
- references/auswahllisten-erweitern.md — laden, wenn eine Modell-/Auswahlliste unvollstaendig ist oder gekuerzt werden soll
- references/auxiliary-kompression.md — laden, wenn eine Karte/Sitzung mit "context window ... below the minimum 64,000" abbricht oder `auxiliary.compression` gesetzt werden soll
- references/modellkette-messen.md — laden, wenn ein Modell eingesetzt werden soll ("bestmoegliche Hilfsmodelle", "welches Modell laeuft wo"): Fenster aus dem Loader holen, jeden Kandidaten einmal wirklich rufen, Aggregator/Hilfsmodelle/Mainmodell nach Rolle trennen, tote Schluessel finden; enthaelt auch die Nachweisstufen (verdrahtet ≠ belegt) und das zeilenweise Block-Ersetzen in YAML
- references/moa-und-hilfsmodelle.md — laden, wenn `moa:`, `auxiliary:` oder `prompt_caching.cache_ttl` gestellt wird: der Aggregator IST das handelnde Modell (lokales Modell dort = Fehlbau), `provider: auto` erbt das Hauptmodell, und der 1h-Nachweis braucht eine Pause laenger als 5 min plus Gegenprobe auf 5m

## Nachweis (Abschluss)

- `scripts/config-wert-pruefen.py` meldet denselben `sha8` wie vorher.
- `Compare-Object` Sicherung ↔ Datei: genau eine geänderte Zeile.
- `hermes gateway status`: Aufgabe registriert, Prozess läuft — ohne Neustart.
- `Wissen/Hermes.md` nennt Änderung, Prüfweg, Sicherungspfad und Falle; committet.
- Der Bericht trennt **verdrahtet** (Leser nimmt den Wert, per Funktionsaufruf
  geprüft) und **belegt** (ein Lauf zeigt die Wirkung). Fehlt die zweite Stufe,
  steht sie als offener Beleg mit dem fehlenden Lauf drin — nicht als Erfolg.
  Ein Config-Wert im Bericht ohne seinen Lauf ist eine Behauptung.
