# --- Light CUDA Runtime Image ---
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
# Use --allow-releaseinfo-change-suite to handle NVIDIA repo issues
RUN apt-get update --allow-releaseinfo-change || apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# --- Install GPU PyTorch (CUDA 12.1 compatible) ---
RUN pip install --no-cache-dir torch==2.1.0 --index-url https://download.pytorch.org/whl/cu121

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]