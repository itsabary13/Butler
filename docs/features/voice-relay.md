# Feature: Voice Relay (Phase 1)

Jarvis is now reachable by voice from your phone — not just from a Claude Code session at your desk.

## What it does

- **Talk to Jarvis over Telegram.** Send a voice message to a dedicated Telegram bot from anywhere (no home network required), and Jarvis transcribes it, thinks about it, and replies with a spoken voice message back.
- **Knows what you've already told it.** The relay reads the same memory wiki `remember`/`recall` use, so it can answer using facts you've saved previously — the same information, reached a different way.
- **Can save new memories and reminders by voice.** Tell it something worth keeping, and it saves it the same way `remember` would (merging into an existing page, or creating a new one) — just triggered by a spoken message instead of a typed one.
- **Can create calendar events by voice.** "Schedule lunch with Alex next Wednesday at one" creates a real event on your primary Google Calendar. If a date or time is ambiguous, it asks rather than guessing. Create-only for now — it won't move or cancel an existing event by voice yet.
- **Remembers the last few turns of a conversation.** A short follow-up in the same chat ("actually make it 2pm") is understood in context, without you needing to repeat the whole request. This short-term memory is separate from the permanent wiki and doesn't survive a relay restart.
- **Can check whether a document exists.** Ask whether Jarvis has a particular document on file, and it can confirm by name/metadata — it doesn't read or deliver file contents over voice yet.

## How it works, briefly

This is the one part of Jarvis that runs as an actual always-on-style server process, rather than living entirely inside Claude Code skills — genuine voice (understanding speech, speaking a reply) has no way to work without one. It's a small standalone service (`backend/voice-relay/`) that: transcribes your voice message, has its own conversation with Claude (using the same wiki files as the rest of Jarvis, plus calendar/document tools), and speaks the reply back through Telegram. It's a separate, small program from the skills that power the rest of this repo — it reuses their *conventions* (the same memory file format, for instance) but doesn't call them directly, since skills only run inside a Claude Code session and this needs to run on its own.

Right now it runs locally on your own machine (or through a temporary tunnel like ngrok) — it is not yet hosted anywhere that's on 24/7 by itself. That's the planned next phase.

## Known limitations (Phase 1, deferred to later phases)

- **Not hosted 24/7 yet.** It runs only while you have it running locally. Moving it to always-on hosting is a separate, later phase — this phase is about proving the voice mechanism itself works.
- **Turn-based voice messages, not a live phone call.** You send a voice note and get one back; there's no real-time streaming conversation with interruptions yet.
- **Single user only.** It's locked to one Telegram chat (yours) — there's no multi-user support.
- **Calendar is create-only.** No update or delete by voice yet, matching the same limitation Jarvis's calendar sync already has.
- **No document contents over voice.** It can confirm a document exists but can't read it aloud or send the file itself.
- **Billed separately from your Claude Code subscription.** This service makes its own direct API calls to Anthropic and Google Calendar, so it has its own usage cost outside your normal Claude Code/claude.ai plan. Speech-to-text and text-to-speech run fully locally (no OpenAI or other speech-provider account, no per-request cost for either).

## Where things live (for reference)

- `specs/epics/voice-relay.md` — full scope, phasing rationale, and decision history
- `backend/voice-relay/` — the actual implementation (a standalone Python/FastAPI service, not a Claude Code skill)
- `backend/voice-relay/README.md` — setup steps, required accounts/credentials, and the billing note above in more detail
