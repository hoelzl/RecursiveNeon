/**
 * Tests for TimeService
 *
 * Tests frontend time synchronization and interpolation.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { TimeService } from './timeService';

describe('TimeService', () => {
  let timeService: TimeService;
  let mockWsClient: any;

  beforeEach(() => {
    timeService = new TimeService();

    // Mock WebSocket client
    mockWsClient = {
      sendMessage: vi.fn(),
    };

    // Mock performance.now()
    vi.spyOn(performance, 'now').mockReturnValue(1000);
  });

  afterEach(() => {
    timeService.destroy();
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize with default values', () => {
      const state = timeService.getState();

      expect(state.timeDilation).toBe(1.0);
      expect(state.isPaused).toBe(false);
    });

    it('should initialize with WebSocket client', () => {
      timeService.initialize(mockWsClient);

      // Should request initial sync
      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'time',
        data: {
          action: 'get_time',
        },
      });
    });

    it('should set up periodic sync interval', () => {
      vi.useFakeTimers();

      timeService.initialize(mockWsClient);

      // Fast-forward 5 seconds
      vi.advanceTimersByTime(5000);

      // Should have called sync again
      expect(mockWsClient.sendMessage).toHaveBeenCalledTimes(2);

      vi.useRealTimers();
    });
  });

  describe('Time Interpolation', () => {
    it('should interpolate time correctly with 1.0 dilation', () => {
      const anchorTime = new Date('2048-11-13T08:00:00Z');

      timeService.handleTimeUpdate({
        data: {
          current_time: anchorTime.toISOString(),
          time_dilation: 1.0,
          is_paused: false,
          real_time: 1000,
        },
      });

      // Advance 1 second in real time
      vi.spyOn(performance, 'now').mockReturnValue(2000);

      const currentTime = timeService.getCurrentTime();
      const expected = new Date(anchorTime.getTime() + 1000);

      expect(Math.abs(currentTime.getTime() - expected.getTime())).toBeLessThan(100);
    });

    it('should interpolate time correctly with 2.0 dilation', () => {
      const anchorTime = new Date('2048-11-13T08:00:00Z');

      timeService.handleTimeUpdate({
        data: {
          current_time: anchorTime.toISOString(),
          time_dilation: 2.0,
          is_paused: false,
          real_time: 1000,
        },
      });

      // Advance 1 second in real time
      vi.spyOn(performance, 'now').mockReturnValue(2000);

      const currentTime = timeService.getCurrentTime();
      const expected = new Date(anchorTime.getTime() + 2000); // 2 game seconds

      expect(Math.abs(currentTime.getTime() - expected.getTime())).toBeLessThan(100);
    });

    it('should interpolate time correctly with 0.5 dilation', () => {
      const anchorTime = new Date('2048-11-13T08:00:00Z');

      timeService.handleTimeUpdate({
        data: {
          current_time: anchorTime.toISOString(),
          time_dilation: 0.5,
          is_paused: false,
          real_time: 1000,
        },
      });

      // Advance 2 seconds in real time
      vi.spyOn(performance, 'now').mockReturnValue(3000);

      const currentTime = timeService.getCurrentTime();
      const expected = new Date(anchorTime.getTime() + 1000); // 1 game second

      expect(Math.abs(currentTime.getTime() - expected.getTime())).toBeLessThan(100);
    });

    it('should not advance time when paused', () => {
      const anchorTime = new Date('2048-11-13T08:00:00Z');

      timeService.handleTimeUpdate({
        data: {
          current_time: anchorTime.toISOString(),
          time_dilation: 0.0,
          is_paused: true,
          real_time: 1000,
        },
      });

      // Advance 5 seconds in real time
      vi.spyOn(performance, 'now').mockReturnValue(6000);

      const currentTime = timeService.getCurrentTime();

      expect(currentTime.getTime()).toBe(anchorTime.getTime());
    });
  });

  describe('State Management', () => {
    it('should return current time dilation', () => {
      timeService.handleTimeUpdate({
        data: {
          current_time: new Date().toISOString(),
          time_dilation: 3.5,
          is_paused: false,
          real_time: 1000,
        },
      });

      expect(timeService.getTimeDilation()).toBe(3.5);
    });

    it('should return paused state', () => {
      timeService.handleTimeUpdate({
        data: {
          current_time: new Date().toISOString(),
          time_dilation: 0.0,
          is_paused: true,
          real_time: 1000,
        },
      });

      expect(timeService.isTimePaused()).toBe(true);
    });

    it('should return complete state', () => {
      const anchorTime = new Date('2048-11-13T08:00:00Z');

      timeService.handleTimeUpdate({
        data: {
          current_time: anchorTime.toISOString(),
          time_dilation: 2.0,
          is_paused: false,
          real_time: 1000,
        },
      });

      const state = timeService.getState();

      expect(state.timeDilation).toBe(2.0);
      expect(state.isPaused).toBe(false);
      expect(state.currentTime).toBeInstanceOf(Date);
    });
  });

  describe('Subscriptions', () => {
    it('should notify subscribers on update', () => {
      const callback = vi.fn();

      timeService.subscribe(callback);

      timeService.handleTimeUpdate({
        data: {
          current_time: new Date().toISOString(),
          time_dilation: 1.0,
          is_paused: false,
          real_time: 1000,
        },
      });

      expect(callback).toHaveBeenCalled();
    });

    it('should allow unsubscribing', () => {
      const callback = vi.fn();

      const unsubscribe = timeService.subscribe(callback);
      unsubscribe();

      timeService.handleTimeUpdate({
        data: {
          current_time: new Date().toISOString(),
          time_dilation: 1.0,
          is_paused: false,
          real_time: 1000,
        },
      });

      expect(callback).not.toHaveBeenCalled();
    });

    it('should notify multiple subscribers', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();

      timeService.subscribe(callback1);
      timeService.subscribe(callback2);

      timeService.handleTimeUpdate({
        data: {
          current_time: new Date().toISOString(),
          time_dilation: 1.0,
          is_paused: false,
          real_time: 1000,
        },
      });

      expect(callback1).toHaveBeenCalled();
      expect(callback2).toHaveBeenCalled();
    });
  });

  describe('Control Methods', () => {
    beforeEach(() => {
      timeService.initialize(mockWsClient);
      mockWsClient.sendMessage.mockClear();
    });

    it('should send set_dilation message', async () => {
      await timeService.setTimeDilation(2.5);

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'time',
        data: {
          action: 'set_dilation',
          value: 2.5,
        },
      });
    });

    it('should send pause message', async () => {
      await timeService.pause();

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'time',
        data: {
          action: 'pause',
        },
      });
    });

    it('should send resume message', async () => {
      await timeService.resume();

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'time',
        data: {
          action: 'resume',
        },
      });
    });

    it('should send jump_to message', async () => {
      const targetTime = new Date('2050-01-01T00:00:00Z');

      await timeService.jumpTo(targetTime);

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'time',
        data: {
          action: 'jump_to',
          target_time: targetTime.toISOString(),
        },
      });
    });

    it('should send advance message', async () => {
      await timeService.advance(3600);

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'time',
        data: {
          action: 'advance',
          value: 3600,
        },
      });
    });

    it('should send rewind message', async () => {
      await timeService.rewind(7200);

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'time',
        data: {
          action: 'rewind',
          value: 7200,
        },
      });
    });
  });

  describe('Drift Detection', () => {
    it('should log warning when drift exceeds 2 seconds', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const anchorTime = new Date('2048-11-13T08:00:00Z');

      // Set initial anchor
      timeService.handleTimeUpdate({
        data: {
          current_time: anchorTime.toISOString(),
          time_dilation: 1.0,
          is_paused: false,
          real_time: 1000,
        },
      });

      // Update with time that's way off (5 seconds ahead)
      const driftedTime = new Date(anchorTime.getTime() + 5000);

      timeService.handleTimeUpdate({
        data: {
          current_time: driftedTime.toISOString(),
          time_dilation: 1.0,
          is_paused: false,
          real_time: 1100, // Only 0.1 seconds passed in real time
        },
      });

      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('drift'));

      consoleSpy.mockRestore();
    });
  });

  describe('Cleanup', () => {
    it('should clear interval on destroy', () => {
      vi.useFakeTimers();

      timeService.initialize(mockWsClient);
      mockWsClient.sendMessage.mockClear();

      timeService.destroy();

      // Fast-forward 10 seconds
      vi.advanceTimersByTime(10000);

      // Should not have called sync
      expect(mockWsClient.sendMessage).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });
});
