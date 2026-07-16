# Story: Have a voice conversation with Butler from anywhere

## User story

As the Butler user, I want to send a voice message from my phone (via Telegram, on any network) and get a spoken reply that's aware of what Butler already knows about me, so that I don't need to be at my computer or type to use it.

## Acceptance criteria

- **Given** the user sends a voice message to the Telegram bot from their own allowlisted chat, **when** the relay processes it, **then** it's transcribed, answered using relevant wiki content (if any topic matches), and replied to as a voice message.
- **Given** a question relates to something in the wiki (e.g. a fact, a reminder), **when** the relay answers, **then** it reads the specific relevant page(s) — following `[[wiki-link]]` references where relevant — rather than guessing or ignoring stored memory.
- **Given** a follow-up message arrives within the session TTL, **when** the relay answers, **then** it uses the prior turn(s) of that same conversation as context (e.g. "actually make it 2pm" resolves against the immediately preceding request).
- **Given** a message arrives from a `chat_id` other than the configured owner, **when** the webhook receives it, **then** it's dropped without processing or replying.
- **Given** the webhook request doesn't present the correct `secret_token`, **when** it arrives, **then** it's rejected.

## Edge cases

- No wiki page matches the question — answer without fabricating a memory that doesn't exist (same rule `recall` already follows).
- Session TTL has expired since the last message — treat it as a fresh conversation, not a continuation.
- STT produces a low-confidence or garbled transcription — still attempt an answer; don't silently fail without any reply.
- The relay process restarts — in-memory/short-term session context may be lost (accepted limitation for v1); wiki and calendar data must not be lost (git-backed).

## Functional requirements

- FR-1: The system MUST verify both the webhook's `secret_token` and the sender's `chat_id` against a single allowlisted value before processing anything.
- FR-2: The system MUST transcribe incoming voice messages via a speech-to-text provider and MUST NOT proceed to answer using a raw/unprocessed audio blob.
- FR-3: The system MUST assemble context from the existing wiki (`backend/memory-module/wiki/`) using the same page/link conventions `remember`/`recall` use, without requiring changes to that file format.
- FR-4: The system MUST maintain short-term, per-`chat_id` conversation history with a time-based expiry, not global/shared across different conversations.
- FR-5: The system MUST reply with synthesized speech, not text-only, for every processed voice message.
- FR-6: Real-time streaming/interruption-style conversation (a live phone call) is OUT OF SCOPE for this story — Telegram's turn-based voice-message model is the v1 transport.
