# Level 1 and the profiles every level uses

Read this, with `reasoning.md`, for any pass above the stakes floor. Level 1 runs these steps at its own depth; levels 2–5 use the same profiles and numbered steps and do not run level 1 first.

## Pick a profile

Name it in one line at the top so it can be corrected. Two lenses are **always** included:

- **Cost to operate** — what it costs *per use*, every time, forever. Not the cost to build. Put a number on it; when the cost is labor, the number is minutes per use and whose. Mark each number measured (from data you saw), estimated (from priors) or inferred (follows from measured facts by a chain you can show — see `reasoning.md`) — an estimate or an inference is a claim to check, not a fact.
- **Rework & reversibility** — what forces a v2, what backing out costs, what you are locked into.

Then add the profile's lenses. The profiles below are starting points, not a boundary: a decision in any field gets lenses chosen for what could go wrong in that kind of decision.

**Automation & internal tooling** — a script, agent, queue, or workflow that runs on its own.
- *Blast radius*: what one wrong action costs when nobody is watching. Cap, undo, approval gate?
- *Silent failure*: how you find out it stopped working. Quietly doing nothing is the common killer, not crashing.
- *Maintenance owner*: who fixes it, and what happens the week that person is unavailable.
- *Autonomy threshold*: which actions it may take alone, which must wait for a human.

**Tool or vendor adoption** — buying, subscribing, standardizing on something external.
- *Exit path*: getting your data out, and what breaks when you leave.
- *True cost at your volume*: not list price — your real usage at the scale you will reach.
- *Integration surface*: what else must change to accommodate it.
- *Vendor viability*: changed terms, acquisition, shutdown.

**Projects & sequencing** — choosing among projects, or what to start next.
- *Opportunity cost*: name the specific thing that will not get done.
- *Concurrency*: how many efforts can genuinely be in flight given who is actually doing the work.
- *Finishing risk*: what is already half-built. Starting something new while three things sit at 80% is usually wrong.
- *Dependency order*: what must exist first for this to pay off.

**Go-to-market & messaging** — campaigns, positioning, copy, outreach.
- *Claim substantiation*: flag anything implying a certification, compliance posture, or customer figure that is not documented.
- *Audience reality*: who actually reads this and what they already believe.
- *Competitive response*: what a competitor does in reply, and whether you still win after that.
- *Measurability*: how you will know it worked, given the data you actually have.

**Sales & deals** — pricing, discounts, terms, renewals, partner or reseller arrangements, which deal to work.
- *Price precedent*: what this price teaches this buyer at renewal, and every other buyer who hears about it. A discount given once is the starting point next time.
- *Velocity vs. margin*: what closing faster is worth, priced as the concession it costs. "This quarter at 30% off" and "next quarter at list" are different bets; say which and why.
- *Path to signature*: who actually signs, and the procurement, legal or PO steps between here and there. A champion who cannot sign is a forecast risk, not a close date.
- *Renewal & expansion*: how the terms shape the next renewal and the growth after it — multi-year lock-in, true-up terms, channel conflict with partners.

Rules check for this profile: discount authority, the price list and quoting procedure, partner and reseller terms, any approval or procurement rules the buyer is bound by. Read the actual price sheet or contract, not the recollection of it.

**Process & policy** — anything that changes what people must do.
- *Adoption*: who has to change behavior, and what is in it for them.
- *Enforcement*: what happens when someone ignores it. If nothing happens, it is a suggestion.
- *Exceptions*: the cases that will not fit, and who decides.
- *Reversal cost*: walking a policy back is socially expensive even when technically easy.

**Anything else** — choose three lenses that fit, and say why those three. When a decision straddles two profiles, borrow one lens from the second and say why.

## Level 1 (default, one turn, no subagents)

Under roughly 600 words, at one of two depths. Moderate stakes — reversible within a week, under a day of work, no one else's approval needed — run steps 1, 2, 7 and 8 only, about 150 words. Everything else runs all nine.

**1. Restate the real decision.** One sentence, built on the premise as checked in Step 0, not as remembered. If the stated question is not the actual one, say so — this is often where the value is. Name any constraint the person stated — budget, deadline, risk appetite — or the assumption you are making in its absence.

**2. Put the options on the table.** This step is the spine of the skill. Produce **two or three genuinely different shapes**, including the one proposed. Different in kind, not in degree: variations on one plan are one option wearing hats.

