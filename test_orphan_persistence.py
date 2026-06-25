"""
Test scenario to verify orphan markers persist and stay consolidated at document top
across multiple sequential operations without scattering.

Test workflow:
1. First operation: Inject markers with some having empty anchors (orphans) → should be at top
2. Extract markers from storage → orphans should have force_orphan flag
3. Second operation: Modify content → orphans should stay at top, not scatter
4. Verify orphans never move to middle/bottom of document
"""
import unittest
import re
from comment_preserve_publish import (
    _extract_inline_markers,
    _inject_inline_markers,
    _ORPHAN_COMMENT_EMPTY_ANCHOR_HTML,
)


def _nth_index(text: str, needle: str, occurrence: int = 1) -> int:
    """Find the nth occurrence of needle in text."""
    start = -1
    for _ in range(occurrence):
        start = text.index(needle, start + 1)
    return start


def _marker(old_storage: str, anchor: str, ref: str, occurrence: int = 1) -> dict:
    """Create a marker dict for testing."""
    anchor_start = _nth_index(old_storage, anchor, occurrence)
    return {
        "ref": ref,
        "anchor_html": anchor,
        "left_context": old_storage[max(0, anchor_start - 80):anchor_start],
        "right_context": old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
        "start": anchor_start,
        "end": anchor_start + len(anchor),
    }


def _orphan_marker(ref: str) -> dict:
    """Create an orphan marker (empty anchor)."""
    return {
        "ref": ref,
        "anchor_html": _ORPHAN_COMMENT_EMPTY_ANCHOR_HTML,
        "left_context": "",
        "right_context": "",
        "start": 0,
        "end": 0,
    }


def _count_orphan_markers_at_top(html: str, max_check_chars: int = 500) -> int:
    """Count orphan markers (empty anchor) in the first N chars of HTML."""
    orphan_pattern = re.compile(
        r'<ac:inline-comment-marker\s+ac:ref="([^"]+)">[\s\u00a0]*</ac:inline-comment-marker>',
        re.IGNORECASE
    )
    
    # Check only first N characters where orphans should be
    top_section = html[:max_check_chars]
    matches = list(orphan_pattern.finditer(top_section))
    return len(matches)


def _count_total_orphan_markers(html: str) -> int:
    """Count all orphan markers in the entire HTML."""
    orphan_pattern = re.compile(
        r'<ac:inline-comment-marker\s+ac:ref="([^"]+)">[\s\u00a0]*</ac:inline-comment-marker>',
        re.IGNORECASE
    )
    return len(orphan_pattern.findall(html))


