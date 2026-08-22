"use client";

import { useState } from "react";
import type { Citation, Triple } from "@/lib/api";

export function CitationPanel({
  citations,
  triples,
}: {
  citations: Citation[];
  triples: Triple[];
}) {
  if (citations.length === 0 && triples.length === 0) return null;

  return (
    <div className="mt-3 space-y-2">
      {citations.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Sources ({citations.length})
          </div>
          {citations.map((c, i) => (
            <CitationCard key={c.parent_id} citation={c} index={i + 1} />
          ))}
        </div>
      )}
      {triples.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Graph relationships ({triples.length})
          </div>
          <div className="flex flex-wrap gap-1.5">
            {triples.map((t, i) => (
              <span
                key={i}
                className="rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs"
              >
                <span className="text-emerald-300">{t.source}</span>
                <span className="mx-1 text-slate-500">
                  {"-["}
                  <span className="text-amber-300">{t.type}</span>
                  {"]->"}
                </span>
                <span className="text-sky-300">{t.target}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CitationCard({
  citation,
  index,
}: {
  citation: Citation;
  index: number;
}) {
  const [open, setOpen] = useState(false);
  const score =
    citation.score != null ? citation.score.toFixed(3) : undefined;

  return (
    <div className="overflow-hidden rounded-lg border border-slate-700 bg-slate-800/40">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-slate-800/70"
      >
        <div className="flex items-center gap-2 text-sm">
          <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-xs text-emerald-300">
            {index}
          </span>
          <span className="font-medium text-slate-200">
            {citation.title || citation.doc_id}
          </span>
          {score && (
            <span className="text-xs text-slate-500">score {score}</span>
          )}
        </div>
        <span className="text-xs text-slate-400">{open ? "Hide" : "Show"}</span>
      </button>
      {open && (
        <div className="border-t border-slate-700 px-3 py-2">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
            {citation.text}
          </p>
          <div className="mt-2 text-[11px] text-slate-500">
            parent: {citation.parent_id.slice(0, 8)} · matched children:{" "}
            {citation.matched_child_ids.length}
          </div>
        </div>
      )}
    </div>
  );
}
