from typing import Any, Dict, Optional


def _extract_storage_from_page_payload(payload: Dict[str, Any]) -> str:
    return str((((payload or {}).get("body") or {}).get("storage") or {}).get("value") or "")


def _extract_storage_from_version_payload(payload: Dict[str, Any]) -> str:
    # Some Confluence responses return content under `content.body.storage.value`
    return str(((((payload or {}).get("content") or {}).get("body") or {}).get("storage") or {}).get("value") or "")


def fetch_latest_and_previous_storage(client: Any, page_id: str) -> Dict[str, Any]:
    """Fetch latest and previous Confluence page versions as storage HTML.

    Returns:
        {
          "available": bool,
          "latest_version": int,
          "previous_version": int,
          "latest_storage": str,
          "previous_storage": str,
        }
    """
    page = client.get_page(page_id)
    if not page:
        return {
            "available": False,
            "latest_version": 0,
            "previous_version": 0,
            "latest_storage": "",
            "previous_storage": "",
        }

    latest_version = int((page.get("version") or {}).get("number") or 0)
    latest_storage = _extract_storage_from_page_payload(page)
    previous_version = max(0, latest_version - 1)

    if latest_version <= 1:
        return {
            "available": False,
            "latest_version": latest_version,
            "previous_version": previous_version,
            "latest_storage": latest_storage,
            "previous_storage": "",
        }

    # Preferred endpoint for historical body
    previous_page_url = f"{client.base_url}/content/{page_id}"
    previous_payload = client._request_json(
        "GET",
        previous_page_url,
        f"get historical version {previous_version} for page {page_id}",
        params={
            "status": "historical",
            "version": previous_version,
            "expand": "body.storage,version",
        },
    )

    previous_storage = ""
    if isinstance(previous_payload, dict):
        previous_storage = _extract_storage_from_page_payload(previous_payload)

    # Fallback endpoint
    if not previous_storage:
        version_url = f"{client.base_url}/content/{page_id}/version/{previous_version}"
        version_payload = client._request_json(
            "GET",
            version_url,
            f"get version payload {previous_version} for page {page_id}",
            params={"expand": "content.body.storage"},
        )
        if isinstance(version_payload, dict):
            previous_storage = _extract_storage_from_version_payload(version_payload)

    return {
        "available": bool(previous_storage),
        "latest_version": latest_version,
        "previous_version": previous_version,
        "latest_storage": latest_storage,
        "previous_storage": previous_storage,
    }


def build_latest_previous_markdown_changes(
    client: Any,
    page_id: str,
    convert_storage_to_markdown: Any,
    collect_net_changes: Any,
) -> Dict[str, Any]:
    version_pair = fetch_latest_and_previous_storage(client, page_id)
    if not version_pair.get("available"):
        return {
            "available": False,
            "latest_version": int(version_pair.get("latest_version") or 0),
            "previous_version": int(version_pair.get("previous_version") or 0),
            "changes": {"added": [], "deleted": [], "replaced": []},
        }

    previous_storage = str(version_pair.get("previous_storage") or "")
    latest_storage = str(version_pair.get("latest_storage") or "")
    previous_markdown = convert_storage_to_markdown(previous_storage)
    latest_markdown = convert_storage_to_markdown(latest_storage)
    changes = collect_net_changes(previous_markdown, latest_markdown)

    return {
        "available": True,
        "latest_version": int(version_pair.get("latest_version") or 0),
        "previous_version": int(version_pair.get("previous_version") or 0),
        "changes": {
            "added": list(changes.get("added") or []),
            "deleted": list(changes.get("deleted") or []),
            "replaced": list(changes.get("replaced") or []),
        },
    }
