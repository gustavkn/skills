#!/usr/bin/env python3
"""PreToolUse hook for Bash: gate pull requests on a code review.

- `gh pr create` must be a draft (`--draft` / `-d`).
- `gh pr ready` and `gh pr merge` are allowed only when the PR's latest
  code-review marker comment says MERGE for the PR's current head commit:

      <!-- code-review verdict=MERGE sha=<head sha> -->

The `code-review` skill posts that comment. Anything else, including a
failed lookup, is denied with a reason the agent can act on.
"""
import json
import re
import shlex
import subprocess
import sys

MARKER = re.compile(r"<!--\s*code-review\s+verdict=(\S+)\s+sha=([0-9a-f]{7,40})\s*-->")
PUNCT = ";&|\n"
GATED = re.compile(r"\bgh\b.*\bpr\b.*\b(create|ready|merge)\b")
# Flags of `gh pr ready/merge` that take a value, so their value isn't mistaken for the PR.
VALUE_FLAGS = {"-R", "--repo", "-b", "--body", "-F", "--body-file", "-t", "--subject",
               "--match-head-commit", "-A", "--author-email"}


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


# `<<EOF`, `<<-'END-TEXT'`; not the `<<<` here-string.
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*(['\"]?)([^\s'\"<>;|&()]+)\1")


def strip_heredocs(command):
    """Drop heredoc bodies: they're data for a command, not commands."""
    out, pending = [], []
    for line in command.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        out.append(line)
        pending = [m.group(2).replace("\\", "") for m in HEREDOC.finditer(line)]
    if pending:
        return command  # a heredoc never closed: misparsed, so check every line
    return "\n".join(out)


def segments(command):
    command = strip_heredocs(command)
    # Newlines separate commands too; quoted newlines stay inside their argument.
    command = command.replace("\\\n", " ")  # backslash-newline is a line continuation
    lexer = shlex.shlex(command, posix=True, punctuation_chars=PUNCT)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    current = []
    for token in lexer:
        if token and all(ch in PUNCT for ch in token):
            if current:
                yield current
            current = []
        else:
            current.append(token)
    if current:
        yield current


def pr_target(args):
    """Return (selector, repo) from the args after `gh pr ready|merge`."""
    selector, repo, i = None, None, 0
    while i < len(args):
        a = args[i]
        if a in VALUE_FLAGS:
            if a in ("-R", "--repo") and i + 1 < len(args):
                repo = args[i + 1]
            i += 2
            continue
        if a.startswith("--repo="):
            repo = a.split("=", 1)[1]
        elif not a.startswith("-") and selector is None:
            selector = a
        i += 1
    return selector, repo


def check_review(action, args, cwd):
    selector, repo = pr_target(args)
    cmd = ["gh", "pr", "view"] + ([selector] if selector else []) + (["-R", repo] if repo else [])
    cmd += ["--json", "number,headRefOid,comments"]
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
    except Exception as e:  # noqa: BLE001 - any failure closes the gate
        deny(f"PR gate: couldn't look up the PR ({e}). `gh pr {action}` is blocked until it can.")
    if out.returncode != 0:
        deny(f"PR gate: `{' '.join(cmd)}` failed: {out.stderr.strip()[:300]}. `gh pr {action}` is blocked.")
    pr = json.loads(out.stdout)
    head = pr["headRefOid"]
    verdict = sha = None
    for c in pr.get("comments", []):
        m = MARKER.search(c.get("body", ""))
        if m:
            verdict, sha = m.group(1), m.group(2)
    if verdict is None:
        deny(f"PR gate: PR #{pr['number']} has no code review yet. Run the `code-review` skill, "
             f"fix its findings, and post the verdict comment before `gh pr {action}`.")
    if not head.startswith(sha):
        deny(f"PR gate: the latest review of PR #{pr['number']} was for {sha[:7]}, but the head is now "
             f"{head[:7]}. Re-review the new commits before `gh pr {action}`.")
    if verdict != "MERGE":
        deny(f"PR gate: the latest review of PR #{pr['number']} says {verdict}. Fix the findings, "
             f"re-review until it says MERGE, then `gh pr {action}`.")


def main():
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "")
    if "gh" not in command or "pr" not in command:
        return
    cwd = data.get("cwd") or None
    try:
        segs = list(segments(command))
    except ValueError:
        if GATED.search(command):
            deny("PR gate: couldn't parse this command (unbalanced quotes?). Run the `gh pr` "
                 "command on its own in a separate Bash call.")
        return
    for seg in segs:
        if seg[0] == "cd" and len(seg) > 1:
            cwd = seg[1] if seg[1].startswith("/") or cwd is None else f"{cwd}/{seg[1]}"
            continue
        if seg[0] != "gh" or "pr" not in seg:
            continue
        # Allow flags around the subcommands, e.g. `gh pr -R o/r merge 42`.
        # Flags before `pr` (like `-R o/r`) are kept with the action's args.
        p = seg.index("pr")
        rest = seg[p + 1:]
        lead = seg[1:p]
        while rest and rest[0].startswith("-"):
            n = 2 if rest[0] in VALUE_FLAGS and len(rest) > 1 else 1
            lead, rest = lead + rest[:n], rest[n:]
        if not rest:
            continue
        action, args = rest[0], lead + rest[1:]
        if action == "create" and not ({"--draft", "-d"} & set(args)):
            deny("PR gate: open PRs as drafts (`gh pr create --draft`). Mark it ready only after "
                 "the `code-review` skill's verdict is MERGE.")
        if action == "ready" and "--undo" not in args:
            check_review(action, args, cwd)
        if action == "merge":
            check_review(action, args, cwd)


if __name__ == "__main__":
    main()
