"""Per-card full text box + game voice clip for a story chapter.

A .msg message = one text box = one voice clip; its \\r\\n sub-lines are just wraps inside
the box. Cards hold one sub-line, so each card gets:
  full : the whole box (sub-lines joined by <br>), the card's sub-line wrapped in
         <span class="hl">, the target word kept as <b> (bold+highlight via CSS)
  clip : mp3 of the box's voice line, or "" when the line is unvoiced
Clips come from the .msg voice command (03 35 -> ACB id + cue index, see vmap2.json built by
voice2.py map), streamed from se.cpk, decoded with vgmstream, encoded with ffmpeg.

Usage: python scripts/audio/sentence_audio.py <ch>   -> data/audio/sentence_ch<ch>.json
                                                      + data/audio/clips/y0v_<acb>_<cue>.mp3
"""
import os, sys, re, json, shutil, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import index

R = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(R, "data", "audio")
CLIPS = os.path.join(D, "clips")
SE = r"C:\Program Files (x86)\Steam\steamapps\common\Yakuza 0\media\data\soundcpk\se.cpk"
VG = os.path.join(R, "tools", "vgmstream", "vgmstream-cli.exe")

def plain(s):
    return re.sub(r"<[^>]*>", "", s)

def find_message(vm, card):
    """(message text, voice) for the card's sub-line, searched in its own .msg file."""
    s = plain(card["sentence"]).strip()
    for text, v in vm.get(card.get("uid", ""), []):
        if s and s in text:
            return text, v
    return None, None

def full_html(text, card):
    """Whole box with the card's sub-line highlighted (its <b>word</b> markup kept)."""
    s = plain(card["sentence"]).strip()
    i = text.find(s)
    body = text[:i] + '<span class="hl">' + card["sentence"].strip() + "</span>" + text[i + len(s):]
    return body.replace("\r\n", "<br>")

def clip_name(v):
    return f"y0v_{v['acb']}_{v['cue']}.mp3"

def make_clips(need):
    """need: {acb: {cue,...}} -> writes missing mp3s into CLIPS."""
    os.makedirs(CLIPS, exist_ok=True)
    todo = {a: cs for a, cs in need.items()
            if any(not os.path.exists(os.path.join(CLIPS, clip_name({"acb": a, "cue": c}))) for c in cs)}
    if not todo:
        return
    _, idx = index(SE)
    with open(SE, "rb") as f, tempfile.TemporaryDirectory() as tmp:
        for a, cues in todo.items():
            off, size = idx[int(a, 16)]
            f.seek(off)
            wd = os.path.join(tmp, a); os.makedirs(wd)
            open(os.path.join(wd, a + ".awb"), "wb").write(f.read(size))
            shutil.copy(os.path.join(D, "soundpar", a + ".acb"), wd)   # gives vgmstream the cue names
            subprocess.run([VG, "-S", "0", "-o", "?n.wav", a + ".awb"], cwd=wd, capture_output=True)
            for c in cues:
                wav = os.path.join(wd, c + ".wav")
                if os.path.exists(wav):
                    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-ac", "1",
                                    "-codec:a", "libmp3lame", "-b:a", "64k",
                                    os.path.join(CLIPS, clip_name({"acb": a, "cue": c}))], check=True)

def main(ch):
    vm = json.load(open(os.path.join(D, "vmap2.json"), encoding="utf-8"))
    cards = json.load(open(os.path.join(R, "data", f"cards_ch{ch}_{ch}.json"), encoding="utf-8"))
    out, need, nfull = {}, {}, 0
    for c in cards:
        text, v = find_message(vm, c)
        if text is None:
            continue
        rec = {"full": full_html(text, c), "clip": ""}; nfull += 1
        if v and v.get("cue"):
            rec["clip"] = clip_name(v)
            need.setdefault(v["acb"], set()).add(v["cue"])
        out[str(c["order"])] = rec
    make_clips(need)
    for rec in out.values():                       # drop clips that failed to decode
        if rec["clip"] and not os.path.exists(os.path.join(CLIPS, rec["clip"])):
            rec["clip"] = ""
    json.dump(out, open(os.path.join(D, f"sentence_ch{ch}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"ch{ch}: {len(cards)} cards, {nfull} with full box, "
          f"{sum(bool(r['clip']) for r in out.values())} with clip")

if __name__ == "__main__":
    main(int(sys.argv[1]))
