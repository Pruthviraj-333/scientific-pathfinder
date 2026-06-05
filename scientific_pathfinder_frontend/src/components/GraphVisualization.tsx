import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { X, ZoomIn, ZoomOut, Maximize2, Minimize2, RotateCcw, Play, Pause } from 'lucide-react';
import { getGraphData } from '../services/api';

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
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [graphData, setGraphData] = useState<{ nodes: Node[]; links: Link[] } | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [simulationRunning, setSimulationRunning] = useState(true);
  const zoomBehaviorRef = useRef<any>(null);
  const simulationRef = useRef<any>(null);

  useEffect(() => {
    fetchGraphData();
  }, [sessionId]);

  // Handle fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const fetchGraphData = async () => {
    setLoading(true);
    try {
      const data = (await getGraphData(sessionId)) as { nodes: Node[]; links: Link[] };
      setGraphData(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
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

    const width = isFullscreen ? window.innerWidth : 900;
    const height = isFullscreen ? window.innerHeight - 100 : 600;

    // Clear previous graph
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);

    // Add zoom behavior
    const g = svg.append('g');

    const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
        setZoom(event.transform.k);
      });

    svg.call(zoomBehavior as any);
    zoomBehaviorRef.current = zoomBehavior;

    // Color scheme
    const colorMap: Record<string, string> = {
      paper: '#3b82f6',
      method: '#10b981',
      dataset: '#f59e0b',
      metric: '#ef4444',
      author: '#8b5cf6',
    };

    // Create a map of node IDs for quick lookup
    const nodeById = new Map(graphData.nodes.map(d => [d.id, d]));
    
     // Filter out links that reference non-existent nodes
    const validLinks = graphData.links.filter(link => {
      const sourceExists = nodeById.has(typeof link.source === 'string' ? link.source : (link.source as any).id);
      const targetExists = nodeById.has(typeof link.target === 'string' ? link.target : (link.target as any).id);
      return sourceExists && targetExists;
    });

    // Create copies of data for D3
    const nodes = graphData.nodes.map(d => ({...d}));
    const links = validLinks.map(d => ({...d}));

    // Create force simulation
    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links as any)
        .id((d: any) => d.id)
        .distance(150))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40));

    simulationRef.current = simulation;

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
      .attr('r', 15)
      .attr('fill', (d) => colorMap[d.type] || '#64748b')
      .attr('stroke', '#fff')
      .attr('stroke-width', 3)
      .style('cursor', 'pointer')
      .on('click', (_event, d) => {
        setSelectedNode(d as Node);
      })
      .on('mouseover', function() {
        d3.select(this).attr('r', 18).attr('stroke-width', 4);
      })
      .on('mouseout', function() {
        d3.select(this).attr('r', 15).attr('stroke-width', 3);
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
      .text((d) => d.label.length > 20 ? d.label.substring(0, 20) + '...' : d.label)
      .attr('font-size', 12)
      .attr('dx', 20)
      .attr('dy', 4)
      .attr('fill', '#f1f5f9')
      .attr('font-weight', 500)
      .style('pointer-events', 'none')
      .style('user-select', 'none');

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

    return () => {
      simulation.stop();
    };
  }, [graphData, isFullscreen]);

  const handleZoomIn = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      const svg = d3.select(svgRef.current);
      svg.transition().duration(300).call(
        zoomBehaviorRef.current.scaleBy,
        1.3
      );
    }
  };

  const handleZoomOut = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      const svg = d3.select(svgRef.current);
      svg.transition().duration(300).call(
        zoomBehaviorRef.current.scaleBy,
        0.7
      );
    }
  };

  const handleReset = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      const svg = d3.select(svgRef.current);
      svg.transition().duration(500).call(
        zoomBehaviorRef.current.transform,
        d3.zoomIdentity
      );
    }
    if (simulationRef.current) {
      simulationRef.current.alpha(1).restart();
      setSimulationRunning(true);
    }
  };

  const toggleFullscreen = async () => {
    if (!containerRef.current) return;

    try {
      if (!isFullscreen) {
        await containerRef.current.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (error) {
      console.error('Fullscreen error:', error);
    }
  };

  const toggleSimulation = () => {
    if (simulationRef.current) {
      if (simulationRunning) {
        simulationRef.current.stop();
        setSimulationRunning(false);
      } else {
        simulationRef.current.alpha(0.3).restart();
        setSimulationRunning(true);
      }
    }
  };

  return (
    <div 
      ref={containerRef}
      className={`fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 ${isFullscreen ? 'p-0' : ''}`}
    >
      <div className={`bg-slate-900 rounded-2xl border border-blue-500/20 w-full h-[80vh] max-h-[90vh] overflow-hidden flex flex-col ${isFullscreen ? 'max-w-full h-screen max-h-full rounded-none' : 'max-w-6xl'}`}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-blue-500/20 bg-slate-900/95">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              🗺️ Knowledge Graph Visualization
            </h2>
            <p className="text-sm text-blue-200/70 mt-1">
              {graphData ? `${graphData.nodes.length} nodes, ${graphData.links.length} relationships` : 'Loading...'}
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
        <div className="flex-1 overflow-hidden relative bg-slate-950">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                <p className="text-slate-400">Loading graph data...</p>
              </div>
            </div>
          )}

          <svg ref={svgRef} className={`w-full h-full ${loading ? 'hidden' : ''}`}></svg>
          
          {!loading && (
            <>
              {/* Controls - Top Right */}
              <div className="absolute top-4 right-4 flex flex-col gap-2">
                <button
                  onClick={handleZoomIn}
                  className="p-3 bg-slate-800/90 backdrop-blur-sm hover:bg-slate-700 rounded-lg border border-blue-500/20 transition-colors group"
                  title="Zoom In"
                >
                  <ZoomIn className="w-5 h-5 text-blue-200 group-hover:text-blue-100" />
                </button>
                <button
                  onClick={handleZoomOut}
                  className="p-3 bg-slate-800/90 backdrop-blur-sm hover:bg-slate-700 rounded-lg border border-blue-500/20 transition-colors group"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-5 h-5 text-blue-200 group-hover:text-blue-100" />
                </button>
                <button
                  onClick={handleReset}
                  className="p-3 bg-slate-800/90 backdrop-blur-sm hover:bg-slate-700 rounded-lg border border-blue-500/20 transition-colors group"
                  title="Reset View"
                >
                  <RotateCcw className="w-5 h-5 text-blue-200 group-hover:text-blue-100" />
                </button>
                <button
                  onClick={toggleSimulation}
                  className="p-3 bg-slate-800/90 backdrop-blur-sm hover:bg-slate-700 rounded-lg border border-blue-500/20 transition-colors group"
                  title={simulationRunning ? "Pause Animation" : "Resume Animation"}
                >
                  {simulationRunning ? (
                    <Pause className="w-5 h-5 text-blue-200 group-hover:text-blue-100" />
                  ) : (
                    <Play className="w-5 h-5 text-blue-200 group-hover:text-blue-100" />
                  )}
                </button>
                <button
                  onClick={toggleFullscreen}
                  className="p-3 bg-slate-800/90 backdrop-blur-sm hover:bg-slate-700 rounded-lg border border-blue-500/20 transition-colors group"
                  title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
                >
                  {isFullscreen ? (
                    <Minimize2 className="w-5 h-5 text-blue-200 group-hover:text-blue-100" />
                  ) : (
                    <Maximize2 className="w-5 h-5 text-blue-200 group-hover:text-blue-100" />
                  )}
                </button>
              </div>

              {/* Legend - Top Left */}
              <div className="absolute top-4 left-4 bg-slate-800/90 backdrop-blur-sm rounded-lg p-4 border border-blue-500/20">
                <h3 className="text-sm font-semibold text-white mb-3">Legend</h3>
                <div className="space-y-2 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-blue-500"></div>
                    <span className="text-slate-300">Papers</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-green-500"></div>
                    <span className="text-slate-300">Methods</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-orange-500"></div>
                    <span className="text-slate-300">Datasets</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-red-500"></div>
                    <span className="text-slate-300">Metrics</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-purple-500"></div>
                    <span className="text-slate-300">Authors</span>
                  </div>
                </div>
              </div>

              {/* Zoom Level Indicator - Bottom Right */}
              <div className="absolute bottom-4 right-4 bg-slate-800/90 backdrop-blur-sm rounded-lg px-4 py-2 border border-blue-500/20">
                <p className="text-xs text-slate-400">
                  Zoom: <span className="text-blue-200 font-mono">{(zoom * 100).toFixed(0)}%</span>
                </p>
              </div>

              {/* Tips - Bottom Left */}
              <div className="absolute bottom-4 left-4 bg-slate-800/90 backdrop-blur-sm rounded-lg p-3 text-xs text-slate-400 border border-blue-500/20 max-w-xs">
                <p className="mb-1">💡 <strong className="text-slate-300">Tips:</strong></p>
                <p>• Drag nodes to rearrange</p>
                <p>• Scroll or pinch to zoom</p>
                <p>• Click nodes for details</p>
                <p>• Use controls to navigate</p>
              </div>
            </>
          )}
        </div>

        {/* Node Details */}
        {selectedNode && (
          <div className="border-t border-blue-500/20 p-6 bg-slate-800/50 max-h-48 overflow-y-auto">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white mb-1">{selectedNode.label}</h3>
                <p className="text-sm text-blue-200/70 capitalize mb-2">Type: {selectedNode.type}</p>
                {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                  <div className="text-xs text-slate-400 space-y-1">
                    {Object.entries(selectedNode.properties).slice(0, 3).map(([key, value]) => (
                      <div key={key}>
                        <span className="font-medium text-slate-300">{key}:</span> {String(value)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-white p-1"
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