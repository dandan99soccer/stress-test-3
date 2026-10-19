# Forecasts — the rules every scorable number follows, and the ledger that scores them

Read this with the level 4 and level 5 files whenever a pass writes a probability, a range or a quantile: the packet's success probability, the load-bearing assumptions, a robustness table's futures, a named-case base rate. Levels 4 and 5 write these numbers today; this file says what each must carry so it can be scored, how numbers are updated and aggregated, the guardrails, and the ledger they go into. Level 6 builds its forecasting phases on the same rules. The math is in `scripts/forecast_tools.py` and the ledger commands in `scripts/forecast_ledger.py` (standard library only; each runs its smoke test with no arguments).

## 1. Three kinds of forecast

- **Event**: a yes-or-no question with a date; the number is P(the event as worded). For a name against a benchmark the convention is P(name beats the benchmark over the horizon), the same as the IBKR scorecard, so the records can merge.
- **Quantity**: a number with a date, given as five quantiles, 5 / 25 / 50 / 75 / 95, monotone. Scored by the mean pinball loss over the five levels, an approximation of CRPS.
- **Ranking**: which of several named items does best by a date; written as one event row per item (P(item is best)), sharing a group so the rows sum to one.

## 2. What every forecast carries

A forecast with any of these missing is not written: the **question** as worded; a **resolution criterion** an outsider could apply; the **resolution source** (the file, feed, filing or person that settles it); the **resolve date**; the number (p, or the five quantiles); a **range** (low and high) meaning the forecaster's own uncertainty about the number, so 0.55 (0.50–0.60) and 0.55 (0.30–0.80) are different claims; the **forecaster** (lead, owner, market, a method forecaster, or aggregate) and the **method**; the **base rate** it started from, with the named class and its n (n under 30 stays `estimated`); the **model cutoff** of the model that produced it, because a pre-cutoff "forecast" is memory, not inference; and one line each on why it might be **too high** and **too low**, kept in the notes column. "Decide nothing yet" still forecasts.

## 3. Decomposition and priors

A headline probability is built from a tree of sub-questions, each leaf with a reference-class base rate (named class, n, a Wilson interval), recombined with the independence assumptions written down; where two leaves share a cause, the recombination says so rather than multiplying. Priors are **pre-registered** from base rates before the research or the model moves them, and so is the option set: every target that a rule in force or a proposed rule names is a pre-registered option, whether or not the lead favors it (the first point-in-time run, 18 Oct 2026, missed the policy's own 20% target because only two caps were enumerated, and the blind replication had to supply it). The packet's **update audit** shows prior → posterior for the three numbers that moved most and the graded finding behind each. A move with no graded finding behind it is an anchor shift and is refused. Every forecaster, a blind replication included, starts from the same pre-registered base-rate table; a forecaster that starts from one half is a dispersion check, not a replication of the forecast (in that run the even-prior replication cost the aggregate 0.04 Brier against the lead on every row).

## 4. Updating

The inside view moves a prior only through a graded finding with a stated likelihood ratio, applied in log-odds by code (`lr_update`), never by hand. Caps: a per-item cap of ln 3 unless the item's ratio is backed by named cases, in which case it uses its own ratio; a per-question cap of ln 4 per reading interval. These two constants are provisional and are to be set from a replay of the project's own record. Hard stops, kill observables and resolutions bypass the caps. Posteriors are recomputed from the prior and the full list of applied ratios, so an update can be voided and replayed.

## 5. Aggregation and dispersion

When several forecasters answer one question (the blind replications, the method forecasters of level 6, the market, the owner): binaries aggregate by the **median**, or by the trimmed mean of log-odds; quantities by averaging each quantile level. Only forecasters that received the same information set are aggregated into the primary number; a forecaster given less (a replication without the research returns) is printed as a dispersion line beside the lead's posterior, which stays primary. **Extremizing** (pushing the aggregate away from one half in log-odds) is reported as an alternative figure and never applied silently; it is defensible only when the forecasters used independent methods and information, and an all-Claude set is less independent than it looks because same-family models share errors. **Dispersion**, the inter-quartile spread of the forecasters in log-odds, is printed beside the aggregate; wide dispersion caps the stated confidence and names the crux. One round of exchange between forecasters is allowed only when the set is diverse; copies of one model gain nothing from debate and are not asked to.

## 6. Guardrails

- No probability under 0.05 or over 0.95 without a named-case base rate behind it.
- Rows in one group (the leaves of an outcome space, the items of a ranking) sum to one within 0.01; conditionals are consistent with their marginals; quantiles are monotone. `forecast_ledger.py --check` enforces these.
- A quantity's quantiles are moved by a parametric fit (a scaled-t or lognormal on the market's implied band), never by linear interpolation between the five levels, which produced a coherence artifact in the first point-in-time run; quantiles narrower than the market reference's band need a graded reason, and the realized 63-day excess of that run (17.4%) fell outside a median of 4.6% whose band had no such reason.
- Every number is dated and carries its range; an edge over a market or crowd forecast (section 7) is claimed only with a graded reason.
- Model forecasters lean toward "yes" and sit too close to one half; the calibration record (section 8) measures both biases and the pass corrects against them, saying so.
- A forecast is never resolved from memory or narrative: the named source settles it, or the row stays open and is counted as open. An ambiguous resolution takes the stricter reading against the forecaster and is flagged for the owner. A question whose source is gone is `void`, never a miss.
- A move is never scored by its outcome; the forecast and the process are scored separately.

