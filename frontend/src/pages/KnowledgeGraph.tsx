import { useEffect, useMemo, useState } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { api, type GraphData } from "../api/client";

const TYPE_COLORS: Record<string, string> = {
  method: "#2563eb",
  dataset: "#16a34a",
  metric: "#d97706",
  model: "#9333ea",
  author: "#64748b",
  institution: "#64748b",
};

// Simple circular layout. A proper graph layout library (dagre, elk) would
// do a better job for large graphs, but for the handful of entities per
// paper this project deals with, laying nodes out in a circle per type is
// readable and avoids one more dependency.
function layoutNodes(graph: GraphData): Node[] {
  const byType = new Map<string, typeof graph.nodes>();
  for (const node of graph.nodes) {
    byType.set(node.type, [...(byType.get(node.type) ?? []), node]);
  }

  const nodes: Node[] = [];
  const types = Array.from(byType.keys());
  types.forEach((type, typeIndex) => {
    const entities = byType.get(type) ?? [];
    const radius = 150 + typeIndex * 180;
    entities.forEach((entity, i) => {
      const angle = (i / Math.max(entities.length, 1)) * 2 * Math.PI;
      nodes.push({
        id: entity.id,
        position: { x: radius * Math.cos(angle), y: radius * Math.sin(angle) },
        data: { label: `${entity.label} (${entity.type})` },
        style: {
          background: TYPE_COLORS[entity.type] ?? "#334155",
          color: "white",
          borderRadius: 8,
          fontSize: 12,
          padding: 6,
        },
      });
    });
  });
  return nodes;
}

export function KnowledgeGraph() {
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });

  useEffect(() => {
    api.getGraph().then(setGraph).catch(console.error);
  }, []);

  const nodes = useMemo(() => layoutNodes(graph), [graph]);
  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((e, i) => ({
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        label: e.relation,
        animated: e.relation === "cites",
      })),
    [graph],
  );

  return (
    <div className="h-[calc(100vh-56px)] w-full">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
