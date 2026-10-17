import os, re, glob, collections
WDR_MSG = r"C:\Users\jordan\AppData\Local\Temp\claude\C--Users-jordan-repos-yakuza\e95fc621-2dfc-4b91-a256-e630facafb68\scratchpad\wdrj\msg"
CODE = re.compile(rb"([abcf])([0-9]{2})[_-]([0-9]{3})")
JP   = re.compile(rb"(?:\xe3[\x81-\x83]|\xe4|\xe5|\xe6|\xe7|\xe8|\xe9)")  # rough UTF-8 JP lead bytes

files = glob.glob(os.path.join(WDR_MSG, "**", "*.msg"), recursive=True)
chap_files = collections.Counter()
prefix_counter = collections.Counter()
files_with_code = 0
uid_ranges_with_code = collections.Counter()
scene_set = set()
for p in files:
    d = open(p,"rb").read()
    codes = CODE.findall(d)
    if codes:
        files_with_code += 1
        uid = re.search(r"uid([0-9a-f]{8})", os.path.basename(p)).group(1)
        uid_ranges_with_code[uid[:2]] += 1
        chaps=set()
        for pre,ch,sc in codes:
            prefix_counter[pre.decode()] += 1
            scene_set.add((pre.decode(),ch.decode(),sc.decode()))
            chaps.add(int(ch))
        for c in chaps: chap_files[c]+=1

print(f"total msg: {len(files)}; files carrying a scene code: {files_with_code}")
print("scene-code prefixes seen:", dict(prefix_counter))
print("uid top-byte of code-carrying files:", dict(uid_ranges_with_code))
print(f"unique scenes referenced: {len(scene_set)}")
print("\nmsg files per chapter (via embedded cutscene code):")
for c in range(0,18):
    if chap_files.get(c): print(f"  ch{c:02}: {chap_files[c]}")
