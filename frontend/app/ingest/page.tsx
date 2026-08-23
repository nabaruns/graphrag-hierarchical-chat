"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ingest, ingestStatus, type IngestDoc } from "@/lib/api";
import { EXAMPLE_PROMPTS, SAMPLE_DOCS as SAMPLE } from "@/lib/sampleData";

export default function IngestPage() {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [status, setStatus] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function submit(docs: IngestDoc[]) {
    setError(null);
    setBusy(true);
    setStatus({ status: "pending" });
    try {
      const jobId = await ingest(docs);
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const s = await ingestStatus(jobId);
          setStatus(s);
          if (s.status === "completed" || s.status === "failed") {
            if (pollRef.current) clearInterval(pollRef.current);
            setBusy(false);
          }
        } catch (e) {
          setError(String(e));
          if (pollRef.current) clearInterval(pollRef.current);
          setBusy(false);
        }
      }, 1500);
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  function submitManual() {
    if (!title.trim() || !text.trim()) return;
    submit([{ title: title.trim(), text: text.trim() }]);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold">Ingest Documents</h1>
        <p className="text-sm text-slate-400">
          Documents are hierarchically chunked, embedded into Qdrant, and their
          entities + relationships extracted into Neo4j. Ingestion runs
          asynchronously; status updates below.
        </p>
      </div>

      {/* Sample dataset preview */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">Sample dataset</h2>
            <p className="text-xs text-slate-400">
              {SAMPLE.length} short documents about a fictional company. Load
              them, then try the questions below on the{" "}
              <Link href="/" className="text-emerald-400 hover:underline">
                Chat
              </Link>{" "}
              tab.
            </p>
          </div>
          <button
            onClick={() => submit(SAMPLE)}
            disabled={busy}
            className="shrink-0 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-40"
          >
            Load sample dataset
          </button>
        </div>

        <div className="grid gap-2 sm:grid-cols-3">
          {SAMPLE.map((d) => (
            <div
              key={d.title}
              className="rounded-lg border border-slate-700 bg-slate-800/40 p-3"
            >
              <div className="text-sm font-medium text-slate-200">{d.title}</div>
              <div className="mb-1 text-[11px] text-slate-500">{d.source}</div>
              <p className="line-clamp-4 text-xs leading-relaxed text-slate-400">
                {d.text}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-4">
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Example questions
          </div>
          <ul className="space-y-1">
            {EXAMPLE_PROMPTS.map((p) => (
              <li
                key={p.q}
                className="flex items-center gap-2 text-sm text-slate-300"
              >
                <span className="text-emerald-400">›</span>
                <span>{p.q}</span>
                {p.hint && (
                  <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] text-amber-300">
                    {p.hint}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-200">
          Or add your own document
        </h2>
        <label className="mb-1 block text-xs font-medium text-slate-400">
          Title
        </label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Document title"
          className="mb-3 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        />
        <label className="mb-1 block text-xs font-medium text-slate-400">
          Text
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={10}
          placeholder="Paste document text here…"
          className="scroll-thin w-full resize-y rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={submitManual}
            disabled={busy || !title.trim() || !text.trim()}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-40"
          >
            Ingest document
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {status && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-sm">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-slate-400">Status:</span>
            <StatusBadge status={status.status} />
          </div>
          {status.status === "completed" && (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="Documents" value={status.documents} />
              <Stat label="Parent chunks" value={status.parent_chunks} />
              <Stat label="Child chunks" value={status.child_chunks} />
              <Stat label="Entities" value={status.entities} />
              <Stat label="Relationships" value={status.relationships} />
            </div>
          )}
          {status.status === "failed" && (
            <p className="text-red-300">{status.error}</p>
          )}
          {(status.status === "pending" || status.status === "running") && (
            <p className="text-slate-400">
              Working… entity extraction on CPU can take a little while.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    completed: "bg-emerald-500/20 text-emerald-300",
    running: "bg-amber-500/20 text-amber-300",
    pending: "bg-slate-600/30 text-slate-300",
    failed: "bg-red-500/20 text-red-300",
  };
  return (
    <span className={`rounded px-2 py-0.5 text-xs ${map[status] || map.pending}`}>
      {status}
    </span>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-slate-800/60 p-3">
      <div className="text-lg font-semibold text-slate-100">{value ?? 0}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}
