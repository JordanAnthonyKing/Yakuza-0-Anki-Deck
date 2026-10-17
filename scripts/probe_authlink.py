"""Does a story cutscene archive (aXX_YYY) reference the dialogue msg UIDs?
Scan every inner file of extracted auth scene(s) for 4-byte LE values that match msg UIDs."""
import os, re, glob, struct

WDR = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"
AUTH = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\authtest2"

uids = set()
for p in glob.glob(os.path.join(WDR, "msg", "**", "*.msg"), recursive=True):
    m = re.search(r"uid([0-9a-fA-F]{8})\.msg$", os.path.basename(p))
    if m: uids.add(int(m.group(1), 16))

# also index which uid -> which top-byte group, to sanity check matches aren't tiny ints
def scan_file(path):
    data = open(path, "rb").read()
    n = len(data)//4
    words = struct.unpack("<%dI" % n, data[:n*4])
    # match on non-trivial uids (>0xffff) to avoid 0/counters
    hits = [w for w in words if w in uids and w > 0xffff]
    return n, hits

for f in glob.glob(os.path.join(AUTH, "**", "*"), recursive=True):
    if os.path.isfile(f):
        n, hits = scan_file(f)
        rel = f.replace(AUTH, "")
        tag = f"  <-- {len(hits)} UID refs: {[format(h,'08x') for h in hits[:12]]}" if hits else ""
        print(f"{rel}  ({n*4} b){tag}")
