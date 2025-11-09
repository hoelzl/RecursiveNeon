import { FileNode } from '../types';

/**
 * Configuration for file type associations
 * Maps MIME types and file extensions to application types
 */
export interface FileTypeAssociation {
  /** MIME type pattern (e.g., 'text/plain', 'image/*') */
  mimeType?: string;
  /** File extension (e.g., '.txt', '.png') */
  extension?: string;
  /** Application type identifier */
  appType: string;
  /** Display name for the application */
  appName: string;
  /** Icon for the file type (optional) */
  icon?: string;
}

/**
 * Default file type associations
 * This can be extended or made configurable in the future
 */
export const DEFAULT_FILE_TYPE_ASSOCIATIONS: FileTypeAssociation[] = [
  // Text files
  { mimeType: 'text/plain', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.txt', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.md', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.json', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.js', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.ts', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.tsx', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.jsx', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.css', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.html', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.xml', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },
  { extension: '.py', appType: 'text-editor', appName: 'Text Editor', icon: '📝' },

  // Image files
  { mimeType: 'image/png', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { mimeType: 'image/jpeg', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { mimeType: 'image/jpg', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { mimeType: 'image/gif', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { mimeType: 'image/webp', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { mimeType: 'image/svg+xml', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { extension: '.png', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { extension: '.jpg', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { extension: '.jpeg', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { extension: '.gif', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { extension: '.webp', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
  { extension: '.svg', appType: 'image-viewer', appName: 'Image Viewer', icon: '🖼️' },
];

/**
 * Custom file type associations that can be configured by the user
 * This allows for extending or overriding default associations
 */
let customAssociations: FileTypeAssociation[] = [];

/**
 * Set custom file type associations
 * @param associations Array of custom file type associations
 */
export function setCustomFileTypeAssociations(associations: FileTypeAssociation[]): void {
  customAssociations = associations;
}

/**
 * Get all file type associations (custom + default)
 * Custom associations take precedence over default ones
 */
export function getAllFileTypeAssociations(): FileTypeAssociation[] {
  return [...customAssociations, ...DEFAULT_FILE_TYPE_ASSOCIATIONS];
}

/**
 * Get the file extension from a filename
 * @param filename The filename to extract extension from
 * @returns The file extension (e.g., '.txt') or null if no extension
 */
function getFileExtension(filename: string): string | null {
  const lastDot = filename.lastIndexOf('.');
  if (lastDot === -1 || lastDot === 0) return null;
  return filename.substring(lastDot).toLowerCase();
}

/**
 * Check if a MIME type matches a pattern
 * Supports wildcards (e.g., 'image/*' matches 'image/png')
 * @param mimeType The actual MIME type
 * @param pattern The pattern to match against
 */
function mimeTypeMatches(mimeType: string, pattern: string): boolean {
  if (pattern.endsWith('/*')) {
    const prefix = pattern.slice(0, -2);
    return mimeType.startsWith(prefix + '/');
  }
  return mimeType === pattern;
}

/**
 * Get the application type for a given file
 * @param file The file node to check
 * @returns The application type or null if no association found
 */
export function getAppTypeForFile(file: FileNode): string | null {
  if (file.type === 'directory') return null;

  const associations = getAllFileTypeAssociations();
  const extension = getFileExtension(file.name);

  // First, try to match by MIME type
  if (file.mime_type) {
    for (const assoc of associations) {
      if (assoc.mimeType && mimeTypeMatches(file.mime_type, assoc.mimeType)) {
        return assoc.appType;
      }
    }
  }

  // Then, try to match by file extension
  if (extension) {
    for (const assoc of associations) {
      if (assoc.extension && assoc.extension.toLowerCase() === extension) {
        return assoc.appType;
      }
    }
  }

  return null;
}

/**
 * Get the application name for a given file
 * @param file The file node to check
 * @returns The application name or null if no association found
 */
export function getAppNameForFile(file: FileNode): string | null {
  if (file.type === 'directory') return null;

  const associations = getAllFileTypeAssociations();
  const extension = getFileExtension(file.name);

  // First, try to match by MIME type
  if (file.mime_type) {
    for (const assoc of associations) {
      if (assoc.mimeType && mimeTypeMatches(file.mime_type, assoc.mimeType)) {
        return assoc.appName;
      }
    }
  }

  // Then, try to match by file extension
  if (extension) {
    for (const assoc of associations) {
      if (assoc.extension && assoc.extension.toLowerCase() === extension) {
        return assoc.appName;
      }
    }
  }

  return null;
}

/**
 * Check if a file can be opened with an application
 * @param file The file node to check
 * @returns True if the file has an associated application
 */
export function canOpenFile(file: FileNode): boolean {
  return getAppTypeForFile(file) !== null;
}

/**
 * Get all supported application types
 * @returns Array of unique application type identifiers
 */
export function getSupportedAppTypes(): string[] {
  const associations = getAllFileTypeAssociations();
  const appTypes = new Set(associations.map(a => a.appType));
  return Array.from(appTypes);
}

/**
 * Add a new file type association
 * @param association The file type association to add
 */
export function addFileTypeAssociation(association: FileTypeAssociation): void {
  customAssociations.push(association);
}

/**
 * Remove file type associations for a specific app type
 * @param appType The application type to remove associations for
 */
export function removeFileTypeAssociationsForApp(appType: string): void {
  customAssociations = customAssociations.filter(a => a.appType !== appType);
}
