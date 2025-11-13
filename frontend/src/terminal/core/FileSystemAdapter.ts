/**
 * File system adapter for terminal
 * Provides path resolution and file system operations
 */

import { AppAPI } from '../../utils/appApi';
import { FileNode } from '../../types';

export interface FileSystemNode extends FileNode {
  path?: string; // Virtual path for terminal use
}

export class FileSystemAdapter {
  private api: AppAPI;
  private rootId: string | null = null;
  private currentDirId: string | null = null;
  private pathCache: Map<string, FileSystemNode> = new Map();
  private idToPathCache: Map<string, string> = new Map();

  constructor(api: AppAPI) {
    this.api = api;
  }

  /**
   * Initialize file system
   */
  async init(): Promise<void> {
    const root = await this.api.initFilesystem();
    this.rootId = root.id;
    this.currentDirId = root.id;
    this.pathCache.set('/', { ...root, path: '/' });
    this.idToPathCache.set(root.id, '/');
  }

  /**
   * Get root directory ID
   */
  getRootId(): string | null {
    return this.rootId;
  }

  /**
   * Get current directory ID
   */
  getCurrentDirId(): string {
    return this.currentDirId || this.rootId || '';
  }

  /**
   * Set current directory by ID
   */
  setCurrentDirId(id: string): void {
    this.currentDirId = id;
  }

  /**
   * Resolve a path to an absolute path
   */
  resolvePath(path: string, cwd: string = '/'): string {
    if (path.startsWith('/')) {
      // Already absolute
      return this.normalizePath(path);
    }

    if (path === '~') {
      return '/';
    }

    if (path.startsWith('~/')) {
      return this.normalizePath('/' + path.substring(2));
    }

    // Relative path
    return this.normalizePath(this.joinPaths(cwd, path));
  }

  /**
   * Normalize a path (resolve .. and .)
   */
  private normalizePath(path: string): string {
    const parts = path.split('/').filter((p) => p.length > 0);
    const normalized: string[] = [];

    for (const part of parts) {
      if (part === '..') {
        if (normalized.length > 0) {
          normalized.pop();
        }
      } else if (part !== '.') {
        normalized.push(part);
      }
    }

    return '/' + normalized.join('/');
  }

  /**
   * Join two paths
   */
  private joinPaths(base: string, ...paths: string[]): string {
    let result = base;
    for (const path of paths) {
      if (!result.endsWith('/')) {
        result += '/';
      }
      result += path;
    }
    return result;
  }

  /**
   * Get directory name from path
   */
  dirname(path: string): string {
    const parts = path.split('/').filter((p) => p.length > 0);
    if (parts.length === 0) {
      return '/';
    }
    parts.pop();
    return '/' + parts.join('/');
  }

  /**
   * Get file name from path
   */
  basename(path: string): string {
    const parts = path.split('/').filter((p) => p.length > 0);
    return parts[parts.length - 1] || '/';
  }

  /**
   * Find a node by path
   */
  async findByPath(path: string): Promise<FileSystemNode | null> {
    const normalized = this.resolvePath(path);

    // Check cache first
    if (this.pathCache.has(normalized)) {
      return this.pathCache.get(normalized)!;
    }

    // Root case
    if (normalized === '/') {
      if (!this.rootId) {
        await this.init();
      }
      const root = await this.api.getFile(this.rootId!);
      const node = { ...root, path: '/' };
      this.pathCache.set('/', node);
      this.idToPathCache.set(root.id, '/');
      return node;
    }

    // Navigate from root
    const parts = normalized.split('/').filter((p) => p.length > 0);
    let currentId = this.rootId!;
    let currentPath = '';

    for (const part of parts) {
      const children = await this.api.listDirectory(currentId);
      const child = children.find((c) => c.name === part);

      if (!child) {
        return null; // Path not found
      }

      currentPath += '/' + part;
      currentId = child.id;

      // Cache this node
      const node = { ...child, path: currentPath };
      this.pathCache.set(currentPath, node);
      this.idToPathCache.set(child.id, currentPath);
    }

    // Get the final node
    const node = await this.api.getFile(currentId);
    const finalNode = { ...node, path: normalized };
    this.pathCache.set(normalized, finalNode);
    this.idToPathCache.set(node.id, normalized);
    return finalNode;
  }

