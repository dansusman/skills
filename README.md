# skills

Agent skills consumed by Claude Code, pi coding agent, and Warp.

Clone to `~/skills`. The dotfiles repo symlinks `config/.config/agents/skills` to this directory, and downstream consumers symlink in turn:

- `~/.claude/skills` → `~/.dotfiles/config/.config/claude/skills` → `../agents/skills` → `~/skills`
- `~/.agents/skills` → `~/skills`
- `~/warp/.claude/skills` → `~/skills`

See [dansusman/dotfiles](https://github.com/dansusman/dotfiles) for install/setup.
