# Deployment guide

The stack deploys across four managed services. The application code is
unchanged from local, everything is driven by environment variables.

```
Next.js UI  ──►  Vercel
FastAPI API ──►  Render (Docker web service, built from this repo)
Neo4j       ──►  Neo4j Aura (managed)
Qdrant      ──►  Qdrant Cloud (managed)
LLM         ──►  OpenRouter (OpenAI-compatible API)
```

Vercel's Marketplace has no graph or vector database, so Neo4j and Qdrant are
provisioned on their own managed clouds (both have free tiers). Embeddings run
inside the backend (fastembed), so no embeddings provider is needed.

Deploy order matters: provision the data + LLM services, deploy the backend, get
its public URL, then point the frontend at it.

---

## 1. Neo4j Aura (graph DB)

1. Create a free instance at <https://console.neo4j.io> (AuraDB Free).
2. On creation, **download / copy the generated password** (shown once).
3. Note the **Connection URI**: `neo4j+s://<id>.databases.neo4j.io`.

Values for the backend: `NEO4J_URI`, `NEO4J_USER` (=`neo4j`), `NEO4J_PASSWORD`.

## 2. Qdrant Cloud (vector DB)

1. Create a free cluster at <https://cloud.qdrant.io>.
2. Copy the **cluster URL** (e.g. `https://<id>.cloud.qdrant.io:6333`).
3. Create an **API key**.

Values: `QDRANT_URL`, `QDRANT_API_KEY`.

## 3. OpenRouter (LLM)

1. Create a key at <https://openrouter.ai/keys> (`sk-or-...`).
2. Add a little credit if required for your chosen model.

Values: `OPENAI_API_KEY` (the OpenRouter key), with
`OPENAI_BASE_URL=https://openrouter.ai/api/v1` and
`LLM_MODEL=openai/gpt-4o-mini` (already defaulted in `render.yaml`).

## 4. Backend on Render

1. In Render: **New > Blueprint**, connect this GitHub repo. Render reads
   `render.yaml` and builds `backend/Dockerfile`.
2. When prompted, fill the `sync: false` secrets from steps 1–3, plus
   `CORS_ORIGINS` (set to your Vercel URL from step 5, e.g.
   `https://graphrag-hierarchical-chat.vercel.app`).
3. Deploy. The service exposes `/health`; the public URL looks like
   `https://graphrag-api.onrender.com`.

Notes:
- On the free plan the service sleeps when idle; the first request after a cold
  start is slow (it also downloads the ~130 MB embedding model on first use).
- Same Docker image runs on Railway / Fly.io / Cloud Run if you prefer.

## 5. Frontend on Vercel

`NEXT_PUBLIC_API_URL` is baked at build time, so it must be set before the build.

```bash
cd frontend
vercel link                       # select/create the project
vercel env add NEXT_PUBLIC_API_URL production
#   value: https://graphrag-api.onrender.com
vercel --prod                     # build + deploy
```

Then set `CORS_ORIGINS` on Render to the resulting Vercel domain and redeploy the
backend (or trigger a redeploy) so the browser is allowed to call the API.

---

## Environment variable reference

| Service | Variable | Example |
|---------|----------|---------|
| Backend | `OPENAI_BASE_URL` | `https://openrouter.ai/api/v1` |
| Backend | `OPENAI_API_KEY` | `sk-or-...` |
| Backend | `LLM_MODEL` | `openai/gpt-4o-mini` |
| Backend | `NEO4J_URI` | `neo4j+s://xxxx.databases.neo4j.io` |
| Backend | `NEO4J_USER` | `neo4j` |
| Backend | `NEO4J_PASSWORD` | `...` |
| Backend | `QDRANT_URL` | `https://xxxx.cloud.qdrant.io:6333` |
| Backend | `QDRANT_API_KEY` | `...` |
| Backend | `CORS_ORIGINS` | `https://<app>.vercel.app` |
| Frontend | `NEXT_PUBLIC_API_URL` | `https://graphrag-api.onrender.com` |

## Smoke test after deploy

```bash
curl https://graphrag-api.onrender.com/health
# {"status":"ok","model":"openai/gpt-4o-mini"}
```

Then open the Vercel URL, ingest the sample dataset on the **Ingest** tab, and
ask a question on the **Chat** tab.
