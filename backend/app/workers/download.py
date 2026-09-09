import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path

from yt_dlp import YoutubeDL

from app.config import settings
from app.models.reel import Reel

logger = logging.getLogger("worker.download")

# Reels are short-form video — generous ceilings against a malformed/huge
# source or a stuck connection, not a tuned production limit.
MAX_FILESIZE_BYTES = 500 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 120


class ReelDownloadError(Exception):
    """Any yt-dlp failure (bad URL, unsupported, oversized, timeout),
    normalized to one type so the caller doesn't need to know yt-dlp's
    exception hierarchy."""


def _write_cookiefile(dest_dir: Path) -> str | None:
    """Netscape cookies.txt holding just the Instagram `sessionid`, or None
    if INSTAGRAM_SESSION_ID is unset (anonymous download, likely to fail)."""
    session_id = settings.instagram_session_id
    if not session_id:
        return None
    path = dest_dir / "ig_cookies.txt"
    path.write_text(
        "# Netscape HTTP Cookie File\n"
        f".instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\t{session_id}\n"
    )
    return str(path)


def download_reel(reel: Reel, dest_dir: Path) -> Path:
    """Download `reel.url` into `dest_dir` via yt-dlp, return the file path.

    Caller owns `dest_dir`'s lifecycle (create it, delete it when done) —
    Phases 5-6 read the same file later in the same worker invocation.
    """
    if not reel.url:
        raise ReelDownloadError("reel has no url")

    ydl_opts = {
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "max_filesize": MAX_FILESIZE_BYTES,
        # ponytail: single-file "best" format so no ffmpeg merge step is
        # needed — this phase only proves download, ffmpeg lands in Phase 5.
        "format": "best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }

    # Instagram now returns an empty media response to anonymous requests —
    # yt-dlp needs a logged-in `sessionid` cookie. Reuse the same session
    # value instagrapi uses (Phase 9). Without it, downloads fail with
    # "Instagram sent an empty media response".
    cookiefile = _write_cookiefile(dest_dir)
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    def _run() -> tuple[Path, dict]:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(reel.url, download=True)
            return Path(ydl.prepare_filename(info)), info

    start = time.monotonic()
    # ponytail: a timed-out download keeps running in its thread until it
    # finishes on its own (Python can't force-kill a thread) — acceptable
    # at this phase's volume; revisit with a subprocess if it ever matters.
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run)
        try:
            path, info = future.result(timeout=DOWNLOAD_TIMEOUT_SECONDS)
        except FutureTimeoutError as exc:
            raise ReelDownloadError(f"download timed out after {DOWNLOAD_TIMEOUT_SECONDS}s") from exc
        except Exception as exc:
            raise ReelDownloadError(str(exc)) from exc

    # Phase 9 (comment-to-unlock): the creator's username, needed later to
    # follow/unfollow via instagrapi — caller's existing `reel.save()` after
    # this call persists it, no extra write needed here.
    reel.creator_username = info.get("channel") or None

    if not path.exists():
        raise ReelDownloadError("yt-dlp reported success but no file was written")

    logger.info(
        "downloaded reel_id=%s path=%s size_bytes=%d elapsed=%.1fs",
        reel.id,
        path,
        path.stat().st_size,
        time.monotonic() - start,
    )
    return path
