/**
 * Text Editor App - Simple text file editor
 */
import { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { FileNode } from '../../types';

export function TextEditorApp() {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [files, setFiles] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
  const [content, setContent] = useState('');
  const [rootId, setRootId] = useState<string | null>(null);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      const root = await api.initFilesystem();
      setRootId(root.id);
      const nodes = await api.listDirectory(root.id);
      const textFiles = nodes.filter(
        (n) => n.type === 'file' && n.mime_type === 'text/plain'
      );
      setFiles(textFiles);
      if (textFiles.length > 0) {
        selectFile(textFiles[0]);
      }
    } catch (error) {
      console.error('Failed to load files:', error);
    }
  };

  const selectFile = async (file: FileNode) => {
    try {
      const fullFile = await api.getFile(file.id);
      setSelectedFile(fullFile);
      setContent(fullFile.content || '');
    } catch (error) {
      console.error('Failed to load file:', error);
    }
  };

  const handleSave = async () => {
    if (!selectedFile) return;
    try {
      await api.updateFile(selectedFile.id, { content });
      alert('File saved!');
    } catch (error) {
      console.error('Failed to save file:', error);
    }
  };

  const handleNew = async () => {
    if (!rootId) return;
    const fileName = prompt('Enter file name:');
    if (!fileName) return;
    try {
      const newFile = await api.createFile(fileName, rootId, '', 'text/plain');
      setFiles([...files, newFile]);
      selectFile(newFile);
    } catch (error) {
      console.error('Failed to create file:', error);
    }
  };

  return (
    <div className="text-editor-app">
      <div className="text-editor-sidebar">
        <div className="text-editor-header">
          <h3>Files</h3>
          <button onClick={handleNew}>+ New</button>
        </div>
        <div className="text-editor-list">
          {files.map((file) => (
            <div
              key={file.id}
              className={`text-editor-item ${selectedFile?.id === file.id ? 'active' : ''}`}
              onClick={() => selectFile(file)}
            >
              {file.name}
            </div>
          ))}
        </div>
      </div>

      <div className="text-editor-main">
        {selectedFile ? (
          <>
            <div className="text-editor-toolbar">
              <span className="text-editor-filename">{selectedFile.name}</span>
              <button onClick={handleSave}>Save</button>
            </div>
            <textarea
              className="text-editor-content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Start typing..."
              spellCheck={false}
            />
          </>
        ) : (
          <div className="text-editor-empty">
            <p>No file selected</p>
            <button onClick={handleNew}>Create New File</button>
          </div>
        )}
      </div>
    </div>
  );
}
