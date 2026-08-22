# Kubernetes deployment (GPU / production path)

The docker-compose setup is the one-command local path and self-hosts the LLM
with Ollama on CPU. For production you typically want a GPU-backed serving
engine; these manifests run the LLM with **vLLM** (OpenAI-compatible, supports
guided JSON decoding for reliable extraction).

The application code is unchanged: the API talks to any OpenAI-compatible
endpoint, so only `OPENAI_BASE_URL` / `LLM_MODEL` differ from compose.

## Prerequisites

- A cluster with a **GPU node pool** (NVIDIA device plugin installed) for vLLM.
- Container images for the API and web built and pushed to a registry; update
  the `image:` fields in `40-api.yaml` and `50-web.yaml`.

## Apply

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/10-neo4j.yaml
kubectl apply -f k8s/20-qdrant.yaml
kubectl apply -f k8s/30-vllm.yaml     # requires GPU
kubectl apply -f k8s/40-api.yaml
kubectl apply -f k8s/50-web.yaml
```

## Notes

- `emptyDir` volumes are placeholders. Use `PersistentVolumeClaim`s for Neo4j,
  Qdrant, and the Hugging Face cache in real deployments.
- Secrets (Neo4j password, any API keys) belong in a `Secret`, not inline env.
- To use a managed LLM (e.g. OpenRouter) instead of vLLM, delete `30-vllm.yaml`
  and set `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, `OPENAI_API_KEY` (from
  a Secret), and `LLM_MODEL=openai/gpt-4o-mini` in `40-api.yaml`.
