# Dockerfile for AI Agent Call Center

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for PyAudio
RUN apt-get update && apt-get install -y \
    python3-dev \
    portaudio19-dev \
    gcc \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Initialize database on container start
ENV DATABASE_URL="sqlite:///./callcenter.db"

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]