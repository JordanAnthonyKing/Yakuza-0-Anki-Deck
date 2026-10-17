"""Test whether msg UID correlates with chapter, using the 129 cutscene-coded files as ground truth."""
import os, re, glob, collections
WDR_MSG = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj\msg"
CODE = re.compile(rb"c([0-9]{2})[_-]([0-9]{3})")

rows = []
for p in glob.glob(os.path.join(WDR_MSG, "**", "*.msg"), recursive=True):
    d = open(p, "rb").read()
    codes = CODE.findall(d)
    if not codes:
        continue
    uid = int(re.search(r"uid([0-9a-f]{8})", os.path.basename(p)).group(1), 16)
    chaps = collections.Counter(int(c) for c, s in codes)
    main_ch = chaps.most_common(1)[0][0]   # dominant chapter in this file
    scenes = sorted(set(f"c{c.decode()}_{s.decode()}" for c, s in codes))
    rows.append((uid, main_ch, scenes[0], len(codes)))

rows.sort()
print(f"{'uid':>10}  ch  first_scene  #lines")
prev_ch = None
inversions = 0
for uid, ch, sc, n in rows:
    flag = ""
    if prev_ch is not None and ch < prev_ch:
        flag = "  <-- chapter DROPS vs prev"
        inversions += 1
    print(f"{uid:08x}  {ch:2}  {sc:10}  {n:4}{flag}")
    prev_ch = ch
print(f"\ntotal coded files: {len(rows)}, chapter inversions when sorted by uid: {inversions}")

# also within each uid top-byte cluster
print("\nper uid-top-byte: chapter range spanned")
byhi = collections.defaultdict(list)
for uid, ch, sc, n in rows:
    byhi[uid >> 24].append(ch)
for hi in sorted(byhi):
    chs = byhi[hi]
    print(f"  {hi:02x}: {len(chs)} files, chapters {min(chs)}-{max(chs)}, order-sorted sample {chs[:20]}")
