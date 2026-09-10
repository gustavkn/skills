# GitHub Projects v2 via GraphQL

`scripts/project_status.py` covers the common case (move a card between Status
columns). Reach for the raw API below when something else is needed: adding an
issue to a board, setting a date or number field, or debugging why a lookup
came back empty.

Projects v2 is **GraphQL only** — there are no REST endpoints, and `gh project`
cannot set a single-select field on an item. All calls go through
`gh api graphql`.

## Scopes

The token needs `project` to write and `read:project` to read:

```bash
gh auth status                 # shows current scopes
gh auth refresh -s project     # interactive; the user must run this
```

A missing scope shows up as `your authentication token is missing required
scopes [read:project]`. Do not try to work around it — ask the user to refresh.

## Finding things

Boards owned by a user or org:

```bash
gh project list --owner <login>
```

Board id, fields and their option ids in one call:

```bash
gh api graphql -f query='
query($login: String!, $number: Int!) {
  user(login: $login) {              # organization(login:) for org boards
    projectV2(number: $number) {
      id
      title
      fields(first: 50) {
        nodes {
          ... on ProjectV2SingleSelectField { id name options { id name } }
          ... on ProjectV2Field { id name dataType }
        }
      }
    }
  }
}' -f login=<login> -F number=<n>
```

Which boards an issue is on, plus its current Status:

```bash
gh api graphql -f query='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      id
      projectItems(first: 20) {
        nodes {
          id
          project { id title number }
          fieldValueByName(name: "Status") {
            ... on ProjectV2ItemFieldSingleSelectValue { name optionId }
          }
        }
      }
    }
  }
}' -f owner=<owner> -f repo=<repo> -F number=<issue>
```

Note the two distinct ids: `project.id` is the board, `node.id` on the item is
the **card**. Mutations need both.

## Mutations

Set a single-select field (this is what the script does):

```bash
gh api graphql -f query='
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId, itemId: $itemId, fieldId: $fieldId,
    value: { singleSelectOptionId: $optionId }
  }) { projectV2Item { id } }
}' -f projectId=<PVT_...> -f itemId=<PVTI_...> -f fieldId=<PVTSSF_...> -f optionId=<abc12345>
```

Other field types swap the `value` shape: `{ text: "..." }`,
`{ number: 3 }`, `{ date: "2026-09-10" }`, `{ iterationId: "..." }`.

Add an issue to a board (returns the new card id):

```bash
gh api graphql -f query='
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
    item { id }
  }
}' -f projectId=<PVT_...> -f contentId=<issue node id>
```

`gh project item-add <number> --owner <login> --url <issue url>` does the same
thing with less ceremony, and is the better choice when the board is known.

## Gotchas

- **Node id prefixes**: `PVT_` board, `PVTI_` card, `PVTSSF_` single-select
  field, `I_` issue. A mutation that rejects an id is usually being handed the
  wrong one of these.
- **Option ids are per-board.** "Done" on one board has a different option id
  than "Done" on another. Never cache them across repos.
- **Column names drift.** "In Progress" / "In progress" / "Doing" are all in the
  wild. The script matches case-insensitively, then by substring, then by close
  match — prefer it over hardcoding a name.
- **Classic projects** (`/projects/1` on a repo, not `/users/x/projects/1`) use a
  different, deprecated API. `projectItems` returns empty for them. If a board
  looks invisible, check whether it is a classic project.
- **Automatic workflows.** Many boards already move cards to "Done" when an
  issue closes. Check the board's built-in workflows before adding a manual move
  that fights them — a duplicate move is harmless, but a contradictory one is
  confusing.
- **Closing an issue does not move the card** unless such a workflow exists.
  Assume it does not.
