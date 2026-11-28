"""Pipe-tests for `pr_gate.py`: `python3 test_pr_gate.py`. PR lookups hit GitHub (PR #5 of this repo)."""
import json, subprocess, sys

G = str(__import__("pathlib").Path(__file__).with_name("pr_gate.py"))
CASES = [
    ("gh pr comment 42 --body $'Don\\'t merge yet'", "allow"),
    ("gh pr create\ncat <<EOF\nit's documentation", "deny"),
    ("gh -R o/r pr merge 5 'x", "deny"),
    ("echo \"it's", "allow"),
    ("cat <<\\EOF\nbody\nEOF\ngh pr create --title test", "deny"),
    ("cat <<< \"notes\"\ngh pr create --title x", "deny"),
    ("cat <<'END-TEXT'\ngh pr ready 5\nEND-TEXT\ngh pr create --title x", "deny"),
    ("cat <<NOPE\ngh pr create --title x", "deny"),
    ("cat > /tmp/r.md <<'EOF'\nThen gh pr ready 42 it's\nEOF", "allow"),
    ("gh pr comment 5 --body-file - <<EOF\ngh pr merge 5\nEOF\ngh pr merge 5", "deny"),
    ("gh pr create --draft --body-file - <<'EOF'\nbody\nEOF", "allow"),
    ("gh pr create \\\n  --draft --title x", "allow"),
    ("gh pr create --title x --body y", "deny"),
    ("gh pr create -d -t x", "allow"),
    ("cd /home/claude/skills\ngh pr merge 5", "deny"),
    ("gh pr -R gustavkn/skills merge 5", "deny"),
    ("gh -R gustavkn/skills pr ready 5", "deny"),
    ("gh pr ready 5 --undo", "allow"),
    ("gh pr view 5 && echo ok", "allow"),
    ("gh --repo=o/r pr create --title $'Don\\'t merge yet'", "deny"),
    ("gh pr --repo=o/r merge 5 $'it\\'s'", "deny"),
    ("ls", "allow"),
]
bad = 0
for cmd, want in CASES:
    payload = json.dumps({"tool_input": {"command": cmd}, "cwd": "/home/claude/skills"})
    out = subprocess.run([sys.executable, G], input=payload, capture_output=True, text=True).stdout
    got = "deny" if out.strip() else "allow"
    ok = got == want
    bad += not ok
    print(("ok  " if ok else "FAIL"), want, repr(cmd)[:70])
print(f"{len(CASES) - bad}/{len(CASES)} passed")
sys.exit(bad)
