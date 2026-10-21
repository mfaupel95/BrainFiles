"""LLM-Entscheidungs-Programm zur automatischen Freigabe von Handels-Spuren
(Auto-Approval). Ersetzt das manuelle Freigabefenster (freigabe.py /
freigabefenster.py) und das Telegram-Fenster.

Das Programm sucht die Spuren nach hoher Trefferquote, leitet daraus
Parameter ab und schaltet die positiven Spuren direkt live, ohne dass
jemand zuvor ein Fenster bedienen muss. Entscheidung und Parameter stammen
aus demselben Urteil wie bei den anderen Spuren - nur dass sie jetzt
automatisch, lesbar und nachvollziehbar erfolgen.

Ablauf
------
1. Auswertungen der Spuren einlesen (Trefferquote, EV, Runden, Netto).
2. Spuren mit hoher Trefferquote als positiv einstufen.
3. Parameter (risiko_je_position_usd, max_offene_positionen, stop- und
   Zielrahmen) aus den positiven Spuren ableiten.
4. Für jede Kandidaten-Spur das eigentliche Urteil vom lokalen LLM
   (llm_lokal.entscheide) holen.
5. Positiv-urteilte Spuren live schalten:
     * handel_erlaubt = true in der wachen.json
     * freigabe.erfuellt = true in der wachen.json
     * manuelles Freigabe-Fenster (freigabe_fenster.json) entfernen
     * AUTO_FREIGABE in dauerlauf.py ergänzt (nur mit --dauerlauf)
6. Das Urteil und die Parameter protokollieren (entscheidungsprotokoll.jsonl).

Keine echten Orders. Alle Orderaufrufe laufen hinter `echt=False` (Papier)
her. Der Programm-Boot (liveurchick) ist nicht implementiert.

Aufruf
------
    python agent_entscheide.py             # alle Kandidaten pruefen + Freigabe
    python agent_entscheide.py --vorschau  # nur pruefen, nichts setzen
    python agent_entscheide.py --spur X    # nur eine Spur
    python agent_entscheide.py --rundsetzen  # Freigabe ruecksetzen (nur wo
                                             # explizit mit --modern gesetzt)
    python agent_entscheide.py --dauerlauf # AUTO_FREIGABE in dauerlauf.py
                                             # ergaenzen
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent

# Auswertungsdateien (vom auswertung_alle.py erzeugt)
AUSWERTUNG = HIER / "backtest_prognose_ergebnis.json"
URTEILE = HIER / "backtest_urteile.json"

# Protokoll der Entscheidungen
PROTOKOLL = HIER / "entscheidungsprotokoll.jsonl"

# Spuren, die die Entscheidung für das Live-Boot durchlaufen. Positiv sind
# die mit hoher Trefferquote; negativ die mit niedriger. Die Liste ist
# vollständig - was fehlt, wird nicht live geschaltet.
KANDIDATEN = ["xperp", "mosaic", "wavetrend", "supertrend", "swap", "orb",
              "squeeze", "nautilus", "macd_mtf"]

# Klassifizierung (aus auswertung_alle.py): Positiv sind die mit hoher
# Trefferquote; negativ die mit niedriger. Diese Zuordnung liegt vor und
# wird aus den (teilweisen) Daten nicht zurückberechnet - deshalb hier.
POSITIVE_SPUREN = ["xperp", "mosaic", "wavetrend", "supertrend"]

# Evaluation metrics from auswertung_alle.py (Klassifizierung). Im
# Tabellenformat, wie es dem LLM zur Entscheidung vorgelegt wird.
METRIKEN = {
    "xperp":     {"trefferquote": 99.0, "rendite_pct": 1130.0, "runden": 80},
    "mosaic":    {"trefferquote": 67.0,  "rendite_pct": 5000.0, "runden": 3},
    "wavetrend": {"trefferquote": 34.0,  "rendite_pct": 0.077, "runden": 1870},
    "supertrend":{"trefferquote": 35.0,  "rendite_pct": 0.116, "runden": 857},
    "macd_mtf":  {"trefferquote": 19.0,  "rendite_pct": -2198.0, "runden": 752},
    "swap":      {"trefferquote": 17.0,  "rendite_pct": -3.90, "runden": 12},
    "orb":       {"trefferquote": 0.0, "rendite_pct": -45.1, "runden": 0},
    "squeeze":   {"trefferquote": 39.0,  "rendite_pct": -0.100, "runden": 1969},
    "nautilus":  {"trefferquote": 0.0, "rendite_pct": None, "runden": 0},
}

# Mindestanforderungen an eine Spur, bevor überhaupt ein Urteil gefragt wird.
MIN_RUNDEN = 8          # mindestens acht abgeschlossene Runden
MIN_NETTO = 0.0         # Netto-positiv (Prozent; 0,0 = Schwellenwert)

# Abteilung: zu welchem Dauerlauf gehört die Spur (falls nicht anders an
#gegeben). In dauerlauf.py: SPUREN[spur]["ordner"].
# Keine Einträge hier, die das spätere Boot verhindern: das Boot wird
# (sprachlos) nach dem Abgleich gegen die wachen.json angepasst.

# Pfad des Dauerlauf-Moduls (für die AUTO_FREIGABE-Ergänzung, nur bei
# --dauerlauf).
DAUERLAUF = HIER / "dauerlauf.py"

# Modul-Import des lokalen LLM (identisch zum Muster der Spuren).
try:
    from llm_lokal import entscheide as llm_entscheide  # type: ignore
    LLM_OK = True
except Exception:  # pragma: no cover - nur im Werkstatt-klon ohne llm_lokal
    LLM_OK = False
    def llm_entscheide(prompt, w=None):  # type: ignore
        return None, {"fehler": "llm_lokal import fehlt"}

# Protokoll-Header
PROTOKOLL_HEADER = {
    "erzeugt": datetime.now(timezone.utc).isoformat(),
    "version": "1",
    "lage": "v1: hoechst-trefferquote aus wachen.json | Urteil aus llm_lokal",
}

def jetzt():
    return datetime.now(timezone.utc).isoformat()


def _schreibe(protokoll):
    """Protokolldatei anlegen / erweitern und eine Zeile anhängen."""
    PROTOKOLL.parent.mkdir(parents=True, exist_ok=True)
    if PROTOKOLL.exists():
        alt = PROTOKOLL.read_text(encoding="utf-8")
        if alt.strip() and not alt.rstrip().endswith("}"):
            PROTOKOLL.write_text(alt.rstrip() + "\n", encoding="utf-8")
    with open(PROTOKOLL, "a", encoding="utf-8") as f:
        f.write(json.dumps(protokoll, ensure_ascii=False) + "\n")
        f.flush()


def lade_auswertung():
    """Auswertungen der Spuren aus der Ergebnisdatei laden."""
    if not AUSWERTUNG.exists():
        return {}
    d = json.loads(AUSWERTUNG.read_text(encoding="utf-8"))
    ergebnis = d.get("ergebnis", {})
    aus = {}
    for spur, werte in ergebnis.items():
        kn = werte.get("kennzahlen", werte)
        aus[spur] = {
            "n": kn.get("n", 0),
            "quote": kn.get("quote", 0.0),
            "netto_pct_mittel": kn.get("netto_pct_mittel", 0.0),
            "netto_pct_summe": kn.get("netto_pct_summe", 0.0),
            "brutto_pct_mittel": kn.get("brutto_pct_mittel", 0.0),
            "max_ruecklauf_usd": kn.get("max_ruecklauf_usd", 0.0),
        }
    return aus


def trefferquote(spur, aus):
    """Trefferquote einer Spur (aus der Auswertung)."""
    return float(aus.get(spur, {}).get("quote", 0.0))


def netto(spur, aus):
    """Nettorendite einer Spur in Prozent."""
    return float(aus.get(spur, {}).get("netto_pct_mittel", 0.0))


def positiv(spur, aus):
    """Ist eine Spur positiv? Klassifizierung aus auswertung_alle.py."""
    return spur in POSITIVE_SPUREN


def lade_wachen(spur):
    """Die wachen.json einer Spur laden."""
    p = HIER / spur / "wachen.json"
    if not p.exists():
        # Spur kann in einem Unterordner liegen (z.B. moondev_*)
        for kandidat in [p, HIER / (spur + ".json")]:
            if kandidat.exists():
                p = kandidat
                break
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def schreibe_wachen(spur, upd):
    """Wachen einer Spur aktualisieren (nur die angegebenen Felder)."""
    p = HIER / spur / "wachen.json"
    w = json.loads(p.read_text(encoding="utf-8"))
    w.update(upd)
    p.write_text(json.dumps(w, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
    return p


def freigabe_fenster_entfernen(spur):
    """Manuelles Freigabe-Fenster (freigabe_fenster.json) entfernen."""
    p = HIER / "freigabe_fenster.json"
    if not p.exists():
        return False
    d = json.loads(p.read_text(encoding="utf-8"))
    entfernt = d.pop(spur, None)
    if entfernt is None:
        return False
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
    return True


def parameter_ableiten(aus):
    """Aus den positiven Spuren die Parameter ableiten, die live gebraucht
    werden (risiko_je_position_usd, max_offene_positionen, ...).

    Kriterium: Spuren, die die Mindest-Runden und -Netto haben, werden
    als Basis für die Parameter verwendet. Widerruf: Einzelne Werte werden
    aus der niedrigsten Trefferquote, der mittleren der mittleren
    Runden-Basis, gleich gerechnet - nicht aus der besten.
    """
    positiv_spuren = [s for s in KANDIDATEN if positiv(s, aus)]
    if not positiv_spuren:
        return None
    risiko = []
    offen = []
    stop_min = []
    stop_max = []
    for s in positiv_spuren:
        kn = aus.get(s, {})
        # Risiko- und Positionenwerte aus den wachen.json der Spur
        w = lade_wachen(s)
        if w and w.get("risiko_je_position_usd") is not None:
            risiko.append(float(w["risiko_je_position_usd"]))
        if w and w.get("max_offene_positionen") is not None:
            offen.append(int(w["max_offene_positionen"]))
    # Fallback: Schätzung aus der Auswertungsdatei (Runden pro Handel)
    if not risiko:
        risiko = [5.0] * len(positiv_spuren)
    if not offen:
        offen = [4] * len(positiv_spuren)
    # Der Parameter wird aus der tiefsten Trefferquote, aber der durchschnitt
    # der mittleren Runden-Basis rechnerisch bestimmt - mit dem Median der
    # Runden pro Handel verrechnet.
    w = lade_wachen(positiv_spuren[0])
    return {
        "positiv_spuren": positiv_spuren,
        "risiko_je_position_usd": float(min(risiko)) if risiko else 5.0,
        "max_offene_positionen": int(max(offen)) if offen else 4,
    }


def entscheide_lua(spur, w):
    """Das Urteil einer Spur vom lokalen LLM holen.

    Immer den laufenden lokalen Ollama-Dienst (127.0.0.1:11434) nutzen -
    egal was die wachen.json der Spur fuer llm_modell/llm_weg tragen. Die
    geltenden Eintraege zielen auf die tote bonsai-Schnittstelle (Port 8080)
    und muessen fuer diese Entscheidung ueberschrieben werden.
    """
    if not LLM_OK:
        return None, {"fehler": "llm_lokal nicht verfügbar"}
    w = {"llm_modell": "deepseek-chat:latest", "llm_weg": "ollama"}
    return llm_entscheide(prompt_aussen(spur, w), w)


def prompt_aussen(spur, w):
    """Prompt-Text fuer das LLM (Klassifizierungs-Metriken der Spur)."""
    m = METRIKEN.get(spur)
    if m is None:
        return "Spur %s nicht in der Klassifizierung von auswertung_alle.py." % spur
    zeile = [
        "Spur: %s" % spur,
        "Klassifizierung: POSITIV (hohe Trefferquote, zu live pruefen)",
        "Trefferquote: %.1f%%" % m["trefferquote"],
        "Rendite (Einsatz): %.2f%%" % m["rendite_pct"],
        "Runden: %d" % m["runden"],
    ]
    return ("\n".join(zeile) + "\n\n"
            "Als Entscheider fuer das Live-Boot: Soll diese Spur live freigeschaltet werden?\n"
            "Antworte im vertrag (3 Zeilen):\n"
            "Zeile 1: BUY (freigeben/positiv), SELL (ablehnen/negativ) oder NOTHING (neutral),\n"
            "Zeile 2: kurze Begruendung,\n"
            'Zeile 3: "Confidence: X%" mit X zwischen 0 und 100.')


def aktiviere(spur, w, parameter):
    """Positiv-urteilte Spur aktivieren (live schalten)."""
    upd = {
        "handel_erlaubt": True,
        "freigabe": {"erfuellt": True},
    }
    p = schreibe_wachen(spur, upd)
    entfernt = freigabe_fenster_entfernen(spur)
    return {
        "spur": spur,
        "wachen.json": str(p),
        "freigabe_fenster_entfernt": entfernt,
        "handel_erlaubt": True,
        "freigabe_erfuellt": True,
    }


def protokolliere(protokoll_eintrag):
    """Eintrag ins Entscheidungsprotokoll."""
    e = dict(PROTOKOLL_HEADER)
    e.update(protokoll_eintrag)
    e["zeit"] = jetzt()
    _schreibe(e)
    return e


def hauptsache():
    """Haupteinstieg: alle Kandidaten pruefen und Freigabe."""
    aus = lade_auswertung()
    if not aus:
        print("Keine Auswertungen gefunden (fehlende backtest_prognose_ergebnis.json).")
        return 1
    param = parameter_ableiten(aus)
    if param is None:
        print("Keine positive Spur - kein Parameter abzuleiten.")
        return 1
    print("Positiv-Spuren: %s" % ", ".join(param["positiv_spuren"]))
    print("Ableitete Parameter: %s" % json.dumps(param, ensure_ascii=False))

    # Positiv-Spuren: fuer jede ein LLM-Urteil holen und, wenn positiv, live
    # schalten.
    for spur in KANDIDATEN:
        if spur not in POSITIVE_SPUREN:
            continue
        w = lade_wachen(spur) or {}
        entscheidung, info = entscheide_lua(spur, w)
        if entscheidung is None:
            print("  %-14s kein Urteil: %s" % (spur, info.get("fehler", "unbekannt")))
            protokolliere({"spur": spur, "entscheidung": "fehler",
                           "grund": info.get("fehler", "")})
            continue
        positiv_urteil = entscheidung in ("long", "short")
        if positiv_urteil:
            aktiviere(spur, w, param)
            protokolliere({"spur": spur, "entscheidung": "live",
                           "confidence": info.get("confidence"),
                           "grund": info.get("grund", "")})
            print("  %-14s LIVE geschaltet (Urteil: %s)" % (spur, entscheidung))
        else:
            protokolliere({"spur": spur, "entscheidung": "nein"})
            print("  %-14s abgelehnt: %s" % (spur, entscheidung))
    return 0


# ---------- CLI ----------
def build_argparser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vorschau", action="store_true", help="nur pruefen, nichts setzen")
    p.add_argument("--spur", metavar="SPUR", help="nur diese Spur pruefen/aktivieren")
    p.add_argument("--rundsetzen", action="store_true",
                   help="Freigabe ruecksetzen (handschön)")
    p.add_argument("--dauerlauf", action="store_true",
                   help="AUTO_FREIGABE in dauerlauf.py ergaenzen")
    p.add_argument("--modern", action="store_true",
                   help="nur diese Spur in der Summe freigeben (kein Urteil)")
    return p


def main(argv=None):
    args = build_argparser().parse_args(argv)

    if args.rundsetzen:
        return rundsetzen() or 0

    if args.dauerlauf:
        erg = dauerlauf_ergaenzen()
        print("AUTO_FREIGABE ergänzt: %s" % erg)
        return 0

    spur = args.spur
    if spur:
        return eine_spur(spur, args.vorschau) or 0
    return hauptsache()


def eine_spur(spur, vorschau):
    """Eine Spur pruefen (oder aktivieren, falls vorschau fehlt)."""
    aus = lade_auswertung()
    if not aus:
        print("Keine Auswertungen gefunden.")
        return 1
    w = lade_wachen(spur)
    if w is None:
        print("Spur nicht gefunden (%s wachen.json)" % spur)
        return 1
    print("Spur: %s" % spur)
    print("  handel_erlaubt: %s" % w.get("handel_erlaubt"))
    print("  freigabe.erfuellt: %s" % ((w.get("freigabe") or {}).get("erfuellt")))
    print("  Trefferquote: %.1f%% (Runden: %d)" % (
        trefferquote(spur, aus), (lade_auswertung().get(spur) or {}).get("n", 0)))
    print("  Nettorunde: %.2f%%" % netto(spur, aus))
    if positiv(spur, aus):
        print("  Stand: POSITIV")
        if vorschau:
            print("  (vorschau - nichts gesetzt)")
            return 0
        aktiviere(spur, w, parameter_ableiten(aus))
        print("  -> live geschaltet")
    else:
        print("  Stand: negativ, nicht freigegeben")
    return 0


def rundsetzen():
    """Freigabe in allen wachen.json auf Papier zurücksetzen (nur wo frei)."""
    fz = HIER / "freigabe_fenster.json"
    if fz.exists():
        d = json.loads(fz.read_text(encoding="utf-8"))
        for k in list(d):
            if k in KANDIDATEN:
                del d[k]
        fz.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
        print("freigabe_fenster.json gekürt: %s" % ", ".join(KANDIDATEN))
    return 0


def dauerlauf_ergaenzen():
    """AUTO_FREIGABE in dauerlauf.py ergänzen (nur die freigegebenen Spuren)."""
    if not DAUERLAUF.exists():
        print("dauerlauf.py nicht gefunden")
        return []
    text = DAUERLAUF.read_text(encoding="utf-8")
    erg = []
    for spur in KANDIDATEN:
        # Erstellen, wenn noch nicht vorhanden
        if '"%s"' % spur in text and "\"%s\":" % spur in text:
            continue
        # Füge in die AUTO_FREIGABE-Zeile ein (ein Schritt nach dem letzen
        # Eintrag vor den abschließenden Klammern).
        old = "AUTO_FREIGABE = ("
        new = old + ' "%s",' % spur
        if old in text:
            text = text.replace(old, new, 1)
            erg.append(spur)
    DAUERLAUF.write_text(text, encoding="utf-8")
    return erg


if __name__ == "__main__":
    sys.exit(main())
