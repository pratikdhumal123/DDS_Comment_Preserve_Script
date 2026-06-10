"""
Confluence API Client
A simple client to interact with Confluence REST API
"""

import requests
import sys
import os
import time
import config as cfg

BASE_URL = cfg.BASE_URL
SPACE_KEY = cfg.SPACE_KEY
API_BASE = cfg.API_BASE
DEFAULT_TREE_PARENT_ID = str(getattr(cfg, "DEFAULT_TREE_PARENT_ID", "381453022"))
# 381453788

class ConfluenceClient:
    def __init__(self):
        self.base_url = API_BASE
        self.base_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.auth_method = getattr(cfg, "AUTH_METHOD", "auto").lower()
        self.access_token = getattr(cfg, "ACCESS_TOKEN", "")
        self.username = getattr(cfg, "USERNAME", "")
        self.password = getattr(cfg, "PASSWORD", "")
        self.session_cookie = getattr(cfg, "SESSION_COOKIE", "")
        self.network_retry_attempts = max(1, int(getattr(cfg, "NETWORK_RETRY_ATTEMPTS", 3)))
        self.network_retry_backoff_seconds = max(0.0, float(getattr(cfg, "NETWORK_RETRY_BACKOFF_SECONDS", 1.5)))
        self.auth_strategies = self._build_auth_strategies()
        self._page_move_supported = None

    def _build_auth_strategies(self):
        strategies = []

        if self.auth_method in ("auto", "cookie") and self.session_cookie:
            strategies.append({
                "name": "cookie",
                "headers": {"Cookie": self.session_cookie},
                "auth": None
            })

        if self.auth_method in ("auto", "bearer") and self.access_token:
            strategies.append({
                "name": "bearer",
                "headers": {"Authorization": f"Bearer {self.access_token}"},
                "auth": None
            })

        if self.auth_method in ("auto", "basic") and self.username and self.password:
            strategies.append({
                "name": "basic",
                "headers": {},
                "auth": (self.username, self.password)
            })

        if not strategies:
            strategies.append({"name": "none", "headers": {}, "auth": None})

        return strategies

    def _looks_like_auth_redirect(self, response):
        content_type = (response.headers.get("content-type") or "").lower()
        location = (response.headers.get("location") or "").lower()
        body_preview = (response.text or "")[:400].lower()

        if response.status_code in (301, 302, 303, 307, 308):
            return True

        if "text/html" in content_type and (
            "final_redirect" in body_preview
            or "duo" in body_preview
            or "login" in body_preview
            or "saml" in body_preview
            or "check?" in location
        ):
            return True

        return False

    def _request_json(self, method, url, action, **kwargs):
        last_response = None
        last_exception = None
        extra_headers = kwargs.pop("headers", {})

        for index, strategy in enumerate(self.auth_strategies):
            headers = dict(self.base_headers)
            headers.update(strategy["headers"])
            headers.update(extra_headers)

            response = None
            for attempt in range(1, self.network_retry_attempts + 1):
                try:
                    response = requests.request(
                        method,
                        url,
                        headers=headers,
                        auth=strategy["auth"],
                        timeout=30,
                        allow_redirects=False,
                        **kwargs
                    )
                    last_response = response
                    last_exception = None
                    break
                except requests.exceptions.RequestException as exc:
                    last_exception = exc
                    if attempt < self.network_retry_attempts:
                        wait_seconds = self.network_retry_backoff_seconds * attempt
                        print(
                            f"Network error while trying to {action} with auth '{strategy['name']}' "
                            f"(attempt {attempt}/{self.network_retry_attempts}): {exc}. "
                            f"Retrying in {wait_seconds:.1f}s..."
                        )
                        if wait_seconds > 0:
                            time.sleep(wait_seconds)
                        continue

                    print(
                        f"Network error while trying to {action} with auth '{strategy['name']}' "
                        f"after {self.network_retry_attempts} attempts: {exc}"
                    )

            if response is None:
                continue

            if self._looks_like_auth_redirect(response) and index < len(self.auth_strategies) - 1:
                print(f"Auth method '{strategy['name']}' redirected to login/SSO. Trying next method...")
                continue

            return self._handle_response(response, action, strategy["name"])

        if last_response is not None:
            return self._handle_response(last_response, action, self.auth_strategies[-1]["name"])

        if last_exception is not None:
            print(f"Error while trying to {action}: {last_exception}")
        return None

    def _handle_response(self, response, action, auth_used):
        """Return JSON payload or print actionable diagnostics"""
        content_type = (response.headers.get("content-type") or "").lower()

        if response.status_code >= 400:
            print(f"Error while trying to {action}: HTTP {response.status_code}")
            if "text/html" in content_type:
                self._print_auth_hint(response, auth_used)
            else:
                print(response.text[:500])
            return None

        if "application/json" not in content_type:
            print(f"Error while trying to {action}: Expected JSON but got '{content_type or 'unknown'}'")
            self._print_auth_hint(response, auth_used)
            return None

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Error while trying to {action}: response was not valid JSON")
            print(f"Response preview: {response.text[:200]}")
            return None

    def _print_auth_hint(self, response, auth_used):
        """Explain likely authentication issue when API returns HTML/login page"""
        preview = (response.text or "")[:200].replace("\n", " ").strip()
        print("It looks like Confluence returned an HTML page instead of API JSON.")
        print("This usually means authentication failed or SSO redirected to login.")
        print(f"Auth tried: {auth_used}")
        if auth_used == "bearer":
            print("Bearer token was sent, but gateway redirected to login/SSO.")
            print("Verify token scope/validity and ask admin to allow token auth for REST API.")
        elif auth_used == "cookie":
            print("Session cookie was sent, but gateway still redirected to login/SSO.")
            print("Refresh browser session cookie or ask admin to allow REST API access without interactive login.")
        else:
            print("Set AUTH_METHOD in config.py to 'auto', 'cookie', 'bearer', or 'basic'.")
            print("For basic auth, set USERNAME and PASSWORD in config.py. For cookie auth, set SESSION_COOKIE.")
        if preview:
            print(f"Response preview: {preview}")
    
    def get_page(self, page_id):
        """Get a page by its ID"""
        url = f"{self.base_url}/content/{page_id}?expand=body.storage,version,ancestors"
        return self._request_json("GET", url, f"get page {page_id}")
    
    def list_pages(self, space_key=None, limit=25):
        """List pages in a space"""
        if space_key is None:
            space_key = SPACE_KEY
        
        url = f"{self.base_url}/content"
        params = {
            "spaceKey": space_key,
            "limit": limit,
            "expand": "version,space"
        }
        
        return self._request_json("GET", url, f"list pages in space {space_key}", params=params)
    
    def create_page(self, title, content, parent_id=None, space_key=None):
        """Create a new page"""
        if space_key is None:
            space_key = SPACE_KEY
        
        url = f"{self.base_url}/content"
        
        data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        
        if parent_id:
            data["ancestors"] = [{"id": parent_id}]
        
        return self._request_json("POST", url, f"create page '{title}'", json=data)
    
    def update_page(self, page_id, new_content, new_title=None, parent_id=None):
        """Update an existing page"""
        # First get the current page to get version info
        page = self.get_page(page_id)
        if not page:
            return None
        
        current_version = page["version"]["number"]
        current_title = page["title"]
        current_content = page.get("body", {}).get("storage", {}).get("value", "")
        target_title = new_title if new_title else current_title
        current_parent_id = None
        ancestors = page.get("ancestors", [])
        if ancestors:
            current_parent_id = str(ancestors[-1].get("id"))

        requested_parent_id = str(parent_id) if parent_id is not None else None
        parent_matches = requested_parent_id is None or current_parent_id == requested_parent_id

        if (
            current_content == new_content
            and current_title == target_title
            and parent_matches
        ):
            unchanged_page = dict(page)
            unchanged_page["_unchanged"] = True
            return unchanged_page
        
        url = f"{self.base_url}/content/{page_id}"
        
        data = {
            "version": {"number": current_version + 1},
            "title": target_title,
            "type": "page",
            "body": {
                "storage": {
                    "value": new_content,
                    "representation": "storage"
                }
            }
        }

        if parent_id:
            data["ancestors"] = [{"id": str(parent_id)}]
        
        return self._request_json("PUT", url, f"update page {page_id}", json=data)

    def _update_page_with_version(self, page_id, new_content, current_version, new_title=None, parent_id=None):
        """Update an existing page using a known version number (faster path)."""
        url = f"{self.base_url}/content/{page_id}"

        title = new_title if new_title else f"Page {page_id}"
        data = {
            "version": {"number": int(current_version) + 1},
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": new_content,
                    "representation": "storage"
                }
            }
        }

        if parent_id:
            data["ancestors"] = [{"id": str(parent_id)}]

        headers = dict(self.base_headers)
        last_response = None
        for strategy in self.auth_strategies:
            headers_for_request = dict(headers)
            headers_for_request.update(strategy["headers"])
            response = requests.request(
                "PUT",
                url,
                headers=headers_for_request,
                auth=strategy["auth"],
                timeout=120,
                allow_redirects=False,
                json=data,
            )
            last_response = response

            if response.status_code == 409:
                return None

            if self._looks_like_auth_redirect(response):
                continue

            return self._handle_response(response, f"fast update page {page_id}", strategy["name"])

        if last_response is not None:
            if last_response.status_code == 409:
                return None
            return self._handle_response(last_response, f"fast update page {page_id}", self.auth_strategies[-1]["name"])
        return None
    
    def search(self, query, limit=25):
        """Search for content"""
        url = f"{self.base_url}/content/search"
        params = {
            "cql": f'space={SPACE_KEY} AND text~"{query}"',
            "limit": limit
        }
        
        return self._request_json("GET", url, f"search for '{query}'", params=params)
    
    def get_page_by_title(self, title, space_key=None):
        """Check if a page with given title exists in space"""
        if space_key is None:
            space_key = SPACE_KEY
        
        url = f"{self.base_url}/content"
        params = {
            "spaceKey": space_key,
            "title": title,
            "expand": "version"
        }
        
        payload = self._request_json("GET", url, f"find page titled '{title}'", params=params)
        if payload is None:
            return None

        results = payload.get('results', [])
        if results:
            return results[0]  # Return first match
        return None

    def get_child_page_by_title(self, parent_id, title):
        """Find a child page by title under a specific parent page."""
        url = f"{self.base_url}/content/{parent_id}/child/page"
        start = 0
        limit = 100

        while True:
            params = {
                "expand": "version",
                "limit": limit,
                "start": start,
            }
            payload = self._request_json(
                "GET",
                url,
                f"find child page titled '{title}' under parent {parent_id}",
                params=params,
            )

            if payload is None:
                return None

            results = payload.get("results", [])
            for page in results:
                if page.get("title") == title:
                    return page

            if len(results) < limit:
                break
            start += limit

        return None

    def list_child_pages(self, parent_id, limit=200):
        """List all direct child pages under a parent page."""
        url = f"{self.base_url}/content/{parent_id}/child/page"
        start = 0
        results = []

        while True:
            params = {
                "expand": "version",
                "limit": limit,
                "start": start,
            }
            payload = self._request_json(
                "GET",
                url,
                f"list child pages under parent {parent_id}",
                params=params,
            )
            if payload is None:
                return results

            page_results = payload.get("results", [])
            results.extend(page_results)

            if len(page_results) < limit:
                break
            start += limit

        return results

    def move_page(self, page_id, target_page_id, position="after"):
        """Move a page relative to another page in the tree."""
        allowed_positions = {"before", "after", "append"}
        if position not in allowed_positions:
            print(f"Error: invalid move position '{position}'. Use one of: {', '.join(sorted(allowed_positions))}")
            return None

        if self._page_move_supported is False:
            return {"status": "unsupported"}

        experimental_base = self.base_url.replace("/rest/api", "/rest/experimental") if "/rest/api" in self.base_url else f"{self.base_url}/experimental"

        candidates = [
            ("POST", f"{self.base_url}/content/{page_id}/move/{position}/{target_page_id}", {}),
            ("PUT", f"{self.base_url}/content/{page_id}/move/{position}/{target_page_id}", {}),
            ("POST", f"{self.base_url}/content/{page_id}/move/{position}", {"params": {"targetId": str(target_page_id)}}),
            ("PUT", f"{self.base_url}/content/{page_id}/move/{position}", {"params": {"targetId": str(target_page_id)}}),
            ("POST", f"{experimental_base}/content/{page_id}/move/{position}/{target_page_id}", {}),
            ("PUT", f"{experimental_base}/content/{page_id}/move/{position}/{target_page_id}", {}),
            ("POST", f"{experimental_base}/content/{page_id}/move/{position}", {"params": {"targetId": str(target_page_id)}}),
            ("PUT", f"{experimental_base}/content/{page_id}/move/{position}", {"params": {"targetId": str(target_page_id)}}),
        ]

        saw_404 = False
        last_error = None

        for method, url, extra_kwargs in candidates:
            for index, strategy in enumerate(self.auth_strategies):
                headers = dict(self.base_headers)
                headers.update(strategy["headers"])

                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    auth=strategy["auth"],
                    timeout=30,
                    allow_redirects=False,
                    **extra_kwargs,
                )

                if self._looks_like_auth_redirect(response) and index < len(self.auth_strategies) - 1:
                    continue

                if response.status_code in (200, 201):
                    self._page_move_supported = True
                    try:
                        return response.json()
                    except requests.exceptions.JSONDecodeError:
                        return {"status": response.status_code}

                if response.status_code == 404:
                    saw_404 = True
                    continue

                if response.status_code in (401, 403):
                    self._page_move_supported = False
                    return {"status": "forbidden"}

                last_error = response

        if saw_404 and last_error is None:
            self._page_move_supported = False
            return {"status": "unsupported"}

        if last_error is not None:
            print(f"Error while trying to move page {page_id} {position} {target_page_id}: HTTP {last_error.status_code}")
            preview = (last_error.text or "")[:500]
            if preview:
                print(preview)
        return None

    def print_page_tree(self, root_page_id, max_depth=8):
        """Print hierarchical page tree from a root page ID."""
        root_page = self.get_page(root_page_id)
        if not root_page:
            print(f"Root page not found: {root_page_id}")
            return

        root_url = f"{BASE_URL}{root_page['_links']['webui']}"
        print(f"📄 Root: {root_page.get('title')} (ID: {root_page_id})")
        print(f"   {root_url}")

        def walk(parent_id, depth):
            if depth > max_depth:
                return
            children = self.list_child_pages(parent_id)
            for child in children:
                child_id = child.get("id")
                title = child.get("title")
                child_url = f"{BASE_URL}{child['_links']['webui']}"
                indent = "  " * depth
                print(f"{indent}└─ {title} (ID: {child_id})")
                print(f"{indent}   {child_url}")
                walk(child_id, depth + 1)

        walk(root_page_id, 1)
    
    def create_or_update_page(
        self,
        title,
        content,
        parent_id=None,
        space_key=None,
        existing_page=None,
        fast_update=False,
        allow_space_fallback=True,
    ):
        """Create a page or update existing page with same title in the space."""
        if space_key is None:
            space_key = SPACE_KEY

        page_update_retries = max(2, int(getattr(cfg, "PAGE_UPDATE_RETRIES", 5)))
        page_create_retries = max(1, int(getattr(cfg, "PAGE_CREATE_RETRIES", 3)))
        page_retry_backoff_seconds = max(0.0, float(getattr(cfg, "PAGE_RETRY_BACKOFF_SECONDS", 1.5)))

        if existing_page is None:
            if parent_id:
                existing_page = self.get_child_page_by_title(parent_id, title)
                if not existing_page and allow_space_fallback:
                    # Some Confluence deployments enforce space-wide unique titles.
                    # In that case, locate existing page in space and move/update it.
                    existing_page = self.get_page_by_title(title, space_key)
            else:
                existing_page = self.get_page_by_title(title, space_key)

        # Guard against self-parent loops (same page chosen as both target page and parent).
        # This can happen when a child heading has the same title as its parent heading.
        if existing_page and parent_id is not None:
            existing_page_id = str(existing_page.get("id")) if isinstance(existing_page, dict) else None
            if existing_page_id and existing_page_id == str(parent_id):
                print(
                    f"Skipping self-parent update for title '{title}' "
                    f"(page id {existing_page_id} equals parent id {parent_id}); creating new child page instead."
                )
                existing_page = None

        if existing_page:
            if fast_update:
                version_info = existing_page.get("version", {}) if isinstance(existing_page, dict) else {}
                current_version = version_info.get("number")
                if current_version is not None:
                    updated_page = self._update_page_with_version(
                        existing_page["id"],
                        content,
                        current_version,
                        new_title=title,
                        parent_id=parent_id,
                    )
                    if updated_page:
                        return (updated_page, "updated")

            updated_page = None
            for attempt in range(page_update_retries):
                updated_page = self.update_page(
                    existing_page["id"],
                    content,
                    new_title=title,
                    parent_id=parent_id,
                )
                if updated_page:
                    break
                if attempt < page_update_retries - 1:
                    wait_seconds = page_retry_backoff_seconds * (attempt + 1)
                    print(
                        f"Retrying update for page '{title}' after conflict/transient failure "
                        f"(attempt {attempt + 2}/{page_update_retries}) in {wait_seconds:.1f}s..."
                    )
                    if wait_seconds > 0:
                        time.sleep(wait_seconds)

            if updated_page:
                if updated_page.get("_unchanged"):
                    return (updated_page, "unchanged")
                return (updated_page, "updated")
            return (None, "error")

        created_page = None
        for attempt in range(page_create_retries):
            created_page = self.create_page(title, content, parent_id, space_key)
            if created_page:
                return (created_page, "created")
            if attempt < page_create_retries - 1:
                wait_seconds = page_retry_backoff_seconds * (attempt + 1)
                print(
                    f"Retrying create for page '{title}' after transient failure "
                    f"(attempt {attempt + 2}/{page_create_retries}) in {wait_seconds:.1f}s..."
                )
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
        return (None, "error")

    def upload_attachment(self, page_id, filename, file_bytes, content_type="application/octet-stream"):
        """Upload attachment to a page. If same filename exists, Confluence versions it."""
        existing = self._get_attachment_by_filename(page_id, filename)
        if existing and existing.get("id"):
            existing_size = existing.get("extensions", {}).get("fileSize")
            if isinstance(existing_size, int) and existing_size == len(file_bytes):
                return {"status": "unchanged", "id": existing.get("id")}
            return self._update_attachment_data(
                page_id=page_id,
                attachment_id=existing["id"],
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
            )

        return self._create_attachment(
            page_id=page_id,
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
        )

    def _get_attachment_by_filename(self, page_id, filename):
        url = f"{self.base_url}/content/{page_id}/child/attachment"
        payload = self._request_json(
            "GET",
            url,
            f"find attachment '{filename}' on page {page_id}",
            params={"filename": filename, "expand": "extensions"},
        )
        if not payload:
            return None
        results = payload.get("results", [])
        return results[0] if results else None

    def _create_attachment(self, page_id, filename, file_bytes, content_type):
        url = f"{self.base_url}/content/{page_id}/child/attachment"
        return self._send_attachment_request(
            url=url,
            method="POST",
            action=f"upload attachment '{filename}' to page {page_id}",
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
        )

    def _update_attachment_data(self, page_id, attachment_id, filename, file_bytes, content_type):
        url = f"{self.base_url}/content/{page_id}/child/attachment/{attachment_id}/data"
        return self._send_attachment_request(
            url=url,
            method="POST",
            action=f"update attachment '{filename}' on page {page_id}",
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
        )

    def _send_attachment_request(self, url, method, action, filename, file_bytes, content_type):
        last_response = None

        for index, strategy in enumerate(self.auth_strategies):
            headers = {
                "Accept": "application/json",
                "X-Atlassian-Token": "no-check",
            }
            headers.update(strategy["headers"])

            files = {
                "file": (filename, file_bytes, content_type)
            }
            data = {
                "minorEdit": "true"
            }

            response = requests.request(
                method,
                url,
                headers=headers,
                auth=strategy["auth"],
                files=files,
                data=data,
                timeout=60,
                allow_redirects=False,
            )
            last_response = response

            if self._looks_like_auth_redirect(response) and index < len(self.auth_strategies) - 1:
                print(f"Auth method '{strategy['name']}' redirected during attachment upload. Trying next method...")
                continue

            if response.status_code in (200, 201):
                try:
                    return response.json()
                except requests.exceptions.JSONDecodeError:
                    return {"status": response.status_code}

            print(f"Error while trying to {action}: HTTP {response.status_code}")
            preview = (response.text or "")[:500]
            if preview:
                print(preview)
            return None

        if last_response is not None:
            print(f"Error while trying to {action}: HTTP {last_response.status_code}")
            preview = (last_response.text or "")[:500]
            if preview:
                print(preview)
        return None
    
    def delete_page(self, page_id, suppress_not_found=False):
        """Delete a page."""
        url = f"{self.base_url}/content/{page_id}"
        strategy = self.auth_strategies[0]
        headers = dict(self.base_headers)
        headers.update(strategy["headers"])
        response = requests.delete(url, headers=headers, auth=strategy["auth"], timeout=30, allow_redirects=False)
        
        if response.status_code == 204:
            return True
        if response.status_code == 404 and suppress_not_found:
            return True
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False

    def diagnose_auth(self, space_key=None):
        """Run a raw auth check and print response details"""
        if space_key is None:
            space_key = SPACE_KEY

        url = f"{self.base_url}/content"
        params = {"spaceKey": space_key, "limit": 1}

        print("\n=== Auth Diagnostic ===")
        print(f"Base URL: {self.base_url}")
        print(f"Space Key: {space_key}")
        print(f"Configured Auth Method: {self.auth_method}")
        print(f"Token Present: {'yes' if bool(self.access_token) else 'no'}")
        print(f"Username Present: {'yes' if bool(self.username) else 'no'}")
        print(f"Session Cookie Present: {'yes' if bool(self.session_cookie) else 'no'}")

        for strategy in self.auth_strategies:
            headers = dict(self.base_headers)
            headers.update(strategy["headers"])

            response = requests.get(
                url,
                params=params,
                headers=headers,
                auth=strategy["auth"],
                timeout=30,
                allow_redirects=False,
            )

            content_type = response.headers.get("content-type")
            location = response.headers.get("location")
            print("\n---")
            print(f"Tried Auth: {strategy['name']}")
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {content_type}")
            print(f"Location: {location}")
            print(f"Body Preview: {(response.text or '')[:200].replace(chr(10), ' ')}")


