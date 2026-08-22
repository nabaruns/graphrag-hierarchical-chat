"use client";

import { useEffect, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import type { Subgraph } from "@/lib/api";

const TYPE_COLORS: Record<string, string> = {
  Person: "#f472b6",
  Company: "#34d399",
  Organization: "#34d399",
  Product: "#60a5fa",
  Technology: "#a78bfa",
  Location: "#fbbf24",
  Unknown: "#94a3b8",
};

function colorFor(type?: string | null): string {
  return TYPE_COLORS[type || "Unknown"] || "#94a3b8";
}

export function GraphInspector({ subgraph }: { subgraph: Subgraph | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const nodes: ElementDefinition[] = (subgraph?.nodes || []).map((n) => ({
      data: { id: n.id, label: n.label, color: colorFor(n.type), type: n.type },
    }));
    const edges: ElementDefinition[] = (subgraph?.edges || []).map((e) => ({
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.type,
      },
    }));

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...nodes, ...edges],
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(label)",
            color: "#e2e8f0",
            "font-size": "10px",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "80px",
            width: 34,
            height: 34,
            "border-width": 2,
            "border-color": "#0f172a",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#475569",
            "target-arrow-color": "#475569",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "8px",
            color: "#94a3b8",
            "text-rotation": "autorotate",
            "text-background-color": "#0f172a",
            "text-background-opacity": 0.8,
            "text-background-padding": "2px",
          },
        },
      ],
      layout: { name: "cose", animate: false, padding: 20 },
    });
    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [subgraph]);

  const isEmpty = !subgraph || subgraph.nodes.length === 0;

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {isEmpty && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center px-6 text-center text-sm text-slate-500">
          The knowledge subgraph used to answer your question will appear here.
        </div>
      )}
    </div>
  );
}
