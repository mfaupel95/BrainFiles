"""Schutzstufen-Pruefung fuer die Agentenseite.

Beantwortet dieselbe Frage wie Agenten/Routinen/safe-file-ops.ps1: in welche
Schutzstufe faellt ein Pfad, und was darf damit geschehen? Der Waechter dort ist
die operative Fassung auf dem Arbeitsrechner; diese Datei ist der tragbare
Zwilling fuer Sitzungen ohne PowerShell.

Quelle der Wahrheit ist Wissen/Schutzregeln.md. Bei Abweichung gilt die Notiz,
NICHT dieses Skript. Gefragt wird hier nur, geurteilt wird nicht gehandelt:
diese Datei loescht nichts, verschiebt nichts, liest keine Dateiinhalte - sie
kennt nur Pfade.

Die Regelsaetze unten muessen Stueck fuer Stueck zu denen in safe-file-ops.ps1
passen. Wer eine Stufe aendert, aendert beide und prueft sie gegeneinander.

Exitcodes (gleich wie safe-file-ops.ps1):
    0 ERLAUBT | 1 ABBRUCH | 2 SICHERUNG_PFLICHT | 3 QUARANTAENE
"""

import argparse
import os
import re
import sys

# --- Stufenregeln -----------------------------------------------------------
# Von oben nach unten geprueft, der erste Treffer gewinnt. Die Reihenfolge ist
# Teil der Regel: Stufe 0 vor den Stufe-2-Ausnahmen vor Stufe 1. Sonst zoege die
# allgemeine Regel "/agenten/routinen(/|$)" die Protokolle mit, die laut
# Schutzregeln ausdruecklich Stufe 2 sind.

# Stufe 0, Schluessel und Zertifikate. Zusaetzlich: nicht lesen, damit der
# Inhalt nie in einem Protokoll oder Transkript landet.
STUFE0_GEHEIM = [
    r'/(zugaenge)\.md$',
    r'/\.env$',
    r'/id_rsa$',
    r'\.(env|pem|pfx|p12|kdbx|key|ovpn|jks|keystore)$',
]

# Stufe 0, die Archivdaten. Die ganze Archivwurzel statt einer Aufzaehlung: das
# Archiv ist am 07.09.2026 nach O:/Archiv gezogen, und ein neuer Unterordner
# waere sonst ungeschuetzt, bis jemand die Liste nachzieht (Fund 12.09.2026 aus
# dem Tor-Test von safe-file-ops.ps1 - vorher urteilte O:/Archiv als Stufe 2).
STUFE0 = [
    r'^o:/archiv(/|$)',
    r'/maxhirn/claude/(dokumente|bilder|videos|musik|posteingang)(/|$)',
]

# Stufe 2 trotz allgemeiner Stufe-1-Regel. (/|$) statt nur /: sonst greift die
# Ausnahme nur fuer Dateien INNERHALB des Ordners, nicht fuer den Ordner selbst -
# "Agenten/Routinen/logs" urteilte dadurch als Stufe 1 (Fund 12.09.2026).
STUFE2_IMMER = [
    r'/agenten/routinen/logs(/|$)',
    r'/\.venv(/|$)',
    r'/__pycache__(/|$)',
    r'/node_modules(/|$)',
    r'/\.git(/|$)',
]

# Stufe 1, betrieblich. Ersetzbar, aber sie brechen still: der Schaden zeigt
# sich Wochen spaeter als Sicherung, die aufgehoert hat zu laufen.
STUFE1 = [
    r'/maxhirn/(agents|claude|dashboard)\.md$',
    r'/maxhirn/\.claude/skills(/|$)',
    r'/maxhirn/\.agents/skills(/|$)',
    r'/maxhirn/optional-skills(/|$)',
    r'/maxhirn/\.obsidian(/|$)',
    r'/maxhirn/archiv/archivsuche(/|$)',
    r'/maxhirn/(sichern|install)[^/]*\.ps1$',
    r'/agenten/routinen(/|$)',
    r'/agenten/mcp-server(/|$)',
    r'/agenten/handel(/|$)',
    r'/agenten/hermes(/|$)',
    r'/agenten/bus(/|$)',
    r'/agenten/\.claude(/|$)',
    r'/agenten/(sichern|mcp-sync-check)[^/]*\.(ps1|json)$',
]

