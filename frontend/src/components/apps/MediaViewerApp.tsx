/**
 * Media Viewer App - Hypnotic spiral display with text overlays
 *
 * Marketed as "MindSync Wellness" - a health and relaxation feature.
 * In-universe, used by corporations and government for subtle manipulation.
 */
import { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { MediaViewerConfig, SpiralStyle } from '../../types';

export function MediaViewerApp() {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();

  const [config, setConfig] = useState<MediaViewerConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [showSettings, setShowSettings] = useState(false);

  // Animation state
  const rotationRef = useRef(0);

  // Load config on mount
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const loadedConfig = await api.getMediaViewerConfig();
      setConfig(loadedConfig);
    } catch (error) {
      console.error('Failed to load media viewer config:', error);
    } finally {
      setLoading(false);
    }
  };

  // Spiral animation loop
  useEffect(() => {
    if (!isPlaying || !canvasRef.current || !config) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const animate = () => {
      // Update rotation
      rotationRef.current += 0.02 * config.rotation_speed;

      // Clear canvas
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw spiral
      drawSpiral(ctx, canvas.width, canvas.height, config.spiral_style);

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, config]);

  // Text message cycling
  useEffect(() => {
    if (!isPlaying || !config || config.messages.length === 0) return;

    const currentMessage = config.messages[currentMessageIndex];
    const duration = currentMessage.duration * 1000; // Convert to milliseconds

    const timer = setTimeout(() => {
      if (config.loop) {
        setCurrentMessageIndex((prev) => (prev + 1) % config.messages.length);
      } else if (currentMessageIndex < config.messages.length - 1) {
        setCurrentMessageIndex((prev) => prev + 1);
      } else {
        // Reached end, stop playing
        setIsPlaying(false);
      }
    }, duration);

    return () => clearTimeout(timer);
  }, [isPlaying, currentMessageIndex, config]);

  const drawSpiral = (
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number,
    style: SpiralStyle
  ) => {
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = Math.min(width, height) / 2;

    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.rotate(rotationRef.current);

    if (style === 'blackwhite') {
      // Black and white spiral
      const segments = 50;
      for (let i = 0; i < segments; i++) {
        const angle = (i / segments) * Math.PI * 2;
        const nextAngle = ((i + 1) / segments) * Math.PI * 2;

        ctx.fillStyle = i % 2 === 0 ? '#FFFFFF' : '#000000';
        ctx.beginPath();
        ctx.moveTo(0, 0);

        // Create spiral effect
        const numCoils = 8;
        for (let r = 0; r <= maxRadius; r += 5) {
          const spiralAngle = angle + (r / maxRadius) * Math.PI * 2 * numCoils;
          ctx.lineTo(
            Math.cos(spiralAngle) * r,
            Math.sin(spiralAngle) * r
          );
        }

        for (let r = maxRadius; r >= 0; r -= 5) {
          const spiralAngle = nextAngle + (r / maxRadius) * Math.PI * 2 * numCoils;
          ctx.lineTo(
            Math.cos(spiralAngle) * r,
            Math.sin(spiralAngle) * r
          );
        }

        ctx.closePath();
        ctx.fill();
      }
    } else {
      // Colorful spiral
      const numCoils = 6;
      const steps = 360;

      for (let i = 0; i < steps; i++) {
        const angle = (i / steps) * Math.PI * 2;
        const radius = (i / steps) * maxRadius;
        const spiralAngle = angle * numCoils;

        // Rainbow colors
        const hue = (i / steps * 360 + rotationRef.current * 100) % 360;
        ctx.strokeStyle = `hsl(${hue}, 80%, 60%)`;
        ctx.lineWidth = 3;

        if (i > 0) {
          const prevAngle = ((i - 1) / steps) * Math.PI * 2 * numCoils;
          const prevRadius = ((i - 1) / steps) * maxRadius;

          ctx.beginPath();
          ctx.moveTo(
            Math.cos(prevAngle) * prevRadius,
            Math.sin(prevAngle) * prevRadius
          );
          ctx.lineTo(
            Math.cos(spiralAngle) * radius,
            Math.sin(spiralAngle) * radius
          );
          ctx.stroke();
        }
      }
    }

    ctx.restore();
  };

  const handleStart = () => {
    setIsPlaying(true);
    setCurrentMessageIndex(0);
  };

  const handleStop = () => {
    setIsPlaying(false);
    setCurrentMessageIndex(0);
  };

  const handleStyleChange = async (newStyle: SpiralStyle) => {
    try {
      const updatedConfig = await api.setMediaViewerStyle(newStyle);
      setConfig(updatedConfig);
    } catch (error) {
      console.error('Failed to update style:', error);
    }
  };

  if (loading) {
    return <div className="media-viewer-loading">Loading MindSync Wellness...</div>;
  }

  if (!config) {
    return <div className="media-viewer-error">Failed to load configuration</div>;
  }

  const currentMessage = config.messages[currentMessageIndex];

  return (
    <div className="media-viewer-app">
      {/* Settings Panel */}
      {showSettings && (
        <div className="media-viewer-settings">
          <h3>Settings</h3>
          <div className="settings-group">
            <label>Spiral Style:</label>
            <select
              value={config.spiral_style}
              onChange={(e) => handleStyleChange(e.target.value as SpiralStyle)}
            >
              <option value="blackwhite">Black & White</option>
              <option value="colorful">Colorful</option>
            </select>
          </div>
          <button onClick={() => setShowSettings(false)}>Close</button>
        </div>
      )}

      {/* Main Canvas */}
      <div className="media-viewer-canvas-container">
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          className="media-viewer-canvas"
        />

        {/* Text Overlay */}
        {isPlaying && currentMessage && currentMessage.text && (
          <div
            className="media-viewer-text-overlay"
            style={{
              fontSize: `${currentMessage.size}px`,
              color: currentMessage.color,
              fontWeight: currentMessage.font_weight,
              left: `${currentMessage.x}%`,
              top: `${currentMessage.y}%`,
              transform: 'translate(-50%, -50%)',
            }}
          >
            {currentMessage.text}
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="media-viewer-controls">
        {!isPlaying ? (
          <button onClick={handleStart} className="media-viewer-btn-primary">
            Start Wellness Session
          </button>
        ) : (
          <button onClick={handleStop} className="media-viewer-btn-secondary">
            Stop
          </button>
        )}

        <button
          onClick={() => setShowSettings(!showSettings)}
          className="media-viewer-btn-secondary"
        >
          ⚙️ Settings
        </button>

        {isPlaying && (
          <div className="media-viewer-status">
            Message {currentMessageIndex + 1} of {config.messages.length}
          </div>
        )}
      </div>

      {/* Branding */}
      <div className="media-viewer-branding">
        <div className="media-viewer-logo">MindSync™ Wellness</div>
        <div className="media-viewer-tagline">
          Enhancing productivity through relaxation
        </div>
      </div>
    </div>
  );
}
