To test `handler.py`, do as follows.

1. Build the Docker image

```bash
docker build -f docker/Dockerfile.runpod -t l2s-ai-runpod:latest .
```

2. Run the Docker container using volume mounting.

```bash
docker run --rm \
  --gpus all \
  -p 8080:8000 \
  --env-file .env \
  -v $(pwd)/runpod/handler.py:/app/handler.py \
  -v $(pwd)/src:/app/src \
  l2s-ai-runpod \
  python3 -u handler.py --rp_serve_api --rp_api_host 0.0.0.0
```