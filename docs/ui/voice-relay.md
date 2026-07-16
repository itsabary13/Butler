# UI Design: Voice Relay

**No dedicated UI.** Telegram itself is the interface — the user speaks a voice message into the Telegram app (any device, no new app to install) and receives a voice message back. There is no Butler-specific screen, web page, or mobile app to design or build for v1.

If a future phase adds a different transport (a real phone call, a web UI, a dedicated mobile app — per the original oversized spec's "multi-device support" wishlist), that would be a new epic's UI concern, not an extension of this one.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact; no `frontend/voice-relay/` subfolder exists.

## Hand-off

Next: `backend-developer` (`/backend-developer`) for implementation.
