# Phase Gate Checklist Template

## Phase Metadata

- `phase_id`:
- `phase_name`:
- `owner`:
- `last_reviewed_at`:

## Entry Checklist (Before Implementation)

- [ ] Phase context is current and marked as planning draft or active correctly.
- [ ] `/gsd-plan-phase` generated derived checks for every plan.
- [ ] Research notes exist for unresolved unknowns.
- [ ] HITL runbooks exist for all required scenarios.
- [ ] Preconditions are resolved or explicitly risk-accepted.
- [ ] Dashboard baseline generated (`plan-vs-reality`).

## Exit Checklist (Before Phase Completion)

- [ ] Every plan has gate artifact (`gates/<plan-id>.json`).
- [ ] Every plan has HITL checkpoint artifact (`hitl/<plan-id>.md`).
- [ ] Drift log includes all deviations with severity + RCA where required.
- [ ] No required phase tests are skip/xfail/placeholder.
- [ ] Plan-vs-reality dashboard is regenerated and reviewed.
- [ ] `STATE.md` updated with objective completion evidence.

## Approval Notes

- Entry approval:
- Exit approval:
- Blocking issues:

