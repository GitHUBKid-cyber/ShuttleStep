FROM python:3.13-slim

# MediaPipe needs these graphics libraries even on a server with no screen.
RUN apt-get update && apt-get install -y --no-install-recommends libegl1 libgles2 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Hugging Face Spaces expects the website on port 7860.
EXPOSE 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--timeout", "600", "--workers", "1", "--threads", "4", "app:app"]
