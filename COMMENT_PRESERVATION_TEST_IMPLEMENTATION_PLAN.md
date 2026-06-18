# Comment Preservation Test Implementation Plan

## Purpose

This document converts the scenario matrix into an executable test plan for the next regression packs.

It is intentionally limited to non-heading-delete work for now.

The goal is to answer:

1. Which test files should be extended first?
2. What concrete test cases should be added next?
3. What behavior should each test prove?
4. In what order should implementation happen so stable logic is not disturbed?

## Planning Rules

The next changes should follow these rules:

1. Add tests before heuristics for every new scenario family.
2. Extend existing test files when the scenario matches their purpose.
3. Prefer synthetic HTML storage tests first, then wider flow tests.
4. Use audit-only expectations for ambiguous cases instead of forcing a wrong re-anchor.
5. Keep heading-deletion work out of this plan until it becomes its own focused pass.

## Recommended File Layout

- Use [test_comment_scenarios.py](c:/Task%203/dds_comment_preserve_solution/test_comment_scenarios.py) for compact happy-path scenario coverage.
- Use [test_comment_reanchor.py](c:/Task%203/dds_comment_preserve_solution/test_comment_reanchor.py) for edge cases, ambiguity handling, and locality protections.
- Use [test_comment_report.py](c:/Task%203/dds_comment_preserve_solution/test_comment_report.py) for audit classification and reporting additions.
- Add a new file [test_comment_structural_scenarios.py](c:/Task%203/dds_comment_preserve_solution/test_comment_structural_scenarios.py) for split, merge, list, and table-local synthetic cases.
- Add a new file [test_comment_scale_scenarios.py](c:/Task%203/dds_comment_preserve_solution/test_comment_scale_scenarios.py) later for high-duplication and large-page stress cases.

## Phase 1: Priority Regression Pack

This is the next pack that should be implemented first.

### 1. List scenarios

Add these tests first in [test_comment_structural_scenarios.py](c:/Task%203/dds_comment_preserve_solution/test_comment_structural_scenarios.py):

- `test_bullet_item_replacement_stays_on_rewritten_item`
Expected behavior: when a bullet item text changes in place, the comment reanchors to the rewritten item text, not to another bullet.

- `test_bullet_item_reorder_does_not_jump_to_same_phrase_in_neighbor_item`
Expected behavior: if list items reorder, the comment should either stay on the correct moved item with strong context or fall back safely instead of binding to a neighbor with similar text.

- `test_numbered_item_renumber_only_keeps_comment_on_same_item_text`
Expected behavior: numbering changes alone should not break the anchor.

- `test_list_item_split_prefers_best_local_fragment`
Expected behavior: when one bullet becomes two bullets, the comment should choose the fragment with strongest surviving context.

- `test_list_item_merge_uses_local_context_not_first_token`
Expected behavior: when two bullets merge into one sentence or one bullet, the comment should land on the correct merged segment, not the first generic token.

### 2. Table scenarios

Add these tests next in [test_comment_structural_scenarios.py](c:/Task%203/dds_comment_preserve_solution/test_comment_structural_scenarios.py):

- `test_table_cell_replacement_stays_in_same_cell`
Expected behavior: if a cell value changes in place, the comment should move to the edited cell text.

- `test_table_row_delete_does_not_jump_to_same_value_in_other_row`
Expected behavior: when a row is deleted, the comment should not attach to a similar value elsewhere in the table.

- `test_table_row_reorder_preserves_comment_on_same_row_content_when_context_is_strong`
Expected behavior: moved rows should be followed only when row-local context remains strong.

- `test_table_column_reorder_does_not_bind_to_same_column_value_in_wrong_row`
Expected behavior: reordering columns should not cause accidental cross-row attachment.

- `test_table_to_paragraph_transform_reports_manual_review_when_identity_is_lost`
Expected behavior: if structural identity is destroyed, the system should prefer a safe audit-style outcome over a weak guess.

### 3. Heading-text and inline-format scenarios

Add these tests in [test_comment_reanchor.py](c:/Task%203/dds_comment_preserve_solution/test_comment_reanchor.py):

