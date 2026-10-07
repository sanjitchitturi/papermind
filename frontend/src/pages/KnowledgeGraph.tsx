import { useEffect, useMemo, useState } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { api, type GraphData } from "../api/client";

// reactflow needs literal style values, Tailwind classes don't reach into
// its inline node styles. Entity types are told apart by grayscale shade
// AND border style together, since shade alone is hard to distinguish at
// a glance once there are more than two or three levels.
const TYPE_STYLE: Record<string, { background: string; color: string; borderStyle: string }> = {
  method: { background: "#0a0a0a", color: "#ffffff", borderStyle: "solid" },
  dataset: { background: "#ffffff", color: "#0a0a0a", borderStyle: "solid" },
  metric: { background: "#ffffff", color: "#0a0a0a", borderStyle: "dashed" },
  model: { background: "#404040", color: "#ffffff", borderStyle: "solid" },
  author: { background: "#ffffff", color: "#525252", borderStyle: "dotted" },
  institution: { background: "#ffffff", color: "#525252", borderStyle: "dotted" },
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
      const style = TYPE_STYLE[entity.type] ?? { background: "#ffffff", color: "#0a0a0a", borderStyle: "solid" };
      nodes.push({
        id: entity.id,
        position: { x: radius * Math.cos(angle), y: radius * Math.sin(angle) },
        data: { label: `${entity.label} (${entity.type})` },
        style: {
          background: style.background,
          color: style.color,
          border: `1.5px ${style.borderStyle} #0a0a0a`,
          borderRadius: 4,
          fontSize: 12,
          fontFamily: "Inter, sans-serif",
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
        style: { stroke: "#737373" },
        labelStyle: { fill: "#0a0a0a", fontSize: 11 },
      })),
    [graph],
  );

  return (
    <div className="h-[calc(100vh-65px)] w-full bg-white">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#d4d4d4" />
        <Controls />
      </ReactFlow>
    </div>
  );
}
