/**
 * Hook for managing WebSocket event handlers
 *
 * Registers and manages all WebSocket message handlers for the application.
 * Extracted from App.tsx for better testability and maintainability.
 */

import { useEffect } from 'react';
import { useGameStoreContext } from '../contexts/GameStoreContext';
import { useWebSocket } from '../contexts/WebSocketContext';
import { timeService } from '../services/timeService';
import { settingsService } from '../services/settingsService';

export function useWebSocketHandlers(): void {
  const { setNPCs, setSystemStatus } = useGameStoreContext();
  const wsClient = useWebSocket();

  useEffect(() => {
    // NPC list handler
    const handleNPCsList = (msg: any) => {
      setNPCs(msg.data.npcs);
    };

    // System status handler
    const handleStatus = (msg: any) => {
      setSystemStatus(msg.data);
    };

    // Error handler
    const handleError = (msg: any) => {
      console.error('Server error:', msg.data);
    };

    // Time service handlers
    const handleTimeResponse = (msg: any) => {
      timeService.handleTimeUpdate(msg);
    };

    const handleTimeUpdate = (msg: any) => {
      timeService.handleTimeUpdate(msg);
    };

    // Settings service handlers
    const handleSettingsResponse = (msg: any) => {
      settingsService.handleSettingsResponse(msg);
    };

    const handleSettingUpdate = (msg: any) => {
      settingsService.handleSettingUpdate(msg);
    };

    const handleSettingsUpdate = (msg: any) => {
      settingsService.handleSettingsUpdate(msg);
    };

    // Register all handlers
    wsClient.on('npcs_list', handleNPCsList);
    wsClient.on('status', handleStatus);
    wsClient.on('error', handleError);
    wsClient.on('time_response', handleTimeResponse);
    wsClient.on('time_update', handleTimeUpdate);
    wsClient.on('settings_response', handleSettingsResponse);
    wsClient.on('setting_update', handleSettingUpdate);
    wsClient.on('settings_update', handleSettingsUpdate);

    // Cleanup: remove all handlers on unmount
    return () => {
      wsClient.off('npcs_list', handleNPCsList);
      wsClient.off('status', handleStatus);
      wsClient.off('error', handleError);
      wsClient.off('time_response', handleTimeResponse);
      wsClient.off('time_update', handleTimeUpdate);
      wsClient.off('settings_response', handleSettingsResponse);
      wsClient.off('setting_update', handleSettingUpdate);
      wsClient.off('settings_update', handleSettingsUpdate);
    };
  }, [wsClient, setNPCs, setSystemStatus]); // Dependencies for handlers
}
