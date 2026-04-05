FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    espeak \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose ports
EXPOSE 5000 8080

# Environment variables
ENV JARVIS_DB_PATH=/app/data/jarvis.db
ENV JARVIS_LOG_FILE=/app/data/jarvis.log

# Default command
CMD ["python", "jarvis.py", "--mode", "api", "--host", "0.0.0.0"]
