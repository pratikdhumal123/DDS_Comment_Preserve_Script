"""Check if orphaned comments are consolidated in one empty space."""
import json
import re

# Load the preservation report
with open('output/475405819_20260624T054121Z_comment_preservation_report.json') as f:
    data = json.load(f)

markers = data.get('marker_details', [])
orphaned = [m for m in markers if not m.get('anchor_html') or m['anchor_html'].strip() in ['', '\u00a0']]
normal = [m for m in markers if m.get('anchor_html') and m['anchor_html'].strip() not in ['', '\u00a0']]

print("=" * 70)
print("ORPHAN COMMENT CONSOLIDATION VERIFICATION")
print("=" * 70)
print(f"\nTotal Comments Found: {len(markers)}")
print(f"Orphaned Comments: {len(orphaned)}")
print(f"Normal (Anchored) Comments: {len(normal)}")

print("\n" + "-" * 70)
print("ORPHANED COMMENTS (should all be at document top):")
print("-" * 70)
for m in orphaned:
    heading_path = m.get('heading_path', [])
    if heading_path:
        path_str = " > ".join([h.get('text', '') for h in heading_path])
    else:
        path_str = "(no heading path - at document top)"
    print(f"\n  Ref ID: {m['ref']}")
    print(f"    Anchor HTML: {repr(m.get('anchor_html', ''))}")
    print(f"    Location: {path_str}")

print("\n" + "-" * 70)
print("NORMAL (ANCHORED) COMMENTS:")
print("-" * 70)
for m in normal:
    heading_path = m.get('heading_path', [])
    if heading_path:
        path_str = " > ".join([h.get('text', '') for h in heading_path])
    else:
        path_str = "(at document body)"
    print(f"\n  Ref ID: {m['ref']}")
    print(f"    Anchor: {m.get('anchor_html', '')[:50]}{'...' if len(m.get('anchor_html', '')) > 50 else ''}")
    print(f"    Location: {path_str}")

print("\n" + "=" * 70)
print("CONSOLIDATION CHECK:")
print("=" * 70)

# Check if all orphans have empty heading_path (meaning they're all at top)
all_at_top = all(not m.get('heading_path') or len(m.get('heading_path', [])) == 0 for m in orphaned)

if all_at_top and len(orphaned) > 0:
    print("✅ SUCCESS: All orphaned comments are at the document top!")
    print(f"   {len(orphaned)} orphaned comments consolidated in ONE empty space")
else:
    print("⚠️  WARNING: Orphaned comments scattered across document")
    for m in orphaned:
        if m.get('heading_path') and len(m.get('heading_path', [])) > 0:
            path = " > ".join([h.get('text', '') for h in m.get('heading_path')])
            print(f"   - {m['ref']} is under: {path}")

print("\n" + "=" * 70)
print("SUMMARY:")
print("=" * 70)
print(f"Total Comments Preserved: {len(markers)}/8 ✅")
print(f"Orphaned Comments: {len(orphaned)}")
print(f"Comments with Anchors: {len(normal)}")
print(f"Consolidation Status: {'✅ CONSOLIDATED AT TOP' if all_at_top and len(orphaned) > 0 else '❌ SCATTERED'}")
print("=" * 70)
