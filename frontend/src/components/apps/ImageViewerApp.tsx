/**
 * Image Viewer App
 */
import { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { FileNode } from '../../types';

export function ImageViewerApp() {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [images, setImages] = useState<FileNode[]>([]);
  const [selectedImage, setSelectedImage] = useState<FileNode | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadImages();
  }, []);

  const loadImages = async () => {
    try {
      // Initialize filesystem if needed
      const root = await api.initFilesystem();
      // List all files in root
      const nodes = await api.listDirectory(root.id);
      // Filter for images
      const imageFiles = nodes.filter(
        (n) => n.type === 'file' && n.mime_type?.startsWith('image/')
      );
      setImages(imageFiles);
      if (imageFiles.length > 0) {
        setSelectedImage(imageFiles[0]);
      }
    } catch (error) {
      console.error('Failed to load images:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="image-viewer-loading">Loading images...</div>;
  }

  return (
    <div className="image-viewer-app">
      <div className="image-viewer-sidebar">
        <h3>Images</h3>
        {images.length === 0 ? (
          <div className="image-viewer-empty">No images found</div>
        ) : (
          <div className="image-viewer-list">
            {images.map((img) => (
              <div
                key={img.id}
                className={`image-viewer-item ${selectedImage?.id === img.id ? 'active' : ''}`}
                onClick={() => setSelectedImage(img)}
              >
                {img.name}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="image-viewer-main">
        {selectedImage ? (
          <div className="image-viewer-display">
            <h2>{selectedImage.name}</h2>
            {selectedImage.content && (
              <img
                src={`data:${selectedImage.mime_type};base64,${selectedImage.content}`}
                alt={selectedImage.name}
              />
            )}
          </div>
        ) : (
          <div className="image-viewer-placeholder">
            Select an image to view
          </div>
        )}
      </div>
    </div>
  );
}
