"""Look at the bytes surrounding each JP string in a .msg to find a length/pointer
structure. If strings are length-prefixed or pointed to by a table, alignment becomes
exact. Prints each JP string's byte offset, the 8 preceding bytes, and the string.
"""
import os, re

BASE = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad"
REL = r"msg\uid01xxxxxx\uid016e00d1.msg"

for root, want in (("wdrj", "jp"), ("wdr", "en")):
    data = open(os.path.join(BASE, root, REL), "rb").read()
    print(f"\n===== {root} ({len(data)} bytes) =====")
    if want == "jp":
        pat = re.compile(rb"(?:[\xe3-\xe9][\x80-\xbf]{2}){2,}")   # runs of JP chars
    else:
        pat = re.compile(rb"[A-Za-z][A-Za-z ',.!?]{4,}")           # english phrases
    cnt = 0
    for m in pat.finditer(data):
        s = m.group().decode("utf-8", "replace")
        pre = data[max(0, m.start()-8):m.start()].hex(" ")
        print(f"  @{m.start():5} pre[{pre}]  {s[:40]}")
        cnt += 1
        if cnt >= 14:
            break
    print(f"  ...total matches: {sum(1 for _ in pat.finditer(data))}")
