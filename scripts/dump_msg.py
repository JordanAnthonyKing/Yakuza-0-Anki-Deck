"""Dump readable JP runs from given .msg/.bin files for inspection.
Usage: python dump_msg.py <relpath> [<relpath> ...]
"""
import os, re, sys

SRC = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"
JP = re.compile(r"[぀-ヿ一-龯ｦ-ﾟ]")

for rel in sys.argv[1:]:
    p = os.path.join(SRC, rel)
    text = open(p, "rb").read().decode("utf-8", "replace")
    runs = [r.strip() for r in re.split(r"[\x00-\x1f�]+", text)]
    runs = [re.sub(r"<[^>]*>", "", r).strip() for r in runs if JP.search(r)]
    runs = [r for r in runs if r]
    print(f"\n===== {rel}  ({len(runs)} JP runs) =====")
    for r in runs[:40]:
        print("  ", r[:90])
