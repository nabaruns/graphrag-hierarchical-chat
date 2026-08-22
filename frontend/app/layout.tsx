import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "GraphRAG Explorer",
  description: "Hierarchical GraphRAG chat with graph inspector",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="flex h-screen flex-col">
          <header className="flex items-center justify-between border-b border-slate-800 bg-slate-900/60 px-6 py-3">
            <div className="flex items-center gap-3">
              <span className="text-lg font-semibold tracking-tight">
                GraphRAG <span className="text-emerald-400">Explorer</span>
              </span>
              <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                Hierarchical + Knowledge Graph
              </span>
            </div>
            <nav className="flex gap-4 text-sm">
              <Link href="/" className="text-slate-300 hover:text-white">
                Chat
              </Link>
              <Link href="/ingest" className="text-slate-300 hover:text-white">
                Ingest
              </Link>
            </nav>
          </header>
          <main className="min-h-0 flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
