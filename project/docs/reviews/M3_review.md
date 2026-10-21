# M3 Review — Test Corpus Construction

Date: 2026-08-18
Reviewer: independent review subagent (milestone-reviewer methodology),
first cycle — no retries needed.

## Verdict: PASS

## Exit criteria checklist

| Criterion | Command | Result |
|---|---|---|
| All 6 files exist under `data/corpus/`, each within ±10% of target size | `ls -la project/data/corpus/` | All 6 present, all within ±1% of the 10 KB/200 KB targets (json_small +0.71% was the largest deviation) |
| `baseline_entropy.csv` shows text/JSON < ~6.5 bits/byte, random > ~7.9 bits/byte | Independently recomputed entropy for all 6 files via `shannon_entropy()` imported live from `scripts/measure_entropy_periodicity.py` | Reviewer's own numbers matched `baseline_entropy.csv` to 6 decimal places. text/JSON 4.52–4.73, random 7.98–8.00 — both bands satisfied |
| Git tag `corpus-v1-frozen` exists and points at the commit containing the corpus | `git log --oneline --all`, `git rev-parse corpus-v1-frozen` / `HEAD`, `git show --stat corpus-v1-frozen`, `git status` | Exactly 2 commits total (M0 + M3, as expected). Tag points at HEAD. Commit touches only `project/data/corpus/*` — 8 files. No scope creep: `src/`, `tests/`, `docs/`, `project/data/aes_key.bin`, `project/data/reference_sequence.txt` all still untracked |

Full suite independently re-run: `pytest tests/ -v` → **20/20 passed**, unaffected by M3.

## Design concerns (surfaced despite PASS)

- **Content quality checked directly, not just its entropy number.** Reviewer
  read the actual text and confirmed `text_small.txt`/`text_large.txt` open
  exactly at Austen's real opening line, with no Gutenberg boilerplate or
  preface leakage. Reviewer independently re-fetched the live Gutenberg URL
  and confirmed the implementation's front-matter-skip marker occurs
  exactly once, in the expected place — the slicing logic is sound, not
  merely lucky on this run.
- **Reproducibility verified byte-for-byte**, not just claimed: reviewer
  reran the corpus-generation logic against a fresh Gutenberg download and
  got exact byte-for-byte matches against all 4 frozen text/JSON files
  (after accounting for CRLF line endings, faithfully inherited from the
  Gutenberg source).
- **`json_large.json` confirmed genuinely distinct from `json_small.json`**,
  not a repeat-to-pad shortcut: different RNG seeds, zero duplicate
  records, `json_small`'s content does not appear as a substring of
  `json_large`. This was worth checking explicitly — a verbatim-repeat
  shortcut would have hit the same size/entropy targets while being much
  less representative of real structured data variety.
- **Public-domain reasoning in SOURCES.md is correct but loosely worded**
  (blends the "life+70" and pre-1929-US-publication rules in one sentence
  without clearly separating which applies here). Not a factual error,
  worth tightening before this text is reused in the thesis.
- **`build_corpus.py`'s live Gutenberg fetch is not checksum-pinned.** Poses
  no risk to the already-frozen, git-tagged corpus (reviewer confirmed
  today's live fetch still reproduces it exactly), but if the script is
  ever rerun after Gutenberg revises that file again, it would silently
  produce a different corpus rather than failing loudly. Worth a checksum
  guard if `build_corpus.py` is ever expected to be rerun rather than
  treated as a one-time, now-historical script.

## Required fixes

None. No retry cycle was needed.
