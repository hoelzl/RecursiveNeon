/**
 * Type definitions for Recursive://Neon
 *
 * These types mirror the backend Pydantic models.
 * Presentation-agnostic — used by both CLI/terminal and GUI interfaces.
 */

// ============================================================================
// NPC Types
// ============================================================================

export interface NPC {
  id: string;
  name: string;
  personality: string;
  role: string;
  background: string;
  occupation: string;
  location: string;
  greeting: string;
  conversation_style: string;
  topics_of_interest: string[];
  secrets?: string[];
  avatar: string;
  theme_color: string;
  memory: {
    npc_id: string;
    conversation_history: ConversationMessage[];
    facts_learned: string[];
    relationship_level: number;
    last_interaction: string | null;
  };
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatMessage {
  npc_id: string;
  npc_name: string;
  message: string;
  timestamp: string;
}

// ============================================================================
// System Types
// ============================================================================

export interface SystemStatus {
  status: string;
  system: {
    status: string;
    ollama_running: boolean;
    ollama_models_loaded: string[];
    npcs_loaded: number;
    uptime_seconds: number;
    last_error: string | null;
  };
  timestamp: string;
}

export interface WebSocketMessage {
  type: string;
  data: any;
}

// ============================================================================
// Window Management (for desktop GUI)
// ============================================================================

export interface WindowState {
  id: string;
  title: string;
  type: string;
  content: any;
  position: { x: number; y: number };
  size: { width: number; height: number };
  zIndex: number;
  minimized: boolean;
}

// ============================================================================
// Virtual Filesystem
// ============================================================================

export interface FileNode {
  id: string;
  name: string;
  type: "file" | "directory";
  parent_id?: string | null;
  content?: string | null;
  mime_type?: string | null;
  created_at?: string;
  updated_at?: string;
}

// ============================================================================
// Notes & Tasks
// ============================================================================

export interface Note {
  id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  title: string;
  completed: boolean;
  parent_id?: string | null;
}

export interface TaskList {
  id: string;
  name: string;
  tasks: Task[];
}
