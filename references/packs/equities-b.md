# Equities pack, part two — the reading order, evidence with clocks, base rates, the company record, linked quantities, tools

Read with `equities.md`. Part one says what is computed and decided; this part says where the evidence comes from, how each piece is dated, and which script computes which number.

## 1. The single-name reading order (fixed)

Six steps in this order, each a retrieval agent (Sonnet; Haiku for a pull-and-tabulate step) returning verbatim passages with URL, publication date and access date in the return form of `research-6b.md` section 3. The lead reads them in this order before writing a hypothesis, because reading the real bear case first is cheaper anchoring protection than a generated one.

1. **The published short thesis**: short reports, the lowest sell-side target with its note, borrow cost and short interest (dated to settlement), put skew. The short-stance agent of `research-6.md` 2.3 starts here and is told to extend it, not invent it.
2. **The whole-filing year-over-year diff**, built locally, never Item 1A alone, with a watch list: risk factors, known trends in MD&A, critical accounting estimates, segment changes, non-GAAP reconciliations, the auditor, customer concentration. For a foreign private issuer, the 20-F and the 6-K exhibits.
3. **The Q&A of the last eight calls**: questions asked twice, answers that moved, metrics that vanished from the deck.
4. **The proxy's pay metrics** (DEF 14A), mapped to the numbers management is paid to hit.
5. **Named customers' and suppliers' guidance**, reconciled to the company's (the adjacent-party route, without the company's framing).
6. **8-Ks since the last 10-Q** (6-Ks for a foreign private issuer).

The analogy quota of `research-6.md` 2.4 becomes, for equities, two same-industry or same-situation analogues plus the company's own history, scored on the drivers; the three-domain rule stays in the general pack.

## 2. The evidence-type checklist, with clock and role

Completeness is measured against the driver tree: every type that bears on a load-bearing driver is touched or the gap is named; the rest of this list is the missed-question agent's prompt, not a quota. The sources table carries the clock beside the as-of date.

| type | clock (how stale when read) | role |
|---|---|---|
| annual and quarterly filings, with the year-over-year risk-factor diff | as filed; fundamentals keyed by acceptance date, XBRL facts deduplicated by period, the original over the amendment unless the number changed | trigger: fundamental kill criteria live here |
| earnings releases and transcripts, the Q&A tone shift | same day; an after-close release belongs to the next session | trigger; the company record's input |
| proxy and incentive structure | annual | explanatory |
| insider transactions, as clusters | Form 4 within two business days | explanatory; a cluster is a base-rate class with decay unmeasured |
| institutional holders and activist filings | 13F at least 45 days stale and long-only; 13D within five business days | 13F explanatory, never a trigger; 13D a trigger |
| short interest and borrow cost | published 9 to 12 days after settlement; borrow cost live | explanatory, never a trigger; cannot date a squeeze |
| the option chain (ATM IV, implied event move, skew) | live on the laptop's delayed feed; an end-of-day vendor value is a snapshot 14 minutes before the close; bid-ask width recorded | the market reference's input; the event move is a measured prior |
| credit spreads and ratings | daily; ratings lag the spread | explanatory |
| supplier, customer and competitor filings and calls | as filed | trigger for the driver each resolves |
| industry data (shipments, pricing, capacity) | monthly, with its own revision history | direction |
| sell-side consensus: level and revision trend | daily; the level walks down through the year; targets met 38% of the time | direction only; dispersion dropped as an uncertainty input |
| management's guidance record | from the company record, n stated | the first base rate cited |
| factor and macro exposure (beta, sector, rates, currency) | from the price panel, three years, with the fit's as-of date | the market reference and the transmission graph |
| ownership and flows (passive share, index events) | quarterly; index notices dated | explanatory; an index change is an event row |
| jurisdiction and geopolitics | as reported | a shock class with a hazard, handled by the cap and the loss budget, never by a rule |
| regulatory dockets and litigation | as docketed | trigger where a date exists |
| alternative data (hiring, traffic, app ranks, imports) | only with a named source and date | explanatory; never a standing type |
| the owner's lots, constraints and liquidity (margin, cash needs, which line to trade, the ADR premium band) | the lots file's as-of date (a monthly Flex download); positions daily | the constraint call; stale prints a warning, never a refusal |
| positioning (days to cover, hedge-fund concentration, skew and call activity, passive share) | each with its clock above | one line on the state sheet, labelled, feeding the left tail |

