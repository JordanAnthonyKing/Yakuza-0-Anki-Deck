"""Locate .msg / .bin files containing game-system / UI vocabulary (tutorial, menus,
help). Scans the raw source tree, decodes utf-8, splits on control bytes, and reports
which files carry known UI terms and whether their UID is chapter-assigned (i.e. was it
already mined for dialogue, or is it untouched system text).
"""
import os, re, glob, json, collections

SRC = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"
ASSIGN = r"C:\Users\jordan\repos\yakuza\data\chapter_assignment.json"

assign = {a["uid"]: a for a in json.load(open(ASSIGN, encoding="utf-8"))}

# distinctive system/UI probe terms
PROBE = ["ボタン", "コントローラー", "スティック", "ヒートアクション", "ヒートゲージ",
         "体力", "回復", "装備", "セーブ", "ミニゲーム", "プレイスポット", "バトル",
         "攻撃", "ガード", "つかむ", "投げ", "必殺", "経験値", "レベル", "マップ",
         "メニュー", "所持金", "ダメージ", "アイテム", "スキル", "強化", "喧嘩",
         "押し", "連打", "長押し", "十字キー", "画面"]

files = glob.glob(os.path.join(SRC, "**", "*.msg"), recursive=True) + \
        glob.glob(os.path.join(SRC, "**", "*.bin"), recursive=True)

hits = []   # (path, n_terms, assigned?, sample_runs)
term_files = collections.Counter()
for p in files:
    text = open(p, "rb").read().decode("utf-8", "replace")
    found = [t for t in PROBE if t in text]
    if len(found) >= 3:                       # file is system-text-ish
        m = re.search(r"uid([0-9a-f]{8})", os.path.basename(p))
        uid = m.group(1) if m else None
        a = assign.get(uid) if uid else None
        assigned = bool(a and a.get("chapter"))
        hits.append((os.path.relpath(p, SRC), len(found), assigned, uid))
        for t in found:
            term_files[t] += 1

hits.sort(key=lambda x: -x[1])
print(f"{len(files)} source files scanned; {len(hits)} look like system/UI text (>=3 probe terms)\n")
print(f"{'terms':>5} {'assigned':>8}  file")
for rel, n, assigned, uid in hits[:60]:
    print(f"{n:5} {('CH' if assigned else '-'):>8}  {rel}")
n_unassigned = sum(1 for h in hits if not h[2])
print(f"\n{n_unassigned} of {len(hits)} system-text files are NOT chapter-assigned (untouched by dialogue mining)")
print("\ntop probe terms by file count:", ", ".join(f"{t}({c})" for t, c in term_files.most_common(15)))
