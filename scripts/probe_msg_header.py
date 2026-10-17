"""Inspect the .msg container header to judge how parseable the string table is.
Shows the first bytes as hex, tries to read a plausible count + 32-bit offset array,
and checks whether those offsets point at the UTF-8 strings -- in both JA and EN.
"""
import os, re, struct

BASE = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad"
REL = r"msg\uid01xxxxxx\uid016e00d1.msg"

for root in ("wdrj", "wdr"):
    data = open(os.path.join(BASE, root, REL), "rb").read()
    print(f"\n===== {root}  ({len(data)} bytes) =====")
    print("first 64 bytes hex:", data[:64].hex(" "))
    # try little-endian u32s at the front
    u32 = struct.unpack_from("<16I", data, 0)
    print("first 16 LE u32:", u32)
    # where does the first UTF-8 text byte appear?
    m = re.search(rb"[\xe3-\xef]", data)            # JP lead byte
    ma = re.search(rb"[A-Za-z]{4}", data)           # english word
    print("first JP-ish byte offset:", m.start() if m else None,
          " first ascii-word offset:", ma.start() if ma else None)
    # heuristic: interpret u32[0] or u32[1] as count, then a table of offsets
    for guesspos in (0, 4, 8):
        cnt = struct.unpack_from("<I", data, guesspos)[0]
        if 1 <= cnt <= 4000:
            offs = struct.unpack_from(f"<{min(cnt,6)}I", data, guesspos+4)
            print(f"  if count@{guesspos}={cnt}: first offsets {offs} "
                  f"(in range={all(0<=o<len(data) for o in offs)})")
