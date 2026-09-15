"""Skill-Katalog: die gelernten Skills nachschlagen, ohne sie zu laden.

WARUM ES IHN GIBT
-----------------
Die Skills eines Agenten liegen in seinem Kontext - und kosten dort bei JEDER
Anfrage Tokens. Deshalb ist die Bibliothek absichtlich klein gehalten (48 statt
127, siehe die Aussortierung vom 11.09.2026). Aus einem Telegram-Chat heraus ist
sie damit aber unsichtbar: man weiss nicht mehr, was es gibt.

Dieser Katalog schlaegt NACH, statt zu laden. Er liest die SKILL.md-Dateien von
der Platte (Frontmatter: name, description, category) und kostet den Agenten
nichts, weil er nur im Bot-Prozess laeuft.

WAS ER NICHT IST
----------------
Keine zweite Skill-Verwaltung: die Bibliothek bleibt die Wahrheit (Ordner,
`.archive`). Der Katalog zeigt nur, was da ist, und holt auf Wunsch den Text.
Der frühere `/skills`-Befehl las die A2A-Agent-Card - die zaehlt aber
WERKZEUGSAETZE auf (42 Zeilen "toolset.x", "Hermes 'x' capabilities"), nicht
die gelernten Skills. Genau daran ist "übersichtlich auf alle Skills
zugreifen" gescheitert.

DIE ZWEI GRENZEN VON TELEGRAM
-----------------------------
1. Eine Nachricht fasst 4096 Zeichen. Der volle Katalog sprengt das, also wird
   in Stuecke geteilt: `katalog_bloecke()`.
2. Ein zu langer Skill wird gekuerzt, nie abgeschnitten ohne Hinweis - sonst
   haelt man das Ende fuer die Wahrheit (`volltext()`).
"""

from __future__ import annotations

import os
import re

# Hermes liegt in Agenten/Hermes, dieser Katalog in Agenten/Bus.
HIER = os.path.dirname(os.path.abspath(__file__))
BIBLIOTHEK = os.path.normpath(os.path.join(HIER, "..", "Hermes", "skills"))

# `.archive` ist absichtlich stillgelegt (11.09.2026, 70 Skills), kaputte
# Reste wie *.rollback-broken ebenso. Beides nicht im Katalog - was nicht
# geladen wird, darf nicht wie geladen aussehen.
NICHT_ZEIGEN = (".archive", "rollback", ".curator_backups")

# Telegram: 4096 Zeichen je Nachricht, mit Reserve fuer Kopf und Fuss.
BLOECKGROESSE = 3500
TEXTGROESSE = 3200


def _frontmatter(text):
    """name/description/category aus dem YAML-Kopf - ohne yaml-Abhaengigkeit.

    Nur diese drei Felder werden gebraucht; ein vollstaendiger Parser waere
    eine Abhaengigkeit fuer drei Zeilen.
    """
    felder = {}
    if not text.startswith("---"):
        return felder
    ende = text.find("\n---", 3)
    if ende < 0:
        return felder
    for zeile in text[3:ende].splitlines():
        if ":" not in zeile or zeile.startswith((" ", "\t")):
            continue
        schluessel, _, wert = zeile.partition(":")
        schluessel = schluessel.strip().lower()
        if schluessel not in ("name", "description", "category"):
            continue
        wert = wert.strip()
        if len(wert) > 1 and wert[0] == wert[-1] and wert[0] in "\"'":
            wert = wert[1:-1]
        felder[schluessel] = wert
    return felder


def _einzeiler(text, breite=72):
    """Erste sinnvolle Beschreibungszeile, auf `breite` gekuerzt."""
    # Die Beschreibung steht im Frontmatter; faellt sie aus, nimmt der Katalog
    # die erste Ueberschrift.
    zeile = text.strip().splitlines()[0] if text.strip() else ""
    zeile = re.sub(r"\s+", " ", zeile).strip()
    if len(zeile) > breite:
        zeile = zeile[: breite - 1].rstrip() + "…"
    return zeile


