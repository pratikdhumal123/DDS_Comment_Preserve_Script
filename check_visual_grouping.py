import re

# Latest file from previous test
with open(r'C:\Task 3\dds_comment_preserve_solution\output\475405819_20260624T054121Z_reanchor_payload_storage.html', 'r') as f:
    content = f.read()

# Find the orphan group marker
if '<strong>Orphaned Comments:</strong>' in content:
    print("✅ VISUAL GROUPING HEADER FOUND!")
    print("=" * 80)
    # Find position and context
    pos = content.find('<strong>Orphaned Comments:</strong>')
    context_start = max(0, pos - 100)
    context_end = min(len(content), pos + 1000)
    
    context = content[context_start:context_end]
    print("\nContext around orphaned comments header:")
    print("-" * 80)
    print(context)
    print("-" * 80)
else:
    print("⚠️  NO VISUAL GROUPING HEADER FOUND")
    print("=" * 80)
    # Check if markers exist at all
    if '<ac:inline-comment-marker' in content:
        print("Orphan markers still exist but no grouping header.")
        # Find first marker
        pos = content.find('<ac:inline-comment-marker')
        context_start = max(0, pos - 100)
        context_end = min(len(content), pos + 300)
        context = content[context_start:context_end]
        print("\nFirst marker context:")
        print("-" * 80)
        print(context)
        print("-" * 80)
    else:
        print("NO MARKERS FOUND AT ALL")
