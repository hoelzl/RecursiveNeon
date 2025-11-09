/**
 * Type definitions for Recursive://Neon
 */

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
