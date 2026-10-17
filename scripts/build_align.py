"""Attach official-English candidates to Chapter 1 cards for the gated translation pass.

Each Ch1 card carries a `uid` -> its source .msg file. We null-split both the JA
(wdrj) and EN (wdr) copies into logical messages, locate the JA message containing the
card's sentence, and take the positionally-aligned EN message plus a couple of
neighbors (to cover merge/split/reorder localization). The LLM gate later decides
whether any candidate is a faithful rendering.

Output: data/align_ch1.json  (list per card, subset-agnostic)
"""
import os, re, glob, json, sys
CH = int(sys.argv[1]) if len(sys.argv) > 1 else 1
try:
    sys.stdout.reconfigure(encoding="utf-8")   # sample printout has JP; cp1252 console crashed
except (AttributeError, ValueError):
    pass

BASE = r"C:\Users\jordan\repos\yakuza\source"   # wdrj/ (JA) + wdr/ (official EN) msg trees
DATA = r"C:\Users\jordan\repos\yakuza\data"
JP = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")
ENW = re.compile(r"[A-Za-z]{2,}"); VOW = re.compile(r"[aeiouAEIOU]")

def clean_txt(s, ja=True):
    s = re.sub(r"<[^>]*>", "", s)
    # JA sub-lines join with no gap; EN sub-lines join with a space to keep word boundaries
    s = re.sub(r"[\r\n]+", "" if ja else " ", s)
    s = s.replace("�", "").strip()
    if not ja:
        s = re.sub(r"^\d+\s*", "", s)     # drop leading format-digit artifacts
        s = re.sub(r"\s{2,}", " ", s)
    return s

def good_en(s):
    # a real English line has >=2 word tokens containing a vowel; kills binary junk
    # like 'hjAp', 'z{Ap', '@UU' that otherwise inflates the EN count and offsets alignment
    toks = [t for t in re.findall(r"[A-Za-z]{2,}", s) if VOW.search(t)]
    if len(toks) >= 2:
        return True
    return len(toks) == 1 and len(s) >= 5 and s.count(" ") == 0 and s[0].isupper()  # lone label word

def messages(path, ja):
    out = []
    for part in open(path, "rb").read().split(b"\x00"):
        s = clean_txt(part.decode("utf-8", "replace"), ja)
        if not s:
            continue
        if ja:
            if JP.search(s):
                out.append(s)
        elif good_en(s):
            out.append(s)
    return out

# uid -> ja file path
uid2path = {}
for p in glob.glob(os.path.join(BASE, "wdrj", "msg", "**", "*.msg"), recursive=True):
    m = re.search(r"uid([0-9a-f]{8})", os.path.basename(p))
    if m:
        uid2path[m.group(1)] = p

_cache = {}
def get_msgs(uid):
    if uid in _cache:
        return _cache[uid]
    jp = uid2path.get(uid)
    if not jp:
        _cache[uid] = ([], [], False); return _cache[uid]
    ep = jp.replace(os.sep + "wdrj" + os.sep, os.sep + "wdr" + os.sep)
    ja = messages(jp, True)
    en = messages(ep, False) if os.path.exists(ep) else []
    _cache[uid] = (ja, en, len(ja) == len(en) and bool(ja))
    return _cache[uid]

def midfracs(msgs):
    """fractional char-position of each message's midpoint within the whole list"""
    lens = [len(m) for m in msgs]
    total = sum(lens) or 1
    fr, acc = [], 0
    for L in lens:
        fr.append((acc + L / 2) / total); acc += L
    return fr

# Proper nouns that survive localization -- used to estimate a per-file index offset
# so the candidate window follows the systematic drift (official sitting a few lines
# ahead of the Japanese). Delta is 0 when a file has no anchors, so aligned files are
# never disturbed.
NAME_ROMAJI = {
    "桐生": "kiryu", "錦": "nishiki", "風間": "kazama", "堂島": "dojima", "真島": "majima",
    "立華": "tachibana", "タチバナ": "tachibana", "バッカス": "bacchus", "ブルーノ": "bruno",
    "神室町": "kamurocho", "蒼天堀": "sotenbori", "神宮": "jingu", "セラ": "sera",
}
_ROMAJI = set(NAME_ROMAJI.values())
def _anch_ja(s): return {v for k, v in NAME_ROMAJI.items() if k in s}
def _anch_en(s):
    low = s.lower(); return {v for v in _ROMAJI if v in low}
