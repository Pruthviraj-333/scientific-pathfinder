import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { X, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

interface Node {
  id: string;
  label: string;
  type: 'paper' | 'method' | 'dataset' | 'metric' | 'author';
  properties?: any;
}

interface Link {
  source: string;
  target: string;
  type: string;
}

interface Props {
  sessionId: string;
  onClose: () => void;
}

export default function GraphVisualization({ sessionId, onClose }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [loading, setLoading] = useState(true);
  const [graphData, setGraphData] = useState<{ nodes: Node[]; links: Link[] } | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  useEffect(() => {
    fetchGraphData();
  }, [sessionId]);

  const fetchGraphData = async () => {
    setLoading(true);
    try {
      // Fetch graph data from backend
      const response = await fetch(`http://localhost:8000/api/graph/data?session_id=${sessionId}`);
      const data = await response.json();
      setGraphData(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
      // Use mock data for demo
      setGraphData(generateMockGraph());
      setLoading(false);
    }
  };

  const generateMockGraph = (): { nodes: Node[]; links: Link[] } => {
    const nodes: Node[] = [
      { id: '1', label: 'Vision Transformer', type: 'method' },
      { id: '2', label: 'ResNet', type: 'method' },
      { id: '3', label: 'ChestX-ray', type: 'dataset' },
      { id: '4', label: 'MIMIC-III', type: 'dataset' },
      { id: '5', label: 'Accuracy', type: 'metric' },
      { id: '6', label: 'F1-Score', type: 'metric' },
      { id: '7', label: 'Paper 1', type: 'paper' },
      { id: '8', label: 'Paper 2', type: 'paper' },
      { id: '9', label: 'CNN', type: 'method' },
      { id: '10', label: 'ImageNet', type: 'dataset' },
    ];

    const links: Link[] = [
      { source: '7', target: '1', type: 'USES_METHOD' },
      { source: '7', target: '3', type: 'USES_DATASET' },
      { source: '7', target: '5', type: 'MEASURES_WITH' },
      { source: '8', target: '2', type: 'USES_METHOD' },
      { source: '8', target: '4', type: 'USES_DATASET' },
      { source: '8', target: '6', type: 'MEASURES_WITH' },
      { source: '7', target: '9', type: 'USES_METHOD' },
      { source: '8', target: '10', type: 'USES_DATASET' },
    ];

    return { nodes, links };
  };

  useEffect(() => {
    if (!graphData || !svgRef.current) return;

    const width = 900;
    const height = 600;

    // Clear previous graph
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);

    // Add zoom behavior
    const g = svg.append('g');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom as any);

    // Color scheme
    const colorMap: Record<string, string> = {
      paper: '#3b82f6',    // blue
      method: '#10b981',   // green
      dataset: '#f59e0b',  // amber
      metric: '#ef4444',   // red
      author: '#8b5cf6',   // purple
    };

    // Create a map of node IDs for quick lookup
    const nodeById = new Map(graphData.nodes.map(d => [d.id, d]));
    
    // Filter out links that reference non-existent nodes
    const validLinks = graphData.links.filter(link => {
      const sourceExists = nodeById.has(typeof link.source === 'string' ? link.source : link.source.id);
      const targetExists = nodeById.has(typeof link.target === 'string' ? link.target : link.target.id);
      return sourceExists && targetExists;
    });

    // Create copies of data for D3
    const nodes = graphData.nodes.map(d => ({...d}));
    const links = validLinks.map(d => ({...d}));

    // Create force simulation
    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links as any)
        .id((d: any) => d.id)
        .distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    // Create links
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#64748b')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2);

    // Create nodes
    const node = g.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', 12)
      .attr('fill', (d) => colorMap[d.type] || '#64748b')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        setSelectedNode(d as Node);
      })
      .call(d3.drag<any, any>()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded) as any);

    // Add labels
    const label = g.append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .text((d) => d.label)
      .attr('font-size', 10)
      .attr('dx', 15)
      .attr('dy', 4)
      .attr('fill', '#e2e8f0')
      .style('pointer-events', 'none');

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node
        .attr('cx', (d: any) => d.x)
        .attr('cy', (d: any) => d.y);

      label
        .attr('x', (d: any) => d.x)
        .attr('y', (d: any) => d.y);
    });

    function dragStarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragEnded(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

  }, [graphData]);

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-2xl border border-blue-500/20 max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-blue-500/20">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              🗺️ Knowledge Graph Visualization
            </h2>
            <p className="text-sm text-blue-200/70 mt-1">
              Interactive force-directed graph • Drag nodes • Click for details
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-slate-400" />
          </button>
        </div>

        {/* Graph Container */}
        <div className="flex-1 overflow-hidden relative">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-blue-200">Loading graph data...</p>
              </div>
            </div>
          ) : (
            <>
              <div className="bg-slate-800/50 rounded-lg m-4 overflow-hidden">
                <svg ref={svgRef} className="w-full" style={{ height: '600px' }} />
              </div>

              {/* Legend */}
              <div className="absolute top-4 left-4 bg-slate-800/90 backdrop-blur-sm rounded-lg p-4 border border-blue-500/20">
                <h3 className="text-sm font-semibold text-white mb-2">Legend</h3>
                <div className="space-y-1 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <span className="text-slate-300">Paper</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span className="text-slate-300">Method</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-amber-500" />
                    <span className="text-slate-300">Dataset</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <span className="text-slate-300">Metric</span>
                  </div>
                </div>
              </div>

              {/* Controls */}
              <div className="absolute top-4 right-4 flex gap-2">
                <button className="p-2 bg-slate-800/90 backdrop-blur-sm hover:bg-slate-700 rounded-lg border border-blue-500/20 transition-colors">
                  <ZoomIn className="w-5 h-5 text-blue-200" />
                </button>
                <button className="p-2 bg-slate-800/90 backdrop-blur-sm hover:bg-slate-700 rounded-lg border border-blue-500/20 transition-colors">
                  <ZoomOut className="w-5 h-5 text-blue-200" />
                </button>
                <button className="p-2 bg-slate-800/90 backdrop-blur-sm hover:bg-slate-700 rounded-lg border border-blue-500/20 transition-colors">
                  <Maximize2 className="w-5 h-5 text-blue-200" />
                </button>
              </div>
            </>
          )}
        </div>

        {/* Node Details */}
        {selectedNode && (
          <div className="border-t border-blue-500/20 p-6 bg-slate-800/50">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">{selectedNode.label}</h3>
                <p className="text-sm text-blue-200/70 capitalize">Type: {selectedNode.type}</p>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}