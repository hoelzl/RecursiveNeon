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

// ============================================================================
// Desktop App Types
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

export interface BrowserPage {
  id: string;
  url: string;
  title: string;
  content: string;
}

// ============================================================================
// Calendar Types
// ============================================================================

export type RecurrenceFrequency = 'daily' | 'weekly' | 'monthly' | 'yearly';

export interface RecurrenceRule {
  frequency: RecurrenceFrequency;
  interval: number;  // Every N days/weeks/months/years
  count?: number;    // Number of occurrences
  until?: string;    // ISO 8601 datetime string - end date for recurrence
  by_day?: number[]; // Days of week (0=Sunday, 6=Saturday)
  by_month_day?: number[]; // Days of month (1-31)
}

export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  start_time: string;  // ISO 8601 datetime string
  end_time: string;    // ISO 8601 datetime string
  location?: string;
  color?: string;      // Hex color code
  notes?: string;
  all_day: boolean;
  recurrence_rule?: RecurrenceRule;
  recurrence_id?: string;  // For event instances, links to parent recurring event
  created_at: string;  // ISO 8601 datetime string
  updated_at: string;  // ISO 8601 datetime string
}

export interface CreateEventData {
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  location?: string;
  color?: string;
  notes?: string;
  all_day?: boolean;
  recurrence_rule?: RecurrenceRule;
}

export type CalendarView = 'month' | 'week' | 'day' | 'list';

export interface CalendarState {
  events: CalendarEvent[];
  selectedDate: Date;
  currentView: CalendarView;
  selectedEvent: CalendarEvent | null;
}

// ============================================================================
// Media Viewer Types
// ============================================================================

export interface TextMessage {
  text: string | null;  // null means pause/blank screen
  duration: number;     // Duration in seconds
  size: number;         // Font size in pixels
  color: string;        // Text color (CSS color)
  x: number;            // X position (percentage 0-100)
  y: number;            // Y position (percentage 0-100)
  font_weight: string;  // CSS font-weight
}

export type SpiralStyle = 'blackwhite' | 'colorful';

export interface MediaViewerConfig {
  spiral_style: SpiralStyle;
  rotation_speed: number;  // Speed multiplier
  messages: TextMessage[];
  loop: boolean;  // Whether to loop messages
}