  /**
   * List directory contents
   */
  async listDirectory(path: string): Promise<FileSystemNode[]> {
    const dir = await this.findByPath(path);

    if (!dir) {
      throw new Error(`Directory not found: ${path}`);
    }

    if (dir.type !== 'directory') {
      throw new Error(`Not a directory: ${path}`);
    }

    const children = await this.api.listDirectory(dir.id);

    // Add paths to children
    return children.map((child) => {
      const childPath = path === '/' ? `/${child.name}` : `${path}/${child.name}`;
      const node = { ...child, path: childPath };

      // Cache the node
      this.pathCache.set(childPath, node);
      this.idToPathCache.set(child.id, childPath);

      return node;
    });
  }

  /**
   * Read file contents
   */
  async readFile(path: string): Promise<string> {
    const file = await this.findByPath(path);

    if (!file) {
      throw new Error(`File not found: ${path}`);
    }

    if (file.type !== 'file') {
      throw new Error(`Not a file: ${path}`);
    }

    return file.content || '';
  }

  /**
   * Create a file
   */
  async createFile(path: string, content: string, mimeType: string = 'text/plain'): Promise<void> {
    const parentPath = this.dirname(path);
    const fileName = this.basename(path);

    const parent = await this.findByPath(parentPath);
    if (!parent) {
      throw new Error(`Parent directory not found: ${parentPath}`);
    }

    await this.api.createFile(fileName, parent.id, content, mimeType);

    // Invalidate cache
    this.pathCache.delete(path);
  }

  /**
   * Create a directory
   */
  async createDirectory(path: string): Promise<void> {
    const parentPath = this.dirname(path);
    const dirName = this.basename(path);

    const parent = await this.findByPath(parentPath);
    if (!parent) {
      throw new Error(`Parent directory not found: ${parentPath}`);
    }

    await this.api.createDirectory(dirName, parent.id);

    // Invalidate cache
    this.pathCache.delete(path);
  }

  /**
   * Delete a file or directory
   */
  async delete(path: string): Promise<void> {
    const node = await this.findByPath(path);

    if (!node) {
      throw new Error(`File not found: ${path}`);
    }

    await this.api.deleteFile(node.id);

    // Invalidate cache
    this.pathCache.delete(path);
    this.idToPathCache.delete(node.id);
  }

  /**
   * Move/rename a file or directory
   */
  async move(sourcePath: string, destPath: string): Promise<void> {
    const source = await this.findByPath(sourcePath);

    if (!source) {
      throw new Error(`Source not found: ${sourcePath}`);
    }

    const destParentPath = this.dirname(destPath);
    const destParent = await this.findByPath(destParentPath);

    if (!destParent) {
      throw new Error(`Destination parent not found: ${destParentPath}`);
    }

    await this.api.moveFile(source.id, destParent.id);

    // Invalidate cache
    this.pathCache.delete(sourcePath);
    this.pathCache.delete(destPath);
    this.idToPathCache.delete(source.id);
  }

  /**
   * Copy a file or directory
   */
  async copy(sourcePath: string, destPath: string): Promise<void> {
    const source = await this.findByPath(sourcePath);

    if (!source) {
      throw new Error(`Source not found: ${sourcePath}`);
    }

    const destParentPath = this.dirname(destPath);
    const destName = this.basename(destPath);
    const destParent = await this.findByPath(destParentPath);

    if (!destParent) {
      throw new Error(`Destination parent not found: ${destParentPath}`);
    }

    await this.api.copyFile(source.id, destParent.id, destName);

    // Invalidate cache
    this.pathCache.delete(destPath);
  }

  /**
   * Check if a path exists
   */
  async exists(path: string): Promise<boolean> {
    try {
      const node = await this.findByPath(path);
      return node !== null;
    } catch {
      return false;
    }
  }

  /**
   * Get the path for a node ID
   */
  getPathById(id: string): string | undefined {
    return this.idToPathCache.get(id);
  }

  /**
   * Clear the path cache
   */
  clearCache(): void {
    this.pathCache.clear();
    this.idToPathCache.clear();
  }
}
