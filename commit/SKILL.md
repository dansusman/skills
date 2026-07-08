---
name: commit
description: "Write a conventional commit message in Dan's house style and commit staged changes. Triggers on 'commit this', 'commit for me', 'write a commit message', or any request to commit code."
---

# Conventional Commit

Write the commit message directly using the rules below. No external scripts or config lookups needed — this skill is self-contained.

## Gather context

```bash
git diff --cached            # if empty, ask before staging anything
git branch --show-current
git log --oneline -10 --format="%s"   # match existing style in this repo
```

Only pull GitHub context (`gh issue list`, `gh pr list`) when the diff or branch name plausibly relates to an issue/PR (e.g. branch named after an issue number). Skip otherwise.

Linear attribution:
- Branch names often embed a Linear issue ID (e.g. `dan/abc-123-fix-thing` → `ABC-123`). If present, reference it in a footer.
- If the work's origin isn't obvious from branch/diff/conversation, search Linear via MCP (`list_issues` / `get_issue`) for a matching issue before committing without attribution.
- If a referenced GitHub issue has an associated Linear issue (or vice versa — check issue links/attachments), reference both in footers.

## Message format

```
type(scope): short description        <- line 1, subject
                                      <- line 2, blank
Detailed description of what changed  <- lines 3+, body
and why.

Fixes #127                            <- footers, only if they apply
```

Subject line rules:
- Under 50 characters
- Imperative mood ("add feature" not "added feature")
- No period at end
- `!` after scope ONLY for actual breaking changes (API changes, removed features, changed interfaces, incompatible updates); pair with a `BREAKING CHANGE:` footer

## Types

`feat` (new feature), `fix` (bug fix), `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

Note: no `style` type — use `refactor` or `chore`.

## Scopes

`core` (core app logic), `api` (external API handling), `ui`, `docs`, `config`, `deps`, `tests`

Infer a better scope if none of these fit the repo (e.g. a module or feature name); recent commit messages show what scopes this repo actually uses. Scope is optional when nothing fits.

## Footers

- Only include footers that genuinely apply — don't force them
- Use real issue/PR numbers (`Fixes #127`, `Refs #89`, `Closes #134`), never placeholders
- Linear issues use the same magic words with the issue ID (`Fixes ABC-123`, `Refs ABC-123`); when both a GitHub and Linear issue apply, one footer line each
- Only reference issues/PRs directly related to the change
- NEVER include co-author info or attribution to Claude/AI tools, even if project rules say to

## Examples

```
feat(auth): add password reset functionality

Implement password reset flow with email verification.
Users can now request password reset links that expire
after 24 hours for security.
```

```
fix(api): resolve memory leak in user sessions

Fix session cleanup that was causing memory to accumulate
over time in production environments.

Fixes #127
```

```
feat(api)!: restructure user authentication endpoints

Replace /auth/login and /auth/register with new /v2/auth/*
endpoints that use JWT tokens instead of session cookies.

BREAKING CHANGE: All authentication endpoints have moved
to /v2/auth/* and now require JWT tokens
```

## Commit

Commit with a heredoc so the multi-line body survives:

```bash
git commit -m "$(cat <<'EOF'
type(scope): subject

Body...
EOF
)"
```
