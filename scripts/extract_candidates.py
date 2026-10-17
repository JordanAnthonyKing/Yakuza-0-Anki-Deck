"""Generous candidate pool for the Chapter-0 (CORE) + MINIGAME decks.

Keeps non-dialogue lines in the system/UI OR minigame register (high recall -- the
subagent classifier is the precision filter), tokenizes with build_deck's filters
(drop known/function words, require a JMdict gloss), and emits one record per unique
candidate word with: reading, POS, JMdict candidate senses, up to 3 short example
sentences, and a hint of whether it showed up in minigame-flavored lines.

Output: data/candidates_ch0.json
"""
import os, re, glob, json, collections
import fugashi
from build_deck import DATA, CONTENT_POS, SKIP_POS2, STOPLEMMA, kata2hira, load_jmdict, gloss_pos

SRC = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"
JP    = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
NOISE = re.compile(r"^(Talk|MOT|MTN|face|cam|ROOM|EVENT|se_|vo_|bgm)", re.I)

CTRL = re.compile("スティック|カーソル|十字キー|方向キー|トリガー|コントローラー|[ＬＲ][１２]")
CORE = re.compile(
    "体力|回復|装備|武器|防具|ヒート|ゲージ|アクション|ミニゲーム|プレイスポット|"
    "セーブ|ロード|メニュー|マップ|経験値|レベル|ダメージ|コンボ|必殺技|スキル|"
    "強化|素材|アイテム|所持金|所持品|所持数|攻撃|防御|ガード|回避|投げ技|つかみ|"
    "ダッシュ|ジャンプ|カメラ|視点|操作|ステージ|ランク|報酬|制限時間|図鑑|バトル|"
    "スタイル|挑戦|記録|賞金|チップ|習得|発動|入手|効果時間|ボタン|画面|"
    "選択|決定|表示|出現|敵|耐久|威力")
MINI = re.compile(
    "麻雀|将棋|花札|こいこい|チンチロ|ポーカー|ブラックジャック|バカラ|ルーレット|"
    "カジノ|カラオケ|ディスコ|ポケットサーキット|ポケサー|サーキット|テレクラ|"
    "キャバ|接客|嬢|ボウリング|ダーツ|ビリヤード|バッティング|クレーンゲーム|ＵＦＯ|"
    "釣り|撒き餌|メスキング|不動産|経営|物件|グラビア|撮影|水鉄砲|盤面|"
    "役満|リーチ|テンパイ|ドラ|得点|コース|マシン|パーツ|モーター")
MENU = set("基本操作 戻る 次へ 前へ 決定 確認 所持品 詳細 装備する 強化する 選択 表示 遊び方 やめる 続ける".split())
# JMdict pos tags that mark a grammatical/function word (never a teachable game term)
FUNC_POS = {"int", "prt", "conj", "adj-pn", "pn", "aux", "aux-v", "aux-adj", "cop-da", "cop", "unc"}
DIALOGUE = re.compile(
    "[「」『』]|俺|オレ|私|わし|ワシ|あんた|アンタ|お前|おまえ|てめえ|君|きみ|"
    "あたし|ボク|僕|お主|おぬし|"
    "や。|やん|やで|ねん|なぁ|なあ|ぜ。|ぞ。|わよ|かい？|さ。|"
    "だろ|だぜ|だぞ|じゃ。|のう|っす|ちゃう|やろ|やわ|"
    "されました？|されますか|どうされ|ください。|ください！")

tagger = fugashi.Tagger()
known = json.load(open(os.path.join(DATA, "known_words.json"), encoding="utf-8"))
known_w = set(known["words"]); known_r = set(known["readings"])
jm = load_jmdict()

def clean(r):
    r = re.sub(r"<[^>]*>", "", r).strip()
    r = re.sub(r"[%＆][sd&Rr]", "", r).strip()
    return r

# word -> {reading,pos,senses, examples:set, mini_hits:int, total:int}
cand = {}
files = glob.glob(os.path.join(SRC, "**", "*.msg"), recursive=True) + \
        glob.glob(os.path.join(SRC, "**", "*.bin"), recursive=True)

for p in files:
    text = open(p, "rb").read().decode("utf-8", "replace")
    for raw in re.split(r"[\x00-\x1f�]+", text):
        raw = raw.strip()
        if not raw or NOISE.match(raw) or not JP.search(raw):
            continue
        line = clean(raw)
        if not line or DIALOGUE.search(line):
            continue
        label = re.sub(r"[（）「」『』\(\)\s、。]", "", line)
        is_mini = bool(MINI.search(line))
        if not (CTRL.search(line) or CORE.search(line) or is_mini or label in MENU):
            continue
        for t in tagger(line):
            if t.feature.pos1 not in CONTENT_POS or t.feature.pos2 in SKIP_POS2:
                continue
            lemma = re.sub(r"-.*$", "", t.feature.lemma or t.surface)
            reading = kata2hira(t.feature.kana or "")
            if lemma in STOPLEMMA or lemma in known_w or reading in known_r or lemma not in jm:
                continue
            e = jm[lemma]
            # drop grammatical / function words (leaked demonstratives, particles, etc.)
            if set(e["senses"][0]["pos"]) & FUNC_POS:
                continue
            c = cand.get(lemma)
            if not c:
                senses = [f"({gloss_pos(s['pos'])}) " + "; ".join(s["glosses"]) for s in e["senses"]]
                c = cand[lemma] = dict(word=lemma, reading=e["reading"] or reading,
                                       pos=gloss_pos(e["senses"][0]["pos"]),
                                       candidates=senses, examples=[], mini=0, total=0)
            c["total"] += 1
            if is_mini:
                c["mini"] += 1
            if len(line) <= 42 and len(c["examples"]) < 4 and line not in c["examples"]:
                c["examples"].append(line)

out = list(cand.values())
for c in out:
    c["mini_ratio"] = round(c["mini"] / c["total"], 2)
out.sort(key=lambda c: c["word"])
json.dump(out, open(os.path.join(DATA, "candidates_ch0.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
mini_lean = sum(1 for c in out if c["mini_ratio"] >= 0.5)
print(f"{len(out)} candidate words  ({mini_lean} lean minigame, {len(out)-mini_lean} lean system)")
print("no example sentence:", sum(1 for c in out if not c["examples"]))
print("\nsample:")
for c in out[:20]:
    ex = c["examples"][0] if c["examples"] else "-"
    print(f"  {c['word']:8} ({c['reading']:6}) mini={c['mini_ratio']}  {c['candidates'][0][:34]:36} | {ex[:30]}")
