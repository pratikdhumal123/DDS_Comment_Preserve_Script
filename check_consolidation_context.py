import re

with open(r'C:\Task 3\dds_comment_preserve_solution\output\475405819_20260624T054121Z_reanchor_payload_storage.html', 'r') as f:
    content = f.read()

# Find ALL inline comment markers
orphan_markers = re.finditer(r'<ac:inline-comment-marker ac:ref="([^"]+)">([^<]*)</ac:inline-comment-marker>', content)
matches = list(orphan_markers)

print(f'ORPHAN CONSOLIDATION STATUS')
print('=' * 80)
print(f'Total orphan markers: {len(matches)}')

if matches:
    # Get the first and last marker position
    first_pos = matches[0].start()
    last_pos = matches[-1].end()
    
    # Extract context around markers
    context_start = max(0, first_pos - 200)
    context_end = min(len(content), last_pos + 500)
    
    context = content[context_start:context_end]
    
    print(f'\nContext around all orphan markers:')
    print('-' * 80)
    print(context)
    print('-' * 80)
    
    # Check what's between markers
    print(f'\nMarker spacing analysis:')
    between_first_last = content[first_pos:last_pos]
    
    # Count how many closing/opening tags are between markers
    closing_tags = between_first_last.count('</ac:inline-comment-marker>')
    opening_tags = between_first_last.count('<ac:inline-comment-marker')
    
    print(f'  Span from first to last marker: {last_pos - first_pos} chars')
    print(f'  Number of markers: {len(matches)}')
    print(f'  All markers in single structure: {"YES ✅" if "</p>" not in between_first_last else "NO ⚠️"}')
    
    # Check if they're all in same paragraph
    para_start = content.rfind('<p', 0, first_pos)
    para_end = content.find('</p>', last_pos)
    
    if para_start > 0 and para_end > last_pos:
        para_content = content[para_start:para_end+4]
        print(f'  All markers in same paragraph: YES ✅')
        print(f'  Paragraph length: {len(para_content)} chars')
