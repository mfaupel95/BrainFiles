---
name: rust-cargo-betrieb
description: "Rust/cargo bauen, linten, Toolchain reparieren."
version: 0.1.0
author: Hermes
platforms: [windows]
category: brainfiles
metadata:
  hermes:
    tags: [Rust, Cargo, Clippy, Windows, Build]
---

# Rust/cargo auf diesem Host

Gilt fuer die Rust-Projekte im Haus: `Werkstatt/omnitrade` (Rust-Workspace),
`Werkstatt/omnitrade-pr` (Arbeitsklon derselben Repo), `Agenten/Handel/nautilus-rust`,
`Werkstatt/kraken-cli` (selbst gebaut). Bash/MSYS ist die Shell, cargo ist ein
natives Windows-Programm — Argumente brauchen `C:/...`-Pfade, nie `/c/...`
(gilt fuer alle nativen Programme); `cd` als Bash-Builtin ist davon ausgenommen.

## Wann

- `cargo: command not found`, `rustup` meldet „could not choose a version of cargo to run“
- ein Rust-Workspace soll gebaut, getestet oder gelintet werden
- eine neue CLI-Option soll durch alle Crates (clap, Live-Args, Config, Test-Harness)
- `cargo build --release` endet mit `Zugriff verweigert (os error 5)`

## 1. Toolchain reparieren (wenn cargo/rustc fehlen)

**Der von `sh.rustup.rs` angebotene Installer laeuft unter MSYS unzuverlaessig** — er
schreibt nach einem `/tmp`-Pfad, den das native curl nicht findet bzw. nicht
beschreiben kann (zwei Formen: „No such file or directory“ fuer das Skript, dann
`curl: (23) client returned ERROR on write`). Nicht mehrfach wiederholen.

Der belegte Weg ist der native Installer:

```bash
cd "$TMPDIR" && curl -sSL -o rustup-init.exe \
  https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe \
  && ls -la rustup-init.exe && ./rustup-init.exe -y --default-toolchain stable --profile minimal
```

Danach **nicht** auf `cargo` aus dem PATH verlassen, sondern das Binary direkt rufen:
`/c/Users/faupe/.cargo/bin/cargo --version`. Je nach Vorgeschichte liegt die Toolchain
auch unter `C:\Users\faupe\.config\cargo\bin` (dort gehoeren `CARGO_HOME`/`RUSTUP_HOME`
hin) — den Fundort mit `ls /c/Users/faupe/.cargo/bin/cargo.exe` bzw.
`.config/cargo/bin` feststellen, nicht raten.

**`--profile minimal` enthaelt weder clippy noch rustfmt.** Vor dem ersten
Lint-Lauf einmalig:

```bash
/c/Users/faupe/.cargo/bin/rustup component add clippy
```

Ohne diesen Schritt bricht `cargo clippy` mit „run `rustup component add clippy`“
ab — und wer die Zeile nur als Hinweis liest, haelt den Lint faelschlich fuer gruen.

## 2. Die Reihenfolge, die zaehlt

```bash
cd C:/Users/faupe/Documents/BrainFiles/Werkstatt/omnitrade-pr \
 && /c/Users/faupe/.cargo/bin/cargo test --workspace 2>&1 | grep -E "test result:|FAILED" \
 && /c/Users/faupe/.cargo/bin/rustup component list --installed >/dev/null \
 && /c/Users/faupe/.cargo/bin/cargo clippy --workspace --all-targets -- -D warnings 2>&1 | tail -3 \
 && /c/Users/faupe/.cargo/bin/cargo build --release -p omnitrade-cli 2>&1 | tail -2
```

- **Testzahl aus den `test result:`-Zeilen summieren**, nicht aus dem letzten Binary:
  `awk -F'[ ;]+' '{p+=$4; f+=$6}'` summiert Testfaelle ueber alle Binaries; „95
  passed“ ist ein Binary, nicht der Workspace.
- **Eine LEERE Summe („TESTS:  passed,  failed“) ist kein Null-Ergebnis, sondern ein
  Compile-Fehler**: dann hat KEIN Test-Binary eine `test result:`-Zeile gedruckt.
  Nicht weiterdeuten und nicht „0 Tests“ berichten, sondern die Fehler holen:
  `cargo test -p <crate> --no-run 2>&1 | grep -B3 -A8 "^error"`. Kommen dort keine
  Fehler, war der Lauf gegen ein veraltetes Artefakt geraten — denselben Befehl
  einmal ohne Pipe wiederholen, bevor du den Code verdaechtigst.
- **Der Exitcode einer grep-Pipeline ist der von `grep`/`tail`, nicht von cargo.**
  Scheitert der Build, zeigt die Pipeline trotzdem `exit 0`. Entweder ohne Pipe
  fahren (die Ausgabe wird ohnehin gekuerzt gespeichert) oder `PIPESTATUS[0]` lesen;
  sonst wird ein roter Build als gruen gemeldet.
- Ein voller `cargo test --workspace` laeuft **laenger als 600 s** (Vorderrunden-Grenze
  des `terminal`-Werkzeugs) — als Hintergrundprozess mit `notify_on_complete` starten
  und auf das Ergebnis warten, nicht in der Vorderrunde.

## 3. Neue CLI-Option: alle Fundstellen, sonst mehrfach Compile-Fehler

Ein neues Feld in einem clap-Enum trifft **jede** Stelle, die die Struktur baut oder
zerlegt. Reihenfolge (belegt an `--allow-shorts`):

