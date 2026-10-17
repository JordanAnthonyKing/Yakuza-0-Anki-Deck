import json, os
DATA = r"C:\Users\jordan\repos\yakuza\data"
cards = json.load(open(os.path.join(DATA, "cards_ch1_1.json"), encoding="utf-8"))
known = json.load(open(os.path.join(DATA, "known_words.json"), encoding="utf-8"))
kw, kr = set(known["words"]), set(known["readings"])
hitw = [c["word"] for c in cards if c["word"] in kw]
hitr = [c["word"] for c in cards if c["reading"] in kr]
print(f"known_words.json: {len(kw)} words, {len(kr)} readings")
print(f"Ch1 cards whose WORD is in known N5/N4 set: {len(hitw)}")
print(f"Ch1 cards whose READING is in known set:    {len(hitr)}  {hitr[:20]}")
