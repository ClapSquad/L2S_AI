To test `handler.py`, do as follows.

1. Build the Docker image

```bash
docker build -f docker/Dockerfile.runpod -t l2s-ai-runpod:latest .
```

2. Run the Docker container using volume mounting.
 -v -l
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

**Run with CPU**: `docker run --rm -p 8080:8000 --env-file .env -v ${PWD}/runpod/handler.py:/app/handler.py -v ${PWD}/src:/app/src l2s-ai-runpod python3 -u handler.py --rp_serve_api --rp_api_host 0.0.0.0`

request body format

- summary generation
```json
{
  "input": {
    "job_id": "0ee8b21e-e86e-4be4-8f7a-29f39ba33be0",
    "task": "process_video",
    "video_url": "https://abcd.supabase.co/storage/v1/object/public/videos/0ee8b21e-e86e-4be4-8f7a-29f39ba33be0.mp4",
    "options": {
      "method": "llm_only",
      "language": "auto"
    }
  }
}
```

- thumbnail generation
```json
{
  "input": {
    "job_id": "0ee8b21e-e86e-4be4-8f7a-29f39ba33be0",
    "task": "generate_thumbnail",
    "video_url": "https://abcd.supabase.co/storage/v1/object/public/videos/0ee8b21e-e86e-4be4-8f7a-29f39ba33be0.mp4"
  }
}
```