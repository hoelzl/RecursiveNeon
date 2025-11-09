/**
 * File Browser App - Windows Explorer-style file browser with sidebar navigation
 */
import { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { FileNode } from '../../types';
import { Dialog } from '../Dialog';

interface ContextMenu {
  x: number;
  y: number;
  node: FileNode;
}

interface DialogState {
  type: 'new-folder' | 'new-file' | 'rename' | 'delete' | null;
  node?: FileNode;
}

interface Clipboard {
  operation: 'copy' | 'cut';
  node: FileNode;
}

export function FileBrowserApp() {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [currentDir, setCurrentDir] = useState<FileNode | null>(null);
  const [contents, setContents] = useState<FileNode[]>([]);
  const [path, setPath] = useState<FileNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<FileNode | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenu | null>(null);
  const [dialog, setDialog] = useState<DialogState>({ type: null });
  const [clipboard, setClipboard] = useState<Clipboard | null>(null);

  useEffect(() => {
    init();
  }, []);

  // Close context menu on click outside
  useEffect(() => {
    const handleClick = () => setContextMenu(null);
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
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
      // Sort: directories first, then files, both alphabetically
      const sorted = nodes.sort((a, b) => {
        if (a.type === b.type) {
          return a.name.localeCompare(b.name);
        }
        return a.type === 'directory' ? -1 : 1;
      });
      setContents(sorted);
    } catch (error) {
      console.error('Failed to load directory:', error);
    }
  };

  const handleOpen = (node: FileNode) => {
    if (node.type === 'directory') {
      setCurrentDir(node);
      setPath([...path, node]);
      loadDirectory(node.id);
      setSelectedNode(null);
    }
  };

  const handleBack = () => {
    if (path.length <= 1) return;
    const newPath = path.slice(0, -1);
    const parent = newPath[newPath.length - 1];
    setPath(newPath);
    setCurrentDir(parent);
    loadDirectory(parent.id);
    setSelectedNode(null);
  };

  const navigateToRoot = () => {
    if (path.length === 0) return;
    const root = path[0];
    setPath([root]);
    setCurrentDir(root);
    loadDirectory(root.id);
    setSelectedNode(null);
  };

  const handleContextMenu = (e: React.MouseEvent, node: FileNode) => {
    e.preventDefault();
    e.stopPropagation();
    // Calculate position relative to the app container
    const appElement = (e.currentTarget as HTMLElement).closest('.file-browser-app');
    if (appElement) {
      const rect = appElement.getBoundingClientRect();
      setContextMenu({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        node
      });
    }
  };

  const handleNewFolder = () => {
    setDialog({ type: 'new-folder' });
  };

  const handleNewFile = () => {
    setDialog({ type: 'new-file' });
  };

  const handleRename = (node: FileNode) => {
    setContextMenu(null);
    setDialog({ type: 'rename', node });
  };

  const handleDelete = (node: FileNode) => {
    setContextMenu(null);
    setDialog({ type: 'delete', node });
  };

  const handleCopy = (node: FileNode) => {
    setContextMenu(null);
    setClipboard({ operation: 'copy', node });
  };

  const handleCut = (node: FileNode) => {
    setContextMenu(null);
    setClipboard({ operation: 'cut', node });
  };

  const handlePaste = async () => {
    setContextMenu(null);
    if (!clipboard || !currentDir) return;

    try {
      if (clipboard.operation === 'copy') {
        await api.copyFile(clipboard.node.id, currentDir.id);
      } else {
        await api.moveFile(clipboard.node.id, currentDir.id);
        setClipboard(null); // Clear clipboard after cut
      }
      await loadDirectory(currentDir.id);
    } catch (error) {
      console.error('Failed to paste:', error);
    }
  };

  const confirmNewFolder = async (name?: string) => {
    if (!currentDir || !name || !name.trim()) {
      setDialog({ type: null });
      return;
    }
    try {
      await api.createDirectory(name.trim(), currentDir.id);
      await loadDirectory(currentDir.id);
    } catch (error) {
      console.error('Failed to create folder:', error);
    }
    setDialog({ type: null });
  };

  const confirmNewFile = async (name?: string) => {
    if (!currentDir || !name || !name.trim()) {
      setDialog({ type: null });
      return;
    }
    try {
      // Create an empty text file
      const fileName = name.trim().endsWith('.txt') ? name.trim() : `${name.trim()}.txt`;
      await api.createFile(fileName, currentDir.id, '', 'text/plain');
      await loadDirectory(currentDir.id);
    } catch (error) {
      console.error('Failed to create file:', error);
    }
    setDialog({ type: null });
  };

  const confirmRename = async (newName?: string) => {
    if (!dialog.node || !newName || !newName.trim()) {
      setDialog({ type: null });
      return;
    }
    try {
      await api.updateFile(dialog.node.id, { name: newName.trim() });
      if (currentDir) {
        await loadDirectory(currentDir.id);
      }
    } catch (error) {
      console.error('Failed to rename:', error);
    }
    setDialog({ type: null });
  };

  const confirmDelete = async () => {
    if (!dialog.node || !currentDir) {
      setDialog({ type: null });
      return;
    }
    try {
      await api.deleteFile(dialog.node.id);
      await loadDirectory(currentDir.id);
      if (selectedNode?.id === dialog.node.id) {
        setSelectedNode(null);
      }
    } catch (error) {
      console.error('Failed to delete:', error);
    }
    setDialog({ type: null });
  };

  const getFileIcon = (node: FileNode) => {
    if (node.type === 'directory') return '📁';

    const mime = node.mime_type || '';
    if (mime.startsWith('image/')) return '🖼️';
    if (mime.startsWith('text/')) return '📄';
    if (mime.startsWith('audio/')) return '🎵';
    if (mime.startsWith('video/')) return '🎬';
    if (mime === 'application/pdf') return '📕';

    return '📄';
  };

  return (
    <div className="file-browser-app">
      {/* Toolbar */}
      <div className="file-browser-toolbar">
        <button onClick={handleBack} disabled={path.length <= 1}>
          ← Back
        </button>
        <div className="file-browser-path">
          {path.map((p) => p.name).join(' / ')}
        </div>
        <button onClick={handleNewFile}>+ New File</button>
        <button onClick={handleNewFolder}>+ New Folder</button>
        {clipboard && (
          <button onClick={handlePaste}>
            📋 Paste ({clipboard.operation === 'copy' ? 'Copy' : 'Move'})
          </button>
        )}
      </div>

      {/* Body with sidebar and content */}
      <div className="file-browser-body">
        {/* Left Sidebar */}
        <div className="file-browser-sidebar">
          <div className="file-browser-sidebar-section">
            <div className="file-browser-sidebar-title">Quick Access</div>
            <div
              className="file-browser-sidebar-item active"
              onClick={navigateToRoot}
            >
              <span className="file-browser-sidebar-icon">🏠</span>
              <span>Home</span>
            </div>
          </div>

          {/* Simple folder tree showing current path */}
          <div className="file-browser-sidebar-section">
            <div className="file-browser-sidebar-title">Folders</div>
            <div className="file-browser-tree">
              {path.map((node, index) => (
                <div
                  key={node.id}
                  className={`file-browser-tree-item ${
                    currentDir?.id === node.id ? 'selected' : ''
                  }`}
                  style={{ paddingLeft: `${index * 12}px` }}
                  onClick={() => {
                    const newPath = path.slice(0, index + 1);
                    setPath(newPath);
                    setCurrentDir(node);
                    loadDirectory(node.id);
                    setSelectedNode(null);
                  }}
                >
                  <span>{index === 0 ? '🏠' : '📁'}</span>
                  <span>{node.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Content Area */}
        <div className="file-browser-content">
          {contents.length === 0 ? (
            <div className="file-browser-empty">This folder is empty</div>
          ) : (
            <div className="file-browser-grid">
              {contents.map((node) => (
                <div
                  key={node.id}
                  className={`file-browser-item ${
                    selectedNode?.id === node.id ? 'selected' : ''
                  }`}
                  onClick={() => setSelectedNode(node)}
                  onDoubleClick={() => handleOpen(node)}
                  onContextMenu={(e) => handleContextMenu(e, node)}
                >
                  <div className="file-browser-icon">{getFileIcon(node)}</div>
                  <div className="file-browser-name">{node.name}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <div
            className="context-menu-item"
            onClick={() => handleCopy(contextMenu.node)}
          >
            📄 Copy
          </div>
          <div
            className="context-menu-item"
            onClick={() => handleCut(contextMenu.node)}
          >
            ✂️ Cut
          </div>
          <div
            className="context-menu-item"
            onClick={() => handleRename(contextMenu.node)}
          >
            ✏️ Rename
          </div>
          <div
            className="context-menu-item"
            onClick={() => handleDelete(contextMenu.node)}
          >
            🗑️ Delete
          </div>
        </div>
      )}

      {/* Dialogs */}
      {dialog.type === 'new-folder' && (
        <Dialog
          title="Create New Folder"
          message="Enter the name for the new folder:"
          defaultValue=""
          onConfirm={confirmNewFolder}
          onCancel={() => setDialog({ type: null })}
          showInput={true}
        />
      )}

      {dialog.type === 'new-file' && (
        <Dialog
          title="Create New File"
          message="Enter the name for the new file (will be saved as .txt):"
          defaultValue=""
          onConfirm={confirmNewFile}
          onCancel={() => setDialog({ type: null })}
          showInput={true}
        />
      )}

      {dialog.type === 'rename' && dialog.node && (
        <Dialog
          title="Rename"
          message={`Enter a new name for "${dialog.node.name}":`}
          defaultValue={dialog.node.name}
          onConfirm={confirmRename}
          onCancel={() => setDialog({ type: null })}
          showInput={true}
        />
      )}

      {dialog.type === 'delete' && dialog.node && (
        <Dialog
          title="Confirm Delete"
          message={`Are you sure you want to delete "${dialog.node.name}"?`}
          onConfirm={confirmDelete}
          onCancel={() => setDialog({ type: null })}
          showInput={false}
        />
      )}
    </div>
  );
}
