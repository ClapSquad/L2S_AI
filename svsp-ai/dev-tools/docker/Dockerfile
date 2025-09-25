# Base image with Python 3.12.11
FROM python:3.12.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (ffmpeg만 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project
COPY . .

CMD ["bash"]