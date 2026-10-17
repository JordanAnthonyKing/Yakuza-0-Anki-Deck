"""Single source of truth for the per-chapter deck pipeline (story chapters 3-17).

All state is derived from files on disk + marker files in data/pipeline/ch{N}/, so any
session can pick up exactly where the last one stopped (cutoff, usage limit, "halt").

  python pipeline.py status            one line per chapter + the next action
  python pipeline.py advance           run every ready deterministic step (validating and
                                       committing as it goes), then print the next AGENT job
                                       or REVIEW for the orchestrator — or DONE / HALT
  python pipeline.py mark <ch> <step>  record a finished review (commits)
  python pipeline.py clear-halt        after the user has dealt with a HALT

Agent jobs are idempotent: a job is done iff its output exists AND validates. An invalid
output is renamed *.invalid and the job is re-offered; a second failure HALTs. Commits are
by explicit path only (never `git add -A`), so nothing in flight is swept in.
"""
import os, re, sys, json, glob, math, shutil, hashlib, subprocess

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
SCRIPTS = os.path.join(REPO, "scripts")
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
PIPE = os.path.join(DATA, "pipeline")
HALT = os.path.join(PIPE, "HALT.md")
CHAPTERS = range(3, 18)                 # ch1-2 were finished by hand before the pipeline
MODEL = {"divergence": "sonnet", "polish": "sonnet", "translate": "opus", "gate": "opus",
         "verify": "opus"}
PROMPT = {"divergence": "divergence_prompt.txt", "polish": "polish_prompt.txt",
          "translate": "translate_prompt.txt", "gate": "gate_prompt.txt",
          "verify": "verify_prompt.txt"}
OFFICIAL_MIN, VETO_MAX = 0.50, 0.15     # anomaly thresholds -> HALT / flag for review


# ---------------------------------------------------------------- helpers
def rel(p):
    return os.path.relpath(p, REPO).replace(os.sep, "/")

def load(p):
    return json.load(open(p, encoding="utf-8"))

def work(ch, *parts):
    return os.path.join(DATA, "work", f"ch{ch}", *parts)

def mpath(ch, step):
    return os.path.join(PIPE, f"ch{ch}", f"{step}.done")

def marked(ch, step):
    return os.path.exists(mpath(ch, step))

def mark(ch, step, note=""):
    os.makedirs(os.path.dirname(mpath(ch, step)), exist_ok=True)
    open(mpath(ch, step), "w", encoding="utf-8").write(note)

def ledger_chapters():
    return load(os.path.join(DATA, "taught_words.json"))["built_chapters"]

