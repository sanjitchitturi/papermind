import { useEffect, useMemo, useState } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { api, type GraphData } from "../api/client";
import { Empty, PageHeader } from "../components/ui";

const TYPE_STYLE: Record<string, { background: string; color: string; borderStyle: string }> = {
  paper: { background: "#0a0a0a", color: "#ffffff", borderStyle: "solid" },
  method: { background: "#ffffff", color: "#0a0a0a", borderStyle: "solid" },
  dataset: { background: "#ffffff", color: "#0a0a0a", borderStyle: "dashed" },
  metric: { background: "#f5f5f5", color: "#0a0a0a", borderStyle: "dotted" },
  model: { background: "#404040", color: "#ffffff", borderStyle: "solid" },
  task: { background: "#ffffff", color: "#525252", borderStyle: "dashed" },
};

function layout(graph: GraphData): Node[] {
  const papers = graph.nodes.filter((n) => n.kind === "paper");
  const entities = graph.nodes.filter((n) => n.kind !== "paper");
  const nodes: Node[] = [];

  papers.forEach((node, i) => {
    const angle = (i / Math.max(papers.length, 1)) * 2 * Math.PI;
    const style = TYPE_STYLE.paper;
    nodes.push({
      id: node.id,
      position: { x: 280 * Math.cos(angle), y: 280 * Math.sin(angle) },
      data: { label: node.label },
      style: {
        background: style.background,
        color: style.color,
        border: `1.5px ${style.borderStyle} #0a0a0a`,
        borderRadius: 2,
        fontSize: 12,
        fontFamily: "Source Serif 4, serif",
        padding: 8,
        maxWidth: 220,
      },
    });
  });

  entities.forEach((node, i) => {
    const angle = (i / Math.max(entities.length, 1)) * 2 * Math.PI;
    const style = TYPE_STYLE[node.type] ?? TYPE_STYLE.method;
    nodes.push({
      id: node.id,
      position: { x: 520 * Math.cos(angle), y: 520 * Math.sin(angle) },
      data: { label: `${node.label} (${node.type})` },
      style: {
        background: style.background,
        color: style.color,
        border: `1.5px ${style.borderStyle} #0a0a0a`,
        borderRadius: 2,
        fontSize: 11,
        fontFamily: "Inter, sans-serif",
        padding: 6,
      },
    });
  });
  return nodes;
}

export function KnowledgeGraph() {
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });

  useEffect(() => {
    api.getGraph().then(setGraph).catch(console.error);
  }, []);

  const nodes = useMemo(() => layout(graph), [graph]);
  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((e, i) => ({
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        label: e.relation,
        animated: e.relation === "cites",
        style: { stroke: e.relation === "cites" ? "#0a0a0a" : "#a3a3a3" },
        labelStyle: { fill: "#525252", fontSize: 10 },
      })),
    [graph],
  );

  return (
    <div className="flex h-[calc(100vh-96px)] flex-col">
      <div className="px-6 pt-6">
        <PageHeader title="Knowledge graph">
          Papers (filled) link to shared entities (outline) and to each other when a bibliography entry
          resolves to another paper in the library.
        </PageHeader>
      </div>
      {graph.nodes.length === 0 ? (
        <div className="px-6 pt-8">
          <Empty>Ingest a paper to populate the graph. Entity extraction runs automatically after indexing.</Empty>
        </div>
      ) : (
        <div className="min-h-0 flex-1">
          <ReactFlow nodes={nodes} edges={edges} fitView>
            <Background color="#d4d4d4" />
            <Controls />
          </ReactFlow>
        </div>
      )}
    </div>
  );
}
