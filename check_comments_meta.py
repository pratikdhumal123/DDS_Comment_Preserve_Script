import glob
import json
import re

# Check what markers are in the comments_after file
files = glob.glob(r'C:\Task 3\dds_comment_preserve_solution\output\475405819_*_comments_after.json')
latest = sorted(files)[-1] if files else None

if latest:
    print(f'Checking: {latest}')
    with open(latest) as f:
        comments = json.load(f)
    
    print(f'\nTotal comments: {len(comments)}')
    print('\nComment refs and their anchors:')
    for c in comments:
        ref = c.get('id')
        body = c.get('body', {}).get('storage', {}).get('value', '')
        # Extract marker ref if exists
        marker_match = re.search(r'<ac:inline-comment-marker ac:ref="([^"]+)"', body)
        if marker_match:
            marker_ref = marker_match.group(1)
            print(f'{ref}: Marker ref = {marker_ref}')
        else:
            print(f'{ref}: No marker ref in body')
