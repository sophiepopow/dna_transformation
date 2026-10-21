---
description: Run one milestone end-to-end - implement, strictly review, retry on failure, then log and summarize for the user.
argument-hint: [milestone-id, e.g. M2]
---

Run milestone $1 of this project end-to-end.

1. Read docs/milestone_plan.md and extract the exact section for milestone
   $1 — objective, reference paper, tasks, requirements, and exit criteria.
   If $1 isn't in the plan, stop and tell the user rather than guessing.

2. Read docs/raport.md. Confirm the milestone immediately before $1 is
   logged as done. If it isn't, warn the user and ask before proceeding —
   don't silently skip ahead.

3. Delegate implementation to the milestone-implementer subagent. Pass it
   the milestone's objective, full task list, requirements, and reference
   paper verbatim from docs/milestone_plan.md. Wait for its completion
   report.

4. Delegate review to the milestone-reviewer subagent. Pass it the
   milestone's exit criteria verbatim, plus the implementer's completion
   report. Make clear in the task prompt that it must independently verify
   everything itself, not trust the report. Wait for its verdict.

5. If the verdict is FAIL: send the reviewer's exact required-fixes list
   back to the milestone-implementer subagent and have it address them,
   then re-run review. Cap this at 3 total implement/review cycles for this
   milestone. If it's still failing after 3 cycles, stop, do not retry
   again, and escalate to the user with the reviewer's latest findings in
   full.

6. If the verdict is PASS:
   a. Write docs/reviews/$1_review.md containing the reviewer's full
      checklist and any design concerns, for the audit trail.
   b. Append a dated entry to docs/raport.md: milestone ID, status, a brief
      description of what was implemented, the verification evidence
      summary, and any design concerns the reviewer flagged even though it
      passed. Do not overwrite existing raport.md content.
   c. In your reply to the user, give a plain-English summary of what
      happened — not a raw log dump. Always surface any reviewer design
      concerns explicitly, even on a PASS, the same way you would for a
      FAIL. Never bury a concern just because the milestone technically
      passed.

7. End your turn after logging and summarizing. Do not automatically start
   the next milestone — wait for the user to run /run-milestone for it.
