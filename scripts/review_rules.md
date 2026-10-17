# Review rules (orchestrator)

Lessons from building Ch1–3 by hand. Apply them at each REVIEW step of `pipeline.py`.
Guiding principle: **better to omit than mislead.** A missing card or a missing official
line costs little; a wrong one teaches the wrong thing.

## divergence-review — `sense_divergent_ch{N}.json`
- Words in `sense_divergent_ch{N}_flags.json` are already kept out of the divergent set. Confirm
  the flags look like real misparses.
- Remove any remaining divergent word that is really a tokenizer misparse:
  - Kansai negation へん / ひん (忘れへん → 辺, 通じひん → 干る)
  - copula やろ / やろう (→ 野郎)
  - ねん (あんねん → 餡)
  - おかしない (→ 犯す)
  - compound fragments (プレイボーイ → プレー)
  - set phrases with no matching candidate (その分 → 分, 名実ともに → 共)
- Keep a word divergent only if a learner who knows its taught gloss would be genuinely misled.

## polish-review — `gloss_polish_ch{N}_flags.json` + `name_leak_scan.py`
- Drop genuine mistags with `drop_cards.py N word…`, BEFORE update_taught. 餡 recurs (dropped
  in ch2 and ch3). Other past drops: ころ (コロっと), つく (について), 引け (手を引く).
- `name_leak_scan.py` is noisy. Act only on real name collisions (錦 = Nishiki, not
  "brocade"). For those: add the name to `data/name_block.json` AND drop the card.
- Place names split by the tokenizer leak as their pieces: 蒼天堀 → 蒼天 "blue sky" + 堀 "moat"
  (found in Ch3 and fixed during Ch4). Watch for this with every multi-kanji place or org name.
  If a leak is found in an already-finished chapter: block it, `drop_cards.py`, remove it from
  the ledger, and set `ledger_words` in `data/pipeline/invariants.json` to the new count, then
  `build_final.py N` (GUID-checked).
- Set-phrase readings with the wrong gloss: 一丁 ("one round; let's give it a shot") was glossed
  as 丁 "counter for long narrow things". Fix the gloss in place.
- Fix an obviously wrong gloss directly in `gloss_polish_ch{N}.json` (e.g. 然も → "as if;
  seemingly").
- More than ~10% of a chapter's cards flagged = something systematic → stop and tell the user.
  Count only GENUINE mistags. Agents also flag borderline notes (idioms, loanword fragments),
  which should get a gloss fix, not a drop. Ch4 (Kansai-heavy): 34 flags, 19 drops (6%).
- More Kansai misparse patterns (Ch4): やと → 野兎, てんねん → 天然, (ええと)こや → 小屋,
  やのうて(な) → 台, ちごた (違った) → 稚児, あない (あんな) → 案内, 食えん → 食, plus Kansai
  adverbial/verb stems lemmatized as nouns (早よ → 早, 軽なる → 軽, 払たる → 払い). Also
  美味しそう → 美味 and もみ返し → 籾 + 返し.
- Loanword fragments of a compound (ドレス|コード, ゴッド|ハンド, ブレイク|ダンス): keep them, with a
  gloss that names the compound.

## regate-review — accepts from the ±5 re-gate
- Accept loose localizations of the SAME beat: rewording, jokes, slang, inserted names, merged lines.
- Reject a reply, the next or previous thought, or a line that only shares a topic or a name.
- Sentence twins (same sentence, different target word) must agree.

## bracket-review — bracket accepts after the strict verifier
- The bracket framing makes the gate lenient, which is why the verifier exists. Read its vetoes.
  It errs cautious (e.g. creative localizations of puns), and that's acceptable.
- In context, two-part sentences mapped onto one two-part official line are fine
  (Ch1 #124/#125).
- Veto rate above 15%, or surviving accepts that look like different statements → look at the
  whole batch, not a sample.

## Never
- Never modify `cards_ch1_1.json` (frozen), or rebuild ch1/ch2 with `build_deck.py`.
- Never `git add -A`; `pipeline.py` commits by explicit path.
- Never "fix" a HALT by deleting the check that raised it. Explain it to the user.

## Stop and ask the user when
- `pipeline.py` HALTs: a protected file changed, GUIDs were lost, the official-line rate is
  below 50%, or an agent output was invalid twice.
- A review finds something systematic rather than a one-off.
- Anything would require rebuilding an already-finished chapter.
