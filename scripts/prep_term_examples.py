"""Prep the Ch0 / minigame term-deck example sentences for the translation pass.

Examples that come from a dialogue .msg get an official-English candidate + ordered ±5
neighbors (same alignment as build_align); the rest (item/kart descriptions stored
outside wdr) get none and end up literal-only. Writes data/translate/terms/in.json;
the subagent (translate_prompt.txt) writes data/translate/terms/out.json, keyed by order.
"""
import os, sys, io, json, contextlib
sys.argv = [sys.argv[0], "1"]                 # build_align runs on import; ch1 is harmless
with contextlib.redirect_stdout(io.StringIO()):
    try:
        import build_align as B
    except UnicodeEncodeError:                # its sample printout can't encode on cp1252
        B = sys.modules["build_align"]

buckets = json.load(open(os.path.join(B.DATA, "ch0_buckets.json"), encoding="utf-8"))
rows = []
for b in ("CORE", "MINIGAME"):
    for c in buckets[b]:
        if not c["example"].strip():
            continue
        sent = B.clean_txt(c["example"])
        cand, neigh = "", []
        for uid in B.uid2path:
            ja, en, _ = B.get_msgs(uid)
            idx = next((i for i, a in enumerate(ja) if len(a) > 3 and (sent in a or a in sent)), None)
            if idx is None or not en:
                continue
            fj, fe = B.midfracs(ja), B.midfracs(en)
            j = min(range(len(en)), key=lambda k: abs(fe[k] - fj[idx]))
            cand = en[j]
            neigh = [en[k] for k in range(j - 5, j + 6) if k != j and 0 <= k < len(en) and en[k] != cand]
            break
        rows.append({"order": len(rows), "bucket": b, "word": c["word"], "reading": c["reading"],
                     "meaning": c["meaning"], "speaker": "", "sentence": sent,
                     "official_candidate": cand, "official_neighbors": neigh})

out = os.path.join(B.DATA, "translate", "terms"); os.makedirs(out, exist_ok=True)
json.dump(rows, open(os.path.join(out, "in.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(rows)} examples, {sum(bool(r['official_candidate']) for r in rows)} with an official candidate"
      f" -> {os.path.join(out, 'in.json')}")
