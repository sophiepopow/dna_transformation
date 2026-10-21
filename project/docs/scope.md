# Scope Document

## Research Question
Does a DNA-encoding transform produce a measurably different statistical signature on low-entropy data (text/JSON) than on high-entropy data (compressed/random), and does the effect disappear once classical encryption is layered on top?

## In-Scope Data Classes
1. Low-entropy text data (plain text / JSON).
2. High-entropy compressed data.
3. High-entropy random data.

## Pipelines
1. Pipeline A — DNA encoding transform applied to raw data, followed by classical (AES-GCM) encryption, then statistical analysis.
2. Pipeline B — Classical (AES-GCM) encryption only, no DNA transform, then statistical analysis. Serves as the control pipeline to test whether any DNA-transform signal survives or is redundant once classical encryption is applied.

## Out of Scope
- NIST STS full suite.
- ECC/ECDH or other public-key cryptography.
- DNA fitness function optimization.
- RAM, CPU, or energy profiling.
- Small-message latency study.
- Multi-sequence/multi-mapping comparisons.

## Scope Boundary Caveat
Statistical randomness testing is not a substitute for formal cryptanalysis, and passing statistical tests does not certify a generator or transform as cryptographically secure. This adapted caveat mirrors the NIST SP 800-22 guidance that statistical testing cannot certify a generator as secure and is not a substitute for cryptanalysis.

## Sign-off Gate
This project requires sign-off on this document before proceeding to M1.
