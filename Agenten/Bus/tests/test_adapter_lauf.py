"""Test fuer adapter_lauf.py. Direkt ausfuehrbar: python tests/test_adapter_lauf.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import adapter_lauf as al   # noqa: E402


def test_aus_fehlend_lesbar():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.jsonl")
        open(p, "w").close()
        cfg = {"quellen": [
            {"name": "a", "typ": "nautilus", "enabled": False, "datei": p},
            {"name": "b", "typ": "nautilus", "enabled": True, "datei": os.path.join(d, "nein")},
            {"name": "c", "typ": "nautilus", "enabled": True, "datei": p}]}
        r = al.lauf(cfg, vorschau=True)
        assert [x[1] for x in r] == ["aus", "datei_fehlt", "lesbar"], r


def test_unbekannter_typ_ist_fehler_nicht_absturz():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x")
        open(p, "w").close()
        r = al.lauf({"quellen": [{"name": "z", "typ": "?", "enabled": True, "datei": p}]})
        assert r[0][1] == "fehler"


def test_konfig_der_repo_ist_gueltig():
    import json
    with open(os.path.join(al.HIER, "adapter_quellen.json"), encoding="utf-8") as f:
        c = json.load(f)
    assert c["mode"] in ("paper", "demo") and c["quellen"]


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            f()
    print("adapter_lauf bestanden")
