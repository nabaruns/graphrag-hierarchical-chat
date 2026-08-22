export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Citation {
  parent_id: string;
  doc_id: string;
  title?: string | null;
  text: string;
  score?: number | null;
  matched_child_ids: string[];
}

export interface Triple {
  source: string;
  type: string;
  target: string;
  source_child_id?: string | null;
  source_parent_id?: string | null;
}

export interface GraphNode {
  id: string;
  label: string;
  type?: string | null;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties?: Record<string, unknown>;
}

export interface Subgraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ChatHandlers {
  onCitations?: (c: Citation[]) => void;
  onSubgraph?: (data: {
    subgraph: Subgraph;
    triples: Triple[];
    seed_entities: string[];
  }) => void;
  onToken?: (text: string) => void;
  onDone?: () => void;
  onError?: (err: unknown) => void;
}

/**
 * POST /api/v1/chat and parse the Server-Sent Events stream.
 * EventSource is GET-only, so we read the fetch ReadableStream manually.
 */
export async function streamChat(
  query: string,
  handlers: ChatHandlers,
  opts?: { top_k?: number; max_hops?: number }
): Promise<void> {
  try {
    const resp = await fetch(`${API_BASE}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, ...opts }),
    });
    if (!resp.ok || !resp.body) {
      throw new Error(`Chat request failed: ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r/g, "");

      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";

      for (const raw of chunks) {
        let event = "message";
        let data = "";
        for (const line of raw.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data += line.slice(5).trim();
        }
        if (!data) continue;

        let payload: any;
        try {
          payload = JSON.parse(data);
        } catch {
          continue;
        }

        if (event === "citations") handlers.onCitations?.(payload as Citation[]);
        else if (event === "subgraph") handlers.onSubgraph?.(payload);
        else if (event === "token") handlers.onToken?.(payload.text);
        else if (event === "done") handlers.onDone?.();
      }
    }
    handlers.onDone?.();
  } catch (err) {
    handlers.onError?.(err);
  }
}

export interface IngestDoc {
  title: string;
  text: string;
  source?: string;
}

export async function ingest(documents: IngestDoc[]): Promise<string> {
  const resp = await fetch(`${API_BASE}/api/v1/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ documents }),
  });
  if (!resp.ok) throw new Error(`Ingest failed: ${resp.status}`);
  const body = await resp.json();
  return body.job_id as string;
}

export async function ingestStatus(jobId: string): Promise<any> {
  const resp = await fetch(`${API_BASE}/api/v1/ingest/${jobId}`);
  if (!resp.ok) throw new Error(`Status failed: ${resp.status}`);
  return resp.json();
}

export async function fetchSubgraph(
  entity?: string,
  hops = 2
): Promise<Subgraph> {
  const params = new URLSearchParams();
  if (entity) params.set("entity", entity);
  params.set("hops", String(hops));
  const resp = await fetch(`${API_BASE}/api/v1/graph/subgraph?${params}`);
  if (!resp.ok) throw new Error(`Subgraph failed: ${resp.status}`);
  return resp.json();
}
