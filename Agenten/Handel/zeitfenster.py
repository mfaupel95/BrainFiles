"""Das Zeitfenster der Auswertung - an EINER Stelle.

Warum es diese Datei gibt: das Journalformat wird sonst zweimal gelesen
(auswertung_alle.zeilen und buchauswertung.lade_zeilen), und der orbk-
Sonderfall (nur Datum, keine Uhrzeit, keine Zone) waere zweimal da. Zwei
Lesarten desselben Zeitstempels laufen auseinander.

Alle Journale ausser orbk schreiben ISO-8601 mit Offset +00:00. Hier wird
alles auf UTC-aware normalisiert - naive Zeitstempel gelten als UTC, weil
das zum Rest des Spurenbaums passt.
"""

import datetime as dt

UTC = dt.timezone.utc


def jetzt():
    """Der aktuelle Zeitpunkt, UTC-aware. Eigene Funktion, damit Tests ihn
    ersetzen koennen, ohne datetime zu patchen."""
    return dt.datetime.now(UTC)


def parse(wert):
    """Ein Journalfeld als UTC-aware datetime, oder None.

    Zwei Formen kommen vor: ISO mit Offset (der Normalfall) und ein blosses
    Datum (orbk). Das Datum wird als Tagesbeginn UTC gelesen - jede andere
    Lesart verschiebt ein Tagesfenster um einen Tag.
    """
    if not wert:
        return None
    s = str(wert).strip()
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)


def _rand(wert, ende=False):
    """Eine Kommandozeilenangabe als Fenstergrenze."""
    d = parse(wert)
    if d is None:
        raise ValueError("Zeitangabe nicht lesbar: %r" % (wert,))
    if ende and len(str(wert).strip()) == 10:
        # Ein blosses Enddatum meint den ganzen Tag, nicht seinen Beginn.
        d = d + dt.timedelta(days=1) - dt.timedelta(microseconds=1)
    return d


def fenster(tage=None, seit=None, bis=None):
    """Die Grenzen eines Fensters. (None, None) heisst: alles.

    tage und seit schliessen sich aus - zwei Angaben fuer denselben Anfang
    waeren eine stille Vorrangregel.

    tage und bis ebenso: `tage` zaehlt von JETZT rueckwaerts, nicht von
    `bis`. Mit einem `bis` in der Vergangenheit liegt der Anfang hinter dem
    Ende, und das Fenster ist leer - ohne Fehler, ohne Meldung, nur ohne
    Zahlen. "--tage 30 --bis 2026-01-01" sieht aus wie 30 Tage im Januar
    und ist nichts. Genauso unbestimmt wie tage+seit, also genauso ein
    Fehler. Wer 30 Tage vor einem Datum will, nennt seit und bis.
    """
    if tage is not None and seit is not None:
        raise ValueError("tage und seit zusammen sind nicht eindeutig")
    if tage is not None and bis is not None:
        raise ValueError("tage zaehlt von jetzt rueckwaerts - mit bis "
                         "zusammen nicht eindeutig; nimm seit und bis")
    if tage is not None:
        return (jetzt() - dt.timedelta(days=int(tage)), None)
    return (_rand(seit) if seit else None,
            _rand(bis, ende=True) if bis else None)


def im_fenster(zeile, von, bis, spalte="zeit"):
    """Liegt die Zeile im Fenster?

    Bei offenem Fenster (von und bis None) ist die Antwort immer ja - auch
    fuer eine Zeile ohne lesbare Zeit. Sonst faellt sie raus: ihre
    Zugehoerigkeit ist nicht belegbar, und sie jedem Fenster zuzuschlagen
    waere die unehrlichere Wahl.
    """
    if von is None and bis is None:
        return True
    d = parse(zeile.get(spalte))
    if d is None:
        return False
    if von is not None and d < von:
        return False
    if bis is not None and d > bis:
        return False
    return True
