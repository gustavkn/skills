---
name: github-issues
description: Guide for working on GitHub issues that are tracked on a Projects v2 board, keeping the card's Status in sync with the work. This skill should be used when picking up, implementing, or closing out a GitHub issue - triggered by "work on issue #123", "take issue 45", "start on this issue", an issue URL, or any request to move an issue to In Progress, Test or Done.
license: MIT
---

# Working on GitHub issues

Work an issue from board to merge, moving its card as the work progresses. The
board is the source of truth for where an issue stands, so every transition
below is mandatory, not optional.

The status flow:

```
In Progress  ->  Test  (needs hands-on verification; issue stays open)
             \
              ->  Done  (no verification needed; issue closes with the PR)
```

## 1. Pick up the issue

Read it properly before touching code:

```bash
gh issue view <number> --comments
```

Comments often carry the real requirements. If the issue is ambiguous,
underspecified, or has grown a scope that no longer matches its title, ask
before starting rather than guessing.

## 2. Move the card to In Progress

Discover the board's actual column names first — they vary per repo, and
guessing wrong wastes a round trip:

```bash
scripts/project_status.py <number> --list
```

Then move it:

```bash
scripts/project_status.py <number> "In Progress"
```

If the issue is not on any board, say so and ask whether to add it. Do not
silently continue — an untracked issue is invisible on the board.

If the token lacks the Projects scope, the script says so; the user must run
`gh auth refresh -s project` themselves. Do not attempt a workaround.

## 3. Branch and implement

Follow the `git` skill for branch naming and commit messages. On a fork-based
open source repo, the `collaboration` skill owns the fork and PR-target rules;
this skill only adds the board moves. Use a worktree
only when explicitly asked, per the `worktrees` skill.

Implement the issue as specified — not the adjacent improvements it suggests.
Anything worth doing that falls outside the issue belongs in a new issue, not
in this PR.

## 4. Decide Test or Done — before opening the PR

Ask the user directly:

> Does #123 need hands-on verification from you, or can it go straight to Done?

Ask before writing the PR body, because the answer changes the linking keyword:

| Answer | PR links with | On merge |
| --- | --- | --- |
| Needs verification | `See #123` | Issue stays open, card -> Test |
| No verification | `Fixes #123` | GitHub closes the issue, card -> Done |

**`Fixes #123` closes the issue the moment the PR merges.** That is the wrong
outcome for anything heading to Test, where the issue must stay open until the
user has actually verified it. Use `See #123` there and close it manually
later.

## 5. Review, then open the PR

Run the `code-review` skill on the changes before opening the PR.

```bash
gh pr create --title "<title>" --body "<body>"
```

## 6. Close out after merge

**Verification needed** — move to Test and leave the user something to work
from:

```bash
scripts/project_status.py <number> Test
gh issue comment <number> --body "<verification notes>"
```

The comment covers three things, briefly:

- What changed, in behaviour terms rather than diff terms
- How to verify it — concrete steps, URLs, commands, test data
- Where it is deployed, if anywhere, and which environment

The issue stays open. The user moves it out of Test once satisfied.

**No verification needed** — the `Fixes #123` link already closed the issue on
merge. Confirm that and move the card:

```bash
gh issue view <number> --json state -q .state    # expect CLOSED
scripts/project_status.py <number> Done
```

If the state is still OPEN, the link did not take — close it explicitly with
`gh issue close <number>`.

Some boards close or move cards automatically. A move that has already happened
is reported as "already in <column>" and costs nothing, so always run the move
rather than assuming a workflow handled it.

## Reference

`references/projects-graphql.md` has the raw GraphQL for anything the script
does not cover — adding an issue to a board, setting other field types, node id
prefixes, and why a board might look invisible.
