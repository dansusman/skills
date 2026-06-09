---
name: prompt-digest
description: Render a Claude Code session transcript into a prompt-centric digest for sharing on AI-assisted PRs. Human prompts are the spine; agent replies are collapsed previews; tool calls/results/thinking are dropped. Triggers on "prompt digest", "share my prompting", "digest this session".
---

Produce a shareable digest of a coding session that shows *how the work was steered* — the human prompts plus thin agent-reply context — without leaking tool I/O, file contents, or secrets.

## When to use

The user wants to share their prompting on an AI-led/AI-assisted PR, or asks for a "prompt digest" of a session. Output is GitHub-flavored markdown, meant to be pasted straight into a PR description or comment.

## How it works

`prompt-digest.py` parses a transcript `.jsonl` and emits an interleaved digest:

- **The arc** — a numbered outline of just the human prompts at the top, for a 10-second scan of the whole session. Each prompt is tagged (`ask`/`steer`/`constraint`/`approve`/`scope`…) via `<kbd>` chips.
- **Human turns** — a bold **You** label (numbered, tagged) with the full prompt in a blockquote.
- **Agent turns** — a bold **Claude** label with the one-line semantic summary flush, followed by a collapsed `<details>` holding the full response as a blockquote.
- **Slash commands** — collapsed to one line (`<kbd>cmd</kbd> /schedule list`).
- **Dropped entirely** — `tool_use`, `tool_result`, `thinking`, any `isMeta` record (command expansions, hook output, injected context), `[Request interrupted…]` markers, and the trailing slash-invocation that triggered the digest. This is the leak surface; it never appears in output.

The asymmetric layout — prompt in a quote, Claude's summary flush — makes the back-and-forth obvious without misleading callout chrome, and renders cleanly in any markdown viewer (not just GitHub).

## Producing a digest (recommended: with semantic summaries)

This is the default workflow when the user asks for a digest. The model (you)
acts as the summarizer — no external API call.

1. **Emit the agent replies** to summarize:
   ```bash
   python3 ~/skills/prompt-digest/prompt-digest.py --latest --project "$PWD" --emit-turns
   ```
   Returns `[{id, text}, …]` for each agent reply (ids are turn indices).
2. **Write `summaries.json`** keyed by turn index. For each agent reply give a
   one-line `summary`; for human prompts (the in-between ids) optionally give
   `tags`. Shape:
   ```json
   {
     "0": {"tags": ["ask"]},
     "1": {"summary": "Four idea tiers; recommends template + prompt extraction."},
     "2": {"tags": ["steer"]}
   }
   ```
   Keep summaries factual and short. Don't invent — summarize only what the
   reply says.
3. **Render** with the summaries and redaction (always redact for anything
   leaving the machine):
   ```bash
   python3 ~/skills/prompt-digest/prompt-digest.py --latest --project "$PWD" \
     --summaries summaries.json --redact
   ```
   Add `--redact-emails` if email addresses count as PII for this audience. The
   scanner always runs and reports detections to stderr; `--redact` replaces
   them inline with `[REDACTED:<type>]`.
4. **Show the user** the output; let them confirm/trim before it goes anywhere.
   Markdown pastes straight into a PR description — nothing leaves the machine.

## Quick / no-summary mode

Skip the summaries pass for a fast first look (agent summaries fall back to each
reply's first meaningful line, prompts are untagged):

```bash
python3 ~/skills/prompt-digest/prompt-digest.py --latest --project "$PWD"
```

## Flags & paths

- `--latest --project DIR` resolves the newest transcript for a working dir and prints the chosen file to stderr. Transcripts live at `~/.claude/projects/<slug>/*.jsonl` (`<slug>` = the dir with `/`→`-` and a leading `-`). Or pass `SESSION.jsonl` directly.
- `--summaries FILE` — the semantic-summary / tag sidecar (above).
- `--emit-turns` — dump human + agent turns as JSON for the summarizer pass.
- `--redact` — replace detected secrets with `[REDACTED:<type>]`.
- `--redact-emails` — also redact email addresses (off by default; emails are common in prose, so this is opt-in).

## Redaction coverage

`--redact` catches high-signal credential shapes: private keys, AWS access keys,
GitHub tokens/PATs, Slack tokens, Anthropic/OpenAI/Google API keys, JWTs,
`user:pass@` URLs, `Bearer` tokens, and `secret=`/`api_key=`-style assignments.
Emails are opt-in via `--redact-emails`.

It is a **safety net, not a guarantee** — it cannot catch novel token shapes,
proprietary identifiers, or sensitive prose. The reviewer still eyeballs the
output before it goes anywhere.

## Caveats (state these when sharing output)

- Redaction is pattern-based; review the output before publishing regardless.
- Agent text is emitted as a blockquote inside `<details>`; a code fence inside a reply can interact with surrounding markdown. Usually fine; eyeball it.
- One-off personal testing tool — not wired into `create-pr`.
