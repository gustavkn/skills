#!/usr/bin/env python3
"""
List and tick the task-list checkboxes (`- [ ] ...`) in a GitHub issue body.

Uses `gh issue view` / `gh issue edit` only, so it works where `gh api` is off
limits. Checkboxes inside fenced code blocks are ignored.

Usage:
    issue_tasks.py <issue>                     List checkboxes with their index
    issue_tasks.py <issue> --check 1 3         Tick by index
    issue_tasks.py <issue> --match "parser"    Tick every box whose text contains this
    issue_tasks.py <issue> --uncheck 2         Untick by index
    issue_tasks.py <issue> --check 1 --dry-run

    <issue>   Issue number (123) or full URL

Options:
    --repo owner/name   Override repo detection (default: current directory)
"""

import argparse
import re
import subprocess
import sys

BOX = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+\[)([ xX])(\]\s+)(.*)$")
FENCE = re.compile(r"^\s*(```|~~~)")


def die(message: str):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def gh(args, stdin=None):
    proc = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)
    if proc.returncode != 0:
        die(proc.stderr.strip() or f"gh {' '.join(args)} failed")
    return proc.stdout


def find_boxes(lines):
    """Return [(line_index, checked, text)] for checkboxes outside code fences."""
    boxes, fenced = [], False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = BOX.match(line)
        if m:
            boxes.append((i, m.group(2) != " ", m.group(4).strip()))
    return boxes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("issue")
    parser.add_argument("--repo")
    parser.add_argument("--check", type=int, nargs="+", default=[])
    parser.add_argument("--uncheck", type=int, nargs="+", default=[])
    parser.add_argument("--match", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = ["--repo", args.repo] if args.repo else []
    body = gh(["issue", "view", args.issue, *repo, "--json", "body", "-q", ".body"])
    trailing_newline = body.endswith("\n")
    lines = body.rstrip("\n").split("\n") if body.strip() else []
    boxes = find_boxes(lines)

    if not (args.check or args.uncheck or args.match):
        if not boxes:
            print("no checkboxes in the issue body")
        for n, (_, checked, text) in enumerate(boxes, 1):
            print(f"{n:>3}  [{'x' if checked else ' '}]  {text}")
        return

    targets = {}
    for n in args.check:
        targets[n] = "x"
    for n in args.uncheck:
        targets[n] = " "
    for needle in args.match:
        hits = [n for n, (_, _, t) in enumerate(boxes, 1) if needle.lower() in t.lower()]
        if not hits:
            die(f"no checkbox text contains '{needle}'")
        for n in hits:
            targets[n] = "x"

    changed = []
    for n, mark in sorted(targets.items()):
        if not 1 <= n <= len(boxes):
            die(f"no checkbox #{n}; the issue has {len(boxes)}")
        line_index, checked, text = boxes[n - 1]
        if checked == (mark == "x"):
            continue
        lines[line_index] = BOX.sub(lambda m: f"{m.group(1)}{mark}{m.group(3)}{m.group(4)}", lines[line_index])
        changed.append(f"[{mark}] {text}")

    if not changed:
        print("nothing to change")
        return
    for c in changed:
        print(("would set " if args.dry_run else "set ") + c)
    if args.dry_run:
        return

    new_body = "\n".join(lines) + ("\n" if trailing_newline else "")
    gh(["issue", "edit", args.issue, *repo, "--body-file", "-"], stdin=new_body)


if __name__ == "__main__":
    main()
