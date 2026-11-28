# ADR-002: Policy thresholds live in a commented TOML file, not in the code

Status: accepted

## Context

The audit's entire output is "the report disagrees with this policy". The policy is therefore
not an implementation detail: it is the claim. A reviewer has to be able to read it, challenge
it, and change one number without reading Python.

## Decision

Every threshold lives in `policy.toml`, loaded with the standard library `tomllib`. The code
holds no default threshold of its own. The file carries a comment on every value explaining
the decision it encodes, including why cost and risk cap at amber.

## Alternatives considered

- **Hardcode the thresholds as module constants.** Rejected. A threshold buried in code reads
  as a law of nature rather than a choice, which is the opposite of the honesty this tool is
  selling. It also makes the sensitivity sweep (ADR-003 neighbour) awkward: perturbing a
  threshold would mean editing code.
- **YAML.** Rejected as a dependency with nothing to add here. TOML is in the standard library
  from Python 3.11, supports comments, and keeps the install free of a parser. The boring
  choice is the right one: fewer moving parts in the thing a reviewer must trust.
- **A default baked into the loader as a fallback.** Rejected explicitly. A silent default
  would override a misspelled key instead of failing, which is the one behavior a policy
  loader must never have. The loader raises `PolicyError` naming the missing key instead.

## Consequences

The loader validates the policy at load time and refuses an incoherent one (an amber SPI line
below the red line, an amber critical count above the red count). The cost of the boring choice
is that the policy is a second file a reviewer has to open; the benefit is that the argument of
the tool is legible to a non-programmer, which for a program-governance audience is the whole
point.
