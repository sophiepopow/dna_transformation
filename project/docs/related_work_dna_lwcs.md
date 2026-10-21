# Related Work Note — DNA-LWCS (Aqeel et al., 2025)

Prepared 2026-08-25, ahead of M7, so this is ready to drop directly into
`docs/thesis/02_related_work.md` (architectural comparison) and
`docs/thesis/07_limitations.md` (the ECC/AES-GCM scoping justification).

**Full citation:** Sehrish Aqeel, Adnan Shahid Khan, Irshad Ahmed Abbasi,
Fahad Algarni, and Daniel Grzonka. "Enhancing IoT security with a
DNA-based lightweight cryptography system." *Scientific Reports*, vol.
15, article 13367 (2025). DOI:
[10.1038/s41598-025-96292-0](https://doi.org/10.1038/s41598-025-96292-0).
Open access (CC BY-NC-ND 4.0). Read in full (24 pages) directly from the
publisher PDF, not summarized secondhand — this is the same paper named
as the M2 pipeline-structure reference in `docs/milestone_plan.md`, and
the paper the M6 reference (TIJER2604279.pdf) was itself summarizing
without quoting numbers.

## What DNA-LWCS actually does

1. **Key material**: three keys extracted from ~52 million publicly
   available DNA sequences, used as an entropy source for key generation
   (not as a fixed transform parameter — see divergence below).
2. **Encoding step**: the message and key are concatenated into one bit
   string, then a substitution operation (XOR / Mod / AND, chosen
   *randomly* per run) and a transposition operation (a ROTATE across the
   whole bit string) are applied.
3. **Classical layer**: Elliptic Curve Cryptography (ECC), curve
   secp256r1/P-256. Encryption computes `C1 = kP`, `C2 = M + kQ` — the
   message is encrypted directly as elliptic-curve point arithmetic, not
   via a symmetric bulk cipher.
4. **DNA mapping table**: `A=00, T=01, C=10, G=11` — identical to this
   project's `DEFAULT_MAPPING` in `src/dna_codec.py`.
5. **Evaluated on**: three images (Female.bmp 256×256, Pepper.bmp
   512×512, Photographer.bmp 512×512 grayscale), compared against three
   other published schemes (LWCS, RF-DECC, DEA-IoT/IoT) on correlation,
   encryption time, throughput, delay, and energy consumption. Python/Jupyter,
   numpy/matplotlib/opencv, Windows 7, Intel i3-3110M @ 2.4GHz, 4GB RAM.

## How it relates to this project

Same base-pair encoding table, same general premise: combine a
DNA-domain encoding step with a classical cipher for lightweight IoT-style
security. `docs/milestone_plan.md`'s M2 section names this paper directly
as the source for the 3-phase pipeline structure this project's own
2-pipeline design was built against.

**A specific, worth-citing observation:** DNA-LWCS's encoding step
(XOR/Mod/AND + ROTATE) is structurally the closest published analogue to
*this project's own original, since-superseded M1 design*
(`derive_mask` + XOR + fixed rotation — see `docs/raport.md`'s M1
section). That design was found, empirically, to erase the exact
entropy-class signal this thesis is built to measure. DNA-LWCS's paper
reports no entropy or chi-square statistic anywhere, so it is an open
question — not settled by their paper, and not something this project
claims to have tested on their exact scheme — whether DNA-LWCS's own
encoding step has the same failure mode this project already found and
fixed in its own earlier design.

## Where this project deliberately diverges

| | DNA-LWCS | This project |
|---|---|---|
| Classical layer | ECC (asymmetric, curve point arithmetic on the message directly) | AES-GCM (symmetric, authenticated) |
| Test data | 3 images | text / JSON / random binary, 2 sizes each, frozen corpus |
| Baseline design | Whole system vs. *other published schemes* | Same cipher, DNA step on vs. off (controlled ablation) |
| Metrics | Correlation, encryption time, throughput, delay, energy | Entropy, chi-square, compression ratio, avalanche, correlation, throughput, size overhead |
| Role of the DNA sequence | Randomness source for key generation | Fixed transform parameter mixed directly with plaintext |
| Reproducibility | Data "available upon request"; no fixed test corpus | Frozen, checksummed, git-tagged corpus (`data/corpus/`, `CHECKSUMS.sha256`) |

### Why AES-GCM instead of ECC is a deliberate, defensible choice, not a shortfall

1. **The research question doesn't require a specific classical cipher.**
   `docs/scope.md`'s research question asks whether the DNA transform
   changes the data's statistical signature, and whether that survives
   "classical encryption" generically — it needs a real classical cipher,
   not specifically ECC.
2. **AES-GCM enables the controlled ablation this thesis actually needs.**
   Pipeline A vs. Pipeline B (same key, same cipher, DNA step present or
   absent) isolates the DNA transform's own contribution. ECC's
   asymmetric key model does not fit this "flip one switch" comparison as
   cleanly.
3. **DNA-LWCS's own use of ECC is itself non-standard for bulk data.**
   Encrypting a message directly via `M + kQ` point arithmetic is not how
   ECC is typically deployed in practice — the standard real-world
   pattern (ECIES and most hybrid schemes) uses ECC only for *key
   exchange*, then a symmetric cipher for the actual data, because raw EC
   point operations do not scale to arbitrary-length messages the way a
   block/stream cipher does. AES-GCM as the classical layer here is
   arguably closer to how ECC-based systems are used in practice, even
   without an explicit key-exchange step.
4. **This was decided at M0, not improvised late.** `docs/scope.md`'s
   out-of-scope list excludes "ECC/ECDH or other public-key
   cryptography" — locked before any code was written, not a deviation
   discovered afterward.
5. **"Inspired by" is not "reproduces."** DNA-LWCS asks a broad
   engineering question (is our whole combined system efficient/secure
   vs. other whole systems). This thesis asks a narrower, more
   mechanistic one (does the DNA step itself leave a statistical
   fingerprint, isolated from the cipher) — a question DNA-LWCS's own
   paper does not test, since it never runs itself with the DNA step
   removed.

## Gaps and methodological oddities in DNA-LWCS's own paper (worth noting plainly, not adopting)

- **No entropy, chi-square, NPCR, or UACI reported anywhere** — surprising
  for a DNA-based encryption paper, since these are the standard
  randomness battery (and the substance of NIST SP 800-22, the reference
  standard `docs/scope.md` itself cites).
- **No avalanche effect reported**, despite having an explicit
  substitution+transposition step that avalanche testing is designed to
  evaluate.
- **Correlation is framed opposite to normal cryptographic practice**:
  higher correlation (up to their own ~0.05 threshold) is called *good*,
  justified as preserving "data recovery" — a non-standard framing,
  since the usual security goal is near-zero correlation between
  plaintext and ciphertext.
- **Throughput/delay/energy are reported against synthetic "data point"
  counts (10–50)** rather than real byte sizes, with no definition given
  of what a "data point" is — not reproducible from the paper text alone,
  unlike this project's byte-size-scaled, checksummed measurements.
- **No fixed, public test corpus** — "data availability: upon request."

## Practical consequence: no valid numeric comparison is possible

This also explains a finding from M6: the TIJER2604279.pdf review paper
that discusses DNA-LWCS had no quotable numeric benchmarks to cite (see
`docs/findings.md`'s external-comparison bullet). Now the reason is
clear: DNA-LWCS's own reported numbers (correlation on images, seconds-scale
encryption time, ambiguous-unit throughput, joules of energy) are measured
in units and on data types that do not translate to this project's
bits-per-byte entropy or bytes-per-second throughput on text/JSON/random
data. **There is no apples-to-apples numeric benchmark to make against
DNA-LWCS specifically** — this should be stated plainly in the thesis
rather than forced.

## Suggested framing for the thesis

- `02_related_work.md`: cite DNA-LWCS as the architectural inspiration
  for the 2-pipeline structure; present the divergence table above;
  note the open question about whether DNA-LWCS's own encoding step
  shares this project's original M1 failure mode.
- `07_limitations.md`: state the ECC→AES-GCM substitution explicitly, with
  the reasoning above, as a deliberate scope decision made at M0 — not an
  oversight discovered late.
- `06_discussion.md` / `05_results.md`: do not attempt a numeric
  comparison against DNA-LWCS's reported figures; state explicitly why
  none is possible (different data types, different metrics, different
  units), rather than omitting the comparison silently.
