"""Extract game-system / UI / tutorial lines from ALL source .msg/.bin files -> a
"Chapter 0" corpus of general game terminology (controls, menus, minigames, shop,
combat tutorials) to learn BEFORE the story dialogue.

Unlike extract_dialogue.py (which keeps spoken story lines and drops menus), this
KEEPS only the system register and ignores chapter assignment. A run qualifies if it
carries a UI/system keyword, an instructional ending, or is a known menu label.

Output: data/system_by_chapter.json = {"0": [{uid, seq, speaker, line}, ...]}
"""
import os, re, glob, json

SRC = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"
OUT = r"C:\Users\jordan\repos\yakuza\data\system_by_chapter.json"

JP    = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
NOISE = re.compile(r"^(Talk|MOT|MTN|face|cam|ROOM|EVENT|se_|vo_|bgm)", re.I)

# Unambiguous hardware controls -- essentially never in dialogue.
# (button glyphs □△○× are excluded: ○○ is also a redaction placeholder and × is "times")
CTRL = re.compile("スティック|カーソル|十字キー|方向キー|トリガー|コントローラー|[ＬＲ][１２]")

# Core game-system vocabulary we actually want to TEACH as a pre-story primer.
# A line is kept only if it carries one of these (or a control token / menu label),
# which keeps the deck focused on UI/combat/menu terms and out of item flavor-text.
CORE = re.compile(
    "体力|回復|装備|武器|防具|ヒート|ゲージ|アクション|ミニゲーム|プレイスポット|"
    "セーブ|ロード|メニュー|マップ|経験値|レベル|ダメージ|コンボ|必殺技|スキル|"
    "強化|素材|アイテム|所持金|所持品|所持数|攻撃|防御|ガード|回避|投げ技|つかみ|"
    "ダッシュ|ジャンプ|カメラ|視点|操作|ステージ|ランク|報酬|制限時間|図鑑|バトル|"
    "スタイル|挑戦|記録|賞金|チップ|習得|発動|入手|効果時間|ボタン|画面|"
    "選択|決定|表示|出現|敵|防具|耐久|威力")

# short exact menu labels
MENU_LABELS = set(
    "基本操作 戻る 次へ 前へ はい いいえ 決定 確認 所持品 詳細 商品 遊び方 "
    "やめる 続ける 開始 終了 設定 説明 一覧 並び替え 売る 買う 使う 装備する "
    "強化する 捨てる 選択 キャンセル ヘルプ 所持数 所持金 制限時間 報酬 出現条件".split())

# conversational markers -> this is spoken dialogue, NOT UI/tutorial text
DIALOGUE = re.compile(
    "[「」『』]|俺|オレ|私|わし|ワシ|あんた|アンタ|お前|おまえ|てめえ|君|きみ|"
    "あたし|ボク|僕|お主|おぬし|"                          # pronouns
    "や。|やん|やで|ねん|なぁ|なあ|ぜ。|ぞ。|わよ|かい？|さ。|"    # casual enders / dialect
    "だろ|だぜ|だぞ|じゃ。|のう|っす|ちゃう|やろ|やわ|"
    "されました？|されますか|どうされ|ください。|ください！")     # keigo NPC speech

def clean(r):
    r = re.sub(r"<[^>]*>", "", r).strip()           # strip control codes
    r = re.sub(r"[%＆][sd&Rr]", "", r).strip()       # strip format tokens like %s &R
    return r

def parse_system(path):
    """Keep only non-dialogue lines that teach a system/UI/combat term: a control
    token, a button-press instruction, a core-vocab keyword, or a menu label."""
    text = open(path, "rb").read().decode("utf-8", "replace")
    out = []
    for r in re.split(r"[\x00-\x1f�]+", text):
        r = r.strip()
        if not r or NOISE.match(r) or not JP.search(r):
            continue
        r = clean(r)
        if not r or DIALOGUE.search(r):
            continue
        label = re.sub(r"[（）「」『』\(\)\s、。]", "", r)
        if CTRL.search(r) or CORE.search(r) or label in MENU_LABELS:
            out.append(r)
    return out

files = glob.glob(os.path.join(SRC, "**", "*.msg"), recursive=True) + \
        glob.glob(os.path.join(SRC, "**", "*.bin"), recursive=True)

seen = set()
rows = []
for p in files:
    uid_m = re.search(r"uid([0-9a-f]{8})", os.path.basename(p))
    uid = uid_m.group(1) if uid_m else os.path.splitext(os.path.basename(p))[0]
    for i, ln in enumerate(parse_system(p)):
        if ln in seen:            # global dedup (menus repeat across files/dialects)
            continue
        seen.add(ln)
        rows.append(dict(uid=uid, seq=i, speaker="", line=ln))

rows.sort(key=lambda x: (x["uid"], x["seq"]))
json.dump({"0": rows}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print(f"scanned {len(files)} files -> {len(rows)} unique system/UI lines -> {OUT}")
print("\nsample lines:")
for r in rows[:30]:
    print("  ", r["line"][:74])
