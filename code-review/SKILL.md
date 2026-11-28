---
name: code-review
description: Guide for making code reviews. Use this when asked to make code reviews, or ask to use it before committing changes. Classifies the change by risk first, then runs a light Claude review, a codex review, or a deep combined review to match.
license: MIT
---

# Code review

Size the review to the risk of the change. A one-line copy fix doesn't need three reviewers; a change to how user data is stored does.

## 1. Collect the change

- On a feature branch: committed and uncommitted changes against the base branch (`git diff <base>...HEAD` plus `git status`). The base is the branch the PR targets, which is not always the repo's default branch; check the repo's CLAUDE.md or `gh pr view --json baseRefName`.
- On the base branch: the staged (or uncommitted) diff.
- For a PR: `gh pr diff <n>` and the PR description.
- For a single commit: `git show <sha>`.

## 2. Classify the risk

Read the diff (`git diff --stat` first, then the content) and put the change in the **highest** tier any part of it hits.

| Tier | What it covers | Examples |
|------|----------------|----------|
| **Low** | Small and local. Easy to see it's right, easy to undo. | Docs, comments, UI copy, tests only, a bug fix inside one function, a refactor inside one file with unchanged behavior |
| **Standard** | A real behavior change, or code spread across several files or components. | New feature or endpoint, changed business logic, a refactor across modules, a new dependency, a CI workflow change, roughly 150+ changed lines of non-generated code |
| **Critical** | A mistake here corrupts data, leaks data, or is expensive to undo. | Stored data or its format (schema, blob/table layout, serialization, migrations, deletes, backfills); user or customer data and PII; authentication, authorization, secrets, RBAC, tenant isolation; money, billing, figures in a report someone files or relies on; infra and anything touching prod; restructuring a larger part of the system (core abstractions, cross-cutting pipelines) |

Rules of thumb:

- Size only moves a change up, never down. A 5-line change to a delete query is Critical.
- Generated code, lock files and snapshots don't count toward size, but whatever generated them does.
- A repo's CLAUDE.md may name its own critical areas (e.g. "anything that changes a figure in a filed report"). Those are Critical here.
- When torn between two tiers, pick the higher one.

State the tier and a one-line reason at the top of the report, e.g. `Tier: Critical (changes the blob layout of stored reports)`.

## 3. Run the review for the tier

Every reviewer gets the **Reviewer brief** below. Give them the diff scope and file paths and let them read the code themselves; don't hand them your own conclusions.

### Low: light Claude review

One subagent, or do it yourself if the diff is a few lines. Check that the change does what it says, doesn't break callers, and has a test where behavior changed. Expect few or zero findings; that's the right answer for most low-risk changes.

### Standard: codex review

Run `codex exec review` against the base branch at `-c model_reasoning_effort="high"`, as described in the `second-opinion` skill under "Code review second opinions". Its built-in reviewer already holds a strict "definite bugs only" bar. If you use a custom prompt instead, include the reviewer brief.