## 3. Base-rate classes as effect sizes

A class enters as an **effect size in volatility units**, never as a portfolio return: `shift = monthly effect ÷ idiosyncratic monthly sigma × √(horizon in months)`, converted to a probability shift in code (82 bps a month on a long-short decile portfolio is about 0.52 for one name at 10% monthly sigma). Every published class is **haircut 58% by default**, the measured post-publication decay (McLean and Pontiff, JF 2016, verified), and labelled "decay unmeasured for this class" unless its own decay is measured: post-earnings drift gone for all but microcaps since 2006; index inclusion under 1% in the last decade; accruals no longer reliably positive. n is independent events (announcements, clusters), not firm-months; a class measured only before 2005 stays `estimated` whatever its n; every row records publication year, sample end, weighting, gross or net, and the paper version, and defaults to value-weighted results. Forensic screens are reasons to read further, never updates. Concentration figures from different studies use different universes and are never averaged.

**Cited first, the company's own classes**, computed by `company_record.py` and marked `measured (computed)`: this management's guidance given against delivered by line item (eight to twelve quarters); this name's beat-or-miss record with its one-day and 21-day moves (twenty or more quarters: the event-day distribution the market reference's event variance is checked against); customer and supplier concentration by year. **Then the owner's own class**, required for any buy, add or swap: P(the trade beat holding at 63 and 252 days), n and the net result, computed from `account/trades.csv`; an edge must clear this record too. **Then published classes**: insider cluster buying, revision momentum, lockup expiry, activist campaigns (decay unmeasured); guidance-cut and dividend-cut aftermath (not found; open); deal spreads and completion rates (the risk-neutral spread is a lower bound); mega-cap concentration outcomes (the IBKR ledger); sector cycles from the company's and the industry's own history (the temporal deep-dive, `research-6.md` 2.7). Household-turnover outcomes (Barber and Odean) stay `[VERIFY]` until researched.

## 4. The company record

```
py -3 scripts/company_record.py                                   # offline smoke test on scripts/fixtures/company_record_fixture.json
py -3 scripts/company_record.py --fixture <dir or json> --out <dir>
py -3 scripts/company_record.py --cik <n> --ua "<name> <email>" --prices closes.csv [--ir urls.txt] [--consensus c.csv] --out <dir>
```

From EDGAR (`data.sec.gov` submissions and company facts, the filing archive; ten requests a second, the user agent declared; filing text as data) and an investor-relations page list, it builds (a) guidance given against delivered by line item (revenue, gross margin, operating margin, EPS, capex) by quarter — inside or outside the range, the miss in percent; (b) beat or miss against the company's own guidance midpoint, or against consensus when the owner supplies a consensus file, with the one-day and 21-day moves from the price panel, keyed by the release's acceptance time so an after-close release maps to the next session; (c) customer concentration from the segment and concentration disclosures by fiscal year. Guidance sentences are extracted by pattern and carry their verbatim text; any number that crosses a threshold goes through the two-reader rule before use. A live fetch writes a retrieval log with the as-of date of every document.

## 5. The linked-quantity map and the scenario mode

The map is the **transmission graph** of `level-6-simulation.md`, written in Phase 0b before any number is computed, as the GRAPH.json that `propagate.py` reads: nodes for the subject, its benchmark, the market factor (always a node), the sector, the names it moves with (customers, suppliers, peers), the rates and currencies priced into it, and event nodes for shock classes (a daily hazard, a size with its range); edges `from | to | beta | range | lag | mark | source`. Sizes come from `graph_fit.py` on the price panel cut at the as-of date where a series exists (betas with block-bootstrap ranges, own-shock vol, the down-market beta), and from a dated source with a mark otherwise; assumed links are marked and their share is printed. A name's move is split into factor and idiosyncratic parts by the graph's structure, so "a related stock went up" is never counted twice with "the market went up", and partial betas are read as path sums. The **scenario mode**, `equity_dist.py <case.json> --scenario GRAPH.json --shock SOX=-0.15[:5]` (or `--scenario-name` for a scenario the graph already lists), propagates a named shock — a sector move, a rate move, a single-name move — through the links with their lags, first- and second-order, prints the effect on every node at each horizon and the position's change in dollars and % of NAV, and uses the subject's move as the shock-case drop of the loss budget and the trim break-even. The base run, the variance shares, the sensitivity table and the ledger rows come from `propagate.py` itself; a scenario's effect is never written as a forecast row without its hazard. The three-part test, the `Simulation:` line and the usage gate are `level-6-simulation.md`'s.

