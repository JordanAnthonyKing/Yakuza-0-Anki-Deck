"""Test whether pac_STID_*.bin files link a scene/stage id to its message UIDs."""
import os, re, glob, struct

WDR = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"

# all known msg UID ints
uids = set()
for p in glob.glob(os.path.join(WDR, "msg", "**", "*.msg"), recursive=True):
    m = re.search(r"uid([0-9a-fA-F]{8})\.msg$", os.path.basename(p))
    if m: uids.add(int(m.group(1), 16))
print("known msg UIDs:", len(uids))

def scan(path):
    data = open(path, "rb").read()
    words = struct.unpack("<%dI" % (len(data)//4), data[:len(data)//4*4])
    hits = [w for w in words if w in uids]
    ss = [s.decode("ascii") for s in re.findall(rb"[\x20-\x7e]{3,}", data)]
    return data, hits, ss

for name in ["pac_STID_ST_DOJIMAGUMI.bin","pac_STID_ST_BOSS.bin","pac_STID_ST_DOJIMA_LAST.bin","pac_STID_ST_CRUISE.bin"]:
    p = os.path.join(WDR, "pac", name)
    if not os.path.exists(p):
        print("missing", name); continue
    data, hits, ss = scan(p)
    print(f"\n==== {name} ({len(data)} b) : {len(hits)} UID matches ({len(set(hits))} unique) ====")
    print("  strings:", ss[:20])
    print("  first UID hits:", [f"{h:08x}" for h in hits[:16]])
