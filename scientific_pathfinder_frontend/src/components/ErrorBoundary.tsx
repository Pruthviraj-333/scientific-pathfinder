import React, { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4">
          <div className="max-w-2xl w-full bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-red-500/20 p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 bg-red-500/10 rounded-lg">
                <AlertTriangle className="w-8 h-8 text-red-500" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Something went wrong</h1>
                <p className="text-slate-400 text-sm mt-1">
                  The application encountered an unexpected error
                </p>
              </div>
            </div>

            {this.state.error && (
              <div className="bg-slate-900/50 rounded-lg p-4 mb-6">
                <p className="text-red-400 font-mono text-sm mb-2">
                  {this.state.error.toString()}
                </p>
                {this.state.errorInfo && (
                  <details className="mt-2">
                    <summary className="text-slate-400 text-xs cursor-pointer hover:text-slate-300">
                      Stack trace
                    </summary>
                    <pre className="text-xs text-slate-500 mt-2 overflow-auto max-h-40">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </details>
                )}
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Reload Application
              </button>
              <button
                onClick={() => window.location.href = '/'}
                className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                Go Home
              </button>
            </div>

            <div className="mt-6 p-4 bg-blue-900/20 rounded-lg">
              <p className="text-sm text-blue-200">
                💡 <strong>Tip:</strong> If this error persists, try clearing your browser cache or 
                checking the browser console for more details.
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}