FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Local speech models: the Piper voice must be downloaded at image build
# time (or mounted as a volume) since the container has no interactive
# setup step. faster-whisper's model downloads/caches on first request
# instead — acceptable since it's a one-time cost, not per-request billing.
RUN python scripts/download_piper_voice.py

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
