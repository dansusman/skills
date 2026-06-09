#!/usr/bin/env python3
"""Render a Claude Code session transcript into a prompt-centric digest.

Human prompts are the spine. Each turn renders with a bold role label: the
"You" prompt sits in a blockquote (the left bar marks it as the input),
while "Claude" shows a one-line semantic summary flush, with the full
response folded into a <details> blockquote below it. Tool calls, tool
results, and thinking blocks are dropped entirely -- they carry the leak
surface (file contents, secrets, paths) and add no prompting signal.

Two-pass workflow for the semantic summaries:
  1. prompt-digest.py SESSION.jsonl --emit-turns > turns.json
  2. (caller summarizes each agent reply into summaries.json)
  3. prompt-digest.py SESSION.jsonl --summaries summaries.json --redact

Usage:
    prompt-digest.py SESSION.jsonl [--summaries FILE] [--redact]
    prompt-digest.py --latest [--project DIR] ...
    prompt-digest.py SESSION.jsonl --emit-turns

Output is GitHub-flavored markdown to stdout.
"""

import argparse
import glob
import json
import os
import re
import sys

META_TAG = re.compile(r"^\s*<(command-message|command-name|command-args|"
                      r"local-command-stdout|local-command-stderr)\b")
SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>",
                             re.DOTALL)
CMD_NAME = re.compile(r"<command-name>(.*?)</command-name>", re.DOTALL)
CMD_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.DOTALL)
MD_LEAD = re.compile(r"^[#>*\-\s`]+")
INTERRUPT = re.compile(r"^\[Request interrupted by user[^\]]*\]$")

# Conservative secret/credential patterns. Each is high-signal -- chosen to
# minimize false positives on ordinary prose and code. The redactor replaces a
# match with [REDACTED:<name>]. Order matters: more specific patterns first.
SECRET_PATTERNS = [
    ("private-key",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*"
                r"PRIVATE KEY-----", re.DOTALL)),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token",
     re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("slack-token",
     re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}"
                       r"\.[A-Za-z0-9_-]{10,}\b")),
    ("url-credentials",
     re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/:@]+@")),
    ("bearer-token",
     re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._-]{20,}")),
    ("assigned-secret",
     re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|"
                r"auth[_-]?token|client[_-]?secret)\b\s*[:=]\s*"
                r"['\"]?[^\s'\"]{6,}['\"]?")),
]
EMAIL_PATTERN = ("email",
                 re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+"
                            r"\.[A-Za-z]{2,}\b"))


def clean_prompt(text):
    """Strip injected meta from a human prompt; return None if nothing real."""
    text = SYSTEM_REMINDER.sub("", text)
    text = text.strip()
    if not text or META_TAG.match(text) or INTERRUPT.match(text):
        return None
    return text


def slash_command(text):
    """If the message is a slash-command invocation, return a one-line label."""
    name = CMD_NAME.search(text)
    if not name:
        return None
    args = CMD_ARGS.search(text)
    label = name.group(1).strip()
    if args and args.group(1).strip():
        label += " " + args.group(1).strip()
    return label


def first_line(text, limit):
    """First meaningful line, markdown lead-ins stripped, clipped to limit."""
    for line in text.splitlines():
        stripped = MD_LEAD.sub("", line).strip()
        if stripped:
            return stripped[:limit] + ("…" if len(stripped) > limit else "")
    return "(reply)"


def one_line(text, limit):
    """Collapse to a single clipped line (for the outline)."""
    flat = " ".join(text.split())
    return flat[:limit] + ("…" if len(flat) > limit else "")


