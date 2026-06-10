"""
Shared client module for Hx markdown splitter utilities.

Use this module when you need a stable import path for the Confluence client
without importing from CLI wrapper scripts.
"""

from confluence_client import ConfluenceClient

__all__ = ["ConfluenceClient"]
