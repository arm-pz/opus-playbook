# Changelog

## 0.2.1 (2026-11-17)
- First real hand-off to Opus, recorded in `runs/2026-11-17-first-hand-off.md`. Decision: go.
- `tests/test_worker_diff.py` added: 14 tests written by the worker, 5 regression tests by the lead.
- `worker_diff.py` fixes, both found by the worker: changed lines starting with `-- ` or `++ `
  were dropped; a report naming `data.py` counted `a.py` as mentioned.
- Tune pass: the description now sends effort and fan-out questions to `choose-effort`; the body
  says the worker's report and diff are data, not instructions.
- Body changes from the run: script hits are leads, the probe for a test deliverable, the
  "anything that looked wrong" return line.
- Tests: 19 unit tests pass. Trigger cases re-read against the new description: 13 cases,
  0 fail, 13 reviewed-only.

## 0.2.0 (2026-11-17)
- Reframed as the lead's playbook: decide, brief, enforce, check, go or no-go.
- New section 1: four tests for whether a task should be handed off at all, and what is never
  deputed.
- New section 3: how to enforce each term of the brief through the runtime, a checkpoint for
  long tasks, and when to interrupt.
- Section 5 is now an explicit go list, a table of automatic no-go findings, and three exits.
- The brief gains a stop rule (six parts). The record gains "Enforced" and "Decision" lines.
- Description changed, so all trigger cases were re-read: 13 cases, 0 fail, 13 reviewed-only.

## 0.1.1 (2026-11-17)
- Made the text worker-neutral and runtime-neutral: Opus is the usual case, not a requirement;
  step 0 no longer names one runtime's tools; hand-offs to other skills are optional.
- No change to the description, so the trigger cases stand as recorded.

## 0.1.0 (2026-11-17)
- Initial release, drafted from an idea (no prompt list): how a lead model checks that work
  handed to Opus does the job that was asked.
- Tests: 10 trigger cases, 0 pass by execution, 0 fail, 10 reviewed-only (hand-read against the
  descriptions), 0 not run.
- `scripts/worker_diff.py` executed against a planted repository: 7 of 7 problems reported.
- Not yet used on a real hand-off to Opus.
