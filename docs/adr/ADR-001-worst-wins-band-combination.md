# ADR-001: Combine signal bands by worst-wins, not by a weighted average

Status: accepted

## Context

The engine recomputes a RAG from five signals: schedule (SPI), cost (CPI), open critical
issues, overdue milestones, and open high risks. Each signal maps to its own band (green,
amber or red). The question is how to combine five bands into one colour.

## Decision

The combined colour is the worst band any single signal reaches. A program that is on budget,
on scope and badly behind schedule is Red, not an average of one red and four greens.

## Alternatives considered

- **Weighted average of the band severities.** Rejected. Averaging lets a healthy dimension
  dilute an emergency: four green signals and one red SPI would average to amber, which is
  exactly the optimism this tool exists to detect. The whole product would then launder the
  same dilution it is meant to catch.
- **Points-based scoring with a red threshold.** Rejected as a dressed-up average with more
  knobs. Worst-wins has one rule and no tuning surface, which is easier to defend in a status
  meeting.

## Consequences

The verdict is conservative by construction and the reasons list leads with the band that set
the colour. A reviewer who disagrees argues about a single threshold in `policy.toml`, not
about a weighting scheme. Cost and risk are deliberately capped at amber (see ADR-002), so
worst-wins can still never be driven to red by cost alone.
