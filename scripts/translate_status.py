"""Monitor + resume basis for the translation run. State is derived entirely from the
range files in data/translate/ch{ch}/ -- no manifest to keep in sync.
Usage: python translate_status.py [chapter] [batchsize]
"""
import os, json, glob, sys
DATA = r"C:\Users\jordan\repos\yakuza\data"
ch = int(sys.argv[1]) if len(sys.argv) > 1 else 1
B = int(sys.argv[2]) if len(sys.argv) > 2 else 64

align = json.load(open(os.path.join(DATA, f"align_ch{ch}.json"), encoding="utf-8"))
orders = sorted(r["order"] for r in align)
tdir = os.path.join(DATA, "translate", f"ch{ch}")
done = {}
for f in sorted(glob.glob(os.path.join(tdir, "*.json"))):
    done.update(json.load(open(f, encoding="utf-8")))

done_orders = [o for o in orders if str(o) in done]
ok = sum(1 for o in done_orders if done[str(o)].get("official_ok"))
maxo = orders[-1] if orders else -1
batches = [(s, min(s + B - 1, maxo)) for s in range(0, maxo + 1, B)]
def bdone(s, e):
    os_ = [o for o in orders if s <= o <= e]
    return bool(os_) and all(str(o) in done for o in os_)
ndoneb = sum(1 for s, e in batches if bdone(s, e))
nxt = next((f"{s:03d}-{e:03d}" for s, e in batches if not bdone(s, e)), "ALL DONE")

pct = 100 * len(done_orders) // max(1, len(orders))
print(f"Chapter {ch}: {len(done_orders)}/{len(orders)} cards done ({pct}%)")
print(f"batches (size {B}): {ndoneb}/{len(batches)} complete   next: {nxt}")
if done_orders:
    print(f"official kept: {ok}/{len(done_orders)} ({100*ok//len(done_orders)}%)")
for s, e in batches:
    print(f"  [{'x' if bdone(s, e) else ' '}] {s:03d}-{e:03d}")