def extract_turns(path):
    """Walk the transcript, yielding ('human'|'slash'|'agent', text) in order."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("isMeta"):
                continue  # command expansions, hook output, injected context
            if rec.get("type") == "user":
                content = rec.get("message", {}).get("content")
                if isinstance(content, str):
                    cmd = slash_command(content)
                    if cmd:
                        yield ("slash", cmd)
                        continue
                    prompt = clean_prompt(content)
                    if prompt:
                        yield ("human", prompt)
                elif isinstance(content, list):
                    for block in content:
                        if block.get("type") == "text":
                            prompt = clean_prompt(block.get("text", ""))
                            if prompt:
                                yield ("human", prompt)
            elif rec.get("type") == "assistant":
                parts = []
                for block in rec.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                text = "\n".join(parts).strip()
                if text:
                    yield ("agent", text)


def merge_agent(turns):
    """Collapse consecutive agent turns (split by tool calls) into one."""
    merged = []
    for kind, text in turns:
        if kind == "agent" and merged and merged[-1][0] == "agent":
            merged[-1] = ("agent", merged[-1][1] + "\n\n" + text)
        else:
            merged.append((kind, text))
    return merged


def drop_trailing_slash(turns):
    """Drop trailing slash turns -- usually the invocation that made this digest."""
    while turns and turns[-1][0] == "slash":
        turns.pop()
    return turns


def emit_turns_json(turns):
    """Emit human + agent turns keyed by index, for an external summarizer.

    Agent turns want a `summary`; human turns want an outline `summary` and
    optional `tags`.
    """
    return [{"id": i, "kind": kind, "text": text}
            for i, (kind, text) in enumerate(turns) if kind in ("human", "agent")]


def tag_kbd(meta):
    """Render tags as <kbd> chips (these survive GitHub markdown sanitization)."""
    tags = meta.get("tags") if meta else None
    return "".join(f" <kbd>{t}</kbd>" for t in tags) if tags else ""


def quote(text):
    """Render text as a markdown blockquote, preserving blank lines."""
    return "\n".join((f"> {ln}" if ln.strip() else ">")
                     for ln in text.strip().splitlines())


def redact_turns(turns, do_redact, include_emails, findings):
    """Scan every turn's text for secrets. Tally into `findings`.

    When do_redact, replace each match with [REDACTED:<name>]; otherwise leave
    text untouched (the tally still warns the caller). Returns new turns.
    """
    patterns = list(SECRET_PATTERNS)
    if include_emails:
        patterns.append(EMAIL_PATTERN)

    def scrub(text):
        for name, pat in patterns:
            if do_redact:
                def repl(m, name=name):
                    findings[name] = findings.get(name, 0) + 1
                    return f"[REDACTED:{name}]"
                text = pat.sub(repl, text)
            else:
                hits = len(pat.findall(text))
                if hits:
                    findings[name] = findings.get(name, 0) + hits
        return text

    return [(kind, scrub(text)) for kind, text in turns]


def render_md(turns, summaries):
    outline, body = [], []
    n = 0
    for i, (kind, text) in enumerate(turns):
        meta = summaries.get(str(i), {})
        if kind == "human":
            n += 1
            tags = tag_kbd(meta)
            label = meta.get("summary") or one_line(text, 120)
            outline.append(f"{n}. {label}{tags}")
            if n > 1:
                body.append("---\n")
            body.append(f"**{n}. You**{tags}\n\n{quote(text)}\n")
        elif kind == "slash":
            outline.append(f"- <kbd>cmd</kbd> `{text}`")
            body.append(f"**<kbd>cmd</kbd> `{text}`**\n")
        elif kind == "agent":
            summary = meta.get("summary") or first_line(text, 90)
            body.append(f"**Claude** — {summary}\n")
            body.append("<details><summary>full response</summary>\n\n" +
                        quote(text) + "\n\n</details>\n")

    out = ["# Prompt digest\n", "## The arc\n"]
    out.extend(outline)
    out.append("\n---\n")
    out.extend(body)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session", nargs="?", help="path to SESSION.jsonl")
    ap.add_argument("--latest", action="store_true",
                    help="use most recent transcript in --project")
    ap.add_argument("--project", default=os.getcwd(),
                    help="working dir to resolve transcripts for --latest")
    ap.add_argument("--emit-turns", action="store_true",
                    help="emit agent replies as JSON for an external summarizer")
    ap.add_argument("--summaries",
                    help="JSON file: {turn_index: {summary, tags}}")
    ap.add_argument("--redact", action="store_true",
                    help="replace detected secrets with [REDACTED:<type>]")
    ap.add_argument("--redact-emails", action="store_true",
                    help="also treat email addresses as redactable PII")
    args = ap.parse_args()

    path = args.session
    if args.latest:
        slug = "-" + args.project.strip("/").replace("/", "-")
        pattern = os.path.expanduser(f"~/.claude/projects/{slug}/*.jsonl")
        matches = sorted(glob.glob(pattern), key=os.path.getmtime)
        if not matches:
            sys.exit(f"no transcripts found for {pattern}")
        path = matches[-1]
        print(f"# source: {path}", file=sys.stderr)
    if not path:
        ap.error("provide SESSION.jsonl or --latest")

    turns = drop_trailing_slash(merge_agent(list(extract_turns(path))))

    findings = {}
    turns = redact_turns(turns, args.redact, args.redact_emails, findings)
    if findings:
        verb = "Redacted" if args.redact else "DETECTED (not redacted)"
        report = ", ".join(f"{n}×{k}" for k, n in sorted(findings.items()))
        print(f"# {verb}: {report}", file=sys.stderr)
        if not args.redact:
            print("# Re-run with --redact to scrub before sharing.",
                  file=sys.stderr)

    if args.emit_turns:
        json.dump(emit_turns_json(turns), sys.stdout, indent=2,
                  ensure_ascii=False)
        print()
        return

    summaries = {}
    if args.summaries:
        with open(args.summaries) as f:
            summaries = json.load(f)

    print(render_md(turns, summaries))


if __name__ == "__main__":
    main()