If codex is unavailable (not logged in, usage limit hit, sandbox broken and the fallback in `second-opinion` doesn't work), fall back to two Claude subagents, one on architecture and one on implementation, and say so in the report.

### Critical: deep review

Run these in parallel:

1. **codex review**, as for Standard.
2. **An adversarial codex prompt** (plain `codex exec`, see `second-opinion`) aimed at whatever made the change Critical. For example: "This change alters how X is stored. Find how it fails: data loss or corruption, existing data the migration doesn't handle, a user seeing another user's data, a wrong number reaching a report." Ask for a concrete failing scenario per finding.
3. **An independent Claude subagent** reviewing architecture and implementation together, briefed on the same risk area but not shown codex's output.

Then cross-check. A finding two reviewers reached independently is strong; a finding only one reviewer has needs your own verification before it goes in the report.

## Reviewer brief

Give every reviewer this bar, adapted to the change:

- Report problems that will **realistically happen** in normal use or a plausible failure: a wrong result, a crash, lost or corrupted data, a security hole, a broken caller, a missing test for changed behavior.
- For each finding: what goes wrong, the concrete scenario (input or state, then the wrong outcome), and the fix.
- **Don't report** style, naming, formatting, hypothetical scaling problems, races that need several unlikely events to line up, defense-in-depth against states the system can't produce, or "consider adding" suggestions with no concrete failure behind them.
- Pre-existing problems aren't findings for this change. If one is worth fixing, list it separately as a follow-up.
- Zero findings is a valid and welcome result. Don't pad the list.

Don't tell reviewers they're competing or that more findings is better. That's how you get nitpicks.

## 4. Triage the findings

Reviewers over-report even with a strict bar. Before relaying, put each finding in one of three buckets:

- **Fix**: realistic, in scope, and the fix is clear. This includes anything in a Critical area that can cause data loss, a data leak, or a wrong figure, however unlikely; those are never downgraded for being rare.
- **Follow-up**: valuable but out of scope, pre-existing, or bigger than this change should carry. Open an issue, or list it under `## Follow-ups` in the PR if that's the repo's convention: one line on the problem, one on why it matters.
- **Drop**: nitpicks, speculation and gold-plating. Mention only the count ("dropped 4: style, speculative") so it's clear they were seen.

Verify every Fix finding before acting on it: read the code, run the scenario, or write the failing test. A finding you can't reproduce or trace through the code goes to Follow-up with a note, not into the fix list.

## 5. Report

Keep it short:

```
Tier: <Low|Standard|Critical> (<reason>)
Reviewers: <Claude light | codex high | codex high + adversarial codex + Claude>
Verdict: <MERGE | MERGE AFTER FIXES | NEEDS REWORK>

Fix:
- `path/file.cs:42` <what goes wrong, scenario> -> <fix>

Follow-ups:
- <issue link or one-liner>

Dropped: <n> (<kinds>)
```

`MERGE` means no Fix findings remain.

## 6. Every PR: draft until the review says MERGE

Every PR gets this review, and stays a draft until it passes:

1. Open the PR as a draft: `gh pr create --draft ...`.
2. Review it at its tier. Apply the Fix bucket, push, and review the fix commits as a new round: at the same tier when the fixes were non-trivial, or by a fresh Claude subagent when they're small and obvious. Never by yourself; you wrote the fix.
3. Repeat until the verdict is `MERGE`. You may post `MERGE` only when the latest review round covered the current head and left no Fix findings after triage (list what you dropped). A fix you pushed after that round needs its own round, even a small one.
4. **Round limit.** After three rounds that still produced Fix findings, stop. Post the report with `verdict=OWNER_DECISION`, leave the PR as a draft, and ask the owner. Only the owner then decides: they mark it ready themselves, or tell you to post `MERGE`. Don't post `MERGE` on your own triage past the limit; a reviewer that keeps finding things is information, even when each finding is small.
5. Post the report as a PR comment, ending with the verdict marker for the commit you reviewed:

   `SHA` is the head you captured with `gh pr view <n> --json headRefOid -q .headRefOid` *before* the review started, and the review must cover exactly that commit. Before posting, check the head is still `SHA`; if someone pushed meanwhile, review the new commits first.

   ```sh
   [ "$(gh pr view <n> --json headRefOid -q .headRefOid)" = "$SHA" ] || echo "head moved: re-review"
   # $DIR/report.md holds the report from section 5 (scratchpad, not the repo)
   printf '\n<!-- code-review verdict=MERGE sha=%s -->\n' "$SHA" >> "$DIR/report.md"
   gh pr comment <n> --body-file "$DIR/report.md"
   ```

   Post the marker for non-MERGE verdicts too (`verdict=MERGE_AFTER_FIXES`, `verdict=NEEDS_REWORK`, `verdict=OWNER_DECISION`), so the PR shows where it stands.
6. Only after a `MERGE` verdict, `gh pr ready <n>`, and only if the repo lets you mark PRs ready (some repos leave that to the owner; then the MERGE comment is the hand-off).

A hook (`scripts/pr_gate.py`, see the README) enforces this: it denies `gh pr create` without `--draft`, and `gh pr ready` / `gh pr merge` unless the latest marker says `MERGE` for the PR's current head. A push after the review moves the head, so it needs a new review and marker. Don't work around a denial; do what it says.