Generate more shapes than you will keep, up to one pass through the list below — about ten shapes at most, the generation ceiling every level uses. The list is a generator, not a quota: do it much smaller; do it later, after a specific fact is known; buy or rent it instead of building; remove the need rather than meeting it; solve the adjacent problem that makes this one disappear; do nothing and accept the current cost; run a small test before committing — a pilot, a trial period, a try-measure-stop-measure run — when the case for the plan is inferred rather than measured; sequence two shapes (one now, the other once a named fact is known); a hybrid that takes the one thing each of two shapes is better at. Then screen: drop what breaks a hard constraint, what is dominated on every lens by another shape, and what shares another shape's premise (merge those). Keep the two or three that survive and differ in kind; name the dropped ones in a single line, each with its reason, so one can be revived if a lens later disagrees. Decisions that fail usually failed at this step — one option, defended, is the common shape of a failed decision — and the winner is often a hybrid that only appears once several shapes are on the table together.

Give each option one line: what it is, and the one thing it is better at. If after real effort there is only one viable option, say so explicitly and say why the others fail — do not invent filler alternatives to fill the shape.

**3. Challenge the framing.** What has to be true for any of this to be worth doing? Name the assumption the whole question rests on. If that assumption is shaky, the comparison below matters less than testing it. The best version of this step names an assumption that is cheap to check — a contract clause, a report, a count — and makes that check the first step. Mark the assumption measured, estimated or inferred; an inferred one gets its chain and weakest link written out, because that link is usually the cheap check.

**4. Compare through the lenses.** Run the profile's lenses **across the options**, not down the proposal. The point is where they diverge: an option that is cheap to operate and expensive to reverse is a different bet from the opposite. Keep it to a line or two per lens. Skip any lens that genuinely does not apply and say which. Where lenses disagree, resolve it by reasoning, not averaging — a split usually points at a shape not yet on the table.

**5. Risks of the front-runner.** Only risks that would change the choice — what breaks, how likely, how bad. Drop the rest; an unranked list of objections is noise. The weakest inferred link in the case for the front-runner is always one of them: say what happens to the choice if that link fails.

**6. Check it against the rules.** Before recommending anything, name the constraints that actually govern this system — approval tiers, protected terms, spend caps, brand or legal limits, the project's own written procedure — and check each recommendation against them. Read the governing document rather than recalling it.

A recommendation that breaks a rule is not a queued action. Say which rule it breaks and hand it back as a decision for the user. Do not route around a constraint, and do not describe an action as automatic or low-tier without confirming which tier it actually falls under. If no written rules govern this, say so in one line and move on. If the governing document cannot be read, the rules check is an open item, not a pass: say what you could not read and what depends on it.

**7. The call.** Either a recommendation with a concrete first step, or **"decide nothing yet"** plus the specific fact to go find — or the specific inference to test, and how. The second is a legitimate outcome — do not manufacture a verdict when the decision turns on something unknown and cheap to learn. A recommendation may rest on inference alone when it is marked and reversibility allows it (see `reasoning.md`); when it does, say so in the call.

Name the decision owner when it is not the user: then the output is a proposal to that person, the first step is that conversation, and the recommendation still says what you would have the owner do. An owner line is not a license to punt.

**8. Two lines that always appear.**
- **Success looks like:** an observable condition, with a number and a date where possible. A date that depends on someone else acting is a wish — write it as the trigger ("after the product owner answers the licensing question") or name the date that person committed to. Say who checks it and on what date. If you cannot state a condition at all, say so — that is itself a finding.
- **Abandon this if:** the condition under which stopping is correct.

**9. Trade-offs.** What the chosen path gives up, including what the runner-up would have given you.

## Failures the steps do not already catch

**Sound but not allowed** is the worse failure, because it is the part that gets acted on. Step 6 exists for it; do not let it be the step that gets skipped.

**One option in disguise.** Three plans that differ only in scope or timing are one plan. If every option shares the same premise, the premise is what needs testing — go back to step 3.

**Build cost is not operating cost.** Something cheap to build and expensive to run every day is the worse outcome, and the harder one to see, because the bill arrives later.

**Version churn is a design smell, not progress.** If the plan is likely to reach v3 by way of v2, the requirements were never settled. Name the decision being deferred and what it would take to settle it now, while it is still cheap.
