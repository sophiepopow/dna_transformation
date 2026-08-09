# M0 Status Report

## Completed Steps
- Created project structure under `/project/` with directories:
  - `project/src/`
  - `project/data/corpus/`
  - `project/results/`
  - `project/docs/`
  - `project/tests/`
  - `project/scripts/`
- Wrote `project/docs/scope.md` with:
  - the research question verbatim,
  - the three data classes,
  - the two pipelines,
  - the out-of-scope list,
  - the NIST SP 800-22 adapted scope boundary caveat.
- Set up a Python virtual environment using Python 3.11:
  - created `.venv/`
  - installed `pycryptodome`, `numpy`, `scipy`, `pandas`, `matplotlib`, `pytest`
  - froze dependencies to `requirements.txt`.
- Verified the environment with `python --version` and import checks for `Crypto`, `numpy`, and `scipy`.

## Results
- The environment now uses Python 3.11.7.
- The required packages are installed and import successfully.
- `requirements.txt` is present and contains all requested dependencies.

## Notes for the Research Paper
- The research question focuses on statistical signatures of DNA encoding on low-entropy versus high-entropy data, and whether classical encryption removes that signature.
- The study explicitly excludes the full NIST STS suite, formal cryptanalysis, public-key protocols, DNA fitness functions, performance profiling, and latency benchmarking.
- The scope boundary emphasizes that statistical testing alone does not certify cryptographic security, echoing NIST SP 800-22.

## Next Gate
- `project/docs/scope.md` must be reviewed and signed off before starting M1.
