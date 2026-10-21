"""
scripts/build_corpus.py

DO NOT MODIFY corpus after freezing -- see git tag corpus-v1-frozen.

M3 -- Test Corpus Construction. Builds the frozen 3-class x 2-size test
dataset used throughout the thesis (text / JSON / random, ~10 KB and
~200 KB each) under data/corpus/, spanning the entropy spectrum from
structured text to random binary (see docs/milestone_plan.md's M3
section for the full spec and exit criteria).

Data classes produced:
- text_small.txt / text_large.txt: real public-domain English prose,
  sliced from Jane Austen's "Pride and Prejudice" (Project Gutenberg
  eBook #1342, plain-text UTF-8 edition). See data/corpus/SOURCES.md
  for the exact source, edition, URL, and public-domain justification
  (first published 1813, author died 1817 -- unambiguously pre-1929).
- json_small.json / json_large.json: synthetic, programmatically
  generated structured application-log data (JSON array of log-entry
  objects), deterministic per a fixed random seed.
- random_small.bin / random_large.bin: os.urandom() output -- the
  high-entropy reference point at the opposite end of the spectrum.

Entropy: computed with shannon_entropy(), reused verbatim (not
reimplemented -- see the M3 milestone rule requiring this) from
scripts/measure_entropy_periodicity.py, and written to
data/corpus/baseline_entropy.csv (columns: filename, size_bytes,
entropy_bits_per_byte).

Reference paper (context only, not load-bearing for the code): "A New
Look at the Classical Entropy of Written English",
https://arxiv.org/pdf/0911.2284 -- reports computed English-text entropy
figures in roughly the 1-1.5 bits/character range for higher-order
models; this project's simple byte-frequency Shannon entropy (order-0,
no context modelling) lands substantially higher than that (see
baseline_entropy.csv), which is expected -- order-0 byte entropy is a
weaker/looser bound than the higher-order character-model entropy that
paper computes, not a comparable-methodology figure.

Run from the `project/` directory:
    python3 scripts/build_corpus.py
"""

import csv
import json
import os
import random
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from measure_entropy_periodicity import shannon_entropy  # reused, not reimplemented

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data", "corpus"))

TARGET_SMALL_BYTES = 10 * 1024   # ~10 KB
TARGET_LARGE_BYTES = 200 * 1024  # ~200 KB

GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/1342/pg1342.txt"
NOVEL_START_MARKER = "It is a truth universally acknowledged"
GUTENBERG_END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"

JSON_SEED = 20260816

LOG_ACTIONS = ["login", "logout", "upload", "download", "delete", "update", "create", "view"]
LOG_STATUSES = ["ok", "error", "timeout", "denied"]


def fetch_novel_text() -> str:
    """
    Download the plain-text Project Gutenberg edition of "Pride and
    Prejudice" and strip it down to the actual novel body: drop the
    Gutenberg legal boilerplate header/footer and the illustrated
    edition's preface/table-of-contents front matter, starting at the
    novel's real opening line ("It is a truth universally acknowledged
    ..."). See data/corpus/SOURCES.md for the full source citation.
    """
    with urllib.request.urlopen(GUTENBERG_URL, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    start = raw.index(NOVEL_START_MARKER)
    end = raw.index(GUTENBERG_END_MARKER)
    return raw[start:end]


def slice_to_size(text: str, target_bytes: int) -> str:
    """
    Return a prefix of `text` whose UTF-8 encoding is within a few bytes
    of target_bytes, cut back to the nearest preceding whitespace so a
    word (or multi-byte character) isn't split mid-way. Repeats the text
    defensively if it's shorter than target_bytes (not expected for this
    source -- the novel body is ~700 KB, comfortably larger than both
    the ~10 KB and ~200 KB targets).
    """
    encoded = text.encode("utf-8")
    if len(encoded) < target_bytes:
        reps = target_bytes // len(encoded) + 1
        encoded = (text * reps).encode("utf-8")

    cut = encoded[:target_bytes]
    # Back off over any dangling UTF-8 continuation bytes (10xxxxxx) so we
    # don't decode a truncated multi-byte character.
    while cut and (cut[-1] & 0xC0) == 0x80:
        cut = cut[:-1]
    decoded = cut.decode("utf-8", errors="ignore")

    last_space = decoded.rfind(" ")
    last_newline = decoded.rfind("\n")
    cut_at = max(last_space, last_newline)
    if cut_at != -1:
        decoded = decoded[:cut_at]
    return decoded.rstrip() + "\n"


def build_json_corpus(target_bytes: int, seed: int) -> str:
    """
    Generate a JSON array of synthetic application-log entries, growing
    it one entry at a time until its serialized size reaches
    target_bytes. Deterministic per `seed` so the frozen corpus is
    reproducible from this script.
    """
    rng = random.Random(seed)
    entries = []
    serialized = "[]"
    while len(serialized.encode("utf-8")) < target_bytes:
        idx = len(entries) + 1
        entries.append(
            {
                "event_id": idx,
                "user": f"user{rng.randint(1, 500)}",
                "action": rng.choice(LOG_ACTIONS),
                "status": rng.choice(LOG_STATUSES),
                "timestamp": 1700000000 + idx * rng.randint(1, 120),
                "ip": f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
                "session": "".join(rng.choice("0123456789abcdef") for _ in range(16)),
                "duration_ms": rng.randint(5, 4000),
                "bytes_transferred": rng.randint(0, 500000),
            }
        )
        serialized = json.dumps(entries, indent=2)
    return serialized


def write_bytes(filename: str, data: bytes) -> str:
    path = os.path.join(CORPUS_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path


def main():
    os.makedirs(CORPUS_DIR, exist_ok=True)

    print(f"Fetching novel text from {GUTENBERG_URL} ...")
    novel_text = fetch_novel_text()
    print(f"  novel body: {len(novel_text.encode('utf-8'))} bytes (before slicing)")

    text_small = slice_to_size(novel_text, TARGET_SMALL_BYTES)
    text_large = slice_to_size(novel_text, TARGET_LARGE_BYTES)

    json_small = build_json_corpus(TARGET_SMALL_BYTES, seed=JSON_SEED)
    json_large = build_json_corpus(TARGET_LARGE_BYTES, seed=JSON_SEED + 1)

    random_small = os.urandom(TARGET_SMALL_BYTES)
    random_large = os.urandom(TARGET_LARGE_BYTES)

    files = [
        ("text_small.txt", text_small.encode("utf-8")),
        ("text_large.txt", text_large.encode("utf-8")),
        ("json_small.json", json_small.encode("utf-8")),
        ("json_large.json", json_large.encode("utf-8")),
        ("random_small.bin", random_small),
        ("random_large.bin", random_large),
    ]

    rows = []
    for filename, data in files:
        path = write_bytes(filename, data)
        size_bytes = len(data)
        entropy = shannon_entropy(data)
        rows.append((filename, size_bytes, entropy))
        print(f"  wrote {path} ({size_bytes} bytes, entropy={entropy:.4f} bits/byte)")

    csv_path = os.path.join(CORPUS_DIR, "baseline_entropy.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "size_bytes", "entropy_bits_per_byte"])
        for filename, size_bytes, entropy in rows:
            writer.writerow([filename, size_bytes, f"{entropy:.6f}"])
    print(f"  wrote {csv_path}")


if __name__ == "__main__":
    main()
