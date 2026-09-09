from pathlib import Path

import pytest
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from app.models.reel import Reel
from app.workers import download as download_module
from app.workers.download import ReelDownloadError, download_reel


class _FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL — writes a small real file to the
    outtmpl's directory so download_reel's existence check passes, without
    hitting the network."""

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=True):
        return {"id": "abc123", "ext": "mp4"}

    def prepare_filename(self, info):
        path = Path(self.opts["outtmpl"] % info)
        path.write_bytes(b"fake video bytes")
        return str(path)


class _FailingYoutubeDL:
    def __init__(self, opts, error_message):
        self.opts = opts
        self._error_message = error_message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=True):
        raise YtDlpDownloadError(self._error_message)


def test_download_reel_success_writes_file_and_returns_its_path(tmp_path, monkeypatch):
    monkeypatch.setattr(download_module, "YoutubeDL", _FakeYoutubeDL)
    reel = Reel(url="https://www.instagram.com/reel/abc123/")

    path = download_reel(reel, tmp_path)

    assert path.exists()
    assert path.read_bytes() == b"fake video bytes"


def test_download_reel_captures_creator_username_from_info_dict(tmp_path, monkeypatch):
    class _FakeYoutubeDLWithChannel(_FakeYoutubeDL):
        def extract_info(self, url, download=True):
            return {"id": "abc123", "ext": "mp4", "channel": "cyberbuddyshivam"}

    monkeypatch.setattr(download_module, "YoutubeDL", _FakeYoutubeDLWithChannel)
    reel = Reel(url="https://www.instagram.com/reel/abc123/")

    download_reel(reel, tmp_path)

    assert reel.creator_username == "cyberbuddyshivam"


def test_download_reel_leaves_creator_username_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(download_module, "YoutubeDL", _FakeYoutubeDL)
    reel = Reel(url="https://www.instagram.com/reel/abc123/")

    download_reel(reel, tmp_path)

    assert reel.creator_username is None


def test_download_reel_raises_on_resolution_failure(tmp_path, monkeypatch):
    def _raising_youtubedl(opts):
        return _FailingYoutubeDL(opts, "Unsupported URL")

    monkeypatch.setattr(download_module, "YoutubeDL", _raising_youtubedl)
    reel = Reel(url="https://www.instagram.com/reel/bad/")

    with pytest.raises(ReelDownloadError, match="Unsupported URL"):
        download_reel(reel, tmp_path)


def test_download_reel_raises_when_oversized(tmp_path, monkeypatch):
    def _raising_youtubedl(opts):
        return _FailingYoutubeDL(opts, "File is larger than max-filesize, aborting")

    monkeypatch.setattr(download_module, "YoutubeDL", _raising_youtubedl)
    reel = Reel(url="https://www.instagram.com/reel/huge/")

    with pytest.raises(ReelDownloadError, match="max-filesize"):
        download_reel(reel, tmp_path)


def test_download_reel_raises_when_url_missing(tmp_path):
    reel = Reel(url=None)

    with pytest.raises(ReelDownloadError, match="no url"):
        download_reel(reel, tmp_path)


def test_download_reel_stays_anonymous_when_first_attempt_succeeds(tmp_path, monkeypatch):
    opts_seen = []

    class _RecordingYoutubeDL(_FakeYoutubeDL):
        def __init__(self, opts):
            super().__init__(opts)
            opts_seen.append(opts)

    monkeypatch.setattr(download_module, "YoutubeDL", _RecordingYoutubeDL)
    monkeypatch.setattr(download_module.settings, "instagram_session_id", "sess-123")
    reel = Reel(url="https://www.instagram.com/reel/abc123/")

    download_reel(reel, tmp_path)

    assert len(opts_seen) == 1
    assert "cookiefile" not in opts_seen[0]


def test_download_reel_retries_with_session_cookie_after_anonymous_failure(tmp_path, monkeypatch):
    opts_seen = []

    class _FailThenSucceedYoutubeDL(_FakeYoutubeDL):
        def __init__(self, opts):
            super().__init__(opts)
            opts_seen.append(opts)

        def extract_info(self, url, download=True):
            if "cookiefile" not in self.opts:
                raise YtDlpDownloadError("Instagram sent an empty media response")
            return super().extract_info(url, download)

    monkeypatch.setattr(download_module, "YoutubeDL", _FailThenSucceedYoutubeDL)
    monkeypatch.setattr(download_module.settings, "instagram_session_id", "sess-123")
    reel = Reel(url="https://www.instagram.com/reel/abc123/")

    path = download_reel(reel, tmp_path)

    assert path.exists()
    assert len(opts_seen) == 2
    cookiefile = Path(opts_seen[1]["cookiefile"])
    assert "sessionid\tsess-123" in cookiefile.read_text()


def test_download_reel_raises_when_anonymous_fails_and_no_session(tmp_path, monkeypatch):
    def _raising_youtubedl(opts):
        return _FailingYoutubeDL(opts, "Instagram sent an empty media response")

    monkeypatch.setattr(download_module, "YoutubeDL", _raising_youtubedl)
    monkeypatch.setattr(download_module.settings, "instagram_session_id", "")
    reel = Reel(url="https://www.instagram.com/reel/abc123/")

    with pytest.raises(ReelDownloadError, match="empty media response"):
        download_reel(reel, tmp_path)


@pytest.mark.slow
def test_download_reel_against_a_real_stable_public_video(tmp_path, app):
    # A small (~800KB), long-stable direct video file — hits yt-dlp's
    # generic extractor rather than a site-specific one, so it isn't
    # exposed to YouTube's anti-bot format gating (confirmed flaky in this
    # sandbox even for well-known fixture videos). `app` isn't otherwise
    # used here, but Reel() needs Beanie initialized (only guaranteed when
    # this test runs standalone via -m slow).
    reel = Reel(url="https://www.w3schools.com/html/mov_bbb.mp4")

    path = download_reel(reel, tmp_path)

    assert path.exists()
    assert path.stat().st_size > 0
