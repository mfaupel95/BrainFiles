#!/usr/bin/env python3
"""Skill-Abgleich Vault <-> Hermes-Kopien - mit Riegel gegen stillen Datenverlust.

WARUM: Am 07.10.2026 hat ein Abgleich drei Hermes-Kopien auf den alten
Vault-Stand zurueckgesetzt und dabei die Weiterarbeit in den Kopien geloescht
(`rueckschau/sitzungen_auswerten.py` 23949 -> 8271 B: `--umwege` und die
zweite Quelle `state.db` weg; `skill/SKILL.md` verlor eine Regel). Vorher wie
nachher waren die Hashes sauber - kein Fehler, keine Meldung.

Die Ursache ist nicht Nachlaessigkeit, sondern die eingebaute Annahme, dass
jede Abweichung ein Rueckstand ist. Ein Hash sagt nur *dass* etwas abweicht,
nie *wer* weiter ist.

DIESES SKRIPT MACHT DREI DINGE, DIE DER HASH NICHT KANN:
  1. Es bestimmt die RICHTUNG je Datei (Zeilen nur in der Quelle / nur in der
     Kopie), nicht nur gleich/ungleich.
  2. Es fasst eine Kopie, die weiter ist als die Quelle, NICHT an. Sie wird
     gemeldet und der Lauf endet mit Code 1.
  3. Es sperrt Dateien, die in den letzten `--min-alter` Minuten geschrieben
     wurden - die koennen mitten in fremder Arbeit stehen.

Ueberschrieben wird nur, was nachweislich Rueckstand ist. Mit
`--zusammenfuehren` wird der Inhalt, den die Kopie voraus hat, zuerst in die
Quelle nachgezogen (Sicherung `.bak-<JJJJMMTT>`), dann kopiert - so geht
nichts verloren.

    python skill-abgleich.py                      # nur zeigen (Standard)
    python skill-abgleich.py --anwenden           # Rueckstand kopieren
    python skill-abgleich.py --anwenden --zusammenfuehren

Exit: 0 = nichts blockiert, 1 = mindestens eine Datei gesperrt (nichts oder
nur der unbedenkliche Teil geschrieben).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Hauswege - per Parameter ueberschreibbar, damit Tests auf Fixtures laufen
# koennen und nie echte Daten anfassen.
H = Path(r"C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes")
BF = Path(r"C:/Users/faupe/Documents/BrainFiles")
VAULT_STD = BF / "MaxHirn" / ".claude" / "skills"
KOPIEN_STD = H / "skills" / "claude-code-imports"
SICHER_STD = H / ".sicherung"

# Nur diese Dateiarten werden als Text verglichen und ggf. zusammengefuehrt.
TEXT_SUFFIXE = {".md", ".py", ".ps1", ".sh", ".txt", ".json", ".yaml", ".yml", ".toml"}

# Streu- und Sicherungsdateien werden nicht uebertragen: sie gehoeren der
# Quelle, sind keine Skill-Bestandteile, und im Vault liegt z. B.
# `archiv/SKILL.md.bak-20260902` aus einer alten Sicherung.
NICHT_UEBERTRAGEN = (".bak", ".bak2", ".tmp", ".orig", ".rej", ".pyc", "~")

# Urteile je Datei.
GLEICH = "gleich"
RUECKSTAND = "rueckstand"          # nur die Quelle hat Zeilen -> kopierbar
KOPIE_WEITER = "kopie_weiter"      # nur die Kopie hat Zeilen -> GESPERRT
BEIDSEITIG = "beidseitig"          # beide haben Eigenes -> Konflikt
ZU_JUNG = "zu_jung"                # frisch geschrieben -> GESPERRT
NUR_KOPIE = "nur_in_kopie"         # Skill gibt es nur in den Kopien -> fremd
BINAER_ABW = "binaer_abweichend"   # nicht als Text lesbar -> GESPERRT
FEHLT = "fehlt_in_kopie"


def uebertragbar(p: Path) -> bool:
    """Streu- und Sicherungsdateien gehoeren nicht in die Kopien."""
    n = p.name
    return not (any(m in n for m in NICHT_UEBERTRAGEN) or "__pycache__" in p.parts)


def dateien(d: Path) -> list[Path]:
    """Alle uebertragbaren Dateien eines Skill-Ordners, in stabiler Reihenfolge."""
    return sorted(x for x in d.rglob("*") if x.is_file() and uebertragbar(x))


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def zeilenenden(b: bytes) -> tuple[str, int]:
    """('crlf'|'lf', anzahl) - das haeufigere Ende gewinnt."""
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    return ("crlf", crlf) if crlf > lf else ("lf", lf)


def als_text(p: Path) -> str | None:
    """Textinhalt mit LF-Zeilenenden, oder None wenn nicht als UTF-8 lesbar."""
    try:
        b = p.read_bytes()
    except OSError:
        return None
    if b"\x00" in b[:8000]:
        return None
    try:
        t = b.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # BOM entfernen, damit der Vergleich nicht an ihm scheitert
    return t.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


def inhalt_zeilen(t: str) -> list[str]:
    return [z.strip() for z in t.splitlines() if z.strip()]


def richtung(quelle: Path, kopie: Path) -> tuple[str, int, int]:
    """Urteil fuer ein abweichendes Dateipaar -> (urteil, nur_quelle, nur_kopie)."""
    tq, tk = als_text(quelle), als_text(kopie)
    if tq is None or tk is None:
        return BINAER_ABW, 0, 0
    if tq == tk:
        return GLEICH, 0, 0
    sq, sk = set(inhalt_zeilen(tq)), set(inhalt_zeilen(tk))
    nur_q = [z for z in inhalt_zeilen(tq) if z not in sk]
    nur_k = [z for z in inhalt_zeilen(tk) if z not in sq]
    if not nur_k:
        return RUECKSTAND, len(nur_q), 0
    if not nur_q:
        return KOPIE_WEITER, 0, len(nur_k)
    return BEIDSEITIG, len(nur_q), len(nur_k)


def abschnitte(t: str) -> list[tuple[str, str]]:
    """Markdown in (Kopfzeile, Rumpf) zerlegen. Vorlauf bekommt Kopf ''."""
    zeilen = t.split("\n")
    bloecke: list[tuple[str, str]] = []
    kopf, rumpf = "", []
    for z in zeilen:
        if z.startswith("## "):
            bloecke.append((kopf, "\n".join(rumpf)))
            kopf, rumpf = z, []
        else:
            rumpf.append(z)
    bloecke.append((kopf, "\n".join(rumpf)))
    return bloecke


def vorlauf_merge(rumpf_q: str, rumpf_k: str) -> tuple[str, list[str]]:
    """Vorlauf (Frontmatter, Titel, Zeilen vor dem ersten '## ') zusammenfuehren.

    Die Kopie ist die Basis. Eine Quellzeile, die dort fehlt, wird weggelassen,
    wenn die Kopie dieselbe Zeilenart weiterentwickelt hat (gleicher Schluessel
    vor dem ':'). Sonst bleibt sie erhalten - nichts geht verloren.
    """
    zq = rumpf_q.split("\n")
    zk = rumpf_k.split("\n")
    sk = {z.strip() for z in zk if z.strip()}
    ergebnis = list(zk)
    konflikte: list[str] = []
    for z in zq:
        zs = z.strip()
        if not zs or zs in sk:
            continue
        schluessel = zs.split(":")[0].strip() if ":" in zs else ""
        weiterentwickelt = any(
            c.strip() and ":" in c and c.strip().split(":")[0].strip() == schluessel
            for c in ergebnis) if schluessel else False
        if weiterentwickelt:
            continue                      # Kopiezeile ist die neuere Fassung
        ergebnis.append(z)
        konflikte.append(f"Zeile nur in der Quelle: {zs[:70]}")
    return "\n".join(ergebnis), konflikte


def zusammenfuehren(quelle: Path, kopie: Path) -> tuple[str | None, list[str]]:
    """Inhalt der Kopie, der in der Quelle fehlt, in die Quelle einarbeiten.

    Arbeitet abschnittsweise (`## `) und entscheidet je Abschnitt:
      - nur in der Kopie  -> nachziehen
      - in beiden, Kopie-Rumpf ist ein Superset der Quellzeilen -> Kopie
        (sie ist die weiterentwickelte Fassung dieses Abschnitts)
      - in beiden, beide haben Eigenes -> Quelle bleibt, Konflikt gemeldet
    Gibt (neuer Quelltext | None, Liste der Konflikte) zurueck.
    """
    tq, tk = als_text(quelle), als_text(kopie)
    if tq is None or tk is None:
        return None, []
    if not tq.lstrip().startswith("---") and "## " not in tq:
        return None, []
    bq, bk = abschnitte(tq), abschnitte(tk)
    kq = [k for k, _ in bq]
    kopfnach = {k: r for k, r in bk}
    neu: list[tuple[str, str]] = []
    konflikte: list[str] = []
    for kopf, rumpf in bq:
        if kopf == "":
            # Vorlauf: Frontmatter/Titel - die Kopie ist die Basis.
            if "" in kopfnach and kopfnach[""] != rumpf:
                gemischt, k = vorlauf_merge(rumpf, kopfnach[""])
                neu.append((kopf, gemischt))
                konflikte.extend(k)
            else:
                neu.append((kopf, rumpf))
            continue
        if kopf not in kopfnach:
            neu.append((kopf, rumpf))
            continue
        rk = kopfnach[kopf]
        if rk == rumpf:
            neu.append((kopf, rumpf))
            continue
        sq = set(inhalt_zeilen(rumpf))
        sk = set(inhalt_zeilen(rk))
        if sq <= sk:
            neu.append((kopf, rk))          # Kopie ist hier weiter
        else:
            neu.append((kopf, rumpf))
            konflikte.append(kopf.strip() or "(Vorlauf)")
    # Abschnitte, die es nur in der Kopie gibt, an der richtigen Stelle einsetzen
    for i, (kopf, rumpf) in enumerate(bk):
        if not kopf or kopf in kq:
            continue
        ziel = len(neu)
        for kopf2, _ in bk[i + 1:]:
            if kopf2 in kq:
                ziel = next(n for n, (k, _) in enumerate(neu) if k == kopf2)
                break
        neu.insert(ziel, (kopf, rumpf))
    teile = []
    for kopf, rumpf in neu:
        if kopf:
            teile.append(kopf)
        if rumpf:
            teile.append(rumpf)
    ergebnis = "\n".join(teile)
    if tq.endswith("\n") and not ergebnis.endswith("\n"):
        ergebnis += "\n"
    return ergebnis, konflikte


def skills_unter(basis: Path) -> dict[str, Path]:
    gefunden: dict[str, Path] = {}
    if not basis.is_dir():
        return gefunden
    for s in sorted(basis.rglob("SKILL.md")):
        d = s.parent
        if any(teil in d.parts for teil in (".archive", ".sicherung", ".sicherung-junctions", ".git")):
            continue
        if d.name.startswith("."):
            continue
        gefunden[d.name] = d
    return gefunden


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vault", default=str(VAULT_STD), help="Quelle (Vault)")
    ap.add_argument("--kopien", default=str(KOPIEN_STD), help="Ziel (Hermes-Kopien)")
    ap.add_argument("--sicherung", default=str(SICHER_STD), help="Wurzel der Sicherungen")
    ap.add_argument("--min-alter", type=int, default=10,
                    help="Dateien, die juenger sind, werden nicht angefasst (Minuten)")
    ap.add_argument("--anwenden", action="store_true", help="wirklich schreiben")
    ap.add_argument("--zusammenfuehren", action="store_true",
                    help="Inhalt der Kopie zuerst in die Quelle nachziehen")
    ap.add_argument("--nur", default="", help="nur diesen Skill")
    ap.add_argument("--stichtag", default="", help="Sicherungsordner JJJJMMTT")
    a = ap.parse_args()

    vault, kopien = Path(a.vault), Path(a.kopien)
    stichtag = a.stichtag or datetime.now().strftime("%Y%m%d")
    sicher = Path(a.sicherung) / f"skills-import-{stichtag}"
    jetzt = datetime.now().timestamp()
    schwelle = a.min_alter * 60

    vs = skills_unter(vault)
    ks = skills_unter(kopien)
    if a.nur:
        vs = {k: v for k, v in vs.items() if k == a.nur}
        ks = {k: v for k, v in ks.items() if k == a.nur}
    print(f"Vault: {len(vs)} Skills   Kopien: {len(ks)} Skills   "
          f"Frischeschutz: {a.min_alter} min")

    zu_kopieren: list[tuple[str, str, Path, Path]] = []   # (skill, rel, quelle, ziel)
    gesperrt: list[tuple[str, str, str, int, int]] = []   # (skill, rel, urteil, nq, nk)
    zu_mergen: list[tuple[str, str, Path, Path]] = []
    gleich = 0

    for name, vd in sorted(vs.items()):
        kd = ks.get(name)
        if kd is None:
            for f in dateien(vd):
                zu_kopieren.append((name, str(f.relative_to(vd)).replace(os.sep, "/"), f, kd))
            print(f"  {name:<28} FEHLT in den Kopien -> wird angelegt")
            continue

        for f in dateien(vd):
            rel = str(f.relative_to(vd)).replace(os.sep, "/")
            z = kd / rel
            if not z.exists():
                zu_kopieren.append((name, rel, f, z))
                continue
            if md5(f) == md5(z):
                gleich += 1
                continue
            urteil, nq, nk = richtung(f, z)
            if urteil == GLEICH:
                gleich += 1
                continue
            # Frischeschutz: gilt fuer alles, was ueberschrieben wuerde.
            if jetzt - z.stat().st_mtime < schwelle:
                gesperrt.append((name, rel, ZU_JUNG, nq, nk))
                continue
            if urteil == RUECKSTAND:
                zu_kopieren.append((name, rel, f, z))
            elif urteil in (KOPIE_WEITER, BEIDSEITIG):
                if a.zusammenfuehren and f.suffix.lower() in TEXT_SUFFIXE:
                    zu_mergen.append((name, rel, f, z))
                else:
                    gesperrt.append((name, rel, urteil, nq, nk))
            else:
                gesperrt.append((name, rel, urteil, nq, nk))

    fremd = sorted(set(ks) - set(vs))
    print(f"\ngleich: {gleich} Dateien   zu kopieren: {len(zu_kopieren)}   "
          f"zusammenzufuehren: {len(zu_mergen)}   gesperrt: {len(gesperrt)}")
    if fremd:
        print(f"nur in den Kopien (fremd, wird nie angefasst): {len(fremd)} - "
              f"{', '.join(fremd[:6])}{' ...' if len(fremd) > 6 else ''}")

    if zu_kopieren:
        print("\n=== wird kopiert (Rueckstand) ===")
        for name, rel, f, z in zu_kopieren:
            print(f"  {name}/{rel}")

    if zu_mergen:
        print("\n=== Kopie ist weiter als die Quelle - Inhalt wird nachgezogen ===")
        for name, rel, f, z in zu_mergen:
            _, nq, nk = richtung(f, z)
            print(f"  {name}/{rel}: {nk} Zeile(n) nur in der Kopie, {nq} nur in der Quelle")

    if gesperrt:
        print("\n=== GESPERRT - wird nicht angefasst ===")
        for name, rel, urteil, nq, nk in gesperrt:
            grund = {
                ZU_JUNG: f"juenger als {a.min_alter} min (fremde Arbeit moeglich)",
                KOPIE_WEITER: f"{nk} Zeile(n) nur in der Kopie - die Kopie ist weiter",
                BEIDSEITIG: f"beide Seiten eigen: {nq} Zeile(n) nur in der Quelle, "
                            f"{nk} Zeile(n) nur in der Kopie",
                BINAER_ABW: "nicht als Text lesbar, Richtung unbekannt",
            }.get(urteil, urteil)
            print(f"  {name}/{rel}: {grund}")
        print("\nDiese Dateien zuerst von Hand ansehen. Weiterarbeit der Kopie gehoert")
        print("in die Quelle (dann --zusammenfuehren), echter Rueckstand nicht.")

    if not a.anwenden:
        print("\nTrockenlauf - nichts geschrieben. Mit --anwenden ausfuehren.")
        return 1 if gesperrt else 0

    # --- schreiben ---
    sicher.mkdir(parents=True, exist_ok=True)
    geschrieben = 0

    for name, rel, f, z in zu_mergen:
        neu, konflikte = zusammenfuehren(f, z)
        if neu is None:
            gesperrt.append((name, rel, BINAER_ABW, 0, 0))
            print(f"  uebersprungen (nicht zusammenfuehrbar): {name}/{rel}")
            continue
        ziel_sicher = sicher / name / rel
        ziel_sicher.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, ziel_sicher)
        shutil.copy2(f, str(f) + f".bak-{stichtag}")
        art, _ = zeilenenden(f.read_bytes())
        text = neu if art == "lf" else neu.replace("\n", "\r\n")
        f.write_bytes(text.encode("utf-8"))
        # Die Kopie traegt die Nacharbeit nicht mehr - auf den neuen Stand bringen,
        # damit beide Seiten denselben Text haben.
        z.write_bytes(text.encode("utf-8"))
        geschrieben += 1
        print(f"  zusammengefuehrt: {name}/{rel} (Sicherung {ziel_sicher.name}, .bak-{stichtag})")
        for k in konflikte:
            print(f"    ACHTUNG Konflikt in '{k}': beide Seiten eigen - Quellfassung behalten,")
            print(f"    Kopie trotzdem auf den neuen Stand gesetzt. Von Hand pruefen.")

    for name, rel, f, z in zu_kopieren:
        if z is None:
            ziel = Path(a.kopien) / name / rel
        else:
            ziel = z
        ziel.parent.mkdir(parents=True, exist_ok=True)
        if ziel.exists():
            ziel_sicher = sicher / name / rel
            ziel_sicher.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ziel, ziel_sicher)
        shutil.copy2(f, ziel)
        geschrieben += 1

    print(f"\ngeschrieben: {geschrieben} Datei(en)   Sicherung: {sicher}")
    if gesperrt:
        print(f"gesperrt geblieben: {len(gesperrt)} - Lauf endet mit Code 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
