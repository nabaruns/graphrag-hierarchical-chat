"use client";

import { useEffect, useRef, useState } from "react";
import { ingest, ingestStatus, type IngestDoc } from "@/lib/api";

const SAMPLE: IngestDoc[] = [
  {
    title: "TechCorp Acquisition News",
    source: "sample/news-1",
    text: "TechCorp announced today that it has acquired DataStart, an AI analytics startup founded in 2019 by Dr. Elena Reyes. DataStart is based in Austin, Texas, and is known for its real-time streaming analytics platform called StreamIQ. The acquisition, valued at 450 million dollars, is expected to strengthen TechCorp's cloud division. Dr. Elena Reyes will join TechCorp as the Vice President of AI Engineering, reporting directly to TechCorp CEO Marcus Chen. TechCorp is headquartered in Seattle and previously acquired CloudNimbus in 2021.",
  },
  {
    title: "StreamIQ Product Overview",
    source: "sample/product-1",
    text: "StreamIQ is a real-time streaming analytics platform originally developed by DataStart. It is built on top of Apache Kafka and uses a custom query engine written in Rust. After the acquisition by TechCorp, StreamIQ was integrated into the TechCorp Cloud Suite. The engineering team behind StreamIQ is led by Priya Nair, who worked closely with Dr. Elena Reyes at DataStart.",
  },
];

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

      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
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
          <button
            onClick={() => submit(SAMPLE)}
            disabled={busy}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-40"
          >
            Load sample dataset
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
