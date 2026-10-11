---
name: brainfiles-schreibzugriff
description: "Use when BrainFiles-Dateien geaendert/committet werden."
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [BrainFiles, Git, Konfiguration, Schutzstufe, Zeilenenden, Commit]
    related_skills: [aufgabenliste-belegen, aufgabenliste-pflegen]
---

# Bewacht in den BrainFiles-Vault schreiben

Der Vault ist geteilt (mehrere Sitzungen, Hermes und Claude), git-verfolgt und
nach Schutzstufen aufgeteilt. Ein Schreibvorgang ist erst fertig, wenn er
committet ist, nur die EIGENEN Dateien trifft und die Aenderung wirklich wirkt.

## When to Use — Wann

- eine Entscheidung soll in eine Konfig eingetragen werden (`wachen.json`,
  `prognose*.json`, `config.yaml`)
- eine Notiz, ein Skript oder eine Config unter `BrainFiles/` wird geaendert
- ein Ticket ist belegt und die Folge soll jetzt umgesetzt werden

## Ablauf

1. **Stufe bestimmen** (`MaxHirn/Wissen/Schutzregeln.md`). Stufe 0/1 -> vor der
   Aenderung `.bak-JJJJMMTT` anlegen und danach einmal ausfuehren/pruefen;
   Stufe 2 frei. Im Zweifel die hoehere Stufe annehmen. `Agenten/Hermes/` ist
   Stufe 1; Handels-Konfigs tragen ihre Stufe oft selbst als `_stufe`.
2. **Erst lesen, dann schreiben.** Die Datei vollstaendig lesen und den eigenen
   Vermerk im bestehenden Stil ergaenzen (Feld `_..._vermerk` mit Datum,
   Auftrag, alt -> neu), nicht ersetzen.
3. **Zeilenenden erhalten** — siehe Fallen, der haeufigste stille Fehler.
4. **Nur die eigenen Dateien stagen:** `git add <pfad>` je Datei. Nie
   `git add -A`/`git add .` — im Vault liegen fremde uncommittete Aenderungen.
5. **Staged-Diff pruefen, BEVOR committet wird:** `git diff --cached --stat`.
   Eine Zeile je Datei = richtig; hunderte Zeilen = Zeilenenden umgestellt oder
   Fremdes mitgestaged. Nicht committen, solange der Diff gross ist. Nach jedem
   Neu-Schreiben einer Datei **erneut `git add`**: der Index haelt sonst noch den
   alten Blob und `--stat` zeigt weiter den grossen Diff, obwohl die Datei im
   Arbeitsbaum schon sauber ist (zweimal gestaged = einmal zu wenig).
6. **Committen mit Herkunft:** `git commit --author="Hermes <hermes@local>"`.
   Eine Zeile Nachricht je Auftrag: Grund und Wirkung.
7. **Pushen** und Stand kontrollieren (`git log --oneline -2`).
8. **Board/Ticket nachtragen** — die Mess-Seite: `aufgabenliste-belegen`.

## Fallen

- **Zeilenenden-Umstellung blaeuft den Diff auf.** Das Repo setzt `* -text`
  (`.gitattributes`) und `core.autocrlf=false` — Git wandelt NICHT. Einige
  Dateien sind CRLF, andere LF. Ein Patch-/Schreibwerkzeug setzt LF und erzeugt
  aus drei geaenderten Zeilen einen Whole-File-Diff. **Der stille Fallstrick ist
  das LESEN, nicht das Schreiben:** `open(p, encoding="utf-8").read()` plus
  `splitlines(keepends=True)` normalisiert CRLF still zu LF — die Datei wird
  danach als LF zurueckgeschrieben und der Diff explodiert. Rezept (beides
  binaer): `raw = open(p, "rb").read()`; `eol = b"\r\n" if b"\r\n" in raw else b"\n"`;
  `zeilen = raw.decode("utf-8").split(eol.decode())`; Aenderung; `open(p, "wb").write(eol.join(z.encode("utf-8") for z in zeilen))`.
  Danach **nachmessen** (`raw.count(b"\n")` vs. `raw.count(b"\r\n")` — lone LF
  muss 0 sein) und Schritt 5 als Kontrolle. Ist die Datei schon zerstoert, aus
  der `.bak-JJJJMMTT` neu aufbauen (Byte-Quelle) statt weiter zu reparieren.
- **Ein Wert, den niemand liest, ist kein Fix.** Vor dem Eintragen pruefen, ob
  der Codepfad das Feld ueberhaupt zieht (mit `search_files` nach Feld UND
  Spurname). Fehlt
  die Spur in der Zuordnungstabelle des pruefenden Moduls, ist der Wert
  wirkungslos. Dann ehrlich vermerken (im `_..._vermerk` der Datei UND im
  Ticket), was noch fehlt — ein stiller No-op sieht sonst aus wie ein fertiger
  Zaun. Auch die Praemisse des Tickets pruefen: nennt es einen Codepfad oder
  Mechanismus, der existieren soll, erst lesen, ob es ihn gibt.
- **Fremde Aenderungen im Baum.** `git status` zeigt oft Dateien anderer
  Sitzungen. Liegen lassen, nicht mitstagen, nicht verwerfen (`git checkout`,
  `restore`, `stash`, `clean` loeschen fremde Arbeit). Nur die eigenen Pfade
  nennen.
- **`git index.lock` blockiert.** Laeuft ein zweiter git-Prozess, kurz warten,
  dann `rm -f .git/index.lock`. Kein Inhaltsfehler.
- **Notiz unter `Wissen/`:** ergaenzen ohne Rueckfrage; bei Widerspruch zum
  Bestehenden (Aussage umkehren, Abschnitt streichen, belegte Zahl tauschen)
  erst zurueckfragen.
- **Fertige Aenderung nicht als fertig melden, wenn ein Pfad fehlt.** Wenn der
  wirksame Zaun noch einen zweiten Schritt braucht (Registrierung, weitere
  Felder), das als eigenen offenen Auftrag ausweisen statt still umzusetzen.

## Antwortform (Hausregel)

- Was geaendert wurde (Datei, alt -> neu), was gepusht ist, was offen bleibt.
- Eine begruendete Empfehlung statt Optionsliste; genau EINE naechste Aktion.
- Widersprueche zur Ticket-Praemisse ausdruecklich benennen, nicht still
  umsetzen.
