# Forensics audit (Phase 4)

A four-persona adversarial audit of this repository, run before delivery. Grades are PASS,
WEAK or FAIL. The mechanical pre-flight and all four personas were run against the built
artefact, not the intent.

## Mechanical pre-flight

- Git history carries no AI attribution and no co-author trailers; the author is the candidate.
- No em dashes anywhere (data tables excepted, of which there are none with dashes).
- No placeholder handles in any badge or clone URL; badges are static and need no handle.
- Every README image resolves with non-zero dimensions (checked with cmark-gfm plus a browser).
- Lint clean, tests green, `make verify` green from a fresh clone with no network.
- `pip install -e ".[dev]"` and the `status-audit` console script both work in a clean venv.

## Persona 1, Principal Engineer

1. Clone, run, verify: PASS. Fresh clone, `make verify` green, offline.
2. Architecture: PASS. One module per concern; the engine is a pure function.
3. Configurability: PASS with distinction. Every threshold is in a commented TOML file.
4. Error handling: PASS. Validated boundaries, three typed errors, a dedicated exit code.
5. Tests: PASS. Property-named, a bug-pinning test with its story, 100% coverage measured.
6. Determinism: PASS. Seeded generator, pure engine, a determinism test.

## Persona 2, Measurement Auditor

1. Traceability: PASS. Every figure is produced by code and guarded by an anchor phrase.
2. Break the checker: PASS. Changing one README figure fails the build (demonstrated).
3. Honest zeros: PASS. The one zero (0 optimistic workstream-weeks) is an exact census of a
   deterministic corpus, scoped to this portfolio, not a sampled rate presented as general.
4. Machine independence: PASS. No absolute duration is a headline; the demo pacing is labelled.
5. The unflattering number: PASS. The first screen carries the robust floor and the inflated 63.
6. The boundary: PASS. A dedicated section and ADR-005 state what cannot be established.

## Persona 3, UX Director

1. First 30 seconds: PASS. Opens with the impossibility, not with the technology.
2. The so-what: PASS. Results are framed as a week nobody escalated, not as a metric.
3. Visual storytelling: PASS. A committed diagram and a real screenshot, both legible.
4. Actionability: PASS. Ends with the Pivot, future work, and the first metric to watch.

## Persona 4, Hiring Manager

1. Tutorial smell: PASS. The impossibility (a summary cannot audit itself) is real and named.
2. Stolen valour: PASS. Library use (pandas) is delineated from the author-built engine.
3. The war story: PASS. The signed-lag bug, with the phantom 18-week figure that revealed it.
4. Defensibility: PASS. The defense guide has an honest weakest-part answer.
5. One thing I will remember: the confession lag, and that zero optimism came from the leads.

## Verdict

Overall score: 9 / 10. No critical failures. The repository is job-ready.

Impact multipliers considered for a 9 to 10 move: a per-stakeholder reconciliation (the same
program read Green to finance and Amber to engineering); a calibration step that fits the policy
thresholds to an organisation's own closed-project history; and multi-episode confession
tracking. All three are recorded as future work.

Elevator pitch: A weekly RAG status is a human summary, and a summary cannot audit itself, so
status-audit recomputes the colour independently from the objective signals and reconciles the
two across a whole portfolio. On seeded data it found 26 program-weeks reported Green while the
signals said Amber or Red, measured how many weeks each program stayed green after its signals
turned, and priced its own biggest assumption by showing the headline has a robust floor of 26
that only inflates when the amber line is tightened. Every number is re-measured by CI and the
build fails if a document drifts from the code.
