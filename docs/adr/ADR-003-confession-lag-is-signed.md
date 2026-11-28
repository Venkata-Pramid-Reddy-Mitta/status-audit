# ADR-003: Confession lag is signed and scored on the first episode

Status: accepted

## Context

A single week's reconciliation answers "is this color honest". The question a sponsor pays
for is temporal: once the signals turned, how long did the report stay green. That is the
confession lag, and it needs the whole time series for a program, not one week.

## Decision

Confession lag is the gap from the first objectively non-green week to the first reported
non-green week, and it is **signed**: a report that turns at or before the signals has a lag of
zero, never a negative one folded back to positive. The lag is measured on the first
deterioration episode per program.

## The bug this prevents (war story)

The first implementation computed `abs(reported_onset - objective_onset)`. On the seeded
portfolio that handed the worst score to the most honest program. PRG-DELTA is a sandbagger:
its signals stay green until late in the horizon while it reports amber from week one out of
caution. The absolute-value version read the distance between those two onsets and reported a
phantom lag of 18 weeks for DELTA, ranking the single most conservative program as the worst
watermelon in the portfolio. The sign was the entire finding, and the absolute value threw it
away.

The fix is the signed rule above, pinned by
`test_confession_lag_is_zero_when_the_report_leads_the_signals`. With it, the longest real
confession lag in the portfolio is a 4-week lag and exactly 1 program never confessed at all,
which are the numbers the README leads with.

## Alternatives considered

- **Score every episode, not just the first.** Deferred. A program that recovers and relapses
  has a second episode this rule does not score. That is the Pivot in the README, with its
  trigger stated there. First-episode was chosen because it is unambiguous and because the
  recurring case does not occur in the seeded data, so building the machinery now would be
  untested weight.
- **Require a sustained run before counting an onset.** Deferred for the same reason: a
  one-week blip counts as an onset today, which is a stated boundary rather than a hidden one.

## Consequences

The lag is directional and robust to a conservative reporter. The known boundary (transient
blips, recurring episodes) is documented in the README's "What this cannot measure" section
rather than hidden.