- `test_heading_text_comment_survives_heading_rename_without_deletion`
Expected behavior: a comment attached to heading text should stay with the renamed heading when context is still local and clear.

- `test_heading_text_comment_does_not_jump_to_duplicate_heading_name_elsewhere`
Expected behavior: if a similar heading appears elsewhere, the original local heading path must win.

- `test_inline_format_boundary_bold_to_plain_keeps_same_visible_anchor`
Expected behavior: visible text crossing formatting boundaries should still be reanchored safely.

- `test_inline_format_boundary_link_text_to_plain_text_keeps_visible_anchor`
Expected behavior: moving between linked and plain text should not corrupt markup or lose the anchor.

## Phase 2: Ambiguous Relocation Pack

After Phase 1 passes, add the next family in [test_comment_structural_scenarios.py](c:/Task%203/dds_comment_preserve_solution/test_comment_structural_scenarios.py) and [test_comment_reanchor.py](c:/Task%203/dds_comment_preserve_solution/test_comment_reanchor.py):

- `test_paragraph_split_into_two_blocks_prefers_stronger_context_half`
- `test_paragraph_split_into_three_blocks_with_repeated_words_stays_local`
- `test_two_paragraphs_merged_into_one_preserves_comment_on_best_local_segment`
- `test_content_moved_to_another_heading_and_rewritten_follows_only_with_strong_context`
- `test_content_moved_to_renamed_heading_with_weak_context_prefers_safe_local_fallback`

Expected rule for all of these:

- strong local evidence can follow the moved text,
- weak evidence should not produce a broad global guess,
- ambiguous results should be classified for manual review once that reporting path exists.

## Phase 3: Scale And Stress Pack

Add these later in [test_comment_scale_scenarios.py](c:/Task%203/dds_comment_preserve_solution/test_comment_scale_scenarios.py):

- `test_large_page_with_many_repeated_paragraphs_keeps_comments_local`
- `test_many_comments_in_same_section_do_not_pull_later_comments_backward`
- `test_duplicate_heavy_page_prefers_section_scoping_over_global_match`
- `test_sequential_multi_section_reanchor_does_not_cross_contaminate_sections`

These tests are less about one heuristic and more about proving the current architecture scales safely.

## Reporting Extensions To Plan After Structural Tests

Once the structural tests exist, the next audit/report additions should be planned in [test_comment_report.py](c:/Task%203/dds_comment_preserve_solution/test_comment_report.py):

- `manual_review_required` classification for ambiguous but recoverable-looking cases
- confidence or route labels for structural transforms
- clearer distinction between moved-with-confidence and weak fallback outcomes

## Suggested Implementation Order

1. Create [test_comment_structural_scenarios.py](c:/Task%203/dds_comment_preserve_solution/test_comment_structural_scenarios.py) with list and table cases only.
2. Add the heading-text and inline-format regressions to [test_comment_reanchor.py](c:/Task%203/dds_comment_preserve_solution/test_comment_reanchor.py).
3. Run the full existing suite after each scenario family, not after a giant batch.
4. Only after tests fail in a controlled way, touch [comment_preserve_publish.py](c:/Task%203/dds_comment_preserve_solution/comment_preserve_publish.py).
5. After structural coverage is stable, add stress and reporting packs.

## Definition Of Done For The Next Pack

The next implementation step should be considered complete only when:

1. The new structural test file exists.
2. List item edit and reorder cases have explicit coverage.
3. Table cell edit and row deletion cases have explicit coverage.
4. Heading-text rename without deletion has explicit coverage.
5. Inline-format boundary cases have explicit coverage.
6. The existing regression suite still passes unchanged stable scenarios.

## Immediate Next Action

The best next engineering step is:

1. create [test_comment_structural_scenarios.py](c:/Task%203/dds_comment_preserve_solution/test_comment_structural_scenarios.py),
2. implement the first 6 to 8 Phase 1 tests,
3. use those failures to drive the smallest safe changes in [comment_preserve_publish.py](c:/Task%203/dds_comment_preserve_solution/comment_preserve_publish.py).