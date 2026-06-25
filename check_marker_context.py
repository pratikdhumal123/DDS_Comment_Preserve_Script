import glob
import re

# Get the latest output
files = glob.glob(r'C:\Task 3\dds_comment_preserve_solution\output\475405819_*_reanchor_payload_storage.html')
latest = sorted(files)[-1] if files else None

if latest:
    with open(latest) as f:
        content = f.read()
    
    # Find all markers
    matches = list(re.finditer(r'<ac:inline-comment-marker ac:ref="([^"]+)">(.*?)</ac:inline-comment-marker>', content))
    
    print(f'Total markers: {len(matches)}')
    print('\nMarker positions and context:')
    
    for i, m in enumerate(matches):
        ref = m.group(1)
        anchor = m.group(2)
        pos = m.start()
        
        # Get context before marker
        context_start = max(0, pos - 80)
        context_before = content[context_start:pos].replace('\n', ' ')[-40:]
        
        print(f'\n{i+1}. Position {pos}')
        print(f'   Ref: {ref}')
        print(f'   Anchor: {repr(anchor)}')
        print(f'   Context: ...{context_before}<marker>')
