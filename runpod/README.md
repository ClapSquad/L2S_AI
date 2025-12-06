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
  clapmin/l2s-ai-runpod:latest \
  python3 -u handler.py --rp_serve_api --rp_api_host 0.0.0.0
```

**Run with CPU**: 
```bash
docker run --rm \
  -p 8080:8000 \
  --env-file .env \
  -v $(pwd)/runpod/handler.py:/app/handler.py \
  -v $(pwd)/src:/app/src \
  clapmin/l2s-ai-runpod:latest \
  python3 -u handler.py --rp_serve_api --rp_api_host 0.0.0.0
```

**Run on Windows Powershell**
```bash
docker run --rm `
  -p 8080:8000 `
  --env-file .env `
  -v ${PWD}/runpod/handler.py:/app/handler.py `
  -v ${PWD}/src:/app/src `
  l2s-ai-runpod:latest `
  python3 -u handler.py --rp_serve_api --rp_api_host 0.0.0.0
```

## Testing

### Test 1: Basic video processing (no subtitles, no vertical)

```bash
# Test 1: Basic video processing (no subtitles, no vertical)
curl -X POST http://localhost:8080/runsync \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "job_id": "local-test-001",
      "task": "process_video",
      "video_url": "https://your-supabase-url.supabase.co/storage/v1/object/public/videos/test-video.mp4",
      "options": {
        "method": "llm_only",
        "language": "auto",
        "subtitle": false,
        "vertical": false
      }
    }
  }'
```

### Test 2: With subtitles enabled

```bash
# Test 2: With subtitles enabled
curl -X POST http://localhost:8080/runsync \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "job_id": "local-test-002",
      "task": "process_video",
      "video_url": "YOUR_VIDEO_URL_HERE",
      "options": {
        "method": "llm_only",
        "subtitle": true,
        "vertical": false
      }
    }
  }'
```

### Test 3: With vertical conversion enabled

```bash
# Test 3: With vertical conversion enabled
curl -X POST http://localhost:8080/runsync \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "job_id": "local-test-003",
      "task": "process_video",
      "video_url": "YOUR_VIDEO_URL_HERE",
      "options": {
        "method": "llm_only",
        "subtitle": false,
        "vertical": true,
        "crop_method": "center"
      }
    }
  }'
```

### Test 4: Full pipeline (subtitles + vertical)

```bash
# Test 4: Full pipeline (subtitles + vertical)
curl -X POST http://localhost:8080/runsync \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "job_id": "local-test-004",
      "task": "process_video",
      "video_url": "YOUR_VIDEO_URL_HERE",
      "options": {
        "method": "llm_only",
        "subtitle": true,
        "vertical": true,
        "crop_method": "blur"
      }
    }
  }'
```