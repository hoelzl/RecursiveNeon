/**
 * Time Service for frontend time synchronization
 *
 * This service manages game time on the frontend by:
 * - Syncing with backend authoritative time
 * - Interpolating time between sync points
 * - Handling time dilation
 * - Detecting and correcting drift
 */

export interface TimeState {
  currentTime: Date;
  timeDilation: number;
  isPaused: boolean;
}

export interface TimeUpdate {
  current_time: string;      // ISO 8601
  time_dilation: number;
  is_paused: boolean;
  real_time: number;
  update_type?: string;
}

type TimeUpdateCallback = (state: TimeState) => void;

export class TimeService {
  private anchorGameTime: Date;
  private anchorRealTime: number;
  private timeDilation: number;
  private isPaused: boolean;
  private subscribers: TimeUpdateCallback[];
  private syncInterval: number | null;
  private wsClient: any | null;  // WebSocket client reference

  constructor() {
    this.anchorGameTime = new Date();
    this.anchorRealTime = performance.now();
    this.timeDilation = 1.0;
    this.isPaused = false;
    this.subscribers = [];
    this.syncInterval = null;
    this.wsClient = null;
  }

  /**
   * Initialize with WebSocket client and start syncing.
   */
  initialize(wsClient: any): void {
    this.wsClient = wsClient;

    // Request initial sync
    this.sync();

    // Start periodic sync (every 5 seconds)
    this.syncInterval = window.setInterval(() => {
      this.sync();
    }, 5000);
  }

  /**
   * Clean up resources.
   */
  destroy(): void {
    if (this.syncInterval !== null) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  /**
   * Get current game time (interpolated).
   */
  getCurrentTime(): Date {
    if (this.isPaused) {
      return new Date(this.anchorGameTime);
    }

    const realElapsed = (performance.now() - this.anchorRealTime) / 1000; // seconds
    const gameElapsed = realElapsed * this.timeDilation;
    const currentTime = new Date(this.anchorGameTime.getTime() + gameElapsed * 1000);

    return currentTime;
  }

  /**
   * Get current time dilation.
   */
  getTimeDilation(): number {
    return this.timeDilation;
  }

  /**
   * Check if time is paused.
   */
  isTimePaused(): boolean {
    return this.isPaused;
  }

  /**
   * Get complete time state.
   */
  getState(): TimeState {
    return {
      currentTime: this.getCurrentTime(),
      timeDilation: this.timeDilation,
      isPaused: this.isPaused,
    };
  }

  /**
   * Subscribe to time updates.
   */
  subscribe(callback: TimeUpdateCallback): () => void {
    this.subscribers.push(callback);
    return () => {
      const index = this.subscribers.indexOf(callback);
      if (index > -1) {
        this.subscribers.splice(index, 1);
      }
    };
  }

  /**
   * Request sync from backend.
   */
  async sync(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'get_time',
      },
    });
  }

  /**
   * Handle time update from backend.
   */
  handleTimeUpdate(message: any): void {
    const data: TimeUpdate = message.data;

    // Calculate expected time based on current anchor
    const expectedTime = this.getCurrentTime();
    const backendTime = new Date(data.current_time);

    // Calculate drift
    const drift = Math.abs(backendTime.getTime() - expectedTime.getTime());

    if (drift > 2000) { // > 2 seconds
      console.warn(`Time drift detected: ${drift}ms, resyncing`);
    }

    // Update anchor point (this corrects any drift)
    this.anchorGameTime = backendTime;
    this.anchorRealTime = performance.now();
    this.timeDilation = data.time_dilation;
    this.isPaused = data.is_paused;

    // Notify subscribers
    this.notifySubscribers();
  }

  /**
   * Notify all subscribers of state change.
   */
  private notifySubscribers(): void {
    const state = this.getState();
    this.subscribers.forEach(callback => {
      try {
        callback(state);
      } catch (error) {
        console.error('Error in time update callback:', error);
      }
    });
  }

  // Control methods (send commands to backend)

  async setTimeDilation(dilation: number): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'set_dilation',
        value: dilation,
      },
    });
  }

  async pause(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'pause',
      },
    });
  }

  async resume(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'resume',
      },
    });
  }

  async jumpTo(targetTime: Date): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'jump_to',
        target_time: targetTime.toISOString(),
      },
    });
  }

  async advance(seconds: number): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'advance',
        value: seconds,
      },
    });
  }

  async rewind(seconds: number): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'rewind',
        value: seconds,
      },
    });
  }
}

export const timeService = new TimeService();
