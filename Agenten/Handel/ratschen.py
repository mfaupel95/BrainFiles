"""Die Drawdown-Ratsche - EINE Umsetzung fuer alle Spuren.

Vorher rechnete jede Spur ihre eigene Schwelle, und alle benutzten dieselbe
Zahl 15.0 mit einem ANDEREN Nenner:

    scanner   15% x max_gesamt_usd          (1000) -> 150.00 USD
    xperp     15% x max_margin_gesamt_usd   ( 200) ->  30.00 USD
    swap      15% x max_margin_gesamt_usd   ( 200) ->  30.00 USD
    orbk      15% x kill_switch_gesamt_usd  ( 150) ->  22.50 USD
    kraken    15% x max_gesamt_eur          ( 200) ->  30.00 EUR

Dieselbe Zahl bedeutete je Spur einen anderen Betrag - und schlimmer: die
Schwelle hing an einer Groesse, mit der sie nichts zu tun hat. Die Ratsche
misst den Ruecklauf der realisierten Gewinnkurve. Wer den Kapitaldeckel
anhebt, verschiebt lautlos eine Schutzschwelle. Am 15.09.2026 hob
max_gesamt_usd von 400 auf 1000 die scanner-Schwelle von 60 auf 150 USD -
und die 150 haette erst gegriffen, wenn die Spur bei -9.76 USD gestanden
haette, also nach mehr Verlust als ihrem gesamten Hoechstgewinn. Das ist die
Klasse Fehler, die diese Datei abschafft.

DIE REGEL JETZT:

1. Die Schwelle ist ein BETRAG, kein Prozentsatz: drawdown_halbierung_usd.
   Sie steht ausdruecklich in der wachen.json und ist spuruebergreifend
   vergleichbar.
2. Ist sie nicht gesetzt, wird sie hergeleitet - aus dem BUCHRISIKO der Spur,
   also dem, was sie verliert, wenn JEDE offene Position gleichzeitig den Stop
   trifft. Faktor ueber drawdown_halbierung_im_buchrisiko (Standard 1.0).
   Das Buchrisiko ist die einzige Groesse, die den Ruecklauf richtig skaliert:
   sie waechst mit der Positionszahl und mit dem Risiko je Position, und der
   Kapitaldeckel kommt darin nicht vor.
3. Ist auch das nicht herleitbar, gibt es KEINE Ratsche - halbierungsschwelle()
   liefert None, und lage() meldet das sichtbar als "keine Ratsche
   konfiguriert". Eine stillschweigende Ersatzschwelle waere schlimmer als
   keine: sie sieht aus wie Schutz.

Der Prozentsatz drawdown_halbierung_prozent wird NICHT mehr gelesen. Er war
der Fehler.
"""

# Schluesselpaare je Spur: (Risiko einer Position, Hoechstzahl Positionen).
# Die Namen unterscheiden sich zwischen den Spuren; die Bedeutung ist gleich.
BUCHRISIKO_PAARE = (
    ("risiko_je_position_usd",  "max_offene_positionen"),
    ("risiko_je_anlauf_usd",    "max_offene_anlaeufe"),
    ("risiko_pro_trade_usd",    "max_offene_positionen"),
    ("risiko_pro_trade_usdt",   "max_offene_positionen"),
    ("risiko_pro_trade_eur",    "max_offene_positionen"),
    ("risiko_je_position_eur",  "max_offene_positionen"),
)

# Spuren, die ihr Gesamtrisiko schon ausdruecklich nennen, brauchen kein Paar.
BUCHRISIKO_GESAMT = ("max_risiko_gesamt_usd", "max_risiko_gesamt_eur")

STANDARD_FAKTOR = 1.0


