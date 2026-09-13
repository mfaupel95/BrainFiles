# Offene Punkte

Sitzungsübergreifende Aufgabenliste. Einzige Quelle für „was ist noch offen".
Angelegt am 2026-08-28, weil offene Punkte aus früheren Chats bis dahin
nirgends festgehalten wurden und mit dem Sitzungsende verloren gingen.

## Regeln

- **Am Sitzungsanfang lesen**, bevor gefragt wird, woran gearbeitet werden soll.
- **Sofort eintragen**, wenn ein Punkt entsteht — nicht am Sitzungsende sammeln.
  Wird die Sitzung vorher abgebrochen, ist der Punkt sonst weg.
- **Erledigtes nach `## Erledigt` verschieben**, mit Datum. Nicht löschen —
  die Historie zeigt, was schon einmal versucht wurde.
- **Nichts erfinden.** Nur eintragen, was Max gesagt hat oder was aus einer
  abgebrochenen Arbeit tatsächlich offen blieb. Vermutete Folgeaufgaben
  gehören als Vorschlag in die Zeile „Kontext", nicht als eigener Punkt.
- **Stand aktuell halten.** Fällt beim Arbeiten auf, dass ein Eintrag hier
  überholt ist, sofort korrigieren und die Korrektur melden — auch wenn es
  nicht zur laufenden Aufgabe gehört.
- IDs fortlaufend `T-001`, `T-002`, … Einmal vergeben, nie wiederverwenden.

## Status-Kürzel

| Kürzel | Bedeutung |
|---|---|
| `[ ]` | offen, noch nicht angefangen |
| `[~]` | in Arbeit / teilweise erledigt |
| `[?]` | wartet auf Entscheidung oder Information von Max |
| `[!]` | blockiert, Ursache im Kontext benannt |
| `[x]` | erledigt → gehört nach unten |

## Eintragsformat

```
- [ ] **T-001 — Kurztitel**
      Kontext: worum es geht, warum es offen ist
      Nächster Schritt: eine konkrete, ausführbare Handlung
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28
```

Optional zusätzlich: `Betrifft:` (Pfad, Projekt, Gerät), `Wartet auf:` (bei `[?]`/`[!]`).

## Offen

- [x] **T-038 — 21,5 GB Modellgewichte liegen auf `C:`, nicht in `Modelle/`**
      **Erledigt 2026-09-13.** Auf `C:` liegt kein Modellgewicht mehr (C: frei
      3,2 GB → 66,1 GB). Die 21,1 GB `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` liegen
      unter `O:\Modelle\GGUF\`; das 0,84 GB große mmproj wurde nach
      `O:\Modelle\hermes\assets\` verschoben, und
      `%LOCALAPPDATA%\hermes\models` ist jetzt eine Junction auf
      `O:\Modelle\hermes`.
      **Antwort auf die Frage nach der Variable:** Es gibt **keine** eigene
      Variable für den Modellort — `bootstrap.models_dir()` liest
      `get_default_hermes_root() / "models"`, also `%LOCALAPPDATA%\hermes\models`
      (wenn `HERMES_HOME` ungesetzt) bzw. `HERMES_HOME\models`. Mit dem
      gesetzten `HERMES_HOME = ...\BrainFiles\Agenten\Hermes` wäre das
      `Agenten\Hermes\models` — dort ist bewusst **keine** Junction: `Agenten\`
      ist Sicherungsquelle, robocopy würde den Modellen in die Nachtsicherung
      folgen.
      **Offen bleibt:** `local_runtime.enabled` steht auf `false`, deshalb
      liest derzeit niemand diesen Ordner. Vor dem Einschalten muss entschieden
      werden, wohin die Gewichte gehören — sonst landen 20 GB wieder auf `C:`
      oder in der Sicherung.
      Zuletzt: 2026-09-13
      --- ursprünglicher Befund vom 08.09.2026 ---
      Kontext: Bei der Gesundheitsprüfung am 08.09.2026 gemessen.
      `%LOCALAPPDATA%\hermes\models` ist **21,5 GB** groß und damit der größte
      einzelne Posten auf der Systemplatte (`AppData\Local\hermes` gesamt
      22,7 GB). Das widerspricht der Regel aus der Wurzel-`CLAUDE.md`:
      Modellgewichte gehören nach `Modelle/` (Junction auf `O:\Modelle`), sind
      neu herunterladbar und bleiben deshalb aus der Sicherung draußen. Auf
      `C:` werden sie weder gesichert noch aus der Sicherung ausgenommen — sie
      belegen einfach die Platte, die am knappsten ist.
      Zum Vergleich auf derselben Platte: Claude 25,6 GB
      (`Packages\Claude_pzs8sxrjxfjjc` 13,8 + `Roaming\Claude` 11,8),
      `Cleanup_2026` 13,0, `Roaming\Pioneer` 11,7.
      Nächster Schritt: prüfen, ob Hermes den Ort über eine Variable lesen
      kann (wie Ollama über `OLLAMA_MODELS`); wenn ja, Store nach
      `O:\Modelle\hermes` verschieben und die Variable setzen. Wenn nein,
      entscheiden, welche Modelle dort überhaupt gebraucht werden.
      Betrifft: `%LOCALAPPDATA%\hermes\models`, [[Ordnerstruktur]]
      Angelegt: 2026-09-08 · Zuletzt: 2026-09-08

- [x] **T-011 — Wer schreibt `Modelle/.onchainos`?** — erledigt 2026-09-08
      Nach Suche im gesamten Vault: **kein Skript** referenziert diesen Pfad.
      Der Ordner ist ein Überbleibsel von „Stufe 0" (vor dem 30.08.2026),
      wahrscheinlich von OKX/OnchainOS-Werkzeugen angelegt. Inhalt:
      `wallets.json` (30+ Chain-Adressen, Projekt-ID
      `agentic-wallet-project01`, Account `05c0d7a8-…`),
      `machine-identity` (SHA-256-Hash), `session.json` (Session-Key,
      ablaufbar 2027-01-18), `keyring.enc` (verschlüsselt).
      **Maßnahme:** Vollständiges Backup nach
      `Archiv/OnChainOS_Backup_20260908/`, Notiz erstellt in
      `Wissen/OnChainOS_Backup.md`, Original gelöscht.
      Keine aktive Komponente nutzt den Ordner — kein Risiko bei Wegfall.
      Betrifft: `Modelle/.onchainos` → `Archiv/OnChainOS_Backup_20260908/`
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-08

- [ ] **T-032 — In `Werkstatt/` liegt eigene Arbeit, die nirgends gesichert wird**
      Kontext: Beim Abräumen von `G:` am 03.09.2026 aufgefallen. `Werkstatt/`
      ist aus beiden Sicherungen ausgenommen — richtig für geklonte Fremd-Repos
      und Sitzungsreste, falsch für das, was tatsächlich dort liegt:
      `Werkstatt\Sitzungen\m3u_cleaner\` ist eigener Python-Code samt
      PyInstaller-Builds, `Werkstatt\Protokolle\Codex\` sind Auswertungen. Von
      beidem existiert nur noch die alte Kopie auf `G:` (Ordner `Codex\` und
      `Coworking-Space\`, zusammen 0,4 GB), und die stammt von vor dem
      30.08.2026.
      Nächster Schritt: entscheiden, ob `m3u_cleaner` in den Vault gehört
      (dann nach `Archiv/Software/` — liegt seit 07.09.2026 auf `O:\Archiv`,
      T-037 — oder als eigenes Projekt) oder ob `Werkstatt/` eine Ausnahme in
      `sichern.ps1` bekommt. Bis dahin die beiden
      Altordner auf `G:` stehen lassen.
      Betrifft: `Werkstatt/`, `Agenten/sichern.ps1`
      Angelegt: 2026-09-03 · Zuletzt: 2026-09-03

- [?] **T-033 — `OKX_API.env`: Schlüssel im Portal widerrufen**
      Kontext: Beim Abräumen von `G:` am 03.09.2026 im Altzweig gefunden
      (`Claude\Worktrees\Investment\OKX_API.env`, 124 Bytes, Stand
      07.08.2026). Kein Duplikat, sondern der letzte Rest eines alten
      Arbeitszweigs.
      **Erledigt am 03.09.2026:** Inhalt geprüft, Datei nach SHA256-Verifikation
      von `G:` nach `Archiv/Posteingang/_zu_loeschen/` verschoben — damit ist der
      Klartext von der Platte weg, die regelmäßig abgezogen wird (T-015). Befund
      in [[Zugaenge]] festgehalten: Der Secret ist zu kurz (4 Zeichen gemessen,
      am 23.08. mit 6 notiert) und damit unbrauchbar; Key und Passphrase sehen
      echt aus und stehen sonst nirgends in `Zugaenge.md`. Der dortige Pfad-
      verweis auf `Claude/Worktrees/investment/` ist mitgezogen.
      **Nicht gelöscht** — Stufe 0, und die Datei ist bis zum Widerruf das
      Identifikationsmittel im Portal.
      Nächster Schritt: Max ruft `https://web3.okx.com` → API-Verwaltung auf und
      löscht den Schlüssel. **Ob er noch aktiv ist, lässt sich von hier nicht
      feststellen** — ohne gültigen Secret ist keine signierte Anfrage möglich.
      Bis dahin gilt er als möglicherweise aktiv. Danach darf die Datei weg.
      **Es gibt eine zweite Kopie:**
      `O:\MaxHirn-Zweitkopie\Claude\Worktrees\investment\OKX_API.env` (124 Bytes,
      07.08.2026) — der Altzweig, wie er beim letzten Zweitkopie-Lauf aussah.
      Bewusst nicht angefasst: In eine Sicherung greift man nicht nebenbei
      hinein. Nach dem Widerruf müssen **beide** weg, sonst war der Aufwand
      umsonst. Gesucht wurde in `C:\Users\faupe\Documents`, `G:`, `O:` und `J:`
      — **ganz `C:` ist nicht geprüft**, dort ist eine weitere Kopie nur
      unwahrscheinlich, nicht ausgeschlossen.
      Wartet auf: Max — Widerruf im OKX-Portal
      Betrifft: `Archiv/Posteingang/_zu_loeschen/OKX_API.env`,
      `O:\MaxHirn-Zweitkopie\...\OKX_API.env`, [[Zugaenge]]
      Angelegt: 2026-09-03 · Zuletzt: 2026-09-03 (23:34)

