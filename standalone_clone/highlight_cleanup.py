#!/usr/bin/env python3
"""
Highlight Cleanup Script
Removes stale/orphaned highlight data from Confluence page content-properties.
Designed to run after auto-clear timeout to clean up any lingering JSON state.
"""

import argparse
import sys
import os

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)


def cleanup_highlights(page_id: str, base_url: str, username: str, api_token: str, project_root: str = None):
    """
    Remove highlight-related content-properties from a Confluence page.
    
    Args:
        page_id: Confluence page ID
        base_url: Confluence base URL
        username: Confluence username
        api_token: Confluence API token
        project_root: Optional project root for relative imports
    """
    # Add project root to path if provided
    if project_root and project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    try:
        from confluence_client import ConfluenceClient
    except ImportError:
        print(f"ERROR: Could not import ConfluenceClient. Check PYTHONPATH or --project-root.")
        return False
    
    try:
        # Create client with explicit credentials
        # (ConfluenceClient normally reads from config, but we override here)
        client = ConfluenceClient.__new__(ConfluenceClient)
        client.base_url = base_url.rstrip("/") + "/rest/api"
        client.base_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Build auth strategies similar to ConfluenceClient.__init__
        client.auth_strategies = [{
            "name": "bearer",
            "headers": {"Authorization": f"Bearer {api_token}"},
            "auth": None
        }]
        client.network_retry_attempts = 3
        client.network_retry_backoff_seconds = 1.5
        
        # List of highlight-related property keys to remove
        highlight_keys = [
            "docAsCode.diffHighlights",
            "docAsCode.highlightState",
            "docAsCode.pendingHighlights",
        ]
        
        print(f"Cleaning highlights for page {page_id}...")
        
        removed_count = 0
        failed_count = 0
        
        for key in highlight_keys:
            try:
                # Try to delete the content property via REST API
                url = f"{client.base_url}/content/{page_id}/property/{key}"
                result = client._request_json(
                    "DELETE",
                    url,
                    f"delete page property '{key}' for {page_id}"
                )
                if result or result is None:  # DELETE returns None on success
                    print(f"  [OK] Removed: {key}")
                    removed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                # Property might not exist (404), which is fine - just count any other errors
                error_str = str(e).lower()
                if "404" in error_str or "not found" in error_str:
                    print(f"  [INFO] {key}: Not found (already clean)")
                    removed_count += 1
                else:
                    print(f"  [WARN] {key}: {str(e)[:100]}")
                    failed_count += 1
        
        print(f"\nCleanup complete: {removed_count} cleaned, {failed_count} errors.")
        return failed_count == 0
        
    except Exception as e:
        print(f"ERROR during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Remove stale highlight data from Confluence page properties"
    )
    parser.add_argument("page_id", help="Confluence page ID")
    parser.add_argument("--base-url", required=True, help="Confluence base URL")
    parser.add_argument("--username", required=True, help="Confluence username")
    parser.add_argument("--api-token", required=True, help="Confluence API token")
    parser.add_argument("--project-root", help="Optional project root for imports")
    
    args = parser.parse_args()
    
    success = cleanup_highlights(
        args.page_id,
        args.base_url,
        args.username,
        args.api_token,
        args.project_root
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
