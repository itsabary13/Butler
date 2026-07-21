FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

# wiki_sync.py commits to the bind-mounted private wiki/document repos as
# whatever user runs the container (root, no Dockerfile USER) — git refuses
# to commit without an identity, and there's no interactive setup step to
# configure one at runtime, so it's set once at build time instead.
RUN git config --global user.email "voice-relay@localhost" \
    && git config --global user.name "Butler Voice Relay"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY mcp-config.json .

# Local speech models: the Piper voice must be downloaded at image build
# time (or mounted as a volume) since the container has no interactive
# setup step. faster-whisper's model downloads/caches on first request
# instead — acceptable since it's a one-time cost, not per-request billing.
RUN python scripts/download_piper_voice.py

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