- [x] **T-013 — Drei Pfadverweise in `Zugaenge.md` von Hand nachziehen** — erledigt 2026-09-07
      Alle drei Verweise geändert:
      1. Zeile 108: `Claude/Software/…` → `Archiv/Software/…`
      2. Zeile 116: `Claude/Worktrees/investment/` → `Archiv/Worktrees/investment/`
      3. Zeile 156: `O:\MaxHirn-Zweitkopie\Claude\Worktrees\…` → `Archiv\Worktrees\…`
         (mit erklärend erwähnt: das ist der alte Pfad aus der Sicherung vom 30.08.2026)
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-07

- [x] **T-014 — 1,5 GB Ollama-Protokolle in 17 Dateien** — erledigt 2026-09-07
      Das Hauptvolumen (1,5 GB) war nicht in den 17 Protokolldateien, sondern im
      Ordner `updates_v2` (alte Ollama-Versionen). Gelöscht am 07.09.2026, 22:40.
      Danach regenerieren sich die `.log`-Dateien (trivial, <10 KB je). Die
      `.sqlite-wal` und `.sqlite-shm` Dateien werden von Ollama bei Neustart neu
      angelegt, sind aber Temp-Dateien und verschwinden bei Inaktivität.
      **Resultat:** 1,5 GB Speicherplatz auf C: freigegeben.
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-07

