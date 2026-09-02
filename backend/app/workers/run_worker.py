import logging
import time

from redis import Redis
from redis.exceptions import RedisError
from rq import SimpleWorker

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("worker.run_worker")

RECONNECT_DELAY_SECONDS = 5


def main() -> None:
    # Free-tier Redis (Upstash/Redis Cloud) drops idle connections
    # periodically, and RQ's own work() loop raises instead of reconnecting
    # — confirmed in practice, the worker died 3 times from this with no
    # supervisor to bring it back. Retry-forever loop instead of a real
    # process supervisor (systemd/pm2): simplest fix that keeps a single
    # long-lived worker process alive, matches this worker's actual shape
    # (one process, no orchestration around it yet).
    while True:
        try:
            connection = Redis.from_url(settings.redis_url)
            # SimpleWorker, not Worker: RQ's default Worker forks a child
            # process per job, and yt-dlp's networking stack touches macOS's
            # Objective-C runtime (Security.framework via urllib3/
            # SecureTransport) — forking after that crashes with "may have
            # been in progress in another thread when fork() was called"
            # (confirmed locally). SimpleWorker runs jobs in-process, no
            # fork, no crash — one job at a time per worker, scale via more
            # replicas.
            SimpleWorker(["reels"], connection=connection).work()
            # work() only returns normally on a clean shutdown (SIGINT/
            # SIGTERM) — don't loop forever restarting after that.
            break
        except RedisError as exc:
            logger.warning(
                "Redis connection lost (%s), reconnecting in %ss", exc, RECONNECT_DELAY_SECONDS
            )
            time.sleep(RECONNECT_DELAY_SECONDS)


if __name__ == "__main__":
    main()
