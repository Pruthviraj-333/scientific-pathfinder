import { useState } from 'react';
import { Search } from 'lucide-react';

interface Props {
  onSessionStart: (session: any) => void;
}

export default function SearchInterface({ onSessionStart }: Props) {
  const [topic, setTopic] = useState('');
  const [maxPapers, setMaxPapers] = useState(10);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/research/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, max_papers: maxPapers }),
      });

      const data = await response.json();
      onSessionStart({ ...data, topic, max_papers: maxPapers });
    } catch (error) {
      console.error('Failed to start research:', error);
      alert('Failed to connect to backend. Make sure it\'s running on port 8000');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-blue-500/20 p-8">
        <h2 className="text-2xl font-bold text-white mb-6">
          🔍 Start Your Research
        </h2>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-blue-200 mb-2">
              Research Topic
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., vision transformers for medical imaging"
              className="w-full px-4 py-3 bg-slate-900/50 border border-blue-500/30 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-blue-200 mb-2">
              Maximum Papers: {maxPapers}
            </label>
            <input
              type="range"
              min="5"
              max="50"
              value={maxPapers}
              onChange={(e) => setMaxPapers(Number(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>5</span>
              <span>50</span>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !topic}
            className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-all transform hover:scale-105"
          >
            {loading ? (
              <>
                <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
                Initializing...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                Discover Research Gaps
              </>
            )}
          </button>
        </form>

        <div className="mt-6 p-4 bg-blue-900/20 rounded-lg">
          <p className="text-sm text-blue-200/70">
            💡 <strong>Tip:</strong> Be specific! "vision transformers medical imaging" is better than just "AI"
          </p>
        </div>
      </div>
    </div>
  );
}