def eintraege(wurzel=None):
    """Alle sichtbaren Skills: [{name, beschreibung, gruppe, pfad}].

    Sortiert nach Gruppe, dann Name. Der Dateiname entscheidet, nicht die
    Behauptung im Kopf: ein Skill ohne Frontmatter-Namen heisst wie sein Ordner.
    """
    wurzel = wurzel or BIBLIOTHEK
    treffer = []
    for pfad, ordner, dateien in os.walk(wurzel):
        if "SKILL.md" not in dateien:
            continue
        if any(t in pfad for t in NICHT_ZEIGEN):
            continue
        datei = os.path.join(pfad, "SKILL.md")
        try:
            with open(datei, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        felder = _frontmatter(text)
        relativ = os.path.relpath(pfad, wurzel)
        # Gruppe: der Ordner unterhalb der Bibliothek. "brainfiles/handel-spuren"
        # ist die Gruppe brainfiles, ein Top-Level-Skill seine eigene.
        teile = [t for t in relativ.replace("\\", "/").split("/") if t not in (".", "")]
        gruppe = felder.get("category") or (teile[0] if len(teile) > 1 else "ohne Gruppe")
        treffer.append({
            "name": felder.get("name") or (teile[-1] if teile else datei),
            "beschreibung": _einzeiler(felder.get("description", "")),
            "gruppe": gruppe,
            "pfad": datei,
        })
    treffer.sort(key=lambda e: (e["gruppe"].lower(), e["name"].lower()))
    return treffer


def katalog(suchbegriff=None, wurzel=None):
    """Der Katalog als Text, nach Gruppen. Ohne Suchbegriff alles."""
    alle = eintraege(wurzel)
    if suchbegriff:
        s = suchbegriff.strip().lower()
        alle = [e for e in alle
                if s in e["name"].lower() or s in e["beschreibung"].lower()
                or s in e["gruppe"].lower()]
    if not alle:
        return "Kein Skill passt auf %r." % suchbegriff

    zeilen = ["<b>%d Skills</b>" % len(alle)]
    if suchbegriff:
        zeilen[0] += " zu %r" % suchbegriff
    zeilen.append("")
    gruppe = None
    for e in alle:
        if e["gruppe"] != gruppe:
            gruppe = e["gruppe"]
            zeilen.append("<b>%s</b>" % gruppe)
        zeilen.append("  %s — %s" % (e["name"], e["beschreibung"]))
    zeilen.append("")
    zeilen.append("Volltext: /skill NAME")
    return "\n".join(zeilen)


def katalog_bloecke(suchbegriff=None, wurzel=None, groesse=None):
    """Wie katalog(), aber in telegram-grosse Stuecke geschnitten.

    Geschnitten wird nur zwischen Zeilen - eine Gruppe oder ein Skill wird nie
    zerrissen, sonst steht in der zweiten Nachricht eine Zeile ohne Kopf.
    """
    groesse = groesse or BLOECKGROESSE
    text = katalog(suchbegriff, wurzel)
    bloecke, aktuell, laenge = [], [], 0
    for zeile in text.splitlines():
        if laenge + len(zeile) + 1 > groesse and aktuell:
            bloecke.append("\n".join(aktuell))
            aktuell, laenge = [], 0
        aktuell.append(zeile)
        laenge += len(zeile) + 1
    if aktuell:
        bloecke.append("\n".join(aktuell))
    return bloecke


def finde(name, wurzel=None):
    """Ein Skill nach Name (auch Teiltreffer), None wenn es keinen gibt."""
    name = (name or "").strip().lower()
    if not name:
        return None
    alle = eintraege(wurzel)
    for e in alle:
        if e["name"].lower() == name:
            return e
    treffer = [e for e in alle if name in e["name"].lower()]
    return treffer[0] if len(treffer) == 1 else None


def volltext(name, wurzel=None):
    """Die SKILL.md eines Skills, auf Telegram-Groesse gekuerzt.

    Ein Kuerzen wird IMMER gesagt: sonst haelt man den Rest fuer das Ende des
    Skills und uebersieht den entscheidenden Absatz.
    """
    e = finde(name, wurzel)
    if e is None:
        return ("Kein Skill namens %r. /skills zeigt die Liste (Teiltreffer "
                "sind erlaubt, muessen aber eindeutig sein)." % name)
    try:
        with open(e["pfad"], "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as fehler:
        return "Skill %s nicht lesbar: %s" % (e["name"], fehler)

    kopf = "%s  [%s]" % (e["name"], e["gruppe"])
    if len(text) <= TEXTGROESSE:
        return kopf + "\n\n" + text
    rest = len(text) - TEXTGROESSE
    return (kopf + "\n\n" + text[:TEXTGROESSE] + "\n\n… %d Zeichen fehlen. "
            "Volltext: %s" % (rest, e["pfad"]))


def zahlen(wurzel=None):
    """Kurzbild fuer die Systempruefung: Skills je Gruppe."""
    alle = eintraege(wurzel)
    nach = {}
    for e in alle:
        nach[e["gruppe"]] = nach.get(e["gruppe"], 0) + 1
    return {"gesamt": len(alle), "gruppen": nach}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--zahlen":
        print(zahlen())
    elif len(sys.argv) > 1:
        print(katalog(" ".join(sys.argv[1:])))
    else:
        print(katalog())
