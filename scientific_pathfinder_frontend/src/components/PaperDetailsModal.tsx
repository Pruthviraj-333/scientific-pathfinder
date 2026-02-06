import { X, ExternalLink, Users, Calendar, BookOpen, Quote } from 'lucide-react';

interface Paper {
  paper_id: string;
  title: string;
  abstract: string;
  authors: string[];
  year: number;
  citation_count: number;
  url?: string;
  venue?: string;
  entities?: {
    methods: string[];
    datasets: string[];
    metrics: string[];
  };
}

interface Props {
  paper: Paper;
  onClose: () => void;
}

export default function PaperDetailsModal({ paper, onClose }: Props) {
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-2xl border border-blue-500/20 max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-blue-500/20">
          <div className="flex-1 pr-4">
            <h2 className="text-2xl font-bold text-white leading-tight">
              {paper.title}
            </h2>
            <div className="flex items-center gap-4 mt-3 text-sm text-blue-200/70">
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                <span>{paper.year || 'N/A'}</span>
              </div>
              <div className="flex items-center gap-1">
                <Quote className="w-4 h-4" />
                <span>{paper.citation_count || 0} citations</span>
              </div>
              {paper.venue && (
                <div className="flex items-center gap-1">
                  <BookOpen className="w-4 h-4" />
                  <span>{paper.venue}</span>
                </div>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors flex-shrink-0"
          >
            <X className="w-6 h-6 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Authors */}
          {paper.authors && paper.authors.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-blue-200 mb-2 flex items-center gap-2">
                <Users className="w-4 h-4" />
                Authors
              </h3>
              <div className="flex flex-wrap gap-2">
                {paper.authors.map((author, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1 bg-slate-800/50 border border-blue-500/20 rounded-full text-sm text-blue-100"
                  >
                    {author}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Abstract */}
          {paper.abstract && (
            <div>
              <h3 className="text-sm font-semibold text-blue-200 mb-2">Abstract</h3>
              <p className="text-slate-300 leading-relaxed text-sm">
                {paper.abstract}
              </p>
            </div>
          )}

          {/* Extracted Entities */}
          {paper.entities && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Methods */}
              {paper.entities.methods && paper.entities.methods.length > 0 && (
                <div className="bg-slate-800/30 rounded-lg p-4 border border-green-500/20">
                  <h4 className="text-sm font-semibold text-green-400 mb-2">
                    🔬 Methods ({paper.entities.methods.length})
                  </h4>
                  <div className="space-y-1">
                    {paper.entities.methods.slice(0, 5).map((method, idx) => (
                      <div key={idx} className="text-xs text-slate-300 truncate" title={method}>
                        • {method}
                      </div>
                    ))}
                    {paper.entities.methods.length > 5 && (
                      <div className="text-xs text-green-400">
                        +{paper.entities.methods.length - 5} more
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Datasets */}
              {paper.entities.datasets && paper.entities.datasets.length > 0 && (
                <div className="bg-slate-800/30 rounded-lg p-4 border border-amber-500/20">
                  <h4 className="text-sm font-semibold text-amber-400 mb-2">
                    📊 Datasets ({paper.entities.datasets.length})
                  </h4>
                  <div className="space-y-1">
                    {paper.entities.datasets.slice(0, 5).map((dataset, idx) => (
                      <div key={idx} className="text-xs text-slate-300 truncate" title={dataset}>
                        • {dataset}
                      </div>
                    ))}
                    {paper.entities.datasets.length > 5 && (
                      <div className="text-xs text-amber-400">
                        +{paper.entities.datasets.length - 5} more
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Metrics */}
              {paper.entities.metrics && paper.entities.metrics.length > 0 && (
                <div className="bg-slate-800/30 rounded-lg p-4 border border-red-500/20">
                  <h4 className="text-sm font-semibold text-red-400 mb-2">
                    📈 Metrics ({paper.entities.metrics.length})
                  </h4>
                  <div className="space-y-1">
                    {paper.entities.metrics.slice(0, 5).map((metric, idx) => (
                      <div key={idx} className="text-xs text-slate-300 truncate" title={metric}>
                        • {metric}
                      </div>
                    ))}
                    {paper.entities.metrics.length > 5 && (
                      <div className="text-xs text-red-400">
                        +{paper.entities.metrics.length - 5} more
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Paper ID */}
          <div className="text-xs text-slate-500 font-mono">
            ID: {paper.paper_id}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-blue-500/20 p-6 flex gap-3">
          {paper.url && (
            <a
              href={paper.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              View on Semantic Scholar
            </a>
          )}
          <button
            onClick={onClose}
            className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}