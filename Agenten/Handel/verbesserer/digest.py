"""TP5: der woechentliche LLM-Aufruf.

Das Modell *annotiert* nur - es priorisiert die Befunde und schreibt
Klartext-Lehren. Es fasst den Vorschlags-Diff nie an. Jeder Fehler und
``modus == "aus"`` fuehren dazu, dass ``uebersprungen`` gesetzt ist und die
Textfelder leer bleiben; der Vorschlag bleibt in jedem Fall vollstaendig
gueltig.

``erzeuge`` baut den Prompt, ruft das Modell (ueber ``ruf`` ueberschreibbar,
sonst ``_ruf_http``) und teilt die Antwort an einer ``LEHREN:``- bzw.
``## Lehren``-Marke in ``empfehlungen`` und ``lehren``.

``annotiere_bericht`` setzt den Abschnitt ``## Priorisierte Empfehlungen
(LLM)`` vorn in eine bestehende ``bericht.md`` (nach der ersten ``#``-Zeile).
``haenge_lehren_an`` haengt einen datierten Block an
``Werkstatt/handelslehren-eingang.md`` an.

Nur Standardbibliothek (``urllib`` fuer HTTP).
"""

import json
import os
import re
import urllib.request
from pathlib import Path

# Marke, an der die Modellantwort in Empfehlungen / Lehren zerfaellt.
_MARKE = re.compile(r"\n?[ \t]*(?:LEHREN:|##[ \t]*Lehren\b)[ \t]*:?", re.IGNORECASE)


# --- Prompt ---------------------------------------------------------------

def _prompt(befund, basis_wf, kandidat_wf, aenderungen, fast_kandidat=None):
    """Deutscher, knapper Prompt: nennt die Befunde, netto_gv_je_runde
    vorher/nachher, die geaenderten Schluessel und - falls die Basis unter
    20 Runden hat - den ausdruecklichen 'nicht anfassen'-Hinweis."""
    b = (basis_wf or {}).get("gesamt", {})
    k = (kandidat_wf or {}).get("gesamt", {}) if kandidat_wf else {}
    zeilen = [
        "Du bewertest den woechentlichen Vorschlag des Handels-Verbesserers.",
        "Antworte knapp und auf Deutsch.",
        "",
        "Befunde aus dem Journal:",
    ]
    befunde = befund.get("befunde") or []
    for f in befunde:
        zeilen.append(
            "- %s = %s: n = %s, mittleres GuV %s" % (
                f.get("merkmal", "?"), f.get("auspraegung", "?"),
                f.get("n", "?"), f.get("mittel_gv", "?")))
    if not befunde:
        zeilen.append("- (keine)")
    zeilen += [
        "",
        "netto_gv_je_runde (OOS-Aggregat): vorher %s, nachher %s" % (
            b.get("netto_gv_je_runde", "?"),
            k.get("netto_gv_je_runde", "kein Kandidat") if k
            else "kein Kandidat"),
        "Geaenderte wachen.json-Schluessel: %s" % (
            ", ".join(aenderungen.keys()) if aenderungen else "(keine)"),
        "",
        "Gib 2 bis 4 priorisierte Empfehlungen als nummerierte Liste.",
        "Danach eine eigene Zeile, die mit 'LEHREN:' beginnt und 1 bis 3 "
        "Klartext-Saetze enthaelt.",
    ]
    if b.get("n", 0) < 20:
        zeilen.append(
            "Wichtig: Die Basis hat nur %s Runden (< 20). Rate ausdruecklich "
            "dazu, die Parameter vorerst nicht anzufassen." % b.get("n", 0))
    if fast_kandidat:
        zeilen.append(
            "Hinweis: Ein Kandidat schlug die Basis in der Suche, fiel aber im "
            "Holdout durch - deshalb kein Vorschlag. Nur annotieren, nicht "
            "anwenden.")
    return "\n".join(zeilen)


# --- HTTP-Aufruf --------------------------------------------------------

