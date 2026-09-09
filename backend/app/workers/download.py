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


def _base_opts(dest_dir: Path) -> dict:
    return {
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


def _write_cookiefile(dest_dir: Path) -> str | None:
    """Netscape cookies.txt holding just the Instagram `sessionid`, or None
    if INSTAGRAM_SESSION_ID is unset."""
    session_id = settings.instagram_session_id
    if not session_id:
        return None
    path = dest_dir / "ig_cookies.txt"
    path.write_text(
        "# Netscape HTTP Cookie File\n"
        f".instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\t{session_id}\n"
    )
    return str(path)


# Carousel slides yt-dlp writes to disk — anything that isn't one of these
# (a video slide, a leftover .json) is ignored: a carousel's pipeline is
# vision-only, so a video slide has no place in it.
# ponytail: drop video slides entirely; sample a frame from them like the
# reel path only if that ever turns out to lose real signal.
CAROUSEL_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _carousel_opts(dest_dir: Path) -> dict:
    return {
        **_base_opts(dest_dir),
        # A carousel *is* the playlist — every slide, not just the first.
        "outtmpl": str(dest_dir / "slide_%(playlist_index)03d.%(ext)s"),
        "noplaylist": False,
    }


def _run_ytdl(url: str, opts: dict) -> tuple[Path | None, dict]:
    def _run() -> tuple[Path | None, dict]:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # A playlist (a carousel post) has no single output file —
            # `prepare_filename` isn't meaningful for it; the carousel
            # caller globs the dest dir for the slide images instead.
            if info.get("_type") == "playlist":
                return None, info
            return Path(ydl.prepare_filename(info)), info

    # ponytail: a timed-out download keeps running in its thread until it
    # finishes on its own (Python can't force-kill a thread) — acceptable
    # at this phase's volume; revisit with a subprocess if it ever matters.
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run)
        try:
            return future.result(timeout=DOWNLOAD_TIMEOUT_SECONDS)
        except FutureTimeoutError as exc:
            raise ReelDownloadError(
                f"download timed out after {DOWNLOAD_TIMEOUT_SECONDS}s"
            ) from exc
        except Exception as exc:
            raise ReelDownloadError(str(exc)) from exc


def _run_with_session_fallback(
    url: str, dest_dir: Path, opts: dict, reel: Reel
) -> tuple[Path | None, dict]:
    """yt-dlp anonymous first. Instagram increasingly blocks logged-out
    fetches ("empty media response"); only when that fails do we fall back
    to the authenticated session (shared with instagrapi / Phase 9), since
    that account is rate-limit-risky and best kept off the hot path."""
    try:
        return _run_ytdl(url, opts)
    except ReelDownloadError as anon_error:
        cookiefile = _write_cookiefile(dest_dir)
        if not cookiefile:
            raise
        logger.info(
            "anonymous download failed reel_id=%s (%s), retrying with session cookie",
            reel.id,
            anon_error,
        )
        return _run_ytdl(url, {**opts, "cookiefile": cookiefile})


def download_reel(reel: Reel, dest_dir: Path) -> Path:
    """Download `reel.url` into `dest_dir` via yt-dlp, return the file path.

    Caller owns `dest_dir`'s lifecycle (create it, delete it when done) —
    Phases 5-6 read the same file later in the same worker invocation.
    """
    if not reel.url:
        raise ReelDownloadError("reel has no url")

    start = time.monotonic()
    path, info = _run_with_session_fallback(reel.url, dest_dir, _base_opts(dest_dir), reel)

    # Phase 9 (comment-to-unlock): the creator's username, needed later to
    # follow/unfollow via instagrapi — caller's existing `reel.save()` after
    # this call persists it, no extra write needed here.
    reel.creator_username = info.get("channel") or None

    if path is None or not path.exists():
        raise ReelDownloadError("yt-dlp reported success but no file was written")

    logger.info(
        "downloaded reel_id=%s path=%s size_bytes=%d elapsed=%.1fs",
        reel.id,
        path,
        path.stat().st_size,
        time.monotonic() - start,
    )
    return path


def download_carousel(reel: Reel, dest_dir: Path) -> list[Path]:
    """Download every image slide of an Instagram carousel post (`reel.url`
    is an `instagram.com/p/...` permalink) into `dest_dir`, return the image
    paths in slide order. Raises ReelDownloadError if nothing usable came
    down. Same anonymous-first / session-fallback rule as `download_reel`.
    """
    if not reel.url:
        raise ReelDownloadError("reel has no url")

    start = time.monotonic()
    _, info = _run_with_session_fallback(reel.url, dest_dir, _carousel_opts(dest_dir), reel)

    # Same as download_reel — creator username for Phase 9 (carousel posts
    # run "comment X to unlock" campaigns just as often as reels do).
    reel.creator_username = info.get("channel") or info.get("uploader") or None

    images = sorted(p for p in dest_dir.iterdir() if p.suffix.lower() in CAROUSEL_IMAGE_EXTS)
    if not images:
        raise ReelDownloadError("carousel download produced no image slides")

    logger.info(
        "downloaded carousel reel_id=%s slides=%d elapsed=%.1fs",
        reel.id,
        len(images),
        time.monotonic() - start,
    )
    return images
