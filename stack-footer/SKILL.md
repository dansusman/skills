---
name: stack-footer
description: "Add or refresh a stacked-PR footer (### Stack list) on every PR in a stack. Triggers on 'stack footer', 'add stack footer', 'update stack links', or a request to cross-link a stack of PRs in their descriptions."
argument-hint: "[pr-number]"
---

# Stacked-PR Footer

Given a PR (or the current branch's PR), discover the full stack it belongs to and write a cross-linking footer into every PR body in the stack.

## Inputs

- Optional PR number; otherwise use the current branch's PR (`gh pr view --json number`).
- Resolve the repo like any `gh` work: user-named repo wins, else `gh repo view --json nameWithOwner -q .nameWithOwner`. Pass `--repo "$REPO"` on every call.

## Footer format

```markdown
### Stack

1. `main`
2. #101
3. **#102** 👈 this PR
4. `feature-c`
```

Rules:
- Numbered list, ordered bottom→top: item 1 is always the trunk branch name in code ticks; item 2 is the bottom PR of the stack; the last item is the top.
- Each stack entry renders as `#<number>`. A branch that has no PR yet renders as the branch name in code ticks.
- In each PR's own body, bold that PR's entry and append ` 👈 this PR`: `**#102** 👈 this PR`. The bold + pointer moves per PR; everything else is identical across the stack.
- Blank line between `### Stack` and the list, markers on their own lines.

## Workflow

### 1. Discover the stack

Fetch all open PRs once, then chain by base branch:

```bash
gh pr list --repo "$REPO" --state open --json number,headRefName,baseRefName --limit 200
```

- **Downward:** from the starting PR, follow `baseRefName` to the PR whose `headRefName` matches it; repeat until the base has no open PR — that base branch is the trunk.
- **Upward:** find PRs whose `baseRefName` equals the current head; repeat from each. If a branch has more than one child, the stack forks — stop and ask the user which chain to footer rather than guessing.

A single PR based on trunk is a stack of one — still valid; the footer just shows trunk plus that PR.

### 2. Render and replace idempotently

For each PR in the stack, fetch its body (`gh pr view <num> --repo "$REPO" --json body -q .body`), then:

- Otherwise trim trailing newlines and append the block after one blank line. An empty body becomes just the block.

Running the skill twice must produce the same bodies (replace, never append a second block).

### 3. Update the PRs

Write each new body with `gh pr edit <num> --repo "$REPO" --body-file <tempfile>` (body via file, not `--body`, to avoid shell-quoting damage). Update every PR in the stack, not just the starting one.

Finish by listing which PRs were updated, in stack order.

## Notes

- Only edit PR bodies. Never push, rebase, or change PR bases.
- Skip closed/merged PRs when chaining; if the stack's bottom PR merged, the next PR's base is now effectively trunk.
- If `gh` can't find a PR for the current branch and no number was given, stop and ask.
