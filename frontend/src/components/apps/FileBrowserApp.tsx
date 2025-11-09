/**
 * File Browser App - Navigate virtual filesystem
 */
import { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { FileNode } from '../../types';

export function FileBrowserApp() {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [currentDir, setCurrentDir] = useState<FileNode | null>(null);
  const [contents, setContents] = useState<FileNode[]>([]);
  const [path, setPath] = useState<FileNode[]>([]);

  useEffect(() => {
    init();
  }, []);

  const init = async () => {
    try {
      const root = await api.initFilesystem();
      setCurrentDir(root);
      setPath([root]);
      await loadDirectory(root.id);
    } catch (error) {
      console.error('Failed to initialize filesystem:', error);
    }
  };

  const loadDirectory = async (dirId: string) => {
    try {
      const nodes = await api.listDirectory(dirId);
      setContents(nodes);
    } catch (error) {
      console.error('Failed to load directory:', error);
    }
  };

  const handleOpen = (node: FileNode) => {
    if (node.type === 'directory') {
      setCurrentDir(node);
      setPath([...path, node]);
      loadDirectory(node.id);
    }
  };

  const handleBack = () => {
    if (path.length <= 1) return;
    const newPath = path.slice(0, -1);
    const parent = newPath[newPath.length - 1];
    setPath(newPath);
    setCurrentDir(parent);
    loadDirectory(parent.id);
  };

  const handleNewFolder = async () => {
    if (!currentDir) return;
    const name = prompt('Enter folder name:');
    if (!name) return;
    try {
      await api.createDirectory(name, currentDir.id);
      await loadDirectory(currentDir.id);
    } catch (error) {
      console.error('Failed to create folder:', error);
    }
  };

  return (
    <div className="file-browser-app">
      <div className="file-browser-toolbar">
        <button onClick={handleBack} disabled={path.length <= 1}>
          ← Back
        </button>
        <div className="file-browser-path">
          {path.map((p) => p.name).join(' / ')}
        </div>
        <button onClick={handleNewFolder}>+ New Folder</button>
      </div>

      <div className="file-browser-content">
        {contents.length === 0 ? (
          <div className="file-browser-empty">This folder is empty</div>
        ) : (
          <div className="file-browser-grid">
            {contents.map((node) => (
              <div
                key={node.id}
                className="file-browser-item"
                onDoubleClick={() => handleOpen(node)}
              >
                <div className="file-browser-icon">
                  {node.type === 'directory' ? '📁' : '📄'}
                </div>
                <div className="file-browser-name">{node.name}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