def _ruf_http(prompt, konf):
    """Standard-Aufruf. ``modus == "ollama"`` -> POST ``{url}/api/generate``;
    ``modus == "cliproxy"`` -> POST ``{base_url}/v1/chat/completions`` mit
    ``Authorization: Bearer``. Nur ``urllib``. In den Tests nie erreicht -
    dort wird ``ruf`` gesetzt."""
    modus = konf.get("modus", "aus")
    timeout = konf.get("timeout_s", 60)
    if modus == "ollama":
        o = konf["ollama"]
        rumpf_daten = {"model": o["modell"], "prompt": prompt, "stream": False}
        # think:false ist Pflicht: Reasoning-Modelle liefern sonst leeren content.
        if "think" in o:
            rumpf_daten["think"] = o["think"]
        rumpf = json.dumps(rumpf_daten).encode("utf-8")
        anfrage = urllib.request.Request(
            o["url"].rstrip("/") + "/api/generate", data=rumpf,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
        return daten.get("response", "")
    if modus == "cliproxy":
        c = konf["cliproxy"]
        basis = os.environ[c["base_url_env"]].rstrip("/")
        schluessel = os.environ[c["schluessel_env"]]
        rumpf = json.dumps({
            "model": c["modell"],
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        anfrage = urllib.request.Request(
            basis + "/v1/chat/completions", data=rumpf,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + schluessel})
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
        return daten["choices"][0]["message"]["content"]
    raise ValueError("unbekannter LLM-Modus: " + str(modus))


def _trenne(text):
    """Antworttext an der ersten ``LEHREN:``/``## Lehren``-Marke teilen. Keine
    Marke -> alles in ``empfehlungen``, ``lehren`` leer."""
    teile = _MARKE.split(text, maxsplit=1)
    if len(teile) == 1:
        return text.strip(), ""
    return teile[0].strip(), teile[1].strip()


# --- oeffentliche API ---------------------------------------------------

def erzeuge(befund, basis_wf, kandidat_wf, aenderungen, llm_konf, ruf=None,
            fast_kandidat=None):
    """``{"empfehlungen": str, "lehren": str, "uebersprungen": str | None}``.

    ``modus == "aus"`` oder jeder Fehler im Aufruf -> ``uebersprungen``
    gesetzt, beide Textfelder leer.
    """
    if not isinstance(llm_konf, dict):
        return {"empfehlungen": "", "lehren": "",
                "uebersprungen": "LLM-Modus aus"}
    modus = llm_konf.get("modus", "aus")
    if modus == "aus":
        return {"empfehlungen": "", "lehren": "",
                "uebersprungen": "LLM-Modus aus"}
    ruf = ruf or _ruf_http
    try:
        text = ruf(_prompt(befund, basis_wf, kandidat_wf, aenderungen,
                           fast_kandidat), llm_konf)
        # Eine fehlgeformte ``ruf``-Rueckgabe (z. B. ein roher JSON-Rumpf
        # statt des extrahierten Textes) gilt als Fehlschlag: der leere Fall
        # bleibt leer, alles andere Nicht-String loest die except-Zweig aus.
        if text and not isinstance(text, str):
            raise TypeError("ruf lieferte keinen Text: " + type(text).__name__)
        empfehlungen, lehren = _trenne(str(text or ""))
    except Exception as e:  # noqa: BLE001 - jeder Fehler laesst den Vorschlag gueltig
        return {"empfehlungen": "", "lehren": "",
                "uebersprungen": "LLM nicht erreichbar: " + str(e)}
    return {"empfehlungen": empfehlungen, "lehren": lehren,
            "uebersprungen": None}


def annotiere_bericht(bericht_pfad, ergebnis):
    """``## Priorisierte Empfehlungen (LLM)`` mit dem Empfehlungstext (oder,
    wenn ``ergebnis["uebersprungen"]`` gesetzt ist, mit dieser Notiz) direkt
    nach der ersten ``#``-Zeile in ``bericht_pfad`` einsetzen."""
    pfad = Path(bericht_pfad)
    text = pfad.read_text(encoding="utf-8")
    if ergebnis.get("uebersprungen"):
        koerper = ergebnis["uebersprungen"]
    else:
        koerper = ergebnis.get("empfehlungen") or "(keine Empfehlungen)"
    block = "\n## Priorisierte Empfehlungen (LLM)\n\n" + koerper + "\n"
    zeilen = text.splitlines(keepends=True)
    einf = 0
    for i, z in enumerate(zeilen):
        if z.lstrip().startswith("#"):
            einf = i + 1
            break
    zeilen.insert(einf, block)
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        f.write("".join(zeilen))


def haenge_lehren_an(pfad, lehren, datum):
    """Datierten ``## <datum>``-Block an ``pfad`` anhaengen; Datei (und
    Elternordner) anlegen, falls noetig."""
    p = Path(pfad)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n## %s\n\n%s\n" % (datum, lehren))
