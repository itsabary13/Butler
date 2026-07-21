# Deploy: Voice Relay Phase 2 (VPS)

Concrete runbook for hosting the relay 24/7 on a DigitalOcean droplet, instead of running it locally (Phase 1). See `docs/architecture/voice-relay.md`'s Phase 2 addendum for the high-level reasoning; this file is the how-to.

All placeholders below (`<...>`) are fictional — fill in your own values, never commit real ones anywhere in this repo.

## 1. Create the droplet

- Ubuntu 24.04 LTS, region **fra1 (Frankfurt)** (closest DigitalOcean region to Israel).
- Size: Basic, **1 GB RAM / 1 vCPU / 25 GB SSD** (~$6/mo). A 1GB swap file (step 2) absorbs faster-whisper "small"'s transcription-time memory spike, so there's no need to pay for 2GB of RAM that mostly sits idle.
- Add your SSH public key at creation time (no password auth).

## 2. Initial hardening (SSH in as `root` once, then never again)

```bash
adduser deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy

# Disable root login and password auth
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh

# 1GB swap — absorbs faster-whisper's transcription-time memory spike on a
# 1GB-RAM droplet instead of risking an OOM kill. A single-user relay never
# transcribes concurrently, so occasional swap use just means a slightly
# slower reply, not a real problem.
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

apt update && apt install -y ufw fail2ban unattended-upgrades
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable
dpkg-reconfigure -plow unattended-upgrades
```

From here on, SSH in as `deploy`, not `root`.

## 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy
# log out/in (or `newgrp docker`) for the group change to take effect
docker compose version   # confirms the Compose plugin is present
```

## 4. Clone the repos

```bash
git clone https://github.com/itsabary13/Butler.git
cd Butler/backend/voice-relay

# Private repos — one-time clone using the fine-grained PAT as the password
sudo git clone https://<github-username>:<WIKI_GIT_TOKEN>@github.com/itsabary13/butler-memory.git /opt/butler-memory
sudo git clone https://<github-username>:<WIKI_GIT_TOKEN>@github.com/itsabary13/butler-documents.git /opt/butler-documents
sudo chown -R deploy:deploy /opt/butler-memory /opt/butler-documents
```

## 5. Create `.env`

```bash
cp .env.example .env
nano .env
```

Fill in every value from `.env.example`'s comments, with these VPS-specific differences from local dev:

```
WIKI_REPO_PATH=/data/wiki
DOCS_REPO_PATH=/data/docs
WIKI_HOST_PATH=/opt/butler-memory
DOCS_HOST_PATH=/opt/butler-documents
RELAY_DOMAIN=jarvis.<your-domain>
```

- Telegram values, Google OAuth values: same as documented in `.env.example` and `README.md`.
- `CLAUDE_CODE_OAUTH_TOKEN`: generate this by installing the `claude` CLI **locally on your own machine** (`npm install -g @anthropic-ai/claude-code`), logging in with your Claude.ai account, then running `claude setup-token` (it needs a browser for the login/consent screen) — paste the printed token into the VPS's `.env`, not run the command on the VPS itself. This bills against your Claude Pro/Max subscription's usage allowance, not a separate pay-per-token API key (`docs/architecture/voice-relay.md`'s v2 addendum).
- `GOOGLE_OAUTH_REFRESH_TOKEN`: generate this by running `scripts/google_oauth_setup.py` **locally on your own machine** (it needs a browser for the consent screen) — then paste the resulting refresh token into the VPS's `.env`, not run the script on the VPS itself.
- `PIPER_VOICE_MODEL_PATH`: leave as the default (`models/en_US-lessac-medium.onnx`) — the Dockerfile downloads this voice at image build time.

## 6. DNS

At your domain registrar, create an **A record**: `jarvis` (or whatever subdomain you chose) → the droplet's public IPv4 address. Give it a few minutes to propagate before the next step (Caddy's automatic TLS needs this to already resolve).

## 7. Bring it up

```bash
docker compose up -d --build
docker compose logs -f   # watch both services start; Ctrl-C to stop following
```

Caddy requests a Let's Encrypt certificate for `RELAY_DOMAIN` automatically on first start (needs port 80 reachable for the HTTP-01 challenge — already opened in step 2).

## 8. Verify

```bash
curl https://jarvis.<your-domain>/health
# expect: {"status":"ok"}
```

A valid HTTPS response (no cert warning) confirms Caddy's ACME issuance worked.

## 9. Register the Telegram webhook

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
     -d "url=https://jarvis.<your-domain>/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>" \
     -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

(Same call documented in `app/telegram.py`'s module docstring — run it from your own machine, not the VPS, since it's just a one-time registration call to Telegram, not something the relay needs to do itself.)

Then send a real voice message to the bot from your phone and confirm a spoken reply comes back.

## 10. (Optional) Enable and verify proactive notifications

Ships disabled (`PROACTIVE_ENABLED=false`) — the daily scan (`docs/architecture/voice-relay.md`'s v5 addendum) only runs once you opt in.

1. In `.env`, set `PROACTIVE_ENABLED=true` and `LOCAL_TIMEZONE` to your real IANA timezone (e.g. `Asia/Jerusalem`) — this controls both `PROACTIVE_HOUR_LOCAL` and quiet hours. Leave the other `PROACTIVE_*`/`QUIET_HOURS_*` values at their defaults unless you have a reason to change them.
2. `docker compose up -d` (env-only change — no `--build` needed).
3. Put something genuinely test-worthy in place first: a real Google Calendar event in the next `PROACTIVE_LOOKAHEAD_DAYS`, or a fact in the wiki that reads like an overdue pattern (e.g. tell the bot by voice/text "I had a checkup 7 months ago").
4. Trigger a scan immediately, without waiting for the scheduled hour or exposing any new endpoint — this runs the exact same code the daily cron job calls:
   ```bash
   docker compose exec voice-relay python -c "import asyncio; from app.proactive import run_daily_scan; asyncio.run(run_daily_scan())"
   ```
5. Confirm exactly one Telegram message arrives for the item you set up. Run the same command again immediately — confirm nothing sends a second time (dedup working).
6. The next morning, check `docker compose logs` around `PROACTIVE_HOUR_LOCAL` to confirm the scheduled job actually fired on its own, not just via the manual trigger above.

## Updating the deployment later

```bash
cd Butler && git pull
cd backend/voice-relay && docker compose up -d --build
```

Session history (`data/sessions.db`), the proactive-notification dedup log (`data/notifications.db`), and the wiki/document clones (`/opt/butler-memory`, `/opt/butler-documents`) all live outside the container image, so a rebuild/redeploy doesn't lose them. The faster-whisper model is cached in the `whisper_cache` named volume for the same reason — it isn't re-downloaded on every redeploy.

**Do not add `uvicorn --workers` / scale to multiple replicas of this service.** The proactive daily scan (v5 addendum) is scheduled in-process; more than one worker would run — and fire — more than one scheduler, double-sending notifications.

## Cost summary

- Droplet: ~$6/mo (DigitalOcean, 1GB/1vCPU + swap).
- Domain: ~$10/yr (one-time annual, registrar of your choice).
- Answering: billed against your existing Claude Pro/Max subscription's usage allowance (`CLAUDE_CODE_OAUTH_TOKEN`) — no separate pay-per-token API cost. Subject to that plan's normal rate limits.
- Speech (faster-whisper/Piper) and Google Calendar API: no additional cost.

If real usage shows the 1GB droplet is too slow even with swap, resizing to 2GB is a few clicks in DigitalOcean's dashboard (brief downtime, no redeployment needed) — no need to over-provision up front.