- [x] **T-016 — Ordner `MaxHirn/Claude/` → `MaxHirn/Archiv/` samt Verweisen** — erledigt
      2026-09-02. Der physische Rename lief am 01.09. bei der Absturz-Recovery
      durch; `MaxHirn/Claude/` existiert nicht mehr. Am 02.09. nachgezogen:
      `.gitignore`-Whitelist zeigt auf `MaxHirn/Archiv/`, `git check-ignore`
      bestaetigt, dass neue Dateien unter `Archiv/` **nicht** mehr ignoriert
      werden. `.venv` in `Archiv/ArchivSuche/` neu erzeugt (Python 3.13) und
      `requirements.txt` installiert — alle neun Abhaengigkeiten importierbar.
      Textebene: `Claude/` → `Archiv/` in ~25 versionierten Dateien (Notizen,
      Dashboard, Archiv-Doku, Skript-Kommentare); `Claude/Worktrees/` →
      `Werkstatt/Worktrees/`; `%APPDATA%\Claude\` (Claude-Desktop-Config) und
      historische „hiess Claude/"-Erwaehnungen verschont. Dabei drei kaputte
      Skriptpfade gefunden und behoben: `sichern-zweitkopie.ps1` (Medien-
      Ausschluss), `posteingang.ps1` und `mail/mailversand.py` (Wurzel loeste
      seit der Ordnertrennung auf `Agenten/` statt `BrainFiles/` auf).
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-02

- [x] **T-017 — Gehebelter Handel hat noch keine `wachen.json`** — erledigt
      2026-09-01. `Agenten/Handel/xperp/wachen.json` liegt (Höchsteinsatz je
      Anlauf 50 USD Margin, gesamt 200, Höchsthebel 5, Pflicht-Stop in ATR
      statt Prozent, Kill-Switch je Anlauf und gesamt). Der Modulkopf von
      `okxf.py` ist auf Spur 2 umgeschrieben und nennt den alten Wortlaut nur
      noch als Historie. Zusätzlich legt `bot.pruefpflicht()` die vier
      geforderten Zahlen vor; neu gerechnet ist Zahl 4 (nötige gegen
      beobachtete Trefferquote) samt Warnung, wenn die seltenere Seite unter
      zehn Ereignissen liegt. Siehe [[XPERP-Handel]].
      Kontext: [[Schutzregeln]] erlaubt seit dem 01.09.2026 gehebelte
      Positionen auf ausdrückliche Anweisung (Spur 2). Die Grenzen dieser Spur
      stehen bisher **nur in der Prosa der Notiz**, nicht in einer Datei — im
      Gegensatz zu Spur 1, wo `scanner/wachen.json` die einzige Wahrheit ist.
      Genau diese Bauform ist aber der Schutz: eine Sitzung kann eine Regel
      vergessen, eine Datei nicht.
      Zweitens trägt `Agenten/Handel/xperp/okxf.py` im Modulkopf noch den
      alten Wortlaut („gilt ausdruecklich nur fuer nur Spot, nur Long, kein
      Hebel … Dieses Modul faellt NICHT darunter"). Das stimmt seit heute
      nicht mehr und widerspricht der Regeldatei.
      Nächster Schritt: `xperp/wachen.json` anlegen (Höchsteinsatz je Position,
      Gesamtnominal, Höchsthebel, Pflicht-Stop, erlaubte Kontrakte) und den
      Modulkopf auf Spur 2 umschreiben.
      Betrifft: `Agenten/Handel/xperp/` — **dort arbeitete am 01.09. 17:34 eine
      andere Sitzung**, deshalb hier nur eingetragen und nicht angefasst.
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-01

- [x] **T-019 — Die Regel erlaubt jetzt mehr, als der XPERP-Bot kann**
      Erledigt 2026-09-03: Der Live-Pfad ist gebaut, nachdem Max XPERP zum
      Hauptweg gemacht hat. Neu sind `xperp/handeln.py` (Zyklus, Ausstiege,
      Einstiege, Journal, Zustand) und `xperp/wachen_xperp.py` (Bedingungen
      1–5, Rechnung importiert aus `scanner/wachen_pruefung.py`).
      Die vier Pflichtzahlen stehen je Position im Journal, nicht im Chat —
      Spalten `liq_abstand`, `funding_pct`, `gebuehr_pct`, `quote_noetig`,
      `quote_beob`. Und sie sind keine Zierde: Der erste Papierlauf hat
      XAG short (Quote 19,8 % gegen nötige 33,3 %) und XAU short (23,7 gegen
      35,5) abgewiesen und drei Anläufe eröffnet — MSTR, CL, BZ.
      Punkt 2 und 3 der alten Liste sind mit angeglichen: der Hinweis in
      `wachen.json` und die Stellen in `bot.py`, die „es gibt keinen
      Live-Pfad" sagten.
      Gegengeprüft: Notausstieg bei altem Herzschlag schließt alle drei
      Positionen (`herzschlag_alt`), die Rundenrechnung erkennt sie als drei
      abgeschlossene Runden samt Funding. Die Testdaten wurden danach
      zurückgenommen, damit die Freigabe-Statistik sauber bleibt.
      **Offen bleibt daraus:** siehe T-035 (Herzschlag und Dauerbetrieb, vormals fälschlich T-032).

      Angelegt: 2026-09-01 · Zuletzt: 2026-09-01

- [ ] **T-023 — ASUS MG278 antwortet nicht auf DDC/CI, PowerDisplay lässt ihn aus**
      Kontext: Aus dem PowerToys-Report vom 02.09.2026. Von zwei Monitoren
      (beide direkt an DisplayPort) steuert PowerToys PowerDisplay nur den
      Acer XB281HK. Die **ASUS MG278** (`DISPLAY2`, EDID `ACI27A8`, in Windows
      als „Generic PnP Monitor") liefert keine DDC/CI-Daten; unabhängig von
      PowerToys mit `Agenten/Routinen/monitor-ddc-pruefen.ps1` nachgestellt:
      schon `GetCapabilitiesStringLength` scheitert mit Win32-Fehler
      `0xC0262582` (`ERROR_GRAPHICS_DDCCI_VCP_NOT_SUPPORTED`). Kein
      Software-Fehler — Reparatur nur am Monitor möglich.
      Nächster Schritt (Max, am Gerät): MG278-OSD → System Setup → DDC/CI → On;
      hilft das nicht, Monitor ~30 s stromlos, DP-Kabel/-Eingang prüfen. Danach
      `monitor-ddc-pruefen.ps1` erneut, bei Erfolg PowerDisplay „Monitore
      aktualisieren". Details: [[Hardware]], Abschnitt „Monitore und PowerToys
      PowerDisplay".
      Betrifft: Monitor ASUS MG278 · `Agenten/Routinen/monitor-ddc-pruefen.ps1`
      Angelegt: 2026-09-02 · Zuletzt: 2026-09-02

- [!] **T-015 — Seagate Portable (`G:`) wieder ab, Hauptsicherung ohne Ziel**
      Kontext: `G:` ist erneut nicht angeschlossen (`Test-Path G:\` = False; in
      der Datenträgerliste nur C:, O:, J:). Der geplante 20-Uhr-Lauf scheitert
      seit mindestens 30.08. 20:12 mit robocopy-Code 16, „Das System kann den
      angegebenen Pfad nicht finden" — dasselbe Muster wie beim abgezogenen
      Laufwerk in T-001, aber ein neuer Vorfall. `MaxHirn-Sicherung` ist
      deaktiviert, bis ein echter Lauf die Phase-8-Änderung an `sichern.ps1`
      bestätigt (neue Quelle `BrainFiles\`, `/XD Modelle Werkstatt`, Commit
      `fc483d4`/`7e3e561`). `sichern-ausser-haus.ps1` (Ziel `E:`) hängt am
      selben Nagel. `sichern-zweitkopie.ps1` (Ziel `O:`) ist am 31.08. 21:00
      grün durchgelaufen und damit bestätigt.
      Nächster Schritt: Seagate Portable anstecken, `Agenten\sichern.ps1`
      einmal von Hand laufen lassen, bei robocopy-Code < 8 `MaxHirn-Sicherung`
      wieder aktivieren (`Enable-ScheduledTask -TaskName MaxHirn-Sicherung`).
      Alternativ Ziel auf ein dauerhaft erreichbares Laufwerk umstellen.
      Betrifft: `Agenten/sichern.ps1`, `Agenten/sichern-ausser-haus.ps1`,
      Aufgabe `MaxHirn-Sicherung`
      Wartet auf: angeschlossenes Sicherungslaufwerk `G:`
      Angelegt: 2026-08-31 · Zuletzt: 2026-08-31

- [!] **T-004 — Zwölf Abschaltungen ohne Bluescreen seit 08.08., Ursache offen**
      Kontext: Alle zwölf Kernel-Power-41-Ereignisse haben `BugcheckCode = 0`
      und `PowerButtonTimestamp = 0` — kein Bluescreen, kein Speicherabbild,
      sondern harter Stromverlust. Keine WHEA-Fehler in 30 Tagen, keine
      Plattenfehler (nur ID 98, Information), kein Dump. In den drei Minuten
      vor dem letzten Abschalten steht **ein einziger** Protokolleintrag.
      **Die Beobachtung vom 28.08. ist entschieden — negativ.** Sie musste nicht
      auslaufen: seit dem Start am 28.08. um 16:00 ist der Rechner dreimal
      ausgegangen (29.08. 10:45, 29.08. 13:17, 30.08. 20:59, echte Zeitpunkte
      aus Ereignis 6008). Aus neun Vorfällen sind damit zwölf geworden, und die
      Abstände sind kürzer geworden: drei in zwei Tagen gegen sieben in den
      vierzehn Tagen davor.
      **Standby scheidet als Ursache aus.** Seit dem 28.08. 06:46 gab es keinen
      einzigen Standby-Zyklus mehr (kein Kernel-Power 42/107) — die drei neuen
      Abstürze fielen also in eine Phase ganz ohne Standby. Der Ablauf „3–10
      Minuten nach dem Aufwachen aus S3" war Begleiterscheinung, nicht Ursache.
      Das frühere Merkmal `SleepInProgress = 16` beruhte auf einer Verwechslung
      mit dem Feld `Checkpoint`; `SleepInProgress` ist bei allen zwölf `0`.
      Nächster Schritt: **Stromzufuhr ausserhalb des Netzteils prüfen** —
      Kaltgerätekabel, Steckdosenleiste, Wandsteckdose. Billig und nie geprüft,
      deshalb zuerst; danach erst der Gegentest mit einem bekannt guten Netzteil.
      Beides Handgriffe an der Hardware, also Max' Sache, und **einen nach dem
      anderen**, sonst ist unbekannt, welcher gewirkt hat. Bei zuletzt 2,5 bis
      32 Stunden Abstand zeigt sich das binnen zwei bis drei Tagen.
      Wartet auf: Max — Handgriff an Kabel und Steckdose.
      Messbefehl: Routinen/absturz-nachmessen.ps1 (nur lesend, ohne Adminrechte)
      Betrifft: [[Hardware]], Abschnitt „Nachmessung 30.08.2026, 22:20"
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-30 (22:20)

- [ ] **T-007 — 18 claude.ai-Connectors ohne einen einzigen Aufruf**
      Kontext: `claude mcp list` meldet 21 aktive claude.ai-Connectors. In
      53 gespeicherten Sitzungen wurden davon **drei** je einmal aufgerufen
      (Kalender, Gmail, Drive); die übrigen 18 kein einziges Mal — darunter
      Uber, Uber Eats, PayPal, HubSpot, monday.com, Morningstar, DataHub,
      Play Sheet Music, tldraw, Excalidraw, Sprouts, Windsor.ai, Superhuman
      Docs, ChangeThisFile, UseMyContext, Unstructured, Economic Index.
      Jeder belegt in **jeder** Sitzung Kontext, bevor ein Wort gesagt ist.
      Max hat das am 27.08. selbst als größten Hebel benannt; der Punkt ging
      danach verloren, weil er nirgends eingetragen war.
      Nächster Schritt: Max schaltet sie in den Connector-Einstellungen auf
      claude.ai ab — das geht nicht lokal und nicht aus einer Sitzung heraus.
      Messbefehl für den Vorher-Nachher-Vergleich:
      `sitzungen_auswerten.py --werkzeuge`
      Betrifft: claude.ai-Konto, nicht den Vault
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

- [?] **T-008 — MCP-Server `mail` ist nicht eingerichtet**
      Kontext: `Archiv/CLAUDE.md` beschreibt den Versand über `mail_senden`
      als den vorgesehenen Weg für „schick mir das per Mail". Der Server
      antwortet aber mit „Keine Absenderadresse hinterlegt" — in 53 Sitzungen
      wurde er kein einziges Mal erfolgreich benutzt. Der dokumentierte Weg
      existiert also nur auf dem Papier. Die CLAUDE.md ist am 28.08.
      entsprechend korrigiert.
      Nächster Schritt: `MCP-Server/mail/.venv\Scripts\python.exe einrichten.py`
      — braucht Absenderadresse und App-Passwort, also Max' Zutun.
      Wartet auf: Zugangsdaten von Max
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28

- [?] **T-009 — `Zugaenge.md` als einzige Notiz ohne Frontmatter**
      Kontext: Am 30.08.2026 haben alle 21 übrigen Notizen in `Wissen/`
      YAML-Frontmatter mit stabiler `id` bekommen, dazu `Wissen/INDEX.md` als
      vollständige Registry. `Zugaenge.md` wurde bewusst ausgelassen, weil sie
      in [[Schutzregeln]] unter den geschützten Schlüsseldateien steht und dort
      kein Agent ohne ausdrückliche Anordnung schreibt. Sie ist in der Registry
      geführt, hat aber keine `id`. Fachlich spricht nichts dagegen — das
      Frontmatter berührt keine Zugangsdaten, sondern steht davor.
      Nächster Schritt: Max gibt frei (oder nicht); dann acht Zeilen Frontmatter
      voranstellen, `id: 20260830-zugaenge`, `tags: [sicherheit]`.
      Vorschlag zum selben Themenkreis, nicht eingetragen als eigener Punkt:
      Die Dateinamen in `Wissen/` sind gemischt geschrieben statt durchgehend
      kleingeschrieben. Eine Umbenennung würde alle `[[Wikilinks]]` brechen und
      ist den Gewinn vermutlich nicht wert.
      Betrifft: `Wissen/Zugaenge.md`, `Wissen/INDEX.md`
      Wartet auf: Freigabe von Max
      Angelegt: 2026-08-30 · Zuletzt: 2026-08-30

- [ ] **T-036 — Codex über OmniRoute: Provider „codex" hat im Router keine aktiven Credentials**
      Kontext: Am 07.09.2026 war `MaxHirn/.codex/config.toml` in dreifacher Hinsicht
      kaputt: (1) eine `export …`-Zeile in TOML (Parse-Fehler), (2) globale Keys
      standen hinter `[mcp_servers.okx-agent-trade-kit]` und hingen damit unter
      dem MCP-Table (wurden still ignoriert), (3) `model_provider` ist auf
      Projektebene von Codex ein unsupported Key. Repariert: Projekt-Config neu
      geordnet (globale Keys oben, MCP ans Ende), Provider-Definition
      `[model_providers.omniroute]` in die User-Config `~/.codex/config.toml`
      gelegt (additiv, `.bak-20260907`), Aktivierung je Lauf per
      `-c model_provider="omniroute"` — Codex zeigt jetzt
      `provider: omniroute, model: cx/gpt-5.5`. Der Endpunkt selbst antwortet
      (401 ohne Key, Modellkatalog mit Key). **Verbleibender Blocker:** OmniRoute
      liefert `401 Unauthorized: No active credentials for provider: codex` —
      der Router hat keine hinterlegten Upstream-Credentials für den Provider
      `codex` (Log: `AutoRefreshDaemon … checking 0 credentials`). Das ist der
      seit 07.09. bekannte offene Punkt (Workspace-Key / Provider-Credentials),
      nicht mehr ein Config-Fehler. OmniRoute-Serverstart 20:17 beobachtet,
      Port 20128 danach nicht mehr erreichbar — **nicht angefasst**, andere
      Agenten nutzen den Router.
      Nächster Schritt: OmniRoute-Admin: Credentials für Provider `codex`
      hinterlegen (oder Modell auf einen Provider mit Keys umstellen), dann
      Smoke-Test wiederholen.
      Betrifft: `MaxHirn/.codex/config.toml`, `~/.codex/config.toml`, OmniRoute
      Wartet auf: Credentials für Provider `codex` in OmniRoute
      Angelegt: 2026-09-07 · Zuletzt: 2026-09-07

- [ ] **T-018 — Saisonalität rechnet nur auf 50 Tagen, nicht auf der tiefen Reihe**
      Kontext: `indikatoren.saisonalitaet()` (neu am 01.09.2026, hoch gewichtet
      im Signal — siehe [[Saisonalitaet-Signal]]) läuft auf den 300×4h-Kerzen
      des gehandelten Kontrakts, also ~50 Tagen ≈ 7 Beobachtungen je Wochentag.
      `bot.hebel_deckel()` und `bot.trefferquote()` können über `--historie
      auto` schon auf den tieferen `<Basis>-USDT-SWAP` ausweichen; die
      Saisonalität nicht, weil sie in `lage()` steckt und nur `k` bekommt.
      Nächster Schritt: prüfen, ob `zeige_lage()` in `bot.py` die Saisonalität
      auf `k_hist` nachrechnen und `z["sais"]` samt Signal-Merge ersetzen soll,
      wenn `--historie` gesetzt ist — analog zum bestehenden Muster für
      Hebel-Deckel und Trefferquote.
      Betrifft: `Agenten/Handel/xperp/indikatoren.py`, `Agenten/Handel/xperp/bot.py`
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-01


- [ ] **T-041 — Drei Spuren startet der Dauerlauf, ohne dass sie den Bus melden**
      Kontext: Beim Reparieren von `Bus/tests/test_anbindung_handel.py` am
      13.09.2026 aufgefallen. Die Pruefung war seit dem SWAP-Umbau (12.09.2026)
      **tot**: sie suchte die per `subprocess.run` gestarteten Dateinamen als
      Literale in der Aufrufliste, dort steht seitdem die Variable `skript`
      (`SPUREN[spur].get("skript", "handeln.py")`). Sie fand nichts, brach mit
      „keine per subprocess gestarteten .py-Dateien gefunden“ ab - und es fiel
      nicht auf, weil `test_ende_zu_ende.py` genau daran scheiterte.
      Nach der Reparatur (drei Quellen: `SPUREN["skript"]`, der get-Default,
      Listenelemente) prueft sie wieder - und findet sofort drei Luecken:
      `swap/handeln.py`, `spiegel/spiegel.py` und `orbk/handeln.py` tragen kein
      `ereignis.lauf("handel/<spur>")` (0 Treffer fuer "ereignis" in der ganzen
      Datei). `xperp/handeln.py` und `scanner/handeln.py` haben es.
      Folge: Start und Ende dieser drei Spuren erreichen den Bus nicht; sichtbar
      ist nur, was der Dauerlauf aus ihrer Ausgabe herausfiltert. Ob eine Spur
      ueberhaupt lief, steht damit nirgends.
      Naechster Schritt: in den drei Dateien den Hauptlauf in
      `with ereignis.lauf("handel/<spur>"):` legen (Muster: `xperp/handeln.py`),
      dann `Bus/tests/test_anbindung_handel.py` und die Suite
      (`python tests/test_ende_zu_ende.py`) gruen laufen lassen.
      Nicht selbst angefasst: laufender Handel (der Dauerlauf startet diese
      Spuren als Unterprozesse), und es ist ein eigener Auftrag.
      Betrifft: `Agenten/Handel/{swap,spiegel,orbk}`, `Agenten/Bus/tests/`
      Angelegt: 2026-09-13

## Erledigt

- [x] **T-037 — Echter Umzug: Archiv ganz aus dem Vault, konfigbasiert** — erledigt
      2026-09-07. Folgeauftrag zum Junction-Umzug vom 06.09. (Commit ad469fb).
      Die sechs NTFS-Junctions unter `MaxHirn/Archiv/` sind entfernt; die
      Archivdaten (44 GB, 64.745 Dateien) liegen nur noch auf `O:\Archiv`. Alle
      Werkzeuge finden sie über die neue User-Umgebungsvariable
      `ARCHIV_ROOT = O:\Archiv` (Rückfall im Code auf die Vault-Lage).
      `ArchivSuche/` (git-versionierter Code) und der Index `archiv_index.db`
      (neu baubar) bleiben auf `C:`.
      Geändert: `index.py`, `server.py` (`ROOT` aus `ARCHIV_ROOT`);
      `archiv_mcp.py`, `mailversand.py` (Datenwurzel von Indexwurzel getrennt);
      `sichern.ps1` / `sichern-zweitkopie.ps1` (Junction-Sonderfall raus, zweiter
      robocopy-Lauf `O:\Archiv` → `G:`/`J:` bleibt). `vektor_index.py`,
      `vektor_suche.py`, `search_cli.py` unverändert (nur DB).
      Gegenprobe: `index.py` inkrementell → 9712 Einträge, 0 verändert, 0
      entfernt; `search_cli.py`-Testsuche unverändert; `archiv`- und `mail`-MCP
      funktional gegen `O:` geprüft; `90-pruefen.ps1` — MCP-Pfade und Suchindex
      grün. Doku: `Ordnerstruktur.md`, `Schutzregeln.md`, `MaxHirn/CLAUDE.md` +
      `AGENTS.md`, `Archiv/CLAUDE.md` + `AGENTS.md`, `Archiv/README.md`.
      Offen: laufende Prozesse (Claude Desktop, Hermes) sehen `ARCHIV_ROOT` erst
      nach Neustart.
      Betrifft: `MaxHirn/Archiv/ArchivSuche/`, `Agenten/MCP-Server/{archiv,mail}/`,
      `Agenten/sichern*.ps1`
      Angelegt: 2026-09-07 · Zuletzt: 2026-09-07

- [x] **T-034 — Hauptsicherung fehlschlug am 04.09. weil Hermes live läuft** — erledigt
      2026-09-04. Um 20:00 meldete `sichern.ps1` robocopy-Code 11 (FEHLER), obwohl
      47,5 GB kopiert worden waren. Ursache: **Hermes läuft seit dem Umbau
      innerhalb der Sicherungsquelle** (`BrainFiles/Agenten/Hermes`) und hält
      beim 20-Uhr-Lauf seine drei lebenden Laufzeitordner offen:
      `pending_messages/`, `cache/terminal-output/`, `telemetry/shared_metrics/`.
      robocopy scheiterte daran mit Zugriff verweigert, verbrauchte die
      Wiederholungen und brach als Fehler ab (dieselbe Klasse wie der
      `logs`-Ausschluss vom 23.08.).
      **Fix:** diese drei Namen in `/XD` aller drei Sicherungsskripte
      (`sichern.ps1`, `sichern-zweitkopie.ps1`, `sichern-ausser-haus.ps1`)
      aufgenommen — gleiche Behandlung wie `logs` und Claude. Stufe 1:
      `.bak-20260904` angelegt, echter Lauf bestätigte **robocopy-Code 3,
      0 Fehler** (Hermes lief dabei). Commit `8a23529` (Autor Hermes).
      Die drei Ordner sind reine Durchlauf-Caches, damit kein Verlust.
      `MaxHirn-Sicherung` (Aufgabe) war Ready und lief fehlerfrei.
      Angelegt: 2026-09-04 · Zuletzt: 2026-09-04
      Betrifft: `Agenten/sichern*.ps1`, `Agenten/Hermes/{pending_messages,cache/terminal-output,telemetry/shared_metrics}`

- [x] **T-025 — Hauptsicherung nach `G:` hat zwei Tage übersprungen**
      Erledigt 2026-09-02. Die Ursache stand bereits in T-022: Die Aufgabe war
      deaktiviert und wurde heute wieder aktiviert — der Eintrag hier war
      insoweit doppelt und ist korrigiert worden. Bestätigt ist der Lauf jetzt
      auch: `G:` und `O:` tragen um 22:35 den Stand von heute, einschließlich
      der Regeländerungen dieser Sitzung. Beide Kopien sind damit wieder
      aktuell.
      Beobachtung am Rand: Ein zweiter Lauf um 22:40 brach mit `0xC000013A`
      (abgebrochen) ab — zeitgleich mit `MaxHirn-Posteingang`, was nach einem
      Sammelstart von Hand aussieht, fünf Minuten nach dem regulären. Die
      Hausregel „`sichern.ps1` nie doppelt starten" gilt genau dafür; Schaden
      ist keiner entstanden, die Kopie von 22:35 steht.
      Die Erkennungslücke ist geschlossen: Abschnitt 9 der Systemprüfung meldet
      seit heute nicht nur fehlerhafte Läufe, sondern auch ausgebliebene — jede
      `MaxHirn-*`-Aufgabe, die länger als 48 h nicht gestartet ist. Genau das
      hatte zwei Tage lang niemand gesehen.

- [x] **T-012 — Alte Zweige auf `G:` abräumen**
      Kontext: Die Sicherung läuft ohne `/MIR` und räumt deshalb nichts weg,
      was in der Quelle verschwindet. Auf `G:\MaxHirn-Sicherung` liegen nach
      dem Umbau vom 30.08.2026 noch die 51 GB `Modelle\` (ab jetzt aus der
      Sicherung ausgenommen) und der alte Zweig unter dem früheren Namen „Claude“ (er heißt jetzt
      `Archiv`, wird also ein zweites Mal kopiert).
      **Gemessen 03.09.2026**, nach einem vollständigen Lauf der neuen
      Sicherung (robocopy-Code 3, 54:38 Dauer, 29,1 GB übertragen): Auf `G:`
      liegen 190 GB, frei sind 68,5 GB von 2,75 TB.

      | Ordner | GB | Was |
      |---|---|---|
      | `Claude` | 93,8 | alter Archivname, heute `MaxHirn\Archiv` — doppelt gehalten. Allein `Claude\Posteingang\Maximilianbackup0924` sind 48,8 GB |
      | `MaxHirn` | 70,4 | aktuell (Quelle 45 GB; die Differenz sind Altstände, die ohne `/MIR` liegenbleiben) |
      | `Modelle` | 21,1 | seit 30.08.2026 aus der Sicherung ausgenommen |
      | `MCP-Server`, `Hermes`, `Handel`, `Wissen`, `Routinen`, `GitHub`, … | ~5 | Struktur **vor** der Ordnertrennung, heute alles unter `Agenten/` |

      **Abgeräumt am 03.09.2026 auf Max' Freigabe.** Entfernt wurden
      `Modelle\`, `MCP-Server\`, `Hermes\`, `GitHub\`, `Handel\`, `Routinen\`,
      `Wissen\`, `Referenz\`, `.obsidian\`, `.claude\`, `.agents\`, `.codex\`,
      elf lose Altdateien der obersten Ebene und zuletzt `Claude\`.

      Jeder Ordner wurde vorher gegengeprüft, keiner blind gelöscht. Zwei
      Fälle, in denen die Prüfung etwas gefunden hat:

      - **`Codex\` und `Coworking-Space\` (0,4 GB) stehen bewusst noch da.**
        Ihr heutiger Ort ist `Werkstatt\`, und Werkstatt ist aus der Sicherung
        ausgenommen — die Kopie auf `G:` ist die einzige, unter anderem vom
        eigenen `m3u_cleaner`. Siehe T-032.
      - **`Claude\` war nur zu 44,5 von 93,8 GB eine Dublette.** Drei
        Prüfrunden: Pfadvergleich (45 von 64.829 Dateien ohne Entsprechung),
        Namensvergleich über Archiv und Werkstatt (18 davon lagen umsortiert
        woanders), Größenvergleich der restlichen 27. Dabei kam heraus, dass
        die 24 ELSTER-Belege beim Einsortieren **umbenannt** worden waren
        (`1-Lohnsteuerbescheinigung_2022_…` → `2022_Belegabruf_…_2026-08-19`)
        und byteweise identisch vorliegen. Echte Unikate blieben drei:
        `Maximilianbackup0924` (52,4 GB), `EFIbackup0924` (524 MB) und
        `OKX_API.env` (124 B). Sie liegen jetzt in
        `G:\Unikate-aus-Altzweig-20260903\` mit einer `LIESMICH.md`, die den
        Weg dorthin beschreibt.

      **Die Lehre für das nächste Mal:** Ein Pfadvergleich allein hätte 50 GB
      gelöscht oder 41 GB verschont — beides falsch. Erst Pfad, dann Name,
      dann Größe.

      **Ergebnis:** frei auf `G:` von 68,5 GB (vor dem Lauf) auf **109,5 GB**.
      Im Sicherungsordner stehen nur noch `MaxHirn\`, `Agenten\`, die aktuellen
      Wurzeldateien und die beiden zurückgestellten Ordner aus T-032.
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-03

- [x] **T-030 — Drei Handels-Routinen in die Aufgabenplanung eintragen** —
      erledigt 2026-09-02 auf Max' Anweisung. Angelegt mit
      `Register-ScheduledTask` (nicht `schtasks` — das setzt kein „Starten,
      sobald möglich", und ohne das fällt ein Termin nach einer
      Hardware-Abschaltung ersatzlos aus): `MaxHirn-Marktscanner` täglich
      07:30, `MaxHirn-Kraken-Spur3` täglich 07:45, `MaxHirn-Handel-Wachen`
      sonntags 08:00. Alle drei einmal aus der Aufgabenplanung heraus gestartet
      und geprüft — Ergebniscode 0, Protokolle vollständig, keine
      Doppelkäufe. Damit sind es neun geplante Aufgaben. Beide Tagesläufe
      handeln nur auf Papier (`MAXHIRN_ROUTINE=1`, kein `--live`).

- [x] **T-029 — Dritte Spur: Kraken wirklich bauen** — erledigt 2026-09-02
      Auf Max' Anweisung („ich will ihn") das nachgeliefert, was T-027 als Weg
      beschrieben hatte. Neu unter `Agenten/Handel/kraken/`: `wachen.json`
      (EUR, eigener Rahmen), `kraken.py` (REST, nur Standardbibliothek, kein
      Auszahlungsweg), `scan.py`, `handeln.py`, `wachen_kraken.py`, README.
      Die währungsneutrale Rechnung der Bedingungen 2–5 wird aus
      `scanner/wachen_pruefung.py` **importiert**, nicht abgeschrieben.
      `freigabe.py` kennt jetzt drei Spuren und zeigt die Währung der Spur an;
      seine Bestandsschlüssel heißen dafür `gebunden`/`verlust_gesamt` statt
      `…_usd` (`scanner/handeln.py` nachgezogen, beide Spuren nachgeprüft).
      Gemessen dabei: Kraken nimmt 0,40 % Taker statt 0,05 % bei OKX — eine
      Runde kostet 0,80 %. Deshalb Stop mindestens 5 %, C/R mindestens 2,0,
      Score mindestens 65, und die Gebühr steht auch im Papierlauf in den
      Beträgen. Zweiter Befund: Auf dem Konto liegen 0,0094 EUR frei, der Rest
      steckt in Coins — daher die zusätzliche Sperre `mindest_guthaben_eur`.
      Erster Papierlauf gelaufen: 4 Positionen, 200 EUR gebunden; die sechs
      Wochen aus Bedingung 1 laufen ab heute. `handel_erlaubt` bleibt `false`.
      Die schreibenden MCP-Werkzeuge bleiben gesperrt — die Grenze verläuft
      jetzt nicht mehr zwischen Börsen, sondern zwischen Wegen.

- [x] **T-028 — Bestätigungsdialog zum Scharfschalten** — erledigt 2026-09-02
      `Agenten/Handel/freigabe.py` gebaut und an `scanner/handeln.py --live`
      angebunden. Beide Spuren, prüft gegen `wachen.json`, führt selbst nichts
      aus. Die Obergrenze jedes Reglers ist der Wachen-Wert, der Hebeldeckel
      ist senkbar, nie hebbar. Ausstiege laufen nie durch das Fenster.
      Beim Bauen gemessen: `sys.stdin.isatty()` meldet in der Git-Bash unter
      Windows auch bei umgeleitetem stdin ein Terminal — als Sperre gegen den
      Zeitplan taugt es nicht. Deshalb lehnt das Fenster nach 120 s ohne
      Bedienung von selbst ab; das ist der tragende Schutz. Zusätzlich setzen
      `Routinen/marktscanner.ps1` und `handel-wachen.ps1` jetzt
      `MAXHIRN_ROUTINE=1`.
      Offen als eigener Punkt: `xperp/bot.py` ist nicht angebunden — er legt
      Befehle ohnehin nur vor.

- [x] **T-027 — Handelsregeln decken Kraken nicht ab**
      Erledigt 2026-09-02: Neuer Abschnitt *Kraken ist keine dritte Spur* in
      `Wissen/Schutzregeln.md`. Kraken bleibt lesend — die neun lesenden
      Werkzeuge sind ausdrücklich erlaubt, `kraken_order_aufgeben` und
      `kraken_order_stornieren` ausdrücklich nicht, auch nicht mit Bestätigung
      im Chat. Begründung ist der eigene Maßstab des Abschnitts: ohne
      `wachen.json`, Journal und Herzschlag fehlen alle drei Eigenschaften, die
      die Handelserlaubnis tragen. Der Weg zu einer echten dritten Spur ist
      beschrieben. Nicht auf eine Entscheidung gewartet, weil die sichere
      Richtung aus der bestehenden Regel folgt — die Öffnung bleibt möglich.

- [x] **T-026 — `absturz-recovery.md` liegt lose im Skill-Ordner und wird nie geladen**
      Erledigt 2026-09-02: nach `skills/absturz-recovery/SKILL.md` gehoben
      (`git mv`, Inhalt unverändert), die `.bak-20260902` daneben entfernt. Der
      Skill erscheint seither in der Skill-Liste einer Sitzung. Abschnitt 10b
      der Systemprüfung meldet ab jetzt jede lose `.md` im Skill-Ordner und
      jeden Skill-Ordner ohne `SKILL.md`.

- [x] **T-024 — `CLAUDE.md` und `AGENTS.md` sind auseinandergelaufen**
      Erledigt 2026-09-02: Beide Paare zusammengeführt, jedes ist jetzt Zeichen
      für Zeichen gleich — wie in `Werkstatt/` schon erprobt. Übernommen wurde
      jeweils die Vereinigung: die Vektorsuche (`vektor_suche.py`, `--hybrid`,
      Abdeckung, Indexstand 19.08.2026) aus `Archiv/AGENTS.md`, die Mail-Sperre,
      der Netzteil-Kontext, die Umlaut-Suchfalle und die
      `sort_inbox.py`-Sicherungen aus `Archiv/CLAUDE.md`, dazu die schärfere
      Notizen-Regel aus `MaxHirn/AGENTS.md`. Der gemeinsame Kopf nennt jetzt die
      maschinelle Prüfung, die das hält (Abschnitt 10a in `systempruefung.ps1`).

- [x] **T-022 — `MaxHirn-Sicherung` deaktiviert, `MaxHirn-Posteingang` scheiterte**
      Erledigt 2026-09-02: `MaxHirn-Sicherung` auf Anweisung von Max wieder
      aktiviert (`Enable-ScheduledTask`), Auslöser unverändert täglich 20:00,
      „Starten sobald möglich". Warum sie aus war, ist nicht abschließend
      geklärt — vermutlich im Zuge von T-015 (Seagate `G:` war zeitweise ab).
      Der `MaxHirn-Posteingang`-Fehler vom 01.09. 22:00 war der Pfad
      `Agenten\Claude\ArchivSuche` — doppelt veraltet (`Agenten\` statt
      `MaxHirn\`, `Claude\` statt `Archiv\`). Der Wrapper `posteingang.ps1`
      zeigt inzwischen korrekt auf `MaxHirn\Archiv\ArchivSuche` (T-016), der
      nächste Lauf heute 22:00 sollte grün sein.

- [x] **T-021 — Fremd-MCP-Server apify und okx-Lokalklon entfernt**
      Erledigt 2026-09-02: Auf Anweisung von Max beide gelöscht.
      `Agenten/MCP-Server/ant.dir.gh.apify.apify-mcp-server/` (node_modules nur
      noch tote pnpm-Junctions auf den alten `…\MaxHirn\MCP-Server\`-Pfad) und
      `Agenten/MCP-Server/okx/` (eigenes `.venv`, `okx_mcp.py` mit doppelt
      kaputtem Pfad `…\MaxHirn\Claude\Worktrees\…`). Beide in keiner `.mcp.json`;
      der aktive okx-Zugang läuft über den HTTP-Server `okx-agent-trade-kit`.

- [x] **T-010 — Kimi-K2.7-Code entfernt**
      Erledigt 2026-09-02: Auf Anweisung von Max gelöscht. War ein
      HuggingFace-Repo-Klon (`.git` mit LFS, ~31 GB, keine Gewichtsdatei je
      ausgecheckt) unter `O:\Modelle\Kimi-K2.7-Code`. Reproduzierbar per
      `git clone`, falls je gebraucht.

- [x] **T-020 — Fremd-Repo `MaxHirn/OmniRoute` lag am falschen Ort**
      Erledigt 2026-09-02: Klon von `github.com/diegosouzapw/OmniRoute`,
      Branch `release/v3.8.51`. Beide Klone geprüft — weder unter `MaxHirn/`
      noch unter `Werkstatt/` gab es eigene Commits, Stashes oder Branches
      (Werkstatt-Reflog: nur `clone`; die geänderten `package*.json` dort waren
      reine `npm install`-Nebenwirkung). Der alte `Werkstatt/OmniRoute`
      (älterer HEAD, 4,3 GB mit `node_modules`/`dist`) wurde gelöscht, der
      neuere saubere Klon aus `MaxHirn/` (715 MB, Arbeitsbaum sauber) an seine
      Stelle verschoben. Die Übergangsregel `MaxHirn/OmniRoute/` in `.gitignore`
      ist wieder raus — `Werkstatt/*/` deckt den neuen Ort ab. Wer dort
      arbeiten will: `npm install` neu.

- [x] **T-001 — Sicherungslaufwerk G: fehlt, Hauptsicherung hat kein Ziel**
      Erledigt 2026-08-28: Kein Defekt. Max hatte die USB-Platten für einen
      CMOS-Reset abgezogen. Seagate Portable ist wieder angeschlossen,
      `G:\MaxHirn-Sicherung` erreichbar (2751,1 GB, 128,8 GB frei, `Healthy`).
      Der 20-Uhr-Lauf kann wieder arbeiten. Der Fehlstand bestand nur, solange
      die Platte ab war.

- [x] **T-002 — Auslagerungsdatei liegt auf einer USB-Platte**
      Erledigt 2026-08-28: Max hat den Eintrag mit erhöhten Rechten entfernt.
      Nachgemessen um 17:15: `PagingFiles` enthält nur noch
      `c:\pagefile.sys 0 0` und `o:\pagefile.sys 4096 16384`, auf `G:` liegt
      keine `pagefile.sys`. Ob damit auch T-004 verschwindet, ist offen —
      die Hypothese ist nicht bewiesen, nur die Fehlkonfiguration beseitigt.
      Sicherung des Schlüssels: `Routinen/sicherungen/MemoryManagement-20260828.reg`.

- [x] **T-003 — Windows Search stürzt seit 24.08. in Endlosschleife ab**
      Erledigt 2026-08-28: Der Starttyp wurde um **16:00:04** auf „Deaktiviert"
      gesetzt (Ereignis 7040). Letzter Absturz **15:59:41**, seither **null** in
      77 Minuten. Vorher waren es 16.926 in sieben Tagen, allein 984 zwischen
      dem Start um 15:19:36 und 15:59:41 — rund 24 pro Minute.
      Der Suchindex wurde nicht neu gebaut; die Suche im Startmenü bleibt tot.
      Max' eigene Archivsuche ist davon nicht betroffen (SQLite).
      Gewinn: Das Systemprotokoll reicht wieder bis zum **05.08.2026** zurück
      statt vier Tage — die Absturzspuren für T-004 überleben jetzt lange genug.

- [x] **T-005 — J: (WD My Book) nicht angeschlossen, iCloud-Junction ins Leere**
      Erledigt 2026-08-28: Die Platte ist wieder da. `Extern_BackUp`, 1.953 GB
      gesamt, 246 GB frei, `Healthy`; NTFS meldete um 15:47:51 „Volume J: ist
      fehlerfrei". Die Junction `C:\Users\faupe\iCloudPhotos` löst wieder auf.
      Unverändert gilt: 479 unkorrigierte Lesefehler (Messung 14.08.), die
      30.635 Mediendateien liegen weiter auf dem schwächsten Laufwerk.

- [x] **T-006 — Echtzeituhr ging 68 Minuten nach**
      Erledigt 2026-08-28: harmlos. Die Korrektur um 15:20:12 kam 36 Sekunden
      nach dem Kaltstart um 15:19:36 — der CMOS-Reset hatte die Uhr geleert,
      der Zeitdienst zog sie einmal gerade. **Seither kein weiterer Sprung**,
      Abweichung 0,12 s gegen `time.windows.com` (gemessen 17:17).
      Eine schwache CMOS-Batterie würde erneut driften; ein zweiter Messpunkt
      in einigen Tagen bestätigt es endgültig. Bis dahin kein Handlungsbedarf.

- [x] **T-031 — Telegram-Bot fuer Meldung und Steuerung einrichten** — erledigt 08.09.2026
      Die fünf Module (`Handel/melder.py`, `tagesbericht.py`, `freigabefenster.py`,
      `dauerlauf.py`, `Routinen/handel-dauerlauf.ps1`) waren seit 07.09. fertig,
      aber stumm — es fehlten nur die Token.

      Eingerichtet 08.09.2026: Bot **@CodeClaudebitbitbot**. `TELEGRAM_TOKEN`
      und `TELEGRAM_CHAT_ID` (`7648512088`) stehen als **Benutzervariablen** in
      `HKCU\Environment`. `melder.py` liest sie live aus der Registry
      (`_aus_registry`), ein laufender Dauerlauf braucht dafür **keinen
      Neustart**. Probe bestätigt, der Bot beantwortet Befehle.

      Fallen fürs nächste Mal:
      - Der Bot muss zuerst **vom Nutzer angeschrieben** werden, sonst gibt
        `sendMessage` HTTP 400 ("chat not found").
      - `melder.py --chat-id-suchen` liefert nichts, solange der Dauerlauf
        läuft: Telegram gibt jede Nachricht per `getUpdates` nur einmal aus,
        der Dauerlauf holt sie zuerst. Chat-ID dann aus `dauerlauf.log`
        (Zeilen „Befehl: …") lesen oder den Dauerlauf kurz stoppen.
      - Gültige Befehle: `/ja [h]`, `/nein`, `/hilfe`.

      Geplante Aufgaben stehen alle (State Ready): `MaxHirn-Handel-Dauerlauf`
      (+ `-Waechter`), `MaxHirn-Handel-Wachen`, `MaxHirn-Verbesserer`.

- [ ] **T-035 — Spur 2 ist nur im Dauerbetrieb nutzbar (Herzschlag 30 min)**
      Aufgefallen 03.09.2026 beim Bau des XPERP-Live-Pfads (T-019).
      `xperp/wachen.json` setzt `herzschlag_max_minuten` auf 30. Das ist
      richtig — eine gehebelte Position, die einen Neustart "überlebt", ist
      unbewacht, und die Kernel-Power-41-Abschaltungen aus [[Hardware]]
      nehmen den Rechner ohne Vorwarnung mit.
      Die Folge ist aber unbequem: Läuft `dauerlauf.py` nicht, ist der
      Herzschlag nach einer halben Stunde alt, und der nächste Lauf stellt
      **zuerst alles flach**, bevor er irgendetwas anderes tut. Gemessen am
      03.09.2026: vier Stunden nach dem Papierlauf meldete der Tagesbericht
      "Herzschlag alt (Bed. 3)".
      Damit sammelt ein von Hand gestarteter Papierlauf nie die 50 Runden
      aus Bedingung 1 — er schließt jedes Mal, was er beim letzten Mal
      eröffnet hat.
      Zwei Wege, und die Entscheidung gehört Max:
      1. Den Dauerlauf tatsächlich durchlaufen lassen (T-031 zuerst, sonst
         läuft er stumm). Dann passt der 15-Minuten-Takt zu den 30 Minuten.
      2. Den Herzschlag an eine tatsächliche Taktung anpassen — nicht
         abschalten. Bei einem Lauf pro Tag wären 1440+ Minuten ehrlich,
         aber dann ist eine Position bis zu einem Tag unbewacht.
      Betrifft: `Agenten/Handel/xperp/wachen.json`, `dauerlauf.py`

- [x] **T-039 — Hebel-Deckel-Tabelle in [[XPERP-Handel]] ist überholt** — erledigt 2026-09-13
      **Erledigt 2026-09-13.** Tabelle auf 3,6× (SOL), 4,1× (HYPE), 1,7×
      (ZEC) ersetzt, die Aussage „alle Tore bestanden" für die drei
      zurückgenommen, und der Messfehler als Falle danebengeschrieben
      (Deckel auf **Tageskerzen** rechnen — das 300-Kerzen-Fenster des
      gehandelten Kontrakts sind nur 50 Tage).
      Aufgefallen 09.09.2026. Die Tabelle in `Wissen/XPERP-Handel.md`
      (Abschnitt „Hebel-Deckel ≥ 5", Zeilen 165–171) stammt aus einer
      **fehlerhaften Messung**: `auswahl.py` leitete den Deckel aus 300
      4H-Kerzen ab, das sind nur 50 Tage. SOLs Rücklauf vom 31.05.2026 lag
      außerhalb dieses Fensters.
      Behoben ist der Code — `mae_tage()` rechnet jetzt auf 300 **Tages**kerzen,
      committet. Die Notiz nicht.

      | Wert | steht dort | gemessen (200 Tage) |
      |---|---|---|
      | SOL | 10,0× | **3,6×** |
      | HYPE | 6,4× | **4,1×** |
      | ZEC | 5,8× | **1,7×** |

      Damit trägt die Überschrift „Hebel-Deckel ≥ 5" für keinen der drei
      Werte mehr. Zu tun: Tabelle ersetzen, den Messfehler als Falle
      danebenschreiben (sonst wiederholt ihn die nächste Sitzung), und die
      Aussage „alle Tore bestanden" für die drei zurücknehmen.
      Betrifft: `MaxHirn/Wissen/XPERP-Handel.md`
      **Nachtrag 13.09.2026 (Max' Auftrag „README-Tabelle richtigstellen“):**
      Die Tabelle in `xperp/README.md` (Abschnitt „Gemessen am 01.09.2026“)
      trug noch die alten Deckel 10,0×/6,4×/5,8× — ersetzt auf 3,6×/4,1×/1,7×,
      „alle Tore bestanden“ zurückgenommen, Messfehler als Falle daneben
      (konsistent zu dieser Notiz). Dazu `bot.hebel_deckel()` auf Tageskerzen
      gezogen (`auswahl.mae_tage`): die Aufrufe in `pruefpflicht()` (neuer
      Parameter `stat_id`) und `zeige_lage()` holen jetzt die 1D-Reihe der
      Statistik-Quelle (bei `--historie` die des SWAP), ebenso der
      `historie.py`-Vergleich; Test `xperp/test_deckel.py` (3 Tests, Seam
      `bot.tages_kerzen_quelle`), alle 12 xperp-Tests grün. Frische
      CHIP-Messung auf Tagesbasis: jung 4,3× / 48 % vs. SWAP 2,2× / 29 %
      gegen 34 % nötig.

- [?] **T-040 — SOL long, 106 USD: Hebel 5× liegt über dem Deckel**
      Anweisung von Max am 09.09.2026: „SOL long 5x hebel 106 usd und stop
      schlage vor oder setz automatisch klug". Der Stop ist **gemessen**
      (`xperp/stopwahl.py`), der Hebel ist der Konflikt.

      Gemessene Geometrie: **Stop 3,00 ATR / Ziel 4,00 ATR**, E = +0,321 %
      je Runde über alles, +0,894 % in der jüngeren Hälfte, 469 Ziel- gegen
      557 Stop-Ereignisse, 24 von 42 Kombinationen in beiden Hälften positiv.
      Bei 1,92 % ATR sind das **5,75 % Stop / 7,66 % Ziel**.

      Der Deckel für SOL long ist **3,5–3,6×** (größter 7-Tage-Rücklauf
      27,9 %). Gerechnet bei Kurs 100,68:

      | | Nominal | Kontrakte | Verlust am Stop | Liq entfernt |
      |---|---|---|---|---|
      | 5× | 529,58 USD | 526 | 30,46 USD (28,8 % der Margin) | 19,5 % |
      | 3× | 317,14 USD | 315 | 18,24 USD (17,3 % der Margin) | 32,8 % |

      3× passt außerdem zu „lieber mehrere Anläufe": rund 6 statt 3 aus
      106 USD. `Wissen/Schutzregeln.md` führt „Hebel höchstens `hebel_deckel`"
      als auch mit Anweisung feste Grenze.
      **Wartet auf Max.** Bestätigt er 5×, wird 5× ausgeführt — vollständig,
      nicht stillschweigend kleiner.
      Vor dem Auftrag `bot.py` **frisch** laufen lassen, die Zahlen oben sind
      vom 09.09.2026.
