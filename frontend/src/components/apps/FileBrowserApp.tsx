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
  node?: FileNode;
  type: 'file' | 'background' | 'sidebar' | 'sidebar-tree' | 'pinned-folder';
  pinnedFolderId?: string;
}

interface DialogState {
  type: 'new-folder' | 'new-file' | 'rename' | 'delete' | null;
  node?: FileNode;
}

interface Clipboard {
  operation: 'copy' | 'cut';
  node: FileNode;
}

interface DragState {
  node: FileNode;
}

interface PinnedFolder {
  id: string;
  name: string;
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
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const [pinnedFolders, setPinnedFolders] = useState<PinnedFolder[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    init();
  }, []);

  // Close context menu on click outside
  useEffect(() => {
    const handleClick = () => setContextMenu(null);
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle shortcuts when no dialog is open
      if (dialog.type) return;

      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'c' && selectedNode) {
          e.preventDefault();
          handleCopy(selectedNode);
        } else if (e.key === 'x' && selectedNode) {
          e.preventDefault();
          handleCut(selectedNode);
        } else if (e.key === 'v' && clipboard && currentDir) {
          e.preventDefault();
          handlePaste();
        }
      } else if (e.key === 'Delete' && selectedNode) {
        e.preventDefault();
        handleDelete(selectedNode);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedNode, clipboard, currentDir, dialog.type]);

  const init = async () => {
    try {
      setIsLoading(true);
      const root = await api.initFilesystem();
      setCurrentDir(root);
      setPath([root]);
      // Load the root directory contents immediately
      await loadDirectory(root.id);
    } catch (error) {
      console.error('Failed to initialize filesystem:', error);
    } finally {
      setIsLoading(false);
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

  const handleContextMenu = (e: React.MouseEvent, type: 'file' | 'background' | 'sidebar' | 'sidebar-tree' | 'pinned-folder', node?: FileNode, pinnedFolderId?: string) => {
    e.preventDefault();
    e.stopPropagation();
    // Calculate position relative to the app container
    const appElement = (e.currentTarget as HTMLElement).closest('.file-browser-app');
    if (appElement) {
      const rect = appElement.getBoundingClientRect();
      setContextMenu({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        type,
        node,
        pinnedFolderId
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

  const handleDragStart = (e: React.DragEvent, node: FileNode) => {
    e.stopPropagation();
    setDragState({ node });
    // Allow both copy and move operations
    e.dataTransfer.effectAllowed = 'copyMove';
    e.dataTransfer.setData('text/plain', node.name);
  };

  const handleDragOver = (e: React.DragEvent, targetId?: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (dragState) {
      // Determine operation based on modifier keys during drag
      e.dataTransfer.dropEffect = e.shiftKey ? 'copy' : 'move';
      setDropTarget(targetId || 'background');
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDropTarget(null);
  };

  const handleDrop = async (e: React.DragEvent, targetNode?: FileNode) => {
    e.preventDefault();
    e.stopPropagation();
    setDropTarget(null);

    if (!dragState || !currentDir) return;

    // Determine operation based on modifier keys at drop time
    const operation = e.shiftKey ? 'copy' : 'move';

    try {
      // Determine target directory
      let targetDirId: string;
      if (targetNode && targetNode.type === 'directory') {
        targetDirId = targetNode.id;
      } else {
        targetDirId = currentDir.id;
      }

      // Don't drop on self or if source and target are the same directory
      if (dragState.node.id === targetDirId) {
        setDragState(null);
        return;
      }

      // Perform the operation
      if (operation === 'copy') {
        await api.copyFile(dragState.node.id, targetDirId);
      } else {
        await api.moveFile(dragState.node.id, targetDirId);
      }

      await loadDirectory(currentDir.id);
    } catch (error) {
      console.error('Failed to drop:', error);
    }

    setDragState(null);
  };

  const handlePinFolder = (folder: FileNode) => {
    if (folder.type !== 'directory') return;
    // Don't pin if already pinned
    if (pinnedFolders.some(p => p.id === folder.id)) return;
    setPinnedFolders([...pinnedFolders, { id: folder.id, name: folder.name, node: folder }]);
  };

  const handleUnpinFolder = (folderId: string) => {
    setPinnedFolders(pinnedFolders.filter(p => p.id !== folderId));
  };

  const navigateToFolder = (folder: FileNode) => {
    setCurrentDir(folder);
    // Build path from root - for now just use the folder as single path
    // In a real app, you'd need to fetch the full path from the API
    setPath([path[0], folder]);
    loadDirectory(folder.id);
    setSelectedNode(null);
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
          ↑ Up
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
              onContextMenu={(e) => handleContextMenu(e, 'sidebar')}
            >
              <span className="file-browser-sidebar-icon">🏠</span>
              <span>Home</span>
            </div>
            {pinnedFolders.map((pinned) => (
              <div
                key={pinned.id}
                className={`file-browser-sidebar-item ${
                  currentDir?.id === pinned.id ? 'active' : ''
                }`}
                onClick={() => navigateToFolder(pinned.node)}
                onContextMenu={(e) => handleContextMenu(e, 'pinned-folder', pinned.node, pinned.id)}
                onDragOver={(e) => handleDragOver(e, pinned.id)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, pinned.node)}
              >
                <span className="file-browser-sidebar-icon">📌</span>
                <span>{pinned.name}</span>
              </div>
            ))}
            {dragState && dragState.node.type === 'directory' && (
              <div
                className={`file-browser-sidebar-item file-browser-pin-drop-zone ${
                  dropTarget === 'pin-zone' ? 'drop-target' : ''
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDropTarget('pin-zone');
                }}
                onDragLeave={handleDragLeave}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDropTarget(null);
                  if (dragState && dragState.node.type === 'directory') {
                    handlePinFolder(dragState.node);
                  }
                  setDragState(null);
                }}
              >
                <span className="file-browser-sidebar-icon">📍</span>
                <span style={{ fontStyle: 'italic', opacity: 0.7 }}>Drop to pin here</span>
              </div>
            )}
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
                  } ${dropTarget === node.id ? 'drop-target' : ''}`}
                  style={{ paddingLeft: `${index * 12}px` }}
                  onClick={() => {
                    const newPath = path.slice(0, index + 1);
                    setPath(newPath);
                    setCurrentDir(node);
                    loadDirectory(node.id);
                    setSelectedNode(null);
                  }}
                  onContextMenu={(e) => handleContextMenu(e, 'sidebar-tree', node)}
                  onDragOver={(e) => handleDragOver(e, node.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, node)}
                >
                  <span>{index === 0 ? '🏠' : '📁'}</span>
                  <span>{node.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Content Area */}
        <div
          className={`file-browser-content ${dropTarget === 'background' ? 'drop-target' : ''}`}
          onContextMenu={(e) => handleContextMenu(e, 'background')}
          onDragOver={(e) => handleDragOver(e)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e)}
        >
          {isLoading ? (
            <div className="file-browser-empty">Loading...</div>
          ) : contents.length === 0 ? (
            <div className="file-browser-empty">This folder is empty</div>
          ) : (
            <div className="file-browser-grid">
              {contents.map((node) => (
                <div
                  key={node.id}
                  className={`file-browser-item ${
                    selectedNode?.id === node.id ? 'selected' : ''
                  } ${dropTarget === node.id && node.type === 'directory' ? 'drop-target' : ''}`}
                  draggable
                  onClick={() => setSelectedNode(node)}
                  onDoubleClick={() => handleOpen(node)}
                  onContextMenu={(e) => handleContextMenu(e, 'file', node)}
                  onDragStart={(e) => handleDragStart(e, node)}
                  onDragOver={(e) => handleDragOver(e, node.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, node)}
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
          {contextMenu.type === 'file' && contextMenu.node && (
            <>
              <div
                className="context-menu-item"
                onClick={() => handleCopy(contextMenu.node!)}
              >
                📄 Copy
              </div>
              <div
                className="context-menu-item"
                onClick={() => handleCut(contextMenu.node!)}
              >
                ✂️ Cut
              </div>
              <div
                className="context-menu-item"
                onClick={() => handleRename(contextMenu.node!)}
              >
                ✏️ Rename
              </div>
              <div
                className="context-menu-item"
                onClick={() => handleDelete(contextMenu.node!)}
              >
                🗑️ Delete
              </div>
            </>
          )}

          {contextMenu.type === 'background' && (
            <>
              <div
                className="context-menu-item"
                onClick={() => {
                  setContextMenu(null);
                  handleNewFile();
                }}
              >
                📄 New File
              </div>
              <div
                className="context-menu-item"
                onClick={() => {
                  setContextMenu(null);
                  handleNewFolder();
                }}
              >
                📁 New Folder
              </div>
              {clipboard && (
                <>
                  <div className="context-menu-separator"></div>
                  <div
                    className="context-menu-item"
                    onClick={handlePaste}
                  >
                    📋 Paste ({clipboard.operation === 'copy' ? 'Copy' : 'Move'})
                  </div>
                </>
              )}
            </>
          )}

          {contextMenu.type === 'sidebar' && (
            <>
              <div
                className="context-menu-item"
                onClick={() => {
                  setContextMenu(null);
                  navigateToRoot();
                }}
              >
                🏠 Go to Home
              </div>
            </>
          )}

          {contextMenu.type === 'sidebar-tree' && contextMenu.node && (
            <>
              <div
                className="context-menu-item"
                onClick={() => {
                  setContextMenu(null);
                  const nodeIndex = path.findIndex(p => p.id === contextMenu.node?.id);
                  if (nodeIndex >= 0) {
                    const newPath = path.slice(0, nodeIndex + 1);
                    setPath(newPath);
                    setCurrentDir(contextMenu.node!);
                    loadDirectory(contextMenu.node!.id);
                    setSelectedNode(null);
                  }
                }}
              >
                📂 Open
              </div>
              {path.length > 1 && (
                <div
                  className="context-menu-item"
                  onClick={() => {
                    setContextMenu(null);
                    handleBack();
                  }}
                >
                  ↑ Go Up
                </div>
              )}
              <div
                className="context-menu-item"
                onClick={() => {
                  setContextMenu(null);
                  navigateToRoot();
                }}
              >
                🏠 Go to Home
              </div>
            </>
          )}

          {contextMenu.type === 'pinned-folder' && contextMenu.node && contextMenu.pinnedFolderId && (
            <>
              <div
                className="context-menu-item"
                onClick={() => {
                  setContextMenu(null);
                  navigateToFolder(contextMenu.node!);
                }}
              >
                📂 Open
              </div>
              <div className="context-menu-separator"></div>
              <div
                className="context-menu-item"
                onClick={() => {
                  setContextMenu(null);
                  handleUnpinFolder(contextMenu.pinnedFolderId!);
                }}
              >
                📌 Unpin
              </div>
            </>
          )}
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
