"""Compare a wdrj (JA) .msg with its wdr counterpart to identify wdr's language and
how well the string runs line up positionally. Usage: python compare_lang.py <relpath>
"""
import os, re, sys

BASE = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad"
JP  = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
LAT = re.compile(r"[A-Za-z]")

def runs(root, rel, want):
    p = os.path.join(BASE, root, rel)
    if not os.path.exists(p):
        return None
    text = open(p, "rb").read().decode("utf-8", "replace")
    out = []
    for r in re.split(r"[\x00-\x1f�]+", text):
        r = re.sub(r"<[^>]*>", "", r).strip()
        if r and want.search(r):
            out.append(r)
    return out

rel = sys.argv[1]
ja = runs("wdrj", rel, JP) or []
en = runs("wdr", rel, LAT) or []
print(f"JA runs: {len(ja)}   wdr Latin runs: {len(en)}\n")
n = max(len(ja), len(en))
for i in range(min(n, 20)):
    j = ja[i][:46] if i < len(ja) else ""
    e = en[i][:46] if i < len(en) else ""
    print(f"  [{i:2}] JA: {j:48} EN: {e}")
