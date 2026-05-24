import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { api } from "../lib/api.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

export default function NetworkGraph() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["graph"],
    queryFn: () => api.graph(300),
  });

  if (isLoading) return <PageLoader message="Building transaction network graph…" />;
  if (error) return <ErrorState error={error} />;

  const { nodes = [], edges = [] } = data;
  const suspiciousCount = nodes.filter((n) => n.is_suspicious).length;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Transaction Network Graph"
        subtitle={`${nodes.length} accounts · ${edges.length} transaction flows · ${suspiciousCount} suspicious nodes`}
      />
      <div className="flex-1 relative overflow-hidden">
        <div className="absolute top-4 left-4 z-10 flex gap-3">
          <Legend color="#6366f1" label="Clean account" />
          <Legend color="#ef4444" label="Suspicious account" />
        </div>
        {nodes.length > 0 ? (
          <ForceGraph nodes={nodes} edges={edges} />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-600">
            No graph data available. Run the simulation first.
          </div>
        )}
      </div>
    </div>
  );
}

function Legend({ color, label }) {
  return (
    <div className="flex items-center gap-1.5 bg-surface-card border border-surface-border rounded-lg px-3 py-1.5">
      <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
      <span className="text-xs text-gray-400">{label}</span>
    </div>
  );
}

function ForceGraph({ nodes, edges }) {
  const svgRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    if (!svgRef.current || !nodes.length) return;

    const el = svgRef.current;
    const width = el.clientWidth;
    const height = el.clientHeight;

    d3.select(el).selectAll("*").remove();

    const svg = d3
      .select(el)
      .attr("width", width)
      .attr("height", height);

    // Zoom layer
    const g = svg.append("g");
    svg.call(
      d3.zoom()
        .scaleExtent([0.3, 4])
        .on("zoom", (event) => g.attr("transform", event.transform))
    );

    const nodeMap = new Map(nodes.map((n) => [n.id, { ...n, x: width / 2, y: height / 2 }]));
    const linkData = edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        source: nodeMap.get(e.source),
        target: nodeMap.get(e.target),
        weight: e.weight || 1,
        count: e.count || 1,
      }));

    const nodeData = Array.from(nodeMap.values());

    // Edge weight scale
    const weightScale = d3
      .scaleLog()
      .domain([1, Math.max(...linkData.map((l) => l.weight), 2)])
      .range([0.5, 3]);

    // Draw edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(linkData)
      .join("line")
      .attr("stroke", "#1f2937")
      .attr("stroke-width", (d) => weightScale(Math.max(d.weight, 1)))
      .attr("stroke-opacity", 0.6);

    // Draw nodes
    const node = g
      .append("g")
      .selectAll("circle")
      .data(nodeData)
      .join("circle")
      .attr("r", 5)
      .attr("fill", (d) => (d.is_suspicious ? "#ef4444" : "#6366f1"))
      .attr("fill-opacity", 0.85)
      .attr("stroke", (d) => (d.is_suspicious ? "#fca5a5" : "#818cf8"))
      .attr("stroke-width", 1)
      .style("cursor", "pointer")
      .on("mouseover", (event, d) => {
        setTooltip({ id: d.id, suspicious: d.is_suspicious, x: event.clientX, y: event.clientY });
        d3.select(event.currentTarget).attr("r", 8).attr("stroke-width", 2);
      })
      .on("mouseout", (event) => {
        setTooltip(null);
        d3.select(event.currentTarget).attr("r", 5).attr("stroke-width", 1);
      })
      .call(
        d3.drag()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    // Simulation
    const simulation = d3
      .forceSimulation(nodeData)
      .force("link", d3.forceLink(linkData).id((d) => d.id).distance(60).strength(0.3))
      .force("charge", d3.forceManyBody().strength(-80))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(8))
      .on("tick", () => {
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);
        node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
      });

    return () => simulation.stop();
  }, [nodes, edges]);

  return (
    <>
      <svg ref={svgRef} className="w-full h-full" />
      {tooltip && (
        <div
          className="fixed z-20 bg-surface-card border border-surface-border rounded-lg px-3 py-2 text-xs pointer-events-none"
          style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
        >
          <p className="font-mono text-white">{tooltip.id}</p>
          <p className={tooltip.suspicious ? "text-red-400" : "text-green-400"}>
            {tooltip.suspicious ? "Suspicious" : "Clean"}
          </p>
        </div>
      )}
    </>
  );
}