class OrphanPersistenceTests(unittest.TestCase):
    """Test suite for orphan marker persistence across operations."""

    def test_orphan_marker_extracted_with_force_orphan_flag(self):
        """Verify orphan markers extracted from storage are marked with force_orphan flag."""
        # Storage HTML with one normal marker and one orphan marker
        storage = (
            '<p>Content before.</p>'
            '<ac:inline-comment-marker ac:ref="ref-normal">normal text</ac:inline-comment-marker>'
            '<p>More content.</p>'
            f'<ac:inline-comment-marker ac:ref="ref-orphan">{_ORPHAN_COMMENT_EMPTY_ANCHOR_HTML}</ac:inline-comment-marker>'
            '<p>Content after.</p>'
        )
        
        markers = _extract_inline_markers(storage)
        
        # Find normal and orphan markers
        normal = next((m for m in markers if m["ref"] == "ref-normal"), None)
        orphan = next((m for m in markers if m["ref"] == "ref-orphan"), None)
        
        self.assertIsNotNone(normal, "Normal marker should be extracted")
        self.assertIsNotNone(orphan, "Orphan marker should be extracted")
        
        # Normal marker should NOT have force_orphan flag
        self.assertFalse(normal.get("force_orphan", False), "Normal marker should not have force_orphan")
        
        # Orphan marker SHOULD have force_orphan flag
        self.assertTrue(orphan.get("force_orphan", False), "Orphan marker should have force_orphan flag")

    def test_orphan_markers_injected_at_document_top(self):
        """Verify orphan markers are injected at the document top in first operation."""
        storage = "<p>Initial content.</p>"
        
        # Mix of normal and orphan markers
        markers = [
            _marker(storage, "Initial", "ref-normal"),
            _orphan_marker("ref-orphan-1"),
            _orphan_marker("ref-orphan-2"),
        ]
        
        updated, reanchored, skipped, icons = _inject_inline_markers(
            storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(storage)),
        )
        
        # Check that orphans appear in first 300 chars (at top)
        top_section = updated[:300]
        self.assertIn('ac:ref="ref-orphan-1"', top_section, "Orphan-1 should be in top section")
        self.assertIn('ac:ref="ref-orphan-2"', top_section, "Orphan-2 should be in top section")
        
        # Count orphan markers at top
        orphan_count_at_top = _count_orphan_markers_at_top(updated, 300)
        self.assertEqual(orphan_count_at_top, 2, "Both orphan markers should be at top")

    def test_orphan_markers_stay_at_top_across_content_modification(self):
        """Test that orphan markers stay at top when content is modified in operation 2."""
        # Operation 1: Initial storage with orphan markers injected at top
        initial_storage = (
            '<ac:inline-comment-marker ac:ref="ref-orphan-1">\u00a0</ac:inline-comment-marker>'
            '<ac:inline-comment-marker ac:ref="ref-orphan-2">\u00a0</ac:inline-comment-marker>'
            '<p>Section A: Content that will be modified.</p>'
            '<p>Section B: More content.</p>'
        )
        
        # Operation 2: Modify content (delete/change)
        modified_storage = (
            '<ac:inline-comment-marker ac:ref="ref-orphan-1">\u00a0</ac:inline-comment-marker>'
            '<ac:inline-comment-marker ac:ref="ref-orphan-2">\u00a0</ac:inline-comment-marker>'
            '<p>Section A: Content was COMPLETELY CHANGED.</p>'
            '<p>Section B: Different content now.</p>'
        )
        
        # Extract markers from modified storage (simulates second operation starting)
        markers = _extract_inline_markers(modified_storage)
        orphan_markers = [m for m in markers if bool(m.get("force_orphan"))]
        
        # Verify both orphans are marked with force_orphan
        self.assertEqual(len(orphan_markers), 2, "Both orphans should be detected with force_orphan flag")
        
        # Now re-inject with some content further changes
        re_modified_storage = (
            '<p>Section A: Yet another change.</p>'
            '<p>Section B: And another change.</p>'
        )
        
        # Re-inject should put orphans back at top
        updated, reanchored, skipped, icons = _inject_inline_markers(
            re_modified_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(re_modified_storage)),
        )
        
        # Both orphans should be at top, not scattered in middle
        orphan_count_at_top = _count_orphan_markers_at_top(updated, 500)
        self.assertEqual(orphan_count_at_top, 2, "Orphans should still be at top after re-modification")
        
        # Verify they're in first 250 chars (both marker tags together)
        top_250 = updated[:250]
        self.assertIn('ac:ref="ref-orphan-1"', top_250)
        self.assertIn('ac:ref="ref-orphan-2"', top_250)

    def test_orphan_markers_not_mixed_with_normal_markers(self):
        """Verify orphan markers stay at top, not scattered among normal markers."""
        storage = (
            '<p>Alpha</p>'
            '<p>Beta</p>'
            '<p>Gamma</p>'
        )
        
        # Mix orphan and normal markers - orphans should group at top
        markers = [
            _marker(storage, "Alpha", "ref-normal-1"),
            _orphan_marker("ref-orphan-1"),
            _marker(storage, "Beta", "ref-normal-2"),
            _orphan_marker("ref-orphan-2"),
            _marker(storage, "Gamma", "ref-normal-3"),
        ]
        
        updated, reanchored, skipped, icons = _inject_inline_markers(
            storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(storage)),
        )
        
        # Orphans should appear before normal markers
        orphan1_pos = updated.find('ac:ref="ref-orphan-1"')
        orphan2_pos = updated.find('ac:ref="ref-orphan-2"')
        normal1_pos = updated.find('ac:ref="ref-normal-1"')
        normal2_pos = updated.find('ac:ref="ref-normal-2"')
        normal3_pos = updated.find('ac:ref="ref-normal-3"')
        
        self.assertGreaterEqual(orphan1_pos, 0, "Orphan-1 should exist")
        self.assertGreaterEqual(orphan2_pos, 0, "Orphan-2 should exist")
        self.assertGreaterEqual(normal1_pos, 0, "Normal-1 should exist")
        
        # Orphans should come before normal markers
        self.assertLess(orphan1_pos, normal1_pos, "Orphan-1 should come before Normal-1")
        self.assertLess(orphan2_pos, normal2_pos, "Orphan-2 should come before Normal-2")

    def test_force_orphan_flag_prevents_reanchoring(self):
        """Test that markers with force_orphan flag are routed to batch orphan injection."""
        storage = "<p>Content that will change.</p>"
        
        # Create marker with force_orphan flag set
        marker = _orphan_marker("ref-force-orphan")
        marker["force_orphan"] = True
        
        updated, reanchored, skipped, icons = _inject_inline_markers(
            storage,
            [marker],
            open_ref_ids=set(),
            section_span=(0, len(storage)),
        )
        
        # The orphan should be injected as a batch orphan at top
        self.assertIn('ac:ref="ref-force-orphan"', updated)
        self.assertIn(f'>{_ORPHAN_COMMENT_EMPTY_ANCHOR_HTML}<', updated)
        
        # Verify it's in the first part of the document
        pos = updated.find('ac:ref="ref-force-orphan"')
        self.assertLess(pos, 200, "Force-orphan marker should be near document top")


