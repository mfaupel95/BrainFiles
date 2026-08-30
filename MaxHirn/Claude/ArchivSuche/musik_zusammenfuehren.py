"""
Fuehrt eine zerstreute/zerstoerte Musikbibliothek wieder zusammen.

Das Problem, das dieses Skript loest: dieselbe Aufnahme liegt mehrfach vor -
unter verschiedenen Dateinamen, in verschiedenen Formaten (WAV/MP3/FLAC/AIFF),
in verschiedenen Qualitaeten und mit unterschiedlich vollstaendigen oder
schlicht falschen Metadaten. Ein Vergleich ueber Dateiname oder Groesse
scheitert daran zwangslaeufig.

Loesungsweg:
  1. AKUSTISCHER FINGERABDRUCK (Chromaprint/fpcalc): erkennt dieselbe Aufnahme
     unabhaengig von Dateiname, Format und Bitrate.
  2. QUALITAETSBEWERTUNG: verlustfrei schlaegt verlustbehaftet, danach
     zaehlen Bittiefe, Abtastrate, Bitrate und Kanaele.
  3. METADATEN ZUSAMMENFUEHREN: aus allen Duplikaten wird pro Feld der
     vertrauenswuerdigste Wert gewaehlt (Mehrheit, dann Vollstaendigkeit).
     Fehlende/widerspruechliche Felder koennen online ueber AcoustID +
     MusicBrainz ergaenzt werden.
  4. AUSGABE ALS AIFF: verlustfrei, mit Tags, ueberall problemlos nutzbar.
  5. Unterlegene Kopien wandern in einen Quarantaene-Ordner (nichts wird
     unwiderruflich geloescht).

Aufruf:
    python musik_zusammenfuehren.py analyse ORDNER [ORDNER2 ...]
        Nur untersuchen: findet Duplikatgruppen, zeigt Qualitaet und
        Metadaten-Konflikte. Veraendert nichts.

    python musik_zusammenfuehren.py zusammenfuehren ORDNER [...] --ziel ZIELORDNER
        Erzeugt pro Gruppe eine AIFF-Datei mit den besten Metadaten.
        --online          zusaetzlich MusicBrainz abfragen (braucht --acoustid-key)
        --quarantaene X   Ordner fuer unterlegene Kopien (Standard: <ziel>/_Duplikate)
        --dry-run         nur anzeigen, was passieren wuerde
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AUDIO_EXTS = {".mp3", ".flac", ".wav", ".aif", ".aiff", ".m4a", ".ogg", ".wma", ".opus", ".alac", ".ape"}
VERLUSTFREI = {"pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le", "pcm_s16be", "pcm_s24be",
               "flac", "alac", "wavpack", "ape", "tta"}

# Fingerabdruck nur ueber die ersten 2 Minuten - reicht zur Identifikation und
# haelt den Durchlauf bei grossen Bibliotheken schnell.
FP_LAENGE = 120


def finde_werkzeug(name):
    """Sucht ein Programm im PATH und an den bekannten winget-Installationsorten
    (nach einer winget-Installation ist der PATH in der laufenden Shell noch alt)."""
    gefunden = shutil.which(name)
    if gefunden:
        return gefunden
    muster = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Python/pythoncore-3.14-64/Scripts",
    ]
    for basis in muster:
        if not basis.exists():
            continue
        for treffer in basis.rglob(f"{name}.exe"):
            return str(treffer)
    return None


FFPROBE = finde_werkzeug("ffprobe")
FFMPEG = finde_werkzeug("ffmpeg")
FPCALC = finde_werkzeug("fpcalc")


def pruefe_werkzeuge(brauche_ffmpeg=True):
    fehlt = []
    if not FPCALC:
        fehlt.append("fpcalc (Chromaprint)  ->  winget install AcoustID.Chromaprint")
    if not FFPROBE:
        fehlt.append("ffprobe (FFmpeg)      ->  winget install Gyan.FFmpeg")
    if brauche_ffmpeg and not FFMPEG:
        fehlt.append("ffmpeg                ->  winget install Gyan.FFmpeg")
    if fehlt:
        print("Es fehlen Werkzeuge:")
        for f in fehlt:
            print("   ", f)
        return False
    return True


# ---------------------------------------------------------------- Analyse ---

def audio_info(pfad):
    """Technische Daten + vorhandene Tags einer Audiodatei."""
    try:
        r = subprocess.run(
            [FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(pfad)],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        d = json.loads(r.stdout)
    except Exception as e:
        return None

    audio = [s for s in d.get("streams", []) if s.get("codec_type") == "audio"]
    if not audio:
        return None
    s = audio[0]
    fmt = d.get("format", {})

    tags = {}
    for quelle in (fmt.get("tags", {}), s.get("tags", {})):
        for k, v in quelle.items():
            k = k.lower().strip()
            if isinstance(v, str) and v.strip():
                tags.setdefault(k, v.strip())

    bits = s.get("bits_per_raw_sample") or s.get("bits_per_sample") or 0
    return {
        "pfad": str(pfad),
        "codec": s.get("codec_name", "?"),
        "verlustfrei": s.get("codec_name") in VERLUSTFREI,
        "samplerate": int(s.get("sample_rate") or 0),
        "kanaele": int(s.get("channels") or 0),
        "bits": int(bits or 0),
        "bitrate": int(fmt.get("bit_rate") or 0),
        "dauer": float(fmt.get("duration") or 0),
        "groesse": int(fmt.get("size") or 0),
        "tags": tags,
    }


def fingerabdruck(pfad):
    """Akustischer Fingerabdruck - identifiziert dieselbe Aufnahme unabhaengig
    von Dateiname, Format und Bitrate.

    Liefert (roh, komprimiert, dauer):
      roh          Liste von 32-Bit-Zahlen, fuer den Aehnlichkeitsvergleich
      komprimiert  Base64-Form, wird fuer die AcoustID-Abfrage gebraucht
    """
    try:
        roh = subprocess.run(
            [FPCALC, "-length", str(FP_LAENGE), "-raw", "-json", str(pfad)],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        d_roh = json.loads(roh.stdout)
        komp = subprocess.run(
            [FPCALC, "-length", str(FP_LAENGE), "-json", str(pfad)],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        d_komp = json.loads(komp.stdout)
        return (d_roh.get("fingerprint") or [],
                d_komp.get("fingerprint"),
                float(d_roh.get("duration") or 0))
    except Exception:
        return [], None, 0


# Ab dieser Uebereinstimmung gelten zwei Aufnahmen als dieselbe. Identische
# Aufnahmen in unterschiedlichen Formaten liegen typisch bei 0,95+; voellig
# verschiedene Stuecke bei etwa 0,5 (Zufallsniveau).
AEHNLICHKEIT_SCHWELLE = 0.88
# Kleine Verschiebungen ausgleichen (z.B. unterschiedlich lange Stille am Anfang).
MAX_VERSATZ = 8


def fp_aehnlichkeit(a, b):
    """Anteil uebereinstimmender Bits zweier Rohfingerabdruecke, mit Ausgleich
    kleiner zeitlicher Verschiebungen. 1,0 = identisch."""
    if not a or not b:
        return 0.0
    bestes = 0.0
    for versatz in range(-MAX_VERSATZ, MAX_VERSATZ + 1):
        if versatz >= 0:
            x, y = a[versatz:], b
        else:
            x, y = a, b[-versatz:]
        n = min(len(x), len(y))
        if n < 10:  # zu wenig Ueberlappung fuer eine belastbare Aussage
            continue
        unterschiede = sum((x[i] ^ y[i]).bit_count() for i in range(n))
        bestes = max(bestes, 1.0 - unterschiede / (n * 32))
    return bestes


def qualitaets_punkte(info):
    """Hoeher = besser. Verlustfrei schlaegt alles andere, danach zaehlen
    Bittiefe, Abtastrate, Bitrate und Kanalzahl."""
    p = 0
    if info["verlustfrei"]:
        p += 1_000_000
    p += min(info["bits"], 32) * 10_000
    p += min(info["samplerate"], 192_000) // 100
    p += min(info["bitrate"], 5_000_000) // 10_000
    p += info["kanaele"] * 50
    return p


def beschreibe_qualitaet(info):
    art = "verlustfrei" if info["verlustfrei"] else "verlustbehaftet"
    teile = [info["codec"], art]
    if info["bits"]:
        teile.append(f"{info['bits']} bit")
    if info["samplerate"]:
        teile.append(f"{info['samplerate'] // 1000} kHz")
    if info["bitrate"]:
        teile.append(f"{info['bitrate'] // 1000} kbit/s")
    return ", ".join(teile)


# ------------------------------------------------------- Metadaten-Logik ---

FELDER = ["title", "artist", "album", "albumartist", "date", "track", "genre", "composer"]
ALIASE = {
    "title": ["title", "tit2", "inam"],
    "artist": ["artist", "tpe1", "iart", "author"],
    "album": ["album", "talb", "iprd"],
    "albumartist": ["albumartist", "album_artist", "tpe2"],
    "date": ["date", "year", "tyer", "tdrc", "icrd"],
    "track": ["track", "tracknumber", "trck"],
    "genre": ["genre", "tcon", "ignr"],
    "composer": ["composer", "tcom"],
}


def hole_feld(tags, feld):
    for schluessel in ALIASE.get(feld, [feld]):
        wert = tags.get(schluessel)
        if wert:
            return wert.strip()
    return None


def fuehre_metadaten_zusammen(infos):
    """Waehlt pro Feld den vertrauenswuerdigsten Wert aus allen Duplikaten:
    zuerst der haeufigste (Mehrheit deutet auf korrekt hin), bei Gleichstand
    der laengste (meist der vollstaendigere).
    Gibt (zusammengefuehrt, konflikte) zurueck."""
    zusammen, konflikte = {}, {}
    for feld in FELDER:
        werte = [w for w in (hole_feld(i["tags"], feld) for i in infos) if w]
        if not werte:
            continue
        zaehler = Counter(werte)
        haeufigkeit = zaehler.most_common()
        spitze = haeufigkeit[0][1]
        kandidaten = [w for w, n in haeufigkeit if n == spitze]
        zusammen[feld] = max(kandidaten, key=len)
        if len(set(werte)) > 1:
            konflikte[feld] = sorted(set(werte))
    return zusammen, konflikte


def musicbrainz_abfrage(fp, dauer, api_key):
    """Fragt AcoustID nach dem Fingerabdruck und liefert die offiziellen
    Metadaten aus MusicBrainz. Nur ergaenzend genutzt."""
    import urllib.parse
    import urllib.request

    daten = urllib.parse.urlencode({
        "client": api_key,
        "duration": str(int(dauer)),
        "fingerprint": fp,
        "meta": "recordings+releasegroups+compress",
    }).encode()
    try:
        with urllib.request.urlopen("https://api.acoustid.org/v2/lookup", data=daten, timeout=20) as r:
            antwort = json.loads(r.read().decode())
    except Exception as e:
        return None, f"Abfrage fehlgeschlagen ({type(e).__name__})"

    if antwort.get("status") != "ok" or not antwort.get("results"):
        return None, "kein Treffer"

    bestes = max(antwort["results"], key=lambda x: x.get("score", 0))
    aufnahmen = bestes.get("recordings") or []
    if not aufnahmen:
        return None, "kein Titel hinterlegt"

    a = aufnahmen[0]
    ergebnis = {}
    if a.get("title"):
        ergebnis["title"] = a["title"]
    if a.get("artists"):
        ergebnis["artist"] = ", ".join(x["name"] for x in a["artists"] if x.get("name"))
    gruppen = a.get("releasegroups") or []
    if gruppen:
        if gruppen[0].get("title"):
            ergebnis["album"] = gruppen[0]["title"]
    return ergebnis, f"Treffer (Sicherheit {bestes.get('score', 0):.0%})"


# ----------------------------------------------------------- Hauptablauf ---

def sammle_dateien(ordner_liste):
    dateien = []
    for o in ordner_liste:
        p = Path(o)
        if not p.exists():
            print(f"WARNUNG: {p} existiert nicht.")
            continue
        for f in p.rglob("*"):
            if f.is_file() and f.suffix.lower() in AUDIO_EXTS:
                dateien.append(f)
    return sorted(dateien)


def gruppiere(dateien, zeige_fortschritt=True):
    """Liest jede Datei ein und gruppiert Aufnahmen, die akustisch
    uebereinstimmen - unabhaengig von Dateiname, Format und Qualitaet.

    Verglichen wird ueber die Bit-Uebereinstimmung der Rohfingerabdruecke.
    Die Spieldauer dient als Vorfilter: Aufnahmen, die sich um mehr als 10
    Sekunden unterscheiden, koennen nicht dasselbe sein und werden gar nicht
    erst verglichen - das haelt den Aufwand auch bei grossen Bibliotheken klein.
    """
    gruppen = []          # Liste von {"vertreter": info, "mitglieder": [info, ...]}
    ohne_fp = []
    t0 = time.time()

    for i, f in enumerate(dateien, 1):
        if zeige_fortschritt and i % 25 == 0:
            print(f"  ... {i}/{len(dateien)} geprueft ({time.time() - t0:.0f}s)", flush=True)
        info = audio_info(f)
        if not info:
            ohne_fp.append((f, "nicht lesbar"))
            continue
        roh, komp, dauer = fingerabdruck(f)
        if not roh:
            ohne_fp.append((f, "kein Fingerabdruck"))
            continue
        info["fp_roh"] = roh
        info["fp"] = komp
        info["fp_dauer"] = dauer

        passend = None
        for g in gruppen:
            v = g["vertreter"]
            if abs(v["fp_dauer"] - dauer) > 10:
                continue
            if fp_aehnlichkeit(v["fp_roh"], roh) >= AEHNLICHKEIT_SCHWELLE:
                passend = g
                break
        if passend:
            passend["mitglieder"].append(info)
        else:
            gruppen.append({"vertreter": info, "mitglieder": [info]})

    return [g["mitglieder"] for g in gruppen], ohne_fp


def cmd_analyse(args):
    if not pruefe_werkzeuge(brauche_ffmpeg=False):
        return 1
    dateien = sammle_dateien(args.ordner)
    print(f"{len(dateien)} Audiodateien gefunden. Erstelle Fingerabdruecke ...\n")
    gruppen, ohne_fp = gruppiere(dateien)

    mehrfach = [v for v in gruppen if len(v) > 1]
    einzeln = len(gruppen) - len(mehrfach)

    print(f"\nEindeutige Aufnahmen : {len(gruppen)}")
    print(f"  davon nur einmal   : {einzeln}")
    print(f"  davon mehrfach     : {len(mehrfach)}")
    print(f"Nicht lesbar         : {len(ohne_fp)}")

    if mehrfach:
        gespart = sum(sum(i["groesse"] for i in sorted(v, key=qualitaets_punkte, reverse=True)[1:])
                      for v in mehrfach)
        print(f"\nDurch Entdoppeln freiwerdend: {gespart / 1024 / 1024 / 1024:.2f} GB\n")
        print("Duplikatgruppen (die erste Zeile ist jeweils die beste Fassung):")
        for v in mehrfach[:args.limit]:
            v = sorted(v, key=qualitaets_punkte, reverse=True)
            zusammen, konflikte = fuehre_metadaten_zusammen(v)
            titel = zusammen.get("title") or Path(v[0]["pfad"]).stem
            kuenstler = zusammen.get("artist", "?")
            print(f"\n  ** {kuenstler} - {titel}")
            for j, i in enumerate(v):
                markierung = "BESTE " if j == 0 else "      "
                print(f"    {markierung}{beschreibe_qualitaet(i):<52} {Path(i['pfad']).name}")
            if konflikte:
                for feld, werte in konflikte.items():
                    print(f"      Konflikt {feld}: {' | '.join(werte)}")
        if len(mehrfach) > args.limit:
            print(f"\n  ... und {len(mehrfach) - args.limit} weitere Gruppen "
                  f"(mit --limit mehr anzeigen)")

    if ohne_fp:
        print(f"\nNicht verarbeitbar ({len(ohne_fp)}):")
        for f, grund in ohne_fp[:15]:
            print(f"  {f.name}  [{grund}]")
    return 0


def sichere_dateiname(text):
    for zeichen in '<>:"/\\|?*':
        text = text.replace(zeichen, "_")
    return text.strip().rstrip(".")[:150] or "Unbenannt"


def cmd_zusammenfuehren(args):
    if not pruefe_werkzeuge(brauche_ffmpeg=True):
        return 1

    ziel = Path(args.ziel)
    quarantaene = Path(args.quarantaene) if args.quarantaene else ziel / "_Duplikate"

    dateien = sammle_dateien(args.ordner)
    print(f"{len(dateien)} Audiodateien gefunden. Erstelle Fingerabdruecke ...\n")
    gruppen, ohne_fp = gruppiere(dateien)
    print(f"\n{len(gruppen)} eindeutige Aufnahmen.\n")

    erzeugt, verschoben, fehler, online_treffer = 0, 0, 0, 0

    for nr, v in enumerate(gruppen, 1):
        v = sorted(v, key=qualitaets_punkte, reverse=True)
        beste = v[0]
        zusammen, konflikte = fuehre_metadaten_zusammen(v)

        # Online nur ergaenzend: wenn Pflichtfelder fehlen oder sich widersprechen.
        if args.online and args.acoustid_key:
            luecke = not zusammen.get("title") or not zusammen.get("artist")
            if luecke or konflikte:
                mb, hinweis = musicbrainz_abfrage(beste["fp"], beste["fp_dauer"], args.acoustid_key)
                if mb:
                    online_treffer += 1
                    for feld, wert in mb.items():
                        # Online gewinnt nur bei Luecke oder Widerspruch,
                        # nicht gegen einen einhelligen lokalen Wert.
                        if not zusammen.get(feld) or feld in konflikte:
                            zusammen[feld] = wert
                time.sleep(0.34)  # AcoustID erlaubt 3 Anfragen pro Sekunde

        kuenstler = zusammen.get("artist", "Unbekannt")
        titel = zusammen.get("title") or Path(beste["pfad"]).stem
        zielname = sichere_dateiname(f"{kuenstler} - {titel}") + ".aiff"
        zieldatei = ziel / zielname

        if args.dry_run:
            print(f"[{nr}] WUERDE erzeugen: {zielname}")
            print(f"      aus: {Path(beste['pfad']).name}  ({beschreibe_qualitaet(beste)})")
            if len(v) > 1:
                print(f"      {len(v) - 1} Duplikat(e) in Quarantaene")
            continue

        ziel.mkdir(parents=True, exist_ok=True)
        zaehler = 2
        while zieldatei.exists():
            zieldatei = ziel / (sichere_dateiname(f"{kuenstler} - {titel}") + f" ({zaehler}).aiff")
            zaehler += 1

        # In AIFF wandeln, Tags direkt mitschreiben.
        # "-write_id3v2 1" ist zwingend: ohne das schreibt der AIFF-Muxer nur
        # den Titel, aber weder Interpret noch Album, Jahr, Genre oder Track.
        befehl = [FFMPEG, "-v", "error", "-y", "-i", beste["pfad"],
                  "-map_metadata", "-1", "-write_id3v2", "1"]
        for feld, wert in zusammen.items():
            befehl += ["-metadata", f"{feld}={wert}"]
        befehl += ["-c:a", "pcm_s16be" if beste["bits"] <= 16 else "pcm_s24be", str(zieldatei)]

        r = subprocess.run(befehl, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0 or not zieldatei.exists():
            print(f"[{nr}] FEHLER bei {Path(beste['pfad']).name}: {r.stderr.strip()[:120]}")
            fehler += 1
            continue
        erzeugt += 1

        # Alle Originale der Gruppe in Quarantaene - auch die beste, da die
        # AIFF-Fassung sie ersetzt. Nichts wird geloescht.
        for i in v:
            quelle = Path(i["pfad"])
            if not quelle.exists():
                continue
            zielq = quarantaene / quelle.name
            zielq.parent.mkdir(parents=True, exist_ok=True)
            z = 2
            while zielq.exists():
                zielq = quarantaene / f"{quelle.stem} ({z}){quelle.suffix}"
                z += 1
            try:
                shutil.move(str(quelle), str(zielq))
                verschoben += 1
            except OSError:
                pass

        if nr % 25 == 0:
            print(f"  ... {nr}/{len(gruppen)} Aufnahmen verarbeitet", flush=True)

    print()
    if args.dry_run:
        print(f"Testlauf beendet - {len(gruppen)} AIFF-Dateien wuerden entstehen. Nichts veraendert.")
    else:
        print(f"AIFF erzeugt        : {erzeugt}")
        print(f"In Quarantaene      : {verschoben}  ({quarantaene})")
        print(f"Fehler              : {fehler}")
        if args.online:
            print(f"Online ergaenzt     : {online_treffer}")
        print(f"\nZielordner: {ziel}")
        print("Die Originale liegen in der Quarantaene - erst nach eigener Pruefung loeschen.")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="befehl", required=True)

    a = sub.add_parser("analyse", help="Duplikate finden, nichts veraendern")
    a.add_argument("ordner", nargs="+")
    a.add_argument("--limit", type=int, default=20, help="wie viele Gruppen anzeigen")
    a.set_defaults(func=cmd_analyse)

    z = sub.add_parser("zusammenfuehren", help="beste Fassung als AIFF erzeugen")
    z.add_argument("ordner", nargs="+")
    z.add_argument("--ziel", required=True)
    z.add_argument("--quarantaene", default=None)
    z.add_argument("--online", action="store_true", help="MusicBrainz ergaenzend abfragen")
    z.add_argument("--acoustid-key", default=os.environ.get("ACOUSTID_KEY"),
                   help="AcoustID-Schluessel (oder Umgebungsvariable ACOUSTID_KEY)")
    z.add_argument("--dry-run", action="store_true")
    z.set_defaults(func=cmd_zusammenfuehren)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
