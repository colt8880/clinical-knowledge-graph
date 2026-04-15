# 0006. CRC as the only v0 guideline domain

Status: Superseded by 0013 (2026-04-15)
Date: 2026-04-14

**Superseded.** See ADR 0013 — v0 domain changed from CRC to USPSTF statins. CRC content is preserved at `docs/reference/crc-model.archived.md` and `evals/archive/crc/`.


## Context

There are ~50 USPSTF Grade A/B recommendations plus specialty-society guidance across dozens of domains. Starting broad means shallow depth everywhere and no domain fully exercising the schema. Starting narrow means one domain is genuinely complete and the schema is stressed by real complexity before scaling.

## Decision

v0 models colorectal cancer screening only, anchored on USPSTF 2021 with ACS and USMSTF modeled where they extend or conflict. Cross-guideline conflicts use `PREEMPTED_BY` edges with conditional predicates; conflicts are modeled explicitly, not resolved silently. A second domain is not added until the CRC slice has end-to-end evals passing.

## Alternatives considered

- **CRC + HTN together.** Rejected: HTN has different schema stressors (diagnosis requires repeat readings, treatment has dose-dependent logic) and muddles the v0 scope.
- **Pick the "easiest" domain.** Rejected: CRC is not easiest (Lynch preemption, surveillance intervals, multi-strategy recs) but it exercises the features we'd hit in most other domains. Easier domains would let the schema be underspecified.

## Consequences

- HTN, lung cancer screening, and statin primary prevention are "pressure-tested" (their shapes inform schema decisions) but not implemented.
- The eval harness is built around CRC fixtures; cross-domain eval tooling arrives with the second domain.
- Ingestion pipeline is built for CRC's shape first; generalization happens on second-domain onboarding.

## Related

- `docs/reference/crc-model.md`
- `evals/SPEC.md`
- `evals/INVENTORY.md`
