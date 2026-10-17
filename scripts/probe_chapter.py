"""Probe whether dialogue msg UIDs can be mapped to story chapters.

Looks at:
  1. distribution of msg UIDs (from the extracted wdr tree),
  2. printable ASCII strings in the scenario_*.bin files (chapter markers? scene codes? uid refs?),
  3. overlap between msg-UID integers and 4-byte little-endian values inside scenario2.bin.
"""
import os, re, glob, struct, collections

WDR = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"
SCEN = r"C:\Program Files (x86)\Steam\steamapps\common\Yakuza 0\media\data\scenario"

# 1. msg UID distribution
uids = []
for p in glob.glob(os.path.join(WDR, "**", "*.msg"), recursive=True):
    m = re.search(r"uid([0-9a-fA-F]{8})\.msg$", os.path.basename(p))
    if m:
        uids.append(int(m.group(1), 16))
uids_set = set(uids)
print(f"msg UIDs: {len(uids)} total, {len(uids_set)} unique")
byhi = collections.Counter(u >> 24 for u in uids)          # top byte
byhi2 = collections.Counter((u >> 16) & 0xff for u in uids)  # 2nd byte
print("  by top byte:", dict(sorted(byhi.items())))
print("  sample sorted:", [f"{u:08x}" for u in sorted(uids_set)[:8]], "...", [f"{u:08x}" for u in sorted(uids_set)[-4:]])

def strings(data, minlen=4):
    return re.findall(rb"[\x20-\x7e]{%d,}" % minlen, data)

# 2. scenario file strings
for f in sorted(glob.glob(os.path.join(SCEN, "*.bin"))):
    data = open(f, "rb").read()
    ss = strings(data)
    print(f"\n==== {os.path.basename(f)} ({len(data)} bytes, {len(ss)} ascii strings) ====")
    # show a variety of strings
    uniq = []
    seen = set()
    for s in ss:
        t = s.decode("ascii")
        if t not in seen:
            seen.add(t); uniq.append(t)
    print("  first 30 unique strings:")
    for t in uniq[:30]:
        print("    ", repr(t))
    # look for chapter/scene-ish tokens
    chap = [t for t in uniq if re.search(r"(chap|chapter|ch[0-9]|a[0-1][0-9]_|scene|scn|kiryu|majima|prologue|finale)", t, re.I)]
    if chap:
        print("  chapter/scene-ish tokens:", chap[:40])

# 3. UID overlap in scenario2.bin (4-byte LE scan)
s2 = os.path.join(SCEN, "scenario2.bin")
if os.path.exists(s2):
    data = open(s2, "rb").read()
    vals = struct.unpack("<%dI" % (len(data)//4), data[:len(data)//4*4])
    hits = [v for v in vals if v in uids_set]
    print(f"\nscenario2.bin: {len(vals)} u32 words, {len(hits)} match msg UIDs ({len(set(hits))} unique)")
    print("  first 12 matches in file order:", [f"{v:08x}" for v in hits[:12]])
