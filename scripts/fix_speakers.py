"""Re-attribute the speaker of every card in cards_ch{N}_{N}.json from the .msg speaker
commands (msg_speakers.py), replacing the old file-wide last-name guess.

Only the `speaker` field changes, in place, so it is safe for the FROZEN cards_ch1_1.json
(orders, words and translations are untouched; note GUIDs key on Sentence+Word).
Cards whose message carries no speaker command get "" (blank beats wrong).

Usage: python fix_speakers.py <ch> [<ch> ...] [--write]   (dry run without --write)
"""
import os, re, sys, json, glob, collections
from msg_speakers import messages
from build_deck import DATA

SRC = r"C:\Users\jordan\repos\yakuza\source\wdrj\msg"
uid2path = {re.search(r"uid([0-9a-f]{8})", os.path.basename(p)).group(1): p
            for p in glob.glob(os.path.join(SRC, "**", "*.msg"), recursive=True)}
_cache = {}

def norm(s):
    s = re.sub(r"<[^>]*>", "", s)
    return re.sub(r"[\s\u3000（）]", "", s)

def speaker_for(uid, sentence):
    if uid not in _cache:
        _cache[uid] = [(norm(t), s) for t, s in messages(uid2path[uid])] if uid in uid2path else []
    sn = norm(sentence)
    hit = next((s for t, s in _cache[uid] if sn and sn in t), None)
    return hit

write = "--write" in sys.argv
for ch in [int(a) for a in sys.argv[1:] if a.isdigit()]:
    path = os.path.join(DATA, f"cards_ch{ch}_{ch}.json")
    cards = json.load(open(path, encoding="utf-8"))
    stats, changes = collections.Counter(), collections.Counter()
    for c in cards:
        if c.get("kind") == "label":                # speaker-descriptor cards: sentence IS the label
            stats["label card (kept)"] += 1
            continue
        new = speaker_for(c["uid"], c["sentence"])
        if new is None:
            # no message record: either the "sentence" is itself a speaker label the old
            # extractor kept as a line (気弱そうな学生), or a line embedded outside the
            # record table — the old file-wide guess is unreliable either way
            stats["no msg record -> blank"] += 1
            new = ""
        old = c.get("speaker") or ""
        stats["same" if new == old else ("now blank" if not new else "changed")] += 1
        if new != old:
            changes[(old, new)] += 1
            c["speaker"] = new
    print(f"Ch{ch}: {dict(stats)}")
    print("   top changes:", ", ".join(f"{o or '-'}→{n or '-'} ×{k}" for (o, n), k in changes.most_common(8)))
    if write:
        json.dump(cards, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("   written", path)
