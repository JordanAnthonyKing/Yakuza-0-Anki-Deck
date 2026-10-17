"""Find files that are genuinely control/tutorial text, keyed on hardware-control
terms (stick/cursor/d-pad/trigger) that essentially never occur in story dialogue.
Reports per-file counts so we can see the real tutorial seam.
"""
import os, re, glob, collections

SRC = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj"
CTRL = re.compile("スティック|カーソル|十字キー|方向キー|トリガー|コントローラー|Ｌ[１２Ｒ]|Ｒ[１２]|□|△|○|×|Ｌスティック|Ｒスティック")

files = glob.glob(os.path.join(SRC, "**", "*.msg"), recursive=True) + \
        glob.glob(os.path.join(SRC, "**", "*.bin"), recursive=True)

rows = []
for p in files:
    text = open(p, "rb").read().decode("utf-8", "replace")
    runs = [r.strip() for r in re.split(r"[\x00-\x1f�]+", text)]
    n = sum(1 for r in runs if CTRL.search(r))
    if n:
        rows.append((n, os.path.relpath(p, SRC)))
rows.sort(reverse=True)
print(f"{len(rows)} files contain hardware-control terms\n")
for n, rel in rows[:40]:
    print(f"{n:4}  {rel}")
print(f"\ntotal control-term lines across all files: {sum(n for n,_ in rows)}")