## 7. The edge statement

Where a market or crowd forecast exists for the question (an options-implied distribution, a deal spread, a prediction-market price, a consensus with dispersion, a professional survey), it enters as a forecaster with weight, and the packet carries an `Edge:` line: what the pass claims to know that the market does not, each claim graded and traced. The posterior departs from the market's number only in proportion to the graded edge; no graded edge means the market's distribution is adopted and the decision rests on the owner's constraints alone. Market numbers are read with their known biases: a risk-neutral probability of a good-state event is a lower bound on the objective one; a prediction-market price under ten cents is an upper bound; related contracts are read at the event level; the resolution text is stored with the price.

## 8. The calibration record

Every pass that writes forecasts appends them to the shared record, and the record is what makes the next pass better than this one. Monthly, and at every review date, `forecast_ledger.py --calibrate` regenerates `CALIBRATION.md` from the shared ledger: resolved n, mean Brier against climatology (0.25), the skill score with an 80% interval from a bootstrap clustered by independent cluster (a decision date by underlying by non-overlapping horizon; rows that share one cause, such as every name in one sector rally after one date, count as one outcome, so twenty rows on one date are one cluster), the calibration table by bin with Wilson 90% intervals, the yes-lean (mean forecast minus mean outcome), and the same by forecaster and by question kind. A new pass opens by reading it and writes a `Calibration:` line in its packet: resolved n, Brier, and the bias in words ("the 60–70 bin resolves at 52% on n=31"). Priors are shrunk toward the measured bias only in a cell with n of 30 or more; otherwise toward the pooled bias, with a note. No calibration test fires below its minimum n: fifteen resolutions from at least two independent questions for a skill test, eight in a bin for a bin test; below that the line reads `n/a`.

## 9. The ledger

Each pass writes `FORECASTS.csv` beside its decision record, one row per forecast, columns in this order: `id, decision, made, kind, question, criterion, source, resolve_date, p, q05, q25, q50, q75, q95, range_low, range_high, forecaster, method, base_rate, base_class, base_n, group, node, cluster, ref_value, model_cutoff, status, outcome, score, score_kind, resolved_on, notes`. `status` is `open`, `resolved` or `void`; `group` names a set of mutually exclusive rows; `node` is the line node id when level 6 lines exist, else blank; `cluster` is the independence cluster (date, underlying, non-overlapping horizon); `ref_value` is the market or crowd reference for the question at the time made, when one exists, so skill can be scored against it as well as against climatology. The shared record is `~/.claude/sessions/stress-test-forecasts/LEDGER.csv`, the same columns with `run` and `project` in front, appended with `--append` (duplicates by run and id are skipped), and `CALIBRATION.md` beside it. The IBKR committee's `scores.csv` uses the same probability convention and can be merged by a project step. Resolution writes `outcome` (1 or 0 for an event; the realized value for a quantity), `resolved_on` and the score (`--score`), and nothing else is edited after the fact: a correction is a new row that cites the old id in its notes.

## 10. Commands

```
py -3 scripts/forecast_tools.py                                   # smoke test of the math
py -3 scripts/forecast_ledger.py                                  # smoke test of the ledger
py -3 scripts/forecast_ledger.py --init  <dir>                    # create LEDGER.csv and CALIBRATION.md in the shared folder
py -3 scripts/forecast_ledger.py --check <FORECASTS.csv>          # required fields, ranges, groups, quantiles, extremes
py -3 scripts/forecast_ledger.py --score <FORECASTS.csv>          # fill score and score_kind where outcome is present
py -3 scripts/forecast_ledger.py --append <FORECASTS.csv> --to <LEDGER.csv> --run <id> --project <name>
py -3 scripts/forecast_ledger.py --calibrate <LEDGER.csv> --out <CALIBRATION.md>
```

## 11. How levels 4 and 5 use this today

Level 4's packet probabilities (success by its date; each load-bearing assumption) and level 5's ranged probabilities, named-case base rates and the robustness table's futures (when the pass puts numbers on them) are written as rows, checked, and appended to the shared record before the packet is delivered. The decision record's review date is the first resolve date; at the review the rows are resolved from their named sources, scored, and the Outcome section is filled from the ledger, not from memory. The `Calibration:` line appears in level 4 and 5 packets once the record holds fifteen resolved rows; before that it reads `Calibration: n/a (n=<count>)`. The owner's own numbers, when he gives them, are rows with forecaster `owner`, elicited before Claude's number is shown. **Constraints first.** When an owner default or a rule in force fixes the direction of the call (a concentration cap, a tax-lot rule, a drawdown-first criterion), the packet's first line after the call says "direction fixed by constraints; the forecasts bear on size and timing", and the forecasts are still written and scored; the first point-in-time run was decided by a default and a cap while its forecasts, which leaned the right way, decided nothing, and a packet that does not say so misreads its own result.

## 12. Rows from a simulation

`scripts/propagate.py --rows` (`references/level-6-simulation.md`) writes a transmission graph's base run as rows: forecaster `model`, method `simulation propagate.py <graph hash>`, the panel's own base rate with its independent n in `base_rate`, `base_class` and `base_n` (`estimated` in the notes under thirty), the range as the spread of the number across the sensitivity variants, and the cluster by date, subject and horizon. They are forecasts like any other: they go through `--check`, the market comparison of section 7 (a simulation never outranks a market distribution without a graded edge) and the calibration record; the lead writes the too-high and too-low lines first; and a scenario's effect is never written as a row without the hazard that would make it a probability.