def buch_risiko(w):
    """Was die Spur verliert, wenn alle offenen Positionen zugleich stoppen.

    Gibt None zurueck, wenn die Spur die beiden Zahlen nicht nennt - dann ist
    das Buchrisiko NICHT herleitbar, und der Aufrufer muss das melden statt zu
    raten. Eine geratene Schwelle ist gefaehrlicher als keine, weil sie wie
    Schutz aussieht.
    """
    for risiko_schluessel, anzahl_schluessel in BUCHRISIKO_PAARE:
        if risiko_schluessel in w and anzahl_schluessel in w:
            try:
                return float(w[risiko_schluessel]) * float(w[anzahl_schluessel])
            except (TypeError, ValueError):
                return None
    for schluessel in BUCHRISIKO_GESAMT:
        if schluessel in w:
            try:
                return float(w[schluessel])
            except (TypeError, ValueError):
                return None
    return None


def halbierungsschwelle(w):
    """Der Ruecklauf, ab dem die Groesse halbiert wird - als Betrag.

    Reihenfolge: ausdruecklicher Betrag, sonst Buchrisiko x Faktor, sonst None.

    Eine Schwelle von 0 oder darunter wird wie KEINE Schwelle behandelt und
    gibt None zurueck. Sie ist keine Linie, die man ueberschreiten kann: als
    Betrag gelesen wuerde sie JEDE Position sofort halbieren, und eine
    Fehlkonfiguration darf den Handel nicht drosseln. Sichtbar bleibt sie
    trotzdem - lage() meldet dann 'keine Ratsche konfiguriert'.
    """
    betrag = w.get("drawdown_halbierung_usd")
    if betrag is not None:
        try:
            schwelle = float(betrag)
        except (TypeError, ValueError):
            return None
        return schwelle if schwelle > 0 else None

    risiko = buch_risiko(w)
    if risiko is None:
        return None
    try:
        faktor = float(w.get("drawdown_halbierung_im_buchrisiko", STANDARD_FAKTOR))
    except (TypeError, ValueError):
        faktor = STANDARD_FAKTOR
    schwelle = risiko * faktor
    return schwelle if schwelle > 0 else None


def groessenfaktor(ruecklauf, w, schwelle=None):
    """1.0 = volle Groesse, 0.5 = halbiert. Ohne Schwelle immer 1.0.

    Ohne Schwelle 1.0 und nicht 0.5: fehlende Konfiguration darf den Handel
    nicht drosseln, sie muss nur sichtbar sein.
    """
    if schwelle is None:
        schwelle = halbierungsschwelle(w)
    if schwelle is None:
        return 1.0
    return 0.5 if ruecklauf >= schwelle else 1.0


def im_gewinn(hoch, w, schwelle=None):
    """Kann die Halbierung noch greifen, SOLANGE die Spur im Gewinn ist?

    Nicht 'erreichbar' - das waere falsch. drawdown() rechnet hoch minus kum,
    und die kumulierte Gewinnkurve darf ins Minus laufen, also waechst der
    Ruecklauf ueber den Hoechststand hinaus. Eine Schwelle ueber dem
    Hoechststand ist damit NICHT unerreichbar; sie greift nur erst, wenn die
    Spur mehr verloren hat als sie je gewonnen hatte, und schuetzt dann keinen
    Gewinn mehr, sondern faengt einen Nettoverlust - dafuer ist der
    Kill-Switch da.
    """
    if schwelle is None:
        schwelle = halbierungsschwelle(w)
    if schwelle is None or hoch is None or hoch == 0:
        return True
    return schwelle <= hoch


# WARUM NICHT EINFACH 'import ratschen': die Spuren werden mit ihrem eigenen
# Ordner als sys.path[0] gestartet. Handel/ waere nur ueber einen sys.path-
# Eintrag erreichbar, und der koennte gleichnamige Spurenmodule verdecken:
# gitter/ importiert ein eigenes grid.py, und daneben liegt Handel/grid.py.
# Deshalb laden die Spuren dieses Modul ueber den PFAD:
#
#     import os
#     from importlib.util import spec_from_file_location, module_from_spec
#     _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
#                       "ratschen.py")
#     _s = spec_from_file_location("ratschen", _p)
#     ratschen = module_from_spec(_s)
#     _s.loader.exec_module(ratschen)
