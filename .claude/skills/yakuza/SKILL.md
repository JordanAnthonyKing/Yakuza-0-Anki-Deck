---
name: yakuza
description: Run, resume, pause or stop the Yakuza 0 Anki deck pipeline (story chapters 3–17). Use when the user says "resume", "carry on", "continue", "let's go", "start the pipeline" — or "halt", "pause", "stop", "I'm shutting down", "done for tonight" — or asks how far the pipeline has got. Also /yakuza.
---

# Yakuza deck pipeline — orchestrator runbook

You are the orchestrator. `scripts/pipeline.py` is the single source of truth. It derives all
state from disk, runs the deterministic steps, validates and commits agent outputs, and tells you
the next AGENT job or REVIEW. You spawn agents, do reviews, and watch for trouble. Keep your own
token use low: be quiet between steps, and use one-line spawn prompts.

Run Python as `.venv/Scripts/python.exe` from the repo root (`C:\Users\jordan\repos\yakuza`).

## RESUME ("resume", "carry on", "let's go", …)
1. `python scripts/pipeline.py status`. If it shows HALTED, explain the HALT to the user in plain
   words and stop. Don't clear it yourself unless they say so (`pipeline.py clear-halt`).
2. Loop:
   - `python scripts/pipeline.py advance`. It runs every ready deterministic step, then prints ONE of:
     - `JOB ch{N} {step} model=… prompt=… input=… output=…`: spawn ONE background agent
       (subagent_type general-purpose, `model` as given) with exactly:
       `Follow the instructions in C:\Users\jordan\repos\yakuza\<prompt> exactly. INPUT: <input>  OUTPUT: <output>`
       Then wait. You are re-invoked when it finishes. Don't poll, and don't read its transcript.
       On its completion notification, go back to `advance` (it validates the output; an invalid
       output is re-offered once, then HALTs).
     - `REVIEW ch{N} {step}: …`: do the review yourself, following `scripts/review_rules.md`.
       Then `python scripts/pipeline.py mark {N} {step}` and continue the loop.
     - `HALT: …`: stop the loop and tell the user what needs their attention.
     - `DONE`: all story chapters are complete. Tell the user.
   - When a chapter completes (`[chN] COMPLETE: …`), give the user a one-line note
     (cards, official %) and keep going.
3. **One agent at a time** by default: it wastes the least when a usage limit hits. Only if the
   user explicitly asks to go faster (e.g. "I've only got an hour") may you run two jobs from the
   same agent step at once. Never run jobs from different steps together.

## Usage limits
The interactive session waits at a usage limit and continues by itself after the reset
(`autoContinueAtUsageLimit`, on by default). If an agent died at the limit, its output was
never written, and `advance` simply re-offers the job. Nothing else to do.

## HALT ("halt", "pause", "stop", "shutting down", "done for tonight", …)
1. Spawn nothing new.
2. If an agent is running: if the user is about to shut down, stop it (TaskStop). Its output was
   never written (agents write once, at the end), so it is redone on resume. If they aren't in a
   hurry, offer to let it finish first.
3. Commit anything the pipeline left uncommitted: run `python scripts/pipeline.py advance` only
   if no agent is running (it commits validated outputs). Otherwise leave it; resume validates.
   Never `git add -A`.
4. Reply in ONE line: where things stand (`pipeline.py status`) and that it's safe to shut down.

## Rules
- Never edit `cards_ch1_1.json`, never rebuild ch1/ch2, never weaken a check to get past a HALT.
- Record new lessons (new misparse patterns, new failure modes) in `scripts/review_rules.md`, and
  in memory if they matter beyond this pipeline.
- Stop and ask the user whenever `review_rules.md` says to.
