/**
 * Image Viewer App - View images from the file system
 */
import { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { FileNode } from '../../types';

interface ImageViewerAppProps {
  /** Optional file ID to open initially */
  fileId?: string;
}

export function ImageViewerApp({ fileId }: ImageViewerAppProps = {}) {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [selectedImage, setSelectedImage] = useState<FileNode | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (fileId) {
      loadImageById(fileId);
    } else {
      setLoading(false);
    }
  }, [fileId]);

  const loadImageById = async (id: string) => {
    setLoading(true);
    try {
      const file = await api.getFile(id);
      if (file.type === 'file' && file.mime_type?.startsWith('image/')) {
        setSelectedImage(file);
      } else {
        console.error('File is not an image');
      }
    } catch (error) {
      console.error('Failed to load image:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="image-viewer-loading">Loading image...</div>;
  }

  return (
    <div className="image-viewer-app">
      <div className="image-viewer-main">
        {selectedImage ? (
          <div className="image-viewer-display">
            <div className="image-viewer-header">
              <h2>{selectedImage.name}</h2>
            </div>
            <div className="image-viewer-content">
              {selectedImage.content && (
                <img
                  src={`data:${selectedImage.mime_type};base64,${selectedImage.content}`}
                  alt={selectedImage.name}
                  className="image-viewer-image"
                />
              )}
            </div>
          </div>
        ) : (
          <div className="image-viewer-placeholder">
            <p>No image selected</p>
            <p className="image-viewer-hint">Open an image file from the file browser</p>
          </div>
        )}
      </div>
    </div>
  );
}
