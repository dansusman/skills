---
name: pr-table
description: "Read the review comments on a GitHub PR and output a triage table of each comment, whether to address it now, the justification, and ease of implementation. Triggers on 'pr table for <num>', 'triage pr comments for <num>', or a request to look at PR comments and decide what to address."
argument-hint: <pr-number>
---

# Triage PR Comments

Given a PR number, fetch its review comments and produce a single table the human can use to decide what to act on.

## Inputs

The user gives a PR number (e.g. `55102`). Assume the `Ginger-Labs/Notability` repo unless told otherwise.

## Workflow

### 1. Gather PR context and comments

```bash
gh pr view <num> --json title,body,author,url
gh pr diff <num>
# Inline review comments (line-level, the main source)
gh api repos/Ginger-Labs/Notability/pulls/<num>/comments --paginate
# Top-level review summaries
gh api repos/Ginger-Labs/Notability/pulls/<num>/reviews --paginate
# Issue-style conversation comments
gh api repos/Ginger-Labs/Notability/issues/<num>/comments --paginate
```

Read the diff so you can judge each comment against the actual code, not just its text.

### 2. Build the table

One row per substantive comment. Skip pure chatter (e.g. "LGTM", emoji-only, bot noise) — note in a line below the table how many you dropped and why.

For each comment, fill the columns:

- **Comment** — short paraphrase of the ask, with the file:line and commenter. Keep it to one line.
- **Address now or not** — `Now` or `Later` (use `Later` for follow-up tickets, nits the author can defer, or out-of-scope ideas).
- **Justification** — one clause on *why* that call: blocks correctness/ship → Now; cosmetic, speculative, or separate concern → Later.
- **Ease of implementation** — `Trivial` / `Moderate` / `Involved`, judged from the diff and surrounding code.

Order rows `Now` first (hardest first within that group), then `Later`.

### 3. Output

Render as a Markdown table:

| Comment | Address now or not | Justification | Ease of implementation |
|---|---|---|---|

Do **not** post anything to the PR, reply to comments, or push changes — the table is for the human to act on. If the user then asks you to address a row, that's a separate request.

## Notes

- If a comment thread has back-and-forth, judge the *latest* resolved state — don't surface asks the author already pushed back on and the reviewer dropped.
- If `gh` can't reach the PR (wrong repo, auth), stop and report it rather than guessing.
