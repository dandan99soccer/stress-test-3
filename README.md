# stress-test-3

A Claude skill that pressure-tests a decision: it generates genuinely different options, screens them, and compares the survivors through lenses chosen for the kind of decision. Level 1 is a cheap single-turn pass and the default; levels 2 to 6 go deeper (research, replication, forecasting) and run only when asked for by name.

## Install

**Claude Code**

```bash
git clone https://github.com/dandan99soccer/stress-test-3 ~/.claude/skills/stress-test-3
```

The folder name is free: claude.ai may list the skill as `stress-test-31` or another name, and nothing in the files depends on it.

**Claude.ai / Claude desktop:** download this repo as a ZIP and upload it under Settings → Capabilities → Skills.

## Use

Describe a decision and say "stress-test this". Add "level 2" through "level 6" for a deeper pass. See `SKILL.md` for the full behavior. The Python helpers in `scripts/` need Python 3 and no third-party packages unless a script says otherwise. Commands in the reference files are written as `python3 <skill dir>/scripts/<name>.py`; on Windows use `py -3` in place of `python3`.
