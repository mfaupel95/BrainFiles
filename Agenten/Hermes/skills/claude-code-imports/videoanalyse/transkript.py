#!/usr/bin/env python3
"""YouTube-Transkript + Metadaten holen und als Textdatei ausgeben.

Aufruf:
    python transkript.py <URL-oder-VideoID> [Zielordner]

Ergebnis: <Zielordner>/<ISO-Datum>_<Kanal>_<VideoID>_transkript.txt
Zielordner-Vorgabe: aktuelles Verzeichnis.

Der Weg ist bewusst so gebaut, wie er am 02.09.2026 als Einziger funktioniert
hat — siehe SKILL.md, Abschnitt 2 (Fallen).
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


def video_id(s: str) -> str:
    m = re.search(r"(?:v=|/shorts/|/embed/|youtu\.be/)([A-Za-z0-9_-]{11})", s)
    return m.group(1) if m else s.strip()


def hole_metadaten(vid: str) -> dict:
    meta = {"titel": "", "kanal": "", "datum": "", "laenge": "", "aufrufe": ""}
    # Titel + Kanal: oembed ist die einzige verlaessliche Quelle ohne Scraping.
    try:
        u = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
        d = json.load(urllib.request.urlopen(u, timeout=20))
        meta["titel"] = d.get("title", "")
        meta["kanal"] = d.get("author_name", "")
    except Exception as e:
        print(f"  oembed fehlgeschlagen: {e}", file=sys.stderr)
    # Datum/Laenge/Aufrufe: aus der watch-Seite. Nur Metadaten, nicht Untertitel
    # (der timedtext-Abruf von hier liefert leer, siehe SKILL.md).
    try:
        req = urllib.request.Request(
            f"https://www.youtube.com/watch?v={vid}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        for key, pat in (
            ("datum", r'"publishDate":"([^"]+)"'),
            ("laenge", r'"lengthSeconds":"(\d+)"'),
            ("aufrufe", r'"viewCount":"(\d+)"'),
        ):
            m = re.search(pat, html)
            if m:
                meta[key] = m.group(1)
    except Exception as e:
        print(f"  watch-Seite fehlgeschlagen: {e}", file=sys.stderr)
    if meta["datum"]:
        meta["datum"] = meta["datum"][:10]
    if meta["laenge"].isdigit():
        s = int(meta["laenge"])
        meta["laenge"] = f"{s // 60}:{s % 60:02d} min"
    return meta


def hole_transkript(vid: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("  youtube-transcript-api fehlt, installiere ...", file=sys.stderr)
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "youtube-transcript-api"],
            check=True,
        )
        from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()  # ab v1.x Instanz + .fetch(), nicht mehr .get_transcript()
    try:
        fetched = api.fetch(vid, languages=["de", "en"])
    except Exception:
        # Sprache unbekannt: erste verfuegbare nehmen.
        tl = api.list(vid)
        tr = next(iter(tl))
        fetched = tr.fetch()
    return " ".join(seg.text for seg in fetched).strip()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    vid = video_id(sys.argv[1])
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        print(f"Keine gueltige Video-ID erkannt: {vid!r}", file=sys.stderr)
        return 2
    ziel = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
    ziel.mkdir(parents=True, exist_ok=True)

    print(f"Video {vid}")
    meta = hole_metadaten(vid)
    text = hole_transkript(vid)
    print(f"  Transkript: {len(text)} Zeichen")

    kanal = re.sub(r"[^A-Za-z0-9]+", "-", meta["kanal"]).strip("-") or "unbekannt"
    datum = meta["datum"] or "0000-00-00"
    out = ziel / f"{datum}_{kanal}_{vid}_transkript.txt"
    kopf = (
        f"Titel:   {meta['titel']}\n"
        f"Kanal:   {meta['kanal']}\n"
        f"Datum:   {meta['datum']}\n"
        f"Laenge:  {meta['laenge']}\n"
        f"Aufrufe: {meta['aufrufe']} (Stand Abruf)\n"
        f"ID:      {vid}\n"
        f"URL:     https://www.youtube.com/watch?v={vid}\n"
        f"{'-' * 60}\n\n"
    )
    out.write_text(kopf + text + "\n", encoding="utf-8")
    print(f"  geschrieben: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
