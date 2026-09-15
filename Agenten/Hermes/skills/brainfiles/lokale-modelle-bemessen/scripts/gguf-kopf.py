#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GGUF-Kopf lesen: Parameter, KV-Form, Gewichte je Quantisierungsstufe.

Aufruf:
    python gguf-kopf.py <datei.gguf>
    python gguf-kopf.py <datei.gguf> --kontext 8192

Es wird nur der Kopf gelesen (Metadaten + Tensorliste), nie die Tensorblobs -
das laeuft auch bei einer 15-GB-Datei in Sekunden. Die Gegenprobe rechnet die
Gewichte aus den Tensortypen gegen die echte Dateigroesse; weicht sie um mehr
als ~1 % ab, stimmt das Bit-Modell fuer diese Stufe nicht.

Nur Standardbibliothek - kein llama.cpp, kein Torch noetig.
"""

import argparse
import os
import struct
import sys

GIB = 1024.0 ** 3
MIB = 1024.0 ** 2

# GGML-Typ -> (Elemente je Block, Bytes je Block). Daraus die echten Bits je
# Parameter, statt sie zu schaetzen: Q4_K_M ist nicht 4,0 Bit, sondern 4,85.
TYPEN = {
    0: (1, 4), 1: (1, 2), 2: (32, 18), 3: (32, 20), 6: (32, 22), 7: (32, 24),
    8: (32, 34), 9: (32, 36), 10: (256, 84), 11: (256, 110), 12: (256, 144),
    13: (256, 176), 14: (256, 210), 15: (256, 292), 16: (256, 66),
    17: (256, 74), 18: (256, 98), 19: (256, 50), 20: (32, 18), 21: (256, 110),
    22: (256, 82), 23: (256, 136), 24: (1, 1), 25: (1, 2), 26: (1, 4),
    27: (1, 8), 28: (1, 8), 29: (256, 56), 30: (1, 2), 34: (256, 54),
    35: (256, 66),
}
NAMEN = {
    0: "F32", 1: "F16", 2: "Q4_0", 3: "Q4_1", 6: "Q5_0", 7: "Q5_1",
    8: "Q8_0", 9: "Q8_1", 10: "Q2_K", 11: "Q3_K", 12: "Q4_K", 13: "Q5_K",
    14: "Q6_K", 15: "Q8_K", 16: "IQ2_XXS", 17: "IQ2_XS", 18: "IQ3_XXS",
    19: "IQ1_S", 20: "IQ4_NL", 21: "IQ3_S", 22: "IQ2_S", 23: "IQ4_XS",
    24: "I8", 25: "I16", 26: "I32", 27: "I64", 28: "F64", 29: "IQ1_M",
    30: "BF16", 34: "TQ1_0", 35: "TQ2_0",
}

# Praktische Bitwerte je Stufe (Matrizen auf die Stufe, 1-D-Tensoren F16).
STUFEN = [
    ("BF16", 16.0), ("Q8_0", 8.5), ("Q6_K", 6.5625), ("Q5_K_M", 5.65),
    ("Q4_K_M", 4.85), ("Q3_K_M", 3.95), ("IQ3_XXS", 3.0625), ("Q2_K", 2.75),
]

# Bytes je KV-Element: F16 2,0 | Q8_0 1,0625 | Q4_0 0,5625
KV_BYTES = [("F16", 2.0), ("Q8_0", 1.0625), ("Q4_0", 0.5625)]
KONTEXTE = [4096, 8192, 16384, 32768]


def bits(typ):
    e = TYPEN.get(typ)
    return (e[1] * 8.0 / e[0]) if e else 0.0


class Leser:
    """Minimaler Leser fuer den GGUF-Kopf (v2/v3)."""

    def __init__(self, f):
        self.f = f

    def roh(self, n):
        d = self.f.read(n)
        if len(d) != n:
            raise EOFError("Datei endet zu frueh")
        return d

    def u32(self):
        return struct.unpack("<I", self.roh(4))[0]

    def u64(self):
        return struct.unpack("<Q", self.roh(8))[0]

    def text(self):
        return self.roh(self.u64()).decode("utf-8", "replace")

    def wert(self, t):
        if t == 0:
            return self.roh(1)[0]
        if t == 1:
            return struct.unpack("<b", self.roh(1))[0]
        if t == 2:
            return struct.unpack("<H", self.roh(2))[0]
        if t == 3:
            return struct.unpack("<h", self.roh(2))[0]
        if t == 4:
            return self.u32()
        if t == 5:
            return struct.unpack("<i", self.roh(4))[0]
        if t == 6:
            return struct.unpack("<f", self.roh(4))[0]
        if t == 7:
            return self.roh(1)[0] != 0
        if t == 8:
            return self.text()
        if t == 9:
            et, n = self.u32(), self.u64()
            # Tokenizer-Vokabulare sind gross (262k+), aber nicht beliebig.
            if n > 4000000:
                raise ValueError("Array zu gross (%d)" % n)
            return [self.wert(et) for _ in range(n)]
        if t == 10:
            return self.u64()
        if t == 11:
            return struct.unpack("<q", self.roh(8))[0]
        if t == 12:
            return struct.unpack("<d", self.roh(8))[0]
        raise ValueError("unbekannter Werttyp %d" % t)


def kopf(pfad):
    """(version, meta, [(dims, elemente, typ)]) - ohne die Tensorblobs."""
    with open(pfad, "rb") as f:
        r = Leser(f)
        if r.roh(4) != b"GGUF":
            raise ValueError("kein GGUF")
        version = r.u32()
        n_tensor, n_kv = r.u64(), r.u64()
        meta = {}
        for _ in range(n_kv):
            k = r.text()
            t = r.u32()
            try:
                v = r.wert(t)
            except ValueError as e:
                raise ValueError("bei %s: %s" % (k, e))
            # Tokenizer-Felder nur ueberlesen, nicht behalten (Speicher).
            if not k.startswith("tokenizer."):
                meta[k] = v
        tensoren = []
        for _ in range(n_tensor):
            r.text()
            nd = r.u32()
            dims = [r.u64() for _ in range(nd)]
            typ = r.u32()
            r.u64()
            nel = 1
            for d in dims:
                nel *= d
            tensoren.append((dims, nel, typ))
    return version, meta, tensoren


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("datei")
    p.add_argument("--kontext", type=int, default=8192,
                   help="Kontext fuer die KV-Rechnung (Vorgabe 8192)")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    version, meta, ts = kopf(a.datei)
    groesse = os.path.getsize(a.datei)
    arch = str(meta.get("general.architecture", "?"))

    def w(s):
        return meta.get("%s.%s" % (arch, s), meta.get(s))

    params = sum(n for _, n, _ in ts)
    n_1d = sum(n for dims, n, _ in ts if len(dims) == 1)
    n_2d = sum(n for dims, n, _ in ts if len(dims) != 1)
    bit_summe = sum(bits(t) * n for _, n, t in ts)

    bloecke = w("block_count") or 0
    koepfe = w("attention.head_count") or 0
    kv_koepfe = w("attention.head_count_kv") or koepfe
    dmodel = w("embedding_length") or 0
    klaenge = w("attention.key_length") or (dmodel // koepfe if koepfe else 0)
    vlaenge = w("attention.value_length") or (dmodel // koepfe if koepfe else 0)

    print("Datei: %s" % os.path.basename(a.datei))
    print("  %.2f GB Datei | GGUF v%d | %d Tensoren"
          % (groesse / 1e9, version, len(ts)))
    print("  Architektur %s | %s"
          % (arch, str(meta.get("general.name", "?"))[:60]))
    print("  Parameter: %.3f Mrd" % (params / 1e9))
    print("    %.3f Mrd in 2-D-Matrizen, %.3f Mrd in 1-D-Tensoren"
          % (n_2d / 1e9, n_1d / 1e9))
    print("    %d Bloecke | %d Koepfe, davon %d fuer KV | Kopf %d/%d"
          % (bloecke, koepfe, kv_koepfe, klaenge, vlaenge))
    print("    Trainings-Kontext: %s" % w("context_length"))
    print("  effektiv %.2f Bit je Parameter (aus den echten Tensortypen)"
          % (bit_summe / params))
    print("  Gegenprobe: %.2f GB gerechnet gegen %.2f GB Datei (%+.2f %%)"
          % (bit_summe / 8.0 / 1e9, groesse / 1e9,
             100.0 * (groesse - bit_summe / 8.0) / max(bit_summe / 8.0, 1.0)))

    print()
    print("Gewichte je Stufe (Vorhersage)")
    for name, b in STUFEN:
        print("  %-10s %9.2f GiB" % (name, (n_2d * b / 8.0 + n_1d * 2.0) / GIB))

    print()
    print("KV-Cache")
    print("  je Token F16: %.4f MiB"
          % (bloecke * kv_koepfe * (klaenge + vlaenge) * 2.0 / MIB))
    print("  %-9s" % "Kontext" + "".join("%13s" % n for n, _ in KV_BYTES))
    for ctx in KONTEXTE:
        zeile = "  %-9d" % ctx
        for _, by in KV_BYTES:
            zeile += "%10.2f GiB" % (
                bloecke * kv_koepfe * (klaenge + vlaenge) * ctx * by / GIB)
        print(zeile)

    kv = bloecke * kv_koepfe * (klaenge + vlaenge) * a.kontext * KV_BYTES[1][1] / GIB
    print()
    print("Gewichte + KV bei Kontext %d (KV als %s: %.2f GiB)"
          % (a.kontext, KV_BYTES[1][0], kv))
    for name, b in STUFEN:
        g = (n_2d * b / 8.0 + n_1d * 2.0) / GIB
        print("  %-10s %6.2f + %5.2f = %6.2f GiB" % (name, g, kv, g + kv))


if __name__ == "__main__":
    main()
