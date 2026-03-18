FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Kill old processes and start new ones
CMD pkill -f "python bot.py" ; pkill -f "gunicorn" ; sleep 2 ; \
    gunicorn bot:app_flask --bind 0.0.0.0:8081 --workers 1 --threads 2 & \
    python bot.py
