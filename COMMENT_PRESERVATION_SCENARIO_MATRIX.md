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

## Explicitly Deferred

Full structural hardening across lists, tables, macros, heavy split/merge rewrites, and concurrency remains deferred.

Heading deletion is no longer excluded from the current project state. There is direct regression coverage for deleted-heading fallback, but the broader structural rewrite families still need separate hardening.

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
| S23 | Comment anchor spans bold/italic/link/code fragments | Partial | Edited-text preserve | No focused regression yet | One link-safety case exists, but broader inline-format coverage is incomplete. |
| S24 | Commented paragraph split into multiple new paragraphs | Partial | Edited-text preserve | No focused regression yet | Needs deterministic fragment selection rules. |
| S25 | Multiple old paragraphs merged into one new paragraph | Partial | Edited-text preserve | No focused regression yet | Needs semantic locality scoring for merged text. |
| S26 | Commented text moved within same section and rewritten | Partial | Edited-text preserve | Indirectly covered | Strong-context move exists, but not broad move+rewrite coverage. |
| S27 | Commented text moved to another heading and rewritten | Partial | Edited-text preserve or Audit-only | Indirectly covered | Needs explicit proof for cross-heading moved content. |
| S28 | Heading renamed but body mostly stable | Covered | Exact preserve or Local fallback preserve | `test_comment_reanchor.py`, `test_compare_guard_heading_resolution.py` | Direct heading-anchor and body-anchor regressions now exist. |
| S29 | Comment attached directly to heading text | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Heading-text preservation and deleted-heading fallback now have direct regressions. |
| S30 | Large section contains many duplicate boilerplate phrases | Partial | Local fallback preserve | Some repeated-text coverage exists | Needs scale-oriented stress coverage. |
| S46 | Deleted nested heading with surviving ancestor | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Deleted nested heading falls back to a surviving ancestor or safe scope anchor. |
| S47 | Deleted main heading with surviving upper heading | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Main deleted heading is preserved as a deleted-comment marker below the surviving upper heading. |
| S48 | Deleted heading path missing entirely in current scope | Covered | Recoverable heading preserve | `test_comment_reanchor.py` | Comment is pinned to the top of the active scope with a deleted-comment icon. |
| S31 | Bullet list item edited in place | Missing | Edited-text preserve | No focused regression | List structure should be treated like paragraph-local rewrite. |
| S32 | Bullet list item reordered within list | Missing | Local fallback preserve or Audit-only | No focused regression | Reorder can break preferred index assumptions. |
| S33 | Numbered list item split or merged | Missing | Edited-text preserve or Audit-only | No focused regression | Needs block-aware list heuristics. |
| S34 | Table cell text edited in place | Missing | Edited-text preserve | No focused regression in comment-preserve suite | Table helpers exist elsewhere, but preservation path is not proven. |
| S35 | Table row deleted | Missing | Recoverable heading preserve or Audit-only | No focused regression | Needs table-aware local fallback. |
| S36 | Table rows reordered | Missing | Audit-only or strong local fallback | No focused regression | Highly ambiguous without row identity. |
| S37 | Table converted to paragraph/list or reverse | Missing | Audit-only | No focused regression | Structural transform is currently under-modeled. |
| S38 | Content inside Confluence macro rewritten | Missing | Audit-only or Edited-text preserve | No focused regression | Macro-heavy storage is a real risk surface. |
| S39 | Content inside info/expand/panel/tab macro moved | Missing | Audit-only | No focused regression | Needs macro boundary awareness. |
| S40 | Content reordered across multiple headings in one publish | Missing | Edited-text preserve or Audit-only | No end-to-end regression | Multi-section movement is not deeply proven. |
| S41 | Entire section split into several headings | Missing | Recoverable heading preserve or Audit-only | No focused regression | Needs ancestor/descendant redistribution logic. |
| S42 | Several headings merged into one heading | Missing | Recoverable heading preserve or Audit-only | No focused regression | Needs cluster-level heading-path reasoning. |
| S43 | Very large document with dozens of comments and repeated patterns | Missing | Mixed outcomes with confidence scoring | No stress suite | Current logic may work, but scale proof is missing. |
| S44 | Concurrent live page edits during overwrite and reinjection | Missing | Audit-only | No focused regression | This is operationally risky and not solved by anchor logic alone. |
| S45 | Marker removed, history unavailable, context destroyed | Missing by design | Audit-only | Stated limitation | This is a true evidence-loss boundary. |

## Covered Scenario Families

These families are already in a reasonably good state:

- exact-match reinjection,
- local rewrite handling,
- repeated-text locality,
- local deletion routing,
- local heading-based fallback,
- nested heading preference,
- cross-section drift prevention,
- history-based recovery when evidence is strong,
- post-run audit and classification.

## Partial Scenario Families

These areas have some supporting logic but not enough direct proof yet:

- moved content combined with rewriting,
- inline formatting boundary cases,
- large duplicate-heavy sections.

These should be treated as candidates for targeted regression design, not as complete guarantees.

## Missing Scenario Families

These are the main gaps for a truly large-document production workflow:

- list-aware anchoring,
- table-aware anchoring,
- macro-aware anchoring,
- split/merge block reasoning,
- large multi-section reorder reasoning,
- scale and stress validation,
- concurrency-safe final update flow,
- confidence-based refusal for ambiguous cases.

## Recommended Next Work Order

### Priority 1: Structural content cases that are common and recoverable

1. List item edit, reorder, split, and merge scenarios.
2. Table cell edit and row deletion scenarios.
3. Inline formatting boundary scenarios across bold, link, code, and mixed tags.
4. Direct list/table comment cases with repeated local duplicates.

### Priority 2: Ambiguous relocation cases

1. Move within same section plus rewrite.
2. Move across headings plus rewrite.
3. Paragraph split and paragraph merge cases.
4. Duplicate-heavy large-section stress cases.

### Priority 3: Production hardening

1. Confidence score per re-anchor decision.
2. Explicit `manual_review_required` classification when ambiguity is too high.
3. Final PUT precondition checks against page version drift.
4. Stronger payload-vs-saved validation after reinjection.

## Test Plan To Add Next

The next regression pack should add synthetic tests for:

- list item replacement,
- list item reorder,
- list item delete,
- table cell replacement,
- table row deletion,
- inline-format mixed-tag anchor,
- paragraph split into two blocks,
- two paragraphs merged into one block,
- moved-and-rewritten content across headings,
- high-duplication stress page with many comments.

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