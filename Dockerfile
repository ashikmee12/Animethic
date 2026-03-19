FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Flask এবং bot একসাথে চালান
CMD python bot.py & gunicorn bot:app_flask --bind 0.0.0.0:8081
