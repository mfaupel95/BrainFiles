#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Die EINE Kopfregel, mit der das Haus TASKS.md-Eintraege liest.

Gemessen am 04.10.2026 an `MaxHirn/Archiv/TASKS.md` (192 Eintraege im
Abschnitt `## Offen`):

    146 x  '- [ ] **T-NNN - Titel**'   Gevrierstrich
     46 x  '- [ ] **T-NNN - Titel**'   ASCII-Bindestrich (fremde Hand)
     10 x  ... Titel ohne schliessendes '**'   (darunter T-064, Gevrierstrich)

Die alte enge Form ('Gevrierstrich UND schliessendes **') las nur 146 davon
und uebersah 47 offene Punkte. Weil BAUER und PRUEFER dieselbe Enge teilten,
meldete der Pruefer den unvollstaendigen Plan GRUEN: er pruefte die Luecke
nicht, er uebernahm sie. Deshalb steht die Regel hier an EINER Stelle und
wird importiert - und `verdaechtige()` benennt jede Zeile, die wie ein
Eintrag AUSSIEHT, aber nicht gelesen wurde. Eine nicht gelesene Zeile darf
nie stillschweigend wegfallen; sie ist ein Befund, kein Detail.

Regel des Hauses: **ein Trennzeichen-Satz statt einer Trennzeichen-Liste.**
Drei Alternativen als drei Muster waeren drei Fehlerklassen, und ein Leser,
der nur eine kennt, verliert die anderen beiden lautlos. Der Trenner ist
darum ein Zeichenmenge-Quantor, und die Restbreite ist danach nur noch der
Titel.
"""
import re

# Trenner zwischen T-Nummer und Titel: Gevrierstrich, Halbgeviertstrich,
# Bindestrich. Als Zeichenmenge, nicht als Liste von Alternativen.
TRENNER = u'—–-'

# Kopfdreieck: Statuszeichen, T-ID mit Nummer, Trenner, Rest.
# Der Titel darf ohne schliessendes '**' umbrechen - das Haus schreibt es so.
KOPF = re.compile(r'^-\s*\[(.)\]\s+\*\*(T-(\d+))\s+[' + TRENNER + r']\s*(.*)$')

# Zeile, die WIE ein Eintrag aussIEHT. Trifft sie zu, aber KOPF nicht, ist
# das ein Befund: eine Kopfform, die kein Muster kennt.
VERDAECHTIG = re.compile(r'^-\s*\[.\]\s+\*\*T-\d{3,}')

# Ein erledigt-Vermerk am Zeilenende verschmilzt sonst mit dem Titel.
ERLEDIGT_VERMERK = re.compile(r'\s*[-–—]\s*erledigt\b.*$', re.I)


def titel_aus(rest):
    """Rest nach dem Trennzeichen -> Titel.

    Schneidet ein fuehrendes und ein schliessendes Sternchenpaar ab und
    laesst einen erledigt-Vermerk am Zeilenende weg, damit 'Titel' und
    'erledigt am' nicht zu einem verschmelzen. Ein Titel, der ohne `**`
    umbricht, bleibt vollstaendig stehen - er wird NICHT geraten und NICHT
    mit einem Rest aufgefuellt.
    """
    t = rest.strip().lstrip('*').strip()
    if t.endswith('**'):
        return t[:-2].strip()
    return ERLEDIGT_VERMERK.sub('', t).strip()


def abschnitte(zeilen):
    """(index_offen, index_erledigt) - Erledigt fehlt -> Dateiende."""
    a = next(i for i, z in enumerate(zeilen) if z.strip() == '## Offen')
    b = next((i for i, z in enumerate(zeilen) if z.strip() == '## Erledigt'),
             len(zeilen))
    return a, b


def eintraege(zeilen):
    """(bloecke, ungelesen) fuer den Abschnitt '## Offen'.

    Ein Block traegt zeile (1-basiert), status, id, nummer, titel und den
    vollen Textzeilen-Bereich. 'ungelesen' nennt jede Zeile, die wie ein
    Eintrag aussieht, aber von keinem Muster erfasst wurde: [(zeile, text)].
    Beide Listen sind disjunkt, und ihre Längen addieren sich zur Zahl der
    Statuszeichen-Zeilen - das ist die Zusicherung, gegen die der Test
    gebaut ist.
    """
    a, b = abschnitte(zeilen)
    treffer = [(a + k,) + KOPF.match(z).groups()
               for k, z in enumerate(zeilen[a:b]) if KOPF.match(z)]
    ungelesen = [(i + 1, z.strip()) for i, z in enumerate(zeilen[a:b], start=a)
                 if VERDAECHTIG.match(z) and not KOPF.match(z)]
    bloecke = []
    for k, (i, status, tid, nummer, rest) in enumerate(treffer):
        ende = treffer[k + 1][0] if k + 1 < len(treffer) else b
        bloecke.append({'zeile': i + 1, 'status': status.strip(),
                        'id': tid.strip(), 'nummer': nummer.strip(),
                        'titel': titel_aus(rest), 'text': zeilen[i:ende]})
    return bloecke, ungelesen


def datei_lesen(pfad):
    """(bloecke, ungelesen, zeilenenden, zeile_offen, zeile_erledigt)."""
    with open(pfad, 'rb') as fh:
        raw = fh.read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    zeilen = raw.decode('utf-8').replace('\r\n', '\n').split('\n')
    bloecke, ungelesen = eintraege(zeilen)
    a, b = abschnitte(zeilen)
    return bloecke, ungelesen, nl, a + 1, b + 1