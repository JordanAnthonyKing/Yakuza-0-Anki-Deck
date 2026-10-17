import json, os
DATA = r"C:\Users\jordan\repos\yakuza\data"
cards = json.load(open(os.path.join(DATA, "cards_ch1_1.json"), encoding="utf-8"))
pre = json.load(open(os.path.join(DATA, "pretaught_words.json"), encoding="utf-8"))
supp = set(pre["words"])                       # CORE+MINIGAME minus sense-divergent (the ones we WOULD suppress)
div = set(pre["sense_divergent"])              # intentionally allowed to reappear

ch1_words = [c["word"] for c in cards]
uniq = set(ch1_words)
overlap_supp = sorted(w for w in uniq if w in supp)        # redundant: should have been suppressed
overlap_div = sorted(w for w in uniq if w in div)          # intended reappearance -- fine
# count cards (not just unique) affected
cards_supp = [c for c in cards if c["word"] in supp]

print(f"Ch1: {len(cards)} cards, {len(uniq)} unique words")
print(f"pretaught suppress-set: {len(supp)} words; sense-divergent: {len(div)}")
print(f"OVERLAP with suppress-set: {len(overlap_supp)} unique words -> {len(cards_supp)} Ch1 cards that should NOT exist")
print(f"overlap with sense-divergent (intended, keep): {len(overlap_div)} -> {overlap_div}")
print("\nredundant words:", "  ".join(overlap_supp))
