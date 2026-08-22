"use client";

import { useRef, useState } from "react";
import {
  streamChat,
  type Citation,
  type Subgraph,
  type Triple,
} from "@/lib/api";
import { CitationPanel } from "@/components/CitationCard";
import { GraphInspector } from "@/components/GraphInspector";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  triples?: Triple[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [subgraph, setSubgraph] = useState<Subgraph | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
    });
  };

  async function send() {
    const query = input.trim();
    if (!query || busy) return;
    setInput("");
    setBusy(true);

    setMessages((m) => [
      ...m,
      { role: "user", content: query },
      { role: "assistant", content: "", citations: [], triples: [] },
    ]);
    scrollToBottom();

    const patchAssistant = (patch: Partial<Message>) => {
      setMessages((m) => {
        const copy = [...m];
        const last = copy[copy.length - 1];
        copy[copy.length - 1] = { ...last, ...patch };
        return copy;
      });
    };

    await streamChat(query, {
      onCitations: (c) => patchAssistant({ citations: c }),
      onSubgraph: (data) => {
        setSubgraph(data.subgraph);
        setMessages((m) => {
          const copy = [...m];
          const last = copy[copy.length - 1];
          copy[copy.length - 1] = { ...last, triples: data.triples };
          return copy;
        });
      },
      onToken: (text) => {
        setMessages((m) => {
          const copy = [...m];
          const last = copy[copy.length - 1];
          copy[copy.length - 1] = { ...last, content: last.content + text };
          return copy;
        });
        scrollToBottom();
      },
      onDone: () => setBusy(false),
      onError: () => {
        patchAssistant({ content: "⚠️ Something went wrong. Is the backend running?" });
        setBusy(false);
      },
    });
  }

  return (
    <div className="grid h-full grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,480px)]">
      {/* Chat column */}
      <section className="flex min-h-0 flex-col border-r border-slate-800">
        <div ref={scrollRef} className="scroll-thin min-h-0 flex-1 space-y-4 overflow-y-auto p-6">
          {messages.length === 0 && (
            <div className="mx-auto mt-16 max-w-md text-center text-slate-400">
              <h2 className="mb-2 text-xl font-semibold text-slate-200">
                Ask a question about your documents
              </h2>
              <p className="text-sm">
                Answers fuse vector search over hierarchical chunks with
                multi-hop knowledge-graph traversal. Ingest documents first on
                the <span className="text-emerald-400">Ingest</span> tab.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}
            >
              <div
                className={
                  msg.role === "user"
                    ? "max-w-[80%] rounded-2xl rounded-br-sm bg-emerald-600 px-4 py-2 text-sm"
                    : "max-w-[85%] rounded-2xl rounded-bl-sm bg-slate-800/70 px-4 py-3"
                }
              >
                <p className="whitespace-pre-wrap text-sm leading-relaxed">
                  {msg.content || (msg.role === "assistant" && busy ? "…" : "")}
                </p>
                {msg.role === "assistant" && (
                  <CitationPanel
                    citations={msg.citations || []}
                    triples={msg.triples || []}
                  />
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="border-t border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              rows={1}
              placeholder="Ask something… (Enter to send, Shift+Enter for newline)"
              className="scroll-thin max-h-32 flex-1 resize-none rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm outline-none focus:border-emerald-500"
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-medium hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? "…" : "Send"}
            </button>
          </div>
        </div>
      </section>

      {/* Graph inspector */}
      <aside className="flex min-h-0 flex-col bg-slate-900/30">
        <div className="border-b border-slate-800 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-200">Graph Inspector</h3>
          <p className="text-xs text-slate-500">
            Subgraph context used for the latest answer
          </p>
        </div>
        <div className="min-h-0 flex-1">
          <GraphInspector subgraph={subgraph} />
        </div>
      </aside>
    </div>
  );
}