def file_delta(ja, en):
    if not ja or not en:
        return 0
    fj, fe = midfracs(ja), midfracs(en)
    ea = [_anch_en(e) for e in en]
    deltas = []
    for i, a in enumerate(ja):
        aj = _anch_ja(a)
        if not aj:
            continue
        j0 = min(range(len(en)), key=lambda k: abs(fe[k] - fj[i]))
        best, bd = None, 99
        for k in range(max(0, j0 - 15), min(len(en), j0 + 16)):
            if aj & ea[k] and abs(k - j0) < bd:
                bd = abs(k - j0); best = k
        if best is not None:
            deltas.append(best - j0)
    if not deltas:
        return 0
    deltas.sort(); return deltas[len(deltas) // 2]
_delta_cache = {}

_dia = None
def label_official(label):
    """official English of a speaker label, via the index-parallel JA/EN name tables"""
    global _dia
    from msg_speakers import names
    if _dia is None:
        _dia = json.load(open(os.path.join(DATA, "dialogue_by_chapter.json"), encoding="utf-8"))
    for r in _dia.get(str(CH), []):
        if r.get("speaker") != label or r["uid"] not in uid2path:
            continue
        jp = uid2path[r["uid"]]
        ja, en = names(jp), names(jp.replace(os.sep + "wdrj" + os.sep, os.sep + "wdr" + os.sep))
        if label in ja and ja.index(label) < len(en):
            return en[ja.index(label)]
    return ""

cards = json.load(open(os.path.join(DATA, f"cards_ch{CH}_{CH}.json"), encoding="utf-8"))
rows = []
have = 0
for c in cards:
    sent = clean_txt(c["sentence"])           # strips the <b> emphasis too
    if c.get("kind") == "label":
        # speaker-descriptor card: its official English is the localized speaker name at
        # the same index of the parallel wdr/ name table (exact, not positional)
        cand = label_official(sent)
        have += bool(cand)
        rows.append({
            "order": c["order"], "word": c["word"], "reading": c["reading"],
            "meaning": c["meaning"], "pos": c["pos"], "speaker": c.get("speaker", ""),
            "uid": c["uid"], "sentence": sent, "parity": True,
            "official_candidate": cand, "official_neighbors": [],
        })
        continue
    ja, en, parity = get_msgs(c["uid"])
    cand, neigh, idx = "", [], None
    for i, a in enumerate(ja):
        if sent and (sent in a or a in sent):
            idx = i; break
    if idx is not None and en:
        # map JA position -> EN by matching char-length midpoint fraction (handles count
        # mismatch / merge-split / leading-junk offset far better than raw index)
        fj, fe = midfracs(ja), midfracs(en)
        j0 = min(range(len(en)), key=lambda k: abs(fe[k] - fj[idx]))
        d = _delta_cache.get(c["uid"])
        if d is None:
            d = _delta_cache[c["uid"]] = file_delta(ja, en)
        j = max(0, min(len(en) - 1, j0 + d))
        cand = en[j]
        neigh = [en[k] for k in (j-5, j-4, j-3, j-2, j-1, j+1, j+2, j+3, j+4, j+5)
                 if 0 <= k < len(en) and en[k] != cand]
        have += 1
    rows.append({
        "order": c["order"], "word": c["word"], "reading": c["reading"],
        "meaning": c["meaning"], "pos": c["pos"], "speaker": c.get("speaker", ""),
        "uid": c["uid"], "sentence": sent, "parity": parity,
        "official_candidate": cand, "official_neighbors": neigh,   # full ±5 window, in order
    })

json.dump(rows, open(os.path.join(DATA, f"align_ch{CH}.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
nz = {u: d for u, d in _delta_cache.items() if d}
print(f"{len(rows)} Ch{CH} cards; official candidate found for {have} "
      f"({100*have//len(rows)}%); offset-corrected files: {len(nz)} e.g. {list(nz.items())[:6]}")
print("\nsamples:")
for r in rows[:12]:
    print(f"  [{r['word']}] {r['sentence'][:26]}")
    print(f"      cand: {r['official_candidate'][:60]}")
