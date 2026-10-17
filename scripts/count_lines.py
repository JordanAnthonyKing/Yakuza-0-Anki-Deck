import json, os
DATA = r"C:\Users\jordan\repos\yakuza\data"
d = json.load(open(os.path.join(DATA, "dialogue_by_chapter.json"), encoding="utf-8"))
ch = sorted(d, key=int)
tot = sum(len(d[c]) for c in ch)
for c in ch:
    print(f"  ch{int(c):2}: {len(d[c])} lines")
print("total lines:", tot, "| ch1 lines:", len(d["1"]), "| ch1 cards: 636")
