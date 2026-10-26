FROM python:3.13-slim

# MediaPipe needs these graphics libraries even on a server with no screen.
RUN apt-get update && apt-get install -y --no-install-recommends libegl1 libgles2 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Hosts like Render tell the app which port to use in $PORT; 7860 is the fallback (Hugging Face Spaces).
EXPOSE 7860
CMD gunicorn --bind 0.0.0.0:${PORT:-7860} --timeout 600 --workers 1 --threads 4 app:app
