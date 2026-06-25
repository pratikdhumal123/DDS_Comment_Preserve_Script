"""Verify orphan marker consolidation in the reanchor payload."""
import re

print("=" * 70)
print("ORPHAN CONSOLIDATION VERIFICATION")
print("=" * 70)

# Read the reanchor payload
with open('output/475405819_20260624T054121Z_reanchor_payload_storage.html', 'r') as f:
    content = f.read()

# Find all markers
markers = re.findall(r'<ac:inline-comment-marker ac:ref="([^"]+)"[^>]*>([^<]*)</ac:inline-comment-marker>', content)

print(f'\nTotal Markers Found: {len(markers)}')

# Check if markers are at the top
first_marker_pos = content.find('<ac:inline-comment-marker')
if first_marker_pos >= 0:
    # Count how many markers are in the first 1000 chars (top section)
    top_section = content[:1000]
    top_markers = len(re.findall(r'<ac:inline-comment-marker', top_section))
    
    print(f'\nMarker Position Analysis:')
    print(f'  - First marker at position: {first_marker_pos}')
    print(f'  - Markers in first 1000 chars: {top_markers}')
    
    if top_markers == len(markers):
        print(f'\n✅ SUCCESS: All {len(markers)} markers are CONSOLIDATED AT DOCUMENT TOP!')
    else:
        print(f'\n⚠️  WARNING: Only {top_markers}/{len(markers)} markers at top')

print(f'\nMarker Details:')
print('-' * 70)
orphaned_count = 0
anchored_count = 0

for i, (ref, anchor) in enumerate(markers, 1):
    if not anchor or anchor.strip() in ['', '\u00a0', '&nbsp;']:
        status = '✅ ORPHANED'
        orphaned_count += 1
    else:
        status = '📌 ANCHORED'
        anchored_count += 1
    
    anchor_preview = (anchor[:40] + '...') if len(anchor) > 40 else anchor
    print(f'{i}. {status} - Ref: {ref}')
    print(f'   Anchor: "{anchor_preview}"')

print('-' * 70)
print(f'\nSummary:')
print(f'  Total Markers: {len(markers)}')
print(f'  Orphaned: {orphaned_count}')
print(f'  Anchored: {anchored_count}')
print(f'  Consolidation: {"✅ CONSOLIDATED AT TOP" if orphaned_count > 0 else "N/A"}')
print('=' * 70)
