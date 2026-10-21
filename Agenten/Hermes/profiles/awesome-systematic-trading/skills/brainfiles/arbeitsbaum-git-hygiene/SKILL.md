---
name: arbeitsbaum-git-hygiene
category: brainfiles
description: "Use when Commits fremde Aenderungen mitnehmen koennten."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [git, arbeitsbaum, fremdarbeit, gitignore, commit, brainfiles]
    related_skills: [brainfiles-auftrag, hermes-config-ops, sichern]
---

# Fremdarbeit im Arbeitsbaum stehen lassen, eigene Aenderung committen

An einem BrainFiles-Baum arbeiten **mehrere Sitzungen gleichzeitig** (Desktop, CLI,
Telegram, Bots). Deshalb steht beim Commit fast immer mehr im Baum als die eigene
Aenderung. Dieser Skill ist die Disziplin, die eigene Aenderung sauber
herauszuschneiden — Fachliches und Dokumentation stehen in `brainfiles-auftrag`,
die Hermes-Config im Einzelnen in `hermes-config-ops`.

## Wann

- `git status` zeigt Dateien, die diese Sitzung nie angefasst hat
- in EINER Datei stehen eigene und fremde Aenderungen nebeneinander (`config.yaml`,
  Bus-Zustaende, `stand.json`, Skill-Dateien)
- eine Datei soll aus dem Verlauf verschwinden (Nebenprodukt eines Fremdprogramms)
- eine `.gitignore`-Freigabe soll zurueckgenommen werden

## Regeln (immer)

1. **Nie `git add -A`, nie `git commit -a`.** Nur namentliche Pfade stagen
   (`git add -- <pfad1> <pfad2>`). Der Hinweis „modified by sibling subagent" in einem
   Werkzeug-Ergebnis ist echt, nicht Rauschen.
2. **Vor dem Commit zwei Blicke:** `git status --porcelain` (was ist ueberhaupt da) und
   `git diff --cached` (was geht wirklich mit). Danach `git show --stat` gegen die
   Absicht halten.
3. **Gemischte Datei = hunk-weise stagen, nicht die Datei opfern und nicht die
   Fremdarbeit mitnehmen.** `git restore --staged <datei>`, dann
   `printf 'n\nn\ny\n' | git add -p -- <datei>` (ein `y`/`n` je Hunk **in
   Dateireihenfolge**, die eigene Aenderung zuletzt), danach **`git diff --cached --
   <datei>` lesen**: steht dort genau die eigene Aenderung, committen. Steht mehr oder
   weniger, `git restore --staged <datei>` und mit korrigierter Antwortfolge wiederholen —
   die Zahl der Hunks ist vorher nicht sicher bekannt.

   **Im Skriptbetrieb ist `git add -p` unzuverlaessig** — die Hunk-Grenzen haengen vom
   Kontext ab und die Antwortfolge setzt die Hunk-Zahl voraus. Der deterministische Weg:

   1. `git -C <repo> diff --output=<cache>\patch.patch -- <datei>` — `--output`
      schreibt die Bytes selbst; eine PowerShell-Textumleitung verstuemmelt die
      CR-Zeichen einer CRLF-Datei.
   2. Die gewuenschten Hunks herausschneiden: kleines Python-Skript, das an den
      `@@ `-Zeilen splittet, Dateikopf bis zum ersten Hunk PLUS genau den gewaehlten
      Hunk-Block behaelt und mit `b'\n'` wieder zusammensetzt. Vorher die Hunk-Koepfe
      ausgeben und die Zahl der Hunks gegen den Diff zaehlen.
   3. `git apply --cached --check <nur-eigene.patch>`, dann `git apply --cached …`,
      dann `git diff --cached --stat` gegen die eigene Zeilenzahl pruefen — erst wenn
      die stimmt, committen.
   4. **Liegen eigene und fremde Aenderung im SELBEN Hunk, kann der Schnitt sie nicht
      trennen** (z. B. die eigene Zeile und ein fremdes `auto_archive_days` drei Zeilen
      weiter). Dann nicht den ganzen Hunk nehmen, sondern die HEAD-Fassung holen, die
      eigene Aenderung DORT anwenden und das Ergebnis als Blob in den Index setzen —
      der Arbeitsbaum bleibt unberuehrt, die Fremdarbeit steht weiter als `M` daneben:

          cmd /c "git -C <repo> show HEAD:<pfad> > <cache>\head-datei"
          # Anker-Ersatz auf dieser Kopie: count == 1 asserten, Zeilenenden binaer erhalten
          $sha = (& git -C <repo> hash-object -w -- <cache>\head-datei).Trim()
          & git -C <repo> update-index --cacheinfo 100644 $sha <pfad>

      Danach `git diff --cached -- <pfad>` lesen: dort muss GENAU die eigene Zeile
      stehen. Die HEAD-Fassung ueber `cmd /c` umleiten, nicht ueber PowerShell — eine
      PowerShell-Textumleitung schreibt Zeilenenden und Kodierung um.
   Vor dem Python-Aufruf `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH`: mit dem
   verirrten `PYTHONHOME` bricht das venv-Python ab, **ohne eine Zeile auszugeben**
   — der stille Nulltreffer sieht dann wie ein Skriptfehler aus.
4. **Fremde Aenderungen bleiben als `M` im Arbeitsbaum** und werden im Commit-Text als
   NICHT enthalten benannt, nicht stillschweigend mitgenommen und nicht verworfen.
   Fremd Gestagetes nie mitcommitten.
