import re
import os

os.chdir(r'C:\Task 3\dds_comment_preserve_solution\output')

with open('475405819_20260624T054121Z_reanchor_payload_storage.html', 'r') as f:
    content = f.read()

# Find ALL inline comment markers
orphan_markers = re.finditer(r'<ac:inline-comment-marker ac:ref="([^"]+)">([^<]*)</ac:inline-comment-marker>', content)
matches = list(orphan_markers)

print(f'Total markers in file: {len(matches)}')
print('=' * 80)

for i, m in enumerate(matches[:15]):
    ref = m.group(1)
    anchor = m.group(2)
    pos = m.start()
    print(f'{i+1}. Position: {pos}')
    print(f'   Ref: {ref}')
    print(f'   Anchor: {repr(anchor)}')
    print(f'   Is orphan (empty anchor): {anchor == "\\u00a0" or anchor.strip() == ""}')
    print()

print('=' * 80)
# Calculate gaps between consecutive markers
if len(matches) > 1:
    gaps = []
    positions = [m.start() for m in matches]
    for j in range(1, len(positions)):
        gap = positions[j] - positions[j-1]
        gaps.append(gap)
    
    print(f"Gap statistics:")
    print(f"  Total gaps: {len(gaps)}")
    print(f"  Min gap: {min(gaps)} chars")
    print(f"  Max gap: {max(gaps)} chars")
    print(f"  Avg gap: {sum(gaps) / len(gaps):.0f} chars")
    
    # Count small vs large gaps
    small_gaps = [g for g in gaps if g < 200]
    large_gaps = [g for g in gaps if g >= 200]
    
    print(f"  Small gaps (<200): {len(small_gaps)}")
    print(f"  Large gaps (>=200): {len(large_gaps)}")
    
    if len(small_gaps) == len(gaps):
        print("\n✅ ALL markers are TIGHTLY GROUPED (within 200 chars)")
    elif len(large_gaps) > 0:
        print(f"\n⚠️  Markers are SEPARATED into {len(large_gaps) + 1} groups")

print('=' * 80)
print(f"\nFirst 1000 chars of content:")
print(content[:1000])
