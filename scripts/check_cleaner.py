import json, os
from build_deck import strip_orphan_brackets as f, DATA
c = json.load(open(os.path.join(DATA, "cards_ch1_1.json"), encoding="utf-8"))
ch = [(x["sentence"], f(x["sentence"])) for x in c if f(x["sentence"]) != x["sentence"]]
print(f"{len(ch)}/{len(c)} sentences changed")
for a, b in ch[:16]:
    print("  -", repr(a), "->", repr(b))
