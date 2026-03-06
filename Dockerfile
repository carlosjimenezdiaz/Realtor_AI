FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Runtime directories — volumes override these at container start
RUN mkdir -p data logs

# Entrypoint: blocking scheduler daemon
CMD ["python", "scheduler.py"]