def run(args):
    r = subprocess.run([PY, *args], cwd=SCRIPTS, capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    out = (r.stdout + r.stderr).strip()
    if r.returncode:
        raise RuntimeError(f"`{' '.join(args)}` failed:\n{out[-1500:]}")
    return out

def commit(paths, msg):
    # explicit paths only; drop ones that don't exist (git add fails the whole call otherwise)
    paths = [p for p in paths if glob.glob(os.path.join(REPO, p))]
    if paths:
        subprocess.run(["git", "add", "--", *paths], cwd=REPO, capture_output=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO).returncode:
        subprocess.run(["git", "commit", "-q", "-m",
                        f"{msg}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"],
                       cwd=REPO, capture_output=True)

def halt(reason):
    os.makedirs(PIPE, exist_ok=True)
    open(HALT, "w", encoding="utf-8").write(reason + "\n")
    commit([rel(HALT)], "pipeline: HALT")
    print(f"HALT: {reason}")
    sys.exit(2)


# ---------------------------------------------------------------- invariants
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else ""

def invariants():
    """protected state must never shrink / change; baseline recorded on first run"""
    ip = os.path.join(PIPE, "invariants.json")
    dia = load(os.path.join(DATA, "dialogue_by_chapter.json"))
    now = {"dialogue_lines": sum(len(v) for v in dia.values()),
           "ch1_cards_sha": sha(os.path.join(DATA, "cards_ch1_1.json")),
           "ledger_words": len(load(os.path.join(DATA, "taught_words.json"))["entries"])}
    if not os.path.exists(ip):
        os.makedirs(PIPE, exist_ok=True)
        json.dump(now, open(ip, "w"), indent=1)
        return
    base = load(ip)
    if now["dialogue_lines"] != base["dialogue_lines"]:
        halt(f"dialogue_by_chapter.json changed: {base['dialogue_lines']} -> {now['dialogue_lines']} lines")
    if now["ch1_cards_sha"] != base["ch1_cards_sha"]:
        halt("FROZEN cards_ch1_1.json was modified")
    if now["ledger_words"] < base["ledger_words"]:
        halt(f"taught ledger shrank: {base['ledger_words']} -> {now['ledger_words']}")
    base["ledger_words"] = now["ledger_words"]
    json.dump(base, open(ip, "w"), indent=1)

def deck_path(ch):
    return os.path.join(DATA, "decks", f"yakuza0_ch{ch}.apkg")

def guid_guard(ch, build):
    """run a deck build; every surviving note must keep its GUID (else Anki duplicates)"""
    sys.path.insert(0, SCRIPTS)
    from keep_guids import old_guids
    before = old_guids(deck_path(ch))
    out = build()
    after = old_guids(deck_path(ch))
    dl = os.path.join(PIPE, f"ch{ch}", "dropped.json")
    dropped = len(load(dl)) if os.path.exists(dl) else 0
    lost = [k for k in before if after.get(k) != before[k]]
    if len(lost) > dropped:
        halt(f"ch{ch} deck rebuild lost {len(lost)} note GUIDs (only {dropped} cards were dropped): "
             f"{lost[:3]}")
    return out


# ---------------------------------------------------------------- agent output validation
def validate(kind, inp, out):
    """None if `out` is a complete, well-formed answer to `inp`, else the problem"""
    try:
        o = load(out)
    except Exception as e:
        return f"unreadable JSON ({e})"
    i = load(inp)
    if not isinstance(o, dict):
        return "not a JSON object"
    if kind in ("divergence", "polish"):
        o.pop("__flags__", None)
        want = {r["word"] for r in i}
        typ = bool if kind == "divergence" else str
    else:
        want = {str(r["order"]) for r in i}
        typ = bool if kind == "verify" else dict
    miss = want - set(o)
    if miss:
        return f"{len(miss)} of {len(want)} items missing (e.g. {sorted(miss)[:3]})"
    bad = [k for k in want if not isinstance(o[k], typ)]
    if kind == "translate":
        bad += [k for k in want if isinstance(o[k], dict) and not (o[k].get("literal") or "").strip()]
    if kind in ("translate", "gate"):
        bad += [k for k in want if isinstance(o[k], dict) and not isinstance(o[k].get("official_ok"), bool)]
    if bad:
        return f"{len(bad)} malformed items (e.g. {sorted(set(bad))[:3]})"
    return None


# ---------------------------------------------------------------- the step list
def translate_batch_size(ch, maxo):
    """~64 cards per batch, evened out so a chapter never ends in a tiny tail batch (68 cards
    -> one batch, not 64+4). Once range files exist, their layout wins (read from the batch
    that starts at 000), so a chapter never switches sizes midway."""
    first = glob.glob(os.path.join(DATA, "translate", f"ch{ch}", "000-*.json"))
    if first:
        return int(re.search(r"000-(\d+)\.json$", first[0]).group(1)) + 1
    n = maxo + 1
    return -(-n // max(1, round(n / 64)))

def translate_jobs(ch):
    al = load(os.path.join(DATA, f"align_ch{ch}.json"))
    maxo = max(r["order"] for r in al)
    jobs = []
    B = translate_batch_size(ch, maxo)
    for s in range(0, maxo + 1, B):
        e = min(s + B - 1, maxo)
        if not any(s <= r["order"] <= e for r in al):
            continue
        jobs.append(("translate", work(ch, f"tbatch_ch{ch}_{s:03d}-{e:03d}.json"),
                     os.path.join(DATA, "translate", f"ch{ch}", f"{s:03d}-{e:03d}.json")))
    if any(not os.path.exists(i) for _, i, o in jobs if not os.path.exists(o)):
        run(["translate_next.py", str(ch), "999", str(B)])   # (re)write missing inputs
    return jobs

def steps(ch):
    """ordered steps: (name, kind, payload). kind py: (args, commit globs, guarded?);
    agent: [(agent_kind, input, output)]; review: instructions"""
    rg = lambda *p: os.path.join(DATA, "translate", f"regate_ch{ch}", *p)
    vocab_done = ch in ledger_chapters()
    S = []
    if not vocab_done:
        S += [
            ("divergence-prep", "py", (["prep_divergence_batches.py", str(ch), "auto"], [], False)),
            ("divergence", "agent", lambda: [("divergence", p, os.path.join(DATA, f"divergence_ch{ch}_part{re.search(r'_(\d+)\.json$', p).group(1)}.json"))
                                             for p in sorted(glob.glob(work(ch, f"divergence_batch_{ch}_*.json")))]),
            ("divergence-combine", "py", (["combine_divergence.py", str(ch)], [f"data/sense_divergent_ch{ch}*.json"], False)),
            ("divergence-review", "review",
             f"Review data/sense_divergent_ch{ch}.json (+ _flags.json): remove any word that is a tokenizer "
             f"misparse (Kansai へん/ひん/やろう/ねん, compound fragments, set phrases) — see scripts/review_rules.md."),
            ("build", "py", (["build_deck.py", str(ch)], [f"data/cards_ch{ch}_{ch}.json", f"data/decks/yakuza0_ch{ch}.apkg"], False)),
            ("polish-prep", "py", (["prep_polish_batches.py", str(ch), str(ch), "auto"], [], False)),
            ("polish", "agent", lambda: [("polish", p, os.path.join(DATA, f"gloss_polish_ch{ch}_part{re.search(r'_(\d+)\.json$', p).group(1)}.json"))
                                         for p in sorted(glob.glob(work(ch, f"polish_batch_{ch}_*.json")))]),
            ("polish-combine", "py", (["combine_polish.py", str(ch)], [f"data/gloss_polish_ch{ch}*.json"], False)),
            ("polish-review", "review",
             f"Review data/gloss_polish_ch{ch}_flags.json and `name_leak_scan.py` output for ch{ch}; drop "
             f"genuine mistags with `drop_cards.py {ch} <word>...`; fix bad glosses in gloss_polish_ch{ch}.json "
             f"— see scripts/review_rules.md."),
            ("merge-gloss", "py", (["merge_gloss.py", str(ch), str(ch)], [f"data/cards_ch{ch}_{ch}.json", f"data/decks/yakuza0_ch{ch}.apkg", f"data/pipeline/ch{ch}/"], True)),
            ("update-taught", "py", (["update_taught.py", str(ch)], ["data/taught_words.json"], False)),
        ]
    S += [
        ("align", "py", (["build_align.py", str(ch)], [f"data/align_ch{ch}.json"], False)),
        ("translate", "agent", lambda: translate_jobs(ch)),
        # (no ±5 re-gate: that fixed Ch1/Ch2, whose first pass saw a truncated window; from
        # Ch3 on the translate pass already sees the full ±5, so re-gating it repeats itself)
        ("bracket-prep", "py", (["regate.py", "bracket", str(ch)], [f"data/translate/regate_ch{ch}/"], False)),
        ("bracket", "agent", lambda: [("gate", p, p.replace(os.sep + "in_", os.sep + "out_"))
                                      for p in sorted(glob.glob(rg("in_bracket*.json")))]),
        ("verify-prep", "py", (["regate.py", "verify-prep", str(ch)], [f"data/translate/regate_ch{ch}/"], False)),
        ("verify", "agent", lambda: [("verify", rg("verify_in.json"), rg("verify_out.json"))]
                                    if os.path.exists(rg("verify_in.json")) else []),
        ("bracket-review", "review",
         f"Check the verifier's vetoes and ~10 surviving bracket accepts (`pipeline.py sample {ch} bracket`); "
         f"then the pipeline applies vetoes and merges. Veto rate > {VETO_MAX:.0%} = look harder."),
        ("bracket-merge", "py", (None, [f"data/translate/ch{ch}/", f"data/translate/regate_ch{ch}/"], False)),
        ("final", "py", (["build_final.py", str(ch)], [f"data/decks/yakuza0_ch{ch}.apkg", f"data/pipeline/ch{ch}/"], True)),
    ]
    return S


# reviews that have nothing to look at are marked automatically
_rg = lambda ch, pat: glob.glob(os.path.join(DATA, "translate", f"regate_ch{ch}", pat))
REVIEW_SKIP = {
    # nothing to review when the bracket pass accepted nothing
    "bracket-review": lambda ch: not any(v.get("official_ok") for p in _rg(ch, "out_bracket*.json")
                                         for v in load(p).values()),
}


# ---------------------------------------------------------------- driver
def official_rate(ch):
    tr = {}
    for p in glob.glob(os.path.join(DATA, "translate", f"ch{ch}", "*.json")):
        tr.update(load(p))
    al = {str(r["order"]) for r in load(os.path.join(DATA, f"align_ch{ch}.json"))}
    ok = sum(1 for k in al if tr.get(k, {}).get("official_ok"))
    return ok, len(al)

def bracket_merge(ch):
    rg = os.path.join(DATA, "translate", f"regate_ch{ch}")
    out = []
    if os.path.exists(os.path.join(rg, "verify_out.json")):
        out.append(run(["regate.py", "verify-apply", str(ch)]))
        v = load(os.path.join(rg, "verify_out.json"))
        vetoed = sum(1 for x in v.values() if x is False)
        if v and vetoed / len(v) > VETO_MAX:
            out.append(f"WARNING: veto rate {vetoed}/{len(v)} above {VETO_MAX:.0%}")
    out.append(run(["regate.py", "merge", str(ch)]))
    return "\n".join(out)

def chapter_state(ch):
    """(next unfinished step, payload) or (None, None) when the chapter is complete"""
    for name, kind, payload in steps(ch):
        if marked(ch, name):
            continue
        if kind == "agent":
            jobs = payload()
            todo = [j for j in jobs if not os.path.exists(j[2])]
            if todo or any(validate(*j) for j in jobs if os.path.exists(j[2])):
                return name, (kind, jobs)
            mark(ch, name)          # all outputs present + valid
            commit([rel(o) for _, _, o in jobs] + [f"data/pipeline/ch{ch}/"], f"pipeline: ch{ch} {name} done")
            continue
        if kind == "review" and REVIEW_SKIP.get(name, lambda c: False)(ch):
            mark(ch, name, "skipped: nothing to review")
            continue
        return name, (kind, payload)
    return None, None

def advance():
    if os.path.exists(HALT):
        print("HALTED — see data/pipeline/HALT.md; fix, then `pipeline.py clear-halt`.")
        print(open(HALT, encoding="utf-8").read()); sys.exit(2)
    invariants()
    for ch in CHAPTERS:
        while True:
            name, st = chapter_state(ch)
            if name is None:
                break
            kind, payload = st
            if kind == "py":
                args, globs, guarded = payload
                print(f"[ch{ch}] {name} ...")
                try:
                    if name == "bracket-merge":
                        out = bracket_merge(ch)
                    elif guarded:
                        out = guid_guard(ch, lambda: run(args))
                    else:
                        out = run(args)
                except RuntimeError as e:
                    halt(f"ch{ch} step {name}: {e}")
                print("   " + "\n   ".join(out.splitlines()[-4:]))
                mark(ch, name)
                if name == "final":
                    ok, n = official_rate(ch)
                    print(f"[ch{ch}] COMPLETE: {n} cards, {ok} official ({ok * 100 // max(n, 1)}%)")
                    if n and ok / n < OFFICIAL_MIN:
                        commit(globs + [f"data/pipeline/ch{ch}/"], f"pipeline: ch{ch} {name}")
                        halt(f"ch{ch} official-line rate {ok}/{n} below {OFFICIAL_MIN:.0%} — check alignment")
                invariants()
                commit(globs + [f"data/pipeline/ch{ch}/", "data/pipeline/invariants.json"],
                       f"pipeline: ch{ch} {name}")
                continue
            if kind == "agent":
                for k, inp, out in payload:
                    if os.path.exists(out):
                        err = validate(k, inp, out)
                        if not err:
                            continue
                        fails = os.path.join(PIPE, f"ch{ch}", "failures.json")
                        f = load(fails) if os.path.exists(fails) else {}
                        f[rel(out)] = f.get(rel(out), 0) + 1
                        json.dump(f, open(fails, "w"), indent=1)
                        shutil.move(out, out + ".invalid")
                        if f[rel(out)] >= 2:
                            halt(f"ch{ch} {name}: {rel(out)} invalid twice: {err}")
                        print(f"[ch{ch}] {name}: {rel(out)} invalid ({err}) — re-offering the job")
                # commit every validated output from this agent step
                commit([rel(o) for _, _, o in payload if os.path.exists(o)], f"pipeline: ch{ch} {name} output")
                todo = [(k, i, o) for k, i, o in payload if not os.path.exists(o)]
                if todo:
                    k, inp, out = todo[0]
                    print(f"JOB ch{ch} {name} ({len(todo)} left in step) model={MODEL[k]}")
                    print(f"  prompt: scripts/{PROMPT[k]}")
                    print(f"  input : {inp}")
                    print(f"  output: {out}")
                    return
                continue
            if kind == "review":
                print(f"REVIEW ch{ch} {name}: {payload}")
                print(f"  when done: python scripts/pipeline.py mark {ch} {name}")
                return
    print("DONE — all story chapters complete.")

def status():
    if os.path.exists(HALT):
        print("HALTED:", open(HALT, encoding="utf-8").read().strip())
    for ch in CHAPTERS:
        names = [s[0] for s in steps(ch)]
        n_done = sum(marked(ch, s) for s in names)
        name, _ = chapter_state(ch)
        state = "complete" if name is None else f"next: {name}"
        extra = ""
        if name is None or marked(ch, "translate"):
            ok, n = official_rate(ch)
            extra = f"  ({n} cards, {ok} official)"
        vocab = "vocab ✓" if ch in ledger_chapters() else "vocab …"
        print(f"ch{ch:>2}: {vocab}  {n_done}/{len(names)} steps  {state}{extra}")
        if name is not None:
            break                   # later chapters can't start before this one finishes

def sample(ch, tag, n=10):
    import random
    d = os.path.join(DATA, "translate", f"regate_ch{ch}")
    inp = {str(r["order"]): r for p in glob.glob(os.path.join(d, f"in_{tag}*.json")) for r in load(p)}
    out = {}
    for p in glob.glob(os.path.join(d, f"out_{tag}*.json")):
        out.update(load(p))
    if tag == "bracket" and os.path.exists(os.path.join(d, "verify_out.json")):
        v = load(os.path.join(d, "verify_out.json"))
        print("vetoed:", " ".join(k for k, x in v.items() if x is False) or "(none)")
    acc = [k for k, v in out.items() if v.get("official_ok")]
    print(f"{len(acc)}/{len(out)} accepted")
    for k in random.sample(acc, min(n, len(acc))):
        print(f"{k} | {inp[k]['sentence'][:40]}\n   lit: {inp[k]['literal'][:90]}\n   off: {out[k]['official'][:90]}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "advance":
        advance()
    elif cmd == "mark":
        ch, step = int(sys.argv[2]), sys.argv[3]
        if step not in [s[0] for s in steps(ch)]:
            sys.exit(f"unknown step {step}")
        mark(ch, step)
        commit([f"data/pipeline/ch{ch}/", f"data/cards_ch{ch}_{ch}.json", f"data/gloss_polish_ch{ch}.json",
                f"data/sense_divergent_ch{ch}.json", f"data/translate/regate_ch{ch}/"],
               f"pipeline: ch{ch} {step} reviewed")
        print(f"marked ch{ch} {step}")
    elif cmd == "sample":
        sample(int(sys.argv[2]), sys.argv[3])
    elif cmd == "clear-halt":
        if os.path.exists(HALT):
            os.remove(HALT)
            subprocess.run(["git", "rm", "-q", "--cached", "--ignore-unmatch", rel(HALT)], cwd=REPO)
            commit([], "pipeline: halt cleared")
        print("halt cleared")
    else:
        sys.exit(__doc__)
