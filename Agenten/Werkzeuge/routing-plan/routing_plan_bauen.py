#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Baut den Routing-Plan aus TASKS.md (Abschnitt 'Offen').

Deterministisch: jeder offene Punkt genau einmal, mit Quelleile,
Definition of Done (der Naechster-Schritt des Hauses), Blockern,
Aufwand, Profil und einer Wellen-Reihenfolge aus den Querverweisen.

Aufruf:  python routing_plan_bauen.py <tasks.md> <ziel.md>
"""
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

# Die Kopfregel steht an EINER Stelle (kopfformen.py) und wird importiert.
# Sie umfasst alle drei Kopfformen, die das Haus schreibt (Gevrierstrich /
# Bindestrich / Titel ohne schliessendes '**'); Begründung und Messzahlen
# stehen dort. Ein zweites Muster hier waere eine zweite Wahrheit: genau so
# ist es am 04.10.2026 zu 47 verlorenen offenen Punkten gekommen, weil der
# Pruefer die Enge des Bauers TEILTE - er pruefte die Luecke nicht.
import kopfformen

KOPF = kopfformen.KOPF          # nur als Kurzname fuer Aufrufer im Haus
FELD = re.compile(r'^\s{2,}([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß /().\-]{1,45}?):\s*(.*)$')
ALLE_IDS = re.compile(r'\bT-(\d{3,})\b')

# Profil-Roster (aus der Karten-Vorgabe) + Haus-Profile.
ROSTER = ('hermes-wartung', 'basic-memory', 'agent-trade-kit',
          'markt-recherche', 'nerd', 'lotse', 'default')

# Kennzeichen je Profil. Bewusst ENGE Wortlisten: eine breite Liste
# ('profil', 'memory', 'signal') traf Nachbarwoerter einer fremden Sache -
# T-339 (Bot-Profile) landete wegen 'memory_query_rewrite' bei basic-memory.
KENNZEICHEN = {
    'agent-trade-kit': (r'agent-trade-kit|trade.?kit|agent[_-]trade[_-]kit', 3),
    'basic-memory': (r'basic-memory|gedaechtnisspeicher|memory.?store|zugaenge\.md|auth\.json|'
                     r'grundlagen\.md', 3),
    'nerd': (r'sicherheit|schwachstelle|vulnerab|defender|exploit|passwortschutz|'
             r'zugangsschutz|code-audit', 3),
    'lotse': (r'kanban|dispatch|delegation|repos-zentrale|skillkatalog|routing|'
              r'zentrale|profil.?flotte', 3),
    'markt-recherche': (r'markt|boerse|b[öo]rse|kraken|okx|spot|futures|perp|'
                        r'gebuhr|kerze|historie|backtest|replay|rotation|tsmom|qqq|'
                        r'studie|regime|gebuhr|kennzahl|strategie|spur', 2),
    'hermes-wartung': (r'agenten/hermes|hermes-wartung|config\.yaml|gateway|'
                       r'claude.?desktop|omni.?route|photon|bonsai|hermes.?update|'
                       r'mcp|skill|cron|profil', 2),
}

# Pfadregeln: eine Datei-Pfadangabe im Eintrag ist ein haerteres Zeugnis
# als ein Wort im Fliesstext.
PFADREGEL = (
    (r'agenten/hermes/(profiles|skills|cron|scripts)|hermes/config\.yaml|'
     r'hermes-agent|knowledge_?hub', 'hermes-wartung'),
    (r'werkstatt/repos/agent-trade-kit', 'agent-trade-kit'),
    (r'werkstatt/repos/basic-memory|\.agents/skills|profiles/basic-memory', 'basic-memory'),
    (r'werkstatt/[^/]*(nerd|claude-red|security)', 'nerd'),
    (r'agenten/bus|agenten/hermes/kanban|repos-zentrale|repos-updaten', 'lotse'),
    (r'agenten/handel|werkstatt/omnitrade|tsmom|okx_bot', 'markt-recherche'),
)

BEGRUENDUNG = {
    'hermes-wartung': 'betrifft den Hermes-Baum (Config/Profile/Skills/Dienste)',
    'basic-memory': 'betrifft den Gedaechtnisspeicher bzw. Zugangsdaten-Verwaltung',
    'agent-trade-kit': 'betrifft das agent-trade-kit-Repo',
    'markt-recherche': 'betrifft Marktdaten, Boersen-Zugriffe oder Strategie-Auswertung',
    'nerd': 'betrifft Sicherheitsmethodik oder Code-/Zugangspruefung',
    'lotse': 'betrifft Routing, Delegation oder die Bot-/Kanban-Flotte',
    'default': 'allgemeine Entwicklungsarbeit ohne Spezialprofil',
}

MAX_HINWEIS = re.compile(r'wartet auf|entscheidung max|nur max|freigabe|pflicht.*max|'
                         r'portalanmeldung|zugangsdat|haushand|kontostand|guthaben|\[.\]', re.I)


def titel_aus(rest):
    """Rest nach dem Trennzeichen -> Titel (Regel liegt in kopfformen.py)."""
    return kopfformen.titel_aus(rest)


def bloecke_lesen(pfad):
    bloecke, ungelesen, nl, offen_ab, erledigt_ab = kopfformen.datei_lesen(pfad)
    # Eine Zeile, die wie ein Eintrag aussieht, aber nicht gelesen wurde, ist
    # ein BEFUND und kein Detail: stillschweigend fehlende Punkte sind genau
    # der Fehler, den diese Karte abstellt (47 von 170 am 04.10.2026).
    if ungelesen:
        raise SystemExit(
            'Abbruch: %d Zeile(n) im Abschnitt "Offen" sehen wie ein Eintrag '
            'aus, werden von kopfformen.KOPF aber nicht erfasst:\n  %s\n'
            'Die Kopfregel in kopfformen.py kennt diese Schreibweise nicht.'
            % (len(ungelesen),
               '\n  '.join('%d: %s' % (z, t[:90]) for z, t in ungelesen[:10])))
    return bloecke, nl, offen_ab, erledigt_ab


def felder(text):
    """Holt die Hausfelder eines Eintrags.

    Ein Feld laeuft bis zur naechsten Zeile mit einem neuen Feldnamen; die
    Folgezeilen ohne Doppelpunkt sind Fortsetzung DESSELBEN Feldes. Ohne das
    liefert 'Naechster Schritt' nur die erste umgebrochene Zeile und damit
    eine Definition of Done, die mitten im Satz endet.
    """
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
            '~': 'in Arbeit', 'x': 'erledigt'}.get(zeichen.strip(), zeichen.strip() or 'offen')


KURZ = 360


def kuerzen(text, grenze=KURZ):
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


def definition_of_done(f):
    """Der Naechster Schritt des Hauses IST die Definition of Done.

    Fehlt er im Eintrag, wird der Kontext als Ersatz benutzt und als solcher
    gekennzeichnet - ein als DoD ausgegebener Kontext ist sonst eine
    Behauptung, die der Eintrag nicht traegt.
    """
    schritt = f.get('Naechster Schritt', []) + f.get('Nächster Schritt', [])
    if schritt:
        return kuerzen(' '.join(schritt))
    kontext = f.get('Kontext', [])
    if kontext:
        return '[aus Kontext abgeleitet, der Eintrag nennt keinen ' \
               'Naechsten Schritt] ' + kuerzen(' '.join(kontext), 300)
    return '[aus dem Titel abgeleitet, der Eintrag nennt weder Naechsten ' \
           'Schritt noch Kontext]'


def blocker(block, f):
    teile = []
    if block['status'] in ('?', '!'):
        teile.append('Status `%s` (%s)' % (
            block['status'],
            'wartet auf Entscheidung/Information von Max' if block['status'] == '?'
            else 'blockiert, Ursache im Kontext'))
    wartet = f.get('Wartet auf', [])
    if wartet:
        teile.append('wartet auf: ' + re.sub(r'\s+', ' ', ' '.join(wartet))[:160])
    elif block['status'] == ' ' and MAX_HINWEIS.search(' '.join(block['text'])):
        teile.append('Entscheidung/Zugang von Max noetig (im Text genannt)')
    return '; '.join(teile) if teile else 'keine'


def aufwand(block, f):
    text = ' '.join(block['text'])
    laenge = len(text)
    schritte = len(f.get('Naechster Schritt', []) + f.get('Nächster Schritt', []))
    hat_max = bool(block['status'] in ('?', '!') or f.get('Wartet auf'))
    punkte = 0
    punkte += 1 if laenge > 900 else 0
    punkte += 1 if laenge > 2200 else 0
    punkte += 1 if schritte > 2 else 0
    punkte += 1 if hat_max else 0
    punkte += 1 if len(ALLE_IDS.findall(text)) > 3 else 0
    if punkte <= 0:
        return 'S'
    return 'M' if punkte <= 2 else 'L'


def profil(block):
    """Waehlt das Profil aus Pfadzeilen und Text, gewichtet nach Pfad = staerker.

    Rueckgabe: (profil, begruendung). Es gibt KEINE stillen Treffer -
    ohne jeden Beleg heisst es 'default', und das wird als Begruendung
    mitgeliefert statt versteckt.
    """
    text = ' '.join(block['text'])
    pfade = ' '.join(z for z in block['text']
                     if re.search(r'(agenten|werkstatt|maxhirn|modelle)/[a-z]', z, re.I))
    punkte = dict.fromkeys(ROSTER, 0)
    belege = defaultdict(list)
    for muster, name in PFADREGEL:
        m = re.search(muster, pfade, re.I)
        if m:
            punkte[name] += 5
            belege[name].append('Pfad `' + m.group(0).rstrip('\\') + '`')
    for name, (muster, gewicht) in KENNZEICHEN.items():
        treffer = re.findall(muster, text, re.I)
        punkte[name] += gewicht * min(len(treffer), 3)
        if treffer:
            eigene = sorted({t.lower() for t in treffer})
            belege[name].append('im Text: ' + ', '.join(eigene[:3]))
    bester = max(punkte, key=lambda n: (punkte[n], n == 'default'))
    if punkte[bester] == 0:
        bester = 'default'
    beleg = '; '.join(belege[bester][:2]) or 'nur der Titel, kein Pfad-Beleg'
    return bester, '%s — %s (Beleg: %s)' % (bester, BEGRUENDUNG[bester], beleg)


def begruendung(name, block):
    titel = block['titel']
    return '%s — %s' % (name, BEGRUENDUNG[name]) + ' — Eintrag: ' + (
        kuerzen(titel, 70))


def wellen(offen):
    """Wellen aus den Querverweisen (topologisch, wiederholte Entspannung)."""
    welle = {b['nummer']: 1 for b in offen}
    for _ in range(len(offen) + 2):
        geaendert = False
        for b in offen:
            for q in ALLE_IDS.findall(' '.join(b['text'])):
                if q in welle and q != b['nummer']:
                    neu = max(welle[b['nummer']], welle[q] + 1)
                    if neu > welle[b['nummer']] and neu <= 6:
                        welle[b['nummer']] = neu
                        geaendert = True
        if not geaendert:
            break
    return welle


def ziel_waehlen(quelle, ziel):
    """Liefert (pfad, gedruckt_hinweis).

    Liegt schon ein Plan im Ordner der Quelle, wird der neue NICHT
    ueberschrieben: er behaelt sein Datum im Namen. Ein Plan, der seinen
    Vorgaenger ohne Spur ersetzt, ist bei einem Haus mit 119 offenen
    Punkten nicht mehr von einem neuen Plan zu unterscheiden.
    """
    if not os.path.exists(ziel):
        return ziel, False
    stamp = date.today().isoformat()
    basis, ext = os.path.splitext(ziel)
    # Ein zweiter Lauf am selben Tag darf den Tagesplan nicht ueberschreiben:
    # -2, -3 ... dahinter, sonst ist der erste Plan des Tages spurlos weg.
    kandidat = '%s_%s%s' % (basis, stamp, ext)
    n = 2
    while os.path.exists(kandidat):
        kandidat = '%s_%s-%d%s' % (basis, stamp, n, ext)
        n += 1
    return kandidat, True


def main():
    quelle, ziel = sys.argv[1], sys.argv[2]
    ziel, datiert = ziel_waehlen(quelle, ziel)
    bloecke, nl, offen_ab, erledigt_ab = bloecke_lesen(quelle)
    offen = [b for b in bloecke if b['status'] != 'x']
    welle = wellen(offen)

    zeilen = []
    zeilen.append('# Routing-Plan: offene Punkte in %s' % os.path.basename(quelle))
    zeilen.append('')
    zeilen.append('Erzeugt am %s · Quelle: `%s` · Werkzeug: `%s`' % (
        date.today().isoformat(), quelle, os.path.basename(__file__)))
    zeilen.append('')

    # (a) gewaehlte Datei
    zeilen.append('## (a) Gewaehlte tasks.md')
    zeilen.append('')
    zeilen.append('**%s**' % quelle)
    zeilen.append('')
    zeilen.append('Das ist die einzige `TASKS.md` im Baum und die einzige mit den '
                  'Abschnitten `## Offen` (ab Zeile %d) und `## Erledigt` (ab Zeile %d) — '
                  'sie ist der aktive Haus-Backlog, alle Profil- und Cron-Karten verweisen '
                  'auf sie.' % (offen_ab, erledigt_ab))
    zeilen.append('')
    zeilen.append('Stand: %d Eintraege im Abschnitt `Offen`, davon %d mit `[x]` '
                  '(im Haus noch nicht nach `## Erledigt` gewandert), **%d offen**. '
                  'Statuszeichen: %s.' % (
                      len(bloecke), len(bloecke) - len(offen), len(offen),
                      ', '.join('%s %d' % (status_text(k), v) for k, v in
                                sorted(Counter(b['status'] for b in bloecke).items()))))
    zeilen.append('')

    # (d) Leer-Aussage zuerst, damit sie nie leer bleibt
    zeilen.append('## (d) Leerzustand')
    zeilen.append('')
    if not offen:
        zeilen.append('**Es gibt null offene Punkte.** Der Abschnitt `Offen` enthaelt '
                      'keinen unerledigten Eintrag; der Plan hat folglich keine '
                      'Inventar- und keine Wellenabschnitte.')
    else:
        zeilen.append('**Nicht leer: %d offene Punkte.** Kein leerer Zustand; die '
                      'Abschnitte (b) und (c) tragen alle %d Eintraege.' % (len(offen), len(offen)))
    zeilen.append('')

    # (b) Inventar
    zeilen.append('## (b) Inventar der offenen Punkte')
    zeilen.append('')
    zeilen.append('| # | Titel | Quelle (TASKS.md) | Definition of Done | Blocker | '
                  'Aufwand | Profil | Begruendung |')
    zeilen.append('|---|---|---|---|---|---|---|---|')
    for k, b in enumerate(offen, 1):
        f = felder(b['text'])
        prof, warum = profil(b)
        zeilen.append('| %d | %s (%s, %s) | Zeile %d | %s | %s | %s | `%s` | %s |' % (
            k, kuerzen(b['titel'], 110), b['id'], status_text(b['status']), b['zeile'],
            definition_of_done(f).replace('|', '/'),
            blocker(b, f).replace('|', '/'),
            aufwand(b, f),
            prof,
            warum.replace('|', '/')))
    zeilen.append('')
    zeilen.append('Summen: %d Zeilen fuer %d offene Punkte (jeder genau einmal), '
                  'Aufwand %s, Profile %s.' % (
                      len(offen), len(offen),
                      ', '.join('%s=%d' % (a, c) for a, c in
                                sorted(Counter(aufwand(b, felder(b['text']))
                                               for b in offen).items())),
                      ', '.join('%s=%d' % (a, c) for a, c in
                                sorted(Counter(profil(b)[0] for b in offen).items()))))
    zeilen.append('')

    # (c) Wellen
    zeilen.append('## (c) Wellen-Reihenfolge')
    zeilen.append('')
    gruppen = defaultdict(list)
    for b in offen:
        gruppen[welle[b['nummer']]].append(b)
    # Wellen dicht nummerieren: eine Luecke (1,2,3,5,6) sieht wie ein
    # verschwundener Abschnitt aus und traegt keine Information.
    dicht = {alt: neu for neu, alt in enumerate(sorted(gruppen), 1)}
    for w in sorted(gruppen):
        eintraege = gruppen[w]
        parallel = len(eintraege) > 1
        zeilen.append('### Welle %d — %s' % (
            dicht[w], 'parallel (%d Eintraege, kein Querverweis zwischen ihnen)'
            % len(eintraege) if parallel else 'sequenziell (1 Eintrag)'))
        zeilen.append('')
        for b in eintraege:
            f = felder(b['text'])
            prof, _ = profil(b)
            zeilen.append('- **%s — %s** · %s · Aufwand %s · Profil `%s` · %s' % (
                b['id'], kuerzen(b['titel'], 110), status_text(b['status']),
                aufwand(b, f), prof, blocker(b, f)))
        zeilen.append('')
    zeilen.append('Regel: Welle 1 ist parallel startbar; jeder Eintrag einer Welle n '
                  'traegt einen Querverweis auf einen Eintrag der Welle n-1 und wartet '
                  'darauf. Innerhalb einer Welle gibt es keine Abhaengigkeit.')
    zeilen.append('')

    # (e) naechste Aktionen
    zeilen.append('## (e) Naechste Aktion — die ersten 3 Dispatches')
    zeilen.append('')
    for k, b in enumerate(offen[:3], 1):
        f = felder(b['text'])
        prof, _ = profil(b)
        zeilen.append('%d. **%s — %s** → `kanban create` mit assignee `%s`, '
                      'Aufwand %s, Blocker: %s' % (
                          k, b['id'], kuerzen(b['titel'], 110), prof,
                          aufwand(b, f), blocker(b, f)))
    zeilen.append('')
    zeilen.append('Nach den ersten drei: Welle 1 restliche %d Eintraege parallel, '
                  'danach Welle 2.' % max(0, len(gruppen.get(1, [])) - 3))
    zeilen.append('')

    inhalt = nl.join(zeilen)
    # Die Datei ist CRLF (wie TASKS.md) - Zeilenenden bewusst gesetzt.
    with open(ziel, 'w', encoding='utf-8', newline='') as fh:
        fh.write(inhalt)
    print('geschrieben: %s' % os.path.abspath(ziel))
    if datiert:
        print('Hinweis: ein Plan lag schon vor, deshalb mit Datum im Namen')
    print('offene Punkte: %d, Zeilen: %d' % (len(offen), len(zeilen)))


if __name__ == '__main__':
    main()