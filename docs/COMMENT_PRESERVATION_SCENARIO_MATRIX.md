# Comment Preservation Scenario Matrix

## Scope

This document maps the current comment-preservation behavior for large documents where edits can happen in many directions: inside paragraphs, across sections, across headings, and across multiple publish passes.

This matrix is intended to answer four questions:

1. Which scenarios are already covered well?
2. Which scenarios are only partially covered?
3. Which scenarios are still missing?
4. What should be implemented next to move toward production-grade preservation?

## Current Boundary

This project is strongest when a comment can still be tied back to one or more of these signals:

- exact surviving anchor text,
- strong left/right local context,
- stable section or heading path,
- recoverable inline marker metadata,
- historical artifacts from earlier compare runs.

This project is weaker when several of those signals disappear at the same time.

## Production Readiness Matrix

This is the short operational reading of the current project state.

| Readiness bucket | Scenario families | Current position |
|---|---|---|
| `Ready with confidence` | Exact text survives, local rewrite in same block, heading rename, nested-heading rename, deleted text with surviving heading, repeated text with strong locality, list edit/reorder/split/merge, table cell edit/row delete/row reorder, paragraph split/merge, simple table-paragraph conversion with strong identity, macro-body rewrite, simple macro-to-paragraph relocation with strong visible text | These flows have direct regression proof and are suitable for production use in the current section-scoped publish model. |
| `Usable with manual review` | Mixed inline-format anchors, cross-heading move+rewrite, duplicate-heavy large sections, broader table-paragraph conversions, macro relocation with structure changes, multi-heading reorder in one publish, large-page stress cases, version-conflict retry paths | These flows have some proof or partial hardening, but they should still run under report review and risk-gate checks rather than blind trust. |
| `Not guaranteed automatically` | Evidence-loss cases, arbitrary block restructuring, several headings merged/split at once, weak-identity list/table transforms, deep macro relocation across unrelated containers, full concurrent live-edit choreography during overwrite and reinjection | These flows are not safe to promise as exact-preserve. The system should fail closed, use safe fallback placement, or require manual review. |

### Operational Rule

For production usage today:

1. Treat `Ready with confidence` scenarios as normal supported flows.
2. Treat `Usable with manual review` scenarios as supported only with audit review.
3. Treat `Not guaranteed automatically` scenarios as fail-closed boundaries, not bugs.

### Final Production Verdict

Today, this project is a **production candidate** for section-scoped publishing where edits are mostly local rewrites, heading changes, moderate structural transforms, and repeated-text cases inside a stable hierarchy.

Today, this project is **not yet a universal production-ready engine** for arbitrary whole-document restructuring, deep macro relocation, weak-identity transforms, or live concurrent rewrite races.

## Explicitly Deferred

Arbitrary structural transforms, macro relocation across unrelated containers, and full end-to-end concurrency orchestration remain deferred.

Heading deletion is no longer excluded from the current project state. There is direct regression coverage for deleted-heading fallback, and targeted structural rewrite families now have explicit regression coverage. The remaining gap is not basic structural support, but broader proof across more ambiguous transforms.

## Outcome Classes

Each scenario below is mapped to one of these expected outcomes:

- `Exact preserve`: comment remains on the same logical anchor text.
- `Edited-text preserve`: comment moves to the rewritten local replacement text.
- `Local fallback preserve`: comment is preserved near the original location using a safe nearby anchor.
- `Recoverable heading preserve`: comment is preserved on a local heading or surviving section anchor when direct text anchoring is no longer safe.
- `Audit-only`: comment cannot be safely re-attached with current evidence; the run should report it clearly for manual review.

## Scenario Matrix

| ID | Scenario | Current status | Expected outcome | Evidence in repo | Notes |
|---|---|---|---|---|---|
| S01 | Exact text unchanged in same section | Covered | Exact preserve | `test_comment_scenarios.py` | Baseline exact-match path is stable. |
| S02 | Single word replaced in same sentence | Covered | Edited-text preserve | `test_comment_scenarios.py`, `test_comment_report.py` | Local replacement path is working. |
| S03 | Whole sentence rewritten in same paragraph | Covered | Edited-text preserve | `test_comment_scenarios.py` | Context-guided span selection exists. |
| S04 | Repeated anchor text in same section | Covered | Exact preserve | `test_comment_scenarios.py` | Locality scoring prevents first-match drift. |
| S05 | Prior marker insertions shift later preferred positions | Covered | Exact preserve | `test_comment_scenarios.py` | Injection delta tracking is validated. |
| S06 | Repeated surrounding context across sections | Covered | Edited-text preserve | `test_comment_scenarios.py` | Local section selection is protected. |
| S07 | Deleted body text under a surviving heading | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Routed to nearest local heading. |
| S08 | Deleted body text under nested subheading | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Deepest valid heading path is preferred. |
| S09 | Multiple deleted comments on same deleted block | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Grouping stability is covered. |
| S10 | Previously re-anchored deleted comments survive next overwrite | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Multi-pass durability exists. |
| S11 | Exact text still exists elsewhere but original context is weak | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Prevents drift to wrong surviving copy. |
| S12 | Single deleted word could drift to unrelated surviving word | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Short-word misbinding is blocked. |
| S13 | Same heading name exists in multiple sections | Covered | Local fallback preserve | `test_comment_reanchor.py` | Section boundary checks prevent cross-section drift. |
| S14 | Strong context shows content moved and should be followed | Covered | Edited-text preserve | `test_comment_reanchor.py` | Strong-context follow behavior exists. |
| S15 | Weak context suggests content moved but evidence is poor | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Safer to pin locally than drift globally. |
| S16 | Anchor candidate appears inside unsafe HTML attribute or tag boundary | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Link href corruption is explicitly blocked. |
| S17 | Marker metadata missing from storage but recoverable from inline properties | Covered | Local fallback preserve | `test_comment_reanchor.py` | Ownership filtering is already present. |
| S18 | Marker metadata recoverable from historical compare artifacts | Covered | Local fallback preserve | `test_comment_reanchor.py` | History enrichment and supplementation exist. |
| S19 | Reporting preserved vs missing vs reanchored comments | Covered | Audit-only | `test_comment_report.py` | Audit quality is good. |
| S20 | Auto-targeting single changed heading | Covered | Exact preserve | `test_compare_guard_heading_resolution.py` | Single changed heading detection works. |
| S21 | Auto-targeting multiple changed headings in order | Covered | Exact preserve | `test_compare_guard_heading_resolution.py` | Changed-heading list is returned in markdown order. |
| S22 | Same logical markdown from copied file path | Covered | Exact preserve | `test_compare_guard_heading_resolution.py` | Baseline reuse protects auto mode. |
| S23 | Comment anchor spans bold/italic/link/code fragments | Partial | Edited-text preserve | `test_comment_reanchor.py`, `test_comment_structural_scenarios.py` | Link-boundary safety exists and multi-tag visible-phrase recovery is now covered, but broader formatting families are still incomplete. |
| S24 | Commented paragraph split into multiple new paragraphs | Covered | Edited-text preserve | `test_comment_structural_scenarios.py` | Split-paragraph fragment selection now has direct regression coverage. |
| S25 | Multiple old paragraphs merged into one new paragraph | Covered | Edited-text preserve | `test_comment_structural_scenarios.py` | Merge-to-single-paragraph local anchoring is directly tested. |
| S26 | Commented text moved within same section and rewritten | Covered | Edited-text preserve | `test_comment_reanchor.py` | Strong-context move handling exists with explicit regression proof. |
| S27 | Commented text moved to another heading and rewritten | Covered | Edited-text preserve or Recoverable heading preserve | `test_comment_structural_scenarios.py` | Cross-heading move now follows rewritten content when context is strong; weak evidence still falls back safely. |
| S28 | Heading renamed but body mostly stable | Covered | Exact preserve or Local fallback preserve | `test_comment_reanchor.py`, `test_compare_guard_heading_resolution.py` | Direct heading-anchor and body-anchor regressions now exist. |
| S29 | Comment attached directly to heading text | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Heading-text preservation and deleted-heading fallback now have direct regressions. |
| S30 | Large section contains many duplicate boilerplate phrases | Covered | Local fallback preserve | `test_comment_structural_scenarios.py`, `test_comment_scale_scenarios.py` | Duplicate-heavy locality and section stability now have focused regression coverage. |
| S46 | Deleted nested heading with surviving ancestor | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Deleted nested heading falls back to a surviving ancestor or safe scope anchor. |
| S47 | Deleted main heading with surviving upper heading | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Main deleted heading is preserved as a deleted-comment marker below the surviving upper heading. |
| S48 | Deleted heading path missing entirely in current scope | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Comment is pinned to the top of the active scope with a deleted-comment icon. |
| S31 | Bullet list item edited in place | Covered | Edited-text preserve | `test_comment_structural_scenarios.py` | List-item rewrite stays on the rewritten bullet. |
| S32 | Bullet list item reordered within list | Covered | Local fallback preserve or Edited-text preserve | `test_comment_structural_scenarios.py` | Reordered bullet comments stay with the correct moved item when context is strong. |
| S33 | Numbered or bullet list item split or merged | Covered | Edited-text preserve or Audit-only | `test_comment_structural_scenarios.py` | List split and merge now have direct synthetic regression coverage in addition to renumber-only handling. |
| S34 | Table cell text edited in place | Covered | Edited-text preserve | `test_comment_structural_scenarios.py` | Same-cell rewrite behavior is directly tested. |
| S35 | Table row deleted | Covered | Recoverable heading preserve or Audit-only | `test_comment_structural_scenarios.py` | Deleted-row comments are blocked from jumping to duplicate values in other rows. |
| S36 | Table rows reordered | Covered | Audit-only or strong local fallback | `test_comment_structural_scenarios.py` | Row-local context can follow reordered rows when evidence is strong. |
| S37 | Table converted to paragraph/list or reverse | Partial | Edited-text preserve or Audit-only | `test_comment_structural_scenarios.py` | Table-to-paragraph and paragraph-to-table recovery are covered when identity survives strongly; broader transform families remain under-modeled. |
| S38 | Content inside Confluence macro rewritten | Covered | Audit-only or Edited-text preserve | `test_comment_structural_scenarios.py` | Macro-body rewrite inside structured macro is directly tested. |
| S39 | Content inside info/expand/panel/tab macro moved | Partial | Audit-only or Edited-text preserve | `test_comment_structural_scenarios.py`, `stress_comment_preservation_harness.py` | Macro-to-paragraph/simple relocation with strong visible text is now covered, but broader moved-macro families are still incomplete. |
| S40 | Content reordered across multiple headings in one publish | Partial | Edited-text preserve or Audit-only | `test_comment_structural_scenarios.py` | Reordered multi-heading sections with duplicate-heavy content are covered in synthetic form, but broad end-to-end multi-section movement is still not deeply proven. |
| S41 | Entire section split into several headings | Covered | Local fallback preserve (top orphan space) | `test_comment_structural_scenarios.py` | When direct redistribution is ambiguous, the comment is preserved as an orphan marker at top-of-scope empty space. |
| S42 | Several headings merged into one heading | Covered | Local fallback preserve (top orphan space) | `test_comment_structural_scenarios.py` | Merge ambiguity now fails closed to top-of-scope orphan placement instead of risking drift. |
| S43 | Very large document with dozens of comments and repeated patterns | Partial | Mixed outcomes with confidence scoring | `test_comment_scale_scenarios.py`, `stress_comment_preservation_harness.py` | Scale and duplication proof now exists, but production-scale end-to-end validation is still broader than the current synthetic suite. |
| S44 | Concurrent live page edits during overwrite and reinjection | Partial | Audit-only | `test_comment_reanchor.py` | Reanchor storage save now has explicit version-conflict coverage and fail-closed retry behavior, but full end-to-end concurrent publish choreography is still operationally risky. |
| S45 | Marker removed, history unavailable, context destroyed | Missing by design | Audit-only | Stated limitation | This is a true evidence-loss boundary. |

## Covered Scenario Families

These families are already in a reasonably good state:

- exact-match reinjection,
- local rewrite handling,
- list-local rewrites and reorders,
- list split and merge handling,
- table cell, row delete, and row reorder handling,
- table-to-paragraph recovery when row identity survives,
- macro-body rewrite handling,
- simple macro-to-paragraph relocation with strong visible text,
- paragraph split and merge handling,
- simple paragraph-to-table and table-to-paragraph identity-preserving transforms,
- repeated-text locality,
- local deletion routing,
- local heading-based fallback,
- nested heading preference,
- cross-heading moved-and-rewritten follow with strong context,
- cross-section drift prevention,
- history-based recovery when evidence is strong,
- scale-oriented duplicate locality checks,
- post-run audit and classification.

## Partial Scenario Families

These areas have some supporting logic but not enough direct proof yet:

- inline formatting boundary cases,
- macro relocation across containers,
- full end-to-end large-page production validation,
- concurrent live edit choreography across the full overwrite plus reinjection flow.

These should be treated as candidates for targeted regression design, not as complete guarantees.

## Missing Scenario Families

These are the main gaps for a truly large-document production workflow:

- large multi-section reorder reasoning,
- table-to-non-table structural transform reasoning,
- macro relocation and deep macro boundary awareness,
- stronger end-to-end scale validation against real pages,
- concurrency-safe final update orchestration across the full publish cycle,
- confidence-based refusal for ambiguous cases.

