"""Figure out what language/encoding wdr\ uses. Reads a couple of files raw and, for
several encodings, extracts word-like runs (>=3 letters) and counts CJK/Hangul/Latin.
"""
import os, re

BASE = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad"
FILES = [r"msg\uid01xxxxxx\uid016e00d1.msg", r"shop\shop0004.bin"]
ENCS = ["utf-8", "utf-16-le", "utf-16-be", "cp932", "latin-1"]

CJK = re.compile(r"[一-龯]"); KANA = re.compile(r"[぀-ヿ]"); HAN = re.compile(r"[가-힣]")
WORD = re.compile(r"[A-Za-z]{3,}(?:[ '\-][A-Za-z]+)*")

for rel in FILES:
    p = os.path.join(BASE, "wdr", rel)
    data = open(p, "rb").read()
    print(f"\n===== wdr\\{rel}  ({len(data)} bytes) =====")
    for enc in ENCS:
        try:
            t = data.decode(enc, "ignore")
        except Exception as ex:
            print(f"  {enc}: decode error {ex}"); continue
        words = WORD.findall(t)
        words = [w for w in words if len(w) >= 4]
        cjk = len(CJK.findall(t)); kana = len(KANA.findall(t)); han = len(HAN.findall(t))
        sample = "  ".join(words[:12])
        print(f"  {enc:9} cjk={cjk:4} kana={kana:4} hangul={han:4} words>=4={len(words):4} | {sample[:90]}")
