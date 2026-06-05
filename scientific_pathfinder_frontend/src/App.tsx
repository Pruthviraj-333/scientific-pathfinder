import { useState } from 'react';
import { FlaskConical, RefreshCw } from 'lucide-react';
import SearchInterface from './components/SearchInterface';
import ProgressTracker from './components/ProgressTracker';
import ResultsDisplay from './components/ResultsDisplay';
import ErrorBoundary from './components/ErrorBoundary';
import { ResearchSession } from './types';
import './App.css';

function App() {
  const [session, setSession] = useState<ResearchSession | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-blue-800/30 bg-slate-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <FlaskConical className="w-8 h-8 text-blue-400" />
                Scientific Pathfinder
              </h1>
              <p className="mt-1 text-blue-200/70">
                AI-Powered Research Gap Discovery
              </p>
            </div>
            <div className="flex items-center gap-4">
              <a
                href="https://github.com/yourusername/scientific-pathfinder"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-200/70 hover:text-blue-200 transition-colors"
              >
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {!session ? (
          <SearchInterface 
            onSessionStart={(newSession) => {
              setSession(newSession);
              setIsProcessing(true);
            }}
          />
        ) : (
          <div className="space-y-8">
            <ProgressTracker 
              session={session}
              onComplete={() => setIsProcessing(false)}
            />
            {!isProcessing && session.result && (
              <ResultsDisplay 
                result={session.result} 
                sessionId={session.session_id}
              />
            )}
          </div>
        )}

        {/* Reset Button */}
        {session && (
          <div className="mt-8 text-center">
            <button
              onClick={() => {
                setSession(null);
                setIsProcessing(false);
              }}
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Start New Research
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-blue-800/30 mt-20 py-8 bg-slate-900/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-blue-200/50">
          <p>Built with LangGraph, Neo4j, and Groq LLM</p>
          <p className="mt-2 text-sm">© 2024 Scientific Pathfinder</p>
        </div>
      </footer>
    </div>
    </ErrorBoundary>
  );
}

export default App;