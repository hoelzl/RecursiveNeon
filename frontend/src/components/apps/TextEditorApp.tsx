/**
 * Text Editor App - Simple text file editor with file system support
 */
import { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { FileNode } from '../../types';
import { Dialog } from '../Dialog';
import { FileSelectionDialog } from '../FileSelectionDialog';

type DialogType = 'save-success' | null;
type FileDialogType = 'open' | 'save-as' | null;

interface TextEditorAppProps {
  /** Optional file ID to open initially */
  fileId?: string;
}

export function TextEditorApp({ fileId }: TextEditorAppProps = {}) {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [filePath, setFilePath] = useState<string>('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [dialogType, setDialogType] = useState<DialogType>(null);
  const [fileDialogType, setFileDialogType] = useState<FileDialogType>(null);

  useEffect(() => {
    if (fileId) {
      loadFileById(fileId);
    }
  }, [fileId]);

  useEffect(() => {
    setHasUnsavedChanges(content !== originalContent);
  }, [content, originalContent]);

  const loadFileById = async (id: string) => {
    try {
      const file = await api.getFile(id);
      await openFile(file);
    } catch (error) {
      console.error('Failed to load file:', error);
    }
  };

  const openFile = async (file: FileNode) => {
    try {
      const fullFile = await api.getFile(file.id);
      setSelectedFile(fullFile);
      setContent(fullFile.content || '');
      setOriginalContent(fullFile.content || '');
      setFilePath(await getFilePath(fullFile));
    } catch (error) {
      console.error('Failed to load file:', error);
    }
  };

  const getFilePath = async (file: FileNode): Promise<string> => {
    // Build the full path by traversing up the parent chain
    const path: string[] = [file.name];
    let currentFile = file;

    try {
      const root = await api.initFilesystem();

      // Traverse up to build path
      while (currentFile.parent_id && currentFile.parent_id !== root.id) {
        const parent = await findNodeById(currentFile.parent_id);
        if (parent) {
          path.unshift(parent.name);
          currentFile = parent;
        } else {
          break;
        }
      }

      path.unshift(root.name);
      return path.join('/');
    } catch (error) {
      console.error('Failed to build file path:', error);
      return file.name;
    }
  };

  const findNodeById = async (nodeId: string): Promise<FileNode | null> => {
    // Simple implementation: search from root
    // In a real app, you might want to cache the tree structure
    try {
      const root = await api.initFilesystem();
      return await searchNode(root.id, nodeId);
    } catch (error) {
      return null;
    }
  };

  const searchNode = async (dirId: string, targetId: string): Promise<FileNode | null> => {
    try {
      const contents = await api.listDirectory(dirId);

      for (const item of contents) {
        if (item.id === targetId) {
          return item;
        }

        if (item.type === 'directory') {
          const found = await searchNode(item.id, targetId);
          if (found) return found;
        }
      }
    } catch (error) {
      // Continue searching
    }

    return null;
  };

  const handleSave = async () => {
    if (!selectedFile) return;

    try {
      await api.updateFile(selectedFile.id, { content });
      setOriginalContent(content);
      setDialogType('save-success');
    } catch (error) {
      console.error('Failed to save file:', error);
    }
  };

  const handleNew = () => {
    // Clear current file and prompt for save location
    setSelectedFile(null);
    setContent('');
    setOriginalContent('');
    setFilePath('');
    setFileDialogType('save-as');
  };

  const handleOpen = () => {
    setFileDialogType('open');
  };

  const handleFileSelect = async (fileId: string) => {
    // Load the selected file
    await loadFileById(fileId);
  };

  const handleSaveAs = async (parentDirId: string, fullPath: string) => {
    try {
      // Extract filename from path
      const pathParts = fullPath.split('/');
      const fileName = pathParts[pathParts.length - 1];

      // Check if file already exists
      const existingFiles = await api.listDirectory(parentDirId);
      const existingFile = existingFiles.find(f => f.name === fileName && f.type === 'file');

      if (existingFile) {
        // Update existing file
        await api.updateFile(existingFile.id, { content });
        setSelectedFile(existingFile);
        setOriginalContent(content);
        setFilePath(fullPath);
      } else {
        // Create new file
        const newFile = await api.createFile(fileName, parentDirId, content, 'text/plain');
        setSelectedFile(newFile);
        setOriginalContent(content);
        setFilePath(fullPath);
      }

      setDialogType('save-success');
    } catch (error) {
      console.error('Failed to save file:', error);
    }
  };

  return (
    <div className="text-editor-app">
      <div className="text-editor-main">
        <div className="text-editor-toolbar">
          <div className="text-editor-toolbar-left">
            <button onClick={handleNew} title="New File">
              New
            </button>
            <button onClick={handleOpen} title="Open File">
              Open
            </button>
            <button
              onClick={handleSave}
              disabled={!selectedFile || !hasUnsavedChanges}
              title="Save File"
            >
              Save
            </button>
            <button
              onClick={() => setFileDialogType('save-as')}
              title="Save As"
            >
              Save As
            </button>
          </div>
          <div className="text-editor-toolbar-right">
            {filePath && (
              <span className="text-editor-filepath" title={filePath}>
                {filePath}
                {hasUnsavedChanges && ' *'}
              </span>
            )}
          </div>
        </div>

        {selectedFile || content ? (
          <textarea
            className="text-editor-content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Start typing..."
            spellCheck={false}
          />
        ) : (
          <div className="text-editor-empty">
            <p>No file selected</p>
            <p className="text-editor-hint">Click "New" to create a file or "Open" to open an existing file</p>
          </div>
        )}
      </div>

      {dialogType === 'save-success' && (
        <Dialog
          title="Success"
          message="File saved successfully!"
          showInput={false}
          onConfirm={() => setDialogType(null)}
          onCancel={() => setDialogType(null)}
        />
      )}

      {fileDialogType === 'open' && (
        <FileSelectionDialog
          isOpen={true}
          onClose={() => setFileDialogType(null)}
          onSelect={handleFileSelect}
          mode="open"
          title="Open File"
          fileFilter={(file) => {
            // Allow text files and common code files
            if (file.mime_type === 'text/plain') return true;
            const textExtensions = ['.txt', '.md', '.json', '.js', '.ts', '.tsx', '.jsx', '.css', '.html', '.xml', '.py'];
            return textExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
          }}
        />
      )}

      {fileDialogType === 'save-as' && (
        <FileSelectionDialog
          isOpen={true}
          onClose={() => setFileDialogType(null)}
          onSelect={handleSaveAs}
          mode="save"
          title="Save File As"
          initialFilename={selectedFile?.name || 'untitled.txt'}
        />
      )}
    </div>
  );
}
