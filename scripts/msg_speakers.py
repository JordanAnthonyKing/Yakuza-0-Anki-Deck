"""Per-message speakers from a Yakuza 0 .msg file.

.msg layout (big-endian, reverse-engineered 2026-10-17):
  header u32 @0x10 -> name table: u32 pointers to NUL-terminated strings (speaker names,
                      mixed in with Talk_* emotion tags, voice ids, animation names);
                      header u16 @0x0e = name-table entry count.
  message records  -> 12 bytes {u32 text_offset, u32 command_block, u16, u8, u8}; found by
                      looking up each text's offset in the header area.
  command block    -> 16-byte commands; the first with bytes [0x02, 0x00] is the speaker
                      command, u16 @+8 = name-table index. Variant 0x02 0x04 = no speaker.
The old extract_dialogue took the LAST short name-like run in the whole file and stamped it
on every line, so nearly every speaker label was wrong.

  messages(path) -> [(text, speaker)]   text = raw message (sub-lines joined by \\r\\n)
"""
import re, struct

JP = re.compile(r"[぀-ヿ一-龯]")

def _cstr(d, o):
    return d[o:d.index(b"\x00", o)].decode("utf-8", "replace")

def _names(d):
    n_names = struct.unpack(">H", d[0x0e:0x10])[0]
    tbl = struct.unpack(">I", d[0x10:0x14])[0]
    names = []
    for i in range(n_names):
        p = tbl + 4 * i
        if p + 4 > len(d):
            break
        o = struct.unpack(">I", d[p:p + 4])[0]
        names.append(_cstr(d, o) if o < len(d) else "")
    return names

def names(path):
    """The file's name table. The wdr/ (official English) copy of a file is index-parallel,
    so names(en_path)[i] is the localized form of names(ja_path)[i]."""
    d = open(path, "rb").read()
    return _names(d) if len(d) >= 0x24 else []

def records(path):
    """ALL message texts in record order (no language filter). The wdr/ (official English)
    copy is record-parallel: records(en)[i] is the localization of records(ja)[i]."""
    d = open(path, "rb").read()
    if len(d) < 0x24:
        return []
    recs, first_text = {}, len(d)
    for r in range(0x18, len(d) - 12, 4):
        if r >= first_text:
            break
        t, c = struct.unpack(">II", d[r:r + 8])
        if (0 < c < t < len(d) and c % 4 == 0 and d[t - 1] == 0
                and d[c:c + 4] == b"\x01\x00\x00\x00" and t not in recs):
            recs[t] = c
            first_text = min(first_text, t)
    return [_cstr(d, t) for t in sorted(recs)]

def messages(path):
    d = open(path, "rb").read()
    if len(d) < 0x24:
        return []
    names = _names(d)
    # record table sits between the header and the first text; index it by text offset
    # (a valid command block opens with an 01 00 00 00 command); stop once we reach text
    recs, first_text = {}, len(d)
    for r in range(0x18, len(d) - 12, 4):
        if r >= first_text:
            break
        t, c = struct.unpack(">II", d[r:r + 8])
        if (0 < c < t < len(d) and c % 4 == 0 and d[t - 1] == 0
                and d[c:c + 4] == b"\x01\x00\x00\x00" and t not in recs):
            recs[t] = c
            first_text = min(first_text, t)
    cmd_starts = sorted(set(recs.values()))
    out = []
    for t, c in sorted(recs.items()):
        text = _cstr(d, t)
        if not JP.search(text):
            continue
        nxt = next((x for x in cmd_starts if x > c), c + 16 * 24)
        spk = ""
        for k in range(c, min(nxt, len(d) - 16), 16):
            if d[k] == 0x02 and d[k + 1] == 0x00:
                idx = struct.unpack(">H", d[k + 8:k + 10])[0]
                if idx < len(names) and JP.search(names[idx]):
                    spk = names[idx]
                break
        out.append((text, spk))
    return out

if __name__ == "__main__":
    import sys
    for t, s in messages(sys.argv[1])[: int(sys.argv[2]) if len(sys.argv) > 2 else 20]:
        print(f"[{s or '-'}] {t.replace(chr(13) + chr(10), ' ')[:70]}")
