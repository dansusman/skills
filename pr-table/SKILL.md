---
name: pr-table
description: "Read the review comments on a GitHub PR and output a triage table of each comment, whether to address it now, the justification, and ease of implementation. Triggers on 'pr table for <num>', 'triage pr comments for <num>', or a request to look at PR comments and decide what to address."
argument-hint: <pr-number>
---

# Triage PR Comments

Given a PR number, fetch its review comments and produce a single table the human can use to decide what to act on.

## Inputs

The user gives a PR number (e.g. `55102`), optionally with a repo (e.g. `pr table for owner/repo#123`).

**Resolve the repo first, don't hardcode it:**
- If the user names a repo, use it.
- Otherwise default to the repo of the current working directory: `REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)`.
- If that fails (not inside a repo) and the user gave no repo, stop and ask which repo.

All `gh` calls below take `--repo "$REPO"` (or substitute `$REPO` into the api path) so the skill works in any repo, not just one.

## Workflow

### 1. Gather PR context and comments

```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)   # or the repo the user named

gh pr view <num> --repo "$REPO" --json title,body,author,url
gh pr diff <num> --repo "$REPO"
# Inline review comments (line-level, the main source)
gh api "repos/$REPO/pulls/<num>/comments" --paginate
# Top-level review summaries
gh api "repos/$REPO/pulls/<num>/reviews" --paginate
# Issue-style conversation comments
gh api "repos/$REPO/issues/<num>/comments" --paginate
# Thread RESOLUTION state — the REST /comments endpoint does NOT expose whether a
# thread is resolved/outdated. Always pull this too and key the table off it.
# owner/name come from $REPO (split on the slash).
gh api graphql -F owner="${REPO%/*}" -F name="${REPO#*/}" -F num=<num> -f query='
query($owner:String!, $name:String!, $num:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$num) {
      reviewThreads(first:100) {
        nodes {
          isResolved
          isOutdated
          comments(first:20) { nodes { databaseId author{login} path line originalLine } }
        }
      }
    }
  }
}'
```

Read the diff so you can judge each comment against the actual code, not just its text.

**Resolution state is the primary signal, not the diff.** Join each comment (by `databaseId`) to its thread's `isResolved` / `isOutdated`. A maintainer who resolved a thread has already dispositioned it — treat it as closed even if the code looks unchanged (it's a conscious won't-do / deferral). Do not re-litigate resolved threads or infer "still open" from the diff alone; the diff tells you *how* something was addressed, the thread state tells you *whether* it's still live.

### 2. Build the table

One row per substantive **unresolved** comment. Skip pure chatter (e.g. "LGTM", emoji-only, bot noise) — note in a line below the table how many you dropped and why.

Put **resolved** threads in a separate "Already resolved — no action" list below the table, each with a one-clause disposition (fixed in commit X / declined by author / deferred). Don't give them table rows — they're not decisions the human still has to make.

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

- If a comment thread has back-and-forth, judge the *latest* state — don't surface asks the author already pushed back on and the reviewer dropped. A thread marked `isResolved` is settled regardless of what the visible code shows.
- If `gh` can't reach the PR (wrong repo, auth), stop and report it rather than guessing.
