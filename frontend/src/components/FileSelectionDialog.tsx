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
  // Store path as array of directory nodes instead of just names
  const [pathNodes, setPathNodes] = useState<FileNode[]>([]);
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
      setPathNodes([root]);
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

    setPathNodes([...pathNodes, dir]);
    await loadDirectory(dir.id);
    setSelectedFile(null);
  };

  const handleNavigateUp = async () => {
    if (pathNodes.length <= 1) return;

    const newPath = pathNodes.slice(0, -1);
    const parentDir = newPath[newPath.length - 1];
    setPathNodes(newPath);
    await loadDirectory(parentDir.id);
    setSelectedFile(null);
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
        const pathNames = pathNodes.map(n => n.name);
        const fullPath = [...pathNames, file.name].join('/');
        onSelect(file.id, fullPath);
        onClose();
      }
    } else if (mode === 'save') {
      if (filename.trim()) {
        // In save mode, we return the directory ID and the filename
        // The parent component will handle creating the file
        const pathNames = pathNodes.map(n => n.name);
        const fullPath = [...pathNames, filename].join('/');
        const currentDirId = pathNodes[pathNodes.length - 1].id;
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
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-[600px] max-h-[80vh] flex flex-col"
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
          width: '600px',
          maxWidth: '90vw',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          className="px-4 py-3 border-b border-gray-200"
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid #e5e7eb',
          }}
        >
          <h2
            className="text-lg font-semibold text-gray-800"
            style={{
              fontSize: '18px',
              fontWeight: 600,
              color: '#1f2937',
              margin: 0,
            }}
          >
            {title || (mode === 'open' ? 'Open File' : 'Save File')}
          </h2>
        </div>

        {/* Location bar */}
        <div
          className="px-4 py-2 border-b border-gray-200 bg-gray-50"
          style={{
            padding: '8px 16px',
            borderBottom: '1px solid #e5e7eb',
            backgroundColor: '#f9fafb',
          }}
        >
          <div
            className="flex items-center space-x-2"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <button
              onClick={handleNavigateUp}
              disabled={pathNodes.length <= 1 || loading}
              className="px-2 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                padding: '4px 8px',
                fontSize: '14px',
                backgroundColor: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                cursor: pathNodes.length <= 1 || loading ? 'not-allowed' : 'pointer',
                opacity: pathNodes.length <= 1 || loading ? 0.5 : 1,
              }}
            >
              ⬆ Up
            </button>
            <div
              className="flex-1 px-3 py-1 bg-white border border-gray-300 rounded text-sm font-mono"
              style={{
                flex: 1,
                padding: '4px 12px',
                backgroundColor: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                fontSize: '14px',
                fontFamily: 'monospace',
              }}
            >
              {pathNodes.map(n => n.name).join('/')}
            </div>
          </div>
        </div>

        {/* File list */}
        <div
          className="flex-1 overflow-y-auto p-4 min-h-[300px]"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            minHeight: '300px',
          }}
        >
          {loading ? (
            <div
              className="flex items-center justify-center h-full text-gray-500"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#6b7280',
              }}
            >
              Loading...
            </div>
          ) : filteredContents.length === 0 ? (
            <div
              className="flex items-center justify-center h-full text-gray-500"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#6b7280',
              }}
            >
              No files found
            </div>
          ) : (
            <div className="space-y-1" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
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
                  style={{
                    padding: '8px 12px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    backgroundColor: selectedFile?.id === item.id ? '#dbeafe' : 'transparent',
                    border: selectedFile?.id === item.id ? '1px solid #93c5fd' : '1px solid transparent',
                  }}
                  onMouseEnter={(e) => {
                    if (selectedFile?.id !== item.id) {
                      e.currentTarget.style.backgroundColor = '#f3f4f6';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (selectedFile?.id !== item.id) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <span className="text-xl" style={{ fontSize: '20px' }}>
                    {item.type === 'directory' ? '📁' : '📄'}
                  </span>
                  <span
                    className="flex-1 text-sm text-gray-800"
                    style={{ flex: 1, fontSize: '14px', color: '#1f2937' }}
                  >
                    {item.name}
                  </span>
                  {item.type === 'directory' && (
                    <span className="text-gray-400" style={{ color: '#9ca3af' }}>→</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Filename input (for save mode) */}
        {mode === 'save' && (
          <div
            className="px-4 py-3 border-t border-gray-200"
            style={{
              padding: '12px 16px',
              borderTop: '1px solid #e5e7eb',
            }}
          >
            <label
              className="block text-sm font-medium text-gray-700 mb-2"
              style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 500,
                color: '#374151',
                marginBottom: '8px',
              }}
            >
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
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                fontSize: '14px',
              }}
              placeholder="Enter filename"
              autoFocus
            />
          </div>
        )}

        {/* Footer buttons */}
        <div
          className="px-4 py-3 border-t border-gray-200 flex justify-end space-x-2"
          style={{
            padding: '12px 16px',
            borderTop: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '8px',
          }}
        >
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
            style={{
              padding: '8px 16px',
              fontSize: '14px',
              backgroundColor: '#e5e7eb',
              color: '#1f2937',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#d1d5db';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#e5e7eb';
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => handleConfirm()}
            disabled={!canConfirm}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              padding: '8px 16px',
              fontSize: '14px',
              backgroundColor: canConfirm ? '#2563eb' : '#93c5fd',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: canConfirm ? 'pointer' : 'not-allowed',
              opacity: canConfirm ? 1 : 0.5,
            }}
            onMouseEnter={(e) => {
              if (canConfirm) {
                e.currentTarget.style.backgroundColor = '#1d4ed8';
              }
            }}
            onMouseLeave={(e) => {
              if (canConfirm) {
                e.currentTarget.style.backgroundColor = '#2563eb';
              }
            }}
          >
            {mode === 'open' ? 'Open' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};
