# Defense guide: status-audit

A guide to defending this repository in an interview. Every number here is machine-checked
against the code by `tools/check_numbers.py`, so the guide and the tool cannot drift apart.

## The 30 second version

"A weekly RAG status is a human summary, and a summary cannot audit itself: reading the color
tells you nothing about whether it is honest. status-audit recomputes the color independently
from the objective signals under a written policy, and reconciles the two across a whole
portfolio. On a seeded portfolio of 6 programs it found 26 program-weeks reported Green while
the signals said Amber or Red, and it measures how long each program stayed green after its
signals turned."

Then stop. The question that usually comes next is "how do you know your recomputed color is
any more correct than theirs". That is the right question, and the answer is the next section.

## The claims and how each is proved

### Claim 1: 26 program-weeks were green over trouble

- Prove it: `python -m status_audit.cli audit` prints the verdict and the count; exit code `1`.
- The numbers: 26 program-weeks reported Green over Amber/Red signals, 16 of them Green over Red.
- If pushed ("is your policy just stricter than theirs?"): the sensitivity sweep answers this
  directly. The count has a robust floor of 26 when the amber SPI line is loosened, and it
  inflates to 63 only if the line is tightened to on-plan. The 26 are driven by open criticals,
  overdue milestones and red-level SPI, not by a marginal amber call. I publish the floor.

### Claim 2: the confession lag is signed, and it caught a real bug

- Prove it: `python experiments/exp_confession_lag.py` prints the per-program table.
- The numbers: the longest was a 4-week confession lag, and 1 program never confessed.
- If pushed ("isn't lag just the distance between two dates?"): no, and that exact mistake was
  my first implementation. Absolute distance reported a phantom lag of 18 weeks for the most
  conservative program in the set, inverting the finding. The signed rule and the test that
  pins it are in ADR-003.

### Claim 3: the rollup check is independent of the signal check

- Prove it: `python experiments/exp_rollup_rule.py`, and
  `test_the_rollup_liar_is_caught_by_rollup_without_a_signal_violation`.
- The numbers: 48 rollup integrity violations under the strict rule, and 17 still contradict the
  report under the lenient majority rule.
- If pushed ("you found those because your rule is strict"): a little over a third survive the
  lenient rule, which is the robustness number. PRG-FORGE is the worked example: its signals are
  green and its program report is green, so the signal check sees nothing, yet a workstream
  reported red, so the rollup check flags it. The two checks are not redundant.

### Claim 4: every number here is reproduced offline

- Prove it: `make verify` from a fresh clone, no network.
- The numbers: 132 tests, 100% line and branch coverage, and the number checker fails the build
  if a figure drifts. 624 reconciled reports in total.
- If pushed ("the data is fake"): yes, and deliberately. The generator models reporting
  behavior (honest, watermelon, sandbagger, rollup-liar), which a live feed would not label. A
  live tracker would change realism, not the method, and would cost reproducibility (ADR-005).

## Questions that are meant to be hard

**"Isn't this just a wrapper around a few if-statements?"** The if-statements are the easy part
and they are in one pure function (`policy_engine.compute_rag`). The work is everything that
makes the output trustworthy: the signed temporal reconciliation, the separation of the
objective rollup from the configurable integrity rule, and above all the sensitivity sweep that
prices the thresholds. A wrapper asserts a number; this prices its own biggest assumption.

**"The corpus is synthetic. Does any of this transfer?"** The method transfers exactly; the
numbers are of the fixture. The reconciliation, the confession lag and the rollup check all run
on a real export unchanged, because they only need a reported color and the signals. What would
not transfer is the specific count of 26, which is a fact about this seeded portfolio.

**"What is the weakest part?"** Confession lag scores the first deterioration episode only. A
program that recovers and relapses has a second episode the current version does not score, and
a one-week blip counts as an onset. I chose first-episode because it is unambiguous and the
recurring case does not occur in the seeded data, so building the machinery now would be untested
weight. It is the Pivot, with its trigger written in the README.

**"What would you do differently with more time?"** A per-stakeholder view, because the same
program can read Green to finance and Amber to engineering, and reconciling those is a richer
version of the same idea. And a calibration step that fits the policy thresholds to an
organization's own closed-project history instead of asserting them, which would turn the
sensitivity sweep from a caveat into a feature.

**"Why worst-wins instead of a weighted model?"** Because averaging launders the exact optimism
the tool exists to catch: four green signals and one red SPI average to amber. ADR-001.

**"Could a team game this?"** Yes, by making the signals lie too, not just the color. The tool
audits the report against the signals; it cannot audit the signals against reality. That is the
honest boundary, and it is why the output is "disagreement", not "truth".

## Things to say, and things not to say

Say:
- "The tool detects disagreement between a report and a written policy, and prices how much of
  that disagreement depends on the policy."
- "Zero workstream-weeks were optimistic: the distortion entered at the program rollup."
- "The confession lag is signed, so a cautious reporter scores zero, not a large lag."

Do not say:
- "The tool detects programs that are really in trouble." It detects inconsistency, not truth.
- "26 is the number of troubled weeks." 26 is the floor under this policy; say so, and cite the
  inflated 63 to show you know the difference.
- "Zero false anything." There is no ground-truth label here, so there is no false-positive rate
  to quote. The sensitivity floor is the honest substitute.

## The live demo script

```bash
# 1. the baseline: the committed data fails the gate
python -m status_audit.cli audit ; echo "exit: $?"

# 2. the per-program confession lag, including the program that never confessed
python experiments/exp_confession_lag.py

# 3. the number no status report can give you: how much is policy, how much is program
python experiments/exp_threshold_sensitivity.py

# 4. the rollup contradiction that needs no signal at all
python experiments/exp_rollup_rule.py

# 5. the receipts: every figure re-measured and checked, offline
make verify
```
