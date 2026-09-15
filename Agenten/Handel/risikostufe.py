"""Risikostufe: derselbe Handel, andere Positionsgroessen.

WARUM ES DAS GIBT (Auftrag Max, 15.09.2026)
-------------------------------------------
"neuen Dauerlauf mit gleichem Inhalt, nur anders gesetzter Risiko-Bewertung ...
und alle mit groesseren Positionen je Spur ausser Spiegel, um schneller von den
Daten lernen zu koennen"

Die Strategien bleiben unangetastet: dieselben Wachen, dieselben Regeln, nur
ein Faktor auf die Betraege. Ziel ist NICHT mehr Gewinn, sondern mehr
Beobachtungen je Zeiteinheit - bei 20-EUR-Einsaetzen dauert jede Statistik
Monate, bei 80 EUR sieht man denselben Fehler viermal schneller.

WIE ES WIRKT
------------
1. Der Dauerlauf setzt fuer die Kindprozesse EINER Stufe `HANDEL_RISIKO=mittel`
   (Default `niedrig`, Faktor 1.0).
2. Jede Spur skaliert beim Laden ihre Wachen (`skaliere`) und schreibt Zustand
   und Journal mit Suffix (`datei`: zustand.mittel.json,
   handelsjournal.mittel.csv). Ohne `HANDEL_RISIKO` aendert sich NICHTS - das
   ist die Bedingung dafuer, dass die Umstellung den laufenden Betrieb nicht
   anfasst.

WAS SKALIERT WIRD - UND WAS AUSDRUECKLICH NICHT
-----------------------------------------------
Die erste Fassung skalierte alle Felder mit `_usd`/`_eur` im Namen. Das waere
falsch gewesen und ist an den echten Wachen nachgemessen:

  NICHT skalieren: `marketcap_band_usd` (Marktgroesse des Tokens, kein
  Einsatz!), `groesster_ruecklauf_papierlauf_usd` (eine MESSUNG, kein Limit -
  skaliert waere sie eine Behauptung ueber die Vergangenheit),
  `mindest_guthaben_eur`/`mindest_marge_frei_usd` (Kontoschwellen der Boerse),
  `umsatz_bezug_usd` (Handelsvolumen), `punkt_wert_usd` (Vertragsgroesse).

  Skalieren: alles, was die Buchgroesse begrenzt - `risiko_je_position_usd`,
  `max_pro_trade_usd`, `max_gesamt_usd`, `risiko_je_anlauf_usd`,
  `max_margin_*`, `max_einsatz_*`, `einsatz_usd`, `stop_usd`.

  MIT skalieren muessen `drawdown_halbierung_usd` und `kill_switch_gesamt_usd`:
  sie sind in Buchrisiko ausgedrueckt (1.0x, siehe ratschen.py). Blieben sie
  stehen, wuerde die doppelte Position die Halbierung sofort ausloesen - die
  Stufe waere nach dem ersten Verlust gesperrt und die Daten unbrauchbar.

Felder mit fuehrendem Unterstrich (`_risiko_je_position_usd`) sind in dieser
Codebasis der dokumentierte Vorwert und werden nie angefasst.
"""

from __future__ import annotations

import os

# Faktor je Stufe. 1/2/4 ist bewusst grob: feiner waere bei dieser Datenmenge
# ohnehin nicht unterscheidbar, und die Stufen sollen sich DEUTLICH
# unterscheiden, sonst braucht man sie nicht.
FAKTOREN = {"niedrig": 1.0, "mittel": 2.0, "hoch": 4.0}
STANDARD = "niedrig"

# Die Felder, die die Buchgroesse begrenzen. Positivliste, nicht Muster: eine
# Regel "alles mit _usd" hat an den echten Wachen vier Felder getroffen, die
# Marktdaten oder Messwerte sind (siehe Modulkopf).
SKALIEREN = (
    "risiko_je_position_usd", "risiko_je_position_eur",
    "risiko_pro_trade_usd", "risiko_pro_trade_usdt",
    "risiko_je_anlauf_usd",
    "max_pro_trade_usd", "max_pro_trade_eur",
    "max_gesamt_usd", "max_gesamt_eur",
    "max_gesamt_risiko_usd",
    "max_risiko_gesamt_usd", "max_risiko_pro_trade_usd",
    "max_margin_je_anlauf_usd", "max_margin_gesamt_usd",
    "max_einsatz_je_kopie_usd", "max_einsatz_je_kauf_usd",
    "max_einsatz_je_position_usd",
    "einsatz_usd", "max_verlust_usd", "stop_usd",
    # Die beiden Ratschen - siehe Modulkopf.
    "drawdown_halbierung_usd", "kill_switch_gesamt_usd",
    "kill_switch_gesamt_eur", "kill_switch_gesamt_usd_papier",
)

# Sicherheitsnetz: selbst wenn ein Feld oben faelschlich stehen sollte, wird es
# hier nie skaliert. Marktdaten und Messwerte.
NIE_SKALIEREN = (
    "marketcap_band_usd", "groesster_ruecklauf_papierlauf_usd",
    "groesster_ruecklauf_papierlauf_eur", "groesster_ruecklauf_papierlauf_usdt",
    "mindest_guthaben_eur", "mindest_marge_frei_usd", "mindest_marge_frei_usdt",
    "umsatz_bezug_usd", "punkt_wert_usd", "punkt_wert_usdt",
)


def stufe():
    """Die Stufe dieses Prozesses: niedrig (Vorgabe), mittel oder hoch.

    Unbekannte Werte zaehlen als niedrig - ein Tippfehler darf nicht still die
    vierfache Position handeln.
    """
    wert = (os.environ.get("HANDEL_RISIKO") or "").strip().lower()
    return wert if wert in FAKTOREN else STANDARD


def faktor():
    """Der Zahlenfaktor dieser Stufe."""
    return FAKTOREN[stufe()]


def ist_basis():
    """True, wenn diese Stufe die unveraenderte ist (Faktor 1.0)."""
    return faktor() == 1.0


def suffix():
    """Dateinamen-Zusatz: "" in der Basis, sonst ".mittel"/".hoch"."""
    return "" if ist_basis() else "." + stufe()


def datei(pfad):
    """`.../zustand.json` -> `.../zustand.mittel.json` (Basis: unveraendert).

    Der Zustand MUSS getrennt liegen: zwei Laeufe auf derselben Datei wuerden
    sich die Positionen gegenseitig ueberschreiben.
    """
    s = suffix()
    if not s:
        return pfad
    basis, endung = os.path.splitext(pfad)
    return basis + s + endung


def skaliere(wachen):
    """Wachen-Kopie mit skalierten Betraegen. Aendert die Vorlage nicht.

    Ohne Wirkung in der Basis (Faktor 1.0) - dann kommt die Vorlage selbst
    zurueck, damit ein Vergleichstest "unveraendert" das auch sieht.
    """
    f = faktor()
    if f == 1.0 or not isinstance(wachen, dict):
        return wachen
    aus = dict(wachen)
    for feld in SKALIEREN:
        if feld in NIE_SKALIEREN:
            continue
        wert = aus.get(feld)
        if isinstance(wert, (int, float)) and not isinstance(wert, bool):
            aus[feld] = round(wert * f, 4)
    return aus


def lage():
    """Kurzbild fuer Doku, Tagesbericht und Systempruefung."""
    return {"stufe": stufe(), "faktor": faktor(),
            "suffix": suffix() or "(Basis)", "basis": ist_basis()}
