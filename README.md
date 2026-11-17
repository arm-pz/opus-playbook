# opus-playbook

An agent skill for a lead model, Fable in the usual setup, that deputes tasks to Opus or to any
subagent or worker session. It covers the lead's four jobs:

1. Decide whether the task should be handed off at all.
2. Brief it so the result can be checked.
3. Enforce the terms while it runs: scope, tools, tests, stop rules.
4. Check what comes back and call go or no-go, with the evidence.

It is for people who run a stronger model as the lead and want to know what it verified before
it says "done".

It is not a guide to prompting Opus.

## Install

- Claude Code: copy this folder to `~/.claude/skills/opus-playbook/`, or to a project's
  `.claude/skills/opus-playbook/`.
- Claude app or web: upload `opus-playbook.zip` in the skills settings.
- Other agents: copy the folder into the directory that agent reads (`.agents/skills/`,
  `.cursor/skills/`, `~/.qoder/skills/`).
- From GitHub: `npx skills add arm-pz/opus-playbook`

Then confirm `opus-playbook` appears in the agent's skill list.

## Try it

- "Hand this fix to Opus and make sure it actually did it before we merge."
- "The subagent says the tests pass. Is that true?"
- "If you give this to Opus, how will you check it, and what is your go/no-go?"

## What is in the folder

| File | Why it exists |
| --- | --- |
| `SKILL.md` | The hand-off tests, the brief, the enforcement table, the check ladder, the go and no-go lists and the record |
| `scripts/worker_diff.py` | The mechanical part of the ladder: changed files, files the report never names, test and CI edits, and added lines that skip, silence or stub. Needs Python 3 and git; reads only |
| `tests/test_worker_diff.py` | Unit tests for the script |
| `references/trigger-cases.md` | The trigger test cases and their results |
| `runs/` | Records of real hand-offs the skill was used on |

It needs nothing from the project it runs in. The script works in any git repository, and the
ladder falls back to a manual file list outside one. The skills named under Boundaries are
optional; without them the skill says what it did not cover.

## Boundaries

- Handles: whether to hand a task off, how its terms are enforced, and the go or no-go on what
  comes back, checked against the brief it was given.
- Does not handle: a defect review of code with no brief (`consistent-code-review`), deciding
  which model takes which role (`setup-claude-advisor`), an effort level or how far to fan out (`choose-effort`),
  or pressure-testing a decision (`crash-test`).

## Test results

- Real hand-off: used once, on 2026-11-17, with Fable as lead and Opus as worker. The worker
  wrote this repository's test suite; the lead ran the full ladder and called it a go. The
  record, including what the run changed in the skill, is in
  [runs/2026-11-17-first-hand-off.md](runs/2026-11-17-first-hand-off.md). No no-go has been
  exercised on real work yet.
- Script: `python3 -m unittest discover -s tests` runs 19 tests, all passing.
- Trigger cases, version 0.2.1: 0 pass by execution, 0 fail, 13 reviewed-only, 0 not run. They
  were read by hand against the descriptions; no live triggering session was used.

## A note on the name

A GitHub search on 2026-11-17 found no repository named exactly `opus-playbook` and no topic of
that name. Five repositories have close names, and all of them are guides to prompting or
configuring Opus; the largest, `rennf93/opus-fable-playbook`, had 34 stars. Someone searching
this name is likely to expect a prompting guide.

## Version

See CHANGELOG.md. MIT licence.
