import { useState } from 'react';
import { FileText, Users, Calendar, TrendingUp } from 'lucide-react';
import PaperDetailsModal from './PaperDetailsModal';

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
  papers: Paper[];
}

export default function PapersList({ papers }: Props) {
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [sortBy, setSortBy] = useState<'year' | 'citations'>('citations');

  const sortedPapers = [...papers].sort((a, b) => {
    if (sortBy === 'year') {
      return (b.year || 0) - (a.year || 0);
    }
    return (b.citation_count || 0) - (a.citation_count || 0);
  });

  return (
    <>
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-blue-500/20 p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            📚 Analyzed Papers ({papers.length})
          </h2>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'year' | 'citations')}
            className="px-4 py-2 bg-slate-900/50 border border-blue-500/30 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="citations">Sort by Citations</option>
            <option value="year">Sort by Year</option>
          </select>
        </div>

        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
          {sortedPapers.map((paper) => (
            <div
              key={paper.paper_id}
              onClick={() => setSelectedPaper(paper)}
              className="bg-slate-900/50 rounded-lg p-6 border border-blue-500/10 hover:border-blue-500/30 transition-all cursor-pointer group"
            >
              {/* Title */}
              <h3 className="text-lg font-semibold text-white group-hover:text-blue-400 transition-colors mb-2 line-clamp-2">
                {paper.title}
              </h3>

              {/* Metadata */}
              <div className="flex items-center gap-4 text-sm text-blue-200/70 mb-3">
                <div className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  <span>{paper.year || 'N/A'}</span>
                </div>
                <div className="flex items-center gap-1">
                  <TrendingUp className="w-4 h-4" />
                  <span>{paper.citation_count || 0} citations</span>
                </div>
                {paper.authors && paper.authors.length > 0 && (
                  <div className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    <span>{paper.authors.length} authors</span>
                  </div>
                )}
              </div>

              {/* Authors */}
              {paper.authors && paper.authors.length > 0 && (
                <div className="text-sm text-slate-400 mb-3">
                  <span className="font-medium">Authors:</span>{' '}
                  {paper.authors.slice(0, 3).join(', ')}
                  {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
                </div>
              )}

              {/* Abstract Preview */}
              {paper.abstract && (
                <p className="text-sm text-slate-300 line-clamp-2 mb-3">
                  {paper.abstract}
                </p>
              )}

              {/* Entity Tags */}
              {paper.entities && (
                <div className="flex flex-wrap gap-2">
                  {paper.entities.methods && paper.entities.methods.slice(0, 2).map((method, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-green-500/10 border border-green-500/20 rounded text-xs text-green-400"
                    >
                      {method}
                    </span>
                  ))}
                  {paper.entities.datasets && paper.entities.datasets.slice(0, 2).map((dataset, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-amber-500/10 border border-amber-500/20 rounded text-xs text-amber-400"
                    >
                      {dataset}
                    </span>
                  ))}
                  {paper.entities.metrics && paper.entities.metrics.slice(0, 1).map((metric, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400"
                    >
                      {metric}
                    </span>
                  ))}
                </div>
              )}

              {/* Click hint */}
              <div className="mt-4 text-xs text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity">
                Click to view details →
              </div>
            </div>
          ))}

          {papers.length === 0 && (
            <div className="text-center py-12 text-slate-400">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No papers to display</p>
            </div>
          )}
        </div>
      </div>

      {/* Paper Details Modal */}
      {selectedPaper && (
        <PaperDetailsModal
          paper={selectedPaper}
          onClose={() => setSelectedPaper(null)}
        />
      )}
    </>
  );
}