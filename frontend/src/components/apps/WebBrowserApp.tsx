/**
 * Web Browser App - Sandboxed browser with mapped URLs
 */
import { useState, useEffect, useRef } from 'react';
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
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    loadBookmarks();
    navigateTo('home.html');
  }, []);

  useEffect(() => {
    // Inject styles into iframe for better text contrast
    const iframe = iframeRef.current;
    if (!iframe) return;

    const injectStyles = () => {
      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
        if (!iframeDoc) return;

        // Check if styles are already injected
        if (iframeDoc.getElementById('browser-injected-styles')) return;

        const style = iframeDoc.createElement('style');
        style.id = 'browser-injected-styles';
        style.textContent = `
          body {
            color: #333;
            background-color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            padding: 16px;
            max-width: 100%;
          }
          a {
            color: #0066cc;
            text-decoration: underline;
          }
          a:hover {
            color: #0052a3;
          }
          h1, h2, h3, h4, h5, h6 {
            color: #222;
            margin-top: 1em;
            margin-bottom: 0.5em;
          }
          p {
            margin-bottom: 1em;
          }
        `;
        iframeDoc.head.appendChild(style);
      } catch (e) {
        // Silently fail if we can't access iframe content (CORS)
        console.debug('Could not inject styles into iframe:', e);
      }
    };

    // Inject styles after iframe loads
    iframe.addEventListener('load', injectStyles);
    // Also try to inject immediately in case it's already loaded
    injectStyles();

    return () => {
      iframe.removeEventListener('load', injectStyles);
    };
  }, [currentPage]);

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
            ref={iframeRef}
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
