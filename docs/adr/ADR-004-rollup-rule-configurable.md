# ADR-004: Objective rollup is always worst-of; the integrity rule is configurable

Status: accepted

## Context

There are two different roll-ups in this tool, and conflating them would be a real bug.

1. **The objective program color**: given the computed colors of a program's workstreams,
   what color are the signals saying the program is.
2. **The rollup integrity check**: given the colors a program's workstreams *reported* for
   themselves, is the program's *reported* color even internally consistent.

## Decision

The objective program color is always the worst of its workstreams' computed colors, with no
configuration. "What do the signals say this program is" has one honest answer: as red as its
reddest part.

The rollup integrity rule is configurable (`rollup.rule`), defaulting to `worst_of`, with
`majority` offered as the weaker rule a reporter might lean on.

## Alternatives considered

- **One configurable rule for both.** Rejected. Making the objective color configurable would
  let a lenient rule hide a red workstream from the signal reconciliation, which is the exact
  evasion the tool is built to expose. The objective answer must not have a lever.
- **Only ever `worst_of` for integrity too.** Rejected because offering `majority` is what lets
  the audit quantify robustness: of the rollup integrity violations under the strict rule, a
  little over a third still contradict the report under the lenient majority rule. Publishing
  that fraction is more convincing than asserting the strict rule is correct.

## Consequences

The experiment `exp_rollup_rule.py` reports both counts. The robustness number (how many
contradictions survive the lenient rule) is a stronger claim than the raw violation count,
because it pre-empts the "you only found those because your rule is strict" objection.