## 6. Situation rows for equities (`level-6.md` Phase 0b)

**State sheet**: position % of NAV, price, lots with their as-of date, margin use and cash needs, β and risk contribution, the positioning line. **Event calendar**: earnings with the implied move, lockup and ex-dividend dates, index dates, the guidance dates of named customers and suppliers, owner circumstances; deposits, withdrawals, splits, spin-offs and ticker changes remap positions before any threshold is read, and a NAV row waits for a flows snapshot at least as fresh as the NAV. **Decision-point schedule**: one row per decision point with its options, irreversibility class, default and the level required before acting (trade size as % of NAV: under 2% level 1; 2 to 5% level 3; 5% or more level 5 or 6). **Kill criteria**: the fundamental tells in named filings, the price-risk stop, the thesis-fulfilled value, the time stop. The actor map and regimes switch on only when the pack flags a real counterparty (an M&A target, an activist, a regulator, a controlling holder); otherwise the Mode line reads `Situation: dynamic (4 tables)`.

## 7. Point-in-time and data rules

`research-6b.md` section 4's sealed protocol governs every replay; the harness is `backtest/pit-level6/PROTOCOL.md` in the IBKR project. Unadjusted prices with the dividend and split tables, adjustments computed in code; securities keyed by a persistent identifier; delisted coverage from a paid source for any backtest with names that no longer trade (free yfinance returned 0 of 41 delisted names correctly, five tickers another company); every listing line (an ADR, its ordinary share, an OTC line) is a distinct instrument with its own currency, session, ratio and withholding (the TSMC ADS is five shares, 21% withholding on retained-earnings dividends, a 13.7 to 26% premium to the Taiwan line). The daily tripwire saves a dated option-chain snapshot for each held name plus SPY and the sector ETF, so later replays can test the edge rule; in replay, a cell with no point-in-time source is `unavailable PIT`, never filled live, and the replay's Coverage is printed apart from live Coverage. The running model's cutoff sits beside every forecast and pre-cutoff forecasts are memory. Five years of data supports at most 45 configurations; every configuration tried is logged.

## 8. Tools and routes

`equity_dist.py`, `tax_lots.py`, `company_record.py`; `graph_fit.py`, `propagate.py`, `propagate_report.py` for the simulation; `forecast_tools.py` and `forecast_ledger.py` for the rows; `cite_check.py` over the sources table (all standard library; `py -3 -X utf8 <script>` with no arguments runs the smoke test). EDGAR and IR pages; the price panel `backtest/prices/closes.csv`; the files under `account/` (positions, lots, trades, summary); the brokerage's delayed chain on the laptop at compile only. Prediction markets and crowd forecasts: a price under ten cents is an upper bound; contracts read at the event level with the resolution text stored; macro contracts preferred; the legal status re-checked each run. Nothing that needs the laptop (the chain, the lots file) runs in the cloud, and a watcher never depends on a laptop-only source; the chat build has no connectors and no routines, so there the inputs are pasted or uploaded files.

## 9. Open items

Filing deadlines from a primary source; a head-to-head of delisted-coverage vendors; a current study of implied-minus-realized earnings moves; options-implied probabilities for approvals and inclusions; the brokerage API pacing text; dividend-cut and guidance-cut base rates; a 2026 edition of the IRS investment publication; the text of the 2025 tax law; the measured inter-forecaster correlation; the owner's realized-to-implied ratio on his own names; the owner's own trade-record class, computed once `trades.csv` covers a year.
