import React, { useState, useEffect } from 'react';
import { FileNode } from '../types';
import { AppAPI } from '../utils/appApi';

export type FileSelectionMode = 'open' | 'save';

interface FileSelectionDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback when dialog is closed */
  onClose: () => void;
  /** Callback when a file is selected */
  onSelect: (fileId: string, filePath: string) => void;
  /** Mode: 'open' for selecting existing files, 'save' for specifying new file location */
  mode: FileSelectionMode;
  /** File filter function (optional) - return true to show the file */
  fileFilter?: (file: FileNode) => boolean;
  /** Title of the dialog */
  title?: string;
  /** Initial filename for save mode */
  initialFilename?: string;
  /** AppAPI instance for file operations */
  api: AppAPI;
}

export const FileSelectionDialog: React.FC<FileSelectionDialogProps> = ({
  isOpen,
  onClose,
  onSelect,
  mode,
  fileFilter,
  title,
  initialFilename = '',
  api,
}) => {
  const [currentDirId, setCurrentDirId] = useState<string>('');
  const [currentDirPath, setCurrentDirPath] = useState<string[]>([]);
  const [contents, setContents] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
  const [filename, setFilename] = useState<string>(initialFilename);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      initializeDialog();
    }
  }, [isOpen]);

  const initializeDialog = async () => {
    setLoading(true);
    try {
      const root = await api.initFilesystem();
      setCurrentDirId(root.id);
      setCurrentDirPath([root.name]);
      await loadDirectory(root.id);
      setFilename(initialFilename);
      setSelectedFile(null);
    } catch (error) {
      console.error('Failed to initialize file dialog:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDirectory = async (dirId: string) => {
    setLoading(true);
    try {
      const dirContents = await api.listDirectory(dirId);
      setContents(dirContents);
    } catch (error) {
      console.error('Failed to load directory:', error);
      setContents([]);
    } finally {
      setLoading(false);
    }
  };

  const handleNavigateToDirectory = async (dir: FileNode) => {
    if (dir.type !== 'directory') return;

    setCurrentDirId(dir.id);
    setCurrentDirPath([...currentDirPath, dir.name]);
    await loadDirectory(dir.id);
    setSelectedFile(null);
  };

  const handleNavigateUp = async () => {
    if (currentDirPath.length <= 1) return;

    // Find parent directory
    try {
      // Get current directory to find its parent
      const allDirs = await findParentDirectory(currentDirId);
      if (allDirs) {
        setCurrentDirId(allDirs.id);
        setCurrentDirPath(currentDirPath.slice(0, -1));
        await loadDirectory(allDirs.id);
        setSelectedFile(null);
      }
    } catch (error) {
      console.error('Failed to navigate up:', error);
    }
  };

  const findParentDirectory = async (childId: string): Promise<FileNode | null> => {
    // Get root and search for parent
    const root = await api.initFilesystem();
    return await searchForParent(root.id, childId);
  };

  const searchForParent = async (dirId: string, targetId: string): Promise<FileNode | null> => {
    const contents = await api.listDirectory(dirId);

    // Check if target is directly in this directory
    const found = contents.find(item => item.id === targetId);
    if (found) {
      // Return the current directory as it's the parent
      return contents.find(item => item.id === dirId) || { id: dirId } as FileNode;
    }

    // Recursively search subdirectories
    for (const item of contents) {
      if (item.type === 'directory') {
        const result = await searchForParent(item.id, targetId);
        if (result) return result;
      }
    }

    return null;
  };

  const handleFileClick = (file: FileNode) => {
    if (file.type === 'directory') {
      handleNavigateToDirectory(file);
    } else {
      setSelectedFile(file);
      if (mode === 'save') {
        setFilename(file.name);
      }
    }
  };

  const handleFileDoubleClick = (file: FileNode) => {
    if (file.type === 'directory') {
      handleNavigateToDirectory(file);
    } else if (mode === 'open') {
      // Double-click in open mode immediately selects the file
      handleConfirm(file);
    }
  };

  const handleConfirm = (fileToSelect?: FileNode) => {
    if (mode === 'open') {
      const file = fileToSelect || selectedFile;
      if (file && file.type === 'file') {
        const fullPath = [...currentDirPath, file.name].join('/');
        onSelect(file.id, fullPath);
        onClose();
      }
    } else if (mode === 'save') {
      if (filename.trim()) {
        // In save mode, we return the directory ID and the filename
        // The parent component will handle creating the file
        const fullPath = [...currentDirPath, filename].join('/');
        onSelect(currentDirId, fullPath);
        onClose();
      }
    }
  };

  const handleCancel = () => {
    onClose();
  };

  const filteredContents = contents.filter(item => {
    if (item.type === 'directory') return true;
    if (mode === 'save') return true;
    if (fileFilter) return fileFilter(item);
    return true;
  });

  const canConfirm = mode === 'open' ? selectedFile !== null : filename.trim() !== '';

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-[600px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">
            {title || (mode === 'open' ? 'Open File' : 'Save File')}
          </h2>
        </div>

        {/* Location bar */}
        <div className="px-4 py-2 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-2">
            <button
              onClick={handleNavigateUp}
              disabled={currentDirPath.length <= 1 || loading}
              className="px-2 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ⬆ Up
            </button>
            <div className="flex-1 px-3 py-1 bg-white border border-gray-300 rounded text-sm font-mono">
              {currentDirPath.join('/')}
            </div>
          </div>
        </div>

        {/* File list */}
        <div className="flex-1 overflow-y-auto p-4 min-h-[300px]">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              Loading...
            </div>
          ) : filteredContents.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              No files found
            </div>
          ) : (
            <div className="space-y-1">
              {filteredContents.map(item => (
                <div
                  key={item.id}
                  onClick={() => handleFileClick(item)}
                  onDoubleClick={() => handleFileDoubleClick(item)}
                  className={`px-3 py-2 rounded cursor-pointer flex items-center space-x-2 ${
                    selectedFile?.id === item.id
                      ? 'bg-blue-100 border border-blue-300'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  <span className="text-xl">
                    {item.type === 'directory' ? '📁' : '📄'}
                  </span>
                  <span className="flex-1 text-sm text-gray-800">{item.name}</span>
                  {item.type === 'directory' && (
                    <span className="text-gray-400">→</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Filename input (for save mode) */}
        {mode === 'save' && (
          <div className="px-4 py-3 border-t border-gray-200">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filename:
            </label>
            <input
              type="text"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && canConfirm) {
                  handleConfirm();
                }
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter filename"
              autoFocus
            />
          </div>
        )}

        {/* Footer buttons */}
        <div className="px-4 py-3 border-t border-gray-200 flex justify-end space-x-2">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
          >
            Cancel
          </button>
          <button
            onClick={() => handleConfirm()}
            disabled={!canConfirm}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mode === 'open' ? 'Open' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};