5. **Ein Commit kann einen fremden, schon vorhandenen Commit vor sich haben.** Nach
   dem Push `git log --oneline -4` lesen und im Bericht nennen, was mitging, das nicht
   aus dieser Sitzung stammt.
6. **Vor dem Commit den ZWEIG lesen, nicht annehmen.** `git status -sb` nennt Zweig und
   Abstand zu origin; `master` ist nicht zwingend der Arbeitszweig — eine Schwester-Sitzung
   kann einen eigenen Zweig ausgecheckt haben, und dann landen ALLE Commits dort, auch die
   eigenen, waehrend `master` viele Commits zuruecksteht. Auf dem fremden Zweig committen
   ist richtig; den Zweig NICHT unter der laufenden Sitzung wegwechseln und nie
   force-pushen. Den Befund („Commit liegt auf <zweig>, master ist N dahinter") in den
   Bericht — das Zusammenfuehren entscheidet der Nutzer.

## Datei soll aus dem Verlauf verschwinden

1. **Erst den Schreiber finden, dann loeschen.** Taucht ein Nebenprodukt (Vorlage, Log,
   Cache) an wechselnden Stellen im Baum auf, sucht man die Quelle
   (`grep -rn "<dateiname>" <programmpfad>`) und gibt dem Programm ein festes
   Arbeitsverzeichnis. Nur loeschen heisst: beim naechsten Start ist es wieder da.
2. **Nachweis aus einem FREMDEN Ordner fahren:** Kopie loeschen, Programm aus einem
   anderen Arbeitsverzeichnis starten, pruefen, wo die Datei neu entsteht. Erst damit
   ist die Ursache belegt und nicht nur die Wirkung.
3. **Eine `.gitignore`-Aenderung nimmt nichts aus dem Verlauf.** Was einmal committet
   wurde, bleibt trotz neuer Sperre versioniert und in `git status` sichtbar — es braucht
   `git rm` (Datei loeschen und stagen).
4. **`git check-ignore -v <pfad>` meldet versionierte Pfade grundsaetzlich nicht.** Wer
   prueft, ob eine zurueckgenommene Freigabe greift, fragt
   `git check-ignore -v --no-index <pfad>` — sonst haelt er die fehlende Meldung fuer eine
   fehlende Regel. Gegenprobe fuer neu angelegte Dateien: Datei anlegen, pruefen, loeschen.
   **Und die Ausgabe LESEN, nicht nur ihr Vorhandensein:** `check-ignore -v` nennt das
   LETZTE passende Muster, auch wenn dieses Muster eine Freigabe ist — bei einer neu
   angelegten, korrekt freigegebenen Datei steht dort also die `!`-Negationszeile selbst
   (`.gitignore:409:!Agenten/…<datei>`), und eine nicht-leere Ausgabe heisst hier NICHT
   "ignoriert". Maßgeblich ist, ob das genannte Muster mit `!` beginnt, plus die
   Gegenprobe in `git status --porcelain` (`??` = sichtbar, also frei; keine Zeile = ignoriert).
   Eine neue Datei unter einem gesperrten Ordner braucht BEIDES: die Verzeichnis-Freigabe
   (`!…/profiles/*/`) und den Datei-Eintrag.
5. **Grundsatzregel statt Freigabe.** Dieses Repo arbeitet als Whitelist (`*` ignoriert
   alles, unten wird einzeln freigegeben). Eine Freigabe fuer ein Nebenprodukt
   (`!**/*.env.template`) nimmt nur Servermuell in den Verlauf auf — Nebenprodukte bleiben
   ignoriert, verhindert wird ihre Entstehung am Schreiber (Schritt 1).

## Fallen

- **`git diff --stat <datei>` zeigt viel mehr Zeilen als die eigene Aenderung**
  (z. B. 55 statt 6): die Datei traegt fremde, uncommittete Aenderungen. Das ist das
  Startsignal fuer den Hunk-Schnitt oben — wer hier `git add <datei>` macht, committet
  fremde Arbeit mit. Gegenprobe vor dem Commit: die Zeilenzahl in
  `git diff --cached --stat` muss zur eigenen Aenderung passen.
- **Zeilenenden.** Versionierte Textdateien in BrainFiles sind teils CRLF (`.gitignore`
  LF, `config.yaml` CRLF, viele `SKILL.md` CRLF). Nach JEDER Textaenderung
  `git diff --numstat <pfad>` lesen: eine gewollte Zeile = 1/1. Zeigt der Diff die ganze
  Datei, `git checkout HEAD -- <pfad>` und byte-genau neu patchen — nicht committen.
- **`patch` auf `Agenten/Hermes/config.yaml` ist gesperrt** („Refusing to write to Hermes
  config file"); dafuer `hermes config set`. Siehe `hermes-config-ops`.
- **Ein `.bak-JJJJMMTT` ist nicht nur Sicherung, sondern der einzige Rueckweg**, wenn ein
  Werkzeug die Datei umschreibt (z. B. `hermes config set` schneidet den Kommentar-Schluss
  ab). Byte-genau zurueckspielen: aus der Sicherung den Zieltext ersetzen, Anker auf
  `count == 1` asserten, Zeilenenden binaer erhalten.

## Verification

- `git diff --cached -- <datei>` nennt genau die eigene Aenderung.
- `git diff -- <datei>` laesst die fremden Hunks unveraendert stehen.
- `git log --oneline -1` nennt nur die eigenen Pfade, `git show --stat` passt zur Absicht,
  und der Push ist mit `git log origin/master..master` gegen den eigenen Commit gehalten.