ZERSTOEREND = {'loeschen', 'massenhaft_loeschen', 'ueberschreiben', 'verschieben', 'umbenennen'}

# Englische Namen weiter annehmen, damit aeltere Aufrufe nicht brechen.
ALIASE = {
    'read': 'lesen',
    'delete': 'loeschen',
    'bulk_delete': 'massenhaft_loeschen',
    'overwrite': 'ueberschreiben',
    'move': 'verschieben',
    'rename': 'umbenennen',
}


def normalisieren(pfad):
    """Pfad in die Vergleichsform bringen: absolut, Kleinbuchstaben, Schraegstriche."""
    p = os.path.abspath(os.path.expanduser(pfad))
    return p.replace('\\', '/').lower()


def _trifft(muster, pfad):
    return any(re.search(m, pfad) for m in muster)


def ist_geheim(normiert):
    return _trifft(STUFE0_GEHEIM, normiert)


def schutzstufe(pfad):
    """Liefert 0, 1 oder 2. 2 ist die Vorgabe: was keine Regel nennt, ist frei."""
    n = normalisieren(pfad)
    if ist_geheim(n):
        return 0
    if _trifft(STUFE0, n):
        return 0
    if _trifft(STUFE2_IMMER, n):
        return 2
    if _trifft(STUFE1, n):
        return 1
    return 2


def urteil(pfad, aktion):
    """Urteil zu einer geplanten Operation. Aendert nichts."""
    aktion = ALIASE.get(aktion, aktion)
    n = normalisieren(pfad)
    stufe = schutzstufe(pfad)
    geheim = ist_geheim(n)

    if stufe == 0:
        if geheim:
            return 0, 'ABBRUCH', ('Stufe 0 (Schluessel/Zertifikat): weder lesen noch schreiben noch '
                                  'loeschen. Die Datei ist die einzige Ablage.')
        if aktion in {'loeschen', 'massenhaft_loeschen', 'ueberschreiben'}:
            return 0, 'ABBRUCH', ('Stufe 0: Original ohne Zweitquelle. Kein Loeschen, kein '
                                  'Ueberschreiben - auch nicht auf Ansage.')
        if aktion in {'verschieben', 'umbenennen'}:
            return 0, 'QUARANTAENE', ('Stufe 0: nur in den _zu_loeschen-Ordner verschieben, dort '
                                      'entscheidet ein Mensch.')
        return 0, 'ERLAUBT', 'Stufe 0: Lesen ist erlaubt, Schreiben nicht.'

    if stufe == 1 and aktion in ZERSTOEREND:
        return 1, 'SICHERUNG_PFLICHT', ('Stufe 1: erst .bak-JJJJMMTT anlegen, dann aendern, dann '
                                        'einen echten Lauf zeigen.')

    return stufe, 'ERLAUBT', 'Stufe 2: reproduzierbar oder in Git - freie Hand.'


CODE = {'ERLAUBT': 0, 'ABBRUCH': 1, 'SICHERUNG_PFLICHT': 2, 'QUARANTAENE': 3}


def main():
    p = argparse.ArgumentParser(description='Schutzstufe eines Pfades bestimmen (aendert nichts).')
    p.add_argument('--path', required=True,
                   help='Zielpfad. Windows-Pfade sind auch abseits von Windows auswertbar.')
    p.add_argument('--action', required=True,
                   choices=['lesen', 'loeschen', 'massenhaft_loeschen', 'ueberschreiben',
                            'verschieben', 'umbenennen', 'read', 'delete', 'bulk_delete',
                            'overwrite', 'move', 'rename'])
    args = p.parse_args()

    stufe, entscheidung, grund = urteil(args.path, args.action)
    print('STUFE: {}'.format(stufe))
    print('ENTSCHEIDUNG: {}'.format(entscheidung))
    print('GRUND: {}'.format(grund))
    print('PFAD: {}'.format(normalisieren(args.path)))
    sys.exit(CODE[entscheidung])


if __name__ == '__main__':
    main()
