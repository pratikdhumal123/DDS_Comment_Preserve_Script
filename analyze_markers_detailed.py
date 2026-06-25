import glob
import re

files = glob.glob(r'C:\Task 3\dds_comment_preserve_solution\output\475405819_*_reanchor_payload_storage.html')
latest = sorted(files)[-1] if files else None

if latest:
    with open(latest) as f:
        content = f.read()
    
    matches = list(re.finditer(r'<ac:inline-comment-marker ac:ref="([^"]+)">', content))
    
    with open(r'C:\Task 3\dds_comment_preserve_solution\marker_analysis.txt', 'w') as out:
        out.write(f'Total markers: {len(matches)}\n')
        out.write(f'\nMarker Analysis:\n')
        out.write('='*60 + '\n')
        
        for i, m in enumerate(matches):
            pos = m.start()
            ref = m.group(1)
            out.write(f'{i+1}. Position {pos} - Ref: {ref}\n')
            
            if i > 0:
                prev_end = matches[i-1].end()
                gap = pos - prev_end
                out.write(f'   Gap from previous: {gap} chars\n')
        
        # Check if markers at document start
        out.write(f'\n\nFirst marker is at position: {matches[0].start()}\n')
        out.write(f'\nContext around first marker (200 chars before):\n')
        ctx_start = max(0, matches[0].start() - 200)
        out.write(content[ctx_start:matches[0].start() + 100])
        
    print('Analysis written to marker_analysis.txt')
