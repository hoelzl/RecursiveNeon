import React, { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  gameName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class MinigameErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Minigame error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="minigame-error-boundary">
          <div className="error-content">
            <h2 className="error-title">⚠️ Game Error</h2>
            <p className="error-message">
              {this.props.gameName || 'The minigame'} encountered an error and had to stop.
            </p>
            <div className="error-details">
              <code>{this.state.error?.message}</code>
            </div>
            <button onClick={this.handleReset} className="btn-retry">
              Try Again
            </button>
          </div>

          <style>{`
            .minigame-error-boundary {
              display: flex;
              align-items: center;
              justify-content: center;
              min-height: 400px;
              background: linear-gradient(135deg, #1a0000 0%, #0a0a0a 100%);
              color: #ff0000;
              font-family: 'Courier New', monospace;
              padding: 2rem;
            }

            .error-content {
              text-align: center;
              max-width: 500px;
              padding: 2rem;
              background: rgba(255, 0, 0, 0.1);
              border: 2px solid #ff0000;
              border-radius: 8px;
            }

            .error-title {
              font-size: 1.5rem;
              margin: 0 0 1rem 0;
              color: #ff0000;
            }

            .error-message {
              font-size: 1rem;
              margin-bottom: 1.5rem;
              color: #ff6666;
            }

            .error-details {
              background: #0a0a0a;
              padding: 1rem;
              border-radius: 4px;
              margin-bottom: 1.5rem;
              max-height: 150px;
              overflow: auto;
            }

            .error-details code {
              color: #ff9999;
              font-size: 0.9rem;
              word-break: break-word;
            }

            .btn-retry {
              padding: 0.75rem 1.5rem;
              background: #ff0000;
              color: #fff;
              border: none;
              border-radius: 4px;
              cursor: pointer;
              font-family: 'Courier New', monospace;
              font-weight: bold;
              font-size: 1rem;
              transition: all 0.2s;
            }

            .btn-retry:hover {
              background: #ff3333;
              transform: translateY(-2px);
            }
          `}</style>
        </div>
      );
    }

    return this.props.children;
  }
}
