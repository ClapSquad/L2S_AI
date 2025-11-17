# Stage 1: Build the dependencies
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Create and activate a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies into the virtual environment
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Create the final image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies (ffmpeg is needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy the rest of the project
COPY . .

# The port the server is expected to run on
# Note that this does not actually publish the port
EXPOSE 8000

# Command to run the Uvicorn server
# It will look for the 'app' object in the 'main.py' file.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]