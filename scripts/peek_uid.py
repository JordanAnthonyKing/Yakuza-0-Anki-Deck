import os, re, sys
BASE = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"
import glob
uid = sys.argv[1]
p = next(glob.glob(os.path.join(BASE, "msg", "**", f"uid{uid}.msg"), recursive=True).__iter__())
data = open(p, "rb").read().decode("utf-8", "replace")
JP = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ）（「」『』]")
print("--- control-split lines (how extract_dialogue sees them) ---")
for r in re.split(r"[\x00-\x1f�]+", data):
    r = re.sub(r"<[^>]*>", "", r).strip()
    if r and JP.search(r):
        print("  |", r)
print("\n--- NUL-split messages (full monologue units) ---")
for part in data.split(b"\x00"):
    s = re.sub(r"<[^>]*>", "", part.decode("utf-8", "replace"))
    s = re.sub(r"[\r\n]+", "⏎", s).strip()
    if s and JP.search(s):
        print("  »", s)
