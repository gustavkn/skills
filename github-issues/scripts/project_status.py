#!/usr/bin/env python3
"""
Move a GitHub issue's card to a different Status column on its Projects v2 board.

Projects v2 has no REST endpoints and no first-class `gh` command for setting a
single-select field, so every status change needs the same three GraphQL round
trips: find the issue's project item, look up the Status field and its option
ids, then mutate. This script does that.

Usage:
    project_status.py <issue> <status>      Move the card
    project_status.py <issue> --list        Show boards, current status, options
    project_status.py <issue> <status> --dry-run

    <issue>   Issue number (123) or full URL
    <status>  Target column, matched case-insensitively with fuzzy fallback

Options:
    --repo owner/name   Override repo detection (default: current directory)
    --project NUMBER    Disambiguate when the issue sits on several boards
    --field NAME        Single-select field to set (default: Status)

Requires the `project` OAuth scope: gh auth refresh -s project
"""

import argparse
import difflib
import json
import re
import subprocess
import sys

SCOPE_HINT = (
    "The gh token is missing the Projects scope.\n"
    "Ask the user to run:  gh auth refresh -s project\n"
    "(read:project alone can read boards but cannot move cards.)"
)


def die(message: str, code: int = 1):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def gh_graphql(query: str, **variables):
    """Run a GraphQL query through gh and return the `data` payload."""
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        flag = "-F" if isinstance(value, int) else "-f"
        cmd += [flag, f"{key}={value}"]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    combined = proc.stdout + proc.stderr

    if "read:project" in combined or "'project'" in combined:
        die(SCOPE_HINT)
    if proc.returncode != 0:
        die(f"gh api graphql failed:\n{proc.stderr.strip()}")

    payload = json.loads(proc.stdout or "{}")
    if payload.get("errors"):
        messages = "; ".join(e.get("message", "?") for e in payload["errors"])
        die(f"GraphQL: {messages}")
    return payload.get("data", {})


def current_repo() -> str:
    proc = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        die("could not detect the repo; pass --repo owner/name")
    return proc.stdout.strip()


def parse_issue(ref: str, repo_override: str | None):
    """Return (owner, repo, number) from an issue number or URL."""
    url = re.match(r"https?://github\.com/([^/]+)/([^/]+)/issues/(\d+)", ref)
    if url:
        return url.group(1), url.group(2), int(url.group(3))

    if not ref.lstrip("#").isdigit():
        die(f"'{ref}' is not an issue number or issue URL")

    repo = repo_override or current_repo()
    if "/" not in repo:
        die(f"--repo must look like owner/name, got '{repo}'")
    owner, name = repo.split("/", 1)
    return owner, name, int(ref.lstrip("#"))


ISSUE_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      id
      title
      url
      projectItems(first: 20) {
        nodes {
          id
          project { id title number }
          fieldValueByName(name: "%s") {
            ... on ProjectV2ItemFieldSingleSelectValue { name optionId }
          }
        }
      }
    }
  }
}
"""

FIELD_QUERY = """
query($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      fields(first: 50) {
        nodes {
          ... on ProjectV2SingleSelectField {
            id
            name
            options { id name }
          }
        }
      }
    }
  }
}
"""

MUTATION = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: { singleSelectOptionId: $optionId }
  }) {
    projectV2Item { id }
  }
}
"""


def fetch_issue(owner, repo, number, field_name):
    data = gh_graphql(ISSUE_QUERY % field_name, owner=owner, repo=repo, number=number)
    issue = (data.get("repository") or {}).get("issue")
    if not issue:
        die(f"issue #{number} not found in {owner}/{repo}")
    return issue


def pick_item(items, project_number, issue_url):
    if not items:
        die(
            f"{issue_url} is not on any Projects v2 board.\n"
            "Add it to the board first (in the GitHub UI, or with "
            "`gh project item-add`), then run this again."
        )
    if project_number is not None:
        for item in items:
            if item["project"]["number"] == project_number:
                return item
        available = ", ".join(str(i["project"]["number"]) for i in items)
        die(f"issue is not on project #{project_number}; it is on: {available}")
    if len(items) > 1:
        listing = "\n".join(
            f"  #{i['project']['number']}  {i['project']['title']}" for i in items
        )
        die(f"issue sits on several boards; pick one with --project:\n{listing}")
    return items[0]


def resolve_field(project_id, field_name):
    data = gh_graphql(FIELD_QUERY, projectId=project_id)
    nodes = ((data.get("node") or {}).get("fields") or {}).get("nodes") or []
    for node in nodes:
        if node.get("name", "").lower() == field_name.lower():
            return node
    names = ", ".join(n["name"] for n in nodes if n.get("name")) or "none"
    die(f"no single-select field called '{field_name}' on this board (found: {names})")


def match_option(options, wanted):
    names = [o["name"] for o in options]

    for option in options:
        if option["name"].lower() == wanted.lower():
            return option
    for option in options:
        if wanted.lower() in option["name"].lower():
            return option

    close = difflib.get_close_matches(wanted, names, n=1, cutoff=0.6)
    if close:
        return next(o for o in options if o["name"] == close[0])

    die(f"no column matching '{wanted}'. Columns on this board: {', '.join(names)}")


def main():
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("issue", help="issue number or URL")
    parser.add_argument("status", nargs="?", help="target column name")
    parser.add_argument("--repo", help="owner/name, defaults to current repo")
    parser.add_argument("--project", type=int, help="project number, if on several")
    parser.add_argument("--field", default="Status", help="field name (default: Status)")
    parser.add_argument("--list", action="store_true", help="show boards and columns")
    parser.add_argument("--dry-run", action="store_true", help="resolve but do not move")
    args = parser.parse_args()

    if not args.status and not args.list:
        parser.error("give a target status, or --list to see the options")

    owner, repo, number = parse_issue(args.issue, args.repo)
    issue = fetch_issue(owner, repo, number, args.field)
    items = issue["projectItems"]["nodes"]

    if args.list:
        if not items:
            print(f"#{number} is not on any Projects v2 board.")
            return
        for item in items:
            field = resolve_field(item["project"]["id"], args.field)
            value = item.get("fieldValueByName") or {}
            print(f"project #{item['project']['number']}  {item['project']['title']}")
            print(f"  {args.field}: {value.get('name') or '(unset)'}")
            print(f"  columns: {', '.join(o['name'] for o in field['options'])}")
        return

    item = pick_item(items, args.project, issue["url"])
    field = resolve_field(item["project"]["id"], args.field)
    option = match_option(field["options"], args.status)
    before = (item.get("fieldValueByName") or {}).get("name") or "(unset)"

    if before.lower() == option["name"].lower():
        print(f"#{number} is already in '{option['name']}' — nothing to do.")
        return

    if args.dry_run:
        print(f"would move #{number}: {before} -> {option['name']}")
        return

    gh_graphql(
        MUTATION,
        projectId=item["project"]["id"],
        itemId=item["id"],
        fieldId=field["id"],
        optionId=option["id"],
    )
    print(f"#{number} {before} -> {option['name']}  ({item['project']['title']})")


if __name__ == "__main__":
    main()
