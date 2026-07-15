---
name: flag-emails
description: Reviews unread personal email and flags what's important or needs action, skipping promotions/ads/social/automated mail. Use when the user asks to check their email, see what's important, or find anything needing a response (e.g. "check my email", "anything important come in?", "do I need to respond to anything?"). Manually invoked, since it makes real changes to the user's Gmail (applying labels) — not triggered automatically by casual conversation.
disable-model-invocation: true
---

# Flag Emails

No local storage — this skill is stateless with respect to this repo. Gmail itself holds all the state, via labels applied directly to the user's account.

## Scope

- **Only unread mail** ("only new," per the user's decision) — never re-evaluate mail already read or already labeled by a prior run.
- **Skip promotions/ads/social/automated mail.** Search with `is:unread category:primary -in:draft` — Gmail's own categorization already excludes Promotions/Social/Updates/Forums, which covers most of this for free. Within what's left, still skip obviously automated senders (no-reply@, notifications@, newsletters, purely automated receipts/confirmations with nothing requiring a decision) even if they landed in Primary — Gmail's categorization isn't perfect.
- **"Personal" means addressed to the user**, not a bulk/list send — a real sender writing to the user specifically.

## Steps

1. **Search**: `search_threads` with query `is:unread category:primary -in:draft`, reasonable `pageSize` (start with 50, the max).
2. **Filter out automated/bulk mail** that slipped into Primary, per the Scope section above, using the subject/snippet from the search result (`THREAD_VIEW_MINIMAL` is enough for this first pass — don't fetch full bodies for everything).
3. **Judge each remaining thread** against two independent questions:
   - **Important?** Worth the user's attention — from a real person, meaningful content (personal, financial, legal, work-critical), even if no reply is strictly required.
   - **Needs action?** Requires something from the user — a reply, a decision, a payment, a form, a confirmation, a deadline.
   An email can be both, either, or neither. If genuinely unsure from the snippet alone, use `get_thread` to read the full body before deciding — don't guess off a truncated snippet for a borderline case.
4. **Ensure the labels exist**: `list_labels` first to check for `Jarvis: Important` and `Jarvis: Needs Action`; `create_label` for either that doesn't exist yet (first run only).
5. **Apply labels**: `label_thread` with the relevant label ID(s) for each thread that qualifies as Important and/or Needs Action. Never label something that's neither. Never unlabel/remove Gmail's own labels or change read/unread status — purely additive.
6. **Report back to the user**: a short list of what got flagged (subject line + one-line reason), not just a count — so the chat response itself is immediately useful, not only the labels sitting in Gmail. If nothing qualified, say so briefly.

## Explicitly out of scope

Replying to or drafting responses for flagged emails; deleting, archiving, or marking mail read; anything beyond unread Primary mail (e.g. a full historical inbox sweep) unless the user explicitly asks for a wider scope in that request.
