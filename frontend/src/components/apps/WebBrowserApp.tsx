/**
 * Web Browser App - Sandboxed browser with mapped URLs
 */
import { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { BrowserPage } from '../../types';

export function WebBrowserApp() {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [url, setUrl] = useState('home.html');
  const [currentPage, setCurrentPage] = useState<BrowserPage | null>(null);
  const [bookmarks, setBookmarks] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadBookmarks();
    navigateTo('home.html');
  }, []);

  const loadBookmarks = async () => {
    try {
      const bm = await api.getBookmarks();
      setBookmarks(bm);
    } catch (error) {
      console.error('Failed to load bookmarks:', error);
    }
  };

  const navigateTo = async (pageUrl: string) => {
    setLoading(true);
    try {
      const page = await api.getBrowserPage(pageUrl);
      if (page) {
        setCurrentPage(page);
        setUrl(pageUrl);
      } else {
        setCurrentPage({
          id: 'not-found',
          url: pageUrl,
          title: '404 Not Found',
          content: '<h1>Page Not Found</h1><p>The page you requested does not exist.</p>',
        });
      }
    } catch (error) {
      console.error('Failed to navigate:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGo = () => {
    navigateTo(url);
  };

  const handleBookmark = async () => {
    if (!currentPage) return;
    try {
      if (bookmarks.includes(currentPage.url)) {
        await api.removeBookmark(currentPage.url);
        setBookmarks(bookmarks.filter((b) => b !== currentPage.url));
      } else {
        await api.addBookmark(currentPage.url);
        setBookmarks([...bookmarks, currentPage.url]);
      }
    } catch (error) {
      console.error('Failed to update bookmark:', error);
    }
  };

  const isBookmarked = currentPage && bookmarks.includes(currentPage.url);

  return (
    <div className="browser-app">
      <div className="browser-toolbar">
        <input
          type="text"
          className="browser-address-bar"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleGo()}
          placeholder="Enter page address..."
        />
        <button onClick={handleGo} disabled={loading}>
          Go
        </button>
        <button onClick={handleBookmark} disabled={!currentPage}>
          {isBookmarked ? '★' : '☆'}
        </button>
      </div>

      {bookmarks.length > 0 && (
        <div className="browser-bookmarks">
          {bookmarks.map((bookmark) => (
            <button
              key={bookmark}
              className="browser-bookmark"
              onClick={() => navigateTo(bookmark)}
            >
              {bookmark}
            </button>
          ))}
        </div>
      )}

      <div className="browser-content">
        {loading ? (
          <div className="browser-loading">Loading...</div>
        ) : currentPage ? (
          <iframe
            srcDoc={currentPage.content}
            title={currentPage.title}
            sandbox="allow-scripts"
            className="browser-frame"
          />
        ) : (
          <div className="browser-empty">Enter a URL to browse</div>
        )}
      </div>
    </div>
  );
}
