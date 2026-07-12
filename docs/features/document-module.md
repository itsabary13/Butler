# Feature: Document Module

Jarvis can store actual files for you — PDFs, Word documents, images, anything — and find them again later, separate from its Memory (which only remembers text facts).

## What it does

- **Stores real files.** Give Jarvis a path to a file, or point it at something in your Google Drive, and ask it to save/store it — it keeps an exact copy, no re-encoding, no compression, byte-for-byte. Google Docs/Sheets/Slides (which aren't real files until exported) come in as PDF by default.
- **Finds them again.** Ask about a document later (by topic, not necessarily its exact name) and Jarvis locates it and opens it — for readable formats (PDF, plain text), it can summarize or answer questions using the actual content, not just confirm the file exists.
- **Backed up automatically to a private repo.** Your documents survive a machine change the same way Memory's do — a separate private backup, never exposed via the public-facing project repo. Unlike Memory, this backup isn't pushed after every single add yet — ask if you'd like that too.

## How it works, briefly

Each stored document is its original file plus a small metadata note (a title, the original filename, when it was added) — similar in spirit to how Memory keeps a small note per topic, but here the "content" is the real file itself, not something Jarvis writes for you. There's no database and no server: local files only, kept independent from Memory's wiki.

## Known limitations (deferred, not yet built)

- **No editing, replacing, or deleting** a stored document — saving something with the same topic again creates a separate document rather than replacing the old one.
- **No Private/Work tagging yet** (unlike Memory) — everything you store is retrievable the same way for now.
- **No full-text search inside document contents** — Jarvis finds documents by their metadata/topic, then reads the matching one; it doesn't index the contents of every document up front.
- **Only formats Jarvis can read directly** (PDF, plain text, etc.) can be summarized/searched by content — other formats are still stored and findable, just not "readable" by Jarvis.

## Where things live (for reference)

- `specs/epics/document-module.md` — full scope and decision history
- `.claude/skills/add-document/`, `.claude/skills/find-document/` — the actual implementation
- `backend/document-module/files/` — your stored documents. Excluded from the main Butler repo (personal data) but backed up to its own private GitHub repo (`butler-documents`) — see `backend/document-module/README.md` for restore steps.
