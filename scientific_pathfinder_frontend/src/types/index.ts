export interface ResearchSession {
  session_id: string;
  topic: string;
  max_papers: number;
  status: string;
  result?: ResearchResult;
}

export interface ResearchResult {
  session_id: string;
  topic: string;
  papers: number;
  graph_stats: GraphStats;
  gaps: number;
  hypothesis: string;
  reasoning: string;
}

export interface GraphStats {
  paper_count: number;
  author_count: number;
  method_count: number;
  dataset_count: number;
  metric_count: number;
  relationship_count: number;
}

export interface ProgressUpdate {
  type: 'status' | 'progress' | 'complete' | 'error';
  agent?: string;
  step?: string;
  message: string;
  data?: any;
}