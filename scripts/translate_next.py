"""Prep the next N missing translation batches (idempotent -- skips any range file that
already exists). Writes batch inputs to the scratchpad and prints exactly what to spawn.
Does NOT spawn anything. Usage: python translate_next.py [chapter] [N] [batchsize]
"""
import os, json, glob, sys
DATA = r"C:\Users\jordan\repos\yakuza\data"
SCRATCH = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\661dd7e3-534c-470c-9106-33c76f67f358\scratchpad"
FIELDS = ("order", "word", "reading", "meaning", "speaker", "sentence",
          "official_candidate", "official_neighbors")
ch = int(sys.argv[1]) if len(sys.argv) > 1 else 1
N = int(sys.argv[2]) if len(sys.argv) > 2 else 3
B = int(sys.argv[3]) if len(sys.argv) > 3 else 64

align = {r["order"]: r for r in json.load(open(os.path.join(DATA, f"align_ch{ch}.json"), encoding="utf-8"))}
orders = sorted(align)
maxo = orders[-1]
tdir = os.path.join(DATA, "translate", f"ch{ch}"); os.makedirs(tdir, exist_ok=True)
def outp(s, e): return os.path.join(tdir, f"{s:03d}-{e:03d}.json")
batches = [(s, min(s + B - 1, maxo)) for s in range(0, maxo + 1, B)]
missing = [(s, e) for s, e in batches if not os.path.exists(outp(s, e))][:N]

if not missing:
    print("nothing to do — all batches present"); raise SystemExit
prompt = os.path.join(os.path.dirname(__file__), "translate_prompt.txt")
print(f"Prepared {len(missing)} batch(es). Spawn ONE subagent per batch (model=opus),")
print(f"telling each to follow {prompt} with the given input/output paths:\n")
for s, e in missing:
    rows = [align[o] for o in orders if s <= o <= e]
    slim = [{k: r[k] for k in FIELDS} for r in rows]
    ip = os.path.join(SCRATCH, f"tbatch_ch{ch}_{s:03d}-{e:03d}.json")
    json.dump(slim, open(ip, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  batch {s:03d}-{e:03d}  ({len(slim)} cards)")
    print(f"    input : {ip}")
    print(f"    output: {outp(s, e)}\n")
