---
name: adversarial-review
description: Adversarially review the changes on the current branch — reduce layers, remove complexity, increase reliability, confirm repo-wide policies hold, verify changes work, and preserve the original intent. Use when the user asks for an adversarial review, says "review this branch / these changes", or wants to harden and simplify work before merge. Reads implementation-notes.md when present.
---

# Adversarial Review

Review the changes on the current branch as a skeptic. Goal: simpler, fewer layers, more reliable — without losing the original intent. This is the review step after `/implement`.

## Inputs (gather first)

1. **The diff** — `git diff <base>...HEAD` (ask for base if unclear; default to the repo's main branch).
2. **`implementation-notes.md`** if present — the implementer's record of decisions, deviations, tradeoffs. Treat logged decisions as deliberate (challenge them, but know they were intentional); treat *unlogged* surprises as higher-risk.
3. **Original intent** — the spec / agent brief / issue the work came from. You must preserve this.
4. **Repo-wide policies** — CLAUDE.md, ADRs, lint/test/style conventions.

## Review dimensions

Go through each adversarially — assume there's a problem and try to find it:

- **Reduce layers** — needless indirection, wrapper-of-a-wrapper, abstractions with one caller, premature generalization. Propose the flatter version.
- **Remove complexity** — dead branches, redundant state, special-cases that could be unified, options nobody asked for. Simplest *correct* change wins.
- **Increase reliability** — unhandled errors, race conditions, missing edge cases, silent failures, untested paths. Where would this break in production?
- **Policies hold** — does the diff obey CLAUDE.md / ADRs / repo conventions? Flag every violation.
- **Verified** — are the changes actually exercised? Run tests/build/the app where possible. Don't trust "looks right" — confirm. Call out anything you could not verify.
- **Intent preserved** — does it still do what the spec asked? Flag any simplification that would drop required behavior.

## Output

Group findings by dimension. For each:

- **Severity** — must-fix / should-fix / consider.
- **What** — the issue, with `file:line`.
- **Why** — concrete failure or cost.
- **Fix** — the change you'd make (or the smaller diff).

End with: a one-line verdict (ship / fix-then-ship / rework), and explicitly state what you verified vs. could not verify.

## Rules

- Adversarial ≠ rewrite-everything. Smallest change that's actually right. Don't trade one complexity for another.
- A logged tradeoff in the notes is not automatically wrong — engage with its reasoning before overriding.
- Don't post to the issue tracker or push; this is a local review pass unless the user says otherwise.
