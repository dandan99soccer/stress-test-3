# Paid-search pack, part two — the reading order, evidence with clocks, base rates, linked quantities, data rules, tools, open items

Read with `paid-search.md` (part one: sections 1–9). The section numbers continue part one's, so a cross-reference from either file names one place. Drafted 3 Nov 2026 and untested on a real decision; section 17 is where the first real run records what it changed.

## 10. The reading order

For one account or campaign, fixed, each step a retrieval agent returning verbatim figures with their as-of dates: 1) the change log — what was changed in the last 13 weeks and when (the system of record; the owner profile names where it lives); 2) the weekly series of the primary row and its drivers, 13 weeks, with the conversion window and attribution model noted; 3) the campaign's learning status and bid-strategy report; 4) the search-terms report (what the money actually bought); 5) the auction-insights report (who else is in the auction; whether competitors appear on the brand term); 6) the landing page as a user sees it and its conversion tracking as the tag sees it (a broken tag is the commonest "performance drop"); 7) the platform's recommendations, read last and as a seller's list.

## 11. The evidence-type checklist

| type | clock | role |
|---|---|---|
| weekly performance series | 7 days, lag-adjusted (section 15) | trigger |
| change-log entry | as of the change | explanatory |
| learning status | daily | never a trigger inside two weeks of a change |
| search-terms report | weekly | trigger (negatives, match types) |
| auction insights | weekly | direction only |
| conversion-tag health | daily | trigger (a broken tag voids the series) |
| platform recommendation or simulator | at read | never a trigger |
| industry benchmark | annual | direction only |
| lift or geo-test read-out | at read-out | trigger |
| seasonality (prior year, same weeks) | annual | explanatory |

## 12. The base-rate class library

Unit: the realized change in the primary row as a fraction of the trailing reference. Classes: a budget raise of 25% or more on a campaign at the conversion floor; a bid-strategy switch (manual to target; a target change); match-type broadening; a new campaign type; a brand-term pause; a landing-page change. **No class has a measured rate in this draft**: each is `estimated` until the account's own change record (section 10, step 1) supplies six cases, then ten (`level-5.md`, the named-case rule). The owner's change-record haircut is the realized-over-forecast ratio of the last ten changes, applied to every forecast; until it is measured it is `estimated` at 0.7, an inference from the general finding that forecasts of advertising changes run optimistic, not a measured figure.

## 13. Linked quantities

Nodes: budget → impressions (sign +, convex); impressions → clicks (click-through rate); clicks → conversions (conversion rate, falling with position depth); spend → cost per click (the auction's response, sign +); brand spend ↔ organic brand clicks (sign −, the cannibalization link); campaign A's budget ↔ campaign B's impressions where they share search terms (sign −). Sizes from the account's last two budget changes where they exist, graded; `propagate.py` runs the shock when the three-part test of `level-6-simulation.md` section 1 fires — a budget shift across campaigns that share an auction is the usual case.

## 14. Situation rows

Table 1, the object: account, campaign, bid strategy, budget, conversion definition and window, learning status. Table 2, the record: the 13-week series with changes marked. Table 3, the auction: competitors on the term, impression share lost to budget and to rank. Table 4, the clock: learning-end date, read date, seasonal events inside the horizon, platform changes announced. The actor map switches on when auction insights show a named competitor moving on the brand term.

## 15. Point-in-time and data rules

Conversions arrive late: a day's count keeps rising for the length of the conversion window, so a row resolves only after the window closes (a 4-week row reads on day 28 plus the window), and the reference's quantiles are widened by the account's measured lag. A replay reads the series as it stood on the decision date, never as restated. The attribution model and conversion window in force on each date are recorded beside every figure; a change in either is a break in the series. A lift test — a geographic holdout or a campaign-level experiment — is the only source that resolves incrementality; its read-out is dated and graded like any primary source.

## 16. Tools and routes

Read-only: the platform's reporting connector or export (a Google Ads reporting connector in cloud sessions where one is connected; CSV exports on the laptop; in chat, only what is uploaded). Scripts: `sensitivity_sweep.py` (break-evens of the marginal cost per click and conversion rate), `forecast_ledger.py`, `propagate.py` where section 13 applies. No pack-specific script yet: a fit of the marginal-cost curve from an account's budget-change history is the first candidate, written after the first real run says what it needs. Cloud and laptop can read the connector; chat reads only what is pasted.

## 17. Open items and sources

Open: a measured base rate for any class in section 12; the account's own cannibalization figure; whether the "no learning restart on target or budget changes" statement holds, from the primary source; the conversion floor measured on the account rather than taken from vendor guidance; the daily-budget pacing rule re-read from the help page. Sources for this draft, 3 Nov 2026, each with its provenance state as `packs/README.md` requires (verified passage, primary read, or secondary — primary not read): Google Ads help, "Learning and review periods" (answer 12563349) and "Duration of the learning period for campaigns and what affects it" (answer 13020501) — secondary, via search excerpts; ppc.land, "Google Ads PM says target or budget changes cause no learning period" (2026) — secondary; Blake, Nosko and Tadelis, "Consumer Heterogeneity and Paid Search Effectiveness: A Large-Scale Field Experiment", *Econometrica* 83(1), 2015 — secondary for this draft, the primary not re-read; 2026 benchmark compilations (WordStream/LocaliQ, Search Engine Journal, Visionary Marketing, Digital Applied, Searchlab) — secondary, via excerpts, mutually disagreeing; Coviello, Gneezy and Goette (Edmunds) and Simonov, Nosko and Rao on brand-term competition — secondary, via summaries. No source in this draft is a verified passage or a primary read; the first real run upgrades the ones its call rests on.
