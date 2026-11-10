---
name: moved-code-review
description: "Render a commit, commit range, or PR as a GitHub-style review page (claude.ai Artifact) that folds code that moved unchanged and labels where each block moved to/from, so only real edits stand out. Use when a commit or PR is mostly moved code, when a commit message says code moves 'unchanged', when the user mentions `--color-moved` / dimmed-zebra, or asks for a moved-code / move review view. Triggers on 'moved code review for <sha|#pr>', 'show the moves', 'review these moved methods'."
argument-hint: <sha | A..B | #pr> [--ws allow-indentation-change]
---

# Moved Code Review

GitHub can't show moved code. `scripts/build.py` runs git with `--color-moved=dimmed-zebra`, parses the colors into removed / added / moved lines, pairs each moved-out block with its moved-in copy, and fills `scripts/template.html` into one self-contained page.

## Steps

1. **Resolve the target.** A commit sha, a range (`A..B`, `A...B`), or a PR (`#123`). For a whole stacked branch, a range from the stack base is usually what the user wants. Run from inside the repo, or pass `--repo-dir`.

2. **Build.** Write to the session scratchpad, one file per target:

   ```bash
   python3 -I ~/skills/moved-code-review/scripts/build.py <target> <scratchpad>/moves-<slug>.html --title "<Name>"
   ```

   - `--title`: a two-to-four-word name for the change (e.g. "Library Helpers Move"), not "Moves in abc123". Default is `Moves in <ref>`.
   - `--ws allow-indentation-change`: add when the moved code was re-indented (wrapped in `Task {}`, moved into a nested type, etc.). Without it, re-indented lines count as real edits.
   - PR mode fetches `refs/pull/<n>/head` and the base branch from `origin` and diffs against their merge base.

   It prints one JSON line: `moved_pct`, `real_added`, `real_removed`, `moved`, `unpaired_moved`.

3. **Check the fit.** If `moved_pct` is under ~40, tell the user this change is mostly real edits and the view helps less, then publish anyway if they asked for it. If the result looks low but the code was re-indented, rebuild with `--ws allow-indentation-change` first.

4. **Publish** the file with the Artifact tool (`icon: "code"`, one-sentence description naming the commit/PR). Re-running on the same target: rebuild to the same path and republish that path so the URL stays.

5. **Report**: the link, a small table of per-file real −/+/moved counts, and the real (non-moved) changes in one or two lines so the user knows what to read closely. Mention the artifact is private until shared from its Share menu. Never add the link to a PR description or comment unless the user asks.

## What the page does

- Real removals/additions in red/green; moved lines in purple with alternating shades per block and a marked edge on block boundaries.
- Moved runs fold to "▸ N moved lines unchanged, moved to [file L120–161]". Chips jump to the other side, open its fold, and flash the lines.
- File summary table, sticky file headers, collapse per file, global "Fold moved lines" toggle.

## Caveats to tell the user when relevant

- Pairing is computed by the script (git doesn't report destinations): longest identical contiguous block wins. Long blocks are reliable; 1–3 line fragments (`}`, blank lines, license headers) can link to a different identical copy. Lines with no match show as "unpaired".
- Git's own move detection needs a block of at least 20 alphanumeric characters, so tiny moves show as real −/+.
- The script pins all diff colors with `git -c`, so the user's color config doesn't affect parsing.
