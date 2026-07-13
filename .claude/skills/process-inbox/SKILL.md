---
name: process-inbox
description: Imports any new files sitting in the user's "Jarvis Inbox" Google Drive folder as documents. Use when the user asks to process/check their inbox, or asks what they've shared/sent recently (e.g. "process my inbox", "check what I've shared with you", "anything new from my phone?"). Manually invoked rather than auto-triggered on every mention, since it does bulk work over an external folder.
disable-model-invocation: true
---

# Process Inbox

Extends the Document module (`docs/architecture/document-module.md`) with a bulk-import entry point over a fixed Google Drive folder, reusing `add-document`'s existing Drive-download logic (`.claude/skills/add-document/SKILL.md`) per file rather than reimplementing it.

## Fixed inbox folder

Google Drive folder "Jarvis Inbox", ID `1patoJnkH6PfK_FGAI02yPi2numBV3HJg`. This is the phone-side capture point: the user shares a photo/file to this folder via their OS share sheet, then asks Jarvis to process the inbox next time they chat (mobile or desktop).

## Import tracking

`backend/document-module/files/.imported-inbox-ids.json` — a JSON array of Drive file IDs already imported. Gitignored along with the rest of `backend/document-module/files/`. Read it (treat as `[]` if it doesn't exist yet) before deciding what's new.

## Steps

1. **List the inbox folder**: `search_files` with `parentId = '1patoJnkH6PfK_FGAI02yPi2numBV3HJg'`. Not recursive — only files directly in this folder, no subfolders expected.
2. **Filter to new files**: skip any file whose Drive ID is already in `.imported-inbox-ids.json`.
3. **For each new file**, run the same import steps `add-document` uses (see that skill for full detail): determine title, derive an ASCII slug, download via `download_file_content` (real bytes for uploaded files, `exportMimeType: application/pdf` for Google-native Docs/Sheets/Slides), decode base64 and write bytes directly to `backend/document-module/files/<slug>.<ext>` (never through the model's text tools), write the metadata sidecar noting the source as "Jarvis Inbox" for provenance.
4. **Record the import**: append the Drive file ID to `.imported-inbox-ids.json` and save it, so a later run doesn't reprocess it.
5. **Report to the user**: "Imported N new document(s) from your inbox: ..." or "Nothing new in your inbox" if there's nothing to do — never silent, same as every other write in this project.
6. **Back up automatically**, same as `add-document`/`remember`/`sync-calendar`: commit and push `backend/document-module/files/`'s backup repo (`https://github.com/itsabary13/butler-documents`) after a successful import, unless the user's message says something like "no push."

## Explicitly out of scope

Recursing into subfolders of the inbox; deleting or archiving processed files in Drive itself (tracked locally instead, per above); anything the inbox folder doesn't directly contain.
