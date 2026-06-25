"""Check if orphan markers are grouped in one space or separated."""
import re

# Read the reanchor payload
with open('output/475405819_20260624T054121Z_reanchor_payload_storage.html', 'r') as f:
    content = f.read()

# Get first 3000 chars (where orphans should be)
top_section = content[:3000]

# Find all orphan marker groups
orphan_markers = re.findall(r'<ac:inline-comment-marker ac:ref="([^"]+)">[\s\u00a0]*</ac:inline-comment-marker>', top_section)

print("=" * 70)
print("ORPHAN MARKER CONSOLIDATION CHECK")
print("=" * 70)
print(f"\nTotal Orphan Markers: {len(orphan_markers)}")
for i, ref in enumerate(orphan_markers, 1):
    print(f"  {i}. Ref: {ref}")

if len(orphan_markers) > 1:
    # Find exact positions
    all_matches = list(re.finditer(r'<ac:inline-comment-marker ac:ref="[^"]+">[^<]*</ac:inline-comment-marker>', top_section))
    
    print(f"\nMarker Positions:")
    for i, match in enumerate(all_matches):
        print(f"  Marker {i+1}: position {match.start()}-{match.end()}")
    
    # Calculate gaps between consecutive markers
    gaps = []
    for i in range(len(all_matches) - 1):
        gap = all_matches[i+1].start() - all_matches[i].end()
        gaps.append(gap)
        print(f"    Gap between marker {i+1} and {i+2}: {gap} chars")
    
    print(f"\nGap Analysis:")
    if gaps:
        max_gap = max(gaps)
        min_gap = min(gaps)
        print(f"  Max gap: {max_gap} chars")
        print(f"  Min gap: {min_gap} chars")
        
        if max_gap < 5:  # Almost touching = grouped in one space
            print(f"  ✅ All markers are IN ONE CONSOLIDATED SPACE!")
        elif max_gap < 100:  # Small gap = still together
            print(f"  ⚠️  Markers are close but may have small gap between them")
        else:
            print(f"  ❌ Markers are SEPARATED in different spaces")

print(f"\n" + "=" * 70)
print("RAW HTML (first 600 chars):")
print("=" * 70)
print(top_section[:600])
print("=" * 70)