class OrphanScatteringPreventionTests(unittest.TestCase):
    """Test that orphans DON'T scatter across document when force_orphan is used."""

    def test_multiple_operations_keep_orphans_consolidated(self):
        """Multi-operation scenario: orphans should stay at top across all operations."""
        # Simulate sequential operations with different storage states
        operations = [
            # Op 1: Normal content
            "<p>Heading: Overview</p><p>Content A</p><p>Content B</p>",
            # Op 2: Heading renamed
            "<p>Heading: Introduction</p><p>Content A</p><p>Content B</p>",
            # Op 3: Content A deleted
            "<p>Heading: Introduction</p><p>Content B</p>",
            # Op 4: More content added
            "<p>Heading: Introduction</p><p>Content B</p><p>New Content C</p>",
        ]
        
        # Start with orphaned markers at top
        markers_with_orphans = _extract_inline_markers(
            f'<ac:inline-comment-marker ac:ref="orphan-1">\u00a0</ac:inline-comment-marker>'
            f'<ac:inline-comment-marker ac:ref="orphan-2">\u00a0</ac:inline-comment-marker>'
            f'{operations[0]}'
        )
        
        # Simulate operations
        current_markers = markers_with_orphans
        for i, storage in enumerate(operations[1:], 1):
            updated, _, _, _ = _inject_inline_markers(
                storage,
                current_markers,
                open_ref_ids=set(),
                section_span=(0, len(storage)),
            )
            
            # Extract markers for next operation
            current_markers = _extract_inline_markers(updated)
            
            # Count orphans at top vs elsewhere
            orphan_count_at_top = _count_orphan_markers_at_top(updated, 300)
            total_orphans = _count_total_orphan_markers(updated)
            
            # All orphans should be at top
            self.assertEqual(
                orphan_count_at_top, total_orphans,
                f"Op {i}: All orphans should stay at top, not scatter"
            )
            self.assertGreaterEqual(orphan_count_at_top, 1, f"Op {i}: At least 1 orphan should exist at top")


if __name__ == "__main__":
    unittest.main()
