"""Parse Yakuza 0 .msg files and map the UID space to content types / chapters.

A .msg is: header + offset table(s) + a set of UTF-8 strings (null/control separated).
Strings fall into buckets:
  - dialogue    : contains Japanese (kana/kanji), not an emotion/scene tag
  - speaker     : short Japanese name appended (often after dialogue) -- heuristic
  - talk_tag    : ASCII like 'Talk_Sad', 'Talk_Yes' (portrait/emotion)
  - scene_code  : ASCII like 'c01_160' (cutscene) or 'a01_010' (adventure)
  - other_ascii : short binary-ish ascii noise
"""
import os, re, glob, collections

WDR_MSG = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj\msg"

JP = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
SCENE = re.compile(r"^[abcf][0-9]{2}[_-][0-9]{3}$", re.I)
TALKTAG = re.compile(r"^(Talk_|MOT_|face_|MTN_|ROOM_|EVENT|cam_)", re.I)

def parse(path):
    data = open(path, "rb").read()
    # split into printable/text runs on control bytes (< 0x20 except keep none)
    text = data.decode("utf-8", "replace")
    runs = re.split(r"[\x00-\x1f�]+", text)
    runs = [r for r in runs if len(r) >= 1]
    dialogue, speakers, talktags, scenes, other = [], [], [], [], []
    for r in runs:
        if SCENE.match(r):
            scenes.append(r.lower())
        elif TALKTAG.match(r):
            talktags.append(r)
        elif JP.search(r):
            # Japanese-bearing. Long -> dialogue; very short -> maybe speaker name
            if len(r) <= 6 and not re.search(r"[。、！？…]", r):
                speakers.append(r)
            else:
                dialogue.append(r)
        else:
            if 3 <= len(r) <= 40 and re.match(r"^[\x20-\x7e]+$", r):
                other.append(r)
    return dict(scenes=scenes, dialogue=dialogue, speakers=speakers, talktags=talktags, other=other)

def main():
    files = glob.glob(os.path.join(WDR_MSG, "**", "*.msg"), recursive=True)
    by_hi = collections.defaultdict(lambda: dict(n=0, jp=0, scene=0, chapters=set(), scenes=set()))
    total_jp = 0
    chap_files = collections.Counter()   # chapter -> #msg files carrying that chapter code
    for p in files:
        uid = re.search(r"uid([0-9a-f]{8})", os.path.basename(p)).group(1)
        hi = uid[:4]           # top 16 bits, e.g. '0033'
        r = parse(p)
        g = by_hi[hi]
        g["n"] += 1
        has_jp = bool(r["dialogue"] or r["speakers"])
        if has_jp: g["jp"] += 1; total_jp += 1
        if r["scenes"]:
            g["scene"] += 1
            chaps = set()
            for s in r["scenes"]:
                g["scenes"].add(s)
                m = re.match(r"[abcf]([0-9]{2})", s)
                if m: chaps.add(int(m.group(1))); g["chapters"].add(int(m.group(1)))
            for c in chaps: chap_files[c]+=1
    print(f"total msg files: {len(files)}, files with JP: {total_jp}\n")
    print(f"{'uidHI':6} {'files':>5} {'JP':>5} {'w/scene':>7}  chapters(if any)")
    for hi in sorted(by_hi):
        g = by_hi[hi]
        ch = ",".join(str(c) for c in sorted(g["chapters"])) if g["chapters"] else ""
        print(f"{hi:6} {g['n']:5} {g['jp']:5} {g['scene']:7}  {ch}")
    print("\nmain-story cutscene coverage (msg files carrying each chapter's c-code):")
    for c in range(1,18):
        print(f"  chapter {c:2}: {chap_files.get(c,0)} files")

if __name__ == "__main__":
    main()
