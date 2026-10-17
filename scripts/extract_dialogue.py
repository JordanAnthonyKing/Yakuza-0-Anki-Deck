"""Extract ordered Japanese dialogue lines per chapter from the msg files.

Output: data/dialogue_by_chapter.json = { "1": [ {uid, seq, speaker, line}, ... ], ... }
Ordering: by UID (story order), then by run sequence within the file.
Filtering: keep runs that look like real spoken lines (contain JP + sentence punctuation or length),
drop Talk_ tags, ascii noise, and obvious menu/system prompts.
"""
import os, re, glob, json, collections
from msg_speakers import messages

WDR_MSG = r"C:\Users\jordan\repos\yakuza\source\wdrj\msg"
ASSIGN  = r"C:\Users\jordan\repos\yakuza\data\chapter_assignment.json"
OUT     = r"C:\Users\jordan\repos\yakuza\data\dialogue_by_chapter.json"

JP    = re.compile(r"[぀-ヿ一-龯]")
PUNCT = re.compile(r"[。！？…」』）　]")
NOISE = re.compile(r"^(Talk|MOT|MTN|face|cam|ROOM|EVENT|se_|vo_|bgm)", re.I)
# common menu/system prompts to drop from MAIN-STORY extraction
MENU = set("やめる 放っておく 止めに入る セーブする 調べる 話しかける はい いいえ 続ける やめておく".split())

assign = {a["uid"]: a for a in json.load(open(ASSIGN, encoding="utf-8"))}

DEBUG = re.compile(r"(bot|フラグ|チェック用|座標|手ぶれ|配置|テスト|震度|ＯＦＦ|ＯＮ)")

def parse_lines(path):
    d = open(path, "rb").read()
    text = d.decode("utf-8", "replace")
    # skip whole file if it's developer debug/test content
    if DEBUG.search(text) and len(DEBUG.findall(text)) >= 3:
        return [], None
    runs = re.split(r"[\x00-\x1f�]+", text)
    lines, speaker = [], None
    for r in runs:
        r = r.strip()
        if not r or NOISE.match(r):
            continue
        if not JP.search(r):
            continue
        # short JP with no sentence punctuation -> candidate speaker/name or menu
        if len(r) <= 6 and not PUNCT.search(r):
            cand = re.sub(r"[（）「」『』\(\)\s]", "", r)
            if cand and cand not in MENU:
                speaker = cand       # remember most recent name-like token
            continue
        if r in MENU:
            continue
        r = re.sub(r"<[^>]*>", "", r).strip()   # strip in-game control codes e.g. <Color:7>
        if r:
            lines.append(r)
    return lines, speaker

by_ch = collections.defaultdict(list)
files = glob.glob(os.path.join(WDR_MSG, "**", "*.msg"), recursive=True)
for p in files:
    uid = re.search(r"uid([0-9a-f]{8})", os.path.basename(p)).group(1)
    a = assign.get(uid)
    if not a or not a.get("chapter"):
        continue
    lines, _ = parse_lines(p)
    # per-line speaker from the message's own speaker command (the old file-wide
    # last-name guess was wrong for most lines); "" when no message record holds the line
    msgs = [(re.sub(r"<[^>]*>|\s", "", t), s) for t, s in messages(p)]
    for i, ln in enumerate(lines):
        key = re.sub(r"\s", "", ln)
        speaker = next((s for t, s in msgs if key and key in t), "")
        by_ch[a["chapter"]].append(dict(uid=uid, seq=i, speaker=speaker, line=ln))

# sort each chapter by uid then seq
for ch in by_ch:
    by_ch[ch].sort(key=lambda x: (x["uid"], x["seq"]))

json.dump(by_ch, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("chapters:", sorted(by_ch, key=int))
for ch in sorted(by_ch, key=int):
    print(f"  ch{int(ch):02}: {len(by_ch[ch])} lines")
print("\n---- Chapter 1, first 20 lines in game order ----")
for row in by_ch[1][:20]:
    sp = f"[{row['speaker']}] " if row['speaker'] else ""
    print(f"  {row['uid']}  {sp}{row['line'][:60]}")
