#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Normalisiert den Routing-Plan in eine ausfuehrbare Worklist.

Aufruf:
  python routing_worklist_bauen.py <tasks.md> <worklist.json> [--markdown <worklist.md>]

Was der Plan traegt und was die Worklist daraus macht:
  Plan          -> Arbeitseinheit mit Ausfuehrungsreihenfolge
  TASKS.md      -> Quelle der Wahrheit fuer Abnahmekriterium und Titel

Der Plan verliert Eintraege (gemessen: 47 offene Punkte, darunter T-064,
stehen nicht in ihm). Deshalb liest dieses Werkzeug die Felder aus TASKS.md
und uebernimmt aus dem Plan NUR das, was der Plan wirklich weiss: die
Welle (Reihenfolge) und die Profilwahl. Beides wird mit dem Plan-Pruefer
und einem Gegenbeweis geprueft, damit kein Gruen so gelesen wird, als
trage der Plan alles.

Leerfall: TASKS.md ohne offene Punkte -> leere Worklist, Exit 0,
Meldung 'no open items - nothing to execute'. Die Folgekarten noepen dann.
"""
import os
import re
import sys
import json
import argparse
from collections import Counter, defaultdict, OrderedDict

# --- Eingabe -----------------------------------------------------------------

# Drei Kopfformen kommen im Haus-Backlog vor. Wer nur die Hausform
# (Geviertstrich) kennt, verliert offene Punkte - gemessen: 46 von 170.
#   - [ ] **T-346 — Titel**     (Hausform)
#   - [ ] **T-115 - Titel**     (ASCII-Bindestrich, fremde Hand)
#   - [ ]   **T-335 - Titel**   (fuehrende Leerzeichen)
# Der Trennzeichen-Satz deckt zusaetzlich den Gedankenstrich U+2013 und den
# ASCII-Bindestrich in EINEM Muster - zwei Muster wuerden zwei Fehlerklassen
# bedeuten, die ein Hausform-Leser nur zur Haelfte trifft.
KOPF = re.compile(r'^-\s*\[(.)\]\s+\*\*(T-(\d+))\s+[\u2014\u2013-]\s*(.+?)\*\*(.*)$')

# Untermittelte Kopfzeile: '**T-064 - Titel' OHne schliessende '**'. T-064 in
# TASKS.md (Stand 04.10.2026) traegt genau diesen Fehler und faellt dadurch aus
# JEDEM Muster mit '\*\*$'. Ein stiller Verlust waere eine Behauptung, die
# die Datei nicht traegt - deshalb wird der Fall gelesen UND gemeldet.
KOPF_UNTERMITT = re.compile(r'^-\s*\[(.)\]\s+\*\*(T-(\d+))\s+[\u2014\u2013-]\s*(.+?)\s*$')

# Hausfelder eines Eintrags. Ein Feld laeuft bis zur naechsten Zeile mit
# einem neuen Feldnamen - ohne das endet 'Naechster Schritt' mitten im Satz.
FELD = re.compile(r'^\s{2,}([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß /().\-]{1,45}?):\s*(.*)$')
ALLE_IDS = re.compile(r'\bT-(\d{3,})\b')

SCHRITT_FELDER = ('Naechster Schritt', 'Nächster Schritt', 'Naechster Schritt ')


def lies_bytes(pfad):
    """Liest eine Datei als Bytes - mit geschlossenem Handle.

    Hausregel: die Zeilenenden werden aus dem ROHEN Inhalt abgeleitet, nicht
    ueber eine Text-Decode, die CRLF still nach LF umschreibt.
    """
    with open(pfad, 'rb') as fh:
        return fh.read()


def lies_text(pfad):
    """Liest eine (Markdown-)Datei als UTF-8-Text mit Zeilenliste."""
    roh = lies_bytes(pfad)
    return roh.decode('utf-8', 'replace').replace('\r\n', '\n').split('\n')


def bloecke_lesen(pfad):
    """Liest TASKS.md und liefert jeden Block des Abschnitts 'Offen'.

    Rueckgabe: (bloecke, zeilenende, zeile_offen_ab, zeile_erledigt_ab,
    untermittelt) - die letzte Liste nennt die Kopfzeilen OHNE schliessende
    '**'. Sie werden mitgelesen (ein offener Punkt darf nicht still
    verschwinden), aber gemeldet: die Datei ist die zu reparieren.
    """
    raw = lies_bytes(pfad)
    nl = '\r\n' if b'\r\n' in raw else '\n'
    zeilen = raw.decode('utf-8').replace('\r\n', '\n').split('\n')
    try:
        offen = next(i for i, z in enumerate(zeilen) if z.strip() == '## Offen')
        erledigt = next(i for i, z in enumerate(zeilen) if z.strip() == '## Erledigt')
    except StopIteration:
        raise SystemExit('TASKS.md ohne die Abschnitte "## Offen" und "## Erledigt": '
                         '%s' % pfad)
    idx, untermittelt = [], []
    for i in range(offen, erledigt):
        m = KOPF.match(zeilen[i])
        if m:
            idx.append((i, m.group(1).strip(), m.group(2).strip(),
                        m.group(3).strip(), m.group(4).strip(), False))
            continue
        mu = KOPF_UNTERMITT.match(zeilen[i])
        if mu:
            # Untermittelt, aber eindeutig ein Eintrag: ID + Trennzeichen
            # stehen, nur das schliessende '**' fehlt. Die Fortsetzung des
            # Titels (Folgezeilen) gehoert zum Block, nicht zum Titel.
            idx.append((i, mu.group(1).strip(), mu.group(2).strip(),
                        mu.group(3).strip(), mu.group(4).strip(), True))
            untermittelt.append((i + 1, mu.group(2).strip()))
    out = []
    for k, (i, status, tid, nummer, titel, unterm) in enumerate(idx):
        end = idx[k + 1][0] if k + 1 < len(idx) else erledigt
        out.append({'zeile': i + 1, 'status': status, 'id': tid,
                    'nummer': nummer, 'titel': titel,
                    'untermittelt': unterm, 'text': zeilen[i:end]})
    return out, nl, offen + 1, erledigt + 1, untermittelt


def felder(text):
    """Holt die Hausfelder eines Eintrags (siehe routing_plan_bauen.felder)."""
    aus = defaultdict(list)
    aktiv = None
    for zeile in text[1:]:
        m = FELD.match(zeile)
        if m:
            schluessel = m.group(1).strip()
            kurz = re.split(r'\s*[·(]', schluessel)[0].strip()
            aktiv = kurz if kurz in ('Kontext', 'Naechster Schritt',
                                     'Nächster Schritt', 'Angelegt',
                                     'Zuletzt', 'Betrifft', 'Wartet auf') else None
            if aktiv:
                aus[aktiv].append(m.group(2).strip())
            continue
        if aktiv and zeile.strip():
            aus[aktiv].append(zeile.strip())
    return aus


def status_text(zeichen):
    """Ein Leerzeichen im Codeblock ist im Markdown unsichtbar - ausschreiben."""
    return {' ': 'offen', '?': 'wartet auf Max', '!': 'blockiert',
            '~': 'in Arbeit', 'x': 'erledigt'}.get(zeichen.strip(),
                                                    zeichen.strip() or 'offen')


def kuerzen(text, grenze=360):
    """An einer Satzgrenze schneiden, nie mitten im Satz."""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= grenze:
        return text
    fenster = text[:grenze]
    for trenner in ('. ', '! ', '? ', '; ', ', '):
        pos = fenster.rfind(trenner)
        if pos > grenze * 0.5:
            return fenster[:pos + 1].rstrip(' ,') + '…'
    return fenster.rstrip() + '…'


def abnahmekriterium(f, titel):
    """Das 'Naechster Schritt' des Hauses IST das Abnahmekriterium.

    Fehlt es, wird der Kontext als Ersatz benutzt und als solcher
    gekennzeichnet - ein als Abnahmekriterium ausgegebener Kontext waere
    sonst eine Behauptung, die der Eintrag nicht traegt. Die Herkunft ist
    Teil des Eintrags, damit ein Pruefer weiss, was er prueft.
    """
    schritt = f.get('Naechster Schritt', []) + f.get('Nächster Schritt', [])
    if schritt:
        return kuerzen(' '.join(schritt)), 'explicit'
    kontext = f.get('Kontext', [])
    if kontext:
        return ('[aus Kontext abgeleitet, der Eintrag nennt keinen '
                'Naechsten Schritt] ' + kuerzen(' '.join(kontext), 300)), 'derived_kontext'
    return ('[aus dem Titel abgeleitet, der Eintrag nennt weder Naechsten '
            'Schritt noch Kontext]'), 'derived_titel'


# --- Plan lesen ---------------------------------------------------------------


def plan_wellen(plan_pfad):
    """Liest aus dem Routing-Plan je ID: Welle, Profil, Aufwand.

    Der Plan ist Markdown mit Wellen-Ueberschriften '### Welle N' und
    Stichzeilen '- **T-123 - Titel** · status · Aufwand M · Profil `x`'.
    Was der Plan nicht traegt, taucht hier nicht auf - das wird als Befund
    gemeldet, nicht still ergaenzt.
    """
    if not plan_pfad or not os.path.isfile(plan_pfad):
        return {}
    zeilen = lies_text(plan_pfad)
    rost = set(ROSTER)
    out = {}
    welle = 0
    for z in zeilen:
        w = re.match(r'^###\s*Welle\s+(\d+)', z)
        if w:
            welle = int(w.group(1))
            continue
        m = re.match(r'^\s*-\s+\*\*(T-\d+)\s+[\u2014\u2013-]\s+(.+?)\*\*\s*\u00b7(.*)$', z)
        if m and welle:
            rest = m.group(3)
            aufw = re.search(r'Aufwand\s+([SML])', rest)
            prof = re.search(r'Profil\s+`([a-z0-9][a-z0-9-]{2,30})`', rest)
            out[m.group(1)] = {
                'welle': welle,
                'titel_plan': m.group(2).strip(),
                'aufwand': aufw.group(1) if aufw else None,
                'profil': prof.group(1) if prof and prof.group(1) in rost else None,
            }
    return out


def wellen_berechnen(bloecke):
    """Wellen aus den Querverweisen (topologisch, mit wiederholter Entspannung).

    Uebernommen aus routing_plan_bauen.wellen: jeder Punkt wartet auf alle
    Punkte, auf die er im Text verweist.
    """
    welle = {b['nummer']: 1 for b in bloecke}
    for _ in range(len(bloecke) + 2):
        geaendert = False
        for b in bloecke:
            for q in ALLE_IDS.findall(' '.join(b['text'])):
                if q in welle and q != b['nummer']:
                    neu = max(welle[b['nummer']], welle[q] + 1)
                    if neu > welle[b['nummer']] and neu <= 6:
                        welle[b['nummer']] = neu
                        geaendert = True
        if not geaendert:
            break
    return welle


# --- Worklist ----------------------------------------------------------------


def auflisten(quelle, plan_pfad=None):
    """Baut die Worklist-Liste aus TASKS.md (+ optional Plan fuer Welle/Profil)."""
    bloecke, nl, offen_ab, erledigt_ab, untermittelt = bloecke_lesen(quelle)
    offen = [b for b in bloecke if b['status'] != 'x']
    welle_quelle = plan_wellen(plan_pfad) if plan_pfad else {}
    # Welle aus dem Plan, wo er den Punkt traegt; sonst aus den Querverweisen.
    welle_quer = wellen_berechnen(offen) if offen else {}

    items = []
    for b in offen:
        f = felder(b['text'])
        kriterium, herkunft = abnahmekriterium(f, b['titel'])
        p = welle_quelle.get(b['id'], {})
        welle = p.get('welle')
        wellen_herkunft = 'plan' if welle else 'querverweis'
        if not welle:
            welle = welle_quer.get(b['nummer'], 1)
        items.append(OrderedDict((
            ('id', b['id']),
            ('titel', b['titel']),
            ('beschreibung', kuerzen(' '.join(b['text'][1:]), 400)),
            ('abnahmekriterium', kriterium),
            ('abnahmekriterium_herkunft', herkunft),
            ('assignee', p.get('profil') or 'default'),
            ('profil_aus_plan', p.get('profil') is not None),
            ('bucket', 'ORDERED' if welle > 1 else 'PARALLEL'),
            ('welle', welle),
            ('welle_herkunft', wellen_herkunft),
            ('status', status_text(b['status'])),
            ('aufwand', p.get('aufwand')),
            ('kopf_untermittelt', b['untermittelt']),
            ('quelle_zeile', b['zeile']),
        )))
    return items, {'nl': nl, 'offen_ab': offen_ab, 'erledigt_ab': erledigt_ab,
                   'bloecke': len(bloecke), 'untermittelt': untermittelt}


def buckets(items):
    par = [i for i in items if i['bucket'] == 'PARALLEL']
    ord_ = [i for i in items if i['bucket'] == 'ORDERED']
    return par, ord_


def als_json(items, quelle, plan_pfad, meta):
    par, ord_ = buckets(items)
    dok = OrderedDict((
        ('quelle', os.path.relpath(quelle).replace('\\', '/')),
        ('plan', os.path.relpath(plan_pfad).replace('\\', '/') if plan_pfad else None),
        ('erzeugt', date_heute()),
        ('anzahl', len(items)),
        ('buckets', OrderedDict((('PARALLEL', len(par)), ('ORDERED', len(ord_))))),
        ('items', items),
    ))
    if meta:
        dok['befunde'] = meta
    return dok


def als_markdown(dok):
    z = []
    z.append('# Worklist: offene Punkte aus TASKS.md')
    z.append('')
    z.append('Erzeugt am %s · Quelle: `%s` · Plan: %s · Werkzeug: `%s`'
             % (dok['erzeugt'], dok['quelle'],
                '`%s`' % dok['plan'] if dok['plan'] else 'ohne (Querverweis-Rechnung)',
                os.path.basename(__file__)))
    z.append('')
    z.append('Gesamt **%d** Punkte: **%d PARALLEL** / **%d ORDERED**.'
             % (dok['anzahl'], dok['buckets']['PARALLEL'], dok['buckets']['ORDERED']))
    z.append('')
    if dok.get('befunde'):
        z.append('## Befunde am Planeingang')
        z.append('')
        for k, v in dok['befunde'].items():
            z.append('- **%s**: %s' % (k, v))
        z.append('')
    z.append('## Items')
    z.append('')
    z.append('| # | ID | Titel | Abnahmekriterium | Herkunft | Assignee | Bucket |')
    z.append('|---|---|---|---|---|---|---|')
    for k, i in enumerate(dok['items'], 1):
        z.append('| %d | %s | %s | %s | %s | `%s` | %s |' % (
            k, i['id'], i['titel'].replace('|', '/'),
            i['abnahmekriterium'].replace('|', '/')[:300],
            i['abnahmekriterium_herkunft'],
            i['assignee'], i['bucket']))
    z.append('')
    z.append('Regel: PARALLEL-Eintraege haben keine Reihenfolgebindung untereinander '
             '(Welle 1). ORDERED-Eintraege tragen einen Querverweis auf einen '
             'Punkt einer frueheren Welle und muessen in der Wellen-Reihenfolge '
             'gelaufen werden. Die Reihenfolge in `items` ist die Quell-Reihenfolge '
             'aus TASKS.md; die Ausfuehrungsreihenfolge steht in `welle` + `bucket`.')
    z.append('')
    return '\n'.join(z)


def date_heute():
    import datetime
    return datetime.date.today().isoformat()


ROSTER = ('hermes-wartung', 'basic-memory', 'agent-trade-kit',
          'markt-recherche', 'nerd', 'lotse', 'default')


def main():
    ap = argparse.ArgumentParser(description='Routing-Plan in eine Worklist normalisieren')
    ap.add_argument('tasks')
    ap.add_argument('ziel')
    ap.add_argument('--plan', default=None,
                    help='Routing-Plan (.md); traegt Welle/Profil/Aufwand')
    ap.add_argument('--markdown', default=None, help='zusaetzliche Markdown-Fassung')
    args = ap.parse_args()

    items, meta = auflisten(args.tasks, args.plan)
    par, ord_ = buckets(items)

    befunde = {}
    if args.plan:
        if not os.path.isfile(args.plan):
            befunde['plan_fehlt'] = ('Plan %s nicht gefunden - die Worklist wurde '
                                    'allein aus TASKS.md gebaut (Welle aus '
                                    'Querverweisen, Profil %default).' % args.plan)
        else:
            plan_ids = set(plan_wellen(args.plan))
            fehlend = sorted({i['id'] for i in items} - plan_ids,
                             key=lambda s: int(s[2:]))
            extra = sorted(plan_ids - {i['id'] for i in items},
                           key=lambda s: int(s[2:]))
            if fehlend:
                befunde['plan_unvollstaendig'] = (
                    '%d offene Punkte aus TASKS.md fehlen im Plan: %s. Die '
                    'Worklist traegt sie trotzdem (Quelle ist TASKS.md), der '
                    'Ausfuehrungsplan des Plans selbst bleibt aber unvollstaendig '
                    '- siehe MaxHirn/Archiv/ROUTING_PLAN_pruefbericht_2026-10-04.md.'
                    % (len(fehlend), ', '.join(fehlend[:8]) + ' …'))
            if extra:
                befunde['plan_zu_alt'] = ('Plan traegt %d Punkte, die TASKS.md nicht '
                                          'mehr offen fuehrt (erledigt oder entfernt): '
                                          '%s' % (len(extra), ', '.join(extra[:8])))
    unter = meta.get('untermittelt') or []
    if unter:
        befunde['kopf_untermittelt'] = (
            '%d Kopfzeile(n) in TASKS.md ohne schliessende `**`: %s. Die Punkte '
            'sind in der Worklist enthalten (sonst waeren sie still verloren), '
            'aber ihre Ueberschrift ist fuer einen Menschen unlesbar - die '
            'Dateien gehoeren in MaxHirn/Archiv/TASKS.md (Bereich wissen), '
            'hier nicht geschrieben.'
            % (len(unter), ', '.join('%s (Zeile %d)' % (tid, zl)
                                     for zl, tid in unter[:8])))
    if not items:
        befunde['leerfall'] = ('no open items - nothing to execute; die Worklist '
                               'ist leer, die Folgekarten noepen.')

    dok = als_json(items, args.tasks, args.plan, befunde)
    ensure_parent(args.ziel)
    write_json(dok, args.ziel)
    print('geschrieben: %s' % os.path.abspath(args.ziel))
    if args.markdown:
        ensure_parent(args.markdown)
        with open(args.markdown, 'w', encoding='utf-8', newline='') as fh:
            fh.write(als_markdown(dok))
        print('geschrieben: %s' % os.path.abspath(args.markdown))
    print('offene Punkte: %d, PARALLEL: %d, ORDERED: %d'
          % (len(items), len(par), len(ord_)))
    return 0


def ensure_parent(pfad):
    d = os.path.dirname(pfad)
    if d and not os.path.isdir(d):
        os.makedirs(d)


def write_json(dok, pfad):
    with open(pfad, 'w', encoding='utf-8', newline='') as fh:
        json.dump(dok, fh, ensure_ascii=False, indent=2)
        fh.write('\n')


if __name__ == '__main__':
    sys.exit(main())
