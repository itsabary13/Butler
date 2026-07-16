"""Keeps the relay's view of the private wiki/document repos current and
handles the two-writer race with a desktop Claude Code session
(docs/architecture/voice-relay.md's concurrency note).

Policy: git pull --rebase before reading/writing anything in a turn;
after a turn's writes, commit and push once, retrying the push once on
conflict, then logging (not failing) — the write already landed locally
either way, same "local save stands, backup push failure reported not
fatal" philosophy the remember skill already uses for a single-writer
case, applied here to two writers.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("voice_relay.wiki_sync")


def _run_git(repo_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def is_git_repo(repo_dir: Path) -> bool:
    return (repo_dir / ".git").exists()


def sync_before(repo_dir: Path) -> None:
    """Pull the latest changes before reading/writing, so we don't act on
    (or clobber) stale data relative to what the desktop session last
    pushed."""
    if not is_git_repo(repo_dir):
        logger.info("no git repo at %s — skipping pre-sync", repo_dir)
        return
    result = _run_git(repo_dir, "pull", "--rebase")
    if result.returncode != 0:
        logger.warning("git pull --rebase failed at %s: %s", repo_dir, result.stderr.strip())


def sync_after(repo_dir: Path, commit_message: str) -> None:
    """Commit and push whatever changed this turn. Never raises — a push
    failure is logged, not fatal, since the write already succeeded
    locally."""
    if not is_git_repo(repo_dir):
        logger.info("no git repo at %s — skipping post-sync", repo_dir)
        return

    status = _run_git(repo_dir, "status", "--porcelain")
    if not status.stdout.strip():
        return  # nothing changed this turn

    _run_git(repo_dir, "add", "-A")
    commit = _run_git(repo_dir, "commit", "-m", commit_message)
    if commit.returncode != 0:
        logger.warning("git commit failed at %s: %s", repo_dir, commit.stderr.strip())
        return

    push = _run_git(repo_dir, "push")
    if push.returncode == 0:
        return

    # retry once after a fresh pull --rebase, then give up quietly
    _run_git(repo_dir, "pull", "--rebase")
    retry = _run_git(repo_dir, "push")
    if retry.returncode != 0:
        logger.warning(
            "git push failed twice at %s (local commit stands): %s",
            repo_dir, retry.stderr.strip(),
        )
