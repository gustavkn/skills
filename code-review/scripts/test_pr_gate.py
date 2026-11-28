"""Pipe-tests for `pr_gate.py`: `python3 test_pr_gate.py`.

A fake `gh` on PATH answers `gh pr view` with the JSON in $FAKE_PR, so no
test touches GitHub. Exit status is the number of failures.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

GATE = str(pathlib.Path(__file__).with_name("pr_gate.py"))
HEAD = "a" * 40


def pr(*markers):
    """PR JSON whose comments carry the given (verdict, sha) markers, oldest first."""
    comments = [{"body": f"report\n<!-- code-review verdict={v} sha={s} -->"} for v, s in markers]
    return json.dumps({"number": 5, "headRefOid": HEAD, "comments": comments})


UNREVIEWED = pr()
APPROVED = pr(("MERGE", HEAD))

# (command, what `gh pr view` returns, expected decision)
CASES = [
    # Drafts
    ("gh pr create --title x --body y", UNREVIEWED, "deny"),
    ("gh pr create --draft --body-file - <<'EOF'\nbody\nEOF", UNREVIEWED, "allow"),
    ("gh pr create -d -t x", UNREVIEWED, "allow"),
    ("gh pr create \\\n  --draft --title x", UNREVIEWED, "allow"),
    ("PR_URL=$(gh pr create --title 'Fix timeout' --body-file - <<'EOF'\nbody\nEOF\n)", UNREVIEWED, "deny"),
    ("PR_URL=$(gh pr create --draft --title x)", UNREVIEWED, "allow"),
    # Verdicts
    ("gh pr ready 5", UNREVIEWED, "deny"),
    ("gh pr ready 5", APPROVED, "allow"),
    ("gh pr merge 5 --merge", APPROVED, "allow"),
    ("gh pr merge 5 --merge", pr(("MERGE", "b" * 40)), "deny"),  # head moved since the review
    ("gh pr merge 5 --merge", pr(("MERGE", HEAD), ("NEEDS_REWORK", HEAD)), "deny"),  # latest wins
    ("gh pr merge 5 --merge", pr(("OWNER_DECISION", HEAD)), "deny"),
    ("gh pr merge 5 --merge", "not json from a broken gh", "deny"),
    ("gh pr ready 5 --undo", UNREVIEWED, "allow"),
    # Where the gated call hides
    ("cd /tmp\ngh pr merge 5", UNREVIEWED, "deny"),
    ("cd ~ && gh pr merge 5 --squash", APPROVED, "allow"),
    ("(cd /tmp && gh pr merge 5)", UNREVIEWED, "deny"),
    ("gh pr -R o/r merge 5", UNREVIEWED, "deny"),
    ("gh -R o/r pr ready 5", UNREVIEWED, "deny"),
    # Heredoc bodies are data, not commands
    ("cat > /tmp/r.md <<'EOF'\nThen gh pr ready 42 it's\nEOF", UNREVIEWED, "allow"),
    ("cat <<\\EOF\ngh pr ready 5\nEOF", UNREVIEWED, "allow"),
    ("gh pr comment 5 --body-file - <<EOF\ngh pr merge 5\nEOF\ngh pr merge 5", UNREVIEWED, "deny"),
    ("cat <<< \"notes\"\ngh pr create --title x", UNREVIEWED, "deny"),
    ("cat <<NOPE\ngh pr create --title x", UNREVIEWED, "deny"),
    # Unparseable commands fail closed, but only for gated subcommands
    ("gh pr create\ncat <<EOF\nit's documentation", UNREVIEWED, "deny"),
    ("gh pr comment 42 --body $'Don\\'t merge yet'", UNREVIEWED, "allow"),
    ("echo \"it's", UNREVIEWED, "allow"),
    # Not ours
    ("gh pr view 5 && echo ok", UNREVIEWED, "allow"),
    ("ls", UNREVIEWED, "allow"),
]


def main():
    with tempfile.TemporaryDirectory() as bindir:
        fake = pathlib.Path(bindir, "gh")
        fake.write_text("#!/bin/sh\nprintf '%s' \"$FAKE_PR\"\n")
        fake.chmod(0o755)
        failures = 0
        for command, pr_json, want in CASES:
            env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", FAKE_PR=pr_json)
            payload = json.dumps({"tool_input": {"command": command}, "cwd": "/tmp"})
            out = subprocess.run([sys.executable, GATE], input=payload, env=env,
                                 capture_output=True, text=True)
            got = "deny" if out.stdout.strip() else "allow"
            ok = got == want and out.returncode == 0
            failures += not ok
            print("ok  " if ok else "FAIL", want, repr(command)[:72])
        print(f"{len(CASES) - failures}/{len(CASES)} passed")
        return failures


if __name__ == "__main__":
    sys.exit(main())
