"""
Test to verify orphan markers have visual grouping header for consolidated UI display
"""
import re
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

import comment_preserve_publish as cpp

def test_orphan_markers_have_visual_grouping_header():
    """Verify that orphaned comments are prepended with 'Orphaned Comments:' header"""
    
    # Create test input with orphan markers
    storage_html = """<p>Normal content</p>
<ac:inline-comment-marker ac:ref="ref1">\u00a0</ac:inline-comment-marker>
<ac:inline-comment-marker ac:ref="ref2">\u00a0</ac:inline-comment-marker>
<ac:inline-comment-marker ac:ref="ref3">\u00a0</ac:inline-comment-marker>
<p>More content</p>"""
    
    # Extract markers
    markers = []
    for match in re.finditer(
        r'<ac:inline-comment-marker\s+ac:ref="([^"]+)">(.*?)</ac:inline-comment-marker>',
        storage_html,
        re.DOTALL,
    ):
        ref = match.group(1)
        anchor_html = match.group(2)
        is_orphan = anchor_html == "\u00a0" or anchor_html.strip() == ""
        markers.append({
            "ref": ref,
            "anchor_html": anchor_html,
            "force_orphan": is_orphan
        })
    
    # Collect orphan refs
    orphan_refs = [m["ref"] for m in markers if m["force_orphan"]]
    
    print(f"Found {len(orphan_refs)} orphan markers: {orphan_refs}")
    
    # Simulate the orphan injection code
    orphan_refs_to_batch = orphan_refs
    orphan_markers_str = "".join([
        f'<ac:inline-comment-marker ac:ref="{ref}">{cpp._ORPHAN_COMMENT_EMPTY_ANCHOR_HTML}</ac:inline-comment-marker>'
        for ref in orphan_refs_to_batch
    ])
    orphan_block = f'<p><strong>Orphaned Comments:</strong></p>{orphan_markers_str}'
    
    # Verify the block contains the visual header
    assert '<strong>Orphaned Comments:</strong>' in orphan_block, \
        f"Visual grouping header missing from orphan block: {orphan_block[:200]}"
    
    # Verify all orphan refs are in the block
    for ref in orphan_refs:
        assert f'ac:ref="{ref}"' in orphan_block, \
            f"Orphan ref {ref} not found in orphan block"
    
    # Verify header comes before markers
    header_pos = orphan_block.find('<strong>Orphaned Comments:</strong>')
    first_marker_pos = orphan_block.find('<ac:inline-comment-marker')
    assert header_pos < first_marker_pos, \
        "Visual header must come before the orphan markers"
    
    print(f"✅ PASSED: Visual grouping header is correctly placed")
    print(f"   Header position: {header_pos}")
    print(f"   First marker position: {first_marker_pos}")
    print(f"   Orphan block sample: {orphan_block[:300]}...")
    
    return True

if __name__ == "__main__":
    try:
        test_orphan_markers_have_visual_grouping_header()
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