def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python confluence_client.py get-page <page_id>")
        print("  python confluence_client.py list-pages")
        print("  python confluence_client.py diagnose-auth")
        print("  python confluence_client.py create-page <title> <content>")
        print("  python confluence_client.py update-page <page_id> <content>")
        print("  python confluence_client.py search <query>")
        print("  python confluence_client.py delete-page <page_id>")
        print("  python confluence_client.py show-tree <root_page_id> [max_depth]")
        print("  python confluence_client.py build-tree <file.docx|file.md> <parent_page_id> [--preview] [--yes] [--min-level N] [--max-level N] [--heading-mode auto|style|infer] [--index-title TITLE] [--no-index] [--index-as-root] [--skip-assets]")
        print(f"  python confluence_client.py build-tree-fixed <file.docx|file.md> [--parent-id PAGE_ID] [--preview] [--yes] [--min-level N] [--max-level N] [--heading-mode auto|style|infer] [--index-title TITLE] [--no-index] [--index-as-root] [--skip-assets]  # parent={DEFAULT_TREE_PARENT_ID}")
        print(f"  python confluence_client.py build-tree-smart <file.docx|file.md> [--parent-id PAGE_ID] [--preview] [--yes] [--min-level N] [--max-level N] [--heading-mode auto|style|infer] [--no-index] [--skip-assets]  # parent={DEFAULT_TREE_PARENT_ID}, index-title=filename")
        return
    
    client = ConfluenceClient()
    command = sys.argv[1]
    
    if command == "get-page":
        if len(sys.argv) < 3:
            print("Error: Page ID required")
            return
        
        page_id = sys.argv[2]
        page = client.get_page(page_id)
        
        if page:
            print(f"\n=== Page: {page['title']} ===")
            print(f"ID: {page['id']}")
            print(f"Version: {page['version']['number']}")
            print(f"URL: {BASE_URL}{page['_links']['webui']}")
            print(f"\nContent:\n{page['body']['storage']['value']}")
    
    elif command == "list-pages":
        result = client.list_pages()
        
        if result:
            print(f"\n=== Pages in {SPACE_KEY} ===")
            for page in result['results']:
                print(f"- {page['title']} (ID: {page['id']})")

    elif command == "diagnose-auth":
        client.diagnose_auth()
    
    elif command == "create-page":
        if len(sys.argv) < 4:
            print("Error: Title and content required")
            return
        
        title = sys.argv[2]
        content = sys.argv[3]
        
        page = client.create_page(title, content)
        
        if page:
            print(f"✓ Page created: {page['title']}")
            print(f"  ID: {page['id']}")
            print(f"  URL: {BASE_URL}{page['_links']['webui']}")
    
    elif command == "update-page":
        if len(sys.argv) < 4:
            print("Error: Page ID and content required")
            return
        
        page_id = sys.argv[2]
        content = sys.argv[3]
        
        page = client.update_page(page_id, content)
        
        if page:
            print(f"✓ Page updated: {page['title']}")
            print(f"  Version: {page['version']['number']}")
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("Error: Search query required")
            return
        
        query = sys.argv[2]
        result = client.search(query)
        
        if result:
            print(f"\n=== Search Results for '{query}' ===")
            for page in result['results']:
                print(f"- {page['title']} (ID: {page['id']})")
    
    elif command == "delete-page":
        if len(sys.argv) < 3:
            print("Error: Page ID required")
            return
        
        page_id = sys.argv[2]
        confirm = input(f"Delete page {page_id}? (yes/no): ")
        
        if confirm.lower() == "yes":
            if client.delete_page(page_id):
                print("✓ Page deleted")

    elif command == "show-tree":
        if len(sys.argv) < 3:
            print("Error: Root page ID required")
            print("Usage: python confluence_client.py show-tree <root_page_id> [max_depth]")
            return

        root_page_id = sys.argv[2]
        max_depth = 8
        if len(sys.argv) >= 4:
            try:
                max_depth = max(1, int(sys.argv[3]))
            except ValueError:
                print("Error: max_depth must be an integer")
                return

        client.print_page_tree(root_page_id, max_depth=max_depth)

    elif command == "build-tree":
        if len(sys.argv) < 4:
            print("Error: File path and parent page ID are required")
            print("Usage:")
            print("  python confluence_client.py build-tree <file.docx|file.md> <parent_page_id> [--preview] [--yes] [--min-level N] [--max-level N] [--heading-mode auto|style|infer] [--index-title TITLE] [--no-index] [--index-as-root]")
            return

        file_path = sys.argv[2]
        root_page_id = sys.argv[3]
        preview_only = "--preview" in sys.argv[4:]
        non_interactive = "--yes" in sys.argv[4:]
        min_level = 1
        max_level = None
        heading_mode = "auto"
        create_index = True
        index_title = None
        index_as_root = False
        skip_assets = False

        index = 4
        while index < len(sys.argv):
            arg = sys.argv[index]
            if arg == "--preview":
                index += 1
            elif arg == "--yes":
                index += 1
            elif arg == "--min-level" and index + 1 < len(sys.argv):
                min_level = max(1, int(sys.argv[index + 1]))
                index += 2
            elif arg == "--max-level" and index + 1 < len(sys.argv):
                max_level = max(1, int(sys.argv[index + 1]))
                index += 2
            elif arg == "--heading-mode" and index + 1 < len(sys.argv):
                heading_mode = sys.argv[index + 1].strip().lower()
                index += 2
            elif arg == "--index-title" and index + 1 < len(sys.argv):
                index_title = sys.argv[index + 1].strip()
                index += 2
            elif arg == "--no-index":
                create_index = False
                index += 1
            elif arg == "--index-as-root":
                index_as_root = True
                index += 1
            elif arg == "--skip-assets":
                skip_assets = True
                index += 1
            else:
                print(f"Unknown option: {arg}")
                return

        if max_level is not None and min_level > max_level:
            print("Error: --min-level cannot be greater than --max-level")
            return

        if heading_mode not in {"auto", "style", "infer"}:
            print("Error: --heading-mode must be one of: auto, style, infer")
            return

        if file_path.lower().endswith(".docx"):
            from word_document_splitter import WordDocumentSplitter

            splitter = WordDocumentSplitter()
            if preview_only:
                splitter.preview(
                    file_path,
                    root_page_id=root_page_id,
                    min_level=min_level,
                    max_level=max_level,
                    heading_mode=heading_mode,
                )
            else:
                if non_interactive:
                    splitter.split_and_upload(
                        file_path,
                        root_page_id=root_page_id,
                        min_level=min_level,
                        max_level=max_level,
                        heading_mode=heading_mode,
                        create_index=create_index,
                        index_title=index_title,
                        index_as_root=index_as_root,
                        skip_assets=skip_assets,
                    )
                else:
                    confirm = input(f"\n⚠️  This will create/update pages in Confluence space '{SPACE_KEY}'.\n   Continue? (y/n): ")
                    if confirm.lower() in ["y", "yes"]:
                        splitter.split_and_upload(
                            file_path,
                            root_page_id=root_page_id,
                            min_level=min_level,
                            max_level=max_level,
                            heading_mode=heading_mode,
                            create_index=create_index,
                            index_title=index_title,
                            index_as_root=index_as_root,
                            skip_assets=skip_assets,
                        )
                    else:
                        print("Cancelled.")
        elif file_path.lower().endswith(".md"):
            from word_document_splitter import MarkdownSplitter

            splitter = MarkdownSplitter()
            if preview_only:
                sections = splitter.parse_markdown_document(file_path, min_level=min_level, max_level=max_level)
                print(f"Preview complete: {len(sections)} heading sections")
            else:
                if non_interactive:
                    splitter.split_and_upload(
                        file_path,
                        root_page_id=root_page_id,
                        min_level=min_level,
                        max_level=max_level,
                        create_index=create_index,
                        index_title=index_title,
                        index_as_root=index_as_root,
                    )
                else:
                    confirm = input(f"\n⚠️  This will create/update pages in Confluence space '{SPACE_KEY}'.\n   Continue? (y/n): ")
                    if confirm.lower() in ["y", "yes"]:
                        splitter.split_and_upload(
                            file_path,
                            root_page_id=root_page_id,
                            min_level=min_level,
                            max_level=max_level,
                            create_index=create_index,
                            index_title=index_title,
                            index_as_root=index_as_root,
                        )
                    else:
                        print("Cancelled.")
        else:
            print(f"Unsupported file type: {file_path}")
            print("Supported: .docx, .md")

    elif command == "build-tree-fixed":
        # FULL-HIERARCHY FLOW ENTRYPOINT:
        # This mode builds Confluence pages from heading hierarchy (H1/H2/H3...).
        # Data flow: CLI args -> parser config -> splitter -> API create/update -> CLI summary.
        if len(sys.argv) < 3:
            print("Error: File path is required")
            print("Usage:")
            print(f"  python confluence_client.py build-tree-fixed <file.docx|file.md> [--parent-id PAGE_ID] [--preview] [--yes] [--min-level N] [--max-level N] [--heading-mode auto|style|infer] [--index-title TITLE] [--no-index] [--index-as-root] [--no-reorder] [--fast] [--quiet]  # parent={DEFAULT_TREE_PARENT_ID}")
            return

        file_path = sys.argv[2]
        root_page_id = DEFAULT_TREE_PARENT_ID
        preview_only = "--preview" in sys.argv[3:]
        non_interactive = "--yes" in sys.argv[3:]
        min_level = 1
        max_level = None
        heading_mode = "auto"
        create_index = True
        index_title = None
        index_as_root = True
        skip_assets = False
        reorder_tree = True
        quiet_mode = False
        fast_mode = False

        index = 3
        while index < len(sys.argv):
            # Parse build-tree-fixed options manually for backward compatibility
            # with existing command style used in this project.
            arg = sys.argv[index]
            if arg == "--preview":
                index += 1
            elif arg == "--yes":
                index += 1
            elif arg == "--min-level" and index + 1 < len(sys.argv):
                min_level = max(1, int(sys.argv[index + 1]))
                index += 2
            elif arg == "--max-level" and index + 1 < len(sys.argv):
                max_level = max(1, int(sys.argv[index + 1]))
                index += 2
            elif arg == "--heading-mode" and index + 1 < len(sys.argv):
                heading_mode = sys.argv[index + 1].strip().lower()
                index += 2
            elif arg == "--index-title" and index + 1 < len(sys.argv):
                index_title = sys.argv[index + 1].strip()
                index += 2
            elif arg == "--no-index":
                create_index = False
                index += 1
            elif arg == "--index-as-root":
                index_as_root = True
                index += 1
            elif arg == "--skip-assets":
                skip_assets = True
                index += 1
            elif arg == "--no-reorder":
                reorder_tree = False
                index += 1
            elif arg == "--quiet":
                quiet_mode = True
                index += 1
            elif arg == "--fast":
                fast_mode = True
                index += 1
            elif arg == "--parent-id" and index + 1 < len(sys.argv):
                root_page_id = sys.argv[index + 1].strip()
                index += 2
            else:
                print(f"Unknown option: {arg}")
                return

        if fast_mode:
            # Fast mode optimizes large runs by reducing extra operations.
            reorder_tree = False
            quiet_mode = True

        if max_level is not None and min_level > max_level:
            print("Error: --min-level cannot be greater than --max-level")
            return

        if heading_mode not in {"auto", "style", "infer"}:
            print("Error: --heading-mode must be one of: auto, style, infer")
            return

        if file_path.lower().endswith(".docx"):
            from word_document_splitter import WordDocumentSplitter

            splitter = WordDocumentSplitter()
            if preview_only:
                splitter.preview(
                    file_path,
                    root_page_id=root_page_id,
                    min_level=min_level,
                    max_level=max_level,
                    heading_mode=heading_mode,
                )
            else:
                if non_interactive:
                    splitter.split_and_upload(
                        file_path,
                        root_page_id=root_page_id,
                        min_level=min_level,
                        max_level=max_level,
                        heading_mode=heading_mode,
                        create_index=create_index,
                        index_title=index_title,
                        index_as_root=index_as_root,
                        skip_assets=skip_assets,
                        reorder_tree=reorder_tree,
                    )
                else:
                    confirm = input(f"\n⚠️  This will create/update pages in Confluence space '{SPACE_KEY}' under fixed parent '{root_page_id}'.\n   Continue? (y/n): ")
                    if confirm.lower() in ["y", "yes"]:
                        splitter.split_and_upload(
                            file_path,
                            root_page_id=root_page_id,
                            min_level=min_level,
                            max_level=max_level,
                            heading_mode=heading_mode,
                            create_index=create_index,
                            index_title=index_title,
                            index_as_root=index_as_root,
                            skip_assets=skip_assets,
                            reorder_tree=reorder_tree,
                        )
                    else:
                        print("Cancelled.")
        elif file_path.lower().endswith(".md"):
            from word_document_splitter import MarkdownSplitter

            splitter = MarkdownSplitter()
            if preview_only:
                # Local parse only, no server writes.
                sections = splitter.parse_markdown_document(
                    file_path,
                    min_level=min_level,
                    max_level=max_level,
                    verbose=not quiet_mode,
                )
                print(f"Preview complete: {len(sections)} heading sections")
            else:
                if non_interactive:
                    # Server write path: create/update hierarchy pages and index.
                    splitter.split_and_upload(
                        file_path,
                        root_page_id=root_page_id,
                        min_level=min_level,
                        max_level=max_level,
                        create_index=create_index,
                        index_title=index_title,
                        index_as_root=index_as_root,
                        reorder_tree=reorder_tree,
                        verbose=not quiet_mode,
                    )
                else:
                    confirm = input(f"\n⚠️  This will create/update pages in Confluence space '{SPACE_KEY}' under fixed parent '{root_page_id}'.\n   Continue? (y/n): ")
                    if confirm.lower() in ["y", "yes"]:
                        splitter.split_and_upload(
                            file_path,
                            root_page_id=root_page_id,
                            min_level=min_level,
                            max_level=max_level,
                            create_index=create_index,
                            index_title=index_title,
                            index_as_root=index_as_root,
                            reorder_tree=reorder_tree,
                            verbose=not quiet_mode,
                        )
                    else:
                        print("Cancelled.")
        else:
            print(f"Unsupported file type: {file_path}")
            print("Supported: .docx, .md")

    elif command == "build-tree-smart":
        if len(sys.argv) < 3:
            print("Error: File path is required")
            print("Usage:")
            print(f"  python confluence_client.py build-tree-smart <file.docx|file.md> [--parent-id PAGE_ID] [--preview] [--yes] [--min-level N] [--max-level N] [--heading-mode auto|style|infer] [--no-index] [--skip-assets]  # parent={DEFAULT_TREE_PARENT_ID}, index-title=filename")
            return

        file_path = sys.argv[2]
        root_page_id = DEFAULT_TREE_PARENT_ID
        preview_only = "--preview" in sys.argv[3:]
        non_interactive = "--yes" in sys.argv[3:]
        min_level = 1
        max_level = None
        heading_mode = "auto"
        create_index = True
        skip_assets = False
        index_as_root = True

        basename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(basename)[0].strip()
        index_title = name_without_ext if name_without_ext else "Document"

        index = 3
        while index < len(sys.argv):
            arg = sys.argv[index]
            if arg == "--preview":
                index += 1
            elif arg == "--yes":
                index += 1
            elif arg == "--min-level" and index + 1 < len(sys.argv):
                min_level = max(1, int(sys.argv[index + 1]))
                index += 2
            elif arg == "--max-level" and index + 1 < len(sys.argv):
                max_level = max(1, int(sys.argv[index + 1]))
                index += 2
            elif arg == "--heading-mode" and index + 1 < len(sys.argv):
                heading_mode = sys.argv[index + 1].strip().lower()
                index += 2
            elif arg == "--no-index":
                create_index = False
                index_as_root = False
                index += 1
            elif arg == "--skip-assets":
                skip_assets = True
                index += 1
            elif arg == "--parent-id" and index + 1 < len(sys.argv):
                root_page_id = sys.argv[index + 1].strip()
                index += 2
            else:
                print(f"Unknown option: {arg}")
                return

        if max_level is not None and min_level > max_level:
            print("Error: --min-level cannot be greater than --max-level")
            return

        if heading_mode not in {"auto", "style", "infer"}:
            print("Error: --heading-mode must be one of: auto, style, infer")
            return

        if file_path.lower().endswith(".docx"):
            from word_document_splitter import WordDocumentSplitter

            splitter = WordDocumentSplitter()
            if preview_only:
                splitter.preview(
                    file_path,
                    root_page_id=root_page_id,
                    min_level=min_level,
                    max_level=max_level,
                    heading_mode=heading_mode,
                )
            else:
                if non_interactive:
                    splitter.split_and_upload(
                        file_path,
                        root_page_id=root_page_id,
                        min_level=min_level,
                        max_level=max_level,
                        heading_mode=heading_mode,
                        create_index=create_index,
                        index_title=index_title,
                        index_as_root=index_as_root,
                        skip_assets=skip_assets,
                    )
                else:
                    confirm = input(f"\n⚠️  This will create/update pages in Confluence space '{SPACE_KEY}' under fixed parent '{root_page_id}'.\n   Continue? (y/n): ")
                    if confirm.lower() in ["y", "yes"]:
                        splitter.split_and_upload(
                            file_path,
                            root_page_id=root_page_id,
                            min_level=min_level,
                            max_level=max_level,
                            heading_mode=heading_mode,
                            create_index=create_index,
                            index_title=index_title,
                            index_as_root=index_as_root,
                            skip_assets=skip_assets,
                        )
                    else:
                        print("Cancelled.")
        elif file_path.lower().endswith(".md"):
            from word_document_splitter import MarkdownSplitter

            splitter = MarkdownSplitter()
            if preview_only:
                sections = splitter.parse_markdown_document(file_path, min_level=min_level, max_level=max_level)
                print(f"Preview complete: {len(sections)} heading sections")
            else:
                if non_interactive:
                    splitter.split_and_upload(
                        file_path,
                        root_page_id=root_page_id,
                        min_level=min_level,
                        max_level=max_level,
                        create_index=create_index,
                        index_title=index_title,
                        index_as_root=index_as_root,
                    )
                else:
                    confirm = input(f"\n⚠️  This will create/update pages in Confluence space '{SPACE_KEY}' under fixed parent '{root_page_id}'.\n   Continue? (y/n): ")
                    if confirm.lower() in ["y", "yes"]:
                        splitter.split_and_upload(
                            file_path,
                            root_page_id=root_page_id,
                            min_level=min_level,
                            max_level=max_level,
                            create_index=create_index,
                            index_title=index_title,
                            index_as_root=index_as_root,
                        )
                    else:
                        print("Cancelled.")
        else:
            print(f"Unsupported file type: {file_path}")
            print("Supported: .docx, .md")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Upload interrupted by user.")
