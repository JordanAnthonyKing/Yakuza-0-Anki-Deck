"""Re-run ONLY the official-line gate for cards whose official line was rejected, using the
current align_ch{ch}.json (full ±5 window). Literal translations are never touched.

  python regate.py prep    <ch> [nbatches]  # write batch inputs + print what to spawn
  python regate.py bracket <ch> [nbatches]  # same, but for drifted cards (see below)
  python regate.py merge   <ch>             # fold accepted results into translate/ch{ch}/

bracket: a still-rejected card sandwiched between two ACCEPTED cards of the same .msg file
must find its official line between theirs. When that stretch is dense enough (<= MAX_BRACKET
lines, or <= LINES_PER_CARD lines per card it holds) but reaches outside the ±5 window
already shown, re-gate with the whole stretch plus the two anchor lines. Catches per-file
accumulating drift (e.g. Ch1 orders 77-157: 63 cards in two 48/66-line gaps); sparse
stretches are rewritten scenes and are skipped.

State lives in data/translate/regate_ch{ch}/ (in_*.json / out_*.json). Merge only
flips official_ok false->true; range files are backed up once to *.pre_regate.
"""
import os, sys, io, json, glob, shutil, contextlib
DATA = r"C:\Users\jordan\repos\yakuza\data"
mode, ch = sys.argv[1], int(sys.argv[2])
nb = int(sys.argv[3]) if len(sys.argv) > 3 else 2
tdir = os.path.join(DATA, "translate", f"ch{ch}")
rdir = os.path.join(DATA, "translate", f"regate_ch{ch}"); os.makedirs(rdir, exist_ok=True)

ranges = {p: json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(tdir, "*.json")))}
trans = {k: v for d in ranges.values() for k, v in d.items()}
MAX_BRACKET, LINES_PER_CARD = 24, 3

def write_batches(rows, tag):
    size = -(-len(rows) // nb)
    prompt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate_prompt.txt")
    print(f"{len(rows)} cards -> {nb} batches. Spawn ONE opus subagent per batch following {prompt}:")
    for i in range(nb):
        part = rows[i * size:(i + 1) * size]
        ip, op = (os.path.join(rdir, f"{x}_{tag}{i + 1}.json") for x in ("in", "out"))
        json.dump(part, open(ip, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  {tag}{i + 1} ({len(part)} cards)\n    input : {ip}\n    output: {op}")

if mode in ("prep", "bracket"):
    align = json.load(open(os.path.join(DATA, f"align_ch{ch}.json"), encoding="utf-8"))
    rejected = lambda r: (str(r["order"]) in trans and not trans[str(r["order"])]["official_ok"]
                          and r["official_candidate"])
    base = lambda r: {"order": r["order"], "speaker": r["speaker"], "sentence": r["sentence"],
                      "literal": trans[str(r["order"])]["literal"],
                      "official_candidate": r["official_candidate"],
                      "official_neighbors": r["official_neighbors"]}

if mode == "prep":
    write_batches([base(r) for r in align if rejected(r)], "part")

elif mode == "bracket":
    sys.argv = [sys.argv[0], str(ch)]               # build_align runs on import
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            import build_align as B
        except UnicodeEncodeError:                  # its sample printout can't encode on cp1252
            B = sys.modules["build_align"]
    align.sort(key=lambda r: r["order"])

    def official_pos(r):
        """index in the EN file of the official line accepted for card r, else None"""
        t = trans.get(str(r["order"]))
        if not t or not t["official_ok"]:
            return None
        en, o = B.get_msgs(r["uid"])[1], t["official"].strip()[:30]
        ks = [k for k, e in enumerate(en) if o and o in e]
        j = en.index(r["official_candidate"]) if r["official_candidate"] in en else 0
        return min(ks, key=lambda k: abs(k - j)) if ks else None

    pos = [official_pos(r) for r in align]
    rows = []
    for i, r in enumerate(align):
        if not rejected(r):
            continue
        en = B.get_msgs(r["uid"])[1]
        j = en.index(r["official_candidate"])
        prv = next((x for x in range(i - 1, -1, -1) if align[x]["uid"] == r["uid"] and pos[x] is not None), None)
        nxt = next((x for x in range(i + 1, len(align)) if align[x]["uid"] == r["uid"] and pos[x] is not None), None)
        if prv is None or nxt is None:
            continue
        a, b = pos[prv], pos[nxt]
        n_cards = sum(1 for x in range(prv + 1, nxt) if rejected(align[x]))
        if b < a or (a >= j - 5 and b <= j + 5) or \
                b - a + 1 > max(MAX_BRACKET, LINES_PER_CARD * n_cards):
            continue                                # inverted, nothing new to show, or too sparse
        row = base(r)
        row["official_candidate"] = en[(a + b) // 2]
        row["official_neighbors"] = [en[k] for k in range(a, b + 1)]
        row["prev_official"] = trans[str(align[prv]["order"])]["official"]
        row["next_official"] = trans[str(align[nxt]["order"])]["official"]
        rows.append(row)
    write_batches(rows, "bracket")

elif mode == "merge":
    res = {}                                        # an acceptance from ANY pass wins
    for p in sorted(glob.glob(os.path.join(rdir, "out_*.json"))):
        for k, v in json.load(open(p, encoding="utf-8")).items():
            if v.get("official_ok") or k not in res:
                res[k] = v
    flipped = 0
    for p, d in ranges.items():
        hit = {k: res[k] for k in d if k in res and res[k].get("official_ok")
               and (res[k].get("official") or "").strip() and not d[k]["official_ok"]}
        if not hit:
            continue
        if not os.path.exists(p + ".pre_regate"):
            shutil.copy(p, p + ".pre_regate")
        for k, v in hit.items():
            d[k]["official"], d[k]["official_ok"] = v["official"].strip(), True
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        flipped += len(hit)
    ok = sum(v["official_ok"] for v in trans.values())
    print(f"Ch{ch}: regated {len(res)}, newly accepted {flipped}; "
          f"official now {ok}/{len(trans)} ({100 * ok // len(trans)}%)")