## Recommended Next Work Order

### Priority 1: Structural content cases that are common and recoverable

1. Table transform scenarios beyond the now-covered table-to-paragraph case, especially reverse transforms and weak-identity conversions.
2. Inline formatting boundary scenarios across bold, link, code, and mixed tags.
3. Direct list/table comment cases with repeated local duplicates under larger page stress.
4. Column-identity and cross-row ambiguity transforms.

### Priority 2: Ambiguous relocation cases

1. Move across multiple headings in one publish with several comments at once.
2. Paragraph split into more than two fragments with repeated local text.
3. Macro relocation across containers plus rewrite.
4. Duplicate-heavy large-section stress cases at higher comment density.

### Priority 3: Production hardening

1. Confidence score per re-anchor decision.
2. Explicit `manual_review_required` classification when ambiguity is too high.
3. End-to-end final PUT precondition checks against page version drift.
4. Stronger payload-vs-saved validation after reinjection.

## Test Plan To Add Next

The next regression pack should add synthetic tests for:

- table column reorder with duplicate values,
- paragraph-to-table and weaker table-to-paragraph transforms,
- inline-format mixed-tag anchor,
- paragraph split into three blocks,
- macro relocation across container boundaries,
- multi-comment cross-heading moved-and-rewritten content,
- higher-density stress pages with many duplicate anchors,
- end-to-end conflict telemetry validation around live version drift.

## Proposed Production Rule

For ambiguous cases, the system should prefer:

1. exact local anchor,
2. strong edited-context anchor,
3. safe local heading fallback,
4. audit-only manual review.

It should not choose a weak global guess just to avoid reporting a missing comment.

## Practical Reading Of Current Project State

Today, this project is suitable for section-scoped publishing where most edits are local rewrites, deletions, or repeated-text cases inside a stable document hierarchy.

Today, this project is not yet fully proven for arbitrary large-document rewrites involving lists, tables, macros, heavy block restructuring, or concurrent live edits.

That is the correct boundary to use when planning the next production hardening phase.