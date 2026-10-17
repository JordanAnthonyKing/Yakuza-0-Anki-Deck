"""How redundant is Chapter 0 (system/UI terms) with the rest of the game?

For each Chapter-0 term, check whether its lemma also appears in the REST of the
game's text (every other .msg dialogue run -- main story + substories), i.e. would a
learner meet it anyway later. Also split by the narrow "core UI/combat" set (option 1)
vs the broader minigame vocab, and report coverage within each bucket.
"""
import os, re, glob, json, collections
import fugashi
from build_deck import DATA, CONTENT_POS, SKIP_POS2, STOPLEMMA, kata2hira, load_jmdict

SRC = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"
JP = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")

tagger = fugashi.Tagger()

def lemmas_of(line, jm=None, known_w=None, known_r=None):
    """Content-word lemmas of a line, matching build_deck's normalization. If jm/known
    are given, apply the same known/JMdict filters build_deck used to form ch0 words."""
    out = []
    for t in tagger(line):
        if t.feature.pos1 not in CONTENT_POS or t.feature.pos2 in SKIP_POS2:
            continue
        lemma = t.feature.lemma or t.surface
        lemma = re.sub(r"-.*$", "", lemma)
        reading = kata2hira(t.feature.kana or "")
        if lemma in STOPLEMMA:
            continue
        if known_w is not None and (lemma in known_w or reading in known_r):
            continue
        if jm is not None and lemma not in jm:
            continue
        out.append(lemma)
    return out

# ---- Chapter-0 words (already filtered) ----
cards0 = json.load(open(os.path.join(DATA, "cards_ch0_0.json"), encoding="utf-8"))
ch0_words = [c["word"] for c in cards0]
ch0_set = set(ch0_words)

# ---- narrow "core UI/combat" set (option 1): re-derive from the system lines ----
sys_lines = json.load(open(os.path.join(DATA, "system_by_chapter.json"), encoding="utf-8"))["0"]
sys_line_set = {r["line"] for r in sys_lines}
known = json.load(open(os.path.join(DATA, "known_words.json"), encoding="utf-8"))
known_w = set(known["words"]); known_r = set(known["readings"])
jm = load_jmdict()

CTRL   = re.compile("スティック|カーソル|十字キー|方向キー|トリガー|コントローラー|[ＬＲ][１２]")
NARROW = re.compile(
    "体力|回復|装備|武器|防具|ヒート|ゲージ|アクション|セーブ|ロード|メニュー|マップ|"
    "経験値|レベル|ダメージ|コンボ|必殺技|スキル|強化|素材|アイテム|所持金|所持品|"
    "攻撃|防御|ガード|回避|投げ|つかみ|技|習得|発動|操作|画面|耐久|威力|敵")
MENU = set("基本操作 戻る 次へ 前へ 決定 確認 所持品 詳細 装備する 強化する 選択 表示".split())

core_words = set()
for r in sys_lines:
    ln = r["line"]
    label = re.sub(r"[（）「」『』\(\)\s、。]", "", ln)
    if CTRL.search(ln) or NARROW.search(ln) or label in MENU:
        for lem in lemmas_of(ln, jm, known_w, known_r):
            core_words.add(lem)
core_words &= ch0_set                    # only count words that are actually ch0 cards
dropped = ch0_set - core_words           # terms option 1 would NOT include

# ---- REST-of-game corpus: all .msg dialogue runs that are NOT system lines ----
rest = collections.Counter()
files = glob.glob(os.path.join(SRC, "**", "*.msg"), recursive=True)
for p in files:
    text = open(p, "rb").read().decode("utf-8", "replace")
    for run in re.split(r"[\x00-\x1f�]+", text):
        run = re.sub(r"<[^>]*>", "", run).strip()
        if not run or not JP.search(run) or run in sys_line_set:
            continue
        for lem in lemmas_of(run):        # raw presence, no known/jmdict filter
            rest[lem] += 1

def coverage(words):
    seen  = [w for w in words if rest.get(w, 0) >= 1]
    seen2 = [w for w in words if rest.get(w, 0) >= 3]
    return seen, seen2

allseen, allseen2 = coverage(ch0_set)
dropseen, dropseen2 = coverage(dropped)

print(f"Chapter-0 terms: {len(ch0_set)}")
print(f"  appear elsewhere in game text (>=1x): {len(allseen)}  ({100*len(allseen)//len(ch0_set)}%)")
print(f"  appear repeatedly (>=3x):             {len(allseen2)}  ({100*len(allseen2)//len(ch0_set)}%)")
print(f"  UNIQUE to system/UI text (never else):{len(ch0_set)-len(allseen)}  ({100*(len(ch0_set)-len(allseen))//len(ch0_set)}%)\n")

print(f"Option 1 (core UI/combat) would KEEP:  {len(core_words)} terms")
print(f"Option 1 would DROP:                   {len(dropped)} terms")
print(f"  of those dropped, appear elsewhere (>=1x): {len(dropseen)}  ({100*len(dropseen)//max(1,len(dropped))}%)")
print(f"  of those dropped, UNIQUE to system text:   {len(dropped)-len(dropseen)}  ({100*(len(dropped)-len(dropseen))//max(1,len(dropped))}%)")

uniq_dropped = sorted(dropped - set(dropseen))
print(f"\nsample terms option 1 drops that appear NOWHERE else (would be lost):")
print("  " + "  ".join(uniq_dropped[:40]))
