# Corpus text-class source

`text_small.txt` and `text_large.txt` are sliced directly from a single
real, public-domain English novel, downloaded and processed
programmatically by `scripts/build_corpus.py` (no hand-edited or
AI-generated substitute text).

## Source

- **Title:** Pride and Prejudice
- **Author:** Jane Austen
- **First published:** 1813 (United Kingdom)
- **Project Gutenberg eBook #:** 1342
- **Edition used:** Project Gutenberg plain-text UTF-8 edition (the
  George Allen / illustrated edition transcription, with a preface by
  George Saintsbury and illustrations by Hugh Thomson; only the prose
  text is used here, no illustrations)
- **Gutenberg release date:** June 1, 1998; most recently updated
  February 10, 2026
- **URL fetched by `scripts/build_corpus.py`:**
  https://www.gutenberg.org/cache/epub/1342/pg1342.txt
- **Ebook info page:** https://www.gutenberg.org/ebooks/1342

## Public-domain status

Unambiguous. *Pride and Prejudice* was first published in 1813 and its
author, Jane Austen, died in 1817 — the work has been in the public
domain in the United States (and everywhere else copyright follows a
life+70-years or shorter term) for well over a century, far outside any
disputed post-1929 US copyright-renewal question. Project Gutenberg's
own distribution of this text is explicitly released under the terms of
the Project Gutenberg License, which permits free copying and reuse.

## How the raw download was turned into the corpus files

`scripts/build_corpus.py`'s `fetch_novel_text()`:

1. Downloads the URL above.
2. Locates the novel's actual opening line, `"It is a truth universally
   acknowledged, that a single man in possession..."`, and discards
   everything before it — this drops the Gutenberg legal
   boilerplate header and the illustrated edition's preface /
   table-of-contents / illustration-list front matter, so the corpus
   files contain only Austen's actual narrative prose, not editorial or
   licensing text.
3. Discards everything from the `*** END OF THE PROJECT GUTENBERG EBOOK
   ***` marker onward (the Gutenberg license appendix).
4. The remaining novel body is ~717 KB of UTF-8 text — comfortably
   larger than both the ~10 KB and ~200 KB targets, so no repetition was
   needed. `slice_to_size()` takes a prefix of this body and trims back
   to the nearest preceding whitespace/newline so no word or multi-byte
   UTF-8 character is cut mid-way, producing `text_small.txt` (10,238
   bytes) and `text_large.txt` (204,799 bytes).

## Integrity checksums

`CHECKSUMS.sha256` holds SHA-256 hashes of all 6 frozen corpus files,
generated after the `corpus-v1-frozen` git tag was created. It documents
the exact frozen byte content independent of git (e.g. if `data/corpus/`
is ever copied out on its own for the thesis appendix), and lets anyone
re-verify the corpus hasn't drifted with:

    shasum -a 256 -c data/corpus/CHECKSUMS.sha256

## Reference paper context (not load-bearing for file generation)

*A New Look at the Classical Entropy of Written English*
(https://arxiv.org/pdf/0911.2284) reports higher-order character-model
entropy estimates for English text in roughly the 1-1.5 bits/character
range. This project's `shannon_entropy()` (reused from
`scripts/measure_entropy_periodicity.py`) computes a much simpler
order-0 byte-frequency histogram entropy, with no context/n-gram
modelling, which is a looser (higher) bound than that paper's figure —
consistent with `baseline_entropy.csv` showing `text_small.txt` /
`text_large.txt` at roughly 4.6-4.7 bits/byte, well above the paper's
higher-order estimate but still clearly separated from the ~8 bits/byte
of the random files, which is the entropy-class signal this thesis
actually depends on.
