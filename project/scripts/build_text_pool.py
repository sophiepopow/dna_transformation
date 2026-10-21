"""
scripts/build_text_pool.py

Extends the text-class source pool beyond text_large.txt (204799 bytes,
Pride and Prejudice, Gutenberg #1342), which only allows 19 non-overlapping
10240-byte slices -- not enough for a 50-sample repeated measurement.

Downloads two more public-domain Project Gutenberg prose texts, strips
Gutenberg's own boilerplate (everything outside the "*** START OF ... ***"
/ "*** END OF ... ***" markers), writes the cleaned bodies as new files
under data/corpus/, and appends their SHA-256 checksums to
data/corpus/CHECKSUMS.sha256 in the existing format (sha256<two spaces>filename).

Added texts:
  - Alice's Adventures in Wonderland, Lewis Carroll, Gutenberg #11
    (published 1865, author died 1898) -> data/corpus/text_pool_alice.txt
  - Moby-Dick; or, The Whale, Herman Melville, Gutenberg #2701
    (published 1851, author died 1891) -> data/corpus/text_pool_mobydick.txt

Both are unambiguously public domain by the same standard already
documented in data/corpus/SOURCES.md for Pride and Prejudice (published
well before 1929, authors long deceased, official Gutenberg release
under the Project Gutenberg License).

Does NOT modify text_small.txt, text_large.txt, json_*.json,
random_*.bin, or their existing checksums -- only appends two new lines
to CHECKSUMS.sha256 and adds two new files.

Run from the `project/` directory:
    python3 scripts/build_text_pool.py
"""

import hashlib
import os
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data", "corpus"))
CHECKSUMS_PATH = os.path.join(CORPUS_DIR, "CHECKSUMS.sha256")

START_MARKER = "*** START OF"
END_MARKER = "*** END OF"

TEXTS = [
    {
        "url": "https://www.gutenberg.org/cache/epub/11/pg11.txt",
        "filename": "text_pool_alice.txt",
        "title": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "gutenberg_id": 11,
        "published": 1865,
        "author_died": 1898,
    },
    {
        "url": "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
        "filename": "text_pool_mobydick.txt",
        "title": "Moby-Dick; or, The Whale",
        "author": "Herman Melville",
        "gutenberg_id": 2701,
        "published": 1851,
        "author_died": 1891,
    },
]


def fetch_and_clean(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    start_line_idx = raw.index(START_MARKER)
    start = raw.index("\n", start_line_idx) + 1
    end = raw.index(END_MARKER)
    return raw[start:end].strip() + "\n"


def sha256_of_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run():
    new_manifest_lines = []

    for entry in TEXTS:
        print(f"Fetching {entry['title']} (Gutenberg #{entry['gutenberg_id']}) ...")
        body = fetch_and_clean(entry["url"])
        path = os.path.join(CORPUS_DIR, entry["filename"])
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        size = os.path.getsize(path)
        digest = sha256_of_file(path)
        print(f"  wrote {path} ({size} bytes), sha256={digest}")
        new_manifest_lines.append(f"{digest}  {entry['filename']}\n")

    with open(CHECKSUMS_PATH, "a") as f:
        f.writelines(new_manifest_lines)
    print(f"\nAppended {len(new_manifest_lines)} lines to {CHECKSUMS_PATH}")

    print("\nVerifying all checksums (existing 6 files + 2 new ones) ...")
    with open(CHECKSUMS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            expected_hash, filename = line.split(maxsplit=1)
            path = os.path.join(CORPUS_DIR, filename.strip())
            actual_hash = sha256_of_file(path)
            status = "OK" if actual_hash == expected_hash else "MISMATCH"
            print(f"  {filename}: {status}")
            assert actual_hash == expected_hash, f"checksum mismatch for {filename}"

    total_new_bytes = sum(os.path.getsize(os.path.join(CORPUS_DIR, e["filename"])) for e in TEXTS)
    existing_text_large = os.path.getsize(os.path.join(CORPUS_DIR, "text_large.txt"))
    print(f"\ntext_large.txt: {existing_text_large} bytes ({existing_text_large // 10240} non-overlapping 10240B slices)")
    for e in TEXTS:
        sz = os.path.getsize(os.path.join(CORPUS_DIR, e["filename"]))
        print(f"{e['filename']}: {sz} bytes ({sz // 10240} non-overlapping 10240B slices)")
    total_slices = (existing_text_large // 10240) + sum(
        os.path.getsize(os.path.join(CORPUS_DIR, e["filename"])) // 10240 for e in TEXTS
    )
    print(f"Total non-overlapping 10240B slices available across all three files: {total_slices}")


if __name__ == "__main__":
    run()