1. `omnitrade-cli/src/args.rs` — Flag am Enum-Varianten-Feld (`#[arg(long)]`)
2. `omnitrade-cli/src/main.rs` — das **Destrukturierungs-Pattern** `Commands::Live { … }`
3. `omnitrade-cli/src/commands/live.rs` — `LiveArgs`-Struct **und** seine Dekonstruktion
4. das Config-Struct im Loop-Modul (`live_loop.rs`: `LiveConfig`) + dessen Weitergabe
5. `live_loop/test_support.rs` — der Test-Harness (`Harness`-Feld + Builder)
6. **Test-Helfer, die die Struktur literal bauen** (`LiveArgs { … }` in `live.rs`,
   zwei Stellen: `run()` und `mainnet()`) — die melden `E0063 missing field`

**Muster in Tests: `..` statt Feld binden.** Ein Destrukturierungs-Pattern in einem
Test, das das neue Feld mitbindet und nicht benutzt, erzeugt `unused variable` — und
mit `clippy -D warnings` ist das ein Fehler. `Commands::Live { script, symbol, .. }`
ist die kurze, warnungsfreie Form.

## 4. Clippy-Fallen, die man in Tests trifft

- **`MutexGuard` ueber ein `await` halten** ist bei `clippy -D warnings` ein Fehler
  (`this MutexGuard is held across an await point`). Zwei Locks in einem `#[tokio::test]`
  („erst pruefen, dann den zweiten Lauf awaiten“) halten den Guard bis zum Blockende.
  Fix: den Guard in einen eigenen `{ … }`-Block scope, dann faellt er vor dem `await`.
- `&&str` vs `&str` in Closures: `|s: &&str|` an einer `&str`-Quelle bricht; `|s: &str|` nehmen.

## 5. `Zugriff verweigert (os error 5)` beim Release-Build

Ein **laufender Prozess haelt die `.exe`** — Windows erlaubt kein Ueberschreiben. Der
Fehler kommt als letzte Zeile „Caused by: Zugriff verweigert (os error 5)“ und die
Ursache steht nicht im Text. Vor jedem Release-Build pruefen, wer laeuft:

```bash
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='omnitrade-cli.exe'\" | Group-Object ExecutablePath | Select-Object Count,Name"
```

**Nach `ExecutablePath` gruppieren, nicht nach Name**: im Haus laufen zwoelf Laeufe aus
`Werkstatt/omnitrade/target-live/release/`, die den Build in
`Werkstatt/omnitrade-pr/target/release/` **nicht** sperren — nur der aus dem
Arbeitsklon tut es. Den sperrenden Prozess zuerst beenden (nach Freigabe durch Max:
`taskkill /F /PID <pid>`, einfacher Slash) und danach mit `Get-CimInstance` nachzaehlen.

**Vor dem Beenden die KOMMANDOZEILE lesen, nicht nur den Pfad.** Denselben Loophaken
kann eine PARALLELE Sitzung gestartet haben — mit anderen Parametern (Menge, Deckel,
`--allow-shorts`). Wer nur „mein Binary“ sieht, beendet fremdes Geld:

```bash
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='omnitrade-cli.exe'\" | Where-Object { \$_.ExecutablePath -like '*omnitrade-pr*' } | Select-Object ProcessId,CreationDate,CommandLine | Format-List"
```

Bei einem Lauf auf ECHTEM Geld zuerst den **Flachstand belegen** (`net_quantity == 0`
im Statusfile, sonst abbrechen) — eine offene Position ohne ihren Prozess ist ein
Notfall, kein Build. Nach dem Neustart `--quantity`, Deckel und Flags in der laufenden
Kommandozeile gegenpruefen: das Statusfile nennt sie NICHT, und die Startskript-Sperre
(`Laeuft schon`, Exit 2) haelt nur den zweiten Start ab, nicht den falschen Parameter.

## 6. Ein Test-Fehlschlag gegen den lesbaren Code

Schlaegt ein Test fehl, obwohl der Quelltext auf der Platte die geprueften Regeln
eindeutig enthaelt, ist die erste Vermutung **kein** Logikfehler, sondern ein
**veraltetes Test-Binary** (der Lauf startete vor dem Fix, oder ein frueherer
Compile-Fehler liess das alte Binary stehen). Vorgehen: **den einzelnen Test neu
fahren** (`cargo test -p <crate> <testname> -- --nocapture`) und erst bei
wiederholtem Fehlschlag den Code verdaechtigen. Belegt: eine Long-only-Sperre
„feuerte nicht“, obwohl der Code Zeile fuer Zeile korrekt war — nach dem Neubau war
derselbe Test gruen und die Debug-Ausgabe leer.

Fuer die Diagnose kurzzeitig `eprintln!("DEBUG …")` in den Test setzen und mit
`--nocapture` laufen; die Zeile danach wieder entfernen.

## Verification

Ein Rust-Beitrag ist fertig, wenn **drei** Laeufe im selben Stand gruen sind:
`cargo test --workspace` (Summe aller `test result:`-Zeilen, 0 failed),
`cargo clippy --workspace --all-targets -- -D warnings` (letzte Zeile „Finished“),
`cargo build --release -p <bin>` (letzte Zeile „Finished“). Erst dann committen.
Die Testzahl in den Bericht schreiben (Summe, nicht ein Binary).
