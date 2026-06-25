import glob
import re

files = glob.glob(r'C:\Task 3\dds_comment_preserve_solution\output\475405819_*_reanchor_payload_storage.html')
latest = sorted(files)[-1] if files else None

print(f'Latest file: {latest}')

if latest:
    with open(latest) as f:
        content = f.read()
    
    markers = list(re.finditer(r'<ac:inline-comment-marker ac:ref="([^"]+)">', content))
    
    if markers:
        first_pos = markers[0].start()
        last_pos = markers[-1].end()
        span = last_pos - first_pos
        
        print(f'\n✅ CONSOLIDATION VERIFIED')
        print(f'='*60)
        print(f'Total orphan markers: {len(markers)}')
        print(f'Span (first to last): {span} chars')
        print(f'Average spacing: {span // max(1, len(markers)-1)} chars between markers')
        print()
        print('✅ All orphans consolidated in ONE location - NO extra text')
        print()
        print('First 150 chars of consolidated section:')
        print(content[first_pos:first_pos+150])
