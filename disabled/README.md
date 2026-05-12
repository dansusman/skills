# Disabled Skills

Skills in this directory are kept for reference but excluded from Claude's auto-load.

Claude only scans top-level directories under `~/.claude/skills/` for `SKILL.md`, so anything nested here is invisible to the loader while remaining in the repo.

## Using a disabled skill ad-hoc

Point Claude at the file directly:

> follow the instructions at `~/skills/disabled/<name>/SKILL.md`

## Re-enabling

```
cd ~/skills
git mv disabled/<name> ./
git commit -m "chore: re-enable <name> skill"
git push
```

Then `git pull` in `~/.claude/skills`.
