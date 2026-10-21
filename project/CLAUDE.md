# Project: DNA Encoding Impact on Lightweight Encryption — Thesis Implementation

## What this project is
A one-month-scoped thesis experiment testing whether a DNA-encoding
transform produces a measurably different statistical signature on
low-entropy data (text/JSON) than on high-entropy data (compressed/random),
and whether that effect disappears once classical encryption is layered on
top. See docs/scope.md for the exact research question and out-of-scope list.

## Key documents (read these before doing anything)
- docs/scope.md — frozen research scope, out-of-scope list, scope-boundary sentence
- docs/milestone_plan.md — the full M0-M7 milestone plan: tasks, requirements,
  exit criteria, and a reference paper for each milestone
- docs/raport.md — running status log. READ THIS FIRST every session to know
  what's actually done vs. claimed done

## Workflow rules (non-negotiable)

1. Work one milestone at a time, strictly in order (M0 -> M1 -> ... -> M7).
   Never skip ahead, even if a later milestone looks easy to start early.

2. Never mark a milestone complete based on the implementer subagent's own
   claims. Every milestone must pass independent review from the
   milestone-reviewer subagent before being considered done.

3. Use `/run-milestone <ID>` to execute a milestone end-to-end (implement ->
   review -> retry-on-fail -> log -> summarize). Don't hand-roll this process
   manually in the main conversation — the whole point of the subagent split
   is to keep verbose implementation and verification output out of the main
   context.

4. After every milestone attempt, whether it passes or fails, update
   docs/raport.md and give the user a plain-English summary in the chat
   reply. Never end a milestone turn having done one without the other.

5. If the reviewer flags a methodological or design concern even on a PASS,
   surface it to the user explicitly rather than only reporting the verdict.
   A passing test suite is not the same as a sound experimental design.

6. Never silently expand or narrow a milestone's scope beyond what's written
   in docs/milestone_plan.md. If something in the plan seems missing,
   ambiguous, or wrong, stop and ask the user rather than improvising.

## Project history worth knowing

M1's first implementation used a SHA-256-based mask derivation. It passed
every round-trip test and every stated exit criterion, but it silently
erased the entropy-class signal the entire thesis depends on measuring —
text and random data became statistically indistinguishable after the
transform. This was only caught by actually running the pipeline and
measuring entropy/autocorrelation directly, not by reading the status
report or checking that tests passed. Full details in docs/raport.md.

This is exactly the failure mode milestone-reviewer exists to catch. Treat
"tests pass" as necessary but never sufficient.