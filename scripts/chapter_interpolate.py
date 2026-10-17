"""Assign chapters to main-story msg files by UID-order interpolation from cutscene anchors,
then validate against the English transcript via speaker profile.

Within each uid cluster (top byte), sort files by uid. Coded files (embedded cXX) are anchors.
Uncoded files inherit the chapter of the nearest anchors (forward/back fill; if between two
anchors of the same chapter -> that chapter; if between different -> boundary by midpoint).
"""
import os, re, glob, json, collections

WDR_MSG = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj\msg"
CODE = re.compile(rb"c([0-9]{2})[_-][0-9]{3}")
JP = re.compile(r"[぀-ヿ一-龯]")

def parse_msg(path):
    d = open(path, "rb").read()
    codes = [int(c) for c in CODE.findall(d)]
    chap = collections.Counter(codes).most_common(1)[0][0] if codes else None
    # dialogue + speaker heuristic: UTF-8 runs with JP
    runs = re.split(r"[\x00-\x1f�]+", d.decode("utf-8", "replace"))
    jp_runs = [r for r in runs if JP.search(r) and not r.startswith("Talk")]
    speakers = [r for r in jp_runs if len(r) <= 6 and not re.search(r"[。、！？…]", r)]
    return chap, jp_runs, speakers

files = []
for p in glob.glob(os.path.join(WDR_MSG, "**", "*.msg"), recursive=True):
    uid = int(re.search(r"uid([0-9a-f]{8})", os.path.basename(p)).group(1), 16)
    chap, jp, spk = parse_msg(p)
    files.append(dict(uid=uid, path=p, cluster=uid >> 16, coded=chap, jp=len(jp), spk=spk))

# interpolate within clusters that contain anchors
by_cluster = collections.defaultdict(list)
for f in files:
    by_cluster[f["cluster"]].append(f)

assigned = 0
anchor_clusters = []
for cl, fs in by_cluster.items():
    fs.sort(key=lambda x: x["uid"])
    anchors = [f for f in fs if f["coded"] is not None]
    if not anchors:
        for f in fs: f["chapter"] = None
        continue
    anchor_clusters.append(cl)
    # forward-fill then back-fill using anchors
    last = None
    for f in fs:
        if f["coded"] is not None:
            last = f["coded"]
        f["chapter"] = f["coded"] if f["coded"] is not None else last
    # back-fill leading uncoded
    nxt = None
    for f in reversed(fs):
        if f["coded"] is not None:
            nxt = f["coded"]
        elif f["chapter"] is None:
            f["chapter"] = nxt

for f in files:
    if f.get("chapter") is not None and f["jp"]:
        assigned += 1

print("clusters with anchors:", sorted(f"{c:02x}" for c in anchor_clusters))
print(f"JP files assigned a chapter: {assigned}")
print("\nper anchor-cluster: JP files, coded anchors, chapter span")
for cl in sorted(anchor_clusters):
    fs = [f for f in by_cluster[cl] if f["jp"]]
    coded = [f for f in fs if f["coded"] is not None]
    chaps = [f["chapter"] for f in fs if f["chapter"]]
    print(f"  {cl:02x}: {len(fs):3} JP files, {len(coded):3} anchors, chapters {min(chaps)}-{max(chaps)}")

# save assignment
out = [dict(uid=f"{f['uid']:08x}", cluster=f"{f['cluster']:02x}", coded=f['coded'],
            chapter=f.get('chapter'), jp=f['jp'], spk=f['spk']) for f in files]
json.dump(out, open(r"C:\Users\jordan\repos\yakuza\data\chapter_assignment.json","w",encoding="utf-8"), ensure_ascii=False)

# validate: speaker profile per predicted chapter (top JP speakers)
print("\nvalidation - top JP speakers per predicted chapter (expect to match transcript):")
chap_spk = collections.defaultdict(collections.Counter)
for f in files:
    if f.get("chapter"):
        for s in f["spk"]:
            chap_spk[f["chapter"]][s] += 1
for ch in range(1, 18):
    top = chap_spk[ch].most_common(6)
    print(f"  ch{ch:02}: {[f'{s}({n})' for s,n in top]}")
