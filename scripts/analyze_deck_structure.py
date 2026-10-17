"""Recurrence analysis to decide (a) DEFER placement (fold into side-stories vs its own
minigame deck) and (b) whether pre-teaching Ch0/minigame words hurts later mining.

Buckets the whole .msg corpus:
  MAIN  = chapter-assigned files  -> main-story dialogue (per chapter)
  EXTRA = unassigned files, minus extracted system lines -> substory + minigame dialogue
          split into MINI (minigame-flavored) vs SUB (everything else = side-stories)
For each Chapter-0 candidate word, measure where/how often it recurs, plus a polysemy
signal (script type + #JMdict senses) to judge whether later contexts differ in MEANING.
"""
import os, re, glob, json, collections
import fugashi
from build_deck import DATA, CONTENT_POS, SKIP_POS2, STOPLEMMA, kata2hira, load_jmdict

SRC = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj\msg"
JP = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
KANJI = re.compile(r"[一-龯]")
tagger = fugashi.Tagger()

MINI = re.compile(
    "麻雀|将棋|花札|こいこい|チンチロ|ポーカー|ブラックジャック|バカラ|ルーレット|"
    "カジノ|カラオケ|ディスコ|ポケットサーキット|ポケサー|サーキット|テレクラ|"
    "キャバ|接客|嬢|ボウリング|ダーツ|ビリヤード|バッティング|クレーンゲーム|ＵＦＯ|"
    "釣り|撒き餌|メスキング|不動産|経営|物件|グラビア|撮影|水鉄砲|盤面|ちょんまげ")

def lemmas_of(line):
    out = []
    for t in tagger(line):
        if t.feature.pos1 not in CONTENT_POS or t.feature.pos2 in SKIP_POS2:
            continue
        lemma = re.sub(r"-.*$", "", t.feature.lemma or t.surface)
        if lemma in STOPLEMMA:
            continue
        out.append(lemma)
    return out

assign = {a["uid"]: a for a in json.load(open(os.path.join(DATA, "chapter_assignment.json"), encoding="utf-8"))}
sys_lines = json.load(open(os.path.join(DATA, "system_by_chapter.json"), encoding="utf-8"))["0"]
sys_line_set = {r["line"] for r in sys_lines}
cards0 = json.load(open(os.path.join(DATA, "cards_ch0_0.json"), encoding="utf-8"))
jm = load_jmdict()

# provisional KEEP/DEFER: a ch0 word is DEFER if its card's example sentence is minigame-flavored
prov = {}   # word -> 'DEFER'/'KEEP'
for c in cards0:
    prov[c["word"]] = "DEFER" if MINI.search(c.get("sentence", "")) else "KEEP"

# recurrence counters
main_first = {}                      # lemma -> earliest main-story chapter
main_cnt   = collections.Counter()   # lemma -> main-story occurrences
mini_cnt   = collections.Counter()
sub_cnt    = collections.Counter()

for p in glob.glob(os.path.join(SRC, "**", "*.msg"), recursive=True):
    m = re.search(r"uid([0-9a-f]{8})", os.path.basename(p))
    uid = m.group(1) if m else ""
    a = assign.get(uid)
    ch = a.get("chapter") if a else None
    text = open(p, "rb").read().decode("utf-8", "replace")
    for run in re.split(r"[\x00-\x1f�]+", text):
        run = re.sub(r"<[^>]*>", "", run).strip()
        if not run or not JP.search(run):
            continue
        if ch:                                   # MAIN story
            for lem in lemmas_of(run):
                main_cnt[lem] += 1
                if lem not in main_first or ch < main_first[lem]:
                    main_first[lem] = ch
        else:                                    # EXTRA (unassigned)
            if run in sys_line_set:
                continue
            bucket = mini_cnt if MINI.search(run) else sub_cnt
            for lem in lemmas_of(run):
                bucket[lem] += 1

def script(w): return "kana" if not KANJI.search(w) else "kanji"
def nsenses(w): return len(jm[w]["senses"]) if w in jm else 0

keep = [c["word"] for c in cards0 if prov[c["word"]] == "KEEP"]
defer = [c["word"] for c in cards0 if prov[c["word"]] == "DEFER"]

def report(name, words):
    n = len(words)
    in_main = [w for w in words if main_cnt[w] > 0]
    early   = [w for w in words if main_first.get(w, 99) <= 2]   # recurs by ch1-2
    in_sub  = [w for w in words if sub_cnt[w] > 0]
    in_mini = [w for w in words if mini_cnt[w] > 0]
    # context-divergence proxy: recurs later AND polysemous kanji (>=3 senses)
    polyrec = [w for w in in_main if script(w) == "kanji" and nsenses(w) >= 3]
    stable  = [w for w in in_main if script(w) == "kana" or nsenses(w) <= 2]
    print(f"\n== {name}: {n} terms ==")
    print(f"  recur in MAIN story:        {len(in_main):4} ({pct(in_main,n)}%)   of these first seen by ch2: {len(early)}")
    print(f"  recur in SUBSTORY text:     {len(in_sub):4} ({pct(in_sub,n)}%)")
    print(f"  recur in MINIGAME text:     {len(in_mini):4} ({pct(in_mini,n)}%)")
    print(f"  recurring & polysemous-kanji (context may differ): {len(polyrec):4} ({pct(polyrec,n)}%)")
    print(f"  recurring & mono/loanword  (context stable):       {len(stable):4} ({pct(stable,n)}%)")
    return dict(polyrec=polyrec)

def pct(sub, n): return 100*len(sub)//max(1,n)

print(f"main-story lemmas: {len(main_cnt)}, substory lemmas: {len(sub_cnt)}, minigame lemmas: {len(mini_cnt)}")
print(f"provisional split of {len(cards0)} ch0 words -> KEEP {len(keep)}, DEFER {len(defer)}")
rk = report("KEEP (core, Chapter 0)", keep)
rd = report("DEFER (minigame)", defer)

print("\nsample KEEP terms that recur later as polysemous kanji (re-teaching in new context may help):")
print("  " + "  ".join(sorted(rk["polyrec"])[:30]))
