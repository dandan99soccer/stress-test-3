# stress-test-3

A Claude skill that pressure-tests a decision: it generates genuinely different options, screens them, and compares the survivors through lenses chosen for the kind of decision. Level 1 is a cheap single-turn pass and the default; levels 2 to 6 go deeper (research, replication, forecasting) and run only when asked for by name.

## Install

**Claude Code**

```bash
git clone https://github.com/dandan99soccer/stress-test-3 ~/.claude/skills/stress-test-3
```

The folder name is free: claude.ai may list the skill as `stress-test-31` or another name, and nothing in the files depends on it. Commands in the reference files write the skill's folder as `<skill dir>`.

**Claude.ai / Claude desktop:** download this repo as a ZIP and upload it under Settings → Capabilities → Skills.

**Installing for someone else:** delete `references/owner-profile.md` or replace its contents. It holds one owner's standing rules, measured cost table, file locations and pack defaults; every other file runs without it.

## Use

Describe a decision and say "stress-test this". Add "level 2" through "level 6" for a deeper pass. See `SKILL.md` for the full behavior; `references/triggers.md` holds the gates and the offer wording for levels 3–6. The Python helpers in `scripts/` need Python 3 and no third-party packages unless a script says otherwise. Commands in the reference files are written as `python3 <skill dir>/scripts/<name>.py`; on Windows use `py -3` in place of `python3`. Every script runs its own offline smoke test when called with no arguments.

## What is in the repo

- `SKILL.md` — Step 0, the levels and their triggers, the intake, budget mode, which files each level reads, the fixed output lines, grounding, and the filing offer.
- `references/` — one procedure file per level (`level-1.md` … `level-6.md`, with `-b` parts where a level spans two files), `triggers.md`, `intake.md`, `reasoning.md`, `research.md` and `research-6.md`/`research-6b.md`, `forecast.md`, `level-6-simulation.md`, `budget.md` (included-usage mode, checkpoint and resume), `owner-profile.md` (optional, one owner's rules), and `packs/` (the level 6 domain packs: `equities`, built 18 Oct 2026; `paid-search`, drafted 3 Nov 2026 and untested until its first real run).
- `scripts/` — standard-library Python: `sensitivity_sweep.py`, `forecast_ledger.py` and `forecast_tools.py`, `cite_check.py`, `graph_fit.py`, `propagate.py` and `propagate_report.py`, the equities scripts (`equity_dist.py`, `tax_lots.py`, `company_record.py`, `edgar.py`, `xbrl_quarters.py`, `student_t.py`), and `eval_tally.py`.
- `evals/` — the eval set: past decisions with known outcomes, a sealed brief and key per decision, one results row per run, and the tally that compares levels on them (`evals/README.md`). Empty of decisions until the owner adds them.

## The ledger, the review date and the eval set

Levels 4–6 write their probabilities as rows of a `FORECASTS.csv` and append them to a shared ledger that scores them later (`references/forecast.md` sections 8–13). The ledger must outlive the session: the script resolves its folder from `--to`, then the `STRESS_TEST_LEDGER` environment variable, then a `ledger/` folder in the working repository (which a cloud session commits and pushes), then the laptop's `~/.claude/sessions/stress-test-forecasts/`; `python3 scripts/forecast_ledger.py --where` prints the one in use. In claude.ai chat the ledger is a connected spreadsheet with the same columns, or the rows go in the reply to paste.

A packet's review date is offered as a one-time scheduled task on that date that asks for the outcome, resolves and scores the rows and fills the decision record's Outcome section (`forecast.md` section 13). It is scheduled only when the owner says yes; without it no forecast is ever scored.

The eval set is how a level earns its cost: run each level on decisions whose outcome is known, score the call against the key, and read the paired comparison from `python3 scripts/eval_tally.py evals/results.csv`.
