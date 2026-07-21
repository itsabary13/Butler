"""Daily unattended proactive-notification scan (v1.6 addendum,
docs/architecture/voice-relay.md) — the one path in this service that
initiates contact rather than reacting to an inbound message.

The model (app.claude_code_client.run_proactive_check) only ever proposes
candidates via propose_notification (app/tools/notification_store.py); it
cannot send anything itself. This module is the deterministic gate that
decides what, if anything, actually goes out, and owns the only Telegram
send anywhere in the unattended path — dedup (never repeat the same thing
within its cooldown), a hard daily cap, and quiet hours all apply here,
not inside the model's own reasoning, so a misbehaving or prompt-injected
scan can at worst fill a table Python then caps, never spam the user.
"""

import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app import claude_code_client, telegram, wiki_sync
from app.config import settings
from app.tools import notification_store, wiki_tools

logger = logging.getLogger("voice_relay.proactive")


def _local_now() -> datetime:
    # requirements.txt pins the `tzdata` PyPI package specifically so this
    # works regardless of whether the base image's OS ships the IANA
    # database (python:3.12-slim doesn't by default) — zoneinfo falls back
    # to it automatically, no code-level handling needed here.
    try:
        tz = ZoneInfo(settings.local_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("invalid LOCAL_TIMEZONE %r, falling back to UTC", settings.local_timezone)
        tz = timezone.utc
    return datetime.now(tz)


def _within_quiet_hours() -> bool:
    hour = _local_now().hour
    if settings.quiet_hours_start <= settings.quiet_hours_end:
        return settings.quiet_hours_start <= hour < settings.quiet_hours_end
    return hour >= settings.quiet_hours_start or hour < settings.quiet_hours_end  # wraps past midnight


async def run_daily_scan() -> None:
    if not settings.proactive_enabled:
        return

    try:
        wiki_sync.sync_before(wiki_tools.wiki_dir())
    except Exception:
        logger.exception("proactive scan: wiki sync failed, continuing with local copy")

    run_start = datetime.now(timezone.utc).isoformat()

    try:
        # Runs the same blocking claude subprocess call the webhook path
        # uses, but this fires on a timer rather than per-request — offload
        # it so a concurrent voice/text turn's event-loop handling isn't
        # blocked for the scan's full duration.
        summary = await asyncio.to_thread(claude_code_client.run_proactive_check)
    except Exception:
        logger.exception("proactive scan: run_proactive_check failed")
        return

    logger.info("proactive scan result: %s", summary)

    proposals = notification_store.get_proposals_since(run_start)
    if not proposals:
        return

    if not _within_quiet_hours():
        for proposal in proposals:
            notification_store.mark_status(proposal["id"], "deferred")
        logger.info("proactive scan: %d proposal(s) deferred, outside quiet hours", len(proposals))
        return

    sent_today = notification_store.sent_count_last_24h()
    for proposal in proposals:
        if sent_today >= settings.proactive_max_per_day:
            notification_store.mark_status(proposal["id"], "deferred")
            continue

        if notification_store.was_recently_sent(proposal["dedup_key"], settings.proactive_cooldown_days):
            notification_store.mark_status(proposal["id"], "suppressed")
            continue

        try:
            await telegram.send_text_reply(settings.telegram_owner_chat_id, proposal["message"])
        except Exception:
            logger.exception("proactive scan: failed to send proposal id=%s", proposal["id"])
            continue

        notification_store.mark_status(proposal["id"], "sent")
        sent_today += 1


def register_scheduler(scheduler) -> None:
    from apscheduler.triggers.cron import CronTrigger

    scheduler.add_job(
        run_daily_scan,
        trigger=CronTrigger(hour=settings.proactive_hour_local, timezone=settings.local_timezone),
        id="proactive_daily_scan",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
