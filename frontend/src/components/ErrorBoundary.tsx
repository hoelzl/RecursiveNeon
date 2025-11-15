import { Component, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, errorInfo: string) => ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: string | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo: errorInfo.componentStack || '',
    });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback && this.state.error) {
        return this.props.fallback(this.state.error, this.state.errorInfo || '');
      }

      return (
        <div style={{
          padding: '20px',
          background: '#1a1a2e',
          color: '#e0e0e0',
          borderRadius: '8px',
          border: '2px solid #d32f2f',
        }}>
          <h2 style={{ color: '#d32f2f', marginTop: 0 }}>⚠️ Component Error</h2>
          <p><strong>Error:</strong> {this.state.error?.message || 'Unknown error'}</p>
          <details style={{ marginTop: '1rem' }}>
            <summary style={{ cursor: 'pointer', color: '#00d9ff' }}>Error Details</summary>
            <pre style={{
              marginTop: '0.5rem',
              padding: '1rem',
              background: '#0f3460',
              borderRadius: '4px',
              overflow: 'auto',
              fontSize: '0.85rem',
            }}>
              {this.state.error?.stack}
              {this.state.errorInfo}
            </pre>
          </details>
          <button
            onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              background: '#00d9ff',
              border: 'none',
              borderRadius: '4px',
              color: '#1a1a2e',
              fontWeight: 'bold',
              cursor: 'pointer',
            }}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
