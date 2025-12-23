"""
Browser Service

Manages browser pages and bookmarks for the in-game web browser.
"""
import uuid
from typing import Dict, Any, List, Optional

from recursive_neon.models.app_models import BrowserPage, BrowserState


class BrowserService:
    """
    Service for managing browser pages and bookmarks.

    Provides CRUD operations for the web browser application.
    """

    def __init__(self, browser_state: BrowserState):
        """
        Initialize the browser service.

        Args:
            browser_state: The browser state to manage
        """
        self._state = browser_state

    def get_pages(self) -> List[BrowserPage]:
        """Get all browser pages."""
        return self._state.pages

    def get_page_by_url(self, url: str) -> Optional[BrowserPage]:
        """
        Get a browser page by URL.

        Args:
            url: URL to look up

        Returns:
            The browser page if found, None otherwise
        """
        for page in self._state.pages:
            if page.url == url:
                return page
        return None

    def get_page_by_id(self, page_id: str) -> BrowserPage:
        """
        Get a browser page by ID.

        Args:
            page_id: ID of the page to retrieve

        Returns:
            The browser page

        Raises:
            ValueError: If page not found
        """
        for page in self._state.pages:
            if page.id == page_id:
                return page
        raise ValueError(f"Browser page not found: {page_id}")

    def create_page(self, data: Dict[str, Any]) -> BrowserPage:
        """
        Create a new browser page.

        Args:
            data: Page data (url, title, content)

        Returns:
            The created browser page
        """
        page = BrowserPage(
            id=str(uuid.uuid4()),
            url=data.get("url", ""),
            title=data.get("title", "Untitled"),
            content=data.get("content", ""),
        )
        self._state.pages.append(page)
        return page

    def update_page(self, page_id: str, data: Dict[str, Any]) -> BrowserPage:
        """
        Update a browser page.

        Args:
            page_id: ID of the page to update
            data: Updated page data

        Returns:
            The updated browser page

        Raises:
            ValueError: If page not found
        """
        page = self.get_page_by_id(page_id)

        for i, p in enumerate(self._state.pages):
            if p.id == page_id:
                updated = BrowserPage(
                    id=page.id,
                    url=data.get("url", page.url),
                    title=data.get("title", page.title),
                    content=data.get("content", page.content),
                )
                self._state.pages[i] = updated
                return updated
        raise ValueError(f"Browser page not found: {page_id}")

    def delete_page(self, page_id: str) -> None:
        """
        Delete a browser page.

        Args:
            page_id: ID of the page to delete
        """
        self._state.pages = [
            p for p in self._state.pages if p.id != page_id
        ]

    # ============================================================================
    # Bookmark Operations
    # ============================================================================

    def get_bookmarks(self) -> List[str]:
        """Get all bookmarks."""
        return self._state.bookmarks

    def add_bookmark(self, url: str) -> None:
        """
        Add a bookmark.

        Args:
            url: URL to bookmark
        """
        if url not in self._state.bookmarks:
            self._state.bookmarks.append(url)

    def remove_bookmark(self, url: str) -> None:
        """
        Remove a bookmark.

        Args:
            url: URL to remove from bookmarks
        """
        self._state.bookmarks = [
            b for b in self._state.bookmarks if b != url
        ]

    def is_bookmarked(self, url: str) -> bool:
        """
        Check if a URL is bookmarked.

        Args:
            url: URL to check

        Returns:
            True if bookmarked, False otherwise
        """
        return url in self._state.bookmarks
