---
name: github-issues
description: Guide for working on GitHub issues tracked on a Projects v2 board, keeping the issue and its card in sync with the work - ticking its checkboxes, moving it to In Progress, Waiting, Test or Done, and commenting what needs testing or what it waits on. This skill should be used whenever picking up, implementing, pausing or closing out a GitHub issue - triggered by "work on issue #123", "take issue 45", "start on this issue", an issue URL, an issue assigned in GitHub Actions, or any request to move an issue between columns.
license: MIT
---

# Working on GitHub issues

The issue and its board card are the source of truth for where work stands.
Whoever reads the board should know the state without asking. Every update
below is mandatory, not optional, and happens **when the state changes**, not
batched at the end.

## The columns

| Column | Meaning | The agent moves it here when | Required with the move |
| --- | --- | --- | --- |
| **In Progress** | Being worked on | Work starts, or resumes after Waiting | - |
| **Waiting** | Blocked | It needs an approval or decision, or depends on another issue, PR, release, access or person | Comment: what it waits on, who, what unblocks it |
| **Test** | Ready for testing | The PR is open (or merged) and the change needs verifying | Comment: what to test and how |
| **Done** | Tested and done | The user confirms it is tested, or it has nothing to test (see below) | Issue closed |

Discover the board's real column names before the first move; the script
fuzzy-matches, but check:

```bash
scripts/project_status.py <number> --list
```

## 1. Pick up the issue

```bash
gh issue view <number> --comments
scripts/issue_tasks.py <number>          # the checkboxes, numbered
```

Comments often carry the real requirements. Check open PRs and branches for
the issue first; parallel sessions have duplicated work before.

If the issue is not on any board, add it (`references/projects-graphql.md`)
and note it in the report. If the token lacks the Projects scope, the script
says so; the user must run `gh auth refresh -s project`. Don't work around it;
carry on and list the moves you could not make in the report.

## 2. Move to In Progress

```bash
scripts/project_status.py <number> "In Progress"
```

Do this before the first commit, not after the PR.

## 3. Implement, ticking checkboxes as you go

Follow the `git` skill for branches and commits, and the repo's CLAUDE.md for
base branch and PR rules. Implement the issue as specified; adjacent
improvements go in a follow-up issue.

Tick each checkbox (acceptance criteria, task list) as soon as it is met **and
covered by a test or a stated check**, not all at once at the end:

```bash
scripts/issue_tasks.py <number> --check 2 3
scripts/issue_tasks.py <number> --match "rejects a negative amount"
```

Rules:

- Only tick what is actually done in the code on the branch. A box that needs
  the user (manual check, prod setting, approval) stays unticked; say so in the
  Test or Waiting comment.
- Never edit the wording of a box or delete one. If a criterion turns out wrong
  or out of scope, leave it unticked and explain in a comment.
- Checkboxes in PR descriptions follow the same rules.

## 4. Blocked? Move to Waiting

The moment something outside the agent's control blocks progress - an
approval (anything on the repo's stop-and-ask list), an unsettled decision, a
dependency on another issue or PR, missing access or secrets:

```bash
scripts/project_status.py <number> Waiting
gh issue comment <number> --body-file - <<'EOF'
**Waiting on:** <what - be specific, link the issue/PR/decision>
**Who:** <@person, or "the owner">
**Unblocks when:** <the concrete event or answer>
**Done so far:** <what is on the branch / in the PR, ticked boxes>
EOF
```

Finish everything that doesn't depend on the blocker first, and put all open
questions in that one comment. When unblocked, move back to In Progress.

## 5. Ready for testing: move to Test

When the PR is open and the work is complete (run the `code-review` skill
first):

```bash
scripts/project_status.py <number> Test
gh issue comment <number> --body-file - <<'EOF'
## Ready for testing - <PR link>

**What changed:** <behaviour, not diff - one to three bullets>

**How to test:**
1. <concrete step: URL, command, input data, which account/company>
2. <...>
**Expected:** <what the tester should see>

**Already verified:** <automated tests added/run, CI status>
**Not verified:** <what the agent could not check, e.g. against real Dinero data>
**Environment:** <where it is deployed, or "after merge to dev"/"after release">
EOF
```

Every Test move gets this comment. "Run the tests" is not a test plan; name
the thing a human should click, call or look at, including edge cases worth
trying. If the PR has the same plan, link to it rather than copying.

Linking keyword: follow the repo's rule (e.g. `Closes #N`). Mind that a
closing keyword only fires when the PR merges into the **default** branch; on
repos where that is the release branch, the issue stays open in Test after the
merge to the working branch, which is what we want. Where the PR targets the
default branch directly and the issue needs testing, use `See #N` instead so it
does not close before it is tested.

## 6. Done

Move to Done only when:

- the user says it is tested / approves it, or
- there is genuinely nothing for a human to verify (docs, CI, internal
  refactor with tests) - state that in the issue comment.

```bash
scripts/project_status.py <number> Done
gh issue view <number> --json state -q .state     # close it if still OPEN
gh issue close <number> --comment "Tested and done."   # if needed
```

Before Done, every checkbox should be ticked, or have a comment explaining
why not. Some boards move cards automatically; run the move anyway - "already
in <column>" costs nothing.

## Where gh api is not allowed

`project_status.py` uses `gh api graphql` internally. Where the repo forbids
typing `gh api` (e.g. a CLAUDE.md rule for GitHub Actions runs) but allows the
script, use the script: that is the sanctioned route to the board. If
`PROJECTS_GH_TOKEN` is set, the script uses it for the board calls.

If the script is not allowed, or fails for lack of access, skip the board
moves, still tick checkboxes and post the comments (`issue_tasks.py` and
`gh issue comment` don't use `gh api`), and start the comment with the column
it belongs in, e.g. `**Status: Test**`.

## Reference

`references/projects-graphql.md` has the raw GraphQL for anything the script
does not cover - adding an issue to a board, other field types, node id
prefixes, and why a board might look invisible.
