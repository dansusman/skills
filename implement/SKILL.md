---
name: implement
description: Implement a spec or agent brief while keeping a running implementation-notes.md of decisions, deviations, and tradeoffs not captured in the spec. Use when the user says "implement <spec/brief>", hands off a ready-for-agent issue from /triage, or asks to build a feature and keep a record of choices made along the way.
---

# Implement

Implement a spec or agent brief. While you do, keep a running notes file of everything the spec did **not** decide for you, so the maintainer (and the later review pass) can see what happened.

This is the step after `/triage` produces a `ready-for-agent` brief. The notes file you produce is the handoff artifact that `/adversarial-review` reads.

## Quick start

1. Read the spec/brief. If it's a triage agent brief, the brief is the contract — original issue is context.
2. Create `implementation-notes.md` at repo root (markdown default; use `.html` only if the user asks for a rich rendering).
3. Implement. Update notes **as you go**, not at the end.
4. End by re-reading the notes for accuracy and posting a short summary of the most important entries.

## What goes in the notes

Log an entry whenever you hit something the spec did not pin down. Each entry: **what** + **why**. Categories:

- **Decision** — choice the spec left open (naming, structure, library, edge-case behavior).
- **Deviation** — where you changed something from what the spec said, and why it was necessary.
- **Tradeoff** — option picked over an alternative; name the alternative and the cost.
- **Surprise** — anything in the codebase that contradicted the spec's assumptions.
- **Heads-up** — anything the maintainer should know (follow-up needed, risk, untested path, assumption made).

Skip the obvious. Notes are for non-obvious choices, not a play-by-play of every edit.

## Notes file format

```markdown
# Implementation Notes — <spec/brief title>

Spec: <link to issue / path to spec>

## Decisions
- **<short title>** — <what you chose>. Why: <reason>. Alt considered: <if any>.

## Deviations
- **<what changed vs spec>** — Why: <reason>.

## Tradeoffs
- **<choice>** over <alternative> — Cost: <what you gave up>.

## Heads-up
- <thing the maintainer / reviewer should check>
```

Keep sections; append within them as you work. One file per branch.

## Rules

- Notes file lives at repo root, committed with the work (it's a deliverable, not scratch).
- Do not invent decisions to log — only real ones.
- If the spec is ambiguous on something material, log it as a Decision **and** flag it to the user; don't silently guess on high-stakes calls.
- Follow repo-wide policies (CLAUDE.md, ADRs, lint/test conventions) — those are not "decisions", they're constraints.